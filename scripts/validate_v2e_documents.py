"""Independent V2e document/API/portable-browser evidence using public optics.

This script imports no application document parser, serializer, adapter or
transport decoder. Expected arrays are computed through the unchanged public
APIs. Evidence files are test artifacts, never product settings or qualification.
It starts no service/browser, installs nothing and uses fresh owned runs paths.
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
from urllib.parse import urlsplit
import uuid

import numpy as np
import ohlab.optics as optics
from ohlab.optics import SequentialExperiment, run_experiment, sample_source
from ohlab.optics.interference import TwoArmSpec, run_two_arm
import ohlab.optics.polarization as polarization

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/Scripts/python.exe"
MODES = ("sequential", "two_path", "polarization")
MODELS = {"sequential": "v0_aligned_scalar_forward_v1",
          "two_path": "v2b_unfolded_scalar_two_path_v1",
          "polarization": "v2d_ideal_jones_same_plane_v1"}
MAGIC = {"sequential": b"OHLABV1\0", "two_path": b"OHLAB2P\0", "polarization": b"OHLABPL\0"}
FRAME_CAPS = {"sequential": 2_359_296, "two_path": 4_218_896, "polarization": 280_592}
ROUTES = {"sequential": "/api/v1", "two_path": "/api/v2b", "polarization": "/api/v2d"}
NORM_NAMES = ("inputs", "split", "propagated", "combiner", "outputs")
DIAGNOSTICS = ("inputs_total", "split_total", "propagated_total", "combiner_total", "outputs_total",
               "split_delta", "propagation_delta", "phase_delta", "recombination_delta", "total_delta",
               "output_fractions", "total_output_ratio")


def canonical_bytes(value: object) -> bytes:
    """Independent declared document encoding; no product serializer import."""
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")


def scientific_digest(experiment: dict) -> str:
    encoded = json.dumps(experiment, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def strict_json(data: bytes) -> dict:
    def pairs(items):
        value = {}
        for key, item in items:
            assert key not in value, f"Duplicate decoded key: {key}"
            value[key] = item
        return value

    def constant(value):
        raise AssertionError(f"Nonstandard number: {value}")

    result = json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                        parse_constant=constant)
    pending = [result]
    while pending:
        item = pending.pop()
        if isinstance(item, dict): pending.extend(item.values())
        elif isinstance(item, list): pending.extend(item)
        elif isinstance(item, float): assert math.isfinite(item), "Nonfinite binary64"
    assert isinstance(result, dict)
    return result


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream: stream.write(data)


def write_json(path: Path, value: object) -> None:
    write_bytes(path, canonical_bytes(value))


def numeric_leaves(value: object, path: str = "") -> dict[str, str]:
    """Record actual finite numeric bits; integer fields retain their types."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items(): result.update(numeric_leaves(item, path + "/" + key))
        return result
    if isinstance(value, list):
        result = {}
        for index, item in enumerate(value): result.update(numeric_leaves(item, path + f"/{index}"))
        return result
    if type(value) is float:
        assert math.isfinite(value)
        return {path: "binary64:" + struct.pack(">d", value).hex()}
    if type(value) is int: return {path: "integer:" + str(value)}
    return {}


def assert_correspondence(expected: object, actual: object, path: str = "", *, zeros_equivalent: bool = True) -> None:
    """Exact scientific/text structure, with explicitly unsupported zero sign."""
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and set(actual) == set(expected), f"Fields differ at {path}"
        for key in expected: assert_correspondence(expected[key], actual[key], path + "/" + key, zeros_equivalent=zeros_equivalent)
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected), f"List differs at {path}"
        for index, (left, right) in enumerate(zip(expected, actual)):
            assert_correspondence(left, right, path + f"/{index}", zeros_equivalent=zeros_equivalent)
    elif type(expected) in (int, float) and type(actual) in (int, float):
        if type(expected) is int and path.rsplit("/", 1)[-1] in {"ny", "nx", "row", "column", "schema_version", "document_version", "protocol_version", "offset_bytes", "nbytes", "index"}:
            assert type(actual) is int and actual == expected, f"Integer differs at {path}"
        elif zeros_equivalent and expected == actual == 0:
            pass
        else:
            assert struct.pack(">d", float(expected)) == struct.pack(">d", float(actual)), f"Binary64 differs at {path}: {expected!r} vs {actual!r}"
    else:
        assert type(actual) is type(expected) and actual == expected, f"Value differs at {path}"


