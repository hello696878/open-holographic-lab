"""V2c Jones representation, diagnostic definitions and defensive ownership."""

from dataclasses import FrozenInstanceError
import math

import numpy as np
import pytest

from ohlab import ComplexField, SamplingGrid
from ohlab.optics.polarization import (
    JonesField,
    apply_linear_polarizer,
    apply_linear_retarder,
    transmission_ratio,
)


def scalar(data=1.0, *, grid=None, wavelength=633e-9):
    if grid is None:
        grid = SamplingGrid(ny=2, nx=3, dy=5e-6, dx=4e-6)
    values = np.asarray(data, dtype=np.complex128)
    if values.ndim == 0:
        values = np.full(grid.shape, values, dtype=np.complex128)
    return ComplexField(data=values, grid=grid, wavelength_m=wavelength)


def jones(x=1.0, y=0.0, *, grid=None, wavelength=633e-9):
    first = scalar(x, grid=grid, wavelength=wavelength)
    second = scalar(y, grid=first.grid, wavelength=wavelength)
    return JonesField(x=first, y=second)


def test_jones_keyword_only_frozen_identity_equality_and_metadata():
    source = scalar()
    value = JonesField(x=source, y=source)
    duplicate = JonesField(x=source, y=source)
    assert value != duplicate
    assert value == value
    assert value.grid == source.grid
    assert value.shape == source.shape
    assert value.wavelength_m == source.wavelength_m
    assert JonesField.__dataclass_params__.eq is False
    assert JonesField.__dataclass_params__.frozen is True
    with pytest.raises(TypeError):
        JonesField(source, source)
    with pytest.raises(FrozenInstanceError):
        value.x = source


def test_same_object_components_are_independently_snapshotted():
    data = np.array([[1+2j, -3+0.5j, 0j], [4-2j, 7j, 0.2-0.3j]])
    source = scalar(data)
    value = JonesField(x=source, y=source)
    saved = data.tobytes()
    for component in (value.x, value.y):
        assert component is not source
        assert component.data.dtype == np.dtype(np.complex128)
        assert component.data.dtype.isnative
        assert component.data.flags.owndata
        assert not component.data.flags.writeable
        assert component.data.tobytes() == saved
        assert not np.shares_memory(component.data, source.data)
        assert not np.shares_memory(component.data, data)
    assert not np.shares_memory(value.x.data, value.y.data)
    # Existing public ndarray semantics allow a caller to reopen its own field.
    # The Jones snapshots must remain unchanged; no stronger locking is claimed.
    source.data.setflags(write=True)
    source.data[:] = 17-2j
    data[:] = -9
    assert value.x.data.tobytes() == saved
    assert value.y.data.tobytes() == saved
    with pytest.raises(ValueError):
        value.x.data[0, 0] = 1


def test_total_intensity_sums_orthogonal_component_intensities():
    value = jones(1, 1)
    np.testing.assert_array_equal(value.intensity, np.full(value.shape, 2.0))
    quadrature = jones(1, 1j)
    np.testing.assert_array_equal(quadrature.intensity, np.full(value.shape, 2.0))
    assert value.sampled_norm == float(
        np.sum(np.full(value.shape, 2.0), dtype=np.float64)
        * value.grid.dx * value.grid.dy
    )


def test_asymmetric_spatial_intensity_and_norm_have_independent_reference():
    x = np.array([[1+2j, -0.3+0.7j, 0j], [4-0.2j, -2-1j, 1e-7+3e-8j]])
    y = np.array([[0.4-0.1j, 2+3j, 0j], [-0.7+1j, 0.6+0.8j, -3e-8+4e-8j]])
    value = jones(x, y)
    expected = np.empty(x.shape, dtype=np.float64)
    for index in np.ndindex(x.shape):
        a, b = complex(x[index]), complex(y[index])
        expected[index] = a.real*a.real + a.imag*a.imag + b.real*b.real + b.imag*b.imag
    np.testing.assert_allclose(value.intensity, expected, rtol=2e-13, atol=2e-13*float(np.max(expected)))
    expected_norm = math.fsum(float(v) for v in expected.flat) * value.grid.dx * value.grid.dy
    np.testing.assert_allclose(value.sampled_norm, expected_norm, rtol=2e-13, atol=2e-13*expected_norm)


def test_derived_intensity_is_fresh_native_float64_and_does_not_mutate_storage():
    value = jones(1+2j, 3-4j)
    before = (value.x.data.tobytes(), value.y.data.tobytes())
    first, second = value.intensity, value.intensity
    assert first.dtype == np.dtype(np.float64)
    assert first.dtype.isnative
    assert not np.shares_memory(first, second)
    assert not np.shares_memory(first, value.x.data)
    assert not np.shares_memory(first, value.y.data)
    first[:] = -1
    np.testing.assert_array_equal(second, np.full(value.shape, 30.0))
    assert before == (value.x.data.tobytes(), value.y.data.tobytes())


