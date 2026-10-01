"""V0 imports and propagation reuse without changing existing guards."""

import ast
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def test_v0_core_imports_without_optional_ui_plotting_and_without_io():
    source='''
import importlib.abc, sys
blocked={'matplotlib','PIL','streamlit','plotly','pandas','pyarrow','altair','pydeck'}
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in blocked or fullname.startswith(('ohlab.io','apps.')):
            raise ModuleNotFoundError('blocked '+fullname)
sys.meta_path.insert(0,Block())
import ohlab
import ohlab.optics
from ohlab.optics import SequentialExperiment,run_experiment
assert not hasattr(ohlab,'SequentialExperiment')
e=SequentialExperiment.from_dict({'schema_version':1,'model_contract':'v0_aligned_scalar_forward_v1','wavelength_m':633e-9,'grid':{'ny':2,'nx':3,'dy':4e-6,'dx':4e-6},'source':{'kind':'uniform','amplitude':1,'phase_rad':0},'components':[],'observation':{'id':'screen','z_m':0}})
assert run_experiment(e).observation.shape==(2,3)
assert not blocked.intersection(s.split('.')[0] for s in sys.modules)
assert not any(s.startswith(('ohlab.io','ohlab.algorithms','ohlab.metrics','apps.')) for s in sys.modules)
print('V0_CORE_WITHOUT_OPTIONAL_OR_IO_OK')
'''
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    result=subprocess.run([sys.executable,'-B','-X','utf8','-c',source],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'V0_CORE_WITHOUT_OPTIONAL_OR_IO_OK' in result.stdout


def test_v0_has_no_production_fft_or_duplicate_propagation_function():
    for path in (ROOT/'src/ohlab/optics').glob('*.py'):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.Call):
                name=ast.unparse(node.func)
                assert 'fft' not in name.lower(),(path,name)
            if isinstance(node,ast.ImportFrom):
                assert not (node.module or '').startswith(('ohlab.io','ohlab.algorithms','ohlab.metrics','apps'))
    source=(ROOT/'src/ohlab/optics/simulation.py').read_text(encoding='utf-8')
    assert 'propagate_angular_spectrum(current, distance_m=distance_m, pad_factor=1)' in source
