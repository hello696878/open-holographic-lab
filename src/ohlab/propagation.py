"""Free-space propagation by the Angular Spectrum Method.

Propagates a :class:`~ohlab.field.ComplexField` through homogeneous free space
(``n = 1``) over a signed distance ``z``::

    U(x, y, 0)  --FFT2-->  A(fx, fy; 0)  --x H-->  A(fx, fy; z)  --IFFT2-->  U(x, y, z)

Normative reference: ``docs/math_conventions.md`` sections 3.1, 3.6, 3.8, 3.9.

Conventions implemented here
----------------------------
Time convention (section 3.1)
    ``E(x, y, t) = Re{ U(x, y) * exp(-i*omega*t) }``.

Transfer function (section 3.9), a **single expression for every distance**::

    H(fx, fy; z) = exp( +i * kz * z )        with   kz = 2*pi*sqrt(1/lambda^2 - fx^2 - fy^2)

    taking the principal complex square root, so that  Im(kz) >= 0.

There is deliberately no second expression for negative ``z``. Writing the
backward case separately -- as ``exp(-i*|kz|*z)`` or similar -- invites a sign
error. For real ``kz`` the same formula produces the conjugate propagator when
``z < 0``. For evanescent ``kz = 1j*kappa`` it instead reverses decay into
growth; backward requests on a mesh carrying such samples are refused. The
single mathematical expression and the public rejection policy are distinct.

The pipeline's ``A`` denotes raw DFT coefficients. A physical-coordinate
spectrum also carries sample-area and centered-origin phase factors (section
3.7). They cancel between the same-grid forward and inverse transforms, so
the production pipeline needs no additional shifts or factors.

The three conventions that must agree -- the ``exp(-i*omega*t)`` time
dependence (section 3.1), the ``-i`` forward Fourier kernel (section 3.6), and
the ``+i*kz*z`` propagation sign (section 3.9) -- were **selected and verified
as a mutually consistent set**. NumPy fixes only the discrete Fourier kernel
used by ``fft2``; it does not fix the time-harmonic convention. The external
verification is recorded in ``docs/handoffs/milestone_1/math_used.md``.

Propagating and evanescent components
-------------------------------------
A sample is *propagating* when ``fx^2 + fy^2 < 1/lambda^2`` (``kz`` real,
``|H| = 1``) and *evanescent* when ``fx^2 + fy^2 > 1/lambda^2`` (``kz`` purely
imaginary, ``|H| < 1`` for ``z > 0``).

Whether a grid carries evanescent samples at all is decided from the **actual
discrete frequency mesh**, never from a scalar pitch threshold. On a square
grid the extreme sample is the *corner* of the Nyquist square, at radius
``sqrt(2)/(2*d)``, so evanescent samples can appear for ``d < lambda/sqrt(2)``
-- not only for ``d < lambda/2``, which is the axis-only condition. Between
those two pitches the evanescent region is populated **only near the four
corners** of the frequency mesh. For an anisotropic grid there is no single
``d`` and no scalar threshold exists at all.
"""

from __future__ import annotations

import math

import numpy as np

from .field import ComplexField
from .grid import SamplingGrid
from .validation import require_finite_float, require_positive_int

