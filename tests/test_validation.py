"""Tests for :mod:`ohlab.validation` (Milestone 0, IDs V-01 .. V-12).

Evidence class: behavioural. These tests assert that invalid input fails fast
and loudly rather than propagating into the numerics as a NaN or a silently
transposed array.
"""

from __future__ import annotations

import numpy as np
import pytest

from ohlab.validation import (
    as_complex128_array,
    as_float64_array,
    require_all_finite,
    require_finite_float,
    require_ndim,
    require_positive_finite_float,
    require_positive_int,
    require_shape,
)


# ---------------------------------------------------------------------------
# Scalar validators
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bad", [0.0, -1e-6, -1.0])
def test_v01_non_positive_pitch_rejected(bad: float) -> None:
    """V-01: a zero or negative pixel pitch raises ``ValueError``."""
    with pytest.raises(ValueError, match="strictly positive"):
        require_positive_finite_float(bad, "dx")


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_v02_non_finite_scalar_rejected(bad: float) -> None:
    """V-02: NaN and infinities are rejected for pitches and wavelengths."""
    with pytest.raises(ValueError, match="finite"):
        require_positive_finite_float(bad, "wavelength_m")
    with pytest.raises(ValueError, match="finite"):
        require_finite_float(bad, "distance_m")


@pytest.mark.parametrize("bad", [0, -1, -4])
def test_v03_non_positive_sample_count_rejected(bad: int) -> None:
    """V-03: a zero or negative sample count raises ``ValueError``."""
    with pytest.raises(ValueError, match="positive integer"):
        require_positive_int(bad, "nx")


@pytest.mark.parametrize("bad", [3.5, 8.0, "8", None, [8], complex(8, 0)])
def test_v04_non_integer_sample_count_rejected(bad: object) -> None:
    """V-04: non-integer types raise ``TypeError``.

    ``8.0`` is rejected along with ``3.5``: silently coercing an integral
    float hides the fact that the caller computed a float where a count was
    required.
    """
    with pytest.raises(TypeError, match="positive integer"):
        require_positive_int(bad, "nx")


def test_v05_bool_rejected_as_integer_and_float() -> None:
    """V-05: ``bool`` is rejected by scalar validators.

    ``bool`` subclasses ``int``, so ``SamplingGrid(nx=True)`` would otherwise
    silently mean ``nx=1``.
    """
    with pytest.raises(TypeError, match="bool"):
        require_positive_int(True, "nx")
    with pytest.raises(TypeError, match="bool"):
        require_finite_float(False, "dx")


def test_v05b_numpy_integer_scalars_accepted() -> None:
    """V-05b: NumPy integer scalars are valid sample counts."""
    assert require_positive_int(np.int64(16), "nx") == 16
    assert isinstance(require_positive_int(np.int32(4), "ny"), int)


def test_v05c_complex_scalar_rejected_as_real() -> None:
    """V-05c: a complex scalar is not a valid real parameter."""
    with pytest.raises(TypeError, match="complex is not accepted"):
        require_finite_float(1 + 2j, "dx")


# ---------------------------------------------------------------------------
# Array validators
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bad_value", [np.nan, np.inf, -np.inf])
def test_v06_non_finite_array_rejected(bad_value: float) -> None:
    """V-06: an array containing NaN or Inf raises ``ValueError``.

    The message must locate the first offending element, because a single bad
    pixel in a megapixel field is otherwise impossible to find.
    """
    a = np.ones((3, 4))
    a[2, 1] = bad_value
    with pytest.raises(ValueError, match=r"first at index \(2, 1\)"):
        require_all_finite(a, "data")


def test_v06b_non_finite_complex_array_rejected() -> None:
    """V-06b: a complex array with a non-finite imaginary part is rejected."""
    a = np.ones((2, 2), dtype=np.complex128)
    a[1, 1] = complex(1.0, np.nan)
    with pytest.raises(ValueError, match="finite"):
        require_all_finite(a, "data")


