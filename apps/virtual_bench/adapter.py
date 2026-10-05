"""Strict application limits around the unchanged public V0 solver.

All physical values use SI. This module contains no optical formulas, I/O,
plotting, or browser code. Validation never runs the numerical solver.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math

from ohlab.optics import SequentialExperiment, run_experiment

from .protocol import (MAX_AXIS, MAX_BODY_BYTES, MAX_COMPONENTS, encode_result,
                       experiment_digest, validate_request_id)


class NumericalError(ValueError):
    """A validated experiment has unusable numerical arithmetic in public V0."""


def strict_json_loads(data: bytes) -> object:
    """Parse bounded strict UTF-8 JSON, rejecting duplicate keys and constants."""
    if not isinstance(data, bytes):
        raise TypeError("JSON body must be bytes")
    if len(data) > MAX_BODY_BYTES:
        raise ValueError("JSON body exceeds V1 byte limit")

    def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON object key")
            result[key] = value
        return result

    def invalid_constant(value: str) -> object:
        raise ValueError("nonfinite JSON constants are forbidden")

    def finite_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("JSON number exceeds finite binary64")
        return parsed

    try:
        text = data.decode("utf-8", errors="strict")
        return json.loads(text, object_pairs_hook=object_pairs,
                          parse_constant=invalid_constant, parse_float=finite_float)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("expected bounded strict UTF-8 JSON") from exc


def _cheap_limits(spec: object) -> None:
    """Check types/counts before V0 construction or scientific array work."""
    if not isinstance(spec, dict):
        raise TypeError("experiment: expected JSON object")
    grid = spec.get("grid")
    if not isinstance(grid, dict):
        raise TypeError("grid: expected JSON object")
    for axis in ("ny", "nx"):
        count = grid.get(axis)
        if type(count) is not int:
            raise TypeError(f"grid.{axis}: expected integer excluding bool")
        if not 1 <= count <= MAX_AXIS:
            raise ValueError(f"grid.{axis}: expected 1..{MAX_AXIS}, got {count}")
    components = spec.get("components")
    if not isinstance(components, list):
        raise TypeError("components: expected JSON array")
    if len(components) > MAX_COMPONENTS:
        raise ValueError(f"components: expected at most {MAX_COMPONENTS}, got {len(components)}")


@dataclass(frozen=True, kw_only=True)
class ValidatedSubmission:
    """Immutable request identity and owned V0 SI records; no mutable JSON alias."""

    request_id: str
    experiment: SequentialExperiment
    experiment_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        validate_request_id(self.request_id)
        if not isinstance(self.experiment, SequentialExperiment):
            raise TypeError("experiment: expected SequentialExperiment")
        _cheap_limits(self.experiment.to_dict())
        object.__setattr__(self, "experiment_sha256", experiment_digest(self.experiment))


def validate_submission(payload: object) -> ValidatedSubmission:
    """Validate exact JSON envelope and SI V0 domain without invoking a solver."""
    if not isinstance(payload, dict):
        raise TypeError("submission: expected JSON object")
    if set(payload) != {"request_id", "experiment"}:
        raise ValueError("submission: expected exactly request_id and experiment")
    request_id = validate_request_id(payload["request_id"])
    _cheap_limits(payload["experiment"])
    experiment = SequentialExperiment.from_dict(payload["experiment"])
    return ValidatedSubmission(request_id=request_id, experiment=experiment)


def simulate_submission(submission: ValidatedSubmission) -> bytes:
    """Run V0 once without recorded intermediates and encode its actual result."""
    if not isinstance(submission, ValidatedSubmission):
        raise TypeError("submission: expected ValidatedSubmission")
    try:
        result = run_experiment(submission.experiment, record_fields=())
    except (ValueError, FloatingPointError, OverflowError) as exc:
        raise NumericalError(str(exc)) from exc
    if result.experiment != submission.experiment:
        raise ValueError("solver result does not match immutable submitted experiment")
    return encode_result(submission.request_id, result)
