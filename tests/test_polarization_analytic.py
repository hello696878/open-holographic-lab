"""Independent literal/expanded Jones references and focused weak-signal tests."""

from decimal import Decimal, localcontext
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

MALUS_DEGREES = [-90, -75, -60, -45, -30, -15, 0, 15, 30, 45, 60, 75, 90]
NEAR_EXTINCTION_OFFSETS = [-1e-6, -1e-9, 0.0, 1e-9, 1e-6]
ANGLES = [0.0, math.pi/12, math.pi/8, math.pi/4, math.pi/2, -0.37, 0.61]
RETARDANCES = [0.0, math.pi/2, math.pi, -0.83, 2.41]


def field(x=1.0, y=0.0, *, grid=None):
    if grid is None:
        grid = SamplingGrid(ny=2, nx=3, dy=5e-6, dx=4e-6)
    components = []
    for value in (x, y):
        data = np.asarray(value, dtype=np.complex128)
        if data.ndim == 0:
            data = np.full(grid.shape, data, dtype=np.complex128)
        components.append(ComplexField(data=data, grid=grid, wavelength_m=633e-9))
    return JonesField(x=components[0], y=components[1])


def asymmetric_field():
    return field(
        np.array([[1+2j, -0.3+0.7j, 0j], [4-0.2j, -2-1j, 1e-7+3e-8j]]),
        np.array([[0.4-0.1j, 2+3j, 0j], [-0.7+1j, 0.6+0.8j, -3e-8+4e-8j]]),
    )


def assert_components(actual, expected_x, expected_y, amplitude_scale):
    np.testing.assert_allclose(actual.x.data, expected_x, rtol=2e-14, atol=2e-14*amplitude_scale)
    np.testing.assert_allclose(actual.y.data, expected_y, rtol=2e-14, atol=2e-14*amplitude_scale)


def decimal_near_reference(theta):
    """Evaluate bounded sin/cos directly at the actual binary64 theta.

    The five angles lie near 1.57, so direct Taylor series at 80 digits needs
    neither a rounded pi constant nor argument reduction. Expectations never
    call a production constructor, projector or matrix helper.
    """
    with localcontext() as context:
        context.prec = 80
        angle = Decimal.from_float(theta)
        sine, sine_term = angle, angle
        cosine, cosine_term = Decimal(1), Decimal(1)
        for n in range(1, 100):
            sine_term *= -(angle*angle)/Decimal((2*n)*(2*n+1))
            cosine_term *= -(angle*angle)/Decimal((2*n-1)*(2*n))
            sine += sine_term
            cosine += cosine_term
            if abs(sine_term) < Decimal("1e-78") and abs(cosine_term) < Decimal("1e-78"):
                break
        else:
            raise AssertionError("bounded independent Decimal series failed to converge")
        x = cosine*cosine
        y = cosine*sine
        intensity = x*x + y*y
        return float(x), float(y), float(intensity)


def test_horizontal_polarizer_literal_fixture():
    actual = apply_linear_polarizer(field(1, 1), axis_angle_rad=0)
    np.testing.assert_array_equal(actual.x.data, np.ones(actual.shape, dtype=np.complex128))
    np.testing.assert_array_equal(actual.y.data, np.zeros(actual.shape, dtype=np.complex128))


def test_vertical_polarizer_literal_fixture_and_unsnapped_residual():
    actual = apply_linear_polarizer(field(1, 1), axis_angle_rad=math.pi/2)
    assert_components(actual, 0, 1, 1)
    assert np.any(actual.x.data != 0)


def test_45_degree_analyzer_combines_vector_projection_before_intensity():
    actual = apply_linear_polarizer(field(1, 1), axis_angle_rad=math.pi/4)
    assert_components(actual, 1, 1, 1)
    np.testing.assert_allclose(actual.intensity, 2, rtol=2e-13, atol=2e-13*2)


def test_qwp_axis_zero_preserves_imaginary_phase():
    scale = 1/math.sqrt(2)
    actual = apply_linear_retarder(field(scale, scale), axis_angle_rad=0, retardance_rad=math.pi/2)
    assert_components(actual, scale, 1j*scale, 1)


def test_qwp_rotated_axis_preserves_selected_common_phase():
    actual = apply_linear_retarder(field(), axis_angle_rad=math.pi/4, retardance_rad=math.pi/2)
    assert_components(actual, (1+1j)/2, (1-1j)/2, 1)


def test_hwp_nontrivial_axis_preserves_selected_phase():
    actual = apply_linear_retarder(field(), axis_angle_rad=math.pi/8, retardance_rad=math.pi)
    assert_components(actual, 1/math.sqrt(2), 1/math.sqrt(2), 1)


