"""Independent full-complex V2f optical, direct-sum and weak-signal evidence."""

import cmath
from decimal import Decimal, localcontext
import math

import numpy as np
import pytest

from ohlab import ComplexField, SamplingGrid
from ohlab.optics.interference import TwoArmSpec, run_two_arm
from ohlab.optics.polarization import JonesField, apply_linear_polarizer, transmission_ratio
from ohlab.optics.polarized_interference import (
    PolarizerAction, RetarderAction, PolarizationArm, PolarizedTwoArmSpec,
    run_polarized_two_arm,
)
from scripts import validate_v2f_interference as reference

PHASES = tuple(k*math.pi/8 for k in range(17))
EXTRA_PHASES = (0., math.pi/2, math.pi, 3*math.pi/2, 2*math.pi, .37, -.83, 2.41)
WEAK_PHASES = (-1e-9, 1e-9, math.pi-1e-9, math.pi+1e-9)


def field(x=1, y=0, *, grid=None, wavelength=633e-9):
    if grid is None:
        grid = SamplingGrid(ny=3, nx=4, dy=4.1e-6, dx=3.7e-6)
    values = []
    for data in (x, y):
        data = np.asarray(data, dtype=np.complex128)
        if data.ndim == 0:
            data = np.full(grid.shape, data, dtype=np.complex128)
        values.append(ComplexField(data=data, grid=grid, wavelength_m=wavelength))
    return JonesField(x=values[0], y=values[1])


def spec(*, actions_0=(), actions_1=(), z0=0., z1=0., phase=.37):
    return PolarizedTwoArmSpec(arm_0=PolarizationArm(distance_m=z0, actions=actions_0),
        arm_1=PolarizationArm(distance_m=z1, actions=actions_1), relative_phase_rad=phase)


def arrays(field):
    return np.stack((field.x.data, field.y.data))


def assert_outputs(actual, expected, amplitude, *, tolerance=2e-14):
    for output, target in zip(actual, expected):
        np.testing.assert_allclose(arrays(output), target, rtol=tolerance,
                                   atol=tolerance*amplitude)


def hand_outputs(a, v, phase):
    factor = cmath.exp(1j*phase)
    return ((a+factor*v)/2, 1j*(factor*v-a)/2)


def asymmetric(ny, nx):
    # Fixed independently specified component amplitudes, no RNG or grid helper.
    row, col = np.indices((ny, nx))
    x = (1+.13*row-.07*col) + 1j*(.2+.03*col+.11*row)
    y = (-.31+.09*col-.04*row) + 1j*(.43-.12*col+.07*row)
    return np.stack((x, y)).astype(np.complex128)


@pytest.mark.parametrize("phase", PHASES)
@pytest.mark.parametrize("component", ["x", "y"])
def test_identical_polarization_complete_complex_fixed_sweep(component, phase):
    data = asymmetric(3, 4)[0]
    source = field(data if component == "x" else 0, data if component == "y" else 0)
    result = run_polarized_two_arm(source, spec=spec(phase=phase))
    expected = hand_outputs(arrays(source), arrays(source), phase)
    assert_outputs(result.outputs, expected, float(np.max(np.abs(data))))
    np.testing.assert_allclose(result.norms.output_fractions,
        (math.cos(phase/2)**2, math.sin(phase/2)**2), rtol=2e-13, atol=2e-13)
    assert result.norms.total_output_ratio == pytest.approx(1, rel=2e-13, abs=2e-13)


