"""M7 editable JSON ownership and its independent M5 float64-array boundary."""

import json
import os
from pathlib import Path
import stat
from types import SimpleNamespace

import numpy as np
import pytest

from ohlab import SamplingGrid
from ohlab.io import designs
from ohlab.io.artifacts import load_run_bundle, replay_run_bundle, run_and_save_bundle, verify_run_bundle
from ohlab.io.config import RunConfig
from ohlab.target_design import TargetDesign2D, rasterize_target_design
from ohlab.targets import intensity_to_amplitude


def document():
    return {"schema_version": 1, "rasterizer_version": "center_sample_overwrite_v1",
            "coordinate_system": "centered_pixels_y_down_v1", "canvas": {"ny": 4, "nx": 5},
            "background_intensity": -0.0, "objects": [
                {"id": "1" * 32, "type": "disk", "intensity": 0.3,
                 "parameters": {"cx_px": 1.0, "cy_px": -1.0, "radius_px": 1.0}},
                {"id": "2" * 32, "type": "segment", "intensity": float.fromhex("0x1.0000000000001p-1"),
                 "parameters": {"x0_px": -0.0, "y0_px": -1.3, "x1_px": 2.7,
                                "y1_px": 1.3, "width_px": 0.5}},
            ]}


def float_hex_tree(value):
    if type(value) is float:
        return value.hex()
    if isinstance(value, dict):
        return {key: float_hex_tree(item) for key, item in value.items()}
    if isinstance(value, list):
        return [float_hex_tree(item) for item in value]
    return value


