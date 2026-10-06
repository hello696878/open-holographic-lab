"""Independent byte/descriptor assertions for the bounded V2b encoder."""

import hashlib
import json
import struct

import numpy as np
import pytest

from apps.virtual_bench import two_path_adapter as adapter, two_path_protocol as protocol
from apps.virtual_bench import protocol as legacy
from ohlab import ComplexField, SamplingGrid
from ohlab.optics.interference import TwoArmNorms, TwoArmResult, TwoArmSpec

REQUEST_ID = "12345678-1234-4234-8234-123456789abc"


def synthetic_result(ny=3, nx=4):
    """Port-specific asymmetric transport fixture, not a claimed optical solve."""
    grid = SamplingGrid(ny=ny, nx=nx, dy=5e-6, dx=2e-6)
    first = np.arange(1, ny * nx + 1, dtype=float).reshape(ny, nx)
    second = 3 + 2 * first[::-1, ::-1]
    fields = tuple(ComplexField(data=values.astype(complex), grid=grid, wavelength_m=633e-9)
                   for values in (first, second))
    norms = tuple(float(np.sum(values**2, dtype=np.float64)) * grid.dx * grid.dy for values in (first, second))
    records = TwoArmNorms(inputs=(sum(norms), 0.0), split=norms,
                          propagated=norms, combiner=norms, outputs=norms)
    spec = TwoArmSpec(arm_0_distance_m=0, arm_1_distance_m=0, relative_phase_rad=.37)
    result = TwoArmResult(spec=spec, outputs=fields, norms=records)
    scientific = {"wavelength_m": 633e-9, "grid": grid.to_dict(),
                  "source": {"kind": "uniform", "amplitude": 1.0, "phase_rad": 0.0},
                  "two_arm_spec": {"arm_0_distance_m": 0.0, "arm_1_distance_m": 0.0,
                                   "relative_phase_rad": .37}}
    return result, scientific, first, second


