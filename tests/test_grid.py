"""Tests for :class:`ohlab.grid.SamplingGrid` (Milestone 0, IDs G-01 .. G-27).

Every test is parametrized over even and odd sample counts wherever centring
matters, and over a round pitch (``1.0``) and a realistic one (``3.74e-6``)
wherever floating-point association matters. The realistic pitch is essential:
at ``d = 1.0`` the division and reciprocal-multiply forms of the frequency
axis coincide bit for bit, which would mask the very bug the bit-identity
tests exist to catch.

Normative reference: ``docs/math_conventions.md`` sections 3.3, 3.4, 3.5, 3.8.
"""

from __future__ import annotations

import dataclasses
import json
import math

import numpy as np
import pytest

from _helpers import assert_bit_identical
from ohlab.grid import SamplingGrid
from ohlab.units import NM, UM

# Even and odd counts; realistic and round pitches.
COUNTS = [7, 8]
PITCHES = [1.0, 3.74e-6]


@pytest.fixture(params=COUNTS, ids=lambda n: f"n{n}")
def n(request: pytest.FixtureRequest) -> int:
    """Sample count, exercised at both parities."""
    return int(request.param)


@pytest.fixture(params=PITCHES, ids=lambda d: f"d{d:g}")
def d(request: pytest.FixtureRequest) -> float:
    """Pixel pitch in metres, round and realistic."""
    return float(request.param)


# ---------------------------------------------------------------------------
# Construction and validation
# ---------------------------------------------------------------------------
def test_g01_shape_is_ny_nx(aniso_grid: SamplingGrid) -> None:
    """G-01: ``shape`` is ``(ny, nx)`` -- rows first (section 3.3)."""
    assert aniso_grid.shape == (6, 10)
    assert aniso_grid.shape == (aniso_grid.ny, aniso_grid.nx)


def test_g02_extent_and_pixel_area(aniso_grid: SamplingGrid) -> None:
    """G-02: extents and pixel area are the plain products of the parameters.

    Exact comparison is correct: each is a single float multiplication, so the
    test and the implementation must produce identical bits.
    """
    assert aniso_grid.extent_y == 6 * 5.0 * UM
    assert aniso_grid.extent_x == 10 * 3.74 * UM
    assert aniso_grid.pixel_area == (5.0 * UM) * (3.74 * UM)


def test_g02b_extent_counts_full_cells(aniso_grid: SamplingGrid) -> None:
    """G-02b: ``extent == x[-1] - x[0] + dx`` (section 3.4).

    Tolerance ``rtol=1e-12`` because the right-hand side involves a difference
    of coordinates that can lose a unit in the last place.
    """
    x = aniso_grid.x
    np.testing.assert_allclose(
        aniso_grid.extent_x, x[-1] - x[0] + aniso_grid.dx, rtol=1e-12, atol=0.0
    )


