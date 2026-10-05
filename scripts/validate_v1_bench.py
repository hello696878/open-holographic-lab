"""Independent V1 HTTP/float64 evidence using unchanged public V0 computation.

This writes transient acceptance evidence, not an experiment archive/replay
schema. Run from the repository root with the existing project interpreter.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import http.client
import json
from pathlib import Path
import re
import struct
import sys
import time
import uuid

import numpy as np
import ohlab.optics as optics
from ohlab.optics import SequentialExperiment, run_experiment

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:8510"
MAX_RESPONSE = 2_359_296


def fixture_specs() -> dict[str, dict[str, object]]:
    """Explicit V0 fixture inputs in SI metres; no optical formulas."""
    common = {
        "schema_version": 1, "model_contract": "v0_aligned_scalar_forward_v1",
        "wavelength_m": 633e-9,
        "grid": {"ny": 512, "nx": 512, "dy": 4e-6, "dx": 4e-6},
        "source": {"kind": "gaussian", "amplitude": 1.0, "phase_rad": 0.0,
                   "waist_radius_m": 100e-6, "waist_z_m": 0.0,
                   "center_x_m": 0.0, "center_y_m": 0.0},
        "components": [], "observation": {"id": "screen", "z_m": 20e-3},
    }
    cases = {"free": copy.deepcopy(common)}
    lens = {"id": "lens", "kind": "thin_lens", "z_m": 0.0, "focal_length_m": 20e-3}
    cases["lens"] = copy.deepcopy(common); cases["lens"]["components"] = [copy.deepcopy(lens)]
    cases["aperture_lens"] = copy.deepcopy(common)
    cases["aperture_lens"]["components"] = [
        {"id": "aperture", "kind": "circular_aperture", "z_m": 0.0, "radius_m": 80e-6},
        copy.deepcopy(lens),
    ]
    cases["negative_lens"] = copy.deepcopy(cases["lens"])
    cases["negative_lens"]["components"][0]["focal_length_m"] = -20e-3
    cases["observation_10mm"] = copy.deepcopy(cases["lens"])
    cases["observation_10mm"]["observation"]["z_m"] = 10e-3
    cases["small_aperture"] = copy.deepcopy(cases["aperture_lens"])
    # Match the explicitly documented editor's multiply-by-SI-unit boundary.
    # 40*1e-6 and literal40e-6 differ by one representable float on this platform.
    cases["small_aperture"]["components"][0]["radius_m"] = 40*1e-6
    cases["dark"] = copy.deepcopy(common); cases["dark"]["source"]["amplitude"] = 0.0
    for name, ny, nx in (("asymmetric_3x4", 3, 4), ("asymmetric_2x5", 2, 5)):
        cases[name] = copy.deepcopy(common)
        cases[name]["grid"] = {"ny": ny, "nx": nx, "dy": 5e-6, "dx": 2e-6}
        cases[name]["source"].update(waist_radius_m=10e-6, center_x_m=2e-6, center_y_m=-5e-6)
        cases[name]["observation"]["z_m"] = 0.0
    cases["max_eight"] = copy.deepcopy(common)
    cases["max_eight"]["components"] = [
        {"id": f"lens{i}", "kind": "thin_lens", "z_m": i*1e-3,
         "focal_length_m": 20e-3 if i % 2 == 0 else -20e-3} for i in range(8)
    ]
    return cases


def request(method: str, path: str, payload: bytes | None = None,
            origin: str = ORIGIN) -> tuple[int, bytes, str]:
    """Send only to the approved loopback service; bound received bytes."""
    connection = http.client.HTTPConnection("127.0.0.1", 8510, timeout=30)
    headers = {"Origin": origin}
    if payload is not None: headers["Content-Type"] = "application/json"
    try:
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        data = response.read(MAX_RESPONSE+1)
        assert len(data) <= MAX_RESPONSE, "Response exceeds approved byte cap"
        return response.status, data, response.getheader("Content-Type", "")
    finally:
        connection.close()


def independent_decode(data: bytes) -> tuple[dict[str, object], list[np.ndarray]]:
    """Decode the published format independently of application encoder code."""
    assert 16 <= len(data) <= MAX_RESPONSE
    assert data[:8] == b"OHLABV1\0"
    header_length, reserved = struct.unpack_from("<II", data, 8)
    assert reserved == 0 and 0 < header_length <= 16_384
    payload_start = 16 + ((header_length+7)//8)*8
    assert payload_start <= len(data)
    assert data[16+header_length:payload_start] == bytes(payload_start-16-header_length)
    def pairs(items):
        result = {}
        for key, value in items:
            assert key not in result, "Duplicate JSON key"
            result[key] = value
        return result
    def invalid_constant(value): raise AssertionError(f"Invalid JSON constant {value}")
    header = json.loads(data[16:16+header_length].decode("utf-8", errors="strict"),
                        object_pairs_hook=pairs, parse_constant=invalid_constant)
    assert set(header) == {"protocol_version", "request_id", "experiment_sha256", "experiment", "stages", "arrays", "intensity_max"}
    assert header["protocol_version"] == 1
    assert re.fullmatch(r"[0-9a-f]{64}", header["experiment_sha256"])
    spec = header["experiment"]; ny, nx = spec["grid"]["ny"], spec["grid"]["nx"]
    expected = [("intensity", [ny, nx], "amplitude_unit^2"), ("x_m", [nx], "m"), ("y_m", [ny], "m")]
    assert len(header["arrays"]) == 3
    arrays = []; offset = 0
    for descriptor, (name, shape, units) in zip(header["arrays"], expected):
        count = int(np.prod(shape)); nbytes = count*8
        assert descriptor == dict(name=name, dtype="float64-le", order="C", shape=shape,
                                  offset_bytes=offset, nbytes=nbytes, units=units)
        assert payload_start+offset+nbytes <= len(data)
        array = np.frombuffer(data, dtype="<f8", count=count, offset=payload_start+offset).copy().reshape(shape)
        assert np.isfinite(array).all()
        arrays.append(array); offset += nbytes
    assert len(data) == payload_start+offset, "Undeclared gap/trailing payload"
    assert (arrays[0] >= 0).all()
    assert header["intensity_max"] == float(arrays[0].max())
    return header, arrays


def run_http_acceptance() -> dict[str, object]:
    """Measure shipped routes and compare real results with independent calls."""
    assert Path(optics.__file__).resolve().is_relative_to(ROOT/"src"/"ohlab")
    assert request("GET", "/api/v1/health")[0] == 200
    status, index, _ = request("GET", "/")
    assert status == 200 and index == (ROOT/"frontend/bench/dist/index.html").read_bytes()
    asset_evidence = {}
    for asset in re.findall(r'(?:src|href)="(/assets/[^\"]+)"', index.decode("utf-8")):
        status, content, _ = request("GET", asset)
        local = ROOT/"frontend/bench/dist"/asset.lstrip("/")
        assert status == 200 and content == local.read_bytes()
        asset_evidence[asset] = hashlib.sha256(content).hexdigest()
    assert asset_evidence, "No served production assets found"
    reports = {}
    for label, raw_spec in fixture_specs().items():
        spec = SequentialExperiment.from_dict(raw_spec)
        request_id = str(uuid.uuid4()); envelope = {"request_id": request_id, "experiment": raw_spec}
        encoded = json.dumps(envelope, allow_nan=False).encode("utf-8")
        status, validated, _ = request("POST", "/api/v1/validate", encoded)
        validation = json.loads(validated)
        assert status == 200 and validation["request_id"] == request_id
        assert validation["experiment"] == spec.to_dict()
        started = time.perf_counter()
        status, response, content_type = request("POST", "/api/v1/simulate", encoded)
        http_seconds = time.perf_counter()-started
        assert status == 200, response.decode("utf-8", errors="replace")[:500]
        assert content_type.split(";",1)[0] == "application/octet-stream"
        header, arrays = independent_decode(response)
        assert header["request_id"] == request_id and header["experiment"] == spec.to_dict()
        assert header["experiment_sha256"] == validation["experiment_sha256"]
        started = time.perf_counter(); direct = run_experiment(spec, record_fields=())
        direct_seconds = time.perf_counter()-started
        assert arrays[0].tobytes() == direct.observation.intensity.astype("<f8", copy=False).tobytes()
        assert arrays[1].tobytes() == spec.grid.x.astype("<f8", copy=False).tobytes()
        assert arrays[2].tobytes() == spec.grid.y.astype("<f8", copy=False).tobytes()
        expected_stages = [{key: getattr(stage, key) for key in
            ("selector", "z_m", "norm", "previous_norm", "delta_norm", "transmission_ratio")}
            for stage in direct.stages]
        assert header["stages"] == expected_stages
        indices = {(0,0), (spec.grid.ny-1,spec.grid.nx-1), (spec.grid.ny//2,spec.grid.nx//2)}
        if spec.grid.nx*spec.grid.ny <= 16: indices = {(r,c) for r in range(spec.grid.ny) for c in range(spec.grid.nx)}
        samples = [{"row":r,"column":c,"intensity":float(arrays[0][r,c]),
                    "x_m":float(arrays[1][c]),"y_m":float(arrays[2][r])} for r,c in sorted(indices)]
        reports[label] = {"experiment":spec.to_dict(),"request_id":request_id,
            "http_wall_s":http_seconds,"direct_solver_s":direct_seconds,"response_bytes":len(response),
            "content_type":content_type,"header_bytes":struct.unpack_from("<I",response,8)[0],
            "intensity_sha256":hashlib.sha256(arrays[0].tobytes()).hexdigest(),
            "intensity_max":header["intensity_max"],"samples":samples,"stages":header["stages"],
            "exact_direct_public_v0_match":True}
    assert reports["negative_lens"]["intensity_sha256"] != reports["lens"]["intensity_sha256"]
    assert reports["observation_10mm"]["intensity_sha256"] != reports["lens"]["intensity_sha256"]
    assert reports["small_aperture"]["intensity_sha256"] != reports["aperture_lens"]["intensity_sha256"]
    invalid = fixture_specs()["free"]; invalid["grid"]["nx"] = 513
    invalid_body=json.dumps({"request_id":str(uuid.uuid4()),"experiment":invalid}).encode()
    rejection_status, _, _ = request("POST","/api/v1/simulate",invalid_body)
    assert rejection_status == 422
    wrong_origin_status, _, _ = request("POST","/api/v1/validate",invalid_body,origin="http://127.0.0.1:8501")
    assert wrong_origin_status == 403
    traversal_status, _, _ = request("GET","/%2e%2e/README.md")
    assert traversal_status in (400,403,404)
    return {"passed":True,"base_url":ORIGIN,"source_location":str(Path(optics.__file__).resolve()),
            "served_asset_sha256":asset_evidence,"cases":reports,
            "negative_http_checks":{"grid513":rejection_status,"other_origin":wrong_origin_status,"traversal":traversal_status},
            "exactness":"same-platform deterministic public V0 field/axis/stage equality; no display or continuous-optics claim",
            "measurement_scope":"actual complete HTTP response time; excludes browser display and GPU performance"}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url",default=ORIGIN,choices=[ORIGIN])
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): parser.error("output already exists; use a fresh owned ignored destination")
    report=run_http_acceptance()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as stream: json.dump(report,stream,indent=2,allow_nan=False)
    print(json.dumps({"passed":True,"cases":len(report["cases"]),"output":str(args.output),
                      "source_location":report["source_location"],"served_asset_sha256":report["served_asset_sha256"]},indent=2))


if __name__ == "__main__": main()
