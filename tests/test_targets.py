"""Independent numerical and ownership contracts for Milestone 2 targets.

Decimal references use 80-digit arithmetic and never call the implementation
under test. Nonzero 8-bit target intensities are at least 1/255, so relative
tolerances need no absolute floor. Endpoints, byte preservation, shape,
ownership, and deterministic output are deliberately exact assertions.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal, localcontext

import numpy as np
import pytest

from _helpers import assert_bit_identical
from ohlab.grid import SamplingGrid
from ohlab.targets import grayscale8_to_intensity, intensity_to_amplitude

TargetConverter = Callable[..., np.ndarray]
CONVERTERS = [
    pytest.param(grayscale8_to_intensity, np.uint8, id="grayscale"),
    pytest.param(intensity_to_amplitude, np.float64, id="intensity"),
]


class _ArraySubclass(np.ndarray):
    """A minimal subclass used to verify the plain-ndarray boundary."""


@pytest.fixture
def target_grid() -> SamplingGrid:
    """An asymmetric mixed-parity grid, with pitches in metres."""
    return SamplingGrid(ny=2, nx=3, dy=5.0e-6, dx=3.74e-6)


def _decimal_references(grayscale: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute intensity and amplitude from exact integer/255 ratios."""
    with localcontext() as context:
        context.prec = 80
        ratios = [Decimal(int(code)) / Decimal(255) for code in grayscale.flat]
        intensity = np.array([float(value) for value in ratios], dtype=np.float64)
        amplitude = np.array(
            [float(value.sqrt()) for value in ratios], dtype=np.float64
        )
    return intensity.reshape(grayscale.shape), amplitude.reshape(grayscale.shape)


def test_t01_known_codes_map_to_design_intensity(target_grid: SamplingGrid) -> None:
    """T-01: fixed /255 preserves low codes and both exact endpoints."""
    source = np.array([[0, 51, 128], [255, 1, 204]], dtype=np.uint8)
    expected = np.array([[0.0, 0.2, 128 / 255], [1.0, 1 / 255, 0.8]])
    intensity = grayscale8_to_intensity(source, grid=target_grid)
    np.testing.assert_allclose(intensity, expected, rtol=2e-15, atol=0.0)
    assert intensity[0, 0] == 0.0  # fixed zero endpoint is exact
    assert intensity[1, 0] == 1.0  # fixed full-scale endpoint is exact
    assert intensity[1, 1] > 0.0  # no threshold discards the lowest code


def test_t02_all_256_codes_match_independent_decimal_references() -> None:
    """T-02: intensity, amplitude and A**2 cover every grayscale code.

    The 2e-15 reference tolerance covers float64 division and sqrt rounding;
    measured maximum relative errors are 0 for intensity and 2.15e-16 for
    amplitude. The 5e-15 square tolerance covers the measured 2.21e-16 error.
    Decimal references retain 80 digits (NumPy 2.4.6, Windows float64).
    No absolute floor is needed: zero is exact and nonzero I >= 1/255.
    """
    grid = SamplingGrid(ny=16, nx=16, dy=5e-6, dx=3.74e-6)
    source = np.arange(256, dtype=np.uint8).reshape(grid.shape)
    expected_intensity, expected_amplitude = _decimal_references(source)
    intensity = grayscale8_to_intensity(source, grid=grid)
    amplitude = intensity_to_amplitude(intensity, grid=grid)
    np.testing.assert_allclose(
        intensity, expected_intensity, rtol=2e-15, atol=0.0
    )
    np.testing.assert_allclose(
        amplitude, expected_amplitude, rtol=2e-15, atol=0.0
    )
    np.testing.assert_allclose(amplitude**2, intensity, rtol=5e-15, atol=0.0)


def test_t03_midgray_is_intensity_not_amplitude(target_grid: SamplingGrid) -> None:
    """T-03: g=128 means I~0.502 and A~0.708, not A~0.502."""
    source = np.full(target_grid.shape, 128, dtype=np.uint8)
    expected_intensity, expected_amplitude = _decimal_references(source)
    intensity = grayscale8_to_intensity(source, grid=target_grid)
    amplitude = intensity_to_amplitude(intensity, grid=target_grid)
    np.testing.assert_allclose(
        intensity, expected_intensity, rtol=2e-15, atol=0.0
    )
    np.testing.assert_allclose(
        amplitude, expected_amplitude, rtol=2e-15, atol=0.0
    )
    assert np.all(amplitude > intensity)


