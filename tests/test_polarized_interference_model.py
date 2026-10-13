"""V2f exact records, checkpoint connections, domain and public ownership."""

from dataclasses import FrozenInstanceError
import math

import numpy as np
import pytest

from ohlab import ComplexField, SamplingGrid
from ohlab.optics.polarization import JonesField
from ohlab.optics import polarized_interference as module
from ohlab.optics.polarized_interference import (
    PolarizerAction, RetarderAction, PolarizationArm, PolarizedTwoArmSpec,
    PolarizedTwoArmNorms, PolarizedTwoArmResult, run_polarized_two_arm,
)


def jones(x=1, y=.3j, *, ny=3, nx=4, dx=4e-6, dy=5e-6, wavelength=633e-9):
    grid = SamplingGrid(ny=ny, nx=nx, dx=dx, dy=dy)
    return JonesField(x=ComplexField(data=np.full(grid.shape, x, dtype=np.complex128),
                                    grid=grid, wavelength_m=wavelength),
                      y=ComplexField(data=np.full(grid.shape, y, dtype=np.complex128),
                                    grid=grid, wavelength_m=wavelength))


def spec(*, actions_0=(), actions_1=(), distance_0=0., distance_1=0., phase=.37):
    return PolarizedTwoArmSpec(arm_0=PolarizationArm(distance_m=distance_0, actions=actions_0),
        arm_1=PolarizationArm(distance_m=distance_1, actions=actions_1), relative_phase_rad=phase)


def norms(**changes):
    values = dict(inputs=(4., 0.), split=(2., 2.), propagated=(1., 2.),
        elements=(.75, 1.25), combiner=(.75, 1.5), outputs=(1.5, .75),
        arm_action_norms=((.875, .75), (1.25,)))
    values.update(changes)
    return PolarizedTwoArmNorms(**values)


def test_closed_records_are_frozen_keyword_only_and_scalar_snapshots():
    polarizer = PolarizerAction(axis_angle_rad=np.float64(-.37))
    retarder = RetarderAction(axis_angle_rad=np.int32(0), retardance_rad=-2*math.pi-.83)
    arm = PolarizationArm(distance_m=np.float64(-0.), actions=(polarizer, retarder))
    request = PolarizedTwoArmSpec(arm_0=arm, arm_1=PolarizationArm(distance_m=0),
                                  relative_phase_rad=np.float64(-.61))
    assert math.copysign(1, arm.distance_m) == -1
    assert type(polarizer.axis_angle_rad) is float
    assert type(retarder.axis_angle_rad) is type(retarder.retardance_rad) is float
    assert type(arm.distance_m) is type(request.relative_phase_rad) is float
    assert arm.actions == (polarizer, retarder)
    for record, name in ((polarizer, "axis_angle_rad"), (retarder, "retardance_rad"),
                          (arm, "distance_m"), (request, "relative_phase_rad")):
        assert record.__dataclass_params__.frozen
        with pytest.raises(FrozenInstanceError):
            setattr(record, name, 0)
    for constructor, args in ((PolarizerAction, (0,)), (RetarderAction, (0, 0)),
        (PolarizationArm, (0,)), (PolarizedTwoArmSpec, (arm, arm, 0))):
        with pytest.raises(TypeError):
            constructor(*args)


@pytest.mark.parametrize("constructor,name", [(PolarizerAction, "axis_angle_rad"),
    (lambda **kw: RetarderAction(axis_angle_rad=0, **kw), "retardance_rad"),
    (PolarizationArm, "distance_m")], ids=["axis", "delta", "distance"])
@pytest.mark.parametrize("value", [True, np.bool_(False), "1", 1j, np.array(1), None,
    np.timedelta64(1, "s"), np.datetime64("2026-01-01")],
    ids=["bool", "npbool", "str", "complex", "array", "none", "duration", "date"])
def test_record_scalar_kind_errors(constructor, name, value):
    with pytest.raises(TypeError, match=name):
        constructor(**{name: value})


