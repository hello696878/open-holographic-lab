"""Independent framing/limit readback and malformed validated-data rejection."""

from copy import deepcopy
import json

import numpy as np
import pytest

from apps.virtual_bench import polarization_adapter as adapter
from apps.virtual_bench import polarization_protocol as protocol
from test_virtual_bench_polarization_adapter import (REQUEST_ID, envelope, output,
                                                     polarizer, sweep_envelope, unpack)


def values(value=None):
    header, arrays = output(envelope() if value is None else value)
    return header, {name: array.copy() for name, array in arrays.items()}


def encode(header, arrays):
    return protocol.encode_result(REQUEST_ID, header["experiment"], header["stages"], **arrays)


@pytest.mark.parametrize("shape", [(1, 1), (3, 4), (64, 64), (128, 128)])
def test_exact_framing_roles_endian_contiguity_padding_and_caps(shape):
    header, arrays = values(envelope(ny=shape[0], nx=shape[1]))
    frame = encode(header, arrays)
    magic, length, reserved = protocol.PREAMBLE.unpack_from(frame)
    assert magic == b"OHLABPL\0" and reserved == 0 and protocol.PREAMBLE.size == 16
    padded_length = length + (-length % 8)
    assert frame[16+length:16+padded_length] == b"\0" * (-length % 8)
    assert padded_length <= protocol.MAX_HEADER_BYTES
    expected_bytes = 8 * (2*shape[0]*shape[1] + shape[1] + shape[0])
    assert len(frame) == 16+padded_length+expected_bytes <= protocol.MAX_RESPONSE_BYTES
    assert expected_bytes <= protocol.MAX_PAYLOAD_BYTES
    position = 0
    for index, (descriptor, name) in enumerate(zip(header["arrays"], ("incident_intensity", "final_intensity", "x_m", "y_m"))):
        assert set(descriptor) == {"name", "role", "stage_id", "dtype", "order", "shape", "offset_bytes", "nbytes", "units"}
        assert descriptor["name"] == name and descriptor["offset_bytes"] == position
        assert descriptor["dtype"] == "float64-le" and descriptor["order"] == "C"
        assert descriptor["role"] == ("intensity" if index < 2 else "coordinate")
        assert descriptor["stage_id"] == ("input", "analyzer", None, None)[index]
        start = 16+padded_length+position
        assert frame[start:start+descriptor["nbytes"]] == arrays[name].astype("<f8").tobytes(order="C")
        position += descriptor["nbytes"]
    assert position == expected_bytes
    assert protocol.MAX_RESPONSE_BYTES == 16+protocol.MAX_HEADER_BYTES+protocol.MAX_PAYLOAD_BYTES == 280592


def test_result_fields_digest_and_fixed_readout_are_complete():
    header, arrays = values()
    assert set(header) == {"protocol_version", "message_type", "request_id", "experiment_sha256", "experiment",
                            "ordered_stage_ids", "stages", "readout", "arrays", "intensity_max"}
    assert header["message_type"] == "polarization_result"
    assert header["experiment_sha256"] == protocol.experiment_digest(header["experiment"])
    assert header["intensity_max"] == [arrays["incident_intensity"].max(), arrays["final_intensity"].max()]
    changed = deepcopy(header["experiment"])
    changed["readout"]["column"] = 0
    assert protocol.experiment_digest(changed) != header["experiment_sha256"]
    assert b"OHLABV1\0" != protocol.MAGIC != b"OHLAB2P\0"


@pytest.mark.parametrize("mutation", [
    lambda h: h["stages"][-1].update(stage_id="wrong"),
    lambda h: h["stages"][-1].update(kind="linear_retarder"),
    lambda h: h["stages"][-1].update(norm=True),
    lambda h: h["stages"][-1].update(previous_norm=False),
    lambda h: h["stages"][-1].update(delta_norm=False),
    lambda h: h["stages"][-1].update(incident_transmission_ratio=True),
    lambda h: h["stages"][-1].update(adjacent_transmission_ratio=float("nan")),
    lambda h: h["stages"][0].update(incident_transmission_ratio=.5),
    lambda h: h["stages"][0].update(previous_norm=0),
    lambda h: h["stages"][-1]["sample"]["x"].update(im=float("inf")),
    lambda h: h["stages"][-1]["sample"]["y"].update(re=False),
    lambda h: h["stages"][-1]["sample"].update(extra=0),
    lambda h: h["experiment"]["readout"].update(column=4),
    lambda h: h["experiment"]["readout"].update(row=True),
])
def test_late_malformed_stage_rejects_whole_result(mutation):
    header, arrays = values()
    mutation(header)
    with pytest.raises((ValueError, TypeError)):
        encode(header, arrays)


@pytest.mark.parametrize("mutation", [
    lambda a: a.update(final_intensity=a["final_intensity"].astype(np.float32)),
    lambda a: a.update(final_intensity=a["final_intensity"][:, :-1]),
    lambda a: a["final_intensity"].__setitem__((0, 0), -1.),
    lambda a: a["incident_intensity"].__setitem__((0, 0), float("inf")),
    lambda a: a["x_m"].__setitem__(0, float("nan")),
])
def test_unusable_transport_arrays_fail_before_frame_publication(mutation):
    header, arrays = values(); mutation(arrays)
    with pytest.raises(ValueError): encode(header, arrays)


