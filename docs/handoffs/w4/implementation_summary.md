# W4 — Fresnel Power Routing implementation candidate

Original evidence recorded2026-10-26; closeout2026-10-29 (Asia/Taipei).
Implementation and validation are approved within exactly47 paths:11 modifications
and36 creations. Baseline `5f7f69fb6303402cffed830b3cfb9794a43b4fcf`. The candidate
remains **UNSTAGED and UNCOMMITTED**, awaiting the **user's visual review**;
staging, commit and push are not authorized. Recorded browser acceptance passed
on Chrome156.0.8078.47; externally updated installed156.0.8078.48 acceptance is
**NOT_RUN**. Its sole identity drift leaves the strict current freeze comparison
FAIL, separately from verified recorded evidence. Earlier W2/W3 handoffs and the
immutable `runs/w4_fresnel_plan_01/` package retain their original provenance.

## Product and supported model

The existing English **Geometric Routing** shell, shared Three.js scene and
camera gain an explicitly selected **Fresnel Power Routing** model. W2 remains
the default; W2/W3 scenes are not upgraded. W4 presets are Normal Slab,
Refracting Prism and TIR Prism. Source polarization presets are unpolarized,
linear source-e1, linear source-e2 and linear45. Edits require deliberate Trace
and detach current paths and event details immediately. Camera, opacity, branch
selection, normals, scrolling and presentation recovery do not trace.

The model supports a single fixed+Z source outside zero/one finite convex
rectangular block or right triangular prism, plus at most four exterior receivers
or beam stops. Interfaces are smooth, lossless, uncoated, isotropic and
nonmagnetic, with real constant indices in[1,2.5]. Source origins are the two
declared preset triples `[0,.08,-.04]`m and `[.02,.08,-.04]`m. There is no source
direction/position editor. Body dimensions are[1e-4,.25]m, pose components±10m,
intrinsic XYZ rotations±stored pi, source-centred exit radius1m and cumulative
distance10m. Conservative finite-face/separation/medium admission can reject
otherwise visually plausible input; inputs and receivers are never moved.

Source-relative optical power is dimensionless. **Receiver total — incoherent
path sum.** This compulsory model assumption does not establish physical
incoherence from a monochromatic source. Line thickness, mounts and direction
markers are presentation, not power calibration, beam width or optical surfaces.
No W1 field is attached to folded rays. See [limitations](known_limitations.md).

## Public numerical and transport contract

- `ohlab.optics.fresnel_interface`: `TransverseFrame`, `RayPowerState`,
  `FresnelCoefficients`, `FresnelInteraction`, `source_power_state`,
  `fresnel_coefficients`, `apply_fresnel_interface`, `polarization_diagnostics`.
- `ohlab.optics.fresnel_routing`: `FresnelScene.from_dict`,
  `validate_fresnel_scene`, `trace_fresnel_scene`, `FresnelTraceResult`.
- Additive W3-owned geometry seam: `CertifiedDielectricGeometry`,
  `CertifiedDielectricDirections`, `CertifiedNormalIncidence`,
  `certified_geometry`, `certified_dielectric_directions`. W4 imports public
  ownership boundaries rather than copying or importing private solvers.
- Adapter: `ValidatedFresnelSubmission`, `validate_submission`,
  `validation_reply`, `trace_submission`. One intentional trace invokes the
  public numerical runner exactly once. Owned immutable submitted scenes,
  validation metadata, results and independent serialization copies prevent
  source/result mutation.

Model=`w4_fresnel_polarized_routing_v1`; schema/protocol1;
power policy=`absolute_source_coherency_v1`;
path addition=`incoherent_phase_averaged_v1`. POST`/api/w4/validate` has exactly
request_id+scene and performs no trace/gate acquisition. POST`/api/w4/trace`
has request_id+scene_sha256+scene. UUIDv4/full canonical scene digest bind the
closed response graph to the submitted model, source, media and request.
Message types are `fresnel_scene_validation`, `fresnel_trace_result`,
`fresnel_routing_error`. Errors have seven flat keys and no partial result.
Complete key inventories remain in the frozen planning contract and strict
production protocol; both Python and browser reject additional/missing fields,
invalid states, graph identities or enclosures before publication/attachment.

Each compact state stores actual geometric direction, medium/index, right-handed
transverse frame, packed Hermitian C=(C00,C11,ReC01,ImC01), power_fraction and
outward numerical bounds. Power is trace(C); the serialized power is checked,
never multiplied into C again. Source trace is1; child attenuation and within-ray
phase remain authoritative. Normalized Stokes/DoP are separate diagnostics,
undefined/null at exactly zero. No hidden normalization, PSD projection, weak
pruning, camera-selected polarization basis or invented receiver matrix is used.
The [math handoff](math_used.md) and normative conventions§3.25 give signs,
frames, coefficients and admission details.

