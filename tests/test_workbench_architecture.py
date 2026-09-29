"""M6 boundaries, optional dependencies and local-server configuration.

These checks complement the unchanged numerical architecture guards. Static
inspection covers ordinary imports; fresh subprocesses test actual import
isolation without uninstalling the optional UI or changing the environment.
"""

from __future__ import annotations

import ast
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import tomllib

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _imports(path):
    """Collect ordinary imports, including aliases and function-local imports."""
    relative = path.relative_to(ROOT).with_suffix("")
    package = ".".join(relative.parts[:-1])
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            name = node.module or ""
            if node.level:
                name = importlib.util.resolve_name("." * node.level + name, package)
            yield name
            yield from (f"{name}.{alias.name}" for alias in node.names)


def _child(source, *, cwd=ROOT):
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, "-B", "-X", "utf8", "-c", textwrap.dedent(source)],
        cwd=cwd, env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="strict", timeout=45,
    )


def test_ui_extra_does_not_expand_numerical_runtime_dependencies():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["dependencies"] == ["numpy>=1.26", "scipy>=1.11"]
    assert project["optional-dependencies"]["ui"] == [
        "streamlit==1.64.0", "pillow>=10.0", "matplotlib>=3.8",
    ]
    assert project["optional-dependencies"]["images"] == ["pillow>=10.0"]


def test_numerical_and_io_source_never_import_app_or_streamlit():
    for path in sorted((ROOT / "src" / "ohlab").rglob("*.py")):
        for name in _imports(path):
            assert name.split(".")[0] not in {"apps", "streamlit"}, (path, name)


@pytest.mark.parametrize("filename", ["workbench.py", "provenance.py"])
def test_controller_and_provenance_do_not_import_ui_or_plotting(filename):
    # Lazy Pillow encoding is app-layer I/O, not plotting. It is independently
    # blocked during the actual controller-import test below.
    forbidden = {"streamlit", "matplotlib", "plotly", "altair", "pydeck"}
    for name in _imports(ROOT / "apps" / filename):
        assert name.split(".")[0] not in forbidden, (filename, name)
        assert name != "apps.presentation" and not name.startswith("apps.presentation."), name
        assert name != "apps.streamlit_app" and not name.startswith("apps.streamlit_app."), name


def test_numerical_core_and_controller_import_with_ui_and_plotting_blocked():
    result = _child('''
        import importlib.abc
        import sys
        blocked = {"streamlit", "matplotlib", "PIL", "altair", "pydeck", "pandas", "pyarrow"}
        class BlockOptional(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split(".")[0] in blocked:
                    raise ModuleNotFoundError("blocked optional dependency: " + fullname, name=fullname)
                return None
        sys.meta_path.insert(0, BlockOptional())
        import ohlab
        import ohlab.targets
        import ohlab.algorithms
        import ohlab.metrics
        import ohlab.io.config
        import ohlab.io.artifacts
        import apps.workbench
        import apps.provenance
        assert not blocked.intersection(name.split(".")[0] for name in sys.modules)
        print("CORE_AND_CONTROLLER_IMPORTS_WITHOUT_UI_OK")
    ''')
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CORE_AND_CONTROLLER_IMPORTS_WITHOUT_UI_OK" in result.stdout


def test_missing_streamlit_gives_actionable_optional_dependency_guidance(tmp_path):
    # This fresh child blocks only Streamlit. A missing transitive dependency
    # must not be disguised as this intentionally absent optional dependency.
    source = '''
        import importlib.abc
        import runpy
        import sys
        class BlockStreamlit(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == "streamlit" or fullname.startswith("streamlit."):
                    raise ModuleNotFoundError("No module named 'streamlit'", name="streamlit")
                return None
        sys.meta_path.insert(0, BlockStreamlit())
        runpy.run_path(APP_PATH, run_name="__main__")
    '''.replace("APP_PATH", repr(str(ROOT / "apps" / "streamlit_app.py")))
    result = _child(source, cwd=tmp_path)
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "streamlit" in output.lower(), output
    assert "ui" in output.lower() and "README.md" in output, output
    assert "streamlit==1.64.0" in output, output
    assert "Traceback" not in output, output


@pytest.mark.parametrize(
    ("section", "name", "expected"),
    [
        ("server", "address", "127.0.0.1"),
        ("server", "port", 8501),
        ("server", "headless", True),
        ("server", "enableCORS", True),
        ("server", "enableXsrfProtection", True),
        ("server", "runOnSave", False),
        ("server", "fileWatcherType", "none"),
        ("server", "maxUploadSize", 8),
        ("browser", "gatherUsageStats", False),
        ("runner", "fastReruns", False),
    ],
)
def test_local_configuration_has_explicit_approved_boundaries(section, name, expected):
    config = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert config[section][name] == expected
    assert type(config[section][name]) is type(expected)


def test_side_effecting_app_operations_are_not_streamlit_cached():
    for filename in ("workbench.py", "streamlit_app.py"):
        tree = ast.parse((ROOT / "apps" / filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                spelling = ast.unparse(decorator)
                assert "cache_data" not in spelling and "cache_resource" not in spelling, (
                    filename, node.name, spelling,
                )
