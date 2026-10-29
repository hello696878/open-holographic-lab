"""Closed W4 wire tests; handwritten fixtures prove transport, not optics."""
from copy import deepcopy
import json
import math

import pytest

from apps.virtual_bench import fresnel_routing_protocol as protocol

REQUEST_ID = "12345678-1234-4234-8234-123456789abc"


def scene():
    return {"schema_version":1,"model_contract":protocol.MODEL_CONTRACT,
        "path_addition":protocol.PATH_ADDITION,
        "source":{"id":"source","origin_m":[0.,.08,-.04],"direction":[0.,0.,1.],
                  "frame_policy":"world_xy_forward_z_v1","polarization":"unpolarized"},
        "exterior_medium":{"id":"exterior","refractive_index":1.},"bodies":[],
        "elements":[{"id":"D1","kind":"receiver","pose":{"position_m":[0.,.08,.12],
            "rotation_xyz_rad":[0.,0.,0.]},"aperture":{"kind":"disk","radius_m":.01}}]}


def body_scene():
    value=scene()
    value["bodies"]=[{"id":"B1","kind":"rectangular_block",
        "pose":{"position_m":[0.,.08,.015],"rotation_xyz_rad":[0.,0.,0.]},
        "shape":{"width_x_m":.12,"height_y_m":.08,"depth_z_m":.03},
        "interior_medium":{"id":"body:B1","refractive_index":1.5}}]
    value["elements"].append({"id":"R1","kind":"receiver",
        "pose":{"position_m":[0.,.08,-.12],"rotation_xyz_rad":[0.,0.,0.]},
        "aperture":{"kind":"disk","radius_m":.01}})
    return value


def enclosing(values):
    return [[math.nextafter(value,-math.inf),math.nextafter(value,math.inf)] for value in values]


def state():
    return {"direction":[0.,0.,1.],"medium_id":"exterior","refractive_index":1.,
        "frame":{"e1":[1.,0.,0.],"e2":[0.,1.,0.],"khat":[0.,0.,1.]},
        "C":[.5,.5,0.,0.],"power_fraction":1.,"numerical_bounds":{
            "direction_intervals":enclosing([0.,0.,1.]),
            "frame_intervals":enclosing([1.,0.,0.,0.,1.,0.,0.,0.,1.]),
            "C_intervals":enclosing([.5,.5,0.,0.]),"power_interval":enclosing([1.])[0]}}


def core_record():
    ray=state()
    return {"scene":scene(),"power_policy":protocol.POWER_POLICY,"path_addition":protocol.PATH_ADDITION,
        "media":[{"id":"exterior","refractive_index":1.}],"body_faces":[],
        "terminal_frames":[{"element_id":"D1","u":[1.,0.,0.],"v":[0.,1.,0.],"n":[0.,0.,1.]}],
        "limits":dict(protocol.LIMITS),"status":"complete",
        "branches":[{"id":"r0","parent_id":None,"parent_event_id":None,
            "origin_m":[0.,.08,-.04],"initial_state":deepcopy(ray),"start_cumulative_m":0.,
            "start_interaction_count":0,"outcome":"detected"}],
        "segments":[{"id":"s0001","branch_id":"r0","start_m":[0.,.08,-.04],
            "end_m":[0.,.08,.12],"state":deepcopy(ray),"length_m":.16,"cumulative_end_m":.16,"event_id":"e0001"}],
        "events":[{"id":"e0001","segment_id":"s0001","branch_id":"r0",
            "target":{"kind":"element","body_id":None,"face_id":None,"element_id":"D1"},
            "classification":"receiver_hit","position_m":[0.,.08,.12],"local_uv_m":[0.,0.],
            "incident_state":deepcopy(ray),"segment_length_m":.16,"cumulative_length_m":.16,
            "interface":None,"numerical_bounds":{"t_parameter_interval_m":enclosing([.16])[0],
                "position_intervals_m":enclosing([0.,.08,.12]),"local_uv_intervals_m":enclosing([0.,0.]),
                "incident_direction_intervals":enclosing([0.,0.,1.]),"outgoing_direction_intervals":[],
                "cumulative_length_interval_m":enclosing([.16])[0],"plane_residual_m":0.}}],
        "terminals":[{"branch_id":"r0","category":"detected","element_id":"D1","event_id":"e0001",
            "position_m":[0.,.08,.12],"state":deepcopy(ray),"cumulative_length_m":.16,"reason":"receiver_hit"}],
        "ledger":{"input_power":1.,"detected_power":1.,"stopped_power":0.,"escaped_power":0.,"unresolved_power":0.,
            "signed_residual":0.,"receiver_totals":[{"element_id":"D1","power_fraction":1.,"leaf_branch_ids":["r0"]}],
            "path_addition":protocol.PATH_ADDITION},
        "diagnostics":{"geometry_policy":"binary64_closed_body_outward_v1","polarization_policy":"outward_power_coherency_v1",
            "max_point_width_m":math.nextafter(.12,math.inf)-math.nextafter(.12,-math.inf),
            "max_direction_width":math.nextafter(1.,math.inf)-math.nextafter(1.,-math.inf),
            "max_frame_width":math.nextafter(1.,math.inf)-math.nextafter(1.,-math.inf),
            "max_coefficient_width":0.,"max_C_width":math.nextafter(.5,math.inf)-math.nextafter(.5,-math.inf),
            "max_local_power_residual":0.,"max_frame_residual":0.,"created_branches":1,"surface_events":1,"segments":1,
            "max_ancestry_interactions":1,"record_count":2}}