@pytest.mark.parametrize(
    "bad", [np.array(["a", "b"]), np.array([object(), object()])]
)
def test_v07_non_numeric_array_rejected(bad: np.ndarray) -> None:
    """V-07: string and object dtype arrays raise ``TypeError``."""
    with pytest.raises(TypeError, match="dtype"):
        as_complex128_array(bad, "data")


def test_v07b_complex_rejected_where_real_required() -> None:
    """V-07b: complex input to a real converter is rejected, not truncated.

    Silently discarding an imaginary part is exactly the kind of quiet data
    loss that produces a plausible but wrong hologram.
    """
    with pytest.raises(TypeError, match="real numeric"):
        as_float64_array(np.array([1 + 2j]), "amplitude")


def test_v07c_boolean_array_accepted_as_numeric_mask() -> None:
    """V-07c: a boolean array is accepted and converted (a binary aperture).

    The asymmetry with V-05 is deliberate: for a scalar count ``True`` is a
    semantic mistake, but for an array it is a legitimate 0/1 mask.
    """
    out = as_float64_array(np.array([[True, False]]), "amplitude")
    assert out.dtype == np.float64
    np.testing.assert_array_equal(out, np.array([[1.0, 0.0]]))


@pytest.mark.parametrize("shape", [(4,), (2, 2, 2), ()])
def test_v08_wrong_dimensionality_rejected(shape: tuple[int, ...]) -> None:
    """V-08: an array that is not 2-D raises ``ValueError``."""
    with pytest.raises(ValueError, match="2-dimensional"):
        require_ndim(np.zeros(shape), 2, "data")


def test_v08b_wrong_shape_message_mentions_axis_order() -> None:
    """V-08b: a shape mismatch names both shapes and the (ny, nx) convention.

    The overwhelmingly most common cause is an ``(nx, ny)`` transposition, so
    the message says so explicitly.
    """
    with pytest.raises(ValueError, match=r"\(ny, nx\)"):
        require_shape(np.zeros((10, 6)), (6, 10), "data")


# ---------------------------------------------------------------------------
# Message quality and pass-through
# ---------------------------------------------------------------------------
def test_v09_messages_name_the_parameter_and_the_value() -> None:
    """V-09: every message contains the parameter name and offending value."""
    with pytest.raises(ValueError) as excinfo:
        require_positive_finite_float(-2.5, "pixel_pitch_dx")
    text = str(excinfo.value)
    assert "pixel_pitch_dx" in text
    assert "-2.5" in text

    with pytest.raises(TypeError) as excinfo2:
        require_positive_int("twelve", "n_samples")
    text2 = str(excinfo2.value)
    assert "n_samples" in text2
    assert "twelve" in text2


def test_v10_valid_input_passes_through_with_correct_type() -> None:
    """V-10: validators return the value converted to the canonical type."""
    assert require_positive_int(8, "nx") == 8
    assert isinstance(require_positive_int(8, "nx"), int)
    assert require_positive_finite_float(3.74e-6, "dx") == 3.74e-6
    assert isinstance(require_positive_finite_float(1, "dx"), float)


def test_v11_converters_promote_dtype_and_copy() -> None:
    """V-11: converters return a fresh array of the requested dtype.

    The copy is what gives :class:`ComplexField` its defensive-copy guarantee,
    so it is asserted here at the source rather than only at the field level.
    """
    source = np.arange(6, dtype=np.int32).reshape(2, 3)
    converted = as_complex128_array(source, "data")
    assert converted.dtype == np.complex128
    assert not np.shares_memory(converted, source)
    source[0, 0] = 999
    assert converted[0, 0] == 0  # unaffected by the later mutation


def test_v12_float32_and_complex64_are_accepted_and_widened() -> None:
    """V-12: narrower floating types are widened to the core's precision."""
    assert as_float64_array(np.zeros(3, dtype=np.float32), "a").dtype == np.float64
    assert (
        as_complex128_array(np.zeros(3, dtype=np.complex64), "a").dtype
        == np.complex128
    )
