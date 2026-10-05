"""V2a scalar records, numerical domains and supported public ownership."""

from dataclasses import FrozenInstanceError
import math

import numpy as np
import pytest

from ohlab import ComplexField, SamplingGrid
from ohlab.optics.interference import (TwoArmNorms, TwoArmResult, TwoArmSpec,
                                       apply_uniform_phase, run_two_arm)


def field(*, ny=3, nx=4, dx=4e-6, dy=5e-6, amplitude=1.0, wavelength=633e-9):
    grid = SamplingGrid(ny=ny, nx=nx, dy=dy, dx=dx)
    return ComplexField(data=np.full(grid.shape, amplitude, dtype=np.complex128),
                        grid=grid, wavelength_m=wavelength)


def spec(**changes):
    values = dict(arm_0_distance_m=0.0, arm_1_distance_m=0.0, relative_phase_rad=0.37)
    values.update(changes)
    return TwoArmSpec(**values)


def norms(**changes):
    values = dict(inputs=(4., 0.), split=(2., 2.), propagated=(1., 2.),
                  combiner=(1., 2.), outputs=(2., 1.))
    values.update(changes)
    return TwoArmNorms(**values)


def sampled_norm(value):
    return float(np.sum(np.abs(value.data) ** 2, dtype=np.float64) * value.grid.dx * value.grid.dy)


def test_spec_keyword_only_frozen_signed_phase_and_numpy_scalars():
    value = TwoArmSpec(arm_0_distance_m=np.float64(-0.0), arm_1_distance_m=np.int32(0),
                       relative_phase_rad=np.float64(-2 * math.pi - .37))
    assert math.copysign(1, value.arm_0_distance_m) == -1
    assert value.relative_phase_rad == -2 * math.pi - .37
    assert all(type(getattr(value, name)) is float for name in value.__dataclass_fields__)
    with pytest.raises(TypeError):
        TwoArmSpec(0, 0, 0)
    with pytest.raises(FrozenInstanceError):
        value.relative_phase_rad = 0


@pytest.mark.parametrize("name", ["arm_0_distance_m", "arm_1_distance_m", "relative_phase_rad"])
@pytest.mark.parametrize("value", [True, np.bool_(False), "1", 1+0j, np.array(1), None])
def test_spec_rejects_scalar_kind_errors(name, value):
    with pytest.raises(TypeError, match=name):
        spec(**{name: value})


@pytest.mark.parametrize("name", ["arm_0_distance_m", "arm_1_distance_m", "relative_phase_rad"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), 10**1000])
def test_spec_rejects_unrepresentable_values(name, value):
    with pytest.raises(ValueError, match=name):
        spec(**{name: value})


@pytest.mark.parametrize("name", ["arm_0_distance_m", "arm_1_distance_m"])
def test_distances_reject_negative_values(name):
    with pytest.raises(ValueError, match="nonnegative"):
        spec(**{name: -1e-12})


def test_norms_derive_ten_values_signed_residuals_and_input_denominators():
    value = norms()
    assert (value.inputs_total, value.split_total, value.propagated_total,
            value.combiner_total, value.outputs_total) == (4., 4., 3., 3., 3.)
    assert (value.split_delta, value.propagation_delta, value.phase_delta,
            value.recombination_delta, value.total_delta) == (0., -1., 0., 0., -1.)
    assert value.output_fractions == (.5, .25)
    assert value.total_output_ratio == .75
    increased = norms(combiner=(1., 2.5), outputs=(2., 1.75))
    assert increased.phase_delta == .5
    assert increased.recombination_delta == .25
    assert increased.total_delta == -.25
    assert norms(outputs=(5., 1.)).output_fractions == (1.25, .25)
    assert norms(outputs=(5., 1.)).total_output_ratio == 1.5
    with pytest.raises(FrozenInstanceError):
        value.outputs = (0., 0.)
    with pytest.raises(TypeError):
        TwoArmNorms((0., 0.), (0., 0.), (0., 0.), (0., 0.), (0., 0.))


