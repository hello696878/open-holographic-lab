"""Closed bounded W2 JSON transport; no optical tracing or optional imports.

Positions and lengths are metres, directions and relative weights are
dimensionless. This module validates representation and graph relationships;
the public numerical module alone decides optical intersections/reflections.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import uuid

PROTOCOL_VERSION = 1
MODEL_CONTRACT = "w2_ideal_geometric_routing_v1"
MAX_BODY_BYTES = 32_768
MAX_RESPONSE_BYTES = 524_288
LIMITS = {
    "max_elements": 16, "max_interactions": 32, "max_branches": 63,
    "max_records": 256, "max_hits": 128, "max_segments": 256,
    "trace_radius_m": 1.0, "max_distance_m": 10.0,
}
CORE_KEYS = {"scene", "surface_frames", "limits", "status", "branches",
             "segments", "hits", "terminals", "ledger", "diagnostics"}
REPLY_KEYS = CORE_KEYS | {"protocol_version", "message_type", "request_id",
                          "model_contract", "scene_sha256"}
FRAME_KEYS = {"element_id", "u", "v", "n"}
BRANCH_KEYS = {"id", "parent_id", "parent_hit_id", "origin_m",
               "initial_direction", "relative_weight", "start_cumulative_m",
               "start_interaction_count", "outcome"}
SEGMENT_KEYS = {"id", "branch_id", "start_m", "end_m", "direction",
                "relative_weight", "length_m", "cumulative_end_m", "hit_id"}
HIT_KEYS = {"id", "segment_id", "branch_id", "element_id", "position_m",
            "local_uv_m", "incident_direction", "incoming_weight", "outgoing",
            "segment_length_m", "cumulative_length_m", "numerical_bounds"}
TERMINAL_KEYS = {"branch_id", "category", "element_id", "hit_id",
                 "position_m", "cumulative_length_m", "relative_weight", "reason"}
LEDGER_KEYS = {"input_weight", "detected_weight", "absorbed_weight",
               "escaped_weight", "truncated_weight", "signed_residual"}
DIAGNOSTIC_KEYS = {"predicate_policy", "max_direction_norm_residual",
                   "max_frame_orthogonality_residual", "max_plane_residual_m",
                   "max_point_error_bound_m"}
CATEGORIES = {"detected", "absorbed", "escaped", "resource_truncated"}
REASONS = {"receiver_hit", "stop_hit", "domain_exit", "interaction_cap",
            "distance_cap", "branch_cap", "record_cap"}
EPS = sys.float_info.epsilon


def validate_request_id(value: object) -> str:
    """Require a canonical lowercase UUIDv4 for one temporary request."""
    if type(value) is not str:
        raise TypeError("request_id: expected canonical lowercase UUIDv4")
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise ValueError("request_id: expected canonical lowercase UUIDv4") from exc
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError("request_id: expected canonical lowercase UUIDv4")
    return value


def json_bytes(value: object, *, canonical: bool = False) -> bytes:
    """Encode compact strict UTF-8 JSON without scientific rounding."""
    return json.dumps(value, sort_keys=canonical, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def scene_digest(scene: dict[str, object]) -> str:
    """Hash the complete owned scene; element array order is preserved."""
    if type(scene) is not dict:
        raise TypeError("scene: expected plain dictionary")
    return hashlib.sha256(json_bytes(scene, canonical=True)).hexdigest()


def _parse(data: bytes, maximum: int) -> object:
    if type(data) is not bytes:
        raise TypeError("JSON: expected bytes")
    if len(data) > maximum:
        raise ValueError(f"JSON: exceeds {maximum} bytes")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("JSON: duplicate object key")
            result[key] = value
        return result
    def real(token):
        value = float(token)
        coefficient = token.lower().split("e", 1)[0]
        if not math.isfinite(value) or (value == 0 and any(c in "123456789" for c in coefficient)):
            raise ValueError("JSON: number is not usable finite binary64")
        return value
    def integer(token):
        value = int(token)
        if not math.isfinite(float(value)):
            raise ValueError("JSON: integer exceeds finite binary64")
        return value
    def constant(_):
        raise ValueError("JSON: nonfinite constants are forbidden")
    try:
        return json.loads(data.decode("utf-8", errors="strict"),
                          object_pairs_hook=pairs, parse_float=real,
                          parse_int=integer, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError, OverflowError) as exc:
        raise ValueError("JSON: expected bounded strict UTF-8") from exc


def strict_json_loads(data: bytes) -> object:
    """Parse one <=32KiB request, rejecting duplicates/nonfinite/underflow."""
    return _parse(data, MAX_BODY_BYTES)


def _keys(value: object, expected: set[str], name: str) -> dict:
    if type(value) is not dict:
        raise TypeError(f"{name}: expected plain object")
    if set(value) != expected:
        raise ValueError(f"{name}: expected exactly {sorted(expected)}")
    return value


def _number(value: object, name: str, *, minimum: float | None = None,
            maximum: float | None = None) -> float:
    if type(value) not in (int, float):
        raise TypeError(f"{name}: expected finite real excluding bool")
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{name}: not finite binary64") from exc
    if (not math.isfinite(number) or minimum is not None and number < minimum
            or maximum is not None and number > maximum):
        raise ValueError(f"{name}: outside finite supported bounds")
    return number


def _count(value: object, name: str, maximum: int) -> int:
    if type(value) is not int:
        raise TypeError(f"{name}: expected integer excluding bool")
    if not 0 <= value <= maximum:
        raise ValueError(f"{name}: expected 0..{maximum}")
    return value


def _vector(value: object, size: int, name: str) -> list:
    if type(value) is not list or len(value) != size:
        raise ValueError(f"{name}: expected exactly {size} components")
    for part in value:
        _number(part, name)
    return value


def _direction(value: object, name: str, tolerance: float = 128 * EPS) -> list:
    vector = _vector(value, 3, name)
    if abs(math.hypot(*vector) - 1.0) > tolerance:
        raise ValueError(f"{name}: not a supported nominal unit direction")
    return vector


def _identifier(value: object, name: str, *, branch: bool = False) -> str:
    pattern = r"r0(?:\.[TR]){0,31}" if branch else r"[A-Za-z][A-Za-z0-9_.-]{0,63}"
    if type(value) is not str or re.fullmatch(pattern, value, flags=re.ASCII) is None:
        raise ValueError(f"{name}: expected bounded ASCII identifier")
    return value


def validate_digest(value: object) -> str:
    """Require the opaque canonical Python scene SHA256, not a JS rehash."""
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value, flags=re.ASCII) is None:
        raise ValueError("scene_sha256: expected lowercase SHA256")
    return value


def _scene_shape(value: object) -> dict:
    scene = _keys(value, {"schema_version", "model_contract", "source", "elements"}, "scene")
    if type(scene["schema_version"]) is not int or scene["schema_version"] != 1 or scene["model_contract"] != MODEL_CONTRACT:
        raise ValueError("scene: unsupported version/model")
    source = _keys(scene["source"], {"id", "origin_m", "direction", "relative_weight"}, "source")
    if source["id"] != "source" or _number(source["relative_weight"], "source weight") != 1:
        raise ValueError("source: expected one source of relative weight1")
    _vector(source["origin_m"], 3, "source.origin_m")
    if any(abs(v) > 10 for v in source["origin_m"]):
        raise ValueError("source.origin_m: exceeds10m coordinates")
    _direction(source["direction"], "source.direction", 32 * EPS)
    elements = scene["elements"]
    if type(elements) is not list or len(elements) > 16:
        raise ValueError("elements: expected at most16 records")
    ids = set()
    for raw in elements:
        item = _keys(raw, {"id", "kind", "pose", "aperture"}, "element")
        identifier = _identifier(item["id"], "element.id")
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", identifier, flags=re.ASCII) is None:
            raise ValueError("element.id: expected ASCII identifier without periods")
        if identifier == "source" or identifier in ids:
            raise ValueError("elements: duplicate/reserved identifier")
        ids.add(identifier)
        if item["kind"] not in {"mirror", "ideal_splitter_50_50", "beam_stop", "receiver"}:
            raise ValueError("element: unsupported kind")
        pose = _keys(item["pose"], {"position_m", "rotation_xyz_rad"}, "pose")
        _vector(pose["position_m"], 3, "pose.position_m")
        _vector(pose["rotation_xyz_rad"], 3, "pose.rotation_xyz_rad")
        if any(abs(angle) > math.pi for angle in pose["rotation_xyz_rad"]):
            raise ValueError("pose.rotation_xyz_rad: expected angles in [-pi,pi]")
        aperture = item["aperture"]
        if type(aperture) is not dict:
            raise TypeError("aperture: expected object")
        if aperture.get("kind") == "disk":
            _keys(aperture, {"kind", "radius_m"}, "disk")
            names = ("radius_m",)
        elif aperture.get("kind") == "rectangle":
            _keys(aperture, {"kind", "width_m", "height_m"}, "rectangle")
            names = ("width_m", "height_m")
        else:
            raise ValueError("aperture: unsupported finite shape")
        for name in names:
            _number(aperture[name], name, minimum=1e-6, maximum=.25)
    return scene


def _frames(value: object, scene: dict) -> None:
    if type(value) is not list or len(value) != len(scene["elements"]):
        raise ValueError("surface_frames: expected every submitted element once")
    for frame, element in zip(value, scene["elements"]):
        _keys(frame, FRAME_KEYS, "surface_frame")
        if frame["element_id"] != element["id"]:
            raise ValueError("surface_frames: wrong ordered element identity")
        for axis in ("u", "v", "n"):
            _direction(frame[axis], "surface_frame." + axis, 64 * EPS)
        u, v, n = (frame[axis] for axis in ("u", "v", "n"))
        if any(abs(math.fsum(a*b for a, b in zip(left, right))) > 64 * EPS
               for left, right in ((u, v), (u, n), (v, n))):
            raise ValueError("surface_frame: nonorthogonal returned axes")
        cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
        if any(abs(a-b) > 64 * EPS for a, b in zip(cross, n)):
            raise ValueError("surface_frame: returned axes have wrong handedness")


def encode_validation_reply(request_id: str, scene: dict, surface_frames: list[dict]) -> bytes:
    """Encode a pure validation response; this function performs no trace."""
    validate_request_id(request_id)
    _scene_shape(scene)
    _frames(surface_frames, scene)
    result = {"protocol_version": 1, "message_type": "scene_validation",
              "request_id": request_id, "model_contract": MODEL_CONTRACT,
              "scene_sha256": scene_digest(scene), "scene": scene,
              "surface_frames": surface_frames}
    encoded = json_bytes(result)
    if len(encoded) > MAX_RESPONSE_BYTES:
        raise ValueError("validation response exceeds512KiB")
    return encoded


def _records(value: object, maximum: int, expected: set[str], name: str,
             *, id_key: str = "id", branch_ids: bool = False) -> dict[str, dict]:
    if type(value) is not list or len(value) > maximum:
        raise ValueError(f"{name}: incorrect list or cap")
    records = {}
    for record in value:
        _keys(record, expected, name)
        identifier = _identifier(record[id_key], name + "." + id_key, branch=branch_ids)
        if identifier in records:
            raise ValueError(name + ": duplicate identity")
        records[identifier] = record
    return records


def _intervals(value: object, rows: int, name: str) -> list:
    if type(value) is not list or len(value) != rows:
        raise ValueError(name + ": incorrect interval shape")
    for row in value:
        _vector(row, 2, name)
        if row[0] > row[1]:
            raise ValueError(name + ": reversed interval")
    return value


def validate_trace_reply(value: object, *, request_id: str | None = None,
                         scene: dict | None = None, scene_sha256: str | None = None) -> dict:
    """Validate the complete closed graph/identity without tracing optics."""
    reply = _keys(value, REPLY_KEYS, "trace reply")
    if (type(reply["protocol_version"]) is not int or reply["protocol_version"] != 1
            or reply["message_type"] != "trace_result" or reply["model_contract"] != MODEL_CONTRACT):
        raise ValueError("trace reply: version/model/discriminator mismatch")
    validate_request_id(reply["request_id"])
    actual_scene = _scene_shape(reply["scene"])
    actual_digest = scene_digest(actual_scene)
    if validate_digest(reply["scene_sha256"]) != actual_digest:
        raise ValueError("trace reply: scene digest mismatch")
    if request_id is not None and reply["request_id"] != request_id:
        raise ValueError("trace reply: request identity mismatch")
    if scene_sha256 is not None and actual_digest != scene_sha256:
        raise ValueError("trace reply: submitted digest mismatch")
    if scene is not None and json_bytes(actual_scene, canonical=True) != json_bytes(scene, canonical=True):
        raise ValueError("trace reply: submitted scene mismatch")
    _frames(reply["surface_frames"], actual_scene)
    _keys(reply["limits"], set(LIMITS), "limits")
    for key, expected in LIMITS.items():
        _number(reply["limits"][key], "limits." + key)
        if reply["limits"][key] != expected:
            raise ValueError("limits: changed model cap")
    branches = _records(reply["branches"], 63, BRANCH_KEYS, "branches", branch_ids=True)
    segments = _records(reply["segments"], 256, SEGMENT_KEYS, "segments")
    hits = _records(reply["hits"], 128, HIT_KEYS, "hits")
    terminals = _records(reply["terminals"], 63, TERMINAL_KEYS, "terminals",
                         id_key="branch_id", branch_ids=True)
    if len(segments) + len(hits) > 256 or not branches or next(iter(branches)) != "r0":
        raise ValueError("trace: record/root cap mismatch")
    if (list(segments) != [f"s{index:04d}" for index in range(len(segments))]
            or list(hits) != [f"h{index:04d}" for index in range(len(hits))]):
        raise ValueError("trace: unstable segment/hit ordinal identities")
    elements = {item["id"]: item for item in actual_scene["elements"]}
    seen = set()
    for identifier, branch in branches.items():
        _vector(branch["origin_m"], 3, "branch.origin_m")
        _direction(branch["initial_direction"], "branch.initial_direction")
        _number(branch["relative_weight"], "branch.weight", minimum=0, maximum=1)
        if branch["relative_weight"] <= 0:
            raise ValueError("branch: weight must remain positive")
        _number(branch["start_cumulative_m"], "branch.start_cumulative_m", minimum=0, maximum=10)
        _count(branch["start_interaction_count"], "branch.start_interaction_count", 32)
        if branch["outcome"] not in CATEGORIES | {"split"}:
            raise ValueError("branch: unsupported outcome")
        if identifier == "r0":
            if (branch["parent_id"] is not None or branch["parent_hit_id"] is not None
                    or branch["origin_m"] != actual_scene["source"]["origin_m"]
                    or branch["initial_direction"] != actual_scene["source"]["direction"]
                    or branch["relative_weight"] != 1 or branch["start_cumulative_m"] != 0
                    or branch["start_interaction_count"] != 0):
                raise ValueError("root: inconsistent submitted source")
        else:
            parent = branch["parent_id"]
            if parent not in seen or identifier not in (parent + ".T", parent + ".R"):
                raise ValueError("branch: invalid/cyclic/nonparent-first identity")
            if branch["parent_hit_id"] not in hits:
                raise ValueError("branch: missing parent hit")
            parent_hit = hits[branch["parent_hit_id"]]
            if branches[parent]["outcome"] != "split" or parent_hit["branch_id"] != parent:
                raise ValueError("branch: parent is not its actual split")
        seen.add(identifier)
    by_branch = {key: [] for key in branches}
    for segment in segments.values():
        if segment["branch_id"] not in branches:
            raise ValueError("segment: unknown branch")
        _vector(segment["start_m"], 3, "segment.start_m")
        _vector(segment["end_m"], 3, "segment.end_m")
        _direction(segment["direction"], "segment.direction")
        _number(segment["relative_weight"], "segment.weight", minimum=0, maximum=1)
        _number(segment["length_m"], "segment.length_m", minimum=0, maximum=10 + 128 * EPS)
        if segment["length_m"] <= 0:
            raise ValueError("segment: physical travel must have positive length")
        _number(segment["cumulative_end_m"], "segment.cumulative_end_m", minimum=0, maximum=10 + 128 * EPS)
        if segment["relative_weight"] != branches[segment["branch_id"]]["relative_weight"]:
            raise ValueError("segment: branch weight mismatch")
        if segment["hit_id"] is not None and segment["hit_id"] not in hits:
            raise ValueError("segment: missing hit")
        by_branch[segment["branch_id"]].append(segment)
    for identifier, hit in hits.items():
        if hit["segment_id"] not in segments or hit["element_id"] not in elements or hit["branch_id"] not in branches:
            raise ValueError("hit: unknown segment/element/branch")
        segment = segments[hit["segment_id"]]
        if (segment["hit_id"] != identifier or segment["branch_id"] != hit["branch_id"]
                or segment["end_m"] != hit["position_m"] or segment["direction"] != hit["incident_direction"]
                or segment["relative_weight"] != hit["incoming_weight"]
                or segment["length_m"] != hit["segment_length_m"]
                or segment["cumulative_end_m"] != hit["cumulative_length_m"]):
            raise ValueError("hit: segment relationship mismatch")
        _vector(hit["position_m"], 3, "hit.position_m")
        _vector(hit["local_uv_m"], 2, "hit.local_uv_m")
        _direction(hit["incident_direction"], "hit.incident_direction")
        _number(hit["incoming_weight"], "hit.incoming_weight", minimum=0, maximum=1)
        bounds = _keys(hit["numerical_bounds"], {"t_parameter_interval_m", "position_intervals_m",
                        "local_uv_intervals_m", "plane_residual_m"}, "numerical_bounds")
        _intervals([bounds["t_parameter_interval_m"]], 1, "t parameter")
        if bounds["t_parameter_interval_m"][0] <= 0:
            raise ValueError("hit: positive forward interval was not certified")
        points = _intervals(bounds["position_intervals_m"], 3, "point intervals")
        local = _intervals(bounds["local_uv_intervals_m"], 2, "local intervals")
        _number(bounds["plane_residual_m"], "plane residual")
        if any(not bound[0] <= v <= bound[1] for v, bound in zip(hit["position_m"], points)):
            raise ValueError("hit: nominal point outside enclosure")
        if any(not bound[0] <= v <= bound[1] for v, bound in zip(hit["local_uv_m"], local)):
            raise ValueError("hit: nominal local coordinate outside enclosure")
        outgoing = hit["outgoing"]
        if type(outgoing) is not list or len(outgoing) > 2:
            raise ValueError("hit: outgoing cardinality")
        for child in outgoing:
            _keys(child, {"branch_id", "direction", "relative_weight"}, "outgoing")
            _direction(child["direction"], "outgoing.direction")
            _number(child["relative_weight"], "outgoing.weight", minimum=0, maximum=1)
            if child["branch_id"] not in branches:
                raise ValueError("outgoing: missing branch")
        kind = elements[hit["element_id"]]["kind"]
        if kind in {"receiver", "beam_stop"} and outgoing:
            raise ValueError("terminating hit: has outgoing branch")
        if kind == "mirror" and (len(outgoing) != 1 or outgoing[0]["branch_id"] != hit["branch_id"]
                or outgoing[0]["relative_weight"] != hit["incoming_weight"]):
            raise ValueError("mirror: inconsistent same-branch reflection")
        if kind == "ideal_splitter_50_50" and outgoing:
            expected = [hit["branch_id"] + ".T", hit["branch_id"] + ".R"]
            if [child["branch_id"] for child in outgoing] != expected or branches[hit["branch_id"]]["outcome"] != "split":
                raise ValueError("splitter: wrong child identities/order")
            if outgoing[0]["direction"] != hit["incident_direction"]:
                raise ValueError("splitter: transmitted direction must retain the incident direction")
            for child in outgoing:
                branch = branches[child["branch_id"]]
                if (child["relative_weight"] != hit["incoming_weight"] * .5
                        or branch["relative_weight"] != child["relative_weight"]
                        or branch["parent_id"] != hit["branch_id"] or branch["parent_hit_id"] != identifier
                        or branch["origin_m"] != hit["position_m"]
                        or branch["initial_direction"] != child["direction"]
                        or branch["start_cumulative_m"] != hit["cumulative_length_m"]):
                    raise ValueError("splitter: lost/duplicated/incorrect child state")
    expected_creation_order = ["r0"]
    for hit in hits.values():
        if len(hit["outgoing"]) == 2:
            expected_creation_order.extend(child["branch_id"] for child in hit["outgoing"])
    if list(branches) != expected_creation_order:
        raise ValueError("branches: not stable breadth-first atomic T/R creation order")
    for identifier, branch in branches.items():
        path = by_branch[identifier]
        point, direction, cumulative = branch["origin_m"], branch["initial_direction"], branch["start_cumulative_m"]
        interactions = branch["start_interaction_count"]
        for segment_index, segment in enumerate(path):
            if segment["hit_id"] is None and segment_index != len(path) - 1:
                raise ValueError("branch: nonhit endpoint cannot continue")
            actual_length = math.hypot(*(b - a for a, b in zip(segment["start_m"], segment["end_m"])))
            if abs(actual_length - segment["length_m"]) > 128 * EPS * max(1, actual_length):
                raise ValueError("segment: length disagrees with its actual endpoints")
            if segment["start_m"] != point or segment["direction"] != direction:
                raise ValueError("branch: disconnected segment chain")
            if abs(segment["cumulative_end_m"] - (cumulative + segment["length_m"])) > 128 * EPS * max(1, segment["cumulative_end_m"]):
                raise ValueError("branch: inconsistent accumulated distance")
            point, cumulative = segment["end_m"], segment["cumulative_end_m"]
            if segment["hit_id"] is not None:
                interactions += 1
                outgoing = hits[segment["hit_id"]]["outgoing"]
                if segment_index != len(path) - 1 and (len(outgoing) != 1
                        or outgoing[0]["branch_id"] != identifier):
                    raise ValueError("branch: a terminating or split hit cannot continue")
                if len(outgoing) == 1:
                    direction = outgoing[0]["direction"]
            if interactions > 32:
                raise ValueError("branch: exceeded inherited interaction cap")
        if branch["outcome"] == "split":
            if identifier in terminals or not path or path[-1]["hit_id"] is None:
                raise ValueError("split parent: must not be another terminal")
            last = hits[path[-1]["hit_id"]]
            if len(last["outgoing"]) != 2:
                raise ValueError("split parent: missing atomic child pair")
            for child in last["outgoing"]:
                if branches[child["branch_id"]]["start_interaction_count"] != interactions:
                    raise ValueError("splitter: inherited interaction count mismatch")
        elif identifier not in terminals:
            raise ValueError("branch: unaccounted unresolved weight")
        if identifier in terminals:
            terminal = terminals[identifier]
            if terminal["position_m"] != point or terminal["cumulative_length_m"] != cumulative:
                raise ValueError("terminal: changed actual endpoint/distance")
            if terminal["category"] in {"detected", "absorbed"} and (
                    not path or path[-1]["hit_id"] != terminal["hit_id"]):
                raise ValueError("terminal: detection/absorption must be the final actual hit")
            if terminal["category"] == "escaped" and (not path or path[-1]["hit_id"] is not None):
                raise ValueError("terminal: escape requires an actual nonhit endpoint")
            if terminal["category"] == "resource_truncated":
                if terminal["reason"] == "interaction_cap" and interactions != 32:
                    raise ValueError("terminal: interaction cap precedes its inherited limit")
                if terminal["reason"] == "distance_cap" and abs(cumulative-10.) > 128 * EPS * 10:
                    raise ValueError("terminal: distance cap precedes its cumulative limit")
                last_hit = next((part["hit_id"] for part in reversed(path)
                                 if part["hit_id"] is not None), branch["parent_hit_id"])
                if terminal["hit_id"] != last_hit:
                    raise ValueError("terminal: truncation must retain its last actual hit")
                if last_hit is not None and elements[hits[last_hit]["element_id"]]["kind"] in {"receiver", "beam_stop"}:
                    raise ValueError("terminal: receiver/stop termination precedes resource caps")
    category_weights = {name: [] for name in CATEGORIES}
    for identifier, terminal in terminals.items():
        if identifier not in branches or terminal["category"] != branches[identifier]["outcome"]:
            raise ValueError("terminal: wrong branch/category")
        category = terminal["category"]
        _vector(terminal["position_m"], 3, "terminal.position_m")
        _number(terminal["cumulative_length_m"], "terminal.cumulative_length_m", minimum=0, maximum=10 + 128 * EPS)
        weight = _number(terminal["relative_weight"], "terminal.weight", minimum=0, maximum=1)
        if weight != branches[identifier]["relative_weight"] or terminal["reason"] not in REASONS:
            raise ValueError("terminal: changed weight/reason")
        radius = math.hypot(*(a-b for a, b in zip(terminal["position_m"], actual_scene["source"]["origin_m"])))
        if radius > 1 + 2e-12 or category == "escaped" and abs(radius-1.) > 2e-13:
            raise ValueError("terminal: actual endpoint violates the source-centred trace-domain bound")
        if category in {"detected", "absorbed"}:
            if terminal["hit_id"] not in hits or terminal["element_id"] not in elements:
                raise ValueError("terminal: fabricated detector/stop")
            hit = hits[terminal["hit_id"]]
            kind, reason = ("receiver", "receiver_hit") if category == "detected" else ("beam_stop", "stop_hit")
            if (elements[terminal["element_id"]]["kind"] != kind or terminal["reason"] != reason
                    or hit["element_id"] != terminal["element_id"] or hit["branch_id"] != identifier
                    or hit["position_m"] != terminal["position_m"]):
                raise ValueError("terminal: wrong physical hit identity")
        elif category == "escaped":
            if terminal["reason"] != "domain_exit" or terminal["element_id"] is not None or terminal["hit_id"] is not None:
                raise ValueError("escape: must not fabricate a detector")
        elif category == "resource_truncated":
            if terminal["reason"] not in {"interaction_cap", "distance_cap", "branch_cap", "record_cap"}:
                raise ValueError("truncation: cannot be absorption")
            if terminal["hit_id"] is not None and terminal["hit_id"] not in hits:
                raise ValueError("truncation: unknown retained hit")
            if terminal["element_id"] is not None and terminal["element_id"] not in elements:
                raise ValueError("truncation: unknown retained element")
            if (terminal["hit_id"] is None) != (terminal["element_id"] is None):
                raise ValueError("truncation: retained hit and element must agree")
            if terminal["hit_id"] is not None and hits[terminal["hit_id"]]["element_id"] != terminal["element_id"]:
                raise ValueError("truncation: changed retained element identity")
        category_weights[category].append(weight)
    incomplete = bool(category_weights["resource_truncated"])
    if reply["status"] != ("incomplete" if incomplete else "complete"):
        raise ValueError("trace: hidden resource truncation")
    ledger = _keys(reply["ledger"], LEDGER_KEYS, "ledger")
    for key, value in ledger.items():
        _number(value, "ledger." + key)
    if ledger["input_weight"] != 1:
        raise ValueError("ledger: source weight changed")
    for category, key in (("detected", "detected_weight"), ("absorbed", "absorbed_weight"),
                           ("escaped", "escaped_weight"), ("resource_truncated", "truncated_weight")):
        if abs(ledger[key] - math.fsum(category_weights[category])) > 64 * EPS:
            raise ValueError("ledger: category weight mismatch")
    residual = 1 - math.fsum(t["relative_weight"] for t in terminals.values())
    if abs(residual) > 64 * EPS or abs(ledger["signed_residual"] - residual) > 64 * EPS:
        raise ValueError("ledger: missing/doubled terminal weight")
    diagnostic = _keys(reply["diagnostics"], DIAGNOSTIC_KEYS, "diagnostics")
    if diagnostic["predicate_policy"] != "binary64_outward_intervals_v1":
        raise ValueError("diagnostics: wrong predicate policy")
    for key in DIAGNOSTIC_KEYS - {"predicate_policy"}:
        _number(diagnostic[key], "diagnostics." + key, minimum=0)
    if (diagnostic["max_direction_norm_residual"] > 128 * EPS
            or diagnostic["max_frame_orthogonality_residual"] > 64 * EPS):
        raise ValueError("diagnostics: unsupported direction/frame residual")
    return reply


def encode_trace_result(request_id: str, scene_sha256: str, result: dict) -> bytes:
    """Validate/encode one immutable public result inside actual worker lifetime."""
    validate_request_id(request_id)
    validate_digest(scene_sha256)
    _keys(result, CORE_KEYS, "core result")
    reply = {"protocol_version": 1, "message_type": "trace_result",
             "request_id": request_id, "model_contract": MODEL_CONTRACT,
             "scene_sha256": scene_sha256, **result}
    validate_trace_reply(reply, request_id=request_id, scene_sha256=scene_sha256)
    encoded = json_bytes(reply)
    if len(encoded) > MAX_RESPONSE_BYTES:
        raise ValueError("trace response exceeds524288-byte limit")
    return encoded


def decode_trace_result(data: bytes, **identity) -> dict:
    """Inspect a bounded genuine response for API evidence, never rerun optics."""
    return validate_trace_reply(_parse(data, MAX_RESPONSE_BYTES), **identity)


def error_reply(request_id: str | None, code: str, message: str) -> bytes:
    """Encode a bounded English error without returning partial trace data."""
    if request_id is not None:
        validate_request_id(request_id)
    if type(code) is not str or re.fullmatch(r"[a-z][a-z0-9_]{0,63}", code, flags=re.ASCII) is None:
        raise ValueError("error code: expected bounded ASCII token")
    if type(message) is not str:
        raise TypeError("error message: expected string")
    return json_bytes({"protocol_version": 1, "message_type": "routing_error",
                       "request_id": request_id, "model_contract": MODEL_CONTRACT,
                       "error": {"code": code, "message": message[:300]}})
