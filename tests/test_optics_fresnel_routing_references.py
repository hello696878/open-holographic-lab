"""Independent Decimal90 finite geometry, frames and complex C along every leg.

No reference calls a production Fresnel/direction/frame/interval helper. Exact
Fraction affine targets and Gaussian-elimination inverse are constructed here;
the production operator uses a different stored covector/interval algorithm.
"""
from copy import deepcopy
from decimal import Decimal,localcontext
from fractions import Fraction
import math

import numpy as np
import pytest

from ohlab.optics.fresnel_interface import (
    RayPowerState,TransverseFrame,apply_fresnel_interface,fresnel_coefficients,
)
from ohlab.optics.fresnel_routing import FresnelScene,trace_fresnel_scene
from ohlab.optics.geometric_routing import CertifiedInterval,certify_vector
from ohlab.optics.refractive_routing import CertifiedDielectricDirections
from scripts.validate_w4_fresnel_routing import fixtures,decimal_coefficients,weak_fixtures


def D(value):return Decimal(value.numerator)/Decimal(value.denominator) if isinstance(value,Fraction) else Decimal.from_float(float(value))
def dot(a,b):return sum((x*y for x,y in zip(a,b)),Decimal(0))
def cross(a,b):return [a[j]*b[k]-a[k]*b[j] for j,k in ((1,2),(2,0),(0,1))]
def add(a,b):return [x+y for x,y in zip(a,b)]
def sub(a,b):return [x-y for x,y in zip(a,b)]
def scale(a,b):return [x*b for x in a]
def unit(a):return scale(a,1/dot(a,a).sqrt())
def cp(a,b):return (a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0])
def cj(a):return (a[0],-a[1])
def ca(a,b):return (a[0]+b[0],a[1]+b[1])


def rotate(C,M):
    z=(Decimal(0),Decimal(0))
    return [[sum_complex([cp(cp((M[i][p],Decimal(0)),C[p][q]),(M[j][q],Decimal(0))) for p in range(2) for q in range(2)])
             for j in range(2)] for i in range(2)]


def sum_complex(values):
    result=(Decimal(0),Decimal(0))
    for value in values:result=ca(result,value)
    return result


def diagonal(C,J):return [[cp(cp(J[i],C[i][j]),cj(J[j])) for j in range(2)] for i in range(2)]
def packed(C):return [C[0][0][0],C[1][1][0],C[0][1][0],C[0][1][1]]


def matrix(angles):
    x,y,z=angles;sx,cx,sy,cy,sz,cz=math.sin(x),math.cos(x),math.sin(y),math.cos(y),math.sin(z),math.cos(z)
    rx=((1.,0.,0.),(0.,cx,-sx),(0.,sx,cx));ry=((cy,0.,sy),(0.,1.,0.),(-sy,0.,cy));rz=((cz,-sz,0.),(sz,cz,0.),(0.,0.,1.))
    mul=lambda a,b:tuple(tuple(math.fsum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)) for i in range(3))
    return [[Fraction.from_float(x) for x in row] for row in mul(rz,mul(ry,rx))]


def inverse(A):
    # Independent exact Gaussian elimination; no production adjugate formula.
    rows=[list(row)+[Fraction(i==j) for j in range(3)] for i,row in enumerate(A)]
    for i in range(3):
        pivot=next(j for j in range(i,3) if rows[j][i])
        rows[i],rows[pivot]=rows[pivot],rows[i]
        rows[i]=[x/rows[i][i] for x in rows[i]]
        for j in range(3):
            if j!=i:
                factor=rows[j][i];rows[j]=[x-factor*y for x,y in zip(rows[j],rows[i])]
    return [row[3:] for row in rows]