def test_g03_positional_construction_is_rejected() -> None:
    """G-03: the constructor is keyword-only (section 3.3).

    This makes ``SamplingGrid(nx, ny, dx, dy)`` -- the classic transposition --
    impossible to write rather than merely discouraged.
    """
    with pytest.raises(TypeError):
        SamplingGrid(8, 8, 1e-6, 1e-6)  # type: ignore[misc]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ny": 0, "nx": 8, "dy": 1e-6, "dx": 1e-6},
        {"ny": 8, "nx": -3, "dy": 1e-6, "dx": 1e-6},
        {"ny": 8, "nx": 8, "dy": 0.0, "dx": 1e-6},
        {"ny": 8, "nx": 8, "dy": 1e-6, "dx": -1e-6},
        {"ny": 8, "nx": 8, "dy": float("nan"), "dx": 1e-6},
        {"ny": 8, "nx": 8, "dy": 1e-6, "dx": float("inf")},
    ],
)
def test_g04_invalid_parameters_rejected(kwargs: dict[str, object]) -> None:
    """G-04: out-of-range counts and pitches raise ``ValueError``."""
    with pytest.raises(ValueError):
        SamplingGrid(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ny": 8.0, "nx": 8, "dy": 1e-6, "dx": 1e-6},
        {"ny": True, "nx": 8, "dy": 1e-6, "dx": 1e-6},
        {"ny": 8, "nx": "8", "dy": 1e-6, "dx": 1e-6},
    ],
)
def test_g04b_invalid_parameter_types_rejected(kwargs: dict[str, object]) -> None:
    """G-04b: wrong parameter types raise ``TypeError``."""
    with pytest.raises(TypeError):
        SamplingGrid(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Spatial coordinates
# ---------------------------------------------------------------------------
def test_g05_axis_lengths_and_dtype(aniso_grid: SamplingGrid) -> None:
    """G-05: coordinate axes have the right length and are float64."""
    assert aniso_grid.x.shape == (aniso_grid.nx,)
    assert aniso_grid.y.shape == (aniso_grid.ny,)
    assert aniso_grid.x.dtype == np.float64
    assert aniso_grid.y.dtype == np.float64


def test_g06_axis_spacing_is_the_pitch(n: int, d: float) -> None:
    """G-06: consecutive coordinates differ by exactly the pitch.

    Tolerance ``rtol=1e-12``: ``np.diff`` subtracts coordinates whose
    magnitude can be many times the pitch, so the result can lose a unit in
    the last place. ``1e-12`` is about four orders of magnitude above float64
    epsilon, while any real spacing error would be O(1) relative.
    """
    grid = SamplingGrid(ny=n, nx=n, dy=d, dx=d)
    np.testing.assert_allclose(
        np.diff(grid.x), np.full(n - 1, d), rtol=1e-12, atol=0.0
    )
    np.testing.assert_allclose(
        np.diff(grid.y), np.full(n - 1, d), rtol=1e-12, atol=0.0
    )


def test_g07_origin_sits_exactly_on_index_n_over_2(n: int, d: float) -> None:
    """G-07: ``x[nx//2] == 0.0`` exactly, for even and odd ``n``.

    EXACTNESS IS THE PROPERTY UNDER TEST. ``(n//2 - n//2) * d`` is exactly
    ``0.0`` in IEEE-754, and the whole ``N//2`` centring convention
    (section 3.4) rests on index ``n//2`` being the origin in every array in
    the project. A tolerance here would defeat the purpose.
    """
    grid = SamplingGrid(ny=n, nx=n, dy=d, dx=d)
    assert grid.x[n // 2] == 0.0
    assert grid.y[n // 2] == 0.0


def test_g08_even_grid_span_is_asymmetric_by_one_sample(d: float) -> None:
    """G-08: for even ``n`` the span is ``[-(n/2)d, +(n/2 - 1)d]``.

    This asymmetry is accepted deliberately in exchange for exact index
    alignment with ``fftshift(fftfreq(...))`` (section 3.4).
    """
    grid = SamplingGrid(ny=8, nx=8, dy=d, dx=d)
    np.testing.assert_allclose(grid.x[0], -4.0 * d, rtol=1e-15, atol=0.0)
    np.testing.assert_allclose(grid.x[-1], 3.0 * d, rtol=1e-15, atol=0.0)


def test_g09_odd_grid_span_is_symmetric(d: float) -> None:
    """G-09: for odd ``n`` the coordinate span is symmetric about zero."""
    grid = SamplingGrid(ny=7, nx=7, dy=d, dx=d)
    np.testing.assert_allclose(grid.x[0], -grid.x[-1], rtol=1e-15, atol=0.0)
    np.testing.assert_allclose(grid.x[0], -3.0 * d, rtol=1e-15, atol=0.0)


# ---------------------------------------------------------------------------
# Frequency axes -- agreement with numpy.fft
# ---------------------------------------------------------------------------
def test_g10_fft_ordered_axis_matches_numpy_bit_for_bit(n: int, d: float) -> None:
    """G-10: ``fx_fft`` equals ``np.fft.fftfreq(nx, dx)`` bit for bit.

    EXACTNESS IS THE PROPERTY UNDER TEST. The axis is built independently
    from the documented formula and then compared against NumPy; delegating to
    ``fftfreq`` would make this assertion unfalsifiable.

    Bit-identity is achievable only because the implementation evaluates
    ``(m - n//2) * (1.0 / (n * d))`` -- reciprocal-multiply, matching NumPy's
    internal order. The division form differs by ~1 ULP at realistic pitches
    (section 3.8, v0.2).
    """
    grid = SamplingGrid(ny=n, nx=n, dy=d, dx=d)
    assert_bit_identical(grid.fx_fft, np.fft.fftfreq(n, d))
    assert_bit_identical(grid.fy_fft, np.fft.fftfreq(n, d))


def test_g11_centered_axis_matches_numpy_bit_for_bit(n: int, d: float) -> None:
    """G-11: ``fx_centered`` equals ``fftshift(fftfreq(nx, dx))`` bit for bit."""
    grid = SamplingGrid(ny=n, nx=n, dy=d, dx=d)
    assert_bit_identical(
        grid.fx_centered, np.fft.fftshift(np.fft.fftfreq(n, d))
    )


def test_g12_ordering_round_trip_is_exact(n: int, d: float) -> None:
    """G-12: ``ifftshift(fx_centered) == fx_fft`` exactly.

    Evidence class: round-trip identity. ``fftshift``/``ifftshift`` are pure
    index permutations, so any discrepancy would indicate a genuine ordering
    bug rather than arithmetic error.
    """
    grid = SamplingGrid(ny=n, nx=n, dy=d, dx=d)
    assert_bit_identical(np.fft.ifftshift(grid.fx_centered), grid.fx_fft)
    assert_bit_identical(np.fft.fftshift(grid.fx_fft), grid.fx_centered)


def test_g13_zero_frequency_is_exactly_zero(n: int, d: float) -> None:
    """G-13: zero frequency sits exactly at index 0 (FFT) and ``n//2`` (centred).

    EXACTNESS IS THE PROPERTY UNDER TEST -- this is the frequency-domain half
    of the ``N//2`` centring convention.
    """
    grid = SamplingGrid(ny=n, nx=n, dy=d, dx=d)
    assert grid.fx_fft[0] == 0.0
    assert grid.fx_centered[n // 2] == 0.0


def test_g14_angular_frequency_is_two_pi_times_cyclic(n: int, d: float) -> None:
    """G-14: ``kx = 2*pi*fx`` (section 3.6).

    Tolerance ``rtol=1e-15``: one multiplication, so at most one unit in the
    last place. Confusing cyclic with angular frequency is a factor-of-2pi
    error, six orders of magnitude larger than this bound.
    """
    grid = SamplingGrid(ny=n, nx=n, dy=d, dx=d)
    np.testing.assert_allclose(
        grid.kx_fft, 2.0 * np.pi * grid.fx_fft, rtol=1e-15, atol=0.0
    )
    np.testing.assert_allclose(
        grid.ky_centered, 2.0 * np.pi * grid.fy_centered, rtol=1e-15, atol=0.0
    )


# ---------------------------------------------------------------------------
# Nyquist
# ---------------------------------------------------------------------------
def test_g15_nyquist_value_and_bound(n: int, d: float) -> None:
    """G-15: ``f_nyq = 1/(2d)`` and no sampled frequency exceeds it."""
    grid = SamplingGrid(ny=n, nx=n, dy=d, dx=d)
    np.testing.assert_allclose(
        grid.nyquist_fx, 1.0 / (2.0 * d), rtol=1e-15, atol=0.0
    )
    assert np.max(np.abs(grid.fx_centered)) <= grid.nyquist_fx


def test_g16_even_grid_reaches_negative_nyquist_exactly(d: float) -> None:
    """G-16: for even ``n``, ``fx_centered[0] == -f_nyq`` exactly.

    And the positive Nyquist frequency is NOT a sample: the largest value is
    ``+f_nyq - 1/(n*d)``. Getting this wrong by one bin is a classic
    off-by-one that survives casual inspection.
    """
    grid = SamplingGrid(ny=8, nx=8, dy=d, dx=d)
    assert grid.fx_centered[0] == -grid.nyquist_fx
    assert grid.fx_centered[-1] < grid.nyquist_fx
    np.testing.assert_allclose(
        grid.fx_centered[-1],
        grid.nyquist_fx - 1.0 / (8 * d),
        rtol=1e-12,
        atol=0.0,
    )


# ---------------------------------------------------------------------------
# meshgrid orientation
# ---------------------------------------------------------------------------
def test_g17_meshgrid_orientation(aniso_grid: SamplingGrid) -> None:
    """G-17: the anti-transposition test.

    ``x_grid`` must vary along axis 1 and be constant along axis 0; ``y_grid``
    the reverse. EXACTNESS IS THE PROPERTY UNDER TEST -- meshgrid copies
    values, it does not compute them.

    This test is only meaningful because ``aniso_grid`` has ``ny != nx``: on a
    square grid a transposed implementation would still have the right shape
    and could pass a weaker assertion.
    """
    x_grid, y_grid = aniso_grid.meshgrid()
    assert x_grid.shape == aniso_grid.shape == (6, 10)
    assert y_grid.shape == aniso_grid.shape

    for i in range(aniso_grid.ny):
        assert_bit_identical(x_grid[i, :], aniso_grid.x)
    for j in range(aniso_grid.nx):
        assert_bit_identical(y_grid[:, j], aniso_grid.y)


def test_g18_freq_meshgrid_matches_axes_in_both_orders(
    aniso_grid: SamplingGrid,
) -> None:
    """G-18: ``freq_meshgrid`` is consistent with the 1-D axes, both orders."""
    for order, fx_axis, fy_axis in (
        ("fft", aniso_grid.fx_fft, aniso_grid.fy_fft),
        ("centered", aniso_grid.fx_centered, aniso_grid.fy_centered),
    ):
        fx_grid, fy_grid = aniso_grid.freq_meshgrid(order=order)  # type: ignore[arg-type]
        assert fx_grid.shape == aniso_grid.shape
        assert fy_grid.shape == aniso_grid.shape
        assert_bit_identical(fx_grid[0, :], fx_axis)
        assert_bit_identical(fy_grid[:, 0], fy_axis)


def test_g19_freq_meshgrid_requires_explicit_order(
    aniso_grid: SamplingGrid,
) -> None:
    """G-19: ``order`` is keyword-only with no default.

    Silently defaulting to one ordering is precisely the mistake the
    ``*_fft`` / ``*_centered`` naming discipline exists to prevent
    (section 3.8).
    """
    with pytest.raises(TypeError):
        aniso_grid.freq_meshgrid()  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="'fft' or 'centered'"):
        aniso_grid.freq_meshgrid(order="shifted")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Anisotropy
# ---------------------------------------------------------------------------
def test_g20_axes_depend_only_on_their_own_parameters(
    aniso_grid: SamplingGrid,
) -> None:
    """G-20: x-quantities depend only on ``(nx, dx)``, y-quantities on ``(ny, dy)``.

    Compared bit for bit against independently constructed square grids. Any
    cross-contamination of the axes -- the most likely form of a transposition
    bug -- shows up here immediately.
    """
    x_ref = SamplingGrid(ny=3, nx=aniso_grid.nx, dy=1.0, dx=aniso_grid.dx)
    y_ref = SamplingGrid(ny=aniso_grid.ny, nx=3, dy=aniso_grid.dy, dx=1.0)

    assert_bit_identical(aniso_grid.x, x_ref.x)
    assert_bit_identical(aniso_grid.fx_fft, x_ref.fx_fft)
    assert_bit_identical(aniso_grid.fx_centered, x_ref.fx_centered)
    assert aniso_grid.nyquist_fx == x_ref.nyquist_fx

    assert_bit_identical(aniso_grid.y, y_ref.y)
    assert_bit_identical(aniso_grid.fy_fft, y_ref.fy_fft)
    assert aniso_grid.nyquist_fy == y_ref.nyquist_fy


# ---------------------------------------------------------------------------
# Diffraction angle
# ---------------------------------------------------------------------------
def test_g21_max_diffraction_angle_matches_analytic_formula(
    aniso_grid: SamplingGrid, wavelength: float
) -> None:
    """G-21: ``sin(theta_max) = lambda / (2d)`` (analytic ground truth).

    Tolerance ``rtol=1e-12`` on the sine: the implementation applies ``asin``
    and the test applies ``sin``, a round trip through two libm calls.
    """
    for axis, pitch in (("x", aniso_grid.dx), ("y", aniso_grid.dy)):
        theta = aniso_grid.max_diffraction_angle_rad(wavelength, axis=axis)  # type: ignore[arg-type]
        np.testing.assert_allclose(
            math.sin(theta), wavelength / (2.0 * pitch), rtol=1e-12, atol=0.0
        )


def test_g22_diffraction_angle_spot_check_against_hand_calculation() -> None:
    """G-22: independent hand-computed value.

    lambda = 633 nm, d = 3.74 um -> sin(theta) = 633e-9 / 7.48e-6 = 0.084626,
    theta = 4.855 degrees. Computed by hand, outside the implementation.

    Tolerance 0.01 degrees, set by the precision of the hand calculation, not
    by float64. This is the only external cross-check in the grid suite.
    """
    grid = SamplingGrid.square(n=64, pitch=3.74 * UM)
    theta_deg = math.degrees(
        grid.max_diffraction_angle_rad(633 * NM, axis="x")
    )
    assert theta_deg == pytest.approx(4.855, rel=0.0, abs=0.01)


def test_g23_diffraction_angle_rejects_nyquist_beyond_propagating_cutoff() -> None:
    """G-23: fine sampling is valid, but its Nyquist may have no real angle.

    With ``lambda/(2d) > 1`` no such angle exists; ``math.asin`` would raise a
    domain error and ``np.arcsin`` would return NaN with a warning. Neither is
    acceptable as a public API behaviour. The grid itself remains valid.
    """
    grid = SamplingGrid.square(n=8, pitch=100 * NM)
    with pytest.raises(ValueError, match="Nyquist frequency exceeds the propagating-wave cutoff"):
        grid.max_diffraction_angle_rad(633 * NM, axis="x")
    # The same fine grid has a real angle for a shorter wavelength. The exact
    # value pi/6 is checked with rel=1e-15 for asin rounding, abs=0 at nonzero scale.
    np.testing.assert_allclose(
        grid.max_diffraction_angle_rad(100 * NM, axis="x"),
        math.pi / 6.0,
        rtol=1e-15,
        atol=0.0,
    )
    with pytest.raises(ValueError, match="axis must be"):
        grid.max_diffraction_angle_rad(50 * NM, axis="z")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Serialization, immutability, constructors
# ---------------------------------------------------------------------------
def test_g24_dict_round_trip_is_exact(aniso_grid: SamplingGrid) -> None:
    """G-24: ``from_dict(to_dict(g)) == g``, and the dict is JSON-serializable.

    This is the unit of grid reproducibility that Milestone 5's run
    configuration will embed, so the round trip must be exact, not close.
    """
    payload = aniso_grid.to_dict()
    assert json.loads(json.dumps(payload)) == payload
    assert SamplingGrid.from_dict(payload) == aniso_grid
    assert SamplingGrid.from_dict(json.loads(json.dumps(payload))) == aniso_grid


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"ny": 6, "nx": 10, "dy": 1e-6}, KeyError),
        ({"ny": 6, "nx": 10, "dy": 1e-6, "dx": 1e-6, "z": 0.1}, ValueError),
        ({"ny": 6, "nx": 10, "dy": 1e-6, "dx": 0.0}, ValueError),
        ({"ny": "6", "nx": 10, "dy": 1e-6, "dx": 1e-6}, TypeError),
    ],
)
def test_g25_from_dict_rejects_bad_payloads(
    payload: dict[str, object], expected: type[Exception]
) -> None:
    """G-25: missing, extra, and invalid keys are all rejected distinctly."""
    with pytest.raises(expected):
        SamplingGrid.from_dict(payload)
    with pytest.raises(TypeError):
        SamplingGrid.from_dict([("ny", 6)])  # type: ignore[arg-type]


def test_g26_grid_is_frozen_and_hashable(aniso_grid: SamplingGrid) -> None:
    """G-26: the grid is immutable and usable as a dict key."""
    with pytest.raises(dataclasses.FrozenInstanceError):
        aniso_grid.dx = 1e-6  # type: ignore[misc]
    assert hash(aniso_grid) == hash(
        SamplingGrid(ny=6, nx=10, dy=5.0 * UM, dx=3.74 * UM)
    )


def test_g27_derived_arrays_are_not_shared_between_accesses(
    aniso_grid: SamplingGrid,
) -> None:
    """G-27: mutating a returned axis cannot corrupt the grid.

    Nothing is cached, so each access recomputes. EXACTNESS IS THE PROPERTY
    UNDER TEST -- the second access must reproduce the original values
    identically.
    """
    first = aniso_grid.x
    pristine = first.copy()
    first[0] = 12345.0
    assert_bit_identical(aniso_grid.x, pristine)


def test_g27b_square_constructor_matches_explicit(d: float) -> None:
    """G-27b: ``square()`` is exactly the isotropic explicit constructor."""
    assert SamplingGrid.square(n=16, pitch=d) == SamplingGrid(
        ny=16, nx=16, dy=d, dx=d
    )