def fixture_documents() -> dict[str, dict]:
    """Nontrivial supported 5x8 Gaussian fixtures with authoritative SI values."""
    grid = {"ny": 5, "nx": 8, "dy": 5.100000000000001e-6, "dx": 2.3000000000000004e-6}
    source = {"kind": "gaussian", "amplitude": 0.8125000000000001,
              "phase_rad": 2 * math.pi + 0.17320508075688776,
              "waist_radius_m": 12.000000000000002e-6, "waist_z_m": -3.1000000000000004e-7,
              "center_x_m": 2.125000000000001e-6, "center_y_m": -3.3000000000000006e-6}
    sequential = {"schema_version": 1, "model_contract": MODELS["sequential"], "wavelength_m": 633.0000000000001e-9,
                  "grid": copy.deepcopy(grid), "source": copy.deepcopy(source), "components": [
                      {"id": "mask_b", "kind": "rectangular_aperture", "z_m": 0.0,
                       "width_m": 17.000000000000004e-6, "height_m": 23.000000000000004e-6},
                      {"id": "lens_neg", "kind": "thin_lens", "z_m": 1.0000000000000002e-6,
                       "focal_length_m": -0.020000000000000004},
                      {"id": "mask_a", "kind": "circular_aperture", "z_m": 2.0000000000000003e-6,
                       "radius_m": 11.000000000000002e-6}],
                  "observation": {"id": "screen_z", "z_m": 3.0000000000000005e-6}}
    two_path = {"wavelength_m": sequential["wavelength_m"], "grid": copy.deepcopy(grid), "source": copy.deepcopy(source),
                "two_arm_spec": {"arm_0_distance_m": 1.7000000000000002e-6,
                                 "arm_1_distance_m": 2.9000000000000006e-6,
                                 "relative_phase_rad": 7 * math.pi + 0.37000000000000005}}
    plane_source = copy.deepcopy(source); del plane_source["waist_z_m"]
    polarized = {"schema_version": 1, "model_contract": MODELS["polarization"],
                 "wavelength_m": sequential["wavelength_m"], "grid": copy.deepcopy(grid), "source": plane_source,
                 "coefficients": {"x": {"re": 2.2500000000000004, "im": -0.30000000000000004},
                                  "y": {"re": -0.7000000000000001, "im": 1.1000000000000003}},
                 "elements": [{"id": "wave_z", "kind": "linear_retarder", "axis_angle_rad": 0.27182818284590454,
                               "retardance_rad": 2 * math.pi + 0.9100000000000001},
                              {"id": "polar_b", "kind": "linear_polarizer", "axis_angle_rad": math.pi / 2 + 1e-9},
                              {"id": "wave_a", "kind": "linear_retarder", "axis_angle_rad": -0.42000000000000004,
                               "retardance_rad": -0.37000000000000005}], "readout": {"row": 1, "column": 6}}
    return {mode: {"document_format": "ohlab_virtual_experiment", "document_version": 1,
                   "mode": mode, "model_contract": MODELS[mode], "experiment": experiment,
                   "metadata": {"title": f"設定 {mode} 光學 \U0001f52c e\u0301 <b>文字</b>",
                                "notes": "設定而非結果\n保留 TAB\t與中文、補充平面 \U0001f680 及 combining e\u0301。"}}
            for mode, experiment in zip(MODES, (sequential, two_path, polarized))}


def source_plane(experiment: dict, mode: str) -> SequentialExperiment:
    source = copy.deepcopy(experiment["source"])
    if mode == "polarization" and source["kind"] == "gaussian": source["waist_z_m"] = 0.0
    return SequentialExperiment.from_dict({"schema_version": 1, "model_contract": MODELS["sequential"],
        "wavelength_m": experiment["wavelength_m"], "grid": experiment["grid"], "source": source,
        "components": [], "observation": {"id": "reference_plane", "z_m": 0.0}})


