"""V2c parameter validation and bounded arithmetic, without propagation limits."""

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


def field(x=1.0, y=0.0, *, dx=4e-6, dy=5e-6, wavelength=633e-9, ny=2, nx=3):
    grid = SamplingGrid(ny=ny, nx=nx, dy=dy, dx=dx)
    return JonesField(
        x=ComplexField(data=np.full(grid.shape, x, dtype=np.complex128), grid=grid, wavelength_m=wavelength),
        y=ComplexField(data=np.full(grid.shape, y, dtype=np.complex128), grid=grid, wavelength_m=wavelength),
    )


@pytest.mark.parametrize("value", [True, np.bool_(False), "0", 1+0j, np.array(0), None,
                                   np.datetime64("2026-01-01"), np.timedelta64(1, "s")])
@pytest.mark.parametrize("parameter", ["polarizer_axis", "retarder_axis", "retardance"])
def test_real_parameter_kinds_are_checked_before_dark_or_identity_shortcuts(value, parameter):
    dark = field(0, 0)
    with pytest.raises(TypeError):
        if parameter == "polarizer_axis":
            apply_linear_polarizer(dark, axis_angle_rad=value)
        elif parameter == "retarder_axis":
            apply_linear_retarder(dark, axis_angle_rad=value, retardance_rad=0)
        else:
            apply_linear_retarder(dark, axis_angle_rad=0, retardance_rad=value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), 10**1000])
@pytest.mark.parametrize("parameter", ["polarizer_axis", "retarder_axis", "retardance"])
def test_real_parameter_values_are_checked_before_dark_or_identity_shortcuts(value, parameter):
    dark = field(0, 0)
    with pytest.raises(ValueError):
        if parameter == "polarizer_axis":
            apply_linear_polarizer(dark, axis_angle_rad=value)
        elif parameter == "retarder_axis":
            apply_linear_retarder(dark, axis_angle_rad=value, retardance_rad=0)
        else:
            apply_linear_retarder(dark, axis_angle_rad=0, retardance_rad=value)


@pytest.mark.parametrize("value", [0, 1.0, np.int32(1), np.uint64(1), np.float16(1), np.float64(1), np.longdouble(1)])
def test_supported_real_scalar_angle_families(value):
    source = field()
    assert apply_linear_polarizer(source, axis_angle_rad=value).shape == source.shape
    assert apply_linear_retarder(source, axis_angle_rad=value, retardance_rad=value).shape == source.shape


@pytest.mark.parametrize("operation", [
    lambda value: apply_linear_polarizer(value, axis_angle_rad=0),
    lambda value: apply_linear_retarder(value, axis_angle_rad=0, retardance_rad=-0.0),
    lambda value: transmission_ratio(field(0, 0), value),
])
@pytest.mark.parametrize("change,error", [("dtype", TypeError), ("byteorder", TypeError),
                                         ("shape", ValueError), ("nonfinite", ValueError),
                                         ("wavelength", ValueError), ("grid", TypeError)])
def test_tampered_component_validation_is_not_bypassed(operation, change, error):
    source = field(0, 0)
    if change == "dtype":
        object.__setattr__(source.x, "data", np.zeros(source.shape, dtype=np.complex64))
    elif change == "byteorder":
        object.__setattr__(source.x, "data", np.zeros(source.shape, dtype=">c16"))
    elif change == "shape":
        object.__setattr__(source.x, "data", np.zeros((3, 2), dtype=np.complex128))
    elif change == "nonfinite":
        source.x.data.setflags(write=True)
        source.x.data[0, 0] = np.nan
    elif change == "wavelength":
        object.__setattr__(source.x, "wavelength_m", 0)
    else:
        object.__setattr__(source.x, "grid", None)
    with pytest.raises(error):
        operation(source)


@pytest.mark.parametrize("operation", [
    lambda value: apply_linear_polarizer(value, axis_angle_rad=0),
    lambda value: apply_linear_retarder(value, axis_angle_rad=0, retardance_rad=0),
    lambda value: transmission_ratio(value, field()),
    lambda value: transmission_ratio(field(), value),
    lambda value: JonesField.from_scalar(value, x_coefficient=1, y_coefficient=0),
])
def test_public_functions_reject_nonfield_arguments(operation):
    with pytest.raises(TypeError):
        operation(np.ones((2, 3)))


@pytest.mark.parametrize("retardance", [0.0, -0.0])
def test_signed_zero_retardance_is_validated_fresh_exact_identity(retardance):
    source = field(1+2j, -0.4+0.8j)
    result = apply_linear_retarder(source, axis_angle_rad=-0.37, retardance_rad=retardance)
    assert result.x.data.tobytes() == source.x.data.tobytes()
    assert result.y.data.tobytes() == source.y.data.tobytes()
    assert not np.shares_memory(result.x.data, source.x.data)
    assert not np.shares_memory(result.y.data, source.y.data)


def test_large_finite_parameters_are_used_as_supplied_without_user_modulo():
    theta, delta = 1e20, -1e20
    source = field(1+2j, -0.4+0.8j)
    c, s = math.cos(theta), math.sin(theta)
    q = complex(math.cos(delta), math.sin(delta))
    expected_x = (c*c+q*s*s)*(1+2j) + (1-q)*c*s*(-0.4+0.8j)
    expected_y = (1-q)*c*s*(1+2j) + (s*s+q*c*c)*(-0.4+0.8j)
    result = apply_linear_retarder(source, axis_angle_rad=theta, retardance_rad=delta)
    np.testing.assert_allclose(result.x.data, expected_x, rtol=2e-14, atol=2e-14*math.sqrt(5))
    np.testing.assert_allclose(result.y.data, expected_y, rtol=2e-14, atol=2e-14*math.sqrt(5))


