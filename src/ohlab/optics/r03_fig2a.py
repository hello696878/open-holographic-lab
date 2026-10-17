"""One ideal statistical-polarization ensemble, independent of paper data.

The historical filename is an engineering namespace. Public model identity is
``r03_ideal_statistical_polarization_v1``; no PAX, measured reference, physical
propagation or Figure 2a agreement is implemented. Samples have no SI pitch or
wavelength; the small uniform Jones action is algebraic, without fake grids.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .polarization_statistics import PolarizationMeasurement, coherency_from_samples

__all__ = ["IdealPolarizationSpec", "IdealPolarizationResult", "run_ideal_polarization"]

MODEL_CONTRACT = "r03_ideal_statistical_polarization_v1"
SAMPLE_SHAPE = (16, 16)
SAMPLE_COUNT = 256
SAMPLE_ORDER = "C"
RNG_ALGORITHM = "PCG64"


def _real(value: object, name: str, minimum: float, maximum: float) -> float:
    if isinstance(value, (bool, np.bool_, np.timedelta64)) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        raise TypeError(f"{name}: expected real scalar, got {type(value).__name__}")
    try:
        result = float(value)
    except (ValueError, OverflowError, TypeError) as exc:
        raise ValueError(f"{name}: expected representable finite binary64 value") from exc
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(f"{name}: expected [{minimum!r},{maximum!r}], got {result!r}")
    if result == 0.0 and value != 0:
        raise ValueError(f"{name}: nonzero value underflowed to zero during conversion")
    return result


@dataclass(frozen=True, kw_only=True)
class IdealPolarizationSpec:
    """Complete single-ensemble settings, angles/std in radians.

    ``amplitude`` is real D-source amplitude in [0,1e6], not watts. Mean and
    waveplate axes are in [-2π,2π], Gaussian std in [0,π]. Seed must be a plain
    Python int in [0,2**32-1]. All ranges are software bounds, not recovered
    experimental settings. Extremely weak nonzero amplitudes may be rejected
    when their second moment is unusable rather than silently made dark.
    """

    amplitude: float
    mean_phase_rad: float
    phase_std_rad: float
    qwp_angle_rad: float
    hwp_angle_rad: float
    seed: int

    def __post_init__(self) -> None:
        for name, minimum, maximum in (
            ("amplitude", 0.0, 1e6),
            ("mean_phase_rad", -2.0 * math.pi, 2.0 * math.pi),
            ("phase_std_rad", 0.0, math.pi),
            ("qwp_angle_rad", -2.0 * math.pi, 2.0 * math.pi),
            ("hwp_angle_rad", -2.0 * math.pi, 2.0 * math.pi),
        ):
            object.__setattr__(self, name, _real(getattr(self, name), name, minimum, maximum))
        if type(self.seed) is not int:
            raise TypeError(f"seed: expected plain Python int excluding bool, got {type(self.seed).__name__}")
        if not 0 <= self.seed <= 2**32 - 1:
            raise ValueError(f"seed: expected [0,2**32-1], got {self.seed!r}")


@dataclass(frozen=True, kw_only=True, eq=False)
class IdealPolarizationResult:
    """One identity-bound finite result; owned phase arrays are float64(16,16).

    Four algebraic planes use the exact same realization. The independent
    infinite-Gaussian population DoP is labelled separately and never replaces
    the finite measurement. Phase is rad; C/Stokes are mean amplitude-unit².
    """

    spec: IdealPolarizationSpec
    phase_unwrapped_rad: np.ndarray
    phase_wrapped_rad: np.ndarray
    source: PolarizationMeasurement
    after_slm: PolarizationMeasurement
    after_qwp: PolarizationMeasurement
    output: PolarizationMeasurement
    population_dop: float | None
    model_contract: str = MODEL_CONTRACT
    rng_algorithm: str = RNG_ALGORITHM
    sample_order: str = SAMPLE_ORDER
    sample_shape: tuple[int, int] = SAMPLE_SHAPE
    sample_count: int = SAMPLE_COUNT

    def __post_init__(self) -> None:
        if type(self.spec) is not IdealPolarizationSpec:
            raise TypeError("spec: expected IdealPolarizationSpec")
        snapshot = IdealPolarizationSpec(**{
            name: getattr(self.spec, name) for name in (
                "amplitude", "mean_phase_rad", "phase_std_rad", "qwp_angle_rad", "hwp_angle_rad", "seed"
            )
        })
        object.__setattr__(self, "spec", snapshot)
        for name in ("phase_unwrapped_rad", "phase_wrapped_rad"):
            value = getattr(self, name)
            if type(value) is not np.ndarray or value.dtype != np.dtype(np.float64):
                raise TypeError(f"{name}: expected plain native float64 ndarray")
            if value.shape != SAMPLE_SHAPE or not bool(np.all(np.isfinite(value))):
                raise ValueError(f"{name}: expected finite shape{SAMPLE_SHAPE}, got {value.shape}")
            owned = np.array(value, dtype=np.float64, copy=True, order="C")
            owned.setflags(write=False)
            object.__setattr__(self, name, owned)
        if not bool(np.array_equal(np.mod(self.phase_unwrapped_rad, 2.0 * math.pi), self.phase_wrapped_rad)):
            raise ValueError("phase_wrapped_rad: must be exact np.mod of the submitted unwrapped realization")
        for name in ("source", "after_slm", "after_qwp", "output"):
            value = getattr(self, name)
            if type(value) is not PolarizationMeasurement:
                raise TypeError(f"{name}: expected PolarizationMeasurement")
            object.__setattr__(self, name, PolarizationMeasurement(coherency=value.coherency))
        expected_population = None if snapshot.amplitude == 0.0 else math.exp(-0.5 * snapshot.phase_std_rad**2)
        if self.population_dop is not None and type(self.population_dop) is not float:
            raise TypeError("population_dop: expected plain float or None")
        if self.population_dop != expected_population:
            raise ValueError("population_dop: must match the declared infinite Gaussian ensemble, None for dark")
        for name in ("model_contract", "rng_algorithm", "sample_order"):
            if type(getattr(self, name)) is not str:
                raise TypeError(f"{name}: expected plain str")
        if type(self.sample_count) is not int:
            raise TypeError("sample_count: expected plain int")
        if type(self.sample_shape) is not tuple or len(self.sample_shape) != 2 or any(type(n) is not int for n in self.sample_shape):
            raise TypeError("sample_shape: expected tuple of two plain ints")
        for name, expected in (
            ("model_contract", MODEL_CONTRACT), ("rng_algorithm", RNG_ALGORITHM),
            ("sample_order", SAMPLE_ORDER), ("sample_shape", SAMPLE_SHAPE), ("sample_count", SAMPLE_COUNT),
        ):
            if getattr(self, name) != expected:
                raise ValueError(f"{name}: expected fixed model value {expected!r}")


def _retarder(samples: np.ndarray, theta: float, delta: float) -> np.ndarray:
    """Grid-free R diag(1,exp(iδ)) R.T, preserving the selected common phase."""
    c, s = math.cos(theta), math.sin(theta)
    phase = complex(math.cos(delta), math.sin(delta))
    matrix = np.array(
        [[c*c + phase*s*s, (1.0-phase)*c*s],
         [(1.0-phase)*c*s, s*s + phase*c*c]], dtype=np.complex128,
    )
    return samples @ matrix.T


def run_ideal_polarization(spec: IdealPolarizationSpec) -> IdealPolarizationResult:
    """Generate exactly one 256-sample ideal Gaussian ensemble and measure it.

    Local default_rng(seed), checked to use PCG64, makes one standard_normal((16,16)) call,
    including sigma=0 and a dark source. No sample is centered, variance
    corrected, sorted, rejected or regenerated. Unwrapped φ=μ+σz and its
    separately retained modulo2π action/display phase bind to this result.
    Source D=(A,A)/sqrt2; SLM acts on x, then QWP then HWP. Equal probabilities
    define a mean second moment, without spatial propagation or area factors.
    """
    if type(spec) is not IdealPolarizationSpec:
        raise TypeError(f"spec: expected IdealPolarizationSpec, got {type(spec).__name__}")
    checked = IdealPolarizationSpec(**{
        name: getattr(spec, name) for name in (
            "amplitude", "mean_phase_rad", "phase_std_rad", "qwp_angle_rad", "hwp_angle_rad", "seed"
        )
    })
    # The unchanged repository RNG guard permits only the public default_rng
    # constructor in src/. Check its actual algorithm before drawing, rather
    # than relying silently on a future NumPy default or hiding another import.
    # Independent validation compares the full realization with explicit PCG64.
    rng = np.random.default_rng(checked.seed)
    if type(rng.bit_generator).__name__ != RNG_ALGORITHM:
        raise ValueError(f"run_ideal_polarization: expected PCG64, got {type(rng.bit_generator).__name__}")
    normal = rng.standard_normal(SAMPLE_SHAPE)
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            unwrapped = checked.mean_phase_rad + checked.phase_std_rad * normal
            wrapped = np.mod(unwrapped, 2.0 * math.pi)
            samples = np.full((SAMPLE_COUNT, 2), checked.amplitude / math.sqrt(2.0), dtype=np.complex128)
            probabilities = np.full(SAMPLE_COUNT, 1.0 / SAMPLE_COUNT, dtype=np.float64)
            source = coherency_from_samples(samples, probabilities=probabilities)
            samples[:, 0] *= np.exp(1j * wrapped.reshape(SAMPLE_COUNT, order=SAMPLE_ORDER))
            after_slm = coherency_from_samples(samples, probabilities=probabilities)
            samples = _retarder(samples, checked.qwp_angle_rad, math.pi / 2.0)
            after_qwp = coherency_from_samples(samples, probabilities=probabilities)
            samples = _retarder(samples, checked.hwp_angle_rad, math.pi)
            output = coherency_from_samples(samples, probabilities=probabilities)
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError("run_ideal_polarization: unusable finite-ensemble arithmetic") from exc
    return IdealPolarizationResult(
        spec=checked, phase_unwrapped_rad=unwrapped, phase_wrapped_rad=wrapped,
        source=source, after_slm=after_slm, after_qwp=after_qwp, output=output,
        population_dop=None if checked.amplitude == 0.0 else math.exp(-0.5 * checked.phase_std_rad**2),
    )
