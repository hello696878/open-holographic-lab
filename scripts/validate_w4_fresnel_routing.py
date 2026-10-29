"""Independent W4 Decimal references, fixed apparatus and exclusive evidence.

Run with --output-dir pointing to a fresh task-owned directory. This validator
is outside the numerical core. Its references do not call production Fresnel
helpers and do not fill finite paths with infinite slab sums.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from decimal import Decimal, localcontext
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import time
import tracemalloc

from ohlab.optics.fresnel_interface import fresnel_coefficients
from ohlab.optics.fresnel_routing import FresnelScene,trace_fresnel_scene
from ohlab.optics.geometric_routing import certify_vector

POWER_ATOL=2e-13
RTOL=2e-12
WEAK_RTOL=2e-11
POSITION_ATOL_M=5e-12


def fixtures() -> dict[str,dict]:
    """Frozen admitted W4 apparatus, SI; no target follows the calculated path."""
    source={"id":"source","origin_m":[0.,.08,-.04],"direction":[0.,0.,1.],
            "frame_policy":"world_xy_forward_z_v1","polarization":"unpolarized"}
    block={"id":"B1","kind":"rectangular_block","pose":{"position_m":[0.,.08,.015],"rotation_xyz_rad":[0.,0.,0.]},
        "shape":{"width_x_m":.12,"height_y_m":.08,"depth_z_m":.03},"interior_medium":{"id":"body:B1","refractive_index":1.5}}
    detector={"id":"D1","kind":"receiver","pose":{"position_m":[0.,.08,.12],"rotation_xyz_rad":[0.,0.,0.]},
              "aperture":{"kind":"disk","radius_m":.01}}
    reflected=deepcopy(detector);reflected["id"]="R1";reflected["pose"]["position_m"]=[0.,.08,-.12]
    normal={"schema_version":1,"model_contract":"w4_fresnel_polarized_routing_v1","source":source,
        "exterior_medium":{"id":"exterior","refractive_index":1.},"bodies":[block],"elements":[detector,reflected],
        "path_addition":"incoherent_phase_averaged_v1"}
    prism=deepcopy(normal)
    prism["source"]["origin_m"]=[.02,.08,-.04]
    prism["bodies"][0].update(kind="right_triangular_prism",shape={"leg_x_m":.08,"leg_z_m":.08,"height_y_m":.04})
    prism["bodies"][0]["pose"]["position_m"]=[0.,.08,0.]
    prism["bodies"][0]["interior_medium"]["refractive_index"]=1.2
    prism["elements"]=[deepcopy(detector)]
    tir=deepcopy(prism);tir["bodies"][0]["interior_medium"]["refractive_index"]=1.5
    tir["elements"][0]["pose"].update(position_m=[-.04,.08,.06],rotation_xyz_rad=[0.,math.pi/2,0.])
    e1=deepcopy(normal);e1["source"]["polarization"]="linear_e1";e1["bodies"][0]["pose"]["rotation_xyz_rad"][1]=math.radians(56.)
    e2=deepcopy(e1);e2["source"]["polarization"]="linear_e2"
    equal=deepcopy(normal);equal["bodies"][0]["interior_medium"]["refractive_index"]=1.
    empty=deepcopy(normal);empty["bodies"]=[];empty["elements"]=[]
    stop=deepcopy(normal);stop["elements"][0]["kind"]="beam_stop"
    miss=deepcopy(normal);miss["elements"]=[]
    xyz=deepcopy(normal);xyz["elements"]=[];xyz["bodies"][0]["pose"]["rotation_xyz_rad"]=[.13,-.21,.17]
    return {"normal_slab":normal,"refracting_prism":prism,"tir_prism":tir,"brewster_e1":e1,"brewster_e2":e2,
            "equal_index":equal,"empty":empty,"beam_stop":stop,"finite_miss":miss,"xyz_pose":xyz}


def decimal_coefficients(direction: list[float],covector: list[float],ni: float,nt: float) -> dict:
    """Independent Decimal90 direct square-root formulas on exact stored inputs."""
    with localcontext() as ctx:
        ctx.prec=90
        d,a=([Decimal.from_float(float(x)) for x in v] for v in (direction,covector))
        n,t=Decimal.from_float(ni),Decimal.from_float(nt)
        dot=sum((x*y for x,y in zip(d,a)),Decimal(0))
        ci=-dot/(sum((x*x for x in d),Decimal(0))*sum((x*x for x in a),Decimal(0))).sqrt()
        k=1-(n/t)**2*(1-ci*ci)
        if k>=0:
            ct=k.sqrt();ds=n*ci+t*ct;dp=t*ci+n*ct
            rs=(n*ci-t*ct)/ds;rp=(t*ci-n*ct)/dp;ts=2*n*ci/ds;tp=2*n*ci/dp;g=t*ct/(n*ci)
            return {"rs":rs,"rp":rp,"ts":ts,"tp":tp,"Rs":rs*rs,"Rp":rp*rp,"Ts":g*ts*ts,"Tp":g*tp*tp}
        gamma=(-k).sqrt()
        def pair(x,y):return ((x*x-y*y)/(x*x+y*y),-2*x*y/(x*x+y*y))
        return {"rs_pair":pair(n*ci,t*gamma),"rp_pair":pair(t*ci,n*gamma)}


def weak_fixtures() -> list[tuple[str,list[float]]]:
    """Exactly the seven predeclared Brewster-neighborhood stored directions."""
    center=math.atan(1.5)
    angles=[("minus1e-6",center-1e-6),("minus1e-10",center-1e-10),("next_below",math.nextafter(center,0.)),
            ("stored_atan_label",center),("next_above",math.nextafter(center,math.inf)),("plus1e-10",center+1e-10),("plus1e-6",center+1e-6)]
    return [(name,[math.sin(angle),0.,math.cos(angle)]) for name,angle in angles]


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",required=True,type=Path)
    args=parser.parse_args()
    out=args.output_dir.resolve();out.mkdir(parents=False,exist_ok=False)
    fixed=fixtures()
    with (out/"predeclared.json").open("x",encoding="utf-8") as handle:
        json.dump({"fixtures":fixed,"weak_fixtures":weak_fixtures(),"power_atol":POWER_ATOL,"rtol":RTOL,
            "weak_rtol":WEAK_RTOL,"weak_atol":0.,"position_atol_m":POSITION_ATOL_M,
            "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},handle,indent=2)
    rows=[];failures=[]
    for name,scene in fixed.items():
        try:
            before=deepcopy(scene);admitted=FresnelScene.from_dict(scene)
            tracemalloc.start();start=time.perf_counter();result=trace_fresnel_scene(admitted);elapsed=time.perf_counter()-start
            _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
            wire=result.to_dict()
            assert scene==before
            assert abs(wire["ledger"]["signed_residual"])<=POWER_ATOL
            assert wire["status"]==("incomplete" if wire["ledger"]["unresolved_power"]>0 else "complete")
            if name=="normal_slab":
                first=wire["events"][0]["interface"]["power_fractions"]
                assert abs(first["R_s"]-.04)<=2e-14 and abs(first["T_p"]-.96)<=2e-14
                direct=next(x for x in wire["terminals"] if x["branch_id"]=="r0.T.T")
                assert abs(direct["state"]["power_fraction"]-.9216)<=POWER_ATOL
                assert wire["ledger"]["unresolved_power"]>0
            if name=="tir_prism":
                assert any(x["classification"]=="total_internal_reflection" for x in wire["events"])
                assert any(x["interface"] is not None and x["interface"]["incidence_basis"] is not None and
                    x["interface"]["incidence_basis"]["normal_policy"]=="exact_owner_relation" and x["target"]["face_id"]=="x_min" for x in wire["events"])
            with (out/(name+".json")).open("x",encoding="utf-8") as handle:json.dump(wire,handle,indent=2,allow_nan=False)
            rows.append({"case":name,"status":wire["status"],"counts":{key:len(wire[key]) for key in ("branches","events","segments","terminals")},
                "ledger":wire["ledger"],"diagnostics":wire["diagnostics"],"trace_s_under_tracemalloc":elapsed,"python_tracemalloc_peak_bytes":peak,
                "compact_core_json_bytes":len(json.dumps(wire,separators=(",",":"),allow_nan=False).encode())})
            print(name,"PASS",wire["status"],wire["ledger"],flush=True)
        except Exception as exc:
            if tracemalloc.is_tracing():tracemalloc.stop()
            failures.append({"case":name,"type":type(exc).__name__,"message":str(exc)})
            print(name,"FAIL",type(exc).__name__,str(exc),flush=True)
    weak=[]
    for name,d in weak_fixtures():
        ref=decimal_coefficients(d,[0.,0.,-1.],1.,1.5)
        actual=fresnel_coefficients(certify_vector(tuple(d)),certify_vector((0.,0.,-1.)),1.,1.5)
        rp=abs(actual.r_p)**2;expected=float(ref["Rp"])
        relative=abs(rp-expected)/expected
        passed=rp>0 and relative<=WEAK_RTOL
        weak.append({"case":name,"direction":d,"signed_rp":actual.r_p.real,"reference_signed_rp":str(ref["rp"]),
            "Rp":rp,"reference_Rp":str(ref["Rp"]),"relative_error":relative,"passed":passed})
        if not passed:failures.append({"case":name,"type":"weak_reflection_reference","message":str(relative)})
    report={"rows":rows,"weak":weak,"failures":failures,"python":sys.version,
        "scope":"Current production core only; no protocol/HTTP/UI/browser/GPU measurement. Tracemalloc affects latency; historical planning timings remain distinct."}
    with (out/"results.json").open("x",encoding="utf-8") as handle:json.dump(report,handle,indent=2,allow_nan=False)
    print("W4_CORE_VALIDATION",len(rows),"routes",len(weak),"weak cases",len(failures),"failures",flush=True)
    return int(bool(failures))


if __name__=="__main__":
    raise SystemExit(main())
