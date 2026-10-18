"""Exact binary W1 samples, stage identities, frame bounds and corrupt results."""

import copy

import numpy as np
import pytest

from apps.virtual_bench import wave_field_adapter as adapter
from apps.virtual_bench import wave_field_protocol as protocol
from ohlab.optics import run_experiment
from ohlab.optics.wave_field import default_interior_positions
from test_virtual_bench_wave_field_adapter import REQUEST_ID, envelope, unpack


def result_for(value=None):
    submission = adapter.validate_submission(envelope() if value is None else value)
    return adapter.sample_wave_field(submission.experiment, interior_z_m=submission.interior_z_m)


def test_frame_exact_layout_endianness_positions_stages_and_full_precision_values():
    result = result_for()
    frame = protocol.encode_result(REQUEST_ID, result)
    header, payload = unpack(frame)
    assert set(header) == {"protocol_version", "message_type", "request_id", "experiment_sha256", "experiment",
                           "sampling", "ordered_section_ids", "planes", "stages", "arrays"}
    assert header["protocol_version"] == 1 and header["message_type"] == "w1_wave_field"
    assert header["request_id"] == REQUEST_ID and header["experiment"] == result.experiment.to_dict()
    assert header["sampling"]["interior_z_m"] == list(result.interior_z_m)
    assert header["ordered_section_ids"] == [plane.id for plane in result.planes]
    assert len(set(header["ordered_section_ids"])) == len(result.planes)
    offset = 0
    expected = [("intensities", result.intensities, "amplitude_unit^2"),
                ("x_m", result.x_m, "m"), ("y_m", result.y_m, "m")]
    for descriptor, (name, values, units) in zip(header["arrays"], expected):
        assert descriptor == {"name": name, "dtype": "float64-le", "order": "C", "shape": list(values.shape),
                              "offset_bytes": offset, "nbytes": values.nbytes, "units": units}
        section = payload[offset:offset+values.nbytes]
        assert section == values.astype("<f8", copy=False).tobytes(order="C")
        actual = np.frombuffer(section, dtype="<f8").reshape(values.shape)
        np.testing.assert_array_equal(actual, values)
        offset += values.nbytes
    assert len(payload) == offset and len(frame) <= protocol.MAX_RESPONSE_BYTES
    for stage, native in zip(header["stages"], result.canonical.stages):
        assert stage == {"selector": native.selector, "z_m": native.z_m, "norm": native.norm,
                         "previous_norm": native.previous_norm, "delta_norm": native.delta_norm,
                         "transmission_ratio": native.transmission_ratio}
    plain = run_experiment(result.experiment, record_fields=())
    assert result.observation.data.tobytes() == plain.observation.data.tobytes()
    assert header["planes"][-1]["norm"] == plain.stages[-1].norm


def test_colocated_event_identities_and_physical_loss_signed_residuals_are_not_collapsed():
    result = result_for()
    header, _ = unpack(protocol.encode_result(REQUEST_ID, result))
    planes = {plane["stage"]: plane for plane in header["planes"] if plane["stage"] != "interior"}
    before, after = planes["before:aperture"], planes["after:aperture"]
    assert before["z_m"] == after["z_m"] and before["id"] != after["id"]
    assert after["norm"] < before["norm"] and after["delta_norm"] < 0
    assert after["transmission_ratio"] == after["norm"] / before["norm"]
    assert planes["before:lens"]["id"] != planes["after:lens"]["id"]
    assert all(plane["comparison"] == ("upstream_anchor" if plane["stage"] == "interior" else "previous_stage")
               for plane in header["planes"])


@pytest.mark.parametrize("fault", ["negative", "nonfinite", "float32", "shape", "x_axis", "y_axis",
                                  "identity", "position", "anchor", "collapse", "max", "axis_sample",
                                  "norm", "delta", "ratio", "comparison", "terminal"])
def test_encoder_revalidates_result_even_if_reversible_readonly_storage_is_tampered(fault):
    result = result_for()
    if fault in {"negative", "nonfinite", "terminal"}:
        values = result.intensities.copy()
        values[(-1 if fault == "terminal" else 0), 0, 0] = {"negative": -1.0, "nonfinite": np.nan, "terminal": 123.0}[fault]
        object.__setattr__(result, "intensities", values)
    elif fault in {"float32", "shape"}:
        object.__setattr__(result, "intensities", result.intensities.astype(np.float32) if fault == "float32" else result.intensities[:, :-1])
    elif fault in {"x_axis", "y_axis"}:
        axis = "x_m" if fault == "x_axis" else "y_m"
        object.__setattr__(result, axis, getattr(result, axis)[::-1].copy())
    else:
        rows = list(result.planes)
        index = 1 if fault in {"anchor", "delta", "ratio", "comparison"} else 0
        changes = {"identity": {"id": "section:invented"}, "position": {"z_m": 0.001},
                   "anchor": {"anchor_selector": "after:lens"}, "collapse": {"id": rows[2].id},
                   "max": {"max_intensity": 123.0}, "axis_sample": {"on_axis_intensity": 123.0},
                   "norm": {"norm": 123.0}, "delta": {"delta_norm": 0.5},
                   "ratio": {"transmission_ratio": 0.5}, "comparison": {"comparison": "previous_stage"}}
        rows[index] = copy.copy(rows[index])
        for key, value in changes[fault].items():
            object.__setattr__(rows[index], key, value)
        object.__setattr__(result, "planes", tuple(rows))
    with pytest.raises((ValueError, TypeError)):
        protocol.encode_result(REQUEST_ID, result)


def test_fixed_128_by_128_and_25_section_transport_budget():
    value = envelope(ny=128, nx=128)
    submission = adapter.validate_submission(value)
    positions = default_interior_positions(submission.experiment)
    result = adapter.sample_wave_field(submission.experiment, interior_z_m=positions)
    frame = protocol.encode_result(REQUEST_ID, result)
    header, payload = unpack(frame)
    assert len(header["planes"]) == 25 and len(payload) == 3_276_800 + 2_048
    assert protocol.MAX_RESPONSE_BYTES == 16 + 65_536 + 3_276_800 + 2_048
    assert len(frame) <= protocol.MAX_RESPONSE_BYTES


def test_header_bound_is_enforced_before_publishing(monkeypatch):
    monkeypatch.setattr(protocol, "MAX_HEADER_BYTES", 1)
    with pytest.raises(ValueError, match="header"):
        protocol.encode_result(REQUEST_ID, result_for())


def test_complete_frame_bound_is_enforced_before_publishing(monkeypatch):
    monkeypatch.setattr(protocol, "MAX_RESPONSE_BYTES", 16)
    with pytest.raises(ValueError, match="result exceeds"):
        protocol.encode_result(REQUEST_ID, result_for())
