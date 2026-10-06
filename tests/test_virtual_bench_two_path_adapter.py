"""V2b public sampling/solver reuse and independent integration measurements."""

from dataclasses import FrozenInstanceError
import json
import math
import struct

import numpy as np
import pytest

from apps.virtual_bench import two_path_adapter as adapter
from apps.virtual_bench.two_path_protocol import PHASES_RAD
from ohlab.optics import SequentialExperiment, sample_source
from ohlab.optics.interference import TwoArmSpec, run_two_arm

REQUEST_ID = "12345678-1234-4234-8234-123456789abc"


def envelope(*, uniform=False, amplitude=1.0, phase=0.37, ny=9, nx=10, distance_0=0.0, distance_1=0.0):
    source = {"kind": "uniform", "amplitude": amplitude, "phase_rad": 0.17}
    if not uniform:
        source.update(kind="gaussian", waist_radius_m=25e-6, waist_z_m=-1e-3,
                      center_x_m=3e-6, center_y_m=-4e-6)
    return {"protocol_version": 1, "message_type": "two_path_submission", "request_id": REQUEST_ID,
            "experiment": {"wavelength_m": 633e-9,
                           "grid": {"ny": ny, "nx": nx, "dy": 5e-6, "dx": 4e-6},
                           "source": source, "two_arm_spec": {
                               "arm_0_distance_m": distance_0, "arm_1_distance_m": distance_1,
                               "relative_phase_rad": phase}}}


def sweep_envelope(value=None):
    scientific = (value or envelope())["experiment"]
    arms = scientific["two_arm_spec"]
    return {"protocol_version": 1, "message_type": "two_path_sweep_submission",
            "request_id": REQUEST_ID, "fixed_experiment": {
                **{name: scientific[name] for name in ("wavelength_m", "grid", "source")},
                "arm_0_distance_m": arms["arm_0_distance_m"],
                "arm_1_distance_m": arms["arm_1_distance_m"]}, "phases_rad": list(PHASES_RAD)}


def source_plane(scientific):
    return SequentialExperiment.from_dict({
        "schema_version": 1, "model_contract": "v0_aligned_scalar_forward_v1",
        **{name: scientific[name] for name in ("wavelength_m", "grid", "source")},
        "components": [], "observation": {"id": "source_plane", "z_m": 0.0}})


def unpack(frame):
    magic, length, reserved = struct.unpack("<8sII", frame[:16])
    assert magic == b"OHLAB2P\0" and reserved == 0
    header = json.loads(frame[16:16 + length])
    start = 16 + (length + 7) // 8 * 8
    arrays = {d["name"]: np.frombuffer(frame[start + d["offset_bytes"]:start + d["offset_bytes"] + d["nbytes"]],
                                      dtype="<f8").reshape(d["shape"]) for d in header["arrays"]}
    return header, arrays


@pytest.mark.parametrize("uniform", [False, True])
def test_single_direct_equivalence_validation_zero_sampling_once_runner_once(uniform, monkeypatch):
    value = envelope(uniform=uniform, distance_0=1e-3, distance_1=2e-3)
    samples, calls = [], []
    original_sampler, original_runner = adapter.sample_source, adapter.run_two_arm

    def sample(experiment):
        samples.append(experiment)
        return original_sampler(experiment)

    def run(incident, *, spec):
        calls.append((incident, spec))
        return original_runner(incident, spec=spec)

    monkeypatch.setattr(adapter, "sample_source", sample)
    monkeypatch.setattr(adapter, "run_two_arm", run)
    submission = adapter.validate_submission(value)
    assert samples == calls == []
    header, arrays = unpack(adapter.simulate_submission(submission))
    assert len(samples) == 1 and len(calls) == 1, "SINGLE_CALL_COUNT_DETECTED"
    assert samples[0].components == () and samples[0].observation.z_m == 0
    actual_incident, actual_spec = calls[0]
    expected = run_two_arm(actual_incident, spec=actual_spec)
    assert header["experiment"] == value["experiment"]
    for index in (0, 1):
        assert arrays[f"intensity_port_{index}"].tobytes() == expected.outputs[index].intensity.tobytes()
    assert arrays["x_m"].tobytes() == actual_incident.grid.x.tobytes()
    assert arrays["y_m"].tobytes() == actual_incident.grid.y.tobytes()
    assert header["norms"] == {name: list(getattr(expected.norms, name)) for name in
                               ("inputs", "split", "propagated", "combiner", "outputs")}
    for name, actual in header["diagnostics"].items():
        expected_value = getattr(expected.norms, name)
        assert actual == (list(expected_value) if isinstance(expected_value, tuple) else expected_value)