@pytest.mark.parametrize("theta", ANGLES)
def test_polarizer_idempotence_and_passive_contraction(theta):
    source = asymmetric_field()
    first = apply_linear_polarizer(source, axis_angle_rad=theta)
    second = apply_linear_polarizer(first, axis_angle_rad=theta)
    amplitude = max(float(np.max(np.abs(source.x.data))), float(np.max(np.abs(source.y.data))))
    assert_components(second, first.x.data, first.y.data, amplitude)
    assert first.sampled_norm <= source.sampled_norm + 2e-13*source.sampled_norm
    assert transmission_ratio(source, first) <= 1 + 2e-13


@pytest.mark.parametrize("degrees", MALUS_DEGREES)
def test_malus_sweep_all_declared_angles(degrees):
    theta = math.radians(degrees)
    source = field()
    actual = apply_linear_polarizer(source, axis_angle_rad=theta)
    expected = math.cos(theta)**2
    np.testing.assert_allclose(transmission_ratio(source, actual), expected, rtol=2e-13, atol=2e-13)
    assert actual.sampled_norm <= source.sampled_norm + 2e-13*source.sampled_norm


def test_crossed_and_three_polarizers_for_already_x_polarized_input():
    source = field()
    horizontal = apply_linear_polarizer(source, axis_angle_rad=0)
    crossed = apply_linear_polarizer(horizontal, axis_angle_rad=math.pi/2)
    middle = apply_linear_polarizer(horizontal, axis_angle_rad=math.pi/4)
    triple = apply_linear_polarizer(middle, axis_angle_rad=math.pi/2)
    np.testing.assert_allclose(transmission_ratio(source, crossed), 0, rtol=2e-13, atol=2e-13)
    assert transmission_ratio(source, crossed) > 0  # Floating pi/2 is not snapped.
    assert_components(triple, 0, 0.5, 1)
    np.testing.assert_allclose(transmission_ratio(source, triple), 0.25, rtol=2e-13, atol=2e-13)


@pytest.mark.parametrize("offset", NEAR_EXTINCTION_OFFSETS)
def test_weak_extinction_retains_positive_components_and_diagnostics(offset):
    theta = math.pi/2 + offset
    source = field()
    output = apply_linear_polarizer(source, axis_angle_rad=theta)
    expected_x, expected_y, expected_intensity = decimal_near_reference(theta)
    assert expected_x > 0 and expected_intensity > 0
    assert np.all(output.x.data.real > 0)
    assert np.all(output.y.data != 0)
    assert np.all(output.intensity > 0)
    assert output.sampled_norm > 0
    ratio = transmission_ratio(source, output)
    assert ratio is not None and ratio > 0
    # Signal-specific bounds retain the selected ~1e-18 fractions. The tiny
    # nonzero atol also covers the represented residual at offset exactly 0.
    np.testing.assert_allclose(output.x.data, expected_x, rtol=2e-14, atol=1e-48)
    np.testing.assert_allclose(output.y.data, expected_y, rtol=2e-14, atol=1e-48)
    np.testing.assert_allclose(output.intensity, expected_intensity, rtol=2e-14, atol=1e-48)
    incident_norm = float(np.sum(np.ones(source.shape), dtype=np.float64)*source.grid.dx*source.grid.dy)
    np.testing.assert_allclose(output.sampled_norm, expected_intensity*incident_norm,
                               rtol=2e-14, atol=1e-48*incident_norm)
    np.testing.assert_allclose(ratio, expected_intensity, rtol=2e-14, atol=1e-48)


@pytest.mark.parametrize("theta", ANGLES)
@pytest.mark.parametrize("delta", RETARDANCES)
def test_retarder_public_basis_actions_are_unitary(theta, delta):
    grid = SamplingGrid(ny=1, nx=1, dx=1, dy=1)
    first = apply_linear_retarder(field(1, 0, grid=grid), axis_angle_rad=theta, retardance_rad=delta)
    second = apply_linear_retarder(field(0, 1, grid=grid), axis_angle_rad=theta, retardance_rad=delta)
    matrix = np.array([[first.x.data[0, 0], second.x.data[0, 0]],
                       [first.y.data[0, 0], second.y.data[0, 0]]])
    np.testing.assert_allclose(matrix.conj().T @ matrix, np.eye(2), rtol=0, atol=2e-15)