## Traversal, ownership and resource limits

FIFO processing creates reflected then transmitted children with stable
`r0(.R|.T)*` ancestry. Root and parents count toward31 ever-created branches;
allocation of all positive children is atomic. Caps are8 ancestry surface hits,
32 global surface events,64 segments,96 combined records and16 terminal leaves.
Receivers/stops at their permitted last hit terminate before later propagation.
An unallocated split retains its incident parent as unresolved without counting
candidate children. Every queued/current positive state is accounted at a cap.
Only terminal leaves enter detected/stopped/escaped/resource_unresolved sums;
the signed residual is retained. Any nonzero unresolved power means incomplete.
An ambiguous geometry/criticality or unusable arithmetic fails the trace rather
than publishing a successful partial result.

The same sole actual-worker-lifetime gate now covers12 computing operations
through final W4 encoding, including after disconnect. There is no extra
executor/queue/retry. Loopback Host/Origin/method/body boundaries are preserved.
Request32768B/response393216B are hard atomic caps. W4 local reservations remain
4MiB persistent/8MiB transient inside global16/32MiB. One W4 validation/trace
payload read may be unsettled; only the latest validation candidate is coalesced.
Its8MiB charge survives panel leave/dispose until actual read settlement. Trace
is disabled during a read and still requires an intentional click afterward.

The fixed-size response collector and nonallocating JSON shape/token preflight
bound parse work before object construction. Parse ceiling2,584,576B reserves
the previous4MiB result, response-buffer/string overlap, request and scanner.
New display preparation reserves128KiB and the1MiB DOM allowance before factory
allocation, then checks actual resources. Replacement/rollback and mixed modes
remain subject to aggregate admission; no automatic eviction. These app-owned
budgets are not process/V8/GPU/RSS guarantees. Explicit Release frees results
while preserving drafts/documents and appropriate camera state.

## Launch and deliberate inspection

Use the existing repository interpreter and installed frontend tools. No install
or environment reconstruction is part of launch. The normal existing workflow is:

```powershell
cd C:\holographiclab\frontend\bench
npm run build
cd C:\holographiclab
.\.venv\Scripts\python.exe -m apps.virtual_bench.server
```

Open `http://127.0.0.1:8510`, choose Geometric Routing and explicitly select
Fresnel Power Routing. Do not replace an occupied port/service. Actual acceptance
uses separately owned source-hashed production assets under
`runs/w4_fresnel_implementation_01/build_06/assets/`; an ordinary rebuild does not
inherit that asset identity. The loopback service refuses an occupied8510 and
does not operate the unrelated8501 service.

To inspect the exact source-hashed assets used in the recorded acceptance,
the following optional local command uses the already present task-owned helper;
it does not rebuild or replace the environment. Use a new evidence directory
name each time, and do not replace an occupied service:

```powershell
cd C:\holographiclab
.\.venv\Scripts\python.exe -B -X utf8 runs\w4_fresnel_implementation_01\backend\production_child.py --manifest runs\w4_fresnel_implementation_01\build_06\source_asset_identity.json --evidence-dir runs\w4_fresnel_implementation_01\manual_visual_review_NEW\service
```

This helper injects only verified assets into the ordinary production factory.
It has no controlled worker/fault replacement. Close the task-owned listener
with its normal console interruption or its owned `service/stop.flag`; do not
stop an unrelated listener. This is a review launch option, not a new acceptance
run on current Chrome.48, and no review service is left running by this closeout.

For Normal Slab, inspect the first interface R/T, first straight `r0.T.T` leaf,
receiver totals and nonzero unresolved ledger separately. For the fixed56-degree
Y-tilt compare source-e1/e2 with unchanged receivers; do not label every source
preset universally s/p. For TIR Prism choose linear45 to expose retained complex
coherency, then inspect the reflected medium and absent propagating T leg.
Full strings are nonwrapping and keyboard/pointer accessible within bounded
local tables. The three genuine approved screenshots have source/asset/result
identity receipts. The final genuine42.64s normal-speed recording shows explicit
normal/56-degree source-e1/source-e2/TIR calculations, stale detachment and passive
inspection of the unresolved ledger and first.9216 leaf. The selected-branch
readout is complete; the terminal table also has local horizontal access.
Eight original-video frames and two screenshots were reviewed by the engineer;
this is not continuous manual playback or user acceptance. The first42.6s video,
whose readouts were below the viewport, remains preserved. The original video,
hashes and qualifications are [explicitly recorded](tests_and_evidence.md).