def wire(value=None):
    value=core_record() if value is None else value
    return json.loads(protocol.encode_trace_result(REQUEST_ID,protocol.scene_digest(value["scene"]),value))


def genuine_body_wire():
    from apps.virtual_bench import fresnel_routing_adapter as adapter
    return json.loads(adapter.trace_submission(adapter.validate_submission({"request_id":REQUEST_ID,"scene":body_scene()})))


def test_independent_wire_roundtrip_is_owned_and_closed():
    original=core_record()
    snapshot=deepcopy(original)
    result=wire(original)
    assert protocol.decode_trace_result(protocol.json_bytes(result),request_id=REQUEST_ID,scene=scene())==result
    assert original==snapshot
    assert result["ledger"]["detected_power"]==1.
    assert result["limits"]["response_bytes"]==393216


@pytest.mark.parametrize("change",[
    lambda p:p.update(extra=True),lambda p:p.update(protocol_version=True),
    lambda p:p.update(model_contract="w3_ideal_refractive_routing_v1"),
    lambda p:p.update(message_type="refractive_trace_result"),
    lambda p:p.update(request_id="00000000-0000-4000-8000-000000000001"),
    lambda p:p.update(scene_sha256="0"*64),
    lambda p:p["branches"][0]["initial_state"].update(medium_id="body:missing"),
    lambda p:p["segments"][0]["state"].update(refractive_index=1.5),
    lambda p:p["events"][0]["incident_state"].update(power_fraction=.5),
    lambda p:p["segments"][0]["state"]["C"].__setitem__(0,-1.),
    lambda p:p["segments"][0]["state"]["frame"].update(e2=[1.,0.,0.]),
    lambda p:p["segments"][0]["state"]["frame"].update(khat=[0.,0.,-1.]),
    lambda p:p["segments"][0]["state"]["numerical_bounds"].update(C_intervals=[[0.,0.]]*4),
    lambda p:p["segments"][0]["state"]["numerical_bounds"].update(frame_intervals=[[-1.,1.]]*9),
    lambda p:p["events"][0].update(classification="dielectric_split"),
    lambda p:p["events"][0]["target"].update(body_id="missing"),
    lambda p:p["events"][0].update(interface={}),
    lambda p:p["terminals"].clear(),lambda p:p["terminals"].append(deepcopy(p["terminals"][0])),
    lambda p:p["terminals"][0].update(category="stopped"),
    lambda p:p["terminals"][0].update(reason="distance_cap"),
    lambda p:p["ledger"].update(detected_power=.5),lambda p:p["ledger"].update(signed_residual=1e-16),
    lambda p:p["ledger"].update(path_addition="coherent"),
    lambda p:p["ledger"]["receiver_totals"][0].update(leaf_branch_ids=[]),
    lambda p:p["limits"].update(max_branches=63),lambda p:p["limits"].update(response_bytes=True),
    lambda p:p["diagnostics"].update(created_branches=2),
    lambda p:p["diagnostics"].update(max_frame_width=1e-7),
    lambda p:p["diagnostics"].update(max_C_width=0.),
    lambda p:p["events"][0]["numerical_bounds"].update(t_parameter_interval_m=[0.,.16]),
    lambda p:p["segments"][0].update(length_m=True),
])
def test_independent_closed_identity_graph_state_and_leaf_faults_reject(change):
    value=wire()
    change(value)
    with pytest.raises((ValueError,TypeError)):
        protocol.validate_trace_reply(value,request_id=REQUEST_ID)


