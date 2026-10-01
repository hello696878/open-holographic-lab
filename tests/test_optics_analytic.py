"""Independent discrete and sign-matched continuous V0 optical references."""
from __future__ import annotations

import math

import numpy as np
import pytest

from ohlab import ComplexField, SamplingGrid
from ohlab.optics import SequentialExperiment, apply_component, run_experiment, sample_source
from scripts.validate_v0_optics import (
    WAVELENGTH_M, asymmetric_train_spec, complex_l2, direct_dft_train,
    experiment_spec, gaussian_reference, lens_gaussian_reference, physical_mesh,
    sampled_norm, second_moment_radius,
)


@pytest.mark.parametrize("waist_z_m", [.003, 0.0, -.003])
def test_gaussian_source_independent_amplitude_curvature_gouy_carrier(waist_z_m: float) -> None:
    """Check before/at/after waist with nonzero center, amplitude and phase."""
    spec = experiment_spec(n=9, pitch_m=11e-6, observation_z_m=0)
    spec["grid"] = dict(ny=8, nx=9, dy=14e-6, dx=11e-6)
    spec["source"].update(amplitude=2.3, waist_radius_m=45e-6, waist_z_m=waist_z_m,
                          center_x_m=5e-6, center_y_m=-7e-6, phase_rad=.47)
    experiment = SequentialExperiment.from_dict(spec)
    expected = gaussian_reference(experiment.grid, wavelength_m=WAVELENGTH_M, z_m=0,
                                  **{k: v for k, v in spec["source"].items() if k != "kind"})
    actual = sample_source(experiment).data
    np.testing.assert_allclose(actual, expected, rtol=2e-11, atol=2e-11*np.max(np.abs(expected)))
    assert complex_l2(actual, expected) <= 2e-11


@pytest.mark.parametrize("ny,nx", [(5, 6), (6, 5)])
def test_complete_asymmetric_train_independent_direct_dft(ny: int, nx: int) -> None:
    """Reference constructs all coordinates, bins, H, masks and ordered updates."""
    experiment = SequentialExperiment.from_dict(asymmetric_train_spec(ny, nx))
    expected = direct_dft_train(experiment)
    result = run_experiment(experiment)
    actual = result.observation.data
    np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-10*np.max(np.abs(expected)))
    assert complex_l2(actual, expected) <= 1e-10
    assert result.stages[-1].norm == pytest.approx(sampled_norm(expected, experiment.grid),
                                                  rel=2e-10, abs=0)


def test_direct_reference_does_not_call_production_coordinate_or_numerical_helpers(monkeypatch) -> None:
    """The independent reference remains usable if production arrays are blocked."""
    experiment = SequentialExperiment.from_dict(asymmetric_train_spec())
    expected = direct_dft_train(experiment)

    def prohibited(*args, **kwargs):
        raise AssertionError("production array helper called by independent reference")

    monkeypatch.setattr(SamplingGrid, "meshgrid", prohibited)
    monkeypatch.setattr(SamplingGrid, "freq_meshgrid", prohibited)
    monkeypatch.setattr(np.fft, "fft2", prohibited)
    monkeypatch.setattr(np.fft, "ifft2", prohibited)
    monkeypatch.setattr(np.fft, "fftfreq", prohibited)
    np.testing.assert_array_equal(direct_dft_train(experiment), expected)


@pytest.mark.parametrize("focal", [.02, -.02])
def test_lens_phase_difference_signed_si_reference(focal: float) -> None:
    spec = experiment_spec(n=7, observation_z_m=0, focal_length_m=focal)
    spec["grid"] = dict(ny=5, nx=7, dy=20e-6, dx=10e-6)
    spec["source"] = dict(kind="uniform", amplitude=2.0, phase_rad=.31)
    experiment = SequentialExperiment.from_dict(spec)
    source = sample_source(experiment)
    output = apply_component(source, experiment.components[0])
    # Hand-indexed noncentral position (x=20um,y=-20um), not grid.meshgrid().
    expected_ratio = np.exp(-1j*2*math.pi/WAVELENGTH_M*((20e-6)**2+(-20e-6)**2)/(2*focal))
    np.testing.assert_allclose(output.data[1, 5]/output.data[2, 3], expected_ratio,
                               rtol=2e-14, atol=2e-14)
    np.testing.assert_allclose(np.abs(output.data)**2, np.abs(source.data)**2,
                               rtol=2e-14, atol=2e-14*4)


