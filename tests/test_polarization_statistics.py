"""Bounded public input/ownership/domain checks for optical second moments."""

from dataclasses import FrozenInstanceError
import math

import numpy as np
import pytest

from ohlab.optics.polarization_statistics import (
    PolarizationMeasurement, analyzer_intensity, coherency_from_samples, measure_coherency,
)


def samples():
    return np.array([[1+2j, .3-.4j], [.2+.7j, -.8+.1j]], dtype=np.complex128)


def test_owned_readonly_matrix_does_not_share_inputs():
    fields = samples()
    weights = np.array([.25, .75], dtype=np.float64)
    before_fields, before_weights = fields.copy(), weights.copy()
    result = coherency_from_samples(fields, probabilities=weights)
    np.testing.assert_array_equal(fields, before_fields)
    np.testing.assert_array_equal(weights, before_weights)
    assert result.coherency.dtype == np.complex128 and not result.coherency.flags.writeable
    assert not np.shares_memory(result.coherency, fields)
    direct = measure_coherency(result.coherency)
    assert not np.shares_memory(direct.coherency, result.coherency)
    fields[:] = 0
    weights[:] = 0
    assert result.stokes[0] > 0
    with pytest.raises(ValueError):
        result.coherency[0, 0] = 0
    with pytest.raises(FrozenInstanceError):
        result.stokes = (0, 0, 0, 0)


def test_exact_dark_and_nonzero_unpolarized_are_distinct():
    dark = coherency_from_samples(np.zeros((2, 2), dtype=np.complex128), probabilities=np.array([.5, .5]))
    assert dark.stokes == (0.0, 0.0, 0.0, -0.0)
    assert dark.degree_of_polarization is None
    assert dark.normalized_stokes is None and dark.polarized_direction is None
    mixed = measure_coherency(np.eye(2, dtype=np.complex128))
    assert mixed.stokes[0] == 2 and mixed.degree_of_polarization == 0
    assert mixed.normalized_stokes == (0, 0, 0) and mixed.polarized_direction is None
    assert analyzer_intensity(dark, axis_angle_rad=.2) == 0


@pytest.mark.parametrize("bad", [[], [[1, 0]], np.ones((1, 2), dtype=np.float64), np.ones((1, 2), dtype=np.complex64), np.ones((1, 2), dtype=">c16")])
def test_sample_type_and_dtype_errors(bad):
    with pytest.raises(TypeError, match="samples"):
        coherency_from_samples(bad, probabilities=np.array([1.0]))


@pytest.mark.parametrize("shape", [(0, 2), (257, 2), (2,), (1, 3), (2, 2, 2)])
def test_sample_shape_and_resource_errors(shape):
    with pytest.raises(ValueError, match="shape"):
        coherency_from_samples(np.zeros(shape, dtype=np.complex128), probabilities=np.array([1.0]))


def test_resource_limit_checked_before_copy_or_finite_product(monkeypatch):
    huge_view = np.broadcast_to(np.ones((1, 2), dtype=np.complex128), (1_000_000, 2))
    weights = np.broadcast_to(np.ones(1, dtype=np.float64), (1_000_000,))
    def forbidden(*args, **kwargs):
        raise AssertionError("copy/product reached before resource rejection")
    monkeypatch.setattr(np, "isfinite", forbidden)
    monkeypatch.setattr(np, "array", forbidden)
    with pytest.raises(ValueError, match="1<=M<=256"):
        coherency_from_samples(huge_view, probabilities=weights)


@pytest.mark.parametrize("weights,error", [([.5, .5], TypeError), (np.array([1, 0]), TypeError), (np.array([.5, .5], dtype=np.float32), TypeError), (np.array([[.5, .5]]), ValueError), (np.array([1.]), ValueError), (np.array([-.1, 1.1]), ValueError), (np.array([0., 0.]), ValueError), (np.array([.5, .49]), ValueError), (np.array([np.nan, .5]), ValueError), (np.array([np.inf, .5]), ValueError)])
def test_probability_contract(weights, error):
    with pytest.raises(error, match="probabilities"):
        coherency_from_samples(samples(), probabilities=weights)


