"""Sampling-only public V0 source adapter and unchanged public V2a execution.

Scientific distances use metres and signed phase radians. Validation allocates
no scientific fields and runs no sampler/solver. No optical formulas live here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ohlab.optics import SequentialExperiment, sample_source
from ohlab.optics.interference import TwoArmResult, TwoArmSpec, run_two_arm

from .adapter import NumericalError
from .protocol import validate_request_id
from .two_path_protocol import (MAX_AXIS, MAX_SWEEP_AXIS, PHASES_RAD, PROTOCOL_VERSION,
                                SweepReply, encode_result, encode_sweep_reply,
                                experiment_digest, row_from_result, sweep_digest)


def _keys(value: object, expected: set[str], name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{name}: expected JSON object")
    if set(value) != expected:
        raise ValueError(f"{name}: expected exactly {sorted(expected)}")
    return value


def _source_plane(value: dict[str, object], *, axis_cap: int) -> SequentialExperiment:
    grid = _keys(value["grid"], {"ny", "nx", "dy", "dx"}, "grid")
    for axis in ("ny", "nx"):
        if type(grid[axis]) is not int:
            raise TypeError(f"grid.{axis}: expected integer excluding bool")
        if not 1 <= grid[axis] <= axis_cap:
            raise ValueError(f"grid.{axis}: expected 1..{axis_cap}, got {grid[axis]}")
    # The existing public parser validates source/grid arithmetic and owns the
    # immutable source records. This wrapper is sampling-only, never a train run.
    return SequentialExperiment.from_dict({
        "schema_version": 1, "model_contract": "v0_aligned_scalar_forward_v1",
        "wavelength_m": value["wavelength_m"], "grid": grid, "source": value["source"],
        "components": [], "observation": {"id": "source_plane", "z_m": 0.0},
    })


def _source_dict(source_plane: SequentialExperiment) -> dict[str, object]:
    scientific = source_plane.to_dict()
    return {name: scientific[name] for name in ("wavelength_m", "grid", "source")}


@dataclass(frozen=True, kw_only=True)
class TwoPathExperiment:
    """Owned validated source-plane wrapper and public finite two-arm SI spec."""

    source_plane: SequentialExperiment
    spec: TwoArmSpec

    def __post_init__(self) -> None:
        if not isinstance(self.source_plane, SequentialExperiment):
            raise TypeError("source_plane: expected SequentialExperiment")
        if self.source_plane.components or self.source_plane.observation.z_m != 0.0:
            raise ValueError("source_plane: sampling-only empty train at z=0 required")
        if not isinstance(self.spec, TwoArmSpec):
            raise TypeError("spec: expected TwoArmSpec")
        checked_source = _source_plane(_source_dict(self.source_plane), axis_cap=MAX_AXIS)
        checked_spec = TwoArmSpec(arm_0_distance_m=self.spec.arm_0_distance_m,
                                  arm_1_distance_m=self.spec.arm_1_distance_m,
                                  relative_phase_rad=self.spec.relative_phase_rad)
        object.__setattr__(self, "source_plane", checked_source)
        object.__setattr__(self, "spec", checked_spec)

    def to_dict(self) -> dict[str, object]:
        return {**_source_dict(self.source_plane), "two_arm_spec": {
            "arm_0_distance_m": self.spec.arm_0_distance_m,
            "arm_1_distance_m": self.spec.arm_1_distance_m,
            "relative_phase_rad": self.spec.relative_phase_rad}}


@dataclass(frozen=True, kw_only=True)
class ValidatedTwoPathSubmission:
    request_id: str
    experiment: TwoPathExperiment
    experiment_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        validate_request_id(self.request_id)
        if not isinstance(self.experiment, TwoPathExperiment):
            raise TypeError("experiment: expected TwoPathExperiment")
        object.__setattr__(self, "experiment_sha256", experiment_digest(self.experiment.to_dict()))


@dataclass(frozen=True, kw_only=True)
class ValidatedSweepSubmission:
    request_id: str
    source_plane: SequentialExperiment
    arm_0_distance_m: float
    arm_1_distance_m: float
    phases_rad: tuple[float, ...]
    fixed_experiment_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        validate_request_id(self.request_id)
        if not isinstance(self.source_plane, SequentialExperiment):
            raise TypeError("source_plane: expected SequentialExperiment")
        if self.source_plane.components or self.source_plane.observation.z_m != 0.0:
            raise ValueError("source_plane: sampling-only empty train at z=0 required")
        if not isinstance(self.phases_rad, tuple) or len(self.phases_rad) != 17:
            raise ValueError("phases_rad: expected immutable 17 phase tuple")
        specs = tuple(TwoArmSpec(arm_0_distance_m=self.arm_0_distance_m,
                                arm_1_distance_m=self.arm_1_distance_m,
                                relative_phase_rad=phase) for phase in self.phases_rad)
        if tuple(spec.relative_phase_rad for spec in specs) != PHASES_RAD:
            raise ValueError("phases_rad: expected exact predeclared phases")
        object.__setattr__(self, "source_plane", _source_plane(_source_dict(self.source_plane), axis_cap=MAX_SWEEP_AXIS))
        object.__setattr__(self, "arm_0_distance_m", specs[0].arm_0_distance_m)
        object.__setattr__(self, "arm_1_distance_m", specs[0].arm_1_distance_m)
        object.__setattr__(self, "phases_rad", tuple(spec.relative_phase_rad for spec in specs))
        object.__setattr__(self, "fixed_experiment_sha256",
                           sweep_digest(self.to_dict(), self.phases_rad))

    def to_dict(self) -> dict[str, object]:
        return {**_source_dict(self.source_plane),
                "arm_0_distance_m": self.arm_0_distance_m,
                "arm_1_distance_m": self.arm_1_distance_m}


def _envelope(payload: object, *, sweep: bool = False) -> dict[str, object]:
    names = {"protocol_version", "message_type", "request_id"}
    names |= {"fixed_experiment", "phases_rad"} if sweep else {"experiment"}
    value = _keys(payload, names, "submission")
    if type(value["protocol_version"]) is not int or value["protocol_version"] != PROTOCOL_VERSION:
        raise ValueError("submission: unsupported V2b protocol_version")
    expected = "two_path_sweep_submission" if sweep else "two_path_submission"
    if value["message_type"] != expected:
        raise ValueError(f"submission: expected message_type {expected}")
    validate_request_id(value["request_id"])
    return value


def validate_submission(payload: object) -> ValidatedTwoPathSubmission:
    """Validate SI public source and arm domains without numerical execution."""
    value = _envelope(payload)
    scientific = _keys(value["experiment"], {"wavelength_m", "grid", "source", "two_arm_spec"}, "experiment")
    arms = _keys(scientific["two_arm_spec"],
                 {"arm_0_distance_m", "arm_1_distance_m", "relative_phase_rad"}, "two_arm_spec")
    source_plane = _source_plane(scientific, axis_cap=MAX_AXIS)
    experiment = TwoPathExperiment(source_plane=source_plane, spec=TwoArmSpec(**arms))
    return ValidatedTwoPathSubmission(request_id=value["request_id"], experiment=experiment)


def validate_sweep_submission(payload: object) -> ValidatedSweepSubmission:
    """Validate the fixed source/distances and exact 17 requested literal phases."""
    value = _envelope(payload, sweep=True)
    scientific = _keys(value["fixed_experiment"],
                       {"wavelength_m", "grid", "source", "arm_0_distance_m", "arm_1_distance_m"},
                       "fixed_experiment")
    phases = value["phases_rad"]
    if not isinstance(phases, list) or len(phases) != 17:
        raise ValueError("phases_rad: expected the 17 predeclared phases")
    # Public scalar constructors supply finite/type checks, including bool rejection.
    specs = tuple(TwoArmSpec(arm_0_distance_m=scientific["arm_0_distance_m"],
                            arm_1_distance_m=scientific["arm_1_distance_m"],
                            relative_phase_rad=phase) for phase in phases)
    actual_phases = tuple(spec.relative_phase_rad for spec in specs)
    if actual_phases != PHASES_RAD:
        raise ValueError("phases_rad: expected the exact 17 predeclared literal phases")
    source_plane = _source_plane(scientific, axis_cap=MAX_SWEEP_AXIS)
    return ValidatedSweepSubmission(request_id=value["request_id"], source_plane=source_plane,
                                    arm_0_distance_m=specs[0].arm_0_distance_m,
                                    arm_1_distance_m=specs[0].arm_1_distance_m,
                                    phases_rad=actual_phases)


def _check_result(result: TwoArmResult, source_plane: SequentialExperiment, spec: TwoArmSpec) -> None:
    if not isinstance(result, TwoArmResult) or result.spec != spec:
        raise ValueError("solver result does not match submitted two-arm spec")
    if any(output.grid != source_plane.grid or output.wavelength_m != source_plane.wavelength_m
           for output in result.outputs):
        raise ValueError("solver outputs do not match submitted common grid/wavelength")


def simulate_submission(submission: ValidatedTwoPathSubmission) -> bytes:
    """Sample public V0 once; run public V2a exactly once; encode actual outputs."""
    if not isinstance(submission, ValidatedTwoPathSubmission):
        raise TypeError("submission: expected ValidatedTwoPathSubmission")
    experiment = submission.experiment
    try:
        incident = sample_source(experiment.source_plane)
        result = run_two_arm(incident, spec=experiment.spec)
    except (ValueError, FloatingPointError, OverflowError) as exc:
        raise NumericalError(str(exc)) from exc
    _check_result(result, experiment.source_plane, experiment.spec)
    return encode_result(submission.request_id, experiment.to_dict(), result)


def sweep_submission(submission: ValidatedSweepSubmission) -> SweepReply:
    """Run each actual requested phase; retain scalar rows only and stop on failure.

    HTTP cancellation cannot terminate a running worker. This bounded operation
    remains responsible for its gate until numerical work and encoding finish.
    """
    if not isinstance(submission, ValidatedSweepSubmission):
        raise TypeError("submission: expected ValidatedSweepSubmission")
    rows: list[dict[str, object]] = []
    index = 0
    try:
        incident = sample_source(submission.source_plane)
        for index, phase_rad in enumerate(submission.phases_rad):
            spec = TwoArmSpec(arm_0_distance_m=submission.arm_0_distance_m,
                              arm_1_distance_m=submission.arm_1_distance_m,
                              relative_phase_rad=phase_rad)
            result = run_two_arm(incident, spec=spec)
            _check_result(result, submission.source_plane, spec)
            rows.append(row_from_result(index, phase_rad, result))
            del result
    except (ValueError, FloatingPointError, OverflowError) as exc:
        return encode_sweep_reply(submission.request_id, submission.to_dict(), submission.phases_rad,
                                  rows, failed_index=index,
                                  error={"code": "numerical_failure", "message": str(exc)[:300] or "Numerical failure"},
                                  status_code=422)
    except Exception:
        return encode_sweep_reply(submission.request_id, submission.to_dict(), submission.phases_rad,
                                  rows, failed_index=index,
                                  error={"code": "sweep_failed", "message": "Unexpected internal sweep failure"},
                                  status_code=500)
    return encode_sweep_reply(submission.request_id, submission.to_dict(), submission.phases_rad, rows)
