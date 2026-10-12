"""Adapter-specific public imports and detecting architecture failure controls."""

import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap

import pytest

import test_virtual_bench_architecture as legacy

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "virtual_bench"


def assert_no_private_scientific_imports(source):
    """Reject private/wildcard scientific symbols in every ordinary backend file."""
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("ohlab"):
            assert all(not alias.name.startswith("_") and alias.name != "*" for alias in node.names), "PRIVATE_IMPORT_ELSEWHERE_DETECTED"


def test_all_backend_files_import_only_public_scientific_symbols():
    for path in BACKEND.glob("*.py"):
        assert_no_private_scientific_imports(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["server.py", "ordinary_module.py"])
@pytest.mark.parametrize("symbol", ["_geometry", "*"])
def test_global_private_symbol_guard_detects_ordinary_module_fixture(tmp_path, name, symbol):
    fixture = tmp_path / name
    fixture.write_text(f"from ohlab.optics import {symbol}\n", encoding="utf-8")
    try:
        assert_no_private_scientific_imports(fixture.read_text(encoding="utf-8"))
    except AssertionError as exc:
        assert "PRIVATE_IMPORT_ELSEWHERE_DETECTED" in str(exc)
    else:
        pytest.fail("PRIVATE_IMPORT_ELSEWHERE_DETECTED: ordinary-module fixture escaped the guard")


def assert_adapter_public_only(source):
    tree = ast.parse(source)
    allowed_imports = {"ohlab.optics": {"SequentialExperiment", "sample_source"},
        "ohlab.optics.polarization": {"JonesField", "apply_linear_polarizer", "apply_linear_retarder", "transmission_ratio"}}
    forbidden = {"fft", "fft2", "ifft2", "propagate_angular_spectrum", "gerchberg_saxton",
                 "run_experiment", "run_two_arm", "__import__", "eval", "exec", "import_module"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("ohlab"):
            assert not node.level and node.module in allowed_imports, "PRIVATE_IMPORT_DETECTED"
            assert all(alias.name in allowed_imports[node.module] for alias in node.names), "PRIVATE_IMPORT_DETECTED"
        if isinstance(node, ast.Import):
            assert all(not alias.name.startswith("ohlab") and alias.name != "importlib" for alias in node.names), "PRIVATE_IMPORT_DETECTED"
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            assert name not in forbidden, "PRIVATE_IMPORT_DETECTED"
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden | {"_geometry", "_diagnostics", "_from_data", "_norm"}, "PRIVATE_IMPORT_DETECTED"


def test_polarization_adapter_imports_public_operations_and_duplicates_no_solver():
    source = (BACKEND / "polarization_adapter.py").read_text(encoding="utf-8")
    assert_adapter_public_only(source)
    tree = ast.parse(source)
    assert any(isinstance(node, ast.ImportFrom) and node.module == "ohlab.optics.polarization" for node in ast.walk(tree))
    assert "np.cos" not in source and "np.sin" not in source and "np.exp" not in source
    assert "math.cos(" not in source and "math.sin(" not in source and "math.exp(" not in source


def test_protocol_has_no_direct_or_relative_scientific_dependencies():
    tree = ast.parse((BACKEND / "polarization_protocol.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not node.level and not (node.module or "").startswith("ohlab"), "PROTOCOL_SCIENCE_IMPORT_DETECTED"
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] not in {"ohlab", "scipy", "PIL", "matplotlib", "streamlit"}
                       for alias in node.names), "PROTOCOL_SCIENCE_IMPORT_DETECTED"


def copied_backend(tmp_path, monkeypatch):
    target = tmp_path / "backend"
    target.mkdir()
    shutil.copyfile(BACKEND / "adapter.py", target / "adapter.py")
    monkeypatch.setattr(legacy, "BACKEND", target)
    return target


def test_existing_guard_permits_only_intended_polarization_adapter_import(tmp_path, monkeypatch):
    target = copied_backend(tmp_path, monkeypatch)
    (target / "polarization_adapter.py").write_text("from ohlab.optics.polarization import JonesField\n", encoding="utf-8")
    legacy.test_backend_uses_public_optics_without_replacement_or_unrelated_science()


@pytest.mark.parametrize("name,source", [
    ("server.py", "from ohlab.optics.polarization import JonesField\n"),
    ("polarization_protocol.py", "from ohlab.optics.polarization import JonesField\n"),
    ("polarization_adapter.py", "from ohlab.optics.propagation import propagate_angular_spectrum\n"),
    ("unrelated.py", "import scipy\n"),
    ("unrelated.py", "from ohlab.optics import SequentialExperiment\nx.fft2()\n"),
])
def test_guard_rejects_broadened_dependency_elsewhere(tmp_path, monkeypatch, name, source):
    target = copied_backend(tmp_path, monkeypatch)
    (target / name).write_text(source, encoding="utf-8")
    try:
        legacy.test_backend_uses_public_optics_without_replacement_or_unrelated_science()
    except AssertionError:
        pass
    else:
        pytest.fail("ARCHITECTURE_ALLOWLIST_DETECTED")


@pytest.mark.parametrize("source", [
    "from ohlab.optics.polarization import _geometry\n",
    "from ohlab.optics import run_experiment\n",
    "import importlib\nx=importlib.import_module('ohlab.optics')\n",
    "__import__('ohlab.optics')\n",
    "x._diagnostics()\n",
])
def test_private_solver_or_dynamic_bypass_fails(source):
    with pytest.raises(AssertionError, match="PRIVATE_IMPORT_DETECTED"):
        assert_adapter_public_only(source)


def test_adapter_protocol_import_independent_of_server_optional_ui_and_listeners():
    source = textwrap.dedent('''
        import importlib.abc, sys, socket, threading
        class Blocker(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split('.')[0] in {'starlette','uvicorn','streamlit','PIL','matplotlib'}:
                    raise AssertionError('unexpected optional import: ' + fullname)
        sys.meta_path.insert(0, Blocker())
        def forbidden(*args, **kwargs): raise AssertionError('active import')
        socket.socket.bind = forbidden
        threading.Thread.start = forbidden
        import apps.virtual_bench.polarization_adapter
        import apps.virtual_bench.polarization_protocol
        assert 'apps.virtual_bench.server' not in sys.modules
        print('V2d imports are passive and independent')
    ''')
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", source], cwd=ROOT,
                            env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
