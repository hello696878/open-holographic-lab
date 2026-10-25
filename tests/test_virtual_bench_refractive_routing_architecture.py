"""Exact additive W3 boundary, passive imports and the eleventh gate seam."""
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
BACKEND = ROOT / "apps/virtual_bench"
MARKER = "W3_EXACT_PUBLIC_BOUNDARY_DETECTED"
PUBLIC = {"RefractiveScene", "RefractiveTraceResult", "NumericalAmbiguityError",
          "UnsupportedNumericalInputError", "MediumStateAmbiguityError", "trace_routes", "validate_scene"}


def assert_boundary(source, filename):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            assert all(not alias.name.startswith("ohlab") and alias.name.split(".")[0] not in {"importlib", "scipy", "matplotlib", "PIL", "streamlit"} for alias in node.names), MARKER
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("ohlab"):
            assert filename == "refractive_routing_adapter.py" and node.module == "ohlab.optics.refractive_routing" and node.level == 0, MARKER
            assert all(alias.name in PUBLIC and alias.asname in (None, alias.name) for alias in node.names), MARKER
        if isinstance(node, ast.Name):
            assert node.id not in {"eval", "exec", "__import__", "import_module", "getattr", "setattr", "run_experiment", "sample_source", "apply_component", "propagate_angular_spectrum"}, MARKER
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"fft", "fft2", "ifft", "ifft2", "sin", "cos", "tan", "asin", "acos", "intersect", "reflect", "run_experiment", "propagate_angular_spectrum"}, MARKER


def test_exact_public_adapter_one_runner_and_protocol_without_numerical_import():
    for filename in ("refractive_routing_adapter.py", "refractive_routing_protocol.py"):
        source = (BACKEND / filename).read_text(encoding="utf-8")
        assert_boundary(source, filename)
        calls = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "trace_routes"]
        assert len(calls) == (1 if filename.endswith("adapter.py") else 0)


@pytest.mark.parametrize("source,filename", [
    ("from ohlab.optics.refractive_routing import *", "refractive_routing_adapter.py"),
    ("from ohlab.optics.refractive_routing import _snell", "refractive_routing_adapter.py"),
    ("from ohlab.optics.refractive_routing import trace_routes as hidden", "refractive_routing_adapter.py"),
    ("from ohlab.optics.geometric_routing import trace_routes", "refractive_routing_adapter.py"),
    ("from ohlab.optics.refractive_routing import trace_routes", "refractive_routing_protocol.py"),
    ("from ohlab.optics.refractive_routing import RefractiveScene", "server.py"),
    ("import ohlab.optics.refractive_routing", "refractive_routing_adapter.py"),
    ("import importlib", "refractive_routing_protocol.py"),
    ("math.cos(1)", "refractive_routing_adapter.py"),
    ("x.reflect(d,n)", "refractive_routing_protocol.py"),
    ("getattr(x,'trace_routes')", "refractive_routing_adapter.py"),
])
def test_boundary_controls_reject_wrong_owner_private_formula_and_dynamic_alias(source, filename):
    with pytest.raises(AssertionError, match=MARKER):
        assert_boundary(source, filename)


def test_global_guard_permission_is_only_the_exact_new_adapter(monkeypatch, tmp_path):
    target = tmp_path / "backend"
    target.mkdir()
    shutil.copyfile(BACKEND / "adapter.py", target / "adapter.py")
    monkeypatch.setattr(legacy, "BACKEND", target)
    path = target / "refractive_routing_adapter.py"
    path.write_text("from ohlab.optics.refractive_routing import RefractiveScene\n", encoding="utf-8")
    legacy.test_backend_uses_public_optics_without_replacement_or_unrelated_science()
    for filename in ("refractive_routing_protocol.py", "server.py", "unrelated.py"):
        other = target / filename
        other.write_text("from ohlab.optics.refractive_routing import RefractiveScene\n", encoding="utf-8")
        with pytest.raises(AssertionError):
            legacy.test_backend_uses_public_optics_without_replacement_or_unrelated_science()
        other.unlink()


def test_new_backend_and_acceptance_imports_are_passive():
    source = textwrap.dedent("""
        import importlib.abc,runpy,socket,sys,threading
        class Block(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split('.')[0] in {'starlette','uvicorn','streamlit','PIL','matplotlib'}:
                    raise AssertionError('unexpected optional '+fullname)
        sys.meta_path.insert(0, Block())
        def forbidden(*args,**kwargs):raise AssertionError('active import')
        socket.socket.bind=forbidden
        socket.socket.listen=forbidden
        threading.Thread.start=forbidden
        import apps.virtual_bench.refractive_routing_adapter
        import apps.virtual_bench.refractive_routing_protocol
        assert 'apps.virtual_bench.server' not in sys.modules
        runpy.run_path('scripts/w3_acceptance.py',run_name='w3_passive_test')
        runpy.run_path('scripts/w3_controlled_acceptance_server.py',run_name='w3_child_passive_test')
        print('W3_PASSIVE_IMPORT_OK')
    """)
    child = os.environ.copy()
    child["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", source], cwd=ROOT, env=child, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "W3_PASSIVE_IMPORT_OK" in result.stdout


def test_w3_child_uses_one_existing_factory_all_eleven_workers_and_no_new_gate():
    tree = ast.parse((ROOT / "scripts/w3_controlled_acceptance_server.py").read_text(encoding="utf-8"))
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"Route", "ComputationGate", "ThreadPoolExecutor"} for node in ast.walk(tree))
    factories = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "original_factory"]
    assert len(factories) == 1
    assert {keyword.arg for keyword in factories[0].keywords} == {"assets_dir", "worker", "two_path_worker", "sweep_worker", "polarization_worker", "polarization_sweep_worker", "polarized_two_path_worker", "polarized_two_path_sweep_worker", "r03_ideal_worker", "wave_field_worker", "geometric_routing_worker", "refractive_routing_worker"}
    server = ast.parse((BACKEND / "server.py").read_text(encoding="utf-8"))
    gates = [node for node in ast.walk(server) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "ComputationGate"]
    assert len(gates) == 1
