# W4 mathematics and numerical contract

Normative conventions are `docs/math_conventions.md`§3.25. The immutable W4
planning CONTRACT/NUMERICAL_POLICY and the implementation's pre-integration
CONTRACT_COMPLETION record retain their original identities. This handoff
describes the new W4 model; it does not revise W2/W3 or historical measurements.

## Frames, coherency and units

SI/right-handed world coordinates, +Y up, active column-vector body transform
`B=Rz Ry Rx` (intrinsic X thenY thenZ), harmonic convention exp(-i omega t).
Display scale is not a numerical coordinate change. The actual stored affine
body and finite halfspaces/covectors govern intersections; mesh triangles and
camera axes do not. Geometric directions are inherited verbatim, never replaced
by normalized copies. Separately certified unit khat is for polarization only.

The fixed source propagates+Z with e1=+X,e2=+Y. Source C is unpolarized
(.5,.5,0,0), linear_e1=(1,0,0,0), linear_e2=(0,1,0,0) or
linear_45=(.5,.5,.5,0). The four entries mean C00,C11,ReC01,ImC01; lower C10 is
the conjugate of C01. C has dimensionless **source-relative optical power**
units and trace(C)=power_fraction. That checked duplicate is not a weight
multiplied into C. All states/results own their immutable frame/matrix data.

Raw Stokes=(S0,S1,S2,S3)=(trC,C00-C11,2ReC01,-2ImC01). At positive S0,
normalized Stokes=(1,S1/S0,S2/S0,S3/S0) and DoP=hypot(S1,S2,S3)/S0. At exact
zero all normalized components and DoP are null. Raw nominal roundoff is
retained under explicit physical-state/error allowances. There is no arbitrary
symmetrization, eigenvalue projection, DoP clamp or observed-trace rescaling.

## Interface map

Incident-facing covector a points into the incident medium. For actual d,
ci=-(d·a)/sqrt((d·d)(a·a)). At certified generic incidence
s=normalize(a×k_i), p_i=k_i×s and p_o=k_o×s. Each(s,p,k) frame is right handed.
M rotates the incident stored e1/e2 components to the local s/p basis.
At exact normal incidence the owner must prove the relation from actual
scene/ray/face/stored affine witnesses; then s=incoming e1 is a legitimate
gauge and reflected p reverses. A nominally zero cross product or angle label
is not a proof. Camera movement never selects the basis.

For reliable subcritical transmission between real ni,nt:

```text
r_s = (ni ci - nt ct)/(ni ci + nt ct)
r_p = (nt ci - ni ct)/(nt ci + ni ct)
t_s = 2 ni ci/(ni ci + nt ct)
t_p = 2 ni ci/(nt ci + ni ct)
g   = nt ct/(ni ci)
J_R = diag(r_s,r_p)
J_T = sqrt(g) diag(t_s,t_p)
C_child = J M C_incident M^T J^dagger
```

The n*cos factor converts electric-field coefficients to normal power flux
through the same interface patch. R_s/R_p=|r_s/r_p|² and T_s/T_p=g|t_s/t_p|².
Local actual-state fractions are trace(C_R/T)/trace(C_incident); cumulative
child power is already trace(C_child). Signs and complex coefficients are
distinct from squared fractions. No radiance eta² factor or normalization by
the observed output sum is applied. Conservation is independently checked.

Stored-input Brewster-neighborhood reflection uses the rationalized exact
Fraction numerator before bounded denominator conversion. The seven original
binary64 direction vectors remain unchanged: no angle snapping or small-value
zeroing. Equal stored indices have a certified exact identity crossing:
unchanged d/frame/C and inherited enclosures, new medium ID, R=0/T=1. The exact
zero reflected leg has no traversed branch, rather than a low-power cutoff.

At TIR, ct=+i gamma in this harmonic convention. Only a reflected propagating
child exists; it retains incident medium and relative complex s/p phase.
Transmitted t_s/t_p/g and angle are null; T_s/T_p=0. The auxiliary complex ct
enclosure remains available for the reflection calculation. The exact unit
modulus identity justifies TIR channel power1; the complex reflection phase is
not discarded or inferred from a normalized observed sum. Phase-sensitive
polarized algebraic references are separate from realizable finite routes.

## Geometry, uncertainty and representability

