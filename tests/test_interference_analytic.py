"""Independent ordered complex-field, phase, norm and direct-DFT acceptance."""

from __future__ import annotations

import cmath
import math

import numpy as np
import pytest

from ohlab import ComplexField, SamplingGrid
from ohlab.optics import interference
from ohlab.optics.interference import (
    TwoArmSpec, apply_uniform_phase, mix_balanced, run_two_arm,
)
from ohlab.propagation import propagate_angular_spectrum
import ohlab.propagation as propagation
from scripts import validate_v2a_interference as validation
from scripts.validate_v2a_interference import (
    NEAR_DARK_PHASES, PHASES, WAVELENGTH_M, asymmetric_fixture,
    independent_dft_propagation, independent_dft_reference, sampled_norm,
)


def field(data: np.ndarray, *, dy: float = 4.1e-6, dx: float = 3.7e-6) -> ComplexField:
    return ComplexField(data=data, grid=SamplingGrid(ny=data.shape[0], nx=data.shape[1], dy=dy, dx=dx),
                        wavelength_m=WAVELENGTH_M)


def assert_pair(actual, expected, amplitude, tolerance=2e-14):
    for output, reference in zip(actual, expected):
        np.testing.assert_allclose(output.data, reference, rtol=tolerance, atol=tolerance * amplitude)


@pytest.mark.parametrize("matrix", ["B", "B_dagger"])
def test_coherent_two_input_hand_coefficients(matrix):
    """Simultaneous coherent fields pin the relative i and both ordered ports."""
    a = np.full((3, 4), 1 + 2j, dtype=np.complex128)
    b = np.full((3, 4), .3 - .7j, dtype=np.complex128)
    actual = mix_balanced(field(a), field(b), matrix=matrix)
    # Explicit hand arithmetic, not the production coefficient helper.
    values = ((1.7 + 2.3j, -1.7 + .3j) if matrix == "B"
              else (.3 + 1.7j, 2.3 - 1.7j))
    expected = tuple(np.full(a.shape, value / math.sqrt(2), dtype=np.complex128) for value in values)
    assert_pair(actual, expected, math.sqrt(5))
    before = sampled_norm(a, dx_m=3.7e-6, dy_m=4.1e-6) + sampled_norm(b, dx_m=3.7e-6, dy_m=4.1e-6)
    after = sum(sampled_norm(f.data, dx_m=3.7e-6, dy_m=4.1e-6) for f in actual)
    assert after == pytest.approx(before, rel=2e-13, abs=2e-13 * before)


def test_coherent_one_i_hand_case_inverse_and_literal_unitarity():
    one = field(np.ones((3, 4), dtype=np.complex128))
    imaginary = field(np.full((3, 4), 1j, dtype=np.complex128))
    output = mix_balanced(one, imaginary, matrix="B")
    assert_pair(output, (np.zeros(one.shape, dtype=np.complex128),
                         np.full(one.shape, math.sqrt(2) * 1j)), 1)
    inverse = mix_balanced(one, imaginary, matrix="B_dagger")
    assert_pair(inverse, (np.full(one.shape, math.sqrt(2)), np.zeros(one.shape)), 1)
    composed = mix_balanced(*output, matrix="B_dagger")
    assert_pair(composed, (one.data, imaginary.data), 1)
    matrix = np.array([[1, 1j], [1j, 1]], dtype=np.complex128) / math.sqrt(2)
    np.testing.assert_allclose(matrix.conj().T @ matrix, np.eye(2), rtol=0, atol=2e-15)
    zero = field(np.zeros(one.shape, dtype=np.complex128))
    actual_matrix = np.array([[f.data[0, 0] for f in mix_balanced(one, zero, matrix="B")],
                              [f.data[0, 0] for f in mix_balanced(zero, one, matrix="B")]]).T
    np.testing.assert_allclose(actual_matrix, matrix, rtol=0, atol=2e-15)


@pytest.mark.parametrize("phase", PHASES)
def test_equal_arm_complex_sweep_and_ordered_input_fractions(phase):
    """All eight declared phases; full complex fields including port1=-iW at pi."""
    data = asymmetric_fixture(3, 4)
    source = field(data)
    result = run_two_arm(source, spec=TwoArmSpec(
        arm_0_distance_m=.002, arm_1_distance_m=.002, relative_phase_rad=phase))
    # This independent mixer identity uses unchanged public ASM for W; separate
    # complete-DFT tests independently verify propagation as well.
    w = propagate_angular_spectrum(source, distance_m=.002, pad_factor=1).data
    factor = cmath.exp(1j * phase)
    expected = ((1 + factor) * w / 2, 1j * (factor - 1) * w / 2)
    assert_pair(result.outputs, expected, float(np.max(np.abs(data))))
    np.testing.assert_allclose(result.norms.output_fractions,
        [math.cos(phase / 2) ** 2, math.sin(phase / 2) ** 2], rtol=2e-13, atol=2e-13)
    assert result.norms.total_output_ratio == pytest.approx(1, rel=2e-13, abs=2e-13)
    if phase == math.pi:
        np.testing.assert_allclose(result.outputs[1].data, -1j * w,
                                   rtol=2e-14, atol=2e-14 * float(np.max(np.abs(data))))


