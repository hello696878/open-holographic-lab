# V2b mathematics used

The normative source is unchanged
[math_conventions.md §3.18](../../math_conventions.md#318-v2a-coherent-two-path-interference),
with its existing grid/ASM conventions in §§3.4 and 3.9. V2b adds a web
adapter, transport and display for those public APIs. It adds no propagation,
mixing, norm, reflection or phase law. The equations below explain the reused
model and independent checks; the web implementation does not calculate
optical outputs from them.

## Source and fixed topology

Supported incident fields are the existing uniform and Gaussian sources.
The adapter constructs a public `SequentialExperiment` with an empty
component train and observation at z=0, then calls public `sample_source`
once. It does not run a dummy propagation train or copy source formulas.
The field uses the existing canonical centered grid, native complex128
data and SI wavelength/pitches. A single simulation calls public
`run_two_arm` once; a complete sweep calls it 17 times on the same sampled
incident field with each actual requested phase.

The unchanged V2a model is classical, scalar and monochromatic with
time dependence `exp(-i*omega*t)`. Its ordered logical topology is

```text
(incident U, zero) -> B -> forward arm 0 / forward arm 1
-> extra exp(i*phi) on arm 1 -> B_dagger -> (output 0, output 1)

B        = [[1, +i], [+i, 1]] / sqrt(2)
B_dagger = [[1, -i], [-i, 1]] / sqrt(2).
```

`B_dagger` is the declared inverse mixer at the reference plane. These
logical coefficients do not assert a physical cube orientation, coating or
mirror-reflection law. Each arm has its own forward local z and the same
transverse-frame mapping. Both output screens represent fields immediately
after the recombiner. Cosmetic lane lengths and separated meshes add no
propagation, flip or conjugation.

For `A=P(L0)U` and `V=P(L1)U`, the normative output relation is

```text
U0 = (A + exp(i*phi)*V)/2
U1 = i*(exp(i*phi)*V - A)/2.
```

Each `P` is the existing public Angular Spectrum propagation with
`pad_factor=1`, including a call at zero distance. Its `exp(i*kz*L)` already
contains the carrier and principal-root forward evanescent decay. Extra
phase is a separate uniform arm-1 phase in signed radians; no second carrier
or mirror-displacement formula is introduced.

For equal arms, `W=P(L)U`,

```text
U0 = exp(i*phi/2)*cos(phi/2)*W
U1 = -exp(i*phi/2)*sin(phi/2)*W.
```

Thus zero extra phase gives bright port 0 and dark port 1; pi reverses the
brightness distribution. Uniform phase on equal spatial modes changes
brightness, not spatial stripes. A common incident phase rotates both
complex outputs without changing intensity. Unequal propagation lengths
retain their carrier phase and can change the distribution at phi=0.

## Returned norms and denominators

The unchanged sampled norm is
`N(U)=sum(abs(U)**2,dtype=float64)*dx*dy`, evaluated in that order, in
amplitude-unit² m². It is not watts. V2b copies the ten returned scalar
norms and reads the public derived properties instead of integrating
transported intensity images.

| Ordered pair | Numerical reference plane |
|---|---|
| `inputs` | incident port 0 and exact-zero input port 1 |
| `split` | immediately after B |
| `propagated` | after the two forward propagations, before extra phase |
| `combiner` | after extra arm-1 phase, immediately before B_dagger |
| `outputs` | immediately after B_dagger |

Each `*_total` is the sum of its pair. Signed diagnostics are
`split_total-inputs_total`, `propagated_total-split_total`,
`combiner_total-propagated_total`, `outputs_total-combiner_total`, and
`outputs_total-inputs_total`. Tiny signed floating-point differences remain
signed; the UI does not label them calibrated absorption or percent accuracy.

Port fractions are `outputs[j]/inputs_total`, and total ratio is
`outputs_total/inputs_total`. At exactly zero total input these are
`(None,None)` and `None`, transported as JSON null and displayed explicitly
as undefined. Surviving output is never the denominator.

For equal arms and positive input, let `tau=N(W)/N(U)`. Then

```text
eta0 = tau*cos(phi/2)**2
eta1 = tau*sin(phi/2)**2.
```

Bare cos²/sin² requires tau=1. Existing forward evanescent decay can give
tau<1, so forcing eta0+eta1 to one would conceal real sampled-model loss.
Unitary mixing alone preserves the combined sampled norm; it does not
promise lossless whole-path propagation or calibrated electromagnetic
energy transport for evanescent components.

## Binary64 phases, sweep and display

Distances are finite nonnegative metres and extra phase is finite signed
radians. UI convenience units convert to the authoritative SI values;
degrees are an explanatory label only. Browser-authored source and arm
phases canonicalize numeric -0 to +0 before validation/identity. This is
phase-only transport/UI policy for physically equivalent zero phases.
It does not wrap or alter any nonzero phase. Python-origin JSON may retain
genuine -0.0 where its serializer supports it.

The sweep uses the shared exact literal list of 17 binary64 requested
phases from 0 through 6.283185307179586. The two endpoints are distinct
solver calls; no cached endpoint, forced equality or analytic replacement
is used. Scalar markers are the returned measurements. Connecting lines
are labelled visual interpolation and never bridge missing failed rows.
A point selection does no calculation; a separate explicit action submits
that phase for a full dual result.

Transport retains both original float64 intensity arrays and common metre
axes with explicit little-endian decoding. Display RGBA quantization and
Three.js coordinate conversion are presentation-only. Both ports use one
common color interval; explicit automatic range uses their joint maximum.
Clipping the displayed grayscale neither clamps the original intensity nor
changes a scalar ratio. A valid dark result uses black pixels and an ordinary
nonzero display interval. Raw picks and maxima still read the original data.

## Validation interpretation

New adapter tests compare responses to direct public V2a execution on
identical captured incident inputs. Separate analytic fixtures cover equal
arms, near-dark phases, common phase and the unequal DC-carrier example
`L0=lambda/7`, `L1=L0+lambda/6`, phi=0, whose lossless fractions are .75/.25.
A supported narrow Gaussian on a subwavelength grid demonstrates a total
ratio below one and identifies the original-input denominator.

Independent literal-byte/asymmetric fixtures test transport ordering and
coordinates; they are labelled transport fixtures, not new physical
simulation results. The direct HTTP validator independently decodes the
frame and runs the public source/solver oracle. Agreement validates this
integration on the same discrete periodic model; it does not constitute a
new independent continuum solver or sampling-convergence proof.

V2a's normative finite-case tolerances are unchanged. New fixture-specific
bounds, actual discrepancies and sweep endpoint closure measurements are
recorded in [tests_and_evidence.md](tests_and_evidence.md). Bit-exact dark
cancellation at floating-point pi or 2pi is not claimed, and near-dark
checks use separately stated relative and absolute tolerances.
