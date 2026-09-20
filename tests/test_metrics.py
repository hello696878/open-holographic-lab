"""Independent intensity-metric references and public-contract regressions.

The reference reductions below use scalar Decimal arithmetic on the supplied
binary64 values, not production metric helpers or NumPy reductions. Exact
assertions are reserved for stated shortcuts, dyadic hand results, deterministic
repeats and input representation preservation. Nonzero reductions use
rtol=5e-15/atol=0; PSNR uses rtol=0/atol=1e-12 dB. The M4 handoff records the
measured errors against these references and the deliberate negative controls.
"""

from __future__ import annotations

from decimal import Decimal, localcontext
import gc
import math
import weakref

import numpy as np
import pytest

from ohlab import metrics
from ohlab.algorithms import gerchberg_saxton
from ohlab.field import ComplexField
from ohlab.grid import SamplingGrid
from ohlab.propagation import propagate_angular_spectrum


REDUCTION_RTOL = 5e-15
PSNR_ATOL_DB = 1e-12
PAIR_NAMES = ("intensity_mse", "intensity_nmse", "intensity_psnr")
METRIC_NAMES = PAIR_NAMES + ("signal_region_power_fraction", "regional_intensity_cv")


def _decimal_pair_reference(
    target: np.ndarray, reconstruction: np.ndarray, data_range: float = 1.0,
) -> dict[str, float | None]:
    """80-digit scalar reference, starting from exact stored float values."""
    with localcontext() as context:
        context.prec = 80
        target_values = [Decimal.from_float(float(value)) for value in target.flat]
        result_values = [Decimal.from_float(float(value)) for value in reconstruction.flat]
        error_sum = sum(((r - t)**2 for t, r in zip(target_values, result_values)), Decimal(0))
        target_norm = sum((t**2 for t in target_values), Decimal(0))
        mse = error_sum / Decimal(len(target_values))
        psnr = (
            math.inf if error_sum == 0 else
            float(20 * Decimal.from_float(float(data_range)).log10() - 10 * mse.log10())
        )
        return {
            "intensity_mse": float(mse),
            "intensity_nmse": None if target_norm == 0 else float(error_sum / target_norm),
            "intensity_psnr": psnr,
        }


def _decimal_region_reference(intensity: np.ndarray, mask: np.ndarray) -> dict[str, float | None]:
    """Scalar power and population-CV reference with an explicit region."""
    with localcontext() as context:
        context.prec = 80
        values = [Decimal.from_float(float(value)) for value in intensity.flat]
        selected = [value for value, keep in zip(values, mask.flat) if bool(keep)]
        total = sum(values, Decimal(0))
        signal = sum(selected, Decimal(0))
        cv = None
        if selected and signal > 0:
            mean = signal / Decimal(len(selected))
            variance = sum(((value - mean)**2 for value in selected), Decimal(0)) / Decimal(len(selected))
            cv = float(variance.sqrt() / mean)
        return {
            "signal_region_power_fraction": None if total == 0 else float(signal / total),
            "regional_intensity_cv": cv,
        }


def _base_target() -> np.ndarray:
    return np.array([[0.0, 0.25, 0.5], [0.75, 1.0, 0.0]], dtype=np.float64)


def _region_fixture() -> tuple[np.ndarray, np.ndarray]:
    intensity = np.array([[1.0, 3.0, 7.0], [5.0, 0.0, 0.0]], dtype=np.float64)
    mask = np.array([[True, False, False], [True, False, False]], dtype=np.bool_)
    return intensity, mask


def _reference_pair_cases() -> list[tuple[str, np.ndarray, np.ndarray, float]]:
    """Small stable cases also exposed to the handoff's measurement driver."""
    target = _base_target()
    perturbed = target.copy()
    perturbed[0, 1] += 0.5
    return [
        ("identical", target, target.copy(), 1.0),
        ("one_pixel", target, perturbed, 1.0),
        ("twice_brightness", target, 2.0 * target, 1.0),
        ("scaled_fixed_range", 3.0 * target, 6.0 * target, 1.0),
        ("scaled_range", 3.0 * target, 6.0 * target, 3.0),
        ("explicit_range_two", target, 2.0 * target, 2.0),
        ("nonbinary", np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]),
         np.array([[0.15, 0.18, 0.31], [0.5, 0.45, 0.72]]), 1.0),
        ("large_range", target, 2.0 * target, 1e200),
    ]