def direct_reference(mode: str, experiment: dict) -> tuple[dict, dict[str, np.ndarray]]:
    """Use public computations; no app numerical formulas or result helpers."""
    if mode == "sequential":
        spec = SequentialExperiment.from_dict(experiment)
        result = run_experiment(spec, record_fields=())
        arrays = {"intensity": result.observation.intensity, "x_m": spec.grid.x, "y_m": spec.grid.y}
        records = {"stages": [{name: getattr(stage, name) for name in
                    ("selector", "z_m", "norm", "previous_norm", "delta_norm", "transmission_ratio")}
                    for stage in result.stages], "intensity_max": float(arrays["intensity"].max())}
    elif mode == "two_path":
        plane = source_plane(experiment, mode); incident = sample_source(plane)
        result = run_two_arm(incident, spec=TwoArmSpec(**experiment["two_arm_spec"]))
        arrays = {"intensity_port_0": result.outputs[0].intensity, "intensity_port_1": result.outputs[1].intensity,
                  "x_m": incident.grid.x, "y_m": incident.grid.y}
        records = {"ports": ["port_0", "port_1"], "norms": {name: list(getattr(result.norms, name)) for name in NORM_NAMES},
                   "diagnostics": {name: list(getattr(result.norms, name)) if name == "output_fractions"
                                   else getattr(result.norms, name) for name in DIAGNOSTICS},
                   "intensity_max": [float(arrays[f"intensity_port_{port}"].max()) for port in range(2)]}
    else:
        assert mode == "polarization"
        scalar = sample_source(source_plane(experiment, mode)); coefficients = experiment["coefficients"]
        incident = polarization.JonesField.from_scalar(scalar,
            x_coefficient=complex(coefficients["x"]["re"], coefficients["x"]["im"]),
            y_coefficient=complex(coefficients["y"]["re"], coefficients["y"]["im"]))
        row, column = experiment["readout"]["row"], experiment["readout"]["column"]
        def stage(field, identifier, kind, previous=None):
            return {"stage_id": identifier, "kind": kind, "norm": field.sampled_norm,
                    "previous_norm": None if previous is None else previous.sampled_norm,
                    "delta_norm": None if previous is None else field.sampled_norm - previous.sampled_norm,
                    "adjacent_transmission_ratio": None if previous is None else polarization.transmission_ratio(previous, field),
                    "incident_transmission_ratio": polarization.transmission_ratio(incident, field),
                    "sample": {name: {"re": float(component.data[row, column].real), "im": float(component.data[row, column].imag)}
                               for name, component in (("x", field.x), ("y", field.y))}}
        current, stages = incident, [stage(incident, "input", "input")]
        for element in experiment["elements"]:
            output = (polarization.apply_linear_polarizer(current, axis_angle_rad=element["axis_angle_rad"])
                      if element["kind"] == "linear_polarizer" else polarization.apply_linear_retarder(current,
                          axis_angle_rad=element["axis_angle_rad"], retardance_rad=element["retardance_rad"]))
            stages.append(stage(output, element["id"], element["kind"], current)); current = output
        arrays = {"incident_intensity": incident.intensity, "final_intensity": current.intensity,
                  "x_m": incident.grid.x, "y_m": incident.grid.y}
        records = {"ordered_stage_ids": ["input"] + [item["id"] for item in experiment["elements"]], "stages": stages,
                   "readout": {"row": row, "column": column, "x_m": float(incident.grid.x[column]), "y_m": float(incident.grid.y[row])},
                   "intensity_max": [float(incident.intensity.max()), float(current.intensity.max())]}
    return records, {name: np.asarray(value, dtype="<f8").copy() for name, value in arrays.items()}