def test_accepted_probability_roundoff_is_not_renormalized():
    weights = np.array([.5, .5 + 4*np.finfo(float).eps])
    fields = np.array([[1, 0], [1, 0]], dtype=np.complex128)
    result = coherency_from_samples(fields, probabilities=weights)
    assert result.stokes[0] == float(np.sum(weights))
    assert result.stokes[0] != 1.0


@pytest.mark.parametrize("position,value", [((0, 0), np.nan), ((1, 1), np.inf), ((0, 1), complex(0, np.inf))])
def test_nonfinite_samples_rejected(position, value):
    fields = samples()
    fields[position] = value
    with pytest.raises(ValueError, match="finite"):
        coherency_from_samples(fields, probabilities=np.array([.5, .5]))


@pytest.mark.parametrize("bad,error", [([[1, 0], [0, 1]], TypeError), (np.eye(2), TypeError), (np.eye(2, dtype=np.complex64), TypeError), (np.zeros((2, 3), dtype=np.complex128), ValueError), (np.array([[1, 2], [0, 1]], dtype=np.complex128), ValueError), (np.diag([1, -1]).astype(np.complex128), ValueError), (np.array([[np.inf, 0], [0, 1]], dtype=np.complex128), ValueError)])
def test_invalid_coherency_rejected(bad, error):
    with pytest.raises(error):
        measure_coherency(bad)


def test_scale_relative_domain_has_no_absolute_floor():
    matrix = np.diag([1e-100, -1e-110]).astype(np.complex128)
    with pytest.raises(ValueError, match="eigenvalue"):
        measure_coherency(matrix)


def test_near_domain_roundoff_retains_raw_matrix_eigenvalues_and_dop():
    eps = np.finfo(float).eps
    matrix = np.diag([1., -eps]).astype(np.complex128)
    result = measure_coherency(matrix)
    np.testing.assert_array_equal(result.coherency, matrix)
    assert result.eigenvalues[0] == -eps
    assert result.degree_of_polarization > 1.0
    assert result.roundoff_limited
    near_hermitian = np.array([[1+eps*1j, .1], [.1, 1]], dtype=np.complex128)
    near = measure_coherency(near_hermitian)
    np.testing.assert_array_equal(near.coherency, near_hermitian)
    assert near.roundoff_limited


def test_extreme_energy_domain_and_zero_weight_samples():
    with pytest.raises(ValueError, match="underflow"):
        coherency_from_samples(np.full((1, 2), 1e-200, dtype=np.complex128), probabilities=np.array([1.]))
    with pytest.raises(ValueError, match="overflow"):
        coherency_from_samples(np.full((1, 2), 1e200, dtype=np.complex128), probabilities=np.array([1.]))
    dark = coherency_from_samples(np.array([[1, 2], [0, 0]], dtype=np.complex128), probabilities=np.array([0., 1.]))
    assert dark.degree_of_polarization is None


@pytest.mark.parametrize("angle", [True, "0", np.array(.2), complex(1, 0), np.timedelta64(1)])
def test_analyzer_angle_types(angle):
    with pytest.raises(TypeError):
        analyzer_intensity(measure_coherency(np.eye(2, dtype=np.complex128)), axis_angle_rad=angle)


@pytest.mark.parametrize("angle", [math.inf, math.nan])
def test_analyzer_angle_values(angle):
    with pytest.raises(ValueError):
        analyzer_intensity(measure_coherency(np.eye(2, dtype=np.complex128)), axis_angle_rad=angle)


def test_local_numpy_error_policy_restored_on_success_and_failure():
    with np.errstate(over="ignore", invalid="warn", divide="ignore", under="raise"):
        before = np.geterr().copy()
        coherency_from_samples(samples(), probabilities=np.array([.5, .5]))
        assert np.geterr() == before
        with pytest.raises(ValueError):
            coherency_from_samples(np.full((1, 2), 1e200, dtype=np.complex128), probabilities=np.array([1.]))
        assert np.geterr() == before


def test_revalidated_tampered_stored_matrix_rejected_by_analyzer():
    measurement = measure_coherency(np.eye(2, dtype=np.complex128))
    measurement.coherency.setflags(write=True)
    measurement.coherency[0, 0] = -10
    with pytest.raises(ValueError):
        analyzer_intensity(measurement, axis_angle_rad=0)
