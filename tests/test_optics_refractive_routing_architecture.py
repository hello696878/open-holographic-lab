"""Exact public seam guard; no private W2 imports, UI, I/O or solver copies."""
import ast
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/'src/ohlab/optics/refractive_routing.py'
PUBLIC={"CertifiedInterval","CertifiedVector3","CertifiedPoseFrame","CertifiedRay","CertifiedPlanarFace","CertifiedPlanarHit",
        "GeometricScene","GeometricTraceResult","validate_scene","trace_routes","NumericalAmbiguityError","UnsupportedNumericalInputError",
        "INPUT_UNIT_ATOL","FRAME_ATOL","OUTPUT_UNIT_ATOL",
        "certify_pose_frame","certify_vector","certify_ray","transform_certified_vector","certify_planar_face",
        "certified_vector_add","certified_vector_subtract","certified_vector_scale","certified_dot","certified_norm",
        "certified_point_at","intersect_finite_face","nearest_finite_hit","reflect_certified_direction","certified_domain_exit"}


def guard_source(source):
    tree=ast.parse(source)
    standard={"__future__","collections","dataclasses","fractions","math","numbers","re","typing"}
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            for name in node.names:assert name.name.split('.')[0] in standard and name.asname is None
        if isinstance(node,ast.ImportFrom):
            if node.module=='ohlab.optics.geometric_routing':
                assert all(x.name in PUBLIC and (x.asname is None or (x.name,x.asname)==('trace_routes','trace_geometric_routes')) for x in node.names)
            else:assert (node.module or '').split('.')[0] in standard
        if isinstance(node,ast.Attribute) and isinstance(node.value,ast.Name) and node.value.id=='geometric_routing':
            raise AssertionError('module namespace is not part of the exact public seam')
        if isinstance(node,ast.Call):
            name=ast.unparse(node.func)
            assert not any(word in name.lower() for word in ('__import__','import_module','open','read_text','write_text','fft','random','socket','fetch','raycast'))
        if isinstance(node,ast.Name):assert node.id not in {'eval','exec','getattr','setattr','globals','locals'}
    for node in tree.body:assert not isinstance(node,(ast.With,ast.For,ast.While,ast.Try))


def test_exact_public_import_boundary_is_enforced():
    guard_source(MODULE.read_text(encoding='utf-8'))


@pytest.mark.parametrize('extra',['\nfrom ohlab.optics.geometric_routing import _candidate\n',
    '\nfrom ohlab.optics.geometric_routing import certify_vector as cv\n','\nimport numpy\n',
    '\ndef bad():\n    geometric_routing._candidate()\n','\ndef bad():\n    __import__("ohlab.io")\n',
    '\nfrom ohlab.optics.geometric_routing import *\n'])
def test_actual_guard_detects_forbidden_private_alias_dynamic_and_optional_dependencies(extra):
    with pytest.raises(AssertionError):guard_source(MODULE.read_text(encoding='utf-8')+extra)


def test_core_import_and_empty_validation_work_without_optional_ui_io_wave_packages():
    code='''
import importlib.abc,sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self,name,path=None,target=None):
        if name.split('.')[0] in {'PIL','matplotlib','streamlit','starlette','uvicorn'} or name.startswith(('ohlab.io','apps.')):
            raise ModuleNotFoundError(name)
sys.meta_path.insert(0,Block())
from ohlab.optics.refractive_routing import validate_scene,trace_routes
s=validate_scene({'schema_version':1,'model_contract':'w3_ideal_refractive_routing_v1','source':{'id':'source','origin_m':[0,0,0],'direction':[0,0,1],'relative_weight':1},'exterior_medium':{'id':'exterior','refractive_index':1},'bodies':[],'elements':[]})
assert trace_routes(s).ledger['escaped_weight']==1
print('W3_STDLIB_PUBLIC_CORE_OK')
'''
    result=subprocess.run([sys.executable,'-B','-X','utf8','-c',code],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'W3_STDLIB_PUBLIC_CORE_OK' in result.stdout
