"""W1 delegates science to public V0/M1 without new optional/I/O dependencies."""
import ast
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT/'src/ohlab/optics/wave_field.py'


def test_w1_no_fft_transmission_formula_private_numerical_or_io_imports():
    tree = ast.parse(PATH.read_text(encoding='utf-8'))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imports.append(node.module)
            assert all(not alias.name.startswith('_') for alias in node.names)
            assert not (node.module or '').startswith(('ohlab.io', 'apps', 'matplotlib', 'PIL', 'scipy'))
        if isinstance(node, ast.Call):
            name = ast.unparse(node.func).lower()
            assert 'fft' not in name and not name.endswith(('exp', 'sqrt', 'sin', 'cos'))
            assert not name.endswith(('apply_component', 'sample_source'))
    assert 'propagation' in imports and 'simulation' in imports
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == 'run_experiment']
    assert len(calls) == 1
    propagations = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                   and isinstance(node.func, ast.Name) and node.func.id == 'propagate_angular_spectrum']
    assert len(propagations) == 1
    assert any(k.arg == 'pad_factor' and isinstance(k.value, ast.Constant) and k.value.value == 1
               for k in propagations[0].keywords)


def test_w1_imports_in_isolated_process_without_optional_or_io_and_exports_unchanged():
    source = '''
import importlib.abc, sys
blocked={'matplotlib','PIL','streamlit','plotly','pandas','pyarrow','altair','pydeck'}
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in blocked or fullname.startswith(('ohlab.io','apps.')):
            raise ModuleNotFoundError('blocked '+fullname)
sys.meta_path.insert(0,Block())
import ohlab, ohlab.optics
before=tuple(ohlab.optics.__all__)
from ohlab.optics.wave_field import sample_wave_field,default_interior_positions
assert tuple(ohlab.optics.__all__)==before
assert not hasattr(ohlab.optics,'sample_wave_field')
assert not hasattr(ohlab,'sample_wave_field')
assert not blocked.intersection(s.split('.')[0] for s in sys.modules)
assert not any(s.startswith(('ohlab.io','ohlab.algorithms','ohlab.metrics','apps.')) for s in sys.modules)
print('W1_PUBLIC_DELEGATION_WITHOUT_OPTIONAL_OR_IO_OK')
'''
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    r = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', source], cwd=ROOT,
                       env=env, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stdout+r.stderr
    assert 'W1_PUBLIC_DELEGATION_WITHOUT_OPTIONAL_OR_IO_OK' in r.stdout
