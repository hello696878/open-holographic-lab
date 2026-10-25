"""W3 adapter ownership/public delegation; scientific references live separately."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import json

import pytest

from apps.virtual_bench import refractive_routing_adapter as adapter
from apps.virtual_bench import refractive_routing_protocol as protocol
from test_virtual_bench_refractive_routing_protocol import REQUEST_ID, scene


def envelope(*, trace=False):
    value = {"request_id": REQUEST_ID, "scene": scene()}
    if trace:
        value["scene_sha256"] = protocol.scene_digest(adapter.validate_scene(value["scene"]).to_dict())
    return value


def test_pure_validation_preserves_original_and_runs_no_trace(monkeypatch):
    payload = envelope()
    original = deepcopy(payload)
    monkeypatch.setattr(adapter, "trace_routes", lambda *_: pytest.fail("validation traced"))
    submission = adapter.validate_submission(payload)
    reply = json.loads(adapter.validation_reply(submission))
    assert payload == original and reply["request_id"] == REQUEST_ID
    assert reply["scene"] == submission.scene.to_dict()
    assert reply["scene_sha256"] == protocol.scene_digest(reply["scene"])
    assert len(reply["legacy_surface_frames"]) == 1
    payload["scene"]["source"]["origin_m"][0] = .25
    assert submission.scene.to_dict()["source"]["origin_m"][0] == 0
    reply["scene"]["source"]["origin_m"][0] = .5
    assert submission.scene.to_dict()["source"]["origin_m"][0] == 0
    with pytest.raises(FrozenInstanceError):
        submission.request_id = "changed"


def test_genuine_trace_calls_public_runner_exactly_once_and_captures_identity(monkeypatch):
    calls = []
    original = adapter.trace_routes
    def spy(*values):
        calls.append(values[0])
        return original(*values)
    monkeypatch.setattr(adapter, "trace_routes", spy)
    payload = envelope(trace=True)
    before = deepcopy(payload)
    submission = adapter.validate_submission(payload, trace=True)
    body = adapter.trace_submission(submission)
    reply = protocol.decode_trace_result(body, request_id=submission.request_id,
            scene=submission.scene.to_dict(), scene_sha256=submission.scene_sha256)
    assert len(calls) == 1 and calls[0] is submission.scene
    assert payload == before and reply["status"] == "complete"
    assert reply["terminals"][0]["category"] == "detected"
    assert reply["terminals"][0]["relative_weight"] == 1
    assert reply["ledger"]["signed_residual"] == 0


def test_genuine_body_free_adapter_projection_equals_the_public_w2_result():
    from ohlab.optics.geometric_routing import validate_scene, trace_routes
    from apps.virtual_bench import geometric_routing_protocol as w2
    submission = adapter.validate_submission(envelope(trace=True), trace=True)
    reply = protocol.decode_trace_result(adapter.trace_submission(submission))
    original = submission.scene.to_dict()
    old_scene = {"schema_version": original["schema_version"], "model_contract": w2.MODEL_CONTRACT,
                 "source": original["source"], "elements": original["elements"]}
    assert protocol.project_w2_result(reply) == trace_routes(validate_scene(old_scene)).to_dict()
    assert reply["model_contract"] == protocol.MODEL_CONTRACT


@pytest.mark.parametrize("change", [
    lambda p: p.update(extra=True), lambda p: p.pop("scene"),
    lambda p: p.update(request_id=True), lambda p: p["scene"].update(extra=1),
    lambda p: p["scene"]["source"].update(direction=[0.,0.,0.]),
    lambda p: p["scene"]["source"].update(direction=[0.,0.,2.]),
    lambda p: p["scene"]["elements"][0]["pose"].update(rotation_xyz_rad=[0.,4.,0.]),
    lambda p: p["scene"]["elements"][0]["aperture"].update(radius_m=0),
    lambda p: p["scene"]["elements"].extend([deepcopy(p["scene"]["elements"][0])]*16),
    lambda p: p["scene"]["source"].update(relative_weight=.5),
])
def test_invalid_complete_scene_never_enters_public_trace(monkeypatch, change):
    monkeypatch.setattr(adapter, "trace_routes", lambda *_: pytest.fail("invalid request traced"))
    value = envelope()
    change(value)
    with pytest.raises((TypeError, ValueError)):
        adapter.validate_submission(value)


def test_trace_requires_current_opaque_digest_and_validation_rejects_trace_keys():
    value = envelope(trace=True)
    with pytest.raises(ValueError):
        adapter.validate_submission(value)
    value["scene_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="scene_sha256"):
        adapter.validate_submission(value, trace=True)
    with pytest.raises(ValueError):
        adapter.validate_submission(envelope(), trace=True)
    value = envelope(trace=True)
    value["scene"]["elements"][0]["pose"]["position_m"][2] = .3
    with pytest.raises(ValueError, match="scene_sha256"):
        adapter.validate_submission(value, trace=True)


@pytest.mark.parametrize("exception,code", [
    ("NumericalAmbiguityError", "numerical_ambiguity"),
    ("UnsupportedNumericalInputError", "unsupported_numerical_input"),
    ("MediumStateAmbiguityError", "medium_state_ambiguity"),
])
def test_supported_scientific_failures_are_distinct_422_types(monkeypatch, exception, code):
    submission = adapter.validate_submission(envelope(trace=True), trace=True)
    kind = getattr(adapter, exception)
    calls = []
    def fail(_):
        calls.append(1)
        raise kind("controlled declared numerical boundary")
    monkeypatch.setattr(adapter, "trace_routes", fail)
    with pytest.raises(adapter.RefractiveNumericalError) as caught:
        adapter.trace_submission(submission)
    assert caught.value.code == code and len(calls) == 1


def test_encoder_failure_is_not_reclassified_as_optical_miss_or_numerical_success(monkeypatch):
    submission = adapter.validate_submission(envelope(trace=True), trace=True)
    def fail(*_):
        raise ValueError("controlled complete encoding failure")
    monkeypatch.setattr(adapter, "encode_trace_result", fail)
    with pytest.raises(ValueError, match="encoding") as caught:
        adapter.trace_submission(submission)
    assert not isinstance(caught.value, adapter.NumericalError)


def test_input_types_fail_passively_without_replacement_or_queue():
    for value in (None, [], "bad"):
        with pytest.raises((TypeError, ValueError)):
            adapter.validate_submission(value)
    with pytest.raises(TypeError):
        adapter.trace_submission(object())
    with pytest.raises(TypeError):
        adapter.validation_reply(object())
    with pytest.raises(TypeError):
        adapter.validate_submission(envelope(), trace=1)
    with pytest.raises(ValueError):
        adapter.RefractiveNumericalError("bad", code="hidden")


def test_canonical_digest_identity_retains_negative_zero_source_value():
    value = envelope()
    value["scene"]["source"]["origin_m"][0] = -0.0
    submission = adapter.validate_submission(value)
    reply = json.loads(adapter.validation_reply(submission))
    assert protocol.scene_digest(reply["scene"]) == submission.scene_sha256
    assert json.dumps(reply["scene"]["source"]["origin_m"]).startswith("[-0.0")


@pytest.mark.parametrize("name,code",[("NumericalAmbiguityError","numerical_ambiguity"),
                                     ("UnsupportedNumericalInputError","unsupported_numerical_input"),
                                     ("MediumStateAmbiguityError","medium_state_ambiguity")])
def test_pure_validation_keeps_declared_numerical_failure_classification(monkeypatch,name,code):
    monkeypatch.setattr(adapter,"trace_routes",lambda *_:pytest.fail("pure validation traced"))
    def fail(_):
        raise getattr(adapter,name)("controlled scene arithmetic admission failure")
    monkeypatch.setattr(adapter,"validate_scene",fail)
    with pytest.raises(adapter.RefractiveNumericalError) as caught:
        adapter.validate_submission(envelope())
    assert caught.value.code == code
