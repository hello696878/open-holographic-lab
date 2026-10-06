"""V1 remains an optional presentation layer using the public unchanged V0 API."""

import ast
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import tomllib


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "virtual_bench"


def imports(path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level:
            yield node.module or ""


def test_backend_uses_public_optics_without_replacement_or_unrelated_science():
    allowed = {"ohlab.optics", "ohlab.optics.interference"}
    for path in BACKEND.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for name in imports(path):
            if name.startswith("ohlab"):
                assert name in allowed, (path, name)
            assert name.split(".")[0] not in {"streamlit", "matplotlib", "PIL", "scipy"}, (path, name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr not in {"fft", "fft2", "ifft2", "propagate_angular_spectrum", "gerchberg_saxton"}, (path, node.attr)
    tree = ast.parse((BACKEND / "adapter.py").read_text(encoding="utf-8"))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and
             isinstance(node.func, ast.Name) and node.func.id == "run_experiment"]
    assert len(calls) == 1
    assert any(keyword.arg == "record_fields" and isinstance(keyword.value, ast.Tuple)
                and not keyword.value.elts for keyword in calls[0].keywords)


def test_two_path_adapter_uses_only_public_source_sampler_and_runner():
    tree = ast.parse((BACKEND / "two_path_adapter.py").read_text(encoding="utf-8"))
    forbidden = {"run_experiment", "mix_balanced", "apply_uniform_phase", "_norm", "_geometry"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in forbidden
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("ohlab"):
            assert all(not alias.name.startswith("_") for alias in node.names)
    assert any(isinstance(node, ast.ImportFrom) and node.module == "ohlab.optics.interference"
               and any(alias.name == "run_two_arm" for alias in node.names) for node in ast.walk(tree))


def test_adapter_import_does_not_need_server_browser_or_existing_optional_ui():
    source = textwrap.dedent('''
        import importlib.abc
        import sys
        class Blocker(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split('.')[0] in {'starlette','uvicorn','streamlit','PIL','matplotlib'}:
                    raise AssertionError('unexpected optional import: ' + fullname)
                return None
        sys.meta_path.insert(0, Blocker())
        import apps.virtual_bench.adapter
        import apps.virtual_bench.protocol
        assert 'apps.virtual_bench.server' not in sys.modules
        print('V1 adapter imports independently of optional presentation/server packages')
    ''')
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", source], cwd=ROOT,
                            env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


def test_server_import_has_no_listeners_or_worker_threads():
    source = textwrap.dedent('''
        import socket
        import threading
        def forbidden(*args, **kwargs):
            raise AssertionError('import started a listener or thread')
        socket.socket.bind = forbidden
        socket.socket.listen = forbidden
        threading.Thread.start = forbidden
        import apps.virtual_bench.server
        print('V1 server import is passive')
    ''')
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", source], cwd=ROOT,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


def test_launch_configuration_is_single_loopback_existing_runtime():
    tree = ast.parse((BACKEND / "server.py").read_text(encoding="utf-8"))
    configs = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and
               isinstance(node.func, ast.Attribute) and node.func.attr == "Config"]
    assert len(configs) == 1
    keywords = {item.arg: item.value for item in configs[0].keywords}
    assert isinstance(keywords["host"], ast.Name) and keywords["host"].id == "HOST"
    assert isinstance(keywords["port"], ast.Name) and keywords["port"].id == "PORT"
    expected = {"workers": 1, "reload": False, "proxy_headers": False, "loop": "asyncio",
                "http": "h11", "ws": "none", "limit_concurrency": 16, "timeout_keep_alive": 2}
    assert {key: ast.literal_eval(keywords[key]) for key in expected} == expected
    constants = {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body
                 if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                 and node.targets[0].id in {"HOST", "PORT"}}
    assert constants == {"HOST": "127.0.0.1", "PORT": 8510}


def test_bench_extra_records_installed_server_without_core_or_ui_dependency_changes():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["dependencies"] == ["numpy>=1.26", "scipy>=1.11"]
    assert project["optional-dependencies"]["ui"] == ["streamlit==1.64.0", "pillow>=10.0", "matplotlib>=3.8"]
    assert project["optional-dependencies"]["bench"] == ["starlette==1.7.0", "uvicorn==0.54.0"]
