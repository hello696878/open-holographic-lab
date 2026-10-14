"""Document handling stays a passive app-layer validation boundary."""

import ast
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "virtual_bench"
MARKER = "DOCUMENT_VALIDATION_BOUNDARY_DETECTED"


def assert_validation_boundary(source):
    allowed_relative = {
        "adapter": {"strict_json_loads", "validate_experiment"},
        "two_path_adapter": {"validate_experiment"},
        "polarization_adapter": {"PolarizationExperiment"},
        "polarized_two_path_adapter": {"PolarizedTwoPathExperiment"},
        "protocol": {"experiment_digest"},
        "two_path_protocol": {"experiment_digest"},
        "polarization_protocol": {"experiment_digest"},
        "polarized_two_path_protocol": {"experiment_digest"}}
    allowed_absolute = {"__future__": {"annotations"}, "dataclasses": {"dataclass"},
                        "types": {"MappingProxyType"}}
    forbidden = {"sample_source", "run_experiment", "run_two_arm", "run_polarized_two_arm", "mix_balanced_jones", "apply_linear_polarizer",
                 "apply_linear_retarder", "transmission_ratio", "from_scalar", "simulate_submission",
                 "sweep_submission", "fft", "fft2", "ifft2", "propagate_angular_spectrum",
                 "gerchberg_saxton", "open", "write_text", "write_bytes", "read_text", "read_bytes",
                 "eval", "exec", "__import__", "import_module", "getattr", "setattr", "submit",
                 "acquire", "release", "shutdown", "cos", "sin", "exp", "sqrt"}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            assert all(alias.name in {"json", "math"} for alias in node.names), MARKER
        if isinstance(node, ast.ImportFrom):
            allowed = allowed_relative if node.level == 1 else allowed_absolute if node.level == 0 else {}
            assert node.module in allowed and all(alias.name in allowed[node.module] for alias in node.names), MARKER
        if isinstance(node, ast.Name): assert node.id not in forbidden, MARKER
        if isinstance(node, ast.Attribute): assert node.attr not in forbidden, MARKER


def test_document_module_validation_only_imports_calls_and_no_optical_formulas():
    source = (BACKEND / "experiment_documents.py").read_text(encoding="utf-8")
    assert_validation_boundary(source)


@pytest.mark.parametrize("source", [
    "from .adapter import run_experiment\n",
    "from .adapter import *\n", "from .polarization_adapter import _incident\n",
    "from . import adapter\n", "from ohlab.optics import SequentialExperiment\n",
    "import numpy\n", "import importlib\n", "import pathlib\n", "import socket\n",
    "__import__('ohlab')\n", "eval('1')\n", "getattr(x,'run_experiment')()\n",
    "x.from_scalar(None)\n", "x.submit(None)\n", "x.release()\n", "open('upload.json','w')\n",
    "import math\nx=math.cos(0)\n"])
def test_guard_detects_private_dynamic_numerical_gate_disk_bypass(source):
    with pytest.raises(AssertionError, match=MARKER): assert_validation_boundary(source)


def test_document_handler_does_not_reference_gate_or_compute_dispatch():
    tree = ast.parse((BACKEND / "server.py").read_text(encoding="utf-8"))
    handler = next(node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef) and node.name == "document_validate")
    for node in ast.walk(handler):
        if isinstance(node, ast.Name): assert node.id not in {"gate", "dispatch", "_worker_response"}, MARKER
        if isinstance(node, ast.Attribute): assert node.attr not in {"submit", "_completed", "wait_idle", "shutdown"}, MARKER
    readers = [node for node in ast.walk(handler) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_read_json"]
    assert len(readers) == 1 and any(keyword.arg == "parser" for keyword in readers[0].keywords), MARKER


def test_document_import_independent_of_optional_ui_server_listeners_and_disk():
    source = textwrap.dedent('''
        import importlib.abc, sys, socket, threading
        class Blocker(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split('.')[0] in {'starlette','uvicorn','streamlit','PIL','matplotlib'}:
                    raise AssertionError('unexpected optional import: ' + fullname)
        sys.meta_path.insert(0, Blocker())
        def forbidden(*args, **kwargs): raise AssertionError('active document import')
        socket.socket.bind = forbidden
        socket.socket.listen = forbidden
        threading.Thread.start = forbidden
        import apps.virtual_bench.experiment_documents
        assert 'apps.virtual_bench.server' not in sys.modules
        print('V2e document imports are passive and independent')
    ''')
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", source], cwd=ROOT,
                            env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
