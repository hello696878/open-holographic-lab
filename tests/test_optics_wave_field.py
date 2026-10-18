"""W1 limits, event provenance, canonical identity and ownership contracts."""
from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest

from ohlab.optics import SequentialExperiment, run_experiment
from ohlab import SamplingGrid
from ohlab.optics import simulation
from ohlab.optics import wave_field as wf


def experiment(*, n=11, aperture_z=.03, lens_z=.06, terminal=.22, amplitude=1., focal=.08):
    return SequentialExperiment.from_dict({
        "schema_version": 1, "model_contract": "v0_aligned_scalar_forward_v1",
        "wavelength_m": 633e-9, "grid": {"ny": n, "nx": n, "dy": 16e-6, "dx": 16e-6},
        "source": {"kind": "gaussian", "amplitude": amplitude, "phase_rad": .31,
                   "waist_radius_m": 160e-6, "waist_z_m": 0., "center_x_m": 0., "center_y_m": 0.},
        "components": [{"id": "aperture", "kind": "circular_aperture", "z_m": aperture_z, "radius_m": 60e-6},
                       {"id": "lens", "kind": "thin_lens", "z_m": lens_z, "focal_length_m": focal}],
        "observation": {"id": "screen", "z_m": terminal}})


def test_default_allocation_exact_three_two_fourteen_and_caps():
    e = experiment()
    zs = wf.default_interior_positions(e)
    expected = tuple(start+(end-start)*j/(count+1)
                     for start, end, count in ((0., .03, 3), (.03, .06, 2), (.06, .22, 14))
                     for j in range(1, count+1))
    assert zs == expected
    plan = wf.section_plan(e, interior_z_m=zs)
    assert len(plan) == 25
    assert len({p.id for p in plan}) == 25
    assert [p.stage for p in plan if p.stage != "interior"] == [
        "source", "before:aperture", "after:aperture", "before:lens", "after:lens", "observation"]
    assert [(p.anchor_selector, p.anchor_z_m) for p in plan if p.stage == "interior"] == [
        *(('source', 0.),)*3, *(('after:aperture', .03),)*2, *(('after:lens', .06),)*14]


def test_largest_remainder_stable_tie_and_event_priority():
    e = experiment(aperture_z=1., lens_z=2., terminal=3.)
    z = wf.default_interior_positions(e)
    assert [sum(a < v < b for v in z) for a, b in ((0, 1), (1, 2), (2, 3))] == [7, 6, 6]
    assert len(wf.section_plan(e, interior_z_m=())) == 6


@pytest.mark.parametrize("zs", [[.01], ".01", None, (True,), (1+0j,), ("0.01",), (np.array(.01),)])
def test_sampling_type_errors_before_computation(zs, monkeypatch):
    monkeypatch.setattr(wf, "run_experiment", lambda *a, **k: pytest.fail("validation computed"))
    with pytest.raises(TypeError):
        wf.sample_wave_field(experiment(), interior_z_m=zs)


@pytest.mark.parametrize("zs", [(float("nan"),), (float("inf"),), (0.,), (.03,), (.06,), (.22,),
                                (-.1,), (.3,), (.01, .01), (.02, .01), tuple(i/1000 for i in range(1, 21))])
def test_sampling_value_errors_before_computation(zs, monkeypatch):
    monkeypatch.setattr(wf, "run_experiment", lambda *a, **k: pytest.fail("validation computed"))
    with pytest.raises(ValueError):
        wf.sample_wave_field(experiment(), interior_z_m=zs)


@pytest.mark.parametrize("bad", ["uniform", "missing", "order", "extra", "axis"])
def test_unsupported_is_rejected_without_changing_v0(bad, monkeypatch):
    spec = experiment(n=129 if bad == "axis" else 7).to_dict()
    if bad == "uniform":
        spec["source"] = dict(kind="uniform", amplitude=1., phase_rad=0.)
    elif bad == "missing":
        spec["components"] = []
    elif bad == "order":
        spec["components"] = [dict(id="lens", kind="thin_lens", z_m=0., focal_length_m=.08),
                              dict(id="a", kind="circular_aperture", z_m=.01, radius_m=60e-6)]
    elif bad == "extra":
        spec["components"].append(dict(id="other", kind="thin_lens", z_m=.1, focal_length_m=.08))
    e = SequentialExperiment.from_dict(spec)
    # Existing V0 still accepts each original, unsupported-for-W1 experiment.
    assert run_experiment(e).observation.shape == e.grid.shape
    monkeypatch.setattr(wf, "run_experiment", lambda *a, **k: pytest.fail("W1 validation computed"))
    with pytest.raises(ValueError, match="W1"):
        wf.sample_wave_field(e, interior_z_m=())


