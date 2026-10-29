"""No-browser detection of W4 evidence ownership and frozen-ID mistakes."""
from copy import deepcopy
import ast
import importlib.util
from pathlib import Path

import pytest

from scripts import w2_acceptance as shared
from scripts import w4_acceptance as launcher


def selection():
    return [{"id": "actual-discovered-id", "file": "fresnel_routing.browser.spec.ts",
             "title": "W4-B01 finite parallel slab has two certified interfaces and parallel displaced emergence"}]


def test_selection_requires_actual_id_and_exact_w4_owner_before_launch(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(launcher, "execute_existing", lambda *args, **kwargs: calls.append((args, kwargs)) or {"passed": True})
    selected = selection()
    assert launcher.execute(tmp_path / "run", ["tests/fresnel_routing.browser.spec.ts"], tmp_path / "assets", inputs={}, selected=selected)["passed"]
    assert calls[0][1]["expected_skips"] == 0 and calls[0][1]["selected"] == selected
    for defect in ("missing_id", "other_file", "other_title", "duplicate", "empty"):
        wrong = deepcopy(selected)
        if defect == "missing_id": wrong[0].pop("id")
        elif defect == "other_file": wrong[0]["file"] = "other.ts"
        elif defect == "other_title": wrong[0]["title"] = "W2 prior stage"
        elif defect == "duplicate": wrong *= 2
        else: wrong = []
        with pytest.raises(ValueError):
            launcher.execute(tmp_path / "run", ["tests/fresnel_routing.browser.spec.ts"], tmp_path / "assets", inputs={}, selected=wrong)
    assert len(calls) == 1


def test_w4_namespaces_are_child_only_and_unrelated_proxy_is_retained(monkeypatch):
    monkeypatch.setenv("W4_EVIDENCE_DIR", "stale")
    monkeypatch.setenv("W4_CONTROL_DIR", "foreign")
    monkeypatch.setenv("HTTP_PROXY", "preserve-proxy")
    child = shared.child_environment({"W4_EVIDENCE_DIR": "fresh"})
    assert child["W4_EVIDENCE_DIR"] == "fresh" and "W4_CONTROL_DIR" not in child
    assert child["HTTP_PROXY"] == "preserve-proxy"
    assert shared.os.environ["W4_EVIDENCE_DIR"] == "stale" and shared.os.environ["W4_CONTROL_DIR"] == "foreign"


def test_w4_output_scan_finds_all_custom_evidence_and_figure_roots(tmp_path):
    path = tmp_path / "spec.ts"
    path.write_text("process.env.W4_EVIDENCE_DIR;process.env.W4_FIGURE_DIR;process.env.W4_CONTROL_DIR;process.env.W2_EVIDENCE_DIR", encoding="utf-8")
    scan = shared.scan_environment([path])
    assert scan["outputs"] == ["W2_EVIDENCE_DIR", "W4_EVIDENCE_DIR", "W4_FIGURE_DIR"]
    assert "W4_CONTROL_DIR" in scan["all"]


def test_fresh_outputs_reject_aliases_ancestors_existing_and_escape(tmp_path):
    owner = tmp_path / "runs/w4/one"
    owner.mkdir(parents=True)
    retained = owner / "retained.json"
    retained.write_bytes(b"unchanged original")
    for destination in (owner / "RUNNER", owner / "runner/child", owner, tmp_path / "escape", retained):
        with pytest.raises(ValueError):
            shared.validate_outputs(owner, {"runner": owner / "runner", "custom": destination}, workspace=tmp_path)
    assert retained.read_bytes() == b"unchanged original"
    assert not (owner / "runner").exists()


def test_new_control_child_path_rejects_history_and_parent_without_import_side_effect(tmp_path):
    path = Path(__file__).resolve().parents[1] / "scripts/w4_controlled_acceptance_server.py"
    spec = importlib.util.spec_from_file_location("w4_owned_control_test", path)
    child = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(child)
    owner = tmp_path / "runs"
    owner.mkdir()
    fresh = owner / "fresh"
    assert child._owned_path(fresh, owner, absent=True) == fresh
    for invalid in (owner, owner / ".." / "escape", Path("relative")):
        with pytest.raises(ValueError): child._owned_path(invalid, owner, absent=True)
    child._separate_paths(owner/"service",owner/"assets")
    for left,right in ((owner/"ASSETS",owner/"assets"),(owner/"assets/child",owner/"assets"),(owner/"service",owner/"service/child")):
        with pytest.raises(ValueError):child._separate_paths(left,right)
    fresh.mkdir()
    marker = fresh / "preserved"
    marker.write_bytes(b"prior evidence")
    with pytest.raises(ValueError): child._owned_path(fresh, owner, absent=True)
    assert marker.read_bytes() == b"prior evidence"


def test_w4_exact_controlled_factory_uses_all_twelve_workers_without_new_gate():
    path=Path(__file__).resolve().parents[1]/"scripts/w4_controlled_acceptance_server.py"
    tree=ast.parse(path.read_text(encoding="utf-8"))
    calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call)]
    assert not any(isinstance(node.func,ast.Name) and node.func.id in {"Route","ComputationGate","ThreadPoolExecutor"} for node in calls)
    factories=[node for node in calls if isinstance(node.func,ast.Name) and node.func.id=="original_factory"]
    assert len(factories)==1
    assert {item.arg for item in factories[0].keywords}=={"assets_dir","worker","two_path_worker","sweep_worker",
        "polarization_worker","polarization_sweep_worker","polarized_two_path_worker","polarized_two_path_sweep_worker",
        "r03_ideal_worker","wave_field_worker","geometric_routing_worker","refractive_routing_worker","fresnel_routing_worker"}


def test_shared_launcher_additions_are_exact_child_prefix_and_source_hash_inventory():
    assert "W4_" in shared.PREFIXES
    source=Path(shared.__file__).read_text(encoding="utf-8")
    assert '"w4_controlled_acceptance_server.py"' in source
