"""Closed W3 transport and graph/medium admission before atomic publication.

This module does not trace optics. Positions and residuals are metres, angles
are radians, directions/indices/ideal bookkeeping weights are dimensionless.
The unchanged public W2 representation validator protects the lossless
body-free projection as well as its original API.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re

from . import geometric_routing_protocol as w2
from .geometric_routing_protocol import (
    EPS, json_bytes, scene_digest, strict_json_loads, validate_digest,
    validate_request_id,
)

PROTOCOL_VERSION = 1
MODEL_CONTRACT = "w3_ideal_refractive_routing_v1"
WEIGHT_MODEL = "ideal_route_weights_no_fresnel_v1"
MAX_BODY_BYTES = 32_768
MAX_RESPONSE_BYTES = 524_288
LIMITS = {"max_bodies": 1, "max_body_faces": 6, "max_legacy_elements": 16,
          "max_total_optical_faces": 16, "max_interactions": 32, "max_branches": 31,
          "max_records": 128, "max_events": 64, "max_segments": 128,
          "trace_radius_m": 1.0, "max_distance_m": 10.0}
NO_BODY_LIMITS = {**LIMITS, "max_branches": 63, "max_records": 256,
                  "max_events": 128, "max_segments": 256}
METADATA_KEYS = {"scene", "weight_model", "media", "body_faces", "legacy_surface_frames", "limits"}
CORE_KEYS = METADATA_KEYS | {"status", "branches", "segments", "events", "terminals", "ledger", "diagnostics"}
ENVELOPE_KEYS = {"protocol_version", "message_type", "request_id", "model_contract", "scene_sha256"}
VALIDATION_KEYS = ENVELOPE_KEYS | METADATA_KEYS
REPLY_KEYS = ENVELOPE_KEYS | CORE_KEYS
FACE_KEYS = {"body_id", "face_id", "vertices_m", "plane_covector", "outward_normal", "local_origin_m", "local_basis", "numerical_bounds"}
FACE_BOUNDS = {"vertex_intervals_m", "covector_intervals", "normal_intervals", "basis_u_intervals", "basis_v_intervals"}
BRANCH_KEYS = {"id", "parent_id", "parent_event_id", "origin_m", "initial_direction", "initial_medium_id", "initial_refractive_index", "relative_weight", "start_cumulative_m", "start_interaction_count", "outcome"}
SEGMENT_KEYS = {"id", "branch_id", "start_m", "end_m", "direction", "medium_id", "refractive_index", "relative_weight", "length_m", "cumulative_end_m", "event_id"}
EVENT_KEYS = {"id", "segment_id", "branch_id", "target", "classification", "position_m", "local_uv_m", "incident_direction", "incident_medium_id", "incident_refractive_index", "incoming_weight", "outgoing", "segment_length_m", "cumulative_length_m", "numerical_bounds"}
DIELECTRIC_KEYS = {"outward_normal", "local_basis", "incident_angle_rad", "outgoing_angle_rad"}
COMMON_BOUNDS = {"t_parameter_interval_m", "position_intervals_m", "local_uv_intervals_m", "incident_direction_intervals", "outgoing_direction_intervals", "cumulative_length_interval_m", "plane_residual_m"}
DIELECTRIC_BOUNDS = {"snell_discriminant_interval", "incident_side_interval", "outgoing_side_interval", "body_halfspace_intervals_m"}
OUTGOING_KEYS = {"branch_id", "direction", "medium_id", "refractive_index", "relative_weight"}
TERMINAL_KEYS = {"branch_id", "category", "element_id", "event_id", "position_m", "medium_id", "refractive_index", "cumulative_length_m", "relative_weight", "reason"}
LEDGER_KEYS = {"input_weight", "detected_weight", "absorbed_weight", "escaped_weight", "truncated_weight", "signed_residual"}
DIAGNOSTIC_KEYS = {"predicate_policy", "max_direction_norm_residual", "max_frame_residual", "max_plane_residual_m", "max_point_width_m", "max_direction_width"}
CATEGORIES = {"detected", "absorbed", "escaped", "resource_truncated"}
REASONS = {"receiver_hit", "stop_hit", "domain_exit", "interaction_cap", "distance_cap", "branch_cap", "record_cap"}
ERROR_CODES = {"invalid_scene", "numerical_ambiguity", "medium_state_ambiguity", "unsupported_numerical_input", "numerical_failure", "busy", "request_body_too_large", "encoding_failed", "response_too_large", "trace_failed", "disconnected", "cancelled_before_start", "submission_failed"}
FACE_IDS = {"rectangular_block": ("x_min", "x_max", "y_min", "y_max", "z_min", "z_max"),
            "right_triangular_prism": ("x_min", "z_min", "hypotenuse", "y_min", "y_max")}
LEGACY_CLASS = {"mirror": "mirror_reflection", "ideal_splitter_50_50": "ideal_split", "beam_stop": "stop_hit", "receiver": "receiver_hit"}


def _keys(value: object, keys: set[str], name: str) -> dict:
    if type(value) is not dict:
        raise TypeError(f"{name}: expected plain object")
    if set(value) != keys:
        raise ValueError(f"{name}: expected exactly {sorted(keys)}")
    return value


def _number(value: object, name: str, minimum=None, maximum=None) -> float:
    if type(value) not in (int, float):
        raise TypeError(f"{name}: expected finite real excluding bool")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name}: not finite binary64") from exc
    if not math.isfinite(result) or minimum is not None and result < minimum or maximum is not None and result > maximum:
        raise ValueError(f"{name}: outside finite supported bounds")
    return result


def _vector(value: object, size: int, name: str) -> list:
    if type(value) is not list or len(value) != size:
        raise ValueError(f"{name}: expected {size} components")
    for item in value:
        _number(item, name)
    return value


def _direction(value: object, name: str) -> list:
    vector = _vector(value, 3, name)
    if abs(math.hypot(*vector) - 1) > 128 * EPS:
        raise ValueError(f"{name}: unsupported direction norm")
    return vector


def _identifier(value: object, name: str, *, branch: bool = False) -> str:
    pattern = r"r0(?:\.[TR]){0,31}" if branch else r"[A-Za-z][A-Za-z0-9_.-]{0,63}"
    if type(value) is not str or re.fullmatch(pattern, value, flags=re.ASCII) is None:
        raise ValueError(f"{name}: expected bounded ASCII identity")
    return value


def _intervals(value: object, size: int, name: str, nominal=None, *, width=False) -> list:
    if type(value) is not list or len(value) != size:
        raise ValueError(f"{name}: incorrect interval shape")
    for index, row in enumerate(value):
        _vector(row, 2, name)
        if row[0] > row[1] or width and row[1] - row[0] > 1e-8:
            raise ValueError(f"{name}: reversed or unsupported enclosure width")
        if nominal is not None and not row[0] <= nominal[index] <= row[1]:
            raise ValueError(f"{name}: nominal value outside enclosure")
    return value


def _interval(value: object, name: str, nominal=None) -> list:
    return _intervals([value], 1, name, None if nominal is None else [nominal])[0]


def _records(value: object, maximum: int, name: str, keys=None, *, id_key="id", branch=False) -> dict:
    if type(value) is not list or len(value) > maximum:
        raise ValueError(f"{name}: incorrect list or cap")
    result = {}
    for item in value:
        if keys is not None:
            _keys(item, keys, name)
        if type(item) is not dict or id_key not in item:
            raise ValueError(f"{name}: missing record identity")
        key = _identifier(item[id_key], name, branch=branch)
        if key in result:
            raise ValueError(f"{name}: duplicate identity")
        result[key] = item
    return result


def _legacy_scene(scene: dict) -> dict:
    return {"schema_version": scene["schema_version"], "model_contract": w2.MODEL_CONTRACT,
            "source": scene["source"], "elements": scene["elements"]}


def _scene(value: object) -> dict:
    scene = _keys(value, {"schema_version", "model_contract", "source", "exterior_medium", "bodies", "elements"}, "scene")
    if type(scene["schema_version"]) is not int or scene["schema_version"] != 1 or scene["model_contract"] != MODEL_CONTRACT:
        raise ValueError("scene: unsupported version/model")
    exterior = _keys(scene["exterior_medium"], {"id", "refractive_index"}, "exterior_medium")
    if exterior["id"] != "exterior":
        raise ValueError("exterior_medium: wrong identity")
    _number(exterior["refractive_index"], "exterior index", 1, 2.5)
    bodies = scene["bodies"]
    if type(bodies) is not list or len(bodies) > 1:
        raise ValueError("bodies: expected at most one closed body")
    for body in bodies:
        _keys(body, {"id", "kind", "pose", "shape", "interior_medium"}, "body")
        if type(body["id"]) is not str or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", body["id"], flags=re.ASCII) is None:
            raise ValueError("body: invalid identity")
        if body["kind"] not in FACE_IDS:
            raise ValueError("body: unsupported family")
        pose = _keys(body["pose"], {"position_m", "rotation_xyz_rad"}, "body pose")
        _vector(pose["position_m"], 3, "body position")
        _vector(pose["rotation_xyz_rad"], 3, "body rotation")
        if any(abs(v) > 10 for v in pose["position_m"]) or any(abs(v) > math.pi for v in pose["rotation_xyz_rad"]):
            raise ValueError("body pose: unsupported bounds")
        dimensions = {"width_x_m", "height_y_m", "depth_z_m"} if body["kind"] == "rectangular_block" else {"leg_x_m", "leg_z_m", "height_y_m"}
        for dimension in _keys(body["shape"], dimensions, "body shape").values():
            _number(dimension, "body dimension", .0001, .25)
        medium = _keys(body["interior_medium"], {"id", "refractive_index"}, "interior medium")
        if medium["id"] != "body:" + body["id"]:
            raise ValueError("body: wrong interior medium identity")
        _number(medium["refractive_index"], "interior index", 1, 2.5)
    return scene


def _metadata(reply: dict) -> tuple[dict, dict, dict, dict]:
    scene = _scene(reply["scene"])
    if reply["weight_model"] != WEIGHT_MODEL:
        raise ValueError("weight_model: unsupported physical claim")
    # Public W2 transport validation protects its closed source/element records
    # and old frame policy; this call performs no numerical trace.
    w2.encode_validation_reply(reply["request_id"], _legacy_scene(scene), reply["legacy_surface_frames"])
    expected_media = [scene["exterior_medium"], *[body["interior_medium"] for body in scene["bodies"]]]
    if type(reply["media"]) is not list or reply["media"] != expected_media:
        raise ValueError("media: must preserve each declared identity and index")
    for record in reply["media"]:
        _keys(record, {"id", "refractive_index"}, "medium record")
        _number(record["refractive_index"], "medium index", 1, 2.5)
    media = {item["id"]: item["refractive_index"] for item in expected_media}
    limits = LIMITS if scene["bodies"] else NO_BODY_LIMITS
    _keys(reply["limits"], set(limits), "limits")
    for key, expected in limits.items():
        _number(reply["limits"][key], "limits." + key)
        if reply["limits"][key] != expected:
            raise ValueError("limits: changed conditional model cap")
    expected_faces = [(body, face) for body in scene["bodies"] for face in FACE_IDS[body["kind"]]]
    if type(reply["body_faces"]) is not list or len(reply["body_faces"]) != len(expected_faces):
        raise ValueError("body_faces: missing or extra finite boundary")
    if len(expected_faces) + len(scene["elements"]) > 16:
        raise ValueError("scene: total optical face cap exceeded")
    faces = {}
    for record, (body, face_id) in zip(reply["body_faces"], expected_faces):
        _keys(record, FACE_KEYS, "body face")
        if record["body_id"] != body["id"] or record["face_id"] != face_id:
            raise ValueError("body_faces: wrong canonical ordered face identity")
        vertices = record["vertices_m"]
        count = 3 if body["kind"] == "right_triangular_prism" and face_id in {"y_min", "y_max"} else 4
        if type(vertices) is not list or len(vertices) != count:
            raise ValueError("body face: incorrect triangle/rectangle vertex count")
        for vertex in vertices:
            _vector(vertex, 3, "face vertex")
        _vector(record["plane_covector"], 3, "plane covector")
        if math.hypot(*record["plane_covector"]) == 0:
            raise ValueError("face: zero plane covector")
        _direction(record["outward_normal"], "outward normal")
        _vector(record["local_origin_m"], 3, "face local origin")
        basis = _keys(record["local_basis"], {"u", "v"}, "face local basis")
        _vector(basis["u"], 3, "face u")
        _vector(basis["v"], 3, "face v")
        bounds = _keys(record["numerical_bounds"], FACE_BOUNDS, "face bounds")
        if type(bounds["vertex_intervals_m"]) is not list or len(bounds["vertex_intervals_m"]) != count:
            raise ValueError("face: missing vertex enclosure")
        for vertex, intervals in zip(vertices, bounds["vertex_intervals_m"]):
            _intervals(intervals, 3, "vertex intervals", vertex, width=True)
        for key, nominal in (("covector_intervals", record["plane_covector"]),
                             ("normal_intervals", record["outward_normal"]),
                             ("basis_u_intervals", basis["u"]), ("basis_v_intervals", basis["v"])):
            _intervals(bounds[key], 3, key, nominal)
        faces[(body["id"], face_id)] = record
    return scene, media, faces, limits


def _envelope(value: object, keys: set[str], message_type: str, *, request_id=None, scene=None, scene_sha256=None) -> dict:
    reply = _keys(value, keys, message_type)
    if type(reply["protocol_version"]) is not int or reply["protocol_version"] != 1 or reply["message_type"] != message_type or reply["model_contract"] != MODEL_CONTRACT:
        raise ValueError("reply: version/model/discriminator mismatch")
    validate_request_id(reply["request_id"])
    actual_digest = scene_digest(reply["scene"])
    if validate_digest(reply["scene_sha256"]) != actual_digest:
        raise ValueError("reply: complete scene digest mismatch")
    if request_id is not None and reply["request_id"] != request_id:
        raise ValueError("reply: request identity mismatch")
    if scene_sha256 is not None and actual_digest != validate_digest(scene_sha256):
        raise ValueError("reply: submitted scene digest mismatch")
    if scene is not None and json_bytes(scene, canonical=True) != json_bytes(reply["scene"], canonical=True):
        raise ValueError("reply: submitted scene identity mismatch")
    return reply


def validate_validation_reply(value: object, **identity) -> dict:
    """Validate closed pure-admission metadata, without any optical operation."""
    reply = _envelope(value, VALIDATION_KEYS, "refractive_scene_validation", **identity)
    _metadata(reply)
    return reply


def _bounded(value: object) -> bytes:
    encoded = json_bytes(value)
    if len(encoded) > MAX_RESPONSE_BYTES:
        raise ValueError("W3 response exceeds524288-byte limit")
    return encoded


def encode_validation_reply(request_id: str, scene: dict, *, media: list, body_faces: list,
                            legacy_surface_frames: list, limits: dict) -> bytes:
    """Encode admitted body/medium metadata; this function never traces."""
    reply = {"protocol_version": 1, "message_type": "refractive_scene_validation",
             "model_contract": MODEL_CONTRACT, "request_id": request_id,
             "scene_sha256": scene_digest(scene), "scene": scene,
             "weight_model": WEIGHT_MODEL, "media": media, "body_faces": body_faces,
             "legacy_surface_frames": legacy_surface_frames, "limits": limits}
    validate_validation_reply(reply)
    return _bounded(reply)


def project_w2_result(value: dict) -> dict:
    """Losslessly project a validated body-free W3 result to ten W2 core keys.

