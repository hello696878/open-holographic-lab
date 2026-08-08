"""Tests for :class:`ohlab.field.ComplexField` (Milestone 0, IDs F-01 .. F-27).

Phase comparison policy
-----------------------
Operations such as :meth:`ComplexField.with_amplitude` reconstruct the field
as ``A * exp(i*phi)``, recomputing ``phi`` through ``np.angle`` and re-applying
it through ``np.exp``. The result therefore agrees with the original only to
floating-point precision, **not** bit for bit, so those tests use explicit
``rtol``/``atol`` rather than exact equality.

Phase is also only defined modulo ``2*pi``, and ``np.angle`` has a branch cut
on the negative real axis. Comparisons therefore go through
``wrapped_phase_difference``, i.e. ``angle(exp(i*(actual - expected)))``, which
returns zero for physically identical phases regardless of branch. Pixels of
zero amplitude are excluded, because phase is physically undefined there
(``docs/math_conventions.md`` section 3.2).

Bit-for-bit equality is asserted only where the implementation genuinely
preserves an array without recomputation: the defensive copy (F-19) and
seeded reproducibility (F-22).
"""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from _helpers import assert_bit_identical, assert_phase_allclose
from ohlab.field import ComplexField
from ohlab.grid import SamplingGrid
from ohlab.units import NM, UM


@pytest.fixture
def sample_field(
    aniso_grid: SamplingGrid, wavelength: float, rng: np.random.Generator
) -> ComplexField:
    """A generic field with strictly positive amplitude and varied phase.

    The amplitude floor of 0.5 keeps every pixel's phase well defined, so
    phase assertions are not silently skipped.
    """
    amplitude = 0.5 + rng.random(aniso_grid.shape) * 3.0
    phase = rng.uniform(-math.pi, math.pi, aniso_grid.shape)
    return ComplexField.from_amplitude_phase(
        amplitude=amplitude,
        phase=phase,
        grid=aniso_grid,
        wavelength_m=wavelength,
    )


# ---------------------------------------------------------------------------
# Construction and validation
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "dtype", [np.int32, np.int64, np.float32, np.float64, np.complex64]
)
def test_f01_dtype_promotion(
    aniso_grid: SamplingGrid, wavelength: float, dtype: type
) -> None:
    """F-01: any numeric input dtype is promoted to ``complex128``."""
    data = np.ones(aniso_grid.shape, dtype=dtype)
    field = ComplexField(data=data, grid=aniso_grid, wavelength_m=wavelength)
    assert field.data.dtype == np.complex128


def test_f02_transposed_shape_is_rejected(
    aniso_grid: SamplingGrid, wavelength: float
) -> None:
    """F-02: the transposition trap.

    ``aniso_grid`` is 6 x 10, so passing a 10 x 6 array is a shape error. On a
    square grid this mistake would pass silently, which is why every field
    test uses the anisotropic fixture.
    """
    wrong = np.ones((aniso_grid.nx, aniso_grid.ny), dtype=np.complex128)
    with pytest.raises(ValueError, match=r"\(ny, nx\)"):
        ComplexField(data=wrong, grid=aniso_grid, wavelength_m=wavelength)


def test_f03_non_finite_data_rejected(
    aniso_grid: SamplingGrid, wavelength: float
) -> None:
    """F-03: NaN or Inf anywhere in the data is rejected at construction."""
    data = np.ones(aniso_grid.shape, dtype=np.complex128)
    data[3, 7] = complex(np.nan, 0.0)
    with pytest.raises(ValueError, match="finite"):
        ComplexField(data=data, grid=aniso_grid, wavelength_m=wavelength)


@pytest.mark.parametrize("bad", [0.0, -633e-9, float("nan"), float("inf")])
def test_f04_invalid_wavelength_rejected(
    aniso_grid: SamplingGrid, bad: float
) -> None:
    """F-04: wavelength must be finite and strictly positive."""
    data = np.ones(aniso_grid.shape, dtype=np.complex128)
    with pytest.raises(ValueError):
        ComplexField(data=data, grid=aniso_grid, wavelength_m=bad)


