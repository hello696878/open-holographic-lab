"""W1 strict ownership, cheap limits and one public sampler invocation."""

from dataclasses import FrozenInstanceError
import copy
import json

import pytest

from apps.virtual_bench import wave_field_adapter as adapter
from apps.virtual_bench import wave_field_protocol as protocol

REQUEST_ID = "12345678-1234-4234-8234-123456789abc"


def envelope(*, ny=7, nx=8):
    return {"request_id": REQUEST_ID, "experiment": {
        "schema_version": 1, "model_contract": "v0_aligned_scalar_forward_v1",
        "wavelength_m": 633e-9, "grid": {"ny": ny, "nx": nx, "dy": 19e-6, "dx": 16e-6},
        "source": {"kind": "gaussian", "amplitude": 1.0, "phase_rad": 0.31,
                   "waist_radius_m": 45e-6, "waist_z_m": -0.002,
                   "center_x_m": 5e-6, "center_y_m": -7e-6},
        "components": [{"kind": "circular_aperture", "id": "aperture", "z_m": 0.003,
                        "radius_m": 42e-6},
                       {"kind": "thin_lens", "id": "lens", "z_m": 0.006,
                        "focal_length_m": 0.08}],
        "observation": {"id": "screen", "z_m": 0.022}},
        "sampling": {"interior_z_m": [0.001, 0.005, 0.015]}}


def unpack(frame):
    magic, length, reserved = protocol.PREAMBLE.unpack_from(frame)
    assert magic == protocol.MAGIC and reserved == 0
    header = json.loads(frame[16:16+length])
    payload_start = 16+length+(-length % 8)
    assert frame[16+length:payload_start] == b"\0"*(-length % 8)
    return header, frame[payload_start:]


def test_exact_owned_immutable_envelope_validation_is_noncomputing(monkeypatch):
    value = envelope()
    monkeypatch.setattr(adapter, "sample_wave_field", lambda *a, **k: pytest.fail("solver during validation"))
    submission = adapter.validate_submission(value)
    owned = submission.experiment.to_dict()
    value["experiment"]["source"]["amplitude"] = 13
    value["sampling"]["interior_z_m"][0] = 0.002
    assert submission.experiment.to_dict() == owned and submission.interior_z_m == (0.001, 0.005, 0.015)
    with pytest.raises(FrozenInstanceError):
        submission.request_id = REQUEST_ID
    assert len(submission.experiment_sha256) == 64


@pytest.mark.parametrize("mutate,exception", [
    (lambda value: value.update(message_type="w1_wave_field"), ValueError),
    (lambda value: value.pop("sampling"), ValueError),
    (lambda value: value["sampling"].update(extra=1), ValueError),
    (lambda value: value["sampling"].update(interior_z_m="0.001"), TypeError),
    (lambda value: value["sampling"].update(interior_z_m=[0.001]*20), ValueError),
    (lambda value: value["sampling"].update(interior_z_m=[True]), TypeError),
    (lambda value: value["sampling"].update(interior_z_m=[float("nan")]), ValueError),
    (lambda value: value["sampling"].update(interior_z_m=[0.003]), ValueError),
    (lambda value: value["sampling"].update(interior_z_m=[0.005, 0.001]), ValueError),
    (lambda value: value["sampling"].update(interior_z_m=[-0.001]), ValueError),
    (lambda value: value["experiment"]["grid"].update(nx=129), ValueError),
    (lambda value: value["experiment"]["grid"].update(ny=True), TypeError),
    (lambda value: value["experiment"]["source"].update(kind="uniform"), ValueError),
    (lambda value: value["experiment"]["components"].reverse(), ValueError),
    (lambda value: value["experiment"]["components"].pop(), ValueError),
    (lambda value: value["experiment"].update(unrecognized=True), ValueError),
])
def test_caps_domains_unknown_fields_and_unsupported_trains_fail_before_sampler(monkeypatch, mutate, exception):
    monkeypatch.setattr(adapter, "sample_wave_field", lambda *a, **k: pytest.fail("solver reached"))
    value = envelope()
    mutate(value)
    with pytest.raises(exception):
        adapter.validate_submission(value)


def test_axis_cap_is_checked_before_public_experiment_constructor(monkeypatch):
    value = envelope(nx=129)
    monkeypatch.setattr(adapter, "validate_experiment", lambda *a: pytest.fail("constructor reached"))
    with pytest.raises(ValueError, match="1..128"):
        adapter.validate_submission(value)


def test_one_public_sampler_and_exact_frozen_identity(monkeypatch):
    calls = []
    original = adapter.sample_wave_field
    def counted(experiment, *, interior_z_m):
        calls.append((experiment, interior_z_m))
        return original(experiment, interior_z_m=interior_z_m)
    monkeypatch.setattr(adapter, "sample_wave_field", counted)
    value = envelope()
    before = copy.deepcopy(value)
    submission = adapter.validate_submission(value)
    header, _ = unpack(adapter.simulate_submission(submission))
    assert calls == [(submission.experiment, submission.interior_z_m)]
    assert value == before and header["experiment"] == before["experiment"]
    assert header["experiment_sha256"] == submission.experiment_sha256
    assert header["sampling"] == before["sampling"]
    assert len(header["planes"]) == 9


def test_rectangular_aperture_negative_lens_zero_source_and_zero_interiors_are_supported():
    value = envelope()
    value["experiment"]["components"][0] = {"kind": "rectangular_aperture", "id": "slit", "z_m": 0.003,
                                               "width_m": 36e-6, "height_m": 55e-6}
    value["experiment"]["components"][1]["focal_length_m"] = -0.08
    value["experiment"]["source"]["amplitude"] = 0
    value["sampling"]["interior_z_m"] = []
    header, _ = unpack(adapter.simulate_submission(adapter.validate_submission(value)))
    assert len(header["planes"]) == 6
    assert all(plane["norm"] == 0 and plane["transmission_ratio"] is None for plane in header["planes"])


def test_numerical_failure_is_not_confused_with_encoder_failure(monkeypatch):
    submission = adapter.validate_submission(envelope())
    def broken(*args, **kwargs):
        raise ValueError("controlled numerical arithmetic")
    monkeypatch.setattr(adapter, "sample_wave_field", broken)
    with pytest.raises(adapter.NumericalError, match="controlled numerical"):
        adapter.simulate_submission(submission)
    monkeypatch.undo()
    monkeypatch.setattr(adapter, "encode_result", broken)
    with pytest.raises(ValueError, match="controlled numerical") as caught:
        adapter.simulate_submission(submission)
    assert not isinstance(caught.value, adapter.NumericalError)


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}',
                                  b'{"a":1e-999}', b'\xff', b'{"a":'])
def test_strict_json_never_silently_rewrites_nonfinite_or_underflowing_input(raw):
    with pytest.raises(ValueError):
        protocol.strict_json_loads(raw)
