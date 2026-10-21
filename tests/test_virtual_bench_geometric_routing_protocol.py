"""Independent W2 wire fixtures; synthetic schema stress is not optical evidence."""
from __future__ import annotations

from copy import deepcopy
import json
import math

import pytest

from apps.virtual_bench import geometric_routing_protocol as protocol

REQUEST_ID = "12345678-1234-4234-8234-123456789abc"


def scene():
    return {"schema_version": 1, "model_contract": protocol.MODEL_CONTRACT,
            "source": {"id": "source", "origin_m": [0.0, 0.0, 0.0],
                       "direction": [0.0, 0.0, 1.0], "relative_weight": 1.0},
            "elements": [{"id": "D", "kind": "receiver",
                          "pose": {"position_m": [0.0, 0.0, .2],
                                   "rotation_xyz_rad": [0.0, 0.0, 0.0]},
                          "aperture": {"kind": "disk", "radius_m": .025}}]}


def branch(identifier="r0", **changes):
    value = {"id": identifier, "parent_id": None, "parent_hit_id": None,
             "origin_m": [0.0, 0.0, 0.0], "initial_direction": [0.0, 0.0, 1.0],
             "relative_weight": 1.0, "start_cumulative_m": 0.0,
             "start_interaction_count": 0, "outcome": "detected"}
    value.update(changes)
    return value


def bounds(point, distance):
    return {"t_parameter_interval_m": [math.nextafter(distance, -math.inf),
                                        math.nextafter(distance, math.inf)],
            "position_intervals_m": [[math.nextafter(v, -math.inf), math.nextafter(v, math.inf)] for v in point],
            "local_uv_intervals_m": [[-1e-18, 1e-18], [-1e-18, 1e-18]],
            "plane_residual_m": 0.0}


def core_record():
    return {"scene": scene(), "surface_frames": [{"element_id": "D", "u": [1.0, 0.0, 0.0],
             "v": [0.0, 1.0, 0.0], "n": [0.0, 0.0, 1.0]}],
            "limits": dict(protocol.LIMITS), "status": "complete", "branches": [branch()],
            "segments": [{"id": "s0000", "branch_id": "r0", "start_m": [0.0, 0.0, 0.0],
              "end_m": [0.0, 0.0, .2], "direction": [0.0, 0.0, 1.0],
              "relative_weight": 1.0, "length_m": .2, "cumulative_end_m": .2, "hit_id": "h0000"}],
            "hits": [{"id": "h0000", "segment_id": "s0000", "branch_id": "r0", "element_id": "D",
              "position_m": [0.0, 0.0, .2], "local_uv_m": [0.0, 0.0], "incident_direction": [0.0, 0.0, 1.0],
              "incoming_weight": 1.0, "outgoing": [], "segment_length_m": .2,
              "cumulative_length_m": .2, "numerical_bounds": bounds([0.0, 0.0, .2], .2)}],
            "terminals": [{"branch_id": "r0", "category": "detected", "element_id": "D", "hit_id": "h0000",
              "position_m": [0.0, 0.0, .2], "cumulative_length_m": .2, "relative_weight": 1.0, "reason": "receiver_hit"}],
            "ledger": {"input_weight": 1.0, "detected_weight": 1.0, "absorbed_weight": 0.0,
              "escaped_weight": 0.0, "truncated_weight": 0.0, "signed_residual": 0.0},
            "diagnostics": {"predicate_policy": "binary64_outward_intervals_v1", "max_direction_norm_residual": 0.0,
              "max_frame_orthogonality_residual": 0.0, "max_plane_residual_m": 0.0, "max_point_error_bound_m": 1e-15}}


def encoded(value=None):
    value = core_record() if value is None else value
    return protocol.encode_trace_result(REQUEST_ID, protocol.scene_digest(value["scene"]), value)


def wire(value=None):
    return json.loads(encoded(value))


