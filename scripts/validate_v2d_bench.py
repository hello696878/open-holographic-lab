"""Independent bounded HTTP evidence for the ideal Jones bench integration.

Run only against an explicitly task-owned production or controlled loopback
service. This script neither starts a service nor imports an app encoder,
decoder or adapter. Direct-public transport equality and independent analytic
evidence are recorded separately. Evidence is not an experiment archive.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import http.client
import importlib.metadata
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
import ohlab.optics.polarization as polarization

# This unchanged independently evaluated reference retains its scientific
# tolerances, literal fixtures and actual-binary64-angle Decimal weak oracle.
from validate_v2c_polarization import run_validation, TOLERANCES

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:8510"
MAX_FRAME = 280_592
MAX_HEADER = 16_384
MAX_JSON = 65_536
ANGLES = [degree * (math.pi / 180) for degree in (-90, -75, -60, -45, -30, -15, 0, 15, 30, 45, 60, 75, 90)]
STAGE_KEYS = {"stage_id", "kind", "norm", "previous_norm", "delta_norm",
              "adjacent_transmission_ratio", "incident_transmission_ratio"}


def strict_json(data: bytes) -> dict:
    """Decode finite duplicate-free UTF-8 JSON, independently of app helpers."""
    def pairs(items):
        value = {}
        for key, item in items:
            assert key not in value, f"duplicate JSON key: {key}"
            value[key] = item
        return value

    def constant(value):
        raise AssertionError(f"nonfinite JSON constant: {value}")

    result = json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                        parse_constant=constant)
    def finite(value):
        if isinstance(value, float):
            assert math.isfinite(value), "JSON float overflows binary64"
        elif isinstance(value, dict):
            for item in value.values(): finite(item)
        elif isinstance(value, list):
            for item in value: finite(item)
    finite(result)
    assert isinstance(result, dict)
    return result


def digest(value: dict) -> str:
    """Server-side canonical JSON identity; full structures are also checked."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def request(method: str, path: str, value: dict | bytes | None = None, *,
            maximum: int = MAX_FRAME, origin: str = ORIGIN) -> tuple[int, bytes, str]:
    """Perform one deliberate local request, with no retry or redirects."""
    body = json.dumps(value, allow_nan=False, ensure_ascii=True).encode() if isinstance(value, dict) else value
    if isinstance(value, dict): assert len(body) <= 32_768
    headers = {"Origin": origin}
    if body is not None: headers["Content-Type"] = "application/json"
    connection = http.client.HTTPConnection("127.0.0.1", 8510, timeout=30)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        data = response.read(maximum + 1)
        assert len(data) <= maximum, "route response exceeds cap"
        length = response.getheader("Content-Length")
        if length is not None: assert int(length) == len(data)
        return response.status, data, response.getheader("Content-Type", "").split(";", 1)[0]
    finally:
        connection.close()


