"""Bounded W1 section orchestration over the unchanged public V0 and ASM APIs.

The supported train is Gaussian -> one circular/rectangular aperture -> one
ideal thin lens -> observation, in stored order, on at most 128 samples/axis.
Every optional plane is propagated directly from its actual upstream capture.
No display plane is an upstream anchor for another display plane. The original
V0 terminal complex field is retained by identity; only intensities are stacked.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re

import numpy as np

from ..field import ComplexField
from ..propagation import propagate_angular_spectrum
from .model import (CircularAperture, GaussianSource, RectangularAperture,
                    SequentialExperiment, ThinLens)
from .simulation import SequentialResult, StageRecord, run_experiment

__all__ = ["MAX_AXIS", "MAX_SECTIONS", "MAX_INTERIOR", "WaveFieldPosition",
           "WaveFieldPlane", "WaveFieldResult", "validate_sampling",
           "default_interior_positions", "section_plan", "sample_wave_field"]

MAX_AXIS = 128
MAX_SECTIONS = 25
MAX_INTERIOR = 19
_EVENT = re.compile(r"(?:source|observation|(?:before|after):[A-Za-z][A-Za-z0-9_-]{0,63})\Z", re.ASCII)


def _real(value: object, name: str, *, nonnegative: bool = True) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise TypeError(f"{name} requires a finite real scalar excluding bool")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name} is not representable in binary64") from exc
    if not math.isfinite(result) or (nonnegative and result < 0):
        raise ValueError(f"{name} requires a finite {'nonnegative ' if nonnegative else ''}value; got {result!r}")
    return result


def _supported(experiment: SequentialExperiment) -> None:
    if not isinstance(experiment, SequentialExperiment):
        raise TypeError("experiment must be SequentialExperiment")
    if not isinstance(experiment.source, GaussianSource):
        raise ValueError("W1 supports a Gaussian source, not a uniform source")
    if (len(experiment.components) != 2
            or not isinstance(experiment.components[0], (CircularAperture, RectangularAperture))
            or not isinstance(experiment.components[1], ThinLens)):
        raise ValueError("W1 requires exactly one aperture followed by one thin lens in stored order")
    if experiment.grid.nx > MAX_AXIS or experiment.grid.ny > MAX_AXIS:
        raise ValueError(f"W1 grid requires each axis in 1..{MAX_AXIS}; got {experiment.grid.shape!r}; no resizing is performed")


def validate_sampling(experiment: SequentialExperiment,
                      interior_z_m: tuple[float, ...]) -> tuple[float, ...]:
    """Validate explicit absolute interior positions in metres, without optics.

    Positions must be a tuple of at most 19 finite binary64 reals, strictly
    increasing and strictly inside the three open propagation intervals.
    Optical-event planes are always added separately, including at equal z.
    """
    _supported(experiment)
    if not isinstance(interior_z_m, tuple):
        raise TypeError("interior_z_m must be a tuple of finite real positions in metres")
    if len(interior_z_m) > MAX_INTERIOR:
        raise ValueError(f"at most {MAX_INTERIOR} interior positions are allowed; got {len(interior_z_m)}")
    events = (0.0, *(c.z_m for c in experiment.components), experiment.observation.z_m)
    result: list[float] = []
    for index, value in enumerate(interior_z_m):
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating)):
            raise TypeError(f"interior_z_m[{index}] must be a finite real scalar excluding bool")
        try:
            position = float(value)
        except (ValueError, OverflowError) as exc:
            raise ValueError(f"interior_z_m[{index}] is not representable in binary64") from exc
        if not math.isfinite(position):
            raise ValueError(f"interior_z_m[{index}] must be finite; got {position!r}")
        if result and position <= result[-1]:
            raise ValueError("interior_z_m must be strictly increasing, without duplicates")
        if not any(a < position < b for a, b in zip(events, events[1:])):
            raise ValueError(f"interior_z_m[{index}]={position!r} must be strictly inside a propagation interval, excluding optical events")
        result.append(position)
    return tuple(result)


def default_interior_positions(experiment: SequentialExperiment) -> tuple[float, ...]:
    """Allocate 19 optional positions proportionally, in metres; no computation.

    Floor plus largest remainder, with stable earlier-gap ties, gives required
    events priority. Zero spans get no interiors; an entirely co-located train
    returns no fabricated positions. Rounded endpoints/duplicates fail loudly.
    """
    _supported(experiment)
    boundaries = (0.0, *(c.z_m for c in experiment.components), experiment.observation.z_m)
    total = boundaries[-1]
    if total == 0.0:
        return ()
    spans = [b-a for a, b in zip(boundaries, boundaries[1:])]
    raw = [(span/total)*MAX_INTERIOR for span in spans]
    counts = [math.floor(value) for value in raw]
    remaining = MAX_INTERIOR-sum(counts)
    for index in sorted(range(3), key=lambda i: (-(raw[i]-counts[i]), i))[:remaining]:
        counts[index] += 1
    positions = tuple(start+(end-start)*j/(count+1)
                      for start, end, count in zip(boundaries, boundaries[1:], counts)
                      for j in range(1, count+1))
    return validate_sampling(experiment, positions)


@dataclass(frozen=True, kw_only=True)
class WaveFieldPosition:
    """One genuine section and its upstream provenance; distances in metres."""

    id: str
    stage: str
    z_m: float
    anchor_selector: str
    anchor_z_m: float
    separation_m: float

    def __post_init__(self) -> None:
        for name in ('id', 'stage', 'anchor_selector'):
            if not isinstance(getattr(self, name), str):
                raise TypeError(f'{name} must be str')
        if self.stage != 'interior' and not _EVENT.fullmatch(self.stage):
            raise ValueError(f'invalid section stage {self.stage!r}')
        if (self.stage == 'interior' and re.fullmatch(r'section:interior:[0-9]{3}', self.id) is None
                or self.stage != 'interior' and self.id != 'section:'+self.stage):
            raise ValueError('section id must identify its exact event or explicit interior ordinal')
        if (not _EVENT.fullmatch(self.anchor_selector)
                or self.anchor_selector != 'source' and not self.anchor_selector.startswith('after:')):
            raise ValueError('anchor_selector must identify the source or an after-element capture')
        for name in ('z_m', 'anchor_z_m', 'separation_m'):
            object.__setattr__(self, name, _real(getattr(self, name), name))
        if self.z_m-self.anchor_z_m != self.separation_m:
            raise ValueError('section separation_m must equal z_m minus anchor_z_m without backward travel')


def section_plan(experiment: SequentialExperiment, *,
                 interior_z_m: tuple[float, ...]) -> tuple[WaveFieldPosition, ...]:
    """Return the exact ordered event/interior identities without running V0."""
    positions = validate_sampling(experiment, interior_z_m)
    aperture, lens = experiment.components
    rows: list[WaveFieldPosition] = []

    def append(stage: str, z: float, anchor: str, origin: float,
               identity: str | None = None) -> None:
        rows.append(WaveFieldPosition(id=identity or f"section:{stage}", stage=stage,
                                     z_m=z, anchor_selector=anchor,
                                     anchor_z_m=origin, separation_m=z-origin))

    append("source", 0.0, "source", 0.0)
    bounds = (0.0, aperture.z_m, lens.z_m, experiment.observation.z_m)
    anchors = ("source", f"after:{aperture.id}", f"after:{lens.id}")
    for gap, (start, end, anchor) in enumerate(zip(bounds, bounds[1:], anchors)):
        for index, z in enumerate(positions):
            if start < z < end:
                append("interior", z, anchor, start, f"section:interior:{index:03d}")
        if gap < 2:
            component = experiment.components[gap]
            append(f"before:{component.id}", end, anchor, start)
            append(f"after:{component.id}", end, f"after:{component.id}", end)
        else:
            append("observation", end, anchor, start)
    return tuple(rows)


@dataclass(frozen=True, kw_only=True)
class WaveFieldPlane(WaveFieldPosition):
    """Raw section diagnostics; intensity a.u.², norm a.u.² m².

    Event diagnostics are the unchanged canonical V0 StageRecord values.
    Interior signed change/ratio compare to the named upstream anchor, never
    the preceding display sample and never interpreted as physical absorption.
    """

    norm: float
    previous_norm: float | None
    delta_norm: float | None
    transmission_ratio: float | None
    comparison: str
    on_axis_intensity: float
    max_intensity: float

    def __post_init__(self) -> None:
        WaveFieldPosition.__post_init__(self)
        for name in ('norm', 'on_axis_intensity', 'max_intensity'):
            object.__setattr__(self, name, _real(getattr(self, name), name))
        for name in ('previous_norm', 'transmission_ratio'):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _real(value, name))
        if self.delta_norm is not None:
            object.__setattr__(self, 'delta_norm', _real(self.delta_norm, 'delta_norm', nonnegative=False))
        if not isinstance(self.comparison, str):
            raise TypeError('comparison must be str')
        expected = 'upstream_anchor' if self.stage == 'interior' else 'previous_stage'
        if self.comparison != expected:
            raise ValueError(f'comparison requires {expected!r} for this section')
        record = StageRecord(selector='observation' if self.stage == 'interior' else self.stage,
                             z_m=self.z_m, norm=self.norm, previous_norm=self.previous_norm)
        if (self.delta_norm, self.transmission_ratio) != (record.delta_norm, record.transmission_ratio):
            raise ValueError('section signed change/ratio must retain the exact raw diagnostic arithmetic')
        if self.on_axis_intensity > self.max_intensity:
            raise ValueError('on-axis sampled intensity cannot exceed the actual sampled maximum')


def _readonly_array(value: np.ndarray, shape: tuple[int, ...], name: str) -> np.ndarray:
    if type(value) is not np.ndarray or value.dtype != np.dtype(np.float64):
        raise TypeError(f"{name} requires a plain native float64 ndarray")
    if value.shape != shape or not np.all(np.isfinite(value)):
        raise ValueError(f"{name} requires finite shape {shape!r}; got {value.shape!r}")
    result = np.array(value, dtype=np.float64, copy=True, order="C")
    result.flags.writeable = False
    return result


@dataclass(frozen=True, kw_only=True, eq=False)
class WaveFieldResult:
    """Owned read-only intensities and the actual unchanged canonical V0 result.

    No full intermediate complex stack is retained. Readonly ndarray flags are
    the existing reversible ownership contract, not hardened storage.
    """

    experiment: SequentialExperiment
    interior_z_m: tuple[float, ...]
    canonical: SequentialResult
    planes: tuple[WaveFieldPlane, ...]
    intensities: np.ndarray
    x_m: np.ndarray
    y_m: np.ndarray

    def __post_init__(self) -> None:
        positions = validate_sampling(self.experiment, self.interior_z_m)
        if not isinstance(self.canonical, SequentialResult):
            raise TypeError("canonical must be SequentialResult")
        if self.canonical.experiment is not self.experiment:
            raise ValueError("canonical must belong to the identical captured experiment")
        plan = section_plan(self.experiment, interior_z_m=positions)
        if (not isinstance(self.planes, tuple)
                or not all(isinstance(row, WaveFieldPlane) for row in self.planes)):
            raise TypeError("planes must be a tuple of WaveFieldPlane")
        actual = tuple(WaveFieldPosition(**{name: getattr(row, name)
                         for name in WaveFieldPosition.__dataclass_fields__}) for row in self.planes)
        if actual != plan:
            raise ValueError("planes must match the complete ordered event/interior plan")
        shape = (len(plan), *self.experiment.grid.shape)
        intensity = _readonly_array(self.intensities, shape, "intensities")
        if np.any(intensity < 0):
            raise ValueError("intensities must be nonnegative")
        x = _readonly_array(self.x_m, (self.experiment.grid.nx,), "x_m")
        y = _readonly_array(self.y_m, (self.experiment.grid.ny,), "y_m")
        if not np.array_equal(x, self.experiment.grid.x) or not np.array_equal(y, self.experiment.grid.y):
            raise ValueError("x_m/y_m must preserve the exact physical grid coordinates")
        stages = {record.selector: record for record in self.canonical.stages}
        for row, image in zip(self.planes, intensity):
            if row.stage == "interior":
                reference = stages[row.anchor_selector]
                record = StageRecord(selector="observation", z_m=row.z_m,
                                     norm=row.norm, previous_norm=reference.norm)
                comparison = "upstream_anchor"
            else:
                record = stages[row.stage]
                comparison = "previous_stage"
            if (row.norm, row.previous_norm, row.delta_norm, row.transmission_ratio, row.comparison) != (
                    record.norm, record.previous_norm, record.delta_norm, record.transmission_ratio, comparison):
                raise ValueError(f"section {row.id!r} diagnostics disagree with its authoritative comparison")
            if (row.on_axis_intensity != float(image[self.experiment.grid.ny//2, self.experiment.grid.nx//2])
                    or row.max_intensity != float(np.max(image))):
                raise ValueError(f"section {row.id!r} intensity diagnostics disagree with actual samples")
        object.__setattr__(self, "interior_z_m", positions)
        object.__setattr__(self, "intensities", intensity)
        object.__setattr__(self, "x_m", x)
        object.__setattr__(self, "y_m", y)

    @property
    def observation(self) -> ComplexField:
        """Return the actual canonical terminal field by identity, never a copy."""
        return self.canonical.observation


def _sampled_norm(field: ComplexField) -> float:
    # Same documented full-window reduction as V0, not a normalized display sum.
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            norm = float(np.sum(np.abs(field.data)**2, dtype=np.float64)*field.grid.dx*field.grid.dy)
    except FloatingPointError as exc:
        raise ValueError("section sampled norm overflow or invalid arithmetic") from exc
    if not math.isfinite(norm) or (norm == 0.0 and np.any(field.data != 0)):
        raise ValueError(f"section sampled norm is unusable for a nonzero field: {norm!r}")
    return norm


def _plane_intensity(field: ComplexField) -> np.ndarray:
    """Derive raw intensity only after retaining a complete complex section."""
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            image = field.intensity
    except FloatingPointError as exc:
        raise ValueError("section intensity overflow or invalid arithmetic") from exc
    if not np.all(np.isfinite(image)):
        raise ValueError("section intensity must remain finite")
    return image


def _section_field(position: WaveFieldPosition, canonical: SequentialResult,
                   anchors: dict[str, ComplexField]) -> ComplexField:
    if position.stage == "observation":
        return canonical.observation
    if position.stage in anchors:
        return anchors[position.stage]
    upstream = anchors[position.anchor_selector]
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            return propagate_angular_spectrum(upstream, distance_m=position.separation_m, pad_factor=1)
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError(f"unusable section propagation at {position.id!r}, interval {position.separation_m!r} m") from exc


def sample_wave_field(experiment: SequentialExperiment, *,
                      interior_z_m: tuple[float, ...]) -> WaveFieldResult:
    """Calculate at most 25 sections using one unchanged canonical V0 run.

    Absolute section positions and all experiment lengths are metres. Three
    captures are source, after-aperture, after-lens. The two before-side fields
    use their exact V0 interval; the terminal is never repropagated/replaced.
    """
    positions = validate_sampling(experiment, interior_z_m)
    plan = section_plan(experiment, interior_z_m=positions)
    aperture, lens = experiment.components
    selectors = ("source", f"after:{aperture.id}", f"after:{lens.id}")
    original_spec = experiment.to_dict()
    canonical = run_experiment(experiment, record_fields=selectors)
    if canonical.experiment is not experiment:
        raise ValueError("V0 result is not associated with the identical captured experiment")
    anchors = {selector: canonical.field_at(selector) for selector in selectors}
    terminal = canonical.observation
    original_bytes = {selector: field.data.tobytes(order="C") for selector, field in anchors.items()}
    original_bytes["observation"] = terminal.data.tobytes(order="C")
    stage_records = {record.selector: record for record in canonical.stages}
    images = np.empty((len(plan), *experiment.grid.shape), dtype=np.float64)
    rows: list[WaveFieldPlane] = []
    for index, position in enumerate(plan):
        field = _section_field(position, canonical, anchors)
        norm = _sampled_norm(field)
        images[index] = _plane_intensity(field)
        if position.stage == "interior":
            record = StageRecord(selector="observation", z_m=position.z_m, norm=norm,
                                 previous_norm=stage_records[position.anchor_selector].norm)
            comparison = "upstream_anchor"
        else:
            record = stage_records[position.stage]
            if norm != record.norm:
                raise ValueError(f"section {position.id!r} field disagrees with its canonical V0 event norm")
            comparison = "previous_stage"
        rows.append(WaveFieldPlane(**position.__dict__, norm=record.norm,
                                  previous_norm=record.previous_norm, delta_norm=record.delta_norm,
                                  transmission_ratio=record.transmission_ratio, comparison=comparison,
                                  on_axis_intensity=float(images[index, experiment.grid.ny//2, experiment.grid.nx//2]),
                                  max_intensity=float(np.max(images[index]))))
        del field
    if (canonical.observation is not terminal
            or terminal.data.tobytes(order="C") != original_bytes["observation"]):
        raise ValueError("authoritative V0 terminal field was replaced or mutated")
    if experiment.to_dict() != original_spec or any(
            anchors[selector].data.tobytes(order="C") != original_bytes[selector] for selector in selectors):
        raise ValueError("captured experiment or source/element anchor was mutated")
    return WaveFieldResult(experiment=experiment, interior_z_m=positions, canonical=canonical,
                           planes=tuple(rows), intensities=images,
                           x_m=experiment.grid.x, y_m=experiment.grid.y)
