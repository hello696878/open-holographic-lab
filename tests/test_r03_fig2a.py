"""Actual seeded finite ideal ensemble, without paper data or fitted outputs."""

from dataclasses import replace
import math

import numpy as np
import pytest

from ohlab import ComplexField, SamplingGrid
from ohlab.optics.polarization import JonesField, apply_linear_retarder
from ohlab.optics.r03_fig2a import IdealPolarizationSpec, run_ideal_polarization


def spec(**updates):
    base = dict(amplitude=1., mean_phase_rad=math.pi, phase_std_rad=1.2, qwp_angle_rad=0., hwp_angle_rad=0., seed=20261017)
    base.update(updates)
    return IdealPolarizationSpec(**base)


def scalar_coherency(values):
    return np.array([[sum(complex(e[a])*complex(e[b]).conjugate() for e in values)/len(values) for b in (0,1)] for a in (0,1)], dtype=np.complex128)


def test_actual_single_rng_call_seed_phase_identity_and_owned_result(monkeypatch):
    actual = run_ideal_polarization(spec())
    expected_normal = np.random.Generator(np.random.PCG64(20261017)).standard_normal((16,16))
    expected_unwrapped = math.pi + 1.2*expected_normal
    np.testing.assert_array_equal(actual.phase_unwrapped_rad, expected_unwrapped)
    np.testing.assert_array_equal(actual.phase_wrapped_rad, np.mod(expected_unwrapped, 2*math.pi))
    again = run_ideal_polarization(spec())
    assert actual.spec == again.spec and actual.spec is not again.spec
    for name in ("phase_unwrapped_rad", "phase_wrapped_rad"):
        first, second = getattr(actual,name), getattr(again,name)
        assert not first.flags.writeable and not np.shares_memory(first,second)
        np.testing.assert_array_equal(first,second)
    np.testing.assert_array_equal(actual.output.coherency,again.output.coherency)
    assert actual.population_dop == math.exp(-.5*1.2**2)
    assert abs(actual.output.degree_of_polarization-actual.population_dop) > 1e-5
    assert actual.model_contract == "r03_ideal_statistical_polarization_v1"
    assert actual.rng_algorithm == "PCG64" and actual.sample_count == 256


def test_zero_sigma_still_consumes_exactly_one_standard_normal_call(monkeypatch):
    calls=[]
    original=np.random.default_rng
    class Traced:
        def __init__(self, rng): self.rng=rng
        @property
        def bit_generator(self): return self.rng.bit_generator
        def standard_normal(self, shape):
            calls.append(shape)
            return self.rng.standard_normal(shape)
    monkeypatch.setattr(np.random, "default_rng", lambda seed: Traced(original(seed)))
    result=run_ideal_polarization(spec(phase_std_rad=0.))
    assert calls==[(16,16)]
    np.testing.assert_array_equal(result.phase_unwrapped_rad,np.full((16,16),math.pi))
    assert result.output.degree_of_polarization == pytest.approx(1,rel=2e-13,abs=2e-13)


def test_fail_closed_before_drawing_if_default_rng_algorithm_changes(monkeypatch):
    class Unsupported:
        bit_generator=object()
        def standard_normal(self, shape):
            raise AssertionError("unsupported algorithm must not draw")
    monkeypatch.setattr(np.random,"default_rng",lambda seed: Unsupported())
    with pytest.raises(ValueError,match="expected PCG64"):
        run_ideal_polarization(spec())


@pytest.mark.parametrize("seed,std,theta,beta", [(0,0.,0.,0.), (1,1.2,.37,-.61), (2,math.pi,-1.1,.9), (2**32-1,.4,2*math.pi,-2*math.pi)])
def test_independent_direct_fields_and_old_public_retarder_match(seed,std,theta,beta):
    value=run_ideal_polarization(spec(amplitude=2.3,seed=seed,phase_std_rad=std,qwp_angle_rad=theta,hwp_angle_rad=beta))
    phase=value.phase_wrapped_rad.ravel(order="C")
    fields=np.array([[2.3*complex(math.cos(p),math.sin(p))/math.sqrt(2),2.3/math.sqrt(2)] for p in phase],dtype=np.complex128)
    expected=scalar_coherency(fields)
    np.testing.assert_allclose(value.after_slm.coherency,expected,rtol=2e-14,atol=2e-14*2.3**2)
    expected_finite=abs(sum(complex(math.cos(p),math.sin(p)) for p in phase)/256)
    np.testing.assert_allclose(value.after_slm.degree_of_polarization,expected_finite,rtol=2e-13,atol=2e-13)
    # Actual public Jones actions on a separately declared test-only SI plane.
    grid=SamplingGrid(ny=16,nx=16,dy=4e-6,dx=3e-6)
    source=JonesField(x=ComplexField(data=fields[:,0].reshape(16,16),grid=grid,wavelength_m=633e-9), y=ComplexField(data=fields[:,1].reshape(16,16),grid=grid,wavelength_m=633e-9))
    q=apply_linear_retarder(source,axis_angle_rad=theta,retardance_rad=math.pi/2)
    h=apply_linear_retarder(q,axis_angle_rad=beta,retardance_rad=math.pi)
    for stage,field in ((value.after_qwp,q),(value.output,h)):
        reference=scalar_coherency(list(zip(field.x.data.ravel(),field.y.data.ravel())))
        np.testing.assert_allclose(stage.coherency,reference,rtol=2e-14,atol=2e-14*2.3**2)
        np.testing.assert_allclose(stage.stokes[0],value.source.stokes[0],rtol=2e-13,atol=2e-13*2.3**2)
        np.testing.assert_allclose(stage.degree_of_polarization,expected_finite,rtol=2e-13,atol=2e-13)
    np.testing.assert_allclose(value.source.stokes[0],2.3**2,rtol=2e-13,atol=2e-13*2.3**2)


