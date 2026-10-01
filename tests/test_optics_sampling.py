"""Bounded physical sampling evidence, separate from floating-point identities."""
from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.integrate import quad

from ohlab.optics import SequentialExperiment, run_experiment, sample_source
from scripts.validate_v0_optics import (
    WAVELENGTH_M, complex_l2, experiment_spec, fixed_roi,
    gaussian_reference, lens_gaussian_reference, rectangular_fresnel_reference,
    sampling_diagnostics,
)


def test_gaussian_refinement_preserves_fixed_physical_experiment_and_floor() -> None:
    measured = []
    for n, pitch in ((256, 4e-6), (512, 2e-6), (512, 4e-6)):
        experiment = SequentialExperiment.from_dict(experiment_spec(n=n, pitch_m=pitch))
        expected = gaussian_reference(experiment.grid, wavelength_m=WAVELENGTH_M, z_m=.02)
        measured.append(complex_l2(run_experiment(experiment).observation.data, expected))
    assert all(error <= 1e-6 for error in measured)
    # Exact ASM versus paraxial Gaussian has a nonzero approximation floor.
    assert all(error > 1e-8 for error in measured)


def test_diverging_gaussian_enlargement_exposes_small_window_error() -> None:
    errors = []
    for n in (256, 512):
        experiment = SequentialExperiment.from_dict(experiment_spec(n=n, focal_length_m=-.02))
        expected = lens_gaussian_reference(experiment.grid, wavelength_m=WAVELENGTH_M,
                                            z_m=.02, focal_length_m=-.02)
        errors.append(complex_l2(run_experiment(experiment).observation.data, expected))
    assert errors[0] > 5e-5
    assert errors[1] <= 5e-5
    assert errors[1] < errors[0]/10


def test_continuous_rectangle_reference_is_not_resized_to_sampled_area() -> None:
    errors = []
    areas = []
    for n, pitch in ((512, 4e-6), (1024, 2e-6)):
        spec = experiment_spec(n=n, pitch_m=pitch, observation_z_m=.005)
        spec["source"] = dict(kind="uniform", amplitude=1., phase_rad=0.)
        spec["components"] = [dict(id="slit", kind="rectangular_aperture", z_m=0.,
                                   width_m=80e-6, height_m=120e-6)]
        experiment = SequentialExperiment.from_dict(spec)
        result = run_experiment(experiment)
        reference = rectangular_fresnel_reference(experiment.grid, wavelength_m=WAVELENGTH_M,
                                                    z_m=.005, width_m=80e-6, height_m=120e-6)
        errors.append(complex_l2(result.observation.data, reference, fixed_roi(experiment.grid)))
        areas.append(result.stages[2].norm)
    assert errors[0] > .035 and errors[1] > .035  # Deliberately inadequate coarse cases.
    assert errors[1] < errors[0]*.6
    assert areas[0] > areas[1] > 80e-6*120e-6
    # Required 2048²/1-µm case is executed by the explicit --full validation.


def test_diagnostics_keep_distinct_sampling_mechanisms_and_no_phase_unwrap(monkeypatch) -> None:
    experiment = SequentialExperiment.from_dict(experiment_spec(focal_length_m=.02))
    source = sample_source(experiment)

    def forbidden(*args, **kwargs):
        raise AssertionError("wrapped angle/unwrap cannot establish lens/transfer sampling")

    monkeypatch.setattr(np, "unwrap", forbidden)
    monkeypatch.setattr(np, "angle", forbidden)
    report = sampling_diagnostics(experiment, source.data)
    np.testing.assert_allclose(report["source_radius_samples_xy"], [25., 25.], rtol=2e-14, atol=0)
    assert report["continuous_gaussian_fraction_outside_source_rectangle"] >= 0
    assert report["lens_phase_sampling"][0]["max_analytic_adjacent_phase_rad_xy"][0] > 0
    assert report["transfer_phase_sampling"][-1]["max_occupied_phase_increment_xy"][0] > 0
    assert report["source_evanescent_spectral_norm_fraction"] == 0
    assert "do not prove" in report["limitations"]


def test_dark_source_diagnostics_use_undefined_fractions() -> None:
    spec = experiment_spec(n=9)
    spec["source"] = dict(kind="uniform", amplitude=0., phase_rad=0.)
    experiment = SequentialExperiment.from_dict(spec)
    report = sampling_diagnostics(experiment, sample_source(experiment).data)
    assert report["source_outer_five_percent_norm_fraction"] is None
    assert report["source_evanescent_spectral_norm_fraction"] is None
    assert report["occupied_bin_fraction"] == 0


def test_analytic_gaussian_outside_window_retains_small_nonzero_tail() -> None:
    """Independent scaled quadrature detects subtract-from-one cancellation."""
    experiment = SequentialExperiment.from_dict(experiment_spec())
    actual = sampling_diagnostics(experiment, sample_source(experiment).data)[
        "continuous_gaussian_fraction_outside_source_rectangle"]

    def one_sided_tail(boundary_m: float) -> float:
        lower = math.sqrt(2)*boundary_m/100e-6
        # Factor the tiny exp(-lower²) out of the integral; integrate the
        # remaining O(1/lower) quantity independently of scipy.special.erfc.
        integral, _ = quad(lambda t: math.exp(-2*lower*t-t*t), 0, math.inf,
                           epsabs=1e-14, epsrel=1e-13)
        return math.exp(-lower*lower)/math.sqrt(math.pi)*integral

    # Source sample cells have actual edges -1026 and +1022 micrometres.
    axis_tail = one_sided_tail(1026e-6) + one_sided_tail(1022e-6)
    independent = 2*axis_tail - axis_tail*axis_tail
    assert actual > 0
    assert actual == pytest.approx(independent, rel=2e-13, abs=0)
    assert actual == pytest.approx(8.801041976094034e-93, rel=2e-13, abs=0)
