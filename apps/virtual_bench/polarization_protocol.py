"""Bounded V2d transport of validated data, with no scientific dependencies.

Arrays are actual little-endian float64 intensities and metre coordinates.
Stage norms and ratios are supplied by the adapter, never derived from images.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import struct
import uuid

import numpy as np

MAGIC = b"OHLABPL\0"
PROTOCOL_VERSION = 1
MODEL_CONTRACT = "v2d_ideal_jones_same_plane_v1"
MAX_AXIS = 128
MAX_ELEMENTS = 8
MAX_BODY_BYTES = 32_768
MAX_HEADER_BYTES = 16_384
MAX_PAYLOAD_BYTES = 264_192
MAX_RESPONSE_BYTES = 280_592
MAX_SWEEP_RESPONSE_BYTES = 65_536
PREAMBLE = struct.Struct("<8sII")
ANGLES_RAD = tuple(math.radians(degrees) for degrees in range(-90, 91, 15))
STAGE_SCALAR_KEYS = {"stage_id", "kind", "norm", "previous_norm", "delta_norm",
                     "adjacent_transmission_ratio", "incident_transmission_ratio"}


def validate_request_id(value: object) -> str:
    """Require a canonical lowercase UUIDv4 identity, without physical units."""
    if not isinstance(value, str):
        raise TypeError("request_id: expected canonical UUIDv4 string")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ValueError("request_id: expected canonical UUIDv4 string") from exc
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError("request_id: expected canonical lowercase UUIDv4 string")
    return value


def _json(value: object, *, canonical: bool = False) -> bytes:
    return json.dumps(value, sort_keys=canonical, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def experiment_digest(experiment: dict[str, object]) -> str:
    """Hash complete validated SI inputs using server canonical JSON."""
    if not isinstance(experiment, dict):
        raise TypeError("experiment: expected dictionary")
    return hashlib.sha256(_json(experiment, canonical=True)).hexdigest()


def sweep_digest(experiment: dict[str, object], selected_element_id: str,
                 angles_rad: tuple[float, ...]) -> str:
    """Hash the frozen experiment, selected stable ID and actual radian grid."""
    return hashlib.sha256(_json({"experiment": experiment,
                                "selected_element_id": selected_element_id,
                                "angles_rad": angles_rad}, canonical=True)).hexdigest()


def _real(value: object, name: str, *, nonnegative: bool = False) -> float:
    if type(value) not in (int, float):
        raise TypeError(f"{name}: expected finite real excluding bool")
    result = float(value)
    if not math.isfinite(result) or (nonnegative and result < 0):
        raise ValueError(f"{name}: expected finite {'nonnegative ' if nonnegative else ''}value")
    return result


def ordered_stage_ids(experiment: dict[str, object]) -> list[str]:
    """Return input plus the validated ordered IDs; no scientific operation."""
    return ["input", *(element["id"] for element in experiment["elements"])]


def _check_stages(stages: list[dict[str, object]], experiment: dict[str, object],
                  *, samples: bool) -> None:
    expected_ids = ordered_stage_ids(experiment)
    if not isinstance(stages, list) or len(stages) != len(expected_ids) or len(stages) > 9:
        raise ValueError("stages: expected input plus every ordered element")
    previous = None
    for index, (record, stage_id) in enumerate(zip(stages, expected_ids)):
        keys = STAGE_SCALAR_KEYS | ({"sample"} if samples else set())
        if not isinstance(record, dict) or set(record) != keys:
            raise ValueError("stage: unexpected transport fields")
        kind = "input" if index == 0 else experiment["elements"][index - 1]["kind"]
        if record["stage_id"] != stage_id or record["kind"] != kind:
            raise ValueError("stage: wrong ordered identity or kind")
        norm = _real(record["norm"], "stage.norm", nonnegative=True)
        if index == 0:
            if any(record[key] is not None for key in
                   ("previous_norm", "delta_norm", "adjacent_transmission_ratio")):
                raise ValueError("input stage: previous/delta/adjacent must be null")
        else:
            if _real(record["previous_norm"], "stage.previous_norm", nonnegative=True) != previous:
                raise ValueError("stage.previous_norm: inconsistent chain")
            if _real(record["delta_norm"], "stage.delta_norm") != norm - previous:
                raise ValueError("stage.delta_norm: inconsistent signed difference")
            _check_ratio(record["adjacent_transmission_ratio"], previous)
        _check_ratio(record["incident_transmission_ratio"], stages[0]["norm"])
        if index == 0 and norm != 0 and record["incident_transmission_ratio"] != 1.0:
            raise ValueError("input stage: nonzero self transmission must be one")
        if samples:
            sample = record["sample"]
            if not isinstance(sample, dict) or set(sample) != {"x", "y"}:
                raise ValueError("sample: expected exact x/y pair")
            for label in ("x", "y"):
                component = sample[label]
                if not isinstance(component, dict) or set(component) != {"re", "im"}:
                    raise ValueError("sample component: expected exact re/im pair")
                for part in ("re", "im"):
                    _real(component[part], f"sample.{label}.{part}")
        previous = norm


def _check_ratio(value: object, denominator: float) -> None:
    if denominator == 0:
        if value is not None:
            raise ValueError("ratio: zero denominator requires null")
    else:
        _real(value, "ratio", nonnegative=True)


def encode_result(request_id: str, experiment: dict[str, object],
                  stages: list[dict[str, object]], *, incident_intensity: np.ndarray,
                  final_intensity: np.ndarray, x_m: np.ndarray, y_m: np.ndarray) -> bytes:
    """Encode validated public intensities, samples and scalar diagnostics.

