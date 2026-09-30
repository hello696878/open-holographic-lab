"""Installed AppTest acceptance for M7 callbacks and visible saved identity.

These are widget/controller checks, not browser rendering, download transport,
or real queued-network-event evidence. Those require separate browser records.
"""

import hashlib
import importlib.util
import json

import numpy as np
import pytest

if importlib.util.find_spec("streamlit") is None:
    pytest.skip("optional Streamlit UI is not installed", allow_module_level=True)

from streamlit.testing.v1 import AppTest

from apps import designer as ds, streamlit_app as ui, workbench as wb
from ohlab.io.artifacts import verify_run_bundle
from ohlab.io.designs import design_to_json, load_design
from ohlab.target_design import TargetDesign2D, rasterize_target_design
from _helpers import assert_bit_identical
from test_designer_controller import design_spec, expected_target, DISK_ID, RECTANGLE_ID, SOURCE


def _clean(at):
    assert not at.exception, [item.value for item in at.exception]


def _text(at):
    return "\n".join(str(item.value) for kind in ("markdown", "caption", "text", "code", "info", "warning", "error", "success", "subheader", "title")
                     for item in at.get(kind))


def _button(at, prefix):
    matches = [button for button in at.button if button.key and button.key.startswith(prefix + "_")]
    assert len(matches) == 1, [(item.key, item.label) for item in at.button]
    return matches[0]


def _saved_configs(at):
    values = [json.loads(item.value) if isinstance(item.value, str) else item.value for item in at.json]
    return [item for item in values if isinstance(item, dict) and "solver" in item and "grid" in item]


def _app(*, old_callback=False):
    script = "from apps.streamlit_app import main\nmain()"
    if old_callback:
        script = '''
import streamlit as st
from apps.streamlit_app import main, _submit_generate
if "test_old_designer_nonce" in st.session_state:
    _submit_generate(st.session_state.pop("test_old_designer_nonce"))
main()
'''
    at = AppTest.from_string(script, default_timeout=30).run()
    at.selectbox(key="draft_target_kind").set_value("designer").run()
    _clean(at)
    return at


def _import(at, payload=None, *, filename="same.json"):
    payload = design_to_json(TargetDesign2D(design_spec())) if payload is None else payload
    at.file_uploader(key="designer_json_upload").set_value((filename, payload, "application/json")).run()
    at.button(key="designer_import").click().run()
    _clean(at)
    return at.session_state["designer_editor"]


def _generate(at):
    at.number_input(key="draft_iterations").set_value(0)
    at.number_input(key="draft_distance_mm").set_value(0.0).run()
    _button(at, "generate").click().run()
    _clean(at)
    return at.session_state["workbench"]


