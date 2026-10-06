"""Independent bounded HTTP evidence for the actual V2b public-V2a integration.

No application encoder, decoder, adapter or expected-result helper is imported.
Evidence is transient, not a scientific archive or qualified replay format.
Run against the task-owned production server with the existing project Python.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import http.client
import json
import math
from pathlib import Path
import re
import struct
import time
import uuid

import numpy as np
import ohlab.optics as optics
import ohlab.optics.interference as interference
from ohlab.optics import SequentialExperiment, sample_source
from ohlab.optics.interference import TwoArmSpec, run_two_arm

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:8510"
MAX_SINGLE = 4_218_896
MAX_JSON = 65_536
MAX_HEADER = 16_384
PHASES = [index * (2 * math.pi / 16) for index in range(17)]
PAIRS = ("inputs", "split", "propagated", "combiner", "outputs")
PROPERTIES = ("inputs_total", "split_total", "propagated_total", "combiner_total", "outputs_total",
              "split_delta", "propagation_delta", "phase_delta", "recombination_delta", "total_delta",
              "output_fractions", "total_output_ratio")


def strict_json(data: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            assert key not in result, f"duplicate JSON key: {key}"
            result[key] = value
        return result

    def constant(value):
        raise AssertionError(f"nonfinite JSON constant: {value}")

    def number(value):
        parsed = float(value)
        assert math.isfinite(parsed), "JSON number overflows binary64"
        return parsed

    result = json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                        parse_constant=constant, parse_float=number)
    assert isinstance(result, dict)
    return result


def request(method: str, path: str, payload: dict | bytes | None = None, *,
            maximum: int = MAX_SINGLE, origin: str = ORIGIN) -> tuple[int, bytes, str]:
    connection = http.client.HTTPConnection("127.0.0.1", 8510, timeout=30)
    body = json.dumps(payload, allow_nan=False, ensure_ascii=True).encode("utf-8") if isinstance(payload, dict) else payload
    headers = {"Origin": origin}
    if body is not None:
        assert len(body) <= 32_768 or isinstance(payload, bytes)
        headers["Content-Type"] = "application/json"
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        data = response.read(maximum + 1)
        assert len(data) <= maximum, "response exceeded route-specific byte cap"
        length = response.getheader("Content-Length")
        if length is not None:
            assert int(length) == len(data)
        return response.status, data, response.getheader("Content-Type", "").split(";", 1)[0]
    finally:
        connection.close()


def digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def independent_decode(data: bytes) -> tuple[dict, list[np.ndarray]]:
    assert 16 <= len(data) <= MAX_SINGLE
    assert data[:8] == b"OHLAB2P\0", "distinct two-path magic required"
    header_length, reserved = struct.unpack_from("<II", data, 8)
    assert reserved == 0 and 0 < header_length <= MAX_HEADER
    start = 16 + ((header_length + 7) // 8) * 8
    assert start <= len(data)
    assert data[16 + header_length:start] == bytes(start - 16 - header_length)
    header = strict_json(data[16:16 + header_length])
    assert set(header) == {"protocol_version", "message_type", "request_id", "experiment_sha256",
                           "experiment", "ports", "norms", "diagnostics", "arrays", "intensity_max"}
    assert header["protocol_version"] == 1 and header["message_type"] == "two_path_result"
    identity = uuid.UUID(header["request_id"])
    assert identity.version == 4 and str(identity) == header["request_id"]
    assert header["ports"] == ["port_0", "port_1"]
    assert re.fullmatch(r"[0-9a-f]{64}", header["experiment_sha256"])
    assert header["experiment_sha256"] == digest(header["experiment"])
    grid = header["experiment"]["grid"]
    ny, nx = grid["ny"], grid["nx"]
    assert type(ny) is int and type(nx) is int and 1 <= ny <= 512 and 1 <= nx <= 512
    expected = [("intensity_port_0", "intensity", "port_0", [ny, nx], "amplitude_unit^2"),
                ("intensity_port_1", "intensity", "port_1", [ny, nx], "amplitude_unit^2"),
                ("x_m", "coordinate", None, [nx], "m"), ("y_m", "coordinate", None, [ny], "m")]
    assert len(header["arrays"]) == 4
    arrays = []
    offset = 0
    for descriptor, (name, role, port_id, shape, units) in zip(header["arrays"], expected):
        count = math.prod(shape)
        assert descriptor == {"name": name, "role": role, "port_id": port_id,
                              "dtype": "float64-le", "order": "C", "shape": shape,
                              "offset_bytes": offset, "nbytes": count * 8, "units": units}
        assert start + offset + count * 8 <= len(data)
        values = np.frombuffer(data, dtype="<f8", count=count, offset=start + offset).copy().reshape(shape)
        assert np.isfinite(values).all()
        arrays.append(values)
        offset += count * 8
    assert start + offset == len(data), "no gaps or undeclared trailing payload"
    for port in range(2):
        assert (arrays[port] >= 0).all()
        assert header["intensity_max"][port] == float(arrays[port].max())
    assert np.array_equal(arrays[2], np.asarray([(column - nx // 2) * grid["dx"] for column in range(nx)]))
    assert np.array_equal(arrays[3], np.asarray([(row - ny // 2) * grid["dy"] for row in range(ny)]))
    assert set(header["norms"]) == set(PAIRS) and set(header["diagnostics"]) == set(PROPERTIES)
    return header, arrays


def source_plane(experiment: dict) -> SequentialExperiment:
    return SequentialExperiment.from_dict({
        "schema_version": 1, "model_contract": "v0_aligned_scalar_forward_v1",
        "wavelength_m": experiment["wavelength_m"], "grid": experiment["grid"],
        "source": experiment["source"], "components": [],
        "observation": {"id": "source_plane", "z_m": 0.0},
    })


def scalar_records(result) -> tuple[dict, dict]:
    norms = {name: list(getattr(result.norms, name)) for name in PAIRS}
    diagnostics = {name: (list(getattr(result.norms, name)) if name == "output_fractions"
                         else getattr(result.norms, name)) for name in PROPERTIES}
    return norms, diagnostics


def fixed_experiment(experiment: dict) -> dict:
    return {"wavelength_m": experiment["wavelength_m"], "grid": copy.deepcopy(experiment["grid"]),
            "source": copy.deepcopy(experiment["source"]),
            "arm_0_distance_m": experiment["two_arm_spec"]["arm_0_distance_m"],
            "arm_1_distance_m": experiment["two_arm_spec"]["arm_1_distance_m"]}


def fixture_cases() -> dict[str, dict]:
    """Independent numeric editor texts and their once-converted SI values."""
    def case(*, n=64, kind="uniform", phase="0", amplitude="1", source_phase="0",
             l0="2", l1="2", dx="4", dy="4", ny=None, nx=None, waist="50", cx="0", cy="0"):
        inputs = {"wavelength_m": "633", "grid.ny": str(n if ny is None else ny),
                  "grid.nx": str(n if nx is None else nx), "grid.dy": dy, "grid.dx": dx,
                  "source.amplitude": amplitude, "source.phase_rad": source_phase,
                  "two_arm_spec.arm_0_distance_m": l0, "two_arm_spec.arm_1_distance_m": l1,
                  "two_arm_spec.relative_phase_rad": phase}
        source = {"kind": kind, "amplitude": float(amplitude), "phase_rad": float(source_phase)}
        if kind == "gaussian":
            inputs.update({"source.waist_radius_m": waist, "source.waist_z_m": "0",
                           "source.center_x_m": cx, "source.center_y_m": cy})
            source.update(waist_radius_m=float(waist) * 1e-6, waist_z_m=0.0,
                          center_x_m=float(cx) * 1e-6, center_y_m=float(cy) * 1e-6)
        experiment = {"wavelength_m": 633 * 1e-9,
                      "grid": {"ny": int(inputs["grid.ny"]), "nx": int(inputs["grid.nx"]),
                               "dy": float(dy) * 1e-6, "dx": float(dx) * 1e-6},
                      "source": source,
                      "two_arm_spec": {"arm_0_distance_m": float(l0) * 1e-3,
                                       "arm_1_distance_m": float(l1) * 1e-3,
                                       "relative_phase_rad": float(phase)}}
        return {"experiment": experiment, "editor_inputs": inputs}

    lam = 633 * 1e-9
    cases = {"phase_0": case(), "phase_halfpi": case(phase=repr(math.pi / 2)),
             "phase_pi": case(phase=repr(math.pi)), "signed_phase": case(phase="-0.83"),
             "unwrapped_phase": case(phase=repr(2 * math.pi + .37)),
             "gaussian": case(n=128, kind="gaussian", phase="0.37", l0="20", l1="20", cx="12", cy="-8"),
             "gaussian_changed": case(n=128, kind="gaussian", phase="0.81", l0="19", l1="21", cx="12", cy="-8"),
             "common_phase": case(source_phase="0.67"), "dark": case(amplitude="0"),
             "unequal": case(l0=repr((lam / 7) / 1e-3), l1=repr((lam / 7 + lam / 6) / 1e-3)),
             "asymmetric_3x4": case(kind="gaussian", ny=3, nx=4, dx="2", dy="5", waist="10", cx="2", cy="-5", phase="0.37", l0="0", l1="0.001"),
             "asymmetric_2x5": case(kind="gaussian", ny=2, nx=5, dx="2", dy="5", waist="10", cx="2", cy="-5", phase="0.37", l0="0", l1="0.001"),
             "lossy": case(kind="gaussian", ny=4, nx=5, dx="0.2", dy="0.22", waist="0.1", phase="0.37", l0="0.00008", l1="0.00013"),
             "maximum_grid": case(n=512)}
    for phase in (-1e-4, 1e-4, math.pi - 1e-4, math.pi + 1e-4):
        cases[f"near_dark_{phase!r}"] = case(phase=repr(phase), l0="0", l1="0")
    return cases


def genuine_case(label: str, fixture: dict) -> tuple[dict, list[np.ndarray]]:
    experiment = fixture["experiment"]
    envelope = {"protocol_version": 1, "message_type": "two_path_submission",
                "request_id": str(uuid.uuid4()), "experiment": experiment}
    status, body, mime = request("POST", "/api/v2b/validate", envelope, maximum=MAX_HEADER)
    validation = strict_json(body)
    assert status == 200 and mime == "application/json"
    assert validation["request_id"] == envelope["request_id"] and validation["experiment"] == experiment
    assert validation["experiment_sha256"] == digest(experiment)
    started = time.perf_counter()
    status, frame, mime = request("POST", "/api/v2b/simulate", envelope)
    elapsed = time.perf_counter() - started
    assert status == 200 and mime == "application/octet-stream", frame[:500]
    header, arrays = independent_decode(frame)
    assert header["request_id"] == envelope["request_id"] and header["experiment"] == experiment
    incident = sample_source(source_plane(experiment))
    direct = run_two_arm(incident, spec=TwoArmSpec(**experiment["two_arm_spec"]))
    for index, field in enumerate(direct.outputs):
        assert arrays[index].tobytes() == field.intensity.astype("<f8", copy=False).tobytes(), f"ordered port {index} differs from direct V2a"
    assert arrays[2].tobytes() == incident.grid.x.astype("<f8", copy=False).tobytes()
    assert arrays[3].tobytes() == incident.grid.y.astype("<f8", copy=False).tobytes()
    norms, diagnostics = scalar_records(direct)
    assert header["norms"] == norms and header["diagnostics"] == diagnostics
    ny, nx = incident.grid.shape
    indices = {(0, 0), (ny - 1, nx - 1), (ny // 2, nx // 2), (min(ny - 1, ny // 2 + 1), min(nx - 1, nx // 2 + 2))}
    if nx * ny <= 20:
        indices = {(row, column) for row in range(ny) for column in range(nx)}
    samples = [{"port": f"port_{port}", "row": row, "column": column,
                "x_m": float(arrays[2][column]), "y_m": float(arrays[3][row]),
                "intensity": float(arrays[port][row, column])}
               for port in range(2) for row, column in sorted(indices)]
    report = {**fixture, "request_id": envelope["request_id"], "experiment_sha256": header["experiment_sha256"],
              "intensity_max": header["intensity_max"], "norms": norms, "diagnostics": diagnostics,
              "samples": samples, "http_wall_s": elapsed, "response_bytes": len(frame),
              "header_bytes": struct.unpack_from("<I", frame, 8)[0],
              "intensity_sha256": [hashlib.sha256(array.tobytes()).hexdigest() for array in arrays[:2]],
              "exact_direct_public_v2a_match": True}
    if label in {"phase_0", "phase_halfpi", "phase_pi"} or label.startswith("near_dark_"):
        phi = experiment["two_arm_spec"]["relative_phase_rad"]
        expected = [math.cos(phi / 2) ** 2, math.sin(phi / 2) ** 2]
        np.testing.assert_allclose(diagnostics["output_fractions"], expected, rtol=2e-13, atol=2e-13)
        input_scale = float(incident.intensity.max())
        errors = []
        for index in range(2):
            np.testing.assert_allclose(arrays[index], incident.intensity * expected[index],
                                       rtol=2e-13, atol=2e-13 * input_scale)
            errors.append(float(np.max(np.abs(arrays[index] - incident.intensity * expected[index]))) / input_scale)
        report["analytic_intensity_max_input_scaled_error"] = max(errors)
    if label == "unequal":
        np.testing.assert_allclose(diagnostics["output_fractions"], [.75, .25], rtol=2e-13, atol=2e-13)
    if label == "lossy":
        assert diagnostics["total_output_ratio"] < .99 and diagnostics["propagation_delta"] < 0
        assert sum(diagnostics["output_fractions"]) < .99
    if label == "dark":
        assert all(np.count_nonzero(array) == 0 for array in arrays[:2])
        assert diagnostics["output_fractions"] == [None, None] and diagnostics["total_output_ratio"] is None
    return report, arrays


def genuine_sweep(fixture: dict, *, partial_index: int | None = None) -> dict:
    fixed = fixed_experiment(fixture["experiment"])
    envelope = {"protocol_version": 1, "message_type": "two_path_sweep_submission",
                "request_id": str(uuid.uuid4()), "fixed_experiment": fixed, "phases_rad": PHASES}
    started = time.perf_counter()
    status, body, mime = request("POST", "/api/v2b/sweep", envelope, maximum=MAX_JSON)
    elapsed = time.perf_counter() - started
    reply = strict_json(body)
    assert mime == "application/json"
    assert set(reply) == {"protocol_version", "message_type", "request_id", "fixed_experiment_sha256", "fixed_experiment",
                          "phases_rad", "status", "requested_count", "completed_count", "failed_index", "rows", "error"}
    assert reply["protocol_version"] == 1 and reply["message_type"] == "two_path_sweep_result"
    assert reply["request_id"] == envelope["request_id"] and reply["fixed_experiment"] == fixed and reply["phases_rad"] == PHASES
    assert reply["fixed_experiment_sha256"] == digest({"fixed_experiment": fixed, "phases_rad": PHASES})
    assert reply["requested_count"] == 17
    if partial_index is None:
        assert status == 200 and reply["status"] == "complete" and reply["completed_count"] == 17
        assert reply["failed_index"] is None and reply["error"] is None
    else:
        assert status in (422, 500) and reply["status"] == "failed"
        assert reply["completed_count"] == partial_index and reply["failed_index"] == partial_index
        assert set(reply["error"]) == {"code", "message"}
        assert isinstance(reply["error"]["code"], str) and 0 < len(reply["error"]["code"]) <= 80
        assert isinstance(reply["error"]["message"], str) and len(reply["error"]["message"]) <= 300
    assert len(reply["rows"]) == reply["completed_count"]
    incident = sample_source(source_plane(fixture["experiment"]))
    for index, row in enumerate(reply["rows"]):
        result = run_two_arm(incident, spec=TwoArmSpec(arm_0_distance_m=fixed["arm_0_distance_m"],
                             arm_1_distance_m=fixed["arm_1_distance_m"], relative_phase_rad=PHASES[index]))
        n = result.norms
        expected = {"index": index, "phase_rad": PHASES[index], "input_norm": n.inputs_total,
                    "output_norms": list(n.outputs), "output_fractions": list(n.output_fractions),
                    "total_output_ratio": n.total_output_ratio,
                    **{name: getattr(n, name) for name in ("split_delta", "propagation_delta", "phase_delta", "recombination_delta", "total_delta")}}
        assert row == expected, f"sweep row {index} differs from genuine direct public V2a"
    closure = None
    if partial_index is None:
        closure = max(abs(a - b) for a, b in zip(reply["rows"][0]["output_fractions"], reply["rows"][-1]["output_fractions"]))
        np.testing.assert_allclose(reply["rows"][0]["output_fractions"], reply["rows"][-1]["output_fractions"], rtol=2e-13, atol=2e-13)
    return {"status_code": status, "http_wall_s": elapsed, "response_bytes": len(body),
            "reply": reply, "periodic_fraction_max_absolute_error": closure,
            "periodic_rtol": 2e-13, "periodic_atol": 2e-13, "exact_direct_public_v2a_rows": True,
            "controlled_failure": partial_index is not None}


def run_acceptance(*, controlled_partial_index: int | None = None) -> dict:
    for module in (optics, interference):
        assert Path(module.__file__).resolve().is_relative_to(ROOT / "src" / "ohlab")
    fixtures = fixture_cases()
    if controlled_partial_index is not None:
        return {"passed": True, "base_url": ORIGIN, "controlled_partial_failure": genuine_sweep(fixtures["phase_0"], partial_index=controlled_partial_index)}
    assert request("GET", "/api/v1/health", maximum=MAX_HEADER)[0] == 200
    status, index, _ = request("GET", "/", maximum=MAX_JSON)
    assert status == 200 and index == (ROOT / "frontend/bench/dist/index.html").read_bytes()
    assets = {}
    for asset in re.findall(r'(?:src|href)="(/assets/[^\"]+)"', index.decode()):
        status, content, _ = request("GET", asset, maximum=2_000_000)
        assert status == 200 and content == (ROOT / "frontend/bench/dist" / asset.lstrip("/")).read_bytes()
        assets[asset] = hashlib.sha256(content).hexdigest()
    assert assets
    reports = {}
    phase0_arrays = None
    for label, fixture in fixtures.items():
        report, arrays = genuine_case(label, fixture)
        reports[label] = report
        if label == "phase_0":
            phase0_arrays = arrays[:2]
        if label == "common_phase":
            assert phase0_arrays is not None
            errors = []
            for base, shifted in zip(phase0_arrays, arrays):
                np.testing.assert_allclose(base, shifted, rtol=2e-13, atol=2e-13)
                errors.append(float(np.max(np.abs(base - shifted))))
            report["common_phase_max_absolute_intensity_error"] = max(errors)
    phase0_arrays = None
    sweeps = {name: genuine_sweep(fixtures[name]) for name in ("phase_0", "unequal", "lossy")}
    invalid = copy.deepcopy(fixtures["phase_0"]["experiment"])
    invalid["grid"]["nx"] = 513
    bad = {"protocol_version": 1, "message_type": "two_path_submission", "request_id": str(uuid.uuid4()), "experiment": invalid}
    grid_rejection = request("POST", "/api/v2b/simulate", bad, maximum=MAX_HEADER)[0]
    assert grid_rejection == 422
    origin_rejection = request("POST", "/api/v2b/validate", bad, maximum=MAX_HEADER, origin="http://127.0.0.1:8501")[0]
    assert origin_rejection == 403
    sweep_bad = {"protocol_version": 1, "message_type": "two_path_sweep_submission", "request_id": str(uuid.uuid4()),
                 "fixed_experiment": fixed_experiment(fixtures["maximum_grid"]["experiment"]), "phases_rad": PHASES}
    assert request("POST", "/api/v2b/sweep", sweep_bad, maximum=MAX_HEADER)[0] == 422
    overflow = copy.deepcopy(fixtures["phase_0"]["experiment"])
    overflow["source"]["amplitude"] = 1e300
    domain_envelope = {**bad, "request_id": str(uuid.uuid4()), "experiment": overflow}
    status, body, _ = request("POST", "/api/v2b/simulate", domain_envelope, maximum=MAX_HEADER)
    assert status == 422 and strict_json(body)["error"]["code"] == "numerical_failure"
    return {"passed": True, "base_url": ORIGIN, "source_locations": [str(Path(m.__file__).resolve()) for m in (optics, interference)],
            "served_asset_sha256": assets, "cases": reports, "sweeps": sweeps,
            "limits": {"single_response": MAX_SINGLE, "single_header": MAX_HEADER, "sweep_response": MAX_JSON,
                       "single_axis": 512, "sweep_axis": 128, "sweep_points": 17},
            "negative_http_checks": {"grid513": grid_rejection, "other_origin": origin_rejection, "sweep_grid512": 422,
                                     "genuine_numerical_failure": status},
            "exactness": "same-platform deterministic identical-input public V2a arrays/axes/scalars; analytic references use explicit rtol/atol",
            "measurement_scope": "complete actual HTTP responses; no browser/GPU/whole-process-memory claim"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--controlled-partial-index", type=int, choices=range(1, 17))
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; use a fresh owned ignored destination")
    report = run_acceptance(controlled_partial_index=args.controlled_partial_index)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps({"passed": True, "output": str(args.output), "case_count": len(report.get("cases", {})),
                      "sweep_count": len(report.get("sweeps", {})), "controlled_partial": args.controlled_partial_index}, indent=2))


if __name__ == "__main__":
    main()
