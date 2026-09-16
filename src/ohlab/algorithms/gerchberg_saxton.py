"""Single-plane phase-only synthesis on the complete periodic ASM grid.

This is Gerchberg--Saxton alternating amplitude projection with the project's
existing angular-spectrum propagation, equivalent to ``pad_factor=1``. There
is no padding, crop, phase quantization, input scaling or file I/O. Every mesh
sample must be non-evanescent: then the inverse and adjoint of propagation by
``z`` both equal propagation by ``-z``. This is a discrete periodic model,
not a validation of an arbitrary isolated finite-aperture optical system.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from numpy.typing import NDArray

from ..field import ComplexField
from ..grid import SamplingGrid
from ..propagation import angular_spectrum_transfer_function
from ..validation import (
    require_all_finite,
    require_finite_float,
    require_ndim,
    require_positive_finite_float,
    require_shape,
)

__all__ = ["GerchbergSaxtonResult", "gerchberg_saxton"]


def _require_nonnegative_integer(value: int, name: str) -> int:
    """Accept integer counts/seeds, excluding booleans and implicit conversion."""
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(
            f"{name} must be a non-negative integer, got {value!r} "
            f"(type {type(value).__name__})"
        )
    result = int(value)
    if result < 0:
        raise ValueError(f"{name} must be non-negative, got {result}")
    return result


def _copy_real_map(
    array: NDArray[np.float64], *, grid: SamplingGrid, name: str,
    nonnegative: bool,
) -> NDArray[np.float64]:
    """Validate a plain native-float64 map and take an owned C-order copy."""
    if type(array) is not np.ndarray:
        raise TypeError(
            f"{name} must be a plain numpy.ndarray, got {type(array).__name__}"
        )
    if array.dtype != np.dtype(np.float64) or not array.dtype.isnative:
        raise TypeError(
            f"{name} must have native float64 dtype, got {array.dtype!r}"
        )
    require_ndim(array, 2, name)
    require_shape(array, grid.shape, name)
    require_all_finite(array, name)
    if nonnegative and bool(np.any(array < 0.0)):
        first = tuple(int(index) for index in np.argwhere(array < 0.0)[0])
        raise ValueError(
            f"{name} must be nonnegative, got {array[first]!r} at index {first}"
        )
    return np.array(array, dtype=np.float64, order="C", copy=True)


def _energy_and_power(
    amplitude: NDArray[np.float64], pixel_area: float, name: str,
) -> tuple[float, float]:
    """Return positive representable sum(A**2) and power in a.u. * m^2."""
    try:
        with np.errstate(over="raise", under="raise", invalid="raise", divide="raise"):
            energy = float(np.sum(amplitude**2, dtype=np.float64))
            power = float(np.float64(energy) * pixel_area)
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError(
            f"{name} energy/power arithmetic is not representable in float64; "
            "no rescaling is performed"
        ) from exc
    if not math.isfinite(energy) or energy <= 0.0:
        raise ValueError(
            f"{name} must have positive finite representable energy "
            f"sum(amplitude**2), got {energy!r}; zero targets/sources are unsupported"
        )
    if not math.isfinite(power) or power <= 0.0:
        raise ValueError(
            f"{name} must have positive finite representable power, got {power!r} "
            f"from energy {energy!r} and pixel_area {pixel_area!r} m^2"
        )
    return energy, power


def _phase_with_zero_tie(data: NDArray[np.complex128]) -> NDArray[np.float64]:
    """Fresh phase in radians, (-pi, pi], with phase zero at exact complex zero."""
    phase = np.angle(data)
    phase[phase == -math.pi] = math.pi
    phase[data == 0j] = 0.0
    return phase


def _project_amplitude(
    data: NDArray[np.complex128], amplitude: NDArray[np.float64],
) -> NDArray[np.complex128]:
    """Replace amplitude, using the local deterministic tie at exact zeros."""
    projected = amplitude * np.exp(1j * _phase_with_zero_tie(data))
    require_all_finite(projected, "amplitude-projected field")
    return projected


def _apply_transfer(
    data: NDArray[np.complex128], transfer: NDArray[np.complex128], *, identity: bool,
) -> NDArray[np.complex128]:
    """Apply the existing full-grid FFT expression, or exact identity at z=0."""
    if identity:
        return data
    propagated = np.fft.ifft2(np.fft.fft2(data) * transfer)
    require_all_finite(propagated, "propagated field")
    return propagated


def _amplitude_residual(
    reconstruction: NDArray[np.complex128], target_amplitude: NDArray[np.float64],
    target_energy: float,
) -> float:
    """Unscaled full-grid squared amplitude error divided by target energy."""
    difference = np.abs(reconstruction) - target_amplitude
    residual = float(np.sum(difference**2, dtype=np.float64) / target_energy)
    if not math.isfinite(residual) or residual < 0.0:
        raise ValueError(f"amplitude residual must be finite and nonnegative, got {residual!r}")
    return residual


def _prepare_transfers(
    grid: SamplingGrid, wavelength_m: float, distance_m: float,
) -> tuple[NDArray[np.complex128], NDArray[np.complex128]]:
    """Validate the no-evanescence domain, then call the public H twice."""
    fx, fy = grid.freq_meshgrid(order="fft")
    require_all_finite(fx, "grid fx frequencies")
    require_all_finite(fy, "grid fy frequencies")
    cutoff_squared = (1.0 / wavelength_m) ** 2
    if not math.isfinite(cutoff_squared) or cutoff_squared <= 0.0:
        raise ValueError(
            f"wavelength_m={wavelength_m!r} gives an unrepresentable squared "
            "propagating-frequency cutoff"
        )
    evanescent = fx**2 + fy**2 > cutoff_squared
    count = int(np.count_nonzero(evanescent))
    if count:
        raise ValueError(
            f"the GS operating grid contains {count} of {evanescent.size} "
            f"evanescent samples at wavelength_m={wavelength_m!r}; the full-grid "
            "lossless model requires none, even at zero distance or zero iterations"
        )
    # At a rounded grazing cutoff, the sum predicate can pass while the public
    # H's sequential subtraction yields a negative radicand. That arithmetic
    # would produce attenuation/growth rather than a lossless GS operator.
    # Check the domain only: kz and both transfer functions remain public H's.
    radicand = cutoff_squared - fx**2 - fy**2
    negative_count = int(np.count_nonzero(radicand < 0.0))
    if negative_count:
        raise ValueError(
            "floating-point cutoff geometry cannot represent the lossless "
            f"GS domain: {negative_count} of {radicand.size} public transfer "
            f"radicands are negative (minimum {float(np.min(radicand))!r}); "
            "this is unsupported even at zero distance or zero iterations"
        )
    # Do not retain domain-check meshes while the public implementation builds H.
    del fx, fy, evanescent, radicand
    forward = angular_spectrum_transfer_function(
        grid, wavelength_m=wavelength_m, distance_m=distance_m
    )
    backward = angular_spectrum_transfer_function(
        grid, wavelength_m=wavelength_m, distance_m=-distance_m
    )
    require_all_finite(forward, "forward transfer function")
    require_all_finite(backward, "backward transfer function")
    return forward, backward


@dataclass(frozen=True, kw_only=True, eq=False)
class GerchbergSaxtonResult:
    """Last GS source, its actual reconstruction, and raw residual history.

    ``source_field`` and ``reconstruction`` are immutable ComplexFields on the
    same grid and wavelength. History is an owned, read-only native float64
    array: entry k describes the actual forward propagation of source iterate
    k, before target replacement. Its length is iterations + 1. This residual
    is dimensionless squared amplitude error, not intensity MSE, efficiency,
    a percentage of pixels or a convergence claim. Equality is object identity.
    """

    source_field: ComplexField
    reconstruction: ComplexField
    residual_history: NDArray[np.float64]

    def __post_init__(self) -> None:
        """Validate result structure and own the immutable history storage."""
        for name in ("source_field", "reconstruction"):
            if not isinstance(getattr(self, name), ComplexField):
                raise TypeError(f"{name} must be a ComplexField")
        if self.source_field.grid != self.reconstruction.grid:
            raise ValueError("source_field and reconstruction must use the same grid")
        if self.source_field.wavelength_m != self.reconstruction.wavelength_m:
            raise ValueError("source_field and reconstruction must use the same wavelength_m")
        history = self.residual_history
        if type(history) is not np.ndarray:
            raise TypeError("residual_history must be a plain numpy.ndarray")
        if history.dtype != np.dtype(np.float64) or not history.dtype.isnative:
            raise TypeError("residual_history must have native float64 dtype")
        require_ndim(history, 1, "residual_history")
        if history.size == 0:
            raise ValueError("residual_history must include the initial residual")
        require_all_finite(history, "residual_history")
        if bool(np.any(history < 0.0)):
            raise ValueError("residual_history must contain nonnegative values")
        owned = np.array(history, dtype=np.float64, order="C", copy=True)
        owned.flags.writeable = False
        object.__setattr__(self, "residual_history", owned)

    @property
    def phase(self) -> NDArray[np.float64]:
        """Fresh writable float64 source phase in radians, zero on zero support."""
        return _phase_with_zero_tie(self.source_field.data)

    @property
    def iterations(self) -> int:
        """Number of complete projection cycles represented by the history."""
        return int(self.residual_history.size - 1)


def gerchberg_saxton(
    *,
    target_amplitude: NDArray[np.float64],
    source_amplitude: NDArray[np.float64],
    grid: SamplingGrid,
    wavelength_m: float,
    distance_m: float,
    iterations: int,
    seed: int | None = None,
    initial_phase: NDArray[np.float64] | None = None,
) -> GerchbergSaxtonResult:
    """Synthesize an ideal phase-only source on one complete periodic grid.

    Both amplitudes must be plain native float64 arrays of shape ``grid.shape``,
    finite and nonnegative, with no upper bound of one. They specify amplitude
    in a.u., not intensity. Read-only and noncontiguous inputs are accepted by
    defensive copying. No input is modified, normalized or rescaled.

    Wavelength and signed distance are in metres; wavelength must be positive
    and both must be finite. Grid pitches are in metres. The model is existing
    ASM with pad_factor=1, without cropping; every discrete frequency must be
    non-evanescent, even for zero distance or zero iterations. On this domain
    negative-distance propagation is both inverse and adjoint. Cropped/padded
    propagation is not an inverse and is not used here. A rounded grazing
    cutoff whose public transfer radicand becomes negative is also rejected:
    its floating-point geometry cannot represent this lossless domain.

    Let Ss=sum(source_amplitude**2), St=sum(target_amplitude**2). Both energies
    and their powers S*dx*dy must be positive, finite and representable. Require
    abs(Ss-St) <= 1e-12*max(Ss,St), with absolute tolerance zero. Compatibility
    is necessary, not sufficient for an exactly achievable target. Blank images
    remain valid M2 inputs but are unsupported synthesis requests here.

    Exactly one initialization is required: a nonnegative integer ``seed``
    draws source-plane phase uniformly from [-pi, pi) using default_rng, or a
    plain native float64 ``initial_phase`` array supplies finite radians on any
    branch. ``iterations`` is a nonnegative integer, excluding bool.

    Starting from U0=source_amplitude*exp(i*phase), each cycle computes the
    actual reconstruction V=Pz(U), replaces its amplitude by target_amplitude,
    propagates by -z, then restores source_amplitude. Exact complex zero has
    phase zero for these projections. No near-zero threshold is applied.
    At distance zero propagation is exact identity; the requested projections
    still run and may reset phase where a zero target meets nonzero source.

    History[k] = sum((abs(Pz(Uk))-target_amplitude)**2)/St, over the full grid,
    before target replacement. Return the last source UN and its unmodified
    actual forward reconstruction, never the target-projected field. History
    includes entries 0 through N; N=0 returns initialization and its actual
    reconstruction. Fixed cycle count only: no early stopping or best-iterate
    selection, and no guarantee of zero residual for arbitrary targets.

    Type/dtype errors raise TypeError. Invalid values, incompatible powers,
    evanescent meshes or unusable derived arithmetic raise informative
    ValueError; no clipping or numerical rescaling repairs such requests.
    NumPy overflow, invalid operations, division by zero and underflow are
    treated as errors throughout the solve. This includes tiny/subnormal
    intermediates that signal loss of precision, even when another sample
    keeps the total energy positive; not every positive float64 scale is
    supported. Geometry and scalar-conversion overflows are also rejected.
    Transfer functions at +z and -z are built once per solve through the
    existing public function. There is no global cache or alternate physics.
    """
    stage = "parameter validation"
    try:
        with np.errstate(over="raise", under="raise", invalid="raise", divide="raise"):
            if not isinstance(grid, SamplingGrid):
                raise TypeError(f"grid must be a SamplingGrid, got {type(grid).__name__}")
            wavelength = require_positive_finite_float(wavelength_m, "wavelength_m")
            distance = require_finite_float(distance_m, "distance_m")
            count = _require_nonnegative_integer(iterations, "iterations")
            if count >= np.iinfo(np.intp).max:
                raise ValueError(f"iterations={count} gives an unrepresentable history length")
            if (seed is None) == (initial_phase is None):
                raise ValueError("supply exactly one of seed or initial_phase")
            seed_value = None if seed is None else _require_nonnegative_integer(seed, "seed")
            source = _copy_real_map(
                source_amplitude, grid=grid, name="source_amplitude", nonnegative=True
            )
            target = _copy_real_map(
                target_amplitude, grid=grid, name="target_amplitude", nonnegative=True
            )
            phase = None if initial_phase is None else _copy_real_map(
                initial_phase, grid=grid, name="initial_phase", nonnegative=False
            )

            stage = "grid geometry and amplitude energy/power"
            area = grid.pixel_area
            for name, value in (
                ("pixel_area", area), ("extent_x", grid.extent_x), ("extent_y", grid.extent_y)
            ):
                if not math.isfinite(value) or value <= 0.0:
                    raise ValueError(f"grid {name} must be positive finite and representable, got {value!r}")
            source_energy, source_power = _energy_and_power(source, area, "source_amplitude")
            target_energy, target_power = _energy_and_power(target, area, "target_amplitude")
            if abs(source_energy - target_energy) > 1e-12 * max(source_energy, target_energy):
                raise ValueError(
                    "source and target powers are incompatible: "
                    f"S_source={source_energy!r}, S_target={target_energy!r}, "
                    f"P_source={source_power!r}, P_target={target_power!r} a.u. * m^2; "
                    "require abs(S_source-S_target) <= 1e-12*max(S_source,S_target) "
                    "with absolute tolerance zero; no normalization is performed"
                )

            stage = "frequency-grid validation and transfer-function construction"
            forward, backward = _prepare_transfers(grid, wavelength, distance)
            identity = distance == 0.0
            stage = "source initialization"
            if phase is None:
                phase = np.random.default_rng(seed_value).uniform(-math.pi, math.pi, grid.shape)
            current = source * np.exp(1j * phase)
            require_all_finite(current, "initialized source field")
            history = np.empty(count + 1, dtype=np.float64)
            stage = "initial forward reconstruction and residual"
            reconstruction = _apply_transfer(current, forward, identity=identity)
            history[0] = _amplitude_residual(reconstruction, target, target_energy)
            for step in range(1, count + 1):
                stage = f"projection cycle {step}"
                constrained = _project_amplitude(reconstruction, target)
                returned = _apply_transfer(constrained, backward, identity=identity)
                current = _project_amplitude(returned, source)
                reconstruction = _apply_transfer(current, forward, identity=identity)
                history[step] = _amplitude_residual(reconstruction, target, target_energy)

            stage = "result construction"
            return GerchbergSaxtonResult(
                source_field=ComplexField(data=current, grid=grid, wavelength_m=wavelength),
                reconstruction=ComplexField(data=reconstruction, grid=grid, wavelength_m=wavelength),
                residual_history=history,
            )
    except (FloatingPointError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError(
            f"GS {stage} produced unusable float64/complex128 arithmetic: {exc}; "
            "no clipping or rescaling is performed"
        ) from exc
