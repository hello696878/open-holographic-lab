"""Sampling geometry: :class:`SamplingGrid`.

A :class:`SamplingGrid` is the bridge between array indices and physical
metres. It stores only four numbers -- two sample counts and two pixel
pitches -- and derives everything else, so no two stored quantities can ever
disagree.

Normative reference: ``docs/math_conventions.md`` sections 3.3, 3.4, 3.5, 3.8.

Conventions implemented here
----------------------------
Array layout (section 3.3)
    ``shape == (ny, nx)``. Axis 0 is the row index ``i`` and maps to ``y``;
    axis 1 is the column index ``j`` and maps to ``x``.

Spatial centring (section 3.4)
    ``x[j] = (j - nx//2) * dx`` and ``y[i] = (i - ny//2) * dy``, so that
    ``x[nx//2] == 0.0`` exactly for both even and odd ``nx``.

Frequency grids (section 3.8)
    ``fx_centered[m] = (m - nx//2) * (1.0 / (nx * dx))``, evaluated as a
    multiplication by the reciprocal. See :ref:`the note below <precision>`.

.. _precision:

Why reciprocal-multiply and not division
----------------------------------------
``numpy.fft.fftfreq`` computes ``val = 1.0 / (n * d)`` once and then multiplies
an integer array by ``val``. Writing the mathematically identical expression
as a division, ``(m - n//2) / (n * d)``, reassociates the floating-point
operations and differs from NumPy by roughly one unit in the last place. The
discrepancy is invisible at ``d = 1.0`` and appears at realistic pixel pitches
(measured: ``2.9e-11`` absolute, ``2.2e-16`` relative, at ``n=512``,
``d=3.74e-6``).

Because ``ohlab`` guarantees bit-for-bit agreement with ``numpy.fft.fftfreq``,
the reciprocal-multiply form is required. This is an evaluation-order
specification, not a change of convention; the mathematics is unchanged.
``docs/math_conventions.md`` section 3.8 (v0.2) records it.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from .validation import (
    require_positive_finite_float,
    require_positive_int,
)

__all__ = ["SamplingGrid"]

#: Valid values for the ``order`` argument of :meth:`SamplingGrid.freq_meshgrid`.
FreqOrder = Literal["fft", "centered"]

_SERIALIZED_KEYS = ("ny", "nx", "dy", "dx")


@dataclass(frozen=True, kw_only=True)
class SamplingGrid:
    """A regularly sampled rectangular window in the transverse plane.

    All four parameters are **keyword-only**. This enforces
    ``docs/math_conventions.md`` section 3.3 at the language level: it is not
    possible to write ``SamplingGrid(nx, ny, dx, dy)`` and silently transpose
    the axes.

    Parameters
    ----------
    ny:
        Number of samples along ``y`` (rows, axis 0). Integer ``>= 1``.
    nx:
        Number of samples along ``x`` (columns, axis 1). Integer ``>= 1``.
    dy:
        Pixel pitch along ``y``, in **metres**. Finite and ``> 0``.
    dx:
        Pixel pitch along ``x``, in **metres**. Finite and ``> 0``.

    Notes
    -----
    Instances are immutable (frozen) and hashable. Two grids compare equal
    when all four parameters are equal.

    Derived arrays (:attr:`x`, :attr:`fx_fft`, ...) are **recomputed on every
    access** and are returned writeable. Nothing is cached, so a caller that
    mutates a returned array cannot corrupt the grid. Caching is deliberately
    deferred until Milestone 1, where a propagation hot path exists to profile.

    Examples
    --------
    >>> from ohlab.units import UM
    >>> g = SamplingGrid(ny=6, nx=8, dy=5 * UM, dx=4 * UM)
    >>> g.shape
    (6, 8)
    >>> float(g.x[g.nx // 2])
    0.0
    """

    ny: int
    nx: int
    dy: float
    dx: float

    def __post_init__(self) -> None:
        """Validate and normalise all four stored parameters."""
        # ``object.__setattr__`` is required because the dataclass is frozen.
        object.__setattr__(self, "ny", require_positive_int(self.ny, "ny"))
        object.__setattr__(self, "nx", require_positive_int(self.nx, "nx"))
        object.__setattr__(self, "dy", require_positive_finite_float(self.dy, "dy"))
        object.__setattr__(self, "dx", require_positive_finite_float(self.dx, "dx"))

    # ------------------------------------------------------------------
    # Shape and extent
    # ------------------------------------------------------------------
    @property
    def shape(self) -> tuple[int, int]:
        """Array shape ``(ny, nx)`` -- rows first, matching section 3.3."""
        return (self.ny, self.nx)

    @property
    def extent_y(self) -> float:
        """Physical height of the window, ``ny * dy``, in metres.

        Note that this counts each sample's full cell, so it exceeds
        ``y[-1] - y[0]`` by exactly one ``dy``.
        """
        return self.ny * self.dy

    @property
    def extent_x(self) -> float:
        """Physical width of the window, ``nx * dx``, in metres."""
        return self.nx * self.dx

    @property
    def pixel_area(self) -> float:
        """Area of one sample cell, ``dy * dx``, in square metres.

        This is the ``dx dy`` factor in the discretised power integral
        ``P = sum(I) * pixel_area`` (section 2.1).
        """
        return self.dy * self.dx

    # ------------------------------------------------------------------
    # Spatial coordinates
    # ------------------------------------------------------------------
    @property
    def y(self) -> np.ndarray:
        """Vertical sample coordinates, shape ``(ny,)``, float64, in metres.

        ``y[i] = (i - ny//2) * dy``. Increases with row index, so with
        ``imshow(..., origin='upper')`` the ``+y`` axis points *downward* on
        screen (section 3.5).
        """
        return (np.arange(self.ny) - (self.ny // 2)) * self.dy

    @property
    def x(self) -> np.ndarray:
        """Horizontal sample coordinates, shape ``(nx,)``, float64, in metres.

        ``x[j] = (j - nx//2) * dx``, hence ``x[nx//2] == 0.0`` exactly.
        """
        return (np.arange(self.nx) - (self.nx // 2)) * self.dx

    def meshgrid(self) -> tuple[np.ndarray, np.ndarray]:
        """Return the 2-D spatial coordinate grids ``(x_grid, y_grid)``.

        Both have shape ``(ny, nx)``. ``x_grid`` varies along axis 1 (columns)
        and ``y_grid`` along axis 0 (rows).

        The return order is ``(x, y)``, matching ``numpy.meshgrid``'s own
        convention -- **not** axis order. Section 3.4.

        Returns
        -------
        tuple of ndarray
            ``(x_grid, y_grid)``, each ``(ny, nx)`` float64, in metres.
        """
        return np.meshgrid(self.x, self.y, indexing="xy")

    # ------------------------------------------------------------------
    # Frequency coordinates
    #
    # The ordering is always part of the name. Mixing FFT order with centred
    # order is the single most common failure mode in this kind of code
    # (section 3.8).
    # ------------------------------------------------------------------
    @staticmethod
    def _centered_frequency_axis(n: int, d: float) -> np.ndarray:
        """Return the centred frequency axis for ``n`` samples of pitch ``d``.

        Evaluated as ``(m - n//2) * (1.0 / (n * d))`` -- multiplication by the
        reciprocal, matching ``numpy.fft.fftfreq``'s internal evaluation order
        bit for bit. See the module docstring for why this matters.
        """
        val = 1.0 / (n * d)
        return (np.arange(n) - (n // 2)) * val

    @property
    def fy_centered(self) -> np.ndarray:
        """Centred vertical spatial frequencies, ``(ny,)``, in cycles/metre.

        Zero frequency sits at index ``ny//2``. Bit-identical to
        ``np.fft.fftshift(np.fft.fftfreq(ny, dy))``.
        """
        return self._centered_frequency_axis(self.ny, self.dy)

    @property
    def fx_centered(self) -> np.ndarray:
        """Centred horizontal spatial frequencies, ``(nx,)``, in cycles/metre."""
        return self._centered_frequency_axis(self.nx, self.dx)

    @property
    def fy_fft(self) -> np.ndarray:
        """FFT-ordered vertical spatial frequencies, ``(ny,)``, in cycles/metre.

        Zero frequency sits at index 0. Bit-identical to
        ``np.fft.fftfreq(ny, dy)``. This is the ordering used by propagation
        kernels, so that no full-size array ever needs shifting.
        """
        return np.fft.ifftshift(self.fy_centered)

    @property
    def fx_fft(self) -> np.ndarray:
        """FFT-ordered horizontal spatial frequencies, ``(nx,)``, cycles/metre."""
        return np.fft.ifftshift(self.fx_centered)

    @property
    def ky_centered(self) -> np.ndarray:
        """Centred vertical angular spatial frequencies, ``(ny,)``, in rad/m.

        ``ky = 2 * pi * fy``. Never call a cyclic frequency ``k`` (section 3.6).
        """
        return 2.0 * np.pi * self.fy_centered

    @property
    def kx_centered(self) -> np.ndarray:
        """Centred horizontal angular spatial frequencies, ``(nx,)``, rad/m."""
        return 2.0 * np.pi * self.fx_centered

    @property
    def ky_fft(self) -> np.ndarray:
        """FFT-ordered vertical angular spatial frequencies, ``(ny,)``, rad/m."""
        return 2.0 * np.pi * self.fy_fft

    @property
    def kx_fft(self) -> np.ndarray:
        """FFT-ordered horizontal angular spatial frequencies, ``(nx,)``, rad/m."""
        return 2.0 * np.pi * self.fx_fft

    def freq_meshgrid(self, *, order: FreqOrder) -> tuple[np.ndarray, np.ndarray]:
        """Return the 2-D spatial frequency grids ``(fx_grid, fy_grid)``.

        Parameters
        ----------
        order:
            ``"fft"`` for FFT ordering (zero frequency at index 0), or
            ``"centered"`` for centred ordering (zero at index ``n//2``).
            **Keyword-only and mandatory** -- there is deliberately no default,
            because silently picking one ordering is precisely the mistake this
            API exists to prevent.

        Returns
        -------
        tuple of ndarray
            ``(fx_grid, fy_grid)``, each ``(ny, nx)`` float64, in cycles/metre.

        Raises
        ------
        ValueError
            ``order`` is neither ``"fft"`` nor ``"centered"``.
        """
        if order == "fft":
            fx, fy = self.fx_fft, self.fy_fft
        elif order == "centered":
            fx, fy = self.fx_centered, self.fy_centered
        else:
            raise ValueError(
                f"order must be 'fft' or 'centered', got {order!r}"
            )
        return np.meshgrid(fx, fy, indexing="xy")

    # ------------------------------------------------------------------
    # Sampling limits
    # ------------------------------------------------------------------
    @property
    def nyquist_fy(self) -> float:
        """Nyquist frequency along ``y``, ``1 / (2 * dy)``, in cycles/metre."""
        return 1.0 / (2.0 * self.dy)

    @property
    def nyquist_fx(self) -> float:
        """Nyquist frequency along ``x``, ``1 / (2 * dx)``, in cycles/metre."""
        return 1.0 / (2.0 * self.dx)

    def max_diffraction_angle_rad(
        self, wavelength_m: float, *, axis: Literal["x", "y"]
    ) -> float:
        """Largest diffraction angle this grid can represent, in radians.

        A spatial frequency ``f`` corresponds to light travelling at angle
        ``theta`` with ``sin(theta) = lambda * f``. The finest frequency the
        grid can carry is the Nyquist frequency, so::

            sin(theta_max) = lambda / (2 * d)

        For ``lambda = 633 nm`` and ``d = 3.74 um`` this is about 4.85 degrees
        -- the fundamental reason phase-only SLM holograms have a narrow field
        of view. Section 3.8.

        Parameters
        ----------
        wavelength_m:
            Vacuum wavelength in metres. Finite and ``> 0``.
        axis:
            ``"x"`` or ``"y"``. **Keyword-only and mandatory**: the two axes
            have independent pitches and therefore independent limits, so
            there is no meaningful default.

        Returns
        -------
        float
            The angle in radians, in ``[0, pi/2]``.

        Raises
        ------
        ValueError
            ``axis`` is invalid, or the wavelength is so long relative to the
            pitch that ``lambda / (2 * d) > 1`` and no such angle exists. The
            latter is raised explicitly rather than allowing ``arcsin`` to
            return ``NaN``.
        """
        lam = require_positive_finite_float(wavelength_m, "wavelength_m")
        if axis == "x":
            nyquist, pitch = self.nyquist_fx, self.dx
        elif axis == "y":
            nyquist, pitch = self.nyquist_fy, self.dy
        else:
            raise ValueError(f"axis must be 'x' or 'y', got {axis!r}")

        sin_theta = lam * nyquist
        if sin_theta > 1.0:
            raise ValueError(
                f"no diffraction angle exists: wavelength {lam!r} m with "
                f"pitch {pitch!r} m along {axis!r} gives "
                f"sin(theta) = lambda / (2 * d) = {sin_theta!r} > 1; "
                f"the sampling is too coarse for this wavelength"
            )
        return math.asin(sin_theta)

    # ------------------------------------------------------------------
    # Serialization and alternative constructors
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, int | float]:
        """Return a JSON-serializable dict of the four stored parameters.

        Round-trips exactly through :meth:`from_dict`. This is the unit of
        grid reproducibility that Milestone 5's run configuration will embed.
        """
        return {
            "ny": int(self.ny),
            "nx": int(self.nx),
            "dy": float(self.dy),
            "dx": float(self.dx),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> SamplingGrid:
        """Reconstruct a grid from the output of :meth:`to_dict`.

        Raises
        ------
        TypeError
            ``d`` is not a mapping, or a value has the wrong type.
        KeyError
            A required key is missing.
        ValueError
            An unexpected key is present, or a value is out of range.
        """
        if not isinstance(d, Mapping):
            raise TypeError(
                f"from_dict expects a mapping, got {type(d).__name__}"
            )
        missing = [k for k in _SERIALIZED_KEYS if k not in d]
        if missing:
            raise KeyError(
                f"missing required key(s) {missing}; expected exactly "
                f"{list(_SERIALIZED_KEYS)}"
            )
        extra = [k for k in d if k not in _SERIALIZED_KEYS]
        if extra:
            raise ValueError(
                f"unexpected key(s) {sorted(extra)}; expected exactly "
                f"{list(_SERIALIZED_KEYS)}"
            )
        return cls(ny=d["ny"], nx=d["nx"], dy=d["dy"], dx=d["dx"])

    @classmethod
    def square(cls, *, n: int, pitch: float) -> SamplingGrid:
        """Convenience constructor for an ``n x n`` grid of isotropic pitch.

        Parameters
        ----------
        n:
            Sample count along both axes.
        pitch:
            Pixel pitch along both axes, in metres.
        """
        return cls(ny=n, nx=n, dy=pitch, dx=pitch)