@pytest.mark.parametrize("component", ["x", "y"])
def test_pure_y_reduction_to_scalar(component):
    data = asymmetric(5, 6)[0]
    source = field(data if component == "x" else 0, data if component == "y" else 0,
                   grid=SamplingGrid(ny=5, nx=6, dy=4.1e-6, dx=3.7e-6))
    request = spec(z0=.002731, z1=.004123, phase=-.83)
    actual = run_polarized_two_arm(source, spec=request)
    scalar_result = run_two_arm(getattr(source, component), spec=TwoArmSpec(
        arm_0_distance_m=.002731, arm_1_distance_m=.004123, relative_phase_rad=-.83))
    scale = float(np.max(np.abs(data)))
    for output, scalar in zip(actual.outputs, scalar_result.outputs):
        np.testing.assert_allclose(getattr(output, component).data, scalar.data,
                                   rtol=2e-14, atol=2e-14*scale)
        assert not np.count_nonzero(getattr(output, "y" if component == "x" else "x").data)
    np.testing.assert_allclose(actual.norms.outputs, scalar_result.norms.outputs,
        rtol=2e-13, atol=2e-13*actual.norms.inputs_total)


@pytest.mark.parametrize("phase", PHASES)
def test_orthogonal_arms_analyzers_are_separate(phase):
    source = field()
    request = spec(actions_1=(RetarderAction(axis_angle_rad=math.pi/4,
                                            retardance_rad=math.pi),), phase=phase)
    result = run_polarized_two_arm(source, spec=request)
    a = np.stack((np.ones(source.shape), np.zeros(source.shape)))
    v = np.stack((np.zeros(source.shape), np.ones(source.shape)))
    assert_outputs(result.outputs, hand_outputs(a, v, phase), 1)
    np.testing.assert_allclose(result.norms.output_fractions, (.5, .5), rtol=2e-13, atol=2e-13)
    before = tuple(part.data.tobytes() for out in result.outputs for part in (out.x, out.y))
    analyzed = tuple(apply_linear_polarizer(out, axis_angle_rad=math.pi/4) for out in result.outputs)
    measured = tuple(out.sampled_norm/source.sampled_norm for out in analyzed)
    expected = ((1+math.cos(phase))/4, (1-math.cos(phase))/4)
    np.testing.assert_allclose(measured, expected, rtol=2e-13, atol=2e-13)
    np.testing.assert_allclose(sum(measured), .5, rtol=2e-13, atol=2e-13)
    removed = tuple(raw.sampled_norm-post.sampled_norm for raw, post in zip(result.outputs, analyzed))
    np.testing.assert_allclose(sum(removed), .5*source.sampled_norm,
                               rtol=2e-13, atol=2e-13*source.sampled_norm)
    np.testing.assert_allclose([transmission_ratio(raw, post) for raw, post in zip(result.outputs, analyzed)],
                               [2*value for value in expected], rtol=2e-13, atol=2e-13)
    assert before == tuple(part.data.tobytes() for out in result.outputs for part in (out.x, out.y))


@pytest.mark.parametrize("phase", EXTRA_PHASES)
def test_complex_overlap_full_field_and_argument(phase):
    source = field()
    result = run_polarized_two_arm(source, spec=spec(actions_1=(
        RetarderAction(axis_angle_rad=math.pi/4, retardance_rad=math.pi/2),), phase=phase))
    a = np.stack((np.ones(source.shape), np.zeros(source.shape)))
    v = np.stack((np.full(source.shape, (1+1j)/2), np.full(source.shape, (1-1j)/2)))
    assert_outputs(result.outputs, hand_outputs(a, v, phase), 1)
    gamma = (1+1j)/2
    overlap_term = (cmath.exp(1j*phase)*gamma).real
    np.testing.assert_allclose(result.norms.output_fractions,
        ((1+overlap_term)/2, (1-overlap_term)/2), rtol=2e-13, atol=2e-13)


