"""Installed Streamlit 1.64 UI wiring with actual bounded M5 bundles.

AppTest simulates Streamlit widgets and callbacks. These assertions are not
browser rendering, network-upload, or real queued-browser-event evidence.
The separate browser acceptance records cover those boundaries.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib

import numpy as np
import pytest


# Skip only a genuinely missing optional UI. Broken installed dependencies and
# unexpected versions must fail instead of becoming an optional-dependency skip.
if importlib.util.find_spec("streamlit") is None:
    pytest.skip("optional Streamlit UI is not installed", allow_module_level=True)

from streamlit.testing.v1 import AppTest

from ohlab.io import artifacts
from ohlab.io.config import RunConfig


ROOT = Path(__file__).resolve().parents[1]
DIRTY_SOURCE = {"revision": "1" * 40, "state": "dirty", "method": "caller"}


def _png(codes):
    """Independent PNG encoder; uncompressed deflate gives equal-sized variants."""
    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    ny, nx = codes.shape
    header = struct.pack(">IIBBBBB", nx, ny, 8, 0, 0, 0, 0)
    rows = b"".join(b"\x00" + row.tobytes() for row in codes)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows, level=0)) + chunk(b"IEND", b"")


def _text(at):
    return "\n".join(
        str(element.value)
        for kind in ("markdown", "caption", "text", "code", "info", "warning", "error", "success")
        for element in at.get(kind)
    )


def _button(at, prefix):
    matches = [button for button in at.button if button.key and button.key.startswith(prefix + "_")]
    assert len(matches) == 1, [(button.key, button.label) for button in at.button]
    return matches[0]


def _assert_clean_run(at):
    assert not at.exception, [exception.value for exception in at.exception]


def _app(*, inject_stale_callback=False):
    # The real callable main is exercised so fixture-local roots and targeted
    # failure injection work without an undocumented PYTHONPATH change.
    script = "from apps.streamlit_app import main\nmain()"
    if inject_stale_callback:
        script = '''
import streamlit as st
from apps.streamlit_app import main, _submit_generate
if "test_stale_generate_nonce" in st.session_state:
    _submit_generate(st.session_state.pop("test_stale_generate_nonce"))
main()
'''
    return AppTest.from_string(script, default_timeout=30).run()


def _saved_configs(at):
    values = [json.loads(item.value) if isinstance(item.value, str) else item.value for item in at.json]
    return [value for value in values if isinstance(value, dict) and "solver" in value and "grid" in value]


def _statuses(at):
    return {metric.label: metric.value for metric in at.metric}


def _open(at, path):
    at.text_input(key="bundle_path_input").set_value(str(path)).run()
    _button(at, "open").click().run()
    _assert_clean_run(at)
    return at.session_state["workbench"]


def _upload(at, codes, *, filename="target.png"):
    at.selectbox(key="draft_target_kind").set_value("upload").run()
    at.number_input(key="draft_ny").set_value(codes.shape[0])
    at.number_input(key="draft_nx").set_value(codes.shape[1])
    at.number_input(key="draft_iterations").set_value(0)
    at.file_uploader(key="draft_upload").upload(filename, _png(codes), "image/png").run()
    _assert_clean_run(at)


def _generate(at):
    _button(at, "generate").click().run()
    _assert_clean_run(at)
    return at.session_state["workbench"]


def _existing(path, *, explicit=False, constant=False):
    target = np.array([[0.25, 0.5, 0.75], [0.5, 0.25, 1.0]], dtype=np.float64)
    if constant:
        target = np.full((2, 3), 0.25, dtype=np.float64)
    source = np.sqrt(target) if explicit else np.full(target.shape, np.sqrt(np.sum(np.sqrt(target) ** 2) / target.size))
    initialization = {"mode": "explicit_phase", "artifact": "initial_phase.npy"} if explicit else {"mode": "seed", "seed": 7}
    metric_spec = {
        "intensity_mse": {}, "intensity_nmse": {},
        "intensity_psnr": {"data_range": 2.0},
    }
    if explicit:
        metric_spec.update({
            "signal_region_power_fraction": {"mask": "signal_mask.npy"},
            "regional_intensity_cv": {"mask": "cv_mask.npy"},
        })
    settings = {
        "schema_version": 1,
        "grid": {"ny": 2, "nx": 3, "dy_m": 10e-6, "dx_m": 8e-6},
        "optics": {"wavelength_m": 633e-9, "distance_m": 0.0},
        "solver": {"algorithm": "gerchberg_saxton", "contract": "m3_periodic_lossless_asm_v1", "iterations": 0, "initialization": initialization},
        "metrics": metric_spec,
    }
    kwargs = {}
    if explicit:
        kwargs = {
            "initial_phase": np.zeros(target.shape, dtype=np.float64),
            "signal_mask": np.array([[True, False, True], [False, True, False]]),
            "cv_mask": np.array([[False, True, False], [True, False, False]]),
        }
    return artifacts.run_and_save_bundle(
        path, config=RunConfig(settings), target_intensity=target,
        source_amplitude=source, source_revision=DIRTY_SOURCE, **kwargs,
    )


@pytest.fixture
def ui(tmp_path, monkeypatch):
    from apps import streamlit_app, workbench
    runs = tmp_path / "runs"
    runs.mkdir()
    monkeypatch.setattr(streamlit_app, "RUNS_ROOT", runs)
    return streamlit_app, workbench, runs


@pytest.fixture
def calls(ui, monkeypatch):
    _, workbench, _ = ui
    recorded = {name: [] for name in ("run_and_save_bundle", "load_run_bundle", "verify_run_bundle", "replay_run_bundle")}
    for name, records in recorded.items():
        original = getattr(workbench, name)
        def wrapper(*args, _original=original, _records=records, **kwargs):
            _records.append((args, kwargs))
            return _original(*args, **kwargs)
        monkeypatch.setattr(workbench, name, wrapper)
    return recorded


def test_idle_and_draft_reruns_have_no_scientific_or_persistence_side_effects(ui, calls):
    at = _app()
    _assert_clean_run(at)
    at.number_input(key="draft_seed").set_value(13).run()
    at.number_input(key="draft_distance_mm").set_value(-1.0).run()
    at.run()
    assert all(not entries for entries in calls.values()), calls
    assert at.session_state["workbench"].bundle is None
    assert not list(ui[2].iterdir())


def test_one_generate_action_saves_exactly_once_and_reruns_do_not_repeat(ui, calls):
    at = _app()
    at.number_input(key="draft_iterations").set_value(0).run()
    state = _generate(at)
    assert len(calls["run_and_save_bundle"]) == 1
    assert state.bundle is not None and state.bundle.path.is_dir()
    assert state.submitted is not None
    saved_path = state.bundle.path
    at.run()
    at.number_input(key="draft_seed").set_value(99).run()
    assert len(calls["run_and_save_bundle"]) == 1
    assert at.session_state["workbench"].bundle.path == saved_path
    assert not calls["replay_run_bundle"]


def test_submitted_result_keeps_saved_settings_after_draft_changes(ui, calls):
    at = _app()
    at.number_input(key="draft_iterations").set_value(0).run()
    state = _generate(at)
    before = state.bundle.config.to_dict()
    saved = state.bundle.path
    captured = state.submitted
    at.number_input(key="draft_seed").set_value(987).run()
    at.number_input(key="draft_dx_um").set_value(11.0).run()
    state = at.session_state["workbench"]
    assert state.bundle.path == saved
    assert state.bundle.config.to_dict() == before
    assert state.submitted is captured
    # Independently inspect the rendered saved metadata, not only the controller
    # object: the submitted seed remains visible and the new seed is draft-only.
    rendered = _text(at)
    assert str(saved) in rendered
    assert "Previous submission" in rendered
    assert _saved_configs(at) == [before]
    assert _saved_configs(at)[0]["solver"]["initialization"]["seed"] == 0
    assert len(calls["run_and_save_bundle"]) == 1


def test_same_name_same_size_upload_replacement_uses_actual_bytes(ui, calls):
    codes = np.array([[0, 51, 102], [153, 204, 255]], dtype=np.uint8)
    replacement = codes.copy()
    replacement[0, 1] = 17
    first, second = _png(codes), _png(replacement)
    assert len(first) == len(second) and first != second
    at = _app()
    _upload(at, codes, filename="same.png")
    first_state = _generate(at)
    first_bundle = first_state.bundle
    first_fingerprint = first_state.submitted.draft_fingerprint
    at.file_uploader(key="draft_upload").set_value(("same.png", second, "image/png")).run()
    assert at.session_state["workbench"].bundle.path == first_bundle.path
    assert len(calls["run_and_save_bundle"]) == 1
    state = _generate(at)
    assert len(calls["run_and_save_bundle"]) == 2
    assert state.bundle.path != first_bundle.path
    assert state.submitted.draft_fingerprint != first_fingerprint
    assert np.array_equal(first_bundle.arrays["target_intensity"], codes.astype(np.float64) / 255.0)
    assert np.array_equal(state.bundle.arrays["target_intensity"], replacement.astype(np.float64) / 255.0)
    assert hashlib.sha256(first).digest() != hashlib.sha256(second).digest()


def test_old_rendered_nonce_callback_after_completion_cannot_start_another_save(ui, calls):
    at = _app(inject_stale_callback=True)
    at.number_input(key="draft_iterations").set_value(0).run()
    # Capture the nonce actually associated with the old rendered action.
    old_nonce = _button(at, "generate").key.removeprefix("generate_")
    state = _generate(at)
    assert old_nonce in state.consumed_tokens
    assert old_nonce != state.offered_nonce
    saved = state.bundle.path
    submitted = state.submitted
    # Invoke the real callback in a later script context, when busy is already
    # false. Reusing a stale AppTest Widget alone could be a vacuous no-op.
    at.session_state["test_stale_generate_nonce"] = old_nonce
    at.run()
    _assert_clean_run(at)
    state = at.session_state["workbench"]
    assert len(calls["run_and_save_bundle"]) == 1
    assert state.pending is None and not state.busy
    assert state.bundle.path == saved and state.submitted is submitted
    assert state.error is None


def test_busy_state_disables_conflicting_controls_without_starting_work(ui, calls):
    at = _app()
    state = at.session_state["workbench"]
    state.busy = True
    at.run()
    _assert_clean_run(at)
    for prefix in ("generate", "open", "refresh", "strict", "diagnostic"):
        assert _button(at, prefix).disabled
    assert all(widget.disabled for widget in at.number_input)
    assert at.selectbox(key="draft_target_kind").disabled
    assert at.text_input(key="bundle_path_input").disabled
    assert all(not entries for entries in calls.values()), calls


@pytest.mark.parametrize("payload", [b"not a PNG", b""])
def test_invalid_uploaded_content_reports_error_without_false_success(ui, calls, payload):
    at = _app()
    at.selectbox(key="draft_target_kind").set_value("upload").run()
    at.file_uploader(key="draft_upload").upload("invalid.png", payload, "image/png").run()
    state = _generate(at)
    assert state.error
    assert at.error
    assert state.bundle is None
    assert not at.success
    assert not calls["run_and_save_bundle"]
    assert not calls["replay_run_bundle"]


def test_invalid_upload_then_explicit_valid_submission_recovers(ui, calls):
    at = _app()
    at.selectbox(key="draft_target_kind").set_value("upload").run()
    at.file_uploader(key="draft_upload").upload("same.png", b"not PNG", "image/png").run()
    assert _generate(at).error
    assert not calls["run_and_save_bundle"]
    codes = np.array([[0, 51, 102], [153, 204, 255]], dtype=np.uint8)
    _upload(at, codes, filename="same.png")
    state = _generate(at)
    assert state.error is None and state.bundle is not None
    assert not at.error
    assert len(calls["run_and_save_bundle"]) == 1
    assert np.array_equal(state.bundle.arrays["target_intensity"], codes.astype(np.float64) / 255.0)


def test_save_failure_is_visible_and_does_not_claim_or_retry_success(ui, calls, monkeypatch):
    def fail_save(*args, **kwargs):
        calls["run_and_save_bundle"].append((args, kwargs))
        raise OSError("injected save failure before publication")
    monkeypatch.setattr(ui[1], "run_and_save_bundle", fail_save)
    at = _app()
    at.number_input(key="draft_iterations").set_value(0).run()
    state = _generate(at)
    assert len(calls["run_and_save_bundle"]) == 1
    assert state.bundle is None and state.error
    assert "injected save failure" in _text(at)
    assert at.error and not at.success
    at.run()
    assert len(calls["run_and_save_bundle"]) == 1
    assert not list((ui[2] / "m6").glob("*/manifest.json"))


def test_post_save_presentation_failure_retains_bundle_and_explicit_refresh_recovers(ui, calls, monkeypatch):
    presentation = ui[0].presentation
    original = presentation.build_result_figures
    display_calls = []
    def fail_display(**kwargs):
        display_calls.append(kwargs)
        raise RuntimeError("injected presentation failure after publication")
    monkeypatch.setattr(presentation, "build_result_figures", fail_display)
    at = _app()
    at.number_input(key="draft_iterations").set_value(0).run()
    state = _generate(at)
    path = state.bundle.path
    submitted = state.submitted
    assert state.save_succeeded and state.saved_path == path
    assert state.presentation_error and state.error is None
    assert "injected presentation failure" in _text(at)
    assert str(path) in _text(at)
    assert "已成功" in _text(at) and "已保留" in _text(at)
    assert artifacts.verify_run_bundle(path).status == "passed"
    at.run()
    assert len(calls["run_and_save_bundle"]) == 1
    assert len(display_calls) == 1
    assert state.submitted is submitted and state.bundle.path == path
    monkeypatch.setattr(presentation, "build_result_figures", original)
    _button(at, "refresh").click().run()
    _assert_clean_run(at)
    recovered = at.session_state["workbench"]
    assert recovered.bundle.path == path
    assert recovered.presentation_error is None and recovered.error is None
    assert not at.error
    assert len(calls["run_and_save_bundle"]) == 1
    assert len(calls["verify_run_bundle"]) == 1
    assert len(calls["load_run_bundle"]) == 1
    assert not calls["replay_run_bundle"]
    assert _saved_configs(at) == [recovered.bundle.config.to_dict()]


def test_open_and_refresh_do_not_replay_or_invent_qualification(ui, calls):
    parent = ui[2] / "m5"
    parent.mkdir()
    saved = _existing(parent / "existing")
    at = _app()
    state = _open(at, saved.path)
    assert state.integrity == "passed"
    assert state.qualification == "not_evaluated" and state.comparison == "not_run"
    assert not calls["replay_run_bundle"]
    assert _statuses(at)["資格 Qualification"] == "not_evaluated"
    assert _statuses(at)["數值比較 Comparison"] == "not_run"
    _button(at, "refresh").click().run()
    _assert_clean_run(at)
    assert not calls["replay_run_bundle"]
    assert len(calls["verify_run_bundle"]) == 1
    assert state.qualification == "not_evaluated" and state.comparison == "not_run"


def test_over_limit_valid_bundle_keeps_metadata_disables_replay_and_open_recovers(ui, calls, monkeypatch):
    parent = ui[2] / "m5"
    parent.mkdir()
    settings = {
        "schema_version": 1,
        "grid": {"ny": 1, "nx": 513, "dy_m": 8e-6, "dx_m": 8e-6},
        "optics": {"wavelength_m": 633e-9, "distance_m": 0.0},
        "solver": {"algorithm": "gerchberg_saxton", "contract": "m3_periodic_lossless_asm_v1",
                   "iterations": 0, "initialization": {"mode": "seed", "seed": 0}},
        "metrics": {},
    }
    saved = artifacts.run_and_save_bundle(
        parent / "over_limit", config=RunConfig(settings),
        target_intensity=np.full((1, 513), 0.25, dtype=np.float64),
        source_amplitude=np.full((1, 513), 0.5, dtype=np.float64),
        source_revision=DIRTY_SOURCE,
    )
    valid = _existing(parent / "valid")
    solver_calls = []
    def unexpected_solver(*args, **kwargs):
        solver_calls.append((args, kwargs))
        raise AssertionError("opening/refreshing an existing bundle must not run the solver")
    monkeypatch.setattr(artifacts, "gerchberg_saxton", unexpected_solver)
    at = _app()
    state = _open(at, saved.path)
    assert state.bundle.path == saved.path and state.integrity == "passed"
    assert state.error is None and not at.error
    assert _saved_configs(at) == [saved.config.to_dict()]
    assert any("有效 bundle 超出本 App 操作限制" in str(item.value) for item in at.warning)
    assert _button(at, "strict").disabled and _button(at, "diagnostic").disabled
    assert not _button(at, "open").disabled and not _button(at, "refresh").disabled
    at.checkbox(key="diagnostic_enabled").check().run()
    _assert_clean_run(at)
    assert _button(at, "strict").disabled and _button(at, "diagnostic").disabled
    _button(at, "refresh").click().run()
    _assert_clean_run(at)
    assert _saved_configs(at) == [saved.config.to_dict()]
    assert at.session_state["workbench"].integrity == "passed"
    assert not at.error
    # Changing the selection alone still displays the over-limit bundle. Only
    # an explicit successful Open may re-enable replay for the new bundle.
    at.text_input(key="bundle_path_input").set_value(str(valid.path)).run()
    assert at.session_state["workbench"].bundle.path == saved.path
    assert _button(at, "strict").disabled and _button(at, "diagnostic").disabled
    _button(at, "open").click().run()
    _assert_clean_run(at)
    assert at.session_state["workbench"].bundle.path == valid.path
    assert _saved_configs(at) == [valid.config.to_dict()]
    assert not _button(at, "strict").disabled
    assert _button(at, "diagnostic").disabled
    at.checkbox(key="diagnostic_enabled").check().run()
    _assert_clean_run(at)
    assert not _button(at, "strict").disabled and not _button(at, "diagnostic").disabled
    assert not solver_calls and not calls["replay_run_bundle"]
    assert not calls["run_and_save_bundle"]
    assert len(calls["load_run_bundle"]) == 3 and len(calls["verify_run_bundle"]) == 1


def test_strict_replay_never_silently_enables_diagnostics(ui, calls):
    parent = ui[2] / "m5"
    parent.mkdir()
    saved = _existing(parent / "dirty")
    at = _app()
    _open(at, saved.path)
    assert not at.checkbox(key="diagnostic_enabled").value
    _button(at, "strict").click().run()
    _assert_clean_run(at)
    assert len(calls["replay_run_bundle"]) == 1
    assert calls["replay_run_bundle"][0][1]["diagnostic"] is False
    state = at.session_state["workbench"]
    assert state.integrity == "passed"
    assert state.qualification == "unqualified" and state.comparison == "not_run"
    assert _statuses(at)["數值比較 Comparison"] == "not_run"
    assert not at.checkbox(key="diagnostic_enabled").value
    assert _button(at, "diagnostic").disabled


def test_diagnostic_replay_requires_enablement_action_and_resets_on_selection_change(ui, calls):
    parent = ui[2] / "m5"
    parent.mkdir()
    first = _existing(parent / "first")
    second = _existing(parent / "second")
    at = _app()
    _open(at, first.path)
    assert _button(at, "diagnostic").disabled
    at.checkbox(key="diagnostic_enabled").check().run()
    assert not calls["replay_run_bundle"]
    assert not _button(at, "diagnostic").disabled
    _button(at, "diagnostic").click().run()
    _assert_clean_run(at)
    assert len(calls["replay_run_bundle"]) == 1
    assert calls["replay_run_bundle"][0][1]["diagnostic"] is True
    state = at.session_state["workbench"]
    assert state.qualification == "unqualified" and state.comparison == "passed"
    assert _statuses(at)["資格 Qualification"] == "unqualified"
    at.text_input(key="bundle_path_input").set_value(str(second.path)).run()
    assert not at.checkbox(key="diagnostic_enabled").value
    assert _button(at, "diagnostic").disabled
    assert len(calls["replay_run_bundle"]) == 1


def test_loaded_bundle_displays_its_explicit_phase_nonuniform_source_and_all_metrics(ui, calls):
    parent = ui[2] / "m5"
    parent.mkdir()
    saved = _existing(parent / "explicit", explicit=True)
    at = _app()
    _open(at, saved.path)
    assert _saved_configs(at) == [saved.config.to_dict()]
    assert _saved_configs(at)[0]["solver"]["initialization"]["mode"] == "explicit_phase"
    rendered = _text(at)
    assert "nonuniform" in rendered
    for name in saved.metrics:
        assert name in rendered
    assert "data_range" in rendered and "2.0" in rendered
    assert "signal_mask" in rendered and "cv_mask" in rendered
    assert not calls["run_and_save_bundle"] and not calls["replay_run_bundle"]


def test_exact_match_positive_infinite_psnr_is_explicitly_displayed(ui, calls):
    parent = ui[2] / "m5"
    parent.mkdir()
    saved = _existing(parent / "infinite", explicit=True, constant=True)
    assert saved.metrics["intensity_psnr"] == float("inf")
    at = _app()
    _open(at, saved.path)
    assert "+∞" in _text(at)
    assert "intensity_psnr" in _text(at)


def test_refresh_detects_changed_file_and_clears_success_for_that_attempt(ui, calls):
    parent = ui[2] / "m5"
    parent.mkdir()
    saved = _existing(parent / "changed")
    at = _app()
    _open(at, saved.path)
    metrics_path = saved.path / "metrics.json"
    metrics_path.write_bytes(metrics_path.read_bytes() + b"\n")
    _button(at, "refresh").click().run()
    _assert_clean_run(at)
    state = at.session_state["workbench"]
    assert state.error and state.bundle is None
    assert at.error and not at.success
    assert "passed" not in _statuses(at).values()
    assert not calls["replay_run_bundle"]


def test_new_app_session_does_not_regenerate_previous_session_result(ui, calls):
    at = _app()
    at.number_input(key="draft_iterations").set_value(0).run()
    saved = _generate(at).bundle.path
    fresh = _app()
    _assert_clean_run(fresh)
    assert len(calls["run_and_save_bundle"]) == 1
    assert fresh.session_state["workbench"].bundle is None
    assert saved.is_dir()


def test_initial_workbench_loads_real_entrypoint_without_pythonpath_change():
    at = AppTest.from_file(str(ROOT / "apps" / "streamlit_app.py"), default_timeout=30).run()
    _assert_clean_run(at)
    assert at.title
    assert at.session_state["workbench"].bundle is None