def _call_pair(name: str, target: np.ndarray, reconstruction: np.ndarray, data_range: float = 1.0) -> float:
    arguments = {"target_intensity": target, "reconstruction_intensity": reconstruction}
    if name == "intensity_psnr":
        arguments["data_range"] = data_range
    return getattr(metrics, name)(**arguments)


def _call_metric(name: str, intensity: np.ndarray, mask: np.ndarray | None = None) -> float:
    if name in PAIR_NAMES:
        return _call_pair(name, intensity, intensity)
    if mask is None:
        mask = np.ones((2, 3), dtype=np.bool_)
    if name == "signal_region_power_fraction":
        return metrics.signal_region_power_fraction(reconstruction_intensity=intensity, signal_mask=mask)
    return metrics.regional_intensity_cv(intensity=intensity, mask=mask)


def _assert_reference(actual: float, expected: float, name: str) -> None:
    assert type(actual) is float
    if math.isinf(expected):
        assert actual == math.inf  # The validated exact-match PSNR contract.
    elif expected == 0.0:
        assert actual == 0.0  # Only exact equal-image/constant-region cases use this path.
    else:
        np.testing.assert_allclose(
            actual, expected,
            rtol=0.0 if name == "intensity_psnr" else REDUCTION_RTOL,
            atol=PSNR_ATOL_DB if name == "intensity_psnr" else 0.0,
        )


def _snapshot(array: np.ndarray) -> tuple:
    """Literal representation, layout and access flags for nonmutation claims."""
    return array.shape, array.dtype.str, array.strides, array.flags.writeable, array.tobytes(order="C")


@pytest.mark.parametrize("name,target,reconstruction,data_range", _reference_pair_cases(), ids=lambda value: value if isinstance(value, str) else None)
def test_pair_metrics_match_independent_decimal_reference(name, target, reconstruction, data_range):
    expected = _decimal_pair_reference(target, reconstruction, data_range)
    for metric_name in PAIR_NAMES:
        _assert_reference(_call_pair(metric_name, target, reconstruction, data_range), expected[metric_name], metric_name)


def test_one_pixel_error_has_hand_calculable_mse_and_target_norm_nmse():
    target = _base_target()
    reconstruction = target.copy()
    reconstruction[0, 1] += 0.5
    # SSE=1/4, N=6, sum(T**2)=15/8: MSE=1/24, NMSE=2/15.
    _assert_reference(_call_pair("intensity_mse", target, reconstruction), 1.0 / 24.0, "intensity_mse")
    _assert_reference(_call_pair("intensity_nmse", target, reconstruction), 2.0 / 15.0, "intensity_nmse")


def test_twice_brightness_nmse_uses_intensity_not_amplitude():
    target = _base_target()
    # The intensity NMSE is exactly one; amplitude NMSE would be (sqrt(2)-1)**2.
    assert _call_pair("intensity_nmse", target, 2.0 * target) == 1.0


def test_twice_brightness_mse_preserves_scale_without_peak_normalization():
    target = _base_target()
    # Dyadic inputs give exactly 5/16; separate peak normalization would erase it.
    assert _call_pair("intensity_mse", target, 2.0 * target) == 5.0 / 16.0


def test_nmse_denominator_is_target_squared_intensity_norm():
    target = _base_target()
    # Reversing the reference quadruples its squared norm, leaving the SSE fixed.
    assert _call_pair("intensity_nmse", 2.0 * target, target) == 0.25
    # NMSE is a squared error and has no upper-one bound.
    assert _call_pair("intensity_nmse", target, 4.0 * target) == 9.0


def test_psnr_uses_declared_range_despite_reconstruction_overshoot():
    target = _base_target()
    reconstruction = 2.0 * target
    expected = _decimal_pair_reference(target, reconstruction, 1.0)["intensity_psnr"]
    _assert_reference(_call_pair("intensity_psnr", target, reconstruction, 1.0), expected, "intensity_psnr")
    # Observed max(R)=2 must not replace the explicitly declared range of one.
    assert expected < 6.0


