"""W3 empty-body exact public W2 projection, full limits and old exceptions."""
from copy import deepcopy
import math

import pytest

from ohlab.optics import geometric_routing, refractive_routing


def element(identity,kind,position,y=0.):
    return {"id":identity,"kind":kind,"pose":{"position_m":list(position),"rotation_xyz_rad":[0.,y,0.]},"aperture":{"kind":"disk","radius_m":.025}}


def inputs():
    values=[[],[element("D","receiver",(0.,.08,.2))],
            [element("M","mirror",(0.,.08,.2),-math.pi/4),element("D","receiver",(.2,.08,.2),-math.pi/2)],
            [element("S","ideal_splitter_50_50",(0.,.08,.2),-math.pi/4),element("DT","receiver",(0.,.08,.4)),element("DR","receiver",(.2,.08,.2),-math.pi/2)],
            [element("S1","ideal_splitter_50_50",(0.,.08,.1)),element("S2","ideal_splitter_50_50",(0.,.08,-.1))]]
    return [{"schema_version":1,"model_contract":geometric_routing.MODEL_CONTRACT,
             "source":{"id":"source","origin_m":[0.,.08,0.],"direction":[0.,0.,1.],"relative_weight":1.},"elements":x} for x in values]


def wrapper(old):
    return {**deepcopy(old),"model_contract":refractive_routing.MODEL_CONTRACT,"bodies":[],"exterior_medium":{"id":"exterior","refractive_index":2.}}


def project(result):
    data=result.to_dict()
    scene=deepcopy(data["scene"]);scene.pop("bodies");scene.pop("exterior_medium");scene["model_contract"]=geometric_routing.MODEL_CONTRACT
    limits=data["limits"]
    for key in ("max_bodies","max_body_faces","max_total_optical_faces"):limits.pop(key)
    limits["max_elements"]=limits.pop("max_legacy_elements");limits["max_hits"]=limits.pop("max_events")
    for item in data["branches"]:
        item.pop("initial_medium_id");item.pop("initial_refractive_index");item["parent_hit_id"]=item.pop("parent_event_id")
    for item in data["segments"]:
        item.pop("medium_id");item.pop("refractive_index");item["hit_id"]=item.pop("event_id")
    for item in data["events"]:
        item["element_id"]=item.pop("target")["element_id"]
        for key in ("classification","incident_medium_id","incident_refractive_index"):item.pop(key)
        for outgoing in item["outgoing"]:outgoing.pop("medium_id");outgoing.pop("refractive_index")
        for key in ("incident_direction_intervals","outgoing_direction_intervals","cumulative_length_interval_m"):item["numerical_bounds"].pop(key)
    for item in data["terminals"]:
        item.pop("medium_id");item.pop("refractive_index");item["hit_id"]=item.pop("event_id")
    return {"scene":scene,"surface_frames":data["legacy_surface_frames"],"limits":limits,"status":data["status"],
            "branches":data["branches"],"segments":data["segments"],"hits":data["events"],"terminals":data["terminals"],
            "ledger":data["ledger"],"diagnostics":data["diagnostics"]}


@pytest.mark.parametrize("old",inputs())
def test_empty_body_lossless_ten_key_projection_exactly_matches_public_W2(old):
    expected=geometric_routing.trace_routes(geometric_routing.validate_scene(old)).to_dict()
    actual=refractive_routing.trace_routes(refractive_routing.validate_scene(wrapper(old)))
    assert project(actual)==expected
    assert actual.limits["max_branches"]==63 and actual.limits["max_records"]==256
    assert actual.limits["max_events"]==128 and actual.limits["max_segments"]==256


def test_empty_body_delegates_once_and_never_applies_new_width_gate(monkeypatch):
    original=geometric_routing.trace_routes; calls=[]
    def counted(scene):calls.append(scene);return original(scene)
    monkeypatch.setattr(refractive_routing,"trace_geometric_routes",counted)
    monkeypatch.setattr(refractive_routing,"_admit_vector",lambda *_a,**_kw:pytest.fail("body width gate ran"))
    result=refractive_routing.trace_routes(refractive_routing.validate_scene(wrapper(inputs()[0])))
    assert len(calls)==1 and result.diagnostics["predicate_policy"]=="binary64_outward_intervals_v1"


def test_existing_w2_schema_still_rejects_w3_and_old_error_text_is_preserved():
    old=inputs()[1];old["source"]["origin_m"][0]=.025
    with pytest.raises(geometric_routing.NumericalAmbiguityError) as expected:
        geometric_routing.trace_routes(geometric_routing.validate_scene(old))
    with pytest.raises(type(expected.value)) as actual:
        refractive_routing.trace_routes(refractive_routing.validate_scene(wrapper(old)))
    assert str(actual.value)==str(expected.value)
    with pytest.raises(ValueError):geometric_routing.validate_scene(wrapper(inputs()[0]))
