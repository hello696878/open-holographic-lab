"""W4 finite, polarized Fresnel power routing; SI and incoherent path addition.

This traversal computes new finite reflected and transmitted paths using only
public geometry owners. It never decorates W3's transmitted-only result list,
prunes weak branches, fills an infinite series or sums inter-path amplitudes.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
import math
from typing import Any

from ohlab.optics.geometric_routing import (
    CertifiedInterval, CertifiedRay, NumericalAmbiguityError,
    UnsupportedNumericalInputError, certify_vector, certify_ray,
    certified_domain_exit, certified_norm, certified_point_at,
    certified_vector_subtract, nearest_finite_hit,
)
from ohlab.optics.refractive_routing import (
    CertifiedDielectricGeometry, CertifiedNormalIncidence, FrozenRecord,
    MediumStateAmbiguityError, RefractiveScene, certified_geometry,
    certified_dielectric_directions,
)
from ohlab.optics.fresnel_interface import (
    POLARIZATION_POLICY, SOURCE_C, RayPowerState,
    UnsupportedPolarizationNumericsError, apply_fresnel_interface,
    source_power_state,
)

MODEL_CONTRACT = "w4_fresnel_polarized_routing_v1"
SCHEMA_VERSION = 1
POWER_POLICY = "absolute_source_coherency_v1"
PATH_ADDITION = "incoherent_phase_averaged_v1"
GEOMETRY_POLICY = "binary64_closed_body_outward_v1"
MAX_BRANCHES = 31
MAX_INTERACTIONS = 8
MAX_EVENTS = 32
MAX_SEGMENTS = 64
MAX_RECORDS = 96
MAX_DISTANCE_M = 10.
REQUEST_BYTES = 32768
RESPONSE_BYTES = 393216


def _freeze(value: Any) -> Any:
    if isinstance(value,Mapping):
        return FrozenRecord(tuple((key,_freeze(item)) for key,item in value.items()))
    if isinstance(value,(tuple,list)):
        return tuple(_freeze(x) for x in value)
    return value


def _closed(value: Any,keys: set[str],context: str) -> Mapping[str,Any]:
    if not isinstance(value,Mapping):
        raise TypeError(f"{context} must be a mapping")
    if set(value)!=keys:
        raise ValueError(f"{context} requires exactly {sorted(keys)!r}; got {sorted(map(str,value))!r}")
    return value


def _limits() -> FrozenRecord:
    return _freeze({"max_bodies":1,"max_body_faces":6,"max_terminal_elements":4,"max_total_optical_faces":10,
        "max_interactions":MAX_INTERACTIONS,"max_branches":MAX_BRANCHES,"max_events":MAX_EVENTS,
        "max_segments":MAX_SEGMENTS,"max_records":MAX_RECORDS,"max_terminal_leaves":16,
        "trace_radius_m":1.,"max_distance_m":MAX_DISTANCE_M,"request_bytes":REQUEST_BYTES,"response_bytes":RESPONSE_BYTES})


@dataclass(frozen=True,slots=True)
class FresnelScene:
    """Owned closed W4 scene, exact source presets and actual certified geometry."""

    _record: FrozenRecord = field(repr=False)
    geometry: CertifiedDielectricGeometry = field(repr=False)
    media: tuple[FrozenRecord,...]
    body_faces: tuple[FrozenRecord,...]
    terminal_frames: tuple[FrozenRecord,...]
    limits: FrozenRecord

    @classmethod
    def from_dict(cls,value: Mapping[str,Any]) -> FresnelScene:
        """Validate complete scene in SI/radians, without tracing."""
        return validate_fresnel_scene(value)

    @property
    def source(self) -> FrozenRecord:
        return self._record["source"]

    @property
    def bodies(self) -> tuple[FrozenRecord,...]:
        return self._record["bodies"]

    @property
    def elements(self) -> tuple[FrozenRecord,...]:
        return self._record["elements"]

    @property
    def exterior_medium(self) -> FrozenRecord:
        return self._record["exterior_medium"]

    def to_dict(self) -> dict[str,Any]:
        """Return detached plain input containers; no geometry handles on wire."""
        return self._record.to_dict()


def validate_fresnel_scene(value: FresnelScene | Mapping[str,Any]) -> FresnelScene:
    """Strict geometry/metadata admission only: zero traces, no numerical solve."""
    if isinstance(value,FresnelScene):
        return value
    raw=_closed(value,{"schema_version","model_contract","source","exterior_medium","bodies","elements","path_addition"},"scene")
    if type(raw["schema_version"]) is not int:
        raise TypeError("schema_version must be int excluding bool")
    if not isinstance(raw["model_contract"],str) or not isinstance(raw["path_addition"],str):
        raise TypeError("model_contract/path_addition must be str")
    if raw["schema_version"]!=1 or raw["model_contract"]!=MODEL_CONTRACT or raw["path_addition"]!=PATH_ADDITION:
        raise ValueError("scene requires W4 schema1 and explicit incoherent_phase_averaged_v1 path addition")
    source=_closed(raw["source"],{"id","origin_m","direction","frame_policy","polarization"},"source")
    if not isinstance(source["frame_policy"],str) or not isinstance(source["polarization"],str):
        raise TypeError("source frame_policy/polarization must be str")
    if source["frame_policy"]!="world_xy_forward_z_v1" or source["polarization"] not in SOURCE_C:
        raise ValueError("source requires fixed world_xy_forward_z_v1 and one of four polarization enums")
    elements=raw["elements"]
    if not isinstance(elements,(tuple,list)):
        raise TypeError("elements must be list or tuple")
    if len(elements)>4:
        raise ValueError("W4 supports at most four receivers/beam stops")
    for element in elements:
        if not isinstance(element,Mapping):
            raise TypeError("element must be mapping")
        if element.get("kind") not in ("receiver","beam_stop"):
            raise ValueError("W4 supports only receiver and beam_stop; no mirror/splitter polarization convention")
    # This is an explicit immutable geometry-only projection. It is neither a
    # conversion of an old document nor a call to the old single-route solver.
    projection={"schema_version":1,"model_contract":"w3_ideal_refractive_routing_v1",
        "source":{"id":source["id"],"origin_m":source["origin_m"],"direction":source["direction"],"relative_weight":1.},
        "exterior_medium":raw["exterior_medium"],"bodies":raw["bodies"],"elements":elements}
    old=RefractiveScene.from_dict(projection)
    if tuple(old.source["direction"])!=(0.,0.,1.):
        raise ValueError("W4 source direction must be exactly[0,0,1]")
    if tuple(old.source["origin_m"]) not in ((0.,.08,-.04),(.02,.08,-.04)):
        raise ValueError("W4 source origin must be one of the two frozen preset triples")
    if len(old.body_faces)+len(old.elements)>10:
        raise ValueError("W4 total optical faces exceed10")
    normalized=old.to_dict()
    normalized.update(model_contract=MODEL_CONTRACT,path_addition=PATH_ADDITION)
    normalized["source"]={"id":"source","origin_m":list(old.source["origin_m"]),"direction":list(old.source["direction"]),
                          "frame_policy":"world_xy_forward_z_v1","polarization":source["polarization"]}
    record=_freeze(normalized)
    return FresnelScene(record,certified_geometry(old),old.media,old.body_faces,old.legacy_surface_frames,_limits())


@dataclass(frozen=True,slots=True)
class FresnelTraceResult:
    """Owned atomic successful bounded graph; numerical errors have no prefix."""

    scene: FresnelScene
    power_policy: str
    path_addition: str
    media: tuple[FrozenRecord,...]
    body_faces: tuple[FrozenRecord,...]
    terminal_frames: tuple[FrozenRecord,...]
    limits: FrozenRecord
    status: str
    branches: tuple[FrozenRecord,...]
    segments: tuple[FrozenRecord,...]
    events: tuple[FrozenRecord,...]
    terminals: tuple[FrozenRecord,...]
    ledger: FrozenRecord
    diagnostics: FrozenRecord

    def to_dict(self) -> dict[str,Any]:
        """Fourteen exact core fields; transport separately adds request identity."""
        return {"scene":self.scene.to_dict(),"power_policy":self.power_policy,"path_addition":self.path_addition,
            "media":[x.to_dict() for x in self.media],"body_faces":[x.to_dict() for x in self.body_faces],
            "terminal_frames":[x.to_dict() for x in self.terminal_frames],"branches":[x.to_dict() for x in self.branches],
            "segments":[x.to_dict() for x in self.segments],"events":[x.to_dict() for x in self.events],
            "terminals":[x.to_dict() for x in self.terminals],
            "limits":self.limits.to_dict(),"status":self.status,"ledger":self.ledger.to_dict(),"diagnostics":self.diagnostics.to_dict()}


@dataclass(slots=True)
class _Pending:
    branch_id: str
    ray: CertifiedRay
    state: RayPowerState
    interactions: int
    event_id: str | None
    relation: CertifiedNormalIncidence | None


def _angle(direction: Any,normal: Any) -> float:
    """Unclamped diagnostic angle in radians from actual nominal vectors."""
    cross=tuple(direction[j]*normal[k]-direction[k]*normal[j] for j,k in ((1,2),(2,0),(0,1)))
    return math.atan2(math.hypot(*cross),abs(math.fsum(x*y for x,y in zip(direction,normal))))


def trace_fresnel_scene(scene: FresnelScene) -> FresnelTraceResult:
    """Trace explicit FIFO R-then-T finite routes, preserving all positive power.

    Root and every allocated child (including one-child continuations) count
    toward31. Eight ancestry hits and32 global events include terminal hits.
    All positive candidates allocate atomically; queued leaves are accounted.
    No renderer, I/O, randomness, threshold, origin epsilon or hidden old solve.
    """
    if not isinstance(scene,FresnelScene):
        raise TypeError("trace_fresnel_scene requires FresnelScene")
    geometry=scene.geometry
    source=certify_vector(scene.source["origin_m"])
    direction=certify_vector(scene.source["direction"])
    initial=source_power_state(direction,"exterior",scene.exterior_medium["refractive_index"],scene.source["polarization"])
    ray=certify_ray(origin=source,direction=direction,cumulative_length_m=0.,cumulative_bounds=CertifiedInterval.point(0.),previous_face_id=None)
    pending=deque([_Pending("r0",ray,initial,0,None,None)])
    def branch(identity: str,parent: str | None,event: str | None,point: Any,state: RayPowerState,cumulative: float,depth: int) -> dict[str,Any]:
        return {"id":identity,"parent_id":parent,"parent_event_id":event,"origin_m":point,
            "initial_state":state.to_dict(),"start_cumulative_m":cumulative,"start_interaction_count":depth,"outcome":""}
    branches=[branch("r0",None,None,source.nominal,initial,0.,0)]
    branch_index={"r0":branches[0]}
    segments: list[dict[str,Any]]=[]
    events: list[dict[str,Any]]=[]
    terminals: list[dict[str,Any]]=[]
    max_point=max_direction=max_frame=max_coefficient=max_C=max_local=max_frame_residual=0.
    max_ancestry=0
    elements={x["id"]:x for x in scene.elements}

    def terminal(item: _Pending,category: str,reason: str,element: str | None=None) -> None:
        if branch_index[item.branch_id]["outcome"]:
            raise UnsupportedPolarizationNumericsError("branch cannot terminate twice")
        branch_index[item.branch_id]["outcome"]=category
        terminals.append({"branch_id":item.branch_id,"category":category,"element_id":element,"event_id":item.event_id,
            "position_m":item.ray.origin.nominal,"state":item.state.to_dict(),"cumulative_length_m":item.ray.cumulative_length_m,"reason":reason})

    def drain(item: _Pending,reason: str) -> None:
        terminal(item,"resource_unresolved",reason)
        while pending:
            terminal(pending.popleft(),"resource_unresolved",reason)

    def measure(state: RayPowerState) -> None:
        nonlocal max_direction,max_frame,max_C,max_frame_residual
        max_direction=max(max_direction,*(x.hi-x.lo for x in state.direction.bounds))
        max_frame=max(max_frame,*(x.hi-x.lo for x in state.frame.intervals))
        max_C=max(max_C,*(x.hi-x.lo for x in state.C_bounds))
        axes=(state.frame.e1.nominal,state.frame.e2.nominal,state.frame.khat.nominal)
        max_frame_residual=max(max_frame_residual,max(abs(math.fsum(x*y for x,y in zip(a,b))-(1. if i==j else 0.))
            for i,a in enumerate(axes) for j,b in enumerate(axes)))

    measure(initial)
    while pending:
        item=pending.popleft()
        ray=item.ray
        if item.interactions>=MAX_INTERACTIONS:
            terminal(item,"resource_unresolved","interaction_cap")
            continue
        if len(events)>=MAX_EVENTS:
            drain(item,"event_cap");break
        if len(segments)>=MAX_SEGMENTS:
            drain(item,"segment_cap");break
        if len(events)+len(segments)>=MAX_RECORDS:
            drain(item,"record_cap");break
        remaining=CertifiedInterval.point(MAX_DISTANCE_M)-ray.cumulative_bounds
        if remaining.hi<=0:
            terminal(item,"resource_unresolved","distance_cap");continue
        if remaining.lo<=0:
            raise NumericalAmbiguityError("remaining geometric distance overlaps zero")
        sphere,sphere_i=certified_domain_exit(ray,source.nominal)
        speed,speed_i=certified_norm(ray.direction)
        distance=(MAX_DISTANCE_M-ray.cumulative_length_m)/speed
        distance_i=remaining/speed_i
        if sphere_i.hi<distance_i.lo:
            reason,parameter,parameter_i="domain_exit",sphere,sphere_i
        elif distance_i.hi<sphere_i.lo:
            reason,parameter,parameter_i="distance_cap",distance,distance_i
        else:
            raise NumericalAmbiguityError("domain and geometric-distance endpoints have unresolved ordering")
        hit=nearest_finite_hit(ray,geometry.faces,parameter_i)
        if hit is not None and not hit.parameter_bounds.hi<parameter_i.lo:
            if hit.parameter_bounds.lo>parameter_i.hi:
                hit=None
            else:
                raise NumericalAmbiguityError("finite hit and endpoint have unresolved ordering")
        cost=2 if hit is not None else 1
        if len(segments)+1>MAX_SEGMENTS:
            drain(item,"segment_cap");break
        if len(events)+len(segments)+cost>MAX_RECORDS:
            drain(item,"record_cap");break
        end=hit.position if hit is not None else certified_point_at(ray,parameter,parameter_i)
        point_width=max(x.hi-x.lo for x in end.bounds)
        if point_width>1e-8:
            raise UnsupportedNumericalInputError("point interval width exceeds1e-8m; no uncertainty reset")
        max_point=max(max_point,point_width)
        length,length_i=certified_norm(certified_vector_subtract(end,ray.origin))
        cumulative=ray.cumulative_length_m+length
        cumulative_i=(ray.cumulative_bounds+length_i).include(cumulative)
        segment_id=f"s{len(segments)+1:04d}"
        event_id=f"e{len(events)+1:04d}" if hit is not None else None
        segments.append({"id":segment_id,"branch_id":item.branch_id,"start_m":ray.origin.nominal,"end_m":end.nominal,
            "state":item.state.to_dict(),"length_m":length,"cumulative_end_m":cumulative,"event_id":event_id})
        item.ray=certify_ray(origin=end,direction=ray.direction,cumulative_length_m=cumulative,cumulative_bounds=cumulative_i,
                            previous_face_id=None if hit is None else hit.face.face_id)
        if hit is None:
            if item.state.medium_id!="exterior":
                raise MediumStateAmbiguityError("body-interior ray cannot escape without its closed finite face")
            item.event_id=None
            terminal(item,"escaped" if reason=="domain_exit" else "resource_unresolved",reason)
            continue
        face=hit.face
        item.event_id=event_id
        item.interactions+=1
        max_ancestry=max(max_ancestry,item.interactions)
        bounds={"t_parameter_interval_m":hit.parameter_bounds.pair(),"position_intervals_m":[x.pair() for x in end.bounds],
            "local_uv_intervals_m":[x.pair() for x in hit.local_uv_bounds],
            "incident_direction_intervals":[x.pair() for x in ray.direction.bounds],"outgoing_direction_intervals":[],
            "cumulative_length_interval_m":cumulative_i.pair(),"plane_residual_m":geometry.plane_residual_m(end,face)}
        event={"id":event_id,"segment_id":segment_id,"branch_id":item.branch_id,"target":{},"classification":"",
            "position_m":end.nominal,"local_uv_m":hit.local_uv_m,"incident_state":item.state.to_dict(),
            "segment_length_m":length,"cumulative_length_m":cumulative,"numerical_bounds":bounds,"interface":None}
        events.append(event)
        record=geometry.face_record(face)
        if record is None:
            if item.state.medium_id!="exterior":
                raise MediumStateAmbiguityError("exterior receiver/stop encountered in body medium")
            kind=elements[face.face_id]["kind"]
            event["target"]={"kind":"element","body_id":None,"face_id":None,"element_id":face.face_id}
            event["classification"]="receiver_hit" if kind=="receiver" else "stop_hit"
            terminal(item,"detected" if kind=="receiver" else "stopped",event["classification"],face.face_id)
            continue
        directions=certified_dielectric_directions(geometry,ray,hit,item.state.medium_id,item.relation)
        interaction=apply_fresnel_interface(item.state,directions)
        coefficients=interaction.coefficients
        max_local=max(max_local,abs(interaction.local_signed_residual))
        for bound in coefficients.bounds:
            if bound is not None:
                max_coefficient=max(max_coefficient,bound.real.hi-bound.real.lo,bound.imag.hi-bound.imag.lo)
        event["target"]={"kind":"body_face","body_id":record["body_id"],"face_id":record["face_id"],"element_id":None}
        event["classification"]=directions.classification
        basis_bounds=None if interaction.basis_bounds is None else [x.pair() for x in interaction.basis_bounds]
        rs,rp,ts,tp=coefficients.channel_powers
        reflected_power=0. if interaction.reflected is None else interaction.reflected.power_fraction
        transmitted_power=0. if interaction.transmitted is None else interaction.transmitted.power_fraction
        power=item.state.power_fraction
        interface={"incident_medium_id":directions.incident_medium_id,"transmission_medium_id":directions.transmission_medium_id,
            "outward_normal":record["outward_normal"],"incident_facing_covector":directions.incident_facing_covector.nominal,
            "incidence_basis":interaction.incidence_basis,"incident_angle_rad":0. if directions.normal_relation is not None else
                _angle(item.state.direction.nominal,record["outward_normal"]),
            "transmitted_angle_rad":None if directions.transmitted is None else (0. if directions.normal_relation is not None else
                _angle(directions.transmitted.nominal,record["outward_normal"])),
            "coefficients":{"r_s":[coefficients.r_s.real,coefficients.r_s.imag],"r_p":[coefficients.r_p.real,coefficients.r_p.imag],
                "t_s":None if coefficients.t_s is None else [coefficients.t_s.real,coefficients.t_s.imag],
                "t_p":None if coefficients.t_p is None else [coefficients.t_p.real,coefficients.t_p.imag],"flux_factor":coefficients.flux_factor},
            "power_fractions":{"R_s":rs,"R_p":rp,"T_s":ts,"T_p":tp,
                "R_incident":None if power==0 else reflected_power/power,"T_incident":None if power==0 else transmitted_power/power},
            "legs":[],"local_signed_residual":interaction.local_signed_residual,
            "numerical_bounds":{"ci_interval":coefficients.ci_bound.pair(),"ct_complex_intervals":coefficients.ct_bound.pair(),
                "coefficient_intervals":[None if x is None else x.pair() for x in coefficients.bounds],
                "flux_factor_interval":None if coefficients.flux_bound is None else coefficients.flux_bound.pair(),
                "basis_intervals":basis_bounds,"local_residual_interval":interaction.local_residual_bound.pair()}}
        event["interface"]=interface
        bounds.update(snell_discriminant_interval=directions.discriminant.pair(),incident_side_interval=directions.incident_side.pair(),
            body_halfspace_intervals_m=[x.pair() for x in directions.body_halfspaces],outgoing_side_intervals=[])
        candidates=[]
        for suffix,child,relation,side in (("R",interaction.reflected,directions.reflected_relation,directions.reflected_side),
                                           ("T",interaction.transmitted,directions.transmitted_relation,directions.transmitted_side)):
            if child is not None:
                if child.power_fraction<=0:
                    raise UnsupportedPolarizationNumericsError("zero rounded candidate lacks an algebraic exact-zero proof")
                measure(child)
                candidates.append((suffix,child,relation,side))
        fits=len(branches)+len(candidates)<=MAX_BRANCHES
        for suffix,child,relation,side in (("R",interaction.reflected,directions.reflected_relation,directions.reflected_side),
                                           ("T",interaction.transmitted,directions.transmitted_relation,directions.transmitted_side)):
            if child is None:
                disposition="exact_zero" if suffix=="R" and directions.classification=="equal_index_identity" else "nonpropagating_TIR"
                medium,index=(directions.incident_medium_id,directions.incident_index) if suffix=="R" else (directions.transmission_medium_id,directions.transmission_index)
                identity=None
            else:
                disposition="allocated" if fits else "resource_unallocated"
                identity=item.branch_id+"."+suffix if fits else None
                medium,index=child.medium_id,child.refractive_index
            interface["legs"].append({"kind":suffix,"disposition":disposition,"branch_id":identity,
                "direction":None if child is None else child.direction.nominal,"medium_id":medium,"refractive_index":index,
                "power_fraction":0. if child is None else child.power_fraction,"state":None if child is None else child.to_dict()})
            bounds["outgoing_direction_intervals"].append({"kind":suffix,"branch_id":identity,
                "direction_intervals":None if child is None else [x.pair() for x in child.direction.bounds]})
            bounds["outgoing_side_intervals"].append({"kind":suffix,"branch_id":identity,"side_interval":None if child is None else side.pair()})
            if child is not None and fits:
                new_branch=branch(identity,item.branch_id,event_id,end.nominal,child,cumulative,item.interactions)
                branches.append(new_branch);branch_index[identity]=new_branch
                child_ray=certify_ray(origin=end,direction=child.direction,cumulative_length_m=cumulative,cumulative_bounds=cumulative_i,previous_face_id=face.face_id)
                pending.append(_Pending(identity,child_ray,child,item.interactions,event_id,relation))
        if not fits:
            drain(item,"branch_cap");break
        branch_index[item.branch_id]["outcome"]="split" if len(candidates)==2 else "continued"
    totals={category:math.fsum(x["state"]["power_fraction"] for x in terminals if x["category"]==category)
            for category in ("detected","stopped","escaped","resource_unresolved")}
    signed=1.-math.fsum(totals.values())
    if abs(signed)>64*2.220446049250313e-16:
        raise UnsupportedPolarizationNumericsError("terminal power accounting exceeds64epsilon; no normalization")
    receivers=[]
    for element in scene.elements:
        if element["kind"]=="receiver":
            leaves=[x for x in terminals if x["category"]=="detected" and x["element_id"]==element["id"]]
            receivers.append({"element_id":element["id"],"power_fraction":math.fsum(x["state"]["power_fraction"] for x in leaves),
                              "leaf_branch_ids":[x["branch_id"] for x in leaves]})
    ledger=_freeze({"input_power":1.,"detected_power":totals["detected"],"stopped_power":totals["stopped"],"escaped_power":totals["escaped"],
        "unresolved_power":totals["resource_unresolved"],"signed_residual":signed,"receiver_totals":receivers,"path_addition":PATH_ADDITION})
    diagnostics=_freeze({"geometry_policy":GEOMETRY_POLICY,"polarization_policy":POLARIZATION_POLICY,
        "max_point_width_m":max_point,"max_direction_width":max_direction,"max_frame_width":max_frame,
        "max_coefficient_width":max_coefficient,"max_C_width":max_C,"max_local_power_residual":max_local,
        "max_frame_residual":max_frame_residual,"created_branches":len(branches),"surface_events":len(events),
        "segments":len(segments),"max_ancestry_interactions":max_ancestry,"record_count":len(events)+len(segments)})
    return FresnelTraceResult(scene,POWER_POLICY,PATH_ADDITION,scene.media,scene.body_faces,scene.terminal_frames,scene.limits,
        "incomplete" if totals["resource_unresolved"]>0 else "complete",tuple(_freeze(x) for x in branches),
        tuple(_freeze(x) for x in segments),tuple(_freeze(x) for x in events),tuple(_freeze(x) for x in terminals),ledger,diagnostics)
