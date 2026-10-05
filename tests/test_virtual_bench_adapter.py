"""V1 limits/ownership and genuine public-V0 integration, without a server."""

from dataclasses import FrozenInstanceError
import hashlib
import json
import struct

import numpy as np
import pytest

from apps.virtual_bench import adapter
from ohlab.optics import SequentialExperiment, run_experiment

REQUEST_ID = "12345678-1234-4234-8234-123456789abc"


def envelope(kind="free", *, amplitude=1.0, ny=9, nx=10):
    components = []
    if kind == "aperture_lens":
        components.append({"id": "aperture", "kind": "circular_aperture",
                           "z_m": 0.0, "radius_m": 16e-6})
    if kind in ("lens", "aperture_lens"):
        components.append({"id": "lens", "kind": "thin_lens", "z_m": 0.0,
                           "focal_length_m": 20e-3})
    return {"request_id": REQUEST_ID, "experiment": {
        "schema_version": 1, "model_contract": "v0_aligned_scalar_forward_v1",
        "wavelength_m": 633e-9,
        "grid": {"ny": ny, "nx": nx, "dy": 5e-6, "dx": 4e-6},
        "source": {"kind": "gaussian", "amplitude": amplitude, "phase_rad": 0.0,
                   "waist_radius_m": 25e-6, "waist_z_m": 0.0,
                   "center_x_m": 3e-6, "center_y_m": -4e-6},
        "components": components, "observation": {"id": "screen", "z_m": 20e-3},
    }}


def unpack(frame):
    magic, length, reserved = struct.unpack("<8sII", frame[:16])
    assert magic == b"OHLABV1\0" and reserved == 0
    header = json.loads(frame[16:16 + length].decode("utf-8"))
    start = 16 + (length + 7) // 8 * 8
    payload = frame[start:]
    return header, {item["name"]: np.frombuffer(
        payload[item["offset_bytes"]:item["offset_bytes"] + item["nbytes"]],
        dtype="<f8").reshape(item["shape"]) for item in header["arrays"]}


@pytest.mark.parametrize("kind", ["free", "lens", "aperture_lens"])
def test_simulation_matches_separate_direct_v0_call_and_calls_once(kind, monkeypatch):
    payload = envelope(kind)
    expected = run_experiment(SequentialExperiment.from_dict(payload["experiment"]), record_fields=())
    calls = []
    original = adapter.run_experiment

    def counted(experiment, *, record_fields):
        calls.append((experiment, record_fields))
        return original(experiment, record_fields=record_fields)

    monkeypatch.setattr(adapter, "run_experiment", counted)
    submitted = adapter.validate_submission(payload)
    assert calls == []  # Validation is independent of numerical execution.
    header, arrays = unpack(adapter.simulate_submission(submitted))
    assert calls == [(submitted.experiment, ())]
    assert header["experiment"] == expected.experiment.to_dict()
    assert arrays["intensity"].tobytes() == expected.observation.intensity.tobytes()
    assert arrays["x_m"].tobytes() == expected.experiment.grid.x.tobytes()
    assert arrays["y_m"].tobytes() == expected.experiment.grid.y.tobytes()
    assert header["stages"] == [{"selector": s.selector, "z_m": s.z_m, "norm": s.norm,
                                  "previous_norm": s.previous_norm, "delta_norm": s.delta_norm,
                                  "transmission_ratio": s.transmission_ratio} for s in expected.stages]


