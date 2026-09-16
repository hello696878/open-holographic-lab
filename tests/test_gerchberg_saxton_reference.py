"""Independent scalar physical-coordinate DFT evidence for M3.

The reference never calls np.fft, the production transfer function, field
projection helpers, or the solver to form expected arrays. It evaluates
the centered-coordinate forward/inverse sums, including sample/frequency
area factors, using cmath and math.fsum. The 3x5 and 5x8 fixtures and signed
0.2 mm distances retain the exact planning-probe parameters.
"""

from __future__ import annotations

import cmath
import math

import numpy as np
import pytest

from ohlab import SamplingGrid
from ohlab.algorithms import gerchberg_saxton


WAVELENGTH_M = 633e-9


def _complex_sum(values) -> complex:
    values = list(values)
    return complex(math.fsum(v.real for v in values), math.fsum(v.imag for v in values))


def _direct_propagation(data: np.ndarray, grid: SamplingGrid, distance: float) -> np.ndarray:
    ny, nx = data.shape
    xs = [(j - nx // 2) * grid.dx for j in range(nx)]
    ys = [(i - ny // 2) * grid.dy for i in range(ny)]
    # Explicit signed integer bins, including the negative even-size Nyquist bin.
    mx = [j if j <= (nx - 1) // 2 else j - nx for j in range(nx)]
    my = [i if i <= (ny - 1) // 2 else i - ny for i in range(ny)]
    fxs = [m / (nx * grid.dx) for m in mx]
    fys = [m / (ny * grid.dy) for m in my]
    spectrum = []
    for fy in fys:
        row = []
        for fx in fxs:
            transformed = grid.dx * grid.dy * _complex_sum(
                complex(data[i, j]) * cmath.exp(-2j * math.pi * (fx * xs[j] + fy * ys[i]))
                for i in range(ny) for j in range(nx)
            )
            kz = 2 * math.pi * math.sqrt((1 / WAVELENGTH_M)**2 - fx**2 - fy**2)
            row.append(transformed * cmath.exp(1j * kz * distance))
        spectrum.append(row)
    result = np.empty((ny, nx), dtype=np.complex128)
    frequency_area = 1 / (nx * ny * grid.dx * grid.dy)
    for i in range(ny):
        for j in range(nx):
            result[i, j] = frequency_area * _complex_sum(
                spectrum[p][q] * cmath.exp(2j * math.pi * (fxs[q] * xs[j] + fys[p] * ys[i]))
                for p in range(ny) for q in range(nx)
            )
    return result


def _project_reference(data: np.ndarray, amplitude: np.ndarray) -> np.ndarray:
    result = np.empty(data.shape, dtype=np.complex128)
    for index in np.ndindex(data.shape):
        value = complex(data[index])
        phase = 0.0 if value == 0j else cmath.phase(value)
        if phase == -math.pi:
            phase = math.pi
        result[index] = float(amplitude[index]) * cmath.exp(1j * phase)
    return result


def _residual_reference(data: np.ndarray, target: np.ndarray) -> float:
    numerator = math.fsum((abs(complex(v)) - float(a))**2
                          for v, a in zip(data.flat, target.flat))
    denominator = math.fsum(float(a)**2 for a in target.flat)
    return numerator / denominator


def _problem(shape: tuple[int, int]):
    grid = SamplingGrid(ny=shape[0], nx=shape[1], dy=10e-6, dx=8e-6)
    rows, cols = np.indices(shape)
    source = (0.2 + 0.01 * rows + 0.02 * cols).astype(np.float64)
    phase = 0.8 * np.sin(2 * np.pi * cols / shape[1]) + 0.5 * np.cos(
        2 * np.pi * rows / shape[0]
    ) + 0.12 * rows * cols
    target_raw = 0.3 + 0.08 * np.sin(rows + 2 * cols)
    target = target_raw * math.sqrt(float(np.sum(source**2) / np.sum(target_raw**2)))
    initial = np.array([float(a) * cmath.exp(1j * float(p))
                        for a, p in zip(source.flat, phase.flat)],
                       dtype=np.complex128).reshape(shape)
    return grid, source, target, phase, initial


@pytest.mark.parametrize("shape", [(3, 5), (5, 8)])
@pytest.mark.parametrize("distance", [2e-4, -2e-4])
@pytest.mark.parametrize("iterations", [0, 1, 3])
def test_gs_complete_iteration_and_history_match_independent_direct_dft(
    shape, distance: float, iterations: int,
) -> None:
    grid, source, target, phase, expected_source = _problem(shape)
    history = []
    for k in range(iterations + 1):
        expected_reconstruction = _direct_propagation(expected_source, grid, distance)
        history.append(_residual_reference(expected_reconstruction, target))
        if k < iterations:
            constrained = _project_reference(expected_reconstruction, target)
            backward = _direct_propagation(constrained, grid, -distance)
            expected_source = _project_reference(backward, source)
    actual = gerchberg_saxton(
        target_amplitude=target, source_amplitude=source, grid=grid,
        wavelength_m=WAVELENGTH_M, distance_m=distance, iterations=iterations,
        initial_phase=phase,
    )
    # Both bounds are explicit; the absolute scale comes from the prescribed
    # input, not a possibly corrupted output. Planning errors were <=2e-15
    # of the field peak and <=1e-16 in normalized residual; final measurements
    # are recorded separately in the M3 handoff.
    absolute_tolerance = 1e-13 * float(source.max())
    np.testing.assert_allclose(actual.source_field.data, expected_source,
                               rtol=1e-12, atol=absolute_tolerance)
    np.testing.assert_allclose(actual.reconstruction.data, expected_reconstruction,
                               rtol=1e-12, atol=absolute_tolerance)
    np.testing.assert_allclose(actual.residual_history, history, rtol=1e-12, atol=1e-14)


@pytest.mark.parametrize("shape", [(3, 5), (5, 8)])
@pytest.mark.parametrize("distance", [2e-4, -2e-4])
def test_gs_directly_constructed_feasible_fixed_point(shape, distance: float) -> None:
    grid, source, _, phase, expected_source = _problem(shape)
    expected_reconstruction = _direct_propagation(expected_source, grid, distance)
    target = np.array([abs(complex(v)) for v in expected_reconstruction.flat],
                      dtype=np.float64).reshape(shape)
    actual = gerchberg_saxton(
        target_amplitude=target, source_amplitude=source, grid=grid,
        wavelength_m=WAVELENGTH_M, distance_m=distance, iterations=4,
        initial_phase=phase,
    )
    absolute_tolerance = 1e-13 * float(source.max())
    np.testing.assert_allclose(actual.source_field.data, expected_source,
                               rtol=1e-12, atol=absolute_tolerance)
    np.testing.assert_allclose(actual.reconstruction.data, expected_reconstruction,
                               rtol=1e-12, atol=absolute_tolerance)
    np.testing.assert_allclose(actual.reconstruction.amplitude, target,
                               rtol=1e-12, atol=absolute_tolerance)
    # Zero is an analytic expected residual. A 1e-26 absolute bound allows
    # squared amplitude roundoff, not an O(1) convergence criterion.
    np.testing.assert_allclose(actual.residual_history, 0.0, rtol=0.0, atol=1e-26)


def test_gs_uniform_plane_wave_fixed_point_has_analytic_forward_phase() -> None:
    grid = SamplingGrid(ny=5, nx=8, dy=10e-6, dx=8e-6)
    row_mode, column_mode = -1, 2
    x, y = grid.meshgrid()
    fx, fy = column_mode / grid.extent_x, row_mode / grid.extent_y
    phase = 2 * np.pi * (fx * x + fy * y) + 0.3
    amplitude = np.full(grid.shape, 0.7, dtype=np.float64)
    distance = 2e-4
    kz = 2 * math.pi * math.sqrt((1 / WAVELENGTH_M)**2 - fx**2 - fy**2)
    initial = amplitude * np.exp(1j * phase)
    expected = initial * cmath.exp(1j * kz * distance)
    result = gerchberg_saxton(
        target_amplitude=amplitude, source_amplitude=amplitude, grid=grid,
        wavelength_m=WAVELENGTH_M, distance_m=distance, iterations=3,
        initial_phase=phase,
    )
    np.testing.assert_allclose(result.source_field.data, initial, rtol=1e-12, atol=7e-14)
    np.testing.assert_allclose(result.reconstruction.data, expected, rtol=1e-12, atol=7e-14)
    np.testing.assert_allclose(result.residual_history, 0.0, rtol=0.0, atol=1e-26)