def independent_decode(data: bytes) -> tuple[dict, list[np.ndarray]]:
    """Check complete OHLABPL framing, descriptors and finite payload independently."""
    assert 16 <= len(data) <= MAX_FRAME and data[:8] == b"OHLABPL\0"
    header_length, reserved = struct.unpack_from("<II", data, 8)
    assert reserved == 0 and 0 < header_length <= MAX_HEADER
    start = 16 + ((header_length + 7) // 8) * 8
    assert start <= len(data) and data[16 + header_length:start] == bytes(start - 16 - header_length)
    header = strict_json(data[16:16 + header_length])
    assert set(header) == {"protocol_version", "message_type", "request_id", "experiment_sha256",
                           "experiment", "ordered_stage_ids", "stages", "readout", "arrays", "intensity_max"}
    assert header["protocol_version"] == 1 and header["message_type"] == "polarization_result"
    identity = uuid.UUID(header["request_id"])
    assert identity.version == 4 and str(identity) == header["request_id"]
    experiment = header["experiment"]
    assert header["experiment_sha256"] == digest(experiment)
    ids = ["input"] + [element["id"] for element in experiment["elements"]]
    assert header["ordered_stage_ids"] == ids and 1 <= len(ids) <= 9
    assert [stage["stage_id"] for stage in header["stages"]] == ids
    for index, stage in enumerate(header["stages"]):
        assert set(stage) == STAGE_KEYS | {"sample"}
        assert stage["kind"] == ("input" if index == 0 else experiment["elements"][index - 1]["kind"])
        assert type(stage["norm"]) in (int, float) and stage["norm"] >= 0
        assert set(stage["sample"]) == {"x", "y"}
        for component in stage["sample"].values():
            assert set(component) == {"re", "im"}
            assert all(type(value) in (int, float) and math.isfinite(value) for value in component.values())
        if index == 0:
            assert all(stage[key] is None for key in ("previous_norm", "delta_norm", "adjacent_transmission_ratio"))
        else:
            previous = header["stages"][index - 1]["norm"]
            assert stage["previous_norm"] == previous and stage["delta_norm"] == stage["norm"] - previous
        for key in ("adjacent_transmission_ratio", "incident_transmission_ratio"):
            assert stage[key] is None or type(stage[key]) in (int, float) and stage[key] >= 0
    grid = experiment["grid"]
    ny, nx = grid["ny"], grid["nx"]
    assert type(ny) is int and type(nx) is int and 1 <= ny <= 128 and 1 <= nx <= 128
    expected = [("incident_intensity", "intensity", "input", [ny, nx], "amplitude_unit^2"),
                ("final_intensity", "intensity", ids[-1], [ny, nx], "amplitude_unit^2"),
                ("x_m", "coordinate", None, [nx], "m"), ("y_m", "coordinate", None, [ny], "m")]
    assert len(header["arrays"]) == 4
    arrays, offset = [], 0
    for descriptor, (name, role, stage_id, shape, units) in zip(header["arrays"], expected):
        count = math.prod(shape)
        assert descriptor == {"name": name, "role": role, "stage_id": stage_id, "dtype": "float64-le",
                              "order": "C", "shape": shape, "offset_bytes": offset,
                              "nbytes": count * 8, "units": units}
        assert start + offset + count * 8 <= len(data)
        values = np.frombuffer(data, dtype="<f8", count=count, offset=start + offset).copy().reshape(shape)
        assert np.isfinite(values).all()
        arrays.append(values); offset += count * 8
    assert offset <= 264_192 and start + offset == len(data), "no undeclared trailing/gap payload"
    for index in range(2):
        assert (arrays[index] >= 0).all() and header["intensity_max"][index] == float(arrays[index].max())
    assert np.array_equal(arrays[2], [(column - nx // 2) * grid["dx"] for column in range(nx)])
    assert np.array_equal(arrays[3], [(row - ny // 2) * grid["dy"] for row in range(ny)])
    row, column = experiment["readout"]["row"], experiment["readout"]["column"]
    assert header["readout"] == {"row": row, "column": column, "x_m": float(arrays[2][column]), "y_m": float(arrays[3][row])}
    return header, arrays


def source_plane(experiment: dict) -> SequentialExperiment:
    """Reuse the public source parser; Gaussian is restricted to its waist plane."""
    source = copy.deepcopy(experiment["source"])
    if source["kind"] == "gaussian": source["waist_z_m"] = 0.0
    return SequentialExperiment.from_dict({"schema_version": 1, "model_contract": "v0_aligned_scalar_forward_v1",
        "wavelength_m": experiment["wavelength_m"], "grid": experiment["grid"], "source": source,
        "components": [], "observation": {"id": "source_plane", "z_m": 0.0}})


def public_incident(experiment: dict):
    scalar = sample_source(source_plane(experiment))
    coefficients = experiment["coefficients"]
    incident = polarization.JonesField.from_scalar(scalar,
        x_coefficient=complex(**{ "real": coefficients["x"]["re"], "imag": coefficients["x"]["im"]}),
        y_coefficient=complex(**{ "real": coefficients["y"]["re"], "imag": coefficients["y"]["im"]}))
    return incident


def public_train(incident, experiment: dict, *, selected_id=None, angle=None, samples=True):
    """Independent app composition of unchanged public operations; no matrices."""
    row, column = experiment["readout"]["row"], experiment["readout"]["column"]
    def record(field, stage_id, kind, previous=None):
        value = {"stage_id": stage_id, "kind": kind, "norm": field.sampled_norm,
                 "previous_norm": None if previous is None else previous.sampled_norm,
                 "delta_norm": None if previous is None else field.sampled_norm - previous.sampled_norm,
                 "adjacent_transmission_ratio": None if previous is None else polarization.transmission_ratio(previous, field),
                 "incident_transmission_ratio": polarization.transmission_ratio(incident, field)}
        if samples:
            value["sample"] = {name: {"re": float(component.data[row, column].real), "im": float(component.data[row, column].imag)}
                               for name, component in (("x", field.x), ("y", field.y))}
        return value
    current, stages = incident, [record(incident, "input", "input")]
    for element in experiment["elements"]:
        theta = angle if element["id"] == selected_id else element["axis_angle_rad"]
        output = (polarization.apply_linear_polarizer(current, axis_angle_rad=theta)
                  if element["kind"] == "linear_polarizer" else
                  polarization.apply_linear_retarder(current, axis_angle_rad=theta, retardance_rad=element["retardance_rad"]))
        stages.append(record(output, element["id"], element["kind"], current)); current = output
    return current, stages


def fixture_cases() -> dict[str, dict]:
    """Explicit numeric fixtures also drive actual browser editor interactions."""
    a = 1 / math.sqrt(2)
    def polar(id, theta): return {"id": id, "kind": "linear_polarizer", "axis_angle_rad": theta}
    def wave(id, theta, delta): return {"id": id, "kind": "linear_retarder", "axis_angle_rad": theta, "retardance_rad": delta}
    def case(preset="analyzer", *, elements=None, phase=0.0, x=1+0j, y=0j, n=64,
             amplitude=1.0, gaussian=False, ny=None, nx=None, row=None, column=None, waist=50e-6, cx=0.0, cy=0.0):
        ny, nx = ny or n, nx or n
        source = {"kind": "gaussian" if gaussian else "uniform", "amplitude": amplitude, "phase_rad": phase}
        if gaussian: source.update(waist_radius_m=waist, center_x_m=cx, center_y_m=cy)
        trains = {"analyzer": [polar("p1", 0.0)], "crossed": [polar("p1", 0.0), polar("p2", math.pi / 2)],
                  "middle": [polar("p1", 0.0), polar("pm", math.pi / 4), polar("p2", math.pi / 2)],
                  "qwp": [wave("w1", 0.0, math.pi / 2)], "hwp": [wave("w1", math.pi / 8, math.pi)], "identity": []}
        if preset == "qwp" and x == 1+0j and y == 0j: x, y = a+0j, a+0j
        experiment = {"schema_version": 1, "model_contract": "v2d_ideal_jones_same_plane_v1", "wavelength_m": 633e-9,
                      "grid": {"ny": ny, "nx": nx, "dy": 4e-6, "dx": 4e-6}, "source": source,
                      "coefficients": {"x": {"re": float(x.real), "im": float(x.imag)}, "y": {"re": float(y.real), "im": float(y.imag)}},
                      "elements": trains[preset] if elements is None else elements,
                      "readout": {"row": ny // 2 if row is None else row, "column": nx // 2 if column is None else column}}
        paths = {"wavelength_m": experiment["wavelength_m"], **{f"grid.{k}": v for k, v in experiment["grid"].items()},
                 **{f"source.{k}": v for k, v in source.items() if k != "kind"},
                 **{f"coefficients.{c}.{k}": v for c, pair in experiment["coefficients"].items() for k, v in pair.items()},
                 **{f"readout.{k}": v for k, v in experiment["readout"].items()},
                 **{f"elements.{i}.{k}": v for i, element in enumerate(experiment["elements"]) for k, v in element.items() if k not in ("id", "kind")}}
        return {"preset": preset, "experiment": experiment, "editor_inputs": {k: repr(v) for k, v in paths.items()}}
    cases = {"analyzer": case(), "analyzer_45": case(elements=[polar("p1", math.pi / 4)]),
             "qwp": case("qwp"), "qwp_shifted": case("qwp", phase=math.pi / 4), "hwp": case("hwp"),
             "crossed": case("crossed"), "middle": case("middle"), "identity": case("identity"),
             "arbitrary": case(elements=[polar("p1", math.pi / 4)], x=2+0j),
             "complex_coefficients": case("qwp", x=2-.3j, y=.7+1j, phase=.67),
             "gaussian": case("qwp", n=128, gaussian=True, cx=12e-6, cy=-8e-6),
             "asymmetric": case("qwp", gaussian=True, ny=3, nx=4, row=1, column=3, waist=10e-6, cx=4e-6, cy=-4e-6),
             "dark": case("qwp", amplitude=0.0), "both_zero": case("identity", x=0j, y=0j),
             "zero_coefficients_unusable_scalar_norm": case("identity", x=0j, y=0j, amplitude=1e300),
             "dark_sample": case("qwp", gaussian=True, waist=5e-6, cx=60e-6, cy=50e-6, row=0, column=0),
             "weak_pi2": case(elements=[polar("p1", math.pi / 2)]),
             "signed_angle": case(elements=[polar("p1", -.3712345678901234)], x=1+.2j, y=.7-.1j),
             "unwrapped_angle": case(elements=[polar("p1", 2*math.pi+.37)], x=1+.2j, y=.7-.1j)}
    mixed = [polar("p1", -.31), wave("w2", .41, math.pi / 2), polar("p3", .73), wave("w4", -.22, math.pi),
             polar("p5", -.6), wave("w6", .91, .83), polar("p7", .19), wave("w8", -.15, -.48)]
    cases["maximum_eight"] = case(elements=mixed, n=128, gaussian=True, x=1+.2j, y=.5j, cx=11e-6, cy=-7e-6, waist=95e-6)
    cases["order_PW"] = case(elements=[polar("p1", 0.0), wave("w1", math.pi / 4, math.pi / 2)])
    cases["order_WP"] = case(elements=[wave("w1", math.pi / 4, math.pi / 2), polar("p1", 0.0)])
    cases["middle_reordered"] = case("middle", elements=[polar("pm", math.pi / 4), polar("p1", 0.0), polar("p2", math.pi / 2)])
    cases["middle_reordered"]["reorder"] = ["pm", "up"]
    for offset in (-1e-6, -1e-9, 0.0, 1e-9, 1e-6):
        cases[f"weak_{offset!r}"] = case(elements=[polar("p1", math.pi / 2 + offset)])
    return cases


def envelope(experiment: dict) -> dict:
    return {"protocol_version": 1, "message_type": "polarization_submission", "request_id": str(uuid.uuid4()),
            "experiment": experiment, "experiment_sha256": digest(experiment)}


def genuine_case(label: str, fixture: dict) -> tuple[dict, list[np.ndarray]]:
    submitted = envelope(fixture["experiment"])
    status, data, mime = request("POST", "/api/v2d/validate", {**submitted, "experiment_sha256": None}, maximum=MAX_HEADER)
    validation = strict_json(data)
    assert status == 200 and mime == "application/json", data[:500]
    assert validation == {"protocol_version": 1, "message_type": "polarization_validation",
                          "request_id": submitted["request_id"], "experiment": submitted["experiment"], "experiment_sha256": submitted["experiment_sha256"]}
    started = time.perf_counter()
    status, data, mime = request("POST", "/api/v2d/simulate", submitted)
    elapsed = time.perf_counter() - started
    assert status == 200 and mime == "application/octet-stream", (label, status, data[:500])
    header, arrays = independent_decode(data)
    assert header["request_id"] == submitted["request_id"] and header["experiment"] == submitted["experiment"]
    incident = public_incident(submitted["experiment"])
    final, stages = public_train(incident, submitted["experiment"])
    direct = (incident.intensity, final.intensity, incident.grid.x, incident.grid.y)
    for index, array in enumerate(direct):
        assert arrays[index].tobytes() == array.astype("<f8", copy=False).tobytes(), f"{label}: exact actual public array {index}"
    assert header["stages"] == stages, f"{label}: actual captured public stage scalars and complex samples"
    row, column = submitted["experiment"]["readout"].values()
    indices = {(0, 0), (arrays[0].shape[0]-1, arrays[0].shape[1]-1), (row, column)}
    if arrays[0].size <= 20: indices = set(np.ndindex(arrays[0].shape))
    samples = [{"view": view, "row": r, "column": c, "x_m": float(arrays[2][c]), "y_m": float(arrays[3][r]), "intensity": float(arrays[view][r, c])}
               for view in range(2) for r, c in sorted(indices)]
    return {**fixture, "request_id": submitted["request_id"], "experiment_sha256": header["experiment_sha256"],
            "stages": stages, "readout": header["readout"], "ordered_stage_ids": header["ordered_stage_ids"],
            "intensity_max": header["intensity_max"], "samples": samples, "http_wall_s": elapsed,
            "response_bytes": len(data), "header_bytes": struct.unpack_from("<I", data, 8)[0],
            "intensity_sha256": [hashlib.sha256(array.tobytes()).hexdigest() for array in arrays[:2]],
            "exact_direct_public_v2c_match": True}, arrays


def genuine_sweep(fixture: dict, *, partial_index: int | None = None, failure_kind="numerical") -> dict:
    submitted = {**envelope(fixture["experiment"]), "message_type": "polarization_sweep_submission",
                 "selected_element_id": "p1", "angles_rad": ANGLES}
    started = time.perf_counter()
    status, data, mime = request("POST", "/api/v2d/sweep", submitted, maximum=MAX_JSON)
    elapsed = time.perf_counter() - started
    reply = strict_json(data)
    assert mime == "application/json"
    assert set(reply) == {"protocol_version", "message_type", "status", "request_id", "experiment_sha256", "sweep_sha256",
                          "experiment", "selected_element_id", "angles_rad", "ordered_stage_ids", "requested_count", "rows", "completed_count", "failed_index", "error"}
    assert reply["protocol_version"] == 1 and reply["message_type"] == "polarization_sweep_result"
    for key in ("request_id", "experiment", "experiment_sha256", "selected_element_id", "angles_rad"):
        assert reply[key] == submitted[key]
    assert reply["sweep_sha256"] == digest({key: submitted[key] for key in ("experiment", "selected_element_id", "angles_rad")})
    assert reply["ordered_stage_ids"] == ["input"] + [element["id"] for element in fixture["experiment"]["elements"]]
    assert reply["requested_count"] == 13
    if partial_index is None:
        assert status == 200 and reply["status"] == "complete" and reply["completed_count"] == 13
        assert reply["failed_index"] is None and reply["error"] is None
    else:
        assert status == (422 if failure_kind == "numerical" else 500) and reply["status"] == "failed"
        assert reply["failed_index"] == reply["completed_count"] == partial_index
        assert set(reply["error"]) == {"code", "message"}
        assert reply["error"]["code"] == ("numerical_failure" if failure_kind == "numerical" else "sweep_failed")
        assert 0 < len(reply["error"]["code"]) <= 64 and reply["error"]["code"].isascii()
        assert len(reply["error"]["message"]) <= 300
    assert len(reply["rows"]) == reply["completed_count"]
    incident = public_incident(fixture["experiment"])
    for index, actual in enumerate(reply["rows"]):
        final, stages = public_train(incident, fixture["experiment"], selected_id="p1", angle=ANGLES[index], samples=False)
        expected = {"index": index, "axis_angle_rad": ANGLES[index], "stages": stages,
                    "final_norm": final.sampled_norm, "incident_transmission_ratio": polarization.transmission_ratio(incident, final),
                    "total_delta": final.sampled_norm - incident.sampled_norm}
        assert actual == expected, f"genuine full-train restart row {index} differs from direct public V2c"
    return {"status_code": status, "response_bytes": len(data), "http_wall_s": elapsed, "reply": reply,
            "exact_direct_public_v2c_rows": True, "controlled_failure": partial_index is not None}


def run_acceptance(*, partial_index=None, failure_kind="numerical") -> dict:
    assert Path(sys.executable).resolve() == (ROOT / ".venv/Scripts/python.exe").resolve()
    assert Path(polarization.__file__).resolve().is_relative_to(ROOT / "src/ohlab")
    fixtures = fixture_cases()
    if partial_index is not None:
        return {"passed": True, "base_url": ORIGIN, "controlled_partial_failure": genuine_sweep(fixtures["analyzer"], partial_index=partial_index, failure_kind=failure_kind)}
    assert request("GET", "/api/v1/health", maximum=MAX_HEADER)[0] == 200
    status, index, _ = request("GET", "/", maximum=MAX_JSON)
    assert status == 200 and index == (ROOT / "frontend/bench/dist/index.html").read_bytes()
    assets = {}
    for url in re.findall(r'(?:src|href)="(/assets/[^\"]+)"', index.decode()):
        status, content, _ = request("GET", url, maximum=2_000_000)
        assert status == 200 and content == (ROOT / "frontend/bench/dist" / url.lstrip("/")).read_bytes()
        assets[url] = hashlib.sha256(content).hexdigest()
    assert assets
    reports = {}
    for label, fixture in fixtures.items():
        reports[label], _ = genuine_case(label, fixture)
    assert reports["qwp"]["stages"][0]["sample"] != reports["qwp"]["stages"][-1]["sample"]
    np.testing.assert_allclose(reports["qwp"]["intensity_max"], [1, 1], rtol=2e-13, atol=2e-13)
    for label, expected in (("qwp", (1/math.sqrt(2), 0.0)), ("qwp_shifted", (.5, -.5))):
        actual = reports[label]["stages"][-1]["sample"]
        np.testing.assert_allclose([actual["x"]["re"], actual["y"]["re"]], expected, rtol=0, atol=2e-15,
                                   err_msg="independent common-phase fixed-tau marker")
        reports[label]["fixed_tau0_expected"] = list(expected)
    sweeps = {label: genuine_sweep(fixtures[label]) for label in ("analyzer", "middle", "maximum_eight")}
    invalid = copy.deepcopy(fixtures["analyzer"]["experiment"]); invalid["grid"]["nx"] = 129
    assert request("POST", "/api/v2d/simulate", envelope(invalid), maximum=MAX_HEADER)[0] == 422
    unsupported = copy.deepcopy(fixtures["gaussian"]["experiment"]); unsupported["source"]["waist_z_m"] = 0
    assert request("POST", "/api/v2d/validate", {**envelope(unsupported), "experiment_sha256": None}, maximum=MAX_HEADER)[0] == 422
    assert request("POST", "/api/v2d/validate", envelope(invalid), maximum=MAX_HEADER, origin="http://127.0.0.1:8501")[0] == 403
    assert request("POST", "/api/v2d/validate", b" " * 32_769, maximum=MAX_HEADER)[0] == 413
    overflow = copy.deepcopy(fixtures["analyzer"]["experiment"]); overflow["source"]["amplitude"] = 1e300
    status, data, _ = request("POST", "/api/v2d/simulate", envelope(overflow), maximum=MAX_HEADER)
    assert status == 422 and strict_json(data)["error"]["code"] == "numerical_failure"
    independent = run_validation(n=64)
    assert independent["acceptance_passed"] and independent["tolerances"] == TOLERANCES
    return {"passed": True, "base_url": ORIGIN, "cases": reports, "sweeps": sweeps,
            "served_asset_sha256": assets, "independent_analytic_v2c": independent,
            "negative_http_checks": {"grid129": 422, "unsupported_gaussian_waist_z": 422, "other_origin": 403, "body32769": 413, "numerical_failure": 422},
            "limits": {"axis": 128, "elements": 8, "sample_records": 9, "request": 32768, "header": MAX_HEADER,
                       "payload": 264192, "frame": MAX_FRAME, "sweep_points": 13, "sweep_json": MAX_JSON},
            "provenance": {"interpreter": sys.executable, "polarization_source": str(Path(polarization.__file__).resolve()),
                "numpy": np.__version__, "scipy": importlib.metadata.version("scipy"),
                "sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in
                    (Path(polarization.__file__).resolve(), ROOT / "scripts/validate_v2c_polarization.py", Path(__file__).resolve())}},
            "exactness": "same-platform identical-input public V2c arrays/stages/samples; independent analytic references use unchanged explicit tolerances",
            "measurement_scope": "actual HTTP responses and independent public computations; excludes browser/GPU/whole-process memory"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--controlled-partial-index", type=int, choices=(0, 3, 12))
    parser.add_argument("--failure-kind", choices=("numerical", "unexpected"), default="numerical")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / "runs"):
        parser.error("Use a fresh owned ignored output under repository runs")
    report = run_acceptance(partial_index=args.controlled_partial_index, failure_kind=args.failure_kind)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream: json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps({"passed": True, "output": str(output), "cases": len(report.get("cases", {})),
                      "sweeps": len(report.get("sweeps", {})), "controlled_partial_index": args.controlled_partial_index}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
