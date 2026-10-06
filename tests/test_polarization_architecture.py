"""V2c boundary checks without modifying established architecture guards."""

import ast
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_polarization_import_and_actions_without_optional_ui_plotting_or_io():
    source = r'''
import importlib.abc
import sys
blocked = {'matplotlib', 'PIL', 'streamlit', 'plotly', 'pandas', 'pyarrow', 'altair', 'pydeck', 'starlette', 'uvicorn'}
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in blocked or fullname.startswith(('ohlab.io', 'apps.')):
            raise ModuleNotFoundError('blocked ' + fullname)
sys.meta_path.insert(0, Block())
import numpy as np
import ohlab
import ohlab.optics
from ohlab import ComplexField, SamplingGrid
from ohlab.optics.polarization import JonesField, apply_linear_polarizer, apply_linear_retarder, transmission_ratio
grid = SamplingGrid(ny=2, nx=3, dy=5e-6, dx=4e-6)
scalar = ComplexField(data=np.ones(grid.shape, dtype=np.complex128), grid=grid, wavelength_m=633e-9)
field = JonesField.from_scalar(scalar, x_coefficient=1, y_coefficient=1j)
projected = apply_linear_polarizer(field, axis_angle_rad=.37)
retarded = apply_linear_retarder(projected, axis_angle_rad=-.61, retardance_rad=.83)
assert transmission_ratio(field, retarded) > 0
assert not blocked.intersection(name.split('.')[0] for name in sys.modules)
assert not any(name.startswith(('ohlab.io', 'ohlab.algorithms', 'ohlab.metrics', 'apps.')) for name in sys.modules)
for name in ('JonesField', 'apply_linear_polarizer', 'apply_linear_retarder', 'transmission_ratio'):
    assert not hasattr(ohlab, name)
    assert not hasattr(ohlab.optics, name)
print('V2C_CORE_WITHOUT_OPTIONAL_OR_IO_OK')
'''
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", source],
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "V2C_CORE_WITHOUT_OPTIONAL_OR_IO_OK" in result.stdout


def test_polarization_module_has_no_io_propagation_plotting_or_global_fp_settings():
    path = ROOT / "src/ohlab/optics/polarization.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden_imports = ("matplotlib", "PIL", "streamlit", "plotly", "pandas", "pyarrow",
                         "starlette", "uvicorn", "ohlab.io", "apps", "propagation", "interference")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith(forbidden_imports), alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not module.startswith(forbidden_imports), module
            assert not module.startswith(("io", "algorithms", "metrics", "simulation", "elements")), module
        elif isinstance(node, ast.Call):
            name = ast.unparse(node.func)
            assert "fft" not in name.lower(), name
            assert "propagate" not in name.lower(), name
            assert name not in ("np.seterr", "numpy.seterr", "warnings.filterwarnings", "warnings.simplefilter"), name
            assert name not in ("open", "Path.write_text", "Path.write_bytes"), name
            assert not name.startswith(("np.random.", "numpy.random.")), name


def test_polarization_public_module_is_exact_bounded_api():
    import ohlab.optics.polarization as module
    assert set(module.__all__) == {
        "JonesField", "apply_linear_polarizer", "apply_linear_retarder", "transmission_ratio"
    }
    assert hasattr(module.JonesField, "from_scalar")
