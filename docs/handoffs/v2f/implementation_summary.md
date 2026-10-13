# V2f implementation summary

Recorded 2026-10-13 before executable implementation. Accepted baseline:
`1dde19c4c1d5419714523828c338bc0c948ea82c`. This records the approved exact
API/model/domain; acceptance and publication are separate measured gates.

## Public signatures, fields and scalar types

Import directly from `ohlab.optics.polarized_interference`. Its `__all__`
contains exactly the eight names below; old initializers/exports do not change.
All records are frozen and keyword-only. Result equality is identity (`eq=False`).

```python
PolarizerAction(*, axis_angle_rad: float)
RetarderAction(*, axis_angle_rad: float, retardance_rad: float)
PolarizationArm(*, distance_m: float,
                actions: tuple[PolarizerAction | RetarderAction, ...] = ())
PolarizedTwoArmSpec(*, arm_0: PolarizationArm, arm_1: PolarizationArm,
                   relative_phase_rad: float)
PolarizedTwoArmNorms(*,
    inputs: tuple[float, float], split: tuple[float, float],
    propagated: tuple[float, float], elements: tuple[float, float],
    combiner: tuple[float, float], outputs: tuple[float, float],
    arm_action_norms: tuple[tuple[float, ...], tuple[float, ...]] = ((), ()))
PolarizedTwoArmResult(*, spec: PolarizedTwoArmSpec,
    outputs: tuple[JonesField, JonesField], norms: PolarizedTwoArmNorms)
mix_balanced_jones(port_0: JonesField, port_1: JonesField, *,
    matrix: Literal["B", "B_dagger"]) -> tuple[JonesField, JonesField]
run_polarized_two_arm(incident: JonesField, *,
    spec: PolarizedTwoArmSpec) -> PolarizedTwoArmResult
```

New records and tuple containers require their exact concrete types; actions
are a tuple of zero to two PolarizerAction/RetarderAction records. Reconstruct
and revalidate owned records rather than trust tampered frozen instances.
No IDs, per-action z positions, dictionary schema, registry or serialization.
Public ComplexField/JonesField instances are supported, with canonical
`type(grid) is SamplingGrid`, exact ny/nx/dy/dx, shape and wavelength.

Distances, axis angles, retardance, extra phase and scalar norms accept Python
int/float and NumPy integer/floating numeric scalars, excluding Python/NumPy
bool, temporal scalars, arrays, strings and complex values. They convert once
to finite binary64; reject nonzero wider values that round to zero. Distances
and norms are nonnegative; angles/retardance/phase are signed, without wrapping
or snapping. Lengths are SI metres and angles radians. Wrong types raise
TypeError; invalid domains, nonfinite/unusable values and derived arithmetic
raise ValueError with useful context. Native finite complex128 field data are
required. Same-shape metadata mismatches, including one ULP, fail exactly.

## Fixed model and independent phase reference

Ordering is `(port0.x, port0.y, port1.x, port1.y)`; polarization is not a port.
Retain exp(-i*omega*t), fixed aligned (+x,+y) basis and identity transverse
correspondence, +y-down display. The ideal polarization-independent splitter
acts on port space as `B=[[1,i],[i,1]]/sqrt(2)` and recombination is B_dagger.
This is not a physical coating law or cube-rotation rule. No reflected-frame
flip, conjugation, quantum interpretation, longitudinal field or tilted plane.

Runner sequence: owned incident JonesField at port0 and exact zero at port1;
B; forward scalar ASM for arm0.x,arm0.y,arm1.x,arm1.y at the declared distances;
ordered terminal Jones actions on each arm; exp(+i*phi) on BOTH arm1 components;
B_dagger; both raw unanalysed output JonesFields immediately after recombination.
Each arm permits zero to two uniform actions at its terminal plane, with no
propagation between them or inferred material thickness. Actions call public
V2c polarizer/retarder functions and preserve their complete complex phase:
selected-axis phase zero, perpendicular +retardance. Never apply an additional
exp(-i*delta/2), phase fit/reset, normalized representative or make a component real.

