"""Independent source phase/amplitude references and thin-element actions."""

from dataclasses import replace
import math

import numpy as np
import pytest

from ohlab import ComplexField, SamplingGrid
from ohlab.optics import (CircularAperture, GaussianSource, ObservationPlane,
                         RectangularAperture, SequentialExperiment, ThinLens,
                         UniformSource, apply_component, sample_source)


def experiment(source, *, grid=None):
    return SequentialExperiment(wavelength_m=633e-9,
                                grid=grid or SamplingGrid(ny=5, nx=7, dy=20e-6, dx=10e-6),
                                source=source, components=(),
                                observation=ObservationPlane(id="detector", z_m=0))


@pytest.mark.parametrize("waist_z", [-0.02, 0.0, 0.02])
def test_gaussian_source_before_at_after_waist_independent_curvature_gouy_reference(waist_z):
    source = GaussianSource(amplitude=2.3, phase_rad=0.73, waist_radius_m=70e-6,
                            waist_z_m=waist_z, center_x_m=13e-6, center_y_m=-17e-6)
    actual = sample_source(experiment(source))
    # Independently write amplitude, curvature, Gouy and carrier terms; avoid
    # the production complex b expression and production coordinate arrays.
    s = -waist_z
    rayleigh = math.pi * (70e-6)**2 / 633e-9
    width = 70e-6 * math.sqrt(1 + (s / rayleigh)**2)
    expected = np.empty((5, 7), dtype=np.complex128)
    for row in range(5):
        for column in range(7):
            radius2 = ((column - 3)*10e-6 - 13e-6)**2 + ((row - 2)*20e-6 + 17e-6)**2
            amplitude = 2.3 * 70e-6 / width * math.exp(-radius2 / width**2)
            curvature_phase = (2*math.pi/633e-9) * radius2 * s / (2*(s*s + rayleigh*rayleigh))
            phase = (2*math.pi/633e-9)*s + 0.73 - math.atan(s/rayleigh) + curvature_phase
            expected[row, column] = amplitude * complex(math.cos(phase), math.sin(phase))
    # Carrier phase evaluation reaches ~2e5 rad; independent operation order
    # adds ~3e-11 absolute discrepancies, rather than a physical model floor.
    np.testing.assert_allclose(actual.data, expected, rtol=1e-10, atol=1e-10*2.3)


def test_waist_radius_is_1e_amplitude_and_1e2_intensity_without_normalization():
    source = GaussianSource(amplitude=2, phase_rad=0.4, waist_radius_m=20e-6,
                            waist_z_m=0, center_x_m=0, center_y_m=0)
    actual = sample_source(experiment(source))
    np.testing.assert_allclose(actual.amplitude[2, 3], 2, rtol=2e-15, atol=0)
    np.testing.assert_allclose(actual.amplitude[2, 5], 2/math.e, rtol=2e-15, atol=0)
    np.testing.assert_allclose(actual.intensity[2, 5], 4/math.e**2, rtol=3e-15, atol=0)


def test_uniform_source_amplitude_phase_periodic_window_and_owned_storage():
    actual = sample_source(experiment(UniformSource(amplitude=2, phase_rad=0.4)))
    expected = 2 * complex(math.cos(0.4), math.sin(0.4))
    np.testing.assert_allclose(actual.data, np.full((5, 7), expected), rtol=2e-15, atol=0)
    np.testing.assert_allclose(actual.intensity, np.full((5, 7), 4), rtol=2e-15, atol=0)
    assert actual.grid.shape == (5, 7)
    assert not actual.data.flags.writeable
    with pytest.raises(ValueError):
        actual.data.setflags(write=True)
    returned_intensity = actual.intensity
    returned_intensity[:] = 99
    assert actual.intensity.max() < 5


def test_anisotropic_circle_inclusive_physical_boundary_hand_mask():
    field = sample_source(experiment(UniformSource(amplitude=2, phase_rad=0)))
    result = apply_component(field, CircularAperture(id="stop", z_m=0, radius_m=20e-6))
    expected = np.array([[0, 0, 0, 0, 0, 0, 0],
                         [0, 0, 0, 1, 0, 0, 0],
                         [0, 1, 1, 1, 1, 1, 0],
                         [0, 0, 0, 1, 0, 0, 0],
                         [0, 0, 0, 0, 0, 0, 0]], dtype=bool)
    np.testing.assert_array_equal(result.data, 2*expected)
    np.testing.assert_allclose(field.power, 2.8e-8, rtol=2e-14, atol=0)
    np.testing.assert_allclose(result.power, 5.6e-9, rtol=2e-14, atol=0)
    assert not result.data.flags.writeable
    with pytest.raises(ValueError):
        result.data.setflags(write=True)


def test_rectangle_is_finite_height_slit_with_inclusive_boundaries():
    field = sample_source(experiment(UniformSource(amplitude=1, phase_rad=0)))
    actual = apply_component(field, RectangularAperture(id="slit", z_m=0, width_m=20e-6, height_m=40e-6))
    expected = np.zeros((5, 7), dtype=np.complex128)
    expected[1:4, 2:5] = 1
    np.testing.assert_array_equal(actual.data, expected)
    assert actual.intensity[0].sum() == 0  # no infinite-height slit assumption