def stress_record():
    """Max record/branch/identifier representation only, NOT a physical route.

    This independently authored closed graph stresses serializer and relationships.
    No expected optical answer is derived from it or claimed by its acceptance.
    """
    result = core_record()
    source_scene = scene()
    source_scene["elements"] = []
    names = {kind: kind[0].upper() + "a" * 63 for kind in ("splitter", "mirror", "detector")}
    for kind, optical in (("splitter", "ideal_splitter_50_50"), ("mirror", "mirror"), ("detector", "receiver")):
        item = deepcopy(scene()["elements"][0])
        item["id"], item["kind"] = names[kind], optical
        source_scene["elements"].append(item)
    for index in range(13):
        item = deepcopy(scene()["elements"][0])
        item["id"] = f"Unused{index}" + "b" * (64 - len(f"Unused{index}"))
        item["kind"] = "beam_stop"
        source_scene["elements"].append(item)
    result.update(scene=source_scene, branches=[branch()], segments=[], hits=[], terminals=[])
    result["surface_frames"] = [{"element_id": item["id"], "u": [1.0, 0.0, 0.0],
                                "v": [0.0, 1.0, 0.0], "n": [0.0, 0.0, 1.0]}
                               for item in source_scene["elements"]]
    queue = [result["branches"][0]]
    leaf_index = 0
    while queue:
        current = queue.pop(0)
        depth = current["start_interaction_count"]
        splitting = current["id"].replace(".R", "") == "r0" and depth < 31
        if splitting:
            count = 1
            current["outcome"] = "split"
        else:
            count = (31, 30, 7)[leaf_index] if leaf_index < 3 else 1
            leaf_index += 1
        point, cumulative = list(current["origin_m"]), current["start_cumulative_m"]
        for within in range(count):
            start = point
            point = [start[0], start[1], start[2] + .001]
            length = math.hypot(*(b-a for a, b in zip(start, point)))
            cumulative += length
            ordinal = len(result["segments"])
            segment_id, hit_id = f"s{ordinal:04}", f"h{ordinal:04}"
            outgoing = []
            if splitting:
                element = names["splitter"]
                for suffix in (".T", ".R"):
                    child = branch(current["id"] + suffix, parent_id=current["id"], parent_hit_id=hit_id,
                                   origin_m=list(point), relative_weight=current["relative_weight"] * .5,
                                   start_cumulative_m=cumulative, start_interaction_count=depth + 1)
                    result["branches"].append(child)
                    queue.append(child)
                    outgoing.append({"branch_id": child["id"], "direction": [0.0, 0.0, 1.0],
                                     "relative_weight": child["relative_weight"]})
            elif within < count - 1:
                element = names["mirror"]
                outgoing = [{"branch_id": current["id"], "direction": [0.0, 0.0, 1.0],
                             "relative_weight": current["relative_weight"]}]
            else:
                element = names["detector"]
            result["segments"].append({"id": segment_id, "branch_id": current["id"], "start_m": start,
                "end_m": list(point), "direction": [0.0, 0.0, 1.0], "relative_weight": current["relative_weight"],
                "length_m": length, "cumulative_end_m": cumulative, "hit_id": hit_id})
            result["hits"].append({"id": hit_id, "segment_id": segment_id, "branch_id": current["id"],
                "element_id": element, "position_m": list(point), "local_uv_m": [0.0, 0.0],
                "incident_direction": [0.0, 0.0, 1.0], "incoming_weight": current["relative_weight"],
                "outgoing": outgoing, "segment_length_m": length, "cumulative_length_m": cumulative,
                "numerical_bounds": bounds(point, length)})
        if not splitting:
            result["terminals"].append({"branch_id": current["id"], "category": "detected",
              "element_id": names["detector"], "hit_id": hit_id, "position_m": list(point),
              "cumulative_length_m": cumulative, "relative_weight": current["relative_weight"], "reason": "receiver_hit"})
    assert len(result["branches"]) == 63 and len(result["segments"]) == len(result["hits"]) == 128
    return result


def test_independent_direct_fixture_roundtrip_identity_and_no_mutation():
    original = core_record()
    before = deepcopy(original)
    body = encoded(original)
    decoded = protocol.decode_trace_result(body, request_id=REQUEST_ID, scene=original["scene"],
                                            scene_sha256=protocol.scene_digest(original["scene"]))
    assert original == before
    assert decoded["hits"][0]["local_uv_m"] == [0.0, 0.0]
    decoded["scene"]["source"]["origin_m"][0] = .5
    assert original == before and body == encoded(original)