def test_complex_first_arm_overlap_hand_anchor():
    """Complex j0 makes missing conjugation reverse the measured 3/4,1/4."""
    q = 1/math.sqrt(2)
    source = field(q, q)
    result = run_polarized_two_arm(source, spec=spec(actions_0=(
        RetarderAction(axis_angle_rad=0, retardance_rad=math.pi/2),), phase=math.pi/2))
    j0 = np.array([q, 1j*q], dtype=np.complex128)
    j1 = np.array([q, q], dtype=np.complex128)
    gamma = np.conj(j0[0])*j1[0]+np.conj(j0[1])*j1[1]
    np.testing.assert_allclose(gamma, (1-1j)/2, rtol=0, atol=2e-15)
    a = np.broadcast_to(j0[:, None, None], (2, *source.shape))
    v = np.broadcast_to(j1[:, None, None], (2, *source.shape))
    assert_outputs(result.outputs, hand_outputs(a, v, math.pi/2), q)
    np.testing.assert_allclose(result.norms.output_fractions, (.75, .25), rtol=2e-13, atol=2e-13)
    wrong_gamma = j0[0]*j1[0]+j0[1]*j1[1]
    wrong_port0 = (1+(1j*wrong_gamma).real)/2
    assert abs(result.norms.output_fractions[0]-wrong_port0) > .49


@pytest.mark.parametrize("phase", EXTRA_PHASES)
def test_orthogonal_circular_arms_explicit_components(phase):
    q = 1/math.sqrt(2)
    source = field(q, q)
    result = run_polarized_two_arm(source, spec=spec(
        actions_0=(RetarderAction(axis_angle_rad=0, retardance_rad=math.pi/2),),
        actions_1=(RetarderAction(axis_angle_rad=0, retardance_rad=-math.pi/2),), phase=phase))
    a = np.broadcast_to(np.array([q, 1j*q])[:, None, None], (2, *source.shape))
    v = np.broadcast_to(np.array([q, -1j*q])[:, None, None], (2, *source.shape))
    assert_outputs(result.outputs, hand_outputs(a, v, phase), q)
    np.testing.assert_allclose(result.norms.output_fractions, (.5, .5), rtol=2e-13, atol=2e-13)


@pytest.mark.parametrize("phase", EXTRA_PHASES)
def test_lossy_arm_original_input_budget(phase):
    source = field()
    result = run_polarized_two_arm(source, spec=spec(actions_1=(
        PolarizerAction(axis_angle_rad=math.pi/3),), phase=phase))
    a = np.stack((np.ones(source.shape), np.zeros(source.shape)))
    v = np.stack((np.full(source.shape, .25), np.full(source.shape, math.sqrt(3)/4)))
    assert_outputs(result.outputs, hand_outputs(a, v, phase), 1)
    np.testing.assert_allclose(result.norms.output_fractions,
        (5/16+math.cos(phase)/8, 5/16-math.cos(phase)/8), rtol=2e-13, atol=2e-13)
    np.testing.assert_allclose(result.norms.total_output_ratio, 5/8, rtol=2e-13, atol=2e-13)
    np.testing.assert_allclose(result.norms.element_deltas, (0, -3/8*source.sampled_norm),
                               rtol=2e-13, atol=2e-13*source.sampled_norm)
    np.testing.assert_allclose(result.norms.total_delta, -3/8*source.sampled_norm,
                               rtol=2e-13, atol=2e-13*source.sampled_norm)


def test_terminal_action_order_is_noncommuting():
    source = field()
    p = PolarizerAction(axis_angle_rad=0)
    w = RetarderAction(axis_angle_rad=math.pi/4, retardance_rad=math.pi/2)
    a = np.stack((np.ones(source.shape), np.zeros(source.shape)))
    p_then_w = np.stack((np.full(source.shape, (1+1j)/2), np.full(source.shape, (1-1j)/2)))
    w_then_p = np.stack((np.full(source.shape, (1+1j)/2), np.zeros(source.shape)))
    first = run_polarized_two_arm(source, spec=spec(actions_1=(p, w)))
    second = run_polarized_two_arm(source, spec=spec(actions_1=(w, p)))
    assert_outputs(first.outputs, hand_outputs(a, p_then_w, .37), 1)
    assert_outputs(second.outputs, hand_outputs(a, w_then_p, .37), 1)
    assert max(np.max(np.abs(arrays(x)-arrays(y))) for x, y in zip(first.outputs, second.outputs)) > .3
    np.testing.assert_allclose(first.norms.total_output_ratio, 1, rtol=2e-13, atol=2e-13)
    np.testing.assert_allclose(second.norms.total_output_ratio, .75, rtol=2e-13, atol=2e-13)


