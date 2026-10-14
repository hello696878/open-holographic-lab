"""Independent literal Jones/finite-sum and inherited weak-signal assertions."""

import cmath
from decimal import localcontext
import math

import numpy as np
import pytest

from apps.virtual_bench import polarized_two_path_adapter as adapter
from scripts.validate_v2f_interference import direct_path, literal_action, decimal_sincos
from test_virtual_bench_polarized_two_path_adapter import envelope, output, polarizer, retarder


def action_tuples(actions):
    return tuple(("polarizer",a["axis_angle_rad"]) if a["kind"]=="linear_polarizer" else
        ("retarder",a["axis_angle_rad"],a["retardance_rad"]) for a in actions)


@pytest.mark.parametrize("shape",[(3,4),(5,6),(6,5)])
@pytest.mark.parametrize("phase",[.37,-.83,2.41])
def test_complete_independent_finite_sum_complex_result_and_analyzer_projection(shape,phase,monkeypatch):
    value=envelope(ny=shape[0],nx=shape[1],gaussian=True,phase=phase,
        actions_0=[retarder("a",-.19,2.13),polarizer("b",.41)],
        actions_1=[polarizer("c",-.27),retarder("d",.31,-1.17)])
    original=adapter.run_polarized_two_arm; seen=[]
    def run(incident,*,spec):
        result=original(incident,spec=spec); seen.append((incident,result)); return result
    monkeypatch.setattr(adapter,"run_polarized_two_arm",run)
    header,arrays=output(value)
    incident,result=seen[0]
    input_array=np.stack((incident.x.data,incident.y.data))
    spec=value["experiment"]
    expected=direct_path(input_array,spec["arm_0"]["distance_m"],spec["arm_1"]["distance_m"],
        action_tuples(spec["arm_0"]["actions"]),action_tuples(spec["arm_1"]["actions"]),phase,
        dy=spec["grid"]["dy"],dx=spec["grid"]["dx"],wavelength=spec["wavelength_m"])
    amplitude=float(np.abs(input_array).max())
    analyzer=literal_action(("polarizer",spec["analyzer"]["axis_angle_rad"]))
    for index,(field,reference) in enumerate(zip(result.outputs,expected)):
        actual=np.stack((field.x.data,field.y.data))
        np.testing.assert_allclose(actual,reference,rtol=1e-11,atol=1e-11*amplitude,
                                   err_msg="V2G_DIRECT_SUM_COMPLEX_DETECTED")
        analyzed=np.einsum("ab,bij->aij",analyzer,reference)
        reference_intensity=np.sum(np.abs(analyzed)**2,axis=0)
        np.testing.assert_allclose(arrays[f"analyzed_port_{index}_intensity"],reference_intensity,
            rtol=1e-11,atol=1e-11*amplitude**2,err_msg="V2G_ANALYZER_PROJECTION_DETECTED")
    assert header["analysis"]["total_removed_norm"]>0


@pytest.mark.parametrize("phase",[0,.37,math.pi/2,math.pi,2*math.pi])
def test_identical_arms_analytic_original_input_fractions(phase):
    header,arrays=output(envelope(enabled=False,phase=phase,distances=(0,0),
        coefficients={"x":{"re":1.,"im":0.},"y":{"re":0.,"im":0.}}))
    expected=((1+math.cos(phase))/2,(1-math.cos(phase))/2)
    np.testing.assert_allclose(header["diagnostics"]["output_fractions"],expected,rtol=2e-13,atol=2e-13,
                               err_msg="V2G_COMMON_PHASE_DETECTED")
    for name in ("raw_port_0_intensity","raw_port_1_intensity"):
        assert np.ptp(arrays[name])==0,"V2G_NO_FAKE_FRINGES_DETECTED"


@pytest.mark.parametrize("phase",[0,.37,math.pi/2,math.pi,2*math.pi])
def test_orthogonal_arms_separate_analyzers_retain_projection_loss(phase):
    header,_=output(envelope(phase=phase,angle=math.pi/4,distances=(0,0),
        coefficients={"x":{"re":1.,"im":0.},"y":{"re":0.,"im":0.}},
        actions_1=[retarder("hwp",math.pi/4,math.pi)]))
    np.testing.assert_allclose(header["diagnostics"]["output_fractions"],(.5,.5),rtol=2e-13,atol=2e-13,
                               err_msg="V2G_RAW_ORTHOGONAL_DETECTED")
    expected=((1+math.cos(phase))/4,(1-math.cos(phase))/4)
    np.testing.assert_allclose([p["original_input_ratio"] for p in header["analysis"]["ports"]],expected,
                               rtol=2e-13,atol=2e-13,err_msg="V2G_ANALYZER_LOSS_DETECTED")
    np.testing.assert_allclose(header["analysis"]["total_original_input_ratio"],.5,rtol=2e-13,atol=2e-13,
                               err_msg="V2G_ANALYZER_LOSS_DETECTED")