The common initial and terminal grids/bases are stipulated, not inferred from
metadata. Unequal unfolded path lengths still meet at the declared common
reference plane. Propagation is a NEW bounded Jones-envelope composition:
aligned parallel planes, homogeneous polarization-independent medium, fixed
grid/pitch/wavelength and no crop/resampling. Its physical interpretation is
low-angle/paraxial; public scalar ASM retains its full inherited kernel, with
explicit pad_factor=1 and nonnegative distance, including zero-distance calls.
Carrier is already in ASM. No second FFT/kz engine or new vector propagator.
Forward evanescent arithmetic remains supported where numerically usable,
without normalization, but sampled norm is not calibrated vector EM energy.

For independent unscaled reference arm fields A=J0 P(L0)E and V=J1 P(L1)E:

```text
F0=(A+exp(i*phi)V)/2; F1=i*(exp(i*phi)V-A)/2.
G0=J0 P(L0); G1=exp(i*phi)J1 P(L1).
B4_dagger diag(G0,G1) B4 =
  [[G0+G1,i*(G0-G1)],[i*(G1-G0),G0+G1]]/2.
```

Actual post-split checkpoints already include 1/sqrt(2); they are NOT A/V.
For C=dx*dy*sum(conj(Ax)*Vx+conj(Ay)*Vy),
N(F0/1)=[N(A)+N(V) +/- 2 Re(exp(i*phi)C)]/4. In the matched no-loss unit-state
case gamma=conj(j0).T@j1 gives eta0/1=[1 +/- Re(exp(i*phi)gamma)]/2. The argument
of gamma matters. A hand anchor j0=(1,i)/sqrt2,j1=(1,1)/sqrt2 gives gamma=(1-i)/2
and eta=(3/4,1/4) at phi=pi/2. These are independent references, not production
substitutes or normalization instructions.

## Complete-pipeline domain and exceptions

Use existing public scalar mix/phase, ASM and Jones actions, with no private
helper imports. Local cheap validation guards may check scalar arithmetic
bounds but must not compute a kz/frequency mesh or propagation kernel.
The runner alone caps each dimension at128 before avoidable copies or FFTs.
The mixer has no runner resource cap. This cap does not certify sampling.

Before optical work validate ALL static records/parameters, incident metadata
and storage, combined Jones norm and both scalar component norms, canonical
geometry and usable area/extents/reciprocals/frequency/wavenumber/distance-phase
bounds for both arms. Before either polarization is mixed, validate both
complete Jones inputs, exact cross-port compatibility, all FOUR scalar norms
and combined totals. Before common phase validate both arm1 scalar components.
Known unsupported y input must fail before any x mixing/phase operation.

Every scalar mixing/phase boundary inherits its input AND output domain:
nonzero whole components need usable finite positive scalar norms, with the
existing abs(data)**2, float64 sum, then *dx*dy reduction. Exact-zero components
are legal. Jones validation instead uses combined x/y norm and can retain a
tiny component beside a usable one. Preserve that broader semantics BETWEEN
pure Jones actions; a later scalar boundary may reject the result.

Static validity cannot guarantee all derived states remain usable: splitting
or cancellation can make an unusable component, and a valid Jones action can
create one. Catch derived TypeError/ValueError/FloatingPointError/OverflowError
at the operation boundary with stage and arm/component where available,
preserve the original cause and raise the appropriate contextual type (derived
numeric errors are ValueError). Return no partial result. Never erase, zero,
clip, rescale, normalize or silently retry an unsupported component.

Local np.errstate restores the exact caller mapping on success/failure.
Overflow/invalid/divide errors fail; bounded product/squared-tail and inherited
forward-decay underflow may occur. A represented nonzero whole scalar component
with zero norm at a scalar boundary, or combined Jones field with zero norm,
fails. Exact dark fields remain valid after full validation. A field that
underflows through the inherited forward propagator to represented all-zero
data is distinct from manually deleting an unsupported component.

## Norm checkpoints and histories

All Jones measurements use public JonesField.sampled_norm, evaluated literally
`sum(abs(Ux)**2+abs(Uy)**2,dtype=float64)*dx*dy` left-to-right, in
amplitude-unit^2*m^2, not watts. No abs(Ux+Uy)**2, scalar .power substitution or
bit-equality claim against independently reduced scalar norms.

| Field | Physical measurement boundary |
|---|---|
| inputs |incident Jones port0 and exact-zero port1|
| split |immediately after B, ordered arm0/arm1|
| propagated |after both component ASM calls per arm, before Jones actions|
| elements |after all ordered terminal actions per arm|
| combiner |after common arm1 phase, immediately before B_dagger|
| outputs |both raw Jones ports immediately after B_dagger|

