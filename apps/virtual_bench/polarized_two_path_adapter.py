"""Public-only V2f/V2c orchestration for the bounded interactive fourth mode.

SI settings are validated without sampling. Numerical measurement and later
encoding are separate failure boundaries; enabled analysis is always atomic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import re

from ohlab.optics import SequentialExperiment, sample_source
from ohlab.optics.polarization import JonesField, apply_linear_polarizer, transmission_ratio
from ohlab.optics.polarized_interference import (
    PolarizerAction, RetarderAction, PolarizationArm, PolarizedTwoArmSpec,
    PolarizedTwoArmResult, run_polarized_two_arm,
)

from .adapter import NumericalError
from .polarized_two_path_protocol import (
    DIAGNOSTIC_KEYS, MAX_ACTIONS, MAX_AXIS, MODEL_CONTRACT, NORM_PAIRS, PHASES_RAD,
    SweepReply, encode_result, encode_sweep_reply, experiment_digest, sweep_digest,
    validate_request_id,
)

_RESERVED_IDS = {"input", "splitter", "combiner", "arm_0", "arm_1", "port_0", "port_1", "analyzer"}


def _keys(value: object, names: set[str], context: str) -> dict[str, object]:
    if type(value) is not dict:
        raise TypeError(f"{context}: expected JSON object")
    if set(value) != names:
        raise ValueError(f"{context}: expected exactly {sorted(names)}")
    return value.copy()


def _real(value: object, context: str) -> float:
    if type(value) not in (int, float):
        raise TypeError(f"{context}: expected finite real excluding bool")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{context}: expected representable finite binary64") from exc
    if not math.isfinite(result) or (value != 0 and result == 0):
        raise ValueError(f"{context}: expected usable finite binary64")
    return 0.0 if result == 0 else result


def _complex(value: object, context: str) -> complex:
    parts = _keys(value, {"re", "im"}, context)
    return complex(_real(parts["re"], f"{context}.re"), _real(parts["im"], f"{context}.im"))


def _complex_dict(value: complex) -> dict[str, float]:
    return {"re": 0.0 if value.real == 0 else value.real,
            "im": 0.0 if value.imag == 0 else value.imag}


@dataclass(frozen=True, kw_only=True)
class PolarizedTwoPathAction:
    """Stable application identity and one terminal action, angles in radians."""

    id: str
    kind: str
    axis_angle_rad: float
    retardance_rad: float | None = None

    def __post_init__(self) -> None:
        if type(self.id) is not str:
            raise TypeError("action.id: expected ASCII identifier string")
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", self.id, flags=re.ASCII) is None or self.id in _RESERVED_IDS:
            raise ValueError("action.id: expected 1..32 ASCII identifier excluding reserved identities")
        if self.kind not in ("linear_polarizer", "linear_retarder"):
            raise ValueError("action.kind: expected linear_polarizer or linear_retarder")
        object.__setattr__(self, "axis_angle_rad", _real(self.axis_angle_rad, "action.axis_angle_rad"))
        if self.kind == "linear_retarder":
            object.__setattr__(self, "retardance_rad", _real(self.retardance_rad, "action.retardance_rad"))
        elif self.retardance_rad is not None:
            raise ValueError("polarizer.retardance_rad: expected None")
        self.public_action()

    def public_action(self) -> PolarizerAction | RetarderAction:
        """Map only declared parameters to the unchanged public action record."""
        if self.kind == "linear_polarizer":
            return PolarizerAction(axis_angle_rad=self.axis_angle_rad)
        return RetarderAction(axis_angle_rad=self.axis_angle_rad, retardance_rad=self.retardance_rad)

    def to_dict(self) -> dict[str, object]:
        result = {"id": self.id, "kind": self.kind, "axis_angle_rad": self.axis_angle_rad}
        if self.kind == "linear_retarder":
            result["retardance_rad"] = self.retardance_rad
        return result


@dataclass(frozen=True, kw_only=True)
class PolarizedTwoPathArm:
    """One forward distance in metres and zero-to-two ordered terminal actions."""

    distance_m: float
    actions: tuple[PolarizedTwoPathAction, ...]

    def __post_init__(self) -> None:
        distance = _real(self.distance_m, "arm.distance_m")
        if distance < 0:
            raise ValueError("arm.distance_m: expected nonnegative metres")
        if type(self.actions) is not tuple or len(self.actions) > MAX_ACTIONS:
            raise ValueError("arm.actions: expected immutable zero-to-two action tuple")
        if any(type(action) is not PolarizedTwoPathAction for action in self.actions):
            raise TypeError("arm.actions: expected PolarizedTwoPathAction records")
        object.__setattr__(self, "distance_m", distance)
        self.public_arm()

    def public_arm(self) -> PolarizationArm:
        """Construct the public arm while preserving every terminal action order."""
        return PolarizationArm(distance_m=self.distance_m,
                               actions=tuple(action.public_action() for action in self.actions))

    def to_dict(self) -> dict[str, object]:
        return {"distance_m": self.distance_m, "actions": [action.to_dict() for action in self.actions]}


@dataclass(frozen=True, kw_only=True)
class OutputAnalyzer:
    """Optional shared output measurement; saved axis remains authoritative."""

    enabled: bool
    axis_angle_rad: float

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise TypeError("analyzer.enabled: expected exact boolean")
        object.__setattr__(self, "axis_angle_rad", _real(self.axis_angle_rad, "analyzer.axis_angle_rad"))

    def to_dict(self) -> dict[str, object]:
        return {"enabled": self.enabled, "axis_angle_rad": self.axis_angle_rad}


@dataclass(frozen=True, kw_only=True)
class PolarizedTwoPathExperiment:
    """Owned immutable complete SI settings; static acceptance executes no optics."""

    source_plane: SequentialExperiment
    coefficients: tuple[complex, complex]
    arm_0: PolarizedTwoPathArm
    arm_1: PolarizedTwoPathArm
    relative_phase_rad: float
    analyzer: OutputAnalyzer

    def __post_init__(self) -> None:
        if type(self.source_plane) is not SequentialExperiment:
            raise TypeError("source_plane: expected public SequentialExperiment")
        source = SequentialExperiment.from_dict(self.source_plane.to_dict())
        if source.components or source.observation.z_m != 0 or source.observation.id != "source_plane":
            raise ValueError("source_plane: empty train and fixed source_plane at zero required")
        if any(not 1 <= count <= MAX_AXIS for count in (source.grid.ny, source.grid.nx)):
            raise ValueError("source_plane.grid: V2g maximum axis is 128")
        if type(self.coefficients) is not tuple or len(self.coefficients) != 2:
            raise TypeError("coefficients: expected immutable x/y pair")
        pair = []
        for value in self.coefficients:
            if type(value) not in (int, float, complex):
                raise TypeError("coefficient: expected finite complex scalar excluding bool")
            pair.append(_complex(_complex_dict(complex(value)), "coefficient"))
        for name in ("arm_0", "arm_1"):
            if type(getattr(self, name)) is not PolarizedTwoPathArm:
                raise TypeError(f"{name}: expected immutable PolarizedTwoPathArm")
        identifiers = [action.id for arm in (self.arm_0, self.arm_1) for action in arm.actions]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("actions: identifiers must be unique across both arms")
        if type(self.analyzer) is not OutputAnalyzer:
            raise TypeError("analyzer: expected immutable OutputAnalyzer")
        object.__setattr__(self, "source_plane", source)
        object.__setattr__(self, "coefficients", tuple(pair))
        object.__setattr__(self, "relative_phase_rad", _real(self.relative_phase_rad, "relative_phase_rad"))
        self.public_spec()

    @classmethod
    def from_dict(cls, payload: object) -> PolarizedTwoPathExperiment:
        """Validate the exact closed full public-source application schema."""
        value = _keys(payload, {"schema_version", "model_contract", "wavelength_m", "grid", "source",
            "coefficients", "arm_0", "arm_1", "relative_phase_rad", "analyzer"}, "experiment")
        if type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise ValueError("schema_version: expected integer 1")
        if value["model_contract"] != MODEL_CONTRACT:
            raise ValueError(f"model_contract: expected {MODEL_CONTRACT}")
        grid = _keys(value["grid"], {"ny", "nx", "dy", "dx"}, "grid")
        for name in ("ny", "nx"):
            if type(grid[name]) is not int:
                raise TypeError(f"grid.{name}: expected integer excluding bool")
            if not 1 <= grid[name] <= MAX_AXIS:
                raise ValueError(f"grid.{name}: expected 1..{MAX_AXIS}, got {grid[name]}")
        for name in ("dy", "dx"):
            grid[name] = _real(grid[name], f"grid.{name}")
        source = value["source"]
        if type(source) is not dict or source.get("kind") not in ("uniform", "gaussian"):
            raise ValueError("source.kind: expected uniform or gaussian")
        names = {"kind", "amplitude", "phase_rad"}
        if source["kind"] == "gaussian":
            names |= {"waist_radius_m", "waist_z_m", "center_x_m", "center_y_m"}
        source = _keys(source, names, "source")
        source = {key: item if key == "kind" else _real(item, f"source.{key}") for key, item in source.items()}
        source_plane = SequentialExperiment.from_dict({"schema_version": 1,
            "model_contract": "v0_aligned_scalar_forward_v1", "wavelength_m": _real(value["wavelength_m"], "wavelength_m"),
            "grid": grid, "source": source, "components": [], "observation": {"id": "source_plane", "z_m": 0.0}})
        coefficients = _keys(value["coefficients"], {"x", "y"}, "coefficients")
        pair = tuple(_complex(coefficients[name], f"coefficients.{name}") for name in ("x", "y"))
        arms = []
        for arm_name in ("arm_0", "arm_1"):
            arm = _keys(value[arm_name], {"distance_m", "actions"}, arm_name)
            if type(arm["actions"]) is not list or len(arm["actions"]) > MAX_ACTIONS:
                raise ValueError(f"{arm_name}.actions: expected ordered JSON list of zero-to-two actions")
            actions = []
            for index, action in enumerate(arm["actions"]):
                if type(action) is not dict or action.get("kind") not in ("linear_polarizer", "linear_retarder"):
                    raise ValueError(f"{arm_name}.actions[{index}]: unsupported kind")
                names = {"id", "kind", "axis_angle_rad"}
                if action["kind"] == "linear_retarder":
                    names.add("retardance_rad")
                action = _keys(action, names, f"{arm_name}.actions[{index}]")
                actions.append(PolarizedTwoPathAction(**action))
            arms.append(PolarizedTwoPathArm(distance_m=arm["distance_m"], actions=tuple(actions)))
        analyzer = OutputAnalyzer(**_keys(value["analyzer"], {"enabled", "axis_angle_rad"}, "analyzer"))
        return cls(source_plane=source_plane, coefficients=pair, arm_0=arms[0], arm_1=arms[1],
                   relative_phase_rad=value["relative_phase_rad"], analyzer=analyzer)

    def public_spec(self, phase_rad: float | None = None) -> PolarizedTwoArmSpec:
        """Construct the unchanged public arm composition for the supplied phase."""
        return PolarizedTwoArmSpec(arm_0=self.arm_0.public_arm(), arm_1=self.arm_1.public_arm(),
            relative_phase_rad=self.relative_phase_rad if phase_rad is None else phase_rad)

    def to_dict(self) -> dict[str, object]:
        """Export fresh complete SI inputs, including inactive analyzer settings."""
        source = self.source_plane.to_dict()
        return {"schema_version": 1, "model_contract": MODEL_CONTRACT,
            **{name: source[name] for name in ("wavelength_m", "grid", "source")},
            "coefficients": {name: _complex_dict(value) for name, value in zip(("x", "y"), self.coefficients)},
            "arm_0": self.arm_0.to_dict(), "arm_1": self.arm_1.to_dict(),
            "relative_phase_rad": self.relative_phase_rad, "analyzer": self.analyzer.to_dict()}

    def fixed_dict(self) -> dict[str, object]:
        """Export sweep settings with only the varied common phase omitted."""
        value = self.to_dict()
        del value["relative_phase_rad"]
        return value


@dataclass(frozen=True, kw_only=True)
class ValidatedPolarizedTwoPathSubmission:
    request_id: str
    experiment: PolarizedTwoPathExperiment
    experiment_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        validate_request_id(self.request_id)
        if type(self.experiment) is not PolarizedTwoPathExperiment:
            raise TypeError("experiment: expected PolarizedTwoPathExperiment")
        owned = PolarizedTwoPathExperiment.from_dict(self.experiment.to_dict())
        object.__setattr__(self, "experiment", owned)
        object.__setattr__(self, "experiment_sha256", experiment_digest(owned.to_dict()))


@dataclass(frozen=True, kw_only=True)
class ValidatedPolarizedTwoPathSweepSubmission:
    request_id: str
    experiment: PolarizedTwoPathExperiment
    phases_rad: tuple[float, ...]
    fixed_experiment_sha256: str = field(init=False)
    sweep_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        validate_request_id(self.request_id)
        if type(self.experiment) is not PolarizedTwoPathExperiment:
            raise TypeError("experiment: expected PolarizedTwoPathExperiment")
        if type(self.phases_rad) is not tuple or len(self.phases_rad) != 17:
            raise ValueError("phases_rad: expected immutable seventeen-phase tuple")
        phases = tuple(_real(phase, "phase_rad") for phase in self.phases_rad)
        if phases != PHASES_RAD:
            raise ValueError("phases_rad: expected exact seventeen declared radians")
        value = self.experiment.fixed_dict()
        owned = PolarizedTwoPathExperiment.from_dict({**value, "relative_phase_rad": 0.0})
        object.__setattr__(self, "experiment", owned)
        object.__setattr__(self, "phases_rad", phases)
        object.__setattr__(self, "fixed_experiment_sha256", experiment_digest(value))
        object.__setattr__(self, "sweep_sha256", sweep_digest(value, phases))

    def fixed_dict(self) -> dict[str, object]:
        return self.experiment.fixed_dict()


def validate_experiment(spec: object) -> PolarizedTwoPathExperiment:
    """Accept static complete settings without any source or Jones operations."""
    return PolarizedTwoPathExperiment.from_dict(spec)


def _envelope(payload, *, sweep, require_digest):
    names = {"protocol_version", "message_type", "request_id"}
    names |= {"fixed_experiment", "fixed_experiment_sha256", "phases_rad"} if sweep else {"experiment", "experiment_sha256"}
    value = _keys(payload, names, "submission")
    if type(value["protocol_version"]) is not int or value["protocol_version"] != 1:
        raise ValueError("protocol_version: expected integer 1")
    expected = "polarized_two_path_sweep_submission" if sweep else "polarized_two_path_submission"
    if value["message_type"] != expected:
        raise ValueError(f"message_type: expected {expected}")
    validate_request_id(value["request_id"])
    if sweep:
        fixed = value["fixed_experiment"]
        if type(fixed) is not dict or "relative_phase_rad" in fixed:
            raise ValueError("fixed_experiment: expected full settings without relative_phase_rad")
        experiment = validate_experiment({**fixed, "relative_phase_rad": 0.0})
        digest, actual = value["fixed_experiment_sha256"], experiment_digest(experiment.fixed_dict())
    else:
        experiment = validate_experiment(value["experiment"])
        digest, actual = value["experiment_sha256"], experiment_digest(experiment.to_dict())
    if require_digest:
        if type(digest) is not str or digest != actual:
            raise ValueError("digest: compute requires matching complete validated settings SHA")
    elif digest is not None:
        raise ValueError("digest: noncomputing validation requires null")
    return value, experiment


def validate_submission(payload: object, *, require_digest: bool = True) -> ValidatedPolarizedTwoPathSubmission:
    """Validate a single immutable identity; execute zero scientific operations."""
    value, experiment = _envelope(payload, sweep=False, require_digest=require_digest)
    return ValidatedPolarizedTwoPathSubmission(request_id=value["request_id"], experiment=experiment)


def validate_sweep_submission(payload: object, *, require_digest: bool = True) -> ValidatedPolarizedTwoPathSweepSubmission:
    """Validate fixed settings and all seventeen actual requested phase values."""
    value, experiment = _envelope(payload, sweep=True, require_digest=require_digest)
    phases = value["phases_rad"]
    if type(phases) is not list or len(phases) != 17:
        raise ValueError("phases_rad: expected JSON list of seventeen declared radians")
    return ValidatedPolarizedTwoPathSweepSubmission(request_id=value["request_id"], experiment=experiment,
                                                   phases_rad=tuple(phases))


def _incident(experiment: PolarizedTwoPathExperiment) -> JonesField:
    scalar = sample_source(experiment.source_plane)
    return JonesField.from_scalar(scalar, x_coefficient=experiment.coefficients[0],
                                  y_coefficient=experiment.coefficients[1])


def _measure(incident: JonesField, experiment: PolarizedTwoPathExperiment, phase_rad: float):
    result = run_polarized_two_arm(incident, spec=experiment.public_spec(phase_rad))
    if type(result) is not PolarizedTwoArmResult or result.spec != experiment.public_spec(phase_rad):
        raise ValueError("public result: immutable submitted spec mismatch")
    for output in result.outputs:
        if output.grid != incident.grid or output.wavelength_m != incident.wavelength_m:
            raise ValueError("public result: common submitted grid/wavelength required")
    norms = {name: getattr(result.norms, name) for name in (*NORM_PAIRS, "arm_action_norms")}
    diagnostics = {name: getattr(result.norms, name) for name in DIAGNOSTIC_KEYS}
    analysis = {"enabled": experiment.analyzer.enabled, "axis_angle_rad": experiment.analyzer.axis_angle_rad,
                "ports": None, "total_norm": None, "total_removed_norm": None, "total_original_input_ratio": None}
    analyzed = None
    if experiment.analyzer.enabled:
        fields, ports = [], []
        for index, raw in enumerate(result.outputs):
            try:
                measured = apply_linear_polarizer(raw, axis_angle_rad=experiment.analyzer.axis_angle_rad)
                analyzed_norm = measured.sampled_norm
                ports.append({"id": f"port_{index}", "raw_norm": result.norms.outputs[index],
                    "analyzed_norm": analyzed_norm, "removed_norm": result.norms.outputs[index] - analyzed_norm,
                    "original_input_ratio": transmission_ratio(incident, measured),
                    "raw_output_ratio": transmission_ratio(raw, measured)})
                fields.append(measured)
            except (ValueError, FloatingPointError, OverflowError) as exc:
                raise ValueError(f"output analyzer port_{index}: {exc}") from exc
        total_norm = sum(port["analyzed_norm"] for port in ports)
        removed = sum(port["removed_norm"] for port in ports)
        ratio = None if result.norms.inputs_total == 0 else sum(port["original_input_ratio"] for port in ports)
        for name, value in (("total_norm", total_norm), ("total_removed_norm", removed), ("total_original_input_ratio", ratio)):
            if value is not None and not math.isfinite(value):
                raise ValueError(f"output analyzer {name}: nonfinite scalar arithmetic")
        analysis.update(ports=ports, total_norm=total_norm, total_removed_norm=removed, total_original_input_ratio=ratio)
        analyzed = tuple(fields)
    return result, norms, diagnostics, analysis, analyzed


def simulate_submission(submission: ValidatedPolarizedTwoPathSubmission) -> bytes:
    """Sample once, run V2f once, measure zero or two analyzers, encode once."""
    if type(submission) is not ValidatedPolarizedTwoPathSubmission:
        raise TypeError("submission: expected ValidatedPolarizedTwoPathSubmission")
    experiment = submission.experiment
    try:
        incident = _incident(experiment)
        result, norms, diagnostics, analysis, analyzed = _measure(incident, experiment, experiment.relative_phase_rad)
        raw_images = tuple(output.intensity for output in result.outputs)
        analyzed_images = None if analyzed is None else tuple(output.intensity for output in analyzed)
    except (ValueError, FloatingPointError, OverflowError) as exc:
        raise NumericalError(f"polarized two-path measurement: {exc}") from exc
    return encode_result(submission.request_id, experiment.to_dict(), norms, diagnostics, analysis,
        raw_intensities=raw_images, analyzed_intensities=analyzed_images, x_m=incident.grid.x, y_m=incident.grid.y)


def sweep_submission(submission: ValidatedPolarizedTwoPathSweepSubmission) -> SweepReply:
    """Sample once and compute seventeen independent scalar measurement rows."""
    if type(submission) is not ValidatedPolarizedTwoPathSweepSubmission:
        raise TypeError("submission: expected ValidatedPolarizedTwoPathSweepSubmission")
    rows, index = [], 0
    try:
        incident = _incident(submission.experiment)
        for index, phase in enumerate(submission.phases_rad):
            result, norms, diagnostics, analysis, analyzed = _measure(incident, submission.experiment, phase)
            rows.append({"index": index, "phase_rad": phase, "norms": norms, "diagnostics": diagnostics, "analysis": analysis})
            del result, analyzed
    except (ValueError, FloatingPointError, OverflowError) as exc:
        return encode_sweep_reply(submission.request_id, submission.fixed_dict(), submission.phases_rad, rows,
            failed_index=index, error={"code": "numerical_failure", "message": str(exc)[:300] or "Numerical failure"}, status_code=422)
    except Exception:
        return encode_sweep_reply(submission.request_id, submission.fixed_dict(), submission.phases_rad, rows,
            failed_index=index, error={"code": "sweep_failed", "message": "Unexpected internal sweep failure"}, status_code=500)
    return encode_sweep_reply(submission.request_id, submission.fixed_dict(), submission.phases_rad, rows)