@pytest.mark.parametrize("scale", [0.25, 3.0, 1e-9])
def test_common_scaling_mse_nmse_and_coordinated_psnr_range(scale):
    target = _base_target()
    reconstruction = 2.0 * target
    original = _decimal_pair_reference(target, reconstruction)
    scaled_target, scaled_reconstruction = scale * target, scale * reconstruction
    _assert_reference(_call_pair("intensity_mse", scaled_target, scaled_reconstruction), scale**2 * original["intensity_mse"], "intensity_mse")
    _assert_reference(_call_pair("intensity_nmse", scaled_target, scaled_reconstruction), original["intensity_nmse"], "intensity_nmse")
    _assert_reference(_call_pair("intensity_psnr", scaled_target, scaled_reconstruction, scale), original["intensity_psnr"], "intensity_psnr")
    fixed_range = original["intensity_psnr"] - 20.0 * math.log10(scale)
    _assert_reference(_call_pair("intensity_psnr", scaled_target, scaled_reconstruction), fixed_range, "intensity_psnr")


def test_psnr_large_finite_range_uses_log_domain_without_squaring():
    target = _base_target()
    expected = _decimal_pair_reference(target, 2.0 * target, 1e200)["intensity_psnr"]
    actual = _call_pair("intensity_psnr", target, 2.0 * target, 1e200)
    assert math.isfinite(actual)
    _assert_reference(actual, expected, "intensity_psnr")


def test_zero_target_mse_and_negative_psnr_are_valid_but_nmse_is_undefined():
    target = np.zeros((2, 3), dtype=np.float64)
    reconstruction = np.full((2, 3), 2.0, dtype=np.float64)
    assert _call_pair("intensity_mse", target, reconstruction) == 4.0
    expected = _decimal_pair_reference(target, reconstruction)["intensity_psnr"]
    _assert_reference(_call_pair("intensity_psnr", target, reconstruction), expected, "intensity_psnr")
    assert expected < 0.0
    with pytest.raises(ValueError, match="target"):
        _call_pair("intensity_nmse", target, reconstruction)


def test_identical_zero_images_preserve_distinct_metric_domains():
    target = np.zeros((2, 3), dtype=np.float64)
    assert _call_pair("intensity_mse", target, target) == 0.0
    assert _call_pair("intensity_psnr", target, target) == math.inf
    with pytest.raises(ValueError, match="target"):
        _call_pair("intensity_nmse", target, target)


def test_psnr_exact_equality_is_numerical_and_preserves_signed_zero_bytes():
    target = np.array([[0.0, -0.0, 1.0], [-0.0, 0.0, 2.0]])
    reconstruction = np.array([[-0.0, 0.0, 1.0], [0.0, -0.0, 2.0]])
    before = _snapshot(target), _snapshot(reconstruction)
    assert target.tobytes() != reconstruction.tobytes()
    assert _call_pair("intensity_psnr", target, reconstruction) == math.inf
    assert (_snapshot(target), _snapshot(reconstruction)) == before


def test_psnr_near_equal_images_are_not_an_approximate_perfect_match():
    target = np.ones((2, 3), dtype=np.float64)
    reconstruction = target.copy()
    reconstruction[0, 0] = np.nextafter(1.0, 2.0)
    expected = _decimal_pair_reference(target, reconstruction)
    assert _call_pair("intensity_mse", target, reconstruction) > 0.0
    actual = _call_pair("intensity_psnr", target, reconstruction)
    assert math.isfinite(actual)
    _assert_reference(actual, expected["intensity_psnr"], "intensity_psnr")


def test_partial_region_fraction_uses_full_window_denominator():
    intensity, mask = _region_fixture()
    # Selected power=1+5=6; total=16, not the selected numerator itself.
    assert metrics.signal_region_power_fraction(reconstruction_intensity=intensity, signal_mask=mask) == 3.0 / 8.0


