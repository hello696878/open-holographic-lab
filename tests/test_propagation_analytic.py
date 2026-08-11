"""Analytic validation of Angular Spectrum propagation (IDs A-01 .. A-12).

These tests carry the evidential weight for Milestone 1. Every one of them
compares against a closed-form solution derived independently of the
implementation, rather than against another numerical result.

Why the round trip is not enough
--------------------------------
``propagate(+z)`` followed by ``propagate(-z)`` is invariant under a global
sign flip of the transfer function, because ``H(-z) = conj(H(z))`` whichever
sign convention is used. A completely wrong propagator cancels itself. The
round trip therefore lives in ``test_propagation.py`` as secondary evidence,
and the sign is pinned here instead.

Why ``pad_factor=1`` throughout the exact tests
-----------------------------------------------
A plane wave and a uniform field fill the entire computational window. They
are exact eigenfunctions of the *periodic* problem, which is what
``pad_factor=1`` solves. Zero-padding embeds them in a larger zero-valued
window, which imposes a hard aperture edge they did not have -- the field is
then no longer an infinite periodic plane wave and the analytic identity
legitimately stops holding. Padding is exercised separately, with compact
fields, in ``test_propagation.py``.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from _helpers import assert_phase_allclose
from ohlab.field import ComplexField
from ohlab.grid import SamplingGrid
from ohlab.propagation import propagate_angular_spectrum
from ohlab.units import MM, NM, UM


@pytest.fixture
def prop_grid() -> SamplingGrid:
    """Anisotropic grid: ny != nx and dy != dx, so an fx/fy swap is detectable."""
    return SamplingGrid(ny=48, nx=64, dy=5.0 * UM, dx=3.74 * UM)


def _on_grid_plane_wave(
    grid: SamplingGrid,
    wavelength_m: float,
    col_offset: int,
    row_offset: int,
    amplitude: float = 1.0,
) -> tuple[ComplexField, float, float, float]:
    """Build a plane wave whose transverse frequencies land exactly on samples.

    Returns ``(field, fx0, fy0, kz)`` where ``kz = 2*pi*sqrt(1/lambda^2 - fx0^2 - fy0^2)``.
    """
    col = grid.nx // 2 + col_offset
    row = grid.ny // 2 + row_offset
    fx0 = float(grid.fx_centered[col])
    fy0 = float(grid.fy_centered[row])
    field = ComplexField.plane_wave(
        grid=grid,
        wavelength_m=wavelength_m,
        theta_x_rad=math.asin(fx0 * wavelength_m),
        theta_y_rad=math.asin(fy0 * wavelength_m),
        amplitude=amplitude,
    )
    kz = 2.0 * math.pi * math.sqrt((1.0 / wavelength_m) ** 2 - fx0**2 - fy0**2)
    return field, fx0, fy0, kz


# ---------------------------------------------------------------------------
# A. Zero distance
# ---------------------------------------------------------------------------
def test_a01_zero_distance_is_the_identity(
    prop_grid: SamplingGrid, wavelength: float
) -> None:
    """A-01: ``z = 0`` returns the source field itself.

    Evidence class: exact identity. See the zero-distance contract in
    ``propagate_angular_spectrum``.
    """
    field = ComplexField.random_phase(
        grid=prop_grid, wavelength_m=wavelength, seed=21
    )
    assert propagate_angular_spectrum(field, distance_m=0.0, pad_factor=1) is field


# ---------------------------------------------------------------------------
# B. Single on-grid plane wave -- the strongest test
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("col_offset", "row_offset"),
    [(0, 0), (7, 5), (-11, -3), (9, -6), (-13, 8)],
)
@pytest.mark.parametrize("z", [1.0 * MM, 50.0 * MM, 200.0 * MM])
def test_a02_on_grid_plane_wave_acquires_exactly_exp_i_kz_z(
    prop_grid: SamplingGrid,
    wavelength: float,
    col_offset: int,
    row_offset: int,
    z: float,
) -> None:
    """A-02: THE decisive test. ``U(z) = U(0) * exp(i*kz*z)``, exactly.

    Evidence class: analytic ground truth, exact and fully non-paraxial. A
    plane wave is an exact eigenfunction of free-space propagation, and when
    its transverse frequencies land on grid samples the DFT represents it with
    no leakage at all. The expected result is therefore known in closed form
    with no approximation whatsoever.

    This pins simultaneously:

    * the SIGN of the propagation phase -- a flip gives ``exp(-i*kz*z)``, an
      O(1) error in the complex field;
    * the MAGNITUDE of ``kz`` -- a wrong square root gives a completely
      different phase;
    * that ``kz`` depends on ``fx`` and ``fy`` correctly, since the four
      offset combinations span all sign quadrants;
    * that the amplitude is untouched, since ``|exp(i*kz*z)| = 1``.

    ``pad_factor=1``: a plane wave fills the window and is an eigenfunction of
    the periodic problem, not of the zero-embedded one.

    Tolerance ``rtol=1e-11`` on the complex field and ``atol=1e-10`` rad on
    the wrapped phase; measured worst case 1.4e-14 and 1.2e-14 respectively,
    leaving roughly a 1000x margin for libm and FFT-backend variation.
    """
    field, fx0, fy0, kz = _on_grid_plane_wave(
        prop_grid, wavelength, col_offset, row_offset
    )
    out = propagate_angular_spectrum(field, distance_m=z, pad_factor=1)
    expected = field.data * np.exp(1j * kz * z)

    np.testing.assert_allclose(out.data, expected, rtol=1e-11, atol=1e-11)
    assert_phase_allclose(
        out.phase, np.angle(expected), atol=1e-10, amplitude=out.amplitude
    )
    # A plane wave never changes amplitude while propagating.
    np.testing.assert_allclose(
        out.amplitude, field.amplitude, rtol=1e-11, atol=0.0
    )


def test_a03_plane_wave_phase_advance_matches_kz_and_is_less_than_k_z(
    prop_grid: SamplingGrid, wavelength: float
) -> None:
    """A-03: a tilted wave advances in phase MORE SLOWLY than an on-axis one.

    ``kz = sqrt(k^2 - kx^2 - ky^2) < k`` for any non-zero tilt, so the axial
    phase accumulated over the same distance must be strictly smaller. This is
    an independent, sign-sensitive physical check: it fails if ``kz`` is
    computed as ``sqrt(k^2 + kx^2 + ky^2)``, which the magnitude-only tests
    would still pass in a round trip.
    """
    k = 2.0 * math.pi / wavelength
    z = 20.0 * MM

    on_axis, _, _, kz_axis = _on_grid_plane_wave(prop_grid, wavelength, 0, 0)
    tilted, _, _, kz_tilt = _on_grid_plane_wave(prop_grid, wavelength, 15, 11)

    np.testing.assert_allclose(kz_axis, k, rtol=1e-12, atol=0.0)
    assert kz_tilt < kz_axis

    out_axis = propagate_angular_spectrum(on_axis, distance_m=z, pad_factor=1)
    out_tilt = propagate_angular_spectrum(tilted, distance_m=z, pad_factor=1)
    # Compare the phase each acquired, relative to its own source.
    advance_axis = np.angle(np.exp(1j * (out_axis.phase - on_axis.phase)))
    advance_tilt = np.angle(np.exp(1j * (out_tilt.phase - tilted.phase)))
    assert_phase_allclose(advance_axis, kz_axis * z, atol=1e-10)
    assert_phase_allclose(advance_tilt, kz_tilt * z, atol=1e-10)


# ---------------------------------------------------------------------------
# B2. Superposition -- detects an fx/fy swap
# ---------------------------------------------------------------------------
def test_a04_superposition_gives_each_component_its_own_kz(
    prop_grid: SamplingGrid, wavelength: float
) -> None:
    """A-04: linearity, with three distinct on-grid plane waves.

    Evidence class: analytic ground truth plus linearity. Each component must
    receive its *own* ``kz``, so this detects errors a single plane wave
    cannot: notably ``fx`` and ``fy`` being swapped, which on this anisotropic
    grid sends each component to the wrong axial phase.

    The components have unequal amplitudes so that a permutation of the
    components is also detectable.

    Tolerance ``rtol=1e-11``; measured 5.2e-15.
    """
    components = [(5, 3, 1.0), (-9, 2, 0.6), (11, -7, 0.35)]
    z = 50.0 * MM

    total = np.zeros(prop_grid.shape, dtype=np.complex128)
    expected = np.zeros(prop_grid.shape, dtype=np.complex128)
    for col_offset, row_offset, amplitude in components:
        part, _, _, kz = _on_grid_plane_wave(
            prop_grid, wavelength, col_offset, row_offset, amplitude
        )
        total += part.data
        expected += part.data * np.exp(1j * kz * z)

    field = ComplexField(
        data=total, grid=prop_grid, wavelength_m=wavelength
    )
    out = propagate_angular_spectrum(field, distance_m=z, pad_factor=1)
    scale = float(np.max(np.abs(expected)))
    np.testing.assert_allclose(
        out.data, expected, rtol=1e-11, atol=1e-11 * scale
    )


# ---------------------------------------------------------------------------
# C. Normal-incidence uniform field
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("z", [0.1 * MM, 1.0 * MM, 10.0 * MM, 100.0 * MM])
def test_a05_uniform_field_acquires_the_on_axis_carrier_phase(
    prop_grid: SamplingGrid, wavelength: float, z: float
) -> None:
    """A-05: a uniform field acquires exactly ``exp(i*k*z)`` and nothing else.

    Evidence class: analytic ground truth. The special case of A-02 at zero
    tilt, where ``kz = k``. Under the ``exp(-i*omega*t)`` convention the phase
    ADVANCES with distance, so a sign error doubles the discrepancy.

    Tolerance scales with distance. The accumulated phase ``k*z`` reaches
    9.9e5 rad at z = 100 mm -- about 1.6e5 cycles -- so its own float64
    rounding is ``k*z*eps``, measured at 1.2e-10. A fixed ``atol=1e-12`` would
    fail here for reasons that have nothing to do with correctness, so the
    tolerance is written as ``100 * k * z * eps``.

    ``pad_factor=1``: a uniform field is constant only on the periodic window.
    """
    field = ComplexField.uniform(
        grid=prop_grid, wavelength_m=wavelength, amplitude=1.0
    )
    k = 2.0 * math.pi / wavelength
    out = propagate_angular_spectrum(field, distance_m=z, pad_factor=1)

    tolerance = 100.0 * k * z * float(np.finfo(np.float64).eps)
    expected = np.exp(1j * k * z)
    np.testing.assert_allclose(
        out.data, np.full(prop_grid.shape, expected), rtol=0.0, atol=tolerance
    )
    # Still uniform, still unit amplitude.
    np.testing.assert_allclose(out.amplitude, 1.0, rtol=0.0, atol=tolerance)


def test_a06_uniform_field_phase_sign_is_positive_with_distance(
    prop_grid: SamplingGrid, wavelength: float
) -> None:
    """A-06: the phase advances, it does not retard.

    Isolates the sign alone, at a distance short enough that ``k*z`` is well
    inside one cycle so the comparison cannot be confused by wrapping.
    ``k = 9.926e6 rad/m``, so ``z = 50 nm`` gives ``k*z = 0.496 rad``.

    A flipped propagation sign gives ``-0.496`` rad, which this test rejects
    outright.
    """
    k = 2.0 * math.pi / wavelength
    z = 50.0 * NM
    assert 0.0 < k * z < math.pi / 2.0

    field = ComplexField.uniform(grid=prop_grid, wavelength_m=wavelength)
    out = propagate_angular_spectrum(field, distance_m=z, pad_factor=1)
    phase = float(np.mean(out.phase))
    assert phase > 0.0, "phase must ADVANCE under the exp(-i*omega*t) convention"
    assert phase == pytest.approx(k * z, rel=1e-9)


# ---------------------------------------------------------------------------
# F. Symmetry
# ---------------------------------------------------------------------------
def test_a07_even_symmetric_field_stays_even_symmetric(
    wavelength: float,
) -> None:
    """A-07: propagation preserves the symmetry of a symmetric source.

    Evidence class: symmetry. A field even about the origin sample must remain
    even, because ``H`` depends only on ``fx^2 + fy^2`` and is therefore even
    itself.

    The flip is realigned by one sample because the ``N//2`` centring
    convention places the origin off-centre for even ``N``: reversing the axis
    maps index ``i`` to ``N-1-i``, which is the origin's mirror only after a
    roll of one.

    Tolerance ``rtol=1e-12``; measured 8.7e-16.
    """
    grid = SamplingGrid.square(n=64, pitch=4.0 * UM)
    x_grid, y_grid = grid.meshgrid()
    symmetric = np.exp(-(x_grid**2 + y_grid**2) / (30.0 * UM) ** 2)
    field = ComplexField(
        data=symmetric.astype(np.complex128), grid=grid, wavelength_m=wavelength
    )
    out = propagate_angular_spectrum(field, distance_m=20.0 * MM, pad_factor=1)

    mirrored = np.roll(np.roll(out.data[::-1, ::-1], 1, axis=0), 1, axis=1)
    scale = float(np.max(np.abs(out.data)))
    np.testing.assert_allclose(out.data, mirrored, rtol=1e-12, atol=1e-12 * scale)


def test_a08_asymmetric_field_does_not_become_symmetric(
    prop_grid: SamplingGrid, wavelength: float
) -> None:
    """A-08: the symmetry test is not vacuous.

    Without this, A-07 would also pass for an implementation that symmetrises
    everything (for example by taking a magnitude somewhere).
    """
    x_grid, y_grid = prop_grid.meshgrid()
    offset = np.exp(
        -((x_grid - 40 * UM) ** 2 + (y_grid - 30 * UM) ** 2) / (25.0 * UM) ** 2
    )
    field = ComplexField(
        data=offset.astype(np.complex128),
        grid=prop_grid,
        wavelength_m=wavelength,
    )
    out = propagate_angular_spectrum(field, distance_m=10.0 * MM, pad_factor=1)
    mirrored = np.roll(np.roll(out.data[::-1, ::-1], 1, axis=0), 1, axis=1)
    scale = float(np.max(np.abs(out.data)))
    assert float(np.max(np.abs(out.data - mirrored))) > 0.1 * scale


# ---------------------------------------------------------------------------
# G. Gaussian beam -- independent analytic solution
# ---------------------------------------------------------------------------
def _gaussian_beam_analytic(
    grid: SamplingGrid, wavelength_m: float, waist_m: float, z: float
) -> np.ndarray:
    """The paraxial Gaussian beam, written out under our sign convention.

    With ``k = 2*pi/lambda`` and ``r^2 = x^2 + y^2``::

        z_R  = pi * w0^2 / lambda                        Rayleigh range      [m]
        w(z) = w0 * sqrt(1 + (z/z_R)^2)                  beam radius         [m]
        R(z) = z * (1 + (z_R/z)^2)                       wavefront curvature [m]
        psi  = arctan(z / z_R)                           Gouy phase          [rad]

        U(r, z) = (w0/w(z)) * exp(-r^2 / w(z)^2)
                  * exp( +i * [ k*z  +  k*r^2 / (2*R(z))  -  psi(z) ] )

    Sign choices under the ``exp(-i*omega*t)`` convention of
    ``math_conventions.md`` section 3.1:

    * ``+k*z``      -- the longitudinal carrier ADVANCES with distance, the
                       same sign as the plane-wave factor ``exp(+i*k*z)``;
    * ``+k*r^2/2R`` -- a diverging beam (``R > 0`` for ``z > 0``) has a
                       wavefront that lags on axis relative to the edge;
    * ``-psi``      -- the Gouy phase is SUBTRACTED, giving a total retardation
                       of ``pi`` across the focus.

    Under the opposite ``exp(+i*omega*t)`` convention every one of these three
    signs flips, and the field is the complex conjugate of this one.
    """
    k = 2.0 * math.pi / wavelength_m
    rayleigh = math.pi * waist_m**2 / wavelength_m
    x_grid, y_grid = grid.meshgrid()
    r_sq = x_grid**2 + y_grid**2

    w_z = waist_m * math.sqrt(1.0 + (z / rayleigh) ** 2)
    gouy = math.atan2(z, rayleigh)
    curvature = 0.0 if z == 0.0 else k * r_sq / (2.0 * z * (1.0 + (rayleigh / z) ** 2))

    return (
        (waist_m / w_z)
        * np.exp(-r_sq / w_z**2)
        * np.exp(1j * (k * z + curvature - gouy))
    )


@pytest.mark.parametrize("z_over_rayleigh", [0.5, 1.0, 2.0])
def test_a09_gaussian_beam_matches_the_analytic_solution(
    wavelength: float, z_over_rayleigh: float
) -> None:
    """A-09: agreement with an independent analytic solution.

    Evidence class: independent analytic solution. Unlike the plane-wave
    tests, this exercises a field with genuine transverse structure and a
    non-trivial amplitude evolution, so it would catch errors that a single
    spatial frequency cannot -- for instance a transfer function correct only
    on the axis.

    **The tolerance floor here is the PARAXIAL APPROXIMATION, not float64.**
    The Angular Spectrum Method is exact and non-paraxial; the Gaussian beam
    formula is a paraxial solution of the same problem. They differ by
    O((lambda/(pi*w0))^2), which for ``w0 = 100 um`` at 633 nm is about
    4e-6. Measured agreement is 8e-7 to 3e-6 -- consistent with that estimate
    and roughly nine orders of magnitude above the float64 floor seen in the
    plane-wave tests.

    ``rtol=1e-4`` therefore has about a 30x margin over the model error.
    **It must not be tightened toward machine precision**: doing so would be
    fitting the test to the wrong physical model, and the failure would be in
    the reference, not the implementation.

    ``pad_factor=2`` is used because the beam is compact and expanding, which
    is exactly the regime where the periodic boundary would wrap.
    """
    waist = 100.0 * UM
    grid = SamplingGrid.square(n=512, pitch=4.0 * UM)
    rayleigh = math.pi * waist**2 / wavelength
    z = z_over_rayleigh * rayleigh

    source = ComplexField(
        data=_gaussian_beam_analytic(grid, wavelength, waist, 0.0),
        grid=grid,
        wavelength_m=wavelength,
    )
    out = propagate_angular_spectrum(source, distance_m=z, pad_factor=2)
    analytic = _gaussian_beam_analytic(grid, wavelength, waist, z)

    scale = float(np.max(np.abs(analytic)))
    error = float(np.max(np.abs(out.data - analytic))) / scale
    assert error < 1e-4, f"relative error {error:.3e} at z = {z_over_rayleigh} z_R"


def test_a10_gaussian_beam_radius_expands_as_predicted(wavelength: float) -> None:
    """A-10: the beam WIDTH follows ``w(z) = w0*sqrt(1 + (z/z_R)^2)``.

    An amplitude-domain check independent of every phase convention. It is
    completely insensitive to a propagation sign error, which is precisely why
    it is a useful companion: it confirms the magnitude of ``kz`` is right
    even if one doubted the sign tests.

    The radius is measured as the second moment of intensity, which for a
    Gaussian equals ``w(z)/2``.
    """
    waist = 100.0 * UM
    grid = SamplingGrid.square(n=512, pitch=4.0 * UM)
    rayleigh = math.pi * waist**2 / wavelength
    x_grid, y_grid = grid.meshgrid()
    r_sq = x_grid**2 + y_grid**2

    source = ComplexField(
        data=np.exp(-r_sq / waist**2).astype(np.complex128),
        grid=grid,
        wavelength_m=wavelength,
    )
    for factor in (0.5, 1.0, 2.0):
        z = factor * rayleigh
        out = propagate_angular_spectrum(source, distance_m=z, pad_factor=2)
        intensity = out.intensity
        second_moment = math.sqrt(
            float(np.sum(intensity * r_sq) / np.sum(intensity)) / 2.0
        )
        measured_w = 2.0 * second_moment
        expected_w = waist * math.sqrt(1.0 + (z / rayleigh) ** 2)
        assert measured_w == pytest.approx(expected_w, rel=2e-3), (
            f"z={factor} z_R: measured w={measured_w*1e6:.2f} um, "
            f"expected {expected_w*1e6:.2f} um"
        )


def test_a11_gaussian_gouy_phase_has_the_expected_sign_and_size(
    wavelength: float,
) -> None:
    """A-11: the Gouy phase is retarded by ``arctan(z/z_R)``.

    The on-axis phase of a Gaussian beam is ``k*z - arctan(z/z_R)``, i.e. it
    lags a plane wave by exactly the Gouy term. At ``z = z_R`` that lag is
    ``pi/4``.

    This is a sharp, sign-sensitive test of a subtle physical effect that no
    plane-wave test can reach, and it depends on the SUBTRACTION of the Gouy
    phase being right under our convention.
    """
    waist = 100.0 * UM
    grid = SamplingGrid.square(n=512, pitch=4.0 * UM)
    k = 2.0 * math.pi / wavelength
    rayleigh = math.pi * waist**2 / wavelength
    x_grid, y_grid = grid.meshgrid()

    source = ComplexField(
        data=np.exp(-(x_grid**2 + y_grid**2) / waist**2).astype(np.complex128),
        grid=grid,
        wavelength_m=wavelength,
    )
    z = rayleigh
    out = propagate_angular_spectrum(source, distance_m=z, pad_factor=2)

    centre = (grid.ny // 2, grid.nx // 2)
    measured_lag = np.angle(np.exp(1j * (k * z - out.phase[centre])))
    np.testing.assert_allclose(
        measured_lag, math.atan2(z, rayleigh), rtol=0.0, atol=2e-3
    )
    np.testing.assert_allclose(measured_lag, math.pi / 4.0, rtol=0.0, atol=2e-3)


def test_a12_gaussian_peak_intensity_falls_as_predicted(wavelength: float) -> None:
    """A-12: on-axis intensity follows ``(w0/w(z))^2``.

    Energy conservation expressed pointwise: as the beam expands its peak
    intensity must fall by exactly the ratio of areas.
    """
    waist = 100.0 * UM
    grid = SamplingGrid.square(n=512, pitch=4.0 * UM)
    rayleigh = math.pi * waist**2 / wavelength
    x_grid, y_grid = grid.meshgrid()
    centre = (grid.ny // 2, grid.nx // 2)

    source = ComplexField(
        data=np.exp(-(x_grid**2 + y_grid**2) / waist**2).astype(np.complex128),
        grid=grid,
        wavelength_m=wavelength,
    )
    peak0 = source.intensity[centre]
    for factor in (0.5, 1.0, 2.0):
        z = factor * rayleigh
        out = propagate_angular_spectrum(source, distance_m=z, pad_factor=2)
        w_z = waist * math.sqrt(1.0 + (z / rayleigh) ** 2)
        expected_ratio = (waist / w_z) ** 2
        assert out.intensity[centre] / peak0 == pytest.approx(
            expected_ratio, rel=5e-3
        )
