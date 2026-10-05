"""Classical scalar coherent two-path interference on one unfolded grid.

Ports and arms are ordered (0, 1). The first ideal balanced mixer is
``B = [[1, i], [i, 1]] / sqrt(2)``; the recombiner is its adjoint.
This inverse-mixing choice describes reference planes, not a physical coating
or a rotated cube. Both arms stipulate identical transverse coordinates.
Normative reference: ``docs/math_conventions.md`` section 3.18.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

import numpy as np

from ..field import ComplexField
from ..grid import SamplingGrid
from ..propagation import propagate_angular_spectrum

__all__ = ["mix_balanced", "apply_uniform_phase", "TwoArmSpec", "TwoArmNorms",
           "TwoArmResult", "run_two_arm"]


def _real(value: object, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
            value, (int, float, np.integer, np.floating)):
        raise TypeError(f"{name}: expected real scalar excluding bool, got {type(value).__name__}")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name}: expected representable finite binary64") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name}: expected finite binary64, got {result!r}")
    return result


def _nonnegative(value: object, name: str) -> float:
    result = _real(value, name)
    if result < 0:
        raise ValueError(f"{name}: expected nonnegative value, got {result!r}")
    return result


def _usable(value: float, name: str, *, positive: bool = False) -> float:
    if not math.isfinite(value) or (positive and value <= 0):
        raise ValueError(f"{name}: unusable derived binary64 value {value!r}")
    return value


def _geometry(grid: SamplingGrid, wavelength_m: float, *, cap: int | None = None) -> float:
    """Validate scalar bounds; do not implement a propagation kernel/mesh."""
    # The unfolded model fixes the public base grid's centered coordinates.
    # A subclass may override those coordinates despite equal scalar metadata.
    if type(grid) is not SamplingGrid:
        raise TypeError(f"grid: expected canonical SamplingGrid coordinate convention, got {type(grid).__name__}")
    for name in ("ny", "nx"):
        count = getattr(grid, name)
        if isinstance(count, (bool, np.bool_)) or not isinstance(count, (int, np.integer)):
            raise TypeError(f"grid.{name}: expected integer excluding bool, got {type(count).__name__}")
        if count < 1 or (cap is not None and count > cap):
            expected = f"1..{cap}" if cap is not None else ">= 1"
            raise ValueError(f"grid.{name}: expected {expected}, got {count}")
    for name in ("dy", "dx"):
        pitch = _real(getattr(grid, name), f"grid.{name}")
        if pitch <= 0:
            raise ValueError(f"grid.{name}: expected positive metres, got {pitch!r}")
    lam = _real(wavelength_m, "wavelength_m")
    if lam <= 0:
        raise ValueError(f"wavelength_m: expected positive metres, got {lam!r}")
    _usable(grid.dx * grid.dy, "grid pixel area", positive=True)
    inverse_wavelength = _usable(1.0 / lam, "inverse wavelength", positive=True)
    cutoff_squared = _usable(inverse_wavelength * inverse_wavelength,
                             "frequency cutoff squared", positive=True)
    k = _usable(2 * math.pi * inverse_wavelength, "wavenumber", positive=True)
    _usable(k * k, "wavenumber squared", positive=True)
    frequency_squared = []
    coordinate_squared = []
    for count, pitch, axis in ((grid.nx, grid.dx, "x"), (grid.ny, grid.dy, "y")):
        extent = _usable(count * pitch, f"grid {axis} extent", positive=True)
        inverse_extent = _usable(1.0 / extent, f"grid {axis} reciprocal extent", positive=True)
        coordinate = _usable((count // 2) * pitch, f"grid {axis} coordinate")
        coordinate_squared.append(_usable(coordinate * coordinate, f"grid {axis} coordinate squared"))
        frequency = _usable((count // 2) * inverse_extent, f"grid {axis} frequency bound")
        frequency_squared.append(_usable(frequency * frequency, f"grid {axis} frequency bound squared"))
    _usable(sum(coordinate_squared), "grid radial coordinate squared")
    # An upper bound for either real or imaginary longitudinal phase. Its use
    # is strictly arithmetic validation; public M1 computes all actual kz.
    radial_bound = _usable(cutoff_squared + sum(frequency_squared), "propagation frequency bound squared")
    return _usable(2 * math.pi * math.sqrt(radial_bound), "propagation phase coefficient", positive=True)


def _field(field: ComplexField, name: str, *, cap: int | None = None) -> None:
    if not isinstance(field, ComplexField):
        raise TypeError(f"{name}: expected ComplexField, got {type(field).__name__}")
    _geometry(field.grid, field.wavelength_m, cap=cap)
    if type(field.data) is not np.ndarray or field.data.dtype != np.dtype(np.complex128):
        raise TypeError(f"{name}.data: expected plain native complex128 ndarray, got {type(field.data).__name__} with dtype {getattr(field.data, 'dtype', None)!r}")
    if field.data.shape != (field.grid.ny, field.grid.nx):
        raise ValueError(f"{name}.data: expected shape {(field.grid.ny, field.grid.nx)}, got {field.data.shape}")
    if not bool(np.all(np.isfinite(field.data))):
        raise ValueError(f"{name}.data: expected finite values, got NaN or infinity")


def _compatible(port_0: ComplexField, port_1: ComplexField) -> None:
    if port_0.grid != port_1.grid:
        raise ValueError(f"port grids must match exactly: expected {port_0.grid!r}, got {port_1.grid!r}; shape alone is insufficient")
    if port_0.wavelength_m != port_1.wavelength_m:
        raise ValueError(f"port wavelengths must match exactly: expected {port_0.wavelength_m!r} m, got {port_1.wavelength_m!r} m")


def _norm(field: ComplexField, name: str) -> float:
    """sum(abs(U)**2, float64)*dx*dy, in amplitude-unit² m².

    Squared individual tails may underflow. A represented nonzero complete
    field whose entire norm rounds to zero is unusable, not intentional dark.
    """
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            total = np.sum(np.abs(field.data) ** 2, dtype=np.float64)
            result = float(total * field.grid.dx * field.grid.dy)
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError(f"{name}: sampled norm overflow or invalid arithmetic") from exc
    if not math.isfinite(result) or (result == 0.0 and np.any(field.data != 0.0)):
        raise ValueError(f"{name}: sampled norm unusable for nonzero field, got {result!r}")
    return result


def _owned(data: np.ndarray, template: ComplexField) -> ComplexField:
    """Use the supported defensive-copy/read-only public constructor."""
    return ComplexField(data=data, grid=template.grid, wavelength_m=template.wavelength_m)


def mix_balanced(port_0: ComplexField, port_1: ComplexField, *,
                 matrix: Literal["B", "B_dagger"]) -> tuple[ComplexField, ComplexField]:
    """Mix ordered coherent inputs using B or B†; return both actual fields.

    Fields use amplitude units and require exact grid and wavelength (metres)
    compatibility with canonical SamplingGrid and identity transverse correspondence. ``matrix`` is
    mandatory. B has crossed +i coefficients and B† crossed -i coefficients.
    Outputs have independently owned complex128 read-only storage, including
    when the caller supplies the same field to both logical ports.
    """
    if not isinstance(matrix, str):
        raise TypeError(f"matrix: expected 'B' or 'B_dagger' string, got {type(matrix).__name__}")
    if matrix not in ("B", "B_dagger"):
        raise ValueError(f"matrix: expected 'B' or 'B_dagger', got {matrix!r}")
    _field(port_0, "port_0")
    _field(port_1, "port_1")
    _compatible(port_0, port_1)
    _usable(_norm(port_0, "port_0") + _norm(port_1, "port_1"), "combined input norm")
    scale = 1.0 / math.sqrt(2.0)
    reflection = 1j if matrix == "B" else -1j
    try:
        # Bounded coefficient products/tails can underflow locally; overflow
        # and invalid arithmetic remain contextual failures.
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            mixed_0 = (port_0.data + reflection * port_1.data) * scale
            mixed_1 = (reflection * port_0.data + port_1.data) * scale
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError(f"{matrix} mixing: overflow or invalid field arithmetic") from exc
    outputs = (_owned(mixed_0, port_0), _owned(mixed_1, port_0))
    _usable(_norm(outputs[0], "mixed port 0") + _norm(outputs[1], "mixed port 1"), "combined output norm")
    return outputs


def apply_uniform_phase(field: ComplexField, *, phase_rad: float) -> ComplexField:
    """Multiply a whole field by exp(i*phase_rad), with phase in signed radians.

    No wrapping, clamping or normalization is performed. The returned public
    ComplexField owns independent read-only complex128 data, even at phase 0.
    Large binary64 phases retain finite argument-precision limitations.
    """
    phase = _real(phase_rad, "phase_rad")
    _field(field, "field")
    _norm(field, "phase input")
    if phase == 0.0:
        return _owned(field.data, field)
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            rotated = field.data * complex(math.cos(phase), math.sin(phase))
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError("uniform phase: overflow or invalid field arithmetic") from exc
    result = _owned(rotated, field)
    _norm(result, "phase output")
    return result


@dataclass(frozen=True, kw_only=True)
class TwoArmSpec:
    """Fixed unfolded two-arm request; path lengths in m, extra phase in rad.

    Lengths are finite and nonnegative, including zero; the finite signed extra
    phase applies only to arm 1 immediately before B†. No shutter/geometry/UI.
    """

    arm_0_distance_m: float
    arm_1_distance_m: float
    relative_phase_rad: float

    def __post_init__(self) -> None:
        for name in ("arm_0_distance_m", "arm_1_distance_m"):
            object.__setattr__(self, name, _nonnegative(getattr(self, name), name))
        object.__setattr__(self, "relative_phase_rad", _real(self.relative_phase_rad, "relative_phase_rad"))


def _pair(value: object, name: str) -> tuple[float, float]:
    if not isinstance(value, tuple):
        raise TypeError(f"{name}: expected tuple of two sampled norms, got {type(value).__name__}")
    if len(value) != 2:
        raise ValueError(f"{name}: expected exactly two sampled norms, got {len(value)}")
    return (_nonnegative(value[0], f"{name}[0]"), _nonnegative(value[1], f"{name}[1]"))


def _ratio(numerator: float, denominator: float, name: str) -> float | None:
    if denominator == 0.0:
        return None
    result = numerator / denominator
    if not math.isfinite(result) or (numerator > 0 and result == 0.0):
        raise ValueError(f"{name}: unusable ratio {numerator!r}/{denominator!r} = {result!r}")
    return result


@dataclass(frozen=True, kw_only=True)
class TwoArmNorms:
    """Ten sampled norms at ordered stages, in amplitude-unit² m².

    ``inputs`` is incident/zero; ``split`` is immediately after B;
    ``propagated`` is after ASM before phase; ``combiner`` is after arm-1 phase
    immediately before B†; ``outputs`` is immediately after B†. Aggregates and
    signed after-minus-before residuals are derived, never clamped or called
    calibrated absorption. Fractions use total input, not surviving output.
    """

    inputs: tuple[float, float]
    split: tuple[float, float]
    propagated: tuple[float, float]
    combiner: tuple[float, float]
    outputs: tuple[float, float]

    def __post_init__(self) -> None:
        for name in ("inputs", "split", "propagated", "combiner", "outputs"):
            pair = _pair(getattr(self, name), name)
            _usable(sum(pair), f"{name} total sampled norm")
            object.__setattr__(self, name, pair)
        # Invalid diagnostic arithmetic fails at construction, not on display.
        _ = self.output_fractions, self.total_output_ratio

    @property
    def inputs_total(self) -> float:
        """Sum of both input norms, amplitude-unit² m²."""
        return sum(self.inputs)

    @property
    def split_total(self) -> float:
        """Sum immediately after B, amplitude-unit² m²."""
        return sum(self.split)

    @property
    def propagated_total(self) -> float:
        """Sum after the two ASM calls before phase, amplitude-unit² m²."""
        return sum(self.propagated)

    @property
    def combiner_total(self) -> float:
        """Sum after arm-1 phase before B†, amplitude-unit² m²."""
        return sum(self.combiner)

    @property
    def outputs_total(self) -> float:
        """Sum immediately after B†, amplitude-unit² m²."""
        return sum(self.outputs)

    @property
    def split_delta(self) -> float:
        """Signed split_total - inputs_total, amplitude-unit² m²."""
        return self.split_total - self.inputs_total

    @property
    def propagation_delta(self) -> float:
        """Signed propagated_total - split_total, amplitude-unit² m²."""
        return self.propagated_total - self.split_total

    @property
    def phase_delta(self) -> float:
        """Signed combiner_total - propagated_total, amplitude-unit² m²."""
        return self.combiner_total - self.propagated_total

    @property
    def recombination_delta(self) -> float:
        """Signed outputs_total - combiner_total, amplitude-unit² m²."""
        return self.outputs_total - self.combiner_total

    @property
    def total_delta(self) -> float:
        """Signed outputs_total - inputs_total, amplitude-unit² m²."""
        return self.outputs_total - self.inputs_total

    @property
    def output_fractions(self) -> tuple[float | None, float | None]:
        """Each output/input-total ratio; (None, None) at zero total input."""
        denominator = self.inputs_total
        return (_ratio(self.outputs[0], denominator, "output fraction 0"),
                _ratio(self.outputs[1], denominator, "output fraction 1"))

    @property
    def total_output_ratio(self) -> float | None:
        """outputs_total/inputs_total; None at zero input, with no clamping."""
        return _ratio(self.outputs_total, self.inputs_total, "total output ratio")


@dataclass(frozen=True, kw_only=True, eq=False)
class TwoArmResult:
    """Owned ordered final complex fields, request and ten scalar norms.

    Output norms must exactly match the declared sampled reduction. Scalar
    records cannot independently authenticate discarded intermediate fields;
    the runner is the actual measurement path. No intermediate fields persist.
    """

    spec: TwoArmSpec
    outputs: tuple[ComplexField, ComplexField]
    norms: TwoArmNorms

    def __post_init__(self) -> None:
        if not isinstance(self.spec, TwoArmSpec):
            raise TypeError(f"spec: expected TwoArmSpec, got {type(self.spec).__name__}")
        checked_spec = TwoArmSpec(arm_0_distance_m=self.spec.arm_0_distance_m,
                                  arm_1_distance_m=self.spec.arm_1_distance_m,
                                  relative_phase_rad=self.spec.relative_phase_rad)
        if not isinstance(self.outputs, tuple):
            raise TypeError("outputs: expected tuple of two ComplexField objects")
        if len(self.outputs) != 2:
            raise ValueError(f"outputs: expected exactly two fields, got {len(self.outputs)}")
        if not isinstance(self.norms, TwoArmNorms):
            raise TypeError(f"norms: expected TwoArmNorms, got {type(self.norms).__name__}")
        checked_norms = TwoArmNorms(**{name: getattr(self.norms, name) for name in
                                      ("inputs", "split", "propagated", "combiner", "outputs")})
        if checked_norms.inputs[1] != 0.0:
            raise ValueError(f"inputs[1]: fixed runner requires zero second input norm, got {checked_norms.inputs[1]!r}")
        for index, field in enumerate(self.outputs):
            _field(field, f"outputs[{index}]")
        _compatible(*self.outputs)
        owned = tuple(_owned(field.data, field) for field in self.outputs)
        for index, field in enumerate(owned):
            measured = _norm(field, f"outputs[{index}]")
            if measured != checked_norms.outputs[index]:
                raise ValueError(f"outputs[{index}] sampled norm: record {checked_norms.outputs[index]!r} differs from measured {measured!r}")
        object.__setattr__(self, "spec", checked_spec)
        object.__setattr__(self, "norms", checked_norms)
        object.__setattr__(self, "outputs", owned)


def _travel(field: ComplexField, distance_m: float, name: str) -> ComplexField:
    bound = _geometry(field.grid, field.wavelength_m)
    _usable(bound * distance_m, f"{name} propagation phase bound")
    try:
        # Existing forward evanescent decay and bounded FFT products can
        # underflow. This child context restores the caller's settings.
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            return propagate_angular_spectrum(field, distance_m=distance_m, pad_factor=1)
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError(f"{name}: unusable forward propagation arithmetic at {distance_m!r} m") from exc


def run_two_arm(incident: ComplexField, *, spec: TwoArmSpec) -> TwoArmResult:
    """Run B -> two forward ASM arms -> arm-1 phase -> B†, retaining both ports.

    Distances are metres and extra phase radians. Each arm calls public M1 once
    with pad_factor=1, including zero distance, preserving its carrier/decay.
    The runner alone caps each dimension at 512 before copies/FFT work. This
    resource policy does not guarantee adequate physical sampling. Mixing
    conserves combined sampled norms; whole-run conservation additionally
    requires lossless arm evolution. Equal-arm fractions include actual
    propagated/input norm tau. Exact all-zero input is valid.
    """
    if not isinstance(spec, TwoArmSpec):
        raise TypeError(f"spec: expected TwoArmSpec, got {type(spec).__name__}")
    spec = TwoArmSpec(arm_0_distance_m=spec.arm_0_distance_m,
                      arm_1_distance_m=spec.arm_1_distance_m,
                      relative_phase_rad=spec.relative_phase_rad)
    _field(incident, "incident", cap=512)
    bound = _geometry(incident.grid, incident.wavelength_m)
    for index, distance in enumerate((spec.arm_0_distance_m, spec.arm_1_distance_m)):
        _usable(bound * distance, f"arm {index} propagation phase bound")
    snapshot = _owned(incident.data, incident)
    zero = _owned(np.zeros(incident.data.shape, dtype=np.complex128), incident)
    inputs = (_norm(snapshot, "incident input"), _norm(zero, "zero input"))
    split_0, split_1 = mix_balanced(snapshot, zero, matrix="B")
    split = (_norm(split_0, "split arm 0"), _norm(split_1, "split arm 1"))
    propagated_0 = _travel(split_0, spec.arm_0_distance_m, "arm 0")
    propagated_1 = _travel(split_1, spec.arm_1_distance_m, "arm 1")
    propagated = (_norm(propagated_0, "propagated arm 0"), _norm(propagated_1, "propagated arm 1"))
    combiner_0 = propagated_0
    combiner_1 = apply_uniform_phase(propagated_1, phase_rad=spec.relative_phase_rad)
    combiner = (_norm(combiner_0, "combiner arm 0"), _norm(combiner_1, "combiner arm 1"))
    outputs = mix_balanced(combiner_0, combiner_1, matrix="B_dagger")
    output_norms = (_norm(outputs[0], "output port 0"), _norm(outputs[1], "output port 1"))
    norms = TwoArmNorms(inputs=inputs, split=split, propagated=propagated,
                        combiner=combiner, outputs=output_norms)
    return TwoArmResult(spec=spec, outputs=outputs, norms=norms)