def test_f04b_positional_construction_rejected(
    aniso_grid: SamplingGrid, wavelength: float
) -> None:
    """F-04b: the constructor is keyword-only (section 3.3)."""
    data = np.ones(aniso_grid.shape, dtype=np.complex128)
    with pytest.raises(TypeError):
        ComplexField(data, aniso_grid, wavelength)  # type: ignore[misc]


def test_f04c_grid_type_is_checked(wavelength: float) -> None:
    """F-04c: ``grid`` must be a :class:`SamplingGrid`, not a bare tuple."""
    with pytest.raises(TypeError, match="SamplingGrid"):
        ComplexField(
            data=np.ones((2, 2)), grid=(2, 2), wavelength_m=wavelength  # type: ignore[arg-type]
        )


def test_f04d_negative_amplitude_rejected(
    aniso_grid: SamplingGrid, wavelength: float
) -> None:
    """F-04d: a negative amplitude is an error, not a hidden extra pi of phase.

    ``(-A) * exp(i*phi)`` equals ``A * exp(i*(phi + pi))``, so accepting it
    would silently alter the phase map the caller thought they supplied.
    """
    amplitude = np.ones(aniso_grid.shape)
    amplitude[0, 0] = -1.0
    with pytest.raises(ValueError, match="non-negative"):
        ComplexField.from_amplitude_phase(
            amplitude=amplitude,
            phase=0.0,
            grid=aniso_grid,
            wavelength_m=wavelength,
        )


# ---------------------------------------------------------------------------
# Amplitude, phase, intensity
# ---------------------------------------------------------------------------
def test_f05_amplitude_phase_round_trip(
    aniso_grid: SamplingGrid, wavelength: float, rng: np.random.Generator
) -> None:
    """F-05: ``from_amplitude_phase`` recovers its own inputs.

    Evidence class: exact algebraic identity, ``|A e^{i phi}| = A``.
    Tolerances: ``rtol=1e-12`` on amplitude and ``atol=1e-12`` rad on the
    wrapped phase difference. Measured worst-case error is 2.9e-16 and
    2.2e-16 respectively, so this leaves roughly a 4000x margin -- ample for
    libm variation across platforms, yet far tighter than any real defect,
    which would be O(1).
    """
    amplitude = 0.25 + rng.random(aniso_grid.shape) * 5.0
    phase = rng.uniform(-math.pi, math.pi, aniso_grid.shape)
    field = ComplexField.from_amplitude_phase(
        amplitude=amplitude, phase=phase, grid=aniso_grid, wavelength_m=wavelength
    )
    np.testing.assert_allclose(field.amplitude, amplitude, rtol=1e-12, atol=0.0)
    assert_phase_allclose(
        field.phase, phase, atol=1e-12, amplitude=field.amplitude
    )


def test_f06_phase_is_wrapped_to_canonical_branch(
    aniso_grid: SamplingGrid, wavelength: float
) -> None:
    """F-06: phase is returned on ``(-pi, +pi]`` (section 3.2).

    Two specific cases are pinned:

    * ``phi = 3*pi/2`` must come back as ``-pi/2``, not ``4.712``.
    * ``U = -1`` must give ``+pi``, not ``-pi``. The interval is half-open at
      the top, and NumPy's convention places the negative real axis at ``+pi``.
    """
    field = ComplexField.from_amplitude_phase(
        amplitude=1.0,
        phase=3.0 * math.pi / 2.0,
        grid=aniso_grid,
        wavelength_m=wavelength,
    )
    np.testing.assert_allclose(
        field.phase, np.full(aniso_grid.shape, -math.pi / 2.0),
        rtol=0.0, atol=1e-12,
    )
    assert np.all(field.phase > -math.pi)
    assert np.all(field.phase <= math.pi)

    negative_real = ComplexField(
        data=np.full(aniso_grid.shape, -1.0 + 0.0j),
        grid=aniso_grid,
        wavelength_m=wavelength,
    )
    assert np.all(negative_real.phase == math.pi)  # exactly +pi, not -pi


