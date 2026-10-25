"""Independent Decimal references, scalar identities, reciprocity and criticality."""
from copy import deepcopy
from decimal import Decimal, localcontext
import math

import pytest

from ohlab.optics import refractive_routing as routing
from ohlab.optics.geometric_routing import CertifiedInterval, certify_vector
from scripts.validate_w3_refractive_routing import compare_case, decimal_trace, fixtures, operator_stress, slab_displacement_reference


@pytest.mark.parametrize("name",list(fixtures()))
def test_independent_Decimal_finite_body_reference_and_every_component_enclosed(name):
    try:
        report=compare_case(name,fixtures()[name])
    except (routing.NumericalAmbiguityError,routing.UnsupportedNumericalInputError,routing.MediumStateAmbiguityError) as exc:
        pytest.fail(f"independently specified supported fixture {name} was numerically rejected: {exc}")
    assert report["all_reference_components_enclosed"]
    assert report["max_position_error_m"]<=5e-12
    assert report["max_direction_error"]<=2e-12
    assert report["max_scalar_angle_error_rad"]<=2e-12


def test_parallel_slab_displacement_separates_exact_stored_and_ideal_angle_targets():
    report=slab_displacement_reference()
    assert report["measured_perpendicular_displacement_m"]==pytest.approx(.005814413464563081,rel=2e-12,abs=5e-12)
    assert Decimal(report["exact_stored_input_reference_m"])!=Decimal(report["ideal_real_30deg_exact_0.03m_reference_m"])


@pytest.mark.parametrize("name",["A_slab","B_prism","B_index1.3","B_yaw10","C_TIR","D_multiple_returns"])
def test_reverse_route_reciprocity_with_original_geometry_and_real_return_faces(name):
    raw=fixtures()[name]; raw["elements"]=[]
    forward=routing.trace_routes(routing.validate_scene(raw))
    last=forward.events[-1]; outgoing=last["outgoing"][0]["direction"]
    reverse=deepcopy(raw)
    reverse["source"]["origin_m"]=[p+.02*d for p,d in zip(last["position_m"],outgoing)]
    reverse["source"]["direction"]=[-d for d in outgoing]
    actual=routing.trace_routes(routing.validate_scene(reverse))
    assert [x["target"]["face_id"] for x in actual.events]==list(reversed([x["target"]["face_id"] for x in forward.events]))
    for event,original in zip(actual.events,reversed(forward.events)):
        assert event["position_m"]==pytest.approx(original["position_m"],rel=2e-12,abs=5e-12)
        assert event["outgoing"][0]["direction"]==pytest.approx(tuple(-x for x in original["incident_direction"]),rel=2e-12,abs=2e-12)
        assert event["incident_medium_id"]==original["outgoing"][0]["medium_id"]
        assert event["outgoing"][0]["medium_id"]==original["incident_medium_id"]


@pytest.mark.parametrize("delta,expected",[(-1e-6,"refraction"),(1e-6,"total_internal_reflection")])
def test_critical_sides_use_certified_K_sign(delta,expected):
    angle=math.asin(1/1.5)+delta
    d=certify_vector((math.sin(angle),0.,math.cos(angle)))
    result=routing._dielectric_direction(d,certify_vector((0.,0.,-1.)),1.5,1.,True)
    assert result[1]==expected
    assert result[2].lo>0 if expected=="refraction" else result[2].hi<0


@pytest.mark.parametrize("angle",[math.asin(1/1.5),math.nextafter(math.asin(1/1.5),0.),math.nextafter(math.asin(1/1.5),math.inf)])
def test_critical_and_adjacent_stored_angles_are_ambiguous_not_forced_transmission(angle):
    with pytest.raises(routing.NumericalAmbiguityError,match="critical"):
        routing._dielectric_direction(certify_vector((math.sin(angle),0.,math.cos(angle))),certify_vector((0.,0.,-1.)),1.5,1.,True)


def test_equal_index_nongrazing_identity_uses_proven_positive_K_without_cancellation():
    d=certify_vector((1.,0.,1e-8))
    out,kind,k,_,_=routing._dielectric_direction(d,certify_vector((0.,0.,-1.)),1.,1.,True)
    assert out is d and out.bounds is d.bounds
    assert kind=="refraction" and k.lo>0
    assert k.lo<=1e-16<=k.hi
    ambiguous=certify_vector((1.,0.,1e-8),(CertifiedInterval.point(1.),CertifiedInterval.point(0.),CertifiedInterval(-1e-8,2e-8)))
    with pytest.raises(routing.MediumStateAmbiguityError):
        routing._dielectric_direction(ambiguous,certify_vector((0.,0.,-1.)),1.,1.,True)


def test_admitted_nonunit_direction_and_scaled_covector_preserve_norm_without_repair():
    epsilon=2.220446049250313e-16
    d=tuple(x*(1+4*epsilon) for x in (.49999999999999994,0.,.8660254037844387))
    out,_,_,_,_=routing._dielectric_direction(certify_vector(d),certify_vector((0.,0.,-3.)),1.,1.5,True)
    assert math.hypot(*out.nominal)!=1.
    assert math.hypot(*out.nominal)==pytest.approx(math.hypot(*d),rel=0.,abs=8e-16)
    with localcontext() as ctx:
        ctx.prec=90
        expected_x=Decimal.from_float(d[0])/Decimal.from_float(1.5)
        norm2=sum(Decimal.from_float(x)**2 for x in d)
        expected_z=(norm2-expected_x**2).sqrt()
        for actual,interval,expected in zip(out.nominal,out.bounds,(expected_x,Decimal(0),expected_z)):
            assert abs(Decimal.from_float(actual)-expected)<=Decimal.from_float(2e-12)
            assert Decimal.from_float(interval.lo)<=expected<=Decimal.from_float(interval.hi)


def test_exact_planning_algebraic_chain_stops_with_fixed_width_policy():
    result=operator_stress()
    assert result["first_failure_operation"]==14
    assert len(result["accepted_prefix"])==13
    assert result["error_type"]=="UnsupportedNumericalInputError"
    assert "width" in result["message"] and "1e-08" in result["message"]
