"""W4 lossless dielectric power-coherency operators with outward certificates.

SI geometry is supplied by its public owner. Harmonic convention exp(-i wt),
right-handed (e1,e2,k), C01=<u1 u2*> and S3=-2 Im(C01). The complete trace of
C is source-relative optical power; it is never another normalized weight.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import math
from numbers import Real
from typing import Any

from ohlab.optics.geometric_routing import (
    CertifiedInterval, CertifiedVector3, NumericalAmbiguityError,
    UnsupportedNumericalInputError, certify_vector, certified_dot,
    certified_norm, certified_vector_scale,
)
from ohlab.optics.refractive_routing import CertifiedDielectricDirections,CertifiedNormalIncidence,FrozenRecord

EPS = 2.220446049250313e-16
MAX_FRAME_WIDTH = 1e-8
MAX_COEFFICIENT_WIDTH = 1e-8
MAX_C_WIDTH = 1e-8
POLARIZATION_POLICY = "outward_power_coherency_v1"
SOURCE_C = FrozenRecord((("unpolarized",(.5,.5,0.,0.)),("linear_e1",(1.,0.,0.,0.)),
                         ("linear_e2",(0.,1.,0.,0.)),("linear_45",(.5,.5,.5,0.))))
_CONGRUENCE_TOKEN = object()


class UnsupportedPolarizationNumericsError(UnsupportedNumericalInputError):
    """An accumulated frame/coherency/coefficient cannot be certified reliably."""


def _real(value: Any, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{context} requires a finite real excluding bool")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{context} is not binary64-representable") from exc
    if not math.isfinite(result):
        raise ValueError(f"{context} must be finite")
    return result


def _point(value: float) -> CertifiedInterval:
    return CertifiedInterval.point(value)


def _sum(values: Any) -> CertifiedInterval:
    result = _point(0.)
    for value in values:
        result = result+value
    return result


def _fraction_bounds(value: Fraction) -> CertifiedInterval:
    lo = hi = float(value)
    if not math.isfinite(lo):
        raise UnsupportedPolarizationNumericsError("exact scalar is not finite binary64")
    while Fraction.from_float(lo) > value:
        lo = math.nextafter(lo, -math.inf)
    while Fraction.from_float(hi) < value:
        hi = math.nextafter(hi, math.inf)
    return CertifiedInterval(lo,hi)


def _width(intervals: Any) -> float:
    return max((x.hi-x.lo for x in intervals), default=0.)


def _admit_width(intervals: Any, limit: float, context: str) -> None:
    width = _width(intervals)
    if width > limit:
        raise UnsupportedPolarizationNumericsError(f"{context} width {width!r} exceeds {limit!r}; no enclosure reset")


def checked_positive_product(a: float, b: float, *, context: str = "power product") -> float:
    """Multiply stored nonnegative scalars with the frozen 64eps relative gate.

    Exact subnormal products are admitted. A positive-to-zero or inaccurate
    subnormal product is unsupported, never a discarded branch or absorption.
    """
    a, b = _real(a,context), _real(b,context)
    if a < 0 or b < 0:
        raise ValueError(f"{context} factors must be nonnegative")
    target = Fraction.from_float(a)*Fraction.from_float(b)
    value = a*b
    if not math.isfinite(value) or (target > 0 and (value <= 0 or
            abs(Fraction.from_float(value)-target) > Fraction.from_float(64*EPS)*target)):
        raise UnsupportedPolarizationNumericsError(f"{context}: positive product is not reliably binary64-representable ({a!r} * {b!r})")
    return value


def checked_amplitude_power(value: complex, *, context: str = "coefficient power") -> float:
    """Squared complex modulus with the same exact-positive representation gate."""
    if not isinstance(value,complex):
        raise TypeError("amplitude must be complex")
    real,imag=_real(value.real,context),_real(value.imag,context)
    parts=(checked_positive_product(abs(real),abs(real),context=context),
           checked_positive_product(abs(imag),abs(imag),context=context))
    result=math.fsum(parts)
    target=Fraction.from_float(real)**2+Fraction.from_float(imag)**2
    if target>0 and (result<=0 or abs(Fraction.from_float(result)-target)>Fraction.from_float(64*EPS)*target):
        raise UnsupportedPolarizationNumericsError(f"{context}: positive amplitude power is not reliably represented")
    return result


def _cross(left: CertifiedVector3, right: CertifiedVector3) -> CertifiedVector3:
    pairs = ((1,2),(2,0),(0,1))
    nominal = tuple(left.nominal[j]*right.nominal[k]-left.nominal[k]*right.nominal[j] for j,k in pairs)
    bounds = tuple((left.bounds[j]*right.bounds[k]-left.bounds[k]*right.bounds[j]).include(n)
                   for (j,k),n in zip(pairs,nominal))
    return certify_vector(nominal,bounds)


def _unit(vector: CertifiedVector3) -> CertifiedVector3:
    value,bound = certified_norm(vector)
    if bound.lo <= 0:
        raise UnsupportedPolarizationNumericsError("frame normalization has no strictly positive norm")
    result = certified_vector_scale(vector,1./value,_point(1.)/bound)
    _admit_width(result.bounds,MAX_FRAME_WIDTH,"frame")
    return result


@dataclass(frozen=True,slots=True)
class TransverseFrame:
    """Owned certified real RH axes; unit khat never replaces geometric d."""

    e1: CertifiedVector3
    e2: CertifiedVector3
    khat: CertifiedVector3

    def __post_init__(self) -> None:
        axes = (self.e1,self.e2,self.khat)
        if not all(isinstance(x,CertifiedVector3) for x in axes):
            raise TypeError("transverse axes require CertifiedVector3")
        _admit_width(tuple(i for x in axes for i in x.bounds),MAX_FRAME_WIDTH,"transverse frame")
        residual = max(abs(certified_dot(a,b)[0]-(1. if i==j else 0.)) for i,a in enumerate(axes) for j,b in enumerate(axes))
        if residual > 128*EPS:
            raise UnsupportedPolarizationNumericsError("nominal transverse frame is not orthonormal within128epsilon")
        cross = _cross(self.e1,self.e2)
        if certified_dot(cross,self.khat)[0] <= 0:
            raise ValueError("transverse frame must be right handed")
        for i,a in enumerate(axes):
            for j,b in enumerate(axes):
                interval = certified_dot(a,b)[1]
                target = 1. if i==j else 0.
                if not interval.lo <= target <= interval.hi:
                    raise UnsupportedPolarizationNumericsError("transverse frame certificate does not enclose orthonormal target")

    def to_dict(self) -> dict[str,Any]:
        """Fresh axis lists for the closed state schema."""
        return {"e1":list(self.e1.nominal),"e2":list(self.e2.nominal),"khat":list(self.khat.nominal)}

    @property
    def intervals(self) -> tuple[CertifiedInterval,...]:
        """Nine e1/e2/khat component enclosures, dimensionless."""
        return self.e1.bounds+self.e2.bounds+self.khat.bounds


def source_frame() -> TransverseFrame:
    """Exact +X,+Y,+Z source convention, independent of every camera."""
    return TransverseFrame(certify_vector((1.,0.,0.)),certify_vector((0.,1.,0.)),certify_vector((0.,0.,1.)))


def polarization_diagnostics(C: tuple[float,...]) -> dict[str,Any]:
    """Raw/normalized algebra; state construction separately validates PSD.

    Exact-dark normalized diagnostics are null. Small raw roundoff is returned
    as recorded, including a permitted value slightly outside the unit sphere.
    """
    if not isinstance(C,(tuple,list)):
        raise TypeError("C diagnostics require four real components")
    if len(C)!=4:
        raise ValueError("C diagnostics require four real components")
    c0,c1,x,y = tuple(_real(value,"C diagnostic") for value in C)
    stokes = (c0+c1,c0-c1,2*x,-2*y)
    s0 = stokes[0]
    return {"stokes":list(stokes),"normalized_stokes":None if s0==0 else [1.,*(v/s0 for v in stokes[1:])],
            "degree_of_polarization":None if s0==0 else math.hypot(*stokes[1:])/s0,
            "eigenvalues":[.5*s0-math.hypot(.5*(c0-c1),x,y),.5*s0+math.hypot(.5*(c0-c1),x,y)]}


@dataclass(frozen=True,slots=True)
class RayPowerState:
    """Compact immutable absolute source-power C in an explicit ray frame.

    Public construction requires a genuinely PSD stored input. Propagated
    records use the congruence owner's structural PSD proof and raw nominal
    roundoff checks; no projection or trace repair is performed.
    """

    direction: CertifiedVector3
    medium_id: str
    refractive_index: float
    frame: TransverseFrame
    C: tuple[float,float,float,float]
    C_bounds: tuple[CertifiedInterval,...] | None = None
    power_bound: CertifiedInterval | None = None
    _congruence_proof: object | None = field(default=None,repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.direction,CertifiedVector3) or not isinstance(self.frame,TransverseFrame):
            raise TypeError("state requires certified direction and frame")
        if not isinstance(self.medium_id,str) or not self.medium_id:
            raise TypeError("medium_id must be a nonempty str")
        index = _real(self.refractive_index,"refractive_index")
        if not 1.<=index<=2.5:
            raise ValueError("refractive_index requires[1,2.5]")
        if not isinstance(self.C,(tuple,list)) or len(self.C)!=4:
            raise ValueError("C requires four real components")
        c = tuple(_real(x,"C") for x in self.C)
        object.__setattr__(self,"C",c)
        object.__setattr__(self,"refractive_index",index)
        power = c[0]+c[1]
        if power<0 or not math.isfinite(power):
            raise UnsupportedPolarizationNumericsError("negative or nonfinite source-relative power")
        eigen = polarization_diagnostics(c)["eigenvalues"][0]
        if eigen < -64*EPS*power:
            raise UnsupportedPolarizationNumericsError("materially non-PSD power coherency")
        if self._congruence_proof is not _CONGRUENCE_TOKEN:
            f = tuple(map(Fraction.from_float,c))
            if f[0]<0 or f[1]<0 or f[0]*f[1]-f[2]*f[2]-f[3]*f[3]<0:
                raise ValueError("stored input C must be positive semidefinite; no PSD repair")
        bounds = tuple(_point(x) for x in c) if self.C_bounds is None else tuple(self.C_bounds)
        if len(bounds)!=4 or not all(isinstance(x,CertifiedInterval) for x in bounds):
            raise TypeError("C_bounds require four CertifiedInterval values")
        if not all(i.lo<=x<=i.hi for x,i in zip(c,bounds)):
            raise ValueError("C nominal leaves its propagated enclosure")
        _admit_width(bounds,MAX_C_WIDTH,"carried C")
        pb = (bounds[0]+bounds[1]).include(power) if self.power_bound is None else self.power_bound
        if not isinstance(pb,CertifiedInterval):
            raise TypeError("power_bound requires CertifiedInterval")
        if not pb.lo<=power<=pb.hi:
            raise ValueError("power nominal leaves its propagated enclosure")
        _admit_width(self.direction.bounds,1e-8,"geometric direction")
        if abs(math.hypot(*self.direction.nominal)-1.)>128*EPS:
            raise UnsupportedPolarizationNumericsError("geometric nominal direction exceeds128epsilon; no normalization")
        unit = _unit(self.direction)
        if max(abs(x-y) for x,y in zip(unit.nominal,self.frame.khat.nominal))>128*EPS:
            raise ValueError("state transverse frame does not belong to its direction")
        object.__setattr__(self,"C_bounds",bounds)
        object.__setattr__(self,"power_bound",pb)

    @property
    def power_fraction(self) -> float:
        """The sole source-relative weight: trace(C), dimensionless."""
        return self.C[0]+self.C[1]

    def to_dict(self) -> dict[str,Any]:
        """Independent JSON-compatible compact state with complete enclosures."""
        return {"direction":list(self.direction.nominal),"medium_id":self.medium_id,"refractive_index":self.refractive_index,
                "frame":self.frame.to_dict(),"C":list(self.C),"power_fraction":self.power_fraction,
                "numerical_bounds":{"direction_intervals":[list(x.pair()) for x in self.direction.bounds],
                    "frame_intervals":[list(x.pair()) for x in self.frame.intervals],
                    "C_intervals":[list(x.pair()) for x in self.C_bounds],"power_interval":list(self.power_bound.pair())}}


def source_power_state(direction: CertifiedVector3, medium_id: str, refractive_index: float,
                       polarization: str) -> RayPowerState:
    """Exact unit-source presets, never a sampled field or hidden normalization."""
    if not isinstance(polarization,str):
        raise TypeError("polarization must be str")
    if polarization not in SOURCE_C:
        raise ValueError(f"polarization requires one of {tuple(SOURCE_C)!r}")
    if direction.nominal!=(0.,0.,1.):
        raise ValueError("source direction must be exactly[0,0,1]")
    return RayPowerState(direction,medium_id,refractive_index,source_frame(),SOURCE_C[polarization])


@dataclass(frozen=True,slots=True)
class ComplexBounds:
    """Rectangular outward enclosure of a complex dimensionless scalar."""

    real: CertifiedInterval
    imag: CertifiedInterval

    @staticmethod
    def point(value: complex) -> ComplexBounds:
        return ComplexBounds(_point(value.real),_point(value.imag))

    def __add__(self, other: ComplexBounds) -> ComplexBounds:
        return ComplexBounds(self.real+other.real,self.imag+other.imag)

    def __neg__(self) -> ComplexBounds:
        return ComplexBounds(-self.real,-self.imag)

    def __sub__(self, other: ComplexBounds) -> ComplexBounds:
        return self+-other

    def __mul__(self, other: ComplexBounds) -> ComplexBounds:
        return ComplexBounds(self.real*other.real-self.imag*other.imag,self.real*other.imag+self.imag*other.real)

    def conjugate(self) -> ComplexBounds:
        return ComplexBounds(self.real,-self.imag)

    def include(self, value: complex) -> ComplexBounds:
        return ComplexBounds(self.real.include(value.real),self.imag.include(value.imag))

    def pair(self) -> list[list[float]]:
        return [list(self.real.pair()),list(self.imag.pair())]


@dataclass(frozen=True,slots=True)
class FresnelCoefficients:
    """Signed electric coefficients, power operators and inherited certificates."""

    classification: str
    ci: float
    ct: complex
    ci_bound: CertifiedInterval
    ct_bound: ComplexBounds
    r_s: complex
    r_p: complex
    t_s: complex | None
    t_p: complex | None
    tau_s: complex | None
    tau_p: complex | None
    flux_factor: float | None
    bounds: tuple[ComplexBounds | None,...]
    tau_bounds: tuple[ComplexBounds | None,...]
    flux_bound: CertifiedInterval | None
    exact_reflection_zero: bool

    @property
    def channel_powers(self) -> tuple[float,float,float,float]:
        """Pure-channel R_s,R_p,T_s,T_p, never a mixed input reset."""
        return (checked_amplitude_power(self.r_s),checked_amplitude_power(self.r_p),
                0. if self.tau_s is None else checked_amplitude_power(self.tau_s),
                0. if self.tau_p is None else checked_amplitude_power(self.tau_p))


def fresnel_coefficients(direction: CertifiedVector3, incident_facing_covector: CertifiedVector3,
                         incident_index: float, transmission_index: float, *,
                         geometry: CertifiedDielectricDirections | None = None) -> FresnelCoefficients:
    """Stable signed Fresnel amplitudes and flux-normalized power operators.

    Exact-Fraction rationalized stored-input numerators retain weak Brewster
    amplitudes. Their outward intervals independently retain accumulated input
    geometry uncertainty. Only an owner-issued relation makes ci exactly1.
    """
    if not isinstance(direction,CertifiedVector3) or not isinstance(incident_facing_covector,CertifiedVector3):
        raise TypeError("coefficients require certified direction and incident-facing covector")
    if geometry is not None and not isinstance(geometry,CertifiedDielectricDirections):
        raise TypeError("geometry must be CertifiedDielectricDirections or None")
    ni,nt = _real(incident_index,"incident index"),_real(transmission_index,"transmission index")
    if not 1<=ni<=2.5 or not 1<=nt<=2.5:
        raise ValueError("indices require[1,2.5]")
    a = incident_facing_covector
    da,dai = certified_dot(direction,a)
    dn,dni = certified_norm(direction)
    an,ani = certified_norm(a)
    if dai.hi>=0 or dni.lo<=0 or ani.lo<=0:
        raise UnsupportedPolarizationNumericsError("incident-facing cosine lacks a strict positive domain")
    exact_normal = geometry is not None and geometry.normal_relation is not None
    if exact_normal and (not isinstance(geometry.normal_relation,CertifiedNormalIncidence)
                         or geometry.normal_relation.face_id is None
                         or geometry.normal_relation.incident_facing_covector is not a):
        raise ValueError("normal coefficient fallback requires an actual face/covector-bound owner proof")
    if geometry is not None and (geometry.incident_facing_covector is not a or geometry.incident_index!=ni or geometry.transmission_index!=nt
                                or exact_normal and geometry.normal_relation.direction is not direction):
        raise ValueError("coefficient geometry belongs to a different incident state")
    df,af = tuple(map(Fraction.from_float,direction.nominal)),tuple(map(Fraction.from_float,a.nominal))
    dot = sum((x*y for x,y in zip(df,af)),Fraction(0))
    u = dot*dot/(sum((x*x for x in df),Fraction(0))*sum((x*x for x in af),Fraction(0)))
    if exact_normal:
        ci,cii,u = 1.,_point(1.),Fraction(1)
    else:
        ci,cii = math.sqrt(float(u)),-dai/(dni*ani)
        cii = cii.include(ci)
    nf,tf = Fraction.from_float(ni),Fraction.from_float(nt)
    v = 1-(nf/tf)**2*(1-u)
    vi = _point(1.)-(_point(ni)/_point(nt)).square()*(_point(1.)-cii.square())
    if ni==nt:
        # Nongrazing equal-index identity eliminates cancellation symbolically.
        vi = cii.square()
    if vi.lo<=0<=vi.hi:
        raise NumericalAmbiguityError("Fresnel transmitted cosine enclosure includes critical zero")
    if ni==nt:
        z,one=ComplexBounds.point(0j),ComplexBounds.point(1+0j)
        return FresnelCoefficients("equal_index_identity",ci,complex(ci),cii,ComplexBounds(cii,_point(0.)),
            0j,0j,1+0j,1+0j,1+0j,1+0j,1.,(z,z,one,one),(one,one),_point(1.),True)
    if vi.hi<0:
        if v>=0:
            raise UnsupportedPolarizationNumericsError("nominal coefficient domain disagrees with certified TIR")
        gamma,gammai = math.sqrt(float(-v)),(-vi).sqrt()
        ct = complex(0.,gamma)
        rs=(ni*ci-nt*ct)/(ni*ci+nt*ct)
        rp=(nt*ci-ni*ct)/(nt*ci+ni*ct)
        def phase(x: CertifiedInterval,y: CertifiedInterval) -> ComplexBounds:
            denominator=x.square()+y.square()
            return ComplexBounds((x.square()-y.square())/denominator,-(_point(2.)*x*y)/denominator)
        rb=(phase(_point(ni)*cii,_point(nt)*gammai).include(rs),phase(_point(nt)*cii,_point(ni)*gammai).include(rp))
        result = FresnelCoefficients("total_internal_reflection",ci,ct,cii,ComplexBounds(_point(0.),gammai),
            rs,rp,None,None,None,None,None,(rb[0],rb[1],None,None),(None,None),None,False)
    else:
        if v<=0:
            raise UnsupportedPolarizationNumericsError("nominal coefficient domain disagrees with positive cosine")
        ct,cti=math.sqrt(float(v)),vi.sqrt()
        ds,dp=ni*ci+nt*ct,nt*ci+ni*ct
        dsi,dpi=_point(ni)*cii+_point(nt)*cti,_point(nt)*cii+_point(ni)*cti
        # Rationalization is essential: direct sqrt subtraction loses positive
        # stored-input rp values around 1e-17 (Rp around 1e-33).
        rs=complex(float(nf*nf-tf*tf)/(ds*ds))
        rp=complex(float(tf*tf*u-nf*nf*v)/(dp*dp))
        ts,tp=complex(2*ni*ci/ds),complex(2*ni*ci/dp)
        flux=nt*ct/(ni*ci)
        fluxi=_point(nt)*cti/(_point(ni)*cii)
        tau=2*math.sqrt(ni*nt*ci*ct)
        taui=_point(2.)*(_point(ni)*_point(nt)*cii*cti).sqrt()
        taus,taup=complex(tau/ds),complex(tau/dp)
        rsi=_fraction_bounds(nf*nf-tf*tf)/dsi.square()
        ui=cii.square()
        rpi=(_point(nt).square()*ui-_point(ni).square()*vi)/dpi.square()
        tsi=_point(2.)*_point(ni)*cii/dsi
        tpi=_point(2.)*_point(ni)*cii/dpi
        rb=tuple(ComplexBounds(i.include(n.real),_point(0.)) for i,n in zip((rsi,rpi,tsi,tpi),(rs,rp,ts,tp)))
        tb=tuple(ComplexBounds(i.include(n.real),_point(0.)) for i,n in zip((taui/dsi,taui/dpi),(taus,taup)))
        # Exact stored-index equality is the only whole-reflection zero in the
        # admitted arbitrary-coherency domain; no epsilon threshold is used.
        result=FresnelCoefficients("dielectric_split",ci,complex(ct),cii,ComplexBounds(cti,_point(0.)),
            rs,rp,ts,tp,taus,taup,flux,rb,tb,fluxi,False)
    all_parts=tuple(part for bound in (*result.bounds,*result.tau_bounds) if bound is not None for part in (bound.real,bound.imag))
    _admit_width(all_parts,MAX_COEFFICIENT_WIDTH,"Fresnel coefficient")
    if result.flux_bound is not None:
        _admit_width((result.flux_bound,),MAX_COEFFICIENT_WIDTH,"flux factor")
    return result


def _rotate_C(state: RayPowerState, s: CertifiedVector3, p: CertifiedVector3,
              exact_normal: bool) -> tuple[tuple[float,...],tuple[CertifiedInterval,...]]:
    if exact_normal:
        # s is the actual incoming e1 and p is its proved RH companion. Their
        # target basis change is exactly I, not a narrowing of stored axes.
        return state.C,state.C_bounds
    axes=(s,p);old=(state.frame.e1,state.frame.e2)
    m=tuple(tuple(certified_dot(a,b)[0] for b in old) for a in axes)
    mi=tuple(tuple(certified_dot(a,b)[1] for b in old) for a in axes)
    a,b=m[0];c,d=m[1];ai,bi=mi[0];ci,di=mi[1]
    u,v,x,y=state.C;ui,vi,xi,yi=state.C_bounds
    nominal=(math.fsum((a*a*u,b*b*v,2*a*b*x)),math.fsum((c*c*u,d*d*v,2*c*d*x)),
             math.fsum((a*c*u,b*d*v,(a*d+b*c)*x)),(a*d-b*c)*y)
    bounds=(ai.square()*ui+bi.square()*vi+_point(2.)*ai*bi*xi,
            ci.square()*ui+di.square()*vi+_point(2.)*ci*di*xi,
            ai*ci*ui+bi*di*vi+(ai*di+bi*ci)*xi,(ai*di-bi*ci)*yi)
    return nominal,tuple(i.include(x) for x,i in zip(nominal,bounds))


def _mapped_state(state: RayPowerState,direction: CertifiedVector3,medium: str,index: float,
                  frame: TransverseFrame,local: tuple[float,...],local_bounds: tuple[CertifiedInterval,...],
                  j: tuple[complex,complex],ji: tuple[ComplexBounds,ComplexBounds],tir: bool=False) -> RayPowerState:
    c0,c1,x,y=local
    if c0 < -64*EPS*state.power_fraction or c1 < -64*EPS*state.power_fraction:
        raise UnsupportedPolarizationNumericsError("basis congruence has materially negative channel power")
    # At TIR |(x-iy)/(x+iy)|²=1 is an analytic exact lossless identity.
    # It does not divide by any observed R+T or repair the complex amplitudes;
    # their raw signed phase and rectangular bounds still determine C01.
    powers=(1.,1.) if tir else (checked_amplitude_power(j[0]),checked_amplitude_power(j[1]))
    diagonals=[]
    for value,factor in zip((c0,c1),powers):
        diagonals.append(checked_positive_product(value,factor) if value>=0 else value*factor)
    factor=j[0]*j[1].conjugate()
    cross=factor*complex(x,y)
    nominal=(*diagonals,cross.real,cross.imag)
    power_intervals=(_point(1.),_point(1.)) if tir else tuple(z.real.square()+z.imag.square() for z in ji)
    factor_i=ji[0]*ji[1].conjugate()
    cross_i=factor_i*ComplexBounds(local_bounds[2],local_bounds[3])
    bounds=(power_intervals[0]*local_bounds[0],power_intervals[1]*local_bounds[1],cross_i.real,cross_i.imag)
    bounds=tuple(i.include(x) for x,i in zip(nominal,bounds))
    power=nominal[0]+nominal[1]
    if state.power_fraction>0 and power==0 and any(value>0 and factor>0 for value,factor in zip((c0,c1),powers)):
        raise UnsupportedPolarizationNumericsError("positive child power rounded to zero")
    return RayPowerState(direction,medium,index,frame,nominal,bounds,None,_CONGRUENCE_TOKEN)


@dataclass(frozen=True,slots=True)
class FresnelInteraction:
    """One pure interface operation; traversal alone assigns branch identities."""

    coefficients: FresnelCoefficients
    reflected: RayPowerState | None
    transmitted: RayPowerState | None
    incidence_basis: dict[str,Any] | None
    basis_bounds: tuple[CertifiedInterval,...] | None
    local_signed_residual: float
    local_residual_bound: CertifiedInterval


def apply_fresnel_interface(state: RayPowerState,geometry: CertifiedDielectricDirections) -> FresnelInteraction:
    """Apply actual medium-aware R/T, preserving within-ray coherency memory."""
    if not isinstance(state,RayPowerState) or not isinstance(geometry,CertifiedDielectricDirections):
        raise TypeError("interface requires RayPowerState and CertifiedDielectricDirections")
    if state.medium_id!=geometry.incident_medium_id or state.refractive_index!=geometry.incident_index:
        raise ValueError("incident power state disagrees with actual geometry medium")
    coefficients=fresnel_coefficients(state.direction,geometry.incident_facing_covector,
                                     geometry.incident_index,geometry.transmission_index,geometry=geometry)
    if coefficients.classification!=geometry.classification:
        raise UnsupportedPolarizationNumericsError("Fresnel and geometric criticality disagree")
    if geometry.classification=="equal_index_identity":
        child=RayPowerState(geometry.transmitted,geometry.transmission_medium_id,geometry.transmission_index,
                           state.frame,state.C,state.C_bounds,state.power_bound,_CONGRUENCE_TOKEN)
        return FresnelInteraction(coefficients,None,child,None,None,0.,_point(0.))
    exact_normal=geometry.normal_relation is not None
    s=state.frame.e1 if exact_normal else _unit(_cross(geometry.incident_facing_covector,state.frame.khat))
    p=state.frame.e2 if exact_normal else _cross(state.frame.khat,s)
    local,local_bounds=_rotate_C(state,s,p,exact_normal)
    reflected=transmitted=None
    if geometry.reflected is not None:
        kr=_unit(geometry.reflected)
        rframe=TransverseFrame(s,_cross(kr,s),kr)
        reflected=_mapped_state(state,geometry.reflected,state.medium_id,state.refractive_index,rframe,local,local_bounds,
            (coefficients.r_s,coefficients.r_p),(coefficients.bounds[0],coefficients.bounds[1]),
            geometry.classification=="total_internal_reflection")
    if geometry.transmitted is not None:
        kt=_unit(geometry.transmitted)
        tframe=TransverseFrame(s,_cross(kt,s),kt)
        transmitted=_mapped_state(state,geometry.transmitted,geometry.transmission_medium_id,geometry.transmission_index,tframe,
            local,local_bounds,(coefficients.tau_s,coefficients.tau_p),coefficients.tau_bounds)
    positive=tuple(x for x in (reflected,transmitted) if x is not None)
    residual=state.power_fraction-math.fsum(x.power_fraction for x in positive)
    residual_i=state.power_bound
    for child in positive:
        residual_i=residual_i-child.power_bound
    residual_i=residual_i.include(residual)
    if abs(residual)>64*EPS*state.power_fraction:
        raise UnsupportedPolarizationNumericsError("local power conservation exceeds64epsilon times incident trace")
    return FresnelInteraction(coefficients,reflected,transmitted,
        {"s":list(s.nominal),"p_i":list(p.nominal),"normal_policy":"exact_owner_relation" if exact_normal else "generic_certified"},
        s.bounds+p.bounds,residual,residual_i)
