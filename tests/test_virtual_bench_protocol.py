"""Independent struct assertions for V1 encoder: no production decoder oracle."""

import json
import struct

import numpy as np
import pytest

from apps.virtual_bench import protocol
from ohlab import ComplexField
from ohlab.optics import SequentialExperiment, SequentialResult, StageRecord

REQUEST_ID = "12345678-1234-4234-8234-123456789abc"


def synthetic_result(ny=3, nx=4):
    experiment = SequentialExperiment.from_dict({
        "schema_version": 1, "model_contract": "v0_aligned_scalar_forward_v1",
        "wavelength_m": 633e-9, "grid": {"ny": ny, "nx": nx, "dy": 5e-6, "dx": 2e-6},
        "source": {"kind": "uniform", "amplitude": 1.0, "phase_rad": 0.0},
        "components": [], "observation": {"id": "screen", "z_m": 0.0}})
    # This is an explicit synthetic terminal field, not a claimed optical solve.
    values = np.arange(1, ny * nx + 1, dtype=float).reshape(ny, nx).astype(complex)
    norm = float(sum(i*i for i in range(1, ny*nx+1))) * 2e-6 * 5e-6
    field = ComplexField(data=values, grid=experiment.grid, wavelength_m=633e-9)
    return SequentialResult(experiment=experiment, observation=field,
                            stages=(StageRecord(selector="source", z_m=0, norm=norm, previous_norm=None),
                                    StageRecord(selector="observation", z_m=0, norm=norm, previous_norm=norm)),
                            recorded_fields=())


@pytest.mark.parametrize("ny,nx,x_values,y_values", [
    (3, 4, [-4e-6, -2e-6, 0, 2e-6], [-5e-6, 0, 5e-6]),
    (2, 5, [-4e-6, -2e-6, 0, 2e-6, 4e-6], [-5e-6, 0]),
])
def test_independent_preamble_header_padding_offsets_bytes_and_mixed_parity(ny, nx, x_values, y_values):
    frame = protocol.encode_result(REQUEST_ID, synthetic_result(ny, nx))
    assert frame[:8] == bytes([79, 72, 76, 65, 66, 86, 49, 0])
    length, reserved = struct.unpack("<II", frame[8:16])
    assert 0 < length <= 16384 and reserved == 0
    raw_header = frame[16:16+length]
    header = json.loads(raw_header.decode("utf-8", errors="strict"))
    padded_length = (length + 7) // 8 * 8
    assert frame[16+length:16+padded_length] == bytes(padded_length-length)
    assert set(header) == {"protocol_version", "request_id", "experiment_sha256", "experiment",
                           "stages", "arrays", "intensity_max"}
    assert header["protocol_version"] == 1 and header["request_id"] == REQUEST_ID
    assert len(header["experiment_sha256"]) == 64
    descriptors = header["arrays"]
    assert descriptors == [
        {"name": "intensity", "dtype": "float64-le", "order": "C", "shape": [ny,nx],
         "offset_bytes": 0, "nbytes": 8*ny*nx, "units": "amplitude_unit^2"},
        {"name": "x_m", "dtype": "float64-le", "order": "C", "shape": [nx],
         "offset_bytes": 8*ny*nx, "nbytes": 8*nx, "units": "m"},
        {"name": "y_m", "dtype": "float64-le", "order": "C", "shape": [ny],
         "offset_bytes": 8*ny*nx+8*nx, "nbytes": 8*ny, "units": "m"},
    ]
    start = 16 + padded_length
    expected_payload = (struct.pack(f"<{ny*nx}d", *(i*i for i in range(1,ny*nx+1))) +
                        struct.pack(f"<{nx}d", *x_values) + struct.pack(f"<{ny}d", *y_values))
    assert frame[start:] == expected_payload  # Exact endian/order/no-gap/no-tail claim.
    assert header["intensity_max"] == (ny*nx)**2
    for s in header["stages"]:
        assert set(s) == {"selector", "z_m", "norm", "previous_norm", "delta_norm", "transmission_ratio"}
    assert header["stages"][0]["previous_norm"] is None
    assert header["stages"][0]["delta_norm"] is None
    assert header["stages"][0]["transmission_ratio"] is None


@pytest.mark.parametrize("kind", ["negative", "nonfinite", "shape", "dtype"])
def test_encoder_rejects_invalid_actual_intensity_before_publication(monkeypatch, kind):
    result = synthetic_result()
    invalid = np.ones((3, 4), dtype=float)
    if kind == "negative": invalid[0,0] = -1
    if kind == "nonfinite": invalid[0,0] = float("nan")
    if kind == "shape": invalid = invalid.T
    if kind == "dtype": invalid = invalid.astype("float32")
    monkeypatch.setattr(ComplexField, "intensity", property(lambda _: invalid))
    with pytest.raises(ValueError):
        protocol.encode_result(REQUEST_ID, result)


def test_encoder_caps_checked_and_no_silent_header_or_response_truncation(monkeypatch):
    result = synthetic_result()
    monkeypatch.setattr(protocol, "MAX_HEADER_BYTES", 10)
    with pytest.raises(ValueError, match="header"):
        protocol.encode_result(REQUEST_ID, result)
    monkeypatch.setattr(protocol, "MAX_HEADER_BYTES", 16384)
    monkeypatch.setattr(protocol, "MAX_RESPONSE_BYTES", 20)
    with pytest.raises(ValueError, match="frame"):
        protocol.encode_result(REQUEST_ID, result)


@pytest.mark.parametrize("value", [None, 1, True, "", REQUEST_ID.upper(),
    "12345678-1234-1234-8234-123456789abc", "{"+REQUEST_ID+"}", REQUEST_ID.replace("-", "")])
def test_request_identity_is_canonical_uuid4(value):
    with pytest.raises((TypeError, ValueError)):
        protocol.validate_request_id(value)


def test_encoder_does_not_mutate_or_make_scientific_arrays_writable():
    result = synthetic_result()
    before = result.observation.data.tobytes()
    first = protocol.encode_result(REQUEST_ID, result)
    second = protocol.encode_result(REQUEST_ID, result)
    assert first == second
    assert result.observation.data.tobytes() == before
    assert not result.observation.data.flags.writeable


def test_actual_maximum_grid_frame_fits_reviewed_response_limit():
    result = synthetic_result(512, 512)
    frame = protocol.encode_result(REQUEST_ID, result)
    header_length = struct.unpack("<I", frame[8:12])[0]
    payload_length = 8*(512*512+512+512)
    assert len(frame) == 16 + (header_length+7)//8*8 + payload_length
    assert len(frame) <= 2_359_296
