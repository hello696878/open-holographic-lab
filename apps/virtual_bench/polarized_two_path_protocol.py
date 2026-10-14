"""Bounded V2g transport; no scientific imports or replacement optics.

All arrays are original little-endian float64 intensities or metre axes.
Scalar histories are measured by public operations and supplied by the adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import struct
import uuid

import numpy as np

MAGIC = b"OHLABPT\0"
PROTOCOL_VERSION = 1
MODEL_CONTRACT = "v2g_ideal_polarized_two_path_v1"
MAX_AXIS = 128
MAX_ACTIONS = 2
MAX_BODY_BYTES = 32_768
MAX_HEADER_BYTES = 16_384
MAX_RAW_PAYLOAD_BYTES = 264_192
MAX_PAYLOAD_BYTES = 526_336
MAX_RAW_RESPONSE_BYTES = 280_592
MAX_RESPONSE_BYTES = 542_736
MAX_SWEEP_RESPONSE_BYTES = 65_536
PREAMBLE = struct.Struct("<8sII")
PHASES_RAD = tuple(k * math.pi / 8 for k in range(17))
NORM_PAIRS = ("inputs", "split", "propagated", "elements", "combiner", "outputs")
DIAGNOSTIC_KEYS = (
    "inputs_total", "split_total", "propagated_total", "elements_total", "combiner_total", "outputs_total",
    "split_delta", "propagation_delta", "elements_delta", "phase_delta", "recombination_delta", "total_delta",
    "propagation_deltas", "element_deltas", "phase_deltas", "arm_action_deltas",
    "output_fractions", "total_output_ratio",
)


def validate_request_id(value: object) -> str:
    """Require a canonical lowercase UUIDv4 temporary operation identity."""
    if type(value) is not str:
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
    """Hash complete validated SI settings, independently of document metadata."""
    if type(experiment) is not dict:
        raise TypeError("experiment: expected dictionary")
    return hashlib.sha256(_json(experiment, canonical=True)).hexdigest()


def sweep_digest(fixed_experiment: dict[str, object], phases_rad: tuple[float, ...]) -> str:
    """Hash fixed SI settings and all actual phase values in radians."""
    return hashlib.sha256(_json({"fixed_experiment": fixed_experiment,
                                "phases_rad": phases_rad}, canonical=True)).hexdigest()


def strict_json_loads(data: bytes) -> object:
    """Parse this new route's strict UTF-8 JSON without nonzero decimal loss."""
    if type(data) is not bytes:
        raise TypeError("JSON body: expected bytes")
    if len(data) > MAX_BODY_BYTES:
        raise ValueError("JSON body exceeds 32768 bytes")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON object key")
            result[key] = value
        return result

    def constant(token):
        raise ValueError("nonfinite JSON constant")

    def real(token):
        value = float(token)
        coefficient = token.lower().split("e", 1)[0]
        if not math.isfinite(value) or (value == 0 and any(c in "123456789" for c in coefficient)):
            raise ValueError("JSON number is not usable finite binary64")
        return value

    def integer(token):
        value = int(token)
        if not math.isfinite(float(value)):
            raise ValueError("JSON integer exceeds finite binary64")
        return value

    try:
        return json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                          parse_constant=constant, parse_float=real, parse_int=integer)
    except (UnicodeError, json.JSONDecodeError, RecursionError, OverflowError) as exc:
        raise ValueError("expected bounded strict UTF-8 JSON") from exc


def _keys(value, names, context):
    if type(value) is not dict or set(value) != set(names):
        raise ValueError(f"{context}: unexpected scalar fields")
    return value


def _real(value, context, *, nonnegative=False):
    if type(value) not in (int, float):
        raise TypeError(f"{context}: expected finite real excluding bool")
    result = float(value)
    if not math.isfinite(result) or (nonnegative and result < 0):
        raise ValueError(f"{context}: expected finite {'nonnegative ' if nonnegative else ''}value")
    return result


def _pair(value, context, *, nonnegative=False):
    if type(value) not in (tuple, list) or len(value) != 2:
        raise ValueError(f"{context}: expected ordered pair")
    return tuple(_real(item, context, nonnegative=nonnegative) for item in value)


