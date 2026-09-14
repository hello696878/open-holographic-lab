"""Literal representation checks for the shared bit-identity assertion.

Exactness is the property under test throughout: byte patterns, shapes, and
dtypes must agree. These tests deliberately do not use approximate phase or
numerical comparisons.
"""

from __future__ import annotations

import numpy as np
import pytest

from _helpers import assert_bit_identical


@pytest.mark.parametrize("dtype", [np.float64, np.complex128])
def test_bit_identity_accepts_identical_copies(dtype: type) -> None:
    """Copying preserves each logical element's literal representation."""
    source = np.array([[0.0, -0.0], [1.5, -2.0]], dtype=dtype)
    assert_bit_identical(source, source.copy())


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (np.array([0.0]), np.array([-0.0])),
        (
            np.array([complex(-1.0, 0.0)]),
            np.array([complex(-1.0, -0.0)]),
        ),
        (
            np.array([complex(0.0, 1.0)]),
            np.array([complex(-0.0, 1.0)]),
        ),
    ],
    ids=["float-zero", "complex-imaginary-zero", "complex-real-zero"],
)
def test_bit_identity_rejects_signed_zero_differences(
    left: np.ndarray, right: np.ndarray
) -> None:
    """Numerical equality alone misses the differing sign bit of zero."""
    # Numerical equality is an exact property of IEEE signed zeros; the
    # deliberately stronger representation assertion below must reject them.
    np.testing.assert_array_equal(left, right)
    with pytest.raises(AssertionError, match="element bytes"):
        assert_bit_identical(left, right)


@pytest.mark.parametrize("layout", ["strided", "transposed", "reversed"])
def test_bit_identity_accepts_equivalent_noncontiguous_arrays(layout: str) -> None:
    """Storage order and stride signs do not change logical C-order bytes."""
    source = np.arange(24, dtype=np.float64).reshape(4, 6)
    source[0, 0] = -0.0
    if layout == "strided":
        view = source[:, ::2]
    elif layout == "transposed":
        view = source.T
    else:
        view = source[::-1, ::-1]
    assert not view.flags.c_contiguous
    contiguous = view.copy(order="C")
    assert contiguous.flags.c_contiguous
    assert view.strides != contiguous.strides
    assert_bit_identical(view, contiguous)


def test_bit_identity_rejects_shape_mismatch_with_identical_bytes() -> None:
    """Equal flattened bytes do not permit different array shapes."""
    source = np.zeros((2, 3), dtype=np.float64)
    other_shape = source.reshape(3, 2)
    assert source.tobytes(order="C") == other_shape.tobytes(order="C")
    with pytest.raises(AssertionError, match="shape mismatch"):
        assert_bit_identical(source, other_shape)


def test_bit_identity_rejects_dtype_mismatch_with_identical_bytes() -> None:
    """A dtype change is a mismatch even when every stored byte is zero."""
    floats = np.zeros(2, dtype=np.float64)
    integers = np.zeros(2, dtype=np.int64)
    assert floats.tobytes(order="C") == integers.tobytes(order="C")
    with pytest.raises(AssertionError, match="dtype mismatch"):
        assert_bit_identical(floats, integers)


@pytest.mark.parametrize("type_code", ["f8", "c16"])
def test_bit_identity_rejects_byte_order_mismatch(type_code: str) -> None:
    """Endian representations differ even for all-zero element bytes."""
    little_endian = np.zeros(2, dtype="<" + type_code)
    big_endian = np.zeros(2, dtype=">" + type_code)
    assert little_endian.tobytes(order="C") == big_endian.tobytes(order="C")
    with pytest.raises(AssertionError, match="dtype mismatch"):
        assert_bit_identical(little_endian, big_endian)


def test_bit_identity_checks_dtype_beyond_the_short_type_string() -> None:
    """Structured field names remain part of the dtype even with equal bytes."""
    left = np.zeros(2, dtype=[("left", np.float64)])
    right = np.zeros(2, dtype=[("right", np.float64)])
    assert left.dtype.str == right.dtype.str
    assert left.tobytes(order="C") == right.tobytes(order="C")
    with pytest.raises(AssertionError, match="dtype mismatch"):
        assert_bit_identical(left, right)
