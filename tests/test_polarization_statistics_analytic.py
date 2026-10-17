"""Independent hand/expanded-scalar references for declared ensemble optics."""

import math

import numpy as np
import pytest

from ohlab import ComplexField, SamplingGrid
from ohlab.optics.polarization import JonesField, apply_linear_polarizer, apply_linear_retarder
from ohlab.optics.polarization_statistics import analyzer_intensity, coherency_from_samples, measure_coherency

RTOL, ATOL = 2e-13, 2e-13


@pytest.mark.parametrize("state,expected", [([1, 0], [1, 1, 0, 0]), ([0, 1], [1, -1, 0, 0]), ([1, 1], [2, 0, 2, 0]), ([1, 1j], [2, 0, 0, 2])])
def test_hand_constant_pure_state(state, expected):
    values = np.array([state, state], dtype=np.complex128)
    result = coherency_from_samples(values, probabilities=np.array([.5, .5]))
    np.testing.assert_allclose(result.stokes, expected, rtol=RTOL, atol=ATOL*expected[0])
    assert result.degree_of_polarization == pytest.approx(1, rel=RTOL, abs=ATOL)
    np.testing.assert_allclose(result.eigenvalues, [0, expected[0]], rtol=RTOL, atol=ATOL*expected[0])


def test_equal_orthogonal_mixture_is_not_coherent_mean_or_centered_covariance():
    values = np.array([[1, 0], [0, 1]], dtype=np.complex128)
    result = coherency_from_samples(values, probabilities=np.array([.5, .5]))
    np.testing.assert_array_equal(result.coherency, np.diag([.5, .5]))
    assert result.stokes == (1, 0, 0, 0) and result.degree_of_polarization == 0
    # Wrong field mean gives [[.25,.25],[.25,.25]], a pure half-power field.
    coherent_mean = np.array([[.25, .25], [.25, .25]], dtype=np.complex128)
    assert not np.array_equal(result.coherency, coherent_mean)
    constant = coherency_from_samples(np.ones((2, 2), dtype=np.complex128), probabilities=np.array([.5, .5]))
    # Centering identical Jones states would erase their nonzero optical power.
    assert constant.stokes[0] == 2 and constant.degree_of_polarization == 1


def test_unequal_hand_mixture_eigenvalues_and_no_M_minus_one():
    result = coherency_from_samples(np.array([[2, 0], [0, 2]], dtype=np.complex128), probabilities=np.array([.75, .25]))
    np.testing.assert_array_equal(result.coherency, np.diag([3., 1.]))
    assert result.stokes == (4, 2, 0, 0)
    assert result.eigenvalues == (1., 3.)
    assert result.degree_of_polarization == .5
    assert result.normalized_stokes == (.5, 0, 0)
    assert result.polarized_direction == (1, 0, 0)


def test_common_phase_invariance_without_individual_normalization():
    fields = np.array([[2+.3j, -.8+.5j], [.1-1.2j, 3j]], dtype=np.complex128)
    weights = np.array([.3, .7])
    before = coherency_from_samples(fields, probabilities=weights)
    after = coherency_from_samples(fields*np.exp(.73j), probabilities=weights)
    np.testing.assert_allclose(after.coherency, before.coherency, rtol=2e-14, atol=2e-14*before.stokes[0])


@pytest.mark.parametrize("theta", [0, .2, math.pi/4, math.pi/2, -.73])
def test_analyzer_matches_independent_per_sample_projection(theta):
    values = np.array([[1+2j, -.3+.8j], [2-.2j, .9-1.5j], [-.2j, .4]], dtype=np.complex128)
    probabilities = np.array([.2, .3, .5])
    expected = sum(float(p)*abs(math.cos(theta)*complex(x)+math.sin(theta)*complex(y))**2 for p, (x, y) in zip(probabilities, values))
    actual = analyzer_intensity(coherency_from_samples(values, probabilities=probabilities), axis_angle_rad=theta)
    np.testing.assert_allclose(actual, expected, rtol=RTOL, atol=ATOL*expected)


def test_signed_imaginary_offdiagonal_and_circular_convention():
    result = measure_coherency(np.array([[.5, -.5j], [.5j, .5]], dtype=np.complex128))
    assert result.stokes == (1, 0, 0, 1)
    assert result.normalized_stokes == (0, 0, 1)
    conjugate = measure_coherency(np.array([[.5, .5j], [-.5j, .5]], dtype=np.complex128))
    assert conjugate.stokes == (1, 0, 0, -1)


@pytest.mark.parametrize("theta,delta", [(0, math.pi/2), (.37, math.pi/2), (-.61, math.pi), (.2, -.83)])
def test_public_jones_retarder_and_polarizer_invariants(theta, delta):
    # This is a genuine test-only spatial fixture, not a grid for the product's
    # statistical sample list. Its explicit SI area is not used in the mean C.
    grid = SamplingGrid(ny=2, nx=3, dy=5e-6, dx=4e-6)
    values = np.array([[1+.2j, -.3+.4j], [.4-.6j, .8+.7j], [.2j, 2], [1, 1j], [.8, .2], [-.1j, .3j]], dtype=np.complex128)
    field = JonesField(
        x=ComplexField(data=values[:, 0].reshape(grid.shape), grid=grid, wavelength_m=633e-9),
        y=ComplexField(data=values[:, 1].reshape(grid.shape), grid=grid, wavelength_m=633e-9),
    )
    probabilities = np.full(6, 1/6)
    source = coherency_from_samples(values, probabilities=probabilities)
    retarded = apply_linear_retarder(field, axis_angle_rad=theta, retardance_rad=delta)
    out = np.column_stack((retarded.x.data.ravel(), retarded.y.data.ravel()))
    measured = coherency_from_samples(out, probabilities=probabilities)
    np.testing.assert_allclose(measured.eigenvalues, source.eigenvalues, rtol=RTOL, atol=ATOL*source.stokes[0])
    np.testing.assert_allclose(measured.stokes[0], source.stokes[0], rtol=RTOL, atol=ATOL*source.stokes[0])
    np.testing.assert_allclose(measured.degree_of_polarization, source.degree_of_polarization, rtol=RTOL, atol=ATOL)
    projected = apply_linear_polarizer(field, axis_angle_rad=theta)
    direct_mean = sum(abs(complex(x))**2 + abs(complex(y))**2 for x, y in zip(projected.x.data.ravel(), projected.y.data.ravel()))/6
    np.testing.assert_allclose(analyzer_intensity(source, axis_angle_rad=theta), direct_mean, rtol=RTOL, atol=ATOL*source.stokes[0])
    assert direct_mean < source.stokes[0]


def test_uniform_test_only_finite_population_squared_dop_expectation():
    # Predeclared fixed seed/512 realizations/M16, not a product distribution.
    # Var(DoP_M²)=(M-1)/M³ for iid uniform phases. The 6 standard-error bound
    # constrains this fixed test sample; no seed search, retry or per-seed claim.
    count, m = 512, 16
    rng = np.random.default_rng(np.random.PCG64(1742026))
    measured = []
    for _ in range(count):
        phase = rng.uniform(0, 2*math.pi, m)
        values = np.column_stack((np.ones(m), np.exp(1j*phase)))/math.sqrt(2)
        result = coherency_from_samples(values, probabilities=np.full(m, 1/m))
        measured.append(result.degree_of_polarization**2)
    tolerance = 6*math.sqrt((m-1)/(m**3*count))
    assert abs(float(np.mean(measured))-1/m) <= tolerance