def _ratio(value, numerator, denominator):
    if denominator == 0:
        if value is not None:
            raise ValueError("ratio: zero denominator requires null")
    else:
        actual = _real(value, "ratio", nonnegative=True)
        if numerator > 0 and actual == 0:
            raise ValueError("ratio: represented positive numerator requires usable positive ratio")
        if numerator == 0 and actual != 0:
            raise ValueError("ratio: exact zero numerator requires zero ratio")


def check_scalar_records(experiment, norms, diagnostics, analysis) -> None:
    """Check closed scalar schemas and exact identical-reduction chains only."""
    _keys(norms, (*NORM_PAIRS, "arm_action_norms"), "norms")
    measured = {name: _pair(norms[name], f"norms.{name}", nonnegative=True) for name in NORM_PAIRS}
    if measured["inputs"][1] != 0:
        raise ValueError("norms.inputs: fixed runner requires zero second input")
    histories = norms["arm_action_norms"]
    if type(histories) not in (tuple, list) or len(histories) != 2:
        raise ValueError("arm_action_norms: expected two ordered histories")
    deltas = []
    for arm_index, arm_name in enumerate(("arm_0", "arm_1")):
        history = histories[arm_index]
        if (type(history) not in (tuple, list) or len(history) > MAX_ACTIONS or
                len(history) != len(experiment[arm_name]["actions"])):
            raise ValueError("arm_action_norms: length must match submitted actions")
        previous, changes = measured["propagated"][arm_index], []
        for value in history:
            current = _real(value, "arm_action_norm", nonnegative=True)
            changes.append(current - previous)
            previous = current
        if previous != measured["elements"][arm_index]:
            raise ValueError("arm_action_norms: inconsistent final endpoint")
        deltas.append(changes)
    if measured["combiner"][0] != measured["elements"][0]:
        raise ValueError("combiner: unchanged arm0 must match elements")
    _keys(diagnostics, DIAGNOSTIC_KEYS, "diagnostics")
    totals = {name: sum(values) for name, values in measured.items()}
    for name, total in totals.items():
        if _real(diagnostics[f"{name}_total"], f"{name}_total", nonnegative=True) != total:
            raise ValueError("diagnostics: inconsistent checkpoint total")
    for key, after, before in (("split_delta", "split", "inputs"),
            ("propagation_delta", "propagated", "split"), ("elements_delta", "elements", "propagated"),
            ("phase_delta", "combiner", "elements"), ("recombination_delta", "outputs", "combiner"),
            ("total_delta", "outputs", "inputs")):
        if _real(diagnostics[key], key) != totals[after] - totals[before]:
            raise ValueError("diagnostics: inconsistent signed total difference")
    for key, after, before in (("propagation_deltas", "propagated", "split"),
            ("element_deltas", "elements", "propagated"), ("phase_deltas", "combiner", "elements")):
        expected = tuple(a - b for a, b in zip(measured[after], measured[before]))
        if _pair(diagnostics[key], key) != expected:
            raise ValueError("diagnostics: inconsistent signed arm difference")
    actual_deltas = diagnostics["arm_action_deltas"]
    if type(actual_deltas) not in (tuple, list) or len(actual_deltas) != 2:
        raise ValueError("arm_action_deltas: expected two histories")
    for actual, expected in zip(actual_deltas, deltas):
        if type(actual) not in (tuple, list) or len(actual) != len(expected):
            raise ValueError("arm_action_deltas: unexpected history length")
        if [_real(item, "arm_action_delta") for item in actual] != expected:
            raise ValueError("arm_action_deltas: inconsistent signed history")
    fractions = diagnostics["output_fractions"]
    if type(fractions) not in (tuple, list) or len(fractions) != 2:
        raise ValueError("output_fractions: expected pair")
    for fraction, numerator in zip(fractions, measured["outputs"]):
        _ratio(fraction, numerator, totals["inputs"])
    _ratio(diagnostics["total_output_ratio"], totals["outputs"], totals["inputs"])
    _keys(analysis, ("enabled", "axis_angle_rad", "ports", "total_norm",
                     "total_removed_norm", "total_original_input_ratio"), "analysis")
    configured = experiment["analyzer"]
    if type(analysis["enabled"]) is not bool or analysis["enabled"] != configured["enabled"]:
        raise ValueError("analysis.enabled: differs from submitted analyzer")
    if _real(analysis["axis_angle_rad"], "analysis.axis_angle_rad") != configured["axis_angle_rad"]:
        raise ValueError("analysis angle: differs from authoritative submitted angle")
    if not analysis["enabled"]:
        if any(analysis[name] is not None for name in ("ports", "total_norm", "total_removed_norm", "total_original_input_ratio")):
            raise ValueError("disabled analysis: measurements must be explicitly null")
        return
    ports = analysis["ports"]
    if type(ports) not in (tuple, list) or len(ports) != 2:
        raise ValueError("analysis.ports: expected both ordered measurements")
    for index, port in enumerate(ports):
        _keys(port, ("id", "raw_norm", "analyzed_norm", "removed_norm", "original_input_ratio", "raw_output_ratio"), "analysis port")
        if port["id"] != f"port_{index}":
            raise ValueError("analysis port: wrong ordered identity")
        raw = _real(port["raw_norm"], "raw_norm", nonnegative=True)
        analyzed = _real(port["analyzed_norm"], "analyzed_norm", nonnegative=True)
        if raw != measured["outputs"][index] or _real(port["removed_norm"], "removed_norm") != raw - analyzed:
            raise ValueError("analysis port: inconsistent measured norm chain")
        _ratio(port["original_input_ratio"], analyzed, totals["inputs"])
        _ratio(port["raw_output_ratio"], analyzed, raw)
    if _real(analysis["total_norm"], "total_norm", nonnegative=True) != sum(p["analyzed_norm"] for p in ports):
        raise ValueError("analysis: inconsistent analyzed total")
    if _real(analysis["total_removed_norm"], "total_removed_norm") != sum(p["removed_norm"] for p in ports):
        raise ValueError("analysis: inconsistent removed total")
    expected = None if totals["inputs"] == 0 else sum(p["original_input_ratio"] for p in ports)
    if analysis["total_original_input_ratio"] is not None:
        _real(analysis["total_original_input_ratio"], "total_original_input_ratio", nonnegative=True)
    if analysis["total_original_input_ratio"] != expected:
        raise ValueError("analysis: inconsistent sum of original-input ratios")


