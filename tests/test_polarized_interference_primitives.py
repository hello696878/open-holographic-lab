"""V2f matching-polarization mixing: independent coefficients and domain gates."""

import math

import numpy as np
import pytest

from ohlab import ComplexField, SamplingGrid
from ohlab.optics.polarization import JonesField
from ohlab.optics import polarized_interference as module
from ohlab.optics.polarized_interference import mix_balanced_jones


def jones(x=1, y=0, *, ny=2, nx=3, dx=4e-6, dy=5e-6, wavelength=633e-9):
    grid = SamplingGrid(ny=ny, nx=nx, dy=dy, dx=dx)
    values = []
    for component in (x, y):
        data = np.asarray(component, dtype=np.complex128)
        if data.ndim == 0:
            data = np.full(grid.shape, data, dtype=np.complex128)
        values.append(ComplexField(data=data, grid=grid, wavelength_m=wavelength))
    return JonesField(x=values[0], y=values[1])


def components(fields):
    return tuple(component for field in fields for component in (field.x, field.y))


@pytest.mark.parametrize("matrix", ["B", "B_dagger"])
def test_literal_four_component_mixing(matrix):
    """Four distinct simultaneous coherent inputs pin port and basis ordering."""
    inputs = (jones(1+2j, -.4+.7j), jones(.3-.7j, -1.1+.2j))
    sign = 1j if matrix == "B" else -1j
    literal = np.array([[1, 0, sign, 0], [0, 1, 0, sign],
                        [sign, 0, 1, 0], [0, sign, 0, 1]], dtype=np.complex128) / math.sqrt(2)
    np.testing.assert_allclose(literal.conj().T @ literal, np.eye(4), rtol=0, atol=2e-15)
    reference = literal @ np.array([1+2j, -.4+.7j, .3-.7j, -1.1+.2j])
    result = mix_balanced_jones(*inputs, matrix=matrix)
    for actual, expected in zip(components(result), reference):
        np.testing.assert_allclose(actual.data, expected, rtol=2e-14, atol=2e-14*math.sqrt(5))
    nin = sum(field.sampled_norm for field in inputs)
    np.testing.assert_allclose(sum(field.sampled_norm for field in result), nin,
                               rtol=2e-13, atol=2e-13*nin)


@pytest.mark.parametrize("matrix", ["B", "B_dagger"])
def test_actual_four_basis_columns_and_inverse(matrix):
    columns = []
    for index in range(4):
        values = [0j]*4
        values[index] = 1
        result = mix_balanced_jones(jones(*values[:2]), jones(*values[2:]), matrix=matrix)
        columns.append([value.data[0, 0] for value in components(result)])
    actual = np.array(columns).T
    sign = 1j if matrix == "B" else -1j
    reference = np.array([[1, 0, sign, 0], [0, 1, 0, sign],
                          [sign, 0, 1, 0], [0, sign, 0, 1]]) / math.sqrt(2)
    np.testing.assert_allclose(actual, reference, rtol=0, atol=2e-15)
    source = (jones(1+2j, .3-.8j), jones(-.7+.1j, 2.1-.9j))
    inverse = "B_dagger" if matrix == "B" else "B"
    restored = mix_balanced_jones(*mix_balanced_jones(*source, matrix=matrix), matrix=inverse)
    amplitude = max(float(np.max(np.abs(value.data))) for value in components(source))
    for actual_field, original in zip(components(restored), components(source)):
        np.testing.assert_allclose(actual_field.data, original.data, rtol=2e-14, atol=2e-14*amplitude)


@pytest.mark.parametrize("matrix", ["B", "B_dagger"])
def test_same_port_instance_outputs_are_owned_and_inputs_unchanged(matrix):
    source = jones(1+2j, -.4+.8j)
    before = (source.x.data.tobytes(), source.y.data.tobytes())
    result = mix_balanced_jones(source, source, matrix=matrix)
    arrays = [component.data for component in components(result)]
    for index, data in enumerate(arrays):
        assert data.dtype == np.dtype(np.complex128) and data.dtype.isnative
        assert data.flags.owndata and not data.flags.writeable
        assert all(not np.shares_memory(data, other) for other in arrays[index+1:])
        assert all(not np.shares_memory(data, original.data) for original in (source.x, source.y))
    source.x.data.setflags(write=True)
    source.x.data[:] = 19
    assert source.y.data.tobytes() == before[1]
    assert all(np.any(data != 19) for data in arrays)


@pytest.mark.parametrize("tag,error", [(None, TypeError), (True, TypeError),
    (np.eye(2), TypeError), ("b", ValueError), ("B†", ValueError), ("", ValueError)],
    ids=["none", "bool", "array", "lower", "symbol", "empty"])
