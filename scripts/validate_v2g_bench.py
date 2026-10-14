"""Independent, bounded HTTP acceptance for the polarized two-path bench.

This script starts no service and imports no application encoder or adapter.
It compares complete received little-endian arrays and scalar measurements to
identical calls of the unchanged public science API. Independent literal Jones
and finite-sum references remain a separately classified evidence layer.
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
import sys
import time
import uuid

import numpy as np
from ohlab.optics import SequentialExperiment, sample_source
from ohlab.optics.polarization import JonesField, apply_linear_polarizer, transmission_ratio
from ohlab.optics.polarized_interference import (
    PolarizerAction, RetarderAction, PolarizationArm, PolarizedTwoArmSpec,
    run_polarized_two_arm,
)
from validate_v2f_interference import run_validation, TOLERANCES

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:8510"
MODEL = "v2g_ideal_polarized_two_path_v1"
PHASES = tuple(k * math.pi / 8 for k in range(17))
NORM_KEYS = ("inputs", "split", "propagated", "elements", "combiner", "outputs", "arm_action_norms")
DIAGNOSTIC_KEYS = (
    "inputs_total", "split_total", "propagated_total", "elements_total", "combiner_total", "outputs_total",
    "split_delta", "propagation_delta", "elements_delta", "phase_delta", "recombination_delta", "total_delta",
    "propagation_deltas", "element_deltas", "phase_deltas", "arm_action_deltas", "output_fractions", "total_output_ratio",
)


def strict_json(data: bytes) -> dict:
    """Independently parse a finite duplicate-free UTF-8 JSON object."""
    def pairs(items):
        result = {}
        for key, value in items:
            assert key not in result, f"duplicate key {key}"
            result[key] = value
        return result

    def constant(token):
        raise AssertionError(f"nonfinite token {token}")

    value = json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=pairs, parse_constant=constant)

    def finite(item):
        if isinstance(item, float):
            assert math.isfinite(item)
        elif isinstance(item, dict):
            for child in item.values(): finite(child)
        elif isinstance(item, list):
            for child in item: finite(child)
    finite(value)
    assert isinstance(value, dict)
    return value


def digest(value: dict) -> str:
    """Hash the independently canonicalized complete SI specification."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def assert_values(actual: object, expected: object, path: str = "record") -> None:
    """Compare complete public records, excluding bool-as-number equality."""
    if type(expected) in (int, float):
        assert type(actual) in (int, float), f"{path}: expected finite real excluding bool"
        assert math.isfinite(actual) and actual == expected, f"{path}: public numerical mismatch"
        if expected != 0:
            assert struct.pack("<d", actual) == struct.pack("<d", expected), f"{path}: nonzero binary64 drift"
    elif isinstance(expected, dict):
        assert type(actual) is dict and set(actual) == set(expected), f"{path}: closed object keys"
        for key in expected: assert_values(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        assert type(actual) is list and len(actual) == len(expected), f"{path}: ordered array"
        for index, value in enumerate(expected): assert_values(actual[index], value, f"{path}[{index}]")
    else:
        assert type(actual) is type(expected) and actual == expected, f"{path}: exact discriminator/value"


def request(method: str, path: str, value: dict | bytes | None = None, *,
            maximum: int = 542_736, origin: str = ORIGIN) -> tuple[int, bytes, str]:
    """Perform one deliberate fixed-loopback request without retry or redirect."""
    body = json.dumps(value, ensure_ascii=True, allow_nan=False).encode() if isinstance(value, dict) else value
    if isinstance(value, dict): assert len(body) <= 32_768
    headers = {"Origin": origin}
    if body is not None: headers["Content-Type"] = "application/json"
    connection = http.client.HTTPConnection("127.0.0.1", 8510, timeout=30)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        data = response.read(maximum + 1)
        assert len(data) <= maximum
        length = response.getheader("Content-Length")
        if length is not None: assert int(length) == len(data)
        return response.status, data, response.getheader("Content-Type", "").split(";", 1)[0]
    finally:
        connection.close()


def independent_decode(data: bytes, expected: dict | None = None) -> tuple[dict, list[np.ndarray]]:
    """Verify the closed conditional frame inventory before inspecting arrays."""
    assert 16 <= len(data) <= 542_736
    magic, length, reserved = struct.unpack_from("<8sII", data)
    assert magic == b"OHLABPT\0" and reserved == 0 and 0 < length <= 16_384
    padded = (length + 7) // 8 * 8
    assert padded <= 16_384 and data[16 + length:16 + padded] == bytes(padded - length)
    header = strict_json(data[16:16 + length])
    assert set(header) == {"protocol_version", "message_type", "request_id", "experiment_sha256", "experiment",
                           "norms", "diagnostics", "analysis", "arrays", "intensity_max"}
    assert type(header["protocol_version"]) is int and header["protocol_version"] == 1 and header["message_type"] == "polarized_two_path_result"
    identity = uuid.UUID(header["request_id"])
    assert identity.version == 4 and str(identity) == header["request_id"]
    experiment = header["experiment"]
    if expected is not None: assert_values(experiment, expected)
    assert experiment["model_contract"] == MODEL and header["experiment_sha256"] == digest(experiment)
    analysis = header["analysis"]
    assert set(analysis) == {"enabled", "axis_angle_rad", "ports", "total_norm", "total_removed_norm", "total_original_input_ratio"}
    assert type(analysis["enabled"]) is bool
    assert analysis["enabled"] == experiment["analyzer"]["enabled"]
    assert analysis["axis_angle_rad"] == experiment["analyzer"]["axis_angle_rad"]
    enabled = analysis["enabled"]
    if not enabled:
        assert all(analysis[key] is None for key in ("ports", "total_norm", "total_removed_norm", "total_original_input_ratio"))
    else:
        assert len(analysis["ports"]) == 2
        for index, port in enumerate(analysis["ports"]):
            assert set(port) == {"id", "raw_norm", "analyzed_norm", "removed_norm", "original_input_ratio", "raw_output_ratio"}
            assert port["id"] == f"port_{index}"
            assert port["removed_norm"] == port["raw_norm"] - port["analyzed_norm"]
    assert set(header["norms"]) == set(NORM_KEYS) and set(header["diagnostics"]) == set(DIAGNOSTIC_KEYS)
    for index in (0, 1):
        assert len(header["norms"]["arm_action_norms"][index]) == len(experiment[f"arm_{index}"]["actions"])
    grid = experiment["grid"]; ny, nx = grid["ny"], grid["nx"]
    assert type(ny) is int and type(nx) is int and 1 <= ny <= 128 and 1 <= nx <= 128
    inventory = [(f"raw_port_{index}_intensity", "intensity", f"port_{index}", "raw", [ny, nx], "amplitude_unit^2") for index in (0, 1)]
    if enabled:
        inventory += [(f"analyzed_port_{index}_intensity", "intensity", f"port_{index}", "analyzed", [ny, nx], "amplitude_unit^2") for index in (0, 1)]
    inventory += [("x_m", "coordinate", None, None, [nx], "m"), ("y_m", "coordinate", None, None, [ny], "m")]
    assert len(header["arrays"]) == len(inventory)
    offset = 0; arrays = []; start = 16 + padded
    for descriptor, (name, role, port, state, shape, units) in zip(header["arrays"], inventory):
        size = math.prod(shape) * 8
        assert_values(descriptor, {"name": name, "role": role, "port_id": port, "state": state, "dtype": "float64-le",
                                  "order": "C", "shape": shape, "offset_bytes": offset, "nbytes": size, "units": units}, "descriptor")
        assert start + offset + size <= len(data)
        array = np.frombuffer(data, dtype="<f8", count=math.prod(shape), offset=start + offset).copy().reshape(shape)
        assert np.isfinite(array).all()
        if role == "intensity": assert (array >= 0).all()
        arrays.append(array); offset += size
    k = 4 if enabled else 2
    assert offset == 8 * (k * nx * ny + nx + ny) and start + offset == len(data)
    assert offset <= (526_336 if enabled else 264_192) and len(data) <= (542_736 if enabled else 280_592)
    assert header["intensity_max"] == [float(array.max()) for array in arrays[:k]]
    assert np.array_equal(arrays[-2], [(column - nx // 2) * grid["dx"] for column in range(nx)])
    assert np.array_equal(arrays[-1], [(row - ny // 2) * grid["dy"] for row in range(ny)])
    return header, arrays


def public_incident(experiment: dict) -> JonesField:
    """Construct the full public source at z=0, preserving signed waist position."""
    plane = SequentialExperiment.from_dict({"schema_version": 1, "model_contract": "v0_aligned_scalar_forward_v1",
        "wavelength_m": experiment["wavelength_m"], "grid": experiment["grid"], "source": experiment["source"],
        "components": [], "observation": {"id": "source_plane", "z_m": 0.0}})
    coefficients = experiment["coefficients"]
    scalar = sample_source(plane)
    return JonesField.from_scalar(scalar, x_coefficient=complex(coefficients["x"]["re"], coefficients["x"]["im"]),
                                  y_coefficient=complex(coefficients["y"]["re"], coefficients["y"]["im"]))


def public_measurement(experiment: dict, incident: JonesField | None = None):
    """Independent public composition; raw outputs are measured without mutation."""
    if incident is None: incident = public_incident(experiment)
    before = (incident.x.data.tobytes(), incident.y.data.tobytes())
    arms = []
    for name in ("arm_0", "arm_1"):
        arm = experiment[name]; actions = []
        for action in arm["actions"]:
            if action["kind"] == "linear_polarizer":
                actions.append(PolarizerAction(axis_angle_rad=action["axis_angle_rad"]))
            else:
                actions.append(RetarderAction(axis_angle_rad=action["axis_angle_rad"], retardance_rad=action["retardance_rad"]))
        arms.append(PolarizationArm(distance_m=arm["distance_m"], actions=tuple(actions)))
    result = run_polarized_two_arm(incident, spec=PolarizedTwoArmSpec(arm_0=arms[0], arm_1=arms[1],
                                                                 relative_phase_rad=experiment["relative_phase_rad"]))
    raw_before = tuple((field.x.data.tobytes(), field.y.data.tobytes()) for field in result.outputs)
    images = [field.intensity for field in result.outputs]
    analyzer = experiment["analyzer"]
    analysis = {"enabled": analyzer["enabled"], "axis_angle_rad": analyzer["axis_angle_rad"], "ports": None,
                "total_norm": None, "total_removed_norm": None, "total_original_input_ratio": None}
    if analyzer["enabled"]:
        analyzed = tuple(apply_linear_polarizer(field, axis_angle_rad=analyzer["axis_angle_rad"]) for field in result.outputs)
        ports = [{"id": f"port_{index}", "raw_norm": raw.sampled_norm, "analyzed_norm": out.sampled_norm,
                  "removed_norm": raw.sampled_norm - out.sampled_norm,
                  "original_input_ratio": transmission_ratio(incident, out), "raw_output_ratio": transmission_ratio(raw, out)}
                 for index, (raw, out) in enumerate(zip(result.outputs, analyzed))]
        ratios = [port["original_input_ratio"] for port in ports]
        analysis.update(ports=ports, total_norm=sum(port["analyzed_norm"] for port in ports),
                        total_removed_norm=sum(port["removed_norm"] for port in ports),
                        total_original_input_ratio=None if any(value is None for value in ratios) else sum(ratios))
        images.extend(field.intensity for field in analyzed)
    assert before == (incident.x.data.tobytes(), incident.y.data.tobytes())
    assert raw_before == tuple((field.x.data.tobytes(), field.y.data.tobytes()) for field in result.outputs)
    # JSON round trip converts public tuples to wire lists without arithmetic.
    norms = json.loads(json.dumps({key: getattr(result.norms, key) for key in NORM_KEYS}))
    diagnostics = json.loads(json.dumps({key: getattr(result.norms, key) for key in DIAGNOSTIC_KEYS}))
    return {"norms": norms, "diagnostics": diagnostics, "analysis": analysis}, images + [incident.grid.x, incident.grid.y]


def experiment(*, enabled: bool = True, orthogonal: bool = False, n: int = 32) -> dict:
    """An explicit baseline fixture in SI; no adapter preset is imported."""
    return {"schema_version": 1, "model_contract": MODEL, "wavelength_m": 633e-9,
        "grid": {"ny": n, "nx": n, "dy": 4e-6, "dx": 4e-6},
        "source": {"kind": "uniform", "amplitude": 1.0, "phase_rad": 0.0},
        "coefficients": {"x": {"re": 1.0, "im": 0.0}, "y": {"re": 0.0, "im": 0.0}},
        "arm_0": {"distance_m": .002, "actions": []},
        "arm_1": {"distance_m": .002, "actions": ([{"id": "hwp_1", "kind": "linear_retarder", "axis_angle_rad": math.pi / 4, "retardance_rad": math.pi}] if orthogonal else [])},
        "relative_phase_rad": 0.0, "analyzer": {"enabled": enabled, "axis_angle_rad": math.pi / 4}}


def fixture_cases() -> dict[str, dict]:
    """Cover full source/complex/actions, weak signals, zero and both caps."""
    asymmetric = experiment(); asymmetric["grid"] = {"ny": 5, "nx": 8, "dy": 4.31e-6, "dx": 3.79e-6}
    asymmetric["source"].update(kind="gaussian", amplitude=1.17, phase_rad=8.71, waist_radius_m=23.7e-6,
                                 waist_z_m=-.00073, center_x_m=2.31e-6, center_y_m=-1.91e-6)
    asymmetric["coefficients"] = {"x": {"re": .83, "im": -.27}, "y": {"re": -.19, "im": .61}}
    asymmetric["arm_0"] = {"distance_m": .0011, "actions": [
        {"id": "r0", "kind": "linear_retarder", "axis_angle_rad": -.31, "retardance_rad": 7.91},
        {"id": "p0", "kind": "linear_polarizer", "axis_angle_rad": .23}]}
    asymmetric["arm_1"] = {"distance_m": .0017, "actions": [
        {"id": "p1", "kind": "linear_polarizer", "axis_angle_rad": -.67},
        {"id": "r1", "kind": "linear_retarder", "axis_angle_rad": .47, "retardance_rad": 1.27}]}
    asymmetric["relative_phase_rad"] = 8.570796326794897
    asymmetric["analyzer"]["axis_angle_rad"] = -.37
    disabled = copy.deepcopy(asymmetric); disabled["analyzer"]["enabled"] = False
    zero = experiment(); zero["source"]["amplitude"] = 0.0
    weak = experiment(enabled=False); weak["relative_phase_rad"] = 1e-9
    return {"identical": experiment(enabled=False), "orthogonal_raw": experiment(enabled=False, orthogonal=True),
            "orthogonal_analyzed": experiment(orthogonal=True), "asymmetric": asymmetric, "disabled_saved_angle": disabled,
            "zero": zero, "near_dark": weak, "cap_disabled": experiment(enabled=False, n=128), "cap_enabled": experiment(n=128)}


def validate(experiment_value: dict) -> dict:
    """Obtain authoritative canonical specification without running optics."""
    submitted = {"protocol_version": 1, "message_type": "polarized_two_path_submission", "request_id": str(uuid.uuid4()),
                 "experiment_sha256": None, "experiment": experiment_value}
    status, data, mime = request("POST", "/api/v2g/validate", submitted, maximum=16_384)
    value = strict_json(data)
    assert status == 200 and mime == "application/json", (status, data[:500])
    assert set(value) == {"protocol_version", "message_type", "request_id", "experiment_sha256", "experiment"}
    assert value["protocol_version"] == 1 and value["message_type"] == "polarized_two_path_validation"
    assert value["request_id"] == submitted["request_id"] and value["experiment"] == experiment_value
    assert value["experiment_sha256"] == digest(value["experiment"])
    return {**submitted, "experiment": value["experiment"], "experiment_sha256": value["experiment_sha256"]}


def genuine_case(label: str, value: dict, frames: Path | None = None) -> dict:
    """Compare every returned float64 byte and public scalar on the same platform."""
    submitted = validate(value); started = time.perf_counter()
    status, data, mime = request("POST", "/api/v2g/simulate", submitted)
    http_wall_s = time.perf_counter() - started
    assert status == 200 and mime == "application/octet-stream", (label, status, data[:500])
    header, arrays = independent_decode(data, submitted["experiment"])
    assert header["request_id"] == submitted["request_id"]
    measurements, expected = public_measurement(submitted["experiment"])
    for key in ("norms", "diagnostics", "analysis"):
        assert_values(header[key], measurements[key], f"{label}.{key}")
    for index, (actual, reference) in enumerate(zip(arrays, expected)):
        assert actual.tobytes() == reference.astype("<f8", copy=False).tobytes(), f"{label}: full direct-public array {index}"
    if frames is not None:
        with (frames / (label + ".bin")).open("xb") as stream: stream.write(data)
    return {"experiment": submitted["experiment"], "request_id": submitted["request_id"], "experiment_sha256": header["experiment_sha256"],
            **measurements, "intensity_max": header["intensity_max"], "response_bytes": len(data), "header_bytes": struct.unpack_from("<I", data, 8)[0],
            "payload_bytes": sum(array.nbytes for array in arrays), "array_sha256": [hashlib.sha256(array.tobytes()).hexdigest() for array in arrays],
            "full_array_and_scalar_public_equality": True, "input_and_raw_outputs_unchanged": True, "http_wall_s": http_wall_s,
            "acceptance_case_wall_s": time.perf_counter() - started}


def genuine_sweep(value: dict, *, partial_index: int | None = None, failure_kind: str = "numerical") -> dict:
    """Check all genuine rows against one independent public incident field."""
    fixed = {key: item for key, item in value.items() if key != "relative_phase_rad"}
    submitted = {"protocol_version": 1, "message_type": "polarized_two_path_sweep_submission", "request_id": str(uuid.uuid4()),
                 "fixed_experiment_sha256": None, "fixed_experiment": fixed, "phases_rad": list(PHASES)}
    status, data, _ = request("POST", "/api/v2g/validate", submitted, maximum=16_384)
    validation = strict_json(data)
    assert status == 200
    sweep_hash = digest({"fixed_experiment": fixed, "phases_rad": list(PHASES)})
    assert validation == {"protocol_version": 1, "message_type": "polarized_two_path_sweep_validation", "request_id": submitted["request_id"],
        "fixed_experiment_sha256": digest(fixed), "fixed_experiment": fixed, "phases_rad": list(PHASES), "sweep_sha256": sweep_hash}
    submitted["fixed_experiment_sha256"] = validation["fixed_experiment_sha256"]
    status, data, mime = request("POST", "/api/v2g/sweep", submitted, maximum=65_536)
    reply = strict_json(data)
    assert mime == "application/json" and set(reply) == {"protocol_version", "message_type", "request_id", "fixed_experiment_sha256",
        "sweep_sha256", "fixed_experiment", "phases_rad", "status", "requested_count", "completed_count", "failed_index", "rows", "error"}
    for key in ("protocol_version", "request_id", "fixed_experiment_sha256", "fixed_experiment", "phases_rad"):
        assert reply[key] == submitted[key]
    assert reply["message_type"] == "polarized_two_path_sweep" and reply["sweep_sha256"] == sweep_hash and reply["requested_count"] == 17
    if partial_index is None:
        assert status == 200 and reply["status"] == "complete" and reply["completed_count"] == 17
        assert reply["failed_index"] is None and reply["error"] is None
    else:
        assert status == (422 if failure_kind == "numerical" else 500) and reply["status"] == "failed"
        assert reply["completed_count"] == reply["failed_index"] == partial_index
        assert reply["error"]["code"] == ("numerical_failure" if failure_kind == "numerical" else "sweep_failed")
        assert set(reply["error"]) == {"code", "message"} and len(reply["error"]["message"]) <= 300
    assert len(reply["rows"]) == reply["completed_count"]
    incident = public_incident(value)
    for index, row in enumerate(reply["rows"]):
        scalars, _ = public_measurement({**fixed, "relative_phase_rad": PHASES[index]}, incident)
        assert_values(row, {"index": index, "phase_rad": PHASES[index], **scalars}, f"genuine contiguous public row {index}")
    endpoint = None
    if partial_index is None:
        first, last = reply["rows"][0], reply["rows"][-1]
        endpoint = [last["norms"]["outputs"][index] - first["norms"]["outputs"][index] for index in (0, 1)]
    return {"status_code": status, "response_bytes": len(data), "reply": reply, "full_public_row_equality": True,
            "independent_endpoint_norm_discrepancy": endpoint, "controlled_failure": partial_index is not None}


def verify_assets(assets: Path) -> dict:
    """Check actual served bytes against the task-owned production build."""
    assert assets.is_relative_to(ROOT / "runs") and assets.is_dir()
    status, index, _ = request("GET", "/", maximum=65_536)
    assert status == 200 and index == (assets / "index.html").read_bytes()
    result = {}
    for path in re.findall(r'(?:src|href)="(/assets/[^\"]+)"', index.decode()):
        status, data, _ = request("GET", path, maximum=2_000_000)
        assert status == 200 and data == (assets / path.lstrip("/")).read_bytes()
        result[path] = hashlib.sha256(data).hexdigest()
    assert result
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--assets-dir", type=Path)
    parser.add_argument("--controlled-partial-index", type=int, choices=(0, 8, 16))
    parser.add_argument("--failure-kind", choices=("numerical", "unexpected"), default="numerical")
    parser.add_argument("--skip-independent-core", action="store_true", help="Postcommit repetition only; preserve earlier full analytic layer")
    parser.add_argument("--browser-frame-dir", type=Path, help="Independently recheck complete captured production browser frames")
    args = parser.parse_args(); output = args.output.resolve()
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve(): parser.error("Use the existing project interpreter")
    if output.exists() or not output.is_relative_to(ROOT / "runs"): parser.error("Use a fresh ignored output under runs")
    frames = output.with_suffix("").with_name(output.stem + "_frames"); frames.mkdir(parents=True, exist_ok=False)
    fixtures = fixture_cases()
    report = {"base_url": ORIGIN, "interpreter": sys.executable, "limits": {"request": 32768, "header_padded": 16384,
        "payload_disabled": 264192, "payload_enabled": 526336, "frame_disabled": 280592, "frame_enabled": 542736, "sweep": 65536},
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in
            (Path(__file__).resolve(), ROOT / "src/ohlab/optics/polarized_interference.py", ROOT / "src/ohlab/optics/polarization.py", ROOT / "scripts/validate_v2f_interference.py")}}
    if args.controlled_partial_index is not None:
        report["controlled_partial"] = genuine_sweep(fixtures["orthogonal_analyzed"], partial_index=args.controlled_partial_index, failure_kind=args.failure_kind)
    else:
        assert request("GET", "/api/v1/health", maximum=16_384)[0] == 200
        if args.assets_dir is None: parser.error("Production acceptance requires explicit owned assets")
        report["served_assets"] = verify_assets(args.assets_dir.resolve())
        report["cases"] = {name: genuine_case(name, value, frames) for name, value in fixtures.items()}
        report["sweeps"] = {name: genuine_sweep(fixtures[name]) for name in ("identical", "orthogonal_analyzed", "asymmetric", "zero", "disabled_saved_angle")}
        tiny = experiment(); tiny["grid"] = {"ny": 2, "nx": 2, "dy": 4e-6, "dx": 4e-6}
        tiny["source"]["amplitude"] = 1e-150; tiny["analyzer"]["axis_angle_rad"] = math.pi / 2
        tiny["arm_0"]["distance_m"] = tiny["arm_1"]["distance_m"] = 0.0
        raw_only = copy.deepcopy(tiny); raw_only["analyzer"]["enabled"] = False
        report["runner_before_genuine_analyzer_failure"] = genuine_case("tiny_raw_only", raw_only, frames)
        status, body, mime = request("POST", "/api/v2g/simulate", validate(tiny), maximum=16_384)
        error = strict_json(body)
        assert status == 422 and mime == "application/json" and error["error"]["code"] == "numerical_failure"
        report["genuine_analyzer_failure"] = {"status": status, "error": error, "raw_only_success_published": False}
        bad = copy.deepcopy(fixtures["identical"]); bad["grid"]["nx"] = 129
        status, _, _ = request("POST", "/api/v2g/validate", {"protocol_version": 1, "message_type": "polarized_two_path_submission", "request_id": str(uuid.uuid4()), "experiment_sha256": None, "experiment": bad}, maximum=16_384)
        assert status == 422
        assert request("POST", "/api/v2g/validate", b" " * 32769, maximum=16_384)[0] == 413
        assert request("POST", "/api/v2g/validate", b"{}", maximum=16_384, origin="http://127.0.0.1:8501")[0] == 403
        report["negative_http"] = {"grid129": 422, "body32769": 413, "wrong_origin": 403}
        if not args.skip_independent_core:
            independent = run_validation()
            report["independent_unchanged_v2f_analytic"] = independent
            report["independent_tolerances"] = TOLERANCES
    if args.browser_frame_dir:
        browser_checks = []
        for path in sorted(args.browser_frame_dir.resolve().rglob("*.bin")):
            data = path.read_bytes()
            if data[:8] != b"OHLABPT\0": continue
            header, actual = independent_decode(data)
            scalars, expected = public_measurement(header["experiment"])
            for key in scalars: assert_values(header[key], scalars[key], f"browser.{key}")
            assert all(a.tobytes() == b.astype("<f8", copy=False).tobytes() for a, b in zip(actual, expected))
            browser_checks.append({"file": str(path), "request_id": header["request_id"], "complete_arrays_and_scalars_exact": True})
        assert browser_checks, "No genuine browser frames captured"
        report["browser_frame_checks"] = browser_checks
    report["passed"] = True
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream: json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps({"passed": True, "output": str(output), "cases": len(report.get("cases", {})), "sweeps": len(report.get("sweeps", {}))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
