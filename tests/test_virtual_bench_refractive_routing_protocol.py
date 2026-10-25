"""Closed W3 wire tests; synthetic records prove representation, not optics."""
from copy import deepcopy
import json
import math

import pytest

from apps.virtual_bench import refractive_routing_protocol as protocol
from apps.virtual_bench import geometric_routing_protocol as w2
from test_virtual_bench_geometric_routing_protocol import (
    REQUEST_ID, core_record as old_core, scene as old_scene,
)


def scene():
    value = old_scene()
    value.update(model_contract=protocol.MODEL_CONTRACT,
                 exterior_medium={"id": "exterior", "refractive_index": 1.0}, bodies=[])
    return value


def body_scene():
    value = scene()
    value["source"]["origin_m"] = [0., 0., -.2]
    value["bodies"] = [{"id": "B", "kind": "rectangular_block",
        "pose": {"position_m": [0., 0., 0.], "rotation_xyz_rad": [0., 0., 0.]},
        "shape": {"width_x_m": .1, "height_y_m": .1, "depth_z_m": .1},
        "interior_medium": {"id": "body:B", "refractive_index": 1.5}}]
    return value


def enclosing(values):
    return [[math.nextafter(value, -math.inf), math.nextafter(value, math.inf)] for value in values]


def core_record():
    """Independently wrap the original handwritten W2 representation fixture."""
    previous = old_core()
    result = {"scene": scene(), "weight_model": protocol.WEIGHT_MODEL,
              "media": [{"id": "exterior", "refractive_index": 1.}], "body_faces": [],
              "legacy_surface_frames": previous["surface_frames"],
              "limits": dict(protocol.NO_BODY_LIMITS), "status": previous["status"],
              "branches": [], "segments": [], "events": [], "terminals": [],
              "ledger": previous["ledger"], "diagnostics": previous["diagnostics"]}
    for record in previous["branches"]:
        item = deepcopy(record)
        item["parent_event_id"] = item.pop("parent_hit_id")
        item.update(initial_medium_id="exterior", initial_refractive_index=1.)
        result["branches"].append(item)
    for name in ("segments", "terminals"):
        for record in previous[name]:
            item = deepcopy(record)
            item["event_id"] = item.pop("hit_id")
            item.update(medium_id="exterior", refractive_index=1.)
            result[name].append(item)
    for record in previous["hits"]:
        item = deepcopy(record)
        item["target"] = {"kind": "element", "element_id": item.pop("element_id")}
        item.update(classification="receiver_hit", incident_medium_id="exterior", incident_refractive_index=1.)
        item["numerical_bounds"].update(incident_direction_intervals=enclosing(item["incident_direction"]),
            outgoing_direction_intervals=[], cumulative_length_interval_m=enclosing([item["cumulative_length_m"]])[0])
        result["events"].append(item)
    return result


def wire(value=None):
    value = core_record() if value is None else value
    return json.loads(protocol.encode_trace_result(REQUEST_ID, protocol.scene_digest(value["scene"]), value))


def genuine_body_wire():
    from apps.virtual_bench import refractive_routing_adapter as adapter
    value = {"request_id": REQUEST_ID, "scene": body_scene()}
    admitted = adapter.validate_submission(value)
    return json.loads(adapter.trace_submission(admitted))


def test_independent_no_body_wire_roundtrip_and_exact_ten_key_projection():
    original = core_record()
    snapshot = deepcopy(original)
    value = wire(original)
    encoded = protocol.json_bytes(value)
    assert protocol.decode_trace_result(encoded, request_id=REQUEST_ID, scene=scene()) == value
    assert original == snapshot
    assert protocol.project_w2_result(value) == old_core()
    assert value["segments"][0]["id"] == "s0000" and value["events"][0]["id"] == "h0000"
    assert value["diagnostics"] == old_core()["diagnostics"]
    assert value["limits"]["max_branches"] == 63


@pytest.mark.parametrize("change", [
    lambda p: p.update(extra=True), lambda p: p.update(protocol_version=True),
    lambda p: p.update(model_contract=w2.MODEL_CONTRACT),
    lambda p: p.update(message_type="trace_result"),
    lambda p: p.update(request_id="00000000-0000-4000-8000-000000000001"),
    lambda p: p.update(scene_sha256="0" * 64),
    lambda p: p["branches"][0].update(initial_medium_id="body:missing"),
    lambda p: p["segments"][0].update(refractive_index=1.5),
    lambda p: p["events"][0].update(incident_medium_id="body:missing"),
    lambda p: p["events"][0].update(classification="exit_refraction"),
    lambda p: p["events"][0]["target"].update(kind="body_face"),
    lambda p: p["terminals"][0].update(medium_id="body:missing"),
    lambda p: p["ledger"].update(detected_weight=.5),
    lambda p: p["limits"].update(max_branches=31),
    lambda p: p["events"][0]["numerical_bounds"].update(incident_direction_intervals=[[0., 0.]] * 3),
    lambda p: p["events"][0]["numerical_bounds"].update(outgoing_direction_intervals=[{"branch_id": "r0", "direction_intervals": [[0., 0.]] * 3}]),
    lambda p: p["events"][0]["numerical_bounds"].update(cumulative_length_interval_m=[0., 0.]),
    lambda p: p["segments"][0].update(length_m=True),
    lambda p: p["events"][0].update(transmitted_angle_rad=math.pi / 2),
])
def test_closed_identity_graph_medium_and_enclosure_faults_reject_atomically(change):
    value = wire()
    change(value)
    with pytest.raises((TypeError, ValueError)):
        protocol.validate_trace_reply(value, request_id=REQUEST_ID)


