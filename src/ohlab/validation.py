"""Shared argument validators for the numerical core.

Every public entry point in :mod:`ohlab` validates its arguments through this
module before doing any numerical work, per ``CLAUDE.md`` section 6.

Error type policy
-----------------
``TypeError``
    The argument is of the wrong *kind*: a string where a number is required,
    a float where an integer is required, an object-dtype array, and so on.
``ValueError``
    The argument is of the right kind but has an unusable *value*: a
    non-positive pixel pitch, a zero sample count, a ``NaN`` or ``Inf``, an
    array of the wrong shape.

Every message names the offending parameter, shows the offending value, and
states what was expected.

Booleans
--------
Python's ``bool`` is a subclass of ``int``, so ``SamplingGrid(nx=True)`` would
otherwise silently mean ``nx=1``. Scalar validators therefore **reject**
``bool`` explicitly.

Array validators are deliberately *more* permissive: a boolean array is an
unambiguous 0/1 numeric mask (a binary aperture, for example) and is accepted
and converted. The asymmetry is intentional -- for a scalar count, ``True``
is a semantic mistake; for an array, it is a legitimate mask.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import numpy.typing as npt

__all__ = [
    "require_positive_int",
    "require_finite_float",
    "require_positive_finite_float",
    "as_float64_array",
    "as_complex128_array",
    "require_ndim",
    "require_shape",
    "require_all_finite",
]

# Numpy dtype "kind" codes that this project accepts as numeric input.
#   b = boolean, i = signed int, u = unsigned int, f = float, c = complex
_REAL_KINDS = frozenset("biuf")
_COMPLEX_KINDS = frozenset("biufc")


def _describe(value: Any) -> str:
    """Return a short, safe description of ``value`` for an error message.

    Arrays are summarised by shape and dtype rather than printed in full, so
    that a validation failure on a 4-megapixel field does not produce an
    unreadable exception.
    """
    if isinstance(value, np.ndarray):
        return f"ndarray(shape={value.shape}, dtype={value.dtype})"
    text = repr(value)
    if len(text) > 80:
        text = text[:77] + "..."
    return f"{text} (type {type(value).__name__})"


# ---------------------------------------------------------------------------
# Scalar validators
# ---------------------------------------------------------------------------
def require_positive_int(value: Any, name: str) -> int:
    """Validate that ``value`` is an integer greater than or equal to 1.

    Parameters
    ----------
    value:
        Candidate value. Python ``int`` and NumPy integer scalars are
        accepted. ``bool`` is rejected (see the module docstring). Floats are
        rejected even when integral, so that ``nx=8.0`` is a loud error rather
        than a silent coercion.
    name:
        Parameter name, used in the error message.

    Returns
    -------
    int
        The validated value as a builtin ``int``.

    Raises
    ------
    TypeError
        ``value`` is not an integer type, or is a ``bool``.
    ValueError
        ``value`` is an integer but is less than 1.
    """
    if isinstance(value, bool):
        raise TypeError(
            f"{name} must be a positive integer, got {_describe(value)}; "
            f"bool is not accepted because True would silently mean 1"
        )
    if not isinstance(value, (int, np.integer)):
        raise TypeError(
            f"{name} must be a positive integer, got {_describe(value)}"
        )
    ivalue = int(value)
    if ivalue < 1:
        raise ValueError(
            f"{name} must be a positive integer (>= 1), got {ivalue}"
        )
    return ivalue


def require_finite_float(value: Any, name: str) -> float:
    """Validate that ``value`` is a finite real number.

    Accepts Python ``int``/``float`` and NumPy real scalars. Rejects ``bool``,
    ``complex``, strings, ``None``, ``NaN``, and infinities.

    Returns
    -------
    float
        The validated value as a builtin ``float``.
    """
    if isinstance(value, bool):
        raise TypeError(
            f"{name} must be a finite real number, got {_describe(value)}; "
            f"bool is not accepted"
        )
    if isinstance(value, complex) and not isinstance(value, (int, float)):
        raise TypeError(
            f"{name} must be a finite real number, got {_describe(value)}; "
            f"complex is not accepted"
        )
    if not isinstance(value, (int, float, np.integer, np.floating)):
        raise TypeError(
            f"{name} must be a finite real number, got {_describe(value)}"
        )
    fvalue = float(value)
    if not math.isfinite(fvalue):
        raise ValueError(
            f"{name} must be finite, got {fvalue!r}"
        )
    return fvalue


def require_positive_finite_float(value: Any, name: str) -> float:
    """Validate that ``value`` is a finite real number strictly greater than 0.

    Used for pixel pitches, wavelengths, and any other quantity for which zero
    is physically meaningless.
    """
    fvalue = require_finite_float(value, name)
    if fvalue <= 0.0:
        raise ValueError(
            f"{name} must be strictly positive, got {fvalue!r}"
        )
    return fvalue


# ---------------------------------------------------------------------------
# Array validators
# ---------------------------------------------------------------------------
def _as_array_of_dtype(
    value: npt.ArrayLike,
    name: str,
    *,
    dtype: type,
    allowed_kinds: frozenset[str],
    what: str,
) -> np.ndarray:
    """Convert ``value`` to a new array of ``dtype``, rejecting non-numeric input.

    The returned array is always a **fresh copy**, never a view of ``value``.
    This is what gives :class:`~ohlab.field.ComplexField` its defensive-copy
    guarantee for free.
    """
    try:
        arr = np.asarray(value)
    except Exception as exc:  # pragma: no cover - numpy is very permissive
        raise TypeError(
            f"{name} must be convertible to a {what} array, got "
            f"{_describe(value)}"
        ) from exc

    if arr.dtype.kind not in allowed_kinds:
        raise TypeError(
            f"{name} must be a {what} array, got dtype {arr.dtype} "
            f"(kind {arr.dtype.kind!r}); allowed dtype kinds are "
            f"{sorted(allowed_kinds)}"
        )

    # astype() copies by default, which is exactly what we want.
    return arr.astype(dtype, copy=True)


def as_float64_array(value: npt.ArrayLike, name: str) -> np.ndarray:
    """Convert ``value`` to a fresh ``float64`` array.

    Complex input is rejected rather than silently having its imaginary part
    discarded. Boolean and integer input is accepted and converted.

    Higher-precision input (``float128``) is accepted and **downcast** to
    ``float64`` without warning; the core computes in double precision by
    convention (``docs/math_conventions.md`` section 3.11).
    """
    return _as_array_of_dtype(
        value, name, dtype=np.float64, allowed_kinds=_REAL_KINDS, what="real numeric"
    )


def as_complex128_array(value: npt.ArrayLike, name: str) -> np.ndarray:
    """Convert ``value`` to a fresh ``complex128`` array.

    Real input is promoted (imaginary part zero). ``complex64`` is upcast and
    ``complex256``/``clongdouble`` is downcast, both without warning.
    """
    return _as_array_of_dtype(
        value,
        name,
        dtype=np.complex128,
        allowed_kinds=_COMPLEX_KINDS,
        what="numeric",
    )


def require_ndim(a: np.ndarray, ndim: int, name: str) -> np.ndarray:
    """Validate that ``a`` has exactly ``ndim`` dimensions."""
    if a.ndim != ndim:
        raise ValueError(
            f"{name} must be {ndim}-dimensional, got {a.ndim} dimensions "
            f"with shape {a.shape}"
        )
    return a


def require_shape(a: np.ndarray, expected: tuple[int, ...], name: str) -> np.ndarray:
    """Validate that ``a`` has exactly the shape ``expected``.

    The error message spells out both shapes, because the overwhelmingly most
    common cause is an ``(nx, ny)`` / ``(ny, nx)`` transposition.
    """
    if a.shape != tuple(expected):
        raise ValueError(
            f"{name} must have shape {tuple(expected)}, got {a.shape}; "
            f"note that arrays are stored as (ny, nx) -- rows are y, "
            f"columns are x"
        )
    return a


def require_all_finite(a: np.ndarray, name: str) -> np.ndarray:
    """Validate that every element of ``a`` is finite.

    For complex arrays, ``np.isfinite`` requires both the real and imaginary
    parts to be finite, which is the intended behaviour.
    """
    finite = np.isfinite(a)
    if not bool(np.all(finite)):
        bad = np.argwhere(~finite)
        n_bad = int(bad.shape[0])
        first = tuple(int(i) for i in bad[0])
        raise ValueError(
            f"{name} must contain only finite values, but {n_bad} of "
            f"{a.size} entries are NaN or Inf; first at index {first} "
            f"with value {a[first]!r}"
        )
    return a