def test_ordered_ports_not_swapped_and_second_output_not_duplicated():
    value = envelope(uniform=True, phase=0.0)
    _, arrays = unpack(adapter.simulate_submission(adapter.validate_submission(value)))
    assert np.min(arrays["intensity_port_0"]) > .99, "PORT_SWAP_DETECTED"
    assert np.max(arrays["intensity_port_1"]) == 0, "DUPLICATE_PORT_DETECTED"


def test_nonzero_phase_is_used_without_wrapping():
    value = envelope(uniform=True, phase=2 * math.pi + .37)
    try:
        header, arrays = unpack(adapter.simulate_submission(adapter.validate_submission(value)))
    except Exception as exc:
        raise AssertionError("IGNORE_PHASE_DETECTED: valid submitted phase did not complete") from exc
    assert header["experiment"]["two_arm_spec"]["relative_phase_rad"] == 2 * math.pi + .37
    expected = math.sin((2 * math.pi + .37) / 2) ** 2
    assert np.allclose(arrays["intensity_port_1"], expected, rtol=2e-13, atol=2e-15), "IGNORE_PHASE_DETECTED"


@pytest.mark.parametrize("phase", [0.0, math.pi / 2, math.pi, 1e-4, -1e-4, math.pi-1e-4, math.pi+1e-4])
def test_equal_arm_analytic_intensity_and_near_dark_remains_nonzero(phase):
    value = envelope(uniform=True, amplitude=2.0, phase=phase, distance_0=1e-3, distance_1=1e-3)
    _, arrays = unpack(adapter.simulate_submission(adapter.validate_submission(value)))
    for index, expected in enumerate((4 * math.cos(phase / 2)**2, 4 * math.sin(phase / 2)**2)):
        np.testing.assert_allclose(arrays[f"intensity_port_{index}"], expected, rtol=2e-11, atol=2e-26)
    if phase != 0.0:
        assert np.min(arrays["intensity_port_0"]) > 0 and np.min(arrays["intensity_port_1"]) > 0


def test_original_input_denominator_retains_actual_evanescent_loss():
    value = envelope(phase=.37, distance_0=100e-9, distance_1=130e-9)
    value["experiment"]["grid"].update(dy=.22e-6, dx=.20e-6)
    value["experiment"]["source"].update(waist_radius_m=.18e-6, waist_z_m=0.0, center_x_m=0.0, center_y_m=0.0)
    direct = run_two_arm(sample_source(source_plane(value["experiment"])), spec=TwoArmSpec(**value["experiment"]["two_arm_spec"]))
    header, _ = unpack(adapter.simulate_submission(adapter.validate_submission(value)))
    diagnostics = header["diagnostics"]
    assert direct.norms.total_output_ratio < .99
    assert diagnostics["output_fractions"] == list(direct.norms.output_fractions), "INPUT_DENOMINATOR_DETECTED"
    assert sum(diagnostics["output_fractions"]) < .99, "INPUT_DENOMINATOR_DETECTED"
    assert diagnostics["total_output_ratio"] == direct.norms.total_output_ratio


def test_common_source_phase_changes_no_intensity_and_unequal_lengths_use_carrier():
    value = envelope(uniform=True, phase=0.0, distance_0=633e-9/7, distance_1=633e-9/7+633e-9/6)
    header, arrays = unpack(adapter.simulate_submission(adapter.validate_submission(value)))
    np.testing.assert_allclose(header["diagnostics"]["output_fractions"], [.75, .25], rtol=2e-13, atol=2e-15)
    value["experiment"]["source"]["phase_rad"] = -2.41
    _, rotated = unpack(adapter.simulate_submission(adapter.validate_submission(value)))
    for index in (0, 1):
        np.testing.assert_allclose(rotated[f"intensity_port_{index}"], arrays[f"intensity_port_{index}"], rtol=2e-13, atol=2e-15)


def test_zero_input_and_server_negative_zero_are_not_clamped_or_relabelled():
    value = envelope(amplitude=0, phase=-0.0)
    submission = adapter.validate_submission(value)
    assert math.copysign(1.0, submission.experiment.spec.relative_phase_rad) == -1
    header, arrays = unpack(adapter.simulate_submission(submission))
    assert all(np.count_nonzero(arrays[f"intensity_port_{i}"]) == 0 for i in (0, 1))
    assert header["diagnostics"]["output_fractions"] == [None, None]
    assert header["diagnostics"]["total_output_ratio"] is None
    assert header["intensity_max"] == [0, 0]


