# A: independent ideal statistical polarization workspace

User-visible identity: **Ideal statistical polarization — independent
theoretical model**. A is a dedicated research workspace inside the existing
virtual bench. It is not a fifth ordinary bench mode, a calibrated instrument,
or Figure2a experimental reproduction. B remains separately gated by relevant
observable/axis/estimator evidence.

## Approved scope and frozen contract

The accepted2026-10-17 A scope derives from the unchanged prior split's exact
41 paths:10 modifications and31 creations. Six B-only paths are excluded.
The old workspace-reference screenshot name is replaced only by the explicit
`fig01_ideal_ensemble_workspace_and_readout.png` creation. The source inventory
hash, Windows path identities, baseline and complete list are frozen in
`runs/r03_ideal_polarization_impl_01/scope.json` before production edits.
The independently defined model, APIs, wire and resource contract was frozen in
that evidence directory's `model_contract.md` before executable implementation.
Earlier readiness/semantics documents and author-question drafts are unchanged.

## Actual model

One deliberate Compute creates one16×16 equal-probability Gaussian phase
realization using a local PCG64 Generator. It retains actual unwrapped and
periodic phases; no second browser RNG, centering, variance correction or
rejection sampling generates the display. D input amplitude is explicit.
Apply the ideal phase-only modulator, uniform QWP and HWP, then report actual
finite second moments at four algebraic stages. The infinite Gaussian
population DoP is separately labelled; it is not substituted for finite data.

`C=sum p E E†` is an expressly assumed statistical observation. Each sample
remains a local coherent Jones state. Random phases do not establish a
physical incoherent collection geometry. Units are amplitude-unit squared
and dimensionless normalized observables, not watts. Exactdark normalized
values/DoP are null. No eigenvalue/DoP clipping repairs material invalid input.
See [the numerical contract](../../math_conventions.md#321-a-ideal-statistical-polarization-independently-declared-ensemble)
and [math used](math_used.md).

The product has fixed256 samples, software amplitude range0..1e6, mean/element
angles±2πrad, standard deviation0..πrad, integer seed0..2^32−1. The grid-free
sample list has no physical pitch or propagation. Its explicit2×2 operations
are independently checked against existing public Jones operations on valid
test fixtures without manufacturing a runtime SamplingGrid.

## Application and identity

New POST routes are `/api/research/r03-fig2a/validate` and
`/api/research/r03-fig2a/simulate`.
The engineering namespace does not name the model as the paper's experiment.
Closed protocol/schema1 carries complete immutable settings/seed and a
SHA256 digest. Validation samples nothing and owns no compute gate.
Simulation makes one public core call and encodes the same phase realization,
four full coherency/Stokes measurements, normalized values, raw DoP/eigenvalues,
roundoff status, population expectation, units and model/RNG provenance.
Request/response ceilings are32768/131072bytes.

Only actual computation joins the existing Future-lifetime backend gate.
Disconnect/HTTP cancellation does not release a running worker. The frontend
shares the existing operation gate, binds immutable submitted identity, detaches
stale results and rejects late attachments. Numerical and presentation failures
are separate; manual display recovery reuses completed data without rerunning
the science. Camera, selection and display changes make no science calls.

## Integrated workspace and boundaries

The original design becomes an actual mounted apparatus, large central view,
useful inspector, visible source-to-modulator-to-measurement functional path,
actual submitted phase-mask texture and adjacent finite C/Stokes/DoP/S0 readout.
The routing cube and distances stay schematic/unknown. Computed rays and
propagated field sections are explicitly unavailable; decorative lighting is
not a quantitative field. A single ellipse never stands for the full mixed state.

The four existing modes and v1/v2 document acceptance matrix remain unchanged.
A settings export, sweeps, fitting, MAT import, reference overlays, paper
residuals, hardware, database, result archives and deployment are excluded.
Global app-owned budgets remain16MiB persistent/32MiB transient, including
old results, new buffers, document reservations and preparation/rollback overlap.
Explicit release preserves drafts, invalid edits, camera and useful documents.

## Verification and publication record

The fresh unchanged baseline is3242 Python passes/one existing Windows
symlink skip,304 frontend tests across18files, typecheck and production build.
The original sandbox frontend startup EPERM and its unchanged permission retry
are retained separately. The historical Chrome response-capture issue remains
historical and is not declared resolved by A.

Current completion evidence is recorded in [tests and evidence](tests_and_evidence.md),
with limitations in [known limitations](known_limitations.md). Screenshots are
actual application captures, not rendered SVG substitutes. One commit and normal
push are approved only under the specified clean-postcommit gate; a required
postcommit failure stops before push without retry-until-green or history rewrite.

Teaching is separate. A asserts no lesson completion; no stage after A begins.
