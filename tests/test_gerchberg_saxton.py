"""M3 public contracts, operator checks, and predeclared synthesis cases.

Independent scalar-DFT references live in test_gerchberg_saxton_reference.py.
Approximate comparisons always name relative and absolute tolerances. The
1e-12 relative / 1e-13 input-peak absolute field bounds cover measured
float64 FFT/projection errors, including cancelling output samples; they are
not physical-model error bounds. Exact assertions concern representation,
zero ties, deterministic repeats, or ownership only.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import importlib
import math
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from _helpers import assert_bit_identical, assert_phase_allclose
from ohlab import ComplexField, SamplingGrid
from ohlab.algorithms import GerchbergSaxtonResult, gerchberg_saxton
from ohlab.io.images import load_target_intensity
from ohlab.propagation import (
    angular_spectrum_transfer_function,
    propagate_angular_spectrum,
)
from ohlab.targets import grayscale8_to_intensity, intensity_to_amplitude


WAVELENGTH_M = 633e-9
gs_module = importlib.import_module("ohlab.algorithms.gerchberg_saxton")


def _arguments() -> dict:
    grid = SamplingGrid(ny=3, nx=5, dy=10e-6, dx=8e-6)
    source = (0.2 + np.arange(15, dtype=np.float64).reshape(3, 5) / 20)
    return dict(
        target_amplitude=np.roll(source, 2, axis=1).copy(),
        source_amplitude=source,
        grid=grid,
        wavelength_m=WAVELENGTH_M,
        distance_m=2e-4,
        iterations=3,
        seed=7,
    )


def _solve(**changes) -> GerchbergSaxtonResult:
    arguments = _arguments()
    arguments.update(changes)
    return gerchberg_saxton(**arguments)


def _raw_residual(data: np.ndarray, target: np.ndarray) -> float:
    # Scalar sums are independent of the solver's reduction implementation.
    return math.fsum((abs(complex(v)) - float(a)) ** 2
                     for v, a in zip(data.flat, target.flat)) / math.fsum(
                         float(a) ** 2 for a in target.flat
                     )


def test_gs_result_and_prescribed_nonuniform_amplitude() -> None:
    arguments = _arguments()
    result = gerchberg_saxton(**arguments)
    assert isinstance(result, GerchbergSaxtonResult)
    assert isinstance(result.source_field, ComplexField)
    assert isinstance(result.reconstruction, ComplexField)
    assert result.source_field.grid == result.reconstruction.grid == arguments["grid"]
    assert result.source_field.wavelength_m == result.reconstruction.wavelength_m == WAVELENGTH_M
    assert result.source_field.data.dtype == np.dtype(np.complex128)
    assert result.reconstruction.data.dtype == np.dtype(np.complex128)
    np.testing.assert_allclose(result.source_field.amplitude,
                               arguments["source_amplitude"], rtol=5e-15, atol=0.0)
    expected_power = math.fsum(float(v) ** 2 for v in arguments["source_amplitude"].flat)
    expected_power *= arguments["grid"].pixel_area
    np.testing.assert_allclose(
        [result.source_field.power, result.reconstruction.power], expected_power,
        rtol=5e-15, atol=0.0,
    )
    assert result.iterations == 3
    assert result.residual_history.shape == (4,)
    assert np.all(np.isfinite(result.residual_history))
    assert np.all(result.residual_history >= 0.0)


@pytest.mark.parametrize("distance", [2e-4, -2e-4, 0.0])
@pytest.mark.parametrize("iterations", [0, 1, 4])
def test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss(
    distance: float, iterations: int,
) -> None:
    arguments = _arguments()
    arguments.update(distance_m=distance, iterations=iterations)
    result = gerchberg_saxton(**arguments)
    rebuilt = ComplexField.from_amplitude_phase(
        amplitude=arguments["source_amplitude"], phase=result.phase,
        grid=arguments["grid"], wavelength_m=WAVELENGTH_M,
    )
    reference = propagate_angular_spectrum(rebuilt, distance_m=distance, pad_factor=1)
    scale = float(arguments["source_amplitude"].max())
    np.testing.assert_allclose(result.source_field.data, rebuilt.data,
                               rtol=1e-12, atol=1e-13 * scale)
    np.testing.assert_allclose(result.reconstruction.data, reference.data,
                               rtol=1e-12, atol=1e-13 * scale)
    independent_residual = _raw_residual(reference.data, arguments["target_amplitude"])
    np.testing.assert_allclose(result.residual_history[-1], independent_residual,
                               rtol=1e-12, atol=1e-14)
    # This deliberately non-fixed-point fixture must not report a projected
    # target as the actual field or conceal its residual behind exact zero.
    assert independent_residual > 1e-5
    assert result.residual_history[-1] > 1e-5


def test_gs_zero_iterations_matches_seeded_source_initialization() -> None:
    arguments = _arguments()
    arguments["iterations"] = 0
    result = gerchberg_saxton(**arguments)
    expected_phase = np.random.default_rng(arguments["seed"]).uniform(
        -np.pi, np.pi, size=arguments["grid"].shape,
    )
    expected = arguments["source_amplitude"] * np.exp(1j * expected_phase)
    np.testing.assert_allclose(result.source_field.data, expected,
                               rtol=1e-12, atol=1e-13 * arguments["source_amplitude"].max())
    assert result.iterations == 0 and result.residual_history.shape == (1,)


def test_gs_history_indices_match_separate_prefix_runs() -> None:
    full = _solve(iterations=4)
    for cycles in (0, 1, 2, 4):
        prefix = _solve(iterations=cycles)
        # Same initialized numerical operations reproduce each prefix exactly.
        assert_bit_identical(prefix.residual_history, full.residual_history[:cycles + 1])


def test_gs_same_seed_repeats_exactly_and_different_seed_differs() -> None:
    first, second, changed = _solve(), _solve(), _solve(seed=8)
    for left, right in (
        (first.source_field.data, second.source_field.data),
        (first.reconstruction.data, second.reconstruction.data),
        (first.residual_history, second.residual_history),
        (first.phase, second.phase),
    ):
        assert_bit_identical(left, right)  # same-platform deterministic contract
        assert not np.shares_memory(left, right)
    assert first.source_field.data.tobytes() != changed.source_field.data.tobytes()


def test_gs_explicit_phase_is_used_without_random_initialization(monkeypatch) -> None:
    phase = np.linspace(-7.0, 8.0, 15, dtype=np.float64).reshape(3, 5)
    def forbidden_rng(*args, **kwargs):
        pytest.fail("explicit initial phase must not create a random generator")
    monkeypatch.setattr(gs_module.np.random, "default_rng", forbidden_rng)
    result = _solve(seed=None, initial_phase=phase, iterations=0)
    assert_phase_allclose(result.phase, phase, atol=1e-12,
                          amplitude=result.source_field.amplitude)
    assert np.all(result.phase > -np.pi) and np.all(result.phase <= np.pi)


@pytest.mark.parametrize("layout", ["c", "fortran", "strided", "reversed"])
def test_gs_owns_outputs_and_preserves_readonly_noncontiguous_inputs(layout: str) -> None:
    arguments = _arguments()
    phase = np.linspace(-2.0, 2.0, 15).reshape(3, 5)
    arrays = [arguments["source_amplitude"], arguments["target_amplitude"], phase]
    transformed = []
    for original in arrays:
        if layout == "fortran":
            array = np.asfortranarray(original)
        elif layout == "strided":
            storage = np.empty((3, 10), dtype=np.float64)
            storage[:, ::2] = original
            array = storage[:, ::2]
        elif layout == "reversed":
            array = original[:, ::-1]
        else:
            array = original.copy()
        array.flags.writeable = False
        transformed.append(array)
    source, target, phase = transformed
    saved = [array.copy() for array in transformed]
    grid_before = arguments["grid"].to_dict()
    arguments.update(source_amplitude=source, target_amplitude=target,
                     initial_phase=phase, seed=None)
    result = gerchberg_saxton(**arguments)
    for array, before in zip(transformed, saved):
        assert_bit_identical(array, before)  # input representation is preserved
        for output in (result.source_field.data, result.reconstruction.data,
                       result.residual_history, result.phase):
            assert not np.shares_memory(output, array)
    assert arguments["grid"].to_dict() == grid_before
    history = result.residual_history
    assert history.dtype == np.dtype(np.float64) and history.dtype.isnative
    assert history.flags.owndata and history.flags.c_contiguous
    assert not history.flags.writeable
    with pytest.raises(ValueError):
        history[0] = 123.0
    phase_out = result.phase
    assert phase_out.dtype == np.dtype(np.float64) and phase_out.dtype.isnative
    assert phase_out.flags.owndata and phase_out.flags.c_contiguous
    assert phase_out.flags.writeable
    original_phase = result.phase
    phase_out[:] = 99.0
    assert_bit_identical(result.phase, original_phase)


def test_gs_result_is_frozen_and_identity_equality() -> None:
    result, another = _solve(), _solve()
    with pytest.raises(FrozenInstanceError):
        result.source_field = another.source_field
    assert result == result
    assert result != another  # eq=False avoids ndarray-generated equality


def test_gs_result_phase_canonical_endpoint_and_exact_zero_tie_are_local() -> None:
    # Direct complex values exercise representation without sin(pi) roundoff.
    # Nearby branch values and tiny nonzero support must not be thresholded.
    below_cut = np.nextafter(-np.pi, 0.0)
    data = np.array([
        [complex(-1.0, -0.0), complex(-1.0, 0.0), complex(np.exp(1j * below_cut)),
         complex(0.0, 0.0), complex(0.0, -0.0)],
        [complex(-0.0, 0.0), complex(-0.0, -0.0), complex(1e-200, -1e-200),
         complex(-1e-200, -0.0), complex(0.0, 1e-200)],
        [complex(1.0, 0.0), complex(0.0, -1.0), complex(1.0, 1.0),
         complex(-1.0, -1.0), complex(-1.0, 1.0)],
    ], dtype=np.complex128)
    field = ComplexField(data=data, grid=_arguments()["grid"], wavelength_m=WAVELENGTH_M)
    stored_before = field.data.copy()
    field_phase_before = field.phase
    result = GerchbergSaxtonResult(source_field=field, reconstruction=field,
                                  residual_history=np.array([0.0], dtype=np.float64))
    phase = result.phase
    assert phase[0, 0] == phase[0, 1] == np.pi  # canonical endpoint, exactly
    assert phase[0, 2] == below_cut  # adjacent negative angle remains negative
    assert np.all(phase[data == 0j] == 0.0)  # all four signed complex zeros
    assert not np.any(np.signbit(phase[data == 0j]))  # chosen tie is positive zero
    np.testing.assert_allclose(phase[1, 2], -np.pi / 4, rtol=0.0, atol=1e-15)
    assert phase[1, 3] == np.pi and phase[1, 4] == np.pi / 2
    assert np.all(phase > -np.pi) and np.all(phase <= np.pi)
    assert_bit_identical(field.data, stored_before)  # M0/M1 stored data untouched
    assert_bit_identical(field.phase, field_phase_before)  # existing phase contract untouched
    assert field.phase[1, 0] == np.pi  # M3 tie does not change ComplexField's signed zeros


def test_gs_result_takes_owned_copy_of_supplied_history() -> None:
    field = _solve(iterations=0).source_field
    backing = np.array([0.8, 99.0, 0.4, 99.0], dtype=np.float64)
    history = backing[::2]
    result = GerchbergSaxtonResult(source_field=field, reconstruction=field,
                                  residual_history=history)
    history[:] = 0.0
    np.testing.assert_array_equal(result.residual_history, [0.8, 0.4])
    assert result.residual_history.flags.owndata
    assert result.residual_history.flags.c_contiguous
    assert not result.residual_history.flags.writeable
    assert not np.shares_memory(result.residual_history, backing)


@pytest.mark.parametrize("history,error", [
    ([0.1], TypeError), (np.array([0.1], dtype=np.float32), TypeError),
    (np.array([], dtype=np.float64), ValueError), (np.array([[0.1]]), ValueError),
    (np.array([-0.1]), ValueError), (np.array([np.nan]), ValueError),
])
def test_gs_result_history_structure_is_validated(history, error) -> None:
    field = _solve(iterations=0).source_field
    with pytest.raises(error, match="residual_history"):
        GerchbergSaxtonResult(source_field=field, reconstruction=field,
                             residual_history=history)


@pytest.mark.parametrize("iterations", [0, 1, 5])
def test_gs_zero_distance_preserves_amplitude_but_resolves_zero_phase_ties(
    iterations: int,
) -> None:
    source = np.array([[1.0, 0.0, 0.0, 2.0, 0.0],
                       [0.0, 1.0, 0.0, 0.0, 0.0],
                       [0.0, 0.0, 0.0, 0.0, 0.0]])
    target = np.array([[0.0, 1.0, 0.0, 2.0, 0.0],
                       [1.0, 0.0, 0.0, 0.0, 0.0],
                       [0.0, 0.0, 0.0, 0.0, 0.0]])
    phase = np.full((3, 5), 0.7, dtype=np.float64)
    result = _solve(source_amplitude=source, target_amplitude=target,
                    seed=None, initial_phase=phase,
                    distance_m=0.0, iterations=iterations)
    expected_phase = phase.copy()
    expected_phase[source == 0.0] = 0.0
    if iterations:
        expected_phase[(source > 0.0) & (target == 0.0)] = 0.0
    np.testing.assert_allclose(result.phase, expected_phase, rtol=0.0, atol=1e-14)
    assert np.all(result.phase[source == 0.0] == 0.0)  # exact solver tie rule
    np.testing.assert_allclose(result.source_field.amplitude, source, rtol=5e-15, atol=0.0)
    assert_bit_identical(result.reconstruction.data, result.source_field.data)
    # Four unit-amplitude mismatches / target energy six = 2/3.
    np.testing.assert_allclose(result.residual_history, 2.0 / 3.0,
                               rtol=1e-12, atol=1e-14)


def test_gs_no_upper_one_limit_or_hidden_amplitude_normalization() -> None:
    arguments = _arguments()
    arguments["source_amplitude"] *= 4.0
    arguments["target_amplitude"] *= 4.0
    result = gerchberg_saxton(**arguments)
    assert arguments["source_amplitude"].max() > 1.0
    np.testing.assert_allclose(result.source_field.amplitude,
                               arguments["source_amplitude"], rtol=5e-15, atol=0.0)


@pytest.mark.parametrize("amplitude_scale", [1.0, 1e-9])
@pytest.mark.parametrize("relative_change,accepted", [(2e-13, True), (2e-12, False)])
def test_gs_power_match_has_relative_tolerance_and_zero_absolute_floor(
    amplitude_scale: float, relative_change: float, accepted: bool,
) -> None:
    arguments = _arguments()
    arguments["source_amplitude"] *= amplitude_scale
    arguments["target_amplitude"] *= amplitude_scale * math.sqrt(1.0 + relative_change)
    if accepted:
        gerchberg_saxton(**arguments)
    else:
        with pytest.raises(ValueError, match="power|energ"):
            gerchberg_saxton(**arguments)


@pytest.mark.parametrize("which", ["source", "target", "both"])
def test_gs_zero_source_or_target_energy_rejected(which: str) -> None:
    changes = {}
    for name in ("source", "target"):
        if which in (name, "both"):
            changes[name + "_amplitude"] = np.zeros((3, 5), dtype=np.float64)
    with pytest.raises(ValueError, match="positive|zero"):
        _solve(**changes)


@pytest.mark.parametrize("iterations,distance", [(0, 0.0), (0, 1e-6), (1, 0.0), (1, -1e-6)])
def test_gs_rejects_evanescent_grid_even_for_identity_requests(iterations, distance) -> None:
    # 400 nm is > lambda/2, yet diagonal frequency bins are evanescent.
    grid = SamplingGrid(ny=8, nx=8, dy=400e-9, dx=400e-9)
    with pytest.raises(ValueError, match="evanescent"):
        _solve(grid=grid, source_amplitude=np.ones(grid.shape),
               target_amplitude=np.ones(grid.shape), iterations=iterations,
               distance_m=distance)


@pytest.mark.parametrize("iterations", [0, 1])
@pytest.mark.parametrize("distance", [-1e-3, 0.0, 1e-3])
def test_gs_rejects_rounded_cutoff_geometry_that_breaks_lossless_model(
    iterations: int, distance: float,
) -> None:
    # In float64 this specific mesh passes the sum-of-squares cutoff test,
    # but the existing public H's sequential radicand rounds slightly below
    # zero. M3 refuses it, including N=0/z=0; M1 remains unchanged.
    grid = SamplingGrid(ny=4, nx=6, dy=1.3e-6, dx=1e-6)
    amplitude = np.ones(grid.shape, dtype=np.float64)
    with pytest.raises(ValueError, match="floating-point cutoff geometry"):
        _solve(grid=grid, source_amplitude=amplitude, target_amplitude=amplitude,
               wavelength_m=1.5852479782092003e-6,
               distance_m=distance, iterations=iterations)


@pytest.mark.parametrize("distance", [-1e-3, 0.0, 1e-3])
def test_gs_exactly_representable_grazing_bin_remains_supported(distance: float) -> None:
    # nx=2, dx=0.5 m, lambda=1 m gives the exact Nyquist bin fx=-1/lambda,
    # fy=0, kz=0. The lossless-domain restriction does not exclude grazing.
    grid = SamplingGrid(ny=1, nx=2, dy=1.0, dx=0.5)
    amplitude = np.ones(grid.shape, dtype=np.float64)
    result = _solve(grid=grid, source_amplitude=amplitude, target_amplitude=amplitude,
                    wavelength_m=1.0, distance_m=distance, iterations=1)
    np.testing.assert_allclose(result.source_field.amplitude, amplitude, rtol=5e-15, atol=0.0)


@pytest.mark.parametrize("name", ["source_amplitude", "target_amplitude", "initial_phase"])
@pytest.mark.parametrize("bad", [1.0, [[1.0]], None])
def test_gs_array_inputs_must_be_plain_arrays(name: str, bad) -> None:
    changes = {name: bad}
    if name == "initial_phase":
        changes["seed"] = None
    expected = ValueError if name == "initial_phase" and bad is None else TypeError
    with pytest.raises(expected):
        _solve(**changes)


@pytest.mark.parametrize("name", ["source_amplitude", "target_amplitude", "initial_phase"])
@pytest.mark.parametrize("dtype", [np.float32, np.int64, np.complex128, np.bool_,
                                    np.dtype(">f8" if np.little_endian else "<f8")])
def test_gs_requires_native_float64(name: str, dtype) -> None:
    changes = {name: np.ones((3, 5), dtype=dtype)}
    if name == "initial_phase":
        changes["seed"] = None
    with pytest.raises(TypeError, match="float64|dtype"):
        _solve(**changes)


@pytest.mark.parametrize("name", ["source_amplitude", "target_amplitude", "initial_phase"])
@pytest.mark.parametrize("masked", [False, True])
def test_gs_rejects_array_subclasses(name: str, masked: bool) -> None:
    class Subclass(np.ndarray):
        pass
    array = np.ones((3, 5), dtype=np.float64)
    array = np.ma.array(array) if masked else array.view(Subclass)
    changes = {name: array}
    if name == "initial_phase":
        changes["seed"] = None
    with pytest.raises(TypeError, match="plain|subclass|ndarray"):
        _solve(**changes)


@pytest.mark.parametrize("name", ["source_amplitude", "target_amplitude", "initial_phase"])
@pytest.mark.parametrize("shape", [(), (15,), (5, 3), (1, 3, 5)])
def test_gs_rejects_dimension_or_shape_mismatch(name: str, shape) -> None:
    changes = {name: np.ones(shape, dtype=np.float64)}
    if name == "initial_phase":
        changes["seed"] = None
    with pytest.raises(ValueError, match="shape|dimension"):
        _solve(**changes)


@pytest.mark.parametrize("name", ["source_amplitude", "target_amplitude", "initial_phase"])
@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_gs_rejects_nonfinite_array_elements(name: str, bad: float) -> None:
    array = np.ones((3, 5), dtype=np.float64)
    array[1, 2] = bad
    changes = {name: array}
    if name == "initial_phase":
        changes["seed"] = None
    with pytest.raises(ValueError, match="finite|NaN|Inf"):
        _solve(**changes)


@pytest.mark.parametrize("name", ["source_amplitude", "target_amplitude"])
def test_gs_rejects_negative_amplitude(name: str) -> None:
    array = np.ones((3, 5), dtype=np.float64)
    array[1, 2] = -1e-10
    with pytest.raises(ValueError, match="negative|nonnegative"):
        _solve(**{name: array})


@pytest.mark.parametrize("name", ["iterations", "seed"])
@pytest.mark.parametrize("bad", [True, np.bool_(False), 1.0, "2", -1])
def test_gs_nonnegative_integer_counts_and_seed(name: str, bad) -> None:
    expected = ValueError if isinstance(bad, int) and not isinstance(bad, bool) and bad < 0 else TypeError
    with pytest.raises(expected, match=name):
        _solve(**{name: bad})


def test_gs_numpy_integer_seed_and_zero_iterations_accepted() -> None:
    result = _solve(seed=np.int64(0), iterations=np.int64(0))
    assert result.iterations == 0


@pytest.mark.parametrize("phase,seed", [(None, None), (np.zeros((3, 5)), 0)])
def test_gs_exactly_one_initialization_required(phase, seed) -> None:
    with pytest.raises(ValueError, match="exactly one|either"):
        _solve(initial_phase=phase, seed=seed)


@pytest.mark.parametrize("name", ["wavelength_m", "distance_m"])
@pytest.mark.parametrize("bad", [True, 1j, "0.1", None, np.nan, np.inf])
def test_gs_scalar_physical_inputs_validated(name: str, bad) -> None:
    expected = ValueError if isinstance(bad, float) and not math.isfinite(bad) else TypeError
    with pytest.raises(expected, match=name):
        _solve(**{name: bad})


@pytest.mark.parametrize("bad", [0.0, -633e-9])
def test_gs_wavelength_must_be_positive(bad: float) -> None:
    with pytest.raises(ValueError, match="wavelength"):
        _solve(wavelength_m=bad)


def test_gs_grid_and_keyword_only_contract() -> None:
    with pytest.raises(TypeError, match="grid"):
        _solve(grid=(3, 5))
    with pytest.raises(TypeError):
        gerchberg_saxton(np.ones((3, 5)))


@pytest.mark.parametrize("magnitude", [1e200, 1e154, 1e-200])
def test_gs_unrepresentable_energy_is_informative_error(magnitude: float) -> None:
    array = np.full((3, 5), magnitude, dtype=np.float64)
    with pytest.raises(ValueError, match="energ|represent|arithmetic|finite"):
        _solve(source_amplitude=array, target_amplitude=array)


@pytest.mark.parametrize("pitch,amplitude,wavelength", [(1e160, 1.0, WAVELENGTH_M),
                                                        (1e-100, 1e-100, 1e-102)])
def test_gs_unrepresentable_physical_power_is_informative_error(
    pitch: float, amplitude: float, wavelength: float,
) -> None:
    grid = SamplingGrid(ny=3, nx=5, dy=pitch, dx=pitch)
    array = np.full(grid.shape, amplitude, dtype=np.float64)
    with pytest.raises(ValueError, match="power|area|represent|arithmetic|finite"):
        _solve(grid=grid, source_amplitude=array, target_amplitude=array,
               wavelength_m=wavelength)


@pytest.mark.parametrize("changes", [{"wavelength_m": 1e-200}, {"distance_m": 1e308}])
def test_gs_unusable_transfer_arithmetic_is_informative_error(changes: dict) -> None:
    with pytest.raises(ValueError, match="transfer|arithmetic|finite|represent"):
        _solve(**changes)


@pytest.mark.parametrize("shape", [(3, 5), (5, 8)])
@pytest.mark.parametrize("distance", [2e-4, -2e-4])
def test_gs_local_operator_matches_public_asm_and_its_adjoint(shape, distance) -> None:
    grid = SamplingGrid(ny=shape[0], nx=shape[1], dy=10e-6, dx=8e-6)
    rng = np.random.default_rng(63)
    u = rng.normal(size=shape) + 1j * rng.normal(size=shape)
    v = rng.normal(size=shape) + 1j * rng.normal(size=shape)
    h = angular_spectrum_transfer_function(grid, wavelength_m=WAVELENGTH_M, distance_m=distance)
    hm = angular_spectrum_transfer_function(grid, wavelength_m=WAVELENGTH_M, distance_m=-distance)
    forward = gs_module._apply_transfer(u, h, identity=False)
    backward_v = gs_module._apply_transfer(v, hm, identity=False)
    for data, signed_distance, actual in ((u, distance, forward), (v, -distance, backward_v)):
        reference = propagate_angular_spectrum(
            ComplexField(data=data, grid=grid, wavelength_m=WAVELENGTH_M),
            distance_m=signed_distance, pad_factor=1,
        )
        np.testing.assert_allclose(actual, reference.data, rtol=1e-12,
                                   atol=1e-13 * np.abs(data).max())
    restored = gs_module._apply_transfer(forward, hm, identity=False)
    np.testing.assert_allclose(restored, u, rtol=1e-12, atol=1e-13 * np.abs(u).max())
    # Inner-product identity checks the adjoint, not only a self-cancelling round trip.
    inner_scale = float(np.linalg.norm(u) * np.linalg.norm(v))
    np.testing.assert_allclose(np.vdot(forward, v), np.vdot(u, backward_v),
                               rtol=1e-12, atol=1e-13 * inner_scale)


@pytest.mark.parametrize("iterations,distance", [(0, 0.0), (0, 2e-4), (4, -2e-4)])
def test_gs_transfer_functions_constructed_once_per_direction(monkeypatch, iterations, distance) -> None:
    original = gs_module.angular_spectrum_transfer_function
    calls = []
    def tracked(grid, *, wavelength_m, distance_m):
        calls.append(distance_m)
        return original(grid, wavelength_m=wavelength_m, distance_m=distance_m)
    monkeypatch.setattr(gs_module, "angular_spectrum_transfer_function", tracked)
    _solve(iterations=iterations, distance_m=distance)
    assert calls == [distance, -distance]


def test_gs_zero_distance_does_not_run_fft(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        pytest.fail("zero-distance propagation must be the exact identity")
    monkeypatch.setattr(gs_module.np.fft, "fft2", forbidden)
    monkeypatch.setattr(gs_module.np.fft, "ifft2", forbidden)
    _solve(distance_m=0.0, iterations=3)


PREDECLARED_CASES = (
    ("smooth_spot_64", 64, 64, 8e-6, 8e-6, "spot"),
    ("two_features_64", 64, 64, 8e-6, 8e-6, "two"),
    ("two_features_rect", 48, 64, 10e-6, 8e-6, "two"),
)


def _predeclared_problem(case):
    """Exact approved planning fixture, including quantization and illumination.

    Preserved independently from scripts/probe_m3_evidence.py. Planning used
    sqrt(mean(decoded intensity)); the demo separately uses the documented
    sqrt(sum(target amplitude**2)/size). Neither operation is in the solver.
    """
    name, ny, nx, dy, dx, kind = case
    grid = SamplingGrid(ny=ny, nx=nx, dy=dy, dx=dx)
    x, y = grid.meshgrid()
    if kind == "spot":
        design = np.exp(-0.5 * ((x / 60e-6)**2 + (y / 60e-6)**2))
    else:
        design = (
            0.65 * np.exp(-0.5 * (((x + 80e-6) / 32e-6)**2 + ((y + 48e-6) / 40e-6)**2))
            + 0.35 * np.exp(-0.5 * (((x - 72e-6) / 40e-6)**2 + ((y - 64e-6) / 28e-6)**2))
        )
    codes = np.rint(255.0 * design).astype(np.uint8)
    intensity = grayscale8_to_intensity(codes, grid=grid)
    target = intensity_to_amplitude(intensity, grid=grid)
    source = np.full(grid.shape, np.sqrt(np.mean(intensity)), dtype=np.float64)
    return name, grid, codes, intensity, target, source


@pytest.mark.parametrize("case", PREDECLARED_CASES, ids=[c[0] for c in PREDECLARED_CASES])
@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_gs_all_predeclared_fixtures_and_seeds_improve(case, seed: int) -> None:
    _, grid, _, _, target, source = _predeclared_problem(case)
    result = gerchberg_saxton(
        target_amplitude=target, source_amplitude=source, grid=grid,
        wavelength_m=WAVELENGTH_M, distance_m=5e-3, iterations=50, seed=seed,
    )
    assert result.residual_history.shape == (51,)
    assert result.residual_history[-1] < 0.05
    assert result.residual_history[-1] < 0.1 * result.residual_history[0]
    np.testing.assert_allclose(result.source_field.amplitude, source, rtol=5e-15, atol=0.0)
    input_power = float(np.sum(source**2) * grid.pixel_area)
    np.testing.assert_allclose([result.source_field.power, result.reconstruction.power],
                               input_power, rtol=5e-15, atol=0.0)
    # These criteria concern these 12 fixed cases, not arbitrary images.


def test_gs_real_png_path_matches_quantized_array_target(tmp_path: Path) -> None:
    _, grid, codes, intensity, target, source = _predeclared_problem(PREDECLARED_CASES[0])
    path = tmp_path / "target.png"
    Image.fromarray(codes).save(path)
    saved = path.read_bytes()
    decoded = load_target_intensity(path, grid=grid)
    assert_bit_identical(decoded, intensity)  # lossless codes and fixed /255
    decoded_amplitude = intensity_to_amplitude(decoded, grid=grid)
    assert_bit_identical(decoded_amplitude, target)
    arguments = dict(source_amplitude=source, grid=grid, wavelength_m=WAVELENGTH_M,
                     distance_m=5e-3, iterations=50, seed=0)
    file_result = gerchberg_saxton(target_amplitude=decoded_amplitude, **arguments)
    array_result = gerchberg_saxton(target_amplitude=target, **arguments)
    assert_bit_identical(file_result.source_field.data, array_result.source_field.data)
    assert_bit_identical(file_result.residual_history, array_result.residual_history)
    assert path.read_bytes() == saved