def surfaces(scene):
    result=[]
    if scene["bodies"]:
        body=scene["bodies"][0];shape=body["shape"];B=matrix(body["pose"]["rotation_xyz_rad"]);inv=inverse(B)
        if body["kind"]=="rectangular_block":
            x,y,z=(Fraction.from_float(shape[k])/2 for k in ("width_x_m","height_y_m","depth_z_m"))
            definitions=[("x_min",(-1,0,0),(-x,0,0)),("x_max",(1,0,0),(x,0,0)),("y_min",(0,-1,0),(0,-y,0)),
                ("y_max",(0,1,0),(0,y,0)),("z_min",(0,0,-1),(0,0,-z)),("z_max",(0,0,1),(0,0,z))]
        else:
            x,z=(Fraction.from_float(shape[k]) for k in ("leg_x_m","leg_z_m"));y=Fraction.from_float(shape["height_y_m"])/2
            definitions=[("x_min",(-1,0,0),(0,0,0)),("z_min",(0,0,-1),(0,0,0)),("hypotenuse",(z,0,x),(x,0,0)),
                ("y_min",(0,-1,0),(0,-y,0)),("y_max",(0,1,0),(0,y,0))]
        translation=list(map(Fraction.from_float,body["pose"]["position_m"]))
        for name,a,o in definitions:
            nf=[sum((inv[j][i]*a[j] for j in range(3)),Fraction(0)) for i in range(3)]
            origin=[sum((B[i][j]*o[j] for j in range(3)),Fraction(0))+translation[i] for i in range(3)]
            result.append({"name":name,"kind":"body","n":list(map(D,nf)),"nf":nf,"o":list(map(D,origin))})
    for e in scene["elements"]:
        B=matrix(e["pose"]["rotation_xyz_rad"])
        result.append({"name":e["id"],"kind":e["kind"],"o":list(map(D,e["pose"]["position_m"])),
            "n":[D(row[2]) for row in B],"u":[D(row[0]) for row in B],"v":[D(row[1]) for row in B],"ap":e["aperture"]})
    return result


def nearest(surfaces_,state):
    candidates=[]
    for face in surfaces_:
        if face["name"]==state["previous"]:continue
        denominator=dot(face["n"],state["d"])
        if denominator==0:continue
        t=dot(face["n"],sub(face["o"],state["o"]))/denominator
        if t<=0:continue
        point=add(state["o"],scale(state["d"],t))
        if face["kind"]=="body":
            if not all(dot(other["n"],sub(point,other["o"]))<0 for other in surfaces_ if other["kind"]=="body" and other is not face):continue
        else:
            uv=[dot(sub(point,face["o"]),face[key]) for key in ("u","v")]
            ap=face["ap"]
            if ap["kind"]=="disk":
                if sum((x*x for x in uv),Decimal(0))>=D(ap["radius_m"])**2:continue
            elif abs(uv[0])>=D(ap["width_m"])/2 or abs(uv[1])>=D(ap["height_m"])/2:continue
        candidates.append((t,face,point))
    return min(candidates,key=lambda x:x[0]) if candidates else None