def test_zero_denominator_is_undefined_and_dark_positive_input_port_is_zero():
    assert norms(inputs=(0., 0.)).output_fractions == (None, None)
    assert norms(inputs=(0., 0.)).total_output_ratio is None
    assert norms(outputs=(0., 3.)).output_fractions == (0., .75)


@pytest.mark.parametrize("name", ["inputs", "split", "propagated", "combiner", "outputs"])
@pytest.mark.parametrize("value,error", [([1., 0.], TypeError), ((1.,), ValueError),
                                        ((1., 0., 0.), ValueError), ((True, 0.), TypeError),
                                        ((np.bool_(False), 0.), TypeError), ((1+0j, 0.), TypeError),
                                        ((-1., 0.), ValueError), ((float("nan"), 0.), ValueError)])
def test_scalar_pairs_validate_shape_kind_and_domain(name, value, error):
    with pytest.raises(error, match=name):
        norms(**{name: value})


def test_norms_reject_aggregate_overflow_ratio_overflow_and_positive_underflow():
    with pytest.raises(ValueError, match="total sampled norm"):
        norms(split=(1e308, 1e308))
    with pytest.raises(ValueError, match="ratio"):
        norms(inputs=(5e-324, 0.), outputs=(1., 0.))
    with pytest.raises(ValueError, match="ratio"):
        norms(inputs=(1e308, 0.), outputs=(5e-324, 0.))


def test_result_copies_both_public_fields_revalidates_norms_and_identity_equality():
    source = field()
    amount = sampled_norm(source)
    records = TwoArmNorms(inputs=(2 * amount, 0.), split=(amount, amount),
                          propagated=(amount, amount), combiner=(amount, amount),
                          outputs=(amount, amount))
    result = TwoArmResult(spec=spec(), outputs=(source, source), norms=records)
    duplicate = TwoArmResult(spec=spec(), outputs=(source, source), norms=records)
    assert result != duplicate
    assert result == result
    for output in result.outputs:
        assert output is not source
        assert output.data.dtype == np.complex128
        assert not output.data.flags.writeable
        assert not np.shares_memory(output.data, source.data)
    assert not np.shares_memory(result.outputs[0].data, result.outputs[1].data)
    before = result.outputs[0].data.tobytes()
    source.data.setflags(write=True)
    source.data[:] = 9
    assert result.outputs[0].data.tobytes() == before
    assert result.outputs[1].data.tobytes() == before
    # Existing public read-only semantics, with no new write-flag hardening.
    with pytest.raises(ValueError):
        result.outputs[0].data[0, 0] = 8
    with pytest.raises(FrozenInstanceError):
        result.outputs = (source, source)


@pytest.mark.parametrize("change,error,match", [
    ({"spec": {}}, TypeError, "spec"), ({"outputs": []}, TypeError, "outputs"),
    ({"outputs": ()}, ValueError, "two fields"), ({"norms": {}}, TypeError, "norms"),
    ({"norms": norms(inputs=(1., 1.))}, ValueError, "second input"),
    ({"norms": norms(outputs=(1., 1.))}, ValueError, "sampled norm")])
def test_result_rejects_bad_records(change, error, match):
    original = run_two_arm(field(), spec=spec())
    values = dict(spec=original.spec, outputs=original.outputs, norms=original.norms)
    values.update(change)
    with pytest.raises(error, match=match):
        TwoArmResult(**values)


def test_result_rejects_incompatible_output_fields():
    original = run_two_arm(field(), spec=spec())
    with pytest.raises(ValueError, match="grids"):
        TwoArmResult(spec=original.spec, outputs=(original.outputs[0], field(dx=6e-6)),
                     norms=original.norms)


@pytest.mark.parametrize("side", ["ny", "nx"])
def test_runner_cap_rejects_before_copies_and_calls(monkeypatch, side):
    import ohlab.optics.interference as module
    value = field(**{side: 513})
    def forbidden(*args, **kwargs):
        pytest.fail("cap must reject before copying or public propagation")
    monkeypatch.setattr(module, "_owned", forbidden)
    monkeypatch.setattr(module, "propagate_angular_spectrum", forbidden)
    with pytest.raises(ValueError, match=f"grid.{side}: expected 1..512"):
        run_two_arm(value, spec=spec())


