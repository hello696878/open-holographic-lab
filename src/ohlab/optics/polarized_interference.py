"""Ideal polarized two-path interference on one aligned unfolded grid.

Ordering is ``(port0.x, port0.y, port1.x, port1.y)``. The numerical
composition uses the public scalar B/B-dagger mixers, forward ASM and Jones
actions; it adds no vector propagation kernel or reflected-frame transform.
Both envelopes share the stipulated transverse basis and periodic DFT window.
Normative contract: ``docs/math_conventions.md`` section 3.20.

The supported domain is the complete-pipeline intersection of the existing
scalar and Jones operations. A valid combined Jones field can contain a tiny
component that is unusable at a later scalar mixing/phase boundary. Such a
component is never erased, normalized or silently retried.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

import numpy as np

from ..field import ComplexField
from ..grid import SamplingGrid
from ..propagation import propagate_angular_spectrum
from .interference import apply_uniform_phase, mix_balanced
from .polarization import JonesField, apply_linear_polarizer, apply_linear_retarder

__all__ = [
    "PolarizerAction", "RetarderAction", "PolarizationArm", "PolarizedTwoArmSpec",
    "PolarizedTwoArmNorms", "PolarizedTwoArmResult", "mix_balanced_jones",
    "run_polarized_two_arm",
]


def _real(value: object, name: str) -> float:
    """Convert an approved real numeric scalar without snapping it to zero."""
    if isinstance(value, (bool, np.bool_, np.timedelta64)) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        raise TypeError(
            f"{name}: expected int/float or NumPy integer/floating scalar "
            f"excluding bool and temporal scalars, got {type(value).__name__}"
        )
    try:
        result = float(value)
    except (OverflowError, ValueError, TypeError) as exc:
        raise ValueError(f"{name}: expected representable finite binary64") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name}: expected finite binary64, got {result!r}")
    if result == 0.0 and value != 0:
        raise ValueError(f"{name}: nonzero value underflowed to zero during binary64 conversion")
    return result


def _nonnegative(value: object, name: str) -> float:
    result = _real(value, name)
    if result < 0.0:
        raise ValueError(f"{name}: expected nonnegative value, got {result!r}")
    return result


def _usable(value: float, name: str, *, positive: bool = False) -> float:
    if not math.isfinite(value) or (positive and value <= 0.0):
        raise ValueError(f"{name}: unusable derived binary64 value {value!r}")
    return value


def _context_error(exc: Exception, name: str) -> TypeError | ValueError:
    """Keep the public type/numeric distinction and the original cause."""
    error = TypeError if isinstance(exc, TypeError) else ValueError
    return error(f"{name}: {exc}")


def _geometry(
    grid: SamplingGrid, wavelength_m: float, name: str, *, cap: int | None = None
) -> float:
    """Cheap scalar arithmetic bounds; no frequency mesh or kz computation."""
    if type(grid) is not SamplingGrid:
        raise TypeError(f"{name}.grid: expected canonical SamplingGrid, got {type(grid).__name__}")
    counts = []
    for key in ("ny", "nx"):
        value = getattr(grid, key)
        if isinstance(value, (bool, np.bool_, np.timedelta64)) or not isinstance(value, (int, np.integer)):
            raise TypeError(f"{name}.grid.{key}: expected integer excluding bool and temporal scalars, got {type(value).__name__}")
        if value < 1 or (cap is not None and value > cap):
            expected = f"1..{cap}" if cap is not None else ">= 1"
            raise ValueError(f"{name}.grid.{key}: expected {expected}, got {value!r}")
        counts.append(int(value))
    pitches = []
    for key in ("dy", "dx"):
        pitch = _real(getattr(grid, key), f"{name}.grid.{key}")
        if pitch <= 0.0:
            raise ValueError(f"{name}.grid.{key}: expected positive metres, got {pitch!r}")
        pitches.append(pitch)
    wavelength = _real(wavelength_m, f"{name}.wavelength_m")
    if wavelength <= 0.0:
        raise ValueError(f"{name}.wavelength_m: expected positive metres, got {wavelength!r}")
    dy, dx = pitches
    ny, nx = counts
    _usable(dx * dy, f"{name}.grid pixel area", positive=True)
    inverse_wavelength = _usable(1.0 / wavelength, f"{name} inverse wavelength", positive=True)
    cutoff_squared = _usable(inverse_wavelength * inverse_wavelength,
                             f"{name} frequency cutoff squared", positive=True)
    wavenumber = _usable(2.0 * math.pi * inverse_wavelength,
                         f"{name} wavenumber", positive=True)
    _usable(wavenumber * wavenumber, f"{name} wavenumber squared", positive=True)
    coordinate_squared = []
    frequency_squared = []
    for count, pitch, axis in ((nx, dx, "x"), (ny, dy, "y")):
        try:
            extent = _usable(count * pitch, f"{name}.grid {axis} extent", positive=True)
            reciprocal_extent = _usable(1.0 / extent, f"{name}.grid {axis} reciprocal extent", positive=True)
            coordinate = _usable((count // 2) * pitch, f"{name}.grid {axis} coordinate")
            coordinate_squared.append(_usable(coordinate * coordinate, f"{name}.grid {axis} coordinate squared"))
            frequency = _usable((count // 2) * reciprocal_extent, f"{name}.grid {axis} frequency bound")
            frequency_squared.append(_usable(frequency * frequency, f"{name}.grid {axis} frequency bound squared"))
        except OverflowError as exc:
            # The uncapped mixer can see a tampered, enormous Python count;
            # int-to-float conversion can fail before a float reaches _usable.
            raise ValueError(f"{name}.grid {axis}: unusable derived geometry arithmetic") from exc
    _usable(sum(coordinate_squared), f"{name}.grid radial coordinate squared")
    radial_bound = _usable(cutoff_squared + sum(frequency_squared),
                           f"{name} propagation frequency bound squared")
    return _usable(2.0 * math.pi * math.sqrt(radial_bound),
                   f"{name} propagation phase coefficient", positive=True)


def _component(field: ComplexField, name: str, *, cap: int | None = None) -> float:
    if not isinstance(field, ComplexField):
        raise TypeError(f"{name}: expected ComplexField, got {type(field).__name__}")
    bound = _geometry(field.grid, field.wavelength_m, name, cap=cap)
    if type(field.data) is not np.ndarray or field.data.dtype != np.dtype(np.complex128):
        raise TypeError(
            f"{name}.data: expected plain native complex128 ndarray, got "
            f"{type(field.data).__name__} with dtype {getattr(field.data, 'dtype', None)!r}"
        )
    if field.data.shape != field.grid.shape:
        raise ValueError(f"{name}.data: expected shape {field.grid.shape}, got {field.data.shape}")
    if not bool(np.all(np.isfinite(field.data))):
        raise ValueError(f"{name}.data: expected finite complex values, got NaN or infinity")
    return bound


def _compatible(first: ComplexField, second: ComplexField, name: str) -> None:
    first_grid = (first.grid.ny, first.grid.nx, first.grid.dy, first.grid.dx)
    second_grid = (second.grid.ny, second.grid.nx, second.grid.dy, second.grid.dx)
    if first_grid != second_grid:
        raise ValueError(
            f"{name}: grids must match exactly in ny/nx/dy/dx: expected "
            f"{first.grid!r}, got {second.grid!r}; shape alone is insufficient"
        )
    if first.wavelength_m != second.wavelength_m:
        raise ValueError(
            f"{name}: wavelengths must match exactly: expected "
            f"{first.wavelength_m!r} m, got {second.wavelength_m!r} m"
        )


def _measure(field: JonesField, name: str) -> float:
    try:
        return field.sampled_norm
    except (TypeError, ValueError, FloatingPointError, OverflowError) as exc:
        raise _context_error(exc, f"{name} Jones sampled norm") from exc


def _jones(field: JonesField, name: str, *, cap: int | None = None) -> tuple[float, float]:
    if not isinstance(field, JonesField):
        raise TypeError(f"{name}: expected JonesField, got {type(field).__name__}")
    bound = _component(field.x, f"{name}.x", cap=cap)
    _component(field.y, f"{name}.y", cap=cap)
    _compatible(field.x, field.y, f"{name} polarization components")
    return bound, _measure(field, name)


def _scalar_norm(field: ComplexField, name: str) -> float:
    """Existing scalar mixing/phase reduction, not the Jones checkpoint."""
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            total = np.sum(np.abs(field.data) ** 2, dtype=np.float64)
            result = float(total * field.grid.dx * field.grid.dy)
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError(f"{name}: scalar sampled norm overflow or invalid arithmetic") from exc
    if not math.isfinite(result) or (result == 0.0 and bool(np.any(field.data != 0.0))):
        raise ValueError(f"{name}: scalar sampled norm unusable for nonzero component, got {result!r}")
    return result


def _snapshot(field: JonesField, name: str) -> JonesField:
    try:
        return JonesField(x=field.x, y=field.y)
    except (TypeError, ValueError, FloatingPointError, OverflowError) as exc:
        raise _context_error(exc, f"{name} snapshot") from exc


@dataclass(frozen=True, kw_only=True)
class PolarizerAction:
    """Ideal terminal-plane linear polarizer; transmission axis in radians."""

    axis_angle_rad: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "axis_angle_rad", _real(self.axis_angle_rad, "axis_angle_rad"))


@dataclass(frozen=True, kw_only=True)
class RetarderAction:
    """Ideal terminal retarder; axis and perpendicular +retardance in radians."""

    axis_angle_rad: float
    retardance_rad: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "axis_angle_rad", _real(self.axis_angle_rad, "axis_angle_rad"))
        object.__setattr__(self, "retardance_rad", _real(self.retardance_rad, "retardance_rad"))


def _checked_action(action: PolarizerAction | RetarderAction, name: str) -> PolarizerAction | RetarderAction:
    try:
        if type(action) is PolarizerAction:
            return PolarizerAction(axis_angle_rad=action.axis_angle_rad)
        if type(action) is RetarderAction:
            return RetarderAction(axis_angle_rad=action.axis_angle_rad, retardance_rad=action.retardance_rad)
    except (TypeError, ValueError, FloatingPointError, OverflowError) as exc:
        raise _context_error(exc, name) from exc
    raise TypeError(f"{name}: expected concrete PolarizerAction or RetarderAction, got {type(action).__name__}")


@dataclass(frozen=True, kw_only=True)
class PolarizationArm:
    """Nonnegative forward distance in metres and zero-to-two terminal actions.

    Actions are a concrete immutable tuple in execution order, all at the
    arm's terminal reference plane, without travel between the actions.
    """

    distance_m: float
    actions: tuple[PolarizerAction | RetarderAction, ...] = ()

    def __post_init__(self) -> None:
        distance = _nonnegative(self.distance_m, "distance_m")
        if type(self.actions) is not tuple:
            raise TypeError(f"actions: expected concrete tuple, got {type(self.actions).__name__}")
        if len(self.actions) > 2:
            raise ValueError(f"actions: expected zero to two terminal actions, got {len(self.actions)}")
        actions = tuple(_checked_action(action, f"actions[{index}]")
                        for index, action in enumerate(self.actions))
        object.__setattr__(self, "distance_m", distance)
        object.__setattr__(self, "actions", actions)


def _checked_arm(arm: PolarizationArm, name: str) -> PolarizationArm:
    if type(arm) is not PolarizationArm:
        raise TypeError(f"{name}: expected concrete PolarizationArm, got {type(arm).__name__}")
    try:
        return PolarizationArm(distance_m=arm.distance_m, actions=arm.actions)
    except (TypeError, ValueError, FloatingPointError, OverflowError) as exc:
        raise _context_error(exc, name) from exc


@dataclass(frozen=True, kw_only=True)
class PolarizedTwoArmSpec:
    """Fixed two forward arms in metres and an extra common arm-1 phase in rad."""

    arm_0: PolarizationArm
    arm_1: PolarizationArm
    relative_phase_rad: float

    def __post_init__(self) -> None:
        arm_0 = _checked_arm(self.arm_0, "arm_0")
        arm_1 = _checked_arm(self.arm_1, "arm_1")
        phase = _real(self.relative_phase_rad, "relative_phase_rad")
        object.__setattr__(self, "arm_0", arm_0)
        object.__setattr__(self, "arm_1", arm_1)
        object.__setattr__(self, "relative_phase_rad", phase)


def _checked_spec(spec: PolarizedTwoArmSpec) -> PolarizedTwoArmSpec:
    if type(spec) is not PolarizedTwoArmSpec:
        raise TypeError(f"spec: expected concrete PolarizedTwoArmSpec, got {type(spec).__name__}")
    return PolarizedTwoArmSpec(arm_0=spec.arm_0, arm_1=spec.arm_1,
                               relative_phase_rad=spec.relative_phase_rad)


def _pair(value: object, name: str) -> tuple[float, float]:
    if type(value) is not tuple:
        raise TypeError(f"{name}: expected concrete tuple of two sampled norms, got {type(value).__name__}")
    if len(value) != 2:
        raise ValueError(f"{name}: expected exactly two sampled norms, got {len(value)}")
    return (_nonnegative(value[0], f"{name}[0]"), _nonnegative(value[1], f"{name}[1]"))


def _history(value: object, name: str) -> tuple[float, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name}: expected concrete tuple of after-action norms, got {type(value).__name__}")
    if len(value) > 2:
        raise ValueError(f"{name}: expected zero to two after-action norms, got {len(value)}")
    return tuple(_nonnegative(item, f"{name}[{index}]") for index, item in enumerate(value))


def _ratio(numerator: float, denominator: float, name: str) -> float | None:
    if denominator == 0.0:
        return None
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="raise"):
            ratio = float(np.float64(numerator) / np.float64(denominator))
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError(f"{name}: overflow, underflow or invalid ratio arithmetic") from exc
    if not math.isfinite(ratio) or (numerator > 0.0 and ratio == 0.0):
        raise ValueError(f"{name}: unusable ratio {numerator!r}/{denominator!r} = {ratio!r}")
    return ratio


@dataclass(frozen=True, kw_only=True)
class PolarizedTwoArmNorms:
    """Six Jones checkpoint pairs plus bounded after-action norm histories.

    Every norm is in amplitude-unit^2*m^2, not watts. Checkpoint names identify
    incident/zero inputs, post-B arms, post-ASM arms, post-terminal-action arms,
    post-arm-1-phase combiner inputs, and unanalysed post-B-dagger outputs.
    Histories contain at most two after-action values per arm. Signed changes
    are derived without clamping; fractions use original incident input.
    """

    inputs: tuple[float, float]
    split: tuple[float, float]
    propagated: tuple[float, float]
    elements: tuple[float, float]
    combiner: tuple[float, float]
    outputs: tuple[float, float]
    arm_action_norms: tuple[tuple[float, ...], tuple[float, ...]] = ((), ())

    def __post_init__(self) -> None:
        for name in ("inputs", "split", "propagated", "elements", "combiner", "outputs"):
            pair = _pair(getattr(self, name), name)
            _usable(sum(pair), f"{name} total sampled norm")
            object.__setattr__(self, name, pair)
        if type(self.arm_action_norms) is not tuple:
            raise TypeError(f"arm_action_norms: expected concrete tuple of two histories, got {type(self.arm_action_norms).__name__}")
        if len(self.arm_action_norms) != 2:
            raise ValueError(f"arm_action_norms: expected exactly two histories, got {len(self.arm_action_norms)}")
        histories = (_history(self.arm_action_norms[0], "arm_action_norms[0]"),
                     _history(self.arm_action_norms[1], "arm_action_norms[1]"))
        for index, history in enumerate(histories):
            expected = history[-1] if history else self.propagated[index]
            if self.elements[index] != expected:
                raise ValueError(f"elements[{index}]: expected same-reduction history endpoint {expected!r}, got {self.elements[index]!r}")
        if self.combiner[0] != self.elements[0]:
            raise ValueError(f"combiner[0]: untouched arm 0 must equal elements[0] {self.elements[0]!r}, got {self.combiner[0]!r}")
        object.__setattr__(self, "arm_action_norms", histories)
        # All diagnostics must be usable when the record is constructed.
        _ = self.output_fractions, self.total_output_ratio

    @property
    def inputs_total(self) -> float:
        """Combined incident input norm, amplitude-unit^2*m^2."""
        return sum(self.inputs)

    @property
    def split_total(self) -> float:
        """Combined norm immediately after B, amplitude-unit^2*m^2."""
        return sum(self.split)

    @property
    def propagated_total(self) -> float:
        """Combined post-ASM norm before actions, amplitude-unit^2*m^2."""
        return sum(self.propagated)

    @property
    def elements_total(self) -> float:
        """Combined norm after terminal actions, amplitude-unit^2*m^2."""
        return sum(self.elements)

    @property
    def combiner_total(self) -> float:
        """Combined post-phase norm before B-dagger, amplitude-unit^2*m^2."""
        return sum(self.combiner)

    @property
    def outputs_total(self) -> float:
        """Combined raw output norm, amplitude-unit^2*m^2."""
        return sum(self.outputs)

    @property
    def split_delta(self) -> float:
        """Signed split minus input total, amplitude-unit^2*m^2."""
        return self.split_total - self.inputs_total

    @property
    def propagation_delta(self) -> float:
        """Signed propagated minus split total, amplitude-unit^2*m^2."""
        return self.propagated_total - self.split_total

    @property
    def elements_delta(self) -> float:
        """Signed terminal-action minus propagated total, amplitude-unit^2*m^2."""
        return self.elements_total - self.propagated_total

    @property
    def phase_delta(self) -> float:
        """Signed combiner minus terminal-action total, amplitude-unit^2*m^2."""
        return self.combiner_total - self.elements_total

    @property
    def recombination_delta(self) -> float:
        """Signed raw output minus combiner total, amplitude-unit^2*m^2."""
        return self.outputs_total - self.combiner_total

    @property
    def total_delta(self) -> float:
        """Signed raw output minus original input total, amplitude-unit^2*m^2."""
        return self.outputs_total - self.inputs_total

    @property
    def propagation_deltas(self) -> tuple[float, float]:
        """Per-arm post-ASM minus split norm, amplitude-unit^2*m^2."""
        return (self.propagated[0] - self.split[0], self.propagated[1] - self.split[1])

    @property
    def element_deltas(self) -> tuple[float, float]:
        """Per-arm post-action minus post-ASM norm, amplitude-unit^2*m^2."""
        return (self.elements[0] - self.propagated[0], self.elements[1] - self.propagated[1])

    @property
    def phase_deltas(self) -> tuple[float, float]:
        """Per-arm post-phase minus post-action norm, amplitude-unit^2*m^2."""
        return (self.combiner[0] - self.elements[0], self.combiner[1] - self.elements[1])

    @property
    def arm_action_deltas(self) -> tuple[tuple[float, ...], tuple[float, ...]]:
        """Ordered after-minus-before action norms, amplitude-unit^2*m^2."""
        differences = []
        for index, history in enumerate(self.arm_action_norms):
            before = self.propagated[index]
            changes = []
            for after in history:
                changes.append(after - before)
                before = after
            differences.append(tuple(changes))
        return (differences[0], differences[1])

    @property
    def output_fractions(self) -> tuple[float | None, float | None]:
        """Dimensionless raw output/original input ratios; None at zero input."""
        return (_ratio(self.outputs[0], self.inputs_total, "output fraction 0"),
                _ratio(self.outputs[1], self.inputs_total, "output fraction 1"))

    @property
    def total_output_ratio(self) -> float | None:
        """Dimensionless retained raw total/original input; None at zero input."""
        return _ratio(self.outputs_total, self.inputs_total, "total output ratio")


@dataclass(frozen=True, kw_only=True, eq=False)
class PolarizedTwoArmResult:
    """Owned raw Jones outputs and scalar measurements for a fixed request.

    The four component arrays share no numerical storage with supplied fields
    or each other. Output norms must match the identical public Jones reduction
    exactly. Stored histories do not authenticate discarded intermediate data.
    Downstream analyzers are separate operations and cannot replace raw outputs.
    """

    spec: PolarizedTwoArmSpec
    outputs: tuple[JonesField, JonesField]
    norms: PolarizedTwoArmNorms

    def __post_init__(self) -> None:
        checked_spec = _checked_spec(self.spec)
        if type(self.outputs) is not tuple:
            raise TypeError(f"outputs: expected concrete tuple of two JonesField objects, got {type(self.outputs).__name__}")
        if len(self.outputs) != 2:
            raise ValueError(f"outputs: expected exactly two Jones fields, got {len(self.outputs)}")
        if type(self.norms) is not PolarizedTwoArmNorms:
            raise TypeError(f"norms: expected concrete PolarizedTwoArmNorms, got {type(self.norms).__name__}")
        checked_norms = PolarizedTwoArmNorms(**{
            name: getattr(self.norms, name) for name in
            ("inputs", "split", "propagated", "elements", "combiner", "outputs", "arm_action_norms")
        })
        if checked_norms.inputs[1] != 0.0:
            raise ValueError(f"inputs[1]: fixed runner requires zero second input norm, got {checked_norms.inputs[1]!r}")
        for index, arm in enumerate((checked_spec.arm_0, checked_spec.arm_1)):
            if len(checked_norms.arm_action_norms[index]) != len(arm.actions):
                raise ValueError(f"arm_action_norms[{index}]: expected {len(arm.actions)} values matching spec actions, got {len(checked_norms.arm_action_norms[index])}")
        for index, field in enumerate(self.outputs):
            _jones(field, f"outputs[{index}]")
        _compatible(self.outputs[0].x, self.outputs[1].x, "output ports")
        owned = (_snapshot(self.outputs[0], "outputs[0]"), _snapshot(self.outputs[1], "outputs[1]"))
        for index, field in enumerate(owned):
            measured = _measure(field, f"outputs[{index}]")
            if measured != checked_norms.outputs[index]:
                raise ValueError(f"outputs[{index}] sampled norm: record {checked_norms.outputs[index]!r} differs from measured {measured!r}")
        object.__setattr__(self, "spec", checked_spec)
        object.__setattr__(self, "norms", checked_norms)
        object.__setattr__(self, "outputs", owned)


def mix_balanced_jones(
    port_0: JonesField, port_1: JonesField, *, matrix: Literal["B", "B_dagger"]
) -> tuple[JonesField, JonesField]:
    """Mix matching x/y components across two coherent optical ports.

    Inputs use amplitude units, canonical equal grids with pitches in metres,
    and equal vacuum wavelengths in metres. Validate both combined Jones norms,
    all four scalar component norms and exact compatibility before mixing x.
    B has crossed +i coefficients; B-dagger has crossed -i coefficients. The
    primitive has no runner grid cap. Both raw returned Jones fields own their
    four read-only complex128 component arrays independently.
    """
    if not isinstance(matrix, str):
        raise TypeError(f"matrix: expected 'B' or 'B_dagger' string, got {type(matrix).__name__}")
    if matrix not in ("B", "B_dagger"):
        raise ValueError(f"matrix: expected 'B' or 'B_dagger', got {matrix!r}")
    _, norm_0 = _jones(port_0, "port_0")
    _, norm_1 = _jones(port_1, "port_1")
    _compatible(port_0.x, port_1.x, "optical ports")
    component_norms = (
        _scalar_norm(port_0.x, "port_0.x"), _scalar_norm(port_0.y, "port_0.y"),
        _scalar_norm(port_1.x, "port_1.x"), _scalar_norm(port_1.y, "port_1.y"),
    )
    _usable(norm_0 + norm_1, "combined Jones input norm")
    _usable(component_norms[0] + component_norms[2], "x combined scalar input norm")
    _usable(component_norms[1] + component_norms[3], "y combined scalar input norm")
    first = _snapshot(port_0, "port_0")
    second = _snapshot(port_1, "port_1")
    try:
        x_outputs = mix_balanced(first.x, second.x, matrix=matrix)
    except (TypeError, ValueError, FloatingPointError, OverflowError) as exc:
        raise _context_error(exc, f"{matrix} mixing component x") from exc
    try:
        y_outputs = mix_balanced(first.y, second.y, matrix=matrix)
    except (TypeError, ValueError, FloatingPointError, OverflowError) as exc:
        raise _context_error(exc, f"{matrix} mixing component y") from exc
    outputs = []
    for index in range(2):
        try:
            outputs.append(JonesField(x=x_outputs[index], y=y_outputs[index]))
        except (TypeError, ValueError, FloatingPointError, OverflowError) as exc:
            raise _context_error(exc, f"{matrix} mixed output port {index}") from exc
    _usable(_measure(outputs[0], f"{matrix} output port 0") +
            _measure(outputs[1], f"{matrix} output port 1"), "combined Jones output norm")
    return (outputs[0], outputs[1])


def _travel(field: JonesField, distance_m: float, arm_index: int) -> JonesField:
    propagated = []
    for component, scalar in (("x", field.x), ("y", field.y)):
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
                propagated.append(propagate_angular_spectrum(scalar, distance_m=distance_m, pad_factor=1))
        except (TypeError, ValueError, FloatingPointError, OverflowError) as exc:
            raise _context_error(exc, f"arm {arm_index} propagation component {component}") from exc
    try:
        return JonesField(x=propagated[0], y=propagated[1])
    except (TypeError, ValueError, FloatingPointError, OverflowError) as exc:
        raise _context_error(exc, f"arm {arm_index} propagation Jones output") from exc


def _actions(
    field: JonesField, arm: PolarizationArm, arm_index: int
) -> tuple[JonesField, tuple[float, ...]]:
    history = []
    for index, action in enumerate(arm.actions):
        try:
            if type(action) is PolarizerAction:
                field = apply_linear_polarizer(field, axis_angle_rad=action.axis_angle_rad)
            else:
                field = apply_linear_retarder(field, axis_angle_rad=action.axis_angle_rad,
                                              retardance_rad=action.retardance_rad)
        except (TypeError, ValueError, FloatingPointError, OverflowError) as exc:
            raise _context_error(exc, f"arm {arm_index} terminal action {index}") from exc
        # This is deliberately a Jones-only boundary: a tiny component can be
        # transformed by the next action before any scalar consumer sees it.
        history.append(_measure(field, f"arm {arm_index} terminal action {index}"))
    return field, tuple(history)


def _phase(field: JonesField, phase_rad: float) -> JonesField:
    try:
        _scalar_norm(field.x, "arm 1 extra phase component x input")
        _scalar_norm(field.y, "arm 1 extra phase component y input")
    except (TypeError, ValueError, FloatingPointError, OverflowError) as exc:
        raise _context_error(exc, "arm 1 extra phase scalar preflight") from exc
    phased = []
    for component, scalar in (("x", field.x), ("y", field.y)):
        try:
            phased.append(apply_uniform_phase(scalar, phase_rad=phase_rad))
        except (TypeError, ValueError, FloatingPointError, OverflowError) as exc:
            raise _context_error(exc, f"arm 1 extra phase component {component}") from exc
    try:
        return JonesField(x=phased[0], y=phased[1])
    except (TypeError, ValueError, FloatingPointError, OverflowError) as exc:
        raise _context_error(exc, "arm 1 extra phase Jones output") from exc


def run_polarized_two_arm(
    incident: JonesField, *, spec: PolarizedTwoArmSpec
) -> PolarizedTwoArmResult:
    """Run the fixed ideal two-arm Jones-envelope composition, retaining raw ports.

    Distances are nonnegative metres and the common arm-1 phase is signed
    radians. Each arm propagates both components with public scalar ASM and
    explicit pad_factor=1, including zero distances. Its zero-to-two ordered
    Jones actions are lumped at the terminal plane. The extra phase rotates
    both arm-1 components before B-dagger. No output analyzer is applied.

    Only this runner caps each grid axis at 128, before field snapshots/optical
    work. Validate the full static request before dark/identity cases. Derived
    scalar/Jones failures remain contextual errors with no partial result.
    Fractions use original incident norm and retain loss and signed roundoff.
    This is an aligned low-angle envelope approximation, not a vector Maxwell
    solver or calibrated electromagnetic-energy calculation.
    """
    checked_spec = _checked_spec(spec)
    bound, incident_norm = _jones(incident, "incident", cap=128)
    _scalar_norm(incident.x, "incident.x")
    _scalar_norm(incident.y, "incident.y")
    for index, arm in enumerate((checked_spec.arm_0, checked_spec.arm_1)):
        _usable(bound * arm.distance_m, f"arm {index} propagation phase bound")
    snapshot = _snapshot(incident, "incident")
    try:
        zero_scalar = ComplexField(data=np.zeros(incident.shape, dtype=np.complex128),
                                   grid=incident.grid, wavelength_m=incident.wavelength_m)
        zero = JonesField(x=zero_scalar, y=zero_scalar)
    except (TypeError, ValueError, FloatingPointError, OverflowError) as exc:
        raise _context_error(exc, "zero second input construction") from exc
    inputs = (incident_norm, _measure(zero, "zero second input"))
    try:
        arms = mix_balanced_jones(snapshot, zero, matrix="B")
    except (TypeError, ValueError, FloatingPointError, OverflowError) as exc:
        raise _context_error(exc, "split stage arms 0/1") from exc
    del snapshot, zero, zero_scalar
    split = (_measure(arms[0], "split arm 0"), _measure(arms[1], "split arm 1"))
    arms = (_travel(arms[0], checked_spec.arm_0.distance_m, 0),
            _travel(arms[1], checked_spec.arm_1.distance_m, 1))
    propagated = (_measure(arms[0], "propagated arm 0"), _measure(arms[1], "propagated arm 1"))
    action_0 = _actions(arms[0], checked_spec.arm_0, 0)
    action_1 = _actions(arms[1], checked_spec.arm_1, 1)
    arms = (action_0[0], action_1[0])
    histories = (action_0[1], action_1[1])
    del action_0, action_1
    elements = (_measure(arms[0], "terminal elements arm 0"), _measure(arms[1], "terminal elements arm 1"))
    arms = (arms[0], _phase(arms[1], checked_spec.relative_phase_rad))
    combiner = (_measure(arms[0], "combiner arm 0"), _measure(arms[1], "combiner arm 1"))
    try:
        outputs = mix_balanced_jones(arms[0], arms[1], matrix="B_dagger")
    except (TypeError, ValueError, FloatingPointError, OverflowError) as exc:
        raise _context_error(exc, "recombination stage arms 0/1") from exc
    del arms
    output_norms = (_measure(outputs[0], "raw output port 0"), _measure(outputs[1], "raw output port 1"))
    try:
        norms = PolarizedTwoArmNorms(inputs=inputs, split=split, propagated=propagated,
                                     elements=elements, combiner=combiner, outputs=output_norms,
                                     arm_action_norms=histories)
        return PolarizedTwoArmResult(spec=checked_spec, outputs=outputs, norms=norms)
    except (TypeError, ValueError, FloatingPointError, OverflowError) as exc:
        raise _context_error(exc, "final raw result construction") from exc