Literal W2 IDs, numerical values, bounds, errors and conditional caps are not
renumbered or recomputed. W3 supplemental certificate metadata is stripped.
"""
    if value["scene"]["bodies"]:
        raise ValueError("W2 projection requires an empty body list")
    result = {"scene": _legacy_scene(deepcopy(value["scene"])),
              "surface_frames": deepcopy(value["legacy_surface_frames"]),
              "limits": {key: value["limits"][{"max_elements": "max_legacy_elements", "max_hits": "max_events"}.get(key, key)] for key in w2.LIMITS},
              "status": value["status"], "branches": [], "segments": [], "hits": [],
              "terminals": [], "ledger": deepcopy(value["ledger"]), "diagnostics": deepcopy(value["diagnostics"])}
    for record in value["branches"]:
        item = {k: deepcopy(v) for k, v in record.items() if k not in {"initial_medium_id", "initial_refractive_index", "parent_event_id"}}
        item["parent_hit_id"] = record["parent_event_id"]
        result["branches"].append(item)
    for name in ("segments", "terminals"):
        for record in value[name]:
            item = {k: deepcopy(v) for k, v in record.items() if k not in {"medium_id", "refractive_index", "event_id"}}
            item["hit_id"] = record["event_id"]
            result[name].append(item)
    for record in value["events"]:
        item = {k: deepcopy(v) for k, v in record.items() if k not in {"target", "classification", "incident_medium_id", "incident_refractive_index"}}
        item["element_id"] = record["target"]["element_id"]
        item["outgoing"] = [{k: deepcopy(v) for k, v in part.items() if k not in {"medium_id", "refractive_index"}} for part in record["outgoing"]]
        item["numerical_bounds"] = {k: deepcopy(record["numerical_bounds"][k]) for k in ("t_parameter_interval_m", "position_intervals_m", "local_uv_intervals_m", "plane_residual_m")}
        result["hits"].append(item)
    return result


def _medium(record: dict, media: dict, prefix="") -> str:
    key, index = record[prefix + "medium_id"], record[prefix + "refractive_index"]
    if type(key) is not str or key not in media or _number(index, "medium index", 1, 2.5) != media[key]:
        raise ValueError("medium: unknown identity or changed refractive index")
    return key


def validate_trace_reply(value: object, **identity) -> dict:
    """Admit the complete closed graph, medium transitions and finite bounds."""
    reply = _envelope(value, REPLY_KEYS, "refractive_trace_result", **identity)
    scene, media, faces, limits = _metadata(reply)
    body_present = bool(scene["bodies"])
    elements = {item["id"]: item for item in scene["elements"]}
    branches = _records(reply["branches"], limits["max_branches"], "branches", BRANCH_KEYS, branch=True)
    segments = _records(reply["segments"], limits["max_segments"], "segments", SEGMENT_KEYS)
    events = _records(reply["events"], limits["max_events"], "events")
    terminals = _records(reply["terminals"], limits["max_branches"], "terminals", TERMINAL_KEYS, id_key="branch_id", branch=True)
    if not branches or next(iter(branches)) != "r0" or len(segments) + len(events) > limits["max_records"]:
        raise ValueError("trace: missing root or exceeded combined record cap")
    start, prefix = (1, "e") if body_present else (0, "h")
    if list(segments) != [f"s{i:04d}" for i in range(start, start + len(segments))] or list(events) != [f"{prefix}{i:04d}" for i in range(start, start + len(events))]:
        raise ValueError("trace: unstable conditional record ordinals")
    seen = set()
    for identifier, branch in branches.items():
        _vector(branch["origin_m"], 3, "branch origin")
        _direction(branch["initial_direction"], "branch initial direction")
        _medium(branch, media, "initial_")
        _number(branch["relative_weight"], "branch weight", 0, 1)
        if branch["relative_weight"] <= 0:
            raise ValueError("branch: positive weight required")
        _number(branch["start_cumulative_m"], "branch cumulative", 0, 10)
        count = branch["start_interaction_count"]
        if type(count) is not int or not 0 <= count <= 32 or branch["outcome"] not in CATEGORIES | {"split"}:
            raise ValueError("branch: invalid inherited interaction count/outcome")
        if identifier == "r0":
            if branch["parent_id"] is not None or branch["parent_event_id"] is not None or branch["origin_m"] != scene["source"]["origin_m"] or branch["initial_direction"] != scene["source"]["direction"] or branch["relative_weight"] != 1 or count != 0 or branch["start_cumulative_m"] != 0 or branch["initial_medium_id"] != "exterior":
                raise ValueError("root: inconsistent submitted source/medium")
        else:
            parent = branch["parent_id"]
            if parent not in seen or identifier not in (parent + ".T", parent + ".R") or branch["parent_event_id"] not in events:
                raise ValueError("branch: invalid/cyclic/nonparent-first identity")
            event = events[branch["parent_event_id"]]
            if branches[parent]["outcome"] != "split" or event["branch_id"] != parent:
                raise ValueError("branch: parent is not its actual split")
        seen.add(identifier)
    by_branch = {key: [] for key in branches}
    for segment in segments.values():
        if segment["branch_id"] not in branches:
            raise ValueError("segment: unknown branch")
        _vector(segment["start_m"], 3, "segment start")
        _vector(segment["end_m"], 3, "segment end")
        _direction(segment["direction"], "segment direction")
        _medium(segment, media)
        length = _number(segment["length_m"], "segment length", 0, 10 + 128 * EPS)
        _number(segment["cumulative_end_m"], "segment cumulative", 0, 10 + 128 * EPS)
        if length <= 0 or _number(segment["relative_weight"], "segment weight", 0, 1) != branches[segment["branch_id"]]["relative_weight"]:
            raise ValueError("segment: nonpositive travel or changed weight")
        if segment["event_id"] is not None and segment["event_id"] not in events:
            raise ValueError("segment: missing event")
        by_branch[segment["branch_id"]].append(segment)
    for identifier, event in events.items():
        target = event.get("target")
        dielectric = type(target) is dict and target.get("kind") == "body_face"
        _keys(event, EVENT_KEYS | (DIELECTRIC_KEYS if dielectric else set()), "event")
        if event["segment_id"] not in segments or event["branch_id"] not in branches:
            raise ValueError("event: unknown segment/branch")
        segment = segments[event["segment_id"]]
        if (segment["event_id"] != identifier or segment["branch_id"] != event["branch_id"] or segment["end_m"] != event["position_m"] or segment["direction"] != event["incident_direction"] or segment["relative_weight"] != event["incoming_weight"] or segment["length_m"] != event["segment_length_m"] or segment["cumulative_end_m"] != event["cumulative_length_m"] or segment["medium_id"] != event["incident_medium_id"] or segment["refractive_index"] != event["incident_refractive_index"]):
            raise ValueError("event: disconnected segment/medium relationship")
        _vector(event["position_m"], 3, "event position")
        _vector(event["local_uv_m"], 2, "event local UV")
        _direction(event["incident_direction"], "event incident direction")
        incoming_medium = _medium(event, media, "incident_")
        _number(event["incoming_weight"], "event weight", 0, 1)
        bounds = _keys(event["numerical_bounds"], COMMON_BOUNDS | (DIELECTRIC_BOUNDS if dielectric else set()), "event bounds")
        if _interval(bounds["t_parameter_interval_m"], "forward interval")[0] <= 0:
            raise ValueError("event: forward travel not certified")
        _intervals(bounds["position_intervals_m"], 3, "position bounds", event["position_m"], width=body_present)
        _intervals(bounds["local_uv_intervals_m"], 2, "UV bounds", event["local_uv_m"])
        _intervals(bounds["incident_direction_intervals"], 3, "incident bounds", event["incident_direction"], width=body_present)
        _interval(bounds["cumulative_length_interval_m"], "cumulative bounds", event["cumulative_length_m"])
        _number(bounds["plane_residual_m"], "plane residual")
        outgoing = event["outgoing"]
        if type(outgoing) is not list or len(outgoing) > 2:
            raise ValueError("event: incorrect outgoing cardinality")
        directions = bounds["outgoing_direction_intervals"]
        if type(directions) is not list or len(directions) != len(outgoing):
            raise ValueError("event: missing outgoing direction bounds")
        for part, enclosure in zip(outgoing, directions):
            _keys(part, OUTGOING_KEYS, "outgoing")
            _keys(enclosure, {"branch_id", "direction_intervals"}, "outgoing bounds")
            _direction(part["direction"], "outgoing direction")
            _medium(part, media)
            _number(part["relative_weight"], "outgoing weight", 0, 1)
            if part["branch_id"] not in branches or enclosure["branch_id"] != part["branch_id"]:
                raise ValueError("outgoing: missing or mismatched branch identity")
            _intervals(enclosure["direction_intervals"], 3, "outgoing direction bounds", part["direction"], width=body_present)
        classification = event["classification"]
        expected_medium = "exterior"
        if dielectric:
            _keys(target, {"kind", "body_id", "face_id"}, "body face target")
            key = (target["body_id"], target["face_id"])
            if key not in faces:
                raise ValueError("event: unknown body/finite face identity")
            face = faces[key]
            if event["outward_normal"] != face["outward_normal"] or event["local_basis"] != face["local_basis"]:
                raise ValueError("event: changed authoritative face normal/basis")
            for name in ("incident_angle_rad", "outgoing_angle_rad"):
                _number(event[name], name, 0, math.pi / 2 + 128 * EPS)
            incident = _interval(bounds["incident_side_interval"], "incident side")
            outgoing_side = _interval(bounds["outgoing_side_interval"], "outgoing side")
            discriminant = _interval(bounds["snell_discriminant_interval"], "Snell discriminant")
            _intervals(bounds["body_halfspace_intervals_m"], len(faces), "body halfspaces")
            for face_key, enclosure in zip(faces, bounds["body_halfspace_intervals_m"]):
                if face_key == key:
                    if not enclosure[0] <= 0 <= enclosure[1]:
                        raise ValueError("body event: hit face enclosure does not contain zero")
                elif enclosure[1] >= 0:
                    raise ValueError("body event: other face enclosure is not strictly interior")
            body_medium = "body:" + target["body_id"]
            outside = incoming_medium == "exterior"
            if incoming_medium not in {"exterior", body_medium} or (incident[1] >= 0 if outside else incident[0] <= 0):
                raise ValueError("body event: incident medium/side disagreement")
            if classification == "total_internal_reflection":
                expected_medium = incoming_medium
                if discriminant[1] >= 0 or (outgoing_side[0] <= 0 if outside else outgoing_side[1] >= 0):
                    raise ValueError("TIR: missing strict negative discriminant or reflected side")
            elif classification in {"enter_refraction", "exit_refraction"}:
                expected_medium = body_medium if outside else "exterior"
                if classification != ("enter_refraction" if outside else "exit_refraction") or discriminant[0] <= 0 or (outgoing_side[1] >= 0 if outside else outgoing_side[0] <= 0):
                    raise ValueError("refraction: wrong entry/exit/discriminant/side")
            else:
                raise ValueError("body event: unsupported classification")
        else:
            _keys(target, {"kind", "element_id"}, "element target")
            if target["kind"] != "element" or target["element_id"] not in elements or incoming_medium != "exterior":
                raise ValueError("legacy event: unknown exterior element/medium")
            if classification != LEGACY_CLASS[elements[target["element_id"]]["kind"]]:
                raise ValueError("legacy event: kind/classification disagreement")
        if classification in {"stop_hit", "receiver_hit"}:
            if outgoing:
                raise ValueError("terminating event: must not continue")
        elif classification == "ideal_split":
            if len(outgoing) == 0:
                terminal = terminals.get(event["branch_id"])
                if terminal is None or terminal["event_id"] != identifier or terminal["reason"] != "branch_cap":
                    raise ValueError("splitter: zero children only at actual branch cap")
            elif len(outgoing) != 2 or [part["branch_id"] for part in outgoing] != [event["branch_id"] + ".T", event["branch_id"] + ".R"] or branches[event["branch_id"]]["outcome"] != "split":
                raise ValueError("splitter: pair must be atomic and T/R ordered")
            for part in outgoing:
                child = branches[part["branch_id"]]
                if part["medium_id"] != "exterior" or part["relative_weight"] != event["incoming_weight"] * .5 or child["relative_weight"] != part["relative_weight"] or child["parent_id"] != event["branch_id"] or child["parent_event_id"] != identifier or child["origin_m"] != event["position_m"] or child["initial_direction"] != part["direction"] or child["initial_medium_id"] != part["medium_id"] or child["initial_refractive_index"] != part["refractive_index"] or child["start_cumulative_m"] != event["cumulative_length_m"]:
                    raise ValueError("splitter: changed child birth identity/state")
            if outgoing and outgoing[0]["direction"] != event["incident_direction"]:
                raise ValueError("splitter: transmitted direction changed")
        else:
            if len(outgoing) != 1 or outgoing[0]["branch_id"] != event["branch_id"] or outgoing[0]["relative_weight"] != event["incoming_weight"] or outgoing[0]["medium_id"] != expected_medium:
                raise ValueError("event: expected one same-weight same-branch continuation/medium")
    expected_creation = ["r0"]
    for event in events.values():
        if len(event["outgoing"]) == 2:
            expected_creation.extend(part["branch_id"] for part in event["outgoing"])
    if list(branches) != expected_creation:
        raise ValueError("branches: not stable breadth-first atomic creation order")
    for identifier, branch in branches.items():
        point, direction = branch["origin_m"], branch["initial_direction"]
        medium, cumulative = branch["initial_medium_id"], branch["start_cumulative_m"]
        interactions = branch["start_interaction_count"]
        path = by_branch[identifier]
        last_event = branch["parent_event_id"]
        for index, segment in enumerate(path):
            actual_length = math.hypot(*(b - a for a, b in zip(segment["start_m"], segment["end_m"])))
            if abs(actual_length - segment["length_m"]) > 128 * EPS * max(1, actual_length) or abs(segment["cumulative_end_m"] - cumulative - segment["length_m"]) > 128 * EPS * max(1, segment["cumulative_end_m"]):
                raise ValueError("segment: physical/accumulated distance disagreement")
            if segment["start_m"] != point or segment["direction"] != direction or segment["medium_id"] != medium:
                raise ValueError("branch: disconnected segment/medium chain")
            point, cumulative = segment["end_m"], segment["cumulative_end_m"]
            event_id = segment["event_id"]
            if event_id is None:
                if index != len(path) - 1:
                    raise ValueError("branch: non-event endpoint cannot continue")
            else:
                last_event = event_id
                interactions += 1
                outgoing = events[event_id]["outgoing"]
                if index != len(path) - 1 and (len(outgoing) != 1 or outgoing[0]["branch_id"] != identifier):
                    raise ValueError("branch: terminating/split event cannot continue")
                if len(outgoing) == 1:
                    direction, medium = outgoing[0]["direction"], outgoing[0]["medium_id"]
            if interactions > 32:
                raise ValueError("branch: exceeded inherited interaction cap")
        if branch["outcome"] == "split":
            if identifier in terminals or not path or path[-1]["event_id"] is None or len(events[path[-1]["event_id"]]["outgoing"]) != 2:
                raise ValueError("split parent: missing pair or duplicated terminal weight")
            for child in events[path[-1]["event_id"]]["outgoing"]:
                if branches[child["branch_id"]]["start_interaction_count"] != interactions:
                    raise ValueError("splitter: incorrect inherited interaction count")
        elif identifier not in terminals:
            raise ValueError("branch: unresolved terminal weight")
        if identifier in terminals:
            terminal = terminals[identifier]
            _medium(terminal, media)
            _vector(terminal["position_m"], 3, "terminal position")
            _number(terminal["cumulative_length_m"], "terminal distance", 0, 10 + 128 * EPS)
            _number(terminal["relative_weight"], "terminal weight", 0, 1)
            if terminal["position_m"] != point or terminal["cumulative_length_m"] != cumulative or terminal["medium_id"] != medium or terminal["category"] != branch["outcome"] or terminal["relative_weight"] != branch["relative_weight"] or terminal["reason"] not in REASONS:
                raise ValueError("terminal: changed endpoint/medium/category/weight/reason")
            radius = math.hypot(*(a - b for a, b in zip(point, scene["source"]["origin_m"])))
            if radius > 1 + 2e-12:
                raise ValueError("terminal: outside source-centred trace domain")
            category = terminal["category"]
            if category in {"detected", "absorbed"}:
                event = events.get(terminal["event_id"])
                classification = "receiver_hit" if category == "detected" else "stop_hit"
                if not path or path[-1]["event_id"] != terminal["event_id"] or event is None or event["classification"] != classification or event["branch_id"] != identifier or terminal["element_id"] != event["target"]["element_id"] or terminal["reason"] != classification:
                    raise ValueError("terminal: fabricated detection/absorption")
            elif category == "escaped":
                if not path or path[-1]["event_id"] is not None or terminal["event_id"] is not None or terminal["element_id"] is not None or terminal["reason"] != "domain_exit" or abs(radius - 1) > 2e-13:
                    raise ValueError("terminal: fabricated domain escape")
            elif category == "resource_truncated":
                if terminal["reason"] not in {"interaction_cap", "distance_cap", "branch_cap", "record_cap"} or terminal["event_id"] != last_event:
                    raise ValueError("terminal: changed retained resource event")
                if terminal["reason"] == "interaction_cap" and interactions != 32 or terminal["reason"] == "distance_cap" and abs(cumulative - 10) > 128 * EPS * 10:
                    raise ValueError("terminal: premature resource cap")
                event = events.get(last_event)
                expected_element = None if event is None or event["target"]["kind"] == "body_face" else event["target"]["element_id"]
                if terminal["element_id"] != expected_element or event is not None and event["classification"] in {"receiver_hit", "stop_hit"}:
                    raise ValueError("terminal: changed retained identity or hidden physical stop")
    if set(terminals) - set(branches):
        raise ValueError("terminal: unknown branch")
    incomplete = any(part["category"] == "resource_truncated" for part in terminals.values())
    if reply["status"] != ("incomplete" if incomplete else "complete"):
        raise ValueError("trace: hidden resource truncation")
    ledger = _keys(reply["ledger"], LEDGER_KEYS, "ledger")
    for key, number in ledger.items():
        _number(number, "ledger." + key)
    if ledger["input_weight"] != 1:
        raise ValueError("ledger: changed source weight")
    for category, key in (("detected", "detected_weight"), ("absorbed", "absorbed_weight"), ("escaped", "escaped_weight"), ("resource_truncated", "truncated_weight")):
        if abs(ledger[key] - math.fsum(part["relative_weight"] for part in terminals.values() if part["category"] == category)) > 64 * EPS:
            raise ValueError("ledger: changed category weight")
    residual = 1 - math.fsum(part["relative_weight"] for part in terminals.values())
    if abs(residual) > 64 * EPS or abs(ledger["signed_residual"] - residual) > 64 * EPS:
        raise ValueError("ledger: missing or duplicated leaf weight")
    if body_present:
        diagnostic = _keys(reply["diagnostics"], DIAGNOSTIC_KEYS, "diagnostics")
        if diagnostic["predicate_policy"] != "binary64_closed_body_outward_v1":
            raise ValueError("diagnostics: wrong body predicate policy")
        for key in DIAGNOSTIC_KEYS - {"predicate_policy"}:
            _number(diagnostic[key], "diagnostics." + key, 0)
        if diagnostic["max_direction_norm_residual"] > 128 * EPS or diagnostic["max_point_width_m"] > 1e-8 or diagnostic["max_direction_width"] > 1e-8:
            raise ValueError("diagnostics: unsupported body arithmetic")
    else:
        projected = project_w2_result(reply)
        w2.validate_trace_reply({"protocol_version": 1, "message_type": "trace_result", "model_contract": w2.MODEL_CONTRACT, "request_id": reply["request_id"], "scene_sha256": w2.scene_digest(projected["scene"]), **projected})
    return reply


def encode_trace_result(request_id: str, scene_sha256: str, result: dict) -> bytes:
    """Validate and encode the complete result inside actual worker lifetime."""
    _keys(result, CORE_KEYS, "core W3 result")
    reply = {"protocol_version": 1, "message_type": "refractive_trace_result",
             "model_contract": MODEL_CONTRACT, "request_id": request_id,
             "scene_sha256": scene_sha256, **result}
    validate_trace_reply(reply, request_id=request_id, scene_sha256=scene_sha256)
    return _bounded(reply)


def _response_json(data: bytes) -> object:
    if type(data) is not bytes:
        raise TypeError("W3 response: expected bytes")
    if len(data) > MAX_RESPONSE_BYTES:
        raise ValueError("W3 response: byte cap exceeded")
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("W3 response: duplicate key")
            result[key] = value
        return result
    def real(token):
        value = float(token)
        if not math.isfinite(value) or value == 0 and any(c in "123456789" for c in token.lower().split("e", 1)[0]):
            raise ValueError("W3 response: unusable binary64 scalar")
        return value
    def integer(token):
        value = int(token)
        _number(value, "JSON integer")
        return value
    def constant(_):
        raise ValueError("W3 response: nonfinite constant")
    try:
        return json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                          parse_float=real, parse_int=integer, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError, OverflowError) as exc:
        raise ValueError("W3 response: expected bounded strict UTF-8 JSON") from exc


def decode_trace_result(data: bytes, **identity) -> dict:
    """Decode genuine bounded response bytes, never replay scientific work."""
    return validate_trace_reply(_response_json(data), **identity)


def decode_validation_reply(data: bytes, **identity) -> dict:
    """Decode noncomputing admission metadata under the same closed policy."""
    return validate_validation_reply(_response_json(data), **identity)


def error_reply(request_id: str | None, code: str, message: str) -> bytes:
    """Encode a bounded declared W3 error with no partial route graph."""
    if request_id is not None:
        validate_request_id(request_id)
    if type(code) is not str or code not in ERROR_CODES:
        raise ValueError("W3 error: undeclared error code")
    if type(message) is not str:
        raise TypeError("W3 error: message must be text")
    return json_bytes({"protocol_version": 1, "message_type": "refractive_routing_error",
                       "request_id": request_id, "model_contract": MODEL_CONTRACT,
                       "error": {"code": code, "message": message[:300]}})
