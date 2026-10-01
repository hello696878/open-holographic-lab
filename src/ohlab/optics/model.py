"""Immutable SI specifications for the V0 aligned scalar forward train.

The exact schema and arithmetic contract are normative in
``docs/math_conventions.md`` section 3.17. This module performs no file I/O.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
import re
from typing import ClassVar, TypeAlias

import numpy as np

from ..grid import SamplingGrid

__all__ = ["GaussianSource", "UniformSource", "CircularAperture",
           "RectangularAperture", "ThinLens", "ObservationPlane", "Component",
           "SequentialExperiment"]

_MODEL_CONTRACT = "v0_aligned_scalar_forward_v1"
_EXPERIMENT_KEYS = {"schema_version", "model_contract", "wavelength_m", "grid",
                    "source", "components", "observation"}


def _require_real(value: object, name: str) -> float:
    """Accept finite binary64 real scalars, excluding booleans and arrays."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(
            value, (int, float, np.integer, np.floating)):
        raise TypeError(f"{name}: expected finite real scalar excluding bool, got {type(value).__name__}")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name}: expected finite binary64, value is not representable") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name}: expected finite binary64, got {result!r}")
    return result


def _require_integer(value: object, name: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name}: expected integer excluding bool, got {type(value).__name__}")
    return int(value)


def _real_attribute(record: object, name: str, *, positive: bool = False,
                    nonnegative: bool = False, nonzero: bool = False) -> None:
    value = _require_real(getattr(record, name), name)
    if (positive and value <= 0) or (nonnegative and value < 0) or (nonzero and value == 0):
        domain = "positive" if positive else "nonnegative" if nonnegative else "nonzero"
        raise ValueError(f"{name}: expected finite {domain} value, got {value!r}")
    object.__setattr__(record, name, value)


def _identifier(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"id: expected ASCII string, got {type(value).__name__}")
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", value, flags=re.ASCII) is None or value == "source":
        raise ValueError(f"id: expected ASCII [A-Za-z][A-Za-z0-9_-]{{0,63}}, excluding reserved 'source', got {value!r}")
    return str(value)


def _derived(value: float, name: str, *, positive: bool = False,
             nonzero: bool = False) -> float:
    if not math.isfinite(value) or (positive and value <= 0) or (nonzero and value == 0):
        raise ValueError(f"{name}: unusable binary64 derived geometry, got {value!r}")
    return value


@dataclass(frozen=True, kw_only=True)
class UniformSource:
    """Uniform sampled illumination; amplitude in field units, phase in rad."""

    amplitude: float
    phase_rad: float
    kind: ClassVar[str] = "uniform"

    def __post_init__(self) -> None:
        _real_attribute(self, "amplitude", nonnegative=True)
        _real_attribute(self, "phase_rad")


@dataclass(frozen=True, kw_only=True)
class GaussianSource:
    """Paraxial source, with waist peak amplitude and 1/e amplitude radius.

    All positions/radii are metres; phase_rad is the on-axis waist phase.
    The field is sampled at z=0, potentially before or after the waist.
    """

    amplitude: float
    phase_rad: float
    waist_radius_m: float
    waist_z_m: float
    center_x_m: float
    center_y_m: float
    kind: ClassVar[str] = "gaussian"

    def __post_init__(self) -> None:
        _real_attribute(self, "amplitude", nonnegative=True)
        _real_attribute(self, "waist_radius_m", positive=True)
        for name in ("phase_rad", "waist_z_m", "center_x_m", "center_y_m"):
            _real_attribute(self, name)
        _derived(self.waist_radius_m * self.waist_radius_m, "waist_radius_m squared", positive=True)


@dataclass(frozen=True, kw_only=True)
class CircularAperture:
    """Centered inclusive 0/1 amplitude aperture; z and radius in metres."""

    id: str
    z_m: float
    radius_m: float
    kind: ClassVar[str] = "circular_aperture"

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _identifier(self.id))
        _real_attribute(self, "z_m", nonnegative=True)
        _real_attribute(self, "radius_m", positive=True)
        _derived(self.radius_m * self.radius_m, "radius_m squared", positive=True)