def test_complex_first_arm_overlap_anchor_conjugation_sign_and_common_retarder_phase(monkeypatch):
    value=envelope(enabled=False,phase=math.pi/2,distances=(0,0),
        coefficients={"x":{"re":1.,"im":0.},"y":{"re":0.,"im":0.}},
        actions_0=[retarder("half",math.pi/8,math.pi),retarder("quarter",0.,math.pi/2)],
        actions_1=[retarder("half_other",math.pi/8,math.pi)])
    seen=[]; original=adapter.run_polarized_two_arm
    def run(incident,*,spec):
        result=original(incident,spec=spec); seen.append((incident,result)); return result
    monkeypatch.setattr(adapter,"run_polarized_two_arm",run)
    header,_=output(value)
    a=literal_action(("retarder",0.,math.pi/2))@literal_action(("retarder",math.pi/8,math.pi))@np.array([1,0])
    v=literal_action(("retarder",math.pi/8,math.pi))@np.array([1,0],dtype=np.complex128)
    gamma=np.vdot(a,v)
    np.testing.assert_allclose(gamma,(1-1j)/2,rtol=0,atol=2e-15)
    np.testing.assert_allclose(header["diagnostics"]["output_fractions"],(.75,.25),rtol=2e-13,atol=2e-13,
                               err_msg="V2G_COMPLEX_FIRST_PHASE_DETECTED")
    incident,result=seen[0]
    for field,vector in zip(result.outputs,((a+1j*v)/2,1j*(1j*v-a)/2)):
        actual=np.stack((field.x.data,field.y.data))
        expected=vector[:,None,None]*incident.x.data[None,:,:]
        np.testing.assert_allclose(actual,expected,rtol=2e-14,atol=2e-14,
                                   err_msg="V2G_RETARDER_COMMON_PHASE_DETECTED")


def test_noncommuting_action_order_changes_complete_measurement():
    first=envelope(gaussian=True,actions_0=[retarder("w",.21,1.31),polarizer("p",-.27)])
    second=envelope(gaussian=True,actions_0=[polarizer("p",-.27),retarder("w",.21,1.31)])
    h0,a0=output(first);h1,a1=output(second)
    assert not np.allclose(a0["raw_port_0_intensity"],a1["raw_port_0_intensity"],rtol=2e-13,atol=2e-13),"V2G_ACTION_ORDER_DETECTED"
    assert h0["experiment_sha256"]!=h1["experiment_sha256"]
    assert h0["norms"]["arm_action_norms"][0]!=h1["norms"]["arm_action_norms"][0]


@pytest.mark.parametrize("phase",[-1e-4,1e-4,-1e-7,1e-7,-1e-9,1e-9,
    math.pi-1e-4,math.pi+1e-4,math.pi-1e-7,math.pi+1e-7,math.pi-1e-9,math.pi+1e-9])
def test_selected_near_dark_original_binary64_reference_no_component_deletion(phase):
    # Exact committed V2f validator fixture: 2x3 real uniform (1,0), phase0,
    # zero arm distances/actions. A different global complex phase changes the
    # cancellation conditioning and is not this declared relative-error claim.
    value=envelope(ny=2,nx=3,enabled=False,phase=phase,distances=(0,0),
        coefficients={"x":{"re":1.,"im":0.},"y":{"re":0.,"im":0.}})
    value["experiment"]["source"]["phase_rad"]=0.0
    header,_=output(value)
    sine,cosine=decimal_sincos(phase)
    with localcontext() as context:
        context.prec=80
        if abs(phase)<1:
            expected=float(((1-cosine)**2+sine*sine)/4);actual=header["diagnostics"]["output_fractions"][1]
        else:
            expected=float(((1+cosine)**2+sine*sine)/4);actual=header["diagnostics"]["output_fractions"][0]
    assert actual>0,"V2G_WEAK_SIGNAL_DETECTED"
    np.testing.assert_allclose(actual,expected,rtol=2e-13,atol=1e-40,err_msg="V2G_WEAK_SIGNAL_DETECTED")


def test_lossy_arm_is_not_normalized_and_carrier_applied_once():
    header,_=output(envelope(enabled=False,phase=.37,distances=(0,0),
        coefficients={"x":{"re":1.,"im":0.},"y":{"re":0.,"im":0.}},
        actions_1=[polarizer("loss",math.pi/3)]))
    np.testing.assert_allclose(header["diagnostics"]["total_output_ratio"],5/8,rtol=2e-13,atol=2e-13,
                               err_msg="V2G_ARM_LOSS_DETECTED")
    assert header["diagnostics"]["elements_delta"]<0
    distance=(633e-9/8)
    h,_=output(envelope(enabled=False,phase=0,distances=(0,distance),
        coefficients={"x":{"re":1.,"im":0.},"y":{"re":0.,"im":0.}}))
    expected=((1+math.cos(math.pi/4))/2,(1-math.cos(math.pi/4))/2)
    np.testing.assert_allclose(h["diagnostics"]["output_fractions"],expected,rtol=2e-13,atol=2e-13,
                               err_msg="V2G_CARRIER_ONCE_DETECTED")
