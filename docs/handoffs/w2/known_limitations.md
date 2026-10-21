# W2 known limitations and evidence boundaries

This is an uncommitted implementation candidate for visual review. The
approval covers implementation and validation, not staging, commit, push or
acceptance of a later capability. Exact current full-suite/browser/media
status belongs in [tests_and_evidence.md](tests_and_evidence.md); numerical
core passes alone do not declare those product gates complete.

## Deliberately ideal geometry

The model has one explicit ray in a homogeneous medium, finite disk/rectangle
planes, two-sided ideal mirrors, deterministic zero-thickness50:50 splitters,
absorbing stops and terminating receivers. It has no source bundle, divergence,
physical beam waist, refraction, glass volume, coating response, scattering,
curved optics, polarization, phase, interference or calibrated radiometry.
Receivers record local hit coordinates and relative weight, not images or
watts. Crossing rays do not interfere. Housings and mounting hardware are
decorative and nonblocking; visually crossing a mount is not a hidden solver
failure or an implemented mechanical-occlusion model.

Line thickness, brightness and glow aid inspection. They are not a measured
laser diameter, side-scattering measurement or weight-dependent detector
texture. W1 fields remain on their supported aligned optical train; no field
has been bent, pasted or relabelled as a folded-wave solution. Such coupling
would need its own phase, transverse-frame, sampling and oblique-boundary
contract and separate approval.

## Numerical failures are intentional supported behavior

The entire declared scene must pass type/value/closed-schema, pose/frame and
source-centered-domain admission. A complete finite aperture must be strictly
inside the source's radius1m trace sphere. Source coordinates are bounded by
absolute component10m and aperture dimensions by1e-6..0.25m. These are software
limits, not measured apparatus capabilities.

Input direction is already nominal unit within32epsilon. Frames must satisfy
64epsilon orthogonality policy and reflected directions128epsilon norm
policy. There is no silent normalization, clamp, snap, angle rewrite or
automatic re-aiming. Distances account for retained direction norm drift.

Relevant exact/uncertain aperture edges, near-launch roots, grazing/coplanar
events, near-coincident nearest hits, overlapping faces, domain-order or
distance-cap decisions can fail with numerical ambiguity. In particular:

- An unresolved hit at the10m distance cap is rejected even if nominal
  printed values appear equal. Nominal equality is not a certified tiebreak.
- Exact and immediately adjacent-float disk/rectangle edges may remain
  ambiguous; wider independently certified inside/outside approaches work.
- A remote finite face on an irrelevant infinite plane is conservatively
  culled first; uncertainty in that cull cannot be ignored. A provably farther
  ambiguous face cannot veto a closer certified hit.
- No fixed origin epsilon skips nearby components. Only the preceding
  zero-thickness plane is excluded for one outgoing straight leg; later
  visits are allowed.
- Conservative intervals may widen through32 stages. This is neither a
  promise of uniform grazing accuracy nor permission to replace bounds with
  smaller observed residuals. Unsupported arithmetic produces an error,
  never optical absorption, escape or a successful incomplete result.

Enclosures assume supported binary64 round-to-nearest arithmetic, gradual
underflow, no FTZ/fastmath and correctly directed endpoint arithmetic/square
root. Exact-rational Taylor certificates cover trigonometry at stored
binary64 angles; that target differs from an unstored ideal decimal degree
input. Stored binary64 frame comparisons and ideal-angle comparisons are
independent evidence categories.

## Resource truncation is not a physical loss

Caps are16 elements,32 accumulated interactions/path,63 ever-created branches
including root/split parents,256 combined segment/hit records, source-centered
radius1m, and10m cumulative distance/path. At most128 hits/256segments are
allowed; the segment-only256 guard is redundant under the combined/branch
constraints. Deterministic BFS creates T then R atomically. If a global
branch/record limit prevents work, every current/queued unresolved leaf
retains its weight as `resource_truncated`. No low-weight visibility pruning
or surviving-ray renormalization occurs.

Any truncated leaf makes the result incomplete. An escaped endpoint means
the ray left the declared bounded region, not that it can never hit anything
in an unbounded laboratory. Distance/domain endpoints and cap terminals are
actual calculated/known states; no decorative receiver endpoint is invented.

