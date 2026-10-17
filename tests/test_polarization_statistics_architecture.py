"""Exact new core boundary: no I/O, plotting, spatial grid or legacy mutation."""

import ast
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_exact_small_new_public_apis():
    from ohlab.optics import polarization_statistics, r03_fig2a
    assert set(polarization_statistics.__all__) == {"PolarizationMeasurement", "coherency_from_samples", "measure_coherency", "analyzer_intensity"}
    assert set(r03_fig2a.__all__) == {"IdealPolarizationSpec", "IdealPolarizationResult", "run_ideal_polarization"}


def test_new_core_ast_forbids_IO_optional_stack_propagation_and_global_random():
    for filename in ("polarization_statistics.py", "r03_fig2a.py"):
        tree = ast.parse((ROOT/"src/ohlab/optics"/filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [item.name for item in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                for name in names:
                    assert not name.startswith(("apps", "pathlib", "os", "sys", "subprocess", "json", "matplotlib", "PIL", "streamlit", "propagation", "grid", "field", "interference")), name
            elif isinstance(node, ast.Call):
                name = ast.unparse(node.func)
                assert name not in ("open", "np.seterr", "np.random.seed", "np.random.randn", "np.random.normal", "np.cov")
                assert not any(word in name.lower() for word in ("fft", "propagate", "samplinggrid"))


def test_new_core_import_and_run_without_optional_or_io_modules():
    source = '''
import importlib.abc
import sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'matplotlib','PIL','streamlit','pandas','starlette','uvicorn'} or fullname.startswith(('ohlab.io','apps.')):
            raise ModuleNotFoundError('blocked '+fullname)
sys.meta_path.insert(0, Block())
from ohlab.optics.r03_fig2a import IdealPolarizationSpec, run_ideal_polarization
value=run_ideal_polarization(IdealPolarizationSpec(amplitude=1,mean_phase_rad=0,phase_std_rad=1,qwp_angle_rad=.2,hwp_angle_rad=.3,seed=1))
assert value.sample_count==256
assert not any(n.startswith(('ohlab.io','apps.')) for n in sys.modules)
print('IDEAL_STATISTICAL_CORE_ISOLATED_OK')
'''
    child_env = os.environ.copy()
    child_env["PYTHONDONTWRITEBYTECODE"] = "1"
    child = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", source], cwd=ROOT, env=child_env, capture_output=True, text=True, timeout=30)
    assert child.returncode == 0, child.stdout+child.stderr
    assert "IDEAL_STATISTICAL_CORE_ISOLATED_OK" in child.stdout