def test_zero_source_is_dark_but_preserves_realization_and_null_population():
    result=run_ideal_polarization(spec(amplitude=0.))
    assert result.population_dop is None
    for stage in (result.source,result.after_slm,result.after_qwp,result.output):
        assert stage.degree_of_polarization is None and stage.normalized_stokes is None
        np.testing.assert_array_equal(stage.coherency,np.zeros((2,2)))
    assert np.unique(result.phase_unwrapped_rad).size==256


@pytest.mark.parametrize("key,value,error", [("amplitude",True,TypeError),("amplitude","1",TypeError),("amplitude",-1.,ValueError),("amplitude",1e6+1,ValueError),("amplitude",math.nan,ValueError),("mean_phase_rad",2*math.pi+.01,ValueError),("phase_std_rad",-1e-9,ValueError),("phase_std_rad",math.pi+.01,ValueError),("qwp_angle_rad",math.inf,ValueError),("hwp_angle_rad",np.array(0.),TypeError),("seed",True,TypeError),("seed",np.int64(1),TypeError),("seed",1.,TypeError),("seed",-1,ValueError),("seed",2**32,ValueError)])
def test_invalid_specs(key,value,error):
    with pytest.raises(error): spec(**{key:value})


def test_weak_nonzero_source_rejected_instead_of_fabricated_dark():
    with pytest.raises(ValueError,match="underflow"):
        run_ideal_polarization(spec(amplitude=1e-200))


def test_global_legacy_rng_untouched_and_errors_restored():
    before=np.random.get_state()
    with np.errstate(over="ignore",invalid="warn",divide="ignore",under="raise"):
        policy=np.geterr().copy()
        run_ideal_polarization(spec())
        assert np.geterr()==policy
    after=np.random.get_state()
    assert before[0]==after[0] and before[2:]==after[2:]
    np.testing.assert_array_equal(before[1],after[1])


def test_result_constructor_rejects_phase_relabel_and_owns_all_stages():
    result=run_ideal_polarization(spec())
    with pytest.raises(ValueError,match="exact np.mod"):
        replace(result,phase_wrapped_rad=np.zeros((16,16)))
    with pytest.raises(ValueError,match="population_dop"):
        replace(result,population_dop=.1)
    assert not np.shares_memory(result.source.coherency,result.after_slm.coherency)
    with pytest.raises(TypeError): run_ideal_polarization({})


@pytest.mark.parametrize("updates", [
    {"sample_count":256.0}, {"sample_count":True},
    {"sample_shape":[16,16]}, {"sample_shape":(16.,16)},
    {"sample_shape":(16,np.int64(16))}, {"sample_order":np.str_("C")},
    {"population_dop":True},
])
def test_result_metadata_rejects_equal_but_wrong_types(updates):
    result=run_ideal_polarization(spec())
    with pytest.raises(TypeError):
        replace(result,**updates)


def test_phase_only_modulation_preserves_intensity_but_can_change_ensemble_dop():
    result=run_ideal_polarization(spec())
    np.testing.assert_allclose(result.after_slm.stokes[0],result.source.stokes[0],rtol=2e-13,atol=2e-13)
    assert result.source.degree_of_polarization > .999999999999
    assert result.after_slm.degree_of_polarization < .9
    for stage in (result.after_qwp,result.output):
        np.testing.assert_allclose(stage.eigenvalues,result.after_slm.eigenvalues,rtol=2e-13,atol=2e-13)
        np.testing.assert_allclose(stage.degree_of_polarization,result.after_slm.degree_of_polarization,rtol=2e-13,atol=2e-13)
