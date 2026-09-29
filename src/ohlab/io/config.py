"""Immutable schema-v1 scientific settings for an M5 run bundle.

This module performs no numerical computation or file access. Bundle metadata,
array capture, publication and replay belong to :mod:`ohlab.io.artifacts`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import math
import sys

__all__ = ["RunConfig"]

_TOP_KEYS = frozenset({"schema_version", "grid", "optics", "solver", "metrics"})
_METRIC_PARAMETERS = {
    "intensity_mse": frozenset(),
    "intensity_nmse": frozenset(),
    "intensity_psnr": frozenset({"data_range"}),
    "signal_region_power_fraction": frozenset({"mask"}),
    "regional_intensity_cv": frozenset({"mask"}),
}


def _json_bytes(value: object) -> bytes:
    """Encode deterministic UTF-8 JSON with sorted keys, LF and final newline."""
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")


def _parse_json(data: bytes, context: str) -> object:
    """Decode UTF-8 JSON, rejecting duplicate keys and nonstandard constants.

    A standard numeric token such as ``1e999`` may decode to infinity; callers
    must independently validate the resulting numeric domains against schema.
    """
    if type(data) is not bytes:
        raise TypeError(f"{context} must be UTF-8 bytes, got {type(data).__name__}")

    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key {key!r}")
            result[key] = value
        return result

    def constant(value: str) -> object:
        raise ValueError(f"nonstandard constant {value!r}")

    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=constant)
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise ValueError(f"{context} is invalid UTF-8 JSON: {exc}") from exc


def _mapping(value: object, name: str) -> dict[str, object]:
    """Copy one object level without retaining caller-owned mappings."""
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping, got {type(value).__name__}")
    result = dict(value)
    for key in result:
        if type(key) is not str:
            raise TypeError(f"{name} keys must be strings, got {key!r}")
    return result


def _keys(value: object, expected: frozenset[str] | set[str], name: str) -> dict[str, object]:
    """Require exactly the named keys, returning an owned shallow mapping."""
    result = _mapping(value, name)
    missing = expected - result.keys()
    unknown = result.keys() - expected
    if missing or unknown:
        raise ValueError(
            f"{name} keys mismatch: missing={sorted(missing)!r}, "
            f"unknown={sorted(unknown)!r}; expected {sorted(expected)!r}"
        )
    return result


def _integer(value: object, name: str, minimum: int, maximum: int | None = None) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be a built-in int, excluding bool; got {value!r}")
    if value < minimum or (maximum is not None and value > maximum):
        bound = f"[{minimum}, {maximum}]" if maximum is not None else f">= {minimum}"
        raise ValueError(f"{name} must be {bound}, got {value!r}")
    return value


def _real(value: object, name: str, *, positive: bool) -> float:
    if type(value) not in (int, float):
        raise TypeError(f"{name} must be a built-in int or float, excluding bool; got {value!r}")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be representable as a finite binary64 value") from exc
    if not math.isfinite(result) or (positive and result <= 0.0):
        domain = "finite and positive" if positive else "finite"
        raise ValueError(f"{name} must be {domain}, got {result!r}")
    return result


def _literal(value: object, expected: str, name: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be a string, got {type(value).__name__}")
    if value != expected:
        raise ValueError(f"{name} must be {expected!r}, got {value!r}")
    return value


def _validate(settings: Mapping[str, object]) -> dict[str, object]:
    specification = _keys(settings, _TOP_KEYS, "settings")
    version = _integer(specification["schema_version"], "schema_version", 1)
    if version != 1:
        raise ValueError(f"unsupported schema_version {version!r}; expected 1")

    grid = _keys(specification["grid"], {"ny", "nx", "dy_m", "dx_m"}, "grid")
    for key in ("ny", "nx"):
        grid[key] = _integer(grid[key], f"grid.{key}", 1, sys.maxsize)
    for key in ("dy_m", "dx_m"):
        grid[key] = _real(grid[key], f"grid.{key}", positive=True)

    optics = _keys(specification["optics"], {"wavelength_m", "distance_m"}, "optics")
    optics["wavelength_m"] = _real(optics["wavelength_m"], "optics.wavelength_m", positive=True)
    optics["distance_m"] = _real(optics["distance_m"], "optics.distance_m", positive=False)

    solver = _keys(specification["solver"],
                   {"algorithm", "contract", "iterations", "initialization"}, "solver")
    _literal(solver["algorithm"], "gerchberg_saxton", "solver.algorithm")
    _literal(solver["contract"], "m3_periodic_lossless_asm_v1", "solver.contract")
    solver["iterations"] = _integer(solver["iterations"], "solver.iterations", 0, sys.maxsize - 1)
    initialization = _mapping(solver["initialization"], "solver.initialization")
    if "mode" not in initialization:
        raise ValueError("solver.initialization is missing required key 'mode'")
    mode = initialization["mode"]
    if type(mode) is not str:
        raise TypeError(f"solver.initialization.mode must be a string, got {type(mode).__name__}")
    if mode == "seed":
        initialization = _keys(initialization, {"mode", "seed"}, "solver.initialization")
        initialization["seed"] = _integer(initialization["seed"], "solver.initialization.seed", 0)
    elif mode == "explicit_phase":
        initialization = _keys(initialization, {"mode", "artifact"}, "solver.initialization")
        _literal(initialization["artifact"], "initial_phase.npy", "solver.initialization.artifact")
    else:
        raise ValueError(f"solver.initialization.mode must be 'seed' or 'explicit_phase', got {mode!r}")
    solver["initialization"] = initialization

    metrics = _mapping(specification["metrics"], "metrics")
    unknown = metrics.keys() - _METRIC_PARAMETERS.keys()
    if unknown:
        raise ValueError(f"metrics contains unsupported names {sorted(unknown)!r}")
    for name, value in metrics.items():
        parameters = _keys(value, _METRIC_PARAMETERS[name], f"metrics.{name}")
        if name == "intensity_psnr":
            parameters["data_range"] = _real(parameters["data_range"], f"metrics.{name}.data_range", positive=True)
        elif name == "signal_region_power_fraction":
            _literal(parameters["mask"], "signal_mask.npy", f"metrics.{name}.mask")
        elif name == "regional_intensity_cv":
            _literal(parameters["mask"], "cv_mask.npy", f"metrics.{name}.mask")
        metrics[name] = parameters

    return {"schema_version": version, "grid": grid, "optics": optics,
            "solver": solver, "metrics": metrics}


@dataclass(frozen=True, slots=True, init=False)
class RunConfig:
    """An immutable, fully validated schema-v1 scientific specification.

    ``settings`` accepts nested mappings with exactly the documented schema
    keys. Scalars use built-in JSON-compatible Python types: integer fields
    require ``int`` excluding ``bool``; pitches, wavelength, distance and PSNR
    range accept ``int`` or ``float`` and are stored as finite binary64 floats.
    Pitches, wavelength and distance are in metres. Distance may have either
    sign, including either signed zero; pitches and wavelength are positive.
    PSNR ``data_range`` is a positive intensity value. Counts are positive grid
    dimensions and nonnegative iterations; dimensions must fit ``sys.maxsize``
    and iterations must leave space for the ``N+1`` history length. Seed is a
    nonnegative integer. No array allocation or derived optical-domain check
    is performed here; a structurally valid specification may fail M3 or M4
    validation when used with actual arrays.

    Only canonical immutable JSON bytes are retained. Caller mappings and
    dictionaries returned by :meth:`to_dict` can be changed without changing
    this instance. No nested mutable settings object is exposed. An empty
    metric mapping is valid. Bundle metadata and array artifacts are separate
    from this scientific specification.
    """

    _document: bytes

    def __init__(self, settings: Mapping[str, object]) -> None:
        object.__setattr__(self, "_document", _json_bytes(_validate(settings)))

    def to_dict(self) -> dict[str, object]:
        """Return a fresh deep dictionary of validated scientific settings."""
        return json.loads(self._document)
