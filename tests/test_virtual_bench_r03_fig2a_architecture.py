"""A's precise public boundary adds no experimental comparison permissions."""

import ast
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "virtual_bench"
MARKER = "R03_PUBLIC_BOUNDARY_DETECTED"
PUBLIC = {"IdealPolarizationSpec", "IdealPolarizationResult", "run_ideal_polarization"}


def assert_boundary(source, filename="r03_fig2a_adapter.py"):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            assert all(not item.name.startswith("ohlab") and item.name.split(".")[0] not in
                       {"importlib", "scipy", "matplotlib", "PIL", "streamlit"} for item in node.names), MARKER
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("ohlab"):
                assert filename == "r03_fig2a_adapter.py" and node.level == 0, MARKER
                assert node.module == "ohlab.optics.r03_fig2a", MARKER
                assert all(item.name in PUBLIC and item.asname in (None, item.name) for item in node.names), MARKER
            if node.module == "numpy":
                assert filename == "r03_fig2a_adapter.py", MARKER
                assert [(item.name, item.asname) for item in node.names] == [("__version__", "numpy_version")], MARKER
        if isinstance(node, ast.Name):
            assert node.id not in {"eval", "exec", "__import__", "import_module", "getattr", "setattr",
                "coherency_from_samples", "measure_coherency", "sample_source", "run_experiment",
                "propagate_angular_spectrum", "gerchberg_saxton"}, MARKER
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"fft", "fft2", "ifft", "ifft2", "cos", "sin", "exp", "sqrt",
                "standard_normal", "default_rng", "PCG64", "loadmat", "load", "save", "read_text", "open"}, MARKER


def test_only_new_adapter_can_call_exact_public_model_without_replacement_science():
    source = (BACKEND / "r03_fig2a_adapter.py").read_text(encoding="utf-8")
    assert_boundary(source)
    assert_boundary((BACKEND / "r03_fig2a_protocol.py").read_text(encoding="utf-8"), "r03_fig2a_protocol.py")
    calls = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == "run_ideal_polarization"]
    assert len(calls) == 1, "R03_ONE_REALIZATION_DETECTED"


@pytest.mark.parametrize("source", [
    "from ohlab.optics.r03_fig2a import *", "from ohlab.optics.r03_fig2a import _real",
    "from ohlab.optics.r03_fig2a import run_ideal_polarization as run",
    "from ohlab.optics.polarization_statistics import coherency_from_samples",
    "import ohlab.optics.r03_fig2a", "import importlib", "eval('1')", "getattr(x,'run')",
    "np.random.default_rng(1)", "math.exp(sigma)", "x.loadmat('a.mat')",
])
def test_guard_detects_private_alias_wildcard_dynamic_and_replacement_calculation(source):
    with pytest.raises(AssertionError, match=MARKER):
        assert_boundary(source)


@pytest.mark.parametrize("filename", ["server.py", "r03_fig2a_protocol.py", "unrelated.py"])
def test_new_exception_does_not_allow_science_in_server_protocol_or_unrelated_files(filename):
    with pytest.raises(AssertionError, match=MARKER):
        assert_boundary("from ohlab.optics.r03_fig2a import run_ideal_polarization", filename)


def test_new_modules_import_passively_without_server_ui_or_optional_graphics():
    source = textwrap.dedent('''
        import importlib.abc, sys, socket, threading
        class Blocker(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split('.')[0] in {'starlette','uvicorn','streamlit','PIL','matplotlib'}:
                    raise AssertionError('unexpected optional dependency: ' + fullname)
        sys.meta_path.insert(0, Blocker())
        def forbidden(*args, **kwargs): raise AssertionError('active import')
        socket.socket.bind = forbidden
        socket.socket.listen = forbidden
        threading.Thread.start = forbidden
        import apps.virtual_bench.r03_fig2a_adapter
        import apps.virtual_bench.r03_fig2a_protocol
        assert 'apps.virtual_bench.server' not in sys.modules
        print('Independent ideal model adapter/protocol import passively')
    ''')
    environment = os.environ.copy(); environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", source], cwd=ROOT,
                              env=environment, capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_old_closed_document_boundary_does_not_gain_new_runner_or_reference_access():
    from test_virtual_bench_document_architecture import assert_validation_boundary, MARKER as document_marker
    for source in ("from .r03_fig2a_adapter import simulate_submission",
                   "from .r03_fig2a_adapter import run_ideal_polarization", "x.submit(None)", "open('a.mat')"):
        with pytest.raises(AssertionError, match=document_marker):
            assert_validation_boundary(source)
    assert not (BACKEND / "r03_fig2a_reference.py").exists()
