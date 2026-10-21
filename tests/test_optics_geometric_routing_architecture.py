"""W2's numerical model remains independent of UI, I/O and wave solvers."""
import ast
import hashlib
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/'src/ohlab/optics/geometric_routing.py'


def guard_source(source):
    tree=ast.parse(source)
    allowed={'__future__','collections','dataclasses','fractions','functools','math','numbers','re','typing'}
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            for item in node.names:
                assert item.name.split('.')[0] in allowed,item.name
        if isinstance(node,ast.ImportFrom):
            assert (node.module or '').split('.')[0] in allowed,node.module
        if isinstance(node,ast.Call):
            name=ast.unparse(node.func)
            assert not any(word in name.lower() for word in ('open','read_text','write_text','fft','random','socket','fetch','raycast')),name
    # Only declarations, immutable scalar constants and re.compile at import.
    for node in tree.body:
        assert not isinstance(node,(ast.With,ast.For,ast.While,ast.Try))


def test_geometry_has_no_ui_io_optional_wave_or_legacy_solver_import():
    guard_source(MODULE.read_text(encoding='utf-8'))


@pytest.mark.parametrize('extra',['\nimport pathlib\n','\nfrom ohlab.optics.simulation import run_experiment\n','\nimport numpy.fft\n','\ndef bad():\n    open("forbidden")\n'])
def test_architecture_guard_detects_deliberate_forbidden_changes(extra):
    with pytest.raises(AssertionError):
        guard_source(MODULE.read_text(encoding='utf-8')+extra)


def test_import_and_validation_are_passive_and_leave_old_exports_unchanged():
    before={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('src/ohlab/__init__.py','src/ohlab/optics/__init__.py')}
    code='''
import importlib.abc,sys
blocked={'matplotlib','PIL','streamlit','plotly','pandas','pyarrow','altair','pydeck','starlette','uvicorn'}
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in blocked or fullname.startswith(('ohlab.io','apps.')):
            raise ModuleNotFoundError('blocked '+fullname)
sys.meta_path.insert(0,Block())
import ohlab,ohlab.optics
old_public=set(name for name in dir(ohlab.optics) if not name.startswith('_'))
from ohlab.optics.geometric_routing import GeometricScene,validate_scene,trace_routes
assert old_public==set(name for name in dir(ohlab.optics) if not name.startswith('_') and name!='geometric_routing')
assert not hasattr(ohlab.optics,'GeometricScene')
s=GeometricScene.from_dict({'schema_version':1,'model_contract':'w2_ideal_geometric_routing_v1','source':{'id':'source','origin_m':[0,0,0],'direction':[0,0,1],'relative_weight':1},'elements':[]})
assert validate_scene(s).to_dict()==s.to_dict()
assert trace_routes(s).ledger['escaped_weight']==1
assert not blocked.intersection(name.split('.')[0] for name in sys.modules)
print('W2_PASSIVE_CORE_WITHOUT_OPTIONAL_IO_UI_OK')
'''
    result=subprocess.run([sys.executable,'-B','-X','utf8','-c',code],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'W2_PASSIVE_CORE_WITHOUT_OPTIONAL_IO_UI_OK' in result.stdout
    assert before=={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in before}
