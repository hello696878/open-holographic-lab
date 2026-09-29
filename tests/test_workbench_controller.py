"""M6 orchestration tests: real M2--M5 boundaries, isolated run directories."""

from dataclasses import FrozenInstanceError, replace
from io import BytesIO
from pathlib import Path
import stat
import subprocess
from types import SimpleNamespace

import numpy as np
from PIL import Image
import pytest

from apps import provenance, workbench as wb
from ohlab.grid import SamplingGrid
from ohlab.io.artifacts import run_and_save_bundle
from ohlab.io.config import RunConfig
from ohlab.targets import intensity_to_amplitude


SOURCE = {"revision": "a" * 40, "state": "clean", "method": "git"}


def png_bytes(codes: np.ndarray) -> bytes:
    with BytesIO() as stream, Image.fromarray(codes) as image:
        image.save(stream, format="PNG", compress_level=0)
        return stream.getvalue()


def small_draft(**changes: object) -> wb.RunDraft:
    codes = np.arange(10, 58, dtype=np.uint8).reshape(6, 8)
    base = wb.RunDraft(target_kind="upload", ny=6, nx=8, iterations=2,
                       upload_bytes=png_bytes(codes), upload_name="target.png")
    return replace(base, **changes)


@pytest.fixture(autouse=True)
def stable_provenance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wb, "detect_source_revision", lambda: dict(SOURCE))


def generate(runs: Path, draft: wb.RunDraft | None = None) -> wb.WorkbenchState:
    state = wb.WorkbenchState()
    assert wb.submit_generate(state, draft or small_draft(), offered_nonce=state.offered_nonce, runs_root=runs)
    assert wb.execute_pending_run(state), state.error
    return state