def test_f07_intensity_matches_amplitude_squared(
    sample_field: ComplexField,
) -> None:
    """F-07: ``I == A**2``, computed by two independent code paths.

    ``intensity`` uses ``Re^2 + Im^2`` while ``amplitude`` uses ``np.abs``
    (a hypot). The agreement is therefore a genuine cross-check, not a
    tautology. Tolerance ``rtol=1e-12``; measured worst case 7.5e-16.
    """
    np.testing.assert_allclose(
        sample_field.intensity,
        sample_field.amplitude**2,
        rtol=1e-12,
        atol=0.0,
    )
    assert sample_field.intensity.dtype == np.float64
    assert np.all(sample_field.intensity >= 0.0)
    assert np.all(sample_field.amplitude >= 0.0)


def test_f08_zero_amplitude_phase_is_defined_by_numpy_not_physics(
    aniso_grid: SamplingGrid, wavelength: float
) -> None:
    """F-08: a zero pixel yields phase 0.0 and raises no warning.

    Physically the phase is undefined there. ``0.0`` is NumPy's convention,
    and the project must not attach meaning to it. Because pytest is
    configured with ``filterwarnings = ["error"]``, any RuntimeWarning emitted
    here would fail this test.
    """
    data = np.zeros(aniso_grid.shape, dtype=np.complex128)
    field = ComplexField(data=data, grid=aniso_grid, wavelength_m=wavelength)
    assert np.all(field.phase == 0.0)
    assert np.all(field.amplitude == 0.0)
    assert field.power == 0.0


# ---------------------------------------------------------------------------
# Power
# ---------------------------------------------------------------------------
def test_f09_power_is_the_discretised_area_integral(
    sample_field: ComplexField,
) -> None:
    """F-09: ``P = sum(I) * dx * dy`` (section 2.1)."""
    expected = float(
        np.sum(sample_field.intensity) * sample_field.grid.pixel_area
    )
    assert sample_field.power == pytest.approx(expected, rel=1e-15)


@pytest.mark.parametrize("factor", [2.0, 0.5, -3.0, 1j, (0.6 + 0.8j)])
def test_f09b_power_scales_as_modulus_squared(
    sample_field: ComplexField, factor: complex
) -> None:
    """F-09b: scaling the field by ``c`` scales power by ``|c|^2``.

    Evidence class: exact algebraic identity. ``rtol=1e-12`` covers the
    summation over all pixels, whose error grows only as the square root of
    the pixel count.
    """
    scaled = sample_field.scaled(factor)
    np.testing.assert_allclose(
        scaled.power, sample_field.power * abs(factor) ** 2, rtol=1e-12, atol=0.0
    )


def test_f10_phase_only_multiplication_preserves_intensity_and_power(
    sample_field: ComplexField, rng: np.random.Generator
) -> None:
    """F-10: multiplying by ``exp(i*psi)`` changes neither intensity nor power.

    Evidence class: symmetry / conservation. ``|exp(i*psi)| = 1`` exactly, so
    this is the defining property of a phase-only element -- the reason a
    phase-only SLM can steer light without absorbing it.

    ``psi`` spans many multiples of ``2*pi`` deliberately, to exercise the
    wrapping path rather than only small perturbations.

    Tolerance ``rtol=1e-12``; measured worst case 1.0e-15 for intensity and
    exactly 0 for power.
    """
    psi = rng.uniform(-50 * math.pi, 50 * math.pi, sample_field.shape)
    modulated = sample_field.with_data(sample_field.data * np.exp(1j * psi))

    np.testing.assert_allclose(
        modulated.intensity, sample_field.intensity, rtol=1e-12, atol=0.0
    )
    np.testing.assert_allclose(
        modulated.power, sample_field.power, rtol=1e-12, atol=0.0
    )


def test_f11_normalized_power_hits_target_and_preserves_phase(
    sample_field: ComplexField,
) -> None:
    """F-11: normalisation rescales power and leaves the phase alone.

    Evidence class: round-trip identity.

    The phase is compared with ``atol=1e-12`` rad on the *wrapped* difference,
    not bit for bit: ``scaled`` multiplies the complex data by a positive real
    scalar, and ``atan2(b*c, a*c)`` is not guaranteed to reproduce
    ``atan2(b, a)`` exactly.
    """
    for target in (1.0, 7.5):
        normalised = sample_field.normalized_power(target)
        np.testing.assert_allclose(
            normalised.power, target, rtol=1e-12, atol=0.0
        )
        assert_phase_allclose(
            normalised.phase,
            sample_field.phase,
            atol=1e-12,
            amplitude=sample_field.amplitude,
        )