`arm_action_norms[j]` is the ordered tuple of AFTER-action norms, length0..2.
Its first before-value is propagated[j]; later before-values are the previous
history entry. The last equals elements[j] under the identical measurement;
empty history requires elements[j]==propagated[j]. combiner[0]==elements[0]
because arm0 is untouched. Result construction checks history lengths against
the spec. At most16 scalar measurements are stored; no full intermediates.
Require nonnegative finite pairs/histories, usable totals and derived ratios.

Properties: inputs_total, split_total, propagated_total, elements_total,
combiner_total, outputs_total; split_delta, propagation_delta, elements_delta,
phase_delta, recombination_delta,total_delta (signed after-minus-before);
propagation_deltas,element_deltas,phase_deltas (ordered per-arm pairs);
arm_action_deltas (nested before/after differences); output_fractions and
total_output_ratio. Retain signed roundoff, no adjustment to force conservation.
History/budget reconciliation uses explicit floating tolerances; subtraction
telescoping is not a separate bit-exact arithmetic claim.

Fractions divide raw output norms by original incident norm (inputs_total).
Zero denominator gives (None,None)/None; positive-input dark output gives0.
Ratio division follows strict V2c bounded policy: raise on overflow/invalid,
NumPy-reported inexact subnormal underflow or positive ratios rounded to0.
No epsilon, clamp or surviving-power normalization. The result requires zero
second input and exact same-reduction agreement of output fields and records.
Scalar histories cannot authenticate discarded intermediates supplied by a caller.

## Ownership, downstream analyzers and evidence limits

Use public constructors for input snapshots and four independently owned
read-only complex128 output component arrays, with no input/output/output
storage sharing, even identities/darkness/same-object port inputs. Public ASM
returns its input at zero distance, so final ownership cannot rely on its
freshness. Derived intensities remain fresh writable float64. Existing reversible
ndarray write-flag semantics remain; this is not hardened storage.

Analyze copies/outputs through existing public apply_linear_polarizer outside
the runner. Preserve raw fields/norms; separately report post-analyzer norms,
signed removed norm, original-incident fractions and explicitly labelled
downstream-input ratios. Public transmission_ratio is appropriate for actual
compatible field pairs, with None at zero denominator and no causality badge.

Measured unchanged finite-fixture bounds: matrix rtol0/atol2e-15; ordinary complex
rtol2e-14/atol2e-14*Ain; intensity rtol2e-13/atol2e-13*Ain^2; norm
rtol2e-13/atol2e-13*Nin; fraction rtol=atol2e-13; complete independent direct
sums rtol1e-11/atol1e-11*Ain; selected near-dark fraction rtol2e-13/atol1e-40
and corresponding norm atol1e-40*Nin. Ain is maximum incident component
amplitude over applicable inputs; Nin is their independently reduced combined
Jones input norm. Report maximum complex absolute error/Ain, norm absolute
error/Nin, fraction absolute error and focused reference-relative error.

Measured against shipped functions; see the evidence handoff. Actual-binary64 phase Decimal80 references
justify selected positive ~2.5e-19 fractions; do not extend that relative claim
to each tiny quadrature (planning observed a ~2.5e-19 quadrature round to0).
Retain all17 phases k*pi/8,k0..16, computing0 and2*pi separately. Do not fit phases,
normalize references, duplicate endpoints or claim exact continuous visibility.

No frontend, HTTP route, document mode, persistence, M5 change, material model,
reflection geometry or deployment. V2g requires separate future approval and must
explicitly plan its new-mode document compatibility; V2e remains closed to its
existing three modes. Teaching and learning records remain separate.

## Acceptance status

The opening contract was completed before executable source. Precommit acceptance
passed: baseline 2700 passed/1 skipped, restored final 2942 passed/1 skipped,
242 focused new cases, independent complex/direct-sum/weak references, all 20
classified controls with exact restoration, both demos and three visually
inspected byte-identically regenerated figures. Exact outputs and finite-fixture
measurements are in tests_and_evidence.md. Commit/postcommit/publication are
separate subsequent gates recorded in fresh ignored evidence and the completion
report; this tracked document predicts no publication result or qualified replay.