@pytest.mark.parametrize("constructor,name", [(PolarizerAction, "axis_angle_rad"),
    (lambda **kw: RetarderAction(axis_angle_rad=0, **kw), "retardance_rad"),
    (PolarizationArm, "distance_m")], ids=["axis", "delta", "distance"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), 10**1000],
                         ids=["nan", "inf", "negativeinf", "huge"])
def test_record_unusable_values(constructor, name, value):
    with pytest.raises(ValueError, match=name):
        constructor(**{name: value})


def test_negative_distance_and_closed_action_sequence():
    with pytest.raises(ValueError, match="nonnegative"):
        PolarizationArm(distance_m=-1e-9)
    p = PolarizerAction(axis_angle_rad=0)
    with pytest.raises(ValueError, match="0.*2|at most two|zero.*two"):
        PolarizationArm(distance_m=0, actions=(p, p, p))
    for value in ([p], {"axis_angle_rad": 0}, None):
        with pytest.raises(TypeError, match="actions"):
            PolarizationArm(distance_m=0, actions=value)
    with pytest.raises(TypeError, match="actions"):
        PolarizationArm(distance_m=0, actions=({},))
    class DerivedAction(PolarizerAction):
        pass
    with pytest.raises(TypeError, match="action"):
        PolarizationArm(distance_m=0, actions=(DerivedAction(axis_angle_rad=0),))


@pytest.mark.parametrize("name", ["arm_0", "arm_1"])
def test_spec_requires_exact_arms_and_revalidates_tampering(name):
    arm = PolarizationArm(distance_m=0)
    values = dict(arm_0=arm, arm_1=arm, relative_phase_rad=0)
    values[name] = {}
    with pytest.raises(TypeError, match=name):
        PolarizedTwoArmSpec(**values)
    object.__setattr__(arm, "distance_m", -1.)
    values[name] = arm
    with pytest.raises(ValueError, match="distance_m"):
        PolarizedTwoArmSpec(**values)


def test_norms_checkpoint_totals_histories_signed_budgets_and_denominators():
    value = norms()
    assert tuple(getattr(value, name+"_total") for name in
        ("inputs", "split", "propagated", "elements", "combiner", "outputs")) == (4, 4, 3, 2, 2.25, 2.25)
    assert (value.split_delta, value.propagation_delta, value.elements_delta,
            value.phase_delta, value.recombination_delta, value.total_delta) == (0, -1, -1, .25, 0, -1.75)
    assert value.propagation_deltas == (-1, 0)
    assert value.element_deltas == (-.25, -.75)
    assert value.phase_deltas == (0, .25)
    assert value.arm_action_deltas == ((-.125, -.125), (-.75,))
    assert value.output_fractions == (.375, .1875)
    assert value.total_output_ratio == .5625
    assert sum((value.split_delta, value.propagation_delta, value.elements_delta,
                value.phase_delta, value.recombination_delta)) == value.total_delta
    assert norms(outputs=(5., 1.)).output_fractions == (1.25, .25)
    assert norms(outputs=(5., 1.)).total_output_ratio == 1.5
    tiny_signed = norms(combiner=(.75, float(np.nextafter(1.25, 0))))
    assert tiny_signed.phase_delta < 0
    with pytest.raises(FrozenInstanceError):
        value.outputs = (0., 0.)


@pytest.mark.parametrize("name", ["inputs", "split", "propagated", "elements", "combiner", "outputs"])
@pytest.mark.parametrize("value,error", [([0., 0.], TypeError), ((0.,), ValueError),
    ((True, 0.), TypeError), ((-1., 0.), ValueError), ((float("nan"), 0.), ValueError)],
    ids=["list", "short", "bool", "negative", "nan"])
def test_norm_pair_kind_shape_and_values(name, value, error):
    with pytest.raises(error, match=name):
        norms(**{name: value})


@pytest.mark.parametrize("history,error", [([(), ()], TypeError), (((),), ValueError),
    (([], ()), TypeError), (((1., 1., 1.), ()), ValueError),
    (((True,), (1.25,)), TypeError), (((-.1,), (1.25,)), ValueError)],
    ids=["outerlist", "outershort", "innerlist", "long", "bool", "negative"])
def test_action_histories_are_bounded_immutable_pairs(history, error):
    with pytest.raises(error, match="arm_action_norms"):
        norms(arm_action_norms=history)