@pytest.mark.parametrize("dx,dy", [(1e308, 1e308), (1e-200, 1e-200)])
def test_unusable_pixel_area_rejected_even_for_dark_fields(dx, dy):
    with pytest.raises(ValueError, match="pixel area"):
        field(0, 0, dx=dx, dy=dy)


@pytest.mark.parametrize("dx,dy,wavelength", [(1e200, 1e-200, 5e-324), (5e-324, 1.0, 633e-9)])
def test_same_plane_operations_do_not_apply_propagation_geometry_limits(dx, dy, wavelength):
    source = field(1, 0, nx=1, ny=1, dx=dx, dy=dy, wavelength=wavelength)
    result = apply_linear_retarder(source, axis_angle_rad=0, retardance_rad=0)
    assert result.sampled_norm > 0
    np.testing.assert_array_equal(result.x.data, np.ones((1, 1), dtype=np.complex128))


def test_tiny_orthogonal_component_is_retained_beside_usable_component():
    source = field(1, 1e-200)
    assert np.all(source.y.data == 1e-200)
    np.testing.assert_array_equal(source.intensity, np.ones(source.shape))
    result = apply_linear_retarder(source, axis_angle_rad=0, retardance_rad=0)
    assert result.y.data.tobytes() == source.y.data.tobytes()
    assert result.sampled_norm > 0


@pytest.mark.parametrize("x,dx,dy,ny,nx", [
    (1e200, 1, 1, 1, 1),   # Per-sample intensity overflow.
    (1e154, 1, 1, 2, 3),   # Finite intensities, unusable sum.
    (1e-200, 1, 1, 1, 1),  # Entire represented field's intensity rounds to zero.
    (1e-100, 1e-100, 1e-100, 1, 1),  # Final norm underflow.
    (1e100, 1e200, 1e-200, 1, 1),     # Declared left-to-right reduction overflows.
    (1e-100, 1e-200, 1e200, 1, 1),    # Declared left-to-right reduction underflows.
])
def test_unusable_combined_norm_is_contextual_value_error(x, dx, dy, ny, nx):
    with pytest.raises(ValueError, match="intensity|norm|arithmetic"):
        field(x, 0, dx=dx, dy=dy, ny=ny, nx=nx)


def test_coefficient_product_overflow_is_contextual_value_error():
    source = field(1e150).x
    with pytest.raises(ValueError, match="coefficient|scalar|arithmetic|overflow"):
        JonesField.from_scalar(source, x_coefficient=1e200, y_coefficient=0)


@pytest.mark.parametrize("incident_amplitude,output_amplitude", [(1e150, 1e-150), (1e-150, 1e150)])
def test_strictly_positive_ratio_underflow_and_overflow_are_rejected(incident_amplitude, output_amplitude):
    incident = field(incident_amplitude, dx=1, dy=1, ny=1, nx=1)
    output = field(output_amplitude, dx=1, dy=1, ny=1, nx=1)
    assert incident.sampled_norm > 0
    assert output.sampled_norm > 0
    with pytest.raises(ValueError, match="ratio"):
        transmission_ratio(incident, output)


def test_inexact_positive_subnormal_ratio_triggers_strict_division_underflow():
    incident = field(math.sqrt(3), dx=1, dy=1, ny=1, nx=1)
    output = field(1e-160, dx=1, dy=1, ny=1, nx=1)
    numerator = np.float64(output.sampled_norm)
    denominator = np.float64(incident.sampled_norm)
    assert numerator > 0 and denominator > 0
    with np.errstate(under="ignore"):
        represented_ratio = numerator / denominator
    assert 0 < represented_ratio < np.finfo(np.float64).tiny
    # Confirm this actual platform reports underflow even though division
    # retains an inexact positive subnormal; this is stronger than zero alone.
    with np.errstate(under="raise"):
        with pytest.raises(FloatingPointError):
            numerator / denominator
    with pytest.raises(ValueError, match="ratio.*underflow|underflow.*ratio"):
        transmission_ratio(incident, output)


@pytest.mark.parametrize("mode", ["ignore", "warn", "raise"])
def test_caller_numpy_error_settings_restored_on_success_and_failure(mode):
    source = field(1, 1e-200)
    with np.errstate(all=mode):
        before = np.geterr().copy()
        output = apply_linear_retarder(source, axis_angle_rad=0.37, retardance_rad=0.83)
        assert output.sampled_norm > 0
        assert transmission_ratio(source, output) > 0
        assert np.geterr() == before
        with pytest.raises(ValueError):
            field(1e200)
        assert np.geterr() == before
        with pytest.raises(ValueError):
            apply_linear_retarder(source, axis_angle_rad=math.nan, retardance_rad=0)
        assert np.geterr() == before
        large = field(1e150, dx=1, dy=1, ny=1, nx=1)
        small = field(1e-150, dx=1, dy=1, ny=1, nx=1)
        for incident, transmitted in ((large, small), (small, large)):
            with pytest.raises(ValueError, match="ratio"):
                transmission_ratio(incident, transmitted)
            assert np.geterr() == before
