"""Sequential interval, stage ownership, dark-field and arithmetic contracts."""

from dataclasses import FrozenInstanceError, replace
import numpy as np
import pytest

from ohlab import ComplexField, SamplingGrid
from ohlab.optics import SequentialExperiment, run_experiment
from ohlab.optics.simulation import StageRecord, StageField, SequentialResult, _sampled_norm
from ohlab.optics import simulation


def spec(*, amplitude=2.0):
    return SequentialExperiment.from_dict({
        "schema_version": 1, "model_contract": "v0_aligned_scalar_forward_v1",
        "wavelength_m": 633e-9, "grid": {"ny": 5, "nx": 6, "dy": 13e-6, "dx": 9e-6},
        "source": {"kind": "uniform", "amplitude": amplitude, "phase_rad": .31},
        "components": [
            {"id": "stop", "kind": "rectangular_aperture", "z_m": .0013, "width_m": 36e-6, "height_m": 52e-6},
            {"id": "lens", "kind": "thin_lens", "z_m": .0034, "focal_length_m": .02},
            {"id": "circle", "kind": "circular_aperture", "z_m": .0034, "radius_m": 25e-6},
        ], "observation": {"id": "screen", "z_m": .005},
    })


def test_runner_derives_each_interval_once_including_terminal(monkeypatch):
    calls = []
    original = simulation.propagate_angular_spectrum
    def counted(field, *, distance_m, pad_factor):
        calls.append((distance_m, pad_factor))
        return original(field, distance_m=distance_m, pad_factor=pad_factor)
    monkeypatch.setattr(simulation, "propagate_angular_spectrum", counted)
    result = run_experiment(spec())
    np.testing.assert_allclose([a for a,b in calls], [.0013,.0021,0,.0016], rtol=1e-14, atol=1e-18)
    assert [b for a,b in calls] == [1,1,1,1]
    assert result.stages[-1].selector == "observation"
    assert result.stages[-1].z_m == .005


def test_colocated_stages_remain_distinct_and_requested_fields_do_not_change_result():
    e = spec(); plain = run_experiment(e)
    selectors = ("source", "before:lens", "after:lens", "after:circle")
    recorded = run_experiment(e, record_fields=selectors)
    assert plain.recorded_fields == ()
    assert recorded.observation.data.tobytes() == plain.observation.data.tobytes()
    assert tuple(f.selector for f in recorded.recorded_fields) == selectors
    assert [(s.selector,s.z_m) for s in recorded.stages][3:7] == [
        ("before:lens",.0034),("after:lens",.0034),("before:circle",.0034),("after:circle",.0034)]
    assert recorded.field_at("observation") is recorded.observation
    with pytest.raises(ValueError, match="not recorded"):
        plain.field_at("source")
    # A terminal propagation must change this asymmetric separated train.
    assert np.max(abs(recorded.observation.data-recorded.field_at("after:circle").data)) > .01


@pytest.mark.parametrize("selectors", [("source","source"), ("observation",), ("after:missing",), ("source","before:stop","after:stop","before:lens","after:lens")])
def test_selector_value_errors(selectors):
    with pytest.raises(ValueError):
        run_experiment(spec(), record_fields=selectors)


@pytest.mark.parametrize("selectors", [["source"], "source", (1,)])
def test_selector_type_errors(selectors):
    with pytest.raises(TypeError):
        run_experiment(spec(), record_fields=selectors)


def test_result_fields_are_independent_immutable_owned_storage():
    result = run_experiment(spec(), record_fields=("source", "after:stop"))
    for field in (result.observation, *(s.field for s in result.recorded_fields)):
        assert field.data.dtype == np.dtype("complex128")
        with pytest.raises(ValueError):
            field.data.setflags(write=True)
        derived = field.intensity; derived.fill(99)
        assert not np.all(field.intensity == 99)
    assert not np.shares_memory(result.field_at("source").data, result.observation.data)
    with pytest.raises(FrozenInstanceError):
        result.stages = ()


def test_dark_train_keeps_zero_and_undefined_ratios_valid():
    result = run_experiment(spec(amplitude=0), record_fields=("source",))
    assert np.all(result.observation.data == 0)
    for stage in result.stages:
        assert stage.norm == 0
        assert stage.transmission_ratio is None
    assert result.stages[0].delta_norm is None
    assert all(s.delta_norm == 0 for s in result.stages[1:])


def test_signed_delta_and_lens_roundoff_are_not_clamped():
    record = StageRecord(selector="after:lens",z_m=0,norm=np.nextafter(1.,2.),previous_norm=1.)
    assert record.delta_norm > 0 and record.transmission_ratio > 1
    result = run_experiment(spec())
    aperture = next(s for s in result.stages if s.selector == "after:stop")
    assert aperture.delta_norm < 0
    assert aperture.transmission_ratio == pytest.approx(25/30, rel=2e-14, abs=0)


def test_empty_identity_train_returns_owned_actual_observation():
    d=spec().to_dict(); d['components']=[]; d['observation']['z_m']=0
    result=run_experiment(SequentialExperiment.from_dict(d),record_fields=("source",))
    assert result.observation.data.tobytes() == result.field_at("source").data.tobytes()
    assert not np.shares_memory(result.observation.data,result.field_at("source").data)


def test_forward_evanescent_decay_and_caller_error_settings(monkeypatch):
    d=spec().to_dict();d['grid']={'ny':4,'nx':4,'dy':100e-9,'dx':100e-9};d['components']=[];d['observation']['z_m']=100e-6
    e=SequentialExperiment.from_dict(d)
    pattern=np.zeros((4,4),complex);pattern[:]=(-1.)**(np.indices((4,4)).sum(axis=0))
    field=ComplexField(data=pattern,grid=e.grid,wavelength_m=e.wavelength_m)
    monkeypatch.setattr(simulation,'sample_source',lambda _: field)
    before=np.geterr()
    try:
        np.seterr(all='raise'); caller=np.geterr().copy()
        result=run_experiment(e)
        assert np.all(result.observation.data==0)  # independently only evanescent checkerboard bin
        assert result.stages[-1].transmission_ratio==0
        assert np.geterr()==caller
        with pytest.raises(ValueError):
            _sampled_norm(ComplexField(data=np.full((4,4),1e200+0j),grid=e.grid,wavelength_m=e.wavelength_m))
        assert np.geterr()==caller
    finally:
        np.seterr(**before)


@pytest.mark.parametrize('amplitude', [1e-250,1e200])
def test_unusable_complete_norm_raises_without_relabeling_dark(amplitude):
    with pytest.raises(ValueError,match='norm'):
        run_experiment(spec(amplitude=amplitude))


def test_result_validation_rejects_inconsistent_stage_or_field():
    r=run_experiment(spec())
    with pytest.raises(ValueError,match='stages'):
        replace(r,stages=r.stages[:-1])
    with pytest.raises(ValueError,match='terminal norm'):
        replace(r,observation=ComplexField(data=np.zeros(r.observation.shape),grid=r.experiment.grid,wavelength_m=r.experiment.wavelength_m))
    with pytest.raises(TypeError):
        run_experiment({})
    with pytest.raises(ValueError):
        StageRecord(selector='source',z_m=1,norm=0,previous_norm=None)
    with pytest.raises(ValueError):
        StageRecord(selector='after:lens',z_m=0,norm=0,previous_norm=None)
    with pytest.raises(TypeError):
        StageField(selector='source',field=None)