def independent_decode(mode: str, data: bytes) -> tuple[dict, dict[str, np.ndarray]]:
    """Decode all framing/descriptors/arrays without application decoder imports."""
    assert mode in MODES and 16 <= len(data) <= FRAME_CAPS[mode] and data[:8] == MAGIC[mode]
    length, reserved = struct.unpack_from("<II", data, 8)
    assert reserved == 0 and 0 < length <= 16_384
    start = 16 + ((length + 7) // 8) * 8
    assert start <= len(data) and data[16 + length:start] == bytes(start - 16 - length)
    header = strict_json(data[16:16 + length])
    common = {"protocol_version", "request_id", "experiment_sha256", "experiment", "arrays", "intensity_max"}
    extra = ({"stages"} if mode == "sequential" else
             {"message_type", "ports", "norms", "diagnostics"} if mode == "two_path" else
             {"message_type", "ordered_stage_ids", "stages", "readout"})
    assert set(header) == common | extra and header["protocol_version"] == 1
    if mode != "sequential": assert header["message_type"] == ("two_path_result" if mode == "two_path" else "polarization_result")
    identity = uuid.UUID(header["request_id"])
    assert identity.version == 4 and str(identity) == header["request_id"]
    assert header["experiment_sha256"] == scientific_digest(header["experiment"])
    grid = header["experiment"]["grid"]; ny, nx = grid["ny"], grid["nx"]
    assert type(ny) is int and type(nx) is int and 1 <= ny <= (128 if mode == "polarization" else 512) and 1 <= nx <= (128 if mode == "polarization" else 512)
    names = (["intensity"] if mode == "sequential" else ["intensity_port_0", "intensity_port_1"] if mode == "two_path" else ["incident_intensity", "final_intensity"]) + ["x_m", "y_m"]
    assert len(header["arrays"]) == len(names)
    arrays, offset = {}, 0
    for index, (descriptor, name) in enumerate(zip(header["arrays"], names)):
        intensity = name not in {"x_m", "y_m"}; shape = [ny, nx] if intensity else [nx] if name == "x_m" else [ny]
        count = math.prod(shape)
        expected = {"name": name, "dtype": "float64-le", "order": "C", "shape": shape,
                    "offset_bytes": offset, "nbytes": count * 8, "units": "amplitude_unit^2" if intensity else "m"}
        if mode != "sequential":
            expected["role"] = "intensity" if intensity else "coordinate"
            if mode == "two_path": expected["port_id"] = f"port_{index}" if intensity else None
            else: expected["stage_id"] = ("input" if index == 0 else header["ordered_stage_ids"][-1]) if intensity else None
        assert descriptor == expected, f"Descriptor mismatch for {name}"
        assert start + offset + count * 8 <= len(data)
        values = np.frombuffer(data, dtype="<f8", count=count, offset=start + offset).copy().reshape(shape)
        assert np.isfinite(values).all()
        if intensity: assert (values >= 0).all()
        arrays[name] = values; offset += count * 8
    assert start + offset == len(data), "Gap or undeclared/trailing payload"
    maxima = [float(arrays[name].max()) for name in names[:-2]]
    assert header["intensity_max"] == (maxima[0] if mode == "sequential" else maxima)
    return header, arrays


def compare_arrays(actual: dict[str, np.ndarray], expected: dict[str, np.ndarray]) -> dict:
    assert set(actual) == set(expected)
    report = {}
    for name, left in actual.items():
        right = expected[name]; assert left.shape == right.shape and left.dtype == right.dtype
        equal_bits = left.tobytes(order="C") == right.tobytes(order="C")
        differing = int(np.count_nonzero(left.view("<u8") != right.view("<u8")))
        report[name] = {"shape": list(left.shape), "elements": int(left.size), "bytes": int(left.nbytes),
                        "actual_sha256": hashlib.sha256(left.tobytes()).hexdigest(), "expected_sha256": hashlib.sha256(right.tobytes()).hexdigest(),
                        "differing_binary64_elements": differing, "maximum_absolute_difference": float(np.max(np.abs(left - right))),
                        "exact_binary64_match": equal_bits}
        assert equal_bits, f"Exact same-platform array comparison failed: {name}; {report[name]}"
    return report


def compare_result(mode: str, data: bytes, experiment: dict) -> dict:
    header, actual = independent_decode(mode, data)
    assert_correspondence(experiment, header["experiment"])
    records, expected = direct_reference(mode, experiment)
    for name, value in records.items(): assert_correspondence(value, header[name], "/" + name, zeros_equivalent=False)
    return {"request_id": header["request_id"], "experiment_sha256": header["experiment_sha256"],
            "response_bytes": len(data), "response_sha256": hashlib.sha256(data).hexdigest(),
            "arrays": compare_arrays(actual, expected), "all_scalar_stage_sample_records_exact": True,
            "records": records, "numeric_leaves": numeric_leaves(header["experiment"])}


def request(base_url: str, path: str, data: bytes, *, maximum: int = 32_768) -> tuple[int, bytes, dict[str, str]]:
    """Only the approved fixed loopback; no service launch or alternate port."""
    assert base_url == "http://127.0.0.1:8510", "Only the task-owned approved loopback is supported"
    parsed = urlsplit(base_url)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=30)
    try:
        connection.request("POST", path, body=data, headers={"Content-Type": "application/json", "Origin": base_url})
        response = connection.getresponse(); body = response.read(maximum + 1)
        assert len(body) <= maximum, "Response exceeds route cap"
        headers = {key.lower(): value for key, value in response.getheaders()}
        if "content-length" in headers: assert int(headers["content-length"]) == len(body)
        return response.status, body, headers
    finally:
        connection.close()


