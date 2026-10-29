"""Closed W4 representation, graph and power admission before publication.

This owner performs no intersection or Fresnel calculation. Lengths are SI
metres, angles radians, and matrix traces are source-relative optical power.
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
MODEL_CONTRACT = "w4_fresnel_polarized_routing_v1"
POWER_POLICY = "absolute_source_coherency_v1"
PATH_ADDITION = "incoherent_phase_averaged_v1"
MAX_BODY_BYTES = 32_768
MAX_RESPONSE_BYTES = 393_216
LIMITS = {"max_bodies": 1, "max_body_faces": 6, "max_terminal_elements": 4,
          "max_total_optical_faces": 10, "max_interactions": 8,
          "max_branches": 31, "max_events": 32, "max_segments": 64,
          "max_records": 96, "max_terminal_leaves": 16,
          "trace_radius_m": 1.0, "max_distance_m": 10.0,
          "request_bytes": MAX_BODY_BYTES, "response_bytes": MAX_RESPONSE_BYTES}
METADATA_KEYS = {"scene", "power_policy", "path_addition", "media", "body_faces", "terminal_frames", "limits"}
CORE_KEYS = METADATA_KEYS | {"status", "branches", "segments", "events", "terminals", "ledger", "diagnostics"}
ENVELOPE_KEYS = {"protocol_version", "message_type", "request_id", "model_contract", "scene_sha256"}
VALIDATION_KEYS = ENVELOPE_KEYS | METADATA_KEYS
REPLY_KEYS = ENVELOPE_KEYS | CORE_KEYS
FACE_KEYS = {"body_id", "face_id", "vertices_m", "plane_covector", "outward_normal", "local_origin_m", "local_basis", "numerical_bounds"}
FACE_BOUNDS = {"vertex_intervals_m", "covector_intervals", "normal_intervals", "basis_u_intervals", "basis_v_intervals"}
STATE_KEYS = {"direction", "medium_id", "refractive_index", "frame", "C", "power_fraction", "numerical_bounds"}
STATE_BOUNDS = {"direction_intervals", "frame_intervals", "C_intervals", "power_interval"}
BRANCH_KEYS = {"id", "parent_id", "parent_event_id", "origin_m", "initial_state", "start_cumulative_m", "start_interaction_count", "outcome"}
SEGMENT_KEYS = {"id", "branch_id", "start_m", "end_m", "state", "length_m", "cumulative_end_m", "event_id"}
EVENT_KEYS = {"id", "segment_id", "branch_id", "target", "classification", "position_m", "local_uv_m", "incident_state", "segment_length_m", "cumulative_length_m", "numerical_bounds", "interface"}
TARGET_KEYS = {"kind", "body_id", "face_id", "element_id"}
COMMON_BOUNDS = {"t_parameter_interval_m", "position_intervals_m", "local_uv_intervals_m", "incident_direction_intervals", "outgoing_direction_intervals", "cumulative_length_interval_m", "plane_residual_m"}
DIELECTRIC_BOUNDS = {"snell_discriminant_interval", "incident_side_interval", "body_halfspace_intervals_m", "outgoing_side_intervals"}
INTERFACE_KEYS = {"incident_medium_id", "transmission_medium_id", "outward_normal", "incident_facing_covector", "incidence_basis", "incident_angle_rad", "transmitted_angle_rad", "coefficients", "power_fractions", "legs", "local_signed_residual", "numerical_bounds"}
INTERFACE_BOUNDS = {"ci_interval", "ct_complex_intervals", "coefficient_intervals", "flux_factor_interval", "basis_intervals", "local_residual_interval"}
COEFFICIENT_KEYS = {"r_s", "r_p", "t_s", "t_p", "flux_factor"}
FRACTION_KEYS = {"R_s", "R_p", "T_s", "T_p", "R_incident", "T_incident"}
LEG_KEYS = {"kind", "disposition", "branch_id", "direction", "medium_id", "refractive_index", "power_fraction", "state"}
TERMINAL_KEYS = {"branch_id", "category", "element_id", "event_id", "position_m", "state", "cumulative_length_m", "reason"}
LEDGER_KEYS = {"input_power", "detected_power", "stopped_power", "escaped_power", "unresolved_power", "signed_residual", "receiver_totals", "path_addition"}
DIAGNOSTIC_KEYS = {"geometry_policy", "polarization_policy", "max_point_width_m", "max_direction_width", "max_frame_width", "max_coefficient_width", "max_C_width", "max_local_power_residual", "max_frame_residual", "created_branches", "surface_events", "segments", "max_ancestry_interactions", "record_count"}
CATEGORIES = {"detected", "stopped", "escaped", "resource_unresolved"}
REASONS = {"receiver_hit", "stop_hit", "domain_exit", "interaction_cap", "event_cap", "segment_cap", "record_cap", "branch_cap", "distance_cap"}
ERROR_CODES = {"invalid_scene", "numerical_ambiguity", "medium_state_ambiguity", "unsupported_numerical_input", "unsupported_polarization_numerics", "numerical_failure", "busy", "request_body_too_large", "encoding_failed", "response_too_large", "trace_failed", "disconnected", "cancelled_before_start", "submission_failed"}
FACE_IDS = {"rectangular_block": ("x_min", "x_max", "y_min", "y_max", "z_min", "z_max"),
            "right_triangular_prism": ("x_min", "z_min", "hypotenuse", "y_min", "y_max")}
SOURCE_C = {"unpolarized": [.5, .5, 0., 0.], "linear_e1": [1., 0., 0., 0.],
            "linear_e2": [0., 1., 0., 0.], "linear_45": [.5, .5, .5, 0.]}


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


def _count(value: object, name: str, maximum: int) -> int:
    if type(value) is not int:
        raise TypeError(f"{name}: expected integer excluding bool")
    if not 0 <= value <= maximum:
        raise ValueError(f"{name}: outside count cap")
    return value


def _vector(value: object, size: int, name: str) -> list:
    if type(value) is not list or len(value) != size:
        raise ValueError(f"{name}: expected {size} components")
    for item in value:
        _number(item, name)
    return value


def _direction(value: object, name: str) -> list:
    vector = _vector(value, 3, name)
    if abs(math.hypot(*vector) - 1) > 128 * EPS:
        raise ValueError(f"{name}: unsupported nominal unit direction")
    return vector


def _identifier(value: object, name: str, *, branch=False) -> str:
    pattern = r"r0(?:\.[RT]){0,8}" if branch else r"[A-Za-z][A-Za-z0-9_.-]{0,63}"
    if type(value) is not str or re.fullmatch(pattern, value, flags=re.ASCII) is None:
        raise ValueError(f"{name}: expected bounded ASCII identity")
    return value


def _intervals(value: object, size: int, name: str, nominal=None, *, width=None) -> list:
    if type(value) is not list or len(value) != size:
        raise ValueError(f"{name}: incorrect interval shape")
    for index, row in enumerate(value):
        _vector(row, 2, name)
        if row[0] > row[1] or width is not None and row[1] - row[0] > width:
            raise ValueError(f"{name}: reversed or unsupported enclosure width")
        if nominal is not None and not row[0] <= nominal[index] <= row[1]:
            raise ValueError(f"{name}: nominal outside enclosure")
    return value


def _interval(value: object, name: str, nominal=None, *, width=None) -> list:
    return _intervals([value], 1, name, None if nominal is None else [nominal], width=width)[0]


def _same_power(actual: float, expected: float, name: str) -> None:
    # No unit-size absolute floor: a lost weak positive cannot compare equal0.
    if actual != expected and abs(actual - expected) > 64 * EPS * abs(expected):
        raise ValueError(f"{name}: changed source-relative power")


def _records(value: object, maximum: int, name: str, keys: set[str], *, id_key="id", branch=False) -> dict:
    if type(value) is not list or len(value) > maximum:
        raise ValueError(f"{name}: incorrect list or cap")
    result = {}
    for item in value:
        _keys(item, keys, name)
        key = _identifier(item[id_key], name, branch=branch)
        if key in result:
            raise ValueError(f"{name}: duplicate identity")
        result[key] = item
    return result


def _scene(value: object) -> dict:
    scene = _keys(value, {"schema_version", "model_contract", "source", "exterior_medium", "bodies", "elements", "path_addition"}, "scene")
    if type(scene["schema_version"]) is not int or scene["schema_version"] != 1 or scene["model_contract"] != MODEL_CONTRACT or scene["path_addition"] != PATH_ADDITION:
        raise ValueError("scene: unsupported schema/model/path addition")
    source = _keys(scene["source"], {"id", "origin_m", "direction", "frame_policy", "polarization"}, "source")
    _vector(source["origin_m"], 3, "source origin")
    _vector(source["direction"], 3, "source direction")
    if (source["id"] != "source" or source["direction"] != [0, 0, 1] or source["origin_m"] not in ([0, .08, -.04], [.02, .08, -.04]) or source["frame_policy"] != "world_xy_forward_z_v1" or type(source["polarization"]) is not str or source["polarization"] not in SOURCE_C):
        raise ValueError("source: unsupported fixed source/frame/polarization")
    exterior = _keys(scene["exterior_medium"], {"id", "refractive_index"}, "exterior medium")
    if exterior["id"] != "exterior":
        raise ValueError("exterior medium: wrong identity")
    _number(exterior["refractive_index"], "exterior index", 1, 2.5)
    if type(scene["bodies"]) is not list or len(scene["bodies"]) > 1:
        raise ValueError("bodies: at most one closed body")
    for body in scene["bodies"]:
        _keys(body, {"id", "kind", "pose", "shape", "interior_medium"}, "body")
        if type(body["id"]) is not str or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", body["id"], flags=re.ASCII) is None or body["kind"] not in FACE_IDS:
            raise ValueError("body: unsupported identity/family")
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
    if type(scene["elements"]) is not list or len(scene["elements"]) > 4:
        raise ValueError("elements: at most four finite terminators")
    if any(type(item) is not dict or item.get("kind") not in {"receiver", "beam_stop"} for item in scene["elements"]):
        raise ValueError("elements: only receiver/beam_stop supported")
    return scene


def _metadata(reply: dict) -> tuple[dict, dict, dict]:
    scene = _scene(reply["scene"])
    if reply["power_policy"] != POWER_POLICY or reply["path_addition"] != PATH_ADDITION:
        raise ValueError("metadata: unsupported power/path claim")
    projection = {"schema_version": 1, "model_contract": w2.MODEL_CONTRACT,
                  "source": {"id": "source", "origin_m": scene["source"]["origin_m"], "direction": [0, 0, 1], "relative_weight": 1.0},
                  "elements": scene["elements"]}
    # Public representation admission only; this function never runs optics.
    w2.encode_validation_reply(reply["request_id"], projection, reply["terminal_frames"])
    expected_media = [scene["exterior_medium"], *[body["interior_medium"] for body in scene["bodies"]]]
    if type(reply["media"]) is not list or reply["media"] != expected_media:
        raise ValueError("media: changed declared identities/indices")
    for item in reply["media"]:
        _keys(item, {"id", "refractive_index"}, "medium")
        _number(item["refractive_index"], "medium index", 1, 2.5)
    media = {item["id"]: item["refractive_index"] for item in expected_media}
    _keys(reply["limits"], set(LIMITS), "limits")
    for key, expected in LIMITS.items():
        _number(reply["limits"][key], "limits." + key)
        if reply["limits"][key] != expected or type(expected) is int and type(reply["limits"][key]) is not int:
            raise ValueError("limits: changed fixed W4 cap")
    expected_faces = [(body, face) for body in scene["bodies"] for face in FACE_IDS[body["kind"]]]
    if type(reply["body_faces"]) is not list or len(reply["body_faces"]) != len(expected_faces):
        raise ValueError("body_faces: missing/extra finite face")
    faces = {}
    for record, (body, face_id) in zip(reply["body_faces"], expected_faces):
        _keys(record, FACE_KEYS, "body face")
        if record["body_id"] != body["id"] or record["face_id"] != face_id:
            raise ValueError("body_faces: wrong ordered identity")
        count = 3 if body["kind"] == "right_triangular_prism" and face_id in {"y_min", "y_max"} else 4
        if type(record["vertices_m"]) is not list or len(record["vertices_m"]) != count:
            raise ValueError("body face: wrong finite polygon shape")
        for vertex in record["vertices_m"]:
            _vector(vertex, 3, "face vertex")
        _vector(record["plane_covector"], 3, "face covector")
        if math.hypot(*record["plane_covector"]) == 0:
            raise ValueError("face: zero covector")
        _direction(record["outward_normal"], "face normal")
        _vector(record["local_origin_m"], 3, "face origin")
        basis = _keys(record["local_basis"], {"u", "v"}, "face basis")
        _vector(basis["u"], 3, "face u")
        _vector(basis["v"], 3, "face v")
        bounds = _keys(record["numerical_bounds"], FACE_BOUNDS, "face bounds")
        if type(bounds["vertex_intervals_m"]) is not list or len(bounds["vertex_intervals_m"]) != count:
            raise ValueError("face: missing vertex enclosures")
        for vertex, enclosure in zip(record["vertices_m"], bounds["vertex_intervals_m"]):
            _intervals(enclosure, 3, "vertex bounds", vertex, width=1e-8)
        for key, nominal in (("covector_intervals", record["plane_covector"]), ("normal_intervals", record["outward_normal"]), ("basis_u_intervals", basis["u"]), ("basis_v_intervals", basis["v"])):
            _intervals(bounds[key], 3, key, nominal)
        faces[(body["id"], face_id)] = record
    return scene, media, faces


def _state(value: object, media: dict) -> dict:
    state = _keys(value, STATE_KEYS, "ray state")
    direction = _direction(state["direction"], "state direction")
    if type(state["medium_id"]) is not str or state["medium_id"] not in media or state["refractive_index"] != media[state["medium_id"]]:
        raise ValueError("state: changed medium identity/index")
    _number(state["refractive_index"], "state index", 1, 2.5)
    frame = _keys(state["frame"], {"e1", "e2", "khat"}, "ray frame")
    for vector in frame.values():
        _direction(vector, "frame axis")
    e1, e2, khat = (frame[key] for key in ("e1", "e2", "khat"))
    if any(abs(math.fsum(a*b for a, b in zip(left, right))) > 128*EPS for left, right in ((e1, e2), (e1, khat), (e2, khat))):
        raise ValueError("state: nontransverse frame")
    cross = [e1[1]*e2[2]-e1[2]*e2[1], e1[2]*e2[0]-e1[0]*e2[2], e1[0]*e2[1]-e1[1]*e2[0]]
    if any(abs(a-b) > 128*EPS for a, b in zip(cross, khat)) or any(abs(a/math.hypot(*direction)-b) > 128*EPS for a,b in zip(direction,khat)):
        raise ValueError("state: wrong handedness or propagation frame")
    C = _vector(state["C"], 4, "power coherency")
    power = _number(state["power_fraction"], "state power", 0, 1 + 128*EPS)
    if power != C[0]+C[1] or power <= 0:
        raise ValueError("state: power must be the strictly positive trace(C)")
    # Packed Hermitian convention is exact; these are diagnostics, no repair.
    minimum = (power-math.hypot(C[0]-C[1], 2*C[2], 2*C[3]))/2
    if C[0] < -64*EPS*power or C[1] < -64*EPS*power or minimum < -64*EPS*power:
        raise ValueError("state: materially nonpositive coherency")
    bounds = _keys(state["numerical_bounds"], STATE_BOUNDS, "state bounds")
    _intervals(bounds["direction_intervals"], 3, "state direction bounds", direction, width=1e-8)
    _intervals(bounds["frame_intervals"], 9, "state frame bounds", [*e1,*e2,*khat], width=1e-8)
    _intervals(bounds["C_intervals"], 4, "state C bounds", C, width=1e-8)
    _interval(bounds["power_interval"], "state power bounds", power)
    return state


def _envelope(value: object, keys: set[str], message_type: str, *, request_id=None, scene=None, scene_sha256=None) -> dict:
    reply = _keys(value, keys, message_type)
    if type(reply["protocol_version"]) is not int or reply["protocol_version"] != 1 or reply["message_type"] != message_type or reply["model_contract"] != MODEL_CONTRACT:
        raise ValueError("reply: version/model/discriminator mismatch")
    validate_request_id(reply["request_id"])
    actual = scene_digest(reply["scene"])
    if validate_digest(reply["scene_sha256"]) != actual:
        raise ValueError("reply: complete scene digest mismatch")
    if request_id is not None and reply["request_id"] != request_id or scene_sha256 is not None and actual != validate_digest(scene_sha256):
        raise ValueError("reply: submitted request/digest mismatch")
    if scene is not None and json_bytes(scene, canonical=True) != json_bytes(reply["scene"], canonical=True):
        raise ValueError("reply: submitted scene mismatch")
    return reply


def validate_validation_reply(value: object, **identity) -> dict:
    """Admit closed metadata and identity with zero scientific operations."""
    reply = _envelope(value, VALIDATION_KEYS, "fresnel_scene_validation", **identity)
    _metadata(reply)
    return reply


def _bounded(value: dict) -> bytes:
    encoded = json_bytes(value)
    if len(encoded) > MAX_RESPONSE_BYTES:
        raise ValueError("W4 response: exceeds384KiB")
    return encoded


def encode_validation_reply(request_id: str, scene: dict, *, media: list, body_faces: list, terminal_frames: list, limits: dict) -> bytes:
    """Validate and atomically encode noncomputing W4 scene admission."""
    reply = {"protocol_version": 1, "message_type": "fresnel_scene_validation", "request_id": request_id,
             "model_contract": MODEL_CONTRACT, "scene_sha256": scene_digest(scene),
             "scene": deepcopy(scene), "power_policy": POWER_POLICY, "path_addition": PATH_ADDITION,
             "media": deepcopy(media), "body_faces": deepcopy(body_faces), "terminal_frames": deepcopy(terminal_frames), "limits": deepcopy(limits)}
    validate_validation_reply(reply, request_id=request_id, scene=scene)
    return _bounded(reply)


def _interface(event: dict, media: dict, faces: dict, branches: dict) -> list:
    interface = _keys(event["interface"], INTERFACE_KEYS, "interface")
    target = event["target"]
    key = (target["body_id"], target["face_id"])
    if key not in faces or target["element_id"] is not None:
        raise ValueError("interface: missing actual body face")
    face = faces[key]
    incoming = event["incident_state"]
    outside = incoming["medium_id"] == "exterior"
    body_medium = "body:" + target["body_id"]
    if incoming["medium_id"] not in {"exterior", body_medium}:
        raise ValueError("interface: unrelated incident medium")
    transmission = body_medium if outside else "exterior"
    if interface["incident_medium_id"] != incoming["medium_id"] or interface["transmission_medium_id"] != transmission:
        raise ValueError("interface: changed incident/transmission media")
    if interface["outward_normal"] != face["outward_normal"]:
        raise ValueError("interface: changed finite face normal")
    covector = _vector(interface["incident_facing_covector"], 3, "incident facing covector")
    expected_covector = face["plane_covector"] if outside else [-v for v in face["plane_covector"]]
    if covector != expected_covector:
        raise ValueError("interface: wrong incident-facing covector")
    classification = event["classification"]
    tir = classification == "total_internal_reflection"
    equal = classification == "equal_index_identity"
    if classification not in {"dielectric_split", "total_internal_reflection", "equal_index_identity"}:
        raise ValueError("interface: undeclared classification")
    if equal != (media[incoming["medium_id"]] == media[transmission]):
        raise ValueError("interface: equal-index classification differs from stored indices")
    _number(interface["incident_angle_rad"], "incident angle", 0, math.pi/2)
    if tir:
        if interface["transmitted_angle_rad"] is not None:
            raise ValueError("TIR: no propagating transmitted angle")
    else:
        _number(interface["transmitted_angle_rad"], "transmitted angle", 0, math.pi/2)
    basis = interface["incidence_basis"]
    if equal:
        if basis is not None:
            raise ValueError("equal-index identity: basis must be unnecessary/null")
    else:
        _keys(basis, {"s", "p_i", "normal_policy"}, "incidence basis")
        _direction(basis["s"], "s axis")
        _direction(basis["p_i"], "p axis")
        if basis["normal_policy"] not in {"generic_certified", "exact_owner_relation"}:
            raise ValueError("incidence basis: undeclared normal policy")
        k = incoming["frame"]["khat"]
        s = basis["s"]
        p = [k[1]*s[2]-k[2]*s[1], k[2]*s[0]-k[0]*s[2], k[0]*s[1]-k[1]*s[0]]
        if abs(math.fsum(a*b for a,b in zip(k,s)))>128*EPS or any(abs(a-b)>128*EPS for a,b in zip(p,basis["p_i"])):
            raise ValueError("incidence basis: nontransverse or wrong handedness")
        if basis["normal_policy"] == "exact_owner_relation" and interface["incident_angle_rad"] != 0:
            raise ValueError("normal readout: inconsistent nonzero angle")
    coefficients = _keys(interface["coefficients"], COEFFICIENT_KEYS, "coefficients")
    for name in ("r_s", "r_p", "t_s", "t_p"):
        if tir and name.startswith("t_"):
            if coefficients[name] is not None:
                raise ValueError("TIR: no transmitted field claim")
        else:
            _vector(coefficients[name], 2, "complex amplitude")
    if tir:
        if coefficients["flux_factor"] is not None:
            raise ValueError("TIR: no propagating flux factor")
    else:
        _number(coefficients["flux_factor"], "flux factor", 0)
    fractions = _keys(interface["power_fractions"], FRACTION_KEYS, "local power fractions")
    for value in fractions.values():
        _number(value, "local fraction", 0, 1+128*EPS)
    for name,coefficient in (("R_s","r_s"),("R_p","r_p"),("T_s","t_s"),("T_p","t_p")):
        amplitude=coefficients[coefficient]
        derived=0. if amplitude is None else math.fsum(part*part for part in amplitude)*(1. if name.startswith("R") else coefficients["flux_factor"])
        _same_power(fractions[name],derived,"amplitude/power channel relationship")
    if equal and (coefficients != {"r_s": [0.,0.], "r_p": [0.,0.], "t_s": [1.,0.], "t_p": [1.,0.], "flux_factor": 1.} or fractions != {"R_s":0.,"R_p":0.,"T_s":1.,"T_p":1.,"R_incident":0.,"T_incident":1.}):
        raise ValueError("equal-index identity: changed algebraic identity")
    bounds = _keys(interface["numerical_bounds"], INTERFACE_BOUNDS, "interface bounds")
    _interval(bounds["ci_interval"], "ci bounds", width=1e-8)
    _intervals(bounds["ct_complex_intervals"], 2, "ct bounds", width=1e-8)
    coefficient_bounds = bounds["coefficient_intervals"]
    if type(coefficient_bounds) is not list or len(coefficient_bounds) != 4:
        raise ValueError("interface: four coefficient bounds required")
    for name, enclosure in zip(("r_s","r_p","t_s","t_p"), coefficient_bounds):
        if coefficients[name] is None:
            if enclosure is not None:
                raise ValueError("TIR: absent coefficient must have absent bounds")
        else:
            _intervals(enclosure, 2, name+" bounds", coefficients[name], width=1e-8)
    if tir:
        if bounds["flux_factor_interval"] is not None:
            raise ValueError("TIR: absent flux bound required")
    else:
        _interval(bounds["flux_factor_interval"], "flux bounds", coefficients["flux_factor"], width=1e-8)
    if equal:
        if bounds["basis_intervals"] is not None:
            raise ValueError("equal identity: basis bounds null")
    else:
        _intervals(bounds["basis_intervals"], 6, "basis bounds", [*basis["s"],*basis["p_i"]], width=1e-8)
    residual = _number(interface["local_signed_residual"], "local signed residual")
    _interval(bounds["local_residual_interval"], "local residual bounds", residual)
    if abs(residual) > 128*EPS:
        raise ValueError("interface: material local power residual")
    legs = interface["legs"]
    if type(legs) is not list or len(legs) != 2:
        raise ValueError("interface: fixed R/T slots required")
    allocated = []
    for leg, kind in zip(legs, ("R","T")):
        _keys(leg, LEG_KEYS, "leg")
        if leg["kind"] != kind or leg["medium_id"] != (incoming["medium_id"] if kind == "R" else transmission) or leg["refractive_index"] != media[leg["medium_id"]]:
            raise ValueError("leg: wrong kind/media/index")
        power = _number(leg["power_fraction"], "leg power", 0, 1+128*EPS)
        _same_power(fractions[kind+"_incident"], power/incoming["power_fraction"], "incident-relative fraction")
        disposition = leg["disposition"]
        if disposition in {"allocated", "resource_unallocated"}:
            if power <= 0 or _state(leg["state"], media)["power_fraction"] != power or leg["state"]["direction"] != leg["direction"] or leg["state"]["medium_id"] != leg["medium_id"]:
                raise ValueError("leg: inconsistent positive carried state")
            if disposition == "allocated":
                expected_id = event["branch_id"]+"."+kind
                if leg["branch_id"] != expected_id or expected_id not in branches:
                    raise ValueError("leg: missing actual stable child")
                allocated.append(leg)
            elif leg["branch_id"] is not None:
                raise ValueError("resource unallocated: cannot claim created child")
        elif disposition in {"exact_zero", "nonpropagating_TIR"}:
            if power != 0 or leg["state"] is not None or leg["branch_id"] is not None:
                raise ValueError("zero/nonpropagating leg: no state or child")
            if leg["direction"] is not None:
                _direction(leg["direction"], "certified zero candidate direction")
            if disposition == "nonpropagating_TIR" and (kind != "T" or not tir or leg["direction"] is not None):
                raise ValueError("nonpropagating TIR: wrong slot/classification")
        else:
            raise ValueError("leg: undeclared disposition")
    expected_residual = incoming["power_fraction"]-math.fsum(leg["power_fraction"] for leg in legs)
    if residual != expected_residual:
        raise ValueError("local signed residual: changed absolute source-relative accounting")
    if tir and (legs[1]["disposition"] != "nonpropagating_TIR" or fractions["T_s"] != 0 or fractions["T_p"] != 0):
        raise ValueError("TIR: fabricated propagating transmission")
    if equal and (legs[0]["disposition"] != "exact_zero" or legs[0]["direction"] is not None or legs[1]["state"] != {**incoming, "medium_id": transmission, "refractive_index": media[transmission]}):
        raise ValueError("equal-index: changed direction/frame/C/enclosures")
    unallocated = [leg for leg in legs if leg["disposition"] == "resource_unallocated"]
    if unallocated and allocated:
        raise ValueError("interface: non-atomic child allocation")
    geometry_bounds = event["numerical_bounds"]
    _interval(geometry_bounds["snell_discriminant_interval"], "discriminant")
    discriminant = geometry_bounds["snell_discriminant_interval"]
    if (discriminant[1] >= 0 if tir else discriminant[0] <= 0):
        raise ValueError("interface: criticality is not certified")
    if _interval(geometry_bounds["incident_side_interval"], "incident side")[1] >= 0:
        raise ValueError("interface: incident-facing side must be strictly negative")
    halfspaces = geometry_bounds["body_halfspace_intervals_m"]
    _intervals(halfspaces, len(faces), "body halfspaces")
    for face_key, enclosure in zip(faces, halfspaces):
        if (not enclosure[0] <= 0 <= enclosure[1]) if face_key == key else enclosure[1] >= 0:
            raise ValueError("interface: missing unique hit/interior halfspace proof")
    directions = geometry_bounds["outgoing_direction_intervals"]
    sides = geometry_bounds["outgoing_side_intervals"]
    if type(directions) is not list or len(directions) != 2 or type(sides) is not list or len(sides) != 2:
        raise ValueError("interface: fixed R/T departure enclosures required")
    for leg, enclosure, side in zip(legs,directions,sides):
        _keys(enclosure, {"kind","branch_id","direction_intervals"}, "departure direction")
        _keys(side, {"kind","branch_id","side_interval"}, "departure side")
        if enclosure["kind"] != leg["kind"] or side["kind"] != leg["kind"] or enclosure["branch_id"] != leg["branch_id"] or side["branch_id"] != leg["branch_id"]:
            raise ValueError("departure bounds: changed leg association")
        if leg["direction"] is None:
            if enclosure["direction_intervals"] is not None or side["side_interval"] is not None:
                raise ValueError("nonpropagating leg: no geometric departure proof")
        else:
            _intervals(enclosure["direction_intervals"],3,"outgoing direction",leg["direction"],width=1e-8)
            pair = _interval(side["side_interval"],"outgoing side")
            if pair[0] <= 0 if leg["kind"] == "R" else pair[1] >= 0:
                raise ValueError("departure bounds: wrong certified side")
    return allocated


def validate_trace_reply(value: object, **identity) -> dict:
    """Admit the complete closed graph/identity without rerunning optics."""
    reply = _envelope(value, REPLY_KEYS, "fresnel_trace_result", **identity)
    scene, media, faces = _metadata(reply)
    branches = _records(reply["branches"],31,"branches",BRANCH_KEYS,branch=True)
    segments = _records(reply["segments"],64,"segments",SEGMENT_KEYS)
    events = _records(reply["events"],32,"events",EVENT_KEYS)
    terminals = _records(reply["terminals"],16,"terminals",TERMINAL_KEYS,id_key="branch_id",branch=True)
    if not branches or next(iter(branches)) != "r0" or len(segments)+len(events) > 96:
        raise ValueError("graph: missing root or combined record cap")
    if list(events) != [f"e{index:04d}" for index in range(1,len(events)+1)] or list(segments) != [f"s{index:04d}" for index in range(1,len(segments)+1)]:
        raise ValueError("graph: noncanonical sequential record identities")
    elements = {item["id"]:item for item in scene["elements"]}
    seen = set()
    for identifier, branch in branches.items():
        _vector(branch["origin_m"],3,"branch origin")
        _state(branch["initial_state"],media)
        _number(branch["start_cumulative_m"],"branch cumulative",0,10+128*EPS)
        _count(branch["start_interaction_count"],"branch inherited interactions",8)
        if branch["outcome"] not in CATEGORIES|{"split","continued"}:
            raise ValueError("branch: undeclared outcome")
        if identifier == "r0":
            state = branch["initial_state"]
            if branch["parent_id"] is not None or branch["parent_event_id"] is not None or branch["origin_m"] != scene["source"]["origin_m"] or branch["start_cumulative_m"] != 0 or branch["start_interaction_count"] != 0 or state["direction"] != [0,0,1] or state["medium_id"] != "exterior" or state["C"] != SOURCE_C[scene["source"]["polarization"]] or state["frame"] != {"e1":[1,0,0],"e2":[0,1,0],"khat":[0,0,1]}:
                raise ValueError("root: changed exact owned source state")
        else:
            parent = branch["parent_id"]
            if parent not in seen or identifier not in {parent+".R",parent+".T"} or branch["parent_event_id"] not in events:
                raise ValueError("branch: missing actual parent/event")
        seen.add(identifier)
    by_branch = {key:[] for key in branches}
    for segment in segments.values():
        if segment["branch_id"] not in branches:
            raise ValueError("segment: unknown branch")
        _vector(segment["start_m"],3,"segment start")
        _vector(segment["end_m"],3,"segment end")
        _state(segment["state"],media)
        length = _number(segment["length_m"],"segment length",0,10+128*EPS)
        _number(segment["cumulative_end_m"],"segment cumulative",0,10+128*EPS)
        if length <= 0 or segment["event_id"] is not None and segment["event_id"] not in events:
            raise ValueError("segment: nonpositive travel/missing event")
        by_branch[segment["branch_id"]].append(segment)
    creation = ["r0"]
    for identifier,event in events.items():
        if event["segment_id"] not in segments or event["branch_id"] not in branches:
            raise ValueError("event: missing segment/branch")
        segment = segments[event["segment_id"]]
        if segment["event_id"] != identifier or segment["branch_id"] != event["branch_id"] or segment["end_m"] != event["position_m"] or segment["state"] != event["incident_state"] or segment["length_m"] != event["segment_length_m"] or segment["cumulative_end_m"] != event["cumulative_length_m"]:
            raise ValueError("event: disconnected segment/state identity")
        _vector(event["local_uv_m"],2,"event local UV")
        target = _keys(event["target"],TARGET_KEYS,"event target")
        dielectric = target["kind"] == "body_face"
        bounds = _keys(event["numerical_bounds"],COMMON_BOUNDS|(DIELECTRIC_BOUNDS if dielectric else set()),"event bounds")
        if _interval(bounds["t_parameter_interval_m"],"forward bound")[0] <= 0:
            raise ValueError("event: no strictly positive travel proof")
        _intervals(bounds["position_intervals_m"],3,"event point bounds",event["position_m"],width=1e-8)
        _intervals(bounds["local_uv_intervals_m"],2,"event UV bounds",event["local_uv_m"])
        _intervals(bounds["incident_direction_intervals"],3,"incident direction bounds",event["incident_state"]["direction"],width=1e-8)
        _interval(bounds["cumulative_length_interval_m"],"cumulative bound",event["cumulative_length_m"])
        _number(bounds["plane_residual_m"],"plane residual")
        if dielectric:
            allocated = _interface(event,media,faces,branches)
            creation.extend(leg["branch_id"] for leg in allocated)
            for leg in allocated:
                child = branches[leg["branch_id"]]
                if child["parent_id"] != event["branch_id"] or child["parent_event_id"] != identifier or child["origin_m"] != event["position_m"] or child["initial_state"] != leg["state"] or child["start_cumulative_m"] != event["cumulative_length_m"] or child["start_interaction_count"] != branches[event["branch_id"]]["start_interaction_count"]+1:
                    raise ValueError("child: changed exact birth/state identity")
        else:
            if target["kind"] != "element" or target["body_id"] is not None or target["face_id"] is not None or target["element_id"] not in elements or event["incident_state"]["medium_id"] != "exterior":
                raise ValueError("terminal event: unknown exterior terminator")
            expected = "receiver_hit" if elements[target["element_id"]]["kind"] == "receiver" else "stop_hit"
            if event["classification"] != expected or event["interface"] is not None or bounds["outgoing_direction_intervals"] != []:
                raise ValueError("terminal event: fabricated continuation/interface")
    if list(branches) != creation:
        raise ValueError("branches: not stable FIFO R-before-T atomic creation")
    max_interactions = 0
    for identifier,branch in branches.items():
        path = by_branch[identifier]
        if len(path) > 1:
            raise ValueError("branch: every dielectric continuation creates a child record")
        point,state,cumulative = branch["origin_m"],branch["initial_state"],branch["start_cumulative_m"]
        interactions = branch["start_interaction_count"]
        last_event = branch["parent_event_id"]
        for segment in path:
            actual = math.hypot(*(b-a for a,b in zip(segment["start_m"],segment["end_m"])))
            if segment["start_m"] != point or segment["state"] != state or abs(actual-segment["length_m"]) > 128*EPS*max(1,actual) or abs(segment["cumulative_end_m"]-cumulative-segment["length_m"]) > 128*EPS*max(1,segment["cumulative_end_m"]):
                raise ValueError("branch: disconnected physical state/distance")
            point,cumulative = segment["end_m"],segment["cumulative_end_m"]
            if segment["event_id"] is not None:
                last_event = segment["event_id"]
                interactions += 1
        if interactions > 8:
            raise ValueError("branch: ancestry interaction cap exceeded")
        max_interactions=max(max_interactions,interactions)
        children=[child for child in branches.values() if child["parent_id"] == identifier]
        if children:
            if identifier in terminals or not path or branch["outcome"] != ("split" if len(children)==2 else "continued"):
                raise ValueError("parent: duplicated terminal power or wrong outcome")
        else:
            if identifier not in terminals:
                raise ValueError("leaf: missing terminal accounting")
            terminal = terminals[identifier]
            if terminal["category"] != branch["outcome"] or terminal["category"] not in CATEGORIES or terminal["position_m"] != point or terminal["state"] != state or terminal["cumulative_length_m"] != cumulative or terminal["reason"] not in REASONS:
                raise ValueError("terminal: changed carried endpoint/state/outcome")
            radius=math.hypot(*(a-b for a,b in zip(point,scene["source"]["origin_m"])))
            if radius > 1+2e-12:
                raise ValueError("terminal: outside bounded trace domain")
            if terminal["category"] in {"detected","stopped"}:
                event=events.get(terminal["event_id"])
                expected="receiver_hit" if terminal["category"]=="detected" else "stop_hit"
                if event is None or not path or last_event != terminal["event_id"] or event["classification"] != expected or event["branch_id"] != identifier or event["target"]["element_id"] != terminal["element_id"] or terminal["reason"] != expected:
                    raise ValueError("terminal: fabricated physical detection/stop")
            elif terminal["category"] == "escaped":
                if not path or path[-1]["event_id"] is not None or terminal["event_id"] is not None or terminal["element_id"] is not None or terminal["reason"] != "domain_exit" or abs(radius-1) > 2e-13:
                    raise ValueError("terminal: fabricated domain exit")
            else:
                if terminal["reason"] not in REASONS-{"receiver_hit","stop_hit","domain_exit"} or terminal["event_id"] != last_event:
                    raise ValueError("terminal: changed retained resource identity")
                event=events.get(last_event)
                if terminal["element_id"] is not None or event is not None and event["classification"] in {"receiver_hit","stop_hit"}:
                    raise ValueError("resource terminal: physical terminator cannot become unresolved")
                reason=terminal["reason"]
                if reason=="interaction_cap" and interactions != 8 or reason=="event_cap" and len(events)!=32 or reason=="segment_cap" and len(segments)!=64 or reason=="record_cap" and len(events)+len(segments)<95 or reason=="distance_cap" and abs(cumulative-10)>128*EPS*10:
                    raise ValueError("resource terminal: premature cap")
                if reason=="branch_cap" and not any(leg["disposition"]=="resource_unallocated" for e in events.values() if e["interface"] is not None for leg in e["interface"]["legs"]):
                    raise ValueError("resource terminal: no actual atomic branch-cap event")
    if set(terminals)-set(branches):
        raise ValueError("terminal: unknown branch")
    incomplete=any(t["category"]=="resource_unresolved" for t in terminals.values())
    if reply["status"] != ("incomplete" if incomplete else "complete"):
        raise ValueError("status: hidden positive unresolved power")
    ledger=_keys(reply["ledger"],LEDGER_KEYS,"ledger")
    if ledger["input_power"] != 1 or ledger["path_addition"] != PATH_ADDITION:
        raise ValueError("ledger: wrong source/path addition")
    totals={}
    for category,name in (("detected","detected_power"),("stopped","stopped_power"),("escaped","escaped_power"),("resource_unresolved","unresolved_power")):
        total=math.fsum(t["state"]["power_fraction"] for t in terminals.values() if t["category"]==category)
        _same_power(_number(ledger[name],name,0),total,name)
        totals[name]=total
    residual=1-math.fsum(totals.values())
    _same_power(_number(ledger["signed_residual"],"signed residual"),residual,"signed residual")
    if abs(residual)>128*EPS:
        raise ValueError("ledger: missing/duplicated terminal power")
    receiver_totals=ledger["receiver_totals"]
    expected_receivers=[item["id"] for item in scene["elements"] if item["kind"]=="receiver"]
    if type(receiver_totals) is not list or len(receiver_totals)!=len(expected_receivers):
        raise ValueError("receiver totals: missing/extra receiver")
    for record,element_id in zip(receiver_totals,expected_receivers):
        _keys(record,{"element_id","power_fraction","leaf_branch_ids"},"receiver total")
        ids=[t["branch_id"] for t in terminals.values() if t["category"]=="detected" and t["element_id"]==element_id]
        if record["element_id"]!=element_id or record["leaf_branch_ids"]!=ids:
            raise ValueError("receiver total: changed incoherent leaf identities")
        _same_power(_number(record["power_fraction"],"receiver total",0),math.fsum(terminals[i]["state"]["power_fraction"] for i in ids),"receiver total")
    diagnostic=_keys(reply["diagnostics"],DIAGNOSTIC_KEYS,"diagnostics")
    if diagnostic["geometry_policy"] != "binary64_closed_body_outward_v1" or diagnostic["polarization_policy"] != "outward_power_coherency_v1":
        raise ValueError("diagnostics: wrong numerical policy")
    for key in DIAGNOSTIC_KEYS-{"geometry_policy","polarization_policy"}:
        _number(diagnostic[key],"diagnostics."+key,0)
    counts={"created_branches":len(branches),"surface_events":len(events),"segments":len(segments),"max_ancestry_interactions":max_interactions,"record_count":len(events)+len(segments)}
    for key,expected in counts.items():
        if type(diagnostic[key]) is not int or diagnostic[key]!=expected:
            raise ValueError("diagnostics: changed actual graph counts")
    # These maxima are representation invariants. Exit-point enclosures are
    # internal, so the point readout must at least cover every published event.
    states=[branch["initial_state"] for branch in branches.values()]
    states.extend(leg["state"] for event in events.values() if event["interface"] is not None
                  for leg in event["interface"]["legs"] if leg["state"] is not None)
    known={"max_direction_width":0.,"max_frame_width":0.,"max_C_width":0.,
           "max_point_width_m":0.,"max_coefficient_width":0.,"max_local_power_residual":0.,"max_frame_residual":0.}
    for state in states:
        for name,bound in (("max_direction_width","direction_intervals"),("max_frame_width","frame_intervals"),("max_C_width","C_intervals")):
            known[name]=max(known[name],*(hi-lo for lo,hi in state["numerical_bounds"][bound]))
        axes=[state["frame"][name] for name in ("e1","e2","khat")]
        known["max_frame_residual"]=max(known["max_frame_residual"],*(abs(math.fsum(x*y for x,y in zip(a,b))-(1. if i==j else 0.)) for i,a in enumerate(axes) for j,b in enumerate(axes)))
    for event in events.values():
        known["max_point_width_m"]=max(known["max_point_width_m"],*(hi-lo for lo,hi in event["numerical_bounds"]["position_intervals_m"]))
        if event["interface"] is not None:
            interface=event["interface"]
            known["max_local_power_residual"]=max(known["max_local_power_residual"],abs(interface["local_signed_residual"]))
            for coefficient in interface["numerical_bounds"]["coefficient_intervals"]:
                if coefficient is not None:
                    known["max_coefficient_width"]=max(known["max_coefficient_width"],*(hi-lo for lo,hi in coefficient))
    for name,minimum in known.items():
        if diagnostic[name]<minimum:
            raise ValueError("diagnostics: understates returned record bounds/residuals")
    if any(diagnostic[key]>1e-8 for key in ("max_point_width_m","max_direction_width","max_frame_width","max_coefficient_width","max_C_width")) or diagnostic["max_local_power_residual"]>128*EPS or diagnostic["max_frame_residual"]>128*EPS:
        raise ValueError("diagnostics: unsupported accumulated arithmetic")
    return reply


def encode_trace_result(request_id: str, scene_sha256: str, result: dict) -> bytes:
    """Validate/encode the complete result inside the actual worker lifetime."""
    _keys(result,CORE_KEYS,"core W4 result")
    reply={"protocol_version":1,"message_type":"fresnel_trace_result","request_id":request_id,
           "model_contract":MODEL_CONTRACT,"scene_sha256":scene_sha256,**result}
    validate_trace_reply(reply,request_id=request_id,scene_sha256=scene_sha256)
    return _bounded(reply)


def _response_json(data: bytes) -> object:
    if type(data) is not bytes:
        raise TypeError("W4 response: expected bytes")
    if len(data)>MAX_RESPONSE_BYTES:
        raise ValueError("W4 response: exceeds384KiB")
    def pairs(values):
        result={}
        for key,value in values:
            if key in result:
                raise ValueError("W4 response: duplicate key")
            result[key]=value
        return result
    def real(token):
        value=float(token)
        if not math.isfinite(value) or value==0 and any(c in "123456789" for c in token.lower().split("e",1)[0]):
            raise ValueError("W4 response: unusable finite binary64 scalar")
        return value
    def integer(token):
        value=int(token)
        _number(value,"JSON integer")
        return value
    def constant(_):
        raise ValueError("W4 response: nonfinite constant")
    try:
        return json.loads(data.decode("utf-8",errors="strict"),object_pairs_hook=pairs,parse_float=real,parse_int=integer,parse_constant=constant)
    except (UnicodeError,json.JSONDecodeError,RecursionError,OverflowError) as exc:
        raise ValueError("W4 response: expected strict bounded UTF-8 JSON") from exc


def decode_trace_result(data: bytes, **identity) -> dict:
    """Decode genuine bounded response bytes; never replay scientific work."""
    return validate_trace_reply(_response_json(data),**identity)


def decode_validation_reply(data: bytes, **identity) -> dict:
    """Decode pure metadata with the same closed identity/byte policy."""
    return validate_validation_reply(_response_json(data),**identity)


def error_reply(request_id: str|None, code: str, message: str, scene_sha256: str|None=None) -> bytes:
    """Encode a flat bounded declared error, without a partial route graph."""
    if request_id is not None:
        validate_request_id(request_id)
    if scene_sha256 is not None:
        validate_digest(scene_sha256)
    if type(code) is not str or code not in ERROR_CODES:
        raise ValueError("W4 error: undeclared error code")
    if type(message) is not str:
        raise TypeError("W4 error: message must be text")
    return json_bytes({"protocol_version":1,"message_type":"fresnel_routing_error","request_id":request_id,
                       "model_contract":MODEL_CONTRACT,"scene_sha256":scene_sha256,"code":code,"message":message[:300]})
