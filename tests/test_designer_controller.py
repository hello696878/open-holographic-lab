"""M7 real editor/controller/API integration, independent of Streamlit.

Exact target assertions pin the stored binary64 intensity, not a rendered
preview or an 8-bit approximation. Caller provenance below tests policy;
it does not attest executing source identity.
"""

from dataclasses import FrozenInstanceError, replace
import hashlib
from pathlib import Path

import numpy as np
import pytest

from apps import designer as ds, workbench as wb
from ohlab.io.artifacts import load_run_bundle, replay_run_bundle, verify_run_bundle
from ohlab.io.designs import design_from_json, design_to_json, load_design, save_design
from ohlab.target_design import TargetDesign2D, rasterize_target_design

from _helpers import assert_bit_identical


SOURCE = {"revision": "d" * 40, "state": "dirty", "method": "caller"}
DISK_ID = "1" * 32
RECTANGLE_ID = "2" * 32


def design_spec():
    return {
        "schema_version": 1,
        "rasterizer_version": "center_sample_overwrite_v1",
        "coordinate_system": "centered_pixels_y_down_v1",
        "canvas": {"ny": 4, "nx": 5},
        "background_intensity": 0.125,
        "objects": [
            {"id": DISK_ID, "type": "disk", "parameters": {
                "cx_px": 1.0, "cy_px": -1.0, "radius_px": 1.0}, "intensity": 0.3},
            {"id": RECTANGLE_ID, "type": "rectangle", "parameters": {
                "cx_px": -0.5, "cy_px": 0.0, "width_px": 1.0, "height_px": 2.0}, "intensity": 0.6},
        ],
    }


def expected_target():
    # Hand-derived on x=(-2,-1,0,1,2), y=(-2,-1,0,1); later rectangle wins.
    return np.array([
        [0.125, 0.125, 0.125, 0.3, 0.125],
        [0.125, 0.6, 0.6, 0.3, 0.3],
        [0.125, 0.6, 0.6, 0.3, 0.125],
        [0.125, 0.6, 0.6, 0.125, 0.125],
    ], dtype=np.float64)


def draft(**changes):
    return replace(wb.RunDraft(target_kind="designer", design=TargetDesign2D(design_spec()),
                               iterations=0, distance_mm=0.0), **changes)


def generate(runs, requested=None):
    state = wb.WorkbenchState()
    assert wb.submit_generate(state, requested or draft(), offered_nonce=state.offered_nonce, runs_root=runs), state.error
    assert wb.execute_pending_run(state), state.error
    return state


def file_hashes(path):
    return {str(item.relative_to(path)): hashlib.sha256(item.read_bytes()).hexdigest()
            for item in path.rglob("*") if item.is_file()}


@pytest.fixture(autouse=True)
def caller_source(monkeypatch):
    monkeypatch.setattr(wb, "detect_source_revision", lambda: dict(SOURCE))


def test_designer_exact_fractional_target_direct_m5_and_one_save(tmp_path, monkeypatch):
    state = wb.WorkbenchState()
    requested = draft()
    nonce = state.offered_nonce
    seen = []
    real_save = wb.run_and_save_bundle
    def save(path, **kwargs):
        seen.append(path)
        assert state.busy and state.pending is None and nonce in state.consumed_tokens
        assert kwargs.get("input_png") is None
        assert_bit_identical(kwargs["target_intensity"], expected_target())
        snapshot = tmp_path / "runs" / "designs" / "submissions" / (path.name + ".json")
        assert design_to_json(load_design(snapshot)) == design_to_json(requested.design)
        assert not wb.submit_generate(state, requested, offered_nonce=nonce, runs_root=tmp_path / "runs")
        return real_save(path, **kwargs)
    monkeypatch.setattr(wb, "run_and_save_bundle", save)
    monkeypatch.setattr(wb, "load_target_intensity", lambda *a, **k: pytest.fail("designer must not decode PNG"))
    assert wb.submit_generate(state, requested, offered_nonce=nonce, runs_root=tmp_path / "runs")
    destination = state.pending.destination
    assert destination.parent == tmp_path / "runs" / "m7"
    assert not (tmp_path / "runs").exists()
    assert wb.execute_pending_run(state), state.error
    assert not wb.execute_pending_run(state)
    assert not wb.submit_generate(state, requested, offered_nonce=nonce, runs_root=tmp_path / "runs")
    assert seen == [destination]
    assert state.save_succeeded and state.saved_path == destination
    assert state.design_snapshot_path == tmp_path / "runs" / "designs" / "submissions" / (destination.name + ".json")
    assert_bit_identical(state.bundle.arrays["target_intensity"], expected_target())
    assert "input_target.png" not in verify_run_bundle(destination).files
    assert not any("design" in name for name in verify_run_bundle(destination).files)
    assert list((tmp_path / "runs" / "m7").iterdir()) == [destination]


