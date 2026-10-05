"""Independent complex coefficients and primitive compatibility/ownership."""

import cmath
import math

import numpy as np
import pytest

from ohlab import ComplexField, SamplingGrid
from ohlab.optics.interference import apply_uniform_phase, mix_balanced


def make(data, *, ny=2, nx=3, dx=4e-6, dy=5e-6, wavelength=633e-9):
    grid = SamplingGrid(ny=ny, nx=nx, dy=dy, dx=dx)
    return ComplexField(data=np.full(grid.shape, data, dtype=np.complex128)
                        if np.isscalar(data) else data, grid=grid, wavelength_m=wavelength)


def norm(value):
    return float(np.sum(np.abs(value.data)**2, dtype=np.float64) * value.grid.dx * value.grid.dy)


@pytest.mark.parametrize("matrix", ["B", "B_dagger"])
@pytest.mark.parametrize("a,b", [(1., 1j), (1., 1.), (1+2j, .3-.7j), (-2+.5j, .25+3j)])
def test_two_nonzero_inputs_hand_complex_coefficients_and_combined_norm(matrix, a, b):
    inputs = (make(a), make(b))
    outputs = mix_balanced(*inputs, matrix=matrix)
    if matrix == "B":
        expected = ((a + 1j*b) / math.sqrt(2), (1j*a + b) / math.sqrt(2))
    else:
        expected = ((a - 1j*b) / math.sqrt(2), (-1j*a + b) / math.sqrt(2))
    scale = max(abs(a), abs(b))
    for actual, target in zip(outputs, expected):
        np.testing.assert_allclose(actual.data, target, rtol=2e-14, atol=2e-14*scale)
    combined = norm(inputs[0]) + norm(inputs[1])
    np.testing.assert_allclose(norm(outputs[0]) + norm(outputs[1]), combined,
                               rtol=2e-13, atol=2e-13*combined)


def test_independent_literal_unitarity_and_b_then_adjoint_on_asymmetric_inputs():
    b = np.array([[1, 1j], [1j, 1]], dtype=np.complex128) / math.sqrt(2)
    dagger = np.array([[1, -1j], [-1j, 1]], dtype=np.complex128) / math.sqrt(2)
    np.testing.assert_allclose(dagger @ b, np.eye(2), rtol=0., atol=2e-15)
    np.testing.assert_allclose(b @ dagger, np.eye(2), rtol=0., atol=2e-15)
    a = np.array([[1+2j, -.7+.1j, 2-.5j], [.2-1.1j, 1.3+.4j, -.8-2.2j]])
    other = np.array([[.1-.8j, .5+.2j, -.6+.3j], [1.4+.7j, -.2-.9j, 2.1+.3j]])
    inputs = (make(a), make(other))
    returned = mix_balanced(*mix_balanced(*inputs, matrix="B"), matrix="B_dagger")
    scale = max(float(np.max(np.abs(a))), float(np.max(np.abs(other))))
    for actual, original in zip(returned, inputs):
        np.testing.assert_allclose(actual.data, original.data, rtol=2e-14, atol=2e-14*scale)


def test_coherent_one_i_hand_case_both_matrices_ordered_dark_port():
    out = mix_balanced(make(1), make(1j), matrix="B")
    np.testing.assert_allclose(out[0].data, 0., rtol=0., atol=2e-14)
    np.testing.assert_allclose(out[1].data, math.sqrt(2)*1j, rtol=2e-14, atol=2e-14)
    inverse = mix_balanced(make(1), make(1j), matrix="B_dagger")
    np.testing.assert_allclose(inverse[0].data, math.sqrt(2), rtol=2e-14, atol=2e-14)
    np.testing.assert_allclose(inverse[1].data, 0., rtol=0., atol=2e-14)


@pytest.mark.parametrize("matrix", ["B", "B_dagger"])
def test_same_valid_field_instance_at_both_ports_is_allowed_independent_outputs(matrix):
    source = make(1+2j)
    before = source.data.tobytes()
    outputs = mix_balanced(source, source, matrix=matrix)
    assert source.data.tobytes() == before
    assert not np.shares_memory(outputs[0].data, outputs[1].data)
    for output in outputs:
        assert output is not source
        assert not np.shares_memory(output.data, source.data)
        assert output.data.dtype == np.complex128
        assert not output.data.flags.writeable


@pytest.mark.parametrize("phase", [0., -0., .37, -.83, 2*math.pi+.37, 1e300])
def test_uniform_phase_full_complex_intensity_and_defensive_copy_even_zero(phase):
    values = np.array([[1+2j, -.7+.1j, 2-.5j], [.2-1.1j, 1.3+.4j, -.8-2.2j]])
    source = make(values)
    before = source.data.tobytes()
    result = apply_uniform_phase(source, phase_rad=phase)
    expected = values * cmath.exp(1j*phase)
    scale = float(np.max(np.abs(values)))
    np.testing.assert_allclose(result.data, expected, rtol=2e-14, atol=2e-14*scale)
    np.testing.assert_allclose(result.intensity, source.intensity, rtol=2e-14, atol=2e-14*scale**2)
    if phase == 0:
        assert result.data.tobytes() == before
    assert source.data.tobytes() == before
    assert result is not source
    assert not np.shares_memory(result.data, source.data)
    assert not result.data.flags.writeable
    first_intensity = result.intensity
    first_intensity[:] = 0
    assert np.any(result.intensity > 0)