def test_canonical_json_scalar_bits_and_raster_round_trip():
    model = TargetDesign2D(document())
    encoded = designs.design_to_json(model)
    assert encoded == (json.dumps(model.to_dict(), sort_keys=True, indent=2,
                                  ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    assert encoded.endswith(b"\n") and b"\r" not in encoded
    restored = designs.design_from_json(encoded)
    assert designs.design_to_json(restored) == encoded
    assert float_hex_tree(restored.to_dict()) == float_hex_tree(model.to_dict())
    assert rasterize_target_design(restored).tobytes() == rasterize_target_design(model).tobytes()
    exported = restored.to_dict()
    exported["objects"].clear()
    assert designs.design_to_json(restored) == encoded


@pytest.mark.parametrize("data", [bytearray(b"{}"), "{}", memoryview(b"{}"), None])
def test_json_input_requires_immutable_bytes(data):
    with pytest.raises(TypeError, match="bytes"):
        designs.design_from_json(data)


@pytest.mark.parametrize("data", [
    b'{"schema_version":1,"schema_version":1}',
    b'{"nested":{"x":1,"x":2}}', b'{"value":NaN}', b'{"value":Infinity}',
    b'{"value":-Infinity}', b'\xff', b'\xef\xbb\xbf{}', b'{', b'{} {}',
    b'[' * 2000 + b']' * 2000,
])
def test_malformed_encoding_syntax_duplicate_keys_and_constants(data):
    with pytest.raises(ValueError):
        designs.design_from_json(data)


@pytest.mark.parametrize("key,value", [("schema_version", 2), ("coordinate_system", "other"),
                                       ("extra", None), ("background_intensity", float("inf"))])
def test_json_passes_through_full_schema_validation(key, value):
    supplied = document()
    supplied[key] = value
    encoded = json.dumps(supplied).encode("utf-8")
    if key == "background_intensity":
        encoded = encoded.replace(b"Infinity", b"1e999")
    with pytest.raises(ValueError):
        designs.design_from_json(encoded)


def test_json_exact_encoded_size_limit_checked_before_parsing():
    encoded = designs.design_to_json(TargetDesign2D(document()))
    limit = 256 * 1024
    padded = encoded + b" " * (limit - len(encoded))
    assert designs.design_to_json(designs.design_from_json(padded)) == encoded
    with pytest.raises(ValueError, match="262144"):
        designs.design_from_json(padded + b" ")
    with pytest.raises(ValueError, match="262144"):
        designs.design_from_json(b"!" * (limit + 1))


def test_save_load_exact_new_destination_and_closed_stage(tmp_path, monkeypatch):
    model = TargetDesign2D(document())
    encoded = designs.design_to_json(model)
    destination = tmp_path / "editable.json"
    original = designs.os.rename
    seen = []

    def rename(stage, target):
        # On Windows this opens an independent writer and proves no still-open
        # buffered writer retains the stage. The actual rename must also work.
        with Path(stage).open("r+b") as file:
            assert file.read() == encoded
        seen.append(Path(stage))
        original(stage, target)

    monkeypatch.setattr(designs.os, "rename", rename)
    assert designs.save_design(destination, design=model) == destination.absolute()
    assert len(seen) == 1 and not seen[0].exists()
    assert destination.read_bytes() == encoded
    assert designs.design_to_json(designs.load_design(destination)) == encoded
    assert set(tmp_path.iterdir()) == {destination}


def test_existing_destination_and_unrelated_data_are_preserved(tmp_path):
    existing = tmp_path / "existing.json"
    existing.write_bytes(b"existing independent bytes")
    unrelated = tmp_path / "keep.txt"
    unrelated.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        designs.save_design(existing, design=TargetDesign2D(document()))
    assert existing.read_bytes() == b"existing independent bytes"
    assert unrelated.read_bytes() == b"keep"
    assert set(tmp_path.iterdir()) == {existing, unrelated}


@pytest.mark.parametrize("where", ["fdopen", "fsync", "rename"])
def test_failed_save_closes_resources_and_cleans_only_owned_partial(tmp_path, monkeypatch, where):
    existing = tmp_path / "keep.txt"
    existing.write_bytes(b"keep")
    failure = OSError("injected " + where)
    descriptors = []
    real_mkstemp = designs.tempfile.mkstemp

    def track(*args, **kwargs):
        result = real_mkstemp(*args, **kwargs)
        descriptors.append(result[0])
        return result

    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(designs.tempfile, "mkstemp", track)
    monkeypatch.setattr(designs.os, where, fail)
    with pytest.raises(OSError) as caught:
        designs.save_design(tmp_path / "new.json", design=TargetDesign2D(document()))
    assert caught.value is failure
    assert set(tmp_path.iterdir()) == {existing} and existing.read_bytes() == b"keep"
    assert len(descriptors) == 1
    with pytest.raises(OSError):
        os.fstat(descriptors[0])


def test_write_failure_closes_stream_and_preserves_primary_error(tmp_path, monkeypatch):
    original = designs.os.fdopen
    failure = OSError("injected write failure")
    streams = []

    class BadWriter:
        def __init__(self, fd, mode):
            self.file = original(fd, mode)
            streams.append(self.file)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.file.close()

        def write(self, value):
            self.file.write(value[:20])
            raise failure

    monkeypatch.setattr(designs.os, "fdopen", BadWriter)
    with pytest.raises(OSError) as caught:
        designs.save_design(tmp_path / "new.json", design=TargetDesign2D(document()))
    assert caught.value is failure and streams[0].closed
    assert not list(tmp_path.iterdir())


def test_collision_after_stage_write_is_never_overwritten(tmp_path, monkeypatch):
    target = tmp_path / "new.json"
    original = designs.os.fsync

    def collide(fd):
        original(fd)
        target.write_bytes(b"another owner's destination")

    monkeypatch.setattr(designs.os, "fsync", collide)
    with pytest.raises(FileExistsError):
        designs.save_design(target, design=TargetDesign2D(document()))
    assert target.read_bytes() == b"another owner's destination"
    assert set(tmp_path.iterdir()) == {target}


def test_cleanup_failure_preserves_primary_exception_and_reports_owned_path(tmp_path, monkeypatch):
    primary = OSError("primary rename failure")
    original_unlink = Path.unlink

    def fail_rename(*args):
        raise primary

    def fail_cleanup(path, *args, **kwargs):
        if path.name.startswith(".ohlab-design-partial-"):
            raise PermissionError("injected cleanup denial")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(designs.os, "rename", fail_rename)
    monkeypatch.setattr(Path, "unlink", fail_cleanup)
    with pytest.raises(OSError) as caught:
        designs.save_design(tmp_path / "new.json", design=TargetDesign2D(document()))
    assert caught.value is primary
    partials = list(tmp_path.iterdir())
    assert len(partials) == 1 and partials[0].name.startswith(".ohlab-design-partial-")
    assert str(partials[0]) in " ".join(caught.value.__notes__)
    original_unlink(partials[0])


@pytest.mark.parametrize("action", ["load", "save"])
def test_reparse_ancestor_is_rejected_before_file_access(tmp_path, monkeypatch, action):
    original = Path.lstat

    def reparse(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        if path == tmp_path:
            return SimpleNamespace(st_mode=result.st_mode, st_size=result.st_size,
                                   st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
        return result

    monkeypatch.setattr(Path, "lstat", reparse)
    with pytest.raises(ValueError, match="reparse"):
        if action == "load":
            designs.load_design(tmp_path / "design.json")
        else:
            designs.save_design(tmp_path / "design.json", design=TargetDesign2D(document()))
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("value", [1, b"design.json", None])
def test_path_type_rejected(value):
    with pytest.raises(TypeError):
        designs.load_design(value)


def test_partial_directory_missing_parent_and_oversized_file_rejected(tmp_path):
    partial = tmp_path / ".ohlab-design-partial-owned.json"
    partial.write_bytes(designs.design_to_json(TargetDesign2D(document())))
    with pytest.raises(ValueError, match="partial"):
        designs.load_design(partial)
    with pytest.raises(ValueError, match="regular"):
        designs.load_design(tmp_path)
    with pytest.raises(FileNotFoundError):
        designs.save_design(tmp_path / "missing" / "new.json", design=TargetDesign2D(document()))
    huge = tmp_path / "large.json"
    huge.write_bytes(b" " * (256 * 1024 + 1))
    with pytest.raises(ValueError, match="262144"):
        designs.load_design(huge)
    with pytest.raises(TypeError):
        designs.save_design(tmp_path / "invalid.json", design=document())
    assert not (tmp_path / "invalid.json").exists()


def test_real_m5_path_preserves_fractional_target_bytes_and_external_independence(tmp_path):
    supplied = document()
    supplied["objects"] = supplied["objects"][:1]
    model = TargetDesign2D(supplied)
    editable = designs.save_design(tmp_path / "editable.json", design=model)
    intensity = rasterize_target_design(designs.load_design(editable))
    expected = np.array([[0, 0, 0, 0.3, 0], [0, 0, 0.3, 0.3, 0.3],
                         [0, 0, 0, 0.3, 0], [0, 0, 0, 0, 0]], dtype=np.float64)
    # Background is intentionally negative zero, including pixels untouched by
    # the disk. M5 must preserve those bits along with literal fractional 0.3.
    expected[expected == 0] = -0.0
    assert intensity.tobytes() == expected.tobytes()
    grid = SamplingGrid(ny=4, nx=5, dy=10e-6, dx=8e-6)
    amplitude = intensity_to_amplitude(intensity, grid=grid)
    source = np.full(grid.shape, float(np.sqrt(np.sum(amplitude**2)/amplitude.size)))
    config = RunConfig({"schema_version": 1,
        "grid": {"ny": 4, "nx": 5, "dy_m": 10e-6, "dx_m": 8e-6},
        "optics": {"wavelength_m": 633e-9, "distance_m": 0.0002},
        "solver": {"algorithm": "gerchberg_saxton", "contract": "m3_periodic_lossless_asm_v1",
                   "iterations": 2, "initialization": {"mode": "seed", "seed": 0}},
        "metrics": {"intensity_mse": {}, "intensity_nmse": {}, "intensity_psnr": {"data_range": 1.0}}})
    # Caller-supplied synthetic source records test the M5 metadata policy only;
    # they do not claim current checkout provenance or authenticated source.
    provenance = {"revision": "a" * 40, "state": "clean", "method": "caller"}
    bundle = run_and_save_bundle(tmp_path / "run", config=config, target_intensity=intensity,
                                 source_amplitude=source, source_revision=provenance, input_png=None)
    assert bundle.arrays["target_intensity"].tobytes() == expected.tobytes()
    assert not (tmp_path / "run" / "input.png").exists()
    assert not (tmp_path / "run" / "editable.json").exists()
    editable.unlink()  # only the fixture owned by this test
    assert verify_run_bundle(tmp_path / "run").status == "passed"
    loaded = load_run_bundle(tmp_path / "run")
    assert loaded.arrays["target_intensity"].tobytes() == expected.tobytes()
    report = replay_run_bundle(tmp_path / "run", source_revision=provenance)
    assert (report.integrity, report.qualification, report.comparison) == ("passed", "qualified", "passed")
    assert all(report.checks.values())