@pytest.mark.parametrize("shape", [(1, 1), (3, 4), (4, 3), (1, 512), (512, 1)])
def test_runner_allowed_counts_final_norms_and_nonmutation(shape):
    source = field(ny=shape[0], nx=shape[1])
    original = source.data.tobytes()
    result = run_two_arm(source, spec=spec())
    assert source.data.tobytes() == original
    assert result.spec == spec()
    assert all(output.grid == source.grid for output in result.outputs)
    assert result.norms.inputs == (sampled_norm(source), 0.)
    assert result.norms.outputs == tuple(sampled_norm(output) for output in result.outputs)
    assert not np.shares_memory(result.outputs[0].data, result.outputs[1].data)
    for output in result.outputs:
        assert not np.shares_memory(output.data, source.data)


def test_runner_argument_kinds_and_tampered_spec_revalidation():
    with pytest.raises(TypeError, match="spec"):
        run_two_arm(field(), spec={})
    with pytest.raises(TypeError, match="incident"):
        run_two_arm(np.ones((3, 4)), spec=spec())
    invalid = spec()
    object.__setattr__(invalid, "arm_0_distance_m", -1.)
    with pytest.raises(ValueError, match="nonnegative"):
        run_two_arm(field(), spec=invalid)


@pytest.mark.parametrize("operation", [lambda f: apply_uniform_phase(f, phase_rad=0),
                                       lambda f: run_two_arm(f, spec=spec(relative_phase_rad=0))])
@pytest.mark.parametrize("change,error", [("dtype", TypeError), ("shape", ValueError),
                                        ("nonfinite", ValueError), ("wavelength", ValueError)])
def test_input_validation_is_not_bypassed_at_zero_distance_or_phase(operation, change, error):
    value = field()
    if change == "dtype":
        object.__setattr__(value, "data", np.ones((3, 4), dtype=np.complex64))
    elif change == "shape":
        object.__setattr__(value, "data", np.ones((4, 3), dtype=np.complex128))
    elif change == "nonfinite":
        value.data.setflags(write=True)
        value.data[0, 0] = np.nan
    else:
        object.__setattr__(value, "wavelength_m", 0.)
    with pytest.raises(error):
        operation(value)


def test_dark_and_zero_distance_do_not_bypass_derived_geometry_or_phase_bound():
    dark = field(nx=1, ny=1, dx=5e-324, dy=1., amplitude=0.)
    with pytest.raises(ValueError, match="reciprocal extent"):
        run_two_arm(dark, spec=spec(relative_phase_rad=0.))
    with pytest.raises(ValueError, match="propagation phase bound"):
        run_two_arm(field(amplitude=0.), spec=spec(arm_1_distance_m=1e308))


@pytest.mark.parametrize("changes,match", [
    ({"dx": 1e308, "dy": 1e308}, "pixel area"),
    ({"dx": 1e-200, "dy": 1e-200}, "pixel area"),
    ({"wavelength": 5e-324}, "inverse wavelength"),
    ({"wavelength": 1e-200}, "cutoff squared"),
    ({"nx": 3, "ny": 3, "dx": 1e154, "dy": 1e154}, "radial coordinate squared")])
def test_derived_arithmetic_errors_are_contextual_and_leave_error_settings(changes, match):
    dark = field(amplitude=0., **changes)
    with np.errstate(all="raise"):
        before = np.geterr().copy()
        with pytest.raises(ValueError, match=match):
            apply_uniform_phase(dark, phase_rad=0.)
        assert np.geterr() == before


def test_single_sample_has_no_transverse_mode_despite_anisotropic_extreme_pitch():
    source = field(ny=1, nx=1, dx=1e200, dy=1e-200)
    result = run_two_arm(source, spec=spec(arm_0_distance_m=1e-7, arm_1_distance_m=1e-7))
    np.testing.assert_allclose(result.norms.total_output_ratio, 1., rtol=2e-13, atol=2e-13)