def test_history_connections_and_unchanged_arm_zero_are_exact():
    with pytest.raises(ValueError, match="elements|history|action"):
        norms(arm_action_norms=((.875, .74), (1.25,)))
    with pytest.raises(ValueError, match="elements|history|action"):
        norms(arm_action_norms=((), (1.25,)))
    with pytest.raises(ValueError, match="combiner|arm.?0"):
        norms(combiner=(.76, 1.5))
    empty = PolarizedTwoArmNorms(inputs=(0, 0), split=(0, 0), propagated=(0, 0),
        elements=(0, 0), combiner=(0, 0), outputs=(0, 0))
    assert empty.arm_action_norms == empty.arm_action_deltas == ((), ())
    assert empty.output_fractions == (None, None) and empty.total_output_ratio is None


def test_norm_aggregate_and_strict_ratio_arithmetic():
    with pytest.raises(ValueError, match="total|overflow"):
        norms(split=(1e308, 1e308))
    for changes in (dict(inputs=(5e-324, 0), outputs=(1, 0)),
                    dict(inputs=(1e308, 0), outputs=(5e-324, 0)),
                    dict(inputs=(3, 0), outputs=(5e-324, 0))):
        with pytest.raises(ValueError, match="ratio|fraction|underflow"):
            norms(**changes)


def test_result_four_component_ownership_revalidation_and_identity_equality():
    source = jones()
    n = source.sampled_norm
    records = PolarizedTwoArmNorms(inputs=(2*n, 0), split=(n, n), propagated=(n, n),
                                   elements=(n, n), combiner=(n, n), outputs=(n, n))
    result = PolarizedTwoArmResult(spec=spec(), outputs=(source, source), norms=records)
    duplicate = PolarizedTwoArmResult(spec=spec(), outputs=(source, source), norms=records)
    assert result == result and result != duplicate
    assert result.__dataclass_params__.eq is False
    assert result.spec is not duplicate.spec
    arrays = [part.data for output in result.outputs for part in (output.x, output.y)]
    saved = [data.tobytes() for data in arrays]
    for i, data in enumerate(arrays):
        assert data.dtype == np.dtype(np.complex128) and data.dtype.isnative
        assert data.flags.owndata and not data.flags.writeable
        assert all(not np.shares_memory(data, other) for other in arrays[i+1:])
        assert all(not np.shares_memory(data, original.data) for original in (source.x, source.y))
    source.x.data.setflags(write=True)
    source.x.data[:] = 17
    assert [data.tobytes() for data in arrays] == saved
    with pytest.raises(ValueError):
        arrays[0][0, 0] = 1
    with pytest.raises(FrozenInstanceError):
        result.outputs = (source, source)


def test_result_checks_output_norms_second_input_and_history_lengths():
    result = run_polarized_two_arm(jones(), spec=spec())
    values = dict(spec=result.spec, outputs=result.outputs, norms=result.norms)
    for changes, error, match in ((dict(spec={}), TypeError, "spec"),
        (dict(outputs=[]), TypeError, "outputs"), (dict(outputs=()), ValueError, "two|2"),
        (dict(norms={}), TypeError, "norms")):
        with pytest.raises(error, match=match):
            PolarizedTwoArmResult(**(values | changes))
    base = {name: getattr(result.norms, name) for name in result.norms.__dataclass_fields__}
    for changes, match in ((dict(inputs=(1, 1)), "second|inputs"),
        (dict(outputs=(1, 1)), "norm")):
        with pytest.raises(ValueError, match=match):
            PolarizedTwoArmResult(**(values | {"norms": PolarizedTwoArmNorms(**(base | changes))}))
    with pytest.raises(ValueError, match="history|action"):
        PolarizedTwoArmResult(**(values | {"spec": spec(actions_0=(PolarizerAction(axis_angle_rad=0),))}))