## Checkpoint and preservation

Final Python03: **4616 passed,1 skipped in312.60s (0:05:12)**; the same Windows
symlink-privilege skip remains. Interrupted Python02 has UNKNOWN native status
and no final summary; its raw evidence and the earlier Python01 pass remain
separate. Frontend636/39, typecheck06 and source-unchanged build06 passed, with
the original greater-than500kB warning retained.

Browser07/freeze07 completed160 conditions/134 distinct IDs on Chrome156.0.8078.47,
workers1/retries0/skips0. The separate B11-only freeze08 recording adds one
native0 invocation, without relabelling the160 whole-file identities. Every
owned service exited0 and left8510 free;8501 was untouched. Bridge02 verifies19
original build06 replies by exact public offline replay and independent Decimal90
references, with no added HTTP. Three genuine screenshots and the final recording
are present. `final_acceptance_summary_01/summary.json` classifies this as
`RECORDED_BUILD06_ACCEPTANCE_VERIFIED_WITH_CURRENT_BROWSER_DRIFT`.

The strict resumed freeze comparison remains FAIL solely for the external
Chrome.47→.48 executable change; newer-browser acceptance is NOT_RUN. Other189
frozen identities,52 build sources/three assets,493 protected files,163 planning
files,53 installed Python distributions and7 frontend manifests match. Recorded
main/HEAD/upstream remain the baseline and the index is empty. The final exact
47-path review diff and preservation export are supplied separately after these
documentation edits; this paragraph does not predeclare that export's result.
No dependency change, staging, commit, push, later feature or teaching-state
change is included. Stop at the user's visual-review checkpoint.

## 2026-10-29 — approved copy correction and Chrome .48 precommit qualification

The preceding checkpoint is preserved verbatim as dated history. The user's new
approval accepts the main W4 visual/interaction direction and conditionally
authorizes one publication commit after the declared gates. The only production
correction changes the visible and accessible labels from “Exterior fresnel
index” / “Interior fresnel index” to **“Exterior refractive index” / “Interior
refractive index”**. Existing input IDs, JSON paths, values, model/API/transport
names, numerical logic, formatting and defaults are unchanged. One focused unit
test verifies the actual editor bindings and passive rerender; existing B01 keeps
its title/assertions and adds corrected-copy and visible branch/receiver/ledger
checks without additional scientific requests. Exact before/after hashes and the
three-file correction diff are in U/copy_correction_01/receipt.json; here U means
`runs/w4_closeout_chrome48_01/`.

New installed typecheck passed(native0), all **637 frontend tests/39 files**
passed, and precommit build02 passed(native0/source stable). Build01's sandbox
`spawn EPERM` remains preserved; the normal permission route used the same source,
tools/configuration and dependencies for build02, with no repair or installation.
The new **39 precommit conditions/30 IDs passed**, with40 actual Chrome
launches(including the extra B10 zoom launch) all reporting156.0.8078.48,
zero skips/retries and native0 owned-service cleanup/free8510. Fifteen genuine
.48 original replies match exact offline public byte replay and independent
Decimal90 references, with0 added HTTP. Receipts are in
`U/precommit/browser01/result.json`, `U/precommit/bridge_complete02/results.json`
and `U/ENVIRONMENT_TRANSITION_PRECOMMIT.json`. Corrected inspector, normal-slab
and TIR captures are fresh U evidence; historical handoff PNGs are not replaced.

The original42.64s video/screenshots remain genuine **.47** evidence. The original
.47→.48 identity comparison remains **FAIL** and Python02 remains **UNKNOWN**;
neither was rewritten. Python03's4616passed/one existing symlink skip in312.60s,
Decimal90/seven original weak fixtures/13 detecting controls are qualified reuse
under verified unchanged scientific source, inputs/settings, interpreter and
dependencies. W4 remains bounded constant-index lossless-interface power routing,
within-ray polarization and explicitly incoherent path addition.

At this appended **precommit checkpoint**, no clean-postcommit result or push is
claimed. `U/DECLARED_GATES.json` freezes the exact39 precommit and21 postcommit
conditions/exclusions before execution/commit. The single authorized commit is
`feat(w4): add Fresnel power routing with carried polarization`. Publication
requires clean-commit fresh owned assets, actual .48 runtime, the exact21-case
postcommit slice/current-response references, protected identities and unchanged
remote parent. Required failure/drift stops before push without amend/retry.
Final postcommit/publication receipts belong to ignored U evidence and the final
report; this historical checkpoint does not predeclare their outcome. No later
optics, scene persistence, Figure2a or teaching-status work is included.