@pytest.mark.parametrize("stale_shape", [(64, 64), (2, 7), (0, 999)])
def test_designer_canvas_is_authoritative_over_inactive_draft_shape(tmp_path, stale_shape):
    state = generate(tmp_path / "runs", draft(ny=stale_shape[0], nx=stale_shape[1]))
    assert state.bundle.config.to_dict()["grid"]["ny"] == 4
    assert state.bundle.config.to_dict()["grid"]["nx"] == 5
    assert state.bundle.arrays["target_intensity"].shape == (4, 5)
    assert_bit_identical(state.bundle.arrays["target_intensity"], expected_target())


def test_submitted_design_owns_snapshot_and_later_edits_cannot_relabel(tmp_path):
    specification = design_spec()
    requested = draft(design=TargetDesign2D(specification))
    state = wb.WorkbenchState()
    assert wb.submit_generate(state, requested, offered_nonce=state.offered_nonce, runs_root=tmp_path / "runs")
    submitted = state.pending
    before = design_to_json(submitted.design)
    specification["objects"][0]["intensity"] = 0.95
    exported = submitted.design.to_dict()
    exported["objects"].reverse()
    changed = replace(requested, design=TargetDesign2D(exported))
    assert wb.draft_fingerprint(changed) != submitted.draft_fingerprint
    assert design_to_json(submitted.design) == before
    assert submitted.design_sha256 == hashlib.sha256(before).hexdigest()
    with pytest.raises(FrozenInstanceError):
        submitted.design = changed.design
    assert wb.execute_pending_run(state), state.error
    assert state.submitted is submitted
    assert_bit_identical(state.bundle.arrays["target_intensity"], expected_target())
    assert design_to_json(load_design(state.design_snapshot_path)) == before


def test_active_design_order_and_scientific_settings_change_fingerprint():
    first = draft()
    spec = design_spec()
    spec["objects"].reverse()
    spec_same_order_other_intensity = design_spec()
    spec_same_order_other_intensity["objects"][0]["intensity"] = 0.31
    changes = [replace(first, design=TargetDesign2D(spec)),
               replace(first, design=TargetDesign2D(spec_same_order_other_intensity)),
               replace(first, dx_um=9.0), replace(first, seed=9),
               wb.RunDraft(iterations=0, distance_mm=0.0)]
    assert all(wb.draft_fingerprint(value) != wb.draft_fingerprint(first) for value in changes)
    assert wb.draft_fingerprint(replace(first, design=design_from_json(design_to_json(first.design)))) == wb.draft_fingerprint(first)


def test_pitch_changes_only_physical_grid_and_preserves_designer_target(tmp_path):
    first = generate(tmp_path / "runs", draft(dx_um=8.0, dy_um=8.0))
    second = generate(tmp_path / "runs", draft(dx_um=12.0, dy_um=10.0))
    assert_bit_identical(first.bundle.arrays["target_intensity"], second.bundle.arrays["target_intensity"])
    assert_bit_identical(first.bundle.arrays["source_amplitude"], second.bundle.arrays["source_amplitude"])
    assert second.bundle.config.to_dict()["grid"] == {"ny": 4, "nx": 5, "dy_m": 10.0 * 1e-6, "dx_m": 12.0 * 1e-6}
    source = second.bundle.arrays["source_amplitude"]
    amplitude = second.bundle.arrays["target_amplitude"]
    # A uniform source is explicitly constructed; this tests the public value,
    # not merely M3's looser power acceptance. Same operations give exact bits.
    prescribed = np.full((4, 5), np.sqrt(np.sum(amplitude ** 2) / amplitude.size))
    assert_bit_identical(source, prescribed)
    np.testing.assert_allclose(np.sum(source ** 2), np.sum(amplitude ** 2),
                               rtol=8 * np.finfo(np.float64).eps, atol=0.0)