def interface_reference(state,face,ni,nt):
    d=state["d"];entering=state["medium"]=="exterior"
    a=face["n"] if entering else scale(face["n"],Decimal(-1))
    af=face["nf"] if entering else [-x for x in face["nf"]]
    rational=state["rational"]
    normal=rational is not None and all(x==0 for x in cross(rational,af))
    khat=unit(d);ci=Decimal(1) if normal else -dot(d,a)/(dot(d,d)*dot(a,a)).sqrt()
    v=1-(ni/nt)**2*(1-ci*ci)
    if ni==nt:return {"T":dict(d=d,F=state["F"],C=state["C"],rational=rational)},None
    s=state["F"][0] if normal else unit(cross(a,khat));p=state["F"][1] if normal else cross(khat,s)
    M=[[dot(new,old) for old in state["F"]] for new in (s,p)]
    local=state["C"] if normal else rotate(state["C"],M)
    da=dot(d,a);aa=dot(a,a)
    exact_r=None if rational is None else [x-2*sum((p*q for p,q in zip(rational,af)),Fraction(0))*y/sum((z*z for z in af),Fraction(0)) for x,y in zip(rational,af)]
    dr=sub(d,scale(a,2*da/aa)) if exact_r is None else list(map(D,exact_r))
    if v<0:
        gamma=(-v).sqrt()
        phase=lambda x,y:((x*x-y*y)/(x*x+y*y),-2*x*y/(x*x+y*y))
        jr=(phase(ni*ci,nt*gamma),phase(nt*ci,ni*gamma))
        return {"R":dict(d=dr,F=[s,cross(unit(dr),s)],C=diagonal(local,jr),rational=exact_r)},jr
    ct=v.sqrt();ds=ni*ci+nt*ct;dp=nt*ci+ni*ct
    rs=(ni*ci-nt*ct)/ds;rp=(nt*ci-ni*ct)/dp
    ts=2*ni*ci/ds;tp=2*ni*ci/dp;root=(nt*ct/(ni*ci)).sqrt()
    dt=d if normal else sub(scale(sub(d,scale(a,da/aa)),ni/nt),scale(a,(dot(d,d)-(ni/nt)**2*dot(sub(d,scale(a,da/aa)),sub(d,scale(a,da/aa)))) .sqrt()/aa.sqrt()))
    return {"R":dict(d=dr,F=[s,cross(unit(dr),s)],C=diagonal(local,((rs,Decimal(0)),(rp,Decimal(0)))),rational=exact_r),
            "T":dict(d=dt,F=[s,cross(unit(dt),s)],C=diagonal(local,((root*ts,Decimal(0)),(root*tp,Decimal(0)))),rational=rational if normal else None)},((rs,Decimal(0)),(rp,Decimal(0)))


def check_state(actual,reference):
    expected=packed(reference["C"])
    assert actual["C"]==pytest.approx(list(map(float,expected)),rel=2e-12,abs=2e-13)
    for value,pair in zip(expected,actual["numerical_bounds"]["C_intervals"]):
        assert D(pair[0])<=value<=D(pair[1])
    frames=reference["F"]+[unit(reference["d"])]
    for value,pair in zip([x for row in frames for x in row],actual["numerical_bounds"]["frame_intervals"]):
        assert D(pair[0])<=value<=D(pair[1])
    assert actual["direction"]==pytest.approx(list(map(float,reference["d"])),abs=2e-12,rel=2e-12)
    for value,pair in zip(reference["d"],actual["numerical_bounds"]["direction_intervals"]):
        assert D(pair[0])<=value<=D(pair[1])