@pytest.mark.parametrize("ny,nx", [(3, 4), (2, 5), (6, 3)])
def test_independent_ordered_payload_identity_endian_padding_axes(ny, nx):
    result, scientific, first, second = synthetic_result(ny, nx)
    frame = protocol.encode_result(REQUEST_ID, scientific, result)
    assert frame[:8] == bytes([79, 72, 76, 65, 66, 50, 80, 0])
    length, reserved = struct.unpack("<II", frame[8:16])
    assert 0 < length <= 16384 and reserved == 0
    header = json.loads(frame[16:16+length].decode("utf-8", errors="strict"))
    padded_length = (length+7)//8*8
    assert frame[16+length:16+padded_length] == bytes(padded_length-length)
    assert set(header) == {"protocol_version", "message_type", "request_id", "experiment_sha256",
                           "experiment", "ports", "norms", "diagnostics", "arrays", "intensity_max"}
    assert header["protocol_version"] == 1 and header["message_type"] == "two_path_result"
    assert header["request_id"] == REQUEST_ID and header["experiment"] == scientific
    expected_digest = hashlib.sha256(json.dumps(scientific, sort_keys=True, separators=(",", ":"),
                                                ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    assert header["experiment_sha256"] == expected_digest
    assert header["ports"] == ["port_0", "port_1"]
    intensity_bytes = 8*ny*nx
    expected_descriptors = []
    for name, role, port_id, shape, offset, nbytes, units in [
        ("intensity_port_0", "intensity", "port_0", [ny,nx], 0, intensity_bytes, "amplitude_unit^2"),
        ("intensity_port_1", "intensity", "port_1", [ny,nx], intensity_bytes, intensity_bytes, "amplitude_unit^2"),
        ("x_m", "coordinate", None, [nx], 2*intensity_bytes, 8*nx, "m"),
        ("y_m", "coordinate", None, [ny], 2*intensity_bytes+8*nx, 8*ny, "m"),
    ]:
        expected_descriptors.append({"name": name, "role": role, "port_id": port_id,
                                     "dtype": "float64-le", "order": "C", "shape": shape,
                                     "offset_bytes": offset, "nbytes": nbytes, "units": units})
    assert header["arrays"] == expected_descriptors
    expected_payload = (struct.pack(f"<{ny*nx}d", *(v*v for v in first.flat)) +
                        struct.pack(f"<{ny*nx}d", *(v*v for v in second.flat)) +
                        struct.pack(f"<{nx}d", *((c-nx//2)*2e-6 for c in range(nx))) +
                        struct.pack(f"<{ny}d", *((r-ny//2)*5e-6 for r in range(ny))))
    assert frame[16+padded_length:] == expected_payload
    assert header["intensity_max"] == [float(first.max()**2), float(second.max()**2)]
    assert set(header["norms"]) == {"inputs", "split", "propagated", "combiner", "outputs"}
    assert all(len(pair) == 2 for pair in header["norms"].values())


@pytest.mark.parametrize("kind", ["negative", "nonfinite", "shape", "dtype"])
def test_invalid_intensity_never_publishes_a_partial_frame(monkeypatch, kind):
    result, scientific, _, _ = synthetic_result()
    invalid = np.ones((3,4), dtype=float)
    if kind == "negative": invalid[0,0] = -1
    if kind == "nonfinite": invalid[0,0] = float("nan")
    if kind == "shape": invalid = invalid.T
    if kind == "dtype": invalid = invalid.astype("float32")
    monkeypatch.setattr(ComplexField, "intensity", property(lambda _: invalid))
    with pytest.raises(ValueError):
        protocol.encode_result(REQUEST_ID, scientific, result)


def test_exact_maximum_complete_frame_bound_and_legacy_cap_unchanged():
    value = {"protocol_version": 1, "message_type": "two_path_submission", "request_id": REQUEST_ID,
             "experiment": {"wavelength_m": 633e-9, "grid": {"ny": 512, "nx": 512, "dy": 4e-6, "dx": 4e-6},
                            "source": {"kind": "uniform", "amplitude": 1.0, "phase_rad": 0.0},
                            "two_arm_spec": {"arm_0_distance_m": 0.0, "arm_1_distance_m": 0.0,
                                             "relative_phase_rad": .37}}}
    frame = adapter.simulate_submission(adapter.validate_submission(value))
    length = struct.unpack("<I", frame[8:12])[0]
    payload = 8*(2*512*512+512+512)
    assert payload == 4_202_496
    assert len(frame) == 16+(length+7)//8*8+payload
    assert protocol.MAX_RESPONSE_BYTES == 16+16384+payload == 4_218_896
    assert len(frame) <= protocol.MAX_RESPONSE_BYTES
    assert len(frame) > legacy.MAX_RESPONSE_BYTES == 2_359_296
    assert protocol.MAGIC != legacy.MAGIC


def test_caps_reject_without_truncation_and_input_storage_unchanged(monkeypatch):
    result, scientific, _, _ = synthetic_result()
    before = [field.data.tobytes() for field in result.outputs]
    first = protocol.encode_result(REQUEST_ID, scientific, result)
    assert protocol.encode_result(REQUEST_ID, scientific, result) == first
    assert [field.data.tobytes() for field in result.outputs] == before
    assert all(not field.data.flags.writeable for field in result.outputs)
    monkeypatch.setattr(protocol, "MAX_HEADER_BYTES", 10)
    with pytest.raises(ValueError, match="header"):
        protocol.encode_result(REQUEST_ID, scientific, result)
    monkeypatch.setattr(protocol, "MAX_HEADER_BYTES", 16384)
    monkeypatch.setattr(protocol, "MAX_RESPONSE_BYTES", 20)
    with pytest.raises(ValueError, match="frame"):
        protocol.encode_result(REQUEST_ID, scientific, result)


def test_scalar_sweep_has_exact_typed_identity_keys_and_no_arrays():
    result, scientific, _, _ = synthetic_result()
    fixed = {**{name: scientific[name] for name in ("wavelength_m", "grid", "source")},
             "arm_0_distance_m": 0.0, "arm_1_distance_m": 0.0}
    rows = [protocol.row_from_result(index, phase, result) for index, phase in enumerate(protocol.PHASES_RAD)]
    reply = protocol.encode_sweep_reply(REQUEST_ID, fixed, protocol.PHASES_RAD, rows)
    body = json.loads(reply.body)
    assert set(body) == {"protocol_version", "message_type", "request_id", "fixed_experiment_sha256",
                         "fixed_experiment", "phases_rad", "status", "requested_count", "completed_count",
                         "failed_index", "rows", "error"}
    assert body["message_type"] == "two_path_sweep_result" and "arrays" not in body
    expected_digest = hashlib.sha256(json.dumps({"fixed_experiment": fixed, "phases_rad": protocol.PHASES_RAD},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    assert body["fixed_experiment_sha256"] == expected_digest
    assert len(reply.body) <= 65536 and reply.status_code == 200
    assert set(rows[0]) == {"index", "phase_rad", "input_norm", "output_norms", "output_fractions",
                            "total_output_ratio", "split_delta", "propagation_delta", "phase_delta",
                            "recombination_delta", "total_delta"}
    failed = protocol.encode_sweep_reply(REQUEST_ID, fixed, protocol.PHASES_RAD, rows[:2], failed_index=2,
                                        error={"code": "numerical_failure", "message": "controlled"}, status_code=422)
    assert json.loads(failed.body)["status"] == "failed" and failed.status_code == 422
    with pytest.raises(ValueError, match="all 17"):
        protocol.encode_sweep_reply(REQUEST_ID, fixed, protocol.PHASES_RAD, rows[:2])
    with pytest.raises(ValueError, match="inconsistent"):
        protocol.encode_sweep_reply(REQUEST_ID, fixed, protocol.PHASES_RAD, rows[:2], failed_index=3,
                                   error={"code": "failure", "message": "controlled"}, status_code=422)
    with pytest.raises(ValueError, match="Out of range"):
        bad = [{**row, "input_norm": float("nan")} for row in rows]
        protocol.encode_sweep_reply(REQUEST_ID, fixed, protocol.PHASES_RAD, bad)