@pytest.fixture
def local_ui(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    runs.mkdir()
    monkeypatch.setattr(ui, "RUNS_ROOT", runs)
    monkeypatch.setattr(wb, "detect_source_revision", lambda: dict(SOURCE))
    calls = {name: [] for name in ("run_and_save_bundle", "verify_run_bundle", "load_run_bundle", "replay_run_bundle")}
    for name, recorded in calls.items():
        original = getattr(wb, name)
        def observe(*args, _original=original, _recorded=recorded, **kwargs):
            _recorded.append((args, kwargs))
            return _original(*args, **kwargs)
        monkeypatch.setattr(wb, name, observe)
    return runs, calls


def test_designer_edits_selection_and_preview_have_no_run_or_persistence_side_effects(local_ui):
    runs, calls = local_ui
    at = _app()
    editor = _import(at)
    assert editor.design.to_dict() == TargetDesign2D(design_spec()).to_dict()
    assert "Desired intensity preview" in _text(at)
    assert not any(widget.key in {"draft_ny", "draft_nx"} for widget in at.number_input)
    at.selectbox(key="designer_selected").set_value(RECTANGLE_ID).run()
    before = design_to_json(editor.design)
    at.selectbox(key="designer_selected").set_value(DISK_ID).run()
    assert design_to_json(editor.design) == before
    at.number_input(key="designer_intensity").set_value(0.35).run()
    at.number_input(key="designer_cx_px").set_value(0.5).run()
    at.number_input(key="designer_nx").set_value(7).run()
    _clean(at)
    assert editor.design.to_dict()["canvas"] == {"ny": 4, "nx": 7}
    assert editor.design.to_dict()["objects"][0]["parameters"]["cx_px"] == 0.5
    assert editor.design.to_dict()["objects"][0]["intensity"] == 0.35
    assert all(not entries for entries in calls.values())
    assert not list(runs.iterdir())


def test_add_delete_reorder_and_brightness_are_real_editor_callbacks(local_ui):
    at = _app()
    editor = _import(at)
    at.selectbox(key="designer_selected").set_value(DISK_ID).run()
    at.button(key="designer_front").click().run()
    assert [obj["id"] for obj in editor.design.to_dict()["objects"]] == [RECTANGLE_ID, DISK_ID]
    # The disk is now on top at hand-known overlap (x=0,y=-1), index[1,2].
    assert rasterize_target_design(editor.design)[1, 2] == 0.3
    at.number_input(key="designer_intensity").set_value(0.0).run()
    assert rasterize_target_design(editor.design)[1, 2] == 0.0
    at.button(key="designer_delete").click().run()
    assert [obj["id"] for obj in editor.design.to_dict()["objects"]] == [RECTANGLE_ID]
    at.selectbox(key="designer_add_type").set_value("segment").run()
    at.button(key="designer_add").click().run()
    _clean(at)
    assert editor.design.to_dict()["objects"][-1]["type"] == "segment"
    assert editor.selected_id == editor.design.to_dict()["objects"][-1]["id"]
    assert all(not entries for entries in local_ui[1].values())
    assert not list(local_ui[0].iterdir())


def test_selection_alone_does_not_mark_saved_result_stale_but_content_edit_does(local_ui):
    at = _app()
    editor = _import(at)
    state = _generate(at)
    saved, submitted = state.bundle, state.submitted
    original_design = design_to_json(submitted.design)
    original_config = saved.config.to_dict()
    assert "Previous submission" not in _text(at)
    at.selectbox(key="designer_selected").set_value(RECTANGLE_ID).run()
    assert "Previous submission" not in _text(at)
    assert design_to_json(editor.design) == original_design
    at.number_input(key="designer_intensity").set_value(0.4).run()
    at.number_input(key="draft_seed").set_value(17).run()
    _clean(at)
    assert "Previous submission" in _text(at)
    assert f"Design SHA-256: {hashlib.sha256(original_design).hexdigest()}" in _text(at)
    assert str(saved.path) in _text(at)
    assert _saved_configs(at) == [original_config]
    assert state.bundle is saved and state.submitted is submitted
    assert design_to_json(state.submitted.design) == original_design
    assert_bit_identical(saved.arrays["target_intensity"], expected_target())
    assert len(local_ui[1]["run_and_save_bundle"]) == 1


def test_designer_generate_once_saves_exact_target_and_old_nonce_cannot_repeat(local_ui):
    at = _app(old_callback=True)
    _import(at)
    at.number_input(key="draft_iterations").set_value(0)
    at.number_input(key="draft_distance_mm").set_value(0.0).run()
    nonce = _button(at, "generate").key.removeprefix("generate_")
    _button(at, "generate").click().run()
    _clean(at)
    state = at.session_state["workbench"]
    saved = state.bundle.path
    at.run()
    at.session_state["test_old_designer_nonce"] = nonce
    at.run()
    _clean(at)
    assert len(local_ui[1]["run_and_save_bundle"]) == 1
    assert state.bundle.path == saved and state.save_succeeded
    assert_bit_identical(state.bundle.arrays["target_intensity"], expected_target())
    assert state.bundle.config.to_dict()["grid"]["ny"] == 4
    assert state.bundle.config.to_dict()["grid"]["nx"] == 5
    assert state.design_snapshot_path.is_file()
    assert state.design_snapshot_path.parent == local_ui[0] / "designs" / "submissions"
    assert list((local_ui[0] / "m7").iterdir()) == [saved]


def test_same_filename_changed_content_requires_explicit_import_then_atomic_replacement(local_ui):
    at = _app()
    editor = _import(at)
    first = design_to_json(editor.design)
    specification = design_spec()
    specification["objects"][0]["intensity"] = 0.9
    second = design_to_json(TargetDesign2D(specification))
    assert len(first) == len(second) and first != second
    at.file_uploader(key="designer_json_upload").set_value(("same.json", second, "application/json")).run()
    assert design_to_json(editor.design) == first
    at.button(key="designer_import").click().run()
    _clean(at)
    assert design_to_json(editor.design) == second
    assert editor.error is None
    assert at.number_input(key="designer_intensity").value == 0.9
    assert all(not entries for entries in local_ui[1].values())
    assert not list(local_ui[0].iterdir())


def test_invalid_import_and_invalid_geometry_keep_coherent_editor_then_recover(local_ui):
    at = _app()
    editor = _import(at)
    at.selectbox(key="designer_selected").set_value(RECTANGLE_ID).run()
    before = design_to_json(editor.design)
    selected = editor.selected_id
    at.file_uploader(key="designer_json_upload").set_value(("same.json", b"{}", "application/json")).run()
    at.button(key="designer_import").click().run()
    _clean(at)
    assert at.error and editor.error
    assert design_to_json(editor.design) == before and editor.selected_id == selected
    assert at.selectbox(key="designer_selected").value == selected
    assert at.number_input(key="designer_width_px").value == 1.0
    at.number_input(key="designer_width_px").set_value(0.0).run()
    _clean(at)
    assert editor.error and design_to_json(editor.design) == before
    assert at.number_input(key="designer_width_px").value == 1.0
    _import(at)
    assert editor.error is None and not at.error
    assert design_to_json(editor.design) == before
    assert all(not entries for entries in local_ui[1].values())


def test_save_design_copy_is_explicit_and_does_not_generate(local_ui):
    at = _app()
    editor = _import(at, filename="../../untrusted-browser-name.json")
    assert not list(local_ui[0].iterdir())
    at.button(key="designer_save").click().run()
    _clean(at)
    first = editor.saved_path
    assert first.parent == local_ui[0] / "designs"
    assert first.name != "untrusted-browser-name.json"
    assert design_to_json(load_design(first)) == design_to_json(editor.design)
    assert str(first) in _text(at)
    at.button(key="designer_save").click().run()
    assert editor.saved_path != first and first.is_file()
    assert all(not entries for entries in local_ui[1].values())
    # Download transport is tested in the real browser, not inferred from this widget.
    assert len(at.get("download_button")) == 1


def test_blank_preview_and_save_are_allowed_but_generate_fails_without_substitution(local_ui):
    at = _app()
    editor = at.session_state["designer_editor"]
    assert np.count_nonzero(rasterize_target_design(editor.design)) == 0
    assert "Desired intensity preview" in _text(at)
    at.button(key="designer_save").click().run()
    saved_design = editor.saved_path
    state = _generate(at)
    assert state.error and at.error and not state.save_succeeded and state.bundle is None
    assert saved_design.is_file()
    assert not local_ui[1]["run_and_save_bundle"]
    assert not list((local_ui[0] / "m7").glob("*/manifest.json"))


@pytest.mark.parametrize("stage", ["snapshot", "m5"])
def test_design_and_numerical_persistence_failures_are_visibly_distinct(local_ui, monkeypatch, stage):
    at = _app()
    _import(at)
    def failure(*args, **kwargs):
        raise OSError(f"injected {stage} persistence failure")
    monkeypatch.setattr(wb, "save_design" if stage == "snapshot" else "run_and_save_bundle", failure)
    state = _generate(at)
    assert state.error and at.error and not state.save_succeeded and state.bundle is None
    assert f"injected {stage} persistence failure" in _text(at)
    if stage == "snapshot":
        assert state.design_snapshot_path is None
        assert not local_ui[1]["run_and_save_bundle"]
    else:
        assert state.design_snapshot_path.is_file()
        assert str(state.design_snapshot_path) in _text(at)
        assert "Design saved; numerical run failed" in _text(at)
    at.run()
    assert not state.busy and state.pending is None


def test_completed_designer_bundle_survives_presentation_failure_and_refresh(local_ui, monkeypatch):
    at = _app()
    _import(at)
    original = ui.presentation.build_result_figures
    def fail_display(**kwargs):
        raise RuntimeError("injected designer result display failure")
    monkeypatch.setattr(ui.presentation, "build_result_figures", fail_display)
    state = _generate(at)
    path, snapshot = state.saved_path, state.design_snapshot_path
    assert state.save_succeeded and state.error is None and state.presentation_error
    assert path.is_dir() and snapshot.is_file()
    assert "injected designer result display failure" in _text(at)
    at.run()
    assert len(local_ui[1]["run_and_save_bundle"]) == 1
    monkeypatch.setattr(ui.presentation, "build_result_figures", original)
    _button(at, "refresh").click().run()
    _clean(at)
    assert state.bundle.path == path and state.presentation_error is None
    assert not at.error and snapshot.is_file()
    assert len(local_ui[1]["run_and_save_bundle"]) == 1
    assert not local_ui[1]["replay_run_bundle"]


@pytest.mark.parametrize("association", ["missing", "invalid", "mismatch", "match"])
def test_explicit_association_four_states_preserve_or_replace_editor_and_never_auto_replay(local_ui, association):
    at = _app()
    editor = _import(at)
    state = _generate(at)
    path, snapshot = state.saved_path, state.design_snapshot_path
    submitted = design_to_json(state.submitted.design)
    at.number_input(key="designer_intensity").set_value(0.45).run()
    current = design_to_json(editor.design)
    selected = editor.selected_id
    if association == "missing":
        snapshot.unlink()
    elif association == "invalid":
        snapshot.write_bytes(b"not JSON")
    elif association == "mismatch":
        snapshot.write_bytes(current)
    _button(at, "associated").click().run()
    _clean(at)
    assert state.bundle.path == path and state.integrity == "passed"
    assert state.association_status == association
    if association == "match":
        assert design_to_json(editor.design) == submitted
        assert "Raster match" in _text(at)
    else:
        assert design_to_json(editor.design) == current and editor.selected_id == selected
        assert at.selectbox(key="designer_selected").value == selected
        assert f"External design: {association}" in _text(at)
    assert not local_ui[1]["replay_run_bundle"]
    assert verify_run_bundle(path).status == "passed"
    assert not _button(at, "strict").disabled


def test_mode_change_preserves_saved_design_identity_revokes_diagnostic_and_status(local_ui):
    at = _app()
    _import(at)
    state = _generate(at)
    path, submitted = state.saved_path, state.submitted
    at.checkbox(key="diagnostic_enabled").check().run()
    at.selectbox(key="draft_target_kind").set_value("builtin").run()
    _clean(at)
    assert not at.checkbox(key="diagnostic_enabled").value
    assert state.comparison == "not_run" and state.qualification == "not_evaluated"
    assert state.bundle.path == path and state.submitted is submitted
    assert "Design SHA-256: " + submitted.design_sha256 in _text(at)
    assert "Previous submission" in _text(at)
    at.selectbox(key="draft_target_kind").set_value("designer").run()
    _clean(at)
    assert not at.checkbox(key="diagnostic_enabled").value
    assert state.submitted is submitted
    assert at.number_input(key="designer_ny").value == 4
    assert at.number_input(key="designer_nx").value == 5
    assert at.selectbox(key="designer_selected").value == at.session_state["designer_editor"].selected_id
    at.checkbox(key="diagnostic_enabled").check().run()
    _button(at, "diagnostic").click().run()
    assert state.comparison == "passed" and state.qualification == "unqualified"
    # Public replay first reloads the bundle, so accepted M6 semantics clear
    # the session's submitted record. A later mode switch must retain this
    # loaded identity rather than inventing a current-draft submission.
    loaded = state.bundle
    assert state.submitted is None
    at.selectbox(key="draft_target_kind").set_value("upload").run()
    _clean(at)
    assert state.bundle is loaded and state.bundle.path == path
    assert state.submitted is None and state.replay_report is None
    assert state.comparison == "not_run" and state.qualification == "not_evaluated"
    assert not at.checkbox(key="diagnostic_enabled").value
    assert _saved_configs(at) == [loaded.config.to_dict()]
    assert len(local_ui[1]["run_and_save_bundle"]) == 1


def test_changing_selected_bundle_resets_replay_status_without_relabeling_loaded_arrays(local_ui):
    at = _app()
    _import(at)
    state = _generate(at)
    at.checkbox(key="diagnostic_enabled").check().run()
    _button(at, "diagnostic").click().run()
    _clean(at)
    assert state.comparison == "passed" and state.replay_report is not None
    loaded = state.bundle
    other_selection = local_ui[0] / "m7" / ("f" * 32)
    at.text_input(key="bundle_path_input").set_value(str(other_selection)).run()
    _clean(at)
    assert not at.checkbox(key="diagnostic_enabled").value
    assert state.qualification == "not_evaluated" and state.comparison == "not_run"
    assert state.replay_report is None
    assert state.bundle is loaded and state.submitted is None
    assert _saved_configs(at) == [loaded.config.to_dict()]
    assert str(loaded.path) in _text(at)
    assert len(local_ui[1]["replay_run_bundle"]) == 1
    assert len(local_ui[1]["run_and_save_bundle"]) == 1


def test_busy_designer_controls_disable_and_fresh_session_requires_explicit_reopening(local_ui):
    at = _app()
    _import(at)
    state = _generate(at)
    path = state.saved_path
    state.busy = True
    at.run()
    _clean(at)
    for key in ("designer_add", "designer_delete", "designer_save", "designer_import"):
        assert at.button(key=key).disabled
    assert at.selectbox(key="designer_selected").disabled
    assert all(widget.disabled for widget in at.number_input)
    assert _button(at, "generate").disabled and _button(at, "associated").disabled
    fresh = _app()
    _clean(fresh)
    assert fresh.session_state["workbench"].bundle is None
    assert len(local_ui[1]["run_and_save_bundle"]) == 1
    fresh.text_input(key="bundle_path_input").set_value(str(path)).run()
    _button(fresh, "open").click().run()
    _clean(fresh)
    assert fresh.session_state["workbench"].bundle.path == path
    assert not local_ui[1]["replay_run_bundle"]