def test_explicit_exact_matrix_tag(tag, error):
    with pytest.raises(error, match="matrix"):
        mix_balanced_jones(jones(), jones(0, 0), matrix=tag)
    with pytest.raises(TypeError):
        mix_balanced_jones(jones(), jones(0, 0))


@pytest.mark.parametrize("changes", [dict(ny=3), dict(nx=4),
    dict(dx=float(np.nextafter(4e-6, math.inf))), dict(dy=float(np.nextafter(5e-6, math.inf))),
    dict(wavelength=float(np.nextafter(633e-9, math.inf)))],
    ids=["ny", "nx", "dx", "dy", "lambda"])
def test_exact_cross_port_metadata_not_shape_only(changes):
    with pytest.raises(ValueError, match="grid|wavelength|metadata"):
        mix_balanced_jones(jones(), jones(**changes), matrix="B")


@pytest.mark.parametrize("port", [0, 1])
def test_both_port_types_validate_even_at_dark_input(port):
    inputs = [jones(0, 0), jones(0, 0)]
    inputs[port] = np.zeros((2, 3), dtype=np.complex128)
    with pytest.raises(TypeError, match=f"port_{port}"):
        mix_balanced_jones(*inputs, matrix="B")


@pytest.mark.parametrize("port,component", [(0, "x"), (0, "y"), (1, "x"), (1, "y")])
def test_valid_jones_tiny_component_rejected_before_mix(monkeypatch, port, component):
    values = [jones(1, 1), jones(1, 1)]
    values[port] = jones(1e-200 if component == "x" else 1,
                         1e-200 if component == "y" else 1)
    assert values[port].sampled_norm > 0
    tiny = getattr(values[port], component).data
    assert np.all(tiny != 0)
    before = tiny.tobytes()
    def forbidden(*args, **kwargs):
        pytest.fail("all four scalar input norms must pass before the first x mixing")
    monkeypatch.setattr(module, "mix_balanced", forbidden)
    with pytest.raises(ValueError, match=f"port_{port}.*{component}.*norm"):
        mix_balanced_jones(*values, matrix="B")
    assert tiny.tobytes() == before


@pytest.mark.parametrize("matrix", ["B", "B_dagger"])
def test_scalar_boundary_derived_cancellation_is_rejected(matrix):
    amplitude = 1e-150
    adjacent = float(np.nextafter(amplitude, math.inf))
    # Each input y norm is usable. Its cancellation residual is represented,
    # but squaring the whole residual underflows; x stays a valid Jones field.
    crossed = 1j if matrix == "B" else -1j
    inputs = (jones(1, amplitude), jones(2, crossed*adjacent))
    assert np.sum(np.abs(inputs[0].y.data)**2)*4e-6*5e-6 > 0
    with pytest.raises(ValueError, match="y.*(mix|norm)|mix.*y") as caught:
        mix_balanced_jones(*inputs, matrix=matrix)
    assert caught.value.__cause__ is not None


def test_combined_intensity_has_no_scalar_cross_term():
    outputs = mix_balanced_jones(jones(1, 1), jones(0, 0), matrix="B")
    for output in outputs:
        np.testing.assert_allclose(output.intensity, 1, rtol=2e-13, atol=2e-13)
        assert not np.allclose(np.abs(output.x.data+output.y.data)**2, output.intensity,
                               rtol=2e-13, atol=2e-13)


def test_primitive_does_not_inherit_runner_cap():
    output = mix_balanced_jones(jones(1, 1j, ny=1, nx=129),
                                jones(0, 0, ny=1, nx=129), matrix="B")
    assert all(field.shape == (1, 129) for field in output)


def test_exact_dark_mixer_and_distinct_equal_grids():
    first, second = jones(0, 0), jones(0, 0)
    assert first.grid is not second.grid and first.grid == second.grid
    for value in mix_balanced_jones(first, second, matrix="B_dagger"):
        assert value.sampled_norm == 0
        assert not np.count_nonzero(value.x.data) and not np.count_nonzero(value.y.data)


@pytest.mark.parametrize("setting", ["ignore", "warn", "raise"])
def test_mixer_restores_caller_error_settings_on_success_and_domain_failure(setting):
    source, dark = jones(1+2j, 1e-155), jones(0, 0)
    with np.errstate(all=setting):
        before = np.geterr().copy()
        mix_balanced_jones(source, dark, matrix="B")
        assert np.geterr() == before
        with pytest.raises(ValueError):
            mix_balanced_jones(jones(1, 1e-200), dark, matrix="B")
        assert np.geterr() == before
