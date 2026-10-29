"""Accepted-source exact W2/W3 differential, additive prefix and model separation."""
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

from ohlab.optics import geometric_routing,refractive_routing
from ohlab.optics.fresnel_routing import FresnelScene,trace_fresnel_scene
from scripts.validate_w3_refractive_routing import fixtures as old_fixtures
from scripts.validate_w4_fresnel_routing import fixtures

ROOT=Path(__file__).resolve().parents[1]
BASELINE='5f7f69fb6303402cffed830b3cfb9794a43b4fcf'


@pytest.fixture(scope='module')
def accepted_owner(tmp_path_factory):
    p=subprocess.run(['git','show',BASELINE+':src/ohlab/optics/refractive_routing.py'],cwd=ROOT,capture_output=True)
    assert p.returncode==0,p.stderr.decode()
    original=p.stdout.decode('utf-8')
    current=(ROOT/'src/ohlab/optics/refractive_routing.py').read_text(encoding='utf-8')
    assert current.startswith(original),'old W3 source prefix/arithmetic order changed'
    path=tmp_path_factory.mktemp('w4_accepted_owner')/'accepted_refractive_owner.py';path.write_text(original,encoding='utf-8')
    spec=importlib.util.spec_from_file_location('w4_accepted_refractive_owner',path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('name',list(old_fixtures()))
def test_all_existing_w3_fixtures_exact_differential_or_same_exception(accepted_owner,name):
    raw=old_fixtures()[name]
    def outcome(module):
        try:return ('result',module.trace_routes(module.RefractiveScene.from_dict(raw)).to_dict())
        except Exception as exc:return ('error',type(exc).__name__,str(exc))
    assert outcome(refractive_routing)==outcome(accepted_owner)


def test_empty_w3_still_projects_old_w2_exactly_and_w4_does_not_relabel_weights(accepted_owner):
    raw={'schema_version':1,'model_contract':'w3_ideal_refractive_routing_v1','source':{'id':'source','origin_m':[0,.08,-.04],
        'direction':[0,0,1],'relative_weight':1},'exterior_medium':{'id':'exterior','refractive_index':1},'bodies':[],'elements':[]}
    assert refractive_routing.trace_routes(refractive_routing.validate_scene(raw)).to_dict()==accepted_owner.trace_routes(accepted_owner.validate_scene(raw)).to_dict()
    scene=FresnelScene.from_dict(fixtures()['normal_slab'])
    w4=trace_fresnel_scene(scene).to_dict()
    assert w4['power_policy']=='absolute_source_coherency_v1'
    old=old_fixtures()['normal'];ideal=refractive_routing.trace_routes(refractive_routing.validate_scene(old))
    assert ideal.weight_model=='ideal_route_weights_no_fresnel_v1'
    assert ideal.ledger['escaped_weight']==1


def test_new_validation_and_trace_do_not_call_old_single_route_solver(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('old trace is not a W4 solver')
    monkeypatch.setattr(refractive_routing,'trace_routes',forbidden)
    monkeypatch.setattr(geometric_routing,'trace_routes',forbidden)
    result=trace_fresnel_scene(FresnelScene.from_dict(fixtures()['normal_slab']))
    assert result.ledger['unresolved_power']>0