def test_signal_mask_is_honored_not_ignored():
    intensity, mask = _region_fixture()
    # A distinct one-pixel region excludes other positive pixels.
    mask[1, 0] = False
    assert metrics.signal_region_power_fraction(reconstruction_intensity=intensity, signal_mask=mask) == 1.0 / 16.0


def test_signal_mask_is_not_inverted():
    intensity, mask = _region_fixture()
    assert metrics.signal_region_power_fraction(reconstruction_intensity=intensity, signal_mask=mask) == 3.0 / 8.0
    assert metrics.signal_region_power_fraction(reconstruction_intensity=intensity, signal_mask=~mask) == 5.0 / 8.0


def test_regional_cv_is_population_standard_deviation():
    intensity, mask = _region_fixture()
    # Selected [1,5]: mean=3, population variance=4, CV=2/3.
    _assert_reference(metrics.regional_intensity_cv(intensity=intensity, mask=mask), 2.0 / 3.0, "regional_intensity_cv")


def test_sparse_population_cv_is_sqrt_three_and_may_exceed_one():
    intensity = np.array([[0.0, 0.0], [0.0, 4.0]])
    mask = np.ones((2, 2), dtype=np.bool_)
    with localcontext() as context:
        context.prec = 80
        expected = float(Decimal(3).sqrt())
    actual = metrics.regional_intensity_cv(intensity=intensity, mask=mask)
    assert actual > 1.0
    _assert_reference(actual, expected, "regional_intensity_cv")


def test_nonbinary_region_metrics_match_independent_decimal_reference():
    intensity = np.array([[0.1, 2.0, 0.2], [0.5, 0.9, 3.0]])
    mask = np.array([[True, False, True], [True, True, False]])
    expected = _decimal_region_reference(intensity, mask)
    _assert_reference(metrics.signal_region_power_fraction(reconstruction_intensity=intensity, signal_mask=mask), expected["signal_region_power_fraction"], "signal_region_power_fraction")
    _assert_reference(metrics.regional_intensity_cv(intensity=intensity, mask=mask), expected["regional_intensity_cv"], "regional_intensity_cv")


@pytest.mark.parametrize("scale", [0.25, 3.0, 1e-9])
def test_common_intensity_scaling_preserves_power_fraction_and_cv(scale):
    intensity, mask = _region_fixture()
    expected = _decimal_region_reference(intensity, mask)
    scaled = scale * intensity
    _assert_reference(metrics.signal_region_power_fraction(reconstruction_intensity=scaled, signal_mask=mask), expected["signal_region_power_fraction"], "signal_region_power_fraction")
    _assert_reference(metrics.regional_intensity_cv(intensity=scaled, mask=mask), expected["regional_intensity_cv"], "regional_intensity_cv")


def test_outside_region_changes_cv_neither_pixels_nor_mean_but_changes_fraction():
    intensity, mask = _region_fixture()
    changed = intensity.copy()
    changed[0, 1] = 19.0
    expected_cv = 2.0 / 3.0
    _assert_reference(metrics.regional_intensity_cv(intensity=changed, mask=mask), expected_cv, "regional_intensity_cv")
    assert metrics.signal_region_power_fraction(reconstruction_intensity=intensity, signal_mask=mask) == 3.0 / 8.0
    assert metrics.signal_region_power_fraction(reconstruction_intensity=changed, signal_mask=mask) == 3.0 / 16.0


def test_equal_power_fraction_does_not_imply_correct_target_brightness():
    target, mask = _region_fixture()
    reconstruction = 2.0 * target
    assert metrics.signal_region_power_fraction(reconstruction_intensity=target, signal_mask=mask) == 3.0 / 8.0
    assert metrics.signal_region_power_fraction(reconstruction_intensity=reconstruction, signal_mask=mask) == 3.0 / 8.0
    assert _call_pair("intensity_nmse", target, reconstruction) == 1.0
    assert _call_pair("intensity_mse", target, reconstruction) > 0.0


