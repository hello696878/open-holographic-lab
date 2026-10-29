"""Actual finite branching, medium graph, leaf accounting and frozen caps."""
from copy import deepcopy
import math

import pytest

from ohlab.optics import fresnel_routing as routing
from ohlab.optics.fresnel_routing import FresnelScene,trace_fresnel_scene
from scripts.validate_w4_fresnel_routing import fixtures


@pytest.mark.parametrize("name",list(fixtures()))
def test_fixed_actual_routes_conserve_all_leaves_and_do_not_mutate_inputs(name):
    raw=fixtures()[name];before=deepcopy(raw)
    scene=FresnelScene.from_dict(raw);result=trace_fresnel_scene(scene);wire=result.to_dict()
    assert raw==before and scene.to_dict()==before
    assert wire["status"]==("incomplete" if wire["ledger"]["unresolved_power"]>0 else "complete")
    leaves=wire["terminals"];leaf_ids=[x["branch_id"] for x in leaves]
    assert len(leaf_ids)==len(set(leaf_ids))<=16
    assert all(x["state"]["power_fraction"]>0 for x in leaves)
    assert math.fsum(x["state"]["power_fraction"] for x in leaves)==pytest.approx(1.,abs=2e-13,rel=2e-12)
    assert len(wire["branches"])<=31 and len(wire["events"])<=32 and len(wire["segments"])<=64
    assert len(wire["events"])+len(wire["segments"])<=96
    branches={x["id"]:x for x in wire["branches"]}
    for branch in branches.values():
        if branch["id"]=="r0":assert branch["parent_id"] is None
        else:assert branch["parent_id"] in branches and branch["id"].rsplit(".",1)[0]==branch["parent_id"]
        assert branch["outcome"] in ("split","continued","detected","stopped","escaped","resource_unresolved")
    for event in wire["events"]:
        if event["interface"] is None:continue
        assert event["numerical_bounds"]["incident_side_interval"][1]<0
        for leg,side in zip(event["interface"]["legs"],event["numerical_bounds"]["outgoing_side_intervals"]):
            if leg["state"] is not None:
                assert leg["power_fraction"]==sum(leg["state"]["C"][:2])
                assert side["side_interval"][0]>0 if leg["kind"]=="R" else side["side_interval"][1]<0
                if leg["disposition"]=="allocated":
                    assert branches[leg["branch_id"]]["initial_state"]==leg["state"]
    original_C=wire["branches"][0]["initial_state"]["C"][:]
    wire["branches"][0]["initial_state"]["C"][0]=100
    assert result.to_dict()["branches"][0]["initial_state"]["C"]==original_C


def test_normal_actual_finite_slab_first_leaf_later_leaves_and_infinite_reference_remain_distinct():
    wire=trace_fresnel_scene(FresnelScene.from_dict(fixtures()["normal_slab"])).to_dict()
    first=wire["events"][0]["interface"]
    assert first["power_fractions"]==pytest.approx({"R_s":.04,"R_p":.04,"T_s":.96,"T_p":.96,"R_incident":.04,"T_incident":.96},abs=2e-14,rel=2e-12)
    direct=next(x for x in wire["terminals"] if x["branch_id"]=="r0.T.T")
    assert direct["element_id"]=="D1" and direct["state"]["power_fraction"]==pytest.approx(.9216,abs=2e-13,rel=2e-12)
    assert direct["position_m"]==pytest.approx([0.,.08,.12],abs=5e-12,rel=2e-12)
    d1=wire["ledger"]["receiver_totals"][0]
    assert len(d1["leaf_branch_ids"])==3 and d1["power_fraction"]>direct["state"]["power_fraction"]
    infinite=.96**2/(1-.04**2)
    assert infinite==pytest.approx(12/13,abs=2e-14,rel=2e-12)
    assert d1["power_fraction"]<infinite
    assert wire["ledger"]["unresolved_power"]==pytest.approx(3.93216e-9,abs=0.,rel=2e-12)
    assert wire["status"]=="incomplete"


def test_equal_index_zero_leg_does_not_allocate_or_erase_identity_state():
    wire=trace_fresnel_scene(FresnelScene.from_dict(fixtures()["equal_index"])).to_dict()
    assert len(wire["branches"])==3 and wire["status"]=="complete"
    for event in wire["events"]:
        if event["interface"] is None:continue
        interface=event["interface"];r,t=interface["legs"]
        assert r["disposition"]=="exact_zero" and r["state"] is None and r["branch_id"] is None
        assert interface["incidence_basis"] is None
        assert t["state"]["C"]==event["incident_state"]["C"]
        assert t["state"]["frame"]==event["incident_state"]["frame"]
        assert t["state"]["numerical_bounds"]["C_intervals"]==event["incident_state"]["numerical_bounds"]["C_intervals"]