def test_owned_submission_and_hash_do_not_follow_mutable_input():
    payload = envelope("aperture_lens")
    submitted = adapter.validate_submission(payload)
    scientific = submitted.experiment.to_dict()
    expected_hash = hashlib.sha256(json.dumps(scientific, sort_keys=True,
        separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    assert submitted.experiment_sha256 == expected_hash
    payload["experiment"]["source"]["amplitude"] = 7
    payload["experiment"]["grid"]["nx"] = 30
    payload["experiment"]["components"][0]["radius_m"] = 1e-9
    assert submitted.experiment.to_dict() == scientific
    assert submitted.experiment_sha256 == expected_hash
    with pytest.raises(FrozenInstanceError):
        submitted.request_id = REQUEST_ID


@pytest.mark.parametrize("axis,value,error", [
    ("nx", True, TypeError), ("ny", 3.0, TypeError), ("nx", "3", TypeError),
    ("ny", 0, ValueError), ("nx", 513, ValueError), ("ny", 10**100, ValueError),
])
def test_cheap_dimension_rejections_happen_before_v0_construction(axis, value, error, monkeypatch):
    payload = envelope()
    payload["experiment"]["grid"][axis] = value
    monkeypatch.setattr(adapter.SequentialExperiment, "from_dict", lambda _: pytest.fail("V0 constructor reached"))
    with pytest.raises(error, match=axis):
        adapter.validate_submission(payload)


def test_cheap_component_rejection_precedes_v0(monkeypatch):
    payload = envelope()
    payload["experiment"]["components"] = [{}] * 9
    monkeypatch.setattr(adapter.SequentialExperiment, "from_dict", lambda _: pytest.fail("V0 constructor reached"))
    with pytest.raises(ValueError, match="at most 8"):
        adapter.validate_submission(payload)


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(extra=1), lambda d: d.pop("request_id"),
    lambda d: d.update(request_id=True),
    lambda d: d.update(request_id="12345678-1234-1234-8234-123456789abc"),
    lambda d: d.update(request_id=REQUEST_ID.upper()),
    lambda d: d["experiment"].update(extra=True),
    lambda d: d["experiment"]["source"].update(amplitude=-1),
    lambda d: d["experiment"]["source"].update(center_x_m=float("inf")),
    lambda d: d["experiment"]["grid"].update(dx=False),
])
def test_exact_envelope_and_existing_v0_validation(mutation):
    payload = envelope()
    mutation(payload)
    with pytest.raises((ValueError, TypeError)):
        adapter.validate_submission(payload)


def test_preserves_colocation_and_rejects_order_instead_of_sorting():
    payload = envelope("aperture_lens")
    submitted = adapter.validate_submission(payload)
    assert [c.id for c in submitted.experiment.components] == ["aperture", "lens"]
    payload["experiment"]["components"][0]["z_m"] = 1e-3
    with pytest.raises(ValueError, match="previous"):
        adapter.validate_submission(payload)


def test_dark_source_is_real_zero_with_null_incident_ratios():
    header, arrays = unpack(adapter.simulate_submission(adapter.validate_submission(envelope("aperture_lens", amplitude=0))))
    assert np.count_nonzero(arrays["intensity"]) == 0
    assert header["intensity_max"] == 0
    assert all(s["norm"] == 0 and s["transmission_ratio"] is None for s in header["stages"])
    assert header["stages"][0]["delta_norm"] is None
    assert all(s["delta_norm"] == 0 for s in header["stages"][1:])


@pytest.mark.parametrize("amplitude", [1e-250, 1e200])
def test_existing_v0_unusable_arithmetic_is_reported_without_clamping(amplitude):
    submitted = adapter.validate_submission(envelope(amplitude=amplitude))
    assert submitted.experiment.source.amplitude == amplitude
    with pytest.raises(adapter.NumericalError, match="norm"):
        adapter.simulate_submission(submitted)


def test_real_parameter_change_and_loss_are_not_ignored_or_normalized():
    free_header, free = unpack(adapter.simulate_submission(adapter.validate_submission(envelope())))
    lens_header, lens = unpack(adapter.simulate_submission(adapter.validate_submission(envelope("lens"))))
    clipped_header, clipped = unpack(adapter.simulate_submission(adapter.validate_submission(envelope("aperture_lens"))))
    assert np.max(np.abs(free["intensity"] - lens["intensity"])) > 1e-3
    assert clipped_header["stages"][-1]["norm"] < lens_header["stages"][-1]["norm"]
    # Aperture loss constrains full-window norm, not each diffracted peak.
    assert np.max(np.abs(clipped["intensity"] - lens["intensity"])) > 1e-3
    assert free_header["experiment"] != lens_header["experiment"]


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":{"z":1,"z":2}}',
                                      b'{"a":NaN}', b'{"a":Infinity}', b'{"a":-Infinity}',
                                      b'\xff', b'"unterminated', b'[' * 3000, b' ' * 32769,
                                      b'{"a":1e999}', b'{"a":-1e999}'],
                         ids=["duplicate", "nested_duplicate", "nan", "inf", "negative_inf",
                              "invalid_utf8", "incomplete", "deep", "over_limit",
                              "overflow_number", "negative_overflow_number"])
def test_strict_json_rejects_ambiguous_nonfinite_or_unbounded_input(raw):
    with pytest.raises(ValueError):
        adapter.strict_json_loads(raw)


def test_strict_json_accepts_exact_unicode_and_scalars_before_envelope_validation():
    assert adapter.strict_json_loads('{"label":"觀察"}'.encode()) == {"label": "觀察"}
    for raw in (b'null', b'[]', b'1', b'"x"'):
        with pytest.raises(TypeError):
            adapter.validate_submission(adapter.strict_json_loads(raw))