def test_only_one_canonical_call_three_anchors_and_exact_terminal_identity(monkeypatch):
    e = experiment(n=13)
    plain = run_experiment(e)
    captured = []
    def once(experiment, *, record_fields):
        assert record_fields == ("source", "after:aperture", "after:lens")
        result = run_experiment(experiment, record_fields=record_fields)
        captured.append(result)
        return result
    monkeypatch.setattr(wf, "run_experiment", once)
    r = wf.sample_wave_field(e, interior_z_m=wf.default_interior_positions(e))
    assert len(captured) == 1
    assert r.canonical is captured[0]
    assert r.observation is captured[0].observation
    assert r.observation.data.tobytes() == plain.observation.data.tobytes()
    assert r.planes[-1].norm == plain.stages[-1].norm
    assert r.planes[-1].delta_norm == plain.stages[-1].delta_norm


def test_every_asm_uses_correct_capture_forward_separation_and_explicit_pad1(monkeypatch):
    e = experiment()
    plan = wf.section_plan(e, interior_z_m=wf.default_interior_positions(e))
    calls, canonical_calls = [], []
    public = wf.propagate_angular_spectrum
    original = simulation.propagate_angular_spectrum
    def canonical(field, *, distance_m, pad_factor):
        canonical_calls.append((distance_m, pad_factor))
        return original(field, distance_m=distance_m, pad_factor=pad_factor)
    def section(field, *, distance_m, pad_factor):
        calls.append((field, distance_m, pad_factor))
        return public(field, distance_m=distance_m, pad_factor=pad_factor)
    monkeypatch.setattr(simulation, "propagate_angular_spectrum", canonical)
    monkeypatch.setattr(wf, "propagate_angular_spectrum", section)
    r = wf.sample_wave_field(e, interior_z_m=wf.default_interior_positions(e))
    computed = [p for p in plan if p.stage == "interior" or p.stage.startswith("before:")]
    assert len(calls) == 21
    assert len(canonical_calls)+len(calls) == 24
    for (field, distance, pad), p in zip(calls, computed):
        assert field is r.canonical.field_at(p.anchor_selector)
        assert distance == p.z_m-p.anchor_z_m >= 0
        assert pad == 1
    assert [p for _, p in canonical_calls] == [1, 1, 1]


@pytest.mark.parametrize("positions", [(0., 0., 0.), (.03, .03, .03), (0., .06, .06), (0., 0., .22)])
def test_colocated_events_never_collapse_and_zero_spans_get_no_interiors(positions):
    e = experiment(aperture_z=positions[0], lens_z=positions[1], terminal=positions[2])
    z = wf.default_interior_positions(e)
    r = wf.sample_wave_field(e, interior_z_m=z)
    events = [p for p in r.planes if p.stage != "interior"]
    assert len(events) == len({p.id for p in events}) == 6
    assert [p.z_m for p in events] == [0., positions[0], positions[0], positions[1], positions[1], positions[2]]
    assert len(z) == (0 if positions[-1] == 0 else 19)
    if positions == (0., 0., 0.):
        assert len(r.planes) == 6
        assert not np.array_equal(r.intensities[1], r.intensities[2])


@pytest.mark.parametrize("focal", [.08, -.08])
def test_source_and_result_owned_readonly_no_mutation_and_local_error_settings(focal):
    e = experiment(focal=focal)
    spec = e.to_dict()
    settings = np.geterr()
    try:
        np.seterr(all="raise")
        r = wf.sample_wave_field(e, interior_z_m=(.01, .04, .1))
        assert np.geterr() == dict.fromkeys(settings, "raise")
    finally:
        np.seterr(**settings)
    assert e.to_dict() == spec
    for array in (r.intensities, r.x_m, r.y_m):
        assert array.flags.owndata and not array.flags.writeable
    for f in (r.observation, *(p.field for p in r.canonical.recorded_fields)):
        assert not np.shares_memory(r.intensities, f.data)
    with pytest.raises(FrozenInstanceError):
        r.planes = ()
    mutated = r.intensities.copy()
    copy = replace(r, intensities=mutated)
    mutated.fill(99)
    assert not np.any(copy.intensities == 99)


def test_dark_field_zero_distance_and_zero_ratios():
    e = experiment(amplitude=0, aperture_z=0, lens_z=0, terminal=0)
    r = wf.sample_wave_field(e, interior_z_m=())
    assert np.count_nonzero(r.intensities) == 0
    assert all(p.norm == p.max_intensity == p.on_axis_intensity == 0 for p in r.planes)
    assert all(p.transmission_ratio is None for p in r.planes)
    assert r.planes[0].delta_norm is None
    assert all(p.delta_norm == 0 for p in r.planes[1:])