def test_one_slot_short_allocates_neither_positive_child_and_accounts_queue(monkeypatch):
    monkeypatch.setattr(routing,"MAX_BRANCHES",2)
    wire=trace_fresnel_scene(FresnelScene.from_dict(fixtures()["normal_slab"])).to_dict()
    assert len(wire["branches"])==1
    assert wire["ledger"]["unresolved_power"]==1. and wire["terminals"][0]["reason"]=="branch_cap"
    assert [x["disposition"] for x in wire["events"][0]["interface"]["legs"]]==["resource_unallocated"]*2
    assert all(x["branch_id"] is None for x in wire["events"][0]["interface"]["legs"])


def test_receiver_on_last_allowed_interaction_wins(monkeypatch):
    monkeypatch.setattr(routing,"MAX_INTERACTIONS",3)
    wire=trace_fresnel_scene(FresnelScene.from_dict(fixtures()["normal_slab"])).to_dict()
    leaf=next(x for x in wire["terminals"] if x["branch_id"]=="r0.T.T")
    assert leaf["category"]=="detected" and leaf["reason"]=="receiver_hit"
    assert leaf["state"]["power_fraction"]==pytest.approx(.9216,abs=2e-13,rel=2e-12)


def test_terminal_on_global_last_event_wins_and_remaining_queue_is_accounted(monkeypatch):
    monkeypatch.setattr(routing,"MAX_EVENTS",2)
    wire=trace_fresnel_scene(FresnelScene.from_dict(fixtures()["normal_slab"])).to_dict()
    assert len(wire["events"])==2
    assert wire["events"][-1]["classification"]=="receiver_hit"
    assert wire["ledger"]["detected_power"]==pytest.approx(.04,abs=2e-14,rel=2e-12)
    assert wire["ledger"]["unresolved_power"]==pytest.approx(.96,abs=2e-14,rel=2e-12)


@pytest.mark.parametrize("limit,value,reason",[("MAX_SEGMENTS",1,"segment_cap"),("MAX_RECORDS",1,"record_cap")])
def test_atomic_record_budget_cannot_publish_orphan_segments_or_lose_power(monkeypatch,limit,value,reason):
    monkeypatch.setattr(routing,limit,value)
    wire=trace_fresnel_scene(FresnelScene.from_dict(fixtures()["normal_slab"])).to_dict()
    assert wire["ledger"]["unresolved_power"]==pytest.approx(1.)
    assert all(x["reason"]==reason for x in wire["terminals"])
    if limit=="MAX_RECORDS":assert not wire["segments"] and not wire["events"]


def test_lossless_interface_is_not_stop_absorption_and_stop_is_actual_finite_hit():
    wire=trace_fresnel_scene(FresnelScene.from_dict(fixtures()["beam_stop"])).to_dict()
    assert wire["ledger"]["stopped_power"]>0
    for leaf in wire["terminals"]:
        if leaf["category"]=="stopped":
            assert leaf["element_id"]=="D1" and leaf["reason"]=="stop_hit"


def test_distance_endpoint_preserves_positive_power_at_actual_bounded_location(monkeypatch):
    monkeypatch.setattr(routing,"MAX_DISTANCE_M",.01)
    wire=trace_fresnel_scene(FresnelScene.from_dict(fixtures()["normal_slab"])).to_dict()
    assert wire["status"]=="incomplete" and not wire["events"]
    assert wire["ledger"]["unresolved_power"]==1.
    assert wire["terminals"][0]["reason"]=="distance_cap"
    assert wire["terminals"][0]["position_m"]==pytest.approx([0.,.08,-.03],abs=5e-12,rel=2e-12)


@pytest.mark.parametrize("change",["model","path","source_direction","source_origin","extra_source","extra_scene","mirror","five_targets"])
def test_closed_w4_inputs_fail_without_implicitly_upgrading_old_scenes(change):
    raw=fixtures()["normal_slab"]
    if change=="model":raw["model_contract"]="w3_ideal_refractive_routing_v1"
    if change=="path":raw["path_addition"]="coherent"
    if change=="source_direction":raw["source"]["direction"]=[.5,0.,math.sqrt(.75)]
    if change=="source_origin":raw["source"]["origin_m"]=[.001,.08,-.04]
    if change=="extra_source":raw["source"]["relative_weight"]=1.
    if change=="extra_scene":raw["wavelength_m"]=633e-9
    if change=="mirror":raw["elements"][0]["kind"]="mirror"
    if change=="five_targets":raw["elements"]*=3
    with pytest.raises((TypeError,ValueError)):FresnelScene.from_dict(raw)
