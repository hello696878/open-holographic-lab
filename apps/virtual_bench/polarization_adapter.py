"""Public-source/public-Jones V2d adapter: ordered ideal actions at one plane.

No propagation, optical equations, coefficient normalization or phase reset.
Gaussian waist position zero is a restriction of this app's input boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import re

from ohlab.optics import SequentialExperiment, sample_source
from ohlab.optics.polarization import (JonesField, apply_linear_polarizer,
                                       apply_linear_retarder, transmission_ratio)

from .adapter import NumericalError
from .polarization_protocol import (ANGLES_RAD, MAX_AXIS, MAX_ELEMENTS, MODEL_CONTRACT,
                                    PROTOCOL_VERSION, SweepReply, encode_result,
                                    encode_sweep_reply, experiment_digest, sweep_digest,
                                    validate_request_id)


def _keys(value: object, expected: set[str], name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{name}: expected JSON object")
    if set(value) != expected:
        raise ValueError(f"{name}: expected exactly {sorted(expected)}")
    return value.copy()


def _real(value: object, name: str) -> float:
    if type(value) not in (int, float):
        raise TypeError(f"{name}: expected finite real excluding bool")
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{name}: expected representable finite binary64") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name}: expected finite binary64, got {result!r}")
    return 0.0 if result == 0.0 else result


def _complex(value: object, name: str) -> complex:
    value = _keys(value, {"re", "im"}, name)
    return complex(_real(value["re"], f"{name}.re"), _real(value["im"], f"{name}.im"))


def _complex_dict(value: complex) -> dict[str, float]:
    return {"re": float(value.real), "im": float(value.imag)}


@dataclass(frozen=True, kw_only=True)
class PolarizationElement:
    """Owned ordered ideal element; axis and retardance are authoritative radians."""

    id: str
    kind: str
    axis_angle_rad: float
    retardance_rad: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str):
            raise TypeError("element.id: expected ASCII identifier string")
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", self.id, flags=re.ASCII) is None or self.id == "input":
            raise ValueError("element.id: expected 1..32 ASCII identifier excluding input")
        if self.kind not in ("linear_polarizer", "linear_retarder"):
            raise ValueError("element.kind: expected linear_polarizer or linear_retarder")
        object.__setattr__(self, "axis_angle_rad", _real(self.axis_angle_rad, "element.axis_angle_rad"))
        if self.kind == "linear_retarder":
            object.__setattr__(self, "retardance_rad", _real(self.retardance_rad, "element.retardance_rad"))
        elif self.retardance_rad is not None:
            raise ValueError("polarizer.retardance_rad: expected None")

    def to_dict(self) -> dict[str, object]:
        result = {"id": self.id, "kind": self.kind, "axis_angle_rad": self.axis_angle_rad}
        if self.kind == "linear_retarder":
            result["retardance_rad"] = self.retardance_rad
        return result


@dataclass(frozen=True, kw_only=True)
class PolarizationExperiment:
    """Owned immutable source plane, coefficients, train and fixed sample identity."""

    source_plane: SequentialExperiment
    coefficients: tuple[complex, complex]
    elements: tuple[PolarizationElement, ...]
    row: int
    column: int

    def __post_init__(self) -> None:
        if type(self.source_plane) is not SequentialExperiment:
            raise TypeError("source_plane: expected canonical public SequentialExperiment")
        source = SequentialExperiment.from_dict(self.source_plane.to_dict())
        if source.components or source.observation.z_m != 0.0:
            raise ValueError("source_plane: empty train and observation zero required")
        if source.to_dict()["source"].get("waist_z_m", 0.0) != 0.0:
            raise ValueError("source_plane: Gaussian waist position must be fixed at zero")
        if any(not 1 <= count <= MAX_AXIS for count in (source.grid.ny, source.grid.nx)):
            raise ValueError("source_plane.grid: V2d maximum axis is 128")
        if not isinstance(self.coefficients, (tuple, list)) or len(self.coefficients) != 2:
            raise TypeError("coefficients: expected x/y pair")
        coefficients = []
        for index, value in enumerate(self.coefficients):
            if type(value) not in (int, float, complex):
                raise TypeError(f"coefficients[{index}]: expected finite scalar excluding bool")
            coefficients.append(_complex(_complex_dict(complex(value)), f"coefficients[{index}]"))
        if not isinstance(self.elements, (tuple, list)) or len(self.elements) > MAX_ELEMENTS:
            raise TypeError("elements: expected at most eight element records")
        elements, ids = [], {"input"}
        for element in self.elements:
            if type(element) is not PolarizationElement:
                raise TypeError("elements: expected PolarizationElement records")
            if element.id in ids:
                raise ValueError("elements: duplicate stable identifier")
            ids.add(element.id)
            elements.append(PolarizationElement(**element.to_dict()))
        for name, count in (("row", source.grid.ny), ("column", source.grid.nx)):
            index = getattr(self, name)
            if type(index) is not int:
                raise TypeError(f"readout.{name}: expected integer excluding bool")
            if not 0 <= index < count:
                raise ValueError(f"readout.{name}: expected 0..{count-1}")
        object.__setattr__(self, "source_plane", source)
        object.__setattr__(self, "coefficients", tuple(coefficients))
        object.__setattr__(self, "elements", tuple(elements))

    @classmethod
    def from_dict(cls, payload: object) -> PolarizationExperiment:
        """Validate the exact app SI specification without sampling any fields."""
        value = _keys(payload, {"schema_version", "model_contract", "wavelength_m", "grid",
                                "source", "coefficients", "elements", "readout"}, "experiment")
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
        if not isinstance(source, dict) or source.get("kind") not in ("uniform", "gaussian"):
            raise ValueError("source.kind: expected uniform or gaussian")
        names = {"kind", "amplitude", "phase_rad"}
        if source["kind"] == "gaussian":
            names |= {"waist_radius_m", "center_x_m", "center_y_m"}
        source = _keys(source, names, "source")
        source = {key: item if key == "kind" else _real(item, f"source.{key}") for key, item in source.items()}
        if source["kind"] == "gaussian":
            source["waist_z_m"] = 0.0
        source_plane = SequentialExperiment.from_dict({
            "schema_version": 1, "model_contract": "v0_aligned_scalar_forward_v1",
            "wavelength_m": _real(value["wavelength_m"], "wavelength_m"), "grid": grid,
            "source": source, "components": [], "observation": {"id": "source_plane", "z_m": 0.0}})
        coefficients = _keys(value["coefficients"], {"x", "y"}, "coefficients")
        pair = tuple(_complex(coefficients[name], f"coefficients.{name}") for name in ("x", "y"))
        records = value["elements"]
        if not isinstance(records, list):
            raise TypeError("elements: expected ordered JSON list")
        if len(records) > MAX_ELEMENTS:
            raise ValueError(f"elements: expected at most {MAX_ELEMENTS}")
        elements, ids = [], {"input"}
        for index, item in enumerate(records):
            if not isinstance(item, dict) or item.get("kind") not in ("linear_polarizer", "linear_retarder"):
                raise ValueError(f"elements[{index}].kind: expected linear_polarizer or linear_retarder")
            names = {"id", "kind", "axis_angle_rad"}
            if item["kind"] == "linear_retarder":
                names.add("retardance_rad")
            item = _keys(item, names, f"elements[{index}]")
            identifier = item["id"]
            if not isinstance(identifier, str):
                raise TypeError(f"elements[{index}].id: expected ASCII identifier string")
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", identifier, flags=re.ASCII) is None or identifier in ids:
                raise ValueError(f"elements[{index}].id: expected unique 1..32 ASCII identifier excluding input")
            ids.add(identifier)
            elements.append(PolarizationElement(id=identifier, kind=item["kind"],
                axis_angle_rad=_real(item["axis_angle_rad"], f"elements[{index}].axis_angle_rad"),
                retardance_rad=_real(item["retardance_rad"], f"elements[{index}].retardance_rad")
                if item["kind"] == "linear_retarder" else None))
        readout = _keys(value["readout"], {"row", "column"}, "readout")
        for name, bound in (("row", grid["ny"]), ("column", grid["nx"])):
            if type(readout[name]) is not int:
                raise TypeError(f"readout.{name}: expected integer excluding bool")
            if not 0 <= readout[name] < bound:
                raise ValueError(f"readout.{name}: expected 0..{bound-1}, got {readout[name]}")
        return cls(source_plane=source_plane, coefficients=pair, elements=tuple(elements),
                   row=readout["row"], column=readout["column"])

    def to_dict(self) -> dict[str, object]:
        """Export fresh complete inputs in SI, omitting the fixed internal waist z."""
        source = self.source_plane.to_dict()
        source["source"].pop("waist_z_m", None)
        return {"schema_version": 1, "model_contract": MODEL_CONTRACT,
                **{name: source[name] for name in ("wavelength_m", "grid", "source")},
                "coefficients": {name: _complex_dict(value) for name, value in zip(("x", "y"), self.coefficients)},
                "elements": [element.to_dict() for element in self.elements],
                "readout": {"row": self.row, "column": self.column}}


@dataclass(frozen=True, kw_only=True)
class ValidatedPolarizationSubmission:
    request_id: str
    experiment: PolarizationExperiment
    experiment_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        validate_request_id(self.request_id)
        if not isinstance(self.experiment, PolarizationExperiment):
            raise TypeError("experiment: expected PolarizationExperiment")
        object.__setattr__(self, "experiment", PolarizationExperiment.from_dict(self.experiment.to_dict()))
        object.__setattr__(self, "experiment_sha256", experiment_digest(self.experiment.to_dict()))


@dataclass(frozen=True, kw_only=True)
class ValidatedPolarizationSweepSubmission(ValidatedPolarizationSubmission):
    selected_element_id: str
    angles_rad: tuple[float, ...]
    sweep_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.angles_rad, tuple) or len(self.angles_rad) != 13:
            raise TypeError("angles_rad: expected immutable thirteen-angle tuple")
        angles = tuple(_real(angle, f"angles_rad[{index}]") for index, angle in enumerate(self.angles_rad))
        if angles != ANGLES_RAD:
            raise ValueError("angles_rad: expected exact thirteen declared radians")
        object.__setattr__(self, "angles_rad", angles)
        if not isinstance(self.selected_element_id, str):
            raise TypeError("selected_element_id: expected stable string ID")
        if not any(element.id == self.selected_element_id and element.kind == "linear_polarizer"
                   for element in self.experiment.elements):
            raise ValueError("selected_element_id: expected existing linear polarizer ID")
        object.__setattr__(self, "sweep_sha256", sweep_digest(self.experiment.to_dict(),
                           self.selected_element_id, self.angles_rad))


def _envelope(payload: object, *, sweep: bool, require_digest: bool) -> dict[str, object]:
    keys = {"protocol_version", "message_type", "request_id", "experiment", "experiment_sha256"}
    if sweep:
        keys |= {"selected_element_id", "angles_rad"}
    value = _keys(payload, keys, "submission")
    if type(value["protocol_version"]) is not int or value["protocol_version"] != PROTOCOL_VERSION:
        raise ValueError("protocol_version: expected V2d integer 1")
    expected = "polarization_sweep_submission" if sweep else "polarization_submission"
    if value["message_type"] != expected:
        raise ValueError(f"message_type: expected {expected}")
    validate_request_id(value["request_id"])
    value["experiment"] = PolarizationExperiment.from_dict(value["experiment"])
    digest = value["experiment_sha256"]
    if digest is None:
        if require_digest:
            raise ValueError("experiment_sha256: compute requires matching validation SHA")
    elif not isinstance(digest, str) or digest != experiment_digest(value["experiment"].to_dict()):
        raise ValueError("experiment_sha256: mismatched complete validated experiment")
    return value


def validate_submission(payload: object, *, require_digest: bool = False) -> ValidatedPolarizationSubmission:
    """Validate immutable source/train/sample identity; execute zero optics calls."""
    value = _envelope(payload, sweep=False, require_digest=require_digest)
    return ValidatedPolarizationSubmission(request_id=value["request_id"], experiment=value["experiment"])


def validate_sweep_submission(payload: object, *, require_digest: bool = True) -> ValidatedPolarizationSweepSubmission:
    """Validate a frozen full train and all thirteen actual selected-axis radians."""
    value = _envelope(payload, sweep=True, require_digest=require_digest)
    angles = value["angles_rad"]
    if not isinstance(angles, list) or len(angles) != 13:
        raise ValueError("angles_rad: expected exactly thirteen declared radians")
    actual = tuple(_real(angle, f"angles_rad[{index}]") for index, angle in enumerate(angles))
    if actual != ANGLES_RAD:
        raise ValueError("angles_rad: expected exact thirteen declared radians")
    if not isinstance(value["selected_element_id"], str):
        raise TypeError("selected_element_id: expected stable identifier string")
    return ValidatedPolarizationSweepSubmission(request_id=value["request_id"], experiment=value["experiment"],
                    selected_element_id=value["selected_element_id"], angles_rad=actual)


def _incident(experiment: PolarizationExperiment) -> JonesField:
    scalar = sample_source(experiment.source_plane)
    return JonesField.from_scalar(scalar, x_coefficient=experiment.coefficients[0],
                                  y_coefficient=experiment.coefficients[1])


def _apply_element(field: JonesField, element: PolarizationElement,
                    axis_override: float | None = None) -> JonesField:
    axis = element.axis_angle_rad if axis_override is None else axis_override
    if element.kind == "linear_polarizer":
        return apply_linear_polarizer(field, axis_angle_rad=axis)
    return apply_linear_retarder(field, axis_angle_rad=axis, retardance_rad=element.retardance_rad)


def _record(field: JonesField, incident: JonesField, experiment: PolarizationExperiment,
            *, element: PolarizationElement | None, previous: JonesField | None,
            previous_norm: float | None, include_samples: bool) -> dict[str, object]:
    if field.grid != experiment.source_plane.grid or field.wavelength_m != experiment.source_plane.wavelength_m:
        raise ValueError("public result: submitted common grid/wavelength required")
    norm = field.sampled_norm
    record = {"stage_id": "input" if element is None else element.id,
              "kind": "input" if element is None else element.kind,
              "norm": norm, "previous_norm": previous_norm,
              "delta_norm": None if previous is None else norm - previous_norm,
              "adjacent_transmission_ratio": None if previous is None else transmission_ratio(previous, field),
              "incident_transmission_ratio": transmission_ratio(incident, field)}
    if include_samples:
        record["sample"] = {name: _complex_dict(complex(getattr(field, name).data[experiment.row, experiment.column]))
                            for name in ("x", "y")}
    return record


def _run_train(incident: JonesField, experiment: PolarizationExperiment, *,
               selected_element_id: str | None = None, axis_angle_rad: float | None = None,
               include_samples: bool = True) -> tuple[JonesField, list[dict[str, object]]]:
    current = incident
    stages = [_record(current, incident, experiment, element=None, previous=None,
                      previous_norm=None, include_samples=include_samples)]
    for element in experiment.elements:
        previous = current
        current = _apply_element(previous, element,
                                  axis_angle_rad if element.id == selected_element_id else None)
        stages.append(_record(current, incident, experiment, element=element, previous=previous,
                              previous_norm=stages[-1]["norm"], include_samples=include_samples))
        del previous
    return current, stages


def simulate_submission(submission: ValidatedPolarizationSubmission) -> bytes:
    """Sample once, construct Jones once and apply every public element once."""
    if type(submission) is not ValidatedPolarizationSubmission:
        raise TypeError("submission: expected ValidatedPolarizationSubmission")
    experiment = submission.experiment
    try:
        incident = _incident(experiment)
        final, stages = _run_train(incident, experiment)
        incident_intensity, final_intensity = incident.intensity, final.intensity
    except (ValueError, FloatingPointError, OverflowError) as exc:
        raise NumericalError(str(exc)) from exc
    return encode_result(submission.request_id, experiment.to_dict(), stages,
                         incident_intensity=incident_intensity, final_intensity=final_intensity,
                         x_m=incident.grid.x, y_m=incident.grid.y)


def sweep_submission(submission: ValidatedPolarizationSweepSubmission) -> SweepReply:
    """Restart full train from original incident at each angle; retain scalars only."""
    if not isinstance(submission, ValidatedPolarizationSweepSubmission):
        raise TypeError("submission: expected ValidatedPolarizationSweepSubmission")
    rows, index = [], 0
    try:
        incident = _incident(submission.experiment)
        for index, angle in enumerate(submission.angles_rad):
            final, stages = _run_train(incident, submission.experiment,
                        selected_element_id=submission.selected_element_id, axis_angle_rad=angle,
                        include_samples=False)
            rows.append({"index": index, "axis_angle_rad": angle, "stages": stages,
                         "final_norm": stages[-1]["norm"],
                         "incident_transmission_ratio": stages[-1]["incident_transmission_ratio"],
                         "total_delta": stages[-1]["norm"] - stages[0]["norm"]})
            del final
    except (ValueError, FloatingPointError, OverflowError) as exc:
        return encode_sweep_reply(submission.request_id, submission.experiment.to_dict(),
                   submission.selected_element_id, submission.angles_rad, rows, failed_index=index,
                   error={"code": "numerical_failure", "message": str(exc)[:300] or "Numerical failure"}, status_code=422)
    except Exception:
        return encode_sweep_reply(submission.request_id, submission.experiment.to_dict(),
                   submission.selected_element_id, submission.angles_rad, rows, failed_index=index,
                   error={"code": "sweep_failed", "message": "Unexpected internal sweep failure"}, status_code=500)
    return encode_sweep_reply(submission.request_id, submission.experiment.to_dict(),
                              submission.selected_element_id, submission.angles_rad, rows)