def envelope(mode: str, experiment: dict) -> dict:
    value = {"request_id": str(uuid.uuid4()), "experiment": experiment}
    if mode != "sequential":
        value.update(protocol_version=1, message_type="two_path_submission" if mode == "two_path" else "polarization_submission")
    if mode == "polarization": value["experiment_sha256"] = None
    return value


def check_document_reply(document: dict, data: bytes, headers: dict[str, str]) -> dict:
    assert 0 < len(data) <= 32_768 and not data.startswith(b"\xef\xbb\xbf")
    actual = strict_json(data); assert_correspondence(document, actual)
    assert data == canonical_bytes(actual), "Canonical output differs from independent declared encoding"
    assert headers.get("content-type", "").split(";", 1)[0] == "application/json"
    assert headers.get("cache-control") == "no-store"
    assert headers.get("x-ohlab-experiment-sha256") == scientific_digest(actual["experiment"])
    return actual


def api_acceptance(output: Path, base_url: str, documents: dict[str, dict]) -> dict:
    """Validate canonical documents, ordinary compute identity and all payloads."""
    reports = {}
    for mode, document in documents.items():
        destination = output / mode; submitted = canonical_bytes(document)
        status, canonical, headers = request(base_url, "/api/v2e/documents/validate", submitted)
        assert status == 200, (mode, status, canonical[:400])
        validated = check_document_reply(document, canonical, headers)
        write_bytes(destination / "canonical_document.json", canonical)
        status2, repeated, headers2 = request(base_url, "/api/v2e/documents/validate", canonical)
        assert status2 == 200 and repeated == canonical and headers2["x-ohlab-experiment-sha256"] == headers["x-ohlab-experiment-sha256"]
        metadata = copy.deepcopy(validated); metadata["metadata"]["title"] += " metadata only"
        status3, changed, changed_headers = request(base_url, "/api/v2e/documents/validate", canonical_bytes(metadata))
        assert status3 == 200 and changed != canonical
        assert changed_headers["x-ohlab-experiment-sha256"] == headers["x-ohlab-experiment-sha256"], "Metadata must not alter scientific digest"
        ordinary = envelope(mode, validated["experiment"])
        status4, validation_body, validation_headers = request(base_url, ROUTES[mode] + "/validate", canonical_bytes(ordinary))
        assert status4 == 200 and validation_headers["content-type"].split(";", 1)[0] == "application/json", validation_body[:400]
        validation = strict_json(validation_body)
        assert validation["request_id"] == ordinary["request_id"]
        assert validation["experiment_sha256"] == headers["x-ohlab-experiment-sha256"]
        assert_correspondence(validated["experiment"], validation["experiment"])
        if mode == "polarization": ordinary["experiment_sha256"] = validation["experiment_sha256"]
        started = time.perf_counter()
        status5, frame, result_headers = request(base_url, ROUTES[mode] + "/simulate", canonical_bytes(ordinary), maximum=FRAME_CAPS[mode])
        elapsed = time.perf_counter() - started
        assert status5 == 200 and result_headers["content-type"].split(";", 1)[0] == "application/octet-stream", (mode, status5, frame[:400])
        result = compare_result(mode, frame, validated["experiment"])
        assert result["request_id"] == ordinary["request_id"] and result["experiment_sha256"] == validation["experiment_sha256"]
        write_json(destination / "api_request.json", ordinary); write_bytes(destination / "api_response.bin", frame)
        write_json(destination / "ordinary_validation.json", validation)
        reports[mode] = {"document_bytes": len(canonical), "document_sha256": hashlib.sha256(canonical).hexdigest(),
                         "document_headers": headers, "canonical_idempotent": True, "metadata_digest_unchanged": True,
                         "ordinary_validation_digest_matches": True, "compute_used_ordinary_validation": True,
                         "http_wall_s": elapsed, "result": result}
    negatives = {}
    baseline = documents["polarization"]
    cases = []
    def altered(name, mutate, status, code):
        value = copy.deepcopy(baseline); mutate(value)
        cases.append((name, canonical_bytes(value), status, code))
    altered("version", lambda value: value.update(document_version=2), 422, "unsupported_document_version")
    altered("mode", lambda value: value.update(mode="universal"), 422, "unsupported_document_mode")
    altered("model", lambda value: value.update(model_contract="unsupported"), 422, "unsupported_model_contract")
    altered("imported_status", lambda value: value.update(status="complete"), 422, "invalid_document")
    altered("unknown_nested", lambda value: value["experiment"]["readout"].update(result=True), 422, "invalid_experiment")
    altered("bool_numeric", lambda value: value["experiment"]["coefficients"]["x"].update(re=True), 422, "invalid_experiment")
    altered("invalid_domain", lambda value: value["experiment"]["grid"].update(nx=129), 422, "invalid_experiment")
    altered("metadata_scalar_length", lambda value: value["metadata"].update(title="\U0001f680" * 121), 422, "invalid_metadata")
    altered("forbidden_CR", lambda value: value["metadata"].update(notes="literal\rCR"), 422, "invalid_metadata")
    encoded = canonical_bytes(baseline)
    cases.extend((("BOM", b"\xef\xbb\xbf" + encoded, 400, "invalid_json"), ("invalid_utf8", b"\xff", 400, "invalid_json"),
                  ("truncated", encoded[:-3], 400, "invalid_json"), ("duplicate_decoded_key", b'{"mode":0,"m\\u006fde":1}', 400, "invalid_json"),
                  ("underflow", encoded.replace(b'2.2500000000000004', b'1e-999'), 400, "invalid_json"),
                  ("nonstandard", b'{"value":NaN}', 400, "invalid_json"), ("overflow", b'{"value":1e999}', 400, "invalid_json"),
                  ("oversized", b" " * 32_769, 413, "body_too_large")))
    for name, raw, expected_status, expected_code in cases:
        status, body, _ = request(base_url, "/api/v2e/documents/validate", raw)
        error = strict_json(body)
        assert status == expected_status and error["error"]["code"] == expected_code, (name, status, error)
        assert set(error) == {"protocol_version", "request_id", "error"} and error["request_id"] is None
        assert len(error["error"]["message"]) <= 300
        negatives[name] = {"status": status, "code": error["error"]["code"], "request_bytes": len(raw)}
    return {"modes": reports, "raw_and_domain_rejections": negatives}