@pytest.mark.parametrize("selection,expected", [("empty", 0.0), ("all", 1.0), ("zero_pixels", 0.0)])
def test_fraction_exact_region_endpoints_with_usable_positive_total(selection, expected):
    intensity, _ = _region_fixture()
    mask = np.zeros_like(intensity, dtype=np.bool_)
    if selection == "all":
        mask[:] = True
    elif selection == "zero_pixels":
        mask[1, 1:] = True
    result = metrics.signal_region_power_fraction(reconstruction_intensity=intensity, signal_mask=mask)
    assert type(result) is float
    assert result == expected  # These region endpoint results are exact contracts.


@pytest.mark.parametrize("all_selected", [False, True])
def test_zero_total_power_is_invalid_even_for_empty_or_full_signal_mask(all_selected):
    intensity = np.zeros((2, 3), dtype=np.float64)
    with pytest.raises(ValueError, match="total"):
        metrics.signal_region_power_fraction(reconstruction_intensity=intensity, signal_mask=np.full((2, 3), all_selected, dtype=np.bool_))


@pytest.mark.parametrize("selection", ["empty", "zeros"])
def test_cv_empty_and_zero_mean_regions_raise(selection):
    intensity, _ = _region_fixture()
    mask = np.zeros_like(intensity, dtype=np.bool_)
    if selection == "zeros":
        mask[1, 1:] = True
    with pytest.raises(ValueError):
        metrics.regional_intensity_cv(intensity=intensity, mask=mask)


@pytest.mark.parametrize("value", [0.125, 3.0, 1e308, float.fromhex("0x0.0000000000001p-1022")])
@pytest.mark.parametrize("single_pixel", [False, True])
def test_positive_constant_cv_shortcut_includes_singletons_and_extreme_values(value, single_pixel):
    intensity = np.full((2, 3), value, dtype=np.float64)
    mask = np.ones((2, 3), dtype=np.bool_)
    if single_pixel:
        mask[:] = False
        mask[0, 1] = True
    assert metrics.regional_intensity_cv(intensity=intensity, mask=mask) == 0.0


def test_three_identical_nonbinary_values_have_exact_zero_cv():
    # Float64 reduction of three 0.1 values can round their mean away from the
    # stored value. Exact equality must take the specified shortcut first.
    intensity = np.full((1, 3), 0.1, dtype=np.float64)
    mask = np.ones((1, 3), dtype=np.bool_)
    assert metrics.regional_intensity_cv(intensity=intensity, mask=mask) == 0.0


def test_cv_near_constant_region_is_not_approximately_constant():
    intensity = np.array([[1.0, np.nextafter(1.0, 2.0)]])
    actual = metrics.regional_intensity_cv(intensity=intensity, mask=np.ones((1, 2), dtype=np.bool_))
    # The standard float64 mean is sensitive here; the required claim is that
    # an exact-only shortcut must not erase this nonzero variation.
    assert math.isfinite(actual) and actual > 0.0


class _ArraySubclass(np.ndarray):
    pass


def _invalid_array(kind: str):
    good = np.ones((2, 3), dtype=np.float64)
    if kind == "list":
        return good.tolist()
    if kind == "scalar":
        return 1.0
    if kind == "subclass":
        return good.view(_ArraySubclass)
    if kind == "masked":
        return np.ma.array(good, mask=False)
    if kind == "opposite_endian":
        return good.astype(np.dtype(np.float64).newbyteorder("S"))
    return good.astype(kind)


@pytest.mark.parametrize("name", METRIC_NAMES)
@pytest.mark.parametrize("kind", ["list", "scalar", "subclass", "masked", "float32", "int64", "bool", "complex128", "opposite_endian"])
def test_intensity_requires_plain_native_float64_array(name, kind):
    with pytest.raises(TypeError):
        _call_metric(name, _invalid_array(kind))


@pytest.mark.parametrize("name", PAIR_NAMES)
@pytest.mark.parametrize("kind", ["list", "float32", "opposite_endian", "subclass"])
def test_reconstruction_argument_is_validated_independently(name, kind):
    with pytest.raises(TypeError, match="reconstruction_intensity"):
        _call_pair(name, np.ones((2, 3), dtype=np.float64), _invalid_array(kind))


