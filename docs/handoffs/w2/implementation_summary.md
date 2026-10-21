# W2 — Computed geometric optical routing

Status: implemented and validated within the reported scope; awaiting the
user's visual review, not accepted or published. This candidate is authorized
for implementation and validation only. All changes remain unstaged and
uncommitted at the visual-review checkpoint.

## Frozen contract before executable integration

Accepted parent: `721156cef44bc76425d7d437cc258b6481acf204`.
The original five planning files are immutable. Their hashes and the exact
42-path inventory (9 modifications, 33 creations) are recorded in
`runs/w2_geometric_routing_implementation_01/preflight.json`.

The new independent workspace is **Geometric Routing**, model
`w2_ideal_geometric_routing_v1`. It is not a SequentialExperiment, a wave
simulation, a coherent splitter, a radiometer, or a settings-document mode.
One source ray and at most sixteen finite disk/rectangle optical faces support
two-sided ideal mirrors, zero-thickness deterministic half splitters, absorbing
stops, and terminating receivers. Mounts are decorative and do not obstruct.

Coordinates are right-handed physical SI XYZ, with Y up. Render positions use
one uniform factor of ten. Local surface u/v/n axes begin at X/Y/Z. Pose uses
active column vectors, `R = Rz(z) Ry(y) Rx(x)` (X, then Y, then Z).
Internal angles are radians in [-pi, pi]; the inspector explicitly displays
X/Y/Z rotation in degrees. Untouched fields must preserve their original SI
values. Reflection uses the incoming propagation direction:
`d_out = d_in - 2 dot(d_in,n) n`. No repeated normalization or origin epsilon.

## Limits, equality and precedence

The exact result `limits` record is closed and contains:

```json
{"max_elements":16,"max_interactions":32,"max_branches":63,"max_records":256,"max_hits":128,"max_segments":256,"trace_radius_m":1.0,"max_distance_m":10.0}
```

The root counts as one ever-created branch. A mirror continues the same branch.
A splitter atomically allocates two children, T then R; split parents count
toward the branch cap but never the terminal-weight sum. Breadth-first
scheduling and stable parent/branch/hit/segment identities are required.

An actual surface event consumes one segment and one hit (two combined
records). A domain/distance endpoint consumes one segment and no hit. A cap
terminal at an already known point consumes neither segment nor hit. Exact
capacity is allowed; an event requiring more than the remaining capacity is
not partly allocated. Global branch/record exhaustion terminates every
unresolved current/queued leaf as resource-truncated at its actual known point.

The 32nd certified hit is processed: receiver/stop termination wins; a mirror
then truncates at that hit. A splitter can allocate the atomic pair when
capacity permits; both children inherit 32 interactions and truncate there.
No subsequent propagation occurs for a path already at its interaction cap.

All full finite faces must be conservatively certified strictly inside the
source-centered radius-one-metre trace sphere. Thus an admitted optical face
cannot coincide with the domain boundary. Geometric lengths use actual
`hypot(end-start)`, accounting for direction norm drift. A hit is processed
before the 10 m cap only if its distance is certified within the remaining
length. Unresolved hit/cap interval overlap, including nominal equality, is
numerical ambiguity; there is no nominal-float tie shortcut.

Finite-face impossibility is conservatively checked before ambiguous
infinite-plane predicates. Irrelevant remote coplanar faces cannot reject a
valid route. Closed finite edges with unresolved boundary overlap are
ambiguous. Candidate interval ordering must certify the nearest finite hit;
array order is not a tie breaker. The immediate previous zero-thickness plane
is excluded only for the outgoing straight leg; subsequent returns are legal.

## Exact API and error envelope

Both endpoints are same-origin loopback POST requests under the existing
Host/Origin boundary. Requests are bounded to 32768 UTF-8 bytes. Responses are
bounded to 524288 bytes; overflow fails instead of truncating JSON.

- `/api/w2/validate`: closed request `{request_id, scene}`; validates the
  complete scene and returns owned surface frames and an opaque scene digest.
  It performs no trace and does not acquire the computation gate.
- `/api/w2/trace`: closed request `{request_id, scene_sha256, scene}`; invokes
  the public core trace exactly once and encodes inside the sole existing
  actual-Future-lifetime gate. Disconnect does not release running work.

All replies use protocol_version=1 and the model identifier above.
Validation message_type is `scene_validation`, trace is `trace_result`, error
is `routing_error`. Canonical scene digest is SHA256 of the owned scene DTO
encoded with Python json.dumps(sort_keys=True, separators=(',', ':'),
ensure_ascii=True, allow_nan=False), UTF-8; element array order is retained.
The browser stores the returned opaque digest, not a JS-generated substitute.

Validation reply closed keys: protocol_version, message_type, request_id,
model_contract, scene_sha256, scene, surface_frames.
Trace reply closed keys: protocol_version, message_type, request_id,
model_contract, scene_sha256, scene, surface_frames, limits, status, branches,
segments, hits, terminals, ledger, diagnostics. All nested records follow the
unchanged frozen model_contract.json wire_schemas.

