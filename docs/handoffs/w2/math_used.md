# W2 mathematics and conservative numerical contract

W2 is the separate `w2_ideal_geometric_routing_v1` model documented in
[math_conventions.md §3.23](../../math_conventions.md). It routes one ideal
geometric ray through finite planes. This handoff describes the implemented
core and its current independent checks, not final browser acceptance or
publication. Full gate state belongs in
[tests_and_evidence.md](tests_and_evidence.md).

## Physical scope and conventions

Physical positions are SI metres in right-handed XYZ with +Y up. A nominal
unit direction points **toward** its next hit:

```text
p(t) = o + t d, t > 0
R = Rz(z) Ry(y) Rx(x), active column vectors, X first
u = R (1,0,0), v = R (0,1,0), n = R (0,0,1)
```

Stored angles are radians in [-stored_pi,+stored_pi]. UI degree conversion
is separate. The scene uses uniform render scale10; this never changes the
numerical coordinates or W1's historical display mapping.

For stored plane center c, normal n and projection basis u/v:

```text
t = ((c-o) dot n) / (d dot n)
q = p(t)-c
local U = q dot u, local V = q dot v
disk: U²+V² <= radius²
rectangle: |U| <= width/2, |V| <= height/2
```

The plane/projection-defined finite face uses the returned binary64 frame.
Its small admitted nonorthogonality is included in the error/culling policy;
it is not silently repaired. Plane quotient plus finite-domain testing is
the relevant reference structure in [PBRT's disk discussion](https://pbr-book.org/4ed/Shapes/Disks).
W2 does not adopt its annuli, partial disks, sampling, UV parametrization,
nominal hit snapping or renderer-dependent transformation rules.

Specular reflection reverses the component along a unit normal and leaves
the tangential component unchanged:

```text
d_R = d - 2 (d dot n) n
```

[PBRT's reflection convention](https://pbr-book.org/4ed/Reflection_Models/Specular_Reflection_and_Transmission)
uses `wo` directed away from the surface. Substituting `wo=-d` gives W2's
propagation-direction formula. Both optical sides act identically; changing
normal sign leaves this formula invariant. No Fresnel coefficients, Snell
refraction, coating law or coherent reflection phase is imported.

An ideal splitter makes deterministic T and R children with weights w/2;
T continues straight. A mirror keeps weight w. A receiver records its actual
local UV/weight and terminates; a stop absorbs only an actual finite hit.
The weights are neither complex amplitudes nor calibrated power/irradiance.

## Pose enclosure, including trigonometry

Nominal matrices retain ordinary binary64 sine/cosine and matrix values.
Those returned frames are authoritative stored data. A separate certificate
also encloses the mathematical rotation at each **exact stored binary64
angle**; this is different from an exact decimal degree value a user may
have intended before UI conversion.

The certificate uses the sine/cosine series listed in
[NIST DLMF §4.19](https://dlmf.nist.gov/4.19):

```text
sin x = sum(k=0..31) (-1)^k x^(2k+1)/(2k+1)! + remainder
cos x = sum(k=0..31) (-1)^k x^(2k)/(2k)! + remainder
```

At |x|<=stored_pi, the omitted terms decrease in magnitude and alternate.
The remainder magnitude is at most the first omitted term. The actual
polynomial and bound use exact rational arithmetic, not a rounded Taylor
sum. `Fraction.from_float` preserves the binary64 argument exactly, as
described by [Python3.11's Fraction documentation](https://docs.python.org/3.11/library/fractions.html).
Exact rational comparisons establish the direction of conversion back to
binary64 interval endpoints. Outward matrix multiplication composes RzRyRx;
the enclosure is hulled with the actual nominal matrix.

Thus no one-ULP assumption about libm sine/cosine supplies the proof. If
nominal-frame discrepancy exceeds64epsilon, pose admission fails. The
independent real-angle tests instead use a direct100-term Decimal160
factorial/power series and an expanded closed-form rotation matrix.

## Conditional enclosure arithmetic

The supported runtime assumes finite binary64 round-to-nearest arithmetic,
gradual underflow, no FTZ/fastmath, correctly directed nextafter and correctly
rounded square root. No global floating-point settings are changed. Each
interval add/subtract/multiply/divide and square-root endpoint is rounded
outward. Division requires a denominator interval excluding zero.

Squares and sums of squares have mathematical nonnegative constraints.
Intersecting their enclosures with [0,+infinity) removes only impossible
negative endpoints introduced by outward arithmetic at zero. It never
clamps a physical position, aperture, weight, source or nominal readout.

Composition of these operations establishes an enclosure under the stated
arithmetic assumptions. Finite measured examples independently check the
implementation; small observed error alone is not the enclosure proof.
The general importance of rounding bounds and the danger of a fixed ray
epsilon are explained in [PBRT's rounding-error chapter](https://pbr-book.org/4ed/Shapes/Managing_Rounding_Error).
W2 uses its own bounded finite-plane policy, not that renderer's origin
offset strategy or code.

### Finite culling before infinite-plane predicates

Let F have rows u,v,n. Interval Gram bounds give an upper bound g on the
maximum row sum of `F F^T-I`. Gershgorin then implies
`sigma_min(F)^2 >= 1-g`. A local finite face with circumradius r therefore
fits inside the conservative world bound `r/sqrt(1-g)`. This changes a
culling/admission bound only; the optical aperture retains its exact input
size and finite-domain rule.

Interval closest-line or finite-leg distances discard a surface only when
its entire bounded footprint is unreachable. An uncertain cull cannot discard
it. This precedes unresolved plane-denominator or near-launch predicates:
in preset B the source lies on M2's infinite plane extension but remains
0.2m from its finite aperture during that leg. That extension is no event.

### Intersection, order and departure

Origin and direction intervals are retained from the source through all
interactions. Plane arithmetic encloses t and p, then exact plane constraints
refine the point enclosure in the largest-normal component. This intersects
two valid enclosures; it does not snap the nominal hit onto an aperture.
Local projection intervals certify inside/outside. Exact or adjacent-float
boundary overlaps remain `numerical_ambiguity`.

Nearest-hit intervals must be strictly separated. A relevant unresolved
candidate can block a hit only if it could be at least as early. A certified
farther ambiguous face cannot veto a closer valid hit. Possible-travel lower
bounds are themselves outward-rounded. No array-order physical tiebreak is
allowed, even when IDs order the error text deterministically.

After a mirror, interval propagation uses `(I-2 n n^T)d`, algebraically the
same reflection. This Householder form avoids false repeated dependency
tripling in an expanded interval `d-2 dot(d,n)n`. Nominal output still uses
the stated propagation formula. No direction enclosure is reset to its
estimate and no direction is normalized. Only the immediately previous
zero-thickness plane is excluded during the new straight leg; a noncoplanar
straight line cannot meet that same plane twice. Later visits remain valid.

### Trace sphere and geometric distance

The domain is a radius1m sphere centered on the submitted source, not a
curved optical surface. Complete finite apertures must be outward-certified
strictly inside it. Source coordinates have absolute component limit10m;
disk radius and rectangle full sizes are limited to [1e-6,.25]m.

For q=o-source, `a=d dot d`, `b=q dot d`, `c=q dot q-1`, the positive exit
parameter uses a cancellation-resistant root:

```text
t_exit = -c/(b+sqrt(b²-a c))       for b >= 0
t_exit = (-b+sqrt(b²-a c))/a     otherwise
```

Interval coefficients include the actual origin/direction uncertainty.
Because nominal unit vectors may retain roundoff, t is not treated as exact
Euclidean length. Each segment uses `hypot(end-start)`; norm and accumulated
distance enclosures propagate to the next stage. Hit/domain/distance ordering
must be certified. Overlap at the10m cap, including nominal equality, fails
rather than selecting an attractive endpoint. Escaped endpoints are actual
domain bounds and are never attached to convenient decorative receivers.

## Caps, leaf accounting and tolerances

The root counts among63 ever-created branches; mirrors create no child.
T/R pairs are atomic. Limits are32 inherited interactions per path and256
combined segment/hit records (128hits/256segments). A real hit costs2 records,
an escape/distance endpoint1, and terminals at known points cost none.
Record-cap failure globally truncates current/queued work at known states.
Receiver/stop at the32nd hit act before continuation truncation; a splitter
can create children inheriting32 which immediately truncate at that hit.
The detailed precedence is in [implementation_summary.md](implementation_summary.md).

Only terminal leaves enter the ledger:

```text
signed residual = 1 - fsum(detected + absorbed + escaped + truncated leaves)
```

Split parents are not counted again. Deterministic halving preserves binary
dyadic weights; there is no stochastic selection, pruning, coherent merge
or surviving-weight normalization. Truncation is incomplete, not absorption.

| Policy | Declared tolerance |
|---|---:|
| Input nominal unit residual | 32epsilon |
| Frame orthogonality | 64epsilon |
| Reflected nominal unit residual | 128epsilon |
| Signed weight residual | atol64epsilon, rtol0 |
| Conditioned independent positions/lengths | rtol2e-13, atol2e-13 × max(1m, coordinate norms, cumulative length) |
| Independent direction / angle | atol2e-13 / 2e-13rad |

Here epsilon=2^-52. Comparison tolerances are not substitutes for runtime
intervals. Unsupported arithmetic or material ambiguity returns failure,
without a partial successful trace. No all-grazing accuracy is promised.

## Current independent evidence and its limits

Core evidence lives under
`runs/w2_geometric_routing_implementation_01/core/`:

- `development_core_final_03`: **78 passed in2.12s**, zero skips, with exact
  stdout/stderr/argv and five source hashes.
- `validator_result_03`:14 direct cases and16 deliberate source-copy faults
  detected by substantive assertions; production source hash unchanged and
  restored assertions pass. Import/setup errors are not numerical proof.
- `adapter_pipeline_record256_01`: genuine256-record trace through adapter
  and strict encoder/decoder, exactly one public trace, full reply180815B,
  53branches,128segments+128hits, truncatedweight1, residual0. This is direct
  pipeline evidence, not an ASGI/browser run.

Full32-stage axis and oblique3D chains, including source
(9.5,-9.3,9.1)m, are compared against independent Decimal160 recurrences.
References call no production intersection/reflection helper. Stored frames
are reference inputs for one target; independently constructed ideal real
rotations at stored angles form the other. Every origin/direction, plane
parameter/point, local coordinate, reflected direction, segment norm and
cumulative enclosure contains its reference.

For the recorded oblique case, stored-frame max nominal point/direction
errors are5.551115123125783e-17m /5.551115123125783e-16. Ideal-angle errors
are1.1934897514720433e-15m /1.1546319456101628e-14. The conservative propagated
point bound is about2.68e-9m, not the smaller observed residual. This example
does not establish a uniform all-scene accuracy theorem.

The failed development invocation `development_core_final_01` remains
**73passed/1failed**: outward zero sums produced a negative subnormal norm
bound and a premature generic sqrt ambiguity. The implementation uses the
exact nonnegative norm constraint now; the original assertion was retained.
Earlier planning failure/correction and its source-copy timing disclosure
remain in `runs/w2_geometric_routing_plan_01/probes/probe_report.md`; those
planning measurements are not current production evidence. All historical
W1.1 publication/recovery qualifications remain unchanged.