def test_mutable_request_cannot_change_owned_scientific_identity():
    value = envelope()
    submission = adapter.validate_submission(value)
    scientific, digest = submission.experiment.to_dict(), submission.experiment_sha256
    value["experiment"]["source"]["amplitude"] = 17
    value["experiment"]["grid"]["nx"] = 20
    value["experiment"]["two_arm_spec"]["relative_phase_rad"] = 2
    assert submission.experiment.to_dict() == scientific and submission.experiment_sha256 == digest
    with pytest.raises(FrozenInstanceError):
        submission.request_id = "x"


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(protocol_version=True), lambda d: d.update(message_type="legacy"),
    lambda d: d.update(extra=True), lambda d: d["experiment"].update(extra=True),
    lambda d: d["experiment"]["grid"].update(nx=513), lambda d: d["experiment"]["grid"].update(nx=True),
    lambda d: d["experiment"]["two_arm_spec"].update(relative_phase_rad=True),
    lambda d: d["experiment"]["two_arm_spec"].update(relative_phase_rad=float("inf")),
    lambda d: d["experiment"]["two_arm_spec"].update(arm_0_distance_m=-1),
    lambda d: d["experiment"]["source"].update(amplitude=-1),
])
def test_invalid_requests_fail_before_sampling_or_solver(mutation, monkeypatch):
    value = envelope()
    mutation(value)
    monkeypatch.setattr(adapter, "sample_source", lambda _: pytest.fail("sampler reached"))
    monkeypatch.setattr(adapter, "run_two_arm", lambda *a, **k: pytest.fail("solver reached"))
    with pytest.raises((ValueError, TypeError)):
        adapter.validate_submission(value)


def test_sweep_actual_seventeen_invocations_and_independent_endpoint_values(monkeypatch):
    value = sweep_envelope(envelope(phase=.37, distance_0=1e-3, distance_1=2e-3))
    samples, calls = [], []
    original_sampler, original_runner = adapter.sample_source, adapter.run_two_arm
    monkeypatch.setattr(adapter, "sample_source", lambda e: (samples.append(e), original_sampler(e))[1])

    def counted(incident, *, spec):
        calls.append((incident, spec))
        return original_runner(incident, spec=spec)

    monkeypatch.setattr(adapter, "run_two_arm", counted)
    submission = adapter.validate_sweep_submission(value)
    assert samples == calls == []
    reply = adapter.sweep_submission(submission)
    body = json.loads(reply.body)
    assert reply.status_code == 200 and body["status"] == "complete", "FABRICATED_SWEEP_DETECTED"
    assert len(samples) == 1 and len(calls) == 17, "SWEEP_CALL_COUNT_DETECTED"
    assert [spec.relative_phase_rad for _, spec in calls] == list(PHASES_RAD), "FABRICATED_SWEEP_DETECTED"
    assert calls[0][1].relative_phase_rad == 0 and calls[-1][1].relative_phase_rad != 0
    assert body["requested_count"] == body["completed_count"] == 17
    assert body["failed_index"] is None and body["error"] is None
    for row, (incident, spec) in zip(body["rows"], calls):
        result = run_two_arm(incident, spec=spec)
        assert row["output_norms"] == list(result.norms.outputs), "FABRICATED_SWEEP_DETECTED"
        assert row["output_fractions"] == list(result.norms.output_fractions)
    np.testing.assert_allclose(body["rows"][-1]["output_norms"], body["rows"][0]["output_norms"], rtol=2e-13, atol=1e-25)


@pytest.mark.parametrize("unexpected,status", [(False, 422), (True, 500)])
def test_failed_sweep_returns_only_genuine_prefix_and_never_retries(monkeypatch, unexpected, status):
    submission = adapter.validate_sweep_submission(sweep_envelope())
    calls = []
    original = adapter.run_two_arm

    def fail_third(incident, *, spec):
        calls.append(spec.relative_phase_rad)
        if len(calls) == 3:
            raise RuntimeError("private internal detail") if unexpected else ValueError("controlled numerical failure")
        return original(incident, spec=spec)

    monkeypatch.setattr(adapter, "run_two_arm", fail_third)
    reply = adapter.sweep_submission(submission)
    body = json.loads(reply.body)
    assert reply.status_code == status and body["status"] == "failed"
    assert body["requested_count"] == 17 and body["completed_count"] == body["failed_index"] == 2
    assert len(body["rows"]) == 2 and calls == list(PHASES_RAD[:3])
    assert [row["phase_rad"] for row in body["rows"]] == list(PHASES_RAD[:2])
    assert ("private internal detail" not in reply.body.decode()) if unexpected else body["error"]["code"] == "numerical_failure"


@pytest.mark.parametrize("mutation", [
    lambda d: d["fixed_experiment"]["grid"].update(nx=129),
    lambda d: d["phases_rad"].pop(), lambda d: d["phases_rad"].append(7),
    lambda d: d["phases_rad"].__setitem__(2, .9),
    lambda d: d["phases_rad"].__setitem__(0, True),
    lambda d: d["fixed_experiment"].update(relative_phase_rad=0),
])
def test_sweep_resource_and_exact_phase_policy(mutation):
    value = sweep_envelope()
    mutation(value)
    with pytest.raises((TypeError, ValueError)):
        adapter.validate_sweep_submission(value)