def test_f11b_normalization_rejects_impossible_requests(
    aniso_grid: SamplingGrid, wavelength: float, sample_field: ComplexField
) -> None:
    """F-11b: a zero-power field cannot be normalised; target must be > 0."""
    empty = ComplexField(
        data=np.zeros(aniso_grid.shape), grid=aniso_grid, wavelength_m=wavelength
    )
    with pytest.raises(ValueError, match="zero"):
        empty.normalized_power(1.0)
    with pytest.raises(ValueError, match="strictly positive"):
        sample_field.normalized_power(0.0)


# ---------------------------------------------------------------------------
# Derived-field operations
# ---------------------------------------------------------------------------
def test_f12_with_phase_replaces_phase_and_keeps_amplitude(
    sample_field: ComplexField, rng: np.random.Generator
) -> None:
    """F-12: ``with_phase`` is the Gerchberg-Saxton phase-projection step.

    Amplitude compared with ``rtol=1e-12``; the field is rebuilt as
    ``A * exp(i*phi_new)`` so ``|U|`` is recomputed and cannot be expected to
    match bit for bit.
    """
    new_phase = rng.uniform(-math.pi, math.pi, sample_field.shape)
    result = sample_field.with_phase(new_phase)

    np.testing.assert_allclose(
        result.amplitude, sample_field.amplitude, rtol=1e-12, atol=0.0
    )
    assert_phase_allclose(
        result.phase, new_phase, atol=1e-12, amplitude=result.amplitude
    )


def test_f13_with_amplitude_replaces_amplitude_and_keeps_phase(
    sample_field: ComplexField, rng: np.random.Generator
) -> None:
    """F-13: ``with_amplitude`` is the amplitude-projection step.

    The phase is recomputed via ``np.angle`` and re-applied through ``np.exp``,
    so it is compared as a wrapped difference within ``atol=1e-12`` rad, not
    bit for bit.
    """
    new_amplitude = 0.25 + rng.random(sample_field.shape) * 2.0
    result = sample_field.with_amplitude(new_amplitude)

    np.testing.assert_allclose(
        result.amplitude, new_amplitude, rtol=1e-12, atol=0.0
    )
    assert_phase_allclose(
        result.phase,
        sample_field.phase,
        atol=1e-12,
        amplitude=sample_field.amplitude,
    )


def test_f14_projection_steps_reject_mismatched_shapes(
    sample_field: ComplexField,
) -> None:
    """F-14: projection inputs are validated against the grid."""
    wrong = np.ones((sample_field.grid.nx, sample_field.grid.ny))
    with pytest.raises(ValueError):
        sample_field.with_phase(wrong)
    with pytest.raises(ValueError):
        sample_field.with_amplitude(wrong)
    with pytest.raises(ValueError, match="non-negative"):
        sample_field.with_amplitude(-np.ones(sample_field.shape))


def test_f15_conjugate_negates_phase_and_preserves_amplitude(
    sample_field: ComplexField,
) -> None:
    """F-15: ``U* = A exp(-i phi)``.

    Evidence class: symmetry. Amplitude uses ``rtol=1e-15`` rather than exact
    equality; the phase uses the wrapped difference against ``-phi``, which
    also handles the ``+pi``/``-pi`` branch flip that conjugation induces on
    the negative real axis.
    """
    conjugated = sample_field.conjugate()
    np.testing.assert_allclose(
        conjugated.amplitude, sample_field.amplitude, rtol=1e-15, atol=0.0
    )
    assert_phase_allclose(
        conjugated.phase,
        -sample_field.phase,
        atol=1e-12,
        amplitude=sample_field.amplitude,
    )
    np.testing.assert_allclose(
        conjugated.power, sample_field.power, rtol=1e-12, atol=0.0
    )