def test_consumed_nonce_blocks_duplicate_generation_after_completion(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    state = wb.WorkbenchState()
    nonce = state.offered_nonce
    calls = []
    original = wb.run_and_save_bundle

    def save(path, **kwargs):
        calls.append(path)
        assert state.pending is None and nonce in state.consumed_tokens
        assert state.busy
        assert not wb.submit_generate(state, small_draft(), offered_nonce=nonce, runs_root=runs)
        return original(path, **kwargs)

    monkeypatch.setattr(wb, "run_and_save_bundle", save)
    assert wb.submit_generate(state, small_draft(), offered_nonce=nonce, runs_root=runs)
    destination = state.pending.destination
    assert not runs.exists()  # Submission itself does not write or run science.
    assert not wb.submit_generate(state, small_draft(), offered_nonce=nonce, runs_root=runs)
    assert wb.execute_pending_run(state), state.error
    assert not wb.submit_generate(state, small_draft(), offered_nonce=nonce, runs_root=runs)
    assert not wb.execute_pending_run(state)
    assert calls == [destination]
    assert list((runs / "m6").iterdir()) == [destination]
    assert state.save_succeeded and state.saved_path == destination
    assert state.integrity == "passed"
    assert state.qualification == "not_evaluated" and state.comparison == "not_run"
    assert state.last_operation == "generate" and state.last_operation_path == destination
    assert state.last_operation_at.endswith("+00:00")


def test_submitted_identity_is_immutable_and_draft_changes_do_not_relabel(tmp_path):
    draft = small_draft()
    state = generate(tmp_path / "runs", draft)
    submitted = state.submitted
    saved = state.bundle
    changed = replace(draft, seed=900, distance_mm=-12.0, upload_name="new-name.png")
    assert wb.draft_fingerprint(changed) != submitted.draft_fingerprint
    assert state.submitted is submitted and state.bundle is saved
    assert saved.config.to_dict()["solver"]["initialization"] == {"mode": "seed", "seed": 0}
    exported = submitted.config.to_dict()
    exported["solver"]["initialization"]["seed"] = 999
    assert submitted.config.to_dict()["solver"]["initialization"]["seed"] == 0
    assert not hasattr(submitted, "__dict__") and not hasattr(draft, "__dict__")
    with pytest.raises(FrozenInstanceError):
        submitted.destination = Path("elsewhere")
    with pytest.raises(FrozenInstanceError):
        draft.seed = 900


def test_same_name_and_size_replacement_uses_actual_upload_bytes(tmp_path):
    first = small_draft()
    second = replace(first, upload_bytes=png_bytes(np.full((6, 8), 180, dtype=np.uint8)))
    assert first.upload_name == second.upload_name
    assert len(first.upload_bytes) == len(second.upload_bytes)
    assert wb.draft_fingerprint(first) != wb.draft_fingerprint(second)
    state = generate(tmp_path / "runs", first)
    previous = state.submitted
    assert previous.upload_bytes == first.upload_bytes
    assert state.bundle.arrays["target_intensity"].tobytes() == (
        np.arange(10, 58, dtype=np.uint8).reshape(6, 8).astype(np.float64) / 255.0
    ).tobytes()
    assert state.submitted is previous  # Merely creating a changed draft did nothing.
    assert wb.submit_generate(state, second, offered_nonce=state.offered_nonce, runs_root=tmp_path / "runs")
    assert wb.execute_pending_run(state)
    assert state.submitted.upload_sha256 != previous.upload_sha256
    assert np.all(state.bundle.arrays["target_intensity"] == 180.0 / 255.0)


def test_builtin_png_is_exact_m5_fixture_and_pitch_reinterprets_same_pixels(tmp_path):
    from examples.run_bundle import _write_fixture_png

    reference = tmp_path / "reference.png"
    _write_fixture_png(reference, SamplingGrid(ny=64, nx=64, dy=8e-6, dx=8e-6))
    first = generate(tmp_path / "runs", wb.RunDraft(iterations=0))
    second = generate(tmp_path / "runs", wb.RunDraft(iterations=0, dx_um=12.0, dy_um=10.0))
    assert (first.saved_path / "input_target.png").read_bytes() == reference.read_bytes()
    assert (second.saved_path / "input_target.png").read_bytes() == reference.read_bytes()
    assert first.bundle.arrays["target_intensity"].tobytes() == second.bundle.arrays["target_intensity"].tobytes()
    assert first.bundle.arrays["source_amplitude"].tobytes() == second.bundle.arrays["source_amplitude"].tobytes()
    assert wb.builtin_grayscale() is not wb.builtin_grayscale()


def test_one_si_conversion_and_explicit_matched_uniform_illumination(tmp_path):
    draft = small_draft(dx_um=9.25, dy_um=11.5, wavelength_nm=532.0, distance_mm=-2.5)
    state = generate(tmp_path / "runs", draft)
    spec = state.bundle.config.to_dict()
    assert spec["grid"]["dx_m"] == 9.25 * 1e-6
    assert spec["grid"]["dy_m"] == 11.5 * 1e-6
    assert spec["optics"] == {"wavelength_m": 532.0 * 1e-9, "distance_m": -2.5 * 1e-3}
    source = state.bundle.arrays["source_amplitude"]
    target = state.bundle.arrays["target_amplitude"]
    expected_value = float(np.sqrt(np.sum(target**2) / target.size))
    assert np.all(source == expected_value)
    # The only rounding here is sqrt then squaring; 8eps bounds this 48-pixel
    # fixture comfortably without importing M3's broader acceptance tolerance.
    assert np.sum(source**2) == pytest.approx(np.sum(target**2), rel=8*np.finfo(float).eps, abs=0.0)
    assert len(state.bundle.arrays["residual_history"]) == draft.iterations + 1


@pytest.mark.parametrize("change, message", [
    ({"ny": 0}, "ny"), ({"nx": 513}, "nx"), ({"iterations": -1}, "iterations"),
    ({"iterations": 201}, "iterations"), ({"ny": 512, "nx": 512, "iterations": 51}, "work limit"),
    ({"seed": -1}, "seed"), ({"seed": 2**32}, "seed"), ({"seed": True}, "seed"),
    ({"ny": True}, "ny"), ({"iterations": 1.0}, "iterations"),
    ({"dx_um": 0.0}, "dx_um"), ({"dy_um": float("nan")}, "dy_um"),
    ({"wavelength_nm": float("inf")}, "wavelength_nm"), ({"distance_mm": float("nan")}, "distance_mm"),
    ({"psnr_data_range": 0.0}, "psnr_data_range"), ({"psnr_data_range": True}, "psnr_data_range"),
    ({"upload_bytes": b""}, "encoded bytes"),
    ({"upload_bytes": b"x" * (wb.UPLOAD_LIMIT + 1)}, "encoded bytes"),
    ({"upload_bytes": bytearray(b"abc")}, "immutable"),
    ({"target_kind": "other"}, "target_kind"),
])
def test_invalid_draft_rejected_before_writes_or_save(tmp_path, monkeypatch, change, message):
    monkeypatch.setattr(wb, "run_and_save_bundle", lambda *a, **k: pytest.fail("save must not run"))
    state = wb.WorkbenchState()
    assert not wb.submit_generate(state, replace(small_draft(), **change),
                                  offered_nonce=state.offered_nonce, runs_root=tmp_path / "runs")
    assert message in state.error
    assert not (tmp_path / "runs").exists()
    assert state.bundle is None and not state.save_succeeded


@pytest.mark.parametrize("seed", [0, 2**32 - 1])
def test_exact_app_work_and_seed_boundaries_can_be_submitted_without_running(tmp_path, seed):
    state = wb.WorkbenchState()
    draft = small_draft(ny=512, nx=512, iterations=50, seed=seed)
    assert wb.submit_generate(state, draft, offered_nonce=state.offered_nonce, runs_root=tmp_path / "runs")
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("distance", [float.fromhex("0x0.0000000000001p-1022"),
                                     -float.fromhex("0x0.0000000000001p-1022")])
def test_nonzero_distance_cannot_silently_underflow_during_si_conversion(tmp_path, distance):
    state = wb.WorkbenchState()
    assert not wb.submit_generate(state, small_draft(distance_mm=distance),
                                  offered_nonce=state.offered_nonce, runs_root=tmp_path / "runs")
    assert "nonzero distance underflows" in state.error
    assert state.pending is None and not (tmp_path / "runs").exists()


@pytest.mark.parametrize("distance", [0.0, -0.0])
def test_explicit_signed_zero_distance_survives_si_conversion(tmp_path, distance):
    state = wb.WorkbenchState()
    assert wb.submit_generate(state, small_draft(distance_mm=distance),
                              offered_nonce=state.offered_nonce, runs_root=tmp_path / "runs")
    actual = state.pending.config.to_dict()["optics"]["distance_m"]
    assert actual.hex() == distance.hex()
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("codes, message", [
    (np.zeros((6, 8), dtype=np.uint8), "blank"),
    (np.ones((5, 8), dtype=np.uint8), "shape"),
    (np.ones((6, 8, 3), dtype=np.uint8), "grayscale"),
])
def test_m2_or_blank_rejection_never_saves(tmp_path, monkeypatch, codes, message):
    monkeypatch.setattr(wb, "run_and_save_bundle", lambda *a, **k: pytest.fail("save must not run"))
    state = wb.WorkbenchState()
    draft = small_draft(upload_bytes=png_bytes(codes))
    assert wb.submit_generate(state, draft, offered_nonce=state.offered_nonce, runs_root=tmp_path / "runs")
    assert not wb.execute_pending_run(state)
    assert message in state.error
    assert list((tmp_path / "runs" / "m6").iterdir()) == []
    assert state.pending is None and not state.busy and not state.save_succeeded


@pytest.mark.parametrize("failure", [OSError("injected persistence failure"), KeyboardInterrupt()])
def test_failed_or_interrupted_save_is_consumed_and_never_retried(tmp_path, monkeypatch, failure):
    calls = []

    def fail(*args, **kwargs):
        calls.append(args[0])
        raise failure

    monkeypatch.setattr(wb, "run_and_save_bundle", fail)
    state = wb.WorkbenchState()
    nonce = state.offered_nonce
    assert wb.submit_generate(state, small_draft(), offered_nonce=nonce, runs_root=tmp_path / "runs")
    if isinstance(failure, KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            wb.execute_pending_run(state)
        assert state.stage == "interrupted"
    else:
        assert not wb.execute_pending_run(state)
        assert "injected persistence failure" in state.error
    assert not wb.execute_pending_run(state)
    assert not wb.submit_generate(state, small_draft(), offered_nonce=nonce, runs_root=tmp_path / "runs")
    assert len(calls) == 1 and state.pending is None and not state.busy
    assert state.bundle is None and not state.save_succeeded and state.saved_path is None


def test_presentation_failure_keeps_completed_save_and_explicit_open_recovers(tmp_path):
    runs = tmp_path / "runs"
    state = generate(runs)
    bundle, submitted, path = state.bundle, state.submitted, state.saved_path
    wb.record_presentation_failure(state, RuntimeError("injected plot failure"))
    assert state.bundle is bundle and state.submitted is submitted
    assert state.saved_path == path and state.save_succeeded
    assert state.error is None and "injected plot failure" in state.presentation_error
    assert not wb.execute_pending_run(state)
    assert wb.open_bundle(state, path, runs_root=runs, offered_nonce=state.offered_nonce)
    assert state.presentation_error is None and state.bundle.path == path
    assert state.submitted is None  # Loaded data has no invented current-draft identity.


def test_post_save_temp_cleanup_failure_retains_published_bundle_identity(tmp_path, monkeypatch):
    original = wb.TemporaryDirectory

    class FailingCleanup:
        def __init__(self, **kwargs):
            self.inner = original(**kwargs)

        def __enter__(self):
            return self.inner.__enter__()

        def __exit__(self, *args):
            self.inner.__exit__(*args)
            raise OSError("injected upload staging cleanup failure")

    monkeypatch.setattr(wb, "TemporaryDirectory", FailingCleanup)
    state = wb.WorkbenchState()
    assert wb.submit_generate(state, small_draft(), offered_nonce=state.offered_nonce, runs_root=tmp_path / "runs")
    attempt = state.pending
    assert not wb.execute_pending_run(state)
    assert state.save_succeeded and state.saved_path == attempt.destination
    assert state.bundle.path == attempt.destination and state.submitted is attempt
    assert state.saved_path.is_dir() and state.integrity == "passed"
    assert "cleanup failure" in state.error and not state.busy


def test_new_failed_attempt_cannot_relabel_previous_arrays_or_claim_success(tmp_path):
    runs = tmp_path / "runs"
    state = generate(runs)
    previous_path = state.saved_path
    draft = small_draft(upload_bytes=png_bytes(np.zeros((6, 8), dtype=np.uint8)))
    assert wb.submit_generate(state, draft, offered_nonce=state.offered_nonce, runs_root=runs)
    assert state.bundle is None and state.submitted is None
    assert not wb.execute_pending_run(state)
    assert state.bundle is None and not state.save_succeeded
    assert previous_path.is_dir()


def test_rejected_draft_consumes_nonce_and_clears_previous_success(tmp_path):
    runs = tmp_path / "runs"
    state = generate(runs)
    previous_path = state.saved_path
    nonce = state.offered_nonce
    assert not wb.submit_generate(state, small_draft(seed=-1), offered_nonce=nonce, runs_root=runs)
    assert nonce in state.consumed_tokens and nonce != state.offered_nonce
    assert not wb.submit_generate(state, small_draft(), offered_nonce=nonce, runs_root=runs)
    assert state.bundle is None and state.submitted is None and not state.save_succeeded
    assert state.integrity == state.qualification == "not_evaluated" and state.comparison == "not_run"
    assert not state.busy and state.pending is None and previous_path.is_dir()


def explicit_bundle(runs: Path):
    destination = runs / "m5" / "explicit"
    destination.parent.mkdir(parents=True)
    config = RunConfig({
        "schema_version": 1, "grid": {"ny": 3, "nx": 4, "dy_m": 8e-6, "dx_m": 9e-6},
        "optics": {"wavelength_m": 633e-9, "distance_m": 0.001},
        "solver": {"algorithm": "gerchberg_saxton", "contract": "m3_periodic_lossless_asm_v1",
                   "iterations": 2, "initialization": {"mode": "explicit_phase", "artifact": "initial_phase.npy"}},
        "metrics": {"intensity_mse": {}, "intensity_nmse": {}, "intensity_psnr": {"data_range": 2.5},
                    "signal_region_power_fraction": {"mask": "signal_mask.npy"},
                    "regional_intensity_cv": {"mask": "cv_mask.npy"}},
    })
    target = np.arange(1, 13, dtype=np.float64).reshape(3, 4) / 12.0
    grid = SamplingGrid(ny=3, nx=4, dy=8e-6, dx=9e-6)
    source = intensity_to_amplitude(target, grid=grid)
    mask = np.indices((3, 4)).sum(axis=0) % 2 == 0
    return run_and_save_bundle(destination, config=config, target_intensity=target, source_amplitude=source,
                               initial_phase=np.arange(12, dtype=np.float64).reshape(3, 4) / 10.0,
                               signal_mask=mask, cv_mask=~mask, source_revision=SOURCE)


def test_open_preserves_explicit_phase_nonuniform_source_and_all_saved_metrics(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    original = explicit_bundle(runs)
    monkeypatch.setattr(wb, "replay_run_bundle", lambda *a, **k: pytest.fail("open must not replay"))
    state = wb.WorkbenchState()
    assert wb.open_bundle(state, "m5/explicit", runs_root=runs, offered_nonce=state.offered_nonce)
    assert state.bundle.config.to_dict() == original.config.to_dict()
    assert state.bundle.arrays["source_amplitude"].tobytes() == original.arrays["source_amplitude"].tobytes()
    assert len(state.bundle.metrics) == 5 and state.submitted is None
    assert state.qualification == "not_evaluated" and state.comparison == "not_run"


def test_reverify_calls_verify_then_load_and_resets_replay_status(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    state = generate(runs)
    path = state.saved_path
    assert wb.replay_bundle(state, path, runs_root=runs, offered_nonce=state.offered_nonce)
    assert state.qualification == "qualified" and state.comparison == "passed"
    calls = []
    for name in ("verify_run_bundle", "load_run_bundle"):
        original = getattr(wb, name)

        def wrapped(*args, _name=name, _original=original, **kwargs):
            calls.append(_name)
            return _original(*args, **kwargs)

        monkeypatch.setattr(wb, name, wrapped)
    assert wb.reverify_bundle(state, path, runs_root=runs, offered_nonce=state.offered_nonce)
    assert calls == ["verify_run_bundle", "load_run_bundle"]
    assert state.qualification == "not_evaluated" and state.comparison == "not_run"
    assert state.replay_report is None


def test_dirty_replay_never_enables_diagnostic_automatically_and_detects_afresh(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    state = generate(runs)
    path = state.saved_path
    calls = []

    def current():
        calls.append(1)
        return {**SOURCE, "state": "dirty"}

    monkeypatch.setattr(wb, "detect_source_revision", current)
    assert wb.replay_bundle(state, path, runs_root=runs, offered_nonce=state.offered_nonce)
    assert state.qualification == "unqualified" and state.comparison == "not_run"
    assert wb.replay_bundle(state, path, runs_root=runs, offered_nonce=state.offered_nonce, diagnostic=True)
    assert state.qualification == "unqualified" and state.comparison == "passed"
    assert len(calls) == 2


def test_selection_change_resets_diagnostic_opt_in_and_failed_open_clears_old_view(tmp_path):
    runs = tmp_path / "runs"
    state = generate(runs)
    state.diagnostic_enabled = True
    assert not wb.open_bundle(state, "m6/missing", runs_root=runs, offered_nonce=state.offered_nonce)
    assert not state.diagnostic_enabled and state.bundle is None
    assert state.integrity == "not_evaluated" and state.comparison == "not_run"


def test_replay_exception_after_fresh_load_clears_all_success_badges(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    state = generate(runs)
    path = state.saved_path

    def fail(*args, **kwargs):
        assert state.bundle is not None and state.integrity == "passed"
        raise ValueError("injected replay integrity failure after load")

    monkeypatch.setattr(wb, "replay_run_bundle", fail)
    nonce = state.offered_nonce
    assert not wb.replay_bundle(state, path, runs_root=runs, offered_nonce=nonce)
    assert state.integrity == state.qualification == "not_evaluated" and state.comparison == "not_run"
    assert state.bundle is None and state.replay_report is None
    assert "injected replay integrity failure" in state.error
    assert not wb.replay_bundle(state, path, runs_root=runs, offered_nonce=nonce)


def test_large_valid_bundle_is_loaded_but_not_replayed_as_corruption(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    original = explicit_bundle(runs)
    settings = original.config.to_dict()
    settings["solver"]["iterations"] = 201
    larger = SimpleNamespace(path=original.path, config=RunConfig(settings), arrays=original.arrays)
    monkeypatch.setattr(wb, "load_run_bundle", lambda path: larger)
    monkeypatch.setattr(wb, "replay_run_bundle", lambda *a, **k: pytest.fail("outside app work budget"))
    state = wb.WorkbenchState()
    assert wb.open_bundle(state, original.path, runs_root=runs, offered_nonce=state.offered_nonce)
    assert state.integrity == "passed" and "outside app" in wb.bundle_operating_limit(state.bundle)
    assert not wb.replay_bundle(state, original.path, runs_root=runs, offered_nonce=state.offered_nonce)
    assert state.integrity == "not_evaluated" and state.comparison == "not_run"
    assert "outside app" in state.error  # Resource policy, not a corruption claim.


@pytest.mark.parametrize("selection", ["../outside", "m6/../../outside", ""])
def test_selection_rejects_lexical_escape_and_root(tmp_path, selection):
    with pytest.raises(ValueError):
        wb.selected_bundle_path(selection, runs_root=tmp_path / "runs")
    with pytest.raises(ValueError):
        wb.selected_bundle_path(tmp_path / "outside", runs_root=tmp_path / "runs")


def test_selected_path_keeps_lexical_identity_and_rejects_reparse_ancestor(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    selected = runs / "m5" / "bundle"
    selected.mkdir(parents=True)
    assert wb.selected_bundle_path(selected, runs_root=runs) == selected.absolute()
    original = Path.lstat

    def lstat(path):
        if path == selected.parent:
            return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
        return original(path)

    monkeypatch.setattr(Path, "lstat", lstat)
    with pytest.raises(ValueError, match="reparse"):
        wb.selected_bundle_path(selected, runs_root=runs)


@pytest.mark.parametrize("kind", ["count", "file", "total", "directory"])
def test_stat_preflight_rejects_resource_limits_before_m5_read(tmp_path, monkeypatch, kind):
    runs = tmp_path / "runs"
    path = runs / "m5" / "candidate"
    path.mkdir(parents=True)
    sizes = {"count": [0] * 17, "file": [wb.FILE_LIMIT + 1],
             "total": [wb.FILE_LIMIT] * 5, "directory": []}[kind]
    for number, size in enumerate(sizes):
        with (path / str(number)).open("wb") as stream:
            stream.truncate(size)  # Sparse/stat-only fixtures, not loaded data.
    if kind == "directory":
        (path / "nested").mkdir()
    monkeypatch.setattr(wb, "load_run_bundle", lambda *a, **k: pytest.fail("must not read unbounded content"))
    state = wb.WorkbenchState()
    assert not wb.open_bundle(state, path, runs_root=runs, offered_nonce=state.offered_nonce)
    assert state.bundle is None and state.error is not None


def test_stat_preflight_inclusive_limits_and_candidate_listing_are_bounded(tmp_path):
    runs = tmp_path / "runs"
    path = runs / "m5" / "candidate"
    path.mkdir(parents=True)
    for index in range(16):
        with (path / str(index)).open("wb") as stream:
            stream.truncate(wb.FILE_LIMIT if index < 4 else 0)
    wb.preflight_bundle(path, runs_root=runs)
    for relative in ("m5/completed", "m6/completed", "m6/.ohlab-partial-x", "m6/.upload-x", "m5/group/deep"):
        directory = runs / relative
        directory.mkdir(parents=True)
        for name in ("manifest.json", "config.json", "metrics.json"):
            (directory / name).write_bytes(b"{}")
    assert wb.list_bundle_candidates(runs_root=runs) == (runs / "m5/completed", runs / "m6/completed")


@pytest.mark.parametrize("dirty", [False, True])
def test_provenance_anchors_imported_checkout_and_redetects_each_call(tmp_path, monkeypatch, dirty):
    checkout = tmp_path / "checkout"
    package = checkout / "src" / "ohlab"
    monkeypatch.setattr(provenance.ohlab, "__file__", str(package / "__init__.py"))
    monkeypatch.chdir(tmp_path)
    outputs = iter([str(checkout), "src/ohlab/__init__.py", "b" * 40, " M apps/workbench.py" if dirty else ""] * 2)
    calls = []

    def run(arguments, **kwargs):
        calls.append((arguments, kwargs))
        return SimpleNamespace(stdout=next(outputs))

    monkeypatch.setattr(provenance.subprocess, "run", run)
    for _ in range(2):
        assert provenance.detect_source_revision() == {"revision": "b" * 40, "state": "dirty" if dirty else "clean", "method": "git"}
    assert len(calls) == 8
    assert calls[0][0][:3] == ["git", "-C", str(package)]
    assert all(call[0][2] == str(checkout) for call in calls[1:4])
    assert all(call[1]["timeout"] == 10 and call[1]["env"]["GIT_OPTIONAL_LOCKS"] == "0" for call in calls)


@pytest.mark.parametrize("failure", [FileNotFoundError("git"), subprocess.TimeoutExpired("git", 10),
                                     subprocess.CalledProcessError(1, "git"), UnicodeError("decode")])
def test_provenance_failure_is_explicit_unavailable(monkeypatch, failure):
    def fail(*a, **k):
        raise failure

    monkeypatch.setattr(provenance.subprocess, "run", fail)
    assert provenance.detect_source_revision() == {"revision": None, "state": "unavailable", "method": "git"}


@pytest.mark.parametrize("case", ["no_file", "foreign_checkout", "untracked", "bad_sha"])
def test_provenance_never_guesses_missing_source_identity(tmp_path, monkeypatch, case):
    checkout = tmp_path / "checkout"
    monkeypatch.setattr(provenance.ohlab, "__file__", None if case == "no_file" else str(checkout / "src/ohlab/__init__.py"))
    outputs = iter([str(tmp_path / "foreign") if case == "foreign_checkout" else str(checkout),
                    "wrong" if case == "untracked" else "src/ohlab/__init__.py", "not-a-sha", ""])
    monkeypatch.setattr(provenance.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=next(outputs)))
    assert provenance.detect_source_revision()["state"] == "unavailable"


@pytest.mark.parametrize("history", [np.array([0.25]), np.array([0.4, 0.2, 0.21, 0.1])])
def test_presentation_shared_overshoot_scale_phase_and_all_history_without_mutation(history):
    from apps.presentation import build_result_figures, format_metric_value

    arrays = {"target_intensity": np.array([[0.0, 1.0], [0.5, 0.25]]),
              "reconstruction_intensity": np.array([[1.8, 0.2], [0.3, 0.4]]),
              "phase": np.array([[-np.pi, 0.0], [np.pi, 0.2]]), "residual_history": history}
    before = {key: value.tobytes() for key, value in arrays.items()}
    images, residuals = build_result_figures(arrays=arrays)
    assert images.axes[0].images[0].get_clim() == (0.0, 1.8)
    assert images.axes[1].images[0].get_clim() == (0.0, 1.8)
    assert images.axes[2].images[0].get_clim() == (-np.pi, np.pi)
    np.testing.assert_array_equal(residuals.axes[0].lines[0].get_ydata(), history)
    np.testing.assert_array_equal(residuals.axes[0].lines[0].get_xdata(), np.arange(history.size))
    assert before == {key: value.tobytes() for key, value in arrays.items()}
    assert format_metric_value("intensity_psnr", float("inf")) == "+∞"
    images.clear()
    residuals.clear()


def test_presentation_summary_uses_actual_loaded_settings_and_masks(tmp_path):
    from apps.presentation import summarize_bundle

    bundle = explicit_bundle(tmp_path / "runs")
    before = {key: value.tobytes() for key, value in bundle.arrays.items()}
    summary = summarize_bundle(arrays=bundle.arrays, config=bundle.config, metrics=bundle.metrics)
    assert summary["solver"]["initialization"]["mode"] == "explicit_phase"
    assert summary["illumination"]["kind"] == "nonuniform"
    assert summary["display"]["history_samples"] == 3
    rows = {row["name"]: row for row in summary["metrics"]}
    assert rows["intensity_psnr"]["parameters"] == {"data_range": 2.5}
    assert rows["regional_intensity_cv"]["selected_pixels"] == 6
    assert rows["signal_region_power_fraction"]["selected_pixels"] == 6
    assert {key: value["value"] for key, value in rows.items()} == dict(bundle.metrics)
    summary["solver"]["initialization"]["mode"] = "changed-display-copy"
    assert bundle.config.to_dict()["solver"]["initialization"]["mode"] == "explicit_phase"
    assert before == {key: value.tobytes() for key, value in bundle.arrays.items()}