def encode_result(request_id: str, experiment: dict[str, object], norms: dict[str, object],
                  diagnostics: dict[str, object], analysis: dict[str, object], *,
                  raw_intensities: tuple[np.ndarray, np.ndarray],
                  analyzed_intensities: tuple[np.ndarray, np.ndarray] | None,
                  x_m: np.ndarray, y_m: np.ndarray) -> bytes:
    """Encode one atomic raw/optional-analyzed outcome with SI axes and norms."""
    validate_request_id(request_id)
    check_scalar_records(experiment, norms, diagnostics, analysis)
    ny, nx = experiment["grid"]["ny"], experiment["grid"]["nx"]
    if any(type(n) is not int or not 1 <= n <= MAX_AXIS for n in (ny, nx)):
        raise ValueError("result grid exceeds V2g axis limits")
    if type(raw_intensities) is not tuple or len(raw_intensities) != 2:
        raise ValueError("raw_intensities: expected ordered pair")
    enabled = experiment["analyzer"]["enabled"]
    if enabled:
        if type(analyzed_intensities) is not tuple or len(analyzed_intensities) != 2:
            raise ValueError("enabled analysis: both actual analyzed images required")
    elif analyzed_intensities is not None:
        raise ValueError("disabled analysis: analyzed images must be absent")
    arrays = []
    for state, images in (("raw", raw_intensities), ("analyzed", analyzed_intensities)):
        if images is not None:
            arrays.extend((f"{state}_port_{index}_intensity", "intensity", f"port_{index}", state,
                           values, (ny, nx), "amplitude_unit^2") for index, values in enumerate(images))
    arrays.extend((("x_m", "coordinate", None, None, x_m, (nx,), "m"),
                   ("y_m", "coordinate", None, None, y_m, (ny,), "m")))
    descriptors, parts, maxima, offset = [], [], [], 0
    for name, role, port_id, state, values, shape, units in arrays:
        if type(values) is not np.ndarray or values.dtype != np.dtype("float64") or values.shape != shape:
            raise ValueError(f"{name}: expected float64 shape {shape}")
        if not np.isfinite(values).all() or (role == "intensity" and np.any(values < 0)):
            raise ValueError(f"{name}: expected finite {'nonnegative ' if role == 'intensity' else ''}values")
        part = np.ascontiguousarray(values, dtype="<f8").tobytes(order="C")
        descriptors.append({"name": name, "role": role, "port_id": port_id, "state": state,
            "dtype": "float64-le", "order": "C", "shape": list(shape), "offset_bytes": offset,
            "nbytes": len(part), "units": units})
        parts.append(part)
        offset += len(part)
        if role == "intensity":
            maxima.append(float(np.max(values)))
    header = {"protocol_version": 1, "message_type": "polarized_two_path_result", "request_id": request_id,
        "experiment_sha256": experiment_digest(experiment), "experiment": experiment, "norms": norms,
        "diagnostics": diagnostics, "analysis": analysis, "arrays": descriptors, "intensity_max": maxima}
    encoded = _json(header)
    padding = b"\0" * (-len(encoded) % 8)
    payload_cap = MAX_PAYLOAD_BYTES if enabled else MAX_RAW_PAYLOAD_BYTES
    frame_cap = MAX_RESPONSE_BYTES if enabled else MAX_RAW_RESPONSE_BYTES
    if len(encoded) + len(padding) > MAX_HEADER_BYTES:
        raise ValueError("result exceeds V2g header limit")
    if offset > payload_cap:
        raise ValueError("result exceeds V2g payload limit")
    if PREAMBLE.size + len(encoded) + len(padding) + offset > frame_cap:
        raise ValueError("result exceeds V2g complete frame limit")
    return b"".join((PREAMBLE.pack(MAGIC, len(encoded), 0), encoded, padding, *parts))


