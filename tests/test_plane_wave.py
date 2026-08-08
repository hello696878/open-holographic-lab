"""Analytic validation of :meth:`ComplexField.plane_wave` (IDs P-01 .. P-10).

A tilted plane wave is the one field in Milestone 0 whose structure is known
in closed form, so it is the strongest available check that the coordinate
grid, the wavenumber, and the phase convention all agree.

Two independent analytic checks are used.

**Local complex ratio (primary).** For ``U = A exp(i(kx x + ky y))``,

    U[i, j+1] * conj(U[i, j]) = A^2 * exp(i * kx * dx)

so the argument of the neighbour ratio equals ``kx * dx`` exactly, and
likewise ``ky * dy`` along rows. This needs no unwrapping and no fitting: it
is a pointwise identity, evaluated on every adjacent pair in the field. Test
angles are chosen so that ``|kx * dx|`` stays well inside ``(-pi, +pi]``, away
from the branch cut.

**Unwrapped gradient (secondary).** A least-squares fit to the unwrapped phase
along a row must recover ``kx``. This is kept as a cross-check because it
probes global rather than local structure, but it is not relied on alone --
``np.unwrap`` has its own failure modes near the branch boundary.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from _helpers import assert_phase_allclose
from ohlab.field import ComplexField
from ohlab.grid import SamplingGrid
from ohlab.units import NM, UM

# Tilts expressed as a fraction of the grid's Nyquist frequency.
# With sin(theta) = frac * lambda / (2*d), one gets kx*dx = pi*frac, so every
# fraction here keeps the neighbour-ratio phase safely inside (-pi, +pi].
NYQUIST_FRACTIONS = [
    (0.0, 0.0),
    (0.3, 0.0),
    (0.0, -0.4),
    (0.35, 0.25),
    (-0.45, -0.3),
]


def _tilt_from_nyquist_fraction(
    grid: SamplingGrid, wavelength_m: float, frac_x: float, frac_y: float
) -> tuple[float, float]:
    """Return ``(theta_x, theta_y)`` in radians for the requested tilt fractions."""
    sin_x = frac_x * wavelength_m * grid.nyquist_fx
    sin_y = frac_y * wavelength_m * grid.nyquist_fy
    return math.asin(sin_x), math.asin(sin_y)


# ---------------------------------------------------------------------------
# Analytic structure
# ---------------------------------------------------------------------------
def test_p01_zero_tilt_gives_a_spatially_constant_field(
    aniso_grid: SamplingGrid, wavelength: float
) -> None:
    """P-01: at normal incidence the field is constant across the window."""
    field = ComplexField.plane_wave(
        grid=aniso_grid, wavelength_m=wavelength, amplitude=2.0
    )
    np.testing.assert_allclose(
        field.data, np.full(aniso_grid.shape, 2.0 + 0.0j), rtol=1e-12, atol=1e-15
    )
    assert np.all(field.phase == 0.0)


@pytest.mark.parametrize(("frac_x", "frac_y"), NYQUIST_FRACTIONS)
def test_p02_neighbour_ratio_phase_equals_kx_dx_and_ky_dy(
    aniso_grid: SamplingGrid, wavelength: float, frac_x: float, frac_y: float
) -> None:
    """P-02: the primary analytic check, ``arg(U[j+1] conj(U[j])) == kx*dx``.

    Evidence class: analytic ground truth, evaluated pointwise. No unwrapping,
    no fitting, and no dependence on the absolute phase origin.

    Tolerance ``atol=1e-10`` rad on the wrapped difference. The phase argument
    ``kx*x`` reaches about 16 rad on this grid, so its own rounding is about
    ``16 * eps ~ 3.5e-15``; the product of two such values roughly doubles
    that. ``1e-10`` therefore leaves a margin of about 2500x, while a wrong
    wavenumber, a wrong pitch, or a sign error would be O(1).
    """
    theta_x, theta_y = _tilt_from_nyquist_fraction(
        aniso_grid, wavelength, frac_x, frac_y
    )
    field = ComplexField.plane_wave(
        grid=aniso_grid,
        wavelength_m=wavelength,
        theta_x_rad=theta_x,
        theta_y_rad=theta_y,
    )
    k = 2.0 * math.pi / wavelength
    kx = k * math.sin(theta_x)
    ky = k * math.sin(theta_y)

    ratio_x = field.data[:, 1:] * np.conj(field.data[:, :-1])
    assert_phase_allclose(np.angle(ratio_x), kx * aniso_grid.dx, atol=1e-10)

    ratio_y = field.data[1:, :] * np.conj(field.data[:-1, :])
    assert_phase_allclose(np.angle(ratio_y), ky * aniso_grid.dy, atol=1e-10)


@pytest.mark.parametrize(("frac_x", "frac_y"), NYQUIST_FRACTIONS)
def test_p03_unwrapped_phase_gradient_recovers_the_wavevector(
    aniso_grid: SamplingGrid, wavelength: float, frac_x: float, frac_y: float
) -> None:
    """P-03: secondary check via unwrapping and a least-squares fit.

    Probes global rather than local structure. Retained as a cross-check on
    P-02, not as the sole evidence, because ``np.unwrap`` has its own failure
    modes near the branch boundary.

    Tolerance ``rtol=1e-10`` on a non-zero wavevector; measured error is
    ~4e-16. For the zero-tilt case a relative tolerance is meaningless, so an
    absolute bound scaled to the wavenumber is used instead.
    """
    theta_x, theta_y = _tilt_from_nyquist_fraction(
        aniso_grid, wavelength, frac_x, frac_y
    )
    field = ComplexField.plane_wave(
        grid=aniso_grid,
        wavelength_m=wavelength,
        theta_x_rad=theta_x,
        theta_y_rad=theta_y,
    )
    k = field.wavenumber
    kx = k * math.sin(theta_x)
    ky = k * math.sin(theta_y)

    row = aniso_grid.ny // 2
    slope_x = float(
        np.polyfit(aniso_grid.x, np.unwrap(field.phase[row, :]), 1)[0]
    )
    column = aniso_grid.nx // 2
    slope_y = float(
        np.polyfit(aniso_grid.y, np.unwrap(field.phase[:, column]), 1)[0]
    )

    np.testing.assert_allclose(slope_x, kx, rtol=1e-10, atol=1e-10 * k)
    np.testing.assert_allclose(slope_y, ky, rtol=1e-10, atol=1e-10 * k)


def test_p04_amplitude_is_uniform_and_intensity_is_flat(
    aniso_grid: SamplingGrid, wavelength: float
) -> None:
    """P-04: a plane wave carries a tilt in phase only, never in amplitude."""
    theta_x, theta_y = _tilt_from_nyquist_fraction(
        aniso_grid, wavelength, 0.4, -0.25
    )
    field = ComplexField.plane_wave(
        grid=aniso_grid,
        wavelength_m=wavelength,
        theta_x_rad=theta_x,
        theta_y_rad=theta_y,
        amplitude=1.5,
    )
    np.testing.assert_allclose(
        field.amplitude, np.full(aniso_grid.shape, 1.5), rtol=1e-12, atol=0.0
    )
    np.testing.assert_allclose(
        field.intensity, np.full(aniso_grid.shape, 2.25), rtol=1e-12, atol=0.0
    )


def test_p05_on_grid_plane_wave_lands_in_the_predicted_fft_bin(
    aniso_grid: SamplingGrid, wavelength: float
) -> None:
    """P-05: C-01 repeated through the public constructor.

    The tilt angles are chosen so that the transverse frequencies fall exactly
    on grid samples, so all the energy must land in a single, analytically
    predicted bin. This closes the loop between ``plane_wave``, the coordinate
    grid, and the FFT conventions.
    """
    fx_axis = aniso_grid.fx_centered
    fy_axis = aniso_grid.fy_centered

    for col_offset, row_offset in [(+3, +2), (-4, -2)]:
        col = aniso_grid.nx // 2 + col_offset
        row = aniso_grid.ny // 2 + row_offset
        theta_x = math.asin(fx_axis[col] * wavelength)
        theta_y = math.asin(fy_axis[row] * wavelength)

        field = ComplexField.plane_wave(
            grid=aniso_grid,
            wavelength_m=wavelength,
            theta_x_rad=theta_x,
            theta_y_rad=theta_y,
        )
        magnitude = np.abs(np.fft.fftshift(np.fft.fft2(field.data)))
        peak = np.unravel_index(int(np.argmax(magnitude)), magnitude.shape)
        assert peak == (row, col)

        off_peak = magnitude.copy()
        off_peak[peak] = 0.0
        assert float(np.max(off_peak)) <= 1e-10 * float(magnitude[peak])


# ---------------------------------------------------------------------------
# Physical and sampling validity
# ---------------------------------------------------------------------------
def test_p06_combined_angles_that_are_not_propagating_are_rejected(
    wavelength: float,
) -> None:
    """P-06: ``sin^2(theta_x) + sin^2(theta_y) <= 1`` is enforced jointly.

    Each of 50 degrees in x and 50 degrees in y is individually a perfectly
    reasonable tilt, and on this deliberately fine grid each individually
    satisfies Nyquist. Together they require
    ``kx^2 + ky^2 = 1.174 k^2 > k^2``, hence an imaginary ``kz`` -- an
    evanescent, not a propagating, wave. That combination must be refused.

    The grid pitch is ``0.45 * lambda``, which puts the Nyquist limit at
    ``|sin(theta)| <= 1.11``, so sampling cannot be what triggers the error.
    """
    fine = SamplingGrid.square(n=8, pitch=0.45 * wavelength)
    assert wavelength * fine.nyquist_fx > 1.0  # Nyquist is not the binding limit

    fifty_degrees = math.radians(50.0)
    with pytest.raises(ValueError, match="propagating plane wave"):
        ComplexField.plane_wave(
            grid=fine,
            wavelength_m=wavelength,
            theta_x_rad=fifty_degrees,
            theta_y_rad=fifty_degrees,
        )


def test_p07_combined_angles_that_are_propagating_are_accepted(
    wavelength: float,
) -> None:
    """P-07: the same construction succeeds when the joint condition holds.

    30 degrees in both axes gives ``0.25 + 0.25 = 0.5 <= 1``. Without this
    companion test, P-06 could pass with an implementation that rejects every
    two-axis tilt.
    """
    fine = SamplingGrid.square(n=8, pitch=0.45 * wavelength)
    thirty = math.radians(30.0)
    field = ComplexField.plane_wave(
        grid=fine,
        wavelength_m=wavelength,
        theta_x_rad=thirty,
        theta_y_rad=thirty,
    )
    k = field.wavenumber
    kx = k * math.sin(thirty)
    ratio_x = field.data[:, 1:] * np.conj(field.data[:, :-1])
    assert_phase_allclose(np.angle(ratio_x), kx * fine.dx, atol=1e-10)


@pytest.mark.parametrize("axis", ["x", "y"])
def test_p08_per_axis_nyquist_limit_is_enforced(
    aniso_grid: SamplingGrid, wavelength: float, axis: str
) -> None:
    """P-08: a single-axis tilt beyond Nyquist is rejected, not aliased.

    30 degrees on the realistic grid needs ``|f| = 7.90e5`` cycles/m against a
    Nyquist limit of ``1.34e5``. The joint propagating condition is satisfied
    (``0.25 <= 1``), so this isolates the sampling check from P-06's physical
    check.
    """
    thirty = math.radians(30.0)
    kwargs = {"theta_x_rad": thirty} if axis == "x" else {"theta_y_rad": thirty}
    with pytest.raises(ValueError, match="Nyquist"):
        ComplexField.plane_wave(
            grid=aniso_grid, wavelength_m=wavelength, **kwargs  # type: ignore[arg-type]
        )


def test_p09_boundary_tilt_at_exactly_nyquist_is_accepted(
    aniso_grid: SamplingGrid, wavelength: float
) -> None:
    """P-09: a tilt landing exactly on the Nyquist limit is not rejected.

    The limit is inclusive (``<=``). This guards against an off-by-one-bin
    implementation that quietly refuses the outermost representable angle.
    """
    theta_x = math.asin(wavelength * aniso_grid.nyquist_fx)
    field = ComplexField.plane_wave(
        grid=aniso_grid, wavelength_m=wavelength, theta_x_rad=theta_x
    )
    assert field.shape == aniso_grid.shape


@pytest.mark.parametrize(
    "kwargs",
    [
        {"theta_x_rad": float("nan")},
        {"theta_y_rad": float("inf")},
        {"amplitude": -1.0},
    ],
)
def test_p10_invalid_plane_wave_parameters_rejected(
    aniso_grid: SamplingGrid, wavelength: float, kwargs: dict[str, float]
) -> None:
    """P-10: non-finite angles and negative amplitude are rejected."""
    with pytest.raises(ValueError):
        ComplexField.plane_wave(
            grid=aniso_grid, wavelength_m=wavelength, **kwargs  # type: ignore[arg-type]
        )


def test_p11_wavelength_dependence_is_physical(aniso_grid: SamplingGrid) -> None:
    """P-11: at fixed tilt, a shorter wavelength gives a steeper phase ramp.

    ``kx = (2*pi/lambda) sin(theta)``, so halving the wavelength doubles the
    neighbour-ratio phase. Tolerance ``rtol=1e-10``.
    """
    theta = math.asin(0.2 * 633 * NM * aniso_grid.nyquist_fx)
    long_wave = ComplexField.plane_wave(
        grid=aniso_grid, wavelength_m=633 * NM, theta_x_rad=theta
    )
    short_wave = ComplexField.plane_wave(
        grid=aniso_grid, wavelength_m=316.5 * NM, theta_x_rad=theta
    )

    def neighbour_phase(field: ComplexField) -> float:
        ratio = field.data[:, 1:] * np.conj(field.data[:, :-1])
        return float(np.mean(np.angle(ratio)))

    np.testing.assert_allclose(
        neighbour_phase(short_wave),
        2.0 * neighbour_phase(long_wave),
        rtol=1e-10,
        atol=0.0,
    )