@pytest.mark.parametrize("axis", ["ny", "nx"])
def test_runner_cap_precedes_avoidable_copies_and_optical_work(monkeypatch, axis):
    source = jones(**{axis: 129})
    def forbidden(*args, **kwargs):
        pytest.fail("runner cap must reject before snapshots or optical work")
    monkeypatch.setattr(module, "_snapshot", forbidden)
    for name in ("mix_balanced", "propagate_angular_spectrum", "apply_uniform_phase"):
        monkeypatch.setattr(module, name, forbidden)
    with pytest.raises(ValueError, match=f"{axis}.*128"):
        run_polarized_two_arm(source, spec=spec())


@pytest.mark.parametrize("shape", [(1, 1), (3, 4), (4, 3), (1, 128), (128, 1)])
def test_runner_supported_sizes_checkpoint_reduction_and_input_bytes(shape):
    source = jones(ny=shape[0], nx=shape[1])
    before = (source.x.data.tobytes(), source.y.data.tobytes())
    result = run_polarized_two_arm(source, spec=spec())
    assert result.norms.inputs == (source.sampled_norm, 0)
    assert result.norms.outputs == tuple(field.sampled_norm for field in result.outputs)
    assert result.norms.elements == result.norms.propagated
    assert result.norms.arm_action_norms == ((), ())
    assert before == (source.x.data.tobytes(), source.y.data.tobytes())


@pytest.mark.parametrize("arm", [0, 1])
def test_action_created_tiny_component_fails_at_next_scalar_boundary(arm):
    action = PolarizerAction(axis_angle_rad=1e-200)
    request = spec(**{f"actions_{arm}": (action,)})
    with pytest.raises(ValueError, match="(phase|recombination).*y|y.*(phase|recombination)") as caught:
        run_polarized_two_arm(jones(1, 0), spec=request)
    assert caught.value.__cause__ is not None


def test_jones_only_tiny_intermediate_remains_supported(monkeypatch):
    original = module.apply_linear_polarizer
    observed = []
    def record(field, *, axis_angle_rad):
        result = original(field, axis_angle_rad=axis_angle_rad)
        observed.append(result)
        return result
    monkeypatch.setattr(module, "apply_linear_polarizer", record)
    request = spec(actions_1=(PolarizerAction(axis_angle_rad=1e-200),
                              PolarizerAction(axis_angle_rad=math.pi/4)))
    result = run_polarized_two_arm(jones(1, 0), spec=request)
    assert len(observed) == 2
    assert np.all(observed[0].y.data != 0)
    assert np.max(np.abs(observed[0].y.data)) < 1e-199
    assert observed[0].sampled_norm > 0
    assert np.all(observed[1].y.data != 0)
    assert result.norms.arm_action_norms[1] == tuple(field.sampled_norm for field in observed)
    assert result.norms.elements[1] == observed[-1].sampled_norm


def test_action_measurements_connect_to_all_checkpoints(monkeypatch):
    observed = [[], []]
    original = module.apply_linear_retarder
    def record(field, *, axis_angle_rad, retardance_rad):
        result = original(field, axis_angle_rad=axis_angle_rad, retardance_rad=retardance_rad)
        observed[0 if axis_angle_rad == .13 else 1].append((field.sampled_norm, result.sampled_norm))
        return result
    monkeypatch.setattr(module, "apply_linear_retarder", record)
    request = spec(actions_0=(RetarderAction(axis_angle_rad=.13, retardance_rad=.83),)*2,
                   actions_1=(RetarderAction(axis_angle_rad=.61, retardance_rad=-.37),))
    result = run_polarized_two_arm(jones(), spec=request)
    for arm in range(2):
        assert observed[arm][0][0] == result.norms.propagated[arm]
        assert tuple(after for before, after in observed[arm]) == result.norms.arm_action_norms[arm]
        assert observed[arm][-1][1] == result.norms.elements[arm]
        np.testing.assert_allclose(sum(result.norms.arm_action_deltas[arm]),
            result.norms.element_deltas[arm], rtol=2e-13, atol=2e-13*result.norms.inputs_total)


