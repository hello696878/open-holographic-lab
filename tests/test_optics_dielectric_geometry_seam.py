"""Actual affine handles, both departures, and opaque exact-normal lineage."""
from copy import deepcopy
from dataclasses import FrozenInstanceError,replace
from fractions import Fraction
import math

import pytest

from ohlab.optics.geometric_routing import CertifiedInterval,certify_ray,certify_vector,nearest_finite_hit,certified_domain_exit
from ohlab.optics.refractive_routing import (
    CertifiedNormalIncidence,RefractiveScene,certified_geometry,certified_dielectric_directions,
)
from scripts.validate_w4_fresnel_routing import fixtures
from ohlab.optics.fresnel_interface import source_power_state,apply_fresnel_interface


def projection(raw):
    data=deepcopy(raw);data.pop("path_addition");data["model_contract"]="w3_ideal_refractive_routing_v1"
    data["source"]={k:v for k,v in data["source"].items() if k in ("id","origin_m","direction")}
    data["source"]["relative_weight"]=1.
    return RefractiveScene.from_dict(data)


def root_ray(geometry):
    return certify_ray(origin=certify_vector(geometry.scene.source["origin_m"]),direction=certify_vector(geometry.scene.source["direction"]),
        cumulative_length_m=0.,cumulative_bounds=CertifiedInterval.point(0.),previous_face_id=None)


def hit_of(geometry,ray):
    _,upper=certified_domain_exit(ray,geometry.scene.source["origin_m"])
    return nearest_finite_hit(ray,geometry.faces,upper)


def child_ray(hit,direction):
    return certify_ray(origin=hit.position,direction=direction,cumulative_length_m=hit.parameter,
        cumulative_bounds=hit.parameter_bounds,previous_face_id=hit.face.face_id)


def test_actual_faces_owned_and_two_subcritical_departures_have_opposite_sides():
    geometry=certified_geometry(projection(fixtures()["normal_slab"]))
    ray=root_ray(geometry);hit=hit_of(geometry,ray)
    directions=certified_dielectric_directions(geometry,ray,hit,"exterior")
    assert directions.reflected.nominal==(0.,0.,-1.)
    assert directions.transmitted.nominal==(0.,0.,1.)
    assert directions.incident_side.hi<0<directions.reflected_side.lo
    assert directions.transmitted_side.hi<0
    assert directions.normal_relation.face_id=="body:B1:z_min"
    assert geometry.face_record(hit.face)["face_id"]=="z_min"
    with pytest.raises(FrozenInstanceError):geometry.faces=()
    with pytest.raises(TypeError):CertifiedNormalIncidence()


def test_foreign_and_stale_relation_cannot_authorize_normal_gauge():
    geometry=certified_geometry(projection(fixtures()["normal_slab"]))
    ray=root_ray(geometry);hit=hit_of(geometry,ray)
    directions=certified_dielectric_directions(geometry,ray,hit,"exterior")
    child=child_ray(hit,directions.transmitted);next_hit=hit_of(geometry,child)
    with pytest.raises(ValueError,match="foreign, stale or forged"):
        certified_dielectric_directions(geometry,child,next_hit,"body:B1",directions.normal_relation)
    with pytest.raises(ValueError,match="foreign, stale or forged"):
        certified_dielectric_directions(geometry,child,next_hit,"body:B1",True)
    foreign=certified_geometry(projection(fixtures()["normal_slab"]))
    with pytest.raises(ValueError,match="foreign"):
        foreign.face_record(hit.face)