__all__ = [
    "angular_spectrum_transfer_function",
    "propagate_angular_spectrum",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _evanescent_mask(grid: SamplingGrid, wavelength_m: float) -> np.ndarray:
    """Boolean mask, shape ``grid.shape``, True where a sample is evanescent.

    Evaluated on the FFT-ordered frequency mesh, which is the source of truth.
    """
    fx, fy = grid.freq_meshgrid(order="fft")
    return (fx**2 + fy**2) > (1.0 / wavelength_m) ** 2


def _padded_grid(grid: SamplingGrid, pad_factor: int) -> SamplingGrid:
    """Return the enlarged computation grid. Pitch is unchanged."""
    if pad_factor == 1:
        return grid
    return SamplingGrid(
        ny=pad_factor * grid.ny,
        nx=pad_factor * grid.nx,
        dy=grid.dy,
        dx=grid.dx,
    )


def _pad_offset(n: int, n_padded: int) -> int:
    """Number of samples inserted *before* the original data along one axis.

    Chosen so that the Milestone 0 coordinate-origin convention survives
    padding: original index ``n // 2`` maps to padded index
    ``n_padded // 2``, hence

        pad_before = n_padded // 2 - n // 2

    and therefore ``x_padded[j + pad_before] == x[j]`` **bit-exactly** for
    every original index ``j``, at both parities. ``numpy.pad``'s own default
    placement is deliberately not used: it would define the physical alignment
    implicitly, and for odd sizes it does not agree with this rule.
    """
    return n_padded // 2 - n // 2


def _zero_pad(
    data: np.ndarray, grid: SamplingGrid, padded: SamplingGrid
) -> np.ndarray:
    """Embed ``data`` in a zero-valued array of shape ``padded.shape``."""
    if padded.shape == grid.shape:
        return data
    out = np.zeros(padded.shape, dtype=np.complex128)
    row0 = _pad_offset(grid.ny, padded.ny)
    col0 = _pad_offset(grid.nx, padded.nx)
    out[row0 : row0 + grid.ny, col0 : col0 + grid.nx] = data
    return out


def _crop(
    data: np.ndarray, grid: SamplingGrid, padded: SamplingGrid
) -> np.ndarray:
    """Exact inverse of :func:`_zero_pad`: extract the original window."""
    if padded.shape == grid.shape:
        return data
    row0 = _pad_offset(grid.ny, padded.ny)
    col0 = _pad_offset(grid.nx, padded.nx)
    return data[row0 : row0 + grid.ny, col0 : col0 + grid.nx]


def _reject_backward_evanescent(
    grid: SamplingGrid, wavelength_m: float, distance_m: float
) -> None:
    """Raise if backward propagation would amplify evanescent components.

    For ``z < 0`` the single transfer-function expression turns evanescent
    decay into exponential *growth*. That is an ill-posed inverse problem: it
    amplifies the smallest numerical noise without bound, reaching ``4e8``
    after one micrometre and overflowing to ``inf`` within a hundred on a
    sub-wavelength grid. Zeroing those samples would silently misreport what
    was computed, and clamping would invent a number with no physical meaning,
    so the request is refused instead.
    """
    if distance_m >= 0.0:
        return
    mask = _evanescent_mask(grid, wavelength_m)
    count = int(np.count_nonzero(mask))
    if count == 0:
        return
    raise ValueError(
        f"backward propagation (distance_m={distance_m!r}) is refused because "
        f"{count} of {mask.size} samples of this grid are evanescent "
        f"(fx^2 + fy^2 > 1/lambda^2 with lambda={wavelength_m!r} m). "
        f"Reversing their exponential decay is ill-posed and overflows. "
        f"Use a coarser pitch so that the frequency mesh carries no "
        f"evanescent samples, or propagate forward only."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def angular_spectrum_transfer_function(
    grid: SamplingGrid,
    *,
    wavelength_m: float,
    distance_m: float,
) -> np.ndarray:
    """Angular-spectrum transfer function ``H`` on the FFT-ordered mesh.

    ``H(fx, fy; z) = exp(+i * kz * z)`` with
    ``kz = 2*pi*sqrt(1/lambda^2 - fx^2 - fy^2)`` on the principal branch, so
    ``Im(kz) >= 0``. One expression covers propagating and evanescent samples
    and both signs of ``distance_m``.

    Parameters
    ----------
    grid:
        Sampling geometry. ``H`` is returned in **FFT order** (zero frequency
        at index ``[0, 0]``), matching ``numpy.fft.fft2`` output, so no
        full-size array ever needs shifting.
    wavelength_m:
        Vacuum wavelength in metres. Finite and ``> 0``.
    distance_m:
        Signed propagation distance in metres. Finite. May be zero or
        negative.

    Returns
    -------
    ndarray
        ``(ny, nx)`` complex128. For ``distance_m == 0`` this is exactly
        ``1 + 0j`` everywhere.

    Raises
    ------
    TypeError
        ``grid`` is not a :class:`~ohlab.grid.SamplingGrid`.
    ValueError
        A parameter is out of range, or ``distance_m < 0`` on a grid whose
        frequency mesh carries evanescent samples.

    Notes
    -----
    For ``z > 0`` the evanescent branch underflows smoothly to ``0.0`` without
    emitting a NumPy warning, which matters because the test suite runs with
    ``filterwarnings = ["error"]``.
    """
    if not isinstance(grid, SamplingGrid):
        raise TypeError(
            f"grid must be a SamplingGrid, got {type(grid).__name__}"
        )
    lam = require_finite_float(wavelength_m, "wavelength_m")
    if lam <= 0.0:
        raise ValueError(f"wavelength_m must be strictly positive, got {lam!r}")
    distance = require_finite_float(distance_m, "distance_m")

    _reject_backward_evanescent(grid, lam, distance)

    fx, fy = grid.freq_meshgrid(order="fft")
    # Casting to complex before the square root selects the principal branch,
    # which returns +i*sqrt(|.|) for a negative real argument -- exactly the
    # Im(kz) >= 0 branch required by section 3.9. No manual sign logic.
    radial = (1.0 / lam) ** 2 - fx**2 - fy**2
    kz = 2.0 * np.pi * np.sqrt(radial.astype(np.complex128))
    return np.exp(1j * kz * distance)


def propagate_angular_spectrum(
    field: ComplexField,
    *,
    distance_m: float,
    pad_factor: int = 2,
) -> ComplexField:
    """Propagate ``field`` through free space by ``distance_m`` metres.

    Parameters
    ----------
    field:
        Source field at ``z = 0``.
    distance_m:
        Signed distance in **metres**. Positive is forward (``+z``). Finite.
    pad_factor:
        Integer ``>= 1``. The computation is performed on a grid enlarged by
        this factor along each axis, with the original field embedded in
        zeros, and the result cropped back. ``1`` means no padding.

        **What this does and does not mean.**

        * ``pad_factor=1`` propagates on the original periodic DFT window.
          The DFT treats the field as periodic, so light leaving one edge
          re-enters from the opposite one (circular wrap-around).
        * ``pad_factor > 1`` changes the numerical boundary assumption: the
          original field is embedded in a larger zero-valued window, so light
          that leaves the original window has somewhere to go before it wraps.
        * Padding **reduces** circular wrap-around. It is not a guarantee of
          physical correctness: once light reaches the edge of the *padded*
          window it wraps again, and truncating a field that fills the window
          imposes a finite aperture that the original periodic problem did not
          have. Neither choice is universally right; they are different
          boundary conditions.

        Default ``2``. Measured cost versus ``1``: roughly 4x to 6x the time,
        and a 4x larger computational array. Peak Python-visible allocation
        rises from about 4.5x to about 22x a single *source* field array --
        equivalently, about 4.5x to 5.5x a single array of the *computational*
        grid. See ``docs/handoffs/milestone_1/known_limitations.md`` section
        1.6 for the full table and the process working-set figures.

    Returns
    -------
    ComplexField
        Same shape, same ``grid``, same ``wavelength_m``.

        **Zero-distance contract.** When ``distance_m == 0.0`` this function
        returns **the input object itself** (``result is field``). Propagating
        by zero is the identity operation, and :class:`ComplexField` is
        immutable, so returning the same object is safe and makes the identity
        exact rather than accurate to a few times machine epsilon. Callers
        must not assume the result is a distinct object.

    Raises
    ------
    TypeError
        ``field`` is not a :class:`~ohlab.field.ComplexField`, or
        ``pad_factor`` is not an integer.
    ValueError
        ``distance_m`` is not finite, ``pad_factor < 1``, or ``distance_m < 0``
        on a grid carrying evanescent samples.

    Examples
    --------
    >>> from ohlab import ComplexField, SamplingGrid
    >>> from ohlab.units import MM, NM, UM
    >>> grid = SamplingGrid.square(n=64, pitch=8 * UM)
    >>> source = ComplexField.uniform(grid=grid, wavelength_m=633 * NM)
    >>> out = propagate_angular_spectrum(source, distance_m=10 * MM)
    >>> out.shape == grid.shape
    True
    """
    if not isinstance(field, ComplexField):
        raise TypeError(
            f"field must be a ComplexField, got {type(field).__name__}"
        )
    distance = require_finite_float(distance_m, "distance_m")
    factor = require_positive_int(pad_factor, "pad_factor")

    # Zero distance is the identity. ComplexField is immutable, so returning
    # the same object is safe and makes the identity exact. See the docstring
    # for the contract.
    if distance == 0.0:
        return field

    grid = field.grid
    padded = _padded_grid(grid, factor)

    # Validate on the grid the transfer function is actually evaluated on.
    # Padding leaves the pitch, and hence the Nyquist limit, unchanged, but it
    # samples the frequency plane more finely, so the padded mesh can contain
    # evanescent samples that the unpadded one misses.
    _reject_backward_evanescent(padded, field.wavelength_m, distance)

    source = _zero_pad(field.data, grid, padded)
    transfer = angular_spectrum_transfer_function(
        padded, wavelength_m=field.wavelength_m, distance_m=distance
    )
    propagated = np.fft.ifft2(np.fft.fft2(source) * transfer)
    return field.with_data(_crop(propagated, grid, padded))