def test_t04_brightness_is_preserved_across_targets(target_grid: SamplingGrid) -> None:
    """T-04: equal codes have equal intensity even when image maxima differ."""
    dim = np.full(target_grid.shape, 64, dtype=np.uint8)
    brighter = dim.copy()
    brighter[1, 2] = 255
    dim_intensity = grayscale8_to_intensity(dim, grid=target_grid)
    bright_intensity = grayscale8_to_intensity(brighter, grid=target_grid)
    np.testing.assert_allclose(dim_intensity, 64 / 255, rtol=2e-15, atol=0.0)
    # The identical code is evaluated by the same fixed mapping, exactly.
    assert dim_intensity[0, 0] == bright_intensity[0, 0]
    assert np.max(dim_intensity) < 1.0


@pytest.mark.parametrize("shape", [(2, 3), (3, 2), (3, 4), (4, 3)])
def test_t05_rectangular_mixed_parity_orientation(shape: tuple[int, int]) -> None:
    """T-05: row/column ordering and physical grid parameters are preserved."""
    grid = SamplingGrid(ny=shape[0], nx=shape[1], dy=5e-6, dx=3.74e-6)
    before_grid = grid.to_dict()
    source = np.arange(np.prod(shape), dtype=np.uint8).reshape(shape)
    expected_intensity, expected_amplitude = _decimal_references(source)
    intensity = grayscale8_to_intensity(source, grid=grid)
    amplitude = intensity_to_amplitude(intensity, grid=grid)
    assert intensity.shape == amplitude.shape == shape
    np.testing.assert_allclose(
        intensity, expected_intensity, rtol=2e-15, atol=0.0
    )
    np.testing.assert_allclose(
        amplitude, expected_amplitude, rtol=2e-15, atol=0.0
    )
    assert grid.to_dict() == before_grid  # no grid parameter is recomputed


def test_t06_normalized_float_intensity_has_no_additional_scaling(
    target_grid: SamplingGrid,
) -> None:
    """T-06: a valid low-maximum float target is square-rooted as supplied."""
    intensity = np.array([[0.0, 0.01, 0.04], [0.09, 0.16, 0.25]])
    expected = np.array([[0.0, 0.1, 0.2], [0.3, 0.4, 0.5]])
    amplitude = intensity_to_amplitude(intensity, grid=target_grid)
    np.testing.assert_allclose(amplitude, expected, rtol=2e-15, atol=0.0)


def test_t07_all_zero_targets_remain_valid_zero(target_grid: SamplingGrid) -> None:
    """T-07: loading a blank target requires neither power nor normalization."""
    source = np.zeros(target_grid.shape, dtype=np.uint8)
    intensity = grayscale8_to_intensity(source, grid=target_grid)
    amplitude = intensity_to_amplitude(intensity, grid=target_grid)
    zeros = np.zeros(target_grid.shape, dtype=np.float64)
    # Exactly zero is the defined /255 and sqrt result for these zero inputs.
    assert_bit_identical(intensity, zeros)
    assert_bit_identical(amplitude, zeros)


@pytest.mark.parametrize(("convert", "dtype"), CONVERTERS)
@pytest.mark.parametrize("layout", ["c", "fortran", "strided", "transposed", "reversed"])
def test_t08_ownership_layout_and_nonmutation(
    convert: TargetConverter, dtype: type, layout: str
) -> None:
    """T-08: readonly inputs of any layout yield independent writable C arrays."""
    source = np.arange(24, dtype=dtype).reshape(4, 6)
    if dtype is np.float64:
        source /= 24.0
        source[0, 0] = -0.0  # its sign bit must survive in the input
    if layout == "fortran":
        source = np.asfortranarray(source)
    elif layout == "strided":
        source = source[:, ::2]
    elif layout == "transposed":
        source = source.T
    elif layout == "reversed":
        source = source[::-1, ::-1]
    source.flags.writeable = False
    before = source.tobytes(order="C")
    grid = SamplingGrid(ny=source.shape[0], nx=source.shape[1], dy=5e-6, dx=3.74e-6)
    result = convert(source, grid=grid)
    assert type(result) is np.ndarray
    assert result.shape == source.shape
    assert result.dtype == np.dtype(np.float64) and result.dtype.isnative
    assert result.flags.c_contiguous and result.flags.writeable and result.flags.owndata
    assert not np.shares_memory(result, source)
    result[0, 0] = 0.875
    assert source.tobytes(order="C") == before  # literal input preservation


@pytest.mark.parametrize(("convert", "dtype"), CONVERTERS)
def test_t09_repeat_calls_are_deterministic_and_independent(
    convert: TargetConverter, dtype: type, target_grid: SamplingGrid
) -> None:
    """T-09: repeated inputs reproduce bits without returning shared storage."""
    source = np.ones(target_grid.shape, dtype=dtype)
    first = convert(source, grid=target_grid)
    second = convert(source, grid=target_grid)
    assert_bit_identical(first, second)
    assert not np.shares_memory(first, second)
    first[0, 0] = 0.25
    assert_bit_identical(convert(source, grid=target_grid), second)