@pytest.mark.parametrize("name",["normal_slab","refracting_prism","tir_prism","brewster_e1","brewster_e2","equal_index","xyz_pose"])
def test_every_actual_finite_child_matches_independent_geometry_frame_and_accumulated_C_enclosure(name):
    scene=fixtures()[name];wire=trace_fresnel_scene(FresnelScene.from_dict(scene)).to_dict()
    with localcontext() as ctx:
        ctx.prec=90
        source=scene["source"];p=source["polarization"]
        C={"unpolarized":[.5,.5,0.,0.],"linear_e1":[1.,0.,0.,0.],"linear_e2":[0.,1.,0.,0.],"linear_45":[.5,.5,.5,0.]}[p]
        c0,c1,x,y=map(D,C)
        root={"o":list(map(D,source["origin_m"])),"d":list(map(D,source["direction"])),"rational":list(map(Fraction.from_float,source["direction"])),
            "F":[list(map(D,(1.,0.,0.))),list(map(D,(0.,1.,0.)))],"C":[[(c0,Decimal(0)),(x,y)],[(x,-y),(c1,Decimal(0))]],"medium":"exterior","previous":None}
        states={"r0":root};planes=surfaces(scene)
        for event in wire["events"]:
            state=states[event["branch_id"]];check_state(event["incident_state"],state)
            hit=nearest(planes,state);assert hit is not None
            parameter,face,point=hit
            target=event["target"]["face_id"] if face["kind"]=="body" else event["target"]["element_id"]
            assert target==face["name"]
            assert event["position_m"]==pytest.approx(list(map(float,point)),abs=5e-12,rel=2e-12)
            for value,pair in zip(point,event["numerical_bounds"]["position_intervals_m"]):assert D(pair[0])<=value<=D(pair[1])
            if face["kind"]!="body":continue
            ni=D(scene["exterior_medium"]["refractive_index"] if state["medium"]=="exterior" else scene["bodies"][0]["interior_medium"]["refractive_index"])
            nt=D(scene["bodies"][0]["interior_medium"]["refractive_index"] if state["medium"]=="exterior" else scene["exterior_medium"]["refractive_index"])
            children,amplitudes=interface_reference(state,face,ni,nt)
            if amplitudes is not None:
                for channel,key in enumerate(("r_s","r_p")):
                    expected=amplitudes[channel];actual=event["interface"]["coefficients"][key]
                    assert actual==pytest.approx(list(map(float,expected)),abs=2e-14,rel=2e-12)
                    for value,pair in zip(expected,event["interface"]["numerical_bounds"]["coefficient_intervals"][channel]):assert D(pair[0])<=value<=D(pair[1])
            for leg in event["interface"]["legs"]:
                if leg["state"] is None:continue
                child=children[leg["kind"]]
                child.update(o=point,previous=face["name"],medium=leg["medium_id"])
                check_state(leg["state"],child)
                if leg["branch_id"] is not None:states[leg["branch_id"]]=child
        for segment in wire["segments"]:
            if segment["event_id"] is not None:continue
            state=states[segment["branch_id"]]
            delta=sub(state["o"],root["o"]);speed2=dot(state["d"],state["d"]);od=dot(delta,state["d"])
            t=(-od+(od*od-speed2*(dot(delta,delta)-1)).sqrt())/speed2
            point=add(state["o"],scale(state["d"],t))
            assert segment["end_m"]==pytest.approx(list(map(float,point)),abs=5e-12,rel=2e-12)
        reference_totals={category:Decimal(0) for category in ("detected","stopped","escaped","resource_unresolved")}
        for terminal in wire["terminals"]:
            reference=states[terminal["branch_id"]];check_state(terminal["state"],reference)
            reference_totals[terminal["category"]]+=sum(packed(reference["C"])[:2])
        for category,key in (("detected","detected_power"),("stopped","stopped_power"),("escaped","escaped_power"),("resource_unresolved","unresolved_power")):
            assert wire["ledger"][key]==pytest.approx(float(reference_totals[category]),abs=2e-13,rel=2e-12)


def algebra_state(theta,C,ni=1.,plane_rotation=0.,frame=None,direction=None):
    d=(math.sin(theta),0.,math.cos(theta)) if direction is None else tuple(direction)
    k=tuple(x/math.hypot(*d) for x in d)
    e1=(0.,-1.,0.);e2=(k[2],0.,-k[0])
    eps=4*2.220446049250313e-16
    cv=lambda v:certify_vector(tuple(v),tuple(CertifiedInterval(x-eps,x+eps) for x in v))
    axes=TransverseFrame(cv(e1),cv(e2),cv(k)) if frame is None else frame
    return RayPowerState(cv(d),"incident",ni,axes,C)


def algebra_geometry(state,ni,nt,a=(0.,0.,-1.)):
    # Independent nominal directions only for a pure interface algebra test;
    # finite-body public-seam tests above establish actual production geometry.
    d=np.array(state.direction.nominal);av=np.array(a);da=float(d@av);aa=float(av@av)
    q=d-da/aa*av;K=float(d@d)-(ni/nt)**2*float(q@q)
    dr=d-2*da/aa*av;dt=None if K<0 else (ni/nt)*q-math.sqrt(K/aa)*av
    eps=4*2.220446049250313e-16
    cv=lambda v:certify_vector(tuple(v),tuple(CertifiedInterval(x-eps,x+eps) for x in v))
    return CertifiedDielectricDirections("total_internal_reflection" if K<0 else "dielectric_split",cv(dr),None if dt is None else cv(dt),
        cv(av),CertifiedInterval(K-eps,K+eps),CertifiedInterval(da-eps,da+eps),CertifiedInterval(-da-eps,-da+eps),
        None if dt is None else CertifiedInterval(float(dt@av)-eps,float(dt@av)+eps),"incident","transmission",ni,nt,None,None,None,())