@pytest.mark.parametrize("focal", [None, .02, -.02])
def test_full_complex_gaussian_reference_not_width_only(focal: float | None) -> None:
    experiment = SequentialExperiment.from_dict(experiment_spec(focal_length_m=focal))
    actual = run_experiment(experiment).observation.data
    if focal is None:
        expected = gaussian_reference(experiment.grid, wavelength_m=WAVELENGTH_M, z_m=.02)
        tolerance = 1e-6
    else:
        expected = lens_gaussian_reference(experiment.grid, wavelength_m=WAVELENGTH_M,
                                            z_m=.02, focal_length_m=focal)
        tolerance = 5e-5
    # Absolute complex fields, including carrier/Gouy/prefactor; no fit/alignment.
    assert complex_l2(actual, expected) <= tolerance


@pytest.mark.parametrize("waist_z", [.001, -.001])
def test_lens_reference_phase_continuity_for_nonwaist_input(waist_z: float) -> None:
    spec = experiment_spec(n=17, pitch_m=7e-6, focal_length_m=-.02, observation_z_m=0)
    spec["source"].update(waist_z_m=waist_z, phase_rad=.37, amplitude=1.8)
    experiment = SequentialExperiment.from_dict(spec)
    expected = lens_gaussian_reference(experiment.grid, wavelength_m=WAVELENGTH_M,
                                        z_m=0, focal_length_m=-.02,
                                        waist_z_m=waist_z, phase_rad=.37, amplitude=1.8)
    actual = run_experiment(experiment).observation.data
    np.testing.assert_allclose(actual, expected, rtol=2e-11,
                               atol=2e-11*np.max(np.abs(expected)))


def test_lens_at_waist_minimum_and_neighboring_planes() -> None:
    w0, focal = 100e-6, .02
    zr = math.pi*w0*w0/WAVELENGTH_M
    minimum_z = focal/(1+(focal/zr)**2)
    assert minimum_z == pytest.approx(.017205882758087546, rel=1e-10, abs=1e-12)
    radii = []
    for z in (minimum_z-.001, minimum_z, minimum_z+.001, focal):
        experiment = SequentialExperiment.from_dict(experiment_spec(focal_length_m=focal,
                                                                     observation_z_m=z))
        result = run_experiment(experiment)
        radius = second_moment_radius(result.observation.data, experiment.grid)
        expected_radius = w0*math.sqrt((1-z/focal)**2+(z/zr)**2)
        assert radius == pytest.approx(expected_radius, rel=1e-4, abs=0)
        reference = lens_gaussian_reference(experiment.grid, wavelength_m=WAVELENGTH_M,
                                             z_m=z, focal_length_m=focal)
        assert complex_l2(result.observation.data, reference) <= 5e-5
        radii.append(radius)
    assert radii[1] < min(radii[0], radii[2], radii[3])


def test_analytic_aperture_norm_loss_and_blocked_field() -> None:
    spec = experiment_spec(n=7, pitch_m=10e-6, observation_z_m=0,
                           aperture_radius_m=20e-6)
    spec["grid"] = dict(ny=5, nx=7, dy=20e-6, dx=10e-6)
    spec["source"] = dict(kind="uniform", amplitude=2.0, phase_rad=.31)
    experiment = SequentialExperiment.from_dict(spec)
    source = sample_source(experiment)
    aperture = experiment.components[0]
    result = apply_component(source, aperture)
    assert sampled_norm(source.data, experiment.grid) == pytest.approx(35*4*2e-10, rel=2e-14, abs=0)
    assert sampled_norm(result.data, experiment.grid) == pytest.approx(7*4*2e-10, rel=2e-14, abs=0)
    expected_mask = np.zeros((5, 7), dtype=bool)
    expected_mask[1, 3] = expected_mask[3, 3] = True
    expected_mask[2, 1:6] = True
    np.testing.assert_array_equal(result.data != 0, expected_mask)
    blocked = ComplexField(data=np.where(expected_mask, 0, 2+1j),
                            grid=experiment.grid, wavelength_m=WAVELENGTH_M)
    np.testing.assert_array_equal(apply_component(blocked, aperture).data,
                                   np.zeros(experiment.grid.shape, dtype=np.complex128))


def test_zero_uniform_forward_field_has_no_fabricated_transmission_ratio() -> None:
    spec = experiment_spec(n=9, aperture_radius_m=20e-6, focal_length_m=.02)
    spec["source"] = dict(kind="uniform", amplitude=0.0, phase_rad=.31)
    experiment = SequentialExperiment.from_dict(spec)
    result = run_experiment(experiment)
    np.testing.assert_array_equal(result.observation.data, np.zeros(experiment.grid.shape, dtype=np.complex128))
    assert all(stage.norm == 0 for stage in result.stages)
    assert all(stage.transmission_ratio is None for stage in result.stages)
