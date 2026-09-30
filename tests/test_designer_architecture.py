"""M7 import boundaries; no optional dependency or old contract expansion."""

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
OPTIONAL = {"streamlit", "matplotlib", "PIL", "altair", "pydeck", "pandas", "pyarrow", "plotly"}


def imports(relative):
    path = ROOT / relative
    package_parts = Path(relative).with_suffix("").parts[:-1]
    if package_parts[0] == "src":
        package_parts = package_parts[1:]
    package = ".".join(package_parts)
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            name = node.module or ""
            if node.level:
                name = importlib.util.resolve_name("." * node.level + name, package)
            yield name
            yield from (name + "." + alias.name for alias in node.names)


@pytest.mark.parametrize("relative", [
    "src/ohlab/target_design.py", "src/ohlab/io/designs.py", "apps/designer.py",
])
def test_design_model_io_and_editor_import_no_ui_image_or_plotting_dependency(relative):
    for name in imports(relative):
        assert name.split(".")[0] not in OPTIONAL, (relative, name)
        assert not name.startswith(("apps.streamlit_app", "apps.presentation")), (relative, name)


@pytest.mark.parametrize("relative", [
    "src/ohlab/target_design.py", "src/ohlab/io/designs.py", "apps/designer.py",
])
def test_design_preparation_does_not_import_solver_metrics_or_bundle_writer(relative):
    forbidden = ("ohlab.algorithms", "ohlab.propagation", "ohlab.metrics", "ohlab.io.artifacts")
    for name in imports(relative):
        assert not name.startswith(forbidden), (relative, name)
        if relative == "src/ohlab/target_design.py":
            assert not name.startswith(("ohlab.io", "apps")), (relative, name)


def test_raster_and_json_work_with_optional_dependencies_blocked_in_fresh_process():
    source = '''
        import importlib.abc
        import sys
        blocked = {"streamlit", "matplotlib", "PIL", "altair", "pydeck", "pandas", "pyarrow", "plotly"}
        class BlockOptional(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split(".")[0] in blocked:
                    raise ModuleNotFoundError("blocked optional dependency: " + fullname, name=fullname)
                return None
        sys.meta_path.insert(0, BlockOptional())
        import numpy as np
        from ohlab.target_design import TargetDesign2D, rasterize_target_design
        from ohlab.io.designs import design_to_json, design_from_json
        from apps import designer, workbench
        design = TargetDesign2D({
            "schema_version": 1,
            "rasterizer_version": "center_sample_overwrite_v1",
            "coordinate_system": "centered_pixels_y_down_v1",
            "canvas": {"ny": 2, "nx": 3},
            "background_intensity": 0.3,
            "objects": [],
        })
        encoded = design_to_json(design)
        loaded = design_from_json(encoded)
        actual = rasterize_target_design(loaded)
        assert actual.dtype == np.dtype(np.float64) and actual.shape == (2, 3)
        assert actual.tobytes() == np.full((2, 3), 0.3, dtype=np.float64).tobytes()
        editor = designer.EditorState(design=loaded)
        assert design_to_json(editor.design) == encoded
        assert not blocked.intersection(name.split(".")[0] for name in sys.modules)
        print("DESIGNER_WITHOUT_OPTIONAL_UI_IMAGE_PLOTTING_OK")
    '''
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONUTF8"] = "1"
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", textwrap.dedent(source)],
                            cwd=ROOT, env=environment, capture_output=True, text=True,
                            encoding="utf-8", errors="strict", timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "DESIGNER_WITHOUT_OPTIONAL_UI_IMAGE_PLOTTING_OK" in result.stdout


def test_m7_adds_no_runtime_or_ui_dependencies_or_root_exports():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["dependencies"] == ["numpy>=1.26", "scipy>=1.11"]
    assert project["optional-dependencies"]["ui"] == ["streamlit==1.64.0", "pillow>=10.0", "matplotlib>=3.8"]
    import ohlab
    assert not hasattr(ohlab, "TargetDesign2D")
    assert not hasattr(ohlab, "rasterize_target_design")


@pytest.mark.parametrize("filename", ["designer.py", "workbench.py", "streamlit_app.py"])
def test_designer_side_effects_are_not_streamlit_cached(filename):
    tree = ast.parse((ROOT / "apps" / filename).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                spelling = ast.unparse(decorator)
                assert "cache_data" not in spelling and "cache_resource" not in spelling, (filename, node.name)