Finite geometry uses the W3-owned public certified seam: actual face handles,
nearest-hit/medium decisions, both R/T directions, inherited enclosures and
per-leg strict departure-side proof. Reflected side is positive and transmitted
side negative relative to the incident-facing covector. Only the immediately
preceding certified root is suppressed. No origin nudge, face inflation,
automatic receiver aiming or enclosure reset is allowed.

Nominal input/output norm bounds remain32eps/128eps; point width<=1e-8m and
direction width<=1e-8. New frame/coefficient/C component widths<=1e-8 are
admission ceilings, not accuracy guarantees. Generic nearly normal, critical,
grazing, edge or tied-hit configurations can remain unsupported. Every admitted
reference component must lie inside its reported enclosure, including accumulated
frame/coefficient/C uncertainty through successive interfaces. A small nominal
residual is not an uncertainty certificate.

Positive diagonal/power products use exact stored-binary64 rational comparison:
q=Fraction(a)Fraction(b)>0 requires stored y>0 and
|Fraction(y)-q|<=64eps*q. Exact subnormal copies can pass; inaccurate subnormal
products and positive-to-zero underflow fail. Coefficient-square underflow is
also checked. Cross terms retain outward arithmetic bounds scaled to positive
local trace, without unit-power absolute floors. Unusable arithmetic rejects
the whole trace as unsupported numerics; it is not a loss/absorption entry.

The original planning failures near normal/critical incidence, the rectangular
algebraic C/frame chain and W3 operation14 stress remain historical evidence.
Eight ancestry interactions is a resource cap, not a promise that every
eight-interaction geometry passes numerical admission.

## Traversal and terminal conservation

FIFO R-before-T creation counts root, split parents and one-child continuations.
All positive children are reserved atomically; exact-zero/nonpropagating legs
have explicit dispositions. No magnitude pruning. Receiver/stop hits consume
surface-interaction/event budget and win at the permitted last hit. Reaching a
cap leaves all current/queued positive states unresolved in their actual medium.

The ledger contains terminal leaves only:

```text
signed_residual = 1 - fsum(detected, stopped, escaped, unresolved)
```

Split parents do not contribute again. A beam stop accounts stopped power;
there is no absorption within the dielectric. Any positive unresolved leaf
means incomplete traversal. Numerical ambiguity is an error, not truncation.
Receiver totals sum scalar branch powers incoherently. Matrices in different
frames are not summed into a receiver polarization, and Jones amplitudes from
different paths are never added.

For a symmetric lossless normal slab with complete infinite collection,
first straight transmission=T² and analytic incoherent transmitted sum=
T²/(1-R²). The latter is an independent analytic comparison, never inserted
into the finite graph to fill unresolved power. At ni=1,nt=1.5 the first
interface R=.04,T=.96 and first straight leaf=.9216. The finite capped normal
fixture remains incomplete with unresolved3.932160000000004e-9; its measured
ledger is in the evidence handoff.

Convexity constrains actual supported graphs: an outward departure enters a
supporting face's exterior halfspace and cannot return along the same straight
ray; receivers/stops terminate. There is at most one continuing internal path,
so ancestry8 allows at most17 created branches,9 leaves,15 events and15 segments
(30 combined). Frozen31/32/64 guards remain; synthetic maxima are not claimed
as realizable physical one-body trajectories.

## Independent metrics

Predeclared interface atol2e-14/rtol2e-12; local conservation abs5e-14;
accumulated ordinary C/power atol2e-13/rtol2e-12; position atol5e-12m/rtol2e-12;
direction/angle atol2e-12/rtol2e-12. Seven original weak amplitude/C/power
checks use rtol2e-11/atol0 with positivity, not a unit-sized absolute tolerance.
Independent Decimal90 references use their own formulas and no production
scientific helpers. Gauge checks compare world coherency/invariant observables,
not just basis-dependent matrix coordinates. Detecting faults and unsupported
cases are preserved separately from passing runs; see [evidence](tests_and_evidence.md).

## Dated evidence closeout

Closeout2026-10-29 preserves these numerical contracts, conventions and tolerances
unchanged. Final Python03 passes4616 cases with the one original Windows skip;
recorded Chrome.47 acceptance and19 independent original-response comparisons
are qualified in [tests and evidence](tests_and_evidence.md). The externally
updated installed Chrome.48 has NOT_RUN acceptance; that identity drift is not
a revised scientific result. The normal finite ledger remains incomplete, not
replaced by its infinite-series comparison. User visual approval is still pending.
