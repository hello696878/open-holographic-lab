"""Pure-array intensity errors, regional power fraction and variation.

Inputs are plain native-float64, nonempty two-dimensional arrays of finite
nonnegative intensities. Reconstruction values above one are valid. Arrays
must already share a declared intensity scale and spatial alignment: nothing
is clipped, normalized, resized or registered here. Read-only/noncontiguous
inputs are accepted without mutation or retention; all results are Python
floats. Wrong types/dtypes raise TypeError, while invalid shapes, domains and
unusable arithmetic raise ValueError.

Arithmetic uses float64 with local NumPy overflow, underflow, invalid and
divide-by-zero errors enabled. Precision-losing subnormal intermediates can
therefore be rejected even when a mathematical ratio would be finite. There
is no numerical rescaling or epsilon denominator. Caller error settings are
restored on both success and failure. PSNR's validated exact-match infinity
is the only intentionally nonfinite result.

These metrics evaluate intensity, not the squared amplitude residual used by
Gerchberg--Saxton. Optical power is proportional to sum(I), whereas the NMSE
denominator sum(I_target**2) is a squared intensity norm.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from .validation import (
    require_all_finite,
    require_ndim,
    require_positive_finite_float,
    require_shape,
)

__all__ = [
    "intensity_mse",
    "intensity_nmse",
    "intensity_psnr",
    "signal_region_power_fraction",
    "regional_intensity_cv",
]


def _require_intensity(array: NDArray[np.float64], name: str) -> None:
    """Validate an intensity array without coercion or writes."""
    if type(array) is not np.ndarray:
        raise TypeError(f"{name} must be a plain numpy.ndarray, got {type(array).__name__}")
    if array.dtype != np.dtype(np.float64) or not array.dtype.isnative:
        raise TypeError(f"{name} must have native float64 dtype, got {array.dtype!r}")
    require_ndim(array, 2, name)
    if array.size == 0:
        raise ValueError(f"{name} must have a nonempty 2-D shape, got {array.shape}")
    require_all_finite(array, name)
    negative = array < 0.0
    if bool(np.any(negative)):
        first = tuple(int(index) for index in np.argwhere(negative)[0])
        raise ValueError(f"{name} must be nonnegative, got {array[first]!r} at index {first}")


def _require_comparison(
    target: NDArray[np.float64], reconstruction: NDArray[np.float64],
) -> None:
    """Validate both maps before any exact-result shortcut."""
    _require_intensity(target, "target_intensity")
    _require_intensity(reconstruction, "reconstruction_intensity")
    require_shape(reconstruction, target.shape, "reconstruction_intensity")


def _require_mask(mask: NDArray[np.bool_], shape: tuple[int, ...], name: str) -> None:
    """Require a plain Boolean mask on exactly the supplied window."""
    if type(mask) is not np.ndarray:
        raise TypeError(f"{name} must be a plain numpy.ndarray, got {type(mask).__name__}")
    if mask.dtype != np.dtype(np.bool_):
        raise TypeError(f"{name} must have Boolean dtype, got {mask.dtype!r}")
    require_ndim(mask, 2, name)
    require_shape(mask, shape, name)


def _checked_nonnegative(value: float, name: str, *, positive: bool = False) -> float:
    """Require a usable scalar and return a built-in float."""
    result = float(value)
    if not math.isfinite(result) or result < 0.0 or (positive and result == 0.0):
        domain = "positive finite" if positive else "nonnegative finite"
        raise ValueError(f"{name} must be {domain} and representable, got {result!r}")
    return result


def _squared_error_sum(
    target: NDArray[np.float64], reconstruction: NDArray[np.float64],
) -> float:
    """Direct squared error, rejecting a lost nonzero difference."""
    squared_error = (reconstruction - target)**2
    total = _checked_nonnegative(np.sum(squared_error, dtype=np.float64), "squared error sum")
    if total == 0.0 and not np.array_equal(target, reconstruction):
        raise ValueError("nonidentical intensities produced zero squared error; arithmetic is unusable")
    return total


def _mean_squared_error(
    target: NDArray[np.float64], reconstruction: NDArray[np.float64],
) -> float:
    """Float64 sum/N, with a NumPy division that reports underflow."""
    total = _squared_error_sum(target, reconstruction)
    mean = _checked_nonnegative(np.divide(total, target.size), "intensity MSE")
    if total > 0.0 and mean == 0.0:
        raise ValueError("positive squared error produced zero MSE; arithmetic is unusable")
    return mean


def intensity_mse(
    *, target_intensity: NDArray[np.float64], reconstruction_intensity: NDArray[np.float64],
) -> float:
    """Return sum((reconstruction-target)**2)/N in squared intensity units.

    Both arrays use the same declared intensity scale and exact nonempty 2-D
    shape. Zero targets are valid. Common intensity scaling by c multiplies
    this error by c**2; this is neither a normalized error nor an amplitude
    error. No alignment, normalization or upper-one restriction is applied.
    """
    _require_comparison(target_intensity, reconstruction_intensity)
    try:
        with np.errstate(all="raise"):
            return _mean_squared_error(target_intensity, reconstruction_intensity)
    except (FloatingPointError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError(f"intensity_mse has unusable float64 arithmetic: {exc}") from exc


def intensity_nmse(
    *, target_intensity: NDArray[np.float64], reconstruction_intensity: NDArray[np.float64],
) -> float:
    """Return sum((reconstruction-target)**2)/sum(target**2), dimensionless.

    The target is explicitly the denominator reference. Its squared intensity
    norm is not optical power and must be positive, finite and representable,
    even for identical arrays. Zero target norm is undefined and raises.
    This squared relative error is not NRMSE or the GS amplitude residual;
    it is not bounded above by one. Common positive intensity scaling leaves
    it unchanged when the required arithmetic remains usable.
    """
    _require_comparison(target_intensity, reconstruction_intensity)
    try:
        with np.errstate(all="raise"):
            target_norm = _checked_nonnegative(
                np.sum(target_intensity**2, dtype=np.float64),
                "target squared intensity norm", positive=True,
            )
            error_sum = _squared_error_sum(target_intensity, reconstruction_intensity)
            return _checked_nonnegative(np.divide(error_sum, target_norm), "intensity NMSE")
    except (FloatingPointError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError(f"intensity_nmse has unusable float64 arithmetic: {exc}") from exc


def intensity_psnr(
    *, target_intensity: NDArray[np.float64], reconstruction_intensity: NDArray[np.float64],
    data_range: float,
) -> float:
    """Return intensity PSNR in dB for an explicit finite positive data_range.

    data_range uses the same intensity units as both images and is never
    inferred from their observed maxima. All inputs, including data_range,
    are validated before an exact match returns positive infinity. Equality
    is numerical, so signed zeros compare equal; no tolerance is used.

    Otherwise use 20*log10(data_range)-10*log10(MSE) with usable positive MSE.
    This avoids squaring the range or forming an overflowing ratio. Negative
    PSNR and reconstruction overshoot remain valid. Common image scaling
    preserves PSNR only when data_range is scaled consistently. A nonidentical
    input with unrepresentable squared error raises instead of returning inf.
    """
    _require_comparison(target_intensity, reconstruction_intensity)
    try:
        with np.errstate(all="raise"):
            declared_range = require_positive_finite_float(data_range, "data_range")
            if np.array_equal(target_intensity, reconstruction_intensity):
                return math.inf
            mse = _checked_nonnegative(
                _mean_squared_error(target_intensity, reconstruction_intensity),
                "nonidentical-image MSE", positive=True,
            )
            result = 20.0 * math.log10(declared_range) - 10.0 * math.log10(mse)
            if not math.isfinite(result):
                raise ValueError(f"intensity PSNR must be finite for nonidentical inputs, got {result!r}")
            return float(result)
    except (FloatingPointError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError(f"intensity_psnr has unusable float64 arithmetic: {exc}") from exc


def signal_region_power_fraction(
    *, reconstruction_intensity: NDArray[np.float64], signal_mask: NDArray[np.bool_],
) -> float:
    """Return sum(reconstruction[signal_mask])/sum(reconstruction).

    The denominator covers the entire supplied window and must be positive,
    finite and representable. With that valid denominator, an empty mask
    returns exactly zero and an all-window mask returns exactly one. The mask
    is supplied explicitly; no threshold or region is inferred from an image.

    For uniform pixel area the common area cancels, leaving a dimensionless
    power fraction (mathematically between zero and one). This is not a claim
    of source-normalized or hardware diffraction efficiency. Missing power
    outside the supplied window is not part of the denominator. Results are
    reported without clipping; inputs and their spatial sampling are unchanged.
    """
    _require_intensity(reconstruction_intensity, "reconstruction_intensity")
    _require_mask(signal_mask, reconstruction_intensity.shape, "signal_mask")
    try:
        with np.errstate(all="raise"):
            total = _checked_nonnegative(
                np.sum(reconstruction_intensity, dtype=np.float64),
                "total reconstruction intensity", positive=True,
            )
            if not bool(np.any(signal_mask)):
                return 0.0
            if bool(np.all(signal_mask)):
                return 1.0
            signal = _checked_nonnegative(
                np.sum(reconstruction_intensity[signal_mask], dtype=np.float64),
                "signal-region intensity sum",
            )
            return _checked_nonnegative(np.divide(signal, total), "signal-region power fraction")
    except (FloatingPointError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError(f"signal_region_power_fraction has unusable float64 arithmetic: {exc}") from exc


def regional_intensity_cv(
    *, intensity: NDArray[np.float64], mask: NDArray[np.bool_],
) -> float:
    """Return population std(intensity[mask])/mean(intensity[mask]).

    Use ddof=0: this dimensionless coefficient describes the selected pixels,
    not an estimated sample standard deviation. The region must be nonempty
    with positive mean. An exactly constant positive region, including one
    pixel, returns exactly zero without unnecessary variance arithmetic.

    Lower CV means less regional variation when uniform brightness is intended.
    Desired Gaussian falloff is not thereby a defect or speckle. CV may exceed
    one; it is neither clipped nor converted into an accuracy score. Common
    positive intensity scaling preserves it when arithmetic remains usable.
    Valid intensities outside the region do not affect its value.
    """
    _require_intensity(intensity, "intensity")
    _require_mask(mask, intensity.shape, "mask")
    selected = intensity[mask]
    if selected.size == 0:
        raise ValueError("mask must select at least one pixel for regional intensity CV")
    if bool(np.all(selected == selected[0])):
        if selected[0] == 0.0:
            raise ValueError("regional intensity CV requires positive mean; selected intensities are all zero")
        return 0.0
    try:
        with np.errstate(all="raise"):
            mean = _checked_nonnegative(
                np.mean(selected, dtype=np.float64), "selected-region mean intensity", positive=True,
            )
            standard_deviation = _checked_nonnegative(
                np.std(selected, dtype=np.float64, ddof=0), "selected-region intensity standard deviation",
            )
            return _checked_nonnegative(np.divide(standard_deviation, mean), "regional intensity CV")
    except (FloatingPointError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError(f"regional_intensity_cv has unusable float64 arithmetic: {exc}") from exc
