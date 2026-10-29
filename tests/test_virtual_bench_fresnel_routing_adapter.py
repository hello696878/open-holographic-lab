"""W4 public-call ownership and error separation; optics references are separate."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import json

import pytest

from apps.virtual_bench import fresnel_routing_adapter as adapter
from apps.virtual_bench import fresnel_routing_protocol as protocol
from test_virtual_bench_fresnel_routing_protocol import REQUEST_ID,scene,body_scene


def envelope(*,trace=False):
    value={"request_id":REQUEST_ID,"scene":scene()}
    if trace:value["scene_sha256"]=protocol.scene_digest(adapter.validate_fresnel_scene(value["scene"]).to_dict())
    return value


def test_validation_is_owned_immutable_zero_trace_and_no_added_power():
    value=envelope()
    before=deepcopy(value)
    submission=adapter.validate_submission(value)
    reply=protocol.decode_validation_reply(adapter.validation_reply(submission),request_id=REQUEST_ID,scene=value["scene"])
    assert value==before and reply["scene_sha256"]==submission.scene_sha256
    value["scene"]["source"]["polarization"]="linear_e1"
    assert submission.scene.to_dict()["source"]["polarization"]=="unpolarized"
    reply["scene"]["source"]["origin_m"][0]=.3
    assert submission.scene.to_dict()["source"]["origin_m"][0]==0.
    with pytest.raises(FrozenInstanceError):submission.request_id="changed"


def test_validate_never_traces_and_trace_delegates_once_then_encodes(monkeypatch):
    calls=[]
    original=adapter.trace_fresnel_scene
    monkeypatch.setattr(adapter,"trace_fresnel_scene",lambda *_:pytest.fail("validation traced"))
    validation=adapter.validate_submission(envelope())
    protocol.decode_validation_reply(adapter.validation_reply(validation))
    def spy(scene):
        calls.append(scene)
        return original(scene)
    monkeypatch.setattr(adapter,"trace_fresnel_scene",spy)
    value=envelope(trace=True)
    before=deepcopy(value)
    submission=adapter.validate_submission(value,trace=True)
    reply=protocol.decode_trace_result(adapter.trace_submission(submission),request_id=REQUEST_ID,scene_sha256=submission.scene_sha256,scene=submission.scene.to_dict())
    assert value==before and calls==[submission.scene]
    assert reply["status"]=="complete" and reply["ledger"]["detected_power"]==1.


@pytest.mark.parametrize("change",[
    lambda p:p.update(extra=True),lambda p:p.pop("scene"),lambda p:p.update(request_id=True),
    lambda p:p["scene"].update(extra=1),lambda p:p["scene"]["source"].update(direction=[0.,0.,2.]),
    lambda p:p["scene"]["source"].update(polarization="arbitrary_matrix"),
    lambda p:p["scene"]["source"].update(relative_weight=.5),
    lambda p:p["scene"]["elements"][0].update(kind="mirror"),
    lambda p:p["scene"]["elements"][0]["aperture"].update(radius_m=0),
    lambda p:p["scene"]["elements"].extend([deepcopy(p["scene"]["elements"][0])]*4),
    lambda p:p["scene"].update(path_addition="coherent"),
])
def test_invalid_submission_does_not_reach_runner(monkeypatch,change):
    monkeypatch.setattr(adapter,"trace_fresnel_scene",lambda *_:pytest.fail("invalid request traced"))
    value=envelope()
    change(value)
    with pytest.raises((ValueError,TypeError)):adapter.validate_submission(value)


def test_trace_requires_exact_digest_and_metadata_envelope_stays_closed():
    value=envelope(trace=True)
    with pytest.raises(ValueError):adapter.validate_submission(value)
    value["scene_sha256"]="0"*64
    with pytest.raises(ValueError,match="scene_sha256"):adapter.validate_submission(value,trace=True)
    with pytest.raises(ValueError):adapter.validate_submission(envelope(),trace=True)
    value=envelope(trace=True)
    value["scene"]["source"]["polarization"]="linear_e2"
    with pytest.raises(ValueError,match="scene_sha256"):adapter.validate_submission(value,trace=True)


@pytest.mark.parametrize("name,code",[("NumericalAmbiguityError","numerical_ambiguity"),
    ("UnsupportedNumericalInputError","unsupported_numerical_input"),
    ("MediumStateAmbiguityError","medium_state_ambiguity"),
    ("UnsupportedPolarizationNumericsError","unsupported_polarization_numerics")])
@pytest.mark.parametrize("phase",["validate","trace"])
def test_declared_failures_keep_exact_classification(monkeypatch,name,code,phase):
    submission=adapter.validate_submission(envelope())
    def fail(_):raise getattr(adapter,name)("controlled scientific admission failure")
    monkeypatch.setattr(adapter,"validate_fresnel_scene" if phase=="validate" else "trace_fresnel_scene",fail)
    with pytest.raises(adapter.FresnelNumericalError) as error:
        adapter.validate_submission(envelope()) if phase=="validate" else adapter.trace_submission(submission)
    assert error.value.code==code


def test_representation_failure_remains_distinct_from_science(monkeypatch):
    submission=adapter.validate_submission(envelope())
    def fail(*args):raise ValueError("controlled encoding failure")
    monkeypatch.setattr(adapter,"encode_trace_result",fail)
    with pytest.raises(ValueError,match="encoding"):adapter.trace_submission(submission)
    with pytest.raises(TypeError):adapter.trace_submission(object())
    with pytest.raises(TypeError):adapter.validation_reply(object())
    with pytest.raises(TypeError):adapter.validate_submission(envelope(),trace=1)
    with pytest.raises(ValueError):adapter.FresnelNumericalError("bad",code="hidden")


def test_actual_body_retains_source_and_first_branch_identity():
    value={"request_id":REQUEST_ID,"scene":body_scene()}
    before=deepcopy(value)
    submission=adapter.validate_submission(value)
    reply=json.loads(adapter.trace_submission(submission))
    assert value==before and reply["scene"]==submission.scene.to_dict()
    assert [branch["id"] for branch in reply["branches"][:3]]==["r0","r0.R","r0.T"]
