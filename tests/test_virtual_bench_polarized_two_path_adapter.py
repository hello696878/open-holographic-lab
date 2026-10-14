"""Direct public-call fidelity, immutable settings and atomic measurements."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import math

import numpy as np
import pytest

from apps.virtual_bench import polarized_two_path_adapter as adapter
from apps.virtual_bench import polarized_two_path_protocol as protocol
from ohlab.optics import sample_source
from ohlab.optics.polarization import JonesField, apply_linear_polarizer, transmission_ratio
from ohlab.optics.polarized_interference import (
    PolarizerAction, RetarderAction, PolarizationArm, PolarizedTwoArmSpec, run_polarized_two_arm,
)

REQUEST_ID = "cfdccf7d-d8ee-4ad4-b359-9d2d04106747"


def polarizer(identifier="loss_A", angle=.31):
    return {"id": identifier, "kind": "linear_polarizer", "axis_angle_rad": angle}


def retarder(identifier="plate_B", angle=.19, delta=math.pi / 2):
    return {"id": identifier, "kind": "linear_retarder", "axis_angle_rad": angle, "retardance_rad": delta}


def envelope(*, ny=3, nx=4, gaussian=False, enabled=True, angle=.27, phase=.37,
             amplitude=1.0, coefficients=None, actions_0=None, actions_1=None, distances=(.0011, .0017)):
    source = {"kind": "uniform", "amplitude": amplitude, "phase_rad": .17}
    if gaussian:
        source.update(kind="gaussian", waist_radius_m=11e-6, waist_z_m=-.00073,
                      center_x_m=2e-6, center_y_m=-1e-6)
    return {"protocol_version": 1, "message_type": "polarized_two_path_submission", "request_id": REQUEST_ID,
        "experiment_sha256": None, "experiment": {"schema_version": 1, "model_contract": protocol.MODEL_CONTRACT,
            "wavelength_m": 633e-9, "grid": {"ny": ny, "nx": nx, "dy": 4.1e-6, "dx": 3.7e-6}, "source": source,
            "coefficients": coefficients or {"x": {"re": .8, "im": .3}, "y": {"re": -.2, "im": .7}},
            "arm_0": {"distance_m": distances[0], "actions": [] if actions_0 is None else actions_0},
            "arm_1": {"distance_m": distances[1], "actions": [] if actions_1 is None else actions_1},
            "relative_phase_rad": phase, "analyzer": {"enabled": enabled, "axis_angle_rad": angle}}}


def digested(value=None):
    value = deepcopy(envelope() if value is None else value)
    value["experiment_sha256"] = adapter.validate_submission(value, require_digest=False).experiment_sha256
    return value


def sweep_envelope(value=None, *, digested=True):
    value = deepcopy(envelope() if value is None else value)
    fixed = value["experiment"]
    del fixed["relative_phase_rad"]
    request = {"protocol_version": 1, "message_type": "polarized_two_path_sweep_submission",
        "request_id": value["request_id"], "fixed_experiment_sha256": None,
        "fixed_experiment": fixed, "phases_rad": list(protocol.PHASES_RAD)}
    if digested:
        request["fixed_experiment_sha256"] = adapter.validate_sweep_submission(request, require_digest=False).fixed_experiment_sha256
    return request


def unpack(frame):
    magic, length, reserved = protocol.PREAMBLE.unpack_from(frame)
    assert magic == protocol.MAGIC and reserved == 0
    header = json.loads(frame[16:16+length])
    base = 16+length+(-length % 8)
    arrays = {item["name"]: np.frombuffer(frame, dtype="<f8", count=item["nbytes"]//8,
        offset=base+item["offset_bytes"]).reshape(item["shape"]) for item in header["arrays"]}
    return header, arrays


def output(value=None):
    return unpack(adapter.simulate_submission(adapter.validate_submission(digested(value))))


def direct(value, phase=None):
    """Independent integration callsites; no production adapter mapping helper."""
    source = adapter.validate_experiment(value).source_plane
    scalar = sample_source(source)
    coefficients = tuple(complex(value["coefficients"][name]["re"], value["coefficients"][name]["im"]) for name in ("x", "y"))
    incident = JonesField.from_scalar(scalar, x_coefficient=coefficients[0], y_coefficient=coefficients[1])
    arms = []
    for name in ("arm_0", "arm_1"):
        actions = tuple(PolarizerAction(axis_angle_rad=a["axis_angle_rad"]) if a["kind"] == "linear_polarizer" else
            RetarderAction(axis_angle_rad=a["axis_angle_rad"], retardance_rad=a["retardance_rad"]) for a in value[name]["actions"])
        arms.append(PolarizationArm(distance_m=value[name]["distance_m"], actions=actions))
    result = run_polarized_two_arm(incident, spec=PolarizedTwoArmSpec(arm_0=arms[0], arm_1=arms[1],
        relative_phase_rad=value["relative_phase_rad"] if phase is None else phase))
    analyzed = tuple(apply_linear_polarizer(raw, axis_angle_rad=value["analyzer"]["axis_angle_rad"])
                     for raw in result.outputs) if value["analyzer"]["enabled"] else None
    return incident, result, analyzed


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("gaussian", [False, True])
@pytest.mark.parametrize("shape", [(3,4), (5,6), (6,5)])
def test_complete_public_arrays_axes_norms_histories_and_nonmutation(enabled, gaussian, shape, monkeypatch):
    value = envelope(ny=shape[0], nx=shape[1], gaussian=gaussian, enabled=enabled,
        actions_0=[retarder("a0", -.19, 2.13), polarizer("a1", .41)],
        actions_1=[polarizer("b0", -.27), retarder("b1", .31, -1.17)])
    original = deepcopy(value)
    incident, expected, analyzed = direct(value["experiment"])
    seen = []
    public = adapter.run_polarized_two_arm
    def run(field, *, spec):
        before = (field.x.data.copy(), field.y.data.copy())
        result = public(field, spec=spec)
        np.testing.assert_array_equal(field.x.data, before[0])
        np.testing.assert_array_equal(field.y.data, before[1])
        seen.append(result)
        return result
    monkeypatch.setattr(adapter, "run_polarized_two_arm", run)
    header, arrays = output(value)
    assert value == original, "V2G_INPUT_NONMUTATION_DETECTED"
    for index, field in enumerate(expected.outputs):
        np.testing.assert_array_equal(arrays[f"raw_port_{index}_intensity"], field.intensity,
                                      err_msg="V2G_DIRECT_PUBLIC_DETECTED")
        for component in ("x", "y"):
            np.testing.assert_array_equal(getattr(seen[0].outputs[index], component).data,
                                          getattr(field, component).data, err_msg="V2G_DIRECT_PUBLIC_DETECTED")
    np.testing.assert_array_equal(arrays["x_m"], incident.grid.x)
    np.testing.assert_array_equal(arrays["y_m"], incident.grid.y)
    for name in (*protocol.NORM_PAIRS, "arm_action_norms"):
        assert header["norms"][name] == json.loads(json.dumps(getattr(expected.norms, name))), "V2G_HISTORY_DETECTED"
    for name in protocol.DIAGNOSTIC_KEYS:
        assert header["diagnostics"][name] == json.loads(json.dumps(getattr(expected.norms, name))), "V2G_DIRECT_PUBLIC_DETECTED"
    if enabled:
        for index, measured in enumerate(analyzed):
            np.testing.assert_array_equal(arrays[f"analyzed_port_{index}_intensity"], measured.intensity,
                                          err_msg="V2G_ANALYZER_PUBLIC_DETECTED")
            port = header["analysis"]["ports"][index]
            assert port["raw_norm"] == expected.norms.outputs[index]
            assert port["analyzed_norm"] == measured.sampled_norm, "V2G_ANALYZER_LOSS_DETECTED"
            assert port["original_input_ratio"] == transmission_ratio(incident, measured)
            assert port["raw_output_ratio"] == transmission_ratio(expected.outputs[index], measured)
    else:
        assert header["analysis"]["ports"] is None and not any(name.startswith("analyzed") for name in arrays)
    if gaussian:
        assert header["experiment"]["source"]["waist_z_m"] == -.00073


def spy_calls(monkeypatch):
    counts, incident_ids, phases = {"source": 0, "Jones": 0, "runner": 0, "analyzer": 0}, [], []
    source, jones, run, analyzer = adapter.sample_source, adapter.JonesField.from_scalar, adapter.run_polarized_two_arm, adapter.apply_linear_polarizer
    def sample(spec):
        counts["source"] += 1
        return source(spec)
    def make(cls, field, **kwargs):
        counts["Jones"] += 1
        return jones(field, **kwargs)
    def solve(field, *, spec):
        counts["runner"] += 1
        incident_ids.append(id(field)); phases.append(spec.relative_phase_rad)
        return run(field, spec=spec)
    def analyze(field, **kwargs):
        counts["analyzer"] += 1
        return analyzer(field, **kwargs)
    monkeypatch.setattr(adapter, "sample_source", sample)
    monkeypatch.setattr(adapter.JonesField, "from_scalar", classmethod(make))
    monkeypatch.setattr(adapter, "run_polarized_two_arm", solve)
    monkeypatch.setattr(adapter, "apply_linear_polarizer", analyze)
    return counts, incident_ids, phases


@pytest.mark.parametrize("enabled", [False, True])
def test_single_exact_public_orchestration_count(enabled, monkeypatch):
    counts, _, phases = spy_calls(monkeypatch)
    output(envelope(enabled=enabled))
    assert counts == {"source":1,"Jones":1,"runner":1,"analyzer":2 if enabled else 0}, "V2G_SINGLE_CALLS_DETECTED"
    assert phases == [.37]


@pytest.mark.parametrize("enabled", [False, True])
def test_sweep_seventeen_actual_public_rows_one_incident_and_independent_endpoints(enabled, monkeypatch):
    value = envelope(gaussian=True, enabled=enabled, actions_0=[retarder("w", .21, -.73)],
                     actions_1=[polarizer("p", -.11)], phase=8.31)
    submission = adapter.validate_sweep_submission(sweep_envelope(value))
    counts, incidents, phases = spy_calls(monkeypatch)
    reply = adapter.sweep_submission(submission)
    assert counts == {"source":1,"Jones":1,"runner":17,"analyzer":34 if enabled else 0}, "V2G_SWEEP_CALLS_DETECTED"
    assert len(set(incidents)) == 1 and phases == list(protocol.PHASES_RAD), "V2G_SWEEP_CALLS_DETECTED"
    rows = json.loads(reply.body)["rows"]
    assert len(rows) == 17 and reply.status_code == 200
    for index, row in enumerate(rows):
        _, result, measured = direct(value["experiment"], protocol.PHASES_RAD[index])
        assert row["norms"]["outputs"] == list(result.norms.outputs), "V2G_ACTUAL_SWEEP_DETECTED"
        if enabled:
            assert [p["analyzed_norm"] for p in row["analysis"]["ports"]] == [f.sampled_norm for f in measured], "V2G_ACTUAL_SWEEP_DETECTED"
    assert rows[0]["phase_rad"] == 0 and rows[-1]["phase_rad"] == 2*math.pi


def test_validation_zero_optics_full_ownership_and_disabled_angle_identity(monkeypatch):
    def forbidden(*args, **kwargs): pytest.fail("V2G_VALIDATION_ZERO_OPTICS_DETECTED")
    for name in ("sample_source", "run_polarized_two_arm", "apply_linear_polarizer", "transmission_ratio"):
        monkeypatch.setattr(adapter, name, forbidden)
    monkeypatch.setattr(adapter.JonesField, "from_scalar", forbidden)
    value = envelope(gaussian=True, enabled=False, angle=-7.123456789123456,
                     actions_0=[retarder("a")], actions_1=[polarizer("b")])
    validated = adapter.validate_submission(value, require_digest=False)
    old = validated.experiment.to_dict()
    value["experiment"]["source"]["amplitude"] = 9
    value["experiment"]["arm_0"]["actions"][0]["id"] = "changed"
    assert validated.experiment.to_dict() == old
    copied = validated.experiment.to_dict(); copied["analyzer"]["axis_angle_rad"] = .17
    assert validated.experiment.to_dict()["analyzer"]["axis_angle_rad"] == -7.123456789123456
    assert protocol.experiment_digest(copied) != validated.experiment_sha256, "V2G_DISABLED_ANGLE_IDENTITY_DETECTED"
    with pytest.raises(FrozenInstanceError): validated.experiment.relative_phase_rad = 0
    adapter.validate_sweep_submission(sweep_envelope(envelope(), digested=False), require_digest=False)


@pytest.mark.parametrize("mutation", [
    lambda v: v.update(extra=1), lambda v:v.update(schema_version=True), lambda v:v.update(relative_phase_rad=True),
    lambda v:v["grid"].update(nx=129), lambda v:v["grid"].update(ny=False), lambda v:v["grid"].update(dx=0),
    lambda v:v["coefficients"]["x"].update(re=float("nan")), lambda v:v["coefficients"]["y"].update(im=[]),
    lambda v:v["source"].update(waist_z_m=0), lambda v:v["arm_0"].update(distance_m=-1),
    lambda v:v["analyzer"].update(enabled=0), lambda v:v["analyzer"].update(axis_angle_rad=float("inf")),
    lambda v:v["arm_0"].update(actions=[polarizer("a"),polarizer("b"),polarizer("c")]),
    lambda v:v["arm_0"].update(actions=[polarizer("analyzer")]),
    lambda v:(v["arm_0"].update(actions=[polarizer("same")]),v["arm_1"].update(actions=[retarder("same")])),
    lambda v:v["arm_0"].update(actions=[{**polarizer(),"retardance_rad":0}]),
    lambda v:v["arm_1"].update(actions=[{**retarder(),"ignored":1}]),
])
def test_invalid_full_settings_reject_before_source_sampling(mutation, monkeypatch):
    monkeypatch.setattr(adapter, "sample_source", lambda _:pytest.fail("sampler reached"))
    value = envelope(); mutation(value["experiment"])
    with pytest.raises((TypeError, ValueError)): adapter.validate_submission(value, require_digest=False)


def test_validation_digest_and_sweep_phase_requirements():
    value = envelope()
    with pytest.raises(ValueError, match="digest"): adapter.validate_submission(value)
    valid = digested(value)
    with pytest.raises(ValueError, match="null"): adapter.validate_submission(valid, require_digest=False)
    valid["experiment"]["analyzer"]["axis_angle_rad"] += .01
    with pytest.raises(ValueError, match="digest"): adapter.validate_submission(valid)
    sweep = sweep_envelope(); sweep["phases_rad"][-1] = 0
    with pytest.raises(ValueError, match="seventeen"): adapter.validate_sweep_submission(sweep)
    sweep = sweep_envelope(); sweep["fixed_experiment"]["relative_phase_rad"] = 0
    with pytest.raises(ValueError, match="omitted|without"): adapter.validate_sweep_submission(sweep)


def test_static_mapping_matches_exact_public_actions_order_parameters_and_common_phase():
    value=envelope(actions_0=[retarder("a",-.19,2.13),polarizer("b",.41)],
        actions_1=[polarizer("c",-.27),retarder("d",.31,-1.17)],phase=8.570796326794897,
        distances=(.0011000000000000003,.0017000000000000001))
    experiment=adapter.validate_experiment(value["experiment"])
    expected=PolarizedTwoArmSpec(
        arm_0=PolarizationArm(distance_m=.0011000000000000003,
            actions=(RetarderAction(axis_angle_rad=-.19,retardance_rad=2.13),PolarizerAction(axis_angle_rad=.41))),
        arm_1=PolarizationArm(distance_m=.0017000000000000001,
            actions=(PolarizerAction(axis_angle_rad=-.27),RetarderAction(axis_angle_rad=.31,retardance_rad=-1.17))),
        relative_phase_rad=8.570796326794897)
    actual=experiment.public_spec()
    assert actual==expected,"V2G_ACTION_MAPPING_DETECTED"
    assert tuple(type(action) for action in actual.arm_0.actions)==(RetarderAction,PolarizerAction),"V2G_ACTION_MAPPING_DETECTED"
    assert tuple(type(action) for action in actual.arm_1.actions)==(PolarizerAction,RetarderAction),"V2G_ACTION_MAPPING_DETECTED"
    assert experiment.public_spec(-7.123456789123456).relative_phase_rad==-7.123456789123456,"V2G_ACTION_MAPPING_DETECTED"
    assert [a["id"] for a in experiment.to_dict()["arm_0"]["actions"]]==["a","b"],"V2G_ACTION_MAPPING_DETECTED"


@pytest.mark.parametrize("port", [0,1])
def test_controlled_analyzer_failure_is_atomic_no_replay(port, monkeypatch):
    counts, _, _ = spy_calls(monkeypatch)
    original, calls = adapter.apply_linear_polarizer, []
    def fail(field, **kwargs):
        calls.append(field)
        if len(calls) == port+1: raise ValueError("controlled analyzer arithmetic")
        return original(field, **kwargs)
    monkeypatch.setattr(adapter, "apply_linear_polarizer", fail)
    monkeypatch.setattr(adapter, "encode_result", lambda *a,**k:pytest.fail("V2G_ATOMIC_ANALYZER_DETECTED"))
    with pytest.raises(adapter.NumericalError, match=f"port_{port}") as caught:
        adapter.simulate_submission(adapter.validate_submission(digested()))
    assert caught.value.__cause__ is not None
    assert counts["runner"] == 1 and len(calls) == port+1, "V2G_ATOMIC_ANALYZER_DETECTED"


def test_genuine_public_analyzer_underflow_after_successful_v2f_no_raw_only_outcome(monkeypatch):
    value = envelope(enabled=True, angle=math.pi/2, phase=0, amplitude=1e-150, distances=(0,0),
                     coefficients={"x":{"re":1.,"im":0.},"y":{"re":0.,"im":0.}})
    counts, _, _ = spy_calls(monkeypatch)
    monkeypatch.setattr(adapter, "encode_result", lambda *a,**k:pytest.fail("raw-only success"))
    with pytest.raises(adapter.NumericalError, match="analyzer port_0.*underflow"):
        adapter.simulate_submission(adapter.validate_submission(digested(value)))
    assert counts == {"source":1,"Jones":1,"runner":1,"analyzer":1}, "V2G_ATOMIC_ANALYZER_DETECTED"


@pytest.mark.parametrize("failure_index", [0,8,16])
@pytest.mark.parametrize("analyzer_failure", [False,True])
@pytest.mark.parametrize("error_type,status", [(ValueError,422),(RuntimeError,500)])
def test_sweep_failure_retains_only_genuine_completed_rows(failure_index, analyzer_failure, error_type, status, monkeypatch):
    value = envelope(enabled=True)
    runner, analyzer = adapter.run_polarized_two_arm, adapter.apply_linear_polarizer
    counts = {"runner":0,"analyzer":0}
    def run(field, *, spec):
        counts["runner"] += 1
        if not analyzer_failure and counts["runner"] == failure_index+1: raise error_type("controlled failure")
        return runner(field, spec=spec)
    def analyze(field, **kwargs):
        counts["analyzer"] += 1
        if analyzer_failure and counts["analyzer"] == failure_index*2+2: raise error_type("controlled second analyzer")
        return analyzer(field, **kwargs)
    monkeypatch.setattr(adapter, "run_polarized_two_arm", run)
    monkeypatch.setattr(adapter, "apply_linear_polarizer", analyze)
    reply = adapter.sweep_submission(adapter.validate_sweep_submission(sweep_envelope(value)))
    body = json.loads(reply.body)
    assert reply.status_code == status and body["status"] == "failed"
    assert body["completed_count"] == body["failed_index"] == len(body["rows"]) == failure_index, "V2G_SWEEP_PREFIX_DETECTED"
    assert [r["index"] for r in body["rows"]] == list(range(failure_index))
    assert counts["runner"] == failure_index+1
    assert counts["analyzer"] == (2*(failure_index+1) if analyzer_failure else 2*failure_index)


@pytest.mark.parametrize("enabled", [False,True])
def test_zero_input_and_small_unwrapped_values_preserved(enabled):
    value = envelope(enabled=enabled, amplitude=0, angle=1e-200, phase=-1e-200, distances=(0,0))
    header, arrays = output(value)
    assert header["diagnostics"]["output_fractions"] == [None,None]
    assert header["diagnostics"]["total_output_ratio"] is None
    assert header["analysis"]["axis_angle_rad"] == 1e-200
    assert header["experiment"]["relative_phase_rad"] == -1e-200
    assert all(not np.any(array) for name,array in arrays.items() if name.endswith("intensity"))
    if enabled:
        assert header["analysis"]["total_original_input_ratio"] is None
        assert all(p["original_input_ratio"] is None and p["raw_output_ratio"] is None for p in header["analysis"]["ports"])
