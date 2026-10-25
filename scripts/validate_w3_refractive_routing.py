"""Independent W3 stored-input references and bounded shipped-operator evidence.

This script is outside the numerical core. References use Decimal90 finite
halfspaces and normalized scalar tangent/normal Snell, independently of the
production polygon/Gram/homogeneous implementation. It creates a fresh output
directory exclusively; it never overwrites earlier evidence or changes sources.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from decimal import Decimal, localcontext
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import sys
import time
import traceback

from ohlab.optics import refractive_routing
from ohlab.optics.geometric_routing import (
    CertifiedInterval, certify_ray, certify_vector, certified_point_at,
)

POSITION_ATOL_M = 5e-12
DIRECTION_ATOL = 2e-12
RTOL = 2e-12
ANGLE_ATOL_RAD = 2e-12
DECIMAL_PRECISION = 90


def fixtures() -> dict[str, dict]:
    """Exact original five fixed receiver inputs, plus declared bounded cases."""
    source = {"id": "source", "origin_m": [.02,.08,-.04], "direction": [0.,0.,1.], "relative_weight": 1}
    body = {"id": "B1", "kind": "right_triangular_prism", "pose": {"position_m": [0.,.08,0.], "rotation_xyz_rad": [0.,0.,0.]},
            "shape": {"leg_x_m": .08, "leg_z_m": .08, "height_y_m": .04}, "interior_medium": {"id": "body:B1", "refractive_index": 1.2}}
    receiver = {"id": "D1", "kind": "receiver", "pose": {"position_m": [0.,.08,.12], "rotation_xyz_rad": [0.,0.,0.]},
                "aperture": {"kind": "disk", "radius_m": .01}}
    b = {"schema_version": 1, "model_contract": "w3_ideal_refractive_routing_v1", "source": source,
         "exterior_medium": {"id": "exterior", "refractive_index": 1}, "bodies": [body], "elements": [receiver]}
    a = deepcopy(b)
    a["source"].update(origin_m=[-.015,.08,-.04], direction=[.49999999999999994,0.,.8660254037844387])
    a["bodies"][0].update(kind="rectangular_block", shape={"width_x_m": .12,"height_y_m": .08,"depth_z_m": .03})
    a["bodies"][0]["pose"]["position_m"] = [0.,.08,.015]
    a["bodies"][0]["interior_medium"]["refractive_index"] = 1.5
    a["elements"][0]["pose"]["position_m"] = [.07066213671244954,.08,.12]
    c = deepcopy(b); c["bodies"][0]["interior_medium"]["refractive_index"] = 1.5
    c["elements"][0]["pose"].update(position_m=[-.04,.08,.06], rotation_xyz_rad=[0.,1.5707963267948966,0.])
    index = deepcopy(b); index["bodies"][0]["interior_medium"]["refractive_index"] = 1.3
    pose = deepcopy(b); pose["bodies"][0]["pose"]["rotation_xyz_rad"][1] = .17453292519943295
    result = {"A_slab": a, "B_prism": b, "C_TIR": c, "B_index1.3": index, "B_yaw10": pose}
    d = deepcopy(c); d["elements"] = []
    d["bodies"][0]["shape"]["leg_x_m"] = .02
    d["source"].update(origin_m=[.004,.08,-.02])
    result["D_multiple_returns"] = d
    normal = deepcopy(a); normal["elements"] = []; normal["source"].update(origin_m=[0.,.08,-.04], direction=[0.,0.,1.])
    result["normal"] = normal
    equal = deepcopy(a); equal["elements"] = []; equal["bodies"][0]["interior_medium"]["refractive_index"] = 1.
    result["equal_index"] = equal
    exterior = deepcopy(a); exterior["elements"] = []
    theta = math.radians(50.)
    exterior["source"].update(origin_m=[-.04*math.tan(theta),.08,-.04], direction=[math.sin(theta),0.,math.cos(theta)])
    exterior["exterior_medium"]["refractive_index"] = 1.5
    exterior["bodies"][0]["interior_medium"]["refractive_index"] = 1.
    result["exterior_TIR"] = exterior
    side = deepcopy(a); side["elements"] = []; side["source"]["origin_m"] = [.059,.08,-.001]
    result["block_side"] = side
    end = deepcopy(b); end["elements"] = []
    end["source"].update(origin_m=[.02,.099,-.001], direction=[0.,math.sin(math.pi/6),math.cos(math.pi/6)])
    result["triangle_end_hit"] = end
    miss = deepcopy(b); miss["elements"] = []; miss["source"].update(origin_m=[.07,.03,.07], direction=[0.,1.,0.])
    result["triangle_end_miss"] = miss
    plane = deepcopy(a); plane["elements"] = []; plane["source"].update(origin_m=[.2,.08,-.04], direction=[0.,0.,1.])
    result["finite_plane_miss"] = plane
    combined = deepcopy(b); combined["elements"] = []
    angles = [.13,-.21,.17]
    matrix = stored_matrix(angles)
    # Rotate the entire local experiment once, without normalizing the result.
    combined["bodies"][0]["pose"].update(position_m=[.03,.08,.01], rotation_xyz_rad=angles)
    combined["source"]["origin_m"] = [math.fsum(matrix[i][j]*[.02,0.,-.04][j] for j in range(3))+[.03,.08,.01][i] for i in range(3)]
    combined["source"]["direction"] = [matrix[i][2] for i in range(3)]
    result["combined_XYZ_pose"] = combined
    return result


def stored_matrix(angles):
    """Independent explicit axis matrices with the frozen stored operation order."""
    x,y,z = angles
    sx,cx,sy,cy,sz,cz = math.sin(x),math.cos(x),math.sin(y),math.cos(y),math.sin(z),math.cos(z)
    rx=((1.,0.,0.),(0.,cx,-sx),(0.,sx,cx)); ry=((cy,0.,sy),(0.,1.,0.),(-sy,0.,cy)); rz=((cz,-sz,0.),(sz,cz,0.),(0.,0.,1.))
    def mul(a,b):
        return tuple(tuple(math.fsum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)) for i in range(3))
    return mul(rz,mul(ry,rx))


def dec(value):
    return Decimal.from_float(float(value))


def dot(a,b):
    return sum((x*y for x,y in zip(a,b)),Decimal(0))


def add(a,b):
    return [x+y for x,y in zip(a,b)]


def sub(a,b):
    return [x-y for x,y in zip(a,b)]


def scale(a,b):
    return [x*b for x in a]


def inverse(matrix):
    a,b,c=matrix[0]; d,e,f=matrix[1]; g,h,i=matrix[2]
    adj=((e*i-f*h,c*h-b*i,b*f-c*e),(f*g-d*i,a*i-c*g,c*d-a*f),(d*h-e*g,b*g-a*h,a*e-b*d))
    det=a*adj[0][0]+b*adj[1][0]+c*adj[2][0]
    return [[x/det for x in row] for row in adj]


def decimal_trace(scene: dict) -> list[dict]:
    """Independent Decimal90 finite halfspaces and scalar Snell construction.

    Only body events are returned; fixed receiver comparison separately uses
    the actual stored receiver plane and its finite disk. No production
    geometry, normal, inverse, event or operator supplies reference values.
    """
    with localcontext() as ctx:
        ctx.prec=DECIMAL_PRECISION
        body=scene["bodies"][0]; shape=body["shape"]
        B=[[dec(x) for x in row] for row in stored_matrix(body["pose"]["rotation_xyz_rad"])]
        inv=inverse(B); translation=list(map(dec,body["pose"]["position_m"]))
        if body["kind"]=="rectangular_block":
            local=[(name,list(map(Decimal,a)),dec(shape[key])/2) for name,a,key in
                   (("x_min",[-1,0,0],"width_x_m"),("x_max",[1,0,0],"width_x_m"),
                    ("y_min",[0,-1,0],"height_y_m"),("y_max",[0,1,0],"height_y_m"),
                    ("z_min",[0,0,-1],"depth_z_m"),("z_max",[0,0,1],"depth_z_m"))]
        else:
            x,z,h=(dec(shape[key]) for key in ("leg_x_m","leg_z_m","height_y_m")); zero=Decimal(0); one=Decimal(1)
            local=[("x_min",[-one,zero,zero],zero),("z_min",[zero,zero,-one],zero),
                   ("hypotenuse",[z,zero,x],x*z),("y_min",[zero,-one,zero],h/2),("y_max",[zero,one,zero],h/2)]
        planes=[]
        for name,a,b in local:
            m=[sum((inv[j][i]*a[j] for j in range(3)),Decimal(0)) for i in range(3)]
            planes.append((name,m,b+dot(m,translation)))
        origin=list(map(dec,scene["source"]["origin_m"])); direction=list(map(dec,scene["source"]["direction"]))
        previous=None; medium="exterior"; records=[]
        ne=dec(scene["exterior_medium"]["refractive_index"]); nb=dec(body["interior_medium"]["refractive_index"])
        for _ in range(32):
            candidates=[]
            for name,m,b in planes:
                if name==previous or dot(m,direction)==0:
                    continue
                t=(b-dot(m,origin))/dot(m,direction)
                if t<=0: continue
                point=add(origin,scale(direction,t))
                if any(dot(other,point)-offset>0 for other_name,other,offset in planes if other_name!=name): continue
                candidates.append((t,name,m,point))
            if not candidates: break
            t,name,m,point=min(candidates,key=lambda row:row[0])
            entering=medium=="exterior"; a=m if entering else scale(m,Decimal(-1))
            n1,n2=(ne,nb) if entering else (nb,ne)
            magnitude=dot(direction,direction).sqrt(); normal=scale(a,1/dot(a,a).sqrt()); unit=scale(direction,1/magnitude)
            cosine=-dot(unit,normal); tangent=add(unit,scale(normal,cosine)); rho=n1/n2
            k=1-rho*rho*dot(tangent,tangent)
            before=medium
            if n1==n2:
                out=direction[:]; classification="enter_refraction" if entering else "exit_refraction"; medium="body:B1" if entering else "exterior"
            elif k<0:
                out=scale(add(unit,scale(normal,2*cosine)),magnitude); classification="total_internal_reflection"
            else:
                out=scale(sub(scale(tangent,rho),scale(normal,k.sqrt())),magnitude)
                classification="enter_refraction" if entering else "exit_refraction"; medium="body:B1" if entering else "exterior"
            outward=scale(m,1/dot(m,m).sqrt())
            records.append({"face":name,"point":point,"incoming":direction,"outgoing":out,"outward_normal":outward,
                            "incident_index":n1,"candidate_index":n2,"incident_medium":before,"outgoing_medium":medium,
                            "classification":classification,"unit_discriminant":k})
            origin,direction,previous=point,out,name
        return records


def _contains(pair, value):
    return dec(pair[0]) <= value <= dec(pair[1])


def compare_case(name: str, scene: dict) -> dict:
    actual=refractive_routing.trace_routes(refractive_routing.RefractiveScene.from_dict(scene))
    reference=decimal_trace(scene)
    events=[x for x in actual.events if x["target"]["kind"]=="body_face"]
    assert len(events)==len(reference),(name,"event count",len(events),len(reference))
    position_errors=[]; direction_errors=[]; angle_errors=[]
    for event,ref in zip(events,reference):
        assert event["target"]["face_id"]==ref["face"]
        assert event["classification"]==ref["classification"]
        assert event["incident_medium_id"]==ref["incident_medium"]
        assert event["outgoing"][0]["medium_id"]==ref["outgoing_medium"]
        with localcontext() as ctx:
            ctx.prec=DECIMAL_PRECISION
            n=ref["outward_normal"];d=ref["incoming"]
            cross=[d[j]*n[k]-d[k]*n[j] for j,k in ((1,2),(2,0),(0,1))]
            sine=dot(cross,cross).sqrt()/dot(d,d).sqrt()
            cosine=abs(dot(d,n))/dot(d,d).sqrt()
            incidence=math.atan2(float(sine),float(cosine))
            outgoing_angle=incidence if ref["classification"]=="total_internal_reflection" else math.asin(float(ref["incident_index"]/ref["candidate_index"])*float(sine))
        for observed,expected in ((event["incident_angle_rad"],incidence),(event["outgoing_angle_rad"],outgoing_angle)):
            error=abs(observed-expected);angle_errors.append(error)
            assert error <= ANGLE_ATOL_RAD+RTOL*abs(expected),(name,"scalar angle identity",error)
        for axis in range(3):
            pe=abs(dec(event["position_m"][axis])-ref["point"][axis])
            de=abs(dec(event["outgoing"][0]["direction"][axis])-ref["outgoing"][axis])
            position_errors.append(float(pe)); direction_errors.append(float(de))
            assert pe <= dec(POSITION_ATOL_M)+dec(RTOL)*abs(ref["point"][axis])
            assert de <= dec(DIRECTION_ATOL)+dec(RTOL)*abs(ref["outgoing"][axis])
            assert _contains(event["numerical_bounds"]["position_intervals_m"][axis],ref["point"][axis]),(name,"point enclosure",axis)
            assert _contains(event["numerical_bounds"]["outgoing_direction_intervals"][0]["direction_intervals"][axis],ref["outgoing"][axis]),(name,"direction enclosure",axis)
    if scene["elements"]:
        assert actual.terminals[0]["category"]=="detected"
        receiver=scene["elements"][0]; matrix=stored_matrix(receiver["pose"]["rotation_xyz_rad"])
        with localcontext() as ctx:
            ctx.prec=DECIMAL_PRECISION
            center=list(map(dec,receiver["pose"]["position_m"])); n=[dec(row[2]) for row in matrix]
            final=reference[-1]; t=dot(sub(center,final["point"]),n)/dot(final["outgoing"],n)
            p=add(final["point"],scale(final["outgoing"],t)); q=sub(p,center)
            uv=[dot(q,[dec(row[j]) for row in matrix]) for j in (0,1)]
            assert dot(uv,uv)<dec(receiver["aperture"]["radius_m"])**2
            assert all(abs(dec(a)-b)<=dec(POSITION_ATOL_M)+dec(RTOL)*abs(b) for a,b in zip(actual.terminals[0]["position_m"],p))
    return {"name":name,"source":scene,"body_faces":[x["target"]["face_id"] for x in events],
            "classifications":[x["classification"] for x in events],"status":actual.status,"terminal":actual.terminals[0].to_dict(),
            "max_position_error_m":max(position_errors,default=0.),"max_direction_error":max(direction_errors,default=0.),
            "max_scalar_angle_error_rad":max(angle_errors,default=0.),
            "all_reference_components_enclosed":True,"diagnostics":actual.diagnostics.to_dict(),
            "reference":[{key:[str(v) for v in value] if isinstance(value,list) else str(value) if isinstance(value,Decimal) else value for key,value in row.items()} for row in reference]}


def slab_displacement_reference() -> dict:
    """Measured perpendicular displacement, stored-input and ideal30deg targets."""
    scene=fixtures()["A_slab"]
    result=refractive_routing.trace_routes(refractive_routing.validate_scene(scene))
    entry,exit=result.events[:2]; direction=scene["source"]["direction"]
    step=[b-a for a,b in zip(entry["position_m"],exit["position_m"])]
    cross=[step[j]*direction[k]-step[k]*direction[j] for j,k in ((1,2),(2,0),(0,1))]
    measured=math.hypot(*cross)/math.hypot(*direction)
    with localcontext() as ctx:
        ctx.prec=DECIMAL_PRECISION
        d=list(map(dec,direction));magnitude=dot(d,d).sqrt();si=d[0]/magnitude;ci=d[2]/magnitude
        st=si/dec(1.5);ct=(1-st*st).sqrt();thickness=dec(.03)
        stored=thickness*(si-ci*st/ct)
        ideal=Decimal("0.03")*(Decimal(1)/2-(Decimal(3).sqrt()/2)*(Decimal(1)/3)/(Decimal(8).sqrt()/3))
        error=abs(dec(measured)-stored)
        assert error<=dec(POSITION_ATOL_M)+dec(RTOL)*abs(stored)
        parallel=max(abs(a-b) for a,b in zip(exit["outgoing"][0]["direction"],direction))
        assert parallel<=DIRECTION_ATOL+RTOL
        assert abs(measured-.005814413464563081)<=POSITION_ATOL_M+RTOL*abs(measured)
        return {"measured_perpendicular_displacement_m":measured,"exact_stored_input_reference_m":str(stored),
                "stored_reference_error_m":str(error),"ideal_real_30deg_exact_0.03m_reference_m":str(ideal),
                "ideal_target_qualification":"separate ideal real30deg input, not the stored source direction or stored .03 binary64 thickness",
                "parallel_emergence_max_direction_difference":parallel}


def operator_stress() -> dict:
    """Exact planned .03m/30-degree alternating chain; not a closed-body scene."""
    origin=certify_vector((0.,0.,0.)); direction=certify_vector((.49999999999999994,0.,.8660254037844387))
    records=[]
    for step in range(32):
        z=.03*(step+1)
        parameter=(z-origin.nominal[2])/direction.nominal[2]
        bound=(CertifiedInterval.point(z)-origin.bounds[2])/direction.bounds[2]
        ray=certify_ray(origin=origin,direction=direction,cumulative_length_m=0.,cumulative_bounds=CertifiedInterval.point(0.),previous_face_id=None)
        origin=certified_point_at(ray,parameter,bound)
        entering=step%2==0; outward=certify_vector((0.,0.,-1. if entering else 1.))
        n1,n2=(1.,1.5) if entering else (1.5,1.)
        try:
            direction,_,ki,_,_=refractive_routing._dielectric_direction(direction,outward,n1,n2,entering)
            refractive_routing._admit_vector(origin,position=True)
        except refractive_routing.UnsupportedNumericalInputError as exc:
            return {"interpretation":"algebraic operator chain, not a realizable closed-body scene; stops on first actual admission failure",
                    "first_failure_operation":step+1,"error_type":type(exc).__name__,"message":str(exc),"accepted_prefix":records}
        records.append({"operation":step+1,"point_width_m":max(i.hi-i.lo for i in origin.bounds),
                        "direction_width":max(i.hi-i.lo for i in direction.bounds),"K_interval":ki.pair()})
    raise AssertionError("planned stress unexpectedly passed all32 operations")


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=False,exist_ok=False)
    declared={"position_atol_m":POSITION_ATOL_M,"direction_atol":DIRECTION_ATOL,"rtol":RTOL,"angle_atol_rad":ANGLE_ATOL_RAD,
              "decimal_precision":DECIMAL_PRECISION,"timing_repetitions":25,"retries":0,"source":str(Path(__file__).resolve()),
              "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"python":sys.version,"platform":platform.platform()}
    (args.output/"predeclared.json").write_text(json.dumps(declared,indent=2)+"\n",encoding="utf-8")
    results={"scope":"shipped W3 numerical validation, not browser or GPU evidence","cases":[],"failures":[],"timing":[]}
    inputs=fixtures()
    (args.output/"inputs.json").write_text(json.dumps(inputs,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    for name,scene in inputs.items():
        try:
            record=compare_case(name,scene); results["cases"].append(record)
            print(name,"PASS",record["body_faces"],"position_error_m",record["max_position_error_m"],"direction_error",record["max_direction_error"])
        except Exception as exc:
            results["failures"].append({"case":name,"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()})
            print(name,"FAILED",type(exc).__name__,exc)
    try:
        results["slab_displacement"]=slab_displacement_reference()
        print("slab_displacement PASS",results["slab_displacement"]["measured_perpendicular_displacement_m"],"metres")
    except Exception as exc:
        results["failures"].append({"case":"slab_displacement","type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()})
        print("slab_displacement FAILED",type(exc).__name__,exc)
    try:
        stress=operator_stress();results["stress"]=stress
        assert stress["first_failure_operation"]==14,stress
        print("operator_stress PASS first admission failure",stress["first_failure_operation"])
    except Exception as exc:
        results["failures"].append({"case":"operator_stress","type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()})
        print("operator_stress FAILED",type(exc).__name__,exc)
    for name in ("A_slab","B_prism","C_TIR","D_multiple_returns"):
        try:
            validated=refractive_routing.RefractiveScene.from_dict(inputs[name]); samples=[]
            for _ in range(25):
                start=time.perf_counter();value=refractive_routing.trace_routes(validated);samples.append(time.perf_counter()-start)
            results["timing"].append({"name":name,"seconds_raw":samples,"median_s":statistics.median(samples),
                                       "scope":"public trace including its revalidation; excluding Decimal, encoding, browser and network",
                                       "actual_core_json_bytes":len(json.dumps(value.to_dict(),separators=(",",":"),allow_nan=False).encode())})
        except Exception as exc:
            results["failures"].append({"case":name+" timing","type":type(exc).__name__,"message":str(exc)})
    (args.output/"results.json").write_text(json.dumps(results,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("SUMMARY",len(results["cases"]),"reference cases",len(results["failures"]),"failures")
    return int(bool(results["failures"]))


if __name__=="__main__":
    raise SystemExit(main())