@pytest.mark.parametrize("phase", NEAR_DARK_PHASES)
def test_near_dark_signal_is_resolved_with_input_scaled_absolute_bound(phase):
    data = asymmetric_fixture(3, 4)
    result = run_two_arm(field(data), spec=TwoArmSpec(
        arm_0_distance_m=0., arm_1_distance_m=0., relative_phase_rad=phase))
    factor = cmath.exp(1j * phase)
    expected = ((1 + factor) * data / 2, 1j * (factor - 1) * data / 2)
    scale = float(np.max(np.abs(data)))
    assert_pair(result.outputs, expected, scale)
    near_dark_port = 1 if abs(phase) < .001 else 0
    represented_signal = float(np.max(np.abs(result.outputs[near_dark_port].data)))
    assert represented_signal > 1e-5 * scale
    expected_fraction = (math.sin(phase / 2) ** 2 if near_dark_port == 1
                         else math.cos(phase / 2) ** 2)
    assert expected_fraction > 1e-10  # distinct from the 2e-13 input fraction bound.
    assert result.norms.output_fractions[near_dark_port] == pytest.approx(
        expected_fraction, rel=2e-13, abs=2e-13)


@pytest.mark.parametrize("ny,nx,z0,z1", [(3, 4, .002, .003), (5, 6, .002731, .004123),
                                       (6, 5, .002731, .004123)])
def test_complete_asymmetric_pipeline_independent_direct_dft(ny, nx, z0, z1):
    data = asymmetric_fixture(ny, nx)
    source = field(data)
    expected = independent_dft_reference(data, dy_m=source.grid.dy, dx_m=source.grid.dx,
        wavelength_m=WAVELENGTH_M, arm_0_distance_m=z0, arm_1_distance_m=z1, relative_phase_rad=.37)
    result = run_two_arm(source, spec=TwoArmSpec(
        arm_0_distance_m=z0, arm_1_distance_m=z1, relative_phase_rad=.37))
    assert_pair(result.outputs, expected, float(np.max(np.abs(data))), tolerance=1e-11)
    expected_norms = tuple(sampled_norm(u, dx_m=source.grid.dx, dy_m=source.grid.dy) for u in expected)
    np.testing.assert_allclose(result.norms.outputs, expected_norms, rtol=2e-13,
                               atol=2e-13 * result.norms.inputs_total)


@pytest.mark.parametrize("ny,nx", [(3, 4), (5, 6), (6, 5)])
def test_both_nonzero_coherent_inputs_full_independent_pipeline(ny, nx):
    a = asymmetric_fixture(ny, nx)
    b = (.2 + .4j) * a[::-1, ::-1]
    source_a, source_b = field(a), field(b)
    expected = independent_dft_reference(a, second_input=b, dy_m=source_a.grid.dy,
        dx_m=source_a.grid.dx, wavelength_m=WAVELENGTH_M, arm_0_distance_m=.002,
        arm_1_distance_m=.003, relative_phase_rad=.37)
    split = mix_balanced(source_a, source_b, matrix="B")
    a0 = propagate_angular_spectrum(split[0], distance_m=.002, pad_factor=1)
    a1 = apply_uniform_phase(propagate_angular_spectrum(split[1], distance_m=.003, pad_factor=1), phase_rad=.37)
    output = mix_balanced(a0, a1, matrix="B_dagger")
    assert_pair(output, expected, max(float(np.max(np.abs(a))), float(np.max(np.abs(b)))), tolerance=1e-11)
    input_norm = sampled_norm(a, dx_m=source_a.grid.dx, dy_m=source_a.grid.dy) + sampled_norm(b, dx_m=source_a.grid.dx, dy_m=source_a.grid.dy)
    output_norm = sum(sampled_norm(f.data, dx_m=source_a.grid.dx, dy_m=source_a.grid.dy) for f in output)
    assert output_norm == pytest.approx(input_norm, rel=2e-13, abs=2e-13 * input_norm)