Strict JSON requests/replies remain32KiB/512KiB. Encoding fails rather than
truncating a large graph. Genuine max-record direct integration produced
180815B, but this is a measured case, not a formal worst-case serializer proof.
Separate bounded schema-stress checks and genuine tracer checks must remain
distinct.

Global app-owned budgets remain16MiB retained/32MiB transient. W2's2/4MiB
reservations describe admitted app ownership, not total browser heap, RSS,
native fetch-clone copies, GPU driver memory or a guaranteed frame rate.
Python record/encode/decode measurements do not prove browser admission.
CPU submission/frame-interval observations are not GPU timings. Mixed prior
results, documents, preparation overlap, display rollback and release recovery
have separately qualified current evidence in tests_and_evidence.md.

## Interface and persistence boundaries

Only explicit Trace computes. Editing detaches old paths; a retained prior
result keeps its submitted identity and is labelled previous/detached.
Camera, selection, labels and branch inspection do not compute. Late replies
are not attached to a newer scene. Display failure can retain completed
numerics; manual presentation recovery must not replay Trace.

Routing scene import/export is unsupported in this slice. W2 is not a
SequentialExperiment and is not encoded under old settings v1/v2 or M5 bundle
contracts. Old document state remains separately owned while its controls
are hidden in W2. Future routing persistence needs explicit model/version and
transactional compatibility work.

## Evidence that must stay qualified

At the core handoff checkpoint,78 focused tests and14 direct cases plus16
isolated numerical faults pass. Both actual stored-frame and ideal-angle
Decimal160 references cover full32-stage trajectories. This is current core
evidence, not final Python/frontend/ASGI/browser acceptance. Exact paths,
commands and hashes are in
`runs/w2_geometric_routing_implementation_01/core/core_handoff_manifest.json`
and `NUMERICAL_CONTRACT_AND_EVIDENCE.md`.

The core development failure `development_core_final_01` remains73passed/
1failed. It exposed negative-subnormal lower bounds in an exact-zero norm;
the implementation was corrected using the mathematical nonnegative
constraint without weakening the original assertion. Earlier planning's
initial failed near-parallel screen and asynchronous source-copy disclosure
remain in the original planning report; no old measurement was overwritten.

The accepted W1.1 history remains unchanged: historical3653Python passes/
1Windows symlink skip,445 frontend units,55legacy passes/8controlled-only
skips and27postcommit passes are not freshly rerun merely by citing them.
Some prior controls were reused; two held-worker recoveries were not rerun
with the new capture helper in that accepted history. The old Chrome/CDP
cause remains unknown and one overwritten screenshot remains lost/
unverifiable. New W2 evidence cannot restore or reclassify that old failure.

No hardware, deployment, Figure2a reconciliation, new persistence, teaching
state update or later optical stage is implied by this candidate.


## Current measured resource qualification

The final browser and full-suite checks pass within the reported scope; they
do not remove the ideal-model or numerical limits above. The genuine full-record
response is 180815 B. Separate typed finite-float DTO analysis bounds the relaxed
closed success shape at 427884 B; a 227990 B numeric-representation stress graph
round-trips, while a broader 667286 B integer stress graph is rejected atomically
by the unchanged 512 KiB cap. These representation probes are not physical routes.

The particular 9-element, 256-record original-byte owner replay prepares at
2015948 B, 81204 B below the unchanged 2 MiB reservation; its incoming transient
envelope is 2837512 B under 4 MiB. It uses real decoder/controller/Three CPU
factories plus the full 1 MiB prospective DOM reservation. Its full 128-hit
native browser inspector was not measured, and this margin is not promised
for every 16-element/maximum-identifier combination. Admission can reject a
representation that exceeds the declared budget; no automatic eviction,
precision reduction, visibility pruning or cap increase is used.

Actual current mixed-mode browser release reduces the declared global retained
account from 9030730 B to 622976 B while preserving invalid text and the prepared
document. The last 600 recording samples and worker timings are observations
under concurrent Python-suite load, not isolated benchmarks, full-recording
frame statistics, GPU timings or whole-browser/native memory measurements.
See tests_and_evidence.md for exact samples, exclusions and original sources.