def test_canonical_digest_uses_exact_owned_values_and_preserves_catalog_order():
    a = scene()
    reordered_object = {key: a[key] for key in reversed(a)}
    assert protocol.scene_digest(a) == protocol.scene_digest(reordered_object)
    changed = deepcopy(a)
    changed["source"]["origin_m"][0] = -0.0
    assert protocol.scene_digest(a) != protocol.scene_digest(changed)
    changed = deepcopy(a)
    changed["elements"].append({**deepcopy(changed["elements"][0]), "id": "D2"})
    reversed_elements = deepcopy(changed)
    reversed_elements["elements"].reverse()
    assert protocol.scene_digest(changed) != protocol.scene_digest(reversed_elements)


@pytest.mark.parametrize("data", [
    b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":1e999}',
    b'{"a":1e-999}', b'{"a":-2e-999}', b'{"a":' + b"9" * 400 + b"}",
    b"\xff", b'{"a":1} trailing', b'{"a":[', b" " * 32769,
], ids=["duplicate", "nan", "infinity", "overflow", "underflow",
        "negative-underflow", "integer-overflow", "invalid-utf8",
        "trailing-data", "truncated", "request-over-byte-cap"])
def test_strict_request_parser_rejects_bad_original_bytes(data):
    with pytest.raises((TypeError, ValueError)):
        protocol.strict_json_loads(data)


@pytest.mark.parametrize("data", [b"true", b"null", b"[]", b'{"signed":-0.0,"zero":0e-999}'])
def test_parser_preserves_legal_json_without_claiming_scene_validity(data):
    result = protocol.strict_json_loads(data)
    assert result == json.loads(data)


@pytest.mark.parametrize("identifier", ["", "ABC", "12345678-1234-1234-8234-123456789abc",
                                       REQUEST_ID.upper(), True, None])
def test_uuid_is_exact_canonical_v4(identifier):
    with pytest.raises((TypeError, ValueError)):
        protocol.validate_request_id(identifier)


def test_validation_reply_is_closed_bounded_and_carries_full_frames():
    value = core_record()
    body = protocol.encode_validation_reply(REQUEST_ID, value["scene"], value["surface_frames"])
    reply = json.loads(body)
    assert set(reply) == {"protocol_version", "message_type", "request_id", "model_contract",
                          "scene_sha256", "scene", "surface_frames"}
    assert reply["message_type"] == "scene_validation" and reply["scene"] == value["scene"]
    assert len(body) < protocol.MAX_RESPONSE_BYTES == 524288


@pytest.mark.parametrize("mutate", [
    lambda x: x.update(extra=1),
    lambda x: x.update(protocol_version=True),
    lambda x: x.update(message_type="old_model"),
    lambda x: x.update(scene_sha256="0"*64),
    lambda x: x["limits"].update(max_records=257),
    lambda x: x["branches"].append(deepcopy(x["branches"][0])),
    lambda x: x["branches"][0].update(parent_id="r0"),
    lambda x: x["segments"][0].update(branch_id="r0.R"),
    lambda x: x["segments"][0].update(hit_id="missing"),
    lambda x: x["segments"][0].update(length_m=.1),
    lambda x: x["hits"][0].update(element_id="fake"),
    lambda x: x["hits"][0].update(outgoing=[{"branch_id":"r0","direction":[0.,0.,1.],"relative_weight":1.}]),
    lambda x: x["hits"][0]["numerical_bounds"]["position_intervals_m"][2].__setitem__(1, .1),
    lambda x: x["hits"][0]["numerical_bounds"]["t_parameter_interval_m"].__setitem__(0, 0.),
    lambda x: x["terminals"][0].update(relative_weight=.5),
    lambda x: x["terminals"][0].update(reason="domain_exit"),
    lambda x: x["terminals"][0].update(position_m=[0.,0.,.3]),
    lambda x: x["ledger"].update(detected_weight=2.),
    lambda x: x["ledger"].update(signed_residual=1.),
    lambda x: x.update(status="incomplete"),
    lambda x: x["diagnostics"].update(max_point_error_bound_m=float("nan")),
    lambda x: x["surface_frames"][0].update(u=[0.,0.,0.]),
])
def test_closed_graph_rejects_changed_relationships_identity_and_values(mutate):
    value = wire()
    mutate(value)
    with pytest.raises((TypeError, ValueError)):
        protocol.validate_trace_reply(value)