@dataclass(frozen=True, kw_only=True)
class RectangularAperture:
    """Centered inclusive rectangular aperture, including finite-height slits.

    The longitudinal position, full width and full height are in metres.
    """

    id: str
    z_m: float
    width_m: float
    height_m: float
    kind: ClassVar[str] = "rectangular_aperture"

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _identifier(self.id))
        _real_attribute(self, "z_m", nonnegative=True)
        for name in ("width_m", "height_m"):
            _real_attribute(self, name, positive=True)
            _derived(getattr(self, name) / 2, f"{name} half-size", positive=True)


@dataclass(frozen=True, kw_only=True)
class ThinLens:
    """Centered ideal paraxial lens with signed nonzero focal length in m."""

    id: str
    z_m: float
    focal_length_m: float
    kind: ClassVar[str] = "thin_lens"

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _identifier(self.id))
        _real_attribute(self, "z_m", nonnegative=True)
        _real_attribute(self, "focal_length_m", nonzero=True)


@dataclass(frozen=True, kw_only=True)
class ObservationPlane:
    """Terminal ideal observation plane; longitudinal position z_m in m."""

    id: str
    z_m: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _identifier(self.id))
        _real_attribute(self, "z_m", nonnegative=True)


Component: TypeAlias = CircularAperture | RectangularAperture | ThinLens
Source: TypeAlias = GaussianSource | UniformSource
_COMPONENT_TYPES = (CircularAperture, RectangularAperture, ThinLens)