@pytest.mark.parametrize("theta", ANGLES)
@pytest.mark.parametrize("delta", RETARDANCES)
def test_retarder_expanded_complex_reference_inverse_and_norm(theta, delta):
    source = asymmetric_field()
    x, y = source.x.data, source.y.data
    c, s = math.cos(theta), math.sin(theta)
    q = complex(math.cos(delta), math.sin(delta))
    expected_x = (c*c+q*s*s)*x + (1-q)*c*s*y
    expected_y = (1-q)*c*s*x + (s*s+q*c*c)*y
    actual = apply_linear_retarder(source, axis_angle_rad=theta, retardance_rad=delta)
    amplitude = max(float(np.max(np.abs(x))), float(np.max(np.abs(y))))
    assert_components(actual, expected_x, expected_y, amplitude)
    inverse = apply_linear_retarder(actual, axis_angle_rad=theta, retardance_rad=-delta)
    assert_components(inverse, x, y, amplitude)
    np.testing.assert_allclose(actual.sampled_norm, source.sampled_norm,
                               rtol=2e-13, atol=2e-13*source.sampled_norm)
    np.testing.assert_allclose(transmission_ratio(source, actual), 1, rtol=2e-13, atol=2e-13)


@pytest.mark.parametrize("theta", ANGLES)
def test_polarizer_expanded_asymmetric_complex_reference(theta):
    source = asymmetric_field()
    c, s = math.cos(theta), math.sin(theta)
    x, y = source.x.data, source.y.data
    expected_x, expected_y = c*c*x+c*s*y, c*s*x+s*s*y
    actual = apply_linear_polarizer(source, axis_angle_rad=theta)
    amplitude = max(float(np.max(np.abs(x))), float(np.max(np.abs(y))))
    assert_components(actual, expected_x, expected_y, amplitude)


def test_noncommuting_order_has_distinct_complex_outputs():
    source = field()
    polarizer_then_retarder = apply_linear_retarder(
        apply_linear_polarizer(source, axis_angle_rad=0),
        axis_angle_rad=math.pi/4, retardance_rad=math.pi/2,
    )
    retarder_then_polarizer = apply_linear_polarizer(
        apply_linear_retarder(source, axis_angle_rad=math.pi/4, retardance_rad=math.pi/2),
        axis_angle_rad=0,
    )
    assert_components(polarizer_then_retarder, (1+1j)/2, (1-1j)/2, 1)
    assert_components(retarder_then_polarizer, (1+1j)/2, 0, 1)
    np.testing.assert_allclose(transmission_ratio(source, polarizer_then_retarder), 1, rtol=2e-13, atol=2e-13)
    np.testing.assert_allclose(transmission_ratio(source, retarder_then_polarizer), 0.5, rtol=2e-13, atol=2e-13)


@pytest.mark.parametrize("operation", [
    lambda value: apply_linear_polarizer(value, axis_angle_rad=-0.37),
    lambda value: apply_linear_retarder(value, axis_angle_rad=0.61, retardance_rad=-0.83),
])
def test_common_phase_covariance_and_intensity_invariance(operation):
    source = asymmetric_field()
    phase = complex(math.cos(0.67), math.sin(0.67))
    shifted = field(phase*source.x.data, phase*source.y.data)
    original_output, shifted_output = operation(source), operation(shifted)
    amplitude = max(float(np.max(np.abs(source.x.data))), float(np.max(np.abs(source.y.data))))
    assert_components(shifted_output, phase*original_output.x.data, phase*original_output.y.data, amplitude)
    np.testing.assert_allclose(shifted_output.intensity, original_output.intensity,
                               rtol=2e-13, atol=2e-13*amplitude**2)


def test_relative_phase_changes_analyzer_output_but_not_total_incident_intensity():
    source = field(1, 1)
    changed = field(1, -1)
    np.testing.assert_array_equal(source.intensity, changed.intensity)
    first = apply_linear_polarizer(source, axis_angle_rad=math.pi/4)
    second = apply_linear_polarizer(changed, axis_angle_rad=math.pi/4)
    np.testing.assert_allclose(first.intensity, 2, rtol=2e-13, atol=2e-13*2)
    np.testing.assert_allclose(second.intensity, 0, rtol=2e-13, atol=2e-13*2)


def test_exact_dark_input_is_separate_from_near_extinction():
    source = field(0, 0)
    for operation in (
        lambda: apply_linear_polarizer(source, axis_angle_rad=0.61),
        lambda: apply_linear_retarder(source, axis_angle_rad=-0.37, retardance_rad=math.pi/2),
    ):
        output = operation()
        np.testing.assert_array_equal(output.x.data, np.zeros(source.shape, dtype=np.complex128))
        np.testing.assert_array_equal(output.y.data, np.zeros(source.shape, dtype=np.complex128))
        np.testing.assert_array_equal(output.intensity, np.zeros(source.shape))
        assert output.sampled_norm == 0
        assert transmission_ratio(source, output) is None
