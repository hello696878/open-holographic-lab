"""Independent W2 numeric/enclosure/resource evidence and isolated fault controls.

Run with the existing project interpreter and a new ``--output-dir``. No
server/browser is started. Optional genuine browser JSON is read, never
refetched. Independent expected intersections/reflections use Decimal160,
not production numerical helpers. Faults execute only newly owned copies.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import tracemalloc
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT/"src/ohlab/optics/geometric_routing.py"


def face(identity: str, kind: str, position: Any, y: float = 0., *, angles: Any = None, radius: float = .025) -> dict[str, Any]:
    return {"id": identity, "kind": kind,
            "pose": {"position_m": list(position), "rotation_xyz_rad": list(angles if angles is not None else (0., y, 0.))},
            "aperture": {"kind": "disk", "radius_m": radius}}


def scene(elements: Any = (), *, origin: Any = (0., .08, 0.), direction: Any = (0., 0., 1.)) -> dict[str, Any]:
    return {"schema_version": 1, "model_contract": "w2_ideal_geometric_routing_v1",
            "source": {"id": "source", "origin_m": list(origin), "direction": list(direction), "relative_weight": 1.},
            "elements": list(elements)}


def fixtures() -> dict[str, Any]:
    first = face("M1", "mirror", (0., .08, .2), -math.pi/4)
    common = [face("S", "ideal_splitter_50_50", (0., .08, .2), -math.pi/4),
              face("DT", "receiver", (0., .08, .4), math.pi), face("DR", "receiver", (.2, .08, .2), -math.pi/2)]
    return {"A": scene([first, face("D", "receiver", (.2, .08, .2), -math.pi/2)]),
            "B": scene([first, face("M2", "mirror", (.2, .08, .2), 3*math.pi/4), face("D", "receiver", (.2, .08, .4), math.pi)]),
            "C": scene(common), "C_blocked": scene([*common, face("stop", "beam_stop", (.1, .08, .2), -math.pi/2)]),
            "miss": scene([face("D", "receiver", (.06, .08, .2))]),
            "nearest": scene([face("far", "beam_stop", (0., .08, .4)), face("near", "receiver", (0., .08, .2))]),
            "revisit32": scene([face("plus", "mirror", (0., .08, .1)), face("minus", "mirror", (0., .08, -.1))]),
            "distance": scene([face("plus", "mirror", (0., .08, .8)), face("minus", "mirror", (0., .08, -.8))]),
            "branch63": scene([face("plus", "ideal_splitter_50_50", (0., .08, .1)), face("minus", "ideal_splitter_50_50", (0., .08, -.1))]),
            "nearby": scene([face("S", "ideal_splitter_50_50", (0., .08, .2)), face("near", "receiver", (0., .08, .2+1e-12))]),
            "off_axis": scene([face("D", "receiver", (0., .08, .2))], origin=(.006, .076, 0.))}


def matrix(angles: Any) -> list[list[float]]:
    x, y, z = angles
    sx,cx,sy,cy,sz,cz = math.sin(x),math.cos(x),math.sin(y),math.cos(y),math.sin(z),math.cos(z)
    return [[cz*cy,cz*sy*sx-sz*cx,cz*sy*cx+sz*sx], [sz*cy,sz*sy*sx+cz*cx,sz*sy*cx-cz*sx], [-sy,cy*sx,cy*cx]]


def oblique32() -> dict[str, Any]:
    angles=(.23,-.41,.37);m=matrix(angles)
    normal=[row[2] for row in m];u=[row[0] for row in m]
    direction=[.95*n+math.sqrt(1-.95**2)*t for n,t in zip(normal,u)]
    norm=math.hypot(*direction);direction=[x/norm for x in direction]
    origin=(0.,.08,0.)
    elements=[face("plus","mirror",[o+.01*n for o,n in zip(origin,normal)],angles=angles,radius=.25),
              face("minus","mirror",[o-.01*n for o,n in zip(origin,normal)],angles=angles,radius=.25)]
    return scene(elements,origin=origin,direction=direction)


def record_loop() -> dict[str, Any]:
    vertices=[(0.,0.),(.3,0.),(.3,.2),(.2,.3),(0.,.3),(0.,0.)]
    mirrors=[]
    for sign in (1.,-1.):
        points=[(sign*x,sign*z) for x,z in vertices]
        for i in range(1,5):
            before,point,after=points[i-1],points[i],points[i+1]
            a=[point[j]-before[j] for j in range(2)];b=[after[j]-point[j] for j in range(2)]
            aa,bb=math.hypot(*a),math.hypot(*b)
            normal=[x/aa-y/bb for x,y in zip(a,b)]
            theta=math.atan2(normal[0],normal[1])
            mirrors.append(face(f"M{'p' if sign>0 else 'n'}{i}","mirror",(point[0],.08,point[1]),theta))
    return scene([face("S","ideal_splitter_50_50",(0.,.08,0.),-math.pi/4),*mirrors],origin=(0.,.08,-.05))


def D(value: float) -> Decimal:
    return Decimal.from_float(float(value))


def inside(bounds: Any, exact: Decimal) -> None:
    assert D(bounds[0])<=exact<=D(bounds[1]),(bounds,str(exact))


def chain_reference(result: Any, submitted: Any, expected_ids: Any, frame_target: str = "stored") -> dict[str, Any]:
    """Stored-frame Decimal160 reference, independent of production geometry."""
    frames={f["element_id"]:f for f in result.surface_frames}
    elements={e["id"]:e for e in submitted["elements"]}
    max_point_error=0.;max_direction_error=0.
    with localcontext() as ctx:
        ctx.prec=160
        origin=list(map(D,submitted["source"]["origin_m"]))
        direction=list(map(D,submitted["source"]["direction"]))
        cumulative=Decimal(0)
        dot=lambda a,b:sum(x*y for x,y in zip(a,b))
        for ordinal,identity in enumerate(expected_ids):
            frame=frames[identity]
            if frame_target=="stored":
                normal,u,v=[list(map(D,frame[key])) for key in ("n","u","v")]
            else:
                def trig(value: float, cosine: bool=False) -> Decimal:
                    x=D(value)
                    return sum(Decimal((-1)**k)*(Decimal(1) if 2*k+(0 if cosine else 1)==0 else x**(2*k+(0 if cosine else 1)))
                               /Decimal(math.factorial(2*k+(0 if cosine else 1))) for k in range(100))
                x,y,z=elements[identity]["pose"]["rotation_xyz_rad"]
                sx,sy,sz=[trig(a) for a in (x,y,z)];cx,cy,cz=[trig(a,True) for a in (x,y,z)]
                m=((cz*cy,cz*sy*sx-sz*cx,cz*sy*cx+sz*sx),(sz*cy,sz*sy*sx+cz*cx,sz*sy*cx-cz*sx),(-sy,cy*sx,cy*cx))
                normal,u,v=[[m[i][j] for i in range(3)] for j in (2,0,1)]
            center=list(map(D,elements[identity]["pose"]["position_m"]))
            t=dot([c-o for c,o in zip(center,origin)],normal)/dot(direction,normal)
            point=[o+t*d for o,d in zip(origin,direction)]
            local=[dot([p-c for p,c in zip(point,center)],u),dot([p-c for p,c in zip(point,center)],v)]
            length=sum((p-o)**2 for p,o in zip(point,origin)).sqrt();cumulative+=length
            hit,cert=result.hits[ordinal],result.certificates[ordinal]
            assert hit["element_id"]==identity
            inside(hit["numerical_bounds"]["t_parameter_interval_m"],t)
            for j in range(3):
                inside(cert["start_intervals_m"][j],origin[j]);inside(cert["direction_intervals"][j],direction[j])
                inside(hit["numerical_bounds"]["position_intervals_m"][j],point[j])
                max_point_error=max(max_point_error,abs(float(point[j])-hit["position_m"][j]))
            for j in range(2):inside(hit["numerical_bounds"]["local_uv_intervals_m"][j],local[j])
            inside(cert["length_interval_m"],length);inside(cert["cumulative_interval_m"],cumulative)
            if elements[identity]["kind"]=="mirror":
                dn=dot(direction,normal);direction=[d-2*dn*n for d,n in zip(direction,normal)]
                for j in range(3):
                    inside(cert["outgoing_direction_intervals"][0][j],direction[j])
                    max_direction_error=max(max_direction_error,abs(float(direction[j])-hit["outgoing"][0]["direction"][j]))
            origin=point
    return {"interactions":len(expected_ids),"reference_target":frame_target,"reference_precision_decimal_digits":160,"cumulative_length_m":float(cumulative),
            "max_nominal_point_error_m":max_point_error,"max_nominal_direction_error":max_direction_error,
            "all_propagated_pose_ray_hit_local_reflection_length_certificates_contain_reference":True}


def _evaluate(module: Any, name: str) -> Any:
    data=fixtures()
    submitted=record_loop() if name=="record256" else oblique32() if name=="oblique32" else data.get(name)
    if submitted is None and name=="pose":
        submitted=scene([face("M","mirror",(0.,.08,.2),angles=(.23,-.41,.37))])
    try:
        result=module.trace_routes(module.GeometricScene.from_dict(submitted))
    except ValueError as exc:
        raise AssertionError(f"valid {name} fixture unexpectedly failed numerical execution: {type(exc).__name__}: {exc}") from exc
    ledger=result.ledger
    assert abs(ledger["signed_residual"])<=64*math.ulp(1.)
    assert math.fsum(t["relative_weight"] for t in result.terminals)==1.
    if name=="A":assert ledger["detected_weight"]==1. and len(result.hits)==2
    elif name=="B":assert [h["element_id"] for h in result.hits]==["M1","M2","D"]
    elif name=="C":assert ledger["detected_weight"]==1. and [t["relative_weight"] for t in result.terminals]==[.5,.5]
    elif name=="C_blocked":assert ledger["detected_weight"]==ledger["absorbed_weight"]==.5
    elif name=="miss":assert ledger["escaped_weight"]==1. and not result.hits
    elif name=="nearest":assert result.hits[0]["element_id"]=="near"
    elif name in ("revisit32","oblique32"):
        assert len(result.hits)==32 and result.status=="incomplete" and ledger["truncated_weight"]==1.
        assert result.terminals[0]["reason"]=="interaction_cap"
        chain_reference(result,submitted,["plus","minus"]*16)
    elif name=="distance":assert result.terminals[0]["reason"]=="distance_cap" and result.segments[-1]["hit_id"] is None
    elif name=="branch63":assert len(result.branches)==63 and any(t["reason"]=="branch_cap" for t in result.terminals)
    elif name=="record256":assert len(result.hits)+len(result.segments)==256 and any(t["reason"]=="record_cap" for t in result.terminals)
    elif name=="nearby":assert ledger["detected_weight"]==.5 and any(h["element_id"]=="near" for h in result.hits)
    elif name=="off_axis":
        assert math.isclose(result.hits[0]["local_uv_m"][0],.006,rel_tol=2e-13,abs_tol=2e-13)
        assert math.isclose(result.hits[0]["local_uv_m"][1],-.004,rel_tol=2e-13,abs_tol=2e-13)
    elif name=="pose":
        expected=matrix((.23,-.41,.37));actual=result.surface_frames[0]
        for j,key in enumerate(("u","v","n")):
            for i in range(3):assert abs(actual[key][i]-expected[i][j])<2e-13
        # Independently computed high-precision real-angle rotation must fit.
        with localcontext() as ctx:
            ctx.prec=160
            def trig(value,cosine=False):
                x=D(value)
                return sum(Decimal((-1)**k)*(Decimal(1) if 2*k+(0 if cosine else 1)==0 else x**(2*k+(0 if cosine else 1)))
                           /Decimal(math.factorial(2*k+(0 if cosine else 1))) for k in range(100))
            x,y,z=(.23,-.41,.37);sx,sy,sz=[trig(a) for a in (x,y,z)];cx,cy,cz=[trig(a,True) for a in (x,y,z)]
            exact=((cz*cy,cz*sy*sx-sz*cx,cz*sy*cx+sz*sx),(sz*cy,sz*sy*sx+cz*cx,sz*sy*cx-cz*sx),(-sy,cy*sx,cy*cx))
            for i in range(3):
                for j in range(3):inside(result.scene.pose_certificates[0]["matrix_intervals"][i][j],exact[i][j])
    return result


def load_copy(path: Path) -> Any:
    spec=importlib.util.spec_from_file_location("w2_controlled_core_copy",path)
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


def negative_controls(output: Path) -> list[dict[str, Any]]:
    original=CORE.read_text(encoding="utf-8")
    original_hash=hashlib.sha256(CORE.read_bytes()).hexdigest()
    # Every patch applies only to the new task-owned source copy. The case
    # assertions are the same substantive assertions run above on real code.
    controls=[
        ("wrong_reflection","A",[("    return nominal, enclosed\n","    return direction, di\n")]),
        ("wrong_rotation_order","pose",[("    x, y, z = angles\n","    z, y, x = angles\n")]),
        ("wrong_local_basis","off_axis",[("local = (_dot(nominal_relative, surface.u), _dot(nominal_relative, surface.v))","local = (_dot(nominal_relative, surface.v), _dot(nominal_relative, surface.u))")]),
        ("infinite_aperture","miss",[("    return distance2.lo > surface.bounding_radius.square().hi","    return False"),
            ("if rho2.lo > radius2.hi:","if False:"),("if rho2.hi >= radius2.lo:","if False:")]),
        ("catalog_order","nearest",[("candidates.sort(key=lambda item: (item.ti.lo, item.surface.element[\"id\"]))","candidates.sort(key=lambda item: 0)"),
            ("if not best.ti.hi < candidate.ti.lo:","if False:")]),
        ("irrelevant_infinite_plane_rejection","B",[("surface.element[\"id\"] == state.previous or _finite_cull(state, surface, upper_t)","surface.element[\"id\"] == state.previous")]),
        ("suppressed_legitimate_revisit","revisit32",[("surface.element[\"id\"] == state.previous or _finite_cull(state, surface, upper_t)","surface.element[\"id\"] == state.previous or (state.interactions > 1 and surface.element[\"id\"] == 'plus') or _finite_cull(state, surface, upper_t)")]),
        ("arbitrary_origin_epsilon","nearby",[("if ti.hi < 0. or ti.lo > upper_t.hi:","if ti.hi < 0. or (0. < ti.hi < 1e-9) or ti.lo > upper_t.hi:")]),
        ("lost_split_weight","C",[("child_weight = state.weight/2.","child_weight = state.weight/4.")]),
        ("doubled_split_weight","C",[("child_weight = state.weight/2.","child_weight = state.weight")]),
        ("dropped_pending_branches","record256",[("terminal(queue.popleft(), \"resource_truncated\", reason)","queue.popleft()")]),
        ("truncated_as_complete","revisit32",[("\"incomplete\" if totals[\"truncated_weight\"] else \"complete\"","\"complete\"")]),
        ("truncated_as_absorption","revisit32",[("terminal(state, \"resource_truncated\", \"interaction_cap\")","terminal(state, \"absorbed\", \"interaction_cap\")")]),
        ("fake_detector_on_escape","miss",[("terminal(state, \"escaped\", \"domain_exit\")","terminal(state, \"detected\", \"receiver_hit\")")]),
        ("singleton_pose_certificate","pose",[("enclosed = tuple(tuple(ideal[i][j].include(nominal[i][j]) for j in range(3)) for i in range(3))","enclosed = tuple(tuple(_Interval.point(nominal[i][j]) for j in range(3)) for i in range(3))")]),
        ("reset_departure_uncertainty","oblique32",[("    return nominal, enclosed\n","    return nominal, _iv(nominal)\n")]),
    ]
    target=output/"negative_controls";target.mkdir()
    records=[]
    for name,case,patches in controls:
        destination=target/name;destination.mkdir()
        altered=original
        for before,after in patches:
            assert altered.count(before)==1,(name,before,altered.count(before))
            altered=altered.replace(before,after,1)
        copy=destination/"geometric_routing_mutated.py"
        with copy.open("x",encoding="utf-8",newline="\n") as stream:stream.write(altered)
        command=[sys.executable,"-B","-X","utf8",str(Path(__file__).resolve()),"--fault-child",str(copy),"--fault-case",case]
        started=time.perf_counter();process=subprocess.run(command,cwd=ROOT,capture_output=True)
        for filename,raw in (("stdout.txt",process.stdout),("stderr.txt",process.stderr)):
            with (destination/filename).open("xb") as stream:stream.write(raw)
        text=process.stderr.decode("utf-8",errors="replace")
        detected=process.returncode!=0 and "AssertionError" in text and "_evaluate" in text and "ModuleNotFoundError" not in text and "SyntaxError" not in text
        record={"fault":name,"case_assertion":case,"argv":command,"exit_code":process.returncode,"wall_s":time.perf_counter()-started,
                "detected_by_substantive_assertion":detected,"mutated_source_sha256":hashlib.sha256(copy.read_bytes()).hexdigest(),
                "classification":"intentional isolated numerical fault; not an ordinary passing trace"}
        with (destination/"result.json").open("x",encoding="utf-8") as stream:json.dump(record,stream,indent=2)
        records.append(record)
    assert hashlib.sha256(CORE.read_bytes()).hexdigest()==original_hash,"production core changed during isolated controls"
    assert all(item["detected_by_substantive_assertion"] for item in records),records
    return records


def browser_reference(value: dict[str, Any]) -> dict[str, Any]:
    """Independent ordinary-case raw-response check, no second HTTP request.

    Uses actual stored frame numbers as declared inputs. Independently finds
    the nearest finite intersection for each genuine recorded segment and
    computes reflection, local coordinates and geometric distances. It does
    not call production validation/intersection/reflection helpers.
    """
    frames={f["element_id"]:f for f in value["surface_frames"]}
    elements={e["id"]:e for e in value["scene"]["elements"]}
    checked=0;max_error=0.
    with localcontext() as context:
        context.prec=160
        dot=lambda a,b:sum(x*y for x,y in zip(a,b))
        for hit in value["hits"]:
            segment=next(s for s in value["segments"] if s["id"]==hit["segment_id"])
            origin=list(map(D,segment["start_m"]));direction=list(map(D,segment["direction"]))
            possible=[]
            for identity,element in elements.items():
                frame=frames[identity];normal=list(map(D,frame["n"]));center=list(map(D,element["pose"]["position_m"]))
                denominator=dot(direction,normal)
                if denominator==0:continue
                t=dot([c-o for c,o in zip(center,origin)],normal)/denominator
                # Immediate zero departure root is not another physical hit.
                if t<=Decimal(0):continue
                point=[o+t*d for o,d in zip(origin,direction)]
                relative=[p-c for p,c in zip(point,center)]
                local=[dot(relative,list(map(D,frame[key]))) for key in ("u","v")]
                aperture=element["aperture"]
                valid=(sum(x*x for x in local)<=D(aperture["radius_m"])**2 if aperture["kind"]=="disk" else
                       abs(local[0])<=D(aperture["width_m"])/2 and abs(local[1])<=D(aperture["height_m"])/2)
                if valid:possible.append((t,identity,point,local))
            # With nominal segment origins a preceding plane can have a tiny
            # rounding root; skip only the actual previous/birth surface ID.
            previous=None
            prior=[s for s in value["segments"] if s["branch_id"]==segment["branch_id"] and s["id"]<segment["id"]]
            if prior and prior[-1]["hit_id"]:
                previous=next(h["element_id"] for h in value["hits"] if h["id"]==prior[-1]["hit_id"])
            else:
                branch=next(b for b in value["branches"] if b["id"]==segment["branch_id"])
                if branch["parent_hit_id"]:previous=next(h["element_id"] for h in value["hits"] if h["id"]==branch["parent_hit_id"])
            possible=[item for item in possible if item[1]!=previous]
            assert possible,"genuine hit has no independent finite intersection"
            t,identity,point,local=min(possible,key=lambda x:x[0])
            assert identity==hit["element_id"],(identity,hit["element_id"])
            for actual,expected in zip(hit["position_m"],point):
                error=abs(actual-float(expected));max_error=max(max_error,error)
                assert error<=2e-13*max(1.,hit["cumulative_length_m"],math.hypot(*hit["position_m"]))
            for actual,expected in zip(hit["local_uv_m"],local):assert abs(actual-float(expected))<=2e-13
            length=sum((p-o)**2 for p,o in zip(point,origin)).sqrt()
            assert abs(hit["segment_length_m"]-float(length))<=2e-13*max(1.,hit["cumulative_length_m"])
            n=list(map(D,frames[identity]["n"]));reflected=[d-2*dot(direction,n)*nj for d,nj in zip(direction,n)]
            kind=elements[identity]["kind"]
            expected_outgoing=[] if kind in ("receiver","beam_stop") else [reflected] if kind=="mirror" else [direction,reflected]
            if hit["outgoing"]:
                assert len(hit["outgoing"])==len(expected_outgoing)
                for actual,expected in zip(hit["outgoing"],expected_outgoing):
                    for x,y in zip(actual["direction"],expected):assert abs(x-float(y))<=2e-13
            checked+=1
    terminal_sum=math.fsum(t["relative_weight"] for t in value["terminals"])
    assert abs(terminal_sum-1.)<=64*math.ulp(1.)
    return {"independent_checked_hits":checked,"max_nominal_point_error_m":max_error,
            "terminal_weight_sum":terminal_sum,"scope":"local genuine-segment references; full propagated32state enclosure is a separate recorded gate"}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path)
    parser.add_argument("--negative-controls",action="store_true")
    parser.add_argument("--browser-response",type=Path,action="append",default=[])
    parser.add_argument("--fault-child",type=Path)
    parser.add_argument("--fault-case")
    args=parser.parse_args()
    if args.fault_child:
        _evaluate(load_copy(args.fault_child),args.fault_case)
        print("FAULT_NOT_DETECTED")
        return
    if args.output_dir is None:parser.error("--output-dir is required")
    output=args.output_dir.resolve()
    output.mkdir(exist_ok=False)
    import ohlab.optics.geometric_routing as module
    started=time.perf_counter()
    original_hash=hashlib.sha256(CORE.read_bytes()).hexdigest()
    cases={}
    for name in [*fixtures(),"pose","oblique32","record256"]:
        t=time.perf_counter();result=_evaluate(module,name)
        wire=json.dumps(result.to_dict(),sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("utf-8")
        with (output/(name+".json")).open("xb") as stream:stream.write(wire)
        cases[name]={"status":result.status,"elapsed_s":time.perf_counter()-t,"core_json_bytes":len(wire),
                     "branches":len(result.branches),"segments":len(result.segments),"hits":len(result.hits),
                     "ledger":result.ledger.to_dict(),"diagnostics":result.diagnostics.to_dict()}
        if name in ("revisit32","oblique32"):
            submitted=oblique32() if name=="oblique32" else fixtures()[name]
            cases[name]["independent_reference"]=chain_reference(result,submitted,["plus","minus"]*16)
            cases[name]["ideal_angle_independent_reference"]=chain_reference(result,submitted,["plus","minus"]*16,"ideal")
    tracemalloc.start();base=tracemalloc.get_traced_memory()[0]
    measured=_evaluate(module,"record256")
    retained=tracemalloc.get_traced_memory()[0]-base
    encoded=json.dumps(measured.to_dict(),sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
    decoded=json.loads(encoded);current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    assert decoded["ledger"]["signed_residual"]==0.
    memory={"python_result_record_owned_bytes":retained,"encode_decode_current_bytes":current-base,"encode_decode_peak_bytes":peak-base,
            "actual_max_record_case_core_json_bytes":len(encoded),"scope":"Python traced allocations only, excludes native/browser/GPU/RSS; not frontend admission proof"}
    controls=negative_controls(output) if args.negative_controls else []
    restored={name:_evaluate(module,name).status for name in ("A","B","C","revisit32","oblique32","record256")}
    browser=[]
    for path in args.browser_response:
        raw=path.read_bytes()
        if len(raw)>524288:raise ValueError("genuine browser response exceeds512KiB")
        value=json.loads(raw)
        browser.append({"path":str(path.resolve()),"sha256":hashlib.sha256(raw).hexdigest(),**browser_reference(value)})
    assert hashlib.sha256(CORE.read_bytes()).hexdigest()==original_hash
    report={"status":"PASS","python_executable":sys.executable,"python_version":sys.version,
            "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"core_sha256_before":original_hash,
            "core_sha256_after":hashlib.sha256(CORE.read_bytes()).hexdigest(),"cases":cases,"resource":memory,
            "independent_tolerance":{"rtol":2e-13,"point_length_atol":"2e-13*max(1m,coordinate norms,cumulative)","direction_atol":2e-13},
            "controls":controls,"restored_assertions":restored,"genuine_browser_comparisons":browser,
            "elapsed_s":time.perf_counter()-started,"limits_note":"max_segments256 is redundant under combinedrecords256 plus onehitperphysicalsegment; its guard remains explicit",
            "evidence_scope":"current direct core/reference and deliberate isolated faults; not browser execution or legacy suite"}
    with (output/"report.json").open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2,allow_nan=False)
    print(json.dumps(report,indent=2,allow_nan=False))


if __name__=="__main__":main()