@pytest.mark.parametrize("name", METRIC_NAMES)
@pytest.mark.parametrize("shape", [(), (3,), (1, 2, 3), (0, 3), (2, 0)])
def test_intensity_requires_nonempty_two_dimensional_shape(name, shape):
    with pytest.raises(ValueError):
        _call_metric(name, np.ones(shape, dtype=np.float64))


@pytest.mark.parametrize("name", PAIR_NAMES)
@pytest.mark.parametrize("shape", [(3, 2), (1, 3), (2, 1)])
def test_comparison_shape_must_match_exactly_without_broadcasting(name, shape):
    with pytest.raises(ValueError, match="shape"):
        _call_pair(name, np.ones((2, 3), dtype=np.float64), np.ones(shape, dtype=np.float64))


@pytest.mark.parametrize("name", METRIC_NAMES)
@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf, -0.01])
def test_invalid_intensity_is_rejected_even_outside_selected_region_or_exact_match(name, bad_value):
    intensity, mask = _region_fixture()
    intensity[0, 2] = bad_value  # Outside the valid nonempty region.
    before = _snapshot(intensity), _snapshot(mask)
    with pytest.raises(ValueError):
        _call_metric(name, intensity, mask)
    assert (_snapshot(intensity), _snapshot(mask)) == before


@pytest.mark.parametrize("name", PAIR_NAMES)
@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -1.0])
def test_invalid_reconstruction_values_are_rejected(name, bad_value):
    target = np.ones((2, 3), dtype=np.float64)
    reconstruction = target.copy()
    reconstruction[1, 2] = bad_value
    with pytest.raises(ValueError, match="reconstruction_intensity"):
        _call_pair(name, target, reconstruction)


@pytest.mark.parametrize("name", ["signal_region_power_fraction", "regional_intensity_cv"])
@pytest.mark.parametrize("kind", ["list", "subclass", "uint8", "float64", "object"])
def test_masks_require_plain_boolean_arrays(name, kind):
    intensity, mask = _region_fixture()
    if kind == "list":
        invalid = mask.tolist()
    elif kind == "subclass":
        invalid = mask.view(_ArraySubclass)
    else:
        invalid = mask.astype(kind)
    with pytest.raises(TypeError):
        _call_metric(name, intensity, invalid)


@pytest.mark.parametrize("name", ["signal_region_power_fraction", "regional_intensity_cv"])
@pytest.mark.parametrize("shape", [(), (6,), (1, 2, 3), (3, 2), (1, 3), (2, 1)])
def test_masks_require_exact_two_dimensional_shape_without_broadcasting(name, shape):
    with pytest.raises(ValueError):
        _call_metric(name, np.ones((2, 3), dtype=np.float64), np.ones(shape, dtype=np.bool_))


@pytest.mark.parametrize("data_range", [0.0, -1.0, math.nan, math.inf, -math.inf])
def test_psnr_validates_range_domain_before_exact_match(data_range):
    target = _base_target()
    with pytest.raises(ValueError, match="data_range"):
        _call_pair("intensity_psnr", target, target, data_range)


@pytest.mark.parametrize("data_range", [True, np.bool_(True), "1", 1 + 0j, None])
def test_psnr_validates_range_type_before_exact_match(data_range):
    target = _base_target()
    with pytest.raises(TypeError, match="data_range"):
        _call_pair("intensity_psnr", target, target, data_range)


def test_psnr_requires_explicit_range():
    with pytest.raises(TypeError, match="data_range"):
        metrics.intensity_psnr(target_intensity=_base_target(), reconstruction_intensity=_base_target())


@pytest.mark.parametrize("name", METRIC_NAMES)
def test_public_metrics_are_keyword_only(name):
    with pytest.raises(TypeError):
        getattr(metrics, name)(_base_target(), _base_target())


