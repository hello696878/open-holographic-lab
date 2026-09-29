"""M5 integrity, transaction, ownership and actual replay contracts.

Exact comparisons deliberately include shape, dtype representation and logical
C-order bytes. These tests do not substitute approximate numerical agreement
for the declared same-environment replay criterion. Test manifests and malformed
payloads are constructed with stdlib/NumPy independently of production helpers.
All filesystem fixtures belong to pytest's dedicated temporary directory.
"""

from __future__ import annotations

import builtins
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import runpy
import shutil
import struct
import subprocess
import sys
from types import SimpleNamespace
import zlib

import numpy as np
import pytest

from ohlab import metrics
from ohlab.algorithms import gerchberg_saxton
from ohlab.grid import SamplingGrid
from ohlab.io import artifacts
from ohlab.io.config import RunConfig


# Synthetic caller-supplied provenance exercises the qualification policy; this
# is expressly not attestation that this SHA names the executing candidate code.
SOURCE = {"revision": "1" * 40, "state": "clean", "method": "caller"}
ALL_METRICS = {
    "intensity_mse": {},
    "intensity_nmse": {},
    "intensity_psnr": {"data_range": 1.0},
    "signal_region_power_fraction": {"mask": "signal_mask.npy"},
    "regional_intensity_cv": {"mask": "cv_mask.npy"},
}
BASE_ROLES = {
    "target_intensity", "target_amplitude", "source_amplitude", "source_field",
    "phase", "reconstruction_field", "reconstruction_intensity", "residual_history",
}


def _settings(mode="seed", iterations=5, distance=2e-4, metrics_settings=None):
    initialization = (
        {"mode": "seed", "seed": 7} if mode == "seed" else
        {"mode": "explicit_phase", "artifact": "initial_phase.npy"}
    )
    return {
        "schema_version": 1,
        "grid": {"ny": 3, "nx": 5, "dy_m": 10e-6, "dx_m": 8e-6},
        "optics": {"wavelength_m": 633e-9, "distance_m": distance},
        "solver": {
            "algorithm": "gerchberg_saxton", "contract": "m3_periodic_lossless_asm_v1",
            "iterations": iterations, "initialization": initialization,
        },
        "metrics": copy.deepcopy(ALL_METRICS if metrics_settings is None else metrics_settings),
    }


def _inputs():
    codes = np.array([[0, 16, 32, 64, 255], [128, 192, 8, 48, 96], [224, 16, 64, 128, 192]], dtype=np.uint8)
    target = codes.astype(np.float64) / 255.0
    amplitude = np.sqrt(target)
    source = np.full(target.shape, np.sqrt(np.sum(amplitude**2) / target.size), dtype=np.float64)
    initial = np.linspace(-7.0, 8.0, target.size).reshape(target.shape)
    signal = np.array([[True, False, True, False, False], [False, True, False, True, False], [True, False, False, False, True]])
    cv = np.array([[False, True, False, True, False], [True, False, True, False, False], [False, True, True, False, False]])
    return target, source, initial, signal, cv


def _save(path, *, mode="seed", iterations=5, distance=2e-4, metric_settings=None, source_revision=SOURCE, input_png=None):
    settings = _settings(mode, iterations, distance, metric_settings)
    target, source, initial, signal, cv = _inputs()
    kwargs = {
        "config": RunConfig(settings), "target_intensity": target,
        "source_amplitude": source, "source_revision": copy.deepcopy(source_revision),
    }
    if mode == "explicit_phase":
        kwargs["initial_phase"] = initial
    if "signal_region_power_fraction" in settings["metrics"]:
        kwargs["signal_mask"] = signal
    if "regional_intensity_cv" in settings["metrics"]:
        kwargs["cv_mask"] = cv
    if input_png is not None:
        kwargs["input_png"] = input_png
    return artifacts.run_and_save_bundle(path, **kwargs)


def _assert_bits(actual, expected):
    assert type(actual) is np.ndarray
    assert actual.shape == expected.shape
    assert actual.dtype == expected.dtype and actual.dtype.str == expected.dtype.str
    assert actual.tobytes(order="C") == expected.tobytes(order="C")


def _snapshot(array):
    return array.shape, array.dtype.str, array.strides, array.flags.writeable, array.tobytes(order="C")


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _json(path):
    return json.loads(path.read_bytes().decode("utf-8"))


def _rehash(bundle_path, filename, payload):
    """Alter one controlled fixture artifact and independently rehash it."""
    (bundle_path / filename).write_bytes(payload)
    manifest = _json(bundle_path / "manifest.json")
    matches = [entry for entry in manifest["artifacts"] if entry["path"] == filename]
    assert len(matches) == 1
    matches[0]["size_bytes"] = len(payload)
    matches[0]["sha256"] = hashlib.sha256(payload).hexdigest()
    (bundle_path / "manifest.json").write_bytes(_json_bytes(manifest))


def _npy_bytes(array, *, version=(1, 0)):
    stream = io.BytesIO()
    np.lib.format.write_array(stream, array, version=version, allow_pickle=True)
    return stream.getvalue()