@pytest.mark.parametrize("phase", [0., math.pi/2, .37, -.83])
def test_common_retarder_phase_is_not_removed(phase):
    source = field()
    result = run_polarized_two_arm(source, spec=spec(actions_1=(
        RetarderAction(axis_angle_rad=math.pi/2, retardance_rad=math.pi),), phase=phase))
    a = arrays(source)
    assert_outputs(result.outputs, hand_outputs(a, -a, phase), 1)
    np.testing.assert_allclose(result.norms.output_fractions,
        (math.sin(phase/2)**2, math.cos(phase/2)**2), rtol=2e-13, atol=2e-13)


@pytest.mark.parametrize("ny,nx", [(3, 4), (5, 6), (6, 5)])
def test_complete_independent_direct_sums(ny, nx):
    data = asymmetric(ny, nx)
    grid = SamplingGrid(ny=ny, nx=nx, dy=4.1e-6, dx=3.7e-6)
    source = field(*data, grid=grid)
    literal_0 = (("polarizer", .31), ("retarder", -.47, .83))
    literal_1 = (("retarder", .61, -1.13), ("polarizer", -.29))
    expected = reference.direct_path(data, .002731, .004123, literal_0, literal_1, .37,
                                    dy=grid.dy, dx=grid.dx, wavelength=633e-9)
    request = spec(z0=.002731, z1=.004123, phase=.37,
        actions_0=(PolarizerAction(axis_angle_rad=.31),
                   RetarderAction(axis_angle_rad=-.47, retardance_rad=.83)),
        actions_1=(RetarderAction(axis_angle_rad=.61, retardance_rad=-1.13),
                   PolarizerAction(axis_angle_rad=-.29)))
    actual = run_polarized_two_arm(source, spec=request)
    amplitude = float(np.max(np.abs(data)))
    assert_outputs(actual.outputs, expected, amplitude, tolerance=1e-11)
    # Independent loop squares and fsum; not the production Jones reduction.
    expected_norms = []
    for output in expected:
        terms = [abs(complex(output[0, i, j]))**2+abs(complex(output[1, i, j]))**2
                 for i in range(ny) for j in range(nx)]
        expected_norms.append(math.fsum(terms)*grid.dx*grid.dy)
    np.testing.assert_allclose(actual.norms.outputs, expected_norms, rtol=2e-13,
                               atol=2e-13*source.sampled_norm)


@pytest.mark.parametrize("phase", [0., .37])
def test_unequal_arm_carrier_is_present_once(phase):
    wavelength = 633e-9
    source = field(1, .3j)
    z0, z1 = wavelength/7, wavelength/7+wavelength/6
    k = 2*math.pi/wavelength
    expected = hand_outputs(arrays(source)*cmath.exp(1j*k*z0),
                            arrays(source)*cmath.exp(1j*k*z1), phase)
    result = run_polarized_two_arm(source, spec=spec(z0=z0, z1=z1, phase=phase))
    assert_outputs(result.outputs, expected, 1)
    np.testing.assert_allclose(result.norms.output_fractions,
        (math.cos((k*(z1-z0)+phase)/2)**2, math.sin((k*(z1-z0)+phase)/2)**2),
        rtol=2e-13, atol=2e-13)
    if phase == 0:
        np.testing.assert_allclose(result.norms.output_fractions, (.75, .25), rtol=2e-13, atol=2e-13)