def test_reference_does_not_call_production_helpers_or_fft(monkeypatch):
    data = asymmetric_fixture(3, 4)
    kwargs = dict(dy_m=4.1e-6, dx_m=3.7e-6, wavelength_m=WAVELENGTH_M,
                  arm_0_distance_m=.002, arm_1_distance_m=.003, relative_phase_rad=.37)
    expected = independent_dft_reference(data, **kwargs)

    def prohibited(*args, **kwargs):
        raise AssertionError("production helper called by independent reference")

    for name in ("mix_balanced", "apply_uniform_phase", "run_two_arm", "propagate_angular_spectrum"):
        monkeypatch.setattr(interference, name, prohibited)
        monkeypatch.setattr(validation, name, prohibited)
    monkeypatch.setattr(propagation, "propagate_angular_spectrum", prohibited)
    for name in ("fft2", "ifft2", "fftfreq", "fftshift", "ifftshift"):
        monkeypatch.setattr(np.fft, name, prohibited)
    monkeypatch.setattr(SamplingGrid, "meshgrid", prohibited)
    monkeypatch.setattr(SamplingGrid, "freq_meshgrid", prohibited)
    for name in ("x", "y", "fx_fft", "fy_fft", "fx_centered", "fy_centered"):
        monkeypatch.setattr(SamplingGrid, name, property(prohibited))
    result = independent_dft_reference(data, **kwargs)
    for a, b in zip(result, expected):
        np.testing.assert_array_equal(a, b)  # unchanged deterministic scalar reference.


def test_reference_dense_work_has_explicit_small_sample_limit():
    with pytest.raises(ValueError, match="256 samples"):
        independent_dft_propagation(np.ones((17, 17), dtype=np.complex128), dy_m=4e-6,
                                   dx_m=4e-6, wavelength_m=WAVELENGTH_M, distance_m=.002)


