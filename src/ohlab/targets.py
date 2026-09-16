"""Strict, array-only preparation of design target intensity and amplitude.

An 8-bit grayscale code specifies intensity ``I = g / 255``, not amplitude.
The amplitude constraint is ``A = sqrt(I)``. These normalized design values
are not calibrated irradiance, a complex field, or an SLM phase pattern.
No phase is assigned. Pixel positions and the caller's physical grid are
preserved; this module performs no spatial resampling or per-target normalization.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from .grid import SamplingGrid
from .validation import require_all_finite, require_ndim, require_shape

__all__ = ["grayscale8_to_intensity", "intensity_to_amplitude"]


def _require_target_array(
    array: np.ndarray, *, name: str, dtype: np.dtype, grid: SamplingGrid
) -> None:
    """Validate a plain array on the caller's unchanged sampling grid."""
    if not isinstance(grid, SamplingGrid):
        raise TypeError(
            f"grid must be a SamplingGrid, got {grid!r} "
            f"(type {type(grid).__name__})"
        )
    if type(array) is not np.ndarray:
        raise TypeError(
            f"{name} must be a plain numpy.ndarray, got "
            f"type {type(array).__name__}; array subclasses and array-like "
            f"objects are not accepted"
        )
    if array.dtype != dtype or not array.dtype.isnative:
        raise TypeError(
            f"{name} must have native {dtype.name} dtype, got "
            f"{array.dtype!r}; implicit dtype or bit-depth conversion is not allowed"
        )
    require_ndim(array, 2, name)
    require_shape(array, grid.shape, name)


def grayscale8_to_intensity(
    grayscale: NDArray[np.uint8], *, grid: SamplingGrid
) -> NDArray[np.float64]:
    """Convert 8-bit grayscale codes to normalized target intensity.

    Parameters
    ----------
    grayscale:
        A plain two-dimensional ``uint8`` NumPy array with shape ``(ny, nx)``
        exactly equal to ``grid.shape``. Codes are design intensity values:
        the fixed mapping is ``I_target = grayscale / 255``. Other dtypes
        and array subclasses are rejected, not converted or interpreted.
    grid:
        The caller's sampling grid. Its pitches and coordinates are in metres;
        no grid parameter or pixel position is changed.

    Returns
    -------
    ndarray
        A fresh, writable, C-contiguous native ``float64`` array with the
        same shape, in ``[0, 1]``. Values are dimensionless design intensity,
        not calibrated W/m^2. The result shares no storage with the input.
        All-zero input remains zero. There is no peak/power normalization,
        gamma correction, threshold, clipping, or spatial transformation.

    Raises
    ------
    TypeError
        The input is not a plain ``uint8`` ndarray, or grid has the wrong type.
    ValueError
        The input is not two-dimensional or its shape differs from the grid.
    """
    _require_target_array(
        grayscale, name="grayscale", dtype=np.dtype(np.uint8), grid=grid
    )
    intensity = np.array(grayscale, dtype=np.float64, order="C", copy=True)
    intensity /= 255.0
    return intensity


def intensity_to_amplitude(
    intensity: NDArray[np.float64], *, grid: SamplingGrid
) -> NDArray[np.float64]:
    """Return the target amplitude constraint ``sqrt(intensity)``.

    Parameters
    ----------
    intensity:
        A plain two-dimensional native ``float64`` NumPy array of finite
        dimensionless design intensities in ``[0, 1]``. Its shape ``(ny, nx)``
        must equal ``grid.shape``. Integer codes, lower-precision floats,
        non-native byte order, and array subclasses are rejected explicitly.
    grid:
        The caller's sampling grid, with physical pitches in metres. It is
        neither rescaled nor otherwise modified.

    Returns
    -------
    ndarray
        A fresh, writable, C-contiguous native ``float64`` array with the
        same shape, containing dimensionless normalized amplitude in
        ``[0, 1]``. No storage is shared with the input and no phase is
        assigned. All-zero input remains zero; no nonzero-power requirement
        or additional normalization is imposed.

    Raises
    ------
    TypeError
        The input is not a plain native ``float64`` ndarray, or grid has the
        wrong type.
    ValueError
        The dimensions/shape do not match, or an intensity is non-finite or
        outside ``[0, 1]``. Values are rejected, never clipped or normalized.
    """
    _require_target_array(
        intensity, name="intensity", dtype=np.dtype(np.float64), grid=grid
    )
    require_all_finite(intensity, "intensity")
    invalid = (intensity < 0.0) | (intensity > 1.0)
    if bool(np.any(invalid)):
        first = tuple(int(index) for index in np.argwhere(invalid)[0])
        raise ValueError(
            f"intensity must contain values in [0, 1], got "
            f"{intensity[first]!r} at index {first}; "
            f"clipping and normalization are not performed"
        )
    amplitude = np.array(intensity, dtype=np.float64, order="C", copy=True)
    np.sqrt(amplitude, out=amplitude)
    return amplitude