def test_genuine_bytes_cannot_be_attached_to_a_different_request_or_scene():
    body = encoded()
    with pytest.raises(ValueError, match="request"):
        protocol.decode_trace_result(body, request_id="22345678-1234-4234-8234-123456789abc")
    changed = scene()
    changed["source"]["origin_m"][0] = .01
    with pytest.raises(ValueError, match="scene"):
        protocol.decode_trace_result(body, scene=changed)
    with pytest.raises(ValueError):
        protocol.decode_trace_result(body + b"\n{}")


def test_exact_record_branch_identifier_stress_and_fixed_encoder_cap(monkeypatch):
    value = stress_record()
    body = encoded(value)
    reply = protocol.decode_trace_result(body)
    assert len(reply["branches"]) == 63 and len(reply["hits"]) == 128 and len(reply["segments"]) == 128
    assert max(len(branch["id"]) for branch in reply["branches"]) == 64
    assert len(reply["scene"]["elements"]) == 16
    assert max(len(e["id"]) for e in reply["scene"]["elements"]) == 64
    assert len(body) <= 524288
    monkeypatch.setattr(protocol, "MAX_RESPONSE_BYTES", len(body)-1)
    with pytest.raises(ValueError, match="exceeds"):
        encoded(value)


def test_one_extra_record_or_branch_is_not_silently_omitted():
    value = stress_record()
    value["segments"].append({**deepcopy(value["segments"][-1]), "id": "extra"})
    with pytest.raises(ValueError, match="cap"):
        encoded(value)
    value = stress_record()
    value["branches"].append({**deepcopy(value["branches"][-1]), "id": "r0" + ".T"*31})
    with pytest.raises(ValueError, match="cap"):
        encoded(value)


def test_error_is_bounded_and_contains_no_partial_trace():
    value = json.loads(protocol.error_reply(None, "numerical_ambiguity", "x"*400))
    assert set(value) == {"protocol_version","message_type","request_id","model_contract","error"}
    assert value["message_type"] == "routing_error" and value["request_id"] is None
    assert len(value["error"]["message"]) == 300
    with pytest.raises(ValueError):
        protocol.error_reply(None, "../bad", "bad")


def test_receiver_cannot_continue_into_an_escaped_segment():
    value = wire()
    value["branches"][0]["outcome"] = "escaped"
    value["segments"].append({"id": "s0001", "branch_id": "r0", "start_m": [0.,0.,.2],
        "end_m": [0.,0.,.3], "direction": [0.,0.,1.], "relative_weight": 1.,
        "length_m": .1, "cumulative_end_m": .3, "hit_id": None})
    value["terminals"][0].update(category="escaped",element_id=None,hit_id=None,
        position_m=[0.,0.,.3],cumulative_length_m=.3,reason="domain_exit")
    value["ledger"].update(detected_weight=0.,escaped_weight=1.)
    with pytest.raises(ValueError,match="terminating"):
        protocol.validate_trace_reply(value)


def test_domain_escape_cannot_relabel_an_actual_receiver_hit():
    value = wire()
    value["branches"][0]["outcome"] = "escaped"
    value["terminals"][0].update(category="escaped",element_id=None,hit_id=None,reason="domain_exit")
    value["ledger"].update(detected_weight=0.,escaped_weight=1.)
    with pytest.raises(ValueError,match="nonhit endpoint"):
        protocol.validate_trace_reply(value)


@pytest.mark.parametrize("retained_hit",[None,"h0000"],ids=["lost-last-hit","receiver-priority"])
def test_truncation_retains_last_hit_and_cannot_override_receiver_priority(retained_hit):
    value = wire()
    value["branches"][0]["outcome"] = "resource_truncated"
    value["status"] = "incomplete"
    value["terminals"][0].update(category="resource_truncated",hit_id=retained_hit,reason="record_cap")
    value["ledger"].update(detected_weight=0.,truncated_weight=1.)
    with pytest.raises(ValueError,match="last actual hit|precedes"):
        protocol.validate_trace_reply(value)


def test_zero_travel_is_not_a_physical_segment():
    value = wire()
    value["segments"][0]["length_m"] = 0.
    with pytest.raises(ValueError,match="positive length"):
        protocol.validate_trace_reply(value)