def owned_path(root: Path, relative: object) -> Path:
    assert isinstance(relative, str) and relative and not Path(relative).is_absolute()
    resolved = (root / relative).resolve()
    assert resolved.is_relative_to(root.resolve()) and resolved.is_file(), f"Non-owned evidence path: {relative}"
    return resolved


def browser_acceptance(directory: Path) -> dict:
    """Read actual browser captures and compare original/restored/public results."""
    manifest = strict_json((directory / "portability.json").read_bytes())
    assert set(manifest["modes"]) == set(MODES)
    reports = {}
    required = ("original_request", "original_response", "restored_request", "restored_response", "downloaded", "moved", "reexported")
    for mode in MODES:
        entry = manifest["modes"][mode]
        assert set(required) <= set(entry)
        paths = {name: owned_path(directory, entry[name]) for name in required}
        original = strict_json(paths["original_request"].read_bytes()); restored = strict_json(paths["restored_request"].read_bytes())
        assert original["request_id"] != restored["request_id"], "Restoration must generate a fresh request identity"
        assert_correspondence(original["experiment"], restored["experiment"])
        first = compare_result(mode, paths["original_response"].read_bytes(), original["experiment"])
        second = compare_result(mode, paths["restored_response"].read_bytes(), restored["experiment"])
        assert first["request_id"] == original["request_id"] and second["request_id"] == restored["request_id"]
        first_header, first_arrays = independent_decode(mode, paths["original_response"].read_bytes())
        second_header, second_arrays = independent_decode(mode, paths["restored_response"].read_bytes())
        for key in first_header.keys() - {"request_id"}:
            assert_correspondence(first_header[key], second_header[key], "/" + key, zeros_equivalent=False)
        direct_original_vs_restored = compare_arrays(second_arrays, first_arrays)
        downloaded, moved, reexported = (paths[name].read_bytes() for name in ("downloaded", "moved", "reexported"))
        assert downloaded == moved == reexported, "Canonical prepared file must survive move and unchanged reexport byte-identically"
        document = strict_json(downloaded)
        assert set(document) == {"document_format", "document_version", "mode", "model_contract", "experiment", "metadata"}
        assert document["document_format"] == "ohlab_virtual_experiment" and document["document_version"] == 1
        assert document["mode"] == mode and document["model_contract"] == MODELS[mode]
        assert downloaded == canonical_bytes(document) and len(downloaded) <= 32_768
        assert_correspondence(original["experiment"], document["experiment"])
        reports[mode] = {"paths": entry, "document_bytes": len(downloaded), "document_sha256": hashlib.sha256(downloaded).hexdigest(),
                         "moved_and_reexported_bytes_exact": True, "nonzero_scientific_bits_and_structure_exact": True,
                         "fresh_request_identity": True, "original_vs_restored_arrays": direct_original_vs_restored,
                         "original_vs_public": first, "restored_vs_public": second}
    return reports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--base-url", help="Explicitly collect current API evidence from http://127.0.0.1:8510")
    parser.add_argument("--browser-evidence-dir", type=Path, help="Read actual seven-path portability.json captures")
    args = parser.parse_args()
    if Path(sys.executable).resolve() != PYTHON.resolve(): parser.error("Use the existing repository interpreter")
    output = args.output_dir.resolve()
    if output.exists() or output == ROOT / "runs" or not output.is_relative_to(ROOT / "runs"):
        parser.error("Use a fresh owned ignored output directory under repository runs")
    if args.base_url is not None and args.base_url != "http://127.0.0.1:8510": parser.error("Only approved fixed loopback is supported")
    browser = args.browser_evidence_dir.resolve() if args.browser_evidence_dir else None
    if browser is not None and not browser.is_relative_to(ROOT / "runs"): parser.error("Browser evidence must be owned under repository runs")
    assert Path(optics.__file__).resolve().is_relative_to(ROOT / "src/ohlab"), "Public numerical source is not checkout-owned"
    output.mkdir(parents=True, exist_ok=False)
    documents = fixture_documents(); fixtures, failure = {}, None
    report = {"interpreter": sys.executable, "public_source": optics.__file__,
              "versions": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "starlette", "uvicorn")},
              "claim": "same-platform identical-input full-array/scalar fidelity, not optical accuracy or qualified replay",
              "api_executed": False, "browser_captures_compared": False}
    try:
        for mode, document in documents.items():
            destination = output / mode
            write_json(destination / "fixture_document.json", document)
            records, arrays = direct_reference(mode, document["experiment"])
            direct = {"records": records, "arrays": {}}
            for name, array in arrays.items():
                relative = f"{mode}/direct_{name}.f64"
                write_bytes(output / relative, array.tobytes(order="C"))
                direct["arrays"][name] = {"path": relative, "shape": list(array.shape), "dtype": "float64-le",
                                          "elements": int(array.size), "bytes": int(array.nbytes),
                                          "sha256": hashlib.sha256(array.tobytes()).hexdigest()}
            fixtures[mode] = {"document": document, "canonical_file": f"{mode}/fixture_document.json",
                              "numeric_leaves": numeric_leaves(document["experiment"]), "direct": direct}
        write_json(output / "fixtures.json", fixtures)
        if args.base_url:
            report["api"] = api_acceptance(output, args.base_url, documents); report["api_executed"] = True
        if browser:
            report["browser"] = browser_acceptance(browser); report["browser_captures_compared"] = True
    except Exception as exc:
        failure = {"type": type(exc).__name__, "message": str(exc)}
        report["failure"] = failure
        print(f"STOPPED: {type(exc).__name__}: {exc}", file=sys.stderr)
    report["complete"] = failure is None
    write_json(output / "summary.json", report)
    print(f"fixtures={len(fixtures)}; api_executed={report['api_executed']}; browser_captures_compared={report['browser_captures_compared']}; complete={report['complete']}")
    return 0 if failure is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