def test_no_body_does_not_gain_the_body_width_policy():
    value = wire()
    value["events"][0]["numerical_bounds"]["incident_direction_intervals"] = [[-1., 1.], [-1., 1.], [0., 2.]]
    assert protocol.validate_trace_reply(value) is value
    value["diagnostics"]["max_point_width_m"] = 0.
    with pytest.raises(ValueError):
        protocol.validate_trace_reply(value)


def test_genuine_body_three_event_roundtrip_and_conditional_caps():
    value = genuine_body_wire()
    assert protocol.decode_trace_result(protocol.json_bytes(value)) == value
    assert len(value["body_faces"]) == 6
    assert [event["classification"] for event in value["events"]] == ["enter_refraction", "exit_refraction", "receiver_hit"]
    assert [segment["medium_id"] for segment in value["segments"]] == ["exterior", "body:B", "exterior"]
    assert value["events"][0]["id"] == "e0001" and value["segments"][0]["id"] == "s0001"
    assert value["limits"] == protocol.LIMITS


@pytest.mark.parametrize("face_index,interval", [
    pytest.param(0, [-1., 1.], id="other-face-unresolved-sign"),
    pytest.param(0, [-1., 0.], id="other-face-touching-zero"),
    pytest.param(4, [-1., -.5], id="hit-face-missing-zero"),
])
def test_body_halfspace_certificates_require_one_hit_and_strict_other_faces(face_index, interval):
    value = genuine_body_wire()
    assert [face["face_id"] for face in value["body_faces"]] == [
        "x_min", "x_max", "y_min", "y_max", "z_min", "z_max",
    ]
    event = value["events"][0]
    assert event["target"]["face_id"] == "z_min"
    event["numerical_bounds"]["body_halfspace_intervals_m"][face_index] = interval
    with pytest.raises(ValueError):
        protocol.validate_trace_reply(value)


@pytest.mark.parametrize("defect", ["face", "body", "normal", "index", "entry", "tir_toggle", "side", "critical", "bounds", "halfspace", "width", "ordinal", "missing_face", "extra_fresnel"])
def test_genuine_body_graph_detects_forced_scientific_representation_faults(defect):
    value = genuine_body_wire()
    event = value["events"][0]
    if defect == "face": event["target"]["face_id"] = "nonexistent"
    elif defect == "body": event["target"]["body_id"] = "another"
    elif defect == "normal": event["outward_normal"] = [0., 0., 1.]
    elif defect == "index": event["outgoing"][0]["refractive_index"] = 1.
    elif defect == "entry": event["classification"] = "exit_refraction"
    elif defect == "tir_toggle":
        event["classification"] = "total_internal_reflection"
        event["numerical_bounds"].update(snell_discriminant_interval=[-1., -.5], outgoing_side_interval=[.5, 1.])
    elif defect == "side": event["numerical_bounds"]["incident_side_interval"] = [-1., 1.]
    elif defect == "critical": event["numerical_bounds"]["snell_discriminant_interval"] = [-1., 1.]
    elif defect == "bounds": event["numerical_bounds"]["position_intervals_m"][2] = [1., 2.]
    elif defect == "halfspace": event["numerical_bounds"]["body_halfspace_intervals_m"][0] = [1., 2.]
    elif defect == "width": event["numerical_bounds"]["incident_direction_intervals"][0] = [-1e-7, 1e-7]
    elif defect == "ordinal": value["segments"][0]["id"] = "s0000"
    elif defect == "missing_face": value["body_faces"].pop()
    else: event["fresnel_transmission"] = 1.
    with pytest.raises((TypeError, ValueError)):
        protocol.validate_trace_reply(value)


@pytest.mark.parametrize("data", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'{"a":1e-999}', b'\xff'])
def test_strict_request_and_response_parser_reject_without_partial_object(data):
    with pytest.raises((TypeError, ValueError)):
        protocol.strict_json_loads(data)
    with pytest.raises((TypeError, ValueError)):
        protocol.decode_trace_result(data)


def test_atomic_byte_caps_and_error_whitelist():
    with pytest.raises(ValueError): protocol.strict_json_loads(b" " * (protocol.MAX_BODY_BYTES + 1))
    with pytest.raises(ValueError): protocol.decode_trace_result(b" " * (protocol.MAX_RESPONSE_BYTES + 1))
    with pytest.raises(ValueError): protocol.error_reply(REQUEST_ID, "undeclared", "bad")
    with pytest.raises(TypeError): protocol.error_reply(REQUEST_ID, "invalid_scene", 1)
    value = json.loads(protocol.error_reply(REQUEST_ID, "medium_state_ambiguity", "x" * 500))
    assert set(value) == {"protocol_version", "message_type", "model_contract", "request_id", "error"}
    assert value["message_type"] == "refractive_routing_error"
    assert len(value["error"]["message"]) == 300 and "events" not in value


def test_validation_metadata_requires_exact_media_faces_caps_and_no_trace(monkeypatch):
    from apps.virtual_bench import refractive_routing_adapter as adapter
    monkeypatch.setattr(adapter, "trace_routes", lambda *_: pytest.fail("validation traced"))
    admitted = adapter.validate_submission({"request_id": REQUEST_ID, "scene": body_scene()})
    value = protocol.decode_validation_reply(adapter.validation_reply(admitted))
    for defect in ("media", "faces", "limits", "basis", "bool_index"):
        changed = deepcopy(value)
        if defect == "media": changed["media"].reverse()
        elif defect == "faces": changed["body_faces"][0]["face_id"] = "x_max"
        elif defect == "limits": changed["limits"]["max_records"] = 256
        elif defect == "basis": changed["body_faces"][0]["numerical_bounds"]["basis_u_intervals"][0] = [99., 100.]
        else: changed["media"][0]["refractive_index"] = True
        with pytest.raises((TypeError, ValueError)):
            protocol.validate_validation_reply(changed)
