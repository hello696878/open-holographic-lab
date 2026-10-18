"""Independent complex DFT, Gaussian, mask, phase and coordinate W1 checks."""
from dataclasses import replace
import math

import numpy as np
import pytest

from ohlab import SamplingGrid
from ohlab.optics import SequentialExperiment, run_experiment
from ohlab.optics import wave_field as wf
from scripts.validate_w1_wave_field import (asymmetric, axes, example, gaussian,
    gaussian_fixture, independent_sections, lens_gaussian, observe_complex,
    relative_l2, second_moment_radius)


@pytest.mark.parametrize("ny,nx", [(11, 14), (14, 11), (5, 6), (6, 5)])
@pytest.mark.parametrize("rectangular", [False, True])
@pytest.mark.parametrize("focal", [.08, -.08])
def test_every_section_complex_against_independent_physical_dft(ny, nx, rectangular, focal):
    e = asymmetric(ny=ny, nx=nx, rectangular=rectangular, focal=focal)
    zs = wf.default_interior_positions(e)
    references = independent_sections(e, zs)
    with observe_complex() as actual:
        r = wf.sample_wave_field(e, interior_z_m=zs)
    assert len(actual) == len(references) == 25
    scale = float(np.max(abs(references['section:source'])))
    for row, field, intensity in zip(r.planes, actual, r.intensities):
        expected = references[row.id]
        assert relative_l2(field, expected) <= 2e-11
        np.testing.assert_allclose(field, expected, rtol=2e-11, atol=2e-11*scale)
        np.testing.assert_allclose(intensity, expected.real**2+expected.imag**2,
                                   rtol=4e-11, atol=4e-11*scale**2)
    np.testing.assert_array_equal(r.x_m, [(j-nx//2)*e.grid.dx for j in range(nx)])
    np.testing.assert_array_equal(r.y_m, [(i-ny//2)*e.grid.dy for i in range(ny)])


def test_independent_reference_uses_no_production_science_or_array_helpers(monkeypatch):
    e = asymmetric(ny=5, nx=6)
    expected = independent_sections(e, (.0001, .0005, .001))
    def prohibited(*args, **kwargs):
        raise AssertionError('reference called production numerical/coordinate helper')
    monkeypatch.setattr(wf, 'section_plan', prohibited)
    monkeypatch.setattr(wf, 'run_experiment', prohibited)
    monkeypatch.setattr(wf, 'propagate_angular_spectrum', prohibited)
    monkeypatch.setattr(SamplingGrid, 'meshgrid', prohibited)
    monkeypatch.setattr(SamplingGrid, 'freq_meshgrid', prohibited)
    monkeypatch.setattr(np.fft, 'fft2', prohibited)
    monkeypatch.setattr(np.fft, 'ifft2', prohibited)
    monkeypatch.setattr(np.fft, 'fftfreq', prohibited)
    actual = independent_sections(e, (.0001, .0005, .001))
    for key in expected:
        np.testing.assert_array_equal(actual[key], expected[key])


@pytest.mark.parametrize("rectangular", [False, True])
def test_exact_inclusive_hand_mask_before_after_at_same_physical_z(rectangular):
    s = asymmetric(ny=5, nx=7, rectangular=rectangular).to_dict()
    s['grid'] = dict(ny=5, nx=7, dy=20e-6, dx=10e-6)
    s['components'][0] = (dict(id='aperture', kind='rectangular_aperture', z_m=0., width_m=20e-6, height_m=40e-6)
                            if rectangular else dict(id='aperture', kind='circular_aperture', z_m=0., radius_m=20e-6))
    e = SequentialExperiment.from_dict(s)
    with observe_complex() as fields:
        r = wf.sample_wave_field(e, interior_z_m=())
    before, after = fields[1], fields[2]
    mask = np.zeros((5, 7), bool)
    if rectangular:
        mask[1:4, 2:5] = True
    else:
        mask[1, 3] = mask[3, 3] = True
        mask[2, 1:6] = True
    np.testing.assert_array_equal(after, np.where(mask, before, 0))
    assert r.planes[1].z_m == r.planes[2].z_m == 0.
    assert r.planes[1].id != r.planes[2].id
    assert r.planes[2].delta_norm < 0
    assert r.planes[2].norm == pytest.approx(float(np.sum(abs(before[mask])**2))*20e-6*10e-6,
                                            rel=2e-14, abs=1e-29)


@pytest.mark.parametrize("focal", [.08, -.08])
def test_same_z_lens_changes_complex_phase_not_instantaneous_intensity(focal):
    e = gaussian_fixture(focal=focal, terminal=0.)
    with observe_complex() as fields:
        r = wf.sample_wave_field(e, interior_z_m=())
    before, after = fields[3:5]
    x, y = axes(e)
    expected = np.exp(-1j*math.pi*(x[None, :]**2+y[:, None]**2)/(e.wavelength_m*focal))
    np.testing.assert_allclose(after, before*expected, rtol=2e-14, atol=2e-14*np.max(abs(before)))
    assert relative_l2(after, before) > .05
    np.testing.assert_allclose(r.intensities[3], r.intensities[4], rtol=2e-14, atol=2e-14)
    assert r.planes[3].z_m == r.planes[4].z_m == 0
    assert r.planes[3].id != r.planes[4].id


def test_free_gaussian_full_complex_30_60_120mm_without_phase_fitting():
    spec = example(radius=.01).to_dict()
    spec['components'][0]['z_m'] = .14
    spec['components'][1]['z_m'] = .15
    e = SequentialExperiment.from_dict(spec)
    with observe_complex() as fields:
        r = wf.sample_wave_field(e, interior_z_m=(.03, .06, .12))
    for row, field in zip(r.planes, fields):
        if row.stage == 'interior':
            assert relative_l2(field, gaussian(e, row.z_m)) <= 1e-6


@pytest.mark.parametrize("focal", [.08, -.08])
def test_signed_lens_complete_complex_gaussian_reference(focal):
    e = gaussian_fixture(focal=focal)
    with observe_complex() as fields:
        r = wf.sample_wave_field(e, interior_z_m=(.02, .04, .08))
    for row, field in zip(r.planes, fields):
        if row.stage in ('interior', 'observation'):
            assert relative_l2(field, lens_gaussian(e, row.z_m)) <= 5e-5


def test_converging_lens_nondegenerate_focus_then_divergence():
    e = gaussian_fixture()
    w = e.source.waist_radius_m
    zr = math.pi*w*w/e.wavelength_m
    focal = e.components[1].focal_length_m
    focus = focal/(1+(focal/zr)**2)
    zs = (focus-.01, focus, focus+.01)
    with observe_complex() as fields:
        r = wf.sample_wave_field(e, interior_z_m=zs)
    radii = []
    for row, field in zip(r.planes, fields):
        if row.stage == 'interior':
            radius = second_moment_radius(field, e)
            expected = w*math.sqrt((1-row.z_m/focal)**2+(row.z_m/zr)**2)
            assert radius == pytest.approx(expected, rel=1e-4, abs=0)
            radii.append(radius)
    assert radii[1] < min(radii[0], radii[2])


def test_unchanged_terminal_and_default_sampling_convergence_under_one_percent():
    e = example()
    r = wf.sample_wave_field(e, interior_z_m=wf.default_interior_positions(e))
    plain = run_experiment(e)
    assert r.observation.data.tobytes() == plain.observation.data.tobytes()
    assert r.planes[-1].norm == plain.stages[-1].norm
    pitch = run_experiment(example(n=256, pitch=8e-6)).observation.intensity[::2, ::2]
    window = run_experiment(example(n=256, pitch=16e-6)).observation.intensity[64:192, 64:192]
    assert relative_l2(r.intensities[-1], pitch) <= .01
    assert relative_l2(r.intensities[-1], window) <= .01


def test_strong_clipping_retains_loss_and_informative_sampling_counterexample():
    e = example(radius=80e-6)
    r = wf.sample_wave_field(e, interior_z_m=wf.default_interior_positions(e))
    stages = {p.selector: p for p in r.canonical.stages}
    assert stages['after:aperture'].transmission_ratio < .5
    assert stages['after:aperture'].delta_norm < 0
    reference = run_experiment(example(n=256, pitch=8e-6, radius=80e-6)).observation.intensity[::2, ::2]
    assert relative_l2(r.intensities[-1], reference) > .01


def test_fabricated_endpoint_interpolation_and_gaussian_cone_are_not_sections():
    e = example(radius=80e-6)
    r = wf.sample_wave_field(e, interior_z_m=(.12,))
    index = next(i for i, p in enumerate(r.planes) if p.stage == 'interior')
    fraction = .12/e.observation.z_m
    fabricated = (1-fraction)*r.intensities[0]+fraction*r.intensities[-1]
    assert relative_l2(r.intensities[index], fabricated) > .1
    unperturbed = gaussian(e, .12)
    assert relative_l2(r.intensities[index], abs(unperturbed)**2) > .1


def test_evanescent_forward_samples_match_independent_complex_dft_and_keep_loss():
    s = asymmetric(ny=5, nx=6, rectangular=False).to_dict()
    wavelength = s['wavelength_m']
    s['grid'].update(dx=.2*wavelength, dy=.3*wavelength)
    s['source'].update(waist_radius_m=.4*wavelength, center_x_m=.07*wavelength,
                       center_y_m=-.09*wavelength)
    s['components'][0].update(z_m=.2*wavelength, radius_m=.6*wavelength)
    s['components'][1].update(z_m=.4*wavelength, focal_length_m=10*wavelength)
    s['observation']['z_m'] = .9*wavelength
    e = SequentialExperiment.from_dict(s)
    zs = (.1*wavelength, .3*wavelength, .7*wavelength)
    references = independent_sections(e, zs)
    with observe_complex() as fields:
        r = wf.sample_wave_field(e, interior_z_m=zs)
    for row, actual in zip(r.planes, fields):
        expected = references[row.id]
        np.testing.assert_allclose(actual, expected, rtol=2e-11, atol=2e-11)
    assert r.planes[-1].norm < r.planes[0].norm
    assert any(p.delta_norm < 0 for p in r.planes if p.stage == 'interior')
    # This intentionally subwavelength sample checks the discrete evanescent
    # policy, not physical validity of a paraxial Gaussian/lens approximation.
