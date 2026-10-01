"""Forward sequential orchestration on one complete periodic SI grid.

No propagation formula is defined here: every interval uses public M1 ASM.
Norms are amplitude-unit squared times square metres, never calibrated watts.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

import numpy as np

from ..field import ComplexField
from ..propagation import propagate_angular_spectrum
from .elements import _owned_field, apply_component, sample_source
from .model import SequentialExperiment, _require_real, _validate_grid

__all__ = ["StageRecord", "StageField", "SequentialResult", "run_experiment"]

_SELECTOR = re.compile(r"(?:source|observation|(?:before|after):[A-Za-z][A-Za-z0-9_-]{0,63})\Z", re.ASCII)


def _selector(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"stage selector must be str, got {type(value).__name__}")
    if not _SELECTOR.fullmatch(value):
        raise ValueError(f"invalid stage selector {value!r}")
    return value


def _nonnegative(value: float, name: str) -> float:
    value = _require_real(value, name)
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value!r}")
    return value


def _sampled_norm(field: ComplexField) -> float:
    """Reduce squared magnitude on the whole window; units amplitude-unit² m².

    Individual squared tails can underflow. A nonzero complete field whose
    entire norm rounds to zero is unusable, rather than an intentional dark field.
    """
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            total = np.sum(np.abs(field.data) ** 2, dtype=np.float64)
            norm = float(total * field.grid.dx * field.grid.dy)
    except FloatingPointError as exc:
        raise ValueError("sampled norm overflow or invalid arithmetic") from exc
    if not np.isfinite(norm) or (norm == 0.0 and np.any(field.data != 0.0)):
        raise ValueError(f"sampled norm is unusable for this nonzero field: {norm!r}")
    return norm


@dataclass(frozen=True, kw_only=True)
class StageRecord:
    """Scalar diagnostics at a named stage; z_m in metres, norm in a.u.² m².

    Differences and ratios are derived without clamping, not called absorption
    or calibrated efficiency. The source has no preceding stage.
    """

    selector: str
    z_m: float
    norm: float
    previous_norm: float | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "selector", _selector(self.selector))
        object.__setattr__(self, "z_m", _nonnegative(self.z_m, "z_m"))
        object.__setattr__(self, "norm", _nonnegative(self.norm, "norm"))
        if self.selector == "source":
            if self.previous_norm is not None or self.z_m != 0.0:
                raise ValueError("source stage requires z_m=0 and previous_norm=None")
        else:
            if self.previous_norm is None:
                raise ValueError("non-source stage requires previous_norm")
            object.__setattr__(self, "previous_norm", _nonnegative(self.previous_norm, "previous_norm"))
        # Validate the requested derived arithmetic immediately, including zero.
        _ = self.delta_norm, self.transmission_ratio

    @property
    def delta_norm(self) -> float | None:
        """Signed current-minus-previous norm, amplitude-unit² m²; never clamped."""
        if self.previous_norm is None:
            return None
        try:
            with np.errstate(all="raise"):
                return float(np.float64(self.norm) - np.float64(self.previous_norm))
        except FloatingPointError as exc:
            raise ValueError("unusable stage norm difference") from exc

    @property
    def transmission_ratio(self) -> float | None:
        """Current/previous sampled norm; None when incident norm is undefined."""
        if self.previous_norm is None or self.previous_norm == 0.0:
            return None
        try:
            with np.errstate(all="raise"):
                return float(np.float64(self.norm) / np.float64(self.previous_norm))
        except FloatingPointError as exc:
            raise ValueError("unusable stage norm ratio") from exc


@dataclass(frozen=True, kw_only=True, eq=False)
class StageField:
    """Owned read-only field at one explicitly requested stage."""

    selector: str
    field: ComplexField

    def __post_init__(self) -> None:
        object.__setattr__(self, "selector", _selector(self.selector))
        if not isinstance(self.field, ComplexField):
            raise TypeError(f"field must be ComplexField, got {type(self.field).__name__}")
        _validate_grid(self.field.grid, self.field.wavelength_m)
        object.__setattr__(self, "field", _owned_field(self.field.data, self.field.grid, self.field.wavelength_m))


@dataclass(frozen=True, kw_only=True, eq=False)
class SequentialResult:
    """Actual terminal field, scalar stages, and at most four owned stage fields."""

    experiment: SequentialExperiment
    observation: ComplexField
    stages: tuple[StageRecord, ...]
    recorded_fields: tuple[StageField, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.experiment, SequentialExperiment):
            raise TypeError("experiment must be SequentialExperiment")
        if not isinstance(self.observation, ComplexField):
            raise TypeError("observation must be ComplexField")
        if not isinstance(self.stages, tuple) or not all(isinstance(s, StageRecord) for s in self.stages):
            raise TypeError("stages must be a tuple of StageRecord")
        if not isinstance(self.recorded_fields, tuple) or not all(isinstance(s, StageField) for s in self.recorded_fields):
            raise TypeError("recorded_fields must be a tuple of StageField")
        expected = [("source", 0.0)]
        for c in self.experiment.components:
            expected.extend([(f"before:{c.id}", c.z_m), (f"after:{c.id}", c.z_m)])
        expected.append(("observation", self.experiment.observation.z_m))
        if [(s.selector, s.z_m) for s in self.stages] != expected:
            raise ValueError("stages must match all experiment stages in order and position")
        for a, b in zip(self.stages, self.stages[1:]):
            if b.previous_norm != a.norm:
                raise ValueError("stage previous_norm must match its immediately preceding stage")
        selectors = tuple(s.selector for s in self.recorded_fields)
        _record_selectors(self.experiment, selectors)
        for f in (self.observation, *(s.field for s in self.recorded_fields)):
            if f.grid != self.experiment.grid or f.wavelength_m != self.experiment.wavelength_m:
                raise ValueError("result fields must retain experiment grid and wavelength")
        if _sampled_norm(self.observation) != self.stages[-1].norm:
            raise ValueError("terminal norm record disagrees with actual observation")
        for captured in self.recorded_fields:
            stage = next(s for s in self.stages if s.selector == captured.selector)
            if _sampled_norm(captured.field) != stage.norm:
                raise ValueError(f"recorded field norm disagrees at {captured.selector!r}")
        object.__setattr__(self, "observation", _owned_field(self.observation.data, self.observation.grid, self.observation.wavelength_m))

    def field_at(self, selector: str) -> ComplexField:
        """Return terminal or explicitly recorded field; reject unavailable stages."""
        _selector(selector)
        if selector == "observation":
            return self.observation
        for stage in self.recorded_fields:
            if stage.selector == selector:
                return stage.field
        raise ValueError(f"field at {selector!r} was not recorded")


def _record_selectors(experiment: SequentialExperiment, selectors: tuple[str, ...]) -> None:
    if not isinstance(selectors, tuple):
        raise TypeError("record_fields must be a tuple of selector strings")
    for s in selectors:
        _selector(s)
    if len(selectors) > 4:
        raise ValueError(f"at most four intermediate fields may be requested, got {len(selectors)}")
    if len(set(selectors)) != len(selectors):
        raise ValueError("duplicate record_fields selectors are not allowed")
    permitted = {"source"}
    for c in experiment.components:
        permitted.update((f"before:{c.id}", f"after:{c.id}"))
    unknown = set(selectors) - permitted
    if unknown:
        raise ValueError(f"unknown or non-intermediate record_fields selectors: {sorted(unknown)!r}")


def run_experiment(experiment: SequentialExperiment, *, record_fields: tuple[str, ...] = ()) -> SequentialResult:
    """Simulate forward ordered elements and terminal observation, all in SI.

    Absolute positions are authoritative. Each derived interval is applied
    once with pad_factor=1. Colocated stages remain separately identifiable.
    """
    if not isinstance(experiment, SequentialExperiment):
        raise TypeError(f"experiment must be SequentialExperiment, got {type(experiment).__name__}")
    _record_selectors(experiment, record_fields)
    current = sample_source(experiment)
    z_m = 0.0
    stages: list[StageRecord] = []
    captured: dict[str, StageField] = {}

    def record(selector: str, position: float) -> None:
        previous = stages[-1].norm if stages else None
        stages.append(StageRecord(selector=selector, z_m=position, norm=_sampled_norm(current), previous_norm=previous))
        if selector in record_fields:
            captured[selector] = StageField(selector=selector, field=current)

    def travel(distance_m: float) -> ComplexField:
        # Forward decaying evanescent tails and tiny bounded spectral products
        # can reach zero. This context surrounds only the public propagation
        # call and restores the caller's settings on success and failure.
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
                return propagate_angular_spectrum(current, distance_m=distance_m, pad_factor=1)
        except (FloatingPointError, OverflowError) as exc:
            raise ValueError(f"unusable propagation arithmetic for interval {distance_m!r} m") from exc

    record("source", z_m)
    for component in experiment.components:
        separation = component.z_m - z_m
        current = travel(separation)
        z_m = component.z_m
        record(f"before:{component.id}", z_m)
        current = apply_component(current, component)
        record(f"after:{component.id}", z_m)
    final_separation = experiment.observation.z_m - z_m
    current = travel(final_separation)
    record("observation", experiment.observation.z_m)
    return SequentialResult(experiment=experiment, observation=current, stages=tuple(stages),
                            recorded_fields=tuple(captured[s] for s in record_fields))