def test_actual_finite_body_roundtrip_keeps_all_incomplete_power():
    value=genuine_body_wire()
    assert protocol.decode_trace_result(protocol.json_bytes(value))==value
    assert value["status"]=="incomplete" and value["ledger"]["unresolved_power"]>0
    first=value["events"][0]["interface"]
    assert [leg["kind"] for leg in first["legs"]]==["R","T"]
    assert math.isclose(first["power_fractions"]["R_incident"],.04,rel_tol=2e-12,abs_tol=0)


@pytest.mark.parametrize("defect",["normal","medium","rside","tside","critical","basis","coefficient","flux","power","missingchild","duplicatedleaf","exactzero","tir","halfspace"])
def test_genuine_interface_transport_faults_detect_without_recomputing_fresnel(defect):
    value=genuine_body_wire()
    event=value["events"][0]
    interface=event["interface"]
    if defect=="normal":interface["outward_normal"]=[0.,0.,1.]
    elif defect=="medium":interface["transmission_medium_id"]="exterior"
    elif defect=="rside":event["numerical_bounds"]["outgoing_side_intervals"][0]["side_interval"]=[-1.,-.5]
    elif defect=="tside":event["numerical_bounds"]["outgoing_side_intervals"][1]["side_interval"]=[.5,1.]
    elif defect=="critical":event["numerical_bounds"]["snell_discriminant_interval"]=[-1.,1.]
    elif defect=="basis":interface["incidence_basis"]["normal_policy"]="nominal_zero_is_proof"
    elif defect=="coefficient":interface["numerical_bounds"]["coefficient_intervals"][0]=[[99.,100.],[0.,0.]]
    elif defect=="flux":interface["coefficients"]["flux_factor"]=None
    elif defect=="power":interface["legs"][0]["power_fraction"]*=.5
    elif defect=="missingchild":value["branches"].pop(1)
    elif defect=="duplicatedleaf":value["terminals"].append(deepcopy(value["terminals"][0]))
    elif defect=="exactzero":interface["legs"][0]["disposition"]="exact_zero"
    elif defect=="tir":event["classification"]="total_internal_reflection"
    else:event["numerical_bounds"]["body_halfspace_intervals_m"][0]=[-1.,0.]
    with pytest.raises((ValueError,TypeError)):
        protocol.validate_trace_reply(value)


@pytest.mark.parametrize("data",[b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}',b'{"a":1e-999}',b'\xff'])
def test_strict_request_and_response_parsing_rejects_atomic_invalid_json(data):
    with pytest.raises((TypeError,ValueError)):protocol.strict_json_loads(data)
    with pytest.raises((TypeError,ValueError)):protocol.decode_trace_result(data)


def test_caps_and_flat_error_identity_are_exact():
    with pytest.raises(ValueError):protocol.strict_json_loads(b" "*(32768+1))
    with pytest.raises(ValueError):protocol.decode_trace_result(b" "*(393216+1))
    with pytest.raises(ValueError):protocol.error_reply(REQUEST_ID,"unknown","bad")
    with pytest.raises(TypeError):protocol.error_reply(REQUEST_ID,"invalid_scene",1)
    value=json.loads(protocol.error_reply(REQUEST_ID,"unsupported_polarization_numerics","x"*500,"a"*64))
    assert set(value)=={"protocol_version","message_type","request_id","model_contract","scene_sha256","code","message"}
    assert value["code"]=="unsupported_polarization_numerics" and len(value["message"])==300
    assert "events" not in value