@pytest.mark.parametrize("layout", ["readonly", "fortran", "strided", "reversed"])
def test_supported_layouts_are_deterministic_and_do_not_mutate_or_retain_inputs(layout):
    target = _base_target()
    reconstruction = 2.0 * target + 0.125
    _, mask = _region_fixture()
    if layout == "readonly":
        for array in (target, reconstruction, mask):
            array.setflags(write=False)
    elif layout == "fortran":
        target, reconstruction, mask = (np.asfortranarray(array) for array in (target, reconstruction, mask))
    elif layout == "strided":
        arrays = []
        for array in (target, reconstruction, mask):
            storage = np.empty((4, 6), dtype=array.dtype)
            storage[::2, ::2] = array
            arrays.append(storage[::2, ::2])
        target, reconstruction, mask = arrays
    else:
        target, reconstruction, mask = (array[::-1, ::-1] for array in (target, reconstruction, mask))
    before = tuple(_snapshot(array) for array in (target, reconstruction, mask))
    expected = _decimal_pair_reference(target, reconstruction)
    expected.update(_decimal_region_reference(reconstruction, mask))
    for name in METRIC_NAMES:
        if name in PAIR_NAMES:
            first = _call_pair(name, target, reconstruction)
            second = _call_pair(name, target, reconstruction)
        else:
            first = _call_metric(name, reconstruction, mask)
            second = _call_metric(name, reconstruction, mask)
        _assert_reference(first, expected[name], name)
        assert first == second  # Same input/platform execution is deterministic.
    assert tuple(_snapshot(array) for array in (target, reconstruction, mask)) == before


def test_scalar_results_do_not_retain_input_arrays():
    def evaluate_and_release():
        target = _base_target()
        reconstruction, mask = _region_fixture()
        references = [weakref.ref(array) for array in (target, reconstruction, mask)]
        results = [_call_pair(name, target, reconstruction) for name in PAIR_NAMES]
        results += [_call_metric(name, reconstruction, mask) for name in METRIC_NAMES[3:]]
        return references, results

    references, results = evaluate_and_release()
    gc.collect()
    assert all(type(result) is float for result in results)
    assert all(reference() is None for reference in references)


@pytest.mark.parametrize("name", PAIR_NAMES)
@pytest.mark.parametrize("scale", [1e200, 1e-200])
def test_nonidentical_unusable_squared_error_raises_instead_of_perfect_match(name, scale):
    target = np.full((2, 3), scale, dtype=np.float64)
    reconstruction = 2.0 * target
    with pytest.raises(ValueError, match="arithmetic|representable"):
        _call_pair(name, target, reconstruction)


@pytest.mark.parametrize("scale", [1e200, 1e-200])
def test_nmse_requires_usable_target_norm_even_for_identical_images(scale):
    target = np.full((2, 3), scale, dtype=np.float64)
    assert _call_pair("intensity_psnr", target, target) == math.inf
    assert _call_pair("intensity_mse", target, target) == 0.0
    with pytest.raises(ValueError):
        _call_pair("intensity_nmse", target, target)


@pytest.mark.parametrize("all_selected", [False, True])
def test_fraction_requires_usable_total_before_empty_or_full_mask_shortcut(all_selected):
    intensity = np.full((2, 3), 1e308, dtype=np.float64)
    mask = np.full((2, 3), all_selected, dtype=np.bool_)
    with pytest.raises(ValueError, match="arithmetic|representable"):
        metrics.signal_region_power_fraction(reconstruction_intensity=intensity, signal_mask=mask)


def test_fraction_rejects_underflowing_nonzero_ratio_without_epsilon_or_rescale():
    intensity = np.array([[1e-200, 1e200], [0.0, 0.0]])
    mask = np.array([[True, False], [False, False]])
    with pytest.raises(ValueError, match="arithmetic|representable"):
        metrics.signal_region_power_fraction(reconstruction_intensity=intensity, signal_mask=mask)


@pytest.mark.parametrize("scale", [1e200, 1e-200])
def test_nonconstant_cv_rejects_unusable_variance_arithmetic(scale):
    intensity = np.array([[0.0, scale]])
    with pytest.raises(ValueError, match="arithmetic|representable"):
        metrics.regional_intensity_cv(intensity=intensity, mask=np.ones((1, 2), dtype=np.bool_))