def test_editor_selection_is_content_identity_neutral_and_preview_has_no_io(monkeypatch):
    editor = ds.EditorState(design=TargetDesign2D(design_spec()))
    original = design_to_json(editor.design)
    fingerprint = wb.draft_fingerprint(draft(design=editor.design))
    for name in ("run_and_save_bundle", "verify_run_bundle", "load_run_bundle", "replay_run_bundle"):
        monkeypatch.setattr(wb, name, lambda *a, **k: pytest.fail("preview must not invoke M5"))
    monkeypatch.setattr(ds, "save_copy", lambda *a, **k: pytest.fail("preview must not save editable designs"))
    for selected in (DISK_ID, RECTANGLE_ID, DISK_ID):
        ds.select_object(editor, selected)
        assert editor.selected_id == selected
        assert design_to_json(editor.design) == original
        assert wb.draft_fingerprint(draft(design=editor.design)) == fingerprint
        actual = rasterize_target_design(editor.design)
        assert_bit_identical(actual, expected_target())
        actual[:] = 0.0
    assert_bit_identical(rasterize_target_design(editor.design), expected_target())


def test_editor_canvas_resize_preserves_objects_without_rescaling():
    editor = ds.EditorState(design=TargetDesign2D(design_spec()), selected_id=RECTANGLE_ID)
    original = editor.design.to_dict()["objects"]
    assert ds.update_canvas(editor, 2, 3, 0.2)
    assert editor.design.to_dict()["canvas"] == {"ny": 2, "nx": 3}
    assert editor.design.to_dict()["objects"] == original
    assert editor.selected_id == RECTANGLE_ID
    assert editor.design.to_dict()["background_intensity"] == 0.2


@pytest.mark.parametrize("payload", [b"not JSON", b"{}", b'{"schema_version":1,"schema_version":1}', b"\xff"])
def test_invalid_import_atomically_preserves_design_selection_and_saved_data(tmp_path, payload):
    editor = ds.EditorState(design=TargetDesign2D(design_spec()), selected_id=RECTANGLE_ID)
    saved = ds.save_copy(editor, runs_root=tmp_path / "runs")
    before = design_to_json(editor.design)
    hashes = file_hashes(tmp_path)
    assert not ds.import_design(editor, payload)
    assert editor.error and editor.selected_id == RECTANGLE_ID
    assert design_to_json(editor.design) == before
    assert editor.saved_path == saved
    assert file_hashes(tmp_path) == hashes


def test_valid_same_size_changed_content_import_replaces_actual_design():
    editor = ds.EditorState(design=TargetDesign2D(design_spec()), selected_id=RECTANGLE_ID)
    first = design_to_json(editor.design)
    spec = design_spec()
    spec["objects"][0]["intensity"] = 0.9
    second = design_to_json(TargetDesign2D(spec))
    assert len(first) == len(second) and first != second
    assert ds.import_design(editor, second)
    assert design_to_json(editor.design) == second
    assert editor.error is None
    assert editor.selected_id is None or editor.selected_id in {item["id"] for item in editor.design.to_dict()["objects"]}


def test_editor_edit_delete_and_order_preserve_ids_and_atomic_invalid_updates():
    editor = ds.EditorState(design=TargetDesign2D(design_spec()), selected_id=DISK_ID)
    before = design_to_json(editor.design)
    assert not ds.update_object(editor, DISK_ID, {"cx_px": 0.0, "cy_px": 0.0, "radius_px": -1.0}, 0.3)
    assert design_to_json(editor.design) == before and editor.selected_id == DISK_ID
    assert ds.update_object(editor, DISK_ID, {"cx_px": 0.0, "cy_px": 0.0, "radius_px": 0.5}, 0.35)
    assert editor.design.to_dict()["objects"][0]["id"] == DISK_ID
    assert ds.move_object(editor, DISK_ID, 1)
    assert [obj["id"] for obj in editor.design.to_dict()["objects"]] == [RECTANGLE_ID, DISK_ID]
    assert ds.delete_object(editor, DISK_ID)
    assert [obj["id"] for obj in editor.design.to_dict()["objects"]] == [RECTANGLE_ID]
    assert editor.selected_id is None or editor.selected_id == RECTANGLE_ID
    assert ds.add_object(editor, "segment")
    objects = editor.design.to_dict()["objects"]
    assert len(objects) == 2 and objects[-1]["type"] == "segment"
    assert objects[-1]["id"] != RECTANGLE_ID