@pytest.mark.parametrize("setting", ["ignore", "warn", "raise"])
def test_runner_caller_error_mapping_restored_for_success_and_failure(setting):
    with np.errstate(all=setting):
        before = np.geterr().copy()
        run_polarized_two_arm(jones(), spec=spec(distance_0=.002, distance_1=.003))
        assert np.geterr() == before
        with pytest.raises(ValueError):
            run_polarized_two_arm(jones(1, 1e-200), spec=spec())
        assert np.geterr() == before
        with pytest.raises(ValueError):
            run_polarized_two_arm(jones(), spec=spec(distance_1=1e308))
        assert np.geterr() == before


@pytest.mark.parametrize("change,error", [("dtype", TypeError), ("shape", ValueError),
    ("finite", ValueError), ("wavelength", ValueError), ("crossmeta", ValueError)])
def test_dark_zero_shortcuts_do_not_bypass_input_validation(change, error):
    source = jones(0, 0)
    if change == "dtype":
        object.__setattr__(source.y, "data", np.zeros(source.shape, dtype=np.complex64))
    elif change == "shape":
        object.__setattr__(source.y, "data", np.zeros((4, 3), dtype=np.complex128))
    elif change == "finite":
        source.y.data.setflags(write=True)
        source.y.data[0, 0] = np.nan
    elif change == "wavelength":
        object.__setattr__(source.x, "wavelength_m", 0.)
    else:
        object.__setattr__(source.y, "wavelength_m", 532e-9)
    with pytest.raises(error):
        run_polarized_two_arm(source, spec=spec(phase=0))


def test_tampered_later_action_is_validated_before_any_optical_calls(monkeypatch):
    request = spec(actions_1=(RetarderAction(axis_angle_rad=.37, retardance_rad=.83),))
    object.__setattr__(request.arm_1.actions[0], "retardance_rad", float("nan"))
    def forbidden(*args, **kwargs):
        pytest.fail("validate the complete static request before optical work")
    monkeypatch.setattr(module, "mix_balanced", forbidden)
    with pytest.raises(ValueError, match="retardance_rad"):
        run_polarized_two_arm(jones(0, 0), spec=request)


@pytest.mark.parametrize("axis", ["ny", "nx"])
def test_uncapped_mixer_enormous_tampered_count_has_contextual_geometry_error(monkeypatch, axis):
    source, other = jones(), jones()
    object.__setattr__(source.grid, axis, 10**400)
    def forbidden(*args, **kwargs):
        pytest.fail("invalid geometry must fail before any scalar mixing")
    monkeypatch.setattr(module, "mix_balanced", forbidden)
    with np.errstate(all="raise"):
        before = np.geterr().copy()
        with pytest.raises(ValueError, match="geometry|extent") as caught:
            module.mix_balanced_jones(source, other, matrix="B")
        assert isinstance(caught.value.__cause__, OverflowError)
        assert np.geterr() == before


def test_coordinate_overriding_grid_subclass_is_not_accepted_after_tampering():
    class ReversedGrid(SamplingGrid):
        @property
        def x(self):
            return -super().x
    source = jones()
    changed = ReversedGrid(ny=3, nx=4, dx=4e-6, dy=5e-6)
    object.__setattr__(source.x, "grid", changed)
    with pytest.raises(TypeError, match="canonical SamplingGrid"):
        run_polarized_two_arm(source, spec=spec())


def test_closed_tuple_and_arm_record_types_do_not_accept_subclasses():
    class TupleSubclass(tuple):
        pass
    class ArmSubclass(PolarizationArm):
        pass
    class NormSubclass(PolarizedTwoArmNorms):
        pass
    with pytest.raises(TypeError, match="actions"):
        PolarizationArm(distance_m=0, actions=TupleSubclass())
    with pytest.raises(TypeError, match="arm_0"):
        PolarizedTwoArmSpec(arm_0=ArmSubclass(distance_m=0),
            arm_1=PolarizationArm(distance_m=0), relative_phase_rad=0)
    with pytest.raises(TypeError, match="inputs"):
        norms(inputs=TupleSubclass((4, 0)))
    original = run_polarized_two_arm(jones(), spec=spec())
    alternative = NormSubclass(**{name: getattr(original.norms, name)
                                  for name in original.norms.__dataclass_fields__})
    with pytest.raises(TypeError, match="norms"):
        PolarizedTwoArmResult(spec=original.spec, outputs=original.outputs, norms=alternative)