@pytest.mark.parametrize("name", METRIC_NAMES)
@pytest.mark.parametrize("failing", [False, True])
def test_numpy_error_settings_are_restored_after_success_and_arithmetic_failure(name, failing):
    intensity, mask = _region_fixture()
    if failing:
        intensity = np.full((2, 3), 1e200, dtype=np.float64)
        if name == "signal_region_power_fraction":
            intensity[:] = 1e308
        elif name == "regional_intensity_cv":
            intensity[0, 0] = 0.0
    outer_settings = np.geterr().copy()
    with np.errstate(over="ignore", under="warn", invalid="ignore", divide="warn"):
        caller_settings = np.geterr().copy()
        if failing:
            with pytest.raises(ValueError):
                if name in PAIR_NAMES:
                    _call_pair(name, intensity, 2.0 * intensity)
                else:
                    _call_metric(name, intensity, mask)
        elif name in PAIR_NAMES:
            _call_pair(name, intensity, 2.0 * intensity)
        else:
            _call_metric(name, intensity, mask)
        assert np.geterr() == caller_settings
    assert np.geterr() == outer_settings


def _m3_integration_fixture():
    """Small actual M3 solve; no precomputed or postprocessed reconstruction."""
    grid = SamplingGrid(ny=2, nx=3, dy=10e-6, dx=8e-6)
    source = np.array([[0.5, 0.75, 1.0], [0.25, 0.5, 0.75]])
    target = np.roll(source, 1, axis=1).copy()
    phase = np.array([[0.1, 0.4, -0.7], [1.2, -1.0, 0.3]])
    result = gerchberg_saxton(
        target_amplitude=target, source_amplitude=source, grid=grid,
        wavelength_m=633e-9, distance_m=2e-4, iterations=1, initial_phase=phase,
    )
    return grid, source, target, phase, result


def test_actual_m3_reconstruction_metrics_match_scalar_references_and_preserve_amplitude_residual():
    grid, source, target, initial_phase, result = _m3_integration_fixture()
    target_intensity = target**2
    reconstruction_intensity = result.reconstruction.intensity
    _, mask = _region_fixture()
    snapshots = [
        source, target, initial_phase, target_intensity, reconstruction_intensity,
        mask, result.source_field.data, result.reconstruction.data, result.residual_history,
    ]
    before = [_snapshot(array) for array in snapshots]
    rebuilt_source = ComplexField.from_amplitude_phase(
        amplitude=source, phase=result.phase, grid=grid, wavelength_m=633e-9,
    )
    independent_forward = propagate_angular_spectrum(rebuilt_source, distance_m=2e-4, pad_factor=1)
    # M3's measured complex-field reference budget, scaled only by input peak.
    np.testing.assert_allclose(independent_forward.data, result.reconstruction.data, rtol=1e-12, atol=1e-13 * float(np.max(source)))
    scalar_intensity = np.array([
        [float(value.real)**2 + float(value.imag)**2 for value in row]
        for row in independent_forward.data
    ], dtype=np.float64)
    np.testing.assert_allclose(reconstruction_intensity, scalar_intensity, rtol=1e-12, atol=1e-14)
    # Evaluate the actual result intensity; independent scalar references use
    # the public-ASM reconstruction rebuilt from returned phase and prescribed A.
    expected = _decimal_pair_reference(target_intensity, scalar_intensity)
    expected.update(_decimal_region_reference(scalar_intensity, mask))
    actual = {}
    for name in METRIC_NAMES:
        actual[name] = (
            _call_pair(name, target_intensity, reconstruction_intensity)
            if name in PAIR_NAMES else _call_metric(name, reconstruction_intensity, mask)
        )
        _assert_reference(actual[name], expected[name], name)
    amplitude_error = math.fsum(
        (abs(complex(value)) - float(amplitude))**2
        for value, amplitude in zip(independent_forward.data.flat, target.flat)
    ) / math.fsum(float(amplitude)**2 for amplitude in target.flat)
    np.testing.assert_allclose(result.residual_history[-1], amplitude_error, rtol=1e-12, atol=1e-14)
    # Pin the semantic distinction, without requiring metric monotonicity.
    assert abs(actual["intensity_nmse"] - amplitude_error) > 0.1
    assert [_snapshot(array) for array in snapshots] == before