def test_from_scalar_preserves_arbitrary_common_and_relative_phase():
    source = scalar(np.array([[1+2j, -0.3+0.7j, 0j], [4-0.2j, -2-1j, 1e-7+3e-8j]]))
    before = source.data.tobytes()
    cx, cy = 2+3j, -0.4+0.8j
    actual = JonesField.from_scalar(source, x_coefficient=cx, y_coefficient=cy)
    np.testing.assert_allclose(actual.x.data, cx*source.data, rtol=2e-14, atol=2e-14*float(np.max(np.abs(source.data))))
    np.testing.assert_allclose(actual.y.data, cy*source.data, rtol=2e-14, atol=2e-14*float(np.max(np.abs(source.data))))
    factor = abs(cx)**2 + abs(cy)**2
    scalar_norm = float(np.sum(np.abs(source.data)**2, dtype=np.float64)*source.grid.dx*source.grid.dy)
    np.testing.assert_allclose(actual.sampled_norm, factor*scalar_norm, rtol=2e-13, atol=2e-13*factor*scalar_norm)
    assert source.data.tobytes() == before
    assert not np.shares_memory(actual.x.data, source.data)
    assert not np.shares_memory(actual.y.data, source.data)
    assert not np.shares_memory(actual.x.data, actual.y.data)


@pytest.mark.parametrize("coefficient", [0, -2, 0.25, 1+2j, np.int8(-1), np.uint64(2),
                                        np.float16(0.5), np.float64(-0.25), np.longdouble(0.75),
                                        np.complex64(1+2j), np.complex128(-1j), np.clongdouble(0.5j)])
def test_supported_python_and_numpy_scalar_coefficients(coefficient):
    value = JonesField.from_scalar(scalar(), x_coefficient=coefficient, y_coefficient=0)
    np.testing.assert_array_equal(value.x.data, np.full(value.shape, complex(coefficient), dtype=np.complex128))
    np.testing.assert_array_equal(value.y.data, np.zeros(value.shape, dtype=np.complex128))


@pytest.mark.parametrize("name", ["x_coefficient", "y_coefficient"])
@pytest.mark.parametrize("coefficient", [True, np.bool_(False), "1", np.array(1),
                                        np.array([1]), None, np.datetime64("2026-01-01"), np.timedelta64(1, "s")])
def test_coefficient_kind_errors_do_not_disappear_on_dark_scalar(name, coefficient):
    params = dict(x_coefficient=0, y_coefficient=0)
    params[name] = coefficient
    with pytest.raises(TypeError, match=name):
        JonesField.from_scalar(scalar(0), **params)


@pytest.mark.parametrize("name", ["x_coefficient", "y_coefficient"])
@pytest.mark.parametrize("coefficient", [float("nan"), float("inf"), -float("inf"), complex(1, float("nan")), 10**1000])
def test_coefficient_nonfinite_or_binary64_overflow_rejected(name, coefficient):
    params = dict(x_coefficient=0, y_coefficient=0)
    params[name] = coefficient
    with pytest.raises(ValueError, match=name):
        JonesField.from_scalar(scalar(0), **params)


def test_zero_fields_and_coefficients_are_valid_without_phase_or_loss_normalization():
    dark = JonesField.from_scalar(scalar(0), x_coefficient=3j, y_coefficient=2-1j)
    extinguished = JonesField.from_scalar(scalar(3+4j), x_coefficient=0, y_coefficient=0)
    for value in (dark, extinguished):
        np.testing.assert_array_equal(value.x.data, np.zeros(value.shape, dtype=np.complex128))
        np.testing.assert_array_equal(value.y.data, np.zeros(value.shape, dtype=np.complex128))
        np.testing.assert_array_equal(value.intensity, np.zeros(value.shape))
        assert value.sampled_norm == 0.0
        assert transmission_ratio(value, value) is None


def test_zero_coefficients_can_make_norm_unusable_scalar_a_valid_dark_jones_field():
    # ComplexField accepts finite amplitudes independently of derived intensity.
    for amplitude in (1e200, 1e-200):
        value = JonesField.from_scalar(scalar(amplitude), x_coefficient=0, y_coefficient=0)
        assert value.sampled_norm == 0.0