def test_f16_scaled_rejects_non_finite_and_non_numeric(
    sample_field: ComplexField,
) -> None:
    """F-16: scalar multipliers are validated."""
    with pytest.raises(ValueError, match="finite"):
        sample_field.scaled(complex(float("inf"), 0.0))
    with pytest.raises(TypeError):
        sample_field.scaled("2")  # type: ignore[arg-type]


def test_f17_uniform_field(aniso_grid: SamplingGrid, wavelength: float) -> None:
    """F-17: ``uniform(amplitude=a)`` has intensity ``a**2`` and zero phase."""
    field = ComplexField.uniform(
        grid=aniso_grid, wavelength_m=wavelength, amplitude=3.0
    )
    np.testing.assert_allclose(
        field.intensity, np.full(aniso_grid.shape, 9.0), rtol=1e-12, atol=0.0
    )
    assert np.all(field.phase == 0.0)


def test_f18_from_intensity_phase_is_the_square_root_of_from_amplitude(
    aniso_grid: SamplingGrid, wavelength: float, rng: np.random.Generator
) -> None:
    """F-18: ``from_intensity_phase(I)`` equals ``from_amplitude_phase(sqrt(I))``."""
    intensity = 0.1 + rng.random(aniso_grid.shape) * 4.0
    phase = rng.uniform(-math.pi, math.pi, aniso_grid.shape)
    a = ComplexField.from_intensity_phase(
        intensity=intensity, phase=phase, grid=aniso_grid, wavelength_m=wavelength
    )
    b = ComplexField.from_amplitude_phase(
        amplitude=np.sqrt(intensity),
        phase=phase,
        grid=aniso_grid,
        wavelength_m=wavelength,
    )
    assert a.allclose(b, rtol=1e-12, atol=0.0)
    np.testing.assert_allclose(a.intensity, intensity, rtol=1e-12, atol=0.0)


# ---------------------------------------------------------------------------
# Immutability and determinism
# ---------------------------------------------------------------------------
def test_f19_construction_takes_a_defensive_copy(
    aniso_grid: SamplingGrid, wavelength: float
) -> None:
    """F-19: mutating the source array afterwards cannot alter the field.

    EXACTNESS IS THE PROPERTY UNDER TEST. Here the implementation genuinely
    preserves the stored array without recomputation, so bit-for-bit equality
    is the correct assertion.
    """
    source = np.ones(aniso_grid.shape, dtype=np.complex128)
    field = ComplexField(data=source, grid=aniso_grid, wavelength_m=wavelength)
    snapshot = field.data.copy()

    source[0, 0] = 999.0 + 999.0j
    assert_bit_identical(field.data, snapshot)
    assert not np.shares_memory(field.data, source)


def test_f20_stored_data_is_read_only_and_instance_is_frozen(
    sample_field: ComplexField,
) -> None:
    """F-20: neither the array nor the attribute binding can be mutated."""
    assert sample_field.data.flags.writeable is False
    with pytest.raises(ValueError):
        sample_field.data[0, 0] = 1.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        sample_field.data = np.zeros(sample_field.shape)  # type: ignore[misc]


def test_f21_derived_arrays_are_fresh_and_writeable(
    sample_field: ComplexField,
) -> None:
    """F-21: derived arrays are recomputed, so mutating one is harmless."""
    amplitude = sample_field.amplitude
    pristine = amplitude.copy()
    amplitude[0, 0] = -12345.0
    assert_bit_identical(sample_field.amplitude, pristine)


def test_f22_random_phase_is_reproducible_from_its_seed(
    aniso_grid: SamplingGrid, wavelength: float
) -> None:
    """F-22: same seed gives bit-identical data; a different seed differs.

    EXACTNESS IS THE PROPERTY UNDER TEST -- section 3.10 requires bit-for-bit
    reproducibility from a saved configuration.
    """
    a = ComplexField.random_phase(
        grid=aniso_grid, wavelength_m=wavelength, seed=42
    )
    b = ComplexField.random_phase(
        grid=aniso_grid, wavelength_m=wavelength, seed=42
    )
    c = ComplexField.random_phase(
        grid=aniso_grid, wavelength_m=wavelength, seed=43
    )
    assert_bit_identical(a.data, b.data)
    assert not np.array_equal(a.data, c.data)

    # Uniform amplitude, phase spanning the full branch.
    np.testing.assert_allclose(
        a.amplitude, np.ones(aniso_grid.shape), rtol=1e-12, atol=0.0
    )
    assert np.all(a.phase > -math.pi)
    assert np.all(a.phase <= math.pi)