def _validate_grid(grid: SamplingGrid, wavelength_m: float) -> None:
    """Check V0 resource bounds and usable complete-grid/M1 geometry."""
    if not isinstance(grid, SamplingGrid):
        raise TypeError(f"grid: expected SamplingGrid, got {type(grid).__name__}")
    lam = _require_real(wavelength_m, "wavelength_m")
    if lam <= 0:
        raise ValueError(f"wavelength_m: expected positive, got {lam!r}")
    k = _derived(2 * math.pi / lam, "wavenumber", positive=True)
    _derived(k * k, "wavenumber squared", positive=True)
    cutoff = _derived(1 / lam, "propagating frequency cutoff", positive=True)
    _derived(cutoff * cutoff, "propagating frequency cutoff squared", positive=True)
    for name in ("ny", "nx"):
        count = _require_integer(getattr(grid, name), f"grid.{name}")
        if not 1 <= count <= 2048:
            raise ValueError(f"grid.{name}: expected 1..2048, got {count}")
    for name in ("dy", "dx"):
        pitch = _require_real(getattr(grid, name), f"grid.{name}")
        if pitch <= 0:
            raise ValueError(f"grid.{name}: expected positive, got {pitch!r}")
    _derived(grid.dx * grid.dy, "grid pixel area", positive=True)
    squared_coordinates = []
    squared_frequencies = []
    for count, pitch, name in ((grid.nx, grid.dx, "x"), (grid.ny, grid.dy, "y")):
        extent = _derived(count * pitch, f"grid {name} extent", positive=True)
        inverse_extent = _derived(1 / extent, f"grid {name} reciprocal extent", positive=True)
        coordinate = _derived((count // 2) * pitch, f"grid {name} coordinate")
        squared_coordinates.append(_derived(coordinate * coordinate, f"grid {name} coordinate squared"))
        frequency = _derived(2 * math.pi * (count // 2) * inverse_extent, f"grid {name} angular frequency")
        squared_frequencies.append(_derived(frequency * frequency, f"grid {name} angular frequency squared"))
    _derived(sum(squared_coordinates), "grid radial coordinate squared")
    _derived(sum(squared_frequencies), "grid transverse angular frequency squared")


def _radial_bound(grid: SamplingGrid, center_x_m: float = 0,
                  center_y_m: float = 0) -> float:
    maximum_x = max(abs(-(grid.nx // 2) * grid.dx - center_x_m),
                    abs((grid.nx - 1 - grid.nx // 2) * grid.dx - center_x_m))
    maximum_y = max(abs(-(grid.ny // 2) * grid.dy - center_y_m),
                    abs((grid.ny - 1 - grid.ny // 2) * grid.dy - center_y_m))
    return _derived(maximum_x * maximum_x + maximum_y * maximum_y,
                    "maximum shifted radial coordinate squared")


def _validate_source_geometry(source: Source, grid: SamplingGrid,
                              wavelength_m: float) -> None:
    if type(source) not in (GaussianSource, UniformSource):
        raise TypeError(f"source: expected GaussianSource or UniformSource, got {type(source).__name__}")
    if isinstance(source, UniformSource):
        return
    waist2 = _derived(source.waist_radius_m * source.waist_radius_m,
                      "Gaussian waist squared", positive=True)
    rayleigh = _derived(math.pi * waist2 / wavelength_m, "Gaussian Rayleigh range", positive=True)
    s = -source.waist_z_m
    ratio = _derived(s / rayleigh, "Gaussian s/zR", nonzero=s != 0)
    _derived(waist2 * ratio, "Gaussian complex denominator imaginary part", nonzero=ratio != 0)
    prefactor = source.amplitude / complex(1, ratio)
    if source.amplitude > 0 and prefactor == 0:
        raise ValueError(f"Gaussian amplitude prefactor: unusable binary64 derived geometry; nonzero amplitude {source.amplitude!r} with s/zR={ratio!r} underflowed before tail decay")
    radial2 = _radial_bound(grid, source.center_x_m, source.center_y_m)
    # The unattenuated radial quotient bounds both complex exponent parts.
    _derived(radial2 / waist2, "Gaussian radial exponent scale")
    _derived((2 * math.pi / wavelength_m) * s + source.phase_rad, "Gaussian carrier phase")


def _validate_component_geometry(component: Component, grid: SamplingGrid,
                                 wavelength_m: float) -> None:
    if type(component) not in _COMPONENT_TYPES:
        raise TypeError(f"component: expected supported V0 component, got {type(component).__name__}")
    if isinstance(component, ThinLens):
        denominator = _derived(2 * component.focal_length_m, "lens 2*f", nonzero=True)
        coefficient = _derived(-(2 * math.pi / wavelength_m) / denominator,
                               "lens phase coefficient", nonzero=True)
        _derived(coefficient * _radial_bound(grid), "lens maximum phase")


def _keys(value: object, expected: set[str], name: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name}: expected Mapping, got {type(value).__name__}")
    if any(not isinstance(key, str) for key in value):
        raise TypeError(f"{name}: expected string keys")
    actual = set(value)
    if actual != expected:
        raise ValueError(f"{name}: missing {sorted(expected - actual)}, unknown {sorted(actual - expected)}")
    return dict(value)


def _tagged(value: object, types: dict[str, type], name: str) -> object:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name}: expected Mapping, got {type(value).__name__}")
    if "kind" not in value:
        raise ValueError(f"{name}: missing kind tag")
    kind = value["kind"]
    if not isinstance(kind, str):
        raise TypeError(f"{name}.kind: expected str, got {type(kind).__name__}")
    if kind not in types:
        raise ValueError(f"{name}.kind: unsupported {kind!r}; expected {sorted(types)}")
    record_type = types[kind]
    parameters = _keys(value, set(record_type.__dataclass_fields__), name)
    parameters.pop("kind")
    return record_type(**parameters)


def _record_dict(record: object) -> dict[str, object]:
    return {name: getattr(record, name) for name in record.__dataclass_fields__}


@dataclass(frozen=True, kw_only=True)
class SequentialExperiment:
    """Versioned aligned scalar forward experiment with one grid.

    wavelength_m and absolute longitudinal positions are metres. Components
    are applied in stored order; colocated components are permitted. The source
    is at z=0, and the observation is downstream of the last component. Parsed
    containers are owned immutable records; no disk persistence is provided.
    """

    wavelength_m: float
    grid: SamplingGrid
    source: Source
    components: tuple[Component, ...]
    observation: ObservationPlane
    schema_version: int = 1
    model_contract: str = _MODEL_CONTRACT

    def __post_init__(self) -> None:
        version = _require_integer(self.schema_version, "schema_version")
        if version != 1:
            raise ValueError(f"schema_version: expected 1, got {version}")
        object.__setattr__(self, "schema_version", version)
        if not isinstance(self.model_contract, str):
            raise TypeError("model_contract: expected str")
        if self.model_contract != _MODEL_CONTRACT:
            raise ValueError(f"model_contract: expected {_MODEL_CONTRACT!r}, got {self.model_contract!r}")
        _real_attribute(self, "wavelength_m", positive=True)
        _validate_grid(self.grid, self.wavelength_m)
        _validate_source_geometry(self.source, self.grid, self.wavelength_m)
        if not isinstance(self.components, (list, tuple)):
            raise TypeError(f"components: expected list or tuple of records, got {type(self.components).__name__}")
        if len(self.components) > 16:
            raise ValueError(f"components: expected at most 16, got {len(self.components)}")
        components = tuple(self.components)
        if type(self.observation) is not ObservationPlane:
            raise TypeError(f"observation: expected ObservationPlane, got {type(self.observation).__name__}")
        identifiers = {self.observation.id}
        previous_z = 0.0
        k = 2 * math.pi / self.wavelength_m
        for index, component in enumerate(components):
            _validate_component_geometry(component, self.grid, self.wavelength_m)
            if component.id in identifiers:
                raise ValueError(f"components[{index}].id: duplicate identifier {component.id!r}")
            identifiers.add(component.id)
            if component.z_m < previous_z:
                raise ValueError(f"components[{index}].z_m: expected >= previous {previous_z!r} m, got {component.z_m!r}")
            _derived(k * (component.z_m - previous_z), f"components[{index}] propagation phase")
            previous_z = component.z_m
        if self.observation.z_m < previous_z:
            raise ValueError(f"observation.z_m: expected >= last component {previous_z!r} m, got {self.observation.z_m!r}")
        _derived(k * (self.observation.z_m - previous_z), "terminal propagation phase")
        object.__setattr__(self, "components", components)

    @classmethod
    def from_dict(cls, mapping: Mapping[str, object]) -> SequentialExperiment:
        """Parse the exact schema from an owned copy, rejecting unknown keys."""
        spec = _keys(mapping, _EXPERIMENT_KEYS, "experiment")
        grid = _keys(spec["grid"], {"ny", "nx", "dy", "dx"}, "grid")
        # Validate before the existing grid constructor to retain V0's types.
        for key in ("ny", "nx"):
            grid[key] = _require_integer(grid[key], f"grid.{key}")
        for key in ("dy", "dx"):
            grid[key] = _require_real(grid[key], f"grid.{key}")
        source = _tagged(spec["source"], {"gaussian": GaussianSource, "uniform": UniformSource}, "source")
        if not isinstance(spec["components"], (list, tuple)):
            raise TypeError("components: expected list or tuple of component mappings")
        if len(spec["components"]) > 16:
            raise ValueError(f"components: expected at most 16, got {len(spec['components'])}")
        components = tuple(_tagged(value, {"circular_aperture": CircularAperture,
                                          "rectangular_aperture": RectangularAperture,
                                          "thin_lens": ThinLens}, f"components[{index}]")
                           for index, value in enumerate(spec["components"]))
        observation = ObservationPlane(**_keys(spec["observation"], {"id", "z_m"}, "observation"))
        return cls(wavelength_m=spec["wavelength_m"], grid=SamplingGrid(**grid),
                   source=source, components=components, observation=observation,
                   schema_version=spec["schema_version"], model_contract=spec["model_contract"])

    def to_dict(self) -> dict[str, object]:
        """Export fresh nested dictionaries/lists, with all SI scientific keys."""
        return {"schema_version": self.schema_version, "model_contract": self.model_contract,
                "wavelength_m": self.wavelength_m, "grid": self.grid.to_dict(),
                "source": _record_dict(self.source),
                "components": [_record_dict(component) for component in self.components],
                "observation": _record_dict(self.observation)}