def test_opposite_normal_face_reissues_actual_owner_proof_without_reset():
    geometry=certified_geometry(projection(fixtures()["normal_slab"]))
    ray=root_ray(geometry);hit=hit_of(geometry,ray)
    first=certified_dielectric_directions(geometry,ray,hit,"exterior")
    child=child_ray(hit,first.transmitted);second_hit=hit_of(geometry,child)
    second=certified_dielectric_directions(geometry,child,second_hit,"body:B1",first.transmitted_relation)
    assert second.normal_relation.face_id=="body:B1:z_max"
    assert second.transmitted_relation.exact_direction==(Fraction(0),Fraction(0),Fraction(1))
    assert max(i.hi-i.lo for i in second.transmitted.bounds)>=max(i.hi-i.lo for i in first.transmitted.bounds)


def test_canonical_prism_tir_exact_rational_reflection_reproves_normal_exit():
    geometry=certified_geometry(projection(fixtures()["tir_prism"]))
    ray=root_ray(geometry);hit=hit_of(geometry,ray)
    entry=certified_dielectric_directions(geometry,ray,hit,"exterior")
    internal=child_ray(hit,entry.transmitted);hyp=hit_of(geometry,internal)
    tir=certified_dielectric_directions(geometry,internal,hyp,"body:B1",entry.transmitted_relation)
    assert geometry.face_record(hyp.face)["face_id"]=="hypotenuse"
    assert tir.classification=="total_internal_reflection" and tir.transmitted is None
    assert tir.normal_relation is None
    reflected=child_ray(hyp,tir.reflected);exit_hit=hit_of(geometry,reflected)
    exit_op=certified_dielectric_directions(geometry,reflected,exit_hit,"body:B1",tir.reflected_relation)
    assert exit_op.normal_relation.face_id=="body:B1:x_min"
    assert exit_op.normal_relation.exact_direction==(Fraction(-1),Fraction(0),Fraction(0))


def test_nominal_axis_with_uncertain_root_does_not_get_exact_relation():
    geometry=certified_geometry(projection(fixtures()["normal_slab"]))
    original=root_ray(geometry)
    direction=certify_vector((0.,0.,1.),(CertifiedInterval(-1e-15,1e-15),CertifiedInterval(-1e-15,1e-15),CertifiedInterval(1.-1e-15,1.+1e-15)))
    ray=certify_ray(origin=original.origin,direction=direction,cumulative_length_m=0.,cumulative_bounds=original.cumulative_bounds,previous_face_id=None)
    hit=hit_of(geometry,ray)
    op=certified_dielectric_directions(geometry,ray,hit,"exterior")
    assert op.normal_relation is None and op.transmitted_relation is None


def test_equal_index_keeps_same_direction_object_and_crossing_proofs():
    geometry=certified_geometry(projection(fixtures()["equal_index"]))
    ray=root_ray(geometry);hit=hit_of(geometry,ray)
    op=certified_dielectric_directions(geometry,ray,hit,"exterior")
    assert op.classification=="equal_index_identity"
    assert op.transmitted is ray.direction and op.reflected is None
    assert op.discriminant.lo>0 and op.transmitted_side.hi<0


def test_reusing_a_real_normal_proof_with_an_oblique_covector_is_rejected():
    geometry=certified_geometry(projection(fixtures()["normal_slab"]))
    ray=root_ray(geometry);hit=hit_of(geometry,ray)
    op=certified_dielectric_directions(geometry,ray,hit,"exterior")
    state=source_power_state(ray.direction,"exterior",1.,"unpolarized")
    forged=replace(op,incident_facing_covector=certify_vector((.5,0.,-math.sqrt(.75))))
    with pytest.raises(ValueError,match="face/covector-bound owner proof"):
        apply_fresnel_interface(state,forged)


def test_public_seam_distinguishes_bad_hit_and_medium_types():
    geometry=certified_geometry(projection(fixtures()["normal_slab"]))
    ray=root_ray(geometry);hit=hit_of(geometry,ray)
    with pytest.raises(TypeError,match="CertifiedPlanarHit"):
        certified_dielectric_directions(geometry,ray,{},"exterior")
    with pytest.raises(TypeError,match="medium must be str"):
        certified_dielectric_directions(geometry,ray,hit,True)