@pytest.mark.parametrize("name,d",weak_fixtures())
def test_seven_weak_reflected_coherency_entries_remain_positive_against_Decimal90_with_atol_zero(name,d):
    # Preserve the original stored vector: do not reconstruct an angle and then
    # evaluate sin/cos again. Bounds retain declared independent uncertainty.
    state=algebra_state(0.,(0.,1.,0.,0.),direction=d)
    reflected=apply_fresnel_interface(state,algebra_geometry(state,1.,1.5)).reflected
    reference=decimal_coefficients(d,[0.,0.,-1.],1.,1.5)
    expected=float(reference["Rp"])
    assert reflected.C[1]>0 and reflected.power_fraction>0
    assert reflected.C[1]==pytest.approx(expected,rel=2e-11,abs=0.)
    assert reflected.power_fraction==pytest.approx(expected,rel=2e-11,abs=0.)
    assert reflected.C_bounds[1].lo<=expected<=reflected.C_bounds[1].hi


def test_polarization_memory_two_oblique_interfaces_detects_illegal_unpolarized_reset():
    first=algebra_state(math.pi/4,(.5,.5,0.,0.))
    one=apply_fresnel_interface(first,algebra_geometry(first,1.,1.5))
    carried=one.transmitted
    second=RayPowerState(carried.direction,"incident",1.5,carried.frame,carried.C,carried.C_bounds)
    two=apply_fresnel_interface(second,algebra_geometry(second,1.5,1.))
    assert two.transmitted.power_fraction==pytest.approx(.9037892479288234,abs=2e-13,rel=2e-12)
    coeff=fresnel_coefficients(second.direction,certify_vector((0.,0.,-1.)),1.5,1.)
    wrong=carried.power_fraction*.5*sum(coeff.channel_powers[2:])
    assert wrong==pytest.approx(.9020442266340458,abs=2e-13,rel=2e-12)
    assert abs(two.transmitted.power_fraction-wrong)>1e-4


def test_tir_retains_complex_phase_then_changed_plane_detector_can_see_it():
    state=algebra_state(math.pi/4,(.5,.5,.5,0.),1.5)
    result=apply_fresnel_interface(state,algebra_geometry(state,1.5,1.))
    assert result.transmitted is None and result.reflected.medium_id=="incident"
    assert result.reflected.power_fraction==pytest.approx(1.,abs=5e-14,rel=0.)
    assert result.reflected.C[2:]==pytest.approx((.4,.3),abs=2e-14,rel=2e-12)
    # Diagonal power1 follows the analytic unit-modulus TIR identity. The raw
    # complex electric amplitudes and their relative phase are still retained.
    ref_tir=decimal_coefficients(list(state.direction.nominal),[0.,0.,-1.],1.5,1.)
    for actual,key in ((result.coefficients.r_s,"rs_pair"),(result.coefficients.r_p,"rp_pair")):
        expected=complex(*map(float,ref_tir[key]))
        assert actual==pytest.approx(expected,abs=2e-14,rel=2e-12)
        assert abs(actual)**2==pytest.approx(1.,abs=5e-14,rel=0.)
    # Independent prescribed downstream operator: rotated local frame and a
    # separate30-degree interface, not a claimed realizable one-body path.
    with localcontext() as ctx:
        ctx.prec=90
        theta=math.pi/6;ref=decimal_coefficients([math.sin(theta),0.,math.cos(theta)],[0.,0.,-1.],1.5,1.)
        phi=math.pi/4;M=[[D(math.cos(phi)),D(math.sin(phi))],[-D(math.sin(phi)),D(math.cos(phi))]]
        C=[[(D(.5),Decimal(0)),(D(.4),D(.3))],[(D(.4),-D(.3)),(D(.5),Decimal(0))]]
        out=diagonal(rotate(C,M),((ref["rs"],Decimal(0)),(ref["rp"],Decimal(0))))
        power=float(sum(packed(out)[:2]))
        dropped=[[(D(.5),Decimal(0)),(D(.5),Decimal(0))],[(D(.5),Decimal(0)),(D(.5),Decimal(0))]]
        wrong=float(sum(packed(diagonal(rotate(dropped,M),((ref["rs"],Decimal(0)),(ref["rp"],Decimal(0)))))[:2]))
    assert power==pytest.approx(.09565626637510972,abs=2e-14,rel=2e-12)
    assert abs(power-wrong)>1e-4


