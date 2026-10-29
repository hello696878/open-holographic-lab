"""Exact pure-core public edges; no private solver, renderer, I/O or dynamic bypass."""
import ast
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
PUBLIC_GEOMETRY={"CertifiedInterval","CertifiedVector3","CertifiedRay","NumericalAmbiguityError","UnsupportedNumericalInputError",
    "certify_vector","certify_ray","certified_dot","certified_norm","certified_vector_scale","certified_vector_subtract",
    "certified_domain_exit","certified_point_at","nearest_finite_hit"}
PUBLIC_REFRACTIVE={"CertifiedDielectricDirections","CertifiedDielectricGeometry","CertifiedNormalIncidence","FrozenRecord",
    "MediumStateAmbiguityError","RefractiveScene","certified_geometry","certified_dielectric_directions"}
PUBLIC_INTERFACE={"POLARIZATION_POLICY","SOURCE_C","RayPowerState","UnsupportedPolarizationNumericsError","apply_fresnel_interface","source_power_state"}


def guard(source):
    tree=ast.parse(source)
    allowed={"ohlab.optics.geometric_routing":PUBLIC_GEOMETRY,"ohlab.optics.refractive_routing":PUBLIC_REFRACTIVE,
             "ohlab.optics.fresnel_interface":PUBLIC_INTERFACE}
    standard={"__future__","collections","dataclasses","fractions","math","numbers","typing"}
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            assert all(x.name.split('.')[0] in standard and x.asname is None for x in node.names)
        if isinstance(node,ast.ImportFrom):
            if node.module in allowed:assert all(x.name in allowed[node.module] and x.asname is None for x in node.names)
            else:assert (node.module or '').split('.')[0] in standard and all(x.asname is None for x in node.names)
        if isinstance(node,ast.Call):
            name=ast.unparse(node.func)
            assert not any(x in name.lower() for x in ('__import__','import_module','open','read_text','write_text','socket','fft','random','raycast'))
        if isinstance(node,ast.Name):assert node.id not in {'exec','eval','getattr','setattr','globals','locals'}
        if isinstance(node,ast.Attribute) and isinstance(node.value,ast.Name):
            assert node.value.id not in {'refractive_routing','geometric_routing'}


@pytest.mark.parametrize("filename",["fresnel_interface.py","fresnel_routing.py"])
def test_exact_public_core_import_boundaries(filename):
    guard((ROOT/'src/ohlab/optics'/filename).read_text(encoding='utf-8'))


@pytest.mark.parametrize("extra",['\nfrom ohlab.optics.refractive_routing import _dielectric_direction\n',
    '\nfrom ohlab.optics.geometric_routing import *\n','\nfrom ohlab.optics.refractive_routing import certified_geometry as secret\n',
    '\nimport numpy\n','\ndef hidden():\n    __import__("ohlab.io")\n','\ndef hidden():\n    refractive_routing._faces\n'])
def test_guard_detects_actual_private_wildcard_alias_optional_and_dynamic_bypasses(extra):
    with pytest.raises(AssertionError):guard((ROOT/'src/ohlab/optics/fresnel_routing.py').read_text(encoding='utf-8')+extra)


def test_compact_core_import_without_optional_packages_and_without_old_trace():
    code='''
import importlib.abc,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,name,path=None,target=None):
  if name.split('.')[0] in {'PIL','matplotlib','streamlit','starlette','uvicorn'} or name.startswith(('ohlab.io','apps.')):raise ModuleNotFoundError(name)
sys.meta_path.insert(0,Block())
from ohlab.optics.fresnel_routing import FresnelScene,trace_fresnel_scene
scene=FresnelScene.from_dict({'schema_version':1,'model_contract':'w4_fresnel_polarized_routing_v1','source':{'id':'source','origin_m':[0,.08,-.04],'direction':[0,0,1],'frame_policy':'world_xy_forward_z_v1','polarization':'unpolarized'},'exterior_medium':{'id':'exterior','refractive_index':1},'bodies':[],'elements':[],'path_addition':'incoherent_phase_averaged_v1'})
assert trace_fresnel_scene(scene).ledger['escaped_power']==1
print('W4_COMPACT_STDLIB_CORE_OK')
'''
    p=subprocess.run([sys.executable,'-B','-X','utf8','-c',code],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert p.returncode==0,p.stdout+p.stderr
    assert 'W4_COMPACT_STDLIB_CORE_OK' in p.stdout