Error closed keys: protocol_version, message_type, request_id, model_contract,
error. Error has exactly code and message. request_id is null if no canonical
UUID can be safely recovered. Codes are bounded ASCII tokens; messages are
bounded to 300 characters. Invalid scenes, unsupported numerical inputs and
numerical ambiguity return 422 with distinct codes; busy is 409/no queue;
request overflow is 413; response overflow/unexpected work or encoding failure
is 500, with no successful partial result. Existing malformed framing/JSON,
disconnect, cancellation and security policies retain their distinct statuses.

Production encoding validates the complete result within the worker. An
explicit custom worker is a trusted acceptance seam; deliberately malformed
child-only replies are classified as transport controls, never valid results.

## Numerical and display ownership

The implementation propagates conservative uncertainty through pose/basis,
origin, direction, intersections, finite domains, nearest ordering, reflection,
domain crossings and accumulated geometric length for all 32 supported stages.
Claims against stored binary64 frames and against ideal real angles must be
distinguished. The shipped independent reference/error-bound gate is required;
planning local predicates and small observed residuals do not establish it.

Only terminal leaves contribute to detected + absorbed + escaped + truncated.
The signed residual is one minus math.fsum(leaf weights), rtol=0,
atol=64*binary64 epsilon. No pruning, hidden normalization, coherent merging,
or labelling truncation as absorption. Any truncated leaf means incomplete.

Explicit Trace alone computes. Edits detach old paths; retained prior results
keep their original identity. Complete UUID/revision/attachment-epoch/digest,
scene and graph checks precede atomic publication. Numerical completion and
presentation failure are separate; manual display recovery does not trace.

The global app-owned limits remain 16 MiB persistent and 32 MiB transient.
W2's 2/4 MiB operation reservations must be verified against actual owned
representations, decoded objects, buffers, labels, replacement/rollback and
retained old modes/documents. They are not a total browser/GPU-memory claim.
No automatic eviction, queue, cap increase or resolution reduction is allowed.

## Current verification

Before any implementation edit, the unchanged candidate passed:

```text
3653 passed, 1 skipped in 190.24s (0:03:10)
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
Test Files  28 passed (28)
Tests  445 passed (445)
```

Raw, unedited output and exact commands are retained under the new ignored
implementation root's baseline directory. The first frontend launch was
blocked by sandbox spawn EPERM before tests started; its failure is retained.
The identical installed suite passed with normal process permission. No
dependency or test alteration was used for that baseline. The final current
results below supersede only the candidate qualification; all failures and
historical measurements remain preserved. No stage, commit or push is authorized.


## Validated implementation checkpoint — 2026-10-21

The full frozen candidate passes Python **3910 passed, 1 skipped in 300.98s**
(the original Windows symlink privilege skip), frontend typecheck, **495 unit
tests / 32 files**, and the fresh production build. The >500 kB bundle warning
remains; no build threshold or dependency was changed. Independent science
includes 78 focused tests, 14 direct validator cases and 16 detecting numerical
fault copies. Four frontend source faults trigger their intended assertions;
43 restored W2 unit cases pass. Presentation-failure regressions retain both
initial and replacement numerical ownership for explicit display-only recovery.

Actual final browser coverage is 20 W2 passes, 55 legacy passes / 8 declared
controlled-only exclusions, 12 W1 passes, 7 English passes and 19 fresh legacy
control passes. That is 113 passing invocations / 8 expected skips, 101 unique
IDs and 121 isolated invocations, one attempt each and retries=0. The recording
workflow is 36.056 seconds; its genuine WebM is 36.64 seconds. Three genuine
screenshots cover a reflected hit, pose-edit finite miss and split/blocked
weights. All services and browser contexts owned by these invocations closed.

The final source/assets, protected 429 files, frozen planning, installed
package identities and unchanged baseline HEAD were verified. Exactly 42
approved paths remain unstaged: 9 modifications and 33 creations. Full raw
output, every required failure and correction, numerical/resource qualifications,
media and the complete diff are in [tests_and_evidence.md](tests_and_evidence.md).
There is no outstanding required gate failure. User visual acceptance and
publication remain separate approvals.

## Review the already-built candidate

The default old dist directory was not replaced. From the repository root,
the following command serves the verified final assets through the existing
production factory and normal loopback boundary. Observe mode records actual
work; it introduces no hold, fault response or synthetic optical result.
The evidence directory must be fresh; if it exists, preserve it and choose a
new owned directory. Port 8510 must be free; never stop an unrelated occupant.

```powershell
.\.venv\Scripts\python.exe -B scripts/w2_controlled_acceptance_server.py --mode observe --operation routing --assets-dir C:\holographiclab\runs\w2_geometric_routing_implementation_01\acceptance\frontend_final_04\assets --evidence-dir C:\holographiclab\runs\w2_geometric_routing_implementation_01\manual_visual_review_01
```

Open http://127.0.0.1:8510 and choose **Geometric Routing**. Stop that owned
review service normally with Ctrl+C. No review server is left running by this
implementation pass. No refraction, folded-wave coupling, persistence,
Figure 2a comparison, hardware or teaching-state work was started.
