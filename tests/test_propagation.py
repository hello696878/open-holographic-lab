"""Mechanics of Angular Spectrum propagation (Milestone 1, IDs M-01 .. M-30).

Covers the transfer function, validation, the zero-distance contract, the
evanescent policy, padding/cropping alignment, power bookkeeping, and
wrap-around. Analytic ground truth lives in ``test_propagation_analytic.py``.

Two conventions govern the tests here.

**Padding semantics.** ``pad_factor=1`` propagates on the original periodic
DFT window; ``pad_factor>1`` embeds the field in a larger zero-valued window,
which is a *different boundary condition*, not a strictly better one. Tests
that assert an exact analytic identity therefore use ``pad_factor=1``, and
padding is exercised separately with compact fields whose support sits well
inside the original window.

**|H| = 1 is a mathematical statement, not a bitwise one.** Measured worst-case
deviation of ``abs(exp(i*theta))`` from 1 is 2.220e-16, exactly one float64
epsilon, so the propagating branch is asserted with an explicit
machine-precision tolerance rather than an exact inequality.

**Phase tolerances must scale with distance.** Comparing two values of
``exp(i*kz*z)`` is limited by the rounding of the *angle*, not of the
exponential: ``kz*z`` reaches 9.9e4 rad at z = 10 mm and 9.9e5 rad at
z = 100 mm, so its own float64 representation carries an absolute error of
``|kz*z| * eps``, and ``|exp(i*a) - exp(i*b)| ~ |a - b|``. A fixed ``atol``
would fail for reasons unrelated to correctness. :func:`_phase_tolerance`
encodes this, with a 100x margin over the bare estimate.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from _helpers import assert_bit_identical
from ohlab.field import ComplexField
from ohlab.grid import SamplingGrid
from ohlab.propagation import (
    _crop,
    _evanescent_mask,
    _pad_offset,
    _padded_grid,
    _zero_pad,
    angular_spectrum_transfer_function,
    propagate_angular_spectrum,
)
from ohlab.units import MM, NM, UM

# A pitch strictly between lambda/2 (316.50 nm) and lambda/sqrt(2) (447.60 nm)
# at 633 nm. On a square grid of this pitch, evanescent samples exist ONLY
# near the four corners of the frequency mesh: neither axis reaches the
# evanescent region. This is the case an axis-only "d < lambda/2" rule misses.
CORNER_ONLY_PITCH_M = 400 * NM


def _phase_tolerance(
    wavelength_m: float, distance_m: float, factor: float = 100.0
) -> float:
    """Absolute tolerance for comparing two ``exp(i*kz*z)`` values.

    The accumulated angle ``kz*z`` is at most ``k*|z|``. Representing that
    angle in float64 costs ``|k*z| * eps`` in absolute terms, and since
    ``|exp(i*a) - exp(i*b)|`` is approximately ``|a - b|`` for small
    differences, that rounding sets the achievable agreement floor.

    ``factor`` is the safety margin over the bare estimate. A propagation sign
    error produces a discrepancy of order 2, roughly ten orders of magnitude
    larger than this bound at every distance tested.
    """
    k = 2.0 * math.pi / wavelength_m
    return factor * abs(k * distance_m) * float(np.finfo(np.float64).eps)


@pytest.fixture
def prop_grid() -> SamplingGrid:
    """A realistic anisotropic grid carrying no evanescent samples."""
    return SamplingGrid(ny=48, nx=64, dy=5.0 * UM, dx=3.74 * UM)


# ---------------------------------------------------------------------------
# Transfer function
# ---------------------------------------------------------------------------
def test_m01_transfer_function_shape_dtype_and_ordering(
    prop_grid: SamplingGrid, wavelength: float
) -> None:
    """M-01: H has the grid's shape, is complex128, and is FFT-ordered.

    FFT ordering means the zero-frequency sample is at index ``[0, 0]``, where
    ``kz = k`` and the phase is the on-axis carrier ``k*z``.

    Tolerance from :func:`_phase_tolerance`: at z = 1 mm the angle is
    ``k*z = 9.9e3`` rad, whose float64 rounding alone is 2.2e-12.
    """
    z = 1.0 * MM
    h = angular_spectrum_transfer_function(
        prop_grid, wavelength_m=wavelength, distance_m=z
    )
    assert h.shape == prop_grid.shape
    assert h.dtype == np.complex128
    expected_dc = np.exp(1j * (2 * math.pi / wavelength) * z)
    np.testing.assert_allclose(
        h[0, 0], expected_dc, rtol=0.0, atol=_phase_tolerance(wavelength, z)
    )


def test_m02_transfer_function_is_exactly_unity_at_zero_distance(
    prop_grid: SamplingGrid, wavelength: float
) -> None:
    """M-02: ``H(z=0) == 1 + 0j`` exactly.

    EXACTNESS IS THE PROPERTY UNDER TEST: ``exp(1j * kz * 0.0)`` is exactly
    ``1+0j`` for every finite ``kz``, so any deviation would indicate the
    distance is not being applied as a plain multiplication.
    """
    h = angular_spectrum_transfer_function(
        prop_grid, wavelength_m=wavelength, distance_m=0.0
    )
    assert_bit_identical(h, np.ones(prop_grid.shape, dtype=np.complex128))


@pytest.mark.parametrize("z", [1e-5, 1e-3, 0.05, 1.0, -1e-3, -0.05, -1.0])
def test_m03_propagating_branch_has_unit_modulus(
    prop_grid: SamplingGrid, wavelength: float, z: float
) -> None:
    """M-03: |H| = 1 for every propagating sample, both signs of z.

    Tolerance ``atol=1e-12`` rather than an exact ``<= 1``: measured worst-case
    deviation of ``abs(exp(i*theta))`` from 1 across grids and distances is
    2.220e-16 (one float64 epsilon), and bitwise behaviour of ``exp`` is not
    guaranteed identical across platforms. 1e-12 is ~4500x the measured
    deviation while an evanescent-branch sign error would be O(1) or larger.
    """
    assert not _evanescent_mask(prop_grid, wavelength).any()
    h = angular_spectrum_transfer_function(
        prop_grid, wavelength_m=wavelength, distance_m=z
    )
    np.testing.assert_allclose(np.abs(h), 1.0, rtol=0.0, atol=1e-12)


def test_m04_transfer_function_conjugates_under_distance_reversal(
    prop_grid: SamplingGrid, wavelength: float
) -> None:
    """M-04: ``H(-z) == conj(H(z))`` on this all-propagating mesh.

    The identity requires real kz; it is not true for evanescent components.
    M-11/M-12 separately check forward evanescent decay and refusal to reverse
    it. Existing tolerances rtol=1e-12, atol=1e-14 absorb unit-scale roundoff;
    a second expression with a sign slip would be O(1) wrong.
    """
    z = 12.0 * MM
    forward = angular_spectrum_transfer_function(
        prop_grid, wavelength_m=wavelength, distance_m=z
    )
    backward = angular_spectrum_transfer_function(
        prop_grid, wavelength_m=wavelength, distance_m=-z
    )
    np.testing.assert_allclose(backward, np.conj(forward), rtol=1e-12, atol=1e-14)


def test_m05_transfer_function_composes_over_distance(
    prop_grid: SamplingGrid, wavelength: float
) -> None:
    """M-05: ``H(z1) * H(z2) == H(z1 + z2)``.

    A semigroup property that follows from ``exp(a)exp(b) = exp(a+b)``. It
    fails immediately if the distance enters anywhere other than linearly in
    the exponent.

    Tolerance from :func:`_phase_tolerance` at the *total* distance: the two
    sides accumulate ``kz*(z1+z2) ~ 9.9e4`` rad, whose rounding alone is
    2.2e-11. Measured discrepancy 1.5e-11.
    """
    z1, z2 = 3.0 * MM, 7.0 * MM
    h1 = angular_spectrum_transfer_function(
        prop_grid, wavelength_m=wavelength, distance_m=z1
    )
    h2 = angular_spectrum_transfer_function(
        prop_grid, wavelength_m=wavelength, distance_m=z2
    )
    h12 = angular_spectrum_transfer_function(
        prop_grid, wavelength_m=wavelength, distance_m=z1 + z2
    )
    np.testing.assert_allclose(
        h1 * h2, h12, rtol=0.0, atol=_phase_tolerance(wavelength, z1 + z2)
    )


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"wavelength_m": 0.0, "distance_m": 1e-3}, ValueError),
        ({"wavelength_m": -633e-9, "distance_m": 1e-3}, ValueError),
        ({"wavelength_m": float("nan"), "distance_m": 1e-3}, ValueError),
        ({"wavelength_m": 633e-9, "distance_m": float("inf")}, ValueError),
        ({"wavelength_m": 633e-9, "distance_m": float("nan")}, ValueError),
        ({"wavelength_m": "633nm", "distance_m": 1e-3}, TypeError),
    ],
)
def test_m06_transfer_function_validates_parameters(
    prop_grid: SamplingGrid, kwargs: dict[str, object], expected: type[Exception]
) -> None:
    """M-06: invalid wavelength or distance is rejected."""
    with pytest.raises(expected):
        angular_spectrum_transfer_function(prop_grid, **kwargs)  # type: ignore[arg-type]


def test_m07_transfer_function_requires_a_sampling_grid(wavelength: float) -> None:
    """M-07: ``grid`` must be a SamplingGrid, not a bare shape tuple."""
    with pytest.raises(TypeError, match="SamplingGrid"):
        angular_spectrum_transfer_function(
            (8, 8), wavelength_m=wavelength, distance_m=1e-3  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Evanescent policy
# ---------------------------------------------------------------------------
def test_m08_evanescent_detection_uses_the_discrete_mesh_not_a_pitch_rule(
    wavelength: float,
) -> None:
    """M-08: REGRESSION. Corner-only evanescent samples must be detected.

    At 633 nm, ``lambda/2 = 316.50 nm`` and ``lambda/sqrt(2) = 447.60 nm``. A
    square grid of pitch 400 nm lies strictly between them, so:

    * neither axis reaches the evanescent region -- the axis Nyquist frequency
      is 1.2500e6 < 1/lambda = 1.5798e6;
    * but the *corner* of the Nyquist square sits at radius 1.7678e6 > 1/lambda,
      so 97 of the 4096 samples ARE evanescent.

    An implementation testing ``d < lambda/2`` would report "no evanescent
    samples" here and then silently amplify them under backward propagation.
    The mesh is the source of truth.
    """
    grid = SamplingGrid.square(n=64, pitch=CORNER_ONLY_PITCH_M)

    # The axis-only rule says "no evanescent samples" ...
    assert grid.nyquist_fx < 1.0 / wavelength
    assert CORNER_ONLY_PITCH_M > wavelength / 2.0
    # ... but the corner of the mesh crosses the cutoff.
    assert math.hypot(grid.nyquist_fx, grid.nyquist_fy) > 1.0 / wavelength
    assert CORNER_ONLY_PITCH_M < wavelength / math.sqrt(2.0)

    mask = _evanescent_mask(grid, wavelength)
    assert mask.any()
    assert 0 < int(mask.sum()) < mask.size // 8  # a small corner population

    # And they really are only at the corners: no evanescent sample lies on
    # either frequency axis.
    fx, fy = grid.freq_meshgrid(order="fft")
    assert not mask[fy == 0.0].any()
    assert not mask[fx == 0.0].any()


def test_m09_no_evanescent_samples_on_realistic_grids(
    prop_grid: SamplingGrid, wavelength: float
) -> None:
    """M-09: micrometre-scale pitches carry no evanescent samples at all."""
    for pitch in (3.74 * UM, 8.0 * UM, 1.0 * UM, 0.5 * UM):
        grid = SamplingGrid.square(n=64, pitch=pitch)
        assert not _evanescent_mask(grid, wavelength).any()
    assert not _evanescent_mask(prop_grid, wavelength).any()


def test_m10_anisotropic_grid_has_no_scalar_pitch_threshold(
    wavelength: float,
) -> None:
    """M-10: on an anisotropic grid the corner radius mixes both pitches.

    ``dy = 500 nm`` alone and ``dx = 350 nm`` alone imply different verdicts;
    only the combined mesh radius decides. There is no single ``d``.
    """
    grid = SamplingGrid(ny=32, nx=32, dy=500 * NM, dx=350 * NM)
    corner = math.hypot(grid.nyquist_fx, grid.nyquist_fy)
    assert corner > 1.0 / wavelength
    assert _evanescent_mask(grid, wavelength).any()

    coarse = SamplingGrid(ny=32, nx=32, dy=1000 * NM, dx=400 * NM)
    assert math.hypot(coarse.nyquist_fx, coarse.nyquist_fy) < 1.0 / wavelength
    assert not _evanescent_mask(coarse, wavelength).any()


@pytest.mark.parametrize("pitch", [CORNER_ONLY_PITCH_M, 250 * NM])
def test_m11_evanescent_components_decay_forward_and_never_grow(
    wavelength: float, pitch: float
) -> None:
    """M-11: for z > 0, evanescent samples decay and nothing exceeds unity.

    Checked separately from the propagating branch (M-03), because the
    evanescent branch is where a wrong square-root branch would produce
    exponential *growth* rather than a tiny modulus error.

    Also asserts no NumPy warning is emitted: the suite runs with
    ``filterwarnings = ["error"]``, and a naive implementation emits
    ``overflow encountered in exp`` here.
    """
    grid = SamplingGrid.square(n=64, pitch=pitch)
    mask = _evanescent_mask(grid, wavelength)
    assert mask.any()

    previous = None
    for z in (1e-8, 1e-7, 1e-6):
        h = angular_spectrum_transfer_function(
            grid, wavelength_m=wavelength, distance_m=z
        )
        assert np.all(np.isfinite(h))
        magnitudes = np.abs(h[mask])
        assert np.all(magnitudes <= 1.0 + 1e-12)
        assert np.all(magnitudes < 1.0)  # strictly decaying
        if previous is not None:
            assert np.all(magnitudes <= previous + 1e-15)  # monotone in z
        previous = magnitudes


@pytest.mark.parametrize("pitch", [CORNER_ONLY_PITCH_M, 250 * NM])
def test_m12_backward_propagation_is_refused_when_evanescent_samples_exist(
    wavelength: float, pitch: float
) -> None:
    """M-12: ``z < 0`` on an evanescent grid raises rather than overflowing.

    The corner-only pitch is included deliberately: this is exactly the case a
    ``d < lambda/2`` rule would wave through.
    """
    grid = SamplingGrid.square(n=64, pitch=pitch)
    with pytest.raises(ValueError, match="evanescent"):
        angular_spectrum_transfer_function(
            grid, wavelength_m=wavelength, distance_m=-1e-6
        )
    field = ComplexField.uniform(grid=grid, wavelength_m=wavelength)
    with pytest.raises(ValueError, match="evanescent"):
        propagate_angular_spectrum(field, distance_m=-1e-6, pad_factor=1)


def test_m13_backward_propagation_allowed_without_evanescent_samples(
    prop_grid: SamplingGrid, wavelength: float
) -> None:
    """M-13: the refusal is targeted, not a blanket ban on negative distance."""
    field = ComplexField.random_phase(
        grid=prop_grid, wavelength_m=wavelength, seed=1
    )
    out = propagate_angular_spectrum(field, distance_m=-5.0 * MM, pad_factor=1)
    assert out.shape == prop_grid.shape


def test_m14_forward_propagation_allowed_on_an_evanescent_grid(
    wavelength: float,
) -> None:
    """M-14: forward propagation is fine even when evanescent samples exist."""
    grid = SamplingGrid.square(n=32, pitch=CORNER_ONLY_PITCH_M)
    field = ComplexField.random_phase(grid=grid, wavelength_m=wavelength, seed=2)
    out = propagate_angular_spectrum(field, distance_m=1e-6, pad_factor=1)
    assert np.all(np.isfinite(out.data))


# ---------------------------------------------------------------------------
# Zero-distance contract
# ---------------------------------------------------------------------------
def test_m15_zero_distance_returns_the_same_object(
    prop_grid: SamplingGrid, wavelength: float
) -> None:
    """M-15: the documented zero-distance contract.

    ``propagate_angular_spectrum(field, distance_m=0.0)`` returns **the input
    object itself**. ComplexField is immutable, so this is safe, and it makes
    the identity exact instead of accurate to ~1.6e-15 through an FFT pair.
    The contract is asserted with ``is`` so it cannot drift.
    """
    field = ComplexField.random_phase(
        grid=prop_grid, wavelength_m=wavelength, seed=4
    )
    for factor in (1, 2, 3):
        result = propagate_angular_spectrum(
            field, distance_m=0.0, pad_factor=factor
        )
        assert result is field


def test_m16_zero_distance_negative_zero_is_also_the_identity(
    prop_grid: SamplingGrid, wavelength: float
) -> None:
    """M-16: ``-0.0 == 0.0`` in IEEE-754, so it takes the identity path too."""
    field = ComplexField.uniform(grid=prop_grid, wavelength_m=wavelength)
    assert propagate_angular_spectrum(field, distance_m=-0.0) is field


# ---------------------------------------------------------------------------
# Padding and cropping alignment
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("n", [7, 8, 9, 16, 17])
@pytest.mark.parametrize("factor", [1, 2, 3])
def test_m17_pad_offset_preserves_the_origin_index(n: int, factor: int) -> None:
    """M-17: original index ``n//2`` maps to padded index ``n_pad//2``.

    This is the Milestone 0 coordinate-origin convention surviving padding.
    EXACTNESS IS THE PROPERTY UNDER TEST -- these are integer indices.
    """
    n_padded = factor * n
    before = _pad_offset(n, n_padded)
    after = n_padded - n - before
    assert before >= 0
    assert after >= 0
    assert n // 2 + before == n_padded // 2


@pytest.mark.parametrize(
    ("ny", "nx", "factor"),
    [(8, 8, 2), (7, 7, 2), (7, 8, 2), (8, 7, 2), (6, 10, 3), (9, 16, 2), (16, 9, 3)],
)
def test_m18_padded_grid_coordinates_agree_bit_exactly(
    ny: int, nx: int, factor: int
) -> None:
    """M-18: physical coordinates are unchanged at the shared samples.

    Covers even, odd, mixed-parity and anisotropic shapes. EXACTNESS IS THE
    PROPERTY UNDER TEST: padding must not move a single sample by half a
    pixel, which is precisely the failure mode ``numpy.pad``'s default
    placement would introduce for odd sizes.
    """
    grid = SamplingGrid(ny=ny, nx=nx, dy=5.0 * UM, dx=3.74 * UM)
    padded = _padded_grid(grid, factor)
    row0 = _pad_offset(grid.ny, padded.ny)
    col0 = _pad_offset(grid.nx, padded.nx)

    assert_bit_identical(padded.x[col0 : col0 + nx], grid.x)
    assert_bit_identical(padded.y[row0 : row0 + ny], grid.y)
    assert padded.dx == grid.dx
    assert padded.dy == grid.dy
    # The origin sample coincides.
    assert padded.x[padded.nx // 2] == grid.x[grid.nx // 2] == 0.0


@pytest.mark.parametrize(
    ("ny", "nx", "factor"),
    [(8, 8, 2), (7, 7, 2), (7, 8, 2), (8, 7, 3), (6, 10, 2), (17, 9, 2)],
)
def test_m19_crop_of_pad_recovers_the_field_bit_exactly(
    ny: int, nx: int, factor: int, rng: np.random.Generator
) -> None:
    """M-19: ``crop(pad(U)) == U`` bit for bit, at every parity combination.

    EXACTNESS IS THE PROPERTY UNDER TEST: padding and cropping only move data,
    they do not compute. A one-sample misalignment shows up here immediately.
    """
    grid = SamplingGrid(ny=ny, nx=nx, dy=5.0 * UM, dx=3.74 * UM)
    padded = _padded_grid(grid, factor)
    data = (rng.standard_normal(grid.shape) + 1j * rng.standard_normal(grid.shape))

    embedded = _zero_pad(data, grid, padded)
    assert embedded.shape == padded.shape
    assert_bit_identical(_crop(embedded, grid, padded), data)

    # Everything outside the embedded window really is zero.
    total = np.count_nonzero(embedded)
    assert total <= data.size


def test_m20_pad_factor_one_is_a_no_op(
    prop_grid: SamplingGrid, rng: np.random.Generator
) -> None:
    """M-20: ``pad_factor=1`` neither enlarges nor copies unnecessarily."""
    padded = _padded_grid(prop_grid, 1)
    assert padded is prop_grid
    data = rng.standard_normal(prop_grid.shape).astype(np.complex128)
    assert _zero_pad(data, prop_grid, padded) is data
    assert _crop(data, prop_grid, padded) is data


@pytest.mark.parametrize("bad", [0, -1, 2.0, "2", True])
def test_m21_pad_factor_is_validated(
    prop_grid: SamplingGrid, wavelength: float, bad: object
) -> None:
    """M-21: ``pad_factor`` must be a positive integer (and not a bool)."""
    field = ComplexField.uniform(grid=prop_grid, wavelength_m=wavelength)
    with pytest.raises((ValueError, TypeError)):
        propagate_angular_spectrum(
            field, distance_m=1e-3, pad_factor=bad  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# propagate_angular_spectrum: types, shapes, validation
# ---------------------------------------------------------------------------
def test_m22_output_type_shape_grid_and_wavelength(
    prop_grid: SamplingGrid, wavelength: float
) -> None:
    """M-22: the result is a ComplexField on the same grid and wavelength."""
    field = ComplexField.random_phase(
        grid=prop_grid, wavelength_m=wavelength, seed=6
    )
    out = propagate_angular_spectrum(field, distance_m=2.0 * MM)
    assert isinstance(out, ComplexField)
    assert out.shape == prop_grid.shape
    assert out.grid == prop_grid
    assert out.wavelength_m == wavelength
    assert out.data.dtype == np.complex128
    assert out.data.flags.writeable is False


def test_m23_source_field_is_not_mutated(
    prop_grid: SamplingGrid, wavelength: float
) -> None:
    """M-23: propagation is pure; the input is untouched."""
    field = ComplexField.random_phase(
        grid=prop_grid, wavelength_m=wavelength, seed=7
    )
    snapshot = field.data.copy()
    propagate_angular_spectrum(field, distance_m=5.0 * MM)
    assert_bit_identical(field.data, snapshot)


def test_m24_input_type_is_validated(wavelength: float) -> None:
    """M-24: a bare array is not a field."""
    with pytest.raises(TypeError, match="ComplexField"):
        propagate_angular_spectrum(
            np.ones((8, 8), dtype=np.complex128), distance_m=1e-3  # type: ignore[arg-type]
        )


def test_m25_distance_is_keyword_only(
    prop_grid: SamplingGrid, wavelength: float
) -> None:
    """M-25: distance cannot be passed positionally, so units cannot be
    confused with the field argument."""
    field = ComplexField.uniform(grid=prop_grid, wavelength_m=wavelength)
    with pytest.raises(TypeError):
        propagate_angular_spectrum(field, 1e-3)  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Power bookkeeping
# ---------------------------------------------------------------------------
def test_m26_power_is_conserved_exactly_on_the_periodic_window(
    prop_grid: SamplingGrid, wavelength: float, rng: np.random.Generator
) -> None:
    """M-26: with ``pad_factor=1`` and no evanescent samples, power is conserved.

    Evidence class: conservation law. Every propagating sample has |H| = 1, so
    by Parseval the total power over the periodic computational window is
    invariant. This is an *exact* statement for this configuration, and it is
    asserted only for it -- see M-27 for what happens with padding.

    Tolerance ``rtol=1e-12``; measured 2.8e-16.
    """
    assert not _evanescent_mask(prop_grid, wavelength).any()
    data = rng.standard_normal(prop_grid.shape) + 1j * rng.standard_normal(
        prop_grid.shape
    )
    field = ComplexField(data=data, grid=prop_grid, wavelength_m=wavelength)
    for z in (1.0 * MM, 50.0 * MM, 500.0 * MM, -20.0 * MM):
        out = propagate_angular_spectrum(field, distance_m=z, pad_factor=1)
        np.testing.assert_allclose(out.power, field.power, rtol=1e-12, atol=0.0)


def test_m27_cropped_power_does_not_exceed_source_power(
    wavelength: float,
) -> None:
    """M-27: with padding, power in the cropped window can only decrease.

    This is physically correct -- light that left the original window is no
    longer counted -- and it is deliberately asserted as an inequality. It
    would be wrong to call this "conservation".
    """
    grid = SamplingGrid.square(n=128, pitch=8.0 * UM)
    x_grid, y_grid = grid.meshgrid()
    compact = np.exp(-(x_grid**2 + y_grid**2) / (60 * UM) ** 2)
    field = ComplexField(
        data=compact.astype(np.complex128), grid=grid, wavelength_m=wavelength
    )
    previous = field.power
    for z in (5.0 * MM, 25.0 * MM, 100.0 * MM):
        out = propagate_angular_spectrum(field, distance_m=z, pad_factor=2)
        assert out.power <= field.power * (1.0 + 1e-12)
        previous = out.power
    assert previous < field.power  # light really did leave the window


# ---------------------------------------------------------------------------
# Round trip (secondary evidence only)
# ---------------------------------------------------------------------------
def test_m28_round_trip_recovers_the_source(
    prop_grid: SamplingGrid, wavelength: float, rng: np.random.Generator
) -> None:
    """M-28: forward then backward recovers the field, with ``pad_factor=1``.

    SECONDARY EVIDENCE ONLY. This test is invariant under a global sign flip
    of the transfer function, because ``H(-z) = conj(H(z))`` whichever sign is
    used -- a wrong propagator cancels itself here. The analytic plane-wave
    tests carry the weight for the sign; see ``test_propagation_analytic.py``.

    ``pad_factor=1`` because the round trip is only an identity on the
    periodic window: with padding, light that left the window during the
    forward step cannot return.

    Tolerance ``rtol=1e-11``; measured 7.5e-16.
    """
    data = rng.standard_normal(prop_grid.shape) + 1j * rng.standard_normal(
        prop_grid.shape
    )
    field = ComplexField(data=data, grid=prop_grid, wavelength_m=wavelength)
    for z in (1.0 * MM, 50.0 * MM, 500.0 * MM):
        forward = propagate_angular_spectrum(field, distance_m=z, pad_factor=1)
        back = propagate_angular_spectrum(forward, distance_m=-z, pad_factor=1)
        assert back.allclose(field, rtol=1e-11, atol=1e-11)


def test_m29_two_hops_equal_one_long_hop(
    prop_grid: SamplingGrid, wavelength: float, rng: np.random.Generator
) -> None:
    """M-29: propagating z1 then z2 equals propagating z1+z2 (pad_factor=1).

    The field-level counterpart of M-05. Like the round trip, it cannot detect
    a global sign reversal: exp(-i*kz*z) also composes over distance. It checks
    composition, which non-linear distance dependence or a per-call constant
    can break. The independent analytic tests carry the propagation-sign claim.
    """
    data = rng.standard_normal(prop_grid.shape) + 1j * rng.standard_normal(
        prop_grid.shape
    )
    field = ComplexField(data=data, grid=prop_grid, wavelength_m=wavelength)
    z1, z2 = 4.0 * MM, 9.0 * MM
    stepwise = propagate_angular_spectrum(
        propagate_angular_spectrum(field, distance_m=z1, pad_factor=1),
        distance_m=z2,
        pad_factor=1,
    )
    direct = propagate_angular_spectrum(field, distance_m=z1 + z2, pad_factor=1)
    assert stepwise.allclose(direct, rtol=1e-10, atol=1e-11)


# ---------------------------------------------------------------------------
# Wrap-around
# ---------------------------------------------------------------------------
def test_m30_padding_reduces_circular_wrap_around(wavelength: float) -> None:
    """M-30: padding materially reduces wrap-around for a compact source.

    A compact Gaussian is propagated far enough that, unpadded, diffracted
    light reaches the window edge and re-enters from the opposite side. The
    padded result is compared against the analytic Gaussian solution, which is
    an *independent* reference rather than another numerical run.

    The assertion is that padding improves agreement by at least 100x. It is
    deliberately not a claim that padding is correct in general: padding
    changes the boundary condition from periodic to zero-embedded, and once
    light reaches the padded edge it wraps again.
    """
    grid = SamplingGrid.square(n=256, pitch=3.74 * UM)
    w0 = 40.0 * UM
    k = 2.0 * math.pi / wavelength
    rayleigh = math.pi * w0**2 / wavelength
    x_grid, y_grid = grid.meshgrid()
    r_sq = x_grid**2 + y_grid**2
    field = ComplexField(
        data=np.exp(-r_sq / w0**2).astype(np.complex128),
        grid=grid,
        wavelength_m=wavelength,
    )

    z = 50.0 * MM
    w_z = w0 * math.sqrt(1.0 + (z / rayleigh) ** 2)
    radius_z = z * (1.0 + (rayleigh / z) ** 2)
    gouy = math.atan2(z, rayleigh)
    analytic = (
        (w0 / w_z)
        * np.exp(-r_sq / w_z**2)
        * np.exp(1j * (k * z + k * r_sq / (2.0 * radius_z) - gouy))
    )
    scale = float(np.max(np.abs(analytic)))

    unpadded = propagate_angular_spectrum(field, distance_m=z, pad_factor=1)
    padded = propagate_angular_spectrum(field, distance_m=z, pad_factor=2)

    err_unpadded = float(np.max(np.abs(unpadded.data - analytic))) / scale
    err_padded = float(np.max(np.abs(padded.data - analytic))) / scale

    assert err_unpadded > 1e-3, f"expected visible wrap-around, got {err_unpadded:.3e}"
    assert err_padded < err_unpadded / 100.0, (
        f"padding should improve agreement by >100x: "
        f"unpadded={err_unpadded:.3e} padded={err_padded:.3e}"
    )