def test_empty_design_preview_save_export_are_valid_but_synthesis_does_not_save_run(tmp_path, monkeypatch):
    editor = ds.EditorState(design=ds.empty_design(ny=4, nx=5))
    assert_bit_identical(rasterize_target_design(editor.design), np.zeros((4, 5), dtype=np.float64))
    saved = ds.save_copy(editor, runs_root=tmp_path / "runs")
    assert saved.is_file()
    assert design_to_json(load_design(saved)) == design_to_json(editor.design)
    monkeypatch.setattr(wb, "run_and_save_bundle", lambda *a, **k: pytest.fail("blank must not call M5"))
    state = wb.WorkbenchState()
    assert wb.submit_generate(state, draft(design=editor.design), offered_nonce=state.offered_nonce, runs_root=tmp_path / "runs")
    assert not wb.execute_pending_run(state)
    assert state.error and not state.save_succeeded and state.bundle is None
    assert not list((tmp_path / "runs" / "m7").glob("*/manifest.json"))
    assert saved.is_file()


def test_snapshot_persistence_failure_consumes_nonce_and_never_calls_m5(tmp_path, monkeypatch):
    state = wb.WorkbenchState()
    nonce = state.offered_nonce
    calls = []
    def fail_snapshot(*args, **kwargs):
        assert nonce in state.consumed_tokens and state.pending is None and state.busy
        calls.append(args[0])
        raise OSError("injected editable snapshot persistence failure")
    monkeypatch.setattr(wb, "save_design", fail_snapshot)
    monkeypatch.setattr(wb, "run_and_save_bundle", lambda *a, **k: pytest.fail("snapshot failure must stop M5"))
    assert wb.submit_generate(state, draft(), offered_nonce=nonce, runs_root=tmp_path / "runs")
    assert not wb.execute_pending_run(state)
    assert "snapshot persistence failure" in state.error
    assert len(calls) == 1 and state.bundle is None and not state.save_succeeded
    assert not wb.execute_pending_run(state)
    assert not wb.submit_generate(state, draft(), offered_nonce=nonce, runs_root=tmp_path / "runs")
    assert not list((tmp_path / "runs").rglob("manifest.json"))


def test_m5_failure_preserves_and_reports_saved_editable_snapshot(tmp_path, monkeypatch):
    state = wb.WorkbenchState()
    attempts = []
    def fail_m5(path, **kwargs):
        attempts.append(path)
        assert state.design_snapshot_path.is_file()
        raise OSError("injected M5 failure after editable snapshot")
    monkeypatch.setattr(wb, "run_and_save_bundle", fail_m5)
    assert wb.submit_generate(state, draft(), offered_nonce=state.offered_nonce, runs_root=tmp_path / "runs")
    assert not wb.execute_pending_run(state)
    assert len(attempts) == 1 and "M5 failure" in state.error
    assert state.design_snapshot_path.is_file()
    assert design_to_json(load_design(state.design_snapshot_path)) == design_to_json(draft().design)
    assert state.bundle is None and not state.save_succeeded
    assert not wb.execute_pending_run(state)


def test_rasterization_failure_happens_before_snapshot_or_m5(tmp_path, monkeypatch):
    monkeypatch.setattr(wb, "rasterize_target_design", lambda *a, **k: (_ for _ in ()).throw(ValueError("unusable geometry")))
    monkeypatch.setattr(wb, "save_design", lambda *a, **k: pytest.fail("invalid raster must not be persisted"))
    monkeypatch.setattr(wb, "run_and_save_bundle", lambda *a, **k: pytest.fail("invalid raster must not solve"))
    state = wb.WorkbenchState()
    assert wb.submit_generate(state, draft(), offered_nonce=state.offered_nonce, runs_root=tmp_path / "runs")
    assert not wb.execute_pending_run(state)
    assert "unusable geometry" in state.error
    assert not list((tmp_path / "runs").rglob("*.json"))