@pytest.mark.parametrize("mode,phase", [("DC", 0.), ("DC", .37), ("off_axis", .37)])
def test_unequal_lengths_carrier_absolute_complex_plane_wave(mode, phase):
    g = SamplingGrid(ny=5, nx=6, dy=4.1e-6, dx=3.7e-6)
    row, col = np.indices(g.shape)
    fx = fy = 0.
    data = np.ones(g.shape, dtype=np.complex128)
    if mode == "off_axis":
        fx, fy = 1 / (g.nx * g.dx), -1 / (g.ny * g.dy)
        data = np.exp(2j * math.pi * ((col - g.nx // 2) / g.nx - (row - g.ny // 2) / g.ny))
    source = ComplexField(data=data, grid=g, wavelength_m=WAVELENGTH_M)
    z0, z1 = WAVELENGTH_M / 7, WAVELENGTH_M / 7 + WAVELENGTH_M / 6
    kz = 2 * math.pi * math.sqrt((1 / WAVELENGTH_M) ** 2 - fx ** 2 - fy ** 2)
    h0, h1 = cmath.exp(1j * kz * z0), cmath.exp(1j * (kz * z1 + phase))
    expected = ((h0 + h1) * data / 2, 1j * (h1 - h0) * data / 2)
    result = run_two_arm(source, spec=TwoArmSpec(
        arm_0_distance_m=z0, arm_1_distance_m=z1, relative_phase_rad=phase))
    assert_pair(result.outputs, expected, 1.)
    fractions = (math.cos((kz * (z1 - z0) + phase) / 2) ** 2,
                 math.sin((kz * (z1 - z0) + phase) / 2) ** 2)
    np.testing.assert_allclose(result.norms.output_fractions, fractions, rtol=2e-13, atol=2e-13)
    if mode == "DC" and phase == 0:
        np.testing.assert_allclose(result.norms.output_fractions, [.75, .25], rtol=2e-13, atol=2e-13)


def test_common_global_phase_covariance_intensity_invariance_relative_phase_sensitivity():
    data = asymmetric_fixture(3, 4)
    spec = TwoArmSpec(arm_0_distance_m=.002, arm_1_distance_m=.003, relative_phase_rad=.37)
    base = run_two_arm(field(data), spec=spec)
    factor = cmath.exp(.67j)
    shifted = run_two_arm(field(data * factor), spec=spec)
    assert_pair(shifted.outputs, tuple(f.data * factor for f in base.outputs), float(np.max(np.abs(data))))
    for a, b in zip(base.outputs, shifted.outputs):
        np.testing.assert_allclose(a.intensity, b.intensity, rtol=2e-13,
                                   atol=2e-13 * float(np.max(np.abs(data))) ** 2)
    relative = run_two_arm(field(data), spec=TwoArmSpec(
        arm_0_distance_m=.002, arm_1_distance_m=.003, relative_phase_rad=.81))
    assert max(float(np.max(np.abs(a.intensity - b.intensity)))
               for a, b in zip(base.outputs, relative.outputs)) > .01


@pytest.mark.parametrize("phase", PHASES)
def test_blocked_arm_quarter_outputs_half_removed_phase_invariant(phase):
    data = asymmetric_fixture(3, 4)
    source = field(data)
    zero = field(np.zeros_like(data))
    split = mix_balanced(source, zero, matrix="B")
    input_norm = sampled_norm(data, dx_m=source.grid.dx, dy_m=source.grid.dy)
    blocked_norm = sampled_norm(split[1].data, dx_m=source.grid.dx, dy_m=source.grid.dy)
    assert blocked_norm == pytest.approx(input_norm / 2, rel=2e-13, abs=2e-13 * input_norm)
    output = mix_balanced(apply_uniform_phase(split[0], phase_rad=phase), zero, matrix="B_dagger")
    expected = (data * cmath.exp(1j * phase) / 2, -1j * data * cmath.exp(1j * phase) / 2)
    assert_pair(output, expected, float(np.max(np.abs(data))))
    norms = tuple(sampled_norm(f.data, dx_m=source.grid.dx, dy_m=source.grid.dy) for f in output)
    np.testing.assert_allclose(norms, [input_norm / 4] * 2, rtol=2e-13, atol=2e-13 * input_norm)
    assert sum(norms) == pytest.approx(input_norm - blocked_norm, rel=2e-13, abs=2e-13 * input_norm)
    for f in output:
        np.testing.assert_allclose(f.intensity, np.abs(data) ** 2 / 4, rtol=2e-13,
                                   atol=2e-13 * float(np.max(np.abs(data))) ** 2)


def test_forward_evanescent_unequal_arms_preserve_loss_full_complex():
    row, col = np.indices((4, 5))
    data = (1 + .3 * np.exp(2j * math.pi * (2 * col / 5 + row / 4))).astype(np.complex128)
    source = field(data, dy=.22e-6, dx=.2e-6)
    expected = independent_dft_reference(data, dy_m=source.grid.dy, dx_m=source.grid.dx,
        wavelength_m=WAVELENGTH_M, arm_0_distance_m=80e-9, arm_1_distance_m=130e-9, relative_phase_rad=.37)
    result = run_two_arm(source, spec=TwoArmSpec(
        arm_0_distance_m=80e-9, arm_1_distance_m=130e-9, relative_phase_rad=.37))
    assert_pair(result.outputs, expected, float(np.max(np.abs(data))), tolerance=1e-11)
    assert result.norms.total_output_ratio < .99
    assert result.norms.propagation_delta < 0
    assert result.norms.recombination_delta == pytest.approx(0., rel=0, abs=2e-13 * result.norms.inputs_total)


@pytest.mark.parametrize("phase", PHASES)
def test_equal_mixed_evanescent_input_fractions_include_tau(phase):
    row, col = np.indices((4, 5))
    data = (1 + .3 * np.exp(2j * math.pi * (2 * col / 5 + row / 4))).astype(np.complex128)
    source = field(data, dy=.22e-6, dx=.2e-6)
    w = independent_dft_propagation(data, dy_m=source.grid.dy, dx_m=source.grid.dx,
                                   wavelength_m=WAVELENGTH_M, distance_m=100e-9)
    tau = sampled_norm(w, dx_m=source.grid.dx, dy_m=source.grid.dy) / sampled_norm(
        data, dx_m=source.grid.dx, dy_m=source.grid.dy)
    assert tau < .99
    result = run_two_arm(source, spec=TwoArmSpec(
        arm_0_distance_m=100e-9, arm_1_distance_m=100e-9, relative_phase_rad=phase))
    expected = [tau * math.cos(phase / 2) ** 2, tau * math.sin(phase / 2) ** 2]
    np.testing.assert_allclose(result.norms.output_fractions, expected, rtol=2e-13, atol=2e-13)
    assert result.norms.total_output_ratio == pytest.approx(tau, rel=2e-13, abs=2e-13)
    factor = cmath.exp(1j * phase)
    assert_pair(result.outputs, ((1 + factor) * w / 2, 1j * (factor - 1) * w / 2),
                float(np.max(np.abs(data))), tolerance=1e-11)


def test_exact_zero_input_is_separate_and_has_undefined_input_ratios():
    source = field(np.zeros((3, 4), dtype=np.complex128))
    result = run_two_arm(source, spec=TwoArmSpec(
        arm_0_distance_m=.002, arm_1_distance_m=.003, relative_phase_rad=.37))
    for f in result.outputs:
        assert np.count_nonzero(f.data) == 0
    for pair in (result.norms.inputs, result.norms.split, result.norms.propagated,
                 result.norms.combiner, result.norms.outputs):
        assert pair == (0., 0.)
    assert result.norms.output_fractions == (None, None)
    assert result.norms.total_output_ratio is None