def test_schema_graph_branch_creation_order_is_transmitted_then_reflected():
    value = wire(stress_record())
    value["branches"][1],value["branches"][2]=value["branches"][2],value["branches"][1]
    with pytest.raises(ValueError,match="creation order"):
        protocol.validate_trace_reply(value)


@pytest.mark.parametrize("axis,value", [("v", [1.,0.,0.]), ("n", [0.,0.,-1.])],
                         ids=["nonorthogonal", "left-handed"])
def test_frame_axes_must_form_the_returned_right_handed_orthonormal_frame(axis, value):
    value_record = wire()
    value_record["surface_frames"][0][axis] = value
    with pytest.raises(ValueError, match="orthogonal|handedness"):
        protocol.validate_trace_reply(value_record)


def split_birth_cap_record():
    """Schema-only fixture: queued children may retain their actual parent hit."""
    value = core_record()
    value["scene"]["elements"][0]["kind"] = "ideal_splitter_50_50"
    value["status"] = "incomplete"
    value["branches"][0]["outcome"] = "split"
    hit = value["hits"][0]
    hit["outgoing"] = []
    value["terminals"] = []
    for suffix, direction in (("T", [0.,0.,1.]), ("R", [0.,0.,-1.])):
        identifier = "r0."+suffix
        value["branches"].append(branch(identifier, parent_id="r0", parent_hit_id="h0000",
            origin_m=[0.,0.,.2], initial_direction=direction, relative_weight=.5,
            start_cumulative_m=.2, start_interaction_count=1, outcome="resource_truncated"))
        hit["outgoing"].append({"branch_id":identifier,"direction":direction,"relative_weight":.5})
        value["terminals"].append({"branch_id":identifier,"category":"resource_truncated",
            "element_id":"D","hit_id":"h0000","position_m":[0.,0.,.2],
            "cumulative_length_m":.2,"relative_weight":.5,"reason":"record_cap"})
    value["ledger"].update(detected_weight=0.,truncated_weight=1.)
    return value


def test_unprocessed_children_keep_parent_birth_hit_without_fabricating_own_segments():
    value = protocol.decode_trace_result(encoded(split_birth_cap_record()))
    assert len(value["segments"]) == len(value["hits"]) == 1
    assert [x["hit_id"] for x in value["terminals"]] == ["h0000", "h0000"]
    assert value["ledger"]["truncated_weight"] == 1.


@pytest.mark.parametrize("defect", ["transmitted-direction", "retained-element", "early-interaction-cap",
                                  "early-distance-cap", "mirror-no-outgoing", "record-ordinal",
                                  "excess-direction-residual"], ids=str)
def test_cross_language_metadata_relationship_guards(defect):
    value = wire(split_birth_cap_record())
    if defect == "transmitted-direction":
        value["hits"][0]["outgoing"][0]["direction"] = [0.,0.,-1.]
        value["branches"][1]["initial_direction"] = [0.,0.,-1.]
    elif defect == "retained-element":
        value["terminals"][0]["element_id"] = None
    elif defect == "early-interaction-cap":
        value["terminals"][0]["reason"] = "interaction_cap"
    elif defect == "early-distance-cap":
        value["terminals"][0]["reason"] = "distance_cap"
    elif defect == "mirror-no-outgoing":
        value = wire()
        value["scene"]["elements"][0]["kind"] = "mirror"
        value["scene_sha256"] = protocol.scene_digest(value["scene"])
    elif defect == "record-ordinal":
        value["segments"][0]["id"] = "s0042"
        value["hits"][0]["segment_id"] = "s0042"
    else:
        value["diagnostics"]["max_direction_norm_residual"] = 129*protocol.EPS
    with pytest.raises(ValueError):
        protocol.validate_trace_reply(value)


def test_domain_endpoint_cannot_be_published_inside_the_source_centred_sphere():
    value = wire()
    value["scene"]["elements"] = []
    value["surface_frames"] = []
    value["scene_sha256"] = protocol.scene_digest(value["scene"])
    value["hits"] = []
    value["segments"][0]["hit_id"] = None
    value["branches"][0]["outcome"] = "escaped"
    value["terminals"][0].update(category="escaped",element_id=None,hit_id=None,reason="domain_exit")
    value["ledger"].update(detected_weight=0.,escaped_weight=1.)
    with pytest.raises(ValueError,match="trace-domain"):
        protocol.validate_trace_reply(value)