def test_presentation_failure_retains_bundle_snapshot_and_never_regenerates(tmp_path):
    state = generate(tmp_path / "runs")
    bundle, submitted, snapshot = state.bundle, state.submitted, state.design_snapshot_path
    hashes = file_hashes(tmp_path)
    wb.record_presentation_failure(state, RuntimeError("designer presentation failed"))
    assert state.bundle is bundle and state.submitted is submitted
    assert state.design_snapshot_path == snapshot and state.save_succeeded
    assert state.presentation_error and state.error is None
    assert not wb.execute_pending_run(state)
    assert file_hashes(tmp_path) == hashes


@pytest.mark.parametrize("association", ["missing", "invalid", "mismatch", "match"])
def test_associated_design_four_states_do_not_gate_numerical_inspection_or_replay(tmp_path, association):
    runs = tmp_path / "runs"
    state = generate(runs)
    path = state.saved_path
    snapshot = state.design_snapshot_path
    expected = design_to_json(state.submitted.design)
    bundle_hashes = file_hashes(path)
    if association == "missing":
        snapshot.unlink()
    elif association == "invalid":
        snapshot.write_bytes(b"not valid design JSON")
    elif association == "mismatch":
        spec = design_spec()
        spec["objects"][0]["intensity"] = 0.9
        snapshot.write_bytes(design_to_json(TargetDesign2D(spec)))
    found = wb.load_associated_design(state, path, runs_root=runs, offered_nonce=state.offered_nonce)
    assert state.association_status == association
    assert state.bundle.path == path and state.integrity == "passed"
    assert state.comparison == "not_run"
    if association == "match":
        assert found is not None and design_to_json(found) == expected
    else:
        assert found is None
    # Only a verified match is returned for the explicit UI action to adopt.
    # The AppTest layer independently checks actual editor-state preservation.
    assert verify_run_bundle(path).status == "passed"
    assert_bit_identical(load_run_bundle(path).arrays["target_intensity"], expected_target())
    strict = replay_run_bundle(path, source_revision=SOURCE)
    assert (strict.integrity, strict.qualification, strict.comparison) == ("passed", "unqualified", "not_run")
    diagnostic = replay_run_bundle(path, source_revision=SOURCE, diagnostic=True)
    assert (diagnostic.integrity, diagnostic.qualification, diagnostic.comparison) == ("passed", "unqualified", "passed")
    assert file_hashes(path) == bundle_hashes
    assert path in wb.list_bundle_candidates(runs_root=runs)


def test_association_verifies_bundle_before_accepting_external_matching_name(tmp_path):
    runs = tmp_path / "runs"
    state = generate(runs)
    path = state.saved_path
    metrics = path / "metrics.json"
    metrics.write_bytes(metrics.read_bytes() + b"\n")
    assert wb.load_associated_design(state, path, runs_root=runs, offered_nonce=state.offered_nonce) is None
    assert state.error and state.integrity != "passed"
    assert state.association_status != "match"


def test_association_changed_bundle_revokes_diagnostic_even_when_design_missing(tmp_path):
    runs = tmp_path / "runs"
    first = generate(runs)
    second = generate(runs)
    second.design_snapshot_path.unlink()
    first.diagnostic_enabled = True
    assert first.selected_path != second.saved_path
    assert wb.load_associated_design(first, second.saved_path, runs_root=runs,
                                     offered_nonce=first.offered_nonce) is None
    assert not first.diagnostic_enabled
    assert first.association_status == "missing"
    assert first.bundle.path == second.saved_path and first.integrity == "passed"
    assert first.qualification == "not_evaluated" and first.comparison == "not_run"
    assert first.error is None


def test_designer_preview_array_cannot_become_submitted_target(tmp_path):
    requested = draft()
    preview = rasterize_target_design(requested.design)
    preview[:] = 0.99
    state = generate(tmp_path / "runs", requested)
    assert_bit_identical(state.bundle.arrays["target_intensity"], expected_target())


def test_failed_new_design_submission_preserves_previous_files_without_false_success(tmp_path):
    runs = tmp_path / "runs"
    state = generate(runs)
    previous = state.saved_path
    hashes = file_hashes(previous)
    assert not wb.submit_generate(state, draft(seed=-1), offered_nonce=state.offered_nonce, runs_root=runs)
    assert state.error and not state.save_succeeded and state.bundle is None
    assert state.integrity == "not_evaluated" and state.comparison == "not_run"
    assert file_hashes(previous) == hashes
