"""W3 public closed-body validation, per-event medium and bounded leaf ledger."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import math

import numpy as np
import pytest

from ohlab.optics import refractive_routing as routing
from scripts.validate_w3_refractive_routing import fixtures


def run(value):
    return routing.trace_routes(routing.RefractiveScene.from_dict(value))


def supported_run(value):
    try:
        return run(value)
    except (routing.NumericalAmbiguityError,routing.UnsupportedNumericalInputError,routing.MediumStateAmbiguityError) as exc:
        pytest.fail(f"declared supported resource fixture was rejected before its ledger assertions: {exc}")


def body_events(result):
    return [x for x in result.events if x["target"]["kind"]=="body_face"]


@pytest.mark.parametrize("name",["A_slab","B_prism","B_index1.3","B_yaw10","C_TIR"])
def test_five_frozen_fixed_finite_receivers_are_detected(name):
    result=run(fixtures()[name])
    assert result.status=="complete"
    assert result.ledger["detected_weight"]==1.
    assert result.terminals[0]["element_id"]=="D1"
    assert result.events[-1]["classification"]=="receiver_hit"
    assert result.events[-1]["local_uv_m"][0]**2+result.events[-1]["local_uv_m"][1]**2<.01**2


def test_entry_internal_TIR_exit_has_authoritative_medium_on_every_segment():
    result=run(fixtures()["C_TIR"])
    assert [x["classification"] for x in result.events]==["enter_refraction","total_internal_reflection","exit_refraction","receiver_hit"]
    assert [x["medium_id"] for x in result.segments]==["exterior","body:B1","body:B1","exterior"]
    tir=result.events[1]
    assert tir["incident_medium_id"]==tir["outgoing"][0]["medium_id"]=="body:B1"
    assert tir["numerical_bounds"]["snell_discriminant_interval"][1]<0
    assert tir["outgoing"][0]["direction"]==pytest.approx((-1.,0.,0.),rel=2e-12,abs=2e-12)
    assert tir["outgoing_angle_rad"]==pytest.approx(math.pi/4,rel=2e-12,abs=2e-12)
    assert "transmitted_angle_rad" not in tir and "critical_angle_rad" not in tir


def test_exterior_high_index_TIR_does_not_enter_body():
    result=run(fixtures()["exterior_TIR"])
    assert [x["classification"] for x in result.events]==["total_internal_reflection"]
    assert all(x["medium_id"]=="exterior" for x in result.segments)
    assert result.events[0]["outgoing"][0]["medium_id"]=="exterior"


def test_equal_indices_keep_exact_direction_but_still_change_medium_ids():
    raw=fixtures()["equal_index"]; result=run(raw)
    for event in result.events:
        assert event["outgoing"][0]["direction"]==tuple(raw["source"]["direction"])
    assert [x["medium_id"] for x in result.segments]==["exterior","body:B1","exterior"]


@pytest.mark.parametrize("name,expected",[("D_multiple_returns",["z_min","hypotenuse","x_min","hypotenuse","x_min"]),
                                          ("block_side",["z_min","x_max","z_max"]),
                                          ("triangle_end_hit",["z_min","y_max","hypotenuse"])])
def test_all_finite_side_end_faces_and_legitimate_later_returns_participate(name,expected):
    result=run(fixtures()[name])
    assert [x["target"]["face_id"] for x in body_events(result)]==expected
    assert result.ledger["escaped_weight"]==1.


@pytest.mark.parametrize("name",["finite_plane_miss","triangle_end_miss"])
def test_support_plane_crossing_outside_closed_body_never_switches_medium(name):
    result=run(fixtures()[name])
    assert not result.events
    assert result.segments[0]["medium_id"]=="exterior"
    assert result.terminals[0]["category"]=="escaped"


@pytest.mark.parametrize("origin",[(.08,.08,-.04),(.08,.1,-.04)])
def test_edge_vertex_never_choose_a_face_by_order(origin):
    raw=fixtures()["B_prism"];raw["elements"]=[];raw["source"]["origin_m"]=list(origin)
    with pytest.raises(routing.NumericalAmbiguityError): run(raw)


@pytest.mark.parametrize("path,value,error",[
    (("schema_version",),True,TypeError),(("model_contract",),"w2_ideal_geometric_routing_v1",ValueError),
    (("source","direction"),[0.,0.,2.],ValueError),(("source","direction"),[0.,0.],ValueError),
    (("source","direction"),[False,0.,1.],TypeError),(("exterior_medium","refractive_index"),True,TypeError),
    (("exterior_medium","refractive_index"),.99,ValueError),(("exterior_medium","refractive_index"),2.51,ValueError),
    (("exterior_medium","refractive_index"),float("nan"),ValueError),
    (("bodies",0,"shape","leg_x_m"),0.,ValueError),(("bodies",0,"shape","height_y_m"),.251,ValueError),
    (("bodies",0,"pose","rotation_xyz_rad"),[0.,4.,0.],ValueError),
    (("bodies",0,"interior_medium","id"),"body:wrong",ValueError),
    (("bodies",0,"id"),"D1",ValueError),(("bodies",0,"id"),"B"*33,ValueError),
])
def test_closed_schema_and_domains(path,value,error):
    raw=fixtures()["B_prism"];node=raw
    for key in path[:-1]:node=node[key]
    node[path[-1]]=value
    with pytest.raises(error):routing.validate_scene(raw)


@pytest.mark.parametrize("path",[(),("source",),("exterior_medium",),("bodies",0),("bodies",0,"shape"),("bodies",0,"pose")])
def test_unknown_keys_are_rejected_without_expanding_w2_schema(path):
    raw=fixtures()["B_prism"];node=raw
    for key in path:node=node[key]
    node["unknown"]=0
    with pytest.raises(ValueError):routing.validate_scene(raw)


def test_source_boundary_inside_embedded_and_touching_aperture_rejected():
    for origin in ((.02,.08,.02),(.02,.08,0.)):
        raw=fixtures()["B_prism"];raw["source"]["origin_m"]=list(origin)
        with pytest.raises(ValueError,match="outside"):routing.validate_scene(raw)
    for position in ((.02,.08,.02),(.02,.08,-.01)):
        raw=fixtures()["B_prism"];raw["elements"][0]["pose"]["position_m"]=list(position)
        with pytest.raises(ValueError,match="separated"):routing.validate_scene(raw)


def test_body_domain_and_face_count_are_admitted_before_any_trace(monkeypatch):
    raw=fixtures()["B_prism"];raw["bodies"][0]["pose"]["position_m"]=[0.,.08,1.]
    with pytest.raises(ValueError,match="sphere"):routing.validate_scene(raw)
    raw=fixtures()["B_prism"]
    raw["elements"]=[{**deepcopy(raw["elements"][0]),"id":f"D{i}"} for i in range(12)]
    with pytest.raises(ValueError,match="maximum16"):routing.validate_scene(raw)
    monkeypatch.setattr(routing,"trace_routes",lambda _:pytest.fail("validation traced"))
    assert len(routing.validate_scene(fixtures()["C_TIR"]).body_faces)==5


def test_inputs_outputs_nested_records_and_floating_environment_are_preserved():
    raw=fixtures()["C_TIR"];snapshot=deepcopy(raw); scene=routing.validate_scene(raw)
    raw["bodies"][0]["shape"]["leg_x_m"]=.2
    assert scene.to_dict()==snapshot
    with np.errstate(all="raise"):
        before=np.geterr().copy();result=routing.trace_routes(scene);assert np.geterr()==before
        invalid=deepcopy(snapshot);invalid["source"]["origin_m"]=[.08,.08,-.04];invalid["elements"]=[]
        with pytest.raises(routing.NumericalAmbiguityError):run(invalid)
        assert np.geterr()==before
    exported=result.to_dict();exported["events"][0]["outgoing"][0]["direction"][0]=99.
    assert result.events[0]["outgoing"][0]["direction"][0]!=99.
    with pytest.raises(FrozenInstanceError):scene.media=()


def test_last_admitted_interaction_keeps_computed_outgoing_medium(monkeypatch):
    monkeypatch.setattr(routing,"MAX_INTERACTIONS",1)
    result=run(fixtures()["B_prism"])
    assert result.status=="incomplete"
    assert result.events[0]["classification"]=="enter_refraction"
    assert result.events[0]["outgoing"][0]["medium_id"]=="body:B1"
    assert result.terminals[0]["medium_id"]=="body:B1"
    assert result.terminals[0]["reason"]=="interaction_cap"
    assert result.ledger["truncated_weight"]==1.


def test_record_reservation_failure_terminates_at_known_origin_without_fake_hit(monkeypatch):
    monkeypatch.setattr(routing,"MAX_RECORDS",1)
    result=run(fixtures()["B_prism"])
    assert not result.events and not result.segments
    assert result.terminals[0]["position_m"]==tuple(fixtures()["B_prism"]["source"]["origin_m"])
    assert result.terminals[0]["medium_id"]=="exterior"
    assert result.status=="incomplete" and result.ledger["truncated_weight"]==1.


def test_receiver_wins_on_last_interaction(monkeypatch):
    monkeypatch.setattr(routing,"MAX_INTERACTIONS",3)
    result=run(fixtures()["B_prism"])
    assert result.status=="complete" and result.ledger["detected_weight"]==1.


def test_face_order_is_not_a_geometrical_tie_breaker(monkeypatch):
    original=routing.nearest_finite_hit
    monkeypatch.setattr(routing,"nearest_finite_hit",lambda ray,faces,upper:original(ray,tuple(reversed(faces)),upper))
    result=run(fixtures()["C_TIR"])
    assert [x["target"]["face_id"] for x in body_events(result)]==["z_min","hypotenuse","x_min"]
    ambiguous=fixtures()["B_prism"];ambiguous["elements"]=[];ambiguous["source"]["origin_m"]=[.08,.08,-.04]
    with pytest.raises(routing.NumericalAmbiguityError):run(ambiguous)


def splitter_cavity():
    raw=fixtures()["B_prism"]
    raw["source"].update(origin_m=[0.,.08,0.],direction=[0.,0.,1.])
    raw["bodies"][0]["pose"]["position_m"]=[.4,.08,0.]
    raw["elements"]=[{"id":identity,"kind":"ideal_splitter_50_50","pose":{"position_m":[0.,.08,z],"rotation_xyz_rad":[0.,0.,0.]},
                      "aperture":{"kind":"disk","radius_m":.025}} for identity,z in (("S1",.1),("S2",-.1))]
    return raw


def test_actual_body_branch_cap31_retains_all_queued_leaf_weights():
    result=supported_run(splitter_cavity())
    assert len(result.branches)==31
    assert result.status=="incomplete"
    assert any(x["reason"]=="branch_cap" for x in result.terminals)
    assert len({x["branch_id"] for x in result.terminals})==len(result.terminals)
    assert math.fsum(x["relative_weight"] for x in result.terminals)==1.
    assert result.ledger["signed_residual"]==0.
    assert all(x["medium_id"]=="exterior" for x in result.terminals)
    split=[x for x in result.events if x["classification"]=="ideal_split"]
    assert all(len(x["outgoing"]) in (0,2) for x in split)
    assert split[-1]["outgoing"]==()


@pytest.mark.parametrize("record_cap",[2,7])
def test_global_record_cap_keeps_queued_weights_and_atomic_event_records(monkeypatch,record_cap):
    monkeypatch.setattr(routing,"MAX_RECORDS",record_cap)
    result=supported_run(splitter_cavity())
    assert len(result.segments)+len(result.events)<=record_cap
    assert result.status=="incomplete"
    assert result.ledger["signed_residual"]==0.
    assert math.fsum(x["relative_weight"] for x in result.terminals)==1.
    assert len({x["branch_id"] for x in result.terminals})==len(result.terminals)
    assert all(x["segment_id"] in {s["id"] for s in result.segments} for x in result.events)
    if record_cap==2:
        assert [x["branch_id"] for x in result.terminals]==["r0.T","r0.R"]
        assert [x["relative_weight"] for x in result.terminals]==[.5,.5]
        assert all(x["reason"]=="record_cap" for x in result.terminals)


def test_immediate_child_interaction_cap_keeps_both_split_weights(monkeypatch):
    monkeypatch.setattr(routing,"MAX_INTERACTIONS",1)
    result=run(splitter_cavity())
    assert [x["branch_id"] for x in result.terminals]==["r0.T","r0.R"]
    assert [x["relative_weight"] for x in result.terminals]==[.5,.5]
    assert all(x["reason"]=="interaction_cap" for x in result.terminals)
    assert result.events[0]["outgoing"][0]["branch_id"]=="r0.T"


def test_actual_32nd_mirror_event_is_processed_before_continuation_truncation():
    raw=splitter_cavity()
    for element in raw["elements"]:element["kind"]="mirror"
    result=run(raw)
    assert len(result.events)==32 and len(result.segments)==32
    assert result.events[-1]["outgoing"][0]["direction"]==(0.,0.,1.)
    assert result.terminals[0]["reason"]=="interaction_cap"
    assert result.terminals[0]["position_m"]==result.events[-1]["position_m"]
    assert result.ledger["truncated_weight"]==1. and result.status=="incomplete"
