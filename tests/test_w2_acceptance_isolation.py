"""No-browser negative controls for the actual W2 acceptance preflight."""
import importlib.util
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/w2_acceptance.py"
spec = importlib.util.spec_from_file_location("w2_acceptance_isolation", SCRIPT)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def test_fresh_sibling_outputs_and_exclusive_bytes(tmp_path):
    owner = tmp_path / "runs/task/invocation"
    outputs = {"runner": owner / "runner", "evidence": owner / "evidence", "figures": owner / "figures"}
    assert launcher.validate_outputs(owner, outputs, workspace=tmp_path)["status"] == "PASS"
    owner.mkdir(parents=True)
    path = owner / "retained.txt"
    launcher.exclusive_bytes(path, b"original evidence")
    with pytest.raises(FileExistsError):
        launcher.exclusive_bytes(path, b"replacement")
    assert path.read_bytes() == b"original evidence"


@pytest.mark.parametrize("kind", ["case_alias", "ancestor", "escape", "root", "existing"])
def test_collisions_reject_before_process_and_preserve_evidence(tmp_path, kind):
    owner = tmp_path / "runs/task/invocation"
    owner.mkdir(parents=True)
    original = owner / "original.txt"
    original.write_bytes(b"preserve")
    outputs = {"one": owner / "runner", "two": owner / "other"}
    if kind == "case_alias": outputs["two"] = owner / "RUNNER"
    if kind == "ancestor": outputs["two"] = owner / "runner/child"
    if kind == "escape": outputs["two"] = tmp_path / "outside"
    if kind == "root": outputs["two"] = owner
    if kind == "existing": outputs["two"] = original
    with pytest.raises(ValueError):
        launcher.validate_outputs(owner, outputs, workspace=tmp_path)
    assert original.read_bytes() == b"preserve"
    assert not outputs["one"].exists()


def test_custom_environment_scans_every_selected_output_variable(tmp_path):
    owner = tmp_path / "spec.ts"
    owner.write_text("process.env.W2_EVIDENCE_DIR; process.env.R03_UX_EVIDENCE_DIR; process.env.V2G_FIGURE_DIR; process.env.V2E_FIXTURES", encoding="utf-8")
    result = launcher.scan_environment([owner])
    assert result["outputs"] == ["R03_UX_EVIDENCE_DIR", "V2G_FIGURE_DIR", "W2_EVIDENCE_DIR"]
    assert "V2E_FIXTURES" in result["all"]


def test_reparse_ancestor_is_rejected_without_requiring_windows_privilege(tmp_path, monkeypatch):
    owner = tmp_path / "runs/task"
    owner.mkdir(parents=True)
    original = Path.lstat
    class Linked:
        st_mode = 0
        st_file_attributes = 0x400
    def info(path, *args, **kwargs):
        return Linked() if path == owner else original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "lstat", info)
    with pytest.raises(ValueError, match="reparse"):
        launcher.validate_outputs(owner, {"data": owner / "data"}, workspace=tmp_path)


def test_child_settings_copy_does_not_change_parent(monkeypatch):
    monkeypatch.setenv("W2_EVIDENCE_DIR", "stale")
    monkeypatch.setenv("HTTP_PROXY", "preserved-proxy")
    child = launcher.child_environment({"W2_EVIDENCE_DIR": "fresh"})
    assert child["W2_EVIDENCE_DIR"] == "fresh"
    assert child["HTTP_PROXY"] == "preserved-proxy"
    assert launcher.os.environ["W2_EVIDENCE_DIR"] == "stale"


def test_graceful_stop_targets_only_registered_owned_child_and_restores_class(tmp_path, monkeypatch):
    class Original:
        def __init__(self, *args, **kwargs):
            self.should_exit = False
    foreign = Original()
    module = SimpleNamespace(Server=Original)
    monkeypatch.setitem(sys.modules, "uvicorn", module)
    with launcher.owned_server_lifetime(tmp_path):
        owned = module.Server(None)
        (tmp_path / "stop.flag").write_bytes(b"Stop this test-owned instance only")
        for _ in range(100):
            if owned.should_exit:
                break
            threading.Event().wait(.01)
        assert owned.should_exit
        assert not foreign.should_exit
        assert (tmp_path / "shutdown_requested.json").is_file()
    assert module.Server is Original


def test_legacy_shim_rejects_unapproved_script_before_import_or_listener(tmp_path):
    with pytest.raises(ValueError, match="two unchanged tracked"):
        launcher.legacy_child(tmp_path / "arbitrary.py", tmp_path, [])