@pytest.mark.parametrize("change", ["ny", "nx", "dx", "dy", "wavelength"])
def test_component_metadata_requires_exact_compatibility(change):
    first = scalar()
    params = dict(ny=2, nx=3, dy=5e-6, dx=4e-6)
    wavelength = first.wavelength_m
    if change in ("ny", "nx"):
        params[change] += 1
    elif change in ("dx", "dy"):
        params[change] = float(np.nextafter(params[change], math.inf))
    else:
        wavelength = float(np.nextafter(wavelength, math.inf))
    second = scalar(grid=SamplingGrid(**params), wavelength=wavelength)
    with pytest.raises(ValueError):
        JonesField(x=first, y=second)


def test_distinct_but_exactly_equal_grids_are_compatible():
    first = scalar()
    second = scalar(grid=SamplingGrid(ny=2, nx=3, dx=4e-6, dy=5e-6))
    assert first.grid is not second.grid
    assert JonesField(x=first, y=second).grid == first.grid


def test_coordinate_overriding_grid_subclass_is_rejected_despite_equal_metadata():
    class ReversedXGrid(SamplingGrid):
        @property
        def x(self):
            return -super().x

    canonical = scalar()
    altered_grid = ReversedXGrid(ny=2, nx=3, dx=4e-6, dy=5e-6)
    assert (altered_grid.ny, altered_grid.nx, altered_grid.dy, altered_grid.dx) == (
        canonical.grid.ny, canonical.grid.nx, canonical.grid.dy, canonical.grid.dx
    )
    assert not np.array_equal(altered_grid.x, canonical.grid.x)
    altered = scalar(grid=altered_grid)
    with pytest.raises(TypeError, match="canonical SamplingGrid"):
        JonesField(x=canonical, y=altered)


@pytest.mark.parametrize("change,error", [("grid", TypeError), ("wavelength", ValueError),
                                         ("nonfinite", ValueError)])
def test_from_scalar_zero_coefficients_still_validate_tampered_scalar(change, error):
    source = scalar(0)
    if change == "grid":
        object.__setattr__(source, "grid", None)
    elif change == "wavelength":
        object.__setattr__(source, "wavelength_m", 0)
    else:
        source.data.setflags(write=True)
        source.data[0, 0] = np.nan
    with pytest.raises(error):
        JonesField.from_scalar(source, x_coefficient=0, y_coefficient=0)


@pytest.mark.parametrize("name", ["x", "y"])
@pytest.mark.parametrize("value", [None, {}, np.ones((2, 3)), 1])
def test_component_types_must_be_public_complex_fields(name, value):
    values = dict(x=scalar(), y=scalar())
    values[name] = value
    with pytest.raises(TypeError, match=name):
        JonesField(**values)


def test_ratio_four_for_independently_constructed_compatible_fields():
    incident = jones(1+2j, -0.4+0.8j)
    independent_output = jones(2+4j, -0.8+1.6j)
    np.testing.assert_allclose(transmission_ratio(incident, independent_output), 4.0, rtol=2e-13, atol=2e-13)
    assert transmission_ratio(incident, jones(0, 0)) == 0.0


@pytest.mark.parametrize("change", ["shape", "dx", "dy", "wavelength"])
def test_ratio_validates_exact_compatibility_before_zero_denominator(change):
    incident = jones(0, 0)
    params = dict(ny=2, nx=3, dx=4e-6, dy=5e-6)
    wavelength = incident.wavelength_m
    if change == "shape":
        params["nx"] += 1
    elif change in ("dx", "dy"):
        params[change] = float(np.nextafter(params[change], math.inf))
    else:
        wavelength = float(np.nextafter(wavelength, math.inf))
    output = jones(0, 0, grid=SamplingGrid(**params), wavelength=wavelength)
    with pytest.raises(ValueError):
        transmission_ratio(incident, output)


@pytest.mark.parametrize("operation", [
    lambda value: apply_linear_retarder(value, axis_angle_rad=0, retardance_rad=0),
    lambda value: apply_linear_polarizer(value, axis_angle_rad=0),
])
@pytest.mark.parametrize("dark", [False, True])
def test_every_operation_returns_fresh_independent_components(operation, dark):
    source = jones(0 if dark else 1+2j, 0 if dark else -0.4+0.8j)
    before = (source.x.data.tobytes(), source.y.data.tobytes())
    result = operation(source)
    assert result is not source
    for component in (result.x, result.y):
        assert component.data.dtype == np.complex128
        assert not component.data.flags.writeable
        assert all(not np.shares_memory(component.data, original.data)
                   for original in (source.x, source.y))
    assert not np.shares_memory(result.x.data, result.y.data)
    assert before == (source.x.data.tobytes(), source.y.data.tobytes())