def test_norm_comparison_is_signed_raw_and_anchor_based():
    e = experiment()
    r = wf.sample_wave_field(e, interior_z_m=(.01, .04, .1))
    records = {s.selector: s for s in r.canonical.stages}
    for p in r.planes:
        if p.stage == "interior":
            assert p.comparison == "upstream_anchor"
            assert p.previous_norm == records[p.anchor_selector].norm
            assert p.delta_norm == p.norm-p.previous_norm
            assert p.transmission_ratio == p.norm/p.previous_norm
        else:
            record = records[p.stage]
            assert (p.norm, p.previous_norm, p.delta_norm, p.transmission_ratio) == (
                record.norm, record.previous_norm, record.delta_norm, record.transmission_ratio)
    assert records['after:aperture'].delta_norm < 0
    assert not np.isclose(records['after:aperture'].transmission_ratio, 1, rtol=.01, atol=0)
    synthetic = wf.StageRecord(selector="after:lens", z_m=0, norm=np.nextafter(1., 2.), previous_norm=1.)
    assert synthetic.delta_norm > 0 and synthetic.transmission_ratio > 1


@pytest.mark.parametrize("kind", ["negative", "nan", "shape", "dtype", "axis", "order", "diagnostic"])
def test_public_result_constructor_rejects_invalid_or_unassociated_result(kind):
    r = wf.sample_wave_field(experiment(), interior_z_m=(.01,))
    args = {}
    if kind in ("negative", "nan", "shape", "dtype"):
        a = r.intensities.copy()
        if kind == "negative": a[0, 0, 0] = -1
        if kind == "nan": a[0, 0, 0] = np.nan
        if kind == "shape": a = a[:-1]
        if kind == "dtype": a = a.astype(np.float32)
        args['intensities'] = a
    elif kind == "axis": args['x_m'] = r.x_m[::-1]
    elif kind == "order": args['planes'] = r.planes[::-1]
    elif kind == "diagnostic": args['planes'] = (replace(r.planes[0], max_intensity=123.), *r.planes[1:])
    with pytest.raises((TypeError, ValueError)):
        replace(r, **args)


def test_rounding_cannot_fabricate_interior_positions():
    e = experiment(aperture_z=1., lens_z=1., terminal=np.nextafter(1., 2.))
    with pytest.raises(ValueError, match="strictly|inside"):
        wf.validate_sampling(e, (1.+(e.observation.z_m-1.)/2,))


def test_whole_field_underflow_is_not_accepted_as_dark():
    with pytest.raises(ValueError, match="norm.*unusable"):
        wf.sample_wave_field(experiment(amplitude=1e-200), interior_z_m=())


@pytest.mark.parametrize('ny,nx', [(1, 1), (1, 128), (128, 1), (128, 128)])
def test_axis_bound_inclusive_and_no_silent_resampling(ny, nx):
    e = replace(experiment(), grid=SamplingGrid(ny=ny, nx=nx, dy=16e-6, dx=16e-6))
    r = wf.sample_wave_field(e, interior_z_m=())
    assert r.intensities.shape == (6, ny, nx)
    assert r.experiment is e
    np.testing.assert_array_equal(r.x_m, e.grid.x)
    np.testing.assert_array_equal(r.y_m, e.grid.y)


@pytest.mark.parametrize('changes,error', [
    ({'z_m': True}, TypeError), ({'stage': 1}, TypeError),
    ({'z_m': np.nan}, ValueError), ({'separation_m': -.1}, ValueError),
    ({'id': 'section:after:other'}, ValueError),
    ({'anchor_selector': 'before:aperture'}, ValueError),
    ({'z_m': .2, 'separation_m': .1}, ValueError),
])
def test_public_position_validates_geometry_and_identity(changes, error):
    position = wf.section_plan(experiment(), interior_z_m=(.01,))[1]
    with pytest.raises(error):
        replace(position, **changes)


@pytest.mark.parametrize('changes,error', [
    ({'norm': True}, TypeError), ({'on_axis_intensity': '1'}, TypeError),
    ({'max_intensity': np.inf}, ValueError), ({'norm': -1.}, ValueError),
    ({'comparison': 'previous_sample'}, ValueError),
    ({'on_axis_intensity': 2., 'max_intensity': 1.}, ValueError),
    ({'delta_norm': 0.}, ValueError),
])
def test_public_plane_validates_diagnostic_types_domains_and_raw_arithmetic(changes, error):
    plane = wf.sample_wave_field(experiment(), interior_z_m=()).planes[0]
    with pytest.raises(error):
        replace(plane, **changes)