@pytest.mark.parametrize("field_1,error,match", [
    (lambda: make(1, ny=3), ValueError, "grids"),
    (lambda: make(1, dx=4.1e-6), ValueError, "grids"),
    (lambda: make(1, dy=5.1e-6), ValueError, "grids"),
    (lambda: make(1, wavelength=532e-9), ValueError, "wavelengths"),
    (lambda: np.ones((2, 3)), TypeError, "port_1")])
def test_mixing_requires_grid_not_shape_alone_and_exact_wavelength(field_1, error, match):
    with pytest.raises(error, match=match):
        mix_balanced(make(1), field_1(), matrix="B")


def test_equal_independent_grids_are_compatible_not_identity_required():
    first, second = make(1), make(1j)
    assert first.grid is not second.grid
    assert first.grid == second.grid
    outputs = mix_balanced(first, second, matrix="B")
    np.testing.assert_allclose(outputs[1].data, math.sqrt(2)*1j, rtol=2e-14, atol=2e-14)


def test_grid_subclass_cannot_silently_override_the_transverse_convention():
    class FlippedGrid(SamplingGrid):
        @property
        def x(self):
            return -super().x
    grid = FlippedGrid(ny=2, nx=3, dy=5e-6, dx=4e-6)
    source = ComplexField(data=np.ones(grid.shape, dtype=np.complex128),
                          grid=grid, wavelength_m=633e-9)
    with pytest.raises(TypeError, match="canonical SamplingGrid coordinate convention"):
        mix_balanced(source, source, matrix="B")
    with pytest.raises(TypeError, match="canonical SamplingGrid coordinate convention"):
        apply_uniform_phase(source, phase_rad=0.)


@pytest.mark.parametrize("matrix,error", [(None, TypeError), (True, TypeError),
                                        (np.eye(2), TypeError), ("B†", ValueError),
                                        ("b", ValueError), ("", ValueError)])
def test_matrix_is_required_explicit_exact_tag(matrix, error):
    with pytest.raises(error, match="matrix"):
        mix_balanced(make(1), make(0), matrix=matrix)
    with pytest.raises(TypeError):
        mix_balanced(make(1), make(0))


@pytest.mark.parametrize("phase,error", [(True, TypeError), (np.bool_(True), TypeError),
                                       (1+0j, TypeError), (np.array(.1), TypeError),
                                       (".1", TypeError), (np.nan, ValueError),
                                       (np.inf, ValueError), (10**1000, ValueError)])
def test_phase_scalar_type_and_finiteness(phase, error):
    with pytest.raises(error, match="phase_rad"):
        apply_uniform_phase(make(1), phase_rad=phase)


def test_exact_zero_fields_both_ports_and_phase_remain_exactly_zero():
    dark = make(0)
    for result in (*mix_balanced(dark, dark, matrix="B"),
                   apply_uniform_phase(dark, phase_rad=.37)):
        assert np.count_nonzero(result.data) == 0
        assert norm(result) == 0


@pytest.mark.parametrize("operation", [lambda source: apply_uniform_phase(source, phase_rad=0),
                                       lambda source: mix_balanced(source, make(0), matrix="B")])
@pytest.mark.parametrize("amplitude,match", [(1e160, "overflow"), (1e-200, "nonzero field")])
def test_unusable_whole_norm_fails_with_context(operation, amplitude, match):
    with pytest.raises(ValueError, match=match):
        operation(make(amplitude))


def test_supported_squared_tails_and_field_products_restore_callers_numpy_settings():
    source = make(np.array([[1+2j, 1e-310+1e-310j, 0], [2-1j, 0, 1]], dtype=np.complex128))
    with np.errstate(all="raise"):
        before = np.geterr().copy()
        outputs = mix_balanced(source, make(0), matrix="B")
        rotated = apply_uniform_phase(outputs[0], phase_rad=.37)
        assert np.geterr() == before
        assert np.isfinite(rotated.data).all()
        with pytest.raises(ValueError, match="overflow"):
            apply_uniform_phase(make(1e160), phase_rad=.37)
        assert np.geterr() == before


def test_primitive_has_no_runner_only_resource_cap():
    value = make(1, ny=1, nx=513)
    dark = make(0, ny=1, nx=513)
    assert apply_uniform_phase(value, phase_rad=0.).shape == (1, 513)
    assert mix_balanced(value, dark, matrix="B")[0].shape == (1, 513)
