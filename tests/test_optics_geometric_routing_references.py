"""Independent hand/Decimal/Fraction references for the complete W2 pipeline.

Expected intersections and reflection states never call production geometry
helpers. For a stored-frame enclosure reference, returned binary64 frame
values are reference *inputs*, not an expected geometric answer. Ideal-angle
and actual-stored-frame targets are deliberately tested separately.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import math

import numpy as np
import pytest

import ohlab.optics.geometric_routing as routing
from ohlab.optics.geometric_routing import GeometricScene, trace_routes


def fixture(elements, origin=(0., .08, 0.), direction=(0., 0., 1.)):
    return {"schema_version": 1, "model_contract": "w2_ideal_geometric_routing_v1",
            "source": {"id": "source", "origin_m": list(origin), "direction": list(direction), "relative_weight": 1.}, "elements": elements}


def face(identity, kind, point, angles):
    return {"id": identity, "kind": kind, "pose": {"position_m": list(point), "rotation_xyz_rad": list(angles)},
            "aperture": {"kind": "disk", "radius_m": .025}}


def independent_matrix(angles):
    x, y, z = angles
    sx, cx, sy, cy, sz, cz = math.sin(x), math.cos(x), math.sin(y), math.cos(y), math.sin(z), math.cos(z)
    return np.array([[cz*cy, cz*sy*sx-sz*cx, cz*sy*cx+sz*sx],
                     [sz*cy, sz*sy*sx+cz*cx, sz*sy*cx-cz*sx],
                     [-sy, cy*sx, cy*cx]], dtype=np.float64)


def decimal_trig(x, cosine=False):
    # Independent direct factorial/power series, rather than production's
    # rational term recurrence. At 160 digits, 100 terms leave a negligible
    # remainder for |x|<=pi; pose intervals have much coarser binary64 widths.
    return sum(Decimal((-1)**k)*(Decimal(1) if 2*k+(0 if cosine else 1)==0 else x**(2*k+(0 if cosine else 1)))
               /Decimal(math.factorial(2*k+(0 if cosine else 1))) for k in range(100))


def D(value):
    return Decimal.from_float(float(value))


def assert_contains(bounds, value):
    assert D(bounds[0]) <= value <= D(bounds[1]), (bounds, str(value))


@pytest.mark.parametrize("angles", [(0., 0., 0.), (.23, -.41, .37), (math.pi, -math.pi, math.pi),
                                    (1e-12, -1e-10, .73), (5e-324, 0., 0.)])
def test_pose_certificate_encloses_ideal_rotation_at_exact_stored_angles(angles):
    owned = GeometricScene.from_dict(fixture([face("M", "mirror", (0., .08, .2), angles)]))
    certificate = owned.pose_certificates[0]
    frame = owned.surface_frames[0]
    with localcontext() as context:
        context.prec = 160
        x, y, z = map(D, angles)
        sx, sy, sz = (decimal_trig(a) for a in (x, y, z))
        cx, cy, cz = (decimal_trig(a, True) for a in (x, y, z))
        expected = ((cz*cy, cz*sy*sx-sz*cx, cz*sy*cx+sz*sx),
                    (sz*cy, sz*sy*sx+cz*cx, sz*sy*cx-cz*sx), (-sy, cy*sx, cy*cx))
        for axis, sine, cosine in zip(range(3), (sx, sy, sz), (cx, cy, cz)):
            assert_contains(certificate["sine_intervals"][axis], sine)
            assert_contains(certificate["cosine_intervals"][axis], cosine)
        for row in range(3):
            for col, key in enumerate(("u", "v", "n")):
                assert_contains(certificate["matrix_intervals"][row][col], expected[row][col])
                assert_contains(certificate["matrix_intervals"][row][col], D(frame[key][row]))
    assert certificate["max_pose_error_bound"] <= 64*np.finfo(float).eps


def test_exact_fraction_arithmetic_detects_missing_outward_rounding(monkeypatch):
    a, b = .1, .2
    expected = Fraction.from_float(a)+Fraction.from_float(b)

    def assert_enclosure():
        interval = routing._Interval.point(a)+routing._Interval.point(b)
        assert Fraction.from_float(interval.lo) <= expected <= Fraction.from_float(interval.hi)

    assert_enclosure()
    with monkeypatch.context() as mutation:
        mutation.setattr(routing, "_down", lambda value: value)
        with pytest.raises(AssertionError):
            assert_enclosure()
    assert_enclosure()


@pytest.mark.parametrize("a,b", [((-.31, .47), (.13, .41)), ((1e-200, 2e-200), (.01, .02)),
                                ((-3., -2.), (-.7, -.2)), ((-.0, 0.), (2., 3.))])
def test_interval_operations_enclose_independent_exact_fraction_corners(a, b):
    ia, ib = routing._Interval(*a), routing._Interval(*b)
    for result, operation in [(ia+ib, lambda x,y:x+y), (ia-ib, lambda x,y:x-y),
                              (ia*ib, lambda x,y:x*y), (ia/ib, lambda x,y:x/y)]:
        for x in a:
            for y in b:
                exact = operation(Fraction.from_float(x), Fraction.from_float(y))
                assert Fraction.from_float(result.lo) <= exact <= Fraction.from_float(result.hi)
    with localcontext() as context:
        context.prec=160
        squared = ia.square()
        rooted = squared.sqrt()
        for x in a:
            assert_contains(rooted.pair(), abs(D(x)))


def independent_chain_reference(result, submitted, expected_ids, frame_target="stored"):
    """Independent Decimal160 recurrence including every state and length."""
    elements = {item["id"]: item for item in submitted["elements"]}
    frames = {item["element_id"]: item for item in result.surface_frames}
    with localcontext() as context:
        context.prec=160
        origin = list(map(D, submitted["source"]["origin_m"]))
        direction = list(map(D, submitted["source"]["direction"]))
        cumulative = Decimal(0)
        for ordinal, identity in enumerate(expected_ids):
            element, frame = elements[identity], frames[identity]
            center = list(map(D, element["pose"]["position_m"]))
            if frame_target=="stored":
                normal, u, v = [list(map(D, frame[key])) for key in ("n", "u", "v")]
            else:
                x,y,z=map(D,element["pose"]["rotation_xyz_rad"])
                sx,sy,sz=(decimal_trig(a) for a in (x,y,z));cx,cy,cz=(decimal_trig(a,True) for a in (x,y,z))
                matrix=((cz*cy,cz*sy*sx-sz*cx,cz*sy*cx+sz*sx),
                        (sz*cy,sz*sy*sx+cz*cx,sz*sy*cx-cz*sx),(-sy,cy*sx,cy*cx))
                normal,u,v=[[matrix[i][j] for i in range(3)] for j in (2,0,1)]
            dot = lambda a,b:sum(x*y for x,y in zip(a,b))
            parameter = dot([c-o for c,o in zip(center,origin)],normal)/dot(direction,normal)
            point = [o+parameter*d for o,d in zip(origin,direction)]
            relative = [p-c for p,c in zip(point,center)]
            local = [dot(relative,u),dot(relative,v)]
            step = sum((p-o)**2 for p,o in zip(point,origin)).sqrt()
            cumulative += step
            actual, certificate = result.hits[ordinal], result.certificates[ordinal]
            assert actual["element_id"] == identity
            assert_contains(actual["numerical_bounds"]["t_parameter_interval_m"],parameter)
            for index in range(3):
                assert_contains(certificate["start_intervals_m"][index],origin[index])
                assert_contains(certificate["direction_intervals"][index],direction[index])
                assert_contains(actual["numerical_bounds"]["position_intervals_m"][index],point[index])
            for index in range(2):
                assert_contains(actual["numerical_bounds"]["local_uv_intervals_m"][index],local[index])
            assert_contains(certificate["length_interval_m"],step)
            assert_contains(certificate["cumulative_interval_m"],cumulative)
            if element["kind"] == "mirror":
                dn=dot(direction,normal)
                direction=[d-2*dn*n for d,n in zip(direction,normal)]
                for index in range(3):
                    assert_contains(certificate["outgoing_direction_intervals"][0][index],direction[index])
            origin=point
        return float(cumulative)


def test_full_32_reflection_enclosures_contain_independent_high_precision_chain():
    submitted=fixture([face("plus","mirror",(0.,.08,.1),(0.,0.,0.)),
                       face("minus","mirror",(0.,.08,-.1),(0.,0.,0.))])
    result=trace_routes(GeometricScene.from_dict(submitted))
    assert len(result.hits)==32
    length=independent_chain_reference(result,submitted,["plus","minus"]*16)
    independent_chain_reference(result,submitted,["plus","minus"]*16,"ideal")
    assert length==pytest.approx(6.3,rel=2e-13,abs=2e-13)
    assert result.terminals[0]["reason"]=="interaction_cap"


@pytest.mark.parametrize("source_value",[(0.,.08,0.),(9.5,-9.3,9.1)])
def test_full_32_oblique_three_dimensional_reflections_have_propagated_reference_enclosures(source_value):
    angles=(.23,-.41,.37)
    frame=independent_matrix(angles)
    source=np.array(source_value)
    normal,u=frame[:,2],frame[:,0]
    direction=.95*normal+math.sqrt(1-.95**2)*u
    direction=direction/np.linalg.norm(direction)  # explicitly constructed fixture input
    faces=[face("plus","mirror",source+.01*normal,angles),face("minus","mirror",source-.01*normal,angles)]
    for item in faces:item["aperture"]["radius_m"]=.25
    submitted=fixture(faces,source,direction)
    result=trace_routes(GeometricScene.from_dict(submitted))
    assert len(result.hits)==32
    assert result.terminals[0]["reason"]=="interaction_cap"
    independent_chain_reference(result,submitted,["plus","minus"]*16)
    independent_chain_reference(result,submitted,["plus","minus"]*16,"ideal")
    assert abs(result.hits[-1]["local_uv_m"][0])>.1


def test_both_folded_states_and_receiver_local_intervals_have_independent_reference():
    submitted=fixture([face("M1","mirror",(0.,.08,.2),(0.,-math.pi/4,0.)),
                       face("M2","mirror",(.2,.08,.2),(0.,3*math.pi/4,0.)),
                       face("D","receiver",(.2,.08,.4),(0.,math.pi,0.))])
    result=trace_routes(GeometricScene.from_dict(submitted))
    assert independent_chain_reference(result,submitted,["M1","M2","D"])==pytest.approx(.6,rel=2e-13,abs=2e-13)


def test_general_three_dimensional_pose_reflection_and_local_receiver_coordinates():
    angles=(.23,-.41,.37)
    matrix=independent_matrix(angles)
    n=matrix[:,2]
    incoming=np.array([1.,2.,3.])/math.sqrt(14)
    outgoing=incoming-2*np.dot(incoming,n)*n
    center=np.array([0.,.08,.2])
    origin=center-.2*incoming
    receiver=center+.3*outgoing
    receiver_angles=(-math.asin(float(outgoing[1])),math.atan2(float(outgoing[0]),float(outgoing[2])),0.)
    submitted=fixture([face("M","mirror",center,angles),face("D","receiver",receiver,receiver_angles)],origin,incoming)
    result=trace_routes(GeometricScene.from_dict(submitted))
    assert [h["element_id"] for h in result.hits]==["M","D"]
    np.testing.assert_allclose(result.hits[0]["outgoing"][0]["direction"],outgoing,rtol=2e-13,atol=2e-13)
    np.testing.assert_allclose(result.hits[1]["local_uv_m"],[0.,0.],rtol=0.,atol=2e-13)
    assert independent_chain_reference(result,submitted,["M","D"])==pytest.approx(.5,rel=2e-13,abs=2e-13)


def test_general_off_axis_receiver_projection_uses_rotated_local_basis():
    angles=(.23,-.41,.37);matrix=independent_matrix(angles)
    center=np.array([.1,.1,.3]);expected_point=center+.006*matrix[:,0]-.004*matrix[:,1]
    origin=expected_point-.2*matrix[:,2]
    result=trace_routes(GeometricScene.from_dict(fixture([face("D","receiver",center,angles)],origin,matrix[:,2])))
    np.testing.assert_allclose(result.hits[0]["position_m"],expected_point,rtol=2e-13,atol=2e-13)
    np.testing.assert_allclose(result.hits[0]["local_uv_m"],[.006,-.004],rtol=2e-13,atol=2e-13)


def test_reflection_angle_equality_doubled_mirror_rotation_and_both_sides():
    directions=[]
    for angle in (-math.pi/4,-math.pi/4+1e-4,3*math.pi/4):
        result=trace_routes(GeometricScene.from_dict(fixture([face("M","mirror",(0.,.08,.2),(0.,angle,0.))])))
        hit=result.hits[0];normal=np.array(result.surface_frames[0]["n"])
        incoming=np.array(hit["incident_direction"]);outgoing=np.array(hit["outgoing"][0]["direction"])
        angle_in=math.atan2(float(np.linalg.norm(np.cross(incoming,normal))),abs(float(np.dot(incoming,normal))))
        angle_out=math.atan2(float(np.linalg.norm(np.cross(outgoing,normal))),abs(float(np.dot(outgoing,normal))))
        assert angle_in==pytest.approx(angle_out,rel=0.,abs=2e-13)
        directions.append(outgoing)
    theta=lambda d:math.atan2(float(d[0]),float(d[2]))
    assert abs(theta(directions[1])-theta(directions[0]))==pytest.approx(2e-4,rel=0.,abs=2e-13)
    np.testing.assert_allclose(directions[0],directions[2],rtol=2e-13,atol=2e-13)


def test_rigid_whole_scene_covariance_includes_trace_sphere_escape():
    submitted=fixture([face("M1","mirror",(0.,.08,.2),(0.,-math.pi/4,0.)),
                       face("D","receiver",(.2,.08,.2),(0.,-math.pi/2,0.))])
    transform=independent_matrix((.2,.3,-.1));translation=np.array([.4,-.3,.2])
    transformed=deepcopy(submitted)
    transformed["source"]["origin_m"]=(transform@np.array(submitted["source"]["origin_m"])+translation).tolist()
    transformed["source"]["direction"]=(transform@np.array(submitted["source"]["direction"])).tolist()
    for before,after in zip(submitted["elements"],transformed["elements"]):
        matrix=transform@independent_matrix(before["pose"]["rotation_xyz_rad"])
        after["pose"]["position_m"]=(transform@np.array(before["pose"]["position_m"])+translation).tolist()
        after["pose"]["rotation_xyz_rad"]=[math.atan2(float(matrix[2,1]),float(matrix[2,2])),math.asin(-float(matrix[2,0])),math.atan2(float(matrix[1,0]),float(matrix[0,0]))]
    first,second=[trace_routes(GeometricScene.from_dict(x)) for x in (submitted,transformed)]
    for a,b in zip(first.hits,second.hits):
        np.testing.assert_allclose(b["position_m"],transform@np.array(a["position_m"])+translation,rtol=2e-13,atol=2e-13)
        np.testing.assert_allclose(b["local_uv_m"],a["local_uv_m"],rtol=2e-13,atol=2e-13)
    # No elements: escaped point must transform with the source-centered domain.
    for value in (submitted,transformed):value["elements"]=[]
    first,second=[trace_routes(GeometricScene.from_dict(x)) for x in (submitted,transformed)]
    np.testing.assert_allclose(second.terminals[0]["position_m"],transform@np.array(first.terminals[0]["position_m"])+translation,rtol=2e-13,atol=2e-13)


def test_near_parallel_supported_center_hit_and_independent_interval_reference():
    submitted=fixture([face("D","receiver",(0.,.08,.2),(0.,math.pi/2-1e-10,0.))])
    result=trace_routes(GeometricScene.from_dict(submitted))
    assert result.hits[0]["element_id"]=="D"
    independent_chain_reference(result,submitted,["D"])


def test_wrong_reflection_fault_is_detected_then_restored(monkeypatch):
    submitted=fixture([face("M","mirror",(0.,.08,.2),(0.,-math.pi/4,0.)),
                       face("D","receiver",(.2,.08,.2),(0.,-math.pi/2,0.))])
    def detecting_assertion():
        result=trace_routes(GeometricScene.from_dict(submitted))
        assert result.ledger["detected_weight"]==1.
    detecting_assertion()
    original=routing._reflection
    with monkeypatch.context() as mutation:
        def wrong(direction,enclosure,surface):
            # Unit-but-wrong straight-through "reflection" is a deliberate fault.
            return direction,enclosure
        mutation.setattr(routing,"_reflection",wrong)
        with pytest.raises(AssertionError):detecting_assertion()
    assert routing._reflection is original
    detecting_assertion()