@dataclass(frozen=True, kw_only=True)
class SweepReply:
    """Bounded actual scalar sweep reply, encoded inside worker ownership."""

    status_code: int
    body: bytes


def encode_sweep_reply(request_id: str, fixed_experiment: dict[str, object], phases_rad: tuple[float, ...],
                       rows: list[dict[str, object]], *, failed_index: int | None = None,
                       error: dict[str, str] | None = None, status_code: int = 200) -> SweepReply:
    """Encode seventeen computed rows or a genuine contiguous failed prefix."""
    validate_request_id(request_id)
    if type(phases_rad) is not tuple or len(phases_rad) != 17:
        raise ValueError("sweep: expected exact seventeen-phase tuple")
    phases = tuple(_real(value, "phase_rad") for value in phases_rad)
    if phases != PHASES_RAD or type(rows) is not list or len(rows) > 17:
        raise ValueError("sweep: exact seventeen declared phases required")
    if "relative_phase_rad" in fixed_experiment:
        raise ValueError("fixed_experiment: phase must be omitted")
    failed = failed_index is not None
    if failed:
        if (type(failed_index) is not int or failed_index != len(rows) or not 0 <= failed_index < 17 or
                status_code not in (422, 500) or type(error) is not dict or set(error) != {"code", "message"}):
            raise ValueError("failed sweep: inconsistent prefix, status or error")
        if (error["code"] != ("numerical_failure" if status_code == 422 else "sweep_failed") or
                type(error["message"]) is not str or not 1 <= len(error["message"]) <= 300):
            raise ValueError("failed sweep: expected bounded typed error")
    elif len(rows) != 17 or error is not None or status_code != 200:
        raise ValueError("complete sweep: all seventeen genuine rows required")
    for index, row in enumerate(rows):
        _keys(row, ("index", "phase_rad", "norms", "diagnostics", "analysis"), "sweep row")
        if type(row["index"]) is not int or row["index"] != index or _real(row["phase_rad"], "phase_rad") != phases[index]:
            raise ValueError("sweep rows: expected contiguous requested phase identities")
        check_scalar_records(fixed_experiment, row["norms"], row["diagnostics"], row["analysis"])
    value = {"protocol_version": 1, "message_type": "polarized_two_path_sweep", "request_id": request_id,
        "fixed_experiment_sha256": experiment_digest(fixed_experiment),
        "sweep_sha256": sweep_digest(fixed_experiment, phases_rad), "fixed_experiment": fixed_experiment,
        "phases_rad": list(phases_rad), "status": "failed" if failed else "complete", "requested_count": 17,
        "completed_count": len(rows), "failed_index": failed_index, "rows": rows, "error": error}
    encoded = _json(value)
    if len(encoded) > MAX_SWEEP_RESPONSE_BYTES:
        raise ValueError("sweep response exceeds V2g byte limit")
    return SweepReply(status_code=status_code, body=encoded)
