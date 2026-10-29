"""Pure signed amplitudes, stable weak signals, raw coherency and support gates."""
from dataclasses import FrozenInstanceError
import math

import pytest

from ohlab.optics.geometric_routing import CertifiedInterval,certify_vector,NumericalAmbiguityError
from ohlab.optics.fresnel_interface import (
    RayPowerState,TransverseFrame,UnsupportedPolarizationNumericsError,checked_positive_product,
    checked_amplitude_power,fresnel_coefficients,polarization_diagnostics,source_frame,source_power_state,
)
from scripts.validate_w4_fresnel_routing import decimal_coefficients,weak_fixtures


def test_normal_electric_signs_and_flux_conversion_are_not_power_weights():
    op=fresnel_coefficients(certify_vector((0.,0.,1.)),certify_vector((0.,0.,-1.)),1.,1.5)
    assert op.r_s.real==pytest.approx(-.2,rel=2e-12,abs=2e-14)
    assert op.r_p.real==pytest.approx(.2,rel=2e-12,abs=2e-14)
    assert op.t_s.real==pytest.approx(.8,rel=2e-12,abs=2e-14)
    assert op.flux_factor==1.5
    assert op.channel_powers==pytest.approx((.04,.04,.96,.96),rel=2e-12,abs=2e-14)
    assert abs(op.t_s)**2==pytest.approx(.64)
    assert abs(abs(op.t_s)**2-.96)>.3  # detects a missing n*cos factor


@pytest.mark.parametrize("name,d",weak_fixtures())
def test_all_seven_weak_signed_amplitudes_and_positive_powers_have_zero_absolute_tolerance(name,d):
    ref=decimal_coefficients(d,[0.,0.,-1.],1.,1.5)
    op=fresnel_coefficients(certify_vector(tuple(d)),certify_vector((0.,0.,-1.)),1.,1.5)
    assert op.r_p.real==pytest.approx(float(ref["rp"]),rel=2e-11,abs=0.)
    assert op.r_p.real!=0 and abs(op.r_p)**2>0
    assert abs(op.r_p)**2==pytest.approx(float(ref["Rp"]),rel=2e-11,abs=0.)
    assert op.bounds[1].real.lo<=float(ref["rp"])<=op.bounds[1].real.hi


@pytest.mark.parametrize("polarization,C",[("unpolarized",(.5,.5,0.,0.)),("linear_e1",(1.,0.,0.,0.)),
    ("linear_e2",(0.,1.,0.,0.)),("linear_45",(.5,.5,.5,0.))])
def test_exact_source_presets_owned_hermitian_power_and_derived_normalization(polarization,C):
    state=source_power_state(certify_vector((0.,0.,1.)),"exterior",1.,polarization)
    assert state.C==C and state.power_fraction==1.
    wire=state.to_dict();wire["C"][0]=900;wire["frame"]["e1"][0]=900
    assert state.C==C and state.frame.e1.nominal==(1.,0.,0.)
    with pytest.raises(FrozenInstanceError):state.C=(1.,1.,0.,0.)
    diagnostic=polarization_diagnostics(state.C)
    assert diagnostic["normalized_stokes"][0]==1.
    assert diagnostic["degree_of_polarization"]==pytest.approx(0. if polarization=="unpolarized" else 1.)


def test_circular_stokes_sign_dark_nulls_and_raw_no_clamping():
    state=RayPowerState(certify_vector((0.,0.,1.)),"exterior",1.,source_frame(),(.5,.5,0.,-.5))
    assert polarization_diagnostics(state.C)["stokes"]==[1.,0.,0.,1.]
    dark=polarization_diagnostics((0.,0.,0.,0.))
    assert dark["normalized_stokes"] is None and dark["degree_of_polarization"] is None
    # The diagnostic returns raw values; it is not a public-input PSD repair.
    assert polarization_diagnostics((.5,.5,.5000000000000001,0.))["degree_of_polarization"]>1.


@pytest.mark.parametrize("C",[(-1e-30,1e-30,0.,0.),(.5,.5,.6,0.),(.5,.5,float("nan"),0.)])
def test_invalid_physical_input_is_not_projected_or_symmetrized(C):
    with pytest.raises((ValueError,UnsupportedPolarizationNumericsError)):
        RayPowerState(certify_vector((0.,0.,1.)),"exterior",1.,source_frame(),C)


def test_public_boolean_cannot_replace_congruence_owner_proof():
    with pytest.raises(ValueError,match="positive semidefinite"):
        RayPowerState(certify_vector((0.,0.,1.)),"exterior",1.,source_frame(),(.5,.5,.5000000000000001,0.),_congruence_proof=True)


@pytest.mark.parametrize("a,b,good",[(1.,1e-33,True),(1e-290,1e-33,False),(1e-300,1e-33,False),(5e-324,1.,True)])
def test_frozen_positive_product_gate_distinguishes_subnormals_and_underflow(a,b,good):
    if good:assert checked_positive_product(a,b)==a*b
    else:
        with pytest.raises(UnsupportedPolarizationNumericsError,match="reliably binary64"):
            checked_positive_product(a,b)


@pytest.mark.parametrize("offset",[-1,0,1])
def test_critical_neighborhood_remains_numerically_ambiguous(offset):
    angle=math.asin(1/1.5)
    if offset:angle=math.nextafter(angle,0. if offset<0 else math.inf)
    d=(math.sin(angle),0.,math.cos(angle));eps=4*2.220446049250313e-16
    vector=certify_vector(d,tuple(CertifiedInterval(x-eps,x+eps) for x in d))
    with pytest.raises(NumericalAmbiguityError,match="critical zero"):
        fresnel_coefficients(vector,certify_vector((0.,0.,-1.)),1.5,1.)


def test_equal_index_exact_zero_and_identity_coefficients_are_structural():
    d=certify_vector((.5,0.,math.sqrt(.75)))
    op=fresnel_coefficients(d,certify_vector((0.,0.,-1.)),1.5,1.5)
    assert op.exact_reflection_zero and op.r_s==op.r_p==0j
    assert op.t_s==op.t_p==op.tau_s==op.tau_p==1+0j


@pytest.mark.parametrize("amplitude,good",[(complex(1e-100),True),(complex(1e-170),False),(complex(0.,1e-170),False),(0j,True)])
def test_positive_coefficient_power_cannot_silently_underflow_before_state_product(amplitude,good):
    if good:assert checked_amplitude_power(amplitude)>=0
    else:
        with pytest.raises(UnsupportedPolarizationNumericsError,match="reliably"):
            checked_amplitude_power(amplitude)


@pytest.mark.parametrize("geometry",[True,{},object()])
def test_coefficient_geometry_type_rejected_explicitly(geometry):
    with pytest.raises(TypeError,match="CertifiedDielectricDirections"):
        fresnel_coefficients(certify_vector((0.,0.,1.)),certify_vector((0.,0.,-1.)),1.,1.5,geometry=geometry)
