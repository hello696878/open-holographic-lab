"""Public certified geometry: ownership, exact affine witnesses and finite UV."""
from dataclasses import FrozenInstanceError
from fractions import Fraction
import math

import pytest

from ohlab.optics.geometric_routing import (
    CertifiedInterval, CertifiedVector3, NumericalAmbiguityError,
    certify_planar_face, certify_pose_frame, certify_ray, certify_vector,
    certified_dot, certified_norm, certified_vector_add, certified_vector_scale,
    intersect_finite_face, nearest_finite_hit, transform_certified_vector,
)


def polygon(*, u=(1.,0.,0.), v=(0.,1.,0.), vertices=((0.,0.,0.),(.1,0.,0.),(0.,.1,0.)), angles=(0.,0.,0.)):
    pose=certify_pose_frame(angles); shift=certify_vector((0.,0.,.2))
    world=tuple(certified_vector_add(shift,transform_certified_vector(pose,certify_vector(x))) for x in vertices)
    origin=certified_vector_add(shift,transform_certified_vector(pose,certify_vector((0.,0.,0.))))
    # Zero pose in direct polygon tests gives the exact covector. Rotated
    # canonical bodies exercise certified inverse-transpose in W3 references.
    normal=certify_vector((0.,0.,1.))
    witness={"pose":pose,"translation":shift,"local_vertices":vertices,"local_origin":(0.,0.,0.),
             "local_u":u,"local_v":v,"local_covector":(0.,0.,1.)}
    return certify_planar_face(face_id="triangle",origin=origin,u=transform_certified_vector(pose,certify_vector(u)),
                               v=transform_certified_vector(pose,certify_vector(v)),plane_covector=normal,
                               boundary={"vertices":world,"affine_witness":witness},policy="affine_convex_polygon")


def ray(x=.02,y=.03):
    return certify_ray(origin=certify_vector((x,y,0.)),direction=certify_vector((0.,0.,1.)),
                       cumulative_length_m=0.,cumulative_bounds=CertifiedInterval.point(0.),previous_face_id=None)


def test_public_intervals_delegate_outward_operations_and_preserve_ownership():
    a=CertifiedInterval.point(.1); b=CertifiedInterval.point(.2)
    exact=Fraction.from_float(.1)+Fraction.from_float(.2)
    result=a+b
    assert Fraction.from_float(result.lo)<=exact<=Fraction.from_float(result.hi)
    assert a.pair()==(.1,.1)
    with pytest.raises(FrozenInstanceError): a.lo=0
    with pytest.raises(TypeError): CertifiedInterval.point(True)
    with pytest.raises(ValueError): CertifiedInterval(2.,1.)
    with pytest.raises(NumericalAmbiguityError): a/CertifiedInterval(-1.,1.)


def test_vectors_defensively_own_lists_and_reject_uncontained_nominal():
    values=[1.,2.,3.]; bounds=[CertifiedInterval.point(x) for x in values]
    vector=CertifiedVector3(values,bounds)
    values[0]=99.; bounds[1]=CertifiedInterval.point(99.)
    assert vector.nominal==(1.,2.,3.)
    assert vector.bounds[1].pair()==(2.,2.)
    with pytest.raises(ValueError): certify_vector((1.,2.,3.),(CertifiedInterval.point(0.),)*3)


def test_triangle_halfspaces_reject_inside_bounding_box_but_outside_triangle():
    face=polygon()
    assert intersect_finite_face(ray(.08,.08),face,CertifiedInterval.point(.5)) is None
    hit=intersect_finite_face(ray(),face,CertifiedInterval.point(.5))
    assert hit.position.nominal==pytest.approx((.02,.03,.2),rel=2e-12,abs=5e-12)
    assert hit.local_uv_m==pytest.approx((.02,.03),rel=2e-12,abs=5e-12)


def test_polygon_uv_uses_reciprocal_gram_for_nonorthonormal_declared_basis():
    hit=intersect_finite_face(ray(.05,.02),polygon(u=(2.,0.,0.),v=(1.,1.,0.)),CertifiedInterval.point(.5))
    assert hit.local_uv_m==pytest.approx((.015,.02),rel=2e-12,abs=5e-12)
    assert hit.local_uv_m != (.1,.07)  # the prohibited bare-dot projection


@pytest.mark.parametrize("point",[(0.,0.),(.1,0.),(.05,.05)])
def test_polygon_edge_and_vertex_are_ambiguity_without_epsilon(point):
    with pytest.raises(NumericalAmbiguityError):
        intersect_finite_face(ray(*point),polygon(),CertifiedInterval.point(.5))


def test_exact_affine_witness_rejects_nonplanarity_and_wrong_winding():
    with pytest.raises(ValueError,match="coplanar"):
        polygon(vertices=((0.,0.,0.),(.1,0.,0.),(0.,.1,1e-20)))
    with pytest.raises(ValueError,match="winding"):
        polygon(vertices=((0.,0.,0.),(0.,.1,0.),(.1,0.,0.)))


def test_parallel_plane_is_discarded_only_when_bounded_leg_certifies_no_crossing():
    face=polygon()
    parallel=certify_ray(origin=certify_vector((.01,.01,.1)),direction=certify_vector((1.,0.,0.)),
                         cumulative_length_m=0.,cumulative_bounds=CertifiedInterval.point(0.),previous_face_id=None)
    assert intersect_finite_face(parallel,face,CertifiedInterval.point(.05)) is None


def test_pose_active_X_then_Y_then_Z_and_exact_stored_entries_are_owned():
    angles=(.13,-.21,.17); pose=certify_pose_frame(angles)
    x,y,z=angles
    # Independent sequential scalar rotations of a non-axis vector.
    initial=(.02,-.03,.04)
    first=(initial[0],math.cos(x)*initial[1]-math.sin(x)*initial[2],math.sin(x)*initial[1]+math.cos(x)*initial[2])
    second=(math.cos(y)*first[0]+math.sin(y)*first[2],first[1],-math.sin(y)*first[0]+math.cos(y)*first[2])
    expected=(math.cos(z)*second[0]-math.sin(z)*second[1],math.sin(z)*second[0]+math.cos(z)*second[1],second[2])
    actual=transform_certified_vector(pose,certify_vector(initial))
    assert actual.nominal==pytest.approx(expected,rel=2e-12,abs=5e-12)
    with pytest.raises(FrozenInstanceError): pose.nominal_matrix=()


def test_scaled_vector_never_resets_existing_enclosure():
    original=certify_vector((1.,0.,0.),(CertifiedInterval(.999,1.001),CertifiedInterval(-.001,.001),CertifiedInterval(-.001,.001)))
    result=certified_vector_scale(original,2.,CertifiedInterval.point(2.))
    assert result.bounds[0].lo<1.998 and result.bounds[0].hi>2.002
    assert certified_norm(result)[1].hi>2.
    assert certified_dot(result,result)[1].hi>4.