@pytest.mark.parametrize(("convert", "dtype"), CONVERTERS)
@pytest.mark.parametrize("value", [None, 1, [[0, 1, 2], [3, 4, 5]]])
def test_t10_array_like_objects_are_rejected(
    convert: TargetConverter, dtype: type, value: object, target_grid: SamplingGrid
) -> None:
    """T-10: the boundary requires plain ndarray input, never guessed arrays."""
    with pytest.raises(TypeError, match="plain numpy.ndarray"):
        convert(value, grid=target_grid)


@pytest.mark.parametrize(("convert", "dtype"), CONVERTERS)
@pytest.mark.parametrize("kind", ["subclass", "masked"])
def test_t11_array_subclasses_are_rejected(
    convert: TargetConverter, dtype: type, kind: str, target_grid: SamplingGrid
) -> None:
    """T-11: subclass or mask semantics are not silently discarded."""
    source = np.ones(target_grid.shape, dtype=dtype)
    if kind == "subclass":
        source = source.view(_ArraySubclass)
    else:
        source = np.ma.array(source, mask=True)
    with pytest.raises(TypeError, match="plain numpy.ndarray"):
        convert(source, grid=target_grid)


@pytest.mark.parametrize(
    "dtype",
    [np.bool_, np.int8, np.int64, np.uint16, np.float32, np.float64, np.complex128, object, "U1"],
)
def test_t12_grayscale_requires_exact_uint8_dtype(dtype: object, target_grid: SamplingGrid) -> None:
    """T-12: bit depth is explicit rather than inferred from observed values."""
    source = np.ones(target_grid.shape, dtype=dtype)
    with pytest.raises(TypeError, match="native uint8"):
        grayscale8_to_intensity(source, grid=target_grid)


@pytest.mark.parametrize(
    "dtype",
    [np.bool_, np.int64, np.uint8, np.float32, np.complex128, object, "U1", np.dtype(np.float64).newbyteorder("S")],
)
def test_t13_intensity_requires_native_float64(dtype: object, target_grid: SamplingGrid) -> None:
    """T-13: encoded integers, narrower floats and non-native storage are refused."""
    source = np.ones(target_grid.shape, dtype=dtype)
    with pytest.raises(TypeError, match="native float64"):
        intensity_to_amplitude(source, grid=target_grid)


@pytest.mark.parametrize(("convert", "dtype"), CONVERTERS)
@pytest.mark.parametrize("shape", [(), (6,), (1, 2, 3), (3, 2), (1, 6), (0, 3)])
def test_t14_dimensions_and_grid_shape_are_strict(
    convert: TargetConverter, dtype: type, shape: tuple[int, ...], target_grid: SamplingGrid
) -> None:
    """T-14: mismatched input is rejected, including empty/transposed arrays."""
    source = np.zeros(shape, dtype=dtype)
    with pytest.raises(ValueError) as error:
        convert(source, grid=target_grid)
    assert str(shape) in str(error.value)
    if len(shape) == 2:
        assert str(target_grid.shape) in str(error.value)
        assert "(ny, nx)" in str(error.value)
    else:
        assert "2-dimensional" in str(error.value)


@pytest.mark.parametrize(("convert", "dtype"), CONVERTERS)
def test_t15_grid_type_and_keyword_only_contract(
    convert: TargetConverter, dtype: type, target_grid: SamplingGrid
) -> None:
    """T-15: callers supply a SamplingGrid explicitly as a keyword."""
    source = np.ones(target_grid.shape, dtype=dtype)
    with pytest.raises(TypeError, match="SamplingGrid"):
        convert(source, grid=target_grid.shape)
    with pytest.raises(TypeError):
        convert(source, target_grid)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_t16_nonfinite_intensity_is_rejected(bad: float, target_grid: SamplingGrid) -> None:
    """T-16: no non-finite value reaches the square root."""
    intensity = np.zeros(target_grid.shape, dtype=np.float64)
    intensity[1, 2] = bad
    before = intensity.tobytes(order="C")
    with pytest.raises(ValueError, match=r"finite.*index \(1, 2\)"):
        intensity_to_amplitude(intensity, grid=target_grid)
    assert intensity.tobytes(order="C") == before


@pytest.mark.parametrize("bad", [-1.0, np.nextafter(0.0, -1.0), np.nextafter(1.0, np.inf), 2.0])
def test_t17_out_of_range_intensity_is_rejected_without_clipping(
    bad: float, target_grid: SamplingGrid
) -> None:
    """T-17: even a one-step excursion outside [0,1] is invalid."""
    intensity = np.zeros(target_grid.shape, dtype=np.float64)
    intensity[1, 2] = bad
    before = intensity.tobytes(order="C")
    with pytest.raises(ValueError, match=r"\[0, 1\].*index \(1, 2\)"):
        intensity_to_amplitude(intensity, grid=target_grid)
    assert intensity.tobytes(order="C") == before