@pytest.mark.parametrize("focal", [-0.02, 0.02])
def test_signed_lens_complex_phase_and_intensity_preservation(focal):
    field = sample_source(experiment(UniformSource(amplitude=2, phase_rad=0.4)))
    actual = apply_component(field, ThinLens(id="lens", z_m=0.01, focal_length_m=focal))
    for row, column in [(2, 3), (1, 5), (4, 0)]:
        x = (column-3)*10e-6
        y = (row-2)*20e-6
        phase = 0.4 - math.pi*(x*x+y*y)/(633e-9*focal)
        reference = 2*complex(math.cos(phase), math.sin(phase))
        np.testing.assert_allclose(actual.data[row, column], reference, rtol=2e-14, atol=4e-14)
    np.testing.assert_allclose(actual.intensity, field.intensity, rtol=2e-14, atol=8e-14)
    np.testing.assert_allclose(actual.power, field.power, rtol=2e-14, atol=0)
    np.testing.assert_allclose(actual.data[2, 3], field.data[2, 3], rtol=2e-15, atol=0)


@pytest.mark.parametrize("component", [CircularAperture(id="a", z_m=0, radius_m=20e-6),
                                     RectangularAperture(id="r", z_m=0, width_m=20e-6, height_m=40e-6),
                                     ThinLens(id="l", z_m=0, focal_length_m=0.02)])
def test_standalone_action_independent_of_z_and_preserves_input(component):
    field = sample_source(experiment(UniformSource(amplitude=2, phase_rad=0.4)))
    before = field.data.tobytes()
    near = apply_component(field, component)
    distant = apply_component(field, replace(component, z_m=0.7))
    np.testing.assert_array_equal(near.data, distant.data)
    assert field.data.tobytes() == before
    assert near.grid == field.grid and near.wavelength_m == field.wavelength_m
    assert not np.shares_memory(near.data, field.data)


def test_fully_blocked_supported_field_and_dark_sources_are_valid():
    grid = SamplingGrid(ny=5, nx=7, dy=20e-6, dx=10e-6)
    outside = np.zeros(grid.shape, dtype=np.complex128)
    outside[0, 0] = 2+3j
    field = ComplexField(data=outside, grid=grid, wavelength_m=633e-9)
    result = apply_component(field, CircularAperture(id="stop", z_m=0, radius_m=20e-6))
    np.testing.assert_array_equal(result.data, np.zeros(grid.shape))
    for source in [UniformSource(amplitude=0, phase_rad=0.4),
                   GaussianSource(amplitude=0, phase_rad=0.4, waist_radius_m=100e-6,
                                  waist_z_m=0.02, center_x_m=13e-6, center_y_m=-17e-6)]:
        sampled = sample_source(experiment(source))
        np.testing.assert_array_equal(sampled.data, np.zeros(grid.shape))
        np.testing.assert_array_equal(apply_component(sampled, ThinLens(id="l", z_m=0,
                                                                       focal_length_m=-0.02)).data,
                                      np.zeros(grid.shape))


def test_gaussian_tail_underflow_is_local_and_keeps_caller_settings():
    source = GaussianSource(amplitude=1, phase_rad=0.4, waist_radius_m=1e-6,
                            waist_z_m=0, center_x_m=0, center_y_m=0)
    with np.errstate(all="raise"):
        before = np.geterr().copy()
        field = sample_source(experiment(source))
        assert np.geterr() == before
    assert field.data[0, 0] == 0
    assert field.intensity[2, 3] > 0.99


def test_all_window_samples_can_be_zero_decaying_tails_not_invalid_prefactor():
    source = GaussianSource(amplitude=1, phase_rad=0.4, waist_radius_m=1e-6,
                            waist_z_m=0, center_x_m=1, center_y_m=1)
    field = sample_source(experiment(source))
    np.testing.assert_array_equal(field.data, np.zeros((5, 7)))
    assert field.data.dtype == np.complex128


def test_nonzero_source_prefactor_underflow_is_not_tail_decay():
    source = GaussianSource(amplitude=5e-324, phase_rad=0.4, waist_radius_m=1e-6,
                            waist_z_m=0.2, center_x_m=0, center_y_m=0)
    with pytest.raises(ValueError, match="prefactor.*underflowed"):
        experiment(source)


def test_bounded_transmission_product_underflow_is_local():
    grid = SamplingGrid(ny=3, nx=4, dy=2e-6, dx=3e-6)
    field = ComplexField(data=np.full(grid.shape, 1e-310+1e-310j), grid=grid, wavelength_m=633e-9)
    with np.errstate(all="raise"):
        before = np.geterr().copy()
        actual = apply_component(field, ThinLens(id="lens", z_m=0, focal_length_m=0.02))
        assert np.geterr() == before
    assert np.isfinite(actual.data).all()


def test_dark_field_does_not_bypass_invalid_lens_derived_geometry():
    field = sample_source(experiment(UniformSource(amplitude=0, phase_rad=0)))
    with pytest.raises(ValueError, match="derived geometry"):
        apply_component(field, ThinLens(id="lens", z_m=0, focal_length_m=5e-324))


def test_public_kind_errors():
    with pytest.raises(TypeError, match="experiment"):
        sample_source({})
    with pytest.raises(TypeError, match="field"):
        apply_component(np.zeros((2, 2)), ThinLens(id="l", z_m=0, focal_length_m=0.02))
    field = sample_source(experiment(UniformSource(amplitude=1, phase_rad=0)))
    with pytest.raises(TypeError, match="component"):
        apply_component(field, ObservationPlane(id="o", z_m=0))