def test_f22b_seed_is_mandatory_and_validated(
    aniso_grid: SamplingGrid, wavelength: float
) -> None:
    """F-22b: randomness is never implicit (section 3.10)."""
    with pytest.raises(TypeError):
        ComplexField.random_phase(  # type: ignore[call-arg]
            grid=aniso_grid, wavelength_m=wavelength
        )
    with pytest.raises(ValueError):
        ComplexField.random_phase(
            grid=aniso_grid, wavelength_m=wavelength, seed=-1
        )
    with pytest.raises(TypeError):
        ComplexField.random_phase(
            grid=aniso_grid, wavelength_m=wavelength, seed=True
        )


# ---------------------------------------------------------------------------
# Comparison semantics
# ---------------------------------------------------------------------------
def test_f23_equality_is_identity_and_allclose_is_explicit(
    sample_field: ComplexField,
) -> None:
    """F-23: ``==`` is identity; value comparison requires explicit tolerances.

    A dataclass-generated ``__eq__`` would compare the arrays with ``==`` and
    then raise ``ValueError: truth value of an array is ambiguous``. Asserting
    that ``==`` is well-defined and identity-based pins that design decision.
    """
    twin = sample_field.with_data(sample_field.data)
    assert sample_field == sample_field
    assert sample_field != twin  # identity, not value
    assert sample_field.allclose(twin, rtol=0.0, atol=0.0)

    with pytest.raises(TypeError):
        sample_field.allclose(twin)  # type: ignore[call-arg]


def test_f24_allclose_detects_a_small_perturbation(
    sample_field: ComplexField,
) -> None:
    """F-24: ``allclose`` separates equal fields from slightly perturbed ones."""
    perturbed = sample_field.scaled(1.0 + 1e-9)
    assert not sample_field.allclose(perturbed, rtol=1e-12, atol=0.0)
    assert sample_field.allclose(perturbed, rtol=1e-6, atol=0.0)


def test_f25_allclose_rejects_incompatible_operands(
    sample_field: ComplexField, wavelength: float
) -> None:
    """F-25: fields on different grids or wavelengths cannot be compared."""
    other_grid = SamplingGrid(ny=6, nx=10, dy=1.0 * UM, dx=1.0 * UM)
    other = ComplexField.uniform(grid=other_grid, wavelength_m=wavelength)
    with pytest.raises(ValueError, match="different grids"):
        sample_field.allclose(other, rtol=1e-12, atol=0.0)

    other_wavelength = sample_field.with_data(sample_field.data)
    shifted = ComplexField(
        data=other_wavelength.data,
        grid=sample_field.grid,
        wavelength_m=532 * NM,
    )
    with pytest.raises(ValueError, match="different wavelengths"):
        sample_field.allclose(shifted, rtol=1e-12, atol=0.0)

    with pytest.raises(TypeError):
        sample_field.allclose(object(), rtol=1e-12, atol=0.0)  # type: ignore[arg-type]


def test_f26_wavenumber(aniso_grid: SamplingGrid) -> None:
    """F-26: ``k = 2*pi/lambda``. For 633 nm this is 9.9260e6 rad/m."""
    field = ComplexField.uniform(grid=aniso_grid, wavelength_m=633 * NM)
    np.testing.assert_allclose(
        field.wavenumber, 2.0 * math.pi / 633e-9, rtol=1e-15, atol=0.0
    )
    assert field.wavenumber == pytest.approx(9.926e6, rel=1e-3)


def test_f27_repr_does_not_dump_the_array(sample_field: ComplexField) -> None:
    """F-27: ``repr`` stays readable for megapixel fields."""
    text = repr(sample_field)
    assert "ComplexField(" in text
    assert "shape=(6, 10)" in text
    assert len(text) < 400