@pytest.mark.parametrize("phase", WEAK_PHASES)
def test_near_dark_fractions_actual_binary64_decimal_reference(phase):
    source = field(1, .3j)
    result = run_polarized_two_arm(source, spec=spec(phase=phase))
    # The bounded Decimal series consumes the exact float, never a rounded pi
    # or epsilon-squared replacement. Half-angle avoids cosine cancellation.
    sine, cosine = reference.decimal_sincos(phase/2)
    with localcontext() as context:
        context.prec = 80
        expected = (float(cosine*cosine), float(sine*sine))
    dark_port = 1 if abs(phase) < .001 else 0
    observed = result.norms.output_fractions[dark_port]
    assert expected[dark_port] > 0 and observed > 0
    np.testing.assert_allclose(observed, expected[dark_port], rtol=2e-13, atol=1e-40)
    np.testing.assert_allclose(result.norms.outputs[dark_port],
        expected[dark_port]*source.sampled_norm, rtol=2e-13, atol=1e-40*source.sampled_norm)
    amplitude = float(np.max(np.abs(arrays(source))))
    assert_outputs(result.outputs, hand_outputs(arrays(source), arrays(source), phase), amplitude)
    assert float(np.max(np.abs(arrays(result.outputs[dark_port])))) > 1e-10


def test_fixed_sweep_has_seventeen_distinct_binary64_phases_and_unforced_endpoint():
    assert len(PHASES) == 17 and len(set(PHASES)) == 17
    assert PHASES[0] == 0 and PHASES[-1] == 2*math.pi
    start = run_polarized_two_arm(field(), spec=spec(phase=PHASES[0]))
    end = run_polarized_two_arm(field(), spec=spec(phase=PHASES[-1]))
    assert start.norms.outputs[1] == 0
    assert end.norms.outputs[1] > 0


def test_common_global_phase_covariance_preserves_complete_complex_fields():
    data = asymmetric(3, 4)
    source = field(*data)
    request = spec(z0=.002, z1=.003, actions_1=(
        RetarderAction(axis_angle_rad=.61, retardance_rad=.83),), phase=-.37)
    base = run_polarized_two_arm(source, spec=request)
    q = cmath.exp(.67j)
    changed = run_polarized_two_arm(field(*(q*data)), spec=request)
    assert_outputs(changed.outputs, tuple(q*arrays(out) for out in base.outputs),
                   float(np.max(np.abs(data))))
    for first, second in zip(base.outputs, changed.outputs):
        np.testing.assert_allclose(first.intensity, second.intensity,
            rtol=2e-13, atol=2e-13*float(np.max(np.abs(data)))**2)


def test_inherited_evanescent_loss_is_not_normalized():
    row, col = np.indices((4, 5))
    data = 1+.3*np.exp(2j*math.pi*(2*col/5+row/4))
    grid = SamplingGrid(ny=4, nx=5, dy=.22e-6, dx=.2e-6)
    source = field(data, .4j*data, grid=grid)
    expected = reference.direct_path(arrays(source), 80e-9, 130e-9, (), (), .37,
                                    dy=grid.dy, dx=grid.dx, wavelength=633e-9)
    result = run_polarized_two_arm(source, spec=spec(z0=80e-9, z1=130e-9))
    assert_outputs(result.outputs, expected, float(np.max(np.abs(data))), tolerance=1e-11)
    assert result.norms.total_output_ratio < .99
    assert result.norms.propagation_delta < 0
    np.testing.assert_allclose(result.norms.recombination_delta, 0, rtol=0,
                               atol=2e-13*source.sampled_norm)


def test_exact_dark_input_all_checkpoints_and_actions():
    result = run_polarized_two_arm(field(0, 0), spec=spec(z0=.002, z1=.003,
        actions_0=(PolarizerAction(axis_angle_rad=.37),),
        actions_1=(RetarderAction(axis_angle_rad=.61, retardance_rad=.83),)))
    for name in ("inputs", "split", "propagated", "elements", "combiner", "outputs"):
        assert getattr(result.norms, name) == (0., 0.)
    assert result.norms.arm_action_norms == ((0.,), (0.,))
    assert result.norms.output_fractions == (None, None)
    assert result.norms.total_output_ratio is None
    assert all(not np.count_nonzero(arrays(out)) for out in result.outputs)
