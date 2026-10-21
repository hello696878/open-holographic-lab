"""Bounded ideal geometric routing in SI metres, separate from wave optics.

One deterministic ray meets at most sixteen finite, two-sided planar faces.
Reflection uses an incoming propagation direction, not a rendering ``wo``.
Weights are dimensionless bookkeeping, never coherent amplitudes or watts.

Binary64 round-to-nearest arithmetic, gradual underflow, correctly directed
``nextafter`` and square root within one binary64 ulp are assumed. Each scalar
interval operation rounds outward. Origin, direction and geometric-distance
enclosures survive every interaction; they are never reset to an estimate.
Pose trigonometry additionally has an exact-rational Taylor remainder
certificate for each *stored binary64 angle*. It does not assume that one
``nextafter(math.sin(...))`` encloses a real sine. Returned binary64 frames
remain authoritative; certificates enclose both those stored frames and the
mathematical rotation at the stored angles. Nothing normalizes or snaps rays.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import math
from numbers import Real
import re
from typing import Any

MODEL_CONTRACT = "w2_ideal_geometric_routing_v1"
SCHEMA_VERSION = 1
EPSILON = 2.220446049250313e-16
INPUT_UNIT_ATOL = 32 * EPSILON
FRAME_ATOL = 64 * EPSILON
OUTPUT_UNIT_ATOL = 128 * EPSILON
WEIGHT_ATOL = 64 * EPSILON
MAX_ELEMENTS = 16
MAX_INTERACTIONS = 32
MAX_BRANCHES = 63
MAX_RECORDS = 256
MAX_HITS = 128
MAX_SEGMENTS = 256
TRACE_RADIUS_M = 1.0
MAX_DISTANCE_M = 10.0
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
Vec3 = tuple[float, float, float]


class NumericalAmbiguityError(ValueError):
    """A relevant finite geometric decision cannot be certified."""


class UnsupportedNumericalInputError(ValueError):
    """The declared numerical domain or arithmetic assumptions are exceeded."""


@dataclass(frozen=True, slots=True)
class FrozenRecord(Mapping[str, Any]):
    """An independently owned immutable record; ``to_dict`` returns a copy."""

    _items: tuple[tuple[str, Any], ...]

    def __getitem__(self, key: str) -> Any:
        for name, value in self._items:
            if key == name:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (name for name, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def to_dict(self) -> dict[str, Any]:
        """Return fresh ordinary Python containers without mutable aliases."""
        return {name: _thaw(value) for name, value in self._items}


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return FrozenRecord(tuple((key, _freeze(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, FrozenRecord):
        return value.to_dict()
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class _Interval:
    lo: float
    hi: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.lo) or not math.isfinite(self.hi) or self.lo > self.hi:
            raise UnsupportedNumericalInputError("nonfinite or inverted numerical enclosure")

    @staticmethod
    def point(value: float) -> _Interval:
        return _Interval(value, value)

    def __add__(self, other: _Interval) -> _Interval:
        return _Interval(_down(self.lo + other.lo), _up(self.hi + other.hi))

    def __neg__(self) -> _Interval:
        return _Interval(-self.hi, -self.lo)

    def __sub__(self, other: _Interval) -> _Interval:
        return self + -other

    def __mul__(self, other: _Interval) -> _Interval:
        products = (self.lo * other.lo, self.lo * other.hi,
                    self.hi * other.lo, self.hi * other.hi)
        return _Interval(_down(min(products)), _up(max(products)))

    def __truediv__(self, other: _Interval) -> _Interval:
        if other.lo <= 0.0 <= other.hi:
            raise NumericalAmbiguityError("division denominator enclosure contains zero")
        reciprocal = _Interval(_down(1.0 / other.hi), _up(1.0 / other.lo))
        return self * reciprocal

    def square(self) -> _Interval:
        low = 0.0 if self.lo <= 0.0 <= self.hi else _down(min(self.lo*self.lo, self.hi*self.hi))
        return _Interval(max(0.0, low), _up(max(self.lo*self.lo, self.hi*self.hi)))

    def sqrt(self) -> _Interval:
        if self.lo < 0.0:
            raise NumericalAmbiguityError("square-root enclosure crosses its mathematical domain")
        return _Interval(max(0.0, _down(math.sqrt(self.lo))), _up(math.sqrt(self.hi)))

    def absolute(self) -> _Interval:
        if self.lo <= 0.0 <= self.hi:
            return _Interval(0.0, max(-self.lo, self.hi))
        return _Interval(min(abs(self.lo), abs(self.hi)), max(abs(self.lo), abs(self.hi)))

    def include(self, value: float) -> _Interval:
        return _Interval(min(self.lo, value), max(self.hi, value))

    def pair(self) -> tuple[float, float]:
        return (self.lo, self.hi)


def _down(value: float) -> float:
    return math.nextafter(value, -math.inf)


def _up(value: float) -> float:
    return math.nextafter(value, math.inf)


def _i_sum(values: Any) -> _Interval:
    result = _Interval.point(0.0)
    for value in values:
        result = result + value
    return result


def _iv(vector: Vec3) -> tuple[_Interval, ...]:
    return tuple(_Interval.point(value) for value in vector)


def _i_dot(a: Any, b: Any) -> _Interval:
    return _i_sum(x*y for x, y in zip(a, b))


def _i_norm(a: Any) -> _Interval:
    squared = _i_sum(value.square() for value in a)
    # Sum-of-squares is mathematically nonnegative. Outward addition of exact
    # zeros may introduce a negative subnormal endpoint; intersecting with
    # [0,+inf) is a certified algebraic constraint, not physical clamping.
    return _Interval(max(0., squared.lo), squared.hi).sqrt()


def _dot(a: Any, b: Any) -> float:
    return math.fsum(x*y for x, y in zip(a, b))


def _difference(a: Any, b: Any) -> Vec3:
    return tuple(x-y for x, y in zip(a, b))


def _point_at(o: Vec3, d: Vec3, t: float) -> Vec3:
    return tuple(x+t*y for x, y in zip(o, d))


def _i_point_at(o: Any, d: Any, t: _Interval, nominal: Vec3) -> tuple[_Interval, ...]:
    return tuple((x+t*y).include(z) for x, y, z in zip(o, d, nominal))


def _fraction_enclosure(low: Fraction, high: Fraction) -> _Interval:
    """Prove rational-to-float endpoint direction by exact comparisons."""
    lo, hi = float(low), float(high)
    while Fraction.from_float(lo) > low:
        lo = math.nextafter(lo, -math.inf)
    while Fraction.from_float(hi) < high:
        hi = math.nextafter(hi, math.inf)
    return _Interval(lo, hi)


@lru_cache(maxsize=256)
def _certified_trig(angle: float) -> tuple[_Interval, _Interval]:
    """Sine/cosine at an exact binary64 angle, exact 32-term rational series.

    For abs(x)<=stored pi, term magnitudes are decreasing well before term32;
    the alternating-series remainder is bounded by the first omitted term.
    Fraction arithmetic computes the polynomial and remainder exactly.
    """
    x = Fraction.from_float(angle)
    xx = x*x
    sine_term = x
    cosine_term = Fraction(1)
    sine = sine_term
    cosine = cosine_term
    for k in range(1, 32):
        sine_term *= -xx / ((2*k)*(2*k+1))
        cosine_term *= -xx / ((2*k-1)*(2*k))
        sine += sine_term
        cosine += cosine_term
    sine_tail = abs(sine_term * -xx / (64*65))
    cosine_tail = abs(cosine_term * -xx / (63*64))
    return (_fraction_enclosure(sine-sine_tail, sine+sine_tail),
            _fraction_enclosure(cosine-cosine_tail, cosine+cosine_tail))


def _matrix_product(a: Any, b: Any, interval: bool = False) -> Any:
    product = _i_sum if interval else math.fsum
    return tuple(tuple(product(a[i][k]*b[k][j] for k in range(3))
                       for j in range(3)) for i in range(3))


def _pose_frame(angles: Vec3) -> tuple[Any, Any, FrozenRecord]:
    x, y, z = angles
    sx, cx, sy, cy, sz, cz = math.sin(x), math.cos(x), math.sin(y), math.cos(y), math.sin(z), math.cos(z)
    matrices = (((1., 0., 0.), (0., cx, -sx), (0., sx, cx)),
                ((cy, 0., sy), (0., 1., 0.), (-sy, 0., cy)),
                ((cz, -sz, 0.), (sz, cz, 0.), (0., 0., 1.)))
    nominal = _matrix_product(matrices[2], _matrix_product(matrices[1], matrices[0]))
    ix, icx = _certified_trig(x)
    iy, icy = _certified_trig(y)
    iz, icz = _certified_trig(z)
    zero, one = _Interval.point(0.), _Interval.point(1.)
    exact_matrices = (((one, zero, zero), (zero, icx, -ix), (zero, ix, icx)),
                      ((icy, zero, iy), (zero, one, zero), (-iy, zero, icy)),
                      ((icz, -iz, zero), (iz, icz, zero), (zero, zero, one)))
    ideal = _matrix_product(exact_matrices[2], _matrix_product(exact_matrices[1], exact_matrices[0], True), True)
    enclosed = tuple(tuple(ideal[i][j].include(nominal[i][j]) for j in range(3)) for i in range(3))
    error = max((_Interval.point(nominal[i][j])-ideal[i][j]).absolute().hi for i in range(3) for j in range(3))
    if error > FRAME_ATOL:
        raise UnsupportedNumericalInputError("pose arithmetic differs from its exact-angle certificate beyond frame policy")
    certificate = _freeze({"rotation_xyz_rad": angles, "matrix_intervals": [[cell.pair() for cell in row] for row in enclosed],
                           "sine_intervals": [ix.pair(), iy.pair(), iz.pair()], "cosine_intervals": [icx.pair(), icy.pair(), icz.pair()],
                           "max_pose_error_bound": error, "target": "stored frames and real RzRyRx at exact stored binary64 angles"})
    return nominal, enclosed, certificate


def _closed(value: Any, keys: set[str], context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{context} must be a mapping")
    if set(value) != keys:
        raise ValueError(f"{context} requires exactly {sorted(keys)!r}; got {sorted(map(str, value))!r}")
    return value


def _real(value: Any, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{context} must be a finite real scalar excluding bool")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{context} is not representable as binary64") from exc
    if not math.isfinite(result):
        raise ValueError(f"{context} must be finite; got {result!r}")
    return result


def _vector(value: Any, context: str) -> Vec3:
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{context} must be a list or tuple of three real scalars")
    if len(value) != 3:
        raise ValueError(f"{context} requires shape(3,), got length {len(value)}")
    return tuple(_real(item, f"{context}[{index}]") for index, item in enumerate(value))


def _identifier(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{context} must be an ASCII identifier")
    if _IDENTIFIER.fullmatch(value) is None:
        raise ValueError(f"{context} must match [A-Za-z][A-Za-z0-9_-]{{0,63}}")
    return value


@dataclass(frozen=True, slots=True)
class _Surface:
    element: FrozenRecord
    center: Vec3
    u: Vec3
    v: Vec3
    n: Vec3
    ui: tuple[_Interval, ...]
    vi: tuple[_Interval, ...]
    ni: tuple[_Interval, ...]
    bounding_radius: _Interval
    frame_residual: float


@dataclass(frozen=True, slots=True)
class GeometricScene:
    """Owned version1 ideal scene; positions metres, active XYZ angles radians.

    Use ``from_dict``. All public execution revalidates a scene, so constructing
    this dataclass directly cannot bypass the bounded public input checks.
    """

    _record: FrozenRecord = field(repr=False)
    surface_frames: tuple[FrozenRecord, ...]
    pose_certificates: tuple[FrozenRecord, ...] = field(repr=False)
    _surfaces: tuple[_Surface, ...] = field(repr=False)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> GeometricScene:
        """Validate and own a closed scene mapping without tracing."""
        return validate_scene(value)

    @property
    def source(self) -> FrozenRecord:
        return self._record["source"]

    @property
    def elements(self) -> tuple[FrozenRecord, ...]:
        return self._record["elements"]

    def to_dict(self) -> dict[str, Any]:
        """Return a new closed scene mapping, preserving submitted order."""
        return self._record.to_dict()


def validate_scene(value: GeometricScene | Mapping[str, Any]) -> GeometricScene:
    """Validate the complete scene and pose/domain admission, never trace.

    Metres internally. Source coordinates have absolute component limit10m;
    a complete aperture must be certified strictly inside the source's 1m
    trace sphere. Unit directions are admitted, never silently normalized.
    """
    if isinstance(value, GeometricScene):
        value = value.to_dict()
    data = _closed(value, {"schema_version", "model_contract", "source", "elements"}, "scene")
    if type(data["schema_version"]) is not int:
        raise TypeError("scene.schema_version must be an integer excluding bool")
    if data["schema_version"] != SCHEMA_VERSION:
        raise ValueError("scene.schema_version must be integer1")
    if not isinstance(data["model_contract"], str):
        raise TypeError("scene.model_contract must be str")
    if data["model_contract"] != MODEL_CONTRACT:
        raise ValueError(f"scene.model_contract must equal {MODEL_CONTRACT!r}")
    source = _closed(data["source"], {"id", "origin_m", "direction", "relative_weight"}, "scene.source")
    if not isinstance(source["id"], str):
        raise TypeError("scene.source.id must be str")
    if source["id"] != "source":
        raise ValueError("scene.source.id must equal 'source'")
    origin = _vector(source["origin_m"], "scene.source.origin_m")
    direction = _vector(source["direction"], "scene.source.direction")
    weight = _real(source["relative_weight"], "scene.source.relative_weight")
    if weight != 1.:
        raise ValueError("one source must have relative_weight exactly1")
    if any(abs(item) > 10. for item in origin):
        raise ValueError("source origin component exceeds absolute10m domain")
    if abs(math.hypot(*direction)-1.) > INPUT_UNIT_ATOL:
        raise ValueError("source direction must already be nominal unit within32epsilon; no normalization")
    elements = data["elements"]
    if not isinstance(elements, (list, tuple)):
        raise TypeError("scene.elements must be a list or tuple")
    if len(elements) > MAX_ELEMENTS:
        raise ValueError(f"scene.elements exceeds maximum{MAX_ELEMENTS}")
    owned_elements, surfaces, frames, certificates = [], [], [], []
    used = {"source"}
    for index, raw in enumerate(elements):
        context = f"scene.elements[{index}]"
        element = _closed(raw, {"id", "kind", "pose", "aperture"}, context)
        identity = _identifier(element["id"], context+".id")
        if identity in used:
            raise ValueError(f"duplicate/reserved element id {identity!r}")
        used.add(identity)
        kind = element["kind"]
        if not isinstance(kind, str):
            raise TypeError(context+".kind must be str")
        if kind not in ("mirror", "ideal_splitter_50_50", "beam_stop", "receiver"):
            raise ValueError(f"{context}.kind is unsupported: {kind!r}")
        pose = _closed(element["pose"], {"position_m", "rotation_xyz_rad"}, context+".pose")
        position = _vector(pose["position_m"], context+".pose.position_m")
        angles = _vector(pose["rotation_xyz_rad"], context+".pose.rotation_xyz_rad")
        if any(abs(angle) > math.pi for angle in angles):
            raise ValueError(f"{context} rotation components must lie in [-pi,+pi] radians")
        aperture = element["aperture"]
        if not isinstance(aperture, Mapping):
            raise TypeError(context+".aperture must be a mapping")
        if not isinstance(aperture.get("kind"), str):
            raise TypeError(context+".aperture.kind must be str")
        if aperture.get("kind") == "disk":
            _closed(aperture, {"kind", "radius_m"}, context+".aperture")
            radius = _real(aperture["radius_m"], context+".aperture.radius_m")
            dimensions = (radius,)
            owned_aperture = {"kind": "disk", "radius_m": radius}
            circumradius = _Interval.point(radius)
        elif aperture.get("kind") == "rectangle":
            _closed(aperture, {"kind", "width_m", "height_m"}, context+".aperture")
            width = _real(aperture["width_m"], context+".aperture.width_m")
            height = _real(aperture["height_m"], context+".aperture.height_m")
            dimensions = (width, height)
            owned_aperture = {"kind": "rectangle", "width_m": width, "height_m": height}
            circumradius = (_Interval.point(width).square()+_Interval.point(height).square()).sqrt()/_Interval.point(2.)
        else:
            raise ValueError(context+".aperture.kind must be disk or rectangle")
        if any(not 1e-6 <= item <= .25 for item in dimensions):
            raise ValueError(context+" aperture dimensions must lie in [1e-6,.25] metres")
        nominal, enclosed, certificate = _pose_frame(angles)
        columns = tuple(tuple(nominal[i][j] for i in range(3)) for j in range(3))
        icols = tuple(tuple(enclosed[i][j] for i in range(3)) for j in range(3))
        residual = max(abs(_dot(a, b)-(1. if i == j else 0.)) for i, a in enumerate(columns) for j, b in enumerate(columns))
        if residual > FRAME_ATOL:
            raise UnsupportedNumericalInputError(context+" derived frame orthogonality exceeds64epsilon")
        # For F with rows(u,v,n), Gershgorin gives sigma_min(F)^2>=1-g.
        # Therefore the actual finite projection footprint fits r/sqrt(1-g).
        # This expands only a culling/admission bound, never the optical face.
        gram_error = tuple(tuple(_i_dot(a, b)-_Interval.point(1. if i == j else 0.)
                                 for j, b in enumerate(icols)) for i, a in enumerate(icols))
        gamma = max(_i_sum(cell.absolute() for cell in row).hi for row in gram_error)
        if gamma >= .5:
            raise UnsupportedNumericalInputError(context+" frame certificate has unsupported conditioning")
        bounding_radius = circumradius/(_Interval.point(1.)-_Interval.point(gamma)).sqrt()
        distance = _i_norm(tuple(_Interval.point(a)-_Interval.point(b) for a, b in zip(position, origin)))
        if (distance+bounding_radius).hi >= TRACE_RADIUS_M:
            raise ValueError(context+" complete aperture must be certified strictly inside source-centered radius1m sphere")
        owned = _freeze({"id": identity, "kind": kind, "pose": {"position_m": position, "rotation_xyz_rad": angles}, "aperture": owned_aperture})
        owned_elements.append(owned)
        frames.append(_freeze({"element_id": identity, "u": columns[0], "v": columns[1], "n": columns[2]}))
        certificates.append(certificate)
        surfaces.append(_Surface(owned, position, *columns, *icols, bounding_radius, residual))
    record = _freeze({"schema_version": 1, "model_contract": MODEL_CONTRACT,
                      "source": {"id": "source", "origin_m": origin, "direction": direction, "relative_weight": 1.},
                      "elements": [item.to_dict() for item in owned_elements]})
    return GeometricScene(record, tuple(frames), tuple(certificates), tuple(surfaces))


@dataclass(frozen=True, slots=True)
class GeometricTraceResult:
    """Immutable full bounded trace, plus non-wire validation certificates."""

    scene: GeometricScene
    surface_frames: tuple[FrozenRecord, ...]
    limits: FrozenRecord
    status: str
    branches: tuple[FrozenRecord, ...]
    segments: tuple[FrozenRecord, ...]
    hits: tuple[FrozenRecord, ...]
    terminals: tuple[FrozenRecord, ...]
    ledger: FrozenRecord
    diagnostics: FrozenRecord
    certificates: tuple[FrozenRecord, ...] = field(repr=False)

    def to_dict(self) -> dict[str, Any]:
        """Return the ten closed core reply keys; transport adds its identity."""
        return {"scene": self.scene.to_dict(), "surface_frames": [item.to_dict() for item in self.surface_frames],
                "limits": self.limits.to_dict(), "status": self.status,
                "branches": [item.to_dict() for item in self.branches], "segments": [item.to_dict() for item in self.segments],
                "hits": [item.to_dict() for item in self.hits], "terminals": [item.to_dict() for item in self.terminals],
                "ledger": self.ledger.to_dict(), "diagnostics": self.diagnostics.to_dict()}


@dataclass(slots=True)
class _RayState:
    branch_id: str
    origin: Vec3
    oi: tuple[_Interval, ...]
    direction: Vec3
    di: tuple[_Interval, ...]
    weight: float
    cumulative: float
    ci: _Interval
    interactions: int
    previous: str | None
    last_hit: str | None


@dataclass(frozen=True, slots=True)
class _HitCandidate:
    surface: _Surface
    parameter: float
    ti: _Interval
    point: Vec3
    pi: tuple[_Interval, ...]
    local: tuple[float, float]
    local_i: tuple[_Interval, _Interval]


def _reflection(direction: Vec3, di: Any, surface: _Surface) -> tuple[Vec3, Any]:
    dot = _dot(direction, surface.n)
    nominal = tuple(direction[i]-2.*dot*surface.n[i] for i in range(3))
    # Algebraically identical Householder form avoids interval dependency
    # tripling in d-2*dot(d,n)*n at each of 32 ordinary axial reflections.
    matrix = tuple(tuple(_Interval.point(1. if i == j else 0.)-_Interval.point(2.)*surface.ni[i]*surface.ni[j]
                         for j in range(3)) for i in range(3))
    enclosed = tuple(_i_dot(row, di).include(nominal[i]) for i, row in enumerate(matrix))
    if abs(math.hypot(*nominal)-1.) > OUTPUT_UNIT_ATOL:
        raise UnsupportedNumericalInputError("reflected nominal direction exceeds128epsilon unit residual; no normalization")
    return nominal, enclosed


def _domain_exit(state: _RayState, source: Vec3) -> tuple[float, _Interval]:
    q = _difference(state.origin, source)
    qi = tuple(a-_Interval.point(b) for a, b in zip(state.oi, source))
    a, b, c = _dot(state.direction, state.direction), _dot(q, state.direction), _dot(q, q)-1.
    ai, bi, ci = _i_dot(state.di, state.di), _i_dot(qi, state.di), _i_dot(qi, qi)-_Interval.point(1.)
    if ai.lo <= 0. or ci.hi >= 0.:
        raise NumericalAmbiguityError("current ray state is not certified inside its source-centered trace sphere")
    discriminant = bi.square()-ai*ci
    root_i = discriminant.sqrt()
    if bi.lo >= 0.:
        ti = -ci/(bi+root_i)
    else:
        ti = (-bi+root_i)/ai
    root = math.sqrt(b*b-a*c)
    t = -c/(b+root) if b >= 0. else (-b+root)/a
    return t, ti.include(t)


def _finite_cull(state: _RayState, surface: _Surface, upper_t: _Interval) -> bool:
    """True only if a certified line/finite-leg bound proves a face miss."""
    q = tuple(_Interval.point(a)-b for a, b in zip(surface.center, state.oi))
    dd = _i_dot(state.di, state.di)
    projection = _i_dot(q, state.di)
    if dd.lo <= 0.:
        raise NumericalAmbiguityError("direction enclosure includes an unusable zero direction")
    closest = projection/dd
    if closest.hi < 0.:
        distance2 = _i_dot(q, q)
    elif closest.lo > upper_t.hi:
        end = tuple(o+d*upper_t for o, d in zip(state.oi, state.di))
        difference = tuple(_Interval.point(c)-p for c, p in zip(surface.center, end))
        distance2 = _i_dot(difference, difference)
    else:
        distance2 = _i_dot(q, q)-projection.square()/dd
    return distance2.lo > surface.bounding_radius.square().hi


def _possible_lower_t(state: _RayState, surface: _Surface) -> float:
    q = tuple(_Interval.point(a)-b for a, b in zip(surface.center, state.oi))
    # The distance/speed division is itself outward-rounded; a nominal
    # division rounded upward would not be a certified lower travel bound.
    return max(0., ((_i_norm(q)-surface.bounding_radius)/_i_norm(state.di)).lo)


def _candidate(state: _RayState, surface: _Surface, upper_t: _Interval) -> tuple[_HitCandidate | None, float | None, str | None]:
    if surface.element["id"] == state.previous or _finite_cull(state, surface, upper_t):
        return None, None, None
    den = _i_dot(state.di, surface.ni)
    q = tuple(_Interval.point(a)-b for a, b in zip(surface.center, state.oi))
    num = _i_dot(q, surface.ni)
    lower = _possible_lower_t(state, surface)
    if den.lo <= 0. <= den.hi:
        return None, lower, "relevant parallel/coplanar/grazing plane is unresolved"
    ti = num/den
    if ti.hi < 0. or ti.lo > upper_t.hi:
        return None, None, None
    if ti.lo <= 0.:
        return None, max(0., ti.lo), "relevant near-launch or zero-distance hit is unresolved"
    nominal_den = _dot(state.direction, surface.n)
    if nominal_den == 0.:
        return None, max(0., ti.lo), "nominal plane denominator is zero"
    parameter = _dot(_difference(surface.center, state.origin), surface.n)/nominal_den
    point = _point_at(state.origin, state.direction, parameter)
    pi = _i_point_at(state.oi, state.di, ti, point)
    # Exact plane-constraint refinement prevents origin dependency wrapping;
    # this intersects two certified enclosures, never snaps the nominal hit.
    pivot = max(range(3), key=lambda i: abs(surface.n[i]))
    if not surface.ni[pivot].lo <= 0. <= surface.ni[pivot].hi:
        other = _i_sum(surface.ni[j]*(pi[j]-_Interval.point(surface.center[j])) for j in range(3) if j != pivot)
        constraint = _Interval.point(surface.center[pivot])-other/surface.ni[pivot]
        lo, hi = max(pi[pivot].lo, constraint.lo), min(pi[pivot].hi, constraint.hi)
        if lo > hi:
            raise UnsupportedNumericalInputError("inconsistent plane hit enclosures")
        pi = tuple(_Interval(lo, hi).include(point[j]) if j == pivot else pi[j] for j in range(3))
    relative = tuple(p-_Interval.point(c) for p, c in zip(pi, surface.center))
    local_i = (_i_dot(relative, surface.ui), _i_dot(relative, surface.vi))
    nominal_relative = _difference(point, surface.center)
    local = (_dot(nominal_relative, surface.u), _dot(nominal_relative, surface.v))
    aperture = surface.element["aperture"]
    if aperture["kind"] == "disk":
        radius2 = _Interval.point(aperture["radius_m"]).square()
        rho2 = local_i[0].square()+local_i[1].square()
        if rho2.lo > radius2.hi:
            return None, None, None
        if rho2.hi >= radius2.lo:
            return None, max(0., ti.lo), "finite disk edge is numerically ambiguous"
    else:
        for coordinate, name in zip(local_i, ("width_m", "height_m")):
            half = _Interval.point(aperture[name])/_Interval.point(2.)
            if coordinate.absolute().lo > half.hi:
                return None, None, None
        if any(coordinate.absolute().hi >= (_Interval.point(aperture[name])/_Interval.point(2.)).lo
               for coordinate, name in zip(local_i, ("width_m", "height_m"))):
            return None, max(0., ti.lo), "finite rectangle edge is numerically ambiguous"
    return _HitCandidate(surface, parameter, ti.include(parameter), point, pi, local, local_i), None, None


def _nearest(state: _RayState, surfaces: Any, upper_t: _Interval) -> _HitCandidate | None:
    candidates, unresolved = [], []
    for surface in surfaces:
        hit, lower, reason = _candidate(state, surface, upper_t)
        if hit is not None:
            candidates.append(hit)
        if reason is not None:
            unresolved.append((lower, surface.element["id"], reason))
    candidates.sort(key=lambda item: (item.ti.lo, item.surface.element["id"]))
    best = candidates[0] if candidates else None
    if best is not None:
        for candidate in candidates[1:]:
            if not best.ti.hi < candidate.ti.lo:
                raise NumericalAmbiguityError(f"nearest-hit order/tie unresolved between {best.surface.element['id']} and {candidate.surface.element['id']}")
        for lower, identity, reason in unresolved:
            if not best.ti.hi < lower:
                raise NumericalAmbiguityError(f"{identity}: {reason}; it may precede the certified candidate")
    elif unresolved:
        lower, identity, reason = min(unresolved, key=lambda item: (item[0], item[1]))
        if lower <= upper_t.hi:
            raise NumericalAmbiguityError(f"{identity}: {reason}")
    return best


def _limits() -> FrozenRecord:
    return _freeze({"max_elements": MAX_ELEMENTS, "max_interactions": MAX_INTERACTIONS, "max_branches": MAX_BRANCHES,
                    "max_records": MAX_RECORDS, "max_hits": MAX_HITS, "max_segments": MAX_SEGMENTS,
                    "trace_radius_m": TRACE_RADIUS_M, "max_distance_m": MAX_DISTANCE_M})


def trace_routes(scene: GeometricScene) -> GeometricTraceResult:
    """Trace once, returning an immutable bounded geometric result in metres.

    The root counts as a created branch. A physical hit costs one segment and
    one hit record; a sphere/distance endpoint costs one segment. BFS creates
    T then R children atomically. Receiver/stop processing wins at hit32;
    surviving work at that count truncates. An unresolved equality/order at
    distance10m fails rather than using nominal equality as a tiebreak.
    """
    if not isinstance(scene, GeometricScene):
        raise TypeError("trace_routes requires a validated GeometricScene")
    scene = validate_scene(scene)
    origin, direction = scene.source["origin_m"], scene.source["direction"]
    root = _RayState("r0", origin, _iv(origin), direction, _iv(direction), 1., 0., _Interval.point(0.), 0, None, None)
    queue = deque([root])
    branches = [{"id": "r0", "parent_id": None, "parent_hit_id": None, "origin_m": origin,
                 "initial_direction": direction, "relative_weight": 1., "start_cumulative_m": 0., "start_interaction_count": 0, "outcome": ""}]
    branch_index = {"r0": branches[0]}
    segments, hits, terminals, certificates = [], [], [], []
    max_direction = abs(math.hypot(*direction)-1.)
    max_plane = max_point = 0.

    def terminal(state: _RayState, category: str, reason: str) -> None:
        branch_index[state.branch_id]["outcome"] = category
        terminals.append({"branch_id": state.branch_id, "category": category, "element_id": state.previous,
                          "hit_id": state.last_hit, "position_m": state.origin, "cumulative_length_m": state.cumulative,
                          "relative_weight": state.weight, "reason": reason})

    def global_truncate(state: _RayState, reason: str) -> None:
        terminal(state, "resource_truncated", reason)
        while queue:
            terminal(queue.popleft(), "resource_truncated", reason)

    while queue:
        state = queue.popleft()
        while True:
            if state.interactions >= MAX_INTERACTIONS:
                terminal(state, "resource_truncated", "interaction_cap")
                break
            remaining_i = _Interval.point(MAX_DISTANCE_M)-state.ci
            if remaining_i.hi <= 0.:
                terminal(state, "resource_truncated", "distance_cap")
                break
            if remaining_i.lo <= 0.:
                raise NumericalAmbiguityError("remaining path-distance enclosure overlaps zero")
            sphere_t, sphere_i = _domain_exit(state, origin)
            speed_i = _i_norm(state.di)
            distance_t = (MAX_DISTANCE_M-state.cumulative)/math.hypot(*state.direction)
            distance_i = remaining_i/speed_i
            if sphere_i.hi < distance_i.lo:
                endpoint_kind, endpoint_t, endpoint_i = "domain_exit", sphere_t, sphere_i
            elif distance_i.hi < sphere_i.lo:
                endpoint_kind, endpoint_t, endpoint_i = "distance_cap", distance_t, distance_i
            else:
                raise NumericalAmbiguityError("domain-exit and cumulative-distance boundary ordering is unresolved")
            hit = _nearest(state, scene._surfaces, endpoint_i)
            if hit is not None and not hit.ti.hi < endpoint_i.lo:
                if hit.ti.lo > endpoint_i.hi:
                    hit = None
                else:
                    raise NumericalAmbiguityError("finite hit and trace/distance boundary ordering is unresolved")
            cost = 2 if hit is not None else 1
            if (len(segments)+len(hits)+cost > MAX_RECORDS or len(segments)+1 > MAX_SEGMENTS
                    or hit is not None and len(hits)+1 > MAX_HITS):
                global_truncate(state, "record_cap")
                break
            end = hit.point if hit is not None else _point_at(state.origin, state.direction, endpoint_t)
            end_i = hit.pi if hit is not None else _i_point_at(state.oi, state.di, endpoint_i, end)
            step_vector = _difference(end, state.origin)
            length = math.hypot(*step_vector)
            length_i = _i_norm(tuple(a-b for a, b in zip(end_i, state.oi))).include(length)
            cumulative = state.cumulative+length
            cumulative_i = (state.ci+length_i).include(cumulative)
            segment_id = f"s{len(segments):04d}"
            hit_id = f"h{len(hits):04d}" if hit is not None else None
            segments.append({"id": segment_id, "branch_id": state.branch_id, "start_m": state.origin, "end_m": end,
                             "direction": state.direction, "relative_weight": state.weight, "length_m": length,
                             "cumulative_end_m": cumulative, "hit_id": hit_id})
            error = max((_Interval.point(value)-i).absolute().hi for value, i in zip(end, end_i))
            max_point = max(max_point, error)
            certificate = {"segment_id": segment_id, "branch_id": state.branch_id,
                           "start_intervals_m": [x.pair() for x in state.oi], "direction_intervals": [x.pair() for x in state.di],
                           "end_intervals_m": [x.pair() for x in end_i], "length_interval_m": length_i.pair(),
                           "cumulative_interval_m": cumulative_i.pair(), "outgoing_direction_intervals": []}
            certificates.append(certificate)
            state.origin, state.oi, state.cumulative, state.ci = end, end_i, cumulative, cumulative_i
            if hit is None:
                if endpoint_kind == "distance_cap":
                    terminal(state, "resource_truncated", "distance_cap")
                else:
                    # A domain endpoint is not a hit, even after a real surface.
                    previous, previous_hit = state.previous, state.last_hit
                    state.previous = state.last_hit = None
                    terminal(state, "escaped", "domain_exit")
                    state.previous, state.last_hit = previous, previous_hit
                break
            surface = hit.surface
            state.interactions += 1
            state.previous, state.last_hit = surface.element["id"], hit_id
            signed_plane = _dot(_difference(end, surface.center), surface.n)
            max_plane = max(max_plane, abs(signed_plane))
            event = {"id": hit_id, "segment_id": segment_id, "branch_id": state.branch_id,
                     "element_id": surface.element["id"], "position_m": end, "local_uv_m": hit.local,
                     "incident_direction": state.direction, "incoming_weight": state.weight, "outgoing": [],
                     "segment_length_m": length, "cumulative_length_m": cumulative,
                     "numerical_bounds": {"t_parameter_interval_m": hit.ti.pair(), "position_intervals_m": [x.pair() for x in end_i],
                                          "local_uv_intervals_m": [x.pair() for x in hit.local_i], "plane_residual_m": signed_plane}}
            hits.append(event)
            kind = surface.element["kind"]
            if kind in ("receiver", "beam_stop"):
                terminal(state, "detected" if kind == "receiver" else "absorbed", "receiver_hit" if kind == "receiver" else "stop_hit")
                break
            reflected, reflected_i = _reflection(state.direction, state.di, surface)
            max_direction = max(max_direction, abs(math.hypot(*reflected)-1.))
            if kind == "mirror":
                event["outgoing"].append({"branch_id": state.branch_id, "direction": reflected, "relative_weight": state.weight})
                certificate["outgoing_direction_intervals"] = [[x.pair() for x in reflected_i]]
                state.direction, state.di = reflected, reflected_i
                continue
            if len(branches)+2 > MAX_BRANCHES:
                global_truncate(state, "branch_cap")
                break
            branch_index[state.branch_id]["outcome"] = "split"
            for suffix, d, di in (("T", state.direction, state.di), ("R", reflected, reflected_i)):
                child_id = state.branch_id+"."+suffix
                child_weight = state.weight/2.
                child = {"id": child_id, "parent_id": state.branch_id, "parent_hit_id": hit_id, "origin_m": end,
                         "initial_direction": d, "relative_weight": child_weight, "start_cumulative_m": cumulative,
                         "start_interaction_count": state.interactions, "outcome": ""}
                branches.append(child)
                branch_index[child_id] = child
                queue.append(_RayState(child_id, end, end_i, d, di, child_weight, cumulative, cumulative_i,
                                       state.interactions, surface.element["id"], hit_id))
                event["outgoing"].append({"branch_id": child_id, "direction": d, "relative_weight": child_weight})
                certificate["outgoing_direction_intervals"].append([x.pair() for x in di])
            break
    totals = {name: math.fsum(item["relative_weight"] for item in terminals if item["category"] == category)
              for name, category in (("detected_weight", "detected"), ("absorbed_weight", "absorbed"),
                                     ("escaped_weight", "escaped"), ("truncated_weight", "resource_truncated"))}
    residual = 1.-math.fsum(totals.values())
    if abs(residual) > WEIGHT_ATOL:
        raise UnsupportedNumericalInputError("terminal-leaf weight accounting exceeds declared64epsilon bound")
    ledger = _freeze({"input_weight": 1., **totals, "signed_residual": residual})
    diagnostics = _freeze({"predicate_policy": "binary64_outward_intervals_v1", "max_direction_norm_residual": max_direction,
                           "max_frame_orthogonality_residual": max((item.frame_residual for item in scene._surfaces), default=0.),
                           "max_plane_residual_m": max_plane, "max_point_error_bound_m": max_point})
    return GeometricTraceResult(scene, scene.surface_frames, _limits(), "incomplete" if totals["truncated_weight"] else "complete",
                                tuple(_freeze(x) for x in branches), tuple(_freeze(x) for x in segments), tuple(_freeze(x) for x in hits),
                                tuple(_freeze(x) for x in terminals), ledger, diagnostics, tuple(_freeze(x) for x in certificates))
