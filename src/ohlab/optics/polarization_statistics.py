"""Bounded, explicitly probability-weighted optical second moments.

Each row is a coherent Jones sample in the fixed (+x,+y), exp(-i*omega*t)
basis. Rows become an ensemble only under the caller's declared measurement
assumption. This module neither propagates fields nor infers incoherence from
random phases. Coherency/Stokes units are amplitude-unit squared: probability
weights define a mean, not a spatial integral or calibrated power in watts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math

import numpy as np

__all__ = [
    "PolarizationMeasurement",
    "coherency_from_samples",
    "measure_coherency",
    "analyzer_intensity",
]

_EPS = np.finfo(np.float64).eps
_DOMAIN_RELATIVE = 64.0 * _EPS
_PROBABILITY_ATOL = 16.0 * _EPS
_MAX_SAMPLES = 256


def _array(value: object, *, name: str, dtype: np.dtype) -> np.ndarray:
    if type(value) is not np.ndarray or value.dtype != dtype:
        raise TypeError(f"{name}: expected plain native {dtype} ndarray, got {type(value).__name__} with dtype {getattr(value, 'dtype', None)!r}")
    return value


def _angle(value: object) -> float:
    if isinstance(value, (bool, np.bool_, np.timedelta64)) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        raise TypeError(f"axis_angle_rad: expected real scalar radians, got {type(value).__name__}")
    try:
        angle = float(value)
    except (ValueError, OverflowError, TypeError) as exc:
        raise ValueError("axis_angle_rad: expected representable finite binary64 radians") from exc
    if not math.isfinite(angle) or (angle == 0.0 and value != 0):
        raise ValueError(f"axis_angle_rad: expected usable finite binary64 radians, got {angle!r}")
    return angle


def _ratio(numerator: float, denominator: float, name: str) -> float:
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="raise"):
            answer = float(np.float64(numerator) / np.float64(denominator))
    except FloatingPointError as exc:
        raise ValueError(f"{name}: unusable binary64 ratio") from exc
    if not math.isfinite(answer) or (numerator != 0.0 and answer == 0.0):
        raise ValueError(f"{name}: nonzero ratio underflow or nonfinite result")
    return answer


@dataclass(frozen=True, kw_only=True, eq=False)
class PolarizationMeasurement:
    """Owned coherency and derived observables for an explicit second moment.

    Input is a plain native complex128 (2,2) ndarray in amplitude-unit².
    Authoritative ``coherency`` is copied, retained unchanged and read-only.
    Full ``stokes`` uses Jxy=<Ex Ey*> and S3=-2 Im(Jxy), without external
    handedness names. The normalized tuple divides by actual S0; polarized
    direction separately divides by the polarized radius. Exact dark C gives
    None for both and DoP; nonzero unpolarized C gives DoP=0/direction=None.

    A scale-relative 64*eps envelope (no absolute scale floor) checks
    Hermiticity, PSD and DoP. Only eigenvalue diagnostics use the Hermitian
    part of near-Hermitian input; original C, raw eigenvalues and raw DoP
    are never repaired/clamped. Accepted non-Hermiticity, negative eigenvalue
    or DoP>1 sets ``roundoff_limited``. Material defects are ValueError.
    This is arithmetic acceptance, not an experimental uncertainty budget.
    """

    coherency: np.ndarray
    stokes: tuple[float, float, float, float] = field(init=False)
    normalized_stokes: tuple[float, float, float] | None = field(init=False)
    polarized_direction: tuple[float, float, float] | None = field(init=False)
    degree_of_polarization: float | None = field(init=False)
    eigenvalues: tuple[float, float] = field(init=False)
    roundoff_limited: bool = field(init=False)

    def __post_init__(self) -> None:
        original = _array(self.coherency, name="coherency", dtype=np.dtype(np.complex128))
        if original.shape != (2, 2):
            raise ValueError(f"coherency: expected shape (2,2), got {original.shape}")
        if not bool(np.all(np.isfinite(original))):
            raise ValueError("coherency: expected all finite values")
        owned = np.array(original, dtype=np.complex128, copy=True, order="C")
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
                scale = float(np.max(np.abs(owned)))
                tolerance = _DOMAIN_RELATIVE * scale
                defect = float(np.max(np.abs(owned - owned.conj().T)))
                if defect > tolerance:
                    raise ValueError(f"coherency: Hermiticity defect {defect!r} exceeds {tolerance!r}")
                hermitian = owned if defect == 0.0 else 0.5 * owned + 0.5 * owned.conj().T
                eigenvalues = np.linalg.eigvalsh(hermitian)
                if float(eigenvalues[0]) < -tolerance:
                    raise ValueError(f"coherency: minimum eigenvalue {float(eigenvalues[0])!r} below {-tolerance!r}")
                s0 = float(np.real(owned[0, 0] + owned[1, 1]))
                s1 = float(np.real(owned[0, 0] - owned[1, 1]))
                s2 = float(2.0 * owned[0, 1].real)
                s3 = float(-2.0 * owned[0, 1].imag)
        except (FloatingPointError, OverflowError, np.linalg.LinAlgError) as exc:
            raise ValueError("coherency: unusable binary64 domain/observable arithmetic") from exc
        if not all(math.isfinite(v) for v in (scale, s0, s1, s2, s3, *eigenvalues)):
            raise ValueError("coherency: nonfinite derived observables")
        if scale == 0.0:
            normalized = direction = None
            dop = None
        else:
            if s0 <= 0.0:
                raise ValueError(f"coherency: nonzero state requires usable positive S0, got {s0!r}")
            radius = math.hypot(s1, s2, s3)
            dop = _ratio(radius, s0, "degree_of_polarization")
            if dop > 1.0 + _DOMAIN_RELATIVE:
                raise ValueError(f"coherency: DoP {dop!r} exceeds 1+64eps")
            normalized = tuple(_ratio(v, s0, "normalized_stokes") for v in (s1, s2, s3))
            direction = None if radius == 0.0 else tuple(
                _ratio(v, radius, "polarized_direction") for v in (s1, s2, s3)
            )
        owned.setflags(write=False)
        object.__setattr__(self, "coherency", owned)
        object.__setattr__(self, "stokes", (s0, s1, s2, s3))
        object.__setattr__(self, "normalized_stokes", normalized)
        object.__setattr__(self, "polarized_direction", direction)
        object.__setattr__(self, "degree_of_polarization", dop)
        object.__setattr__(self, "eigenvalues", tuple(float(v) for v in eigenvalues))
        object.__setattr__(self, "roundoff_limited", bool(
            defect != 0.0 or eigenvalues[0] < 0.0 or (dop is not None and dop > 1.0)
        ))


def measure_coherency(coherency: np.ndarray) -> PolarizationMeasurement:
    """Snapshot/check a complex128 (2,2) mean coherency, amplitude-unit²."""
    return PolarizationMeasurement(coherency=coherency)


def coherency_from_samples(
    samples: np.ndarray, *, probabilities: np.ndarray,
) -> PolarizationMeasurement:
    """Return sum(p[m] E[m] E[m]†), with no centering or field normalization.

    ``samples`` must be plain native complex128 (M,2), 1<=M<=256; its
    amplitudes have arbitrary declared amplitude units. ``probabilities``
    must be plain native float64 (M,), finite/nonnegative, with sum within
    16*eps absolute of one. Weights are never renormalized. All shape/resource
    checks precede copies or large products. Unusable overall positive energy
    (overflow or underflow to zero) raises rather than changing the samples.
    Individual negligible product tails may underflow. Inputs remain unchanged.
    """
    values = _array(samples, name="samples", dtype=np.dtype(np.complex128))
    weights = _array(probabilities, name="probabilities", dtype=np.dtype(np.float64))
    if values.ndim != 2 or values.shape[1] != 2 or not 1 <= values.shape[0] <= _MAX_SAMPLES:
        raise ValueError(f"samples: expected shape (M,2) with 1<=M<=256, got {values.shape}")
    if weights.shape != (values.shape[0],):
        raise ValueError(f"probabilities: expected shape {(values.shape[0],)}, got {weights.shape}")
    if not bool(np.all(np.isfinite(values))) or not bool(np.all(np.isfinite(weights))):
        raise ValueError("samples/probabilities: expected all finite values")
    if bool(np.any(weights < 0.0)):
        raise ValueError("probabilities: expected nonnegative weights")
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            probability_sum = float(np.sum(weights, dtype=np.float64))
            if abs(probability_sum - 1.0) > _PROBABILITY_ATOL:
                raise ValueError(f"probabilities: sum {probability_sum!r} differs from1 by more than16eps")
            x, y = values[:, 0], values[:, 1]
            xy = np.sum(weights * x * np.conj(y), dtype=np.complex128)
            # Diagonal absolute squares are real by definition. Computing them
            # directly avoids a spurious imaginary cancellation residual.
            xx = np.sum(weights * (x.real * x.real + x.imag * x.imag), dtype=np.float64)
            yy = np.sum(weights * (y.real * y.real + y.imag * y.imag), dtype=np.float64)
            matrix = np.array([[xx, xy], [np.conj(xy), yy]], dtype=np.complex128)
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError("coherency_from_samples: overflow/invalid second-moment arithmetic") from exc
    if not bool(np.any(matrix != 0.0)) and bool(np.any((weights > 0.0)[:, None] & (values != 0.0))):
        raise ValueError("coherency_from_samples: positive sampled energy underflowed to zero")
    return measure_coherency(matrix)


def analyzer_intensity(
    measurement: PolarizationMeasurement, *, axis_angle_rad: float,
) -> float:
    """Return a† C a for a=(cosθ,sinθ), amplitude-unit², θ in radians.

    Validate the actual stored matrix again because ndarray write flags are
    reversible. No polarizer-loss normalization is applied. A negative value
    within the declared scale-relative PSD envelope is retained as roundoff;
    material negative intensity is rejected. Positive extinction tails remain.
    """
    if type(measurement) is not PolarizationMeasurement:
        raise TypeError(f"measurement: expected PolarizationMeasurement, got {type(measurement).__name__}")
    theta = _angle(axis_angle_rad)
    checked = measure_coherency(measurement.coherency)
    c, s = math.cos(theta), math.sin(theta)
    matrix = checked.coherency
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            value = float(c * c * matrix[0, 0].real + s * s * matrix[1, 1].real + 2.0 * c * s * matrix[0, 1].real)
            tolerance = _DOMAIN_RELATIVE * float(np.max(np.abs(matrix)))
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError("analyzer_intensity: unusable arithmetic") from exc
    if not math.isfinite(value) or value < -tolerance:
        raise ValueError(f"analyzer_intensity: nonphysical intensity {value!r}, tolerance {tolerance!r}")
    return value
