"""Strict bounded W1 submissions around the public section sampler.

All inputs are SI. Validation is noncomputing; this layer contains no optical
formula and never changes the ordinary Sequential limits or experiment.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ohlab.optics import SequentialExperiment
from ohlab.optics.wave_field import sample_wave_field, validate_sampling

from .adapter import NumericalError, validate_experiment
from .protocol import experiment_digest, validate_request_id
from .wave_field_protocol import MAX_AXIS, MAX_INTERIORS, encode_result


def _cheap_limits(spec: object) -> None:
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
            raise ValueError(f"W1 grid.{axis}: expected 1..{MAX_AXIS}, got {count}; ordinary Sequential limits are unchanged")
    source, components = spec.get("source"), spec.get("components")
    if not isinstance(source, dict) or source.get("kind") != "gaussian":
        raise ValueError("W1 requires a Gaussian source")
    if not isinstance(components, list) or len(components) != 2:
        raise ValueError("W1 requires exactly one physical aperture followed by one ideal thin lens")
    if (not isinstance(components[0], dict) or components[0].get("kind") not in
            {"circular_aperture", "rectangular_aperture"} or
            not isinstance(components[1], dict) or components[1].get("kind") != "thin_lens"):
        raise ValueError("W1 requires stored order: physical aperture, ideal thin lens; elements are never reordered")


@dataclass(frozen=True, kw_only=True)
class ValidatedWaveFieldSubmission:
    """Owned immutable experiment and exact explicit metre sampling positions."""

    request_id: str
    experiment: SequentialExperiment
    interior_z_m: tuple[float, ...]
    experiment_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        validate_request_id(self.request_id)
        if not isinstance(self.experiment, SequentialExperiment):
            raise TypeError("experiment: expected SequentialExperiment")
        _cheap_limits(self.experiment.to_dict())
        object.__setattr__(self, "interior_z_m", validate_sampling(self.experiment, self.interior_z_m))
        object.__setattr__(self, "experiment_sha256", experiment_digest(self.experiment))


def validate_submission(payload: object) -> ValidatedWaveFieldSubmission:
    """Validate the route-discriminated exact W1 envelope without propagation."""
    if not isinstance(payload, dict):
        raise TypeError("submission: expected JSON object")
    if set(payload) != {"request_id", "experiment", "sampling"}:
        raise ValueError("W1 submission: expected exactly request_id, experiment and sampling")
    request_id = validate_request_id(payload["request_id"])
    _cheap_limits(payload["experiment"])
    sampling = payload["sampling"]
    if not isinstance(sampling, dict) or set(sampling) != {"interior_z_m"}:
        raise ValueError("sampling: expected exactly interior_z_m")
    values = sampling["interior_z_m"]
    if not isinstance(values, list):
        raise TypeError("sampling.interior_z_m: expected JSON array")
    if len(values) > MAX_INTERIORS:
        raise ValueError(f"sampling.interior_z_m: expected at most {MAX_INTERIORS} explicit positions")
    experiment = validate_experiment(payload["experiment"])
    return ValidatedWaveFieldSubmission(request_id=request_id, experiment=experiment,
                                        interior_z_m=tuple(values))


def simulate_submission(submission: ValidatedWaveFieldSubmission) -> bytes:
    """Sample once through the public W1 orchestrator, then encode within gate."""
    if not isinstance(submission, ValidatedWaveFieldSubmission):
        raise TypeError("submission: expected ValidatedWaveFieldSubmission")
    try:
        result = sample_wave_field(submission.experiment, interior_z_m=submission.interior_z_m)
    except (ValueError, FloatingPointError, OverflowError) as exc:
        raise NumericalError(str(exc)) from exc
    if result.experiment != submission.experiment or result.interior_z_m != submission.interior_z_m:
        raise ValueError("sampler result disagrees with immutable submitted experiment or sampling")
    return encode_result(submission.request_id, result)