def test_world_tensor_gauge_covariance_with_changed_incidence_plane():
    d=np.array([2.,3.,6.])/7;e1=np.array([3.,-2.,0.])/math.sqrt(13);e2=np.cross(d,e1)
    F=np.column_stack([e1,e2]);C=np.array([[.6,.12+.2j],[.12-.2j,.4]],dtype=np.complex128)
    theta,phi=math.pi/6,math.radians(37.)
    a=-math.cos(theta)*d+math.sin(theta)*(math.cos(phi)*e2+math.sin(phi)*e1)
    gamma=.7;U=np.array([[math.cos(gamma),-math.sin(gamma)],[math.sin(gamma),math.cos(gamma)]])
    transformed=U.T@C@U
    eps=4*2.220446049250313e-16
    cv=lambda v:certify_vector(tuple(v),tuple(CertifiedInterval(x-eps,x+eps) for x in v))
    def state(F,C):
        return RayPowerState(cv(d),"incident",1.,TransverseFrame(cv(F[:,0]),cv(F[:,1]),cv(d)),
            (float(C[0,0].real),float(C[1,1].real),float(C[0,1].real),float(C[0,1].imag)))
    original=state(F,C);rebased=state(F@U,transformed)
    one=apply_fresnel_interface(original,algebra_geometry(original,1.,1.5,a))
    two=apply_fresnel_interface(rebased,algebra_geometry(rebased,1.,1.5,a))
    for x,y in ((one.reflected,two.reflected),(one.transmitted,two.transmitted)):
        def world(z):
            f=np.column_stack([z.frame.e1.nominal,z.frame.e2.nominal]);u,v,r,i=z.C
            return f@np.array([[u,r+1j*i],[r-1j*i,v]])@f.T
        np.testing.assert_allclose(world(x),world(y),rtol=2e-12,atol=2e-14)
        assert x.power_fraction==pytest.approx(y.power_fraction,abs=2e-14,rel=2e-12)


@pytest.mark.parametrize("theta,supported",[(1e-6,True),(1e-8,False),(1e-12,False)])
def test_fixed_near_normal_uncertainty_is_conditioned_or_rejected_without_angle_snap(theta,supported):
    state=algebra_state(theta,(.5,.5,0.,0.))
    if supported:
        result=apply_fresnel_interface(state,algebra_geometry(state,1.,1.5))
        assert result.incidence_basis["normal_policy"]=="generic_certified"
    else:
        from ohlab.optics.fresnel_interface import UnsupportedPolarizationNumericsError
        with pytest.raises(UnsupportedPolarizationNumericsError):apply_fresnel_interface(state,algebra_geometry(state,1.,1.5))


def test_positive_tiny_carried_C_underflow_fails_instead_of_dropping_reflected_child():
    from ohlab.optics.fresnel_interface import UnsupportedPolarizationNumericsError
    state=algebra_state(math.atan(1.5),(0.,1e-300,0.,0.))
    with pytest.raises(UnsupportedPolarizationNumericsError,match="reliably"):
        apply_fresnel_interface(state,algebra_geometry(state,1.,1.5))