def _png_bytes(codes):
    """Independent tiny static grayscale PNG fixture, not a production encoder."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    height, width = codes.shape
    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    pixels = b"".join(b"\x00" + row.tobytes() for row in codes)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")


def _assert_no_partial(parent):
    assert not [path for path in parent.iterdir() if path.name.startswith(".ohlab-partial-")]


@pytest.mark.parametrize("mode", ["seed", "explicit_phase"])
@pytest.mark.parametrize("iterations", [0, 5])
@pytest.mark.parametrize("distance", [-2e-4, 0.0, 2e-4])
def test_twelve_case_same_environment_replay_is_literal_and_individually_reported(tmp_path, mode, iterations, distance):
    path = tmp_path / "run"
    bundle = _save(path, mode=mode, iterations=iterations, distance=distance)
    integrity = artifacts.verify_run_bundle(path)
    assert integrity.status == "passed"
    assert tuple(sorted(integrity.files)) == integrity.files
    report = artifacts.replay_run_bundle(path, source_revision=SOURCE)
    assert report.integrity == "passed"
    assert report.qualification == "qualified"
    assert report.comparison == "passed"
    assert not report.qualification_reasons
    assert report.checks and all(value is True for value in report.checks.values())
    assert report.current_source["method"] == "caller"
    assert report.recorded_source["method"] == "caller"
    expected_roles = BASE_ROLES | {"signal_mask", "cv_mask"}
    if mode == "explicit_phase":
        expected_roles.add("initial_phase")
    assert set(bundle.arrays) == expected_roles
    target, source, initial, signal, cv = _inputs()
    grid = SamplingGrid(ny=3, nx=5, dy=10e-6, dx=8e-6)
    kwargs = {"seed": 7} if mode == "seed" else {"initial_phase": initial}
    reference = gerchberg_saxton(target_amplitude=np.sqrt(target), source_amplitude=source, grid=grid, wavelength_m=633e-9, distance_m=distance, iterations=iterations, **kwargs)
    expected = {
        "target_intensity": target, "target_amplitude": np.sqrt(target), "source_amplitude": source,
        "source_field": reference.source_field.data, "phase": reference.phase,
        "reconstruction_field": reference.reconstruction.data,
        "reconstruction_intensity": reference.reconstruction.intensity,
        "residual_history": reference.residual_history, "signal_mask": signal, "cv_mask": cv,
    }
    if mode == "explicit_phase":
        expected["initial_phase"] = initial
    for name, array in expected.items():
        _assert_bits(bundle.arrays[name], array)
    assert bundle.arrays["residual_history"].shape == (iterations + 1,)
    _assert_no_partial(tmp_path)


def test_manifest_hashes_raw_files_with_exact_sorted_inventory(tmp_path):
    path = tmp_path / "run"
    _save(path)
    manifest = _json(path / "manifest.json")
    assert set(manifest) == {"schema_version", "hash_algorithm", "artifacts"}
    assert manifest["schema_version"] == 1 and manifest["hash_algorithm"] == "sha256"
    entries = manifest["artifacts"]
    names = [entry["path"] for entry in entries]
    assert names == sorted(names) and len(set(names)) == len(names)
    assert set(names) == {entry.name for entry in path.iterdir()} - {"manifest.json"}
    assert {"config.json", "metrics.json"} <= set(names)
    for entry in entries:
        raw = (path / entry["path"]).read_bytes()
        assert entry["size_bytes"] == len(raw)
        assert entry["sha256"] == hashlib.sha256(raw).hexdigest()
        if entry["path"].endswith(".npy"):
            assert set(entry) == {"logical_name", "path", "size_bytes", "sha256", "dtype", "shape", "order"}
            assert entry["logical_name"] + ".npy" == entry["path"]
            assert raw[:8] == b"\x93NUMPY\x01\x00"
            stream = io.BytesIO(raw)
            np.lib.format.read_magic(stream)
            shape, fortran, dtype = np.lib.format.read_array_header_1_0(stream, max_header_size=10000)
            assert list(shape) == entry["shape"] and dtype.str == entry["dtype"]
            assert fortran is False and entry["order"] == "C"
            assert stream.tell() + math.prod(shape) * dtype.itemsize == len(raw)
        else:
            assert set(entry) == {"logical_name", "path", "size_bytes", "sha256"}


def test_json_bytes_are_deterministic_utf8_lf_and_have_final_newline(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    _save(first)
    _save(second)
    for filename in ("config.json", "metrics.json", "manifest.json"):
        raw = (first / filename).read_bytes()
        assert raw.endswith(b"\n") and b"\r" not in raw
        document = json.loads(raw.decode("utf-8"))
        assert raw == _json_bytes(document)
        assert raw == (second / filename).read_bytes()


@pytest.mark.parametrize("layout", ["c", "fortran", "strided", "readonly"])
def test_input_capture_preserves_bits_and_does_not_mutate_or_share_layouts(tmp_path, layout):
    target, source, initial, signal, cv = _inputs()
    target[0, 0] = -0.0
    initial[0, 0] = -0.0
    arrays = [target, source, initial, signal, cv]
    if layout == "fortran":
        arrays = [np.asfortranarray(array) for array in arrays]
    elif layout == "strided":
        views = []
        for array in arrays:
            backing = np.zeros((6, 10), dtype=array.dtype)
            backing[::2, ::2] = array
            views.append(backing[::2, ::2])
        arrays = views
    elif layout == "readonly":
        for array in arrays:
            array.setflags(write=False)
    before = [_snapshot(array) for array in arrays]
    target, source, initial, signal, cv = arrays
    bundle = artifacts.run_and_save_bundle(tmp_path / "run", config=RunConfig(_settings("explicit_phase")), target_intensity=target, source_amplitude=source, initial_phase=initial, signal_mask=signal, cv_mask=cv, source_revision=SOURCE)
    for name, array in zip(("target_intensity", "source_amplitude", "initial_phase", "signal_mask", "cv_mask"), arrays):
        _assert_bits(bundle.arrays[name], array)
        assert not np.shares_memory(bundle.arrays[name], array)
        assert bundle.arrays[name].flags.c_contiguous
    assert [_snapshot(array) for array in arrays] == before


def test_all_inputs_are_snapshotted_before_solver_and_only_one_solve_occurs(tmp_path, monkeypatch):
    target, source, initial, signal, cv = _inputs()
    originals = [target, source, initial, signal, cv]
    expected = [array.copy() for array in originals]
    real_solver = artifacts.gerchberg_saxton
    calls = []
    def intercept(**kwargs):
        calls.append(kwargs)
        for name, original in (("source_amplitude", source), ("initial_phase", initial)):
            assert kwargs[name].flags.c_contiguous and kwargs[name].flags.owndata
            assert not np.shares_memory(kwargs[name], original)
        target[:] = 0.9
        source[:] = 99.0
        initial[:] = 17.0
        signal[:] = False
        cv[:] = False
        return real_solver(**kwargs)
    monkeypatch.setattr(artifacts, "gerchberg_saxton", intercept)
    bundle = artifacts.run_and_save_bundle(tmp_path / "run", config=RunConfig(_settings("explicit_phase")), target_intensity=target, source_amplitude=source, initial_phase=initial, signal_mask=signal, cv_mask=cv, source_revision=SOURCE)
    assert len(calls) == 1
    for name, array in zip(("target_intensity", "source_amplitude", "initial_phase", "signal_mask", "cv_mask"), expected):
        _assert_bits(bundle.arrays[name], array)


def test_loaded_arrays_are_owned_readonly_and_mappings_cannot_be_reassigned(tmp_path):
    path = tmp_path / "run"
    saved = _save(path)
    loaded = artifacts.load_run_bundle(path)
    for name, array in loaded.arrays.items():
        assert array.flags.owndata and array.flags.c_contiguous and not array.flags.writeable
        assert not np.shares_memory(array, saved.arrays[name])
        _assert_bits(array, saved.arrays[name])
        with pytest.raises(ValueError):
            array.flat[0] = 0
    with pytest.raises(TypeError):
        loaded.arrays["phase"] = np.zeros((3, 5))
    with pytest.raises(TypeError):
        loaded.metrics["intensity_mse"] = 0.0
    software = loaded.software
    software["tampered"] = True
    assert "tampered" not in loaded.software
    assert loaded.path == path


def test_saved_metrics_use_persisted_actual_intensity_and_distinct_masks(tmp_path):
    bundle = _save(tmp_path / "run")
    target = bundle.arrays["target_intensity"]
    reconstruction = bundle.arrays["reconstruction_intensity"]
    expected = {
        "intensity_mse": metrics.intensity_mse(target_intensity=target, reconstruction_intensity=reconstruction),
        "intensity_nmse": metrics.intensity_nmse(target_intensity=target, reconstruction_intensity=reconstruction),
        "intensity_psnr": metrics.intensity_psnr(target_intensity=target, reconstruction_intensity=reconstruction, data_range=1.0),
        "signal_region_power_fraction": metrics.signal_region_power_fraction(reconstruction_intensity=reconstruction, signal_mask=bundle.arrays["signal_mask"]),
        "regional_intensity_cv": metrics.regional_intensity_cv(intensity=reconstruction, mask=bundle.arrays["cv_mask"]),
    }
    assert not np.array_equal(bundle.arrays["signal_mask"], bundle.arrays["cv_mask"])
    for name, value in expected.items():
        assert type(bundle.metrics[name]) is float
        assert struct.pack(">d", bundle.metrics[name]) == struct.pack(">d", value)


def test_infinite_psnr_uses_only_documented_standard_json_string(tmp_path):
    settings = _settings("explicit_phase", 0, 0.0, {"intensity_mse": {}, "intensity_psnr": {"data_range": 1.0}})
    bundle = artifacts.run_and_save_bundle(tmp_path / "run", config=RunConfig(settings), target_intensity=np.full((3, 5), 0.25), source_amplitude=np.full((3, 5), 0.5), initial_phase=np.zeros((3, 5)), source_revision=SOURCE)
    assert bundle.metrics["intensity_mse"] == 0.0
    assert bundle.metrics["intensity_psnr"] == math.inf
    document = _json(tmp_path / "run" / "metrics.json")
    assert document == {"schema_version": 1, "values": {"intensity_mse": 0.0, "intensity_psnr": "+inf"}}
    assert artifacts.load_run_bundle(tmp_path / "run").metrics["intensity_psnr"] == math.inf
    assert artifacts.replay_run_bundle(tmp_path / "run", source_revision=SOURCE).comparison == "passed"


def test_valid_m4_fraction_rounding_above_one_is_preserved_without_clipping(tmp_path):
    rng = np.random.default_rng(0)
    target = np.zeros((8, 16), dtype=np.float64)
    indices = rng.choice(target.size, 64, replace=False)
    target.flat[indices] = np.exp(rng.uniform(-25.0, 0.0, 64))
    source, mask = np.sqrt(target), target > 0.0
    settings = _settings("explicit_phase", 0, 0.0, {"signal_region_power_fraction": {"mask": "signal_mask.npy"}})
    settings["grid"].update(ny=8, nx=16)
    path = tmp_path / "run"
    bundle = artifacts.run_and_save_bundle(path, config=RunConfig(settings), target_intensity=target, source_amplitude=source, initial_phase=np.zeros_like(target), signal_mask=mask, source_revision=SOURCE)
    expected = metrics.signal_region_power_fraction(reconstruction_intensity=bundle.arrays["reconstruction_intensity"], signal_mask=mask)
    # Full and selected reductions use different orders for this sparse case;
    # unchanged M4 deliberately preserves the resulting one-ULP overshoot.
    assert expected == 1.0000000000000002
    assert bundle.metrics["signal_region_power_fraction"] == expected
    assert artifacts.load_run_bundle(path).metrics["signal_region_power_fraction"] == expected
    report = artifacts.replay_run_bundle(path, source_revision=SOURCE)
    assert report.qualification == "qualified" and report.comparison == "passed"


@pytest.mark.parametrize("metric_settings,optional", [({}, set()), ({"intensity_mse": {}}, set()), ({"signal_region_power_fraction": {"mask": "signal_mask.npy"}}, {"signal_mask"}), ({"regional_intensity_cv": {"mask": "cv_mask.npy"}}, {"cv_mask"})])
def test_conditional_inventory_contains_only_used_masks_and_metrics(tmp_path, metric_settings, optional):
    bundle = _save(tmp_path / "run", metric_settings=metric_settings)
    assert set(bundle.arrays) == BASE_ROLES | optional
    assert set(bundle.metrics) == set(metric_settings)
    assert not (tmp_path / "run" / "input_target.png").exists()
    assert not (tmp_path / "run" / "initial_phase.npy").exists()


def test_modified_payload_is_detected_before_any_array_decode_or_solver_call(tmp_path, monkeypatch):
    path = tmp_path / "run"
    _save(path)
    file = path / "target_intensity.npy"
    payload = bytearray(file.read_bytes())
    payload[-1] ^= 1
    file.write_bytes(payload)
    def forbidden(*args, **kwargs):
        pytest.fail("corrupted bytes reached numerical decoding or the solver")
    monkeypatch.setattr(artifacts.np, "load", forbidden)
    monkeypatch.setattr(artifacts, "gerchberg_saxton", forbidden)
    for function in (artifacts.verify_run_bundle, artifacts.load_run_bundle, artifacts.replay_run_bundle):
        with pytest.raises(ValueError, match="digest|SHA|sha256|hash"):
            function(path)


@pytest.mark.parametrize("filename", ["config.json", "metrics.json", "source_field.npy"])
def test_modified_metadata_and_numerical_files_are_all_hashed(tmp_path, filename):
    path = tmp_path / "run"
    _save(path)
    file = path / filename
    file.write_bytes(file.read_bytes() + b" ")
    with pytest.raises(ValueError):
        artifacts.verify_run_bundle(path)


@pytest.mark.parametrize("change", ["missing", "extra_file", "extra_directory"])
def test_inventory_rejects_missing_and_extra_entries(tmp_path, change):
    path = tmp_path / "run"
    _save(path)
    if change == "missing":
        (path / "phase.npy").unlink()
    elif change == "extra_file":
        (path / "unexpected.txt").write_text("outside the manifest", encoding="utf-8")
    else:
        (path / "unexpected").mkdir()
    with pytest.raises(ValueError):
        artifacts.verify_run_bundle(path)


@pytest.mark.parametrize("change", ["duplicate_entry", "duplicate_logical_name", "wrong_role_path", "self_hash", "wrong_order"])
def test_manifest_rejects_ambiguous_roles_and_nondeterministic_inventory(tmp_path, change):
    path = tmp_path / "run"
    _save(path)
    document = _json(path / "manifest.json")
    if change == "duplicate_entry":
        document["artifacts"].append(copy.deepcopy(document["artifacts"][0]))
    elif change == "duplicate_logical_name":
        document["artifacts"][1]["logical_name"] = document["artifacts"][0]["logical_name"]
    elif change == "wrong_role_path":
        entry = next(item for item in document["artifacts"] if item["path"] == "source_amplitude.npy")
        entry["logical_name"] = "target_amplitude"
    elif change == "self_hash":
        document["artifacts"].append({"logical_name": "manifest", "path": "manifest.json", "size_bytes": 0, "sha256": "0" * 64})
    else:
        document["artifacts"].reverse()
    (path / "manifest.json").write_bytes(_json_bytes(document))
    with pytest.raises(ValueError):
        artifacts.verify_run_bundle(path)


@pytest.mark.parametrize("bad_path", ["../outside.npy", "..\\outside.npy", "/outside.npy", "C:\\outside.npy", "C:outside.npy", "\\\\server\\share\\outside.npy", "phase.npy:stream", "./phase.npy", "PHASE.npy", "phase.npy."])
def test_unsafe_manifest_paths_fail_before_instrumented_outside_reads(tmp_path, monkeypatch, bad_path):
    path = tmp_path / "run"
    _save(path)
    outside = tmp_path / "outside.npy"
    outside.write_bytes(b"independent outside sentinel")
    original = outside.read_bytes()
    document = _json(path / "manifest.json")
    entry = next(item for item in document["artifacts"] if item["path"] == "phase.npy")
    entry["path"] = bad_path
    (path / "manifest.json").write_bytes(_json_bytes(document))
    real_open = builtins.open
    real_io_open = io.open
    observed = []
    def guarded_open(filename, *args, **kwargs):
        if isinstance(filename, (str, os.PathLike)):
            candidate = Path(filename)
            if candidate != path and candidate.parent != path:
                observed.append(str(candidate))
                pytest.fail(f"attempted outside open: {candidate}")
        return real_open(filename, *args, **kwargs)
    def guarded_io_open(filename, *args, **kwargs):
        if isinstance(filename, (str, os.PathLike)):
            candidate = Path(filename)
            if candidate != path and candidate.parent != path:
                observed.append(str(candidate))
                pytest.fail(f"attempted outside io.open: {candidate}")
        return real_io_open(filename, *args, **kwargs)
    with monkeypatch.context() as context:
        context.setattr(builtins, "open", guarded_open)
        context.setattr(io, "open", guarded_io_open)
        with pytest.raises(ValueError):
            artifacts.verify_run_bundle(path)
    assert observed == []
    assert outside.read_bytes() == original


@pytest.mark.parametrize("filename", ["manifest.json", "config.json", "metrics.json"])
def test_duplicate_json_keys_are_rejected_in_every_metadata_document(tmp_path, filename):
    path = tmp_path / "run"
    _save(path)
    payload = (path / filename).read_bytes()
    assert b'"schema_version": 1' in payload
    payload = payload.replace(b'"schema_version": 1', b'"schema_version": 1, "schema_version": 1', 1)
    if filename == "manifest.json":
        (path / filename).write_bytes(payload)
    else:
        _rehash(path, filename, payload)
    with pytest.raises(ValueError, match="duplicate"):
        artifacts.load_run_bundle(path)


@pytest.mark.parametrize("change", ["missing_distance", "unknown_field", "missing_psnr_range", "unsupported_version", "nonfinite_number"])
def test_rehashed_invalid_config_fails_schema_before_solver(tmp_path, monkeypatch, change):
    path = tmp_path / "run"
    _save(path)
    document = _json(path / "config.json")
    if change == "missing_distance":
        del document["optics"]["distance_m"]
    elif change == "unknown_field":
        document["solver"]["unexpected"] = True
    elif change == "missing_psnr_range":
        del document["metrics"]["intensity_psnr"]["data_range"]
    elif change == "unsupported_version":
        document["schema_version"] = 99
    payload = _json_bytes(document)
    if change == "nonfinite_number":
        payload = payload.replace(b'"distance_m": 0.0002', b'"distance_m": 1e999')
        assert b"1e999" in payload
    _rehash(path, "config.json", payload)
    monkeypatch.setattr(artifacts, "gerchberg_saxton", lambda **kwargs: pytest.fail("invalid schema reached solver"))
    with pytest.raises(ValueError):
        artifacts.replay_run_bundle(path, source_revision=SOURCE)


@pytest.mark.parametrize("bad_value,error", [
    ("NaN", ValueError), ("Infinity", ValueError), ("-Infinity", ValueError),
    ("1e999", ValueError), ('"nan"', TypeError), ('"Infinity"', TypeError),
    ('"+inf"', TypeError),
])
def test_undeclared_nonfinite_metric_representations_are_rejected(tmp_path, bad_value, error):
    path = tmp_path / "run"
    _save(path)
    document = _json(path / "metrics.json")
    document["values"]["intensity_mse"] = "REPLACE_THIS_LITERAL"
    payload = _json_bytes(document).replace(b'"REPLACE_THIS_LITERAL"', bad_value.encode())
    _rehash(path, "metrics.json", payload)
    # Preserve every metric name so this reaches literal/type validation,
    # rather than being caught incidentally as an incomplete metrics object.
    with pytest.raises(error):
        artifacts.load_run_bundle(path)


def test_complex128_payload_preserves_all_signed_zero_component_bits(tmp_path):
    path = tmp_path / "run"
    bundle = _save(path)
    expected = bundle.arrays["source_field"].copy()
    components = expected.view(np.float64).reshape(-1)
    components[:8] = [0.0, 0.0, -0.0, 0.0, 0.0, -0.0, -0.0, -0.0]
    _rehash(path, "source_field.npy", _npy_bytes(expected))
    loaded = artifacts.load_run_bundle(path)
    _assert_bits(loaded.arrays["source_field"], expected)
    assert np.signbit(loaded.arrays["source_field"].view(np.float64).reshape(-1)[:8]).tolist() == [False, False, True, False, False, True, True, True]
    # A rehashed artifact is an integrity-valid byte fixture, not a claim that
    # these edited complex values remain the solver's actual output.
    report = artifacts.replay_run_bundle(path, source_revision=SOURCE)
    assert report.integrity == "passed" and report.comparison == "failed"


def test_saved_configuration_preserves_negative_zero_distance_bits(tmp_path):
    path = tmp_path / "run"
    _save(path, distance=-0.0)
    stored = _json(path / "config.json")["optics"]["distance_m"]
    loaded = artifacts.load_run_bundle(path).config.to_dict()["optics"]["distance_m"]
    assert struct.pack(">d", stored) == struct.pack(">d", -0.0)
    assert struct.pack(">d", loaded) == struct.pack(">d", -0.0)
    assert artifacts.replay_run_bundle(path, source_revision=SOURCE).comparison == "passed"


@pytest.mark.parametrize("malformation", ["object", "structured", "npz", "truncated", "trailing", "wrong_shape", "wrong_dtype", "non_native", "fortran", "version2", "oversized_header"])
def test_rehashed_malformed_npy_is_rejected_by_narrow_format_contract(tmp_path, malformation):
    path = tmp_path / "run"
    _save(path)
    array = np.zeros((3, 5), dtype=np.float64)
    if malformation == "object":
        payload = _npy_bytes(np.full((3, 5), {"safe_fixture": True}, dtype=object))
    elif malformation == "structured":
        payload = _npy_bytes(np.zeros((3, 5), dtype=[("value", "f8")]))
    elif malformation == "npz":
        stream = io.BytesIO()
        np.savez(stream, array=array)
        payload = stream.getvalue()
    elif malformation == "truncated":
        payload = _npy_bytes(array)[:-1]
    elif malformation == "trailing":
        payload = _npy_bytes(array) + b"undeclared"
    elif malformation == "wrong_shape":
        payload = _npy_bytes(array.T.copy())
    elif malformation == "wrong_dtype":
        payload = _npy_bytes(array.astype(np.float32))
    elif malformation == "non_native":
        payload = _npy_bytes(array.astype(array.dtype.newbyteorder("S")))
    elif malformation == "fortran":
        payload = _npy_bytes(np.asfortranarray(array))
    elif malformation == "version2":
        payload = _npy_bytes(array, version=(2, 0))
    else:
        header = b"{'descr': '<f8', 'fortran_order': False, 'shape': (3, 5), }" + b" " * 11000 + b"\n"
        payload = b"\x93NUMPY\x01\x00" + struct.pack("<H", len(header)) + header + array.tobytes()
    _rehash(path, "phase.npy", payload)
    with pytest.raises(ValueError):
        artifacts.load_run_bundle(path)


def test_safe_loader_explicitly_disables_pickle_and_uses_verified_byte_streams(tmp_path, monkeypatch):
    path = tmp_path / "run"
    _save(path)
    real_load = np.load
    calls = []
    def guarded(file, *args, **kwargs):
        assert isinstance(file, io.BytesIO)
        assert kwargs.get("allow_pickle") is False
        assert kwargs.get("mmap_mode") is None
        calls.append(file)
        return real_load(file, *args, **kwargs)
    monkeypatch.setattr(artifacts.np, "load", guarded)
    bundle = artifacts.load_run_bundle(path)
    assert len(calls) == len(bundle.arrays)


def test_rehashed_wrong_metric_passes_integrity_but_fails_recomputation(tmp_path):
    path = tmp_path / "run"
    _save(path)
    document = _json(path / "metrics.json")
    document["values"]["intensity_mse"] += 0.125
    _rehash(path, "metrics.json", _json_bytes(document))
    assert artifacts.verify_run_bundle(path).status == "passed"
    report = artifacts.replay_run_bundle(path, source_revision=SOURCE)
    assert report.integrity == "passed"
    assert report.qualification == "qualified"
    assert report.comparison == "failed"
    assert report.checks["saved_metric:intensity_mse"] is False
    assert report.checks["replay_metric:intensity_mse"] is False
    assert all(value for name, value in report.checks.items() if name.startswith("output:"))


@pytest.mark.parametrize("parameter", ["seed", "distance"])
def test_rehashed_valid_changed_config_fails_actual_numerical_replay(tmp_path, parameter):
    path = tmp_path / "run"
    _save(path, iterations=5, distance=2e-4)
    document = _json(path / "config.json")
    if parameter == "seed":
        document["solver"]["initialization"]["seed"] = 8
    else:
        document["optics"]["distance_m"] = -2e-4
    _rehash(path, "config.json", _json_bytes(document))
    assert artifacts.verify_run_bundle(path).status == "passed"
    report = artifacts.replay_run_bundle(path, source_revision=SOURCE)
    assert report.qualification == "qualified" and report.comparison == "failed"
    for role in ("phase", "reconstruction_field", "residual_history"):
        assert report.checks[f"output:{role}"] is False


@pytest.mark.parametrize("reason", ["missing", "different_revision", "dirty"])
def test_unqualified_replay_does_not_run_solver_by_default(tmp_path, monkeypatch, reason):
    path = tmp_path / "run"
    _save(path)
    supplied = None if reason == "missing" else dict(SOURCE)
    if reason == "different_revision":
        supplied["revision"] = "2" * 40
    elif reason == "dirty":
        supplied["state"] = "dirty"
    monkeypatch.setattr(artifacts, "gerchberg_saxton", lambda **kwargs: pytest.fail("unqualified default replay ran solver"))
    report = artifacts.replay_run_bundle(path, source_revision=supplied)
    assert report.integrity == "passed"
    assert report.qualification == "unqualified"
    assert report.comparison == "not_run"
    assert report.qualification_reasons and not report.checks


def test_diagnostic_matching_numerics_never_override_provenance_mismatch(tmp_path):
    path = tmp_path / "run"
    _save(path)
    supplied = {"revision": "2" * 40, "state": "clean", "method": "caller"}
    report = artifacts.replay_run_bundle(path, source_revision=supplied, diagnostic=True)
    assert report.integrity == "passed" and report.qualification == "unqualified"
    assert report.comparison == "passed"
    assert report.qualification_reasons and all(report.checks.values())
    assert report.current_source["revision"] == "2" * 40
    assert report.recorded_source["revision"] == "1" * 40


def test_recorded_runtime_is_compared_with_independent_current_runtime(tmp_path, monkeypatch):
    path = tmp_path / "run"
    _save(path)
    document = _json(path / "config.json")
    document["software"]["required_environment"]["numpy_version"] = "deliberately-different"
    _rehash(path, "config.json", _json_bytes(document))
    with monkeypatch.context() as context:
        context.setattr(artifacts, "gerchberg_saxton", lambda **kwargs: pytest.fail("runtime mismatch reached default solver"))
        report = artifacts.replay_run_bundle(path, source_revision=SOURCE)
    assert report.integrity == "passed" and report.qualification == "unqualified"
    assert report.comparison == "not_run"
    assert any("numpy_version" in reason for reason in report.qualification_reasons)
    diagnostic = artifacts.replay_run_bundle(path, source_revision=SOURCE, diagnostic=True)
    assert diagnostic.qualification == "unqualified" and diagnostic.comparison == "passed"


def test_foreign_endian_bundle_is_inspectable_but_diagnostic_replay_is_not_run(tmp_path, monkeypatch):
    path = tmp_path / "run"
    saved = _save(path)
    manifest = _json(path / "manifest.json")
    expected = {}
    for entry in manifest["artifacts"]:
        if not entry["path"].endswith(".npy"):
            continue
        array = saved.arrays[entry["logical_name"]]
        if array.dtype.itemsize == 1:
            expected[entry["logical_name"]] = array.copy()
            continue
        # Independently swap stored component bytes while retaining their
        # numerical values; update every multi-byte artifact consistently.
        foreign = array.byteswap().view(array.dtype.newbyteorder("S"))
        payload = _npy_bytes(foreign)
        (path / entry["path"]).write_bytes(payload)
        entry.update(dtype=foreign.dtype.str, size_bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
        expected[entry["logical_name"]] = foreign
    document = _json(path / "config.json")
    document["software"]["required_environment"]["byteorder"] = "big" if sys.byteorder == "little" else "little"
    payload = _json_bytes(document)
    (path / "config.json").write_bytes(payload)
    entry = next(item for item in manifest["artifacts"] if item["path"] == "config.json")
    entry.update(size_bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    (path / "manifest.json").write_bytes(_json_bytes(manifest))

    assert artifacts.verify_run_bundle(path).status == "passed"
    loaded = artifacts.load_run_bundle(path)
    for role, array in expected.items():
        _assert_bits(loaded.arrays[role], array)
        assert loaded.arrays[role].flags.c_contiguous and not loaded.arrays[role].flags.writeable
        if array.dtype.itemsize > 1:
            assert not loaded.arrays[role].dtype.isnative
    monkeypatch.setattr(artifacts, "gerchberg_saxton", lambda **kwargs: pytest.fail("foreign-endian diagnostic called native solver"))
    report = artifacts.replay_run_bundle(path, source_revision=SOURCE, diagnostic=True)
    assert report.integrity == "passed"
    assert report.qualification == "unqualified"
    assert any("byteorder" in reason for reason in report.qualification_reasons)
    assert report.comparison == "not_run"
    assert dict(report.checks) == {"native_array_byteorder": False}


def test_informational_environment_paths_do_not_control_qualification(tmp_path):
    path = tmp_path / "run"
    _save(path)
    document = _json(path / "config.json")
    document["software"]["informational_environment"]["python_executable"] = "informational/path/that/does/not/exist"
    document["software"]["informational_environment"]["cpu_count"] = 9999
    _rehash(path, "config.json", _json_bytes(document))
    report = artifacts.replay_run_bundle(path, source_revision=SOURCE)
    assert report.qualification == "qualified" and report.comparison == "passed"


def test_unavailable_recorded_revision_is_not_replaced_by_current_revision(tmp_path):
    path = tmp_path / "run"
    bundle = _save(path, source_revision=None)
    assert bundle.software["source"] == {"revision": None, "state": "unavailable", "method": "caller"}
    report = artifacts.replay_run_bundle(path, source_revision=SOURCE)
    assert report.qualification == "unqualified" and report.comparison == "not_run"
    assert report.recorded_source["revision"] is None
    assert report.current_source["revision"] == SOURCE["revision"]


def test_same_qualification_with_wrong_rehashed_complex_output_is_comparison_failure(tmp_path):
    path = tmp_path / "run"
    bundle = _save(path)
    changed = bundle.arrays["source_field"].copy()
    changed[0, 0] *= 1.01
    _rehash(path, "source_field.npy", _npy_bytes(changed))
    assert artifacts.verify_run_bundle(path).status == "passed"
    report = artifacts.replay_run_bundle(path, source_revision=SOURCE)
    assert report.qualification == "qualified" and report.comparison == "failed"
    assert report.checks["output:source_field"] is False


def test_load_decodes_verified_snapshots_even_if_disk_changes_after_hashing(tmp_path, monkeypatch):
    path = tmp_path / "run"
    expected = _save(path).arrays["phase"].copy()
    real_load = artifacts._load_npy
    mutated = False
    def mutate_after_verification(*args, **kwargs):
        nonlocal mutated
        if not mutated:
            disk_file = path / "phase.npy"
            changed = bytearray(disk_file.read_bytes())
            changed[-1] ^= 1
            disk_file.write_bytes(changed)
            mutated = True
        return real_load(*args, **kwargs)
    monkeypatch.setattr(artifacts, "_load_npy", mutate_after_verification)
    loaded = artifacts.load_run_bundle(path)
    _assert_bits(loaded.arrays["phase"], expected)
    assert mutated
    with pytest.raises(ValueError, match="digest"):
        artifacts.verify_run_bundle(path)


@pytest.mark.parametrize("role,change,error", [
    ("target_intensity", "list", TypeError),
    ("target_intensity", "float32", TypeError),
    ("target_intensity", "non_native", TypeError),
    ("target_intensity", "negative", ValueError),
    ("target_intensity", "above_one", ValueError),
    ("target_intensity", "nan", ValueError),
    ("target_intensity", "shape", ValueError),
    ("source_amplitude", "float32", TypeError),
    ("source_amplitude", "negative", ValueError),
    ("source_amplitude", "nan", ValueError),
    ("initial_phase", "float32", TypeError),
    ("initial_phase", "nan", ValueError),
    ("signal_mask", "float64", TypeError),
    ("cv_mask", "shape", ValueError),
])
def test_capture_rejects_invalid_numerical_inputs_before_solver(tmp_path, monkeypatch, role, change, error):
    values = dict(zip(("target_intensity", "source_amplitude", "initial_phase", "signal_mask", "cv_mask"), _inputs()))
    invalid = values[role].copy()
    if change == "list":
        invalid = invalid.tolist()
    elif change in {"float32", "float64"}:
        invalid = invalid.astype(change)
    elif change == "non_native":
        invalid = invalid.astype(invalid.dtype.newbyteorder("S"))
    elif change == "shape":
        invalid = invalid.T.copy()
    else:
        invalid[0, 0] = {"negative": -0.01, "above_one": 1.01, "nan": math.nan}[change]
    values[role] = invalid
    monkeypatch.setattr(artifacts, "gerchberg_saxton", lambda **kwargs: pytest.fail("invalid captured input reached solver"))
    with pytest.raises(error):
        artifacts.run_and_save_bundle(tmp_path / "run", config=RunConfig(_settings("explicit_phase")), source_revision=SOURCE, **values)
    assert not (tmp_path / "run").exists()
    _assert_no_partial(tmp_path)


@pytest.mark.parametrize("role", ["initial_phase", "signal_mask", "cv_mask"])
@pytest.mark.parametrize("required", [False, True])
def test_optional_input_presence_must_match_configuration_exactly(tmp_path, role, required):
    target, source, initial, signal, cv = _inputs()
    settings = _settings("explicit_phase" if required and role == "initial_phase" else "seed", metrics_settings={})
    if required and role == "signal_mask":
        settings["metrics"]["signal_region_power_fraction"] = {"mask": "signal_mask.npy"}
    elif required and role == "cv_mask":
        settings["metrics"]["regional_intensity_cv"] = {"mask": "cv_mask.npy"}
    arguments = {"target_intensity": target, "source_amplitude": source}
    if not required:
        arguments[role] = {"initial_phase": initial, "signal_mask": signal, "cv_mask": cv}[role]
    with pytest.raises(ValueError, match=role):
        artifacts.run_and_save_bundle(tmp_path / "run", config=RunConfig(settings), **arguments)
    _assert_no_partial(tmp_path)


@pytest.mark.parametrize("entry", ["empty_directory", "completed_directory", "file"])
def test_existing_destination_is_refused_without_altering_it(tmp_path, entry):
    path = tmp_path / "run"
    if entry == "file":
        path.write_bytes(b"existing file sentinel")
        before = path.read_bytes()
    else:
        path.mkdir()
        if entry == "completed_directory":
            (path / "manifest.json").write_bytes(b"existing completed sentinel")
        before = {child.name: child.read_bytes() for child in path.iterdir()}
    with pytest.raises(FileExistsError):
        _save(path)
    after = path.read_bytes() if entry == "file" else {child.name: child.read_bytes() for child in path.iterdir()}
    assert after == before
    _assert_no_partial(tmp_path)


def test_destination_appearing_immediately_before_publication_is_preserved(tmp_path, monkeypatch):
    path = tmp_path / "run"
    real_publish = artifacts._publish
    def race(stage, destination):
        destination.mkdir()
        (destination / "sentinel.txt").write_bytes(b"created by a competing publisher")
        return real_publish(stage, destination)
    monkeypatch.setattr(artifacts, "_publish", race)
    with pytest.raises(OSError):
        _save(path)
    assert (path / "sentinel.txt").read_bytes() == b"created by a competing publisher"
    assert {child.name for child in path.iterdir()} == {"sentinel.txt"}
    _assert_no_partial(tmp_path)


def test_windows_rename_retry_recovers_one_transient_access_denial(tmp_path, monkeypatch):
    path = tmp_path / "run"
    original_rename = os.rename
    calls, waits = [], []
    denial = PermissionError("injected transient Windows rename denial")
    denial.winerror = 5
    def transient(stage, destination):
        assert destination == path and stage.name.startswith(".ohlab-partial-")
        calls.append((stage, destination))
        if len(calls) == 1:
            raise denial
        return original_rename(stage, destination)
    monkeypatch.setattr(artifacts.os, "rename", transient)
    monkeypatch.setattr(artifacts.time, "sleep", waits.append)
    bundle = _save(path)
    assert len(calls) == 2 and waits == [0.01]
    assert bundle.path == path
    assert artifacts.verify_run_bundle(path).status == "passed"
    _assert_no_partial(tmp_path)


def test_windows_rename_retry_exhaustion_preserves_first_error_and_cleans_owned_stage(tmp_path, monkeypatch):
    path = tmp_path / "run"
    sentinel = tmp_path / "unrelated.txt"
    sentinel.write_bytes(b"unrelated sentinel survives exhausted retry")
    errors = [PermissionError(f"injected Windows rename denial {index}") for index in range(4)]
    for error in errors:
        error.winerror = 5
    calls, waits = [], []
    def persistent(stage, destination):
        assert destination == path and stage.name.startswith(".ohlab-partial-")
        calls.append((stage, destination))
        raise errors[len(calls) - 1]
    monkeypatch.setattr(artifacts.os, "rename", persistent)
    monkeypatch.setattr(artifacts.time, "sleep", waits.append)
    with pytest.raises(PermissionError) as caught:
        _save(path)
    assert caught.value is errors[0]
    assert len(calls) == 4 and waits == [0.01, 0.03, 0.10]
    assert not path.exists()
    assert sentinel.read_bytes() == b"unrelated sentinel survives exhausted retry"
    _assert_no_partial(tmp_path)


def test_windows_rename_retry_stops_when_destination_appears_during_wait(tmp_path, monkeypatch):
    path = tmp_path / "run"
    denial = PermissionError("injected denial before competing publication")
    denial.winerror = 5
    calls, waits = [], []
    def denied(stage, destination):
        assert destination == path and stage.name.startswith(".ohlab-partial-")
        calls.append((stage, destination))
        raise denial
    def competing_publication(delay):
        waits.append(delay)
        path.mkdir()
        (path / "foreign.txt").write_bytes(b"foreign destination must not be replaced")
    monkeypatch.setattr(artifacts.os, "rename", denied)
    monkeypatch.setattr(artifacts.time, "sleep", competing_publication)
    with pytest.raises(PermissionError) as caught:
        _save(path)
    assert caught.value is denial
    assert len(calls) == 1 and waits == [0.01]
    assert {entry.name for entry in path.iterdir()} == {"foreign.txt"}
    assert (path / "foreign.txt").read_bytes() == b"foreign destination must not be replaced"
    _assert_no_partial(tmp_path)


def test_windows_rename_retry_preserves_a_later_nonretryable_error(tmp_path, monkeypatch):
    path = tmp_path / "run"
    first = PermissionError("injected initial access denial")
    first.winerror = 5
    second = PermissionError("injected later sharing violation")
    second.winerror = 32
    calls, waits = [], []
    def change_error(stage, destination):
        assert destination == path and stage.name.startswith(".ohlab-partial-")
        calls.append((stage, destination))
        raise first if len(calls) == 1 else second
    monkeypatch.setattr(artifacts.os, "rename", change_error)
    monkeypatch.setattr(artifacts.time, "sleep", waits.append)
    with pytest.raises(PermissionError) as caught:
        _save(path)
    assert caught.value is second
    assert len(calls) == 2 and waits == [0.01]
    assert not path.exists()
    _assert_no_partial(tmp_path)


@pytest.mark.parametrize("platform_name,error_kind", [
    ("nt", "other_winerror"), ("nt", "ordinary_oserror"),
    ("nt", "file_exists"), ("posix", "access_denied"),
])
def test_windows_rename_retry_is_not_used_for_other_errors_or_platforms(tmp_path, monkeypatch, platform_name, error_kind):
    stage, destination = tmp_path / ".ohlab-partial-unit", tmp_path / "run"
    stage.mkdir()
    (stage / "sentinel.txt").write_bytes(b"private publication fixture")
    if error_kind == "ordinary_oserror":
        error = OSError("injected unrelated OS failure")
    elif error_kind == "file_exists":
        error = FileExistsError("injected existing destination")
    else:
        error = PermissionError("injected platform-specific denial")
        error.winerror = 32 if error_kind == "other_winerror" else 5
    calls, waits = [], []
    def fail_rename(source, target):
        assert source == stage and target == destination
        calls.append((source, target))
        raise error
    # A local facade changes only this helper's OS view; changing process-wide
    # os.name on Windows would also change pathlib's platform selection.
    facade = SimpleNamespace(name=platform_name, path=os.path, rename=fail_rename)
    monkeypatch.setattr(artifacts, "os", facade)
    monkeypatch.setattr(artifacts.time, "sleep", waits.append)
    with pytest.raises(type(error)) as caught:
        artifacts._publish(stage, destination)
    assert caught.value is error
    assert len(calls) == 1 and waits == []
    assert not destination.exists()
    assert (stage / "sentinel.txt").read_bytes() == b"private publication fixture"


@pytest.mark.parametrize("stage", ["artifact_write", "fsync", "manifest_write", "publish"])
def test_injected_save_failures_cleanup_only_owned_staging_and_keep_original_error(tmp_path, monkeypatch, stage):
    path = tmp_path / "run"
    sentinel = tmp_path / "unrelated.txt"
    sentinel.write_bytes(b"unrelated user data")
    marker = OSError(f"injected {stage}")
    real_write = artifacts._write_file
    def failing_write(file, data, owned):
        if (stage == "artifact_write" and file.name == "phase.npy") or (stage == "manifest_write" and file.name == "manifest.json"):
            raise marker
        return real_write(file, data, owned)
    def fail(*args, **kwargs):
        raise marker
    if stage in {"artifact_write", "manifest_write"}:
        monkeypatch.setattr(artifacts, "_write_file", failing_write)
    elif stage == "fsync":
        monkeypatch.setattr(artifacts.os, "fsync", fail)
    else:
        monkeypatch.setattr(artifacts, "_publish", fail)
    with pytest.raises(OSError) as caught:
        _save(path)
    assert caught.value is marker
    assert not path.exists()
    assert sentinel.read_bytes() == b"unrelated user data"
    _assert_no_partial(tmp_path)


def test_exclusive_artifact_collision_never_deletes_a_file_it_did_not_create(tmp_path, monkeypatch):
    real_write = artifacts._write_file
    foreign = []
    def insert_foreign_file(file, data, owned):
        if file.name == "phase.npy":
            file.write_bytes(b"foreign staging sentinel")
            foreign.append(file)
        return real_write(file, data, owned)
    monkeypatch.setattr(artifacts, "_write_file", insert_foreign_file)
    with pytest.raises(FileExistsError) as caught:
        _save(tmp_path / "run")
    assert not (tmp_path / "run").exists()
    assert len(foreign) == 1 and foreign[0].read_bytes() == b"foreign staging sentinel"
    assert {entry.name for entry in foreign[0].parent.iterdir()} == {"phase.npy"}
    notes = "\n".join(getattr(caught.value, "__notes__", ()))
    assert "cleanup failed" in notes and str(foreign[0].parent) in notes


def test_cleanup_failure_reports_leftover_staging_without_masking_original_error(tmp_path, monkeypatch):
    original = OSError("original publication failure")
    real_unlink = Path.unlink
    blocked = []
    def fail_publish(*args):
        raise original
    def fail_one_cleanup(path, *args, **kwargs):
        if path.name == "phase.npy" and path.parent.name.startswith(".ohlab-partial-"):
            blocked.append(path)
            raise PermissionError("injected cleanup denial")
        return real_unlink(path, *args, **kwargs)
    monkeypatch.setattr(artifacts, "_publish", fail_publish)
    monkeypatch.setattr(Path, "unlink", fail_one_cleanup)
    with pytest.raises(OSError) as caught:
        _save(tmp_path / "run")
    assert caught.value is original
    assert not (tmp_path / "run").exists()
    assert len(blocked) == 1 and blocked[0].exists()
    notes = "\n".join(getattr(original, "__notes__", ()))
    assert "injected cleanup denial" in notes and str(blocked[0].parent) in notes


def test_manifest_is_written_last_and_all_files_are_closed_before_publication(tmp_path, monkeypatch):
    order = []
    real_write = artifacts._write_file
    real_publish = artifacts._publish
    def record(file, data, owned):
        order.append(file.name)
        return real_write(file, data, owned)
    def publish(stage, destination):
        assert order[-1] == "manifest.json"
        for child in stage.iterdir():
            # On Windows a rename also exercises that no writer holds the file.
            alternate = child.with_name(child.name + ".closed-check")
            child.rename(alternate)
            alternate.rename(child)
        return real_publish(stage, destination)
    monkeypatch.setattr(artifacts, "_write_file", record)
    monkeypatch.setattr(artifacts, "_publish", publish)
    _save(tmp_path / "run")
    assert order[-1] == "manifest.json"


@pytest.mark.parametrize("function_name", ["verify_run_bundle", "load_run_bundle", "replay_run_bundle"])
def test_public_readers_reject_reserved_partial_directories(tmp_path, function_name):
    complete = tmp_path / "complete"
    _save(complete)
    partial = tmp_path / ".ohlab-partial-fixture"
    shutil.copytree(complete, partial)
    with pytest.raises(ValueError, match="partial"):
        getattr(artifacts, function_name)(partial)


def test_bundle_directory_junction_is_rejected_on_windows(tmp_path):
    if os.name != "nt":
        pytest.skip("Windows junction contract")
    original, junction = tmp_path / "original", tmp_path / "junction"
    _save(original)
    result = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(original)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    try:
        for function in (artifacts.verify_run_bundle, artifacts.load_run_bundle, artifacts.replay_run_bundle):
            with pytest.raises(ValueError, match="symlink|reparse"):
                function(junction)
        assert artifacts.verify_run_bundle(original).status == "passed"
    finally:
        # Remove only the test-created junction itself, never recurse into it.
        os.rmdir(junction)


def test_linked_artifact_is_rejected_without_altering_target(tmp_path):
    path = tmp_path / "run"
    _save(path)
    external = tmp_path / "external_phase.npy"
    original = (path / "phase.npy").read_bytes()
    (path / "phase.npy").rename(external)
    try:
        os.symlink(external, path / "phase.npy")
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("this Windows account lacks symlink privilege; junction is tested separately")
        raise
    with pytest.raises(ValueError, match="symlink|reparse"):
        artifacts.load_run_bundle(path)
    assert external.read_bytes() == original


def test_png_provenance_must_match_captured_target_and_failure_cleans_stage(tmp_path):
    wrong_png = tmp_path / "wrong.png"
    wrong_png.write_bytes(_png_bytes(np.full((3, 5), 127, dtype=np.uint8)))
    original = wrong_png.read_bytes()
    with pytest.raises(ValueError, match="PNG|png|target"):
        _save(tmp_path / "run", input_png=wrong_png)
    assert wrong_png.read_bytes() == original
    assert not (tmp_path / "run").exists()
    _assert_no_partial(tmp_path)


def test_optional_original_png_preserves_exact_bytes_and_is_not_replay_input(tmp_path):
    codes = np.rint(_inputs()[0] * 255.0).astype(np.uint8)
    external = tmp_path / "external.png"
    original = _png_bytes(codes)
    external.write_bytes(original)
    path = tmp_path / "run"
    _save(path, input_png=external)
    assert (path / "input_target.png").read_bytes() == original
    external.unlink()  # Only this test-created fixture, never a user input.
    assert artifacts.verify_run_bundle(path).status == "passed"
    assert artifacts.replay_run_bundle(path, source_revision=SOURCE).comparison == "passed"


def test_fresh_process_relocation_replays_without_external_png_or_original_cwd(tmp_path):
    source_dir, copied_dir, other_cwd = tmp_path / "saving", tmp_path / "copied", tmp_path / "other_cwd"
    source_dir.mkdir()
    other_cwd.mkdir()
    external = source_dir / "input.png"
    codes = np.rint(_inputs()[0] * 255.0).astype(np.uint8)
    external.write_bytes(_png_bytes(codes))
    saving_code = '''import json,sys
from pathlib import Path
import numpy as np
from ohlab.grid import SamplingGrid
from ohlab.io.images import load_target_intensity
from ohlab.io.config import RunConfig
from ohlab.io.artifacts import run_and_save_bundle
from ohlab.targets import intensity_to_amplitude
settings=json.loads(sys.argv[1]); source=json.loads(sys.argv[2])
grid=SamplingGrid(ny=3,nx=5,dy=10e-6,dx=8e-6)
target=load_target_intensity(sys.argv[3],grid=grid)
amplitude=intensity_to_amplitude(target,grid=grid)
illumination=np.full(grid.shape,np.sqrt(np.sum(amplitude**2)/amplitude.size))
run_and_save_bundle(sys.argv[4],config=RunConfig(settings),target_intensity=target,source_amplitude=illumination,source_revision=source,input_png=sys.argv[3])
print('saved in exited process')
'''
    original = source_dir / "run"
    settings = _settings(metrics_settings={"intensity_mse": {}, "intensity_nmse": {}, "intensity_psnr": {"data_range": 1.0}})
    saved = subprocess.run([sys.executable, "-B", "-c", saving_code, json.dumps(settings), json.dumps(SOURCE), str(external), str(original)], cwd=source_dir, capture_output=True, text=True, check=False)
    assert saved.returncode == 0, saved.stdout + saved.stderr
    assert saved.stdout.strip() == "saved in exited process"
    shutil.copytree(original, copied_dir)
    external.unlink()
    # Move the test-created original out of its former absolute path as well.
    original.rename(source_dir / "original-unavailable")
    replay_code = '''import json,sys
from ohlab.io.artifacts import verify_run_bundle,replay_run_bundle
p=sys.argv[1]; report=replay_run_bundle(p,source_revision=json.loads(sys.argv[2]))
print(json.dumps({'integrity':verify_run_bundle(p).status,'qualification':report.qualification,'comparison':report.comparison,'checks':dict(report.checks)},sort_keys=True))
'''
    replayed = subprocess.run([sys.executable, "-B", "-c", replay_code, str(copied_dir), json.dumps(SOURCE)], cwd=other_cwd, capture_output=True, text=True, check=False)
    assert replayed.returncode == 0, replayed.stdout + replayed.stderr
    report = json.loads(replayed.stdout)
    assert report["integrity"] == "passed" and report["qualification"] == "qualified" and report["comparison"] == "passed"
    assert report["checks"] and all(report["checks"].values())


def test_example_git_detection_uses_imported_checkout_independently_of_cwd(tmp_path, monkeypatch):
    repository = Path(__file__).resolve().parents[1]
    example = repository / "examples" / "run_bundle.py"
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    revision = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"], capture_output=True, text=True, check=True, env=env).stdout.strip()
    status = subprocess.run(["git", "-C", str(repository), "status", "--porcelain"], capture_output=True, text=True, check=True, env=env).stdout
    monkeypatch.chdir(tmp_path)
    namespace = runpy.run_path(str(example))
    actual = namespace["_detect_source_revision"]()
    assert actual == {"revision": revision, "state": "dirty" if status else "clean", "method": "git"}


def test_example_git_detection_does_not_assign_checkout_head_to_unrelated_installed_code(tmp_path, monkeypatch):
    import ohlab
    repository = Path(__file__).resolve().parents[1]
    namespace = runpy.run_path(str(repository / "examples" / "run_bundle.py"))
    installed = tmp_path / "installed" / "ohlab"
    installed.mkdir(parents=True)
    fake_module = installed / "__init__.py"
    fake_module.write_text("# isolated test module location\n", encoding="utf-8")
    monkeypatch.setattr(ohlab, "__file__", str(fake_module))
    monkeypatch.chdir(repository)
    actual = namespace["_detect_source_revision"]()
    assert actual == {"revision": None, "state": "unavailable", "method": "git"}