Intensity units are amplitude_unit^2; coordinates metres; sampled norms and
signed differences amplitude_unit^2*m^2. No norm/ratio is recomputed here.
"""
    validate_request_id(request_id)
    _check_stages(stages, experiment, samples=True)
    grid = experiment["grid"]
    ny, nx = grid["ny"], grid["nx"]
    if any(type(count) is not int or not 1 <= count <= MAX_AXIS for count in (ny, nx)):
        raise ValueError("result grid exceeds V2d axis limits")
    readout = experiment["readout"]
    row, column = readout["row"], readout["column"]
    if any(type(index) is not int for index in (row, column)) or not (0 <= row < ny and 0 <= column < nx):
        raise ValueError("readout: expected submitted in-bounds integer indices")
    last_id = stages[-1]["stage_id"]
    arrays = (("incident_intensity", "intensity", "input", incident_intensity, (ny, nx), "amplitude_unit^2"),
              ("final_intensity", "intensity", last_id, final_intensity, (ny, nx), "amplitude_unit^2"),
              ("x_m", "coordinate", None, x_m, (nx,), "m"),
              ("y_m", "coordinate", None, y_m, (ny,), "m"))
    descriptors, parts, offset = [], [], 0
    for name, role, stage_id, values, shape, units in arrays:
        if (not isinstance(values, np.ndarray) or values.shape != shape or
                values.dtype != np.dtype("float64")):
            raise ValueError(f"{name}: expected float64 shape {shape}")
        if not np.isfinite(values).all() or (role == "intensity" and np.any(values < 0)):
            raise ValueError(f"{name}: expected finite {'nonnegative ' if role == 'intensity' else ''}values")
        part = np.ascontiguousarray(values, dtype="<f8").tobytes(order="C")
        descriptors.append({"name": name, "role": role, "stage_id": stage_id,
                            "dtype": "float64-le", "order": "C", "shape": list(shape),
                            "offset_bytes": offset, "nbytes": len(part), "units": units})
        parts.append(part)
        offset += len(part)
    header = {"protocol_version": PROTOCOL_VERSION, "message_type": "polarization_result",
              "request_id": request_id, "experiment_sha256": experiment_digest(experiment),
              "experiment": experiment, "ordered_stage_ids": ordered_stage_ids(experiment),
              "stages": stages,
              "readout": {"row": row, "column": column, "x_m": float(x_m[column]), "y_m": float(y_m[row])},
              "arrays": descriptors,
              "intensity_max": [float(np.max(incident_intensity)), float(np.max(final_intensity))]}
    encoded = _json(header)
    padding = b"\0" * (-len(encoded) % 8)
    if len(encoded) + len(padding) > MAX_HEADER_BYTES or offset > MAX_PAYLOAD_BYTES:
        raise ValueError("result exceeds V2d header or payload limit")
    if PREAMBLE.size + len(encoded) + len(padding) + offset > MAX_RESPONSE_BYTES:
        raise ValueError("result exceeds V2d complete frame limit")
    return b"".join((PREAMBLE.pack(MAGIC, len(encoded), 0), encoded, padding, *parts))


@dataclass(frozen=True, kw_only=True)
class SweepReply:
    """Encoded scalar reply; worker ownership includes all encoding work."""

    status_code: int
    body: bytes


def encode_sweep_reply(request_id: str, experiment: dict[str, object],
                       selected_element_id: str, angles_rad: tuple[float, ...],
                       rows: list[dict[str, object]], *, failed_index: int | None = None,
                       error: dict[str, str] | None = None, status_code: int = 200) -> SweepReply:
    """Encode all thirteen actual scalar rows or an explicit genuine prefix."""
    validate_request_id(request_id)
    for index, angle in enumerate(angles_rad):
        _real(angle, f"sweep.angles_rad[{index}]")
    if angles_rad != ANGLES_RAD or len(rows) > 13:
        raise ValueError("sweep: exact thirteen actual angles required")
    failed = failed_index is not None
    if failed:
        if (type(failed_index) is not int or failed_index != len(rows) or not 0 <= failed_index < 13 or
                status_code not in (422, 500) or not isinstance(error, dict) or set(error) != {"code", "message"}):
            raise ValueError("failed sweep: inconsistent prefix, status or error")
        expected_code = "numerical_failure" if status_code == 422 else "sweep_failed"
        if (error["code"] != expected_code or not isinstance(error["message"], str) or
                not 1 <= len(error["message"]) <= 300):
            raise ValueError("failed sweep: expected bounded typed error")
    elif len(rows) != 13 or error is not None or status_code != 200:
        raise ValueError("complete sweep: all thirteen genuine rows required")
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {
                "index", "axis_angle_rad", "stages", "final_norm", "incident_transmission_ratio", "total_delta"}:
            raise ValueError("sweep row: unexpected fields")
        if (type(row["index"]) is not int or row["index"] != index or
                _real(row["axis_angle_rad"], "sweep.axis_angle_rad") != angles_rad[index]):
            raise ValueError("sweep rows: contiguous requested angles required")
        _check_stages(row["stages"], experiment, samples=False)
        if _real(row["final_norm"], "sweep.final_norm", nonnegative=True) != row["stages"][-1]["norm"]:
            raise ValueError("sweep final norm: inconsistent actual stage")
        _check_ratio(row["incident_transmission_ratio"], row["stages"][0]["norm"])
        if row["incident_transmission_ratio"] != row["stages"][-1]["incident_transmission_ratio"]:
            raise ValueError("sweep ratio: inconsistent actual stage")
        if _real(row["total_delta"], "sweep.total_delta") != row["final_norm"] - row["stages"][0]["norm"]:
            raise ValueError("sweep total_delta: inconsistent signed difference")
    value = {"protocol_version": PROTOCOL_VERSION, "message_type": "polarization_sweep_result",
             "status": "failed" if failed else "complete", "request_id": request_id,
             "experiment_sha256": experiment_digest(experiment),
             "sweep_sha256": sweep_digest(experiment, selected_element_id, angles_rad),
             "experiment": experiment, "selected_element_id": selected_element_id,
             "angles_rad": list(angles_rad), "ordered_stage_ids": ordered_stage_ids(experiment),
             "requested_count": 13, "rows": rows, "completed_count": len(rows),
             "failed_index": failed_index, "error": error}
    encoded = _json(value)
    if len(encoded) > MAX_SWEEP_RESPONSE_BYTES:
        raise ValueError("sweep response exceeds V2d byte limit")
    return SweepReply(status_code=status_code, body=encoded)