def test_tiny_nonzero_selected_complex_sample_survives_zero_pixel_intensity_fixture():
    header, arrays = values(envelope(elements=[]))
    readout = header["experiment"]["readout"]
    # Bounded transport fixture: usable field norm elsewhere, tiny selected pair.
    # This is not a new production source or a scientific accuracy claim.
    header["stages"][0]["sample"] = {"x": {"re": 1e-200, "im": -2e-200}, "y": {"re": 0., "im": 0.}}
    for name in ("incident_intensity", "final_intensity"):
        arrays[name][readout["row"], readout["column"]] = 0.
    restored, payload = unpack(encode(header, arrays))
    assert restored["stages"][0]["sample"]["x"] == {"re": 1e-200, "im": -2e-200}
    assert payload["final_intensity"][readout["row"], readout["column"]] == 0.
    assert restored["stages"][0]["norm"] > 0


def test_header_payload_and_sweep_caps_fail_closed(monkeypatch):
    header, arrays = values()
    monkeypatch.setattr(protocol, "MAX_HEADER_BYTES", 16)
    with pytest.raises(ValueError, match="header"): encode(header, arrays)
    monkeypatch.setattr(protocol, "MAX_HEADER_BYTES", 16384)
    monkeypatch.setattr(protocol, "MAX_PAYLOAD_BYTES", 1)
    with pytest.raises(ValueError, match="payload"): encode(header, arrays)
    monkeypatch.setattr(protocol, "MAX_PAYLOAD_BYTES", 264192)
    monkeypatch.setattr(protocol, "MAX_RESPONSE_BYTES", 16)
    with pytest.raises(ValueError, match="frame"): encode(header, arrays)
    monkeypatch.setattr(protocol, "MAX_SWEEP_RESPONSE_BYTES", 2)
    submission = adapter.validate_sweep_submission(sweep_envelope())
    with pytest.raises(ValueError, match="sweep response"): adapter.sweep_submission(submission)


def test_sweep_exact_schema_and_complete_prefix_integrity():
    submission = adapter.validate_sweep_submission(sweep_envelope())
    value = json.loads(adapter.sweep_submission(submission).body)
    assert set(value) == {"protocol_version", "message_type", "status", "request_id", "experiment_sha256",
            "sweep_sha256", "experiment", "selected_element_id", "angles_rad", "ordered_stage_ids",
            "requested_count", "rows", "completed_count", "failed_index", "error"}
    assert value["requested_count"] == value["completed_count"] == 13
    assert value["failed_index"] is value["error"] is None
    assert value["sweep_sha256"] == protocol.sweep_digest(submission.experiment.to_dict(), "analyzer", protocol.ANGLES_RAD)
    for row in value["rows"]:
        assert set(row) == {"index", "axis_angle_rad", "stages", "final_norm", "incident_transmission_ratio", "total_delta"}
        assert all(set(stage) == protocol.STAGE_SCALAR_KEYS for stage in row["stages"])
    rows = value["rows"]
    for mutation in (lambda r: r[0].update(index=True), lambda r: r[6].update(axis_angle_rad=False),
                     lambda r: r[-1].update(final_norm=False), lambda r: r[-1].update(total_delta=False),
                     lambda r: r[-1].update(incident_transmission_ratio=True), lambda r: r[-1].update(extra=0)):
        corrupted = deepcopy(rows); mutation(corrupted)
        with pytest.raises((ValueError, TypeError)):
            protocol.encode_sweep_reply(REQUEST_ID, submission.experiment.to_dict(), "analyzer", protocol.ANGLES_RAD, corrupted)
    with pytest.raises(ValueError, match="complete"):
        protocol.encode_sweep_reply(REQUEST_ID, submission.experiment.to_dict(), "analyzer", protocol.ANGLES_RAD, rows[:12])
    with pytest.raises(ValueError, match="prefix"):
        protocol.encode_sweep_reply(REQUEST_ID, submission.experiment.to_dict(), "analyzer", protocol.ANGLES_RAD, rows[:3],
                          failed_index=4, error={"code": "numerical_failure", "message": "failed"}, status_code=422)


@pytest.mark.parametrize("replacement", [False, None, "0", []], ids=["bool-zero", "null", "string", "list"])
def test_standalone_sweep_encoder_rejects_non_real_angle_values(replacement):
    submission = adapter.validate_sweep_submission(sweep_envelope())
    rows = json.loads(adapter.sweep_submission(submission).body)["rows"]
    angles = list(protocol.ANGLES_RAD)
    angles[6] = replacement
    with pytest.raises((TypeError, ValueError)):
        protocol.encode_sweep_reply(REQUEST_ID, submission.experiment.to_dict(), "analyzer", tuple(angles), rows)
