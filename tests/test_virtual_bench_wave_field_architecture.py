"""W1 adapter calls one public wrapper; the transport never calculates optics."""

import ast
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps/virtual_bench"
MARKER = "W1_PUBLIC_BOUNDARY_DETECTED"
ALLOWED = {
    "wave_field_adapter.py": {"sample_wave_field", "validate_sampling"},
    "wave_field_protocol.py": {"WaveFieldResult", "section_plan"},
}


def assert_boundary(source, filename):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            assert all(not item.name.startswith("ohlab") and item.name.split(".")[0] not in
                       {"importlib", "scipy", "matplotlib", "PIL", "streamlit"} for item in node.names), MARKER
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("ohlab"):
            if node.module == "ohlab.optics":
                assert filename == "wave_field_adapter.py" and all(item.name == "SequentialExperiment" for item in node.names), MARKER
            else:
                assert node.module == "ohlab.optics.wave_field" and node.level == 0, MARKER
                assert filename in ALLOWED and all(item.name in ALLOWED[filename] and item.asname in
                    (None, item.name) for item in node.names), MARKER
        if isinstance(node, ast.Name):
            assert node.id not in {"eval", "exec", "__import__", "import_module", "getattr", "setattr",
                "run_experiment", "sample_source", "apply_component", "propagate_angular_spectrum"}, MARKER
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"fft", "fft2", "ifft", "ifft2", "exp", "sin", "cos", "sqrt",
                                    "default_rng", "standard_normal", "load", "save"}, MARKER


def test_only_approved_new_files_use_public_w1_integration_and_one_sampler_call():
    for filename in ALLOWED:
        source = (BACKEND / filename).read_text(encoding="utf-8")
        assert_boundary(source, filename)
        calls = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == "sample_wave_field"]
        assert len(calls) == (1 if filename == "wave_field_adapter.py" else 0)


@pytest.mark.parametrize("source,filename", [
    ("from ohlab.optics.wave_field import *", "wave_field_adapter.py"),
    ("from ohlab.optics.wave_field import _supported", "wave_field_adapter.py"),
    ("from ohlab.optics.wave_field import sample_wave_field as run", "wave_field_adapter.py"),
    ("from ohlab.optics.wave_field import sample_wave_field", "wave_field_protocol.py"),
    ("from ohlab.optics.wave_field import section_plan", "server.py"),
    ("from ohlab.optics import run_experiment", "wave_field_adapter.py"),
    ("import ohlab.optics.wave_field", "wave_field_adapter.py"),
    ("import importlib", "wave_field_adapter.py"),
    ("np.fft.fft2(field)", "wave_field_adapter.py"),
    ("np.exp(phase)", "wave_field_adapter.py"),
    ("getattr(model, 'sample_wave_field')", "wave_field_adapter.py"),
])
def test_architecture_guard_detects_private_dynamic_formula_and_unapproved_file_bypasses(source, filename):
    with pytest.raises(AssertionError, match=MARKER):
        assert_boundary(source, filename)


def test_existing_global_guard_exception_is_exactly_two_named_new_modules():
    source = (ROOT / "tests/test_virtual_bench_architecture.py").read_text(encoding="utf-8")
    assert '{"wave_field_adapter.py", "wave_field_protocol.py"}' in source
    assert '{"ohlab.optics.wave_field"}' in source
    assert 'node.attr not in {"fft", "fft2", "ifft2", "propagate_angular_spectrum", "gerchberg_saxton"}' in source


def test_new_modules_import_passively_without_server_ui_or_optional_graphics():
    source = textwrap.dedent('''
        import importlib.abc, socket, sys, threading
        class Blocker(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split('.')[0] in {'starlette','uvicorn','streamlit','PIL','matplotlib'}:
                    raise AssertionError('unexpected optional dependency: ' + fullname)
        sys.meta_path.insert(0, Blocker())
        def forbidden(*args, **kwargs): raise AssertionError('active import')
        socket.socket.bind = forbidden
        socket.socket.listen = forbidden
        threading.Thread.start = forbidden
        import apps.virtual_bench.wave_field_adapter
        import apps.virtual_bench.wave_field_protocol
        assert 'apps.virtual_bench.server' not in sys.modules
        print('W1 public adapter and transport import passively')
    ''')
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", source], cwd=ROOT,
                               env=environment, capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_controlled_child_is_passive_and_reuses_production_loopback_gate_without_fault_routes():
    path = ROOT / "scripts/w1_controlled_acceptance_server.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and
                   node.func.id in {"Route", "ComputationGate", "ThreadPoolExecutor"}
                   for node in ast.walk(tree))
    factories = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and
                 isinstance(node.func, ast.Name) and node.func.id == "original_factory"]
    assert len(factories) == 1
    assert {keyword.arg for keyword in factories[0].keywords} == {
        "assets_dir", "worker", "two_path_worker", "sweep_worker", "polarization_worker",
        "polarization_sweep_worker", "polarized_two_path_worker", "polarized_two_path_sweep_worker",
        "r03_ideal_worker", "wave_field_worker"}
    source = textwrap.dedent('''
        import runpy, socket, threading
        def forbidden(*args, **kwargs): raise AssertionError('active controlled import')
        socket.socket.bind = forbidden
        socket.socket.listen = forbidden
        threading.Thread.start = forbidden
        runpy.run_path('scripts/w1_controlled_acceptance_server.py', run_name='w1_passive_test')
        print('W1 controlled child import is passive')
    ''')
    completed = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", source], cwd=ROOT,
                               capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0, completed.stdout + completed.stderr
