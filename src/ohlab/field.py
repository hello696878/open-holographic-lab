"""Sampled complex optical fields: :class:`ComplexField`.

A monochromatic scalar optical field is described at each point by two real
numbers -- an amplitude and a phase -- which are carried together as a single
complex number::

    U(x, y) = A(x, y) * exp(i * phi(x, y))

The physical, real, time-varying field is recovered as
``E(x, y, t) = Re{ U(x, y) * exp(-i * omega * t) }``. The factor
``exp(-i*omega*t)`` is identical at every point and is unchanged by every
linear optical element, so it is never stored. See
``docs/math_conventions.md`` section 3.1 for the sign convention and its
consequences.

Normative reference: ``docs/math_conventions.md`` sections 2.1, 3.1, 3.2, 3.3,
3.10, 3.11.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from .grid import SamplingGrid
from .validation import (
    as_complex128_array,
    as_float64_array,
    require_all_finite,
    require_finite_float,
    require_ndim,
    require_positive_finite_float,
    require_shape,
)

__all__ = ["ComplexField"]


def _require_seed(value: Any, name: str) -> int:
    """Validate a random seed: a non-negative, non-boolean integer."""
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a non-negative integer, got {value!r}")
    if not isinstance(value, (int, np.integer)):
        raise TypeError(
            f"{name} must be a non-negative integer, got {value!r} "
            f"(type {type(value).__name__})"
        )
    ivalue = int(value)
    if ivalue < 0:
        raise ValueError(f"{name} must be non-negative, got {ivalue}")
    return ivalue


def _as_real_map(
    value: npt.ArrayLike,
    name: str,
    grid: SamplingGrid,
    *,
    nonnegative: bool = False,
) -> np.ndarray:
    """Convert ``value`` to a finite float64 array of shape ``grid.shape``.

    A 0-dimensional input (a bare scalar) is broadcast to the full grid, so
    that ``phase=0.0`` is accepted as shorthand for a flat phase map.

    Parameters
    ----------
    nonnegative:
        When ``True``, reject negative entries. Used for amplitude and
        intensity, both of which are non-negative by definition (section 3.2).
        A negative "amplitude" would silently become a positive amplitude with
        an extra ``pi`` of phase, which is exactly the kind of quiet semantic
        drift this project forbids.
    """
    arr = as_float64_array(value, name)
    if arr.ndim == 0:
        arr = np.broadcast_to(arr, grid.shape).copy()
    require_ndim(arr, 2, name)
    require_shape(arr, grid.shape, name)
    require_all_finite(arr, name)
    if nonnegative and bool(np.any(arr < 0.0)):
        n_bad = int(np.count_nonzero(arr < 0.0))
        worst = float(np.min(arr))
        raise ValueError(
            f"{name} must be non-negative, but {n_bad} of {arr.size} entries "
            f"are negative (most negative: {worst!r})"
        )
    return arr


@dataclass(frozen=True, kw_only=True, eq=False, repr=False)
class ComplexField:
    """A sampled monochromatic scalar complex field on a :class:`SamplingGrid`.

    All parameters are **keyword-only**, enforcing section 3.3 at the language
    level.

    Parameters
    ----------
    data:
        The complex field ``U``. Any numeric array-like of shape
        ``grid.shape`` is accepted and converted to ``complex128``; real input
        is promoted. Must contain only finite values.
    grid:
        The sampling geometry.
    wavelength_m:
        Vacuum wavelength ``lambda`` in **metres**. Finite and ``> 0``.

    Notes
    -----
    **Immutability.** The instance is frozen, ``data`` is stored as a
    defensive copy, and that copy is marked non-writeable. Every operation
    returns a *new* :class:`ComplexField`. Gerchberg-Saxton (Milestone 3) is a
    loop that repeatedly swaps amplitudes and phases; aliasing bugs there are
    hard to find and produce plausible-looking wrong output.

    **Equality.** ``__eq__`` is *not* generated (``eq=False``), so ``==`` is
    identity comparison. A dataclass-generated ``__eq__`` would compare the
    ``data`` arrays with ``==``, yielding an array and then
    ``ValueError: truth value of an array is ambiguous``. Rather than paper
    over that with ``np.array_equal``, value comparison is exposed as
    :meth:`allclose`, which *requires* explicit tolerances.

    **Derived arrays** (:attr:`amplitude`, :attr:`phase`, :attr:`intensity`)
    are recomputed on every access and returned writeable. Only the stored
    :attr:`data` is read-only.

    Examples
    --------
    >>> from ohlab.units import NM, UM
    >>> g = SamplingGrid(ny=4, nx=4, dy=4 * UM, dx=4 * UM)
    >>> f = ComplexField.uniform(grid=g, wavelength_m=633 * NM, amplitude=2.0)
    >>> float(f.intensity[0, 0])
    4.0
    """

    data: np.ndarray
    grid: SamplingGrid
    wavelength_m: float

    def __post_init__(self) -> None:
        """Validate inputs, take a defensive copy, and freeze it."""
        if not isinstance(self.grid, SamplingGrid):
            raise TypeError(
                f"grid must be a SamplingGrid, got {type(self.grid).__name__}"
            )
        wavelength = require_positive_finite_float(self.wavelength_m, "wavelength_m")

        # as_complex128_array always returns a fresh array (astype copies), so
        # this is the defensive copy -- a later mutation of the caller's array
        # cannot reach us.
        arr = as_complex128_array(self.data, "data")
        require_ndim(arr, 2, "data")
        require_shape(arr, self.grid.shape, "data")
        require_all_finite(arr, "data")
        arr.flags.writeable = False

        object.__setattr__(self, "data", arr)
        object.__setattr__(self, "wavelength_m", wavelength)

    def __repr__(self) -> str:
        """Compact representation that never prints the array contents."""
        return (
            f"ComplexField(shape={self.shape}, dtype={self.data.dtype}, "
            f"wavelength_m={self.wavelength_m!r}, grid={self.grid!r})"
        )

    # ------------------------------------------------------------------
    # Physical quantities
    # ------------------------------------------------------------------
    @property
    def shape(self) -> tuple[int, int]:
        """Array shape ``(ny, nx)``, identical to ``self.grid.shape``."""
        return self.grid.shape

    @property
    def amplitude(self) -> np.ndarray:
        """Amplitude ``A = |U|``, shape ``(ny, nx)``, float64, ``>= 0``.

        Units are arbitrary (a.u.); see section 2.1.
        """
        return np.abs(self.data)

    @property
    def phase(self) -> np.ndarray:
        """Phase ``phi = arg(U)``, shape ``(ny, nx)``, float64, in radians.

        Returned on the canonical branch ``(-pi, +pi]`` (section 3.2). Note
        that ``np.angle(-1)`` is ``+pi``, not ``-pi``.

        Where the amplitude is zero the phase is **physically undefined**;
        NumPy returns ``0.0`` there as a matter of its own convention. Do not
        attach meaning to those values.
        """
        return np.angle(self.data)

    @property
    def intensity(self) -> np.ndarray:
        """Intensity ``I = |U|^2``, shape ``(ny, nx)``, float64, ``>= 0``.

        Computed as ``Re(U)^2 + Im(U)^2``. This is deliberately *not*
        ``np.abs(U)**2``: computing it independently of :attr:`amplitude`
        means the test asserting ``intensity == amplitude**2`` is a genuine
        cross-check between two separate code paths rather than a tautology.

        The physical constant relating this to W/m^2 is dropped by convention
        (section 2.1), so intensities are relative, not radiometric.

        Because no ``hypot``-style rescaling is used, amplitudes beyond about
        ``1e154`` would overflow. That is far outside any regime this project
        operates in; see ``known_limitations.md``.
        """
        return self.data.real**2 + self.data.imag**2

    @property
    def power(self) -> float:
        """Total optical power ``P = sum(I) * dx * dy``, in a.u. * m^2.

        The discretised area integral of the intensity over the window
        (section 2.1).
        """
        return float(np.sum(self.intensity) * self.grid.pixel_area)

    @property
    def wavenumber(self) -> float:
        """Wavenumber ``k = 2 * pi / lambda``, in rad/m."""
        return 2.0 * math.pi / self.wavelength_m

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------
    @classmethod
    def from_amplitude_phase(
        cls,
        *,
        amplitude: npt.ArrayLike,
        phase: npt.ArrayLike,
        grid: SamplingGrid,
        wavelength_m: float,
    ) -> ComplexField:
        """Build a field from separate amplitude and phase maps.

        ``U = A * exp(i * phi)``.

        Parameters
        ----------
        amplitude:
            Non-negative real map, or a scalar to broadcast. Units a.u.
        phase:
            Real map in radians, or a scalar to broadcast. Any branch is
            accepted; the stored field's :attr:`phase` will be wrapped back to
            ``(-pi, +pi]``.
        """
        if not isinstance(grid, SamplingGrid):
            raise TypeError(
                f"grid must be a SamplingGrid, got {type(grid).__name__}"
            )
        a = _as_real_map(amplitude, "amplitude", grid, nonnegative=True)
        p = _as_real_map(phase, "phase", grid)
        return cls(data=a * np.exp(1j * p), grid=grid, wavelength_m=wavelength_m)

    @classmethod
    def from_intensity_phase(
        cls,
        *,
        intensity: npt.ArrayLike,
        phase: npt.ArrayLike,
        grid: SamplingGrid,
        wavelength_m: float,
    ) -> ComplexField:
        """Build a field from separate intensity and phase maps.

        ``A = sqrt(I)``, then ``U = A * exp(i * phi)``.
        """
        if not isinstance(grid, SamplingGrid):
            raise TypeError(
                f"grid must be a SamplingGrid, got {type(grid).__name__}"
            )
        inten = _as_real_map(intensity, "intensity", grid, nonnegative=True)
        return cls.from_amplitude_phase(
            amplitude=np.sqrt(inten),
            phase=phase,
            grid=grid,
            wavelength_m=wavelength_m,
        )

    @classmethod
    def uniform(
        cls,
        *,
        grid: SamplingGrid,
        wavelength_m: float,
        amplitude: float = 1.0,
    ) -> ComplexField:
        """Build a spatially constant field with zero phase.

        Parameters
        ----------
        amplitude:
            Scalar, finite, ``>= 0``.
        """
        if not isinstance(grid, SamplingGrid):
            raise TypeError(
                f"grid must be a SamplingGrid, got {type(grid).__name__}"
            )
        amp = require_finite_float(amplitude, "amplitude")
        if amp < 0.0:
            raise ValueError(f"amplitude must be non-negative, got {amp!r}")
        data = np.full(grid.shape, amp, dtype=np.complex128)
        return cls(data=data, grid=grid, wavelength_m=wavelength_m)

    @classmethod
    def plane_wave(
        cls,
        *,
        grid: SamplingGrid,
        wavelength_m: float,
        theta_x_rad: float = 0.0,
        theta_y_rad: float = 0.0,
        amplitude: float = 1.0,
    ) -> ComplexField:
        """Build a tilted plane wave of uniform amplitude.

        ``U = A * exp(i * (kx * x + ky * y))`` with
        ``kx = k * sin(theta_x)``, ``ky = k * sin(theta_y)``, ``k = 2*pi/lambda``.

        Two independent conditions are enforced.

        **Physical validity (propagating wave).** A homogeneous plane wave
        must satisfy ``kx^2 + ky^2 + kz^2 = k^2`` with ``kz`` real, hence::

            kx^2 + ky^2 <= k^2      equivalently   sin^2(theta_x) + sin^2(theta_y) <= 1

        A pair of individually reasonable tilt angles can violate this jointly
        -- for example 50 degrees in both x and y gives 1.174 -- which would
        describe an evanescent, not a propagating, wave. That is rejected.

        **Sampling validity (Nyquist).** Each transverse frequency must be
        representable on the grid::

            |sin(theta_x)| / lambda <= 1 / (2 * dx)

        and likewise for y. Exceeding this would alias silently.

        The condition is checked in that order, so a non-propagating request is
        reported as such even on a grid fine enough to sample it.

        Parameters
        ----------
        theta_x_rad, theta_y_rad:
            Tilt angles in radians, finite.
        amplitude:
            Scalar, finite, ``>= 0``.

        Raises
        ------
        ValueError
            The angles describe a non-propagating wave, or exceed the grid's
            Nyquist limit on either axis.
        """
        if not isinstance(grid, SamplingGrid):
            raise TypeError(
                f"grid must be a SamplingGrid, got {type(grid).__name__}"
            )
        lam = require_positive_finite_float(wavelength_m, "wavelength_m")
        tx = require_finite_float(theta_x_rad, "theta_x_rad")
        ty = require_finite_float(theta_y_rad, "theta_y_rad")
        amp = require_finite_float(amplitude, "amplitude")
        if amp < 0.0:
            raise ValueError(f"amplitude must be non-negative, got {amp!r}")

        sin_x = math.sin(tx)
        sin_y = math.sin(ty)

        # (1) Propagating-wave condition, written as sin^2 + sin^2 <= 1 rather
        #     than kx^2 + ky^2 <= k^2. The two are equivalent (divide by k^2)
        #     but this form avoids forming k^2 ~ 1e14 and losing precision to
        #     cancellation. The boundary case is subject to the rounding of
        #     math.sin; grazing incidence is degenerate anyway (kz = 0).
        transverse = sin_x * sin_x + sin_y * sin_y
        if transverse > 1.0:
            raise ValueError(
                f"theta_x_rad={tx!r} and theta_y_rad={ty!r} do not describe a "
                f"propagating plane wave: sin^2(theta_x) + sin^2(theta_y) = "
                f"{transverse!r} > 1, which requires kx^2 + ky^2 > k^2 and "
                f"hence an imaginary kz (an evanescent wave). Each angle is "
                f"individually valid; it is the combination that is not."
            )

        # (2) Per-axis Nyquist limits.
        fx = sin_x / lam
        fy = sin_y / lam
        if abs(fx) > grid.nyquist_fx:
            raise ValueError(
                f"theta_x_rad={tx!r} needs spatial frequency |fx|={abs(fx)!r} "
                f"cycles/m, which exceeds the grid Nyquist frequency "
                f"{grid.nyquist_fx!r} cycles/m (dx={grid.dx!r} m); the field "
                f"would alias"
            )
        if abs(fy) > grid.nyquist_fy:
            raise ValueError(
                f"theta_y_rad={ty!r} needs spatial frequency |fy|={abs(fy)!r} "
                f"cycles/m, which exceeds the grid Nyquist frequency "
                f"{grid.nyquist_fy!r} cycles/m (dy={grid.dy!r} m); the field "
                f"would alias"
            )

        k = 2.0 * math.pi / lam
        kx = k * sin_x
        ky = k * sin_y
        x_grid, y_grid = grid.meshgrid()
        data = amp * np.exp(1j * (kx * x_grid + ky * y_grid))
        return cls(data=data, grid=grid, wavelength_m=lam)

    @classmethod
    def random_phase(
        cls,
        *,
        grid: SamplingGrid,
        wavelength_m: float,
        seed: int,
        amplitude: float = 1.0,
    ) -> ComplexField:
        """Build a field of uniform amplitude and uniformly random phase.

        The phase is drawn from ``U(-pi, +pi)``. This is the standard starting
        point for Gerchberg-Saxton (Milestone 3).

        Parameters
        ----------
        seed:
            Non-negative integer. **Mandatory** -- section 3.10 forbids
            implicit randomness. The generator is
            ``np.random.default_rng(seed)``; the legacy global ``np.random.*``
            API is never used. The same seed reproduces the field bit for bit.
        """
        if not isinstance(grid, SamplingGrid):
            raise TypeError(
                f"grid must be a SamplingGrid, got {type(grid).__name__}"
            )
        amp = require_finite_float(amplitude, "amplitude")
        if amp < 0.0:
            raise ValueError(f"amplitude must be non-negative, got {amp!r}")
        seed_value = _require_seed(seed, "seed")

        rng = np.random.default_rng(seed_value)
        phase = rng.uniform(-math.pi, math.pi, size=grid.shape)
        data = amp * np.exp(1j * phase)
        return cls(data=data, grid=grid, wavelength_m=wavelength_m)

    # ------------------------------------------------------------------
    # Derived fields -- always return a NEW ComplexField
    # ------------------------------------------------------------------
    def with_data(self, data: npt.ArrayLike) -> ComplexField:
        """Return a new field with different data on the same grid/wavelength."""
        return ComplexField(
            data=data, grid=self.grid, wavelength_m=self.wavelength_m
        )

    def with_amplitude(self, amplitude: npt.ArrayLike) -> ComplexField:
        """Return a new field with this field's phase and a new amplitude.

        ``U_new = A_new * exp(i * arg(U))``.

        This is one of the two Gerchberg-Saxton projection steps: replace the
        measured/target amplitude while keeping the retrieved phase.

        Note that the phase is *recomputed* via ``np.angle`` and then
        re-applied through ``exp``, so the resulting phase agrees with the
        original only to floating-point precision, not bit for bit. Where the
        original amplitude is zero the phase is undefined and the result there
        is not meaningful.
        """
        a = _as_real_map(amplitude, "amplitude", self.grid, nonnegative=True)
        return self.with_data(a * np.exp(1j * self.phase))

    def with_phase(self, phase: npt.ArrayLike) -> ComplexField:
        """Return a new field with this field's amplitude and a new phase.

        ``U_new = |U| * exp(i * phi_new)``.

        The other Gerchberg-Saxton projection step: keep the amplitude,
        replace the phase.
        """
        p = _as_real_map(phase, "phase", self.grid)
        return self.with_data(self.amplitude * np.exp(1j * p))

    def scaled(self, factor: complex) -> ComplexField:
        """Return this field multiplied by a complex scalar.

        A real positive ``factor`` rescales amplitude and leaves phase
        unchanged (to floating-point precision); a unit-modulus ``factor``
        adds a constant phase and leaves intensity unchanged.
        """
        if isinstance(factor, bool) or not isinstance(
            factor, (int, float, complex, np.number)
        ):
            raise TypeError(
                f"factor must be a finite number, got {factor!r} "
                f"(type {type(factor).__name__})"
            )
        value = complex(factor)
        if not (math.isfinite(value.real) and math.isfinite(value.imag)):
            raise ValueError(f"factor must be finite, got {value!r}")
        return self.with_data(self.data * value)

    def normalized_power(self, target: float = 1.0) -> ComplexField:
        """Return this field rescaled to have total power ``target``.

        Multiplies by the positive real scalar ``sqrt(target / power)``, so the
        phase is preserved up to floating-point precision.

        Raises
        ------
        ValueError
            ``target`` is not strictly positive, or this field has zero power
            and therefore cannot be rescaled.
        """
        goal = require_positive_finite_float(target, "target")
        current = self.power
        if current <= 0.0:
            raise ValueError(
                "cannot normalise a field whose total power is zero"
            )
        return self.scaled(math.sqrt(goal / current))

    def conjugate(self) -> ComplexField:
        """Return the complex conjugate field, ``U* = A * exp(-i * phi)``.

        Amplitude and power are preserved exactly; the phase is negated.
        """
        return self.with_data(np.conj(self.data))

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------
    def allclose(self, other: ComplexField, *, rtol: float, atol: float) -> bool:
        """Compare two fields elementwise within explicit tolerances.

        Both ``rtol`` and ``atol`` are **keyword-only and mandatory**: there is
        no default tolerance anywhere in this project.

        Raises
        ------
        TypeError
            ``other`` is not a :class:`ComplexField`.
        ValueError
            The two fields have different grids or wavelengths, or a tolerance
            is negative or non-finite.
        """
        if not isinstance(other, ComplexField):
            raise TypeError(
                f"other must be a ComplexField, got {type(other).__name__}"
            )
        if other.grid != self.grid:
            raise ValueError(
                f"cannot compare fields on different grids: "
                f"{self.grid!r} vs {other.grid!r}"
            )
        if other.wavelength_m != self.wavelength_m:
            raise ValueError(
                f"cannot compare fields at different wavelengths: "
                f"{self.wavelength_m!r} m vs {other.wavelength_m!r} m"
            )
        rtol_value = require_finite_float(rtol, "rtol")
        atol_value = require_finite_float(atol, "atol")
        if rtol_value < 0.0 or atol_value < 0.0:
            raise ValueError(
                f"tolerances must be non-negative, got rtol={rtol_value!r}, "
                f"atol={atol_value!r}"
            )
        return bool(
            np.allclose(self.data, other.data, rtol=rtol_value, atol=atol_value)
        )
