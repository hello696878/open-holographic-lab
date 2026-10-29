"""W3 direction-only, closed convex dielectric routing in SI metres.

One exact stored affine block or right triangular prism, one exterior source,
constant positive indices, and explicitly admitted exterior W2 elements.
Weights are ideal bookkeeping: Fresnel losses are not modeled. All numerical
geometry comes through the public certified seam; rendering is not authority.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from fractions import Fraction
import math
from numbers import Real
import re
from typing import Any

from ohlab.optics.geometric_routing import (
    CertifiedInterval, CertifiedPlanarFace, CertifiedRay, CertifiedVector3,
    GeometricScene, NumericalAmbiguityError,
    UnsupportedNumericalInputError, certify_planar_face, certify_pose_frame,
    certify_ray, certify_vector, certified_domain_exit, certified_dot,
    certified_norm, certified_point_at, certified_vector_add,
    certified_vector_scale, certified_vector_subtract, nearest_finite_hit,
    reflect_certified_direction, transform_certified_vector,
    trace_routes as trace_geometric_routes,
)

MODEL_CONTRACT = "w3_ideal_refractive_routing_v1"
SCHEMA_VERSION = 1
WEIGHT_MODEL = "ideal_route_weights_no_fresnel_v1"
PREDICATE_POLICY = "binary64_closed_body_outward_v1"
MAX_POINT_WIDTH_M = 1e-8
MAX_DIRECTION_WIDTH = 1e-8
INPUT_UNIT_ATOL = 32 * 2.220446049250313e-16
OUTPUT_UNIT_ATOL = 128 * 2.220446049250313e-16
WEIGHT_ATOL = 64 * 2.220446049250313e-16
MAX_INTERACTIONS = 32
MAX_BRANCHES = 31
MAX_RECORDS = 128
MAX_EVENTS = 64
MAX_SEGMENTS = 128
MAX_DISTANCE_M = 10.
_BODY_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,31}\Z")


class MediumStateAmbiguityError(ValueError):
    """Current medium and certified closed-boundary crossing disagree."""


@dataclass(frozen=True, slots=True)
class FrozenRecord(Mapping[str, Any]):
    """W3-owned immutable mapping; to_dict returns fresh nested containers."""

    _items: tuple[tuple[str, Any], ...]

    def __getitem__(self, key: str) -> Any:
        for name, value in self._items:
            if name == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (name for name, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def to_dict(self) -> dict[str, Any]:
        """Return a detached plain representation."""
        return {name: _thaw(value) for name, value in self._items}


def _thaw(value: Any) -> Any:
    if isinstance(value, FrozenRecord):
        return value.to_dict()
    if isinstance(value, tuple):
        return [_thaw(x) for x in value]
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return FrozenRecord(tuple((key, _freeze(item)) for key, item in value.items()))
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(x) for x in value)
    return value


def _closed(value: Any, keys: set[str], context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{context} must be a mapping")
    if set(value) != keys:
        raise ValueError(f"{context} requires exactly {sorted(keys)!r}; got {sorted(map(str, value))!r}")
    return value


def _real(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a finite real scalar excluding bool")
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{name} is not representable as binary64") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _vector(value: Any, name: str) -> tuple[float, float, float]:
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{name} must be a list or tuple")
    if len(value) != 3:
        raise ValueError(f"{name} must have three components")
    return tuple(_real(x, name) for x in value)


def _medium(value: Any, identity: str) -> dict[str, Any]:
    raw = _closed(value, {"id", "refractive_index"}, "medium")
    if not isinstance(raw["id"], str):
        raise TypeError("medium.id must be str")
    if raw["id"] != identity:
        raise ValueError(f"medium.id must equal {identity!r}")
    index = _real(raw["refractive_index"], "refractive_index")
    if not 1. <= index <= 2.5:
        raise ValueError("refractive_index must lie in [1,2.5]")
    return {"id": identity, "refractive_index": index}


def _interval_sum(values: Any) -> CertifiedInterval:
    result = CertifiedInterval.point(0.)
    for value in values:
        result = result+value
    return result


def _squared(vector: CertifiedVector3) -> CertifiedInterval:
    bound = _interval_sum(x.square() for x in vector.bounds)
    return CertifiedInterval(max(0., bound.lo), bound.hi)


def _fraction_interval(value: Fraction) -> CertifiedInterval:
    lo = hi = float(value)
    while Fraction.from_float(lo) > value:
        lo = math.nextafter(lo, -math.inf)
    while Fraction.from_float(hi) < value:
        hi = math.nextafter(hi, math.inf)
    return CertifiedInterval(lo, hi)


def _local_vector(values: Any) -> CertifiedVector3:
    fractions = tuple(x if isinstance(x, Fraction) else Fraction.from_float(float(x)) for x in values)
    return certify_vector(tuple(float(x) for x in fractions), tuple(_fraction_interval(x) for x in fractions))


def _inverse(matrix: Any) -> Any:
    # New covector operation: inverse, not transpose of a presumed rotation.
    a, b, c = matrix[0]; d, e, f = matrix[1]; g, h, i = matrix[2]
    adj = ((e*i-f*h, c*h-b*i, b*f-c*e), (f*g-d*i, a*i-c*g, c*d-a*f), (d*h-e*g, b*g-a*h, a*e-b*d))
    determinant = a*adj[0][0]+b*adj[1][0]+c*adj[2][0]
    if isinstance(determinant, CertifiedInterval):
        if determinant.lo <= 0:
            raise UnsupportedNumericalInputError("body affine determinant is not certified positive")
    elif determinant <= 0:
        raise UnsupportedNumericalInputError("body affine determinant is not positive")
    return tuple(tuple(x/determinant for x in row) for row in adj)


def _body_faces(raw: Mapping[str, Any]) -> tuple[tuple[CertifiedPlanarFace, ...], tuple[FrozenRecord, ...]]:
    shape = raw["shape"]
    pose = certify_pose_frame(raw["pose"]["rotation_xyz_rad"])
    translation = certify_vector(raw["pose"]["position_m"])
    inverse = _inverse(pose.nominal_matrix)
    enclosed_inverse = _inverse(pose.interval_matrix)
    one, zero = Fraction(1), Fraction(0)
    if raw["kind"] == "rectangular_block":
        x, y, z = (Fraction.from_float(shape[key])/2 for key in ("width_x_m", "height_y_m", "depth_z_m"))
        definitions = (
            ("x_min", (-1, 0, 0), (0, 1, 0), (0, 0, -1), ((-x,-y,-z),(-x,-y,z),(-x,y,z),(-x,y,-z))),
            ("x_max", (1, 0, 0), (0, 1, 0), (0, 0, 1), ((x,-y,-z),(x,y,-z),(x,y,z),(x,-y,z))),
            ("y_min", (0,-1,0), (1,0,0), (0,0,1), ((-x,-y,-z),(x,-y,-z),(x,-y,z),(-x,-y,z))),
            ("y_max", (0,1,0), (1,0,0), (0,0,-1), ((-x,y,-z),(-x,y,z),(x,y,z),(x,y,-z))),
            ("z_min", (0,0,-1), (1,0,0), (0,-1,0), ((-x,-y,-z),(-x,y,-z),(x,y,-z),(x,-y,-z))),
            ("z_max", (0,0,1), (1,0,0), (0,1,0), ((-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z))),
        )
    else:
        x, z, h = (Fraction.from_float(shape[key]) for key in ("leg_x_m", "leg_z_m", "height_y_m"))
        y = h/2
        scale = Fraction.from_float(1./math.hypot(float(x), float(z)))
        definitions = (
            ("x_min", (-1,0,0), (0,1,0), (0,0,-1), ((zero,-y,zero),(zero,-y,z),(zero,y,z),(zero,y,zero))),
            ("z_min", (0,0,-1), (1,0,0), (0,-1,0), ((zero,-y,zero),(zero,y,zero),(x,y,zero),(x,-y,zero))),
            ("hypotenuse", (z,zero,x), (x*scale,zero,-z*scale), (0,1,0), ((x,-y,zero),(x,y,zero),(zero,y,z),(zero,-y,z))),
            ("y_min", (0,-1,0), (1,0,0), (0,0,1), ((zero,-y,zero),(x,-y,zero),(zero,-y,z))),
            ("y_max", (0,1,0), (1,0,0), (0,0,-1), ((zero,y,zero),(zero,y,z),(x,y,zero))),
        )
    shared = {}
    faces, records = [], []
    for name, a, lu, lv, coordinates in definitions:
        for point in coordinates:
            if point not in shared:
                shared[point] = certified_vector_add(translation, transform_certified_vector(pose, _local_vector(point)))
        local_a = _local_vector(a)
        nominal = tuple(math.fsum(inverse[j][i]*local_a.nominal[j] for j in range(3)) for i in range(3))
        bounds = tuple(_interval_sum(enclosed_inverse[j][i]*local_a.bounds[j] for j in range(3)).include(nominal[i]) for i in range(3))
        covector = certify_vector(nominal, bounds)
        u = transform_certified_vector(pose, _local_vector(lu))
        v = transform_certified_vector(pose, _local_vector(lv))
        vertices = tuple(shared[x] for x in coordinates)
        origin = vertices[0]
        witness = {"pose": pose, "translation": translation, "local_vertices": coordinates,
                   "local_origin": coordinates[0], "local_u": lu, "local_v": lv, "local_covector": a}
        face = certify_planar_face(face_id="body:"+raw["id"]+":"+name, origin=origin, u=u, v=v, plane_covector=covector,
                                   boundary={"vertices": vertices, "affine_witness": witness}, policy="affine_convex_polygon")
        faces.append(face)
        norm, ni = certified_norm(covector)
        normal = certified_vector_scale(covector, 1./norm, CertifiedInterval.point(1.)/ni)
        records.append(_freeze({"body_id": raw["id"], "face_id": name, "vertices_m": [x.nominal for x in vertices],
                                "plane_covector": covector.nominal, "outward_normal": normal.nominal,
                                "local_origin_m": origin.nominal, "local_basis": {"u": u.nominal, "v": v.nominal},
                                "numerical_bounds": {"vertex_intervals_m": [[i.pair() for i in x.bounds] for x in vertices],
                                                     "covector_intervals": [i.pair() for i in covector.bounds],
                                                     "normal_intervals": [i.pair() for i in normal.bounds],
                                                     "basis_u_intervals": [i.pair() for i in u.bounds],
                                                     "basis_v_intervals": [i.pair() for i in v.bounds]}}))
    return tuple(faces), tuple(records)


def _signed_distance(point: CertifiedVector3, face: CertifiedPlanarFace) -> tuple[float, CertifiedInterval]:
    value, vi = certified_dot(certified_vector_subtract(point, face.origin), face.plane_covector)
    norm, ni = certified_norm(face.plane_covector)
    return value/norm, vi/ni


def _limits(has_body: bool) -> FrozenRecord:
    return _freeze({"max_bodies": 1, "max_body_faces": 6, "max_legacy_elements": 16, "max_total_optical_faces": 16,
                    "max_interactions": MAX_INTERACTIONS, "max_branches": MAX_BRANCHES if has_body else 63,
                    "max_records": MAX_RECORDS if has_body else 256,
                    "max_events": MAX_EVENTS if has_body else 128,
                    "max_segments": MAX_SEGMENTS if has_body else 256,
                    "trace_radius_m": 1., "max_distance_m": MAX_DISTANCE_M})


@dataclass(frozen=True, slots=True)
class RefractiveScene:
    """Owned closed W3 input and certified metadata; use from_dict, SI/radians."""

    _record: FrozenRecord = field(repr=False)
    media: tuple[FrozenRecord, ...]
    body_faces: tuple[FrozenRecord, ...]
    legacy_surface_frames: tuple[FrozenRecord, ...]
    limits: FrozenRecord
    _faces: tuple[CertifiedPlanarFace, ...] = field(repr=False)
    _legacy_scene: GeometricScene = field(repr=False)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> RefractiveScene:
        """Validate complete geometry without tracing."""
        return validate_scene(value)

    @property
    def source(self) -> FrozenRecord:
        return self._record["source"]

    @property
    def bodies(self) -> tuple[FrozenRecord, ...]:
        return self._record["bodies"]

    @property
    def elements(self) -> tuple[FrozenRecord, ...]:
        return self._record["elements"]

    @property
    def exterior_medium(self) -> FrozenRecord:
        return self._record["exterior_medium"]

    def to_dict(self) -> dict[str, Any]:
        """Fresh nested plain containers; no caller aliases."""
        return self._record.to_dict()


def validate_scene(value: RefractiveScene | Mapping[str, Any]) -> RefractiveScene:
    """Validate schema, source, full body/domain and exterior separation only."""
    if isinstance(value, RefractiveScene):
        value = value.to_dict()
    data = _closed(value, {"schema_version", "model_contract", "source", "exterior_medium", "bodies", "elements"}, "scene")
    if type(data["schema_version"]) is not int:
        raise TypeError("schema_version must be int excluding bool")
    if not isinstance(data["model_contract"], str):
        raise TypeError("model_contract must be str")
    if data["schema_version"] != 1 or data["model_contract"] != MODEL_CONTRACT:
        raise ValueError("scene requires schema_version1 and W3 model_contract")
    exterior = _medium(data["exterior_medium"], "exterior")
    old = GeometricScene.from_dict({"schema_version": 1, "model_contract": "w2_ideal_geometric_routing_v1",
                                    "source": data["source"], "elements": data["elements"]})
    bodies = data["bodies"]
    if not isinstance(bodies, (list, tuple)):
        raise TypeError("bodies must be a list or tuple")
    if len(bodies) > 1:
        raise ValueError("at most one closed dielectric body is supported")
    owned, body_faces, records = [], (), ()
    if bodies:
        raw = _closed(bodies[0], {"id", "kind", "pose", "shape", "interior_medium"}, "body")
        identity, kind = raw["id"], raw["kind"]
        if not isinstance(identity, str) or not isinstance(kind, str):
            raise TypeError("body id and kind must be str")
        if _BODY_ID.fullmatch(identity) is None or identity in {"source", "exterior", *(x["id"] for x in old.elements)}:
            raise ValueError("body.id must be a unique [A-Za-z][A-Za-z0-9_-]{0,31} identifier")
        names = {"rectangular_block": ("width_x_m", "height_y_m", "depth_z_m"),
                 "right_triangular_prism": ("leg_x_m", "leg_z_m", "height_y_m")}
        if kind not in names:
            raise ValueError("body.kind must be rectangular_block or right_triangular_prism")
        shape_raw = _closed(raw["shape"], set(names[kind]), "body.shape")
        shape = {key: _real(shape_raw[key], key) for key in names[kind]}
        if any(not 1e-4 <= x <= .25 for x in shape.values()):
            raise ValueError("body dimensions must lie in [1e-4,.25] metres")
        pose_raw = _closed(raw["pose"], {"position_m", "rotation_xyz_rad"}, "body.pose")
        position = _vector(pose_raw["position_m"], "body.position_m")
        angles = _vector(pose_raw["rotation_xyz_rad"], "body.rotation_xyz_rad")
        if any(abs(x) > 10. for x in position) or any(abs(x) > math.pi for x in angles):
            raise ValueError("body position requires absolute<=10m and rotations in [-pi,pi]")
        body = {"id": identity, "kind": kind, "pose": {"position_m": position, "rotation_xyz_rad": angles},
                "shape": shape, "interior_medium": _medium(raw["interior_medium"], "body:"+identity)}
        body_faces, records = _body_faces(body)
        if len(body_faces)+len(old.elements) > 16:
            raise ValueError("body faces plus exterior elements exceed maximum16")
        source = certify_vector(old.source["origin_m"])
        if not any(_signed_distance(source, face)[1].lo > 0 for face in body_faces):
            raise ValueError("source must be certified strictly outside the closed body")
        if any(certified_norm(certified_vector_subtract(vertex, source))[1].hi >= 1. for face in body_faces for vertex in face.vertices):
            raise ValueError("every body vertex must be strictly inside the source-centered1m sphere")
        owned.append(body)
    legacy_faces = []
    for element in old.elements:
        pose = certify_pose_frame(element["pose"]["rotation_xyz_rad"])
        columns = tuple(certify_vector(tuple(row[j] for row in pose.nominal_matrix), tuple(row[j] for row in pose.interval_matrix)) for j in range(3))
        face = certify_planar_face(face_id=element["id"], origin=certify_vector(element["pose"]["position_m"]),
                                   u=columns[0], v=columns[1], plane_covector=columns[2], boundary=element["aperture"], policy="legacy_w2_projection")
        if body_faces:
            if not any((_signed_distance(face.origin, other)[1]-face.bounding_radius).lo > 0 for other in body_faces):
                raise ValueError("each complete exterior aperture must be certified separated from the closed body; touching/overlap/unresolved rejected")
        legacy_faces.append(face)
    old_dict = old.to_dict()
    record = _freeze({"schema_version": 1, "model_contract": MODEL_CONTRACT, "source": old_dict["source"],
                      "exterior_medium": exterior, "bodies": owned, "elements": old_dict["elements"]})
    media = (record["exterior_medium"],) + tuple(x["interior_medium"] for x in record["bodies"])
    return RefractiveScene(record, media, records, tuple(_freeze(x) for x in old.surface_frames), _limits(bool(owned)), body_faces+tuple(legacy_faces), old)


@dataclass(frozen=True, slots=True)
class RefractiveTraceResult:
    """Owned bounded graph; numerical exceptions never return a partial result."""

    scene: RefractiveScene
    weight_model: str
    media: tuple[FrozenRecord, ...]
    body_faces: tuple[FrozenRecord, ...]
    legacy_surface_frames: tuple[FrozenRecord, ...]
    limits: FrozenRecord
    status: str
    branches: tuple[FrozenRecord, ...]
    segments: tuple[FrozenRecord, ...]
    events: tuple[FrozenRecord, ...]
    terminals: tuple[FrozenRecord, ...]
    ledger: FrozenRecord
    diagnostics: FrozenRecord

    def to_dict(self) -> dict[str, Any]:
        """Return the thirteen core keys; transport adds request identity."""
        return {"scene": self.scene.to_dict(), "weight_model": self.weight_model,
                **{name: [x.to_dict() for x in values] for name, values in
                   (("media", self.media), ("body_faces", self.body_faces), ("legacy_surface_frames", self.legacy_surface_frames),
                    ("branches", self.branches), ("segments", self.segments), ("events", self.events), ("terminals", self.terminals))},
                "limits": self.limits.to_dict(), "status": self.status, "ledger": self.ledger.to_dict(), "diagnostics": self.diagnostics.to_dict()}


def _no_body(scene: RefractiveScene) -> RefractiveTraceResult:
    old = trace_geometric_routes(scene._legacy_scene)
    data = old.to_dict()
    index = scene.exterior_medium["refractive_index"]
    branches, segments, events, terminals = data["branches"], data["segments"], data["hits"], data["terminals"]
    for branch in branches:
        branch["parent_event_id"] = branch.pop("parent_hit_id")
        branch.update(initial_medium_id="exterior", initial_refractive_index=index)
    for segment in segments:
        segment["event_id"] = segment.pop("hit_id")
        segment.update(medium_id="exterior", refractive_index=index)
    certificates = {x["segment_id"]: x for x in old.certificates}
    kinds = {x["id"]: x["kind"] for x in scene.elements}
    classifications = {"mirror": "mirror_reflection", "ideal_splitter_50_50": "ideal_split", "receiver": "receiver_hit", "beam_stop": "stop_hit"}
    for event in events:
        identity = event.pop("element_id")
        event.update(target={"kind": "element", "element_id": identity}, classification=classifications[kinds[identity]],
                     incident_medium_id="exterior", incident_refractive_index=index)
        certificate = certificates[event["segment_id"]]
        for outgoing in event["outgoing"]:
            outgoing.update(medium_id="exterior", refractive_index=index)
        event["numerical_bounds"].update(incident_direction_intervals=certificate.to_dict()["direction_intervals"],
                                           outgoing_direction_intervals=[{"branch_id": x["branch_id"], "direction_intervals": list(bounds)}
                                                for x, bounds in zip(event["outgoing"], certificate["outgoing_direction_intervals"])],
                                           cumulative_length_interval_m=list(certificate["cumulative_interval_m"]))
    for terminal in terminals:
        terminal["event_id"] = terminal.pop("hit_id")
        terminal.update(medium_id="exterior", refractive_index=index)
    return RefractiveTraceResult(scene, WEIGHT_MODEL, scene.media, (), scene.legacy_surface_frames, scene.limits,
                                 old.status, tuple(_freeze(x) for x in branches), tuple(_freeze(x) for x in segments),
                                 tuple(_freeze(x) for x in events), tuple(_freeze(x) for x in terminals), _freeze(old.ledger), _freeze(old.diagnostics))


def _admit_vector(vector: CertifiedVector3, position: bool = False) -> None:
    width = max(x.hi-x.lo for x in vector.bounds)
    limit = MAX_POINT_WIDTH_M if position else MAX_DIRECTION_WIDTH
    if width > limit:
        raise UnsupportedNumericalInputError(f"{'point' if position else 'direction'} interval width {width!r} exceeds fixed {limit!r}; no uncertainty reset")
    if not position and abs(math.hypot(*vector.nominal)-1.) > OUTPUT_UNIT_ATOL:
        raise UnsupportedNumericalInputError("dielectric nominal direction exceeds128epsilon; no normalization")


def _dielectric_direction(direction: CertifiedVector3, outward: CertifiedVector3, incident_index: float,
                          other_index: float, entering: bool) -> tuple[CertifiedVector3, str, CertifiedInterval, CertifiedInterval, CertifiedInterval]:
    """Actual homogeneous Snell/TIR operator; also used by the shipped stress gate."""
    side = certified_dot(direction, outward)[1]
    if entering and side.hi >= 0 or not entering and side.lo <= 0:
        raise MediumStateAmbiguityError("incident medium lacks a strict oriented body crossing")
    a = outward if entering else certified_vector_scale(outward, -1., CertifiedInterval.point(-1.))
    da, dai = certified_dot(direction, a)
    aa, aai = certified_dot(a, a)
    # The dot enclosure's nonnegative constraint is used only for a.a/d.d/q.q.
    aai = _squared(a)
    if aai.lo <= 0:
        raise UnsupportedNumericalInputError("body covector norm is not certified positive")
    rho = incident_index/other_index
    rhoi = CertifiedInterval.point(incident_index)/CertifiedInterval.point(other_index)
    q = certified_vector_subtract(direction, certified_vector_scale(a, da/aa, dai/aai))
    dd = math.fsum(x*x for x in direction.nominal)
    qq = math.fsum(x*x for x in q.nominal)
    discriminant = dd-rho*rho*qq
    ki = _squared(direction)-rhoi.square()*_squared(q)
    if incident_index == other_index:
        # With rho=1 and q orthogonal to a, S-|q|²=(d.a)²/(a.a).
        # This exact identity removes cancellation, not propagated uncertainty.
        # A strictly nongrazing incident enclosure proves a strictly positive K.
        discriminant = da*da/aa
        ki = dai.square()/aai
    if ki.lo <= 0 <= ki.hi:
        raise NumericalAmbiguityError("Snell discriminant interval includes critical zero")
    if incident_index == other_index:
        outgoing, kind = direction, "refraction"
    elif ki.hi < 0:
        outgoing = certified_vector_subtract(direction, certified_vector_scale(a, 2.*da/aa, CertifiedInterval.point(2.)*dai/aai))
        kind = "total_internal_reflection"
    else:
        if discriminant <= 0:
            raise UnsupportedNumericalInputError("nominal Snell value disagrees with positive certified domain")
        outgoing = certified_vector_subtract(certified_vector_scale(q, rho, rhoi),
                                              certified_vector_scale(a, math.sqrt(discriminant/aa), (ki/aai).sqrt()))
        kind = "refraction"
    _admit_vector(outgoing)
    out_side = certified_dot(outgoing, outward)[1]
    same_sign = kind == "refraction"
    negative = entering if same_sign else not entering
    if negative and out_side.hi >= 0 or not negative and out_side.lo <= 0:
        raise MediumStateAmbiguityError("outgoing medium lacks a strict certified departure side")
    return outgoing, kind, ki, side, out_side


@dataclass(slots=True)
class _State:
    branch_id: str
    ray: CertifiedRay
    medium: str
    index: float
    weight: float
    interactions: int
    event_id: str | None
    element_id: str | None


def _ray(origin: CertifiedVector3, direction: CertifiedVector3, cumulative: float = 0.,
         ci: CertifiedInterval | None = None, previous: str | None = None) -> CertifiedRay:
    return certify_ray(origin=origin, direction=direction, cumulative_length_m=cumulative,
                       cumulative_bounds=CertifiedInterval.point(0.) if ci is None else ci, previous_face_id=previous)


def _angle(direction: tuple[float, ...], normal: tuple[float, ...]) -> float:
    cross = tuple(direction[j]*normal[k]-direction[k]*normal[j] for j, k in ((1, 2), (2, 0), (0, 1)))
    return math.atan2(math.hypot(*cross), abs(math.fsum(a*b for a, b in zip(direction, normal))))


def trace_routes(scene: RefractiveScene) -> RefractiveTraceResult:
    """Trace one validated W3 scene, retaining SI geometry and medium per leg.

    No-body inputs delegate W2 exactly. Body scenes use the frozen smaller
    caps and fixed width admission. Numerical/medium failures raise rather
    than returning a successful diagnostic prefix. No caller state is changed.
    """
    if not isinstance(scene, RefractiveScene):
        raise TypeError("trace_routes requires RefractiveScene")
    scene = validate_scene(scene)
    if not scene.bodies:
        return _no_body(scene)
    origin = certify_vector(scene.source["origin_m"])
    direction = certify_vector(scene.source["direction"])
    exterior = scene.exterior_medium
    interior = scene.bodies[0]["interior_medium"]
    body_count = len(scene.body_faces)
    body_geometry = scene._faces[:body_count]
    body_records = {face.face_id: record for face, record in zip(body_geometry, scene.body_faces)}
    elements = {x["id"]: x for x in scene.elements}
    root = _State("r0", _ray(origin, direction), "exterior", exterior["refractive_index"], 1., 0, None, None)
    queue = deque([root])
    branches = [{"id": "r0", "parent_id": None, "parent_event_id": None, "origin_m": origin.nominal,
                 "initial_direction": direction.nominal, "initial_medium_id": "exterior", "initial_refractive_index": root.index,
                 "relative_weight": 1., "start_cumulative_m": 0., "start_interaction_count": 0, "outcome": ""}]
    branch_index = {"r0": branches[0]}
    segments, events, terminals = [], [], []
    maximum_direction = abs(math.hypot(*direction.nominal)-1.)
    maximum_point_width = maximum_direction_width = maximum_plane = 0.

    def terminal(state: _State, category: str, reason: str) -> None:
        branch_index[state.branch_id]["outcome"] = category
        terminals.append({"branch_id": state.branch_id, "category": category, "element_id": state.element_id,
                          "event_id": state.event_id, "position_m": state.ray.origin.nominal, "medium_id": state.medium,
                          "refractive_index": state.index, "cumulative_length_m": state.ray.cumulative_length_m,
                          "relative_weight": state.weight, "reason": reason})

    def truncate_all(state: _State, reason: str) -> None:
        terminal(state, "resource_truncated", reason)
        while queue:
            terminal(queue.popleft(), "resource_truncated", reason)

    def outgoing_record(state: _State) -> dict[str, Any]:
        return {"branch_id": state.branch_id, "direction": state.ray.direction.nominal,
                "medium_id": state.medium, "refractive_index": state.index, "relative_weight": state.weight}

    while queue:
        state = queue.popleft()
        while True:
            ray = state.ray
            if state.interactions >= MAX_INTERACTIONS:
                terminal(state, "resource_truncated", "interaction_cap")
                break
            remaining_i = CertifiedInterval.point(MAX_DISTANCE_M)-ray.cumulative_bounds
            if remaining_i.hi <= 0:
                terminal(state, "resource_truncated", "distance_cap")
                break
            if remaining_i.lo <= 0:
                raise NumericalAmbiguityError("remaining distance enclosure overlaps zero")
            if len(segments)+len(events) >= MAX_RECORDS or len(events) >= MAX_EVENTS or len(segments) >= MAX_SEGMENTS:
                truncate_all(state, "record_cap")
                break
            sphere, sphere_i = certified_domain_exit(ray, origin.nominal)
            speed, speed_i = certified_norm(ray.direction)
            distance = (MAX_DISTANCE_M-ray.cumulative_length_m)/speed
            distance_i = remaining_i/speed_i
            if sphere_i.hi < distance_i.lo:
                end_reason, parameter, parameter_i = "domain_exit", sphere, sphere_i
            elif distance_i.hi < sphere_i.lo:
                end_reason, parameter, parameter_i = "distance_cap", distance, distance_i
            else:
                raise NumericalAmbiguityError("domain and path-distance endpoint order is unresolved")
            hit = nearest_finite_hit(ray, scene._faces, parameter_i)
            if hit is not None and not hit.parameter_bounds.hi < parameter_i.lo:
                if hit.parameter_bounds.lo > parameter_i.hi:
                    hit = None
                else:
                    raise NumericalAmbiguityError("finite hit and endpoint order is unresolved")
            cost = 2 if hit is not None else 1
            if len(segments)+len(events)+cost > MAX_RECORDS or len(segments)+1 > MAX_SEGMENTS or hit is not None and len(events)+1 > MAX_EVENTS:
                truncate_all(state, "record_cap")
                break
            end = hit.position if hit is not None else certified_point_at(ray, parameter, parameter_i)
            _admit_vector(end, position=True)
            maximum_point_width = max(maximum_point_width, *(x.hi-x.lo for x in end.bounds))
            length, li = certified_norm(certified_vector_subtract(end, ray.origin))
            cumulative = ray.cumulative_length_m+length
            ci = (ray.cumulative_bounds+li).include(cumulative)
            segment_id = f"s{len(segments)+1:04d}"
            event_id = f"e{len(events)+1:04d}" if hit is not None else None
            segments.append({"id": segment_id, "branch_id": state.branch_id, "start_m": ray.origin.nominal, "end_m": end.nominal,
                             "direction": ray.direction.nominal, "medium_id": state.medium, "refractive_index": state.index,
                             "relative_weight": state.weight, "length_m": length, "cumulative_end_m": cumulative, "event_id": event_id})
            state.ray = _ray(end, ray.direction, cumulative, ci, hit.face.face_id if hit is not None else None)
            if hit is None:
                if state.medium != "exterior":
                    raise MediumStateAmbiguityError("body-interior route cannot escape the admitted closed body without a face event")
                state.event_id = state.element_id = None
                terminal(state, "escaped" if end_reason == "domain_exit" else "resource_truncated", end_reason)
                break
            face = hit.face
            state.event_id = event_id
            state.interactions += 1
            plane, _ = _signed_distance(end, face)
            maximum_plane = max(maximum_plane, abs(plane))
            bounds = {"t_parameter_interval_m": hit.parameter_bounds.pair(), "position_intervals_m": [x.pair() for x in end.bounds],
                      "local_uv_intervals_m": [x.pair() for x in hit.local_uv_bounds], "incident_direction_intervals": [x.pair() for x in ray.direction.bounds],
                      "outgoing_direction_intervals": [], "cumulative_length_interval_m": ci.pair(), "plane_residual_m": plane}
            event = {"id": event_id, "segment_id": segment_id, "branch_id": state.branch_id, "target": {}, "classification": "",
                     "position_m": end.nominal, "local_uv_m": hit.local_uv_m, "incident_direction": ray.direction.nominal,
                     "incident_medium_id": state.medium, "incident_refractive_index": state.index, "incoming_weight": state.weight,
                     "outgoing": [], "segment_length_m": length, "cumulative_length_m": cumulative, "numerical_bounds": bounds}
            events.append(event)
            if face.face_id in body_records:
                record = body_records[face.face_id]
                halfspaces = [_signed_distance(end, other)[1] for other in body_geometry]
                if any(side.hi >= 0 for other, side in zip(body_geometry, halfspaces) if other.face_id != face.face_id):
                    raise MediumStateAmbiguityError("body event does not certify the interior of every other halfspace")
                if state.medium not in ("exterior", interior["id"]):
                    raise MediumStateAmbiguityError("unknown incident medium")
                entering = state.medium == "exterior"
                other = interior if entering else exterior
                out, kind, ki, side, out_side = _dielectric_direction(ray.direction, face.plane_covector, state.index, other["refractive_index"], entering)
                event["target"] = {"kind": "body_face", "body_id": record["body_id"], "face_id": record["face_id"]}
                event["classification"] = ("enter_refraction" if entering else "exit_refraction") if kind == "refraction" else kind
                event.update(outward_normal=record["outward_normal"], local_basis=record["local_basis"].to_dict(),
                             incident_angle_rad=_angle(ray.direction.nominal, record["outward_normal"]),
                             outgoing_angle_rad=_angle(out.nominal, record["outward_normal"]))
                bounds.update(snell_discriminant_interval=ki.pair(), incident_side_interval=side.pair(), outgoing_side_interval=out_side.pair(),
                              body_halfspace_intervals_m=[x.pair() for x in halfspaces])
                if kind == "refraction":
                    state.medium, state.index = other["id"], other["refractive_index"]
                state.element_id = None
                state.ray = _ray(end, out, cumulative, ci, face.face_id)
                event["outgoing"].append(outgoing_record(state))
                bounds["outgoing_direction_intervals"].append({"branch_id": state.branch_id, "direction_intervals": [x.pair() for x in out.bounds]})
                maximum_direction = max(maximum_direction, abs(math.hypot(*out.nominal)-1.))
                maximum_direction_width = max(maximum_direction_width, *(x.hi-x.lo for x in out.bounds))
                continue
            if state.medium != "exterior":
                raise MediumStateAmbiguityError("legacy exterior element encountered in body medium")
            state.element_id = face.face_id
            kind = elements[face.face_id]["kind"]
            event["target"] = {"kind": "element", "element_id": face.face_id}
            event["classification"] = {"mirror": "mirror_reflection", "ideal_splitter_50_50": "ideal_split", "receiver": "receiver_hit", "beam_stop": "stop_hit"}[kind]
            if kind in ("receiver", "beam_stop"):
                terminal(state, "detected" if kind == "receiver" else "absorbed", event["classification"])
                break
            reflected = reflect_certified_direction(ray.direction, face)
            _admit_vector(reflected)
            maximum_direction = max(maximum_direction, abs(math.hypot(*reflected.nominal)-1.))
            maximum_direction_width = max(maximum_direction_width, *(x.hi-x.lo for x in reflected.bounds))
            if kind == "mirror":
                state.ray = _ray(end, reflected, cumulative, ci, face.face_id)
                event["outgoing"].append(outgoing_record(state))
                bounds["outgoing_direction_intervals"].append({"branch_id": state.branch_id, "direction_intervals": [x.pair() for x in reflected.bounds]})
                continue
            if len(branches)+2 > MAX_BRANCHES:
                truncate_all(state, "branch_cap")
                break
            branch_index[state.branch_id]["outcome"] = "split"
            for suffix, d in (("T", ray.direction), ("R", reflected)):
                identity = state.branch_id+"."+suffix
                weight = state.weight/2.
                child = {"id": identity, "parent_id": state.branch_id, "parent_event_id": event_id, "origin_m": end.nominal,
                         "initial_direction": d.nominal, "initial_medium_id": state.medium, "initial_refractive_index": state.index,
                         "relative_weight": weight, "start_cumulative_m": cumulative, "start_interaction_count": state.interactions, "outcome": ""}
                branches.append(child); branch_index[identity] = child
                pending = _State(identity, _ray(end, d, cumulative, ci, face.face_id), state.medium, state.index, weight, state.interactions, event_id, face.face_id)
                queue.append(pending)
                event["outgoing"].append(outgoing_record(pending))
                bounds["outgoing_direction_intervals"].append({"branch_id": identity, "direction_intervals": [x.pair() for x in d.bounds]})
            break
    totals = {key: math.fsum(x["relative_weight"] for x in terminals if x["category"] == category) for key, category in
              (("detected_weight", "detected"), ("absorbed_weight", "absorbed"), ("escaped_weight", "escaped"), ("truncated_weight", "resource_truncated"))}
    residual = 1.-math.fsum(totals.values())
    if abs(residual) > WEIGHT_ATOL:
        raise UnsupportedNumericalInputError("terminal weight ledger exceeds64epsilon")
    ledger = _freeze({"input_weight": 1., **totals, "signed_residual": residual})
    frames = [certify_pose_frame(x["pose"]["rotation_xyz_rad"]) for x in (*scene.bodies, *scene.elements)]
    frame_residual = max((frame.certificate["max_pose_error_bound"] for frame in frames), default=0.)
    diagnostics = _freeze({"predicate_policy": PREDICATE_POLICY, "max_direction_norm_residual": maximum_direction,
                           "max_frame_residual": frame_residual, "max_plane_residual_m": maximum_plane,
                           "max_point_width_m": maximum_point_width, "max_direction_width": maximum_direction_width})
    return RefractiveTraceResult(scene, WEIGHT_MODEL, scene.media, scene.body_faces, scene.legacy_surface_frames, scene.limits,
                                 "incomplete" if totals["truncated_weight"] else "complete", tuple(_freeze(x) for x in branches),
                                 tuple(_freeze(x) for x in segments), tuple(_freeze(x) for x in events), tuple(_freeze(x) for x in terminals), ledger, diagnostics)


# Additive W4 geometry seam. Everything above retains W3's original arithmetic
# and evaluation order. Polarization and Fresnel power are deliberately absent
# from this owner: it certifies only finite geometry and direction relations.
from ohlab.optics.geometric_routing import CertifiedPlanarHit


@dataclass(frozen=True, slots=True, init=False)
class CertifiedNormalIncidence:
    """Opaque exact direction lineage, re-proved against each actual affine face.

    Only this module issues instances. A lineage is tied to an owner and the
    actual certified vector object, not a nominal cardinal-axis label. The
    ``face_id`` on an interaction proof identifies its exact normal relation;
    outgoing lineages are not normal proofs until re-proved at the next face.
    """

    direction: CertifiedVector3
    face_id: str | None
    exact_direction: tuple[Fraction, ...]
    incident_facing_covector: CertifiedVector3 | None
    _owner: object = field(repr=False)

    def __init__(self) -> None:
        raise TypeError("normal relations are issued by the geometry owner")


@dataclass(frozen=True, slots=True, init=False)
class CertifiedDielectricGeometry:
    """Immutable actual finite handles and exact stored-affine owner data, SI.

    ``faces`` are the actual certified faces, never reconstructed wire meshes.
    Stored exact covectors target the same B and local witness as their face.
    """

    scene: RefractiveScene
    faces: tuple[CertifiedPlanarFace, ...]
    body_geometry: tuple[CertifiedPlanarFace, ...]
    body_face_records: tuple[FrozenRecord, ...]
    exact_covectors: tuple[tuple[Fraction, ...], ...]
    _owner: object = field(repr=False)

    def __init__(self) -> None:
        raise TypeError("use certified_geometry")

    def face_record(self, face: CertifiedPlanarFace) -> FrozenRecord | None:
        """Return actual face metadata, rejecting a foreign handle."""
        if not any(face is item for item in self.faces):
            raise ValueError("foreign certified face")
        for item, record in zip(self.body_geometry, self.body_face_records):
            if face is item:
                return record
        return None

    def halfspace_intervals(self, point: CertifiedVector3) -> tuple[CertifiedInterval, ...]:
        """Signed outward distances in metres, retaining all point uncertainty."""
        _admit_vector(point, position=True)
        return tuple(_signed_distance(point, face)[1] for face in self.body_geometry)

    def plane_residual_m(self, point: CertifiedVector3, face: CertifiedPlanarFace) -> float:
        """Nominal signed plane residual, metres; this does not move the point."""
        self.face_record(face)
        return _signed_distance(point, face)[0]


@dataclass(frozen=True, slots=True)
class CertifiedDielectricDirections:
    """Both physical departures and unchanged outward uncertainty certificates."""

    classification: str
    reflected: CertifiedVector3 | None
    transmitted: CertifiedVector3 | None
    incident_facing_covector: CertifiedVector3
    discriminant: CertifiedInterval
    incident_side: CertifiedInterval
    reflected_side: CertifiedInterval | None
    transmitted_side: CertifiedInterval | None
    incident_medium_id: str
    transmission_medium_id: str
    incident_index: float
    transmission_index: float
    normal_relation: CertifiedNormalIncidence | None
    reflected_relation: CertifiedNormalIncidence | None
    transmitted_relation: CertifiedNormalIncidence | None
    body_halfspaces: tuple[CertifiedInterval, ...]


def _seam_record(cls: Any, **values: Any) -> Any:
    result = object.__new__(cls)
    for key, value in values.items():
        object.__setattr__(result, key, value)
    return result


def certified_geometry(scene: RefractiveScene) -> CertifiedDielectricGeometry:
    """Own a public immutable view of an already validated W3 geometry scene.

    No trace is run. The exact affine covector target is computed from the
    owner's stored B, its rational inverse and the unchanged local covectors.
    """
    if not isinstance(scene, RefractiveScene):
        raise TypeError("certified_geometry requires RefractiveScene")
    count = len(scene.body_faces)
    exact = []
    if scene.bodies:
        body = scene.bodies[0]
        pose = certify_pose_frame(body["pose"]["rotation_xyz_rad"])
        inverse = _inverse(tuple(tuple(Fraction.from_float(x) for x in row) for row in pose.nominal_matrix))
        shape = body["shape"]
        for record in scene.body_faces:
            name = record["face_id"]
            cardinal = {"x_min": (-1,0,0), "x_max": (1,0,0), "y_min": (0,-1,0),
                        "y_max": (0,1,0), "z_min": (0,0,-1), "z_max": (0,0,1)}
            local = (Fraction.from_float(shape["leg_z_m"]), Fraction(0), Fraction.from_float(shape["leg_x_m"])) if name == "hypotenuse" else tuple(map(Fraction, cardinal[name]))
            exact.append(tuple(sum((inverse[j][i]*local[j] for j in range(3)), Fraction(0)) for i in range(3)))
    return _seam_record(CertifiedDielectricGeometry, scene=scene, faces=scene._faces,
                        body_geometry=scene._faces[:count], body_face_records=scene.body_faces,
                        exact_covectors=tuple(exact), _owner=object())


def _seam_lineage(geometry: CertifiedDielectricGeometry, direction: CertifiedVector3,
                  exact: tuple[Fraction, ...], face_id: str | None = None,
                  covector: CertifiedVector3 | None = None) -> CertifiedNormalIncidence:
    if not all(Fraction.from_float(interval.lo) <= value <= Fraction.from_float(interval.hi) for value, interval in zip(exact, direction.bounds)):
        raise UnsupportedNumericalInputError("exact direction lineage leaves inherited geometry enclosure")
    return _seam_record(CertifiedNormalIncidence, direction=direction, exact_direction=exact,
                        face_id=face_id, incident_facing_covector=covector, _owner=geometry._owner)


def certified_dielectric_directions(geometry: CertifiedDielectricGeometry, ray: CertifiedRay,
                                   hit: CertifiedPlanarHit, medium: str,
                                   normal_relation: CertifiedNormalIncidence | None = None) -> CertifiedDielectricDirections:
    """Certify both R/T directions at the actual closed-body crossing.

    Subcritical reflection uses the same covector algebra as the owner's TIR
    branch. No direction, point or enclosure is normalized/reset. A normal
    proof uses exact stored-affine parallelism and an owner-issued lineage;
    arbitrary nominal zero crosses and caller booleans are never accepted.
    """
    if not isinstance(geometry, CertifiedDielectricGeometry) or not isinstance(ray, CertifiedRay):
        raise TypeError("directions require certified geometry and ray")
    if not isinstance(hit,CertifiedPlanarHit):
        raise TypeError("directions require an actual CertifiedPlanarHit")
    if not isinstance(medium,str):
        raise TypeError("incident medium must be str")
    # CertifiedPlanarHit is intentionally opaque in the shared geometry API.
    face = hit.face
    record = geometry.face_record(face)
    if record is None:
        raise ValueError("dielectric directions require an actual body face")
    if normal_relation is not None and (not isinstance(normal_relation, CertifiedNormalIncidence)
            or normal_relation._owner is not geometry._owner or normal_relation.direction is not ray.direction):
        raise ValueError("foreign, stale or forged direction relation")
    interior = geometry.scene.bodies[0]["interior_medium"]
    exterior = geometry.scene.exterior_medium
    if medium not in (exterior["id"], interior["id"]):
        raise MediumStateAmbiguityError("unknown incident medium")
    entering = medium == exterior["id"]
    current, other = (exterior, interior) if entering else (interior, exterior)
    halfspaces = geometry.halfspace_intervals(hit.position)
    if any(side.hi >= 0 for other_face, side in zip(geometry.body_geometry, halfspaces) if other_face is not face):
        raise MediumStateAmbiguityError("body crossing is not strictly inside every other halfspace")
    outgoing, kind, ki, side, out_side = _dielectric_direction(ray.direction, face.plane_covector,
                                            current["refractive_index"], other["refractive_index"], entering)
    a = face.plane_covector if entering else certified_vector_scale(face.plane_covector, -1., CertifiedInterval.point(-1.))
    da, dai = certified_dot(ray.direction, a)
    aa, _ = certified_dot(a, a)
    aai = _squared(a)
    equal = current["refractive_index"] == other["refractive_index"]
    if equal:
        reflected, transmitted = None, outgoing
        rside, tside = None, certified_dot(transmitted, a)[1]
        classification = "equal_index_identity"
    else:
        reflected = outgoing if kind == "total_internal_reflection" else certified_vector_subtract(
            ray.direction, certified_vector_scale(a, 2.*da/aa, CertifiedInterval.point(2.)*dai/aai))
        _admit_vector(reflected)
        rside = certified_dot(reflected, a)[1]
        if rside.lo <= 0:
            raise MediumStateAmbiguityError("reflected departure is not strictly in incident medium")
        transmitted = None if kind == "total_internal_reflection" else outgoing
        tside = None if transmitted is None else certified_dot(transmitted, a)[1]
        if tside is not None and tside.hi >= 0:
            raise MediumStateAmbiguityError("transmitted departure is not strictly in transmission medium")
        classification = "total_internal_reflection" if transmitted is None else "dielectric_split"
    lineage = normal_relation
    if lineage is None and ray.cumulative_length_m == 0. and ray.previous_face_id is None:
        source = geometry.scene.source
        if ray.origin.nominal == tuple(source["origin_m"]) and ray.direction.nominal == tuple(source["direction"]) and all(
                interval.lo == value == interval.hi for value, interval in zip(ray.direction.nominal, ray.direction.bounds)):
            lineage = _seam_lineage(geometry, ray.direction, tuple(map(Fraction.from_float, ray.direction.nominal)))
    exact_a = geometry.exact_covectors[geometry.body_geometry.index(face)]
    if not entering:
        exact_a = tuple(-x for x in exact_a)
    normal = None
    reflected_relation = transmitted_relation = None
    if lineage is not None:
        d = lineage.exact_direction
        cross = tuple(d[j]*exact_a[k]-d[k]*exact_a[j] for j, k in ((1,2),(2,0),(0,1)))
        if all(x == 0 for x in cross):
            normal = _seam_lineage(geometry, ray.direction, d, face.face_id,a)
        da_exact = sum((x*y for x,y in zip(d, exact_a)), Fraction(0))
        aa_exact = sum((x*x for x in exact_a), Fraction(0))
        if reflected is not None:
            r_exact = tuple(x-2*da_exact*y/aa_exact for x,y in zip(d, exact_a))
            reflected_relation = _seam_lineage(geometry, reflected, r_exact)
        if transmitted is not None and (equal or normal is not None):
            transmitted_relation = _seam_lineage(geometry, transmitted, d)
    return CertifiedDielectricDirections(classification, reflected, transmitted, a, ki, certified_dot(ray.direction,a)[1],
        rside, tside, current["id"], other["id"], current["refractive_index"], other["refractive_index"],
        normal, reflected_relation, transmitted_relation, halfspaces)
