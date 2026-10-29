# W4 tests and evidence — implementation checkpoint

Original evidence recorded2026-10-26; closeout2026-10-29 (Asia/Taipei). This is an
**unstaged, uncommitted candidate**, not user visual acceptance or publication.
Final Python03 passes4616 cases/one existing skip. All160 recorded production/
controlled browser conditions plus one focused final recording pass on original
Chrome156.0.8078.47. Installed156.0.8078.48 changed externally; its acceptance is
**NOT_RUN**, and the strict current freeze comparison remains FAIL on that sole
identity difference. Recorded acceptance is separately verified below. No
staging, commit or push is authorized.

## Provenance and evidence ownership

Repository `C:\holographiclab`; accepted starting HEAD/upstream/live main
`5f7f69fb6303402cffed830b3cfb9794a43b4fcf`. The initially clean main was checked
before implementation without restoring or discarding work. The existing
Windows interpreter is `C:\holographiclab\.venv\Scripts\python.exe`, Python3.11.9.
No dependencies, lockfiles, global Git configuration or persistent environment
settings were changed. Resumed raw identity comparison verifies protected
files, planning, packages and source/assets; only the Chrome executable drift
fails the strict current browser freeze, explicitly qualified below. The final
complete diff/preservation export follows documentation closeout separately.

The fresh ignored evidence owner is
`C:\holographiclab\runs\w4_fresnel_implementation_01` (Q below).
`PREFLIGHT.json` records504 pre-existing tracked files,53 installed Python
distribution metadata trees,7 installed frontend manifests,163 immutable plan
files and the exact47-path allowlist. `CONTRACT_COMPLETION.md` was frozen before
executable integration. The planning directory is preserved; planning timings,
static designs, failed probes and historical W2/W3 acceptance remain historical,
not current shipped acceptance.

Every invocation uses a fresh exclusive evidence directory with exact argv,
working directory, source/tool identities, unedited stdout/stderr and native
return code. A wrapper's successful recording is not substituted for a failing
child's code. Python uses `-B` and pytest disables cache writes. Evidence/output/
temporary paths are owned; no historical artifact is overwritten.

## Whole-suite and frontend gates actually executed

Baseline Python command from the repository root:

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

`Q/baseline/python_01/`: native0, **4202 passed,1 skipped in136.84s**.
Unedited output is in `stdout.txt`; the original Windows symlink skip remains.
The first baseline installed frontend unit invocation failed before collection:
Vite child startup returned `spawn EPERM`. It remains in
`baseline/frontend_unit_01/`. The same unchanged command, through the normal
permission mechanism, executed in `baseline/frontend_unit_permission_02/`:
native0, **569 passed across35 files**. The npm update notice was preserved;
no update/install followed it.

Earlier implementation Python01 command (preserved measurement):

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --basetemp=C:\holographiclab\runs\w4_fresnel_implementation_01\final\python_01\pytest_tmp
```

`Q/final/python_01/`: native0. Exact unedited final lines:

```text
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
4616 passed, 1 skipped in 340.48s (0:05:40)
```

The complete original progress/output is retained in that `stdout.txt` and its
unmodified stderr/native result. No test was changed or privileges elevated to
remove the skip. This full run follows the final core source and restored fault
copies. A later new-test EOF blank cleanup was AST-identical; Python01 remains
qualified to its own original raw source identity rather than being relabelled.

Final closeout Python03 command, from `C:\holographiclab`:

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --basetemp=C:\holographiclab\runs\w4_fresnel_implementation_01\final\python_03\pytest_tmp
```

`Q/final/python_03/`: native0; exact unedited final lines:

```text
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
4616 passed, 1 skipped in 312.60s (0:05:12)
```

Complete unedited output, empty stderr, argv and native status remain in
`stdout.txt`, `stderr.txt`, `invocation.json` and `result.json`. The wrapper took
316.716s; that is distinct from pytest's312.60s. `Q/final/python_02/` was interrupted
after70% progress without final summary or recorded native status. Its preserved
receipt `final/python_02_interruption/receipt.json` says UNKNOWN_NOT_RECORDED;
it is neither a passing completion nor an inferred scientific assertion failure.
After resumed source/environment identity checks found no source/package drift,
one fresh final03 invocation used the existing interpreter without test changes,
privilege elevation, dependency repair, retries-until-green or skip removal.

Frontend commands execute from `C:\holographiclab\frontend\bench` with installed
Node/npm:

```powershell
& 'C:\Program Files\nodejs\node.exe' 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js' run typecheck
& 'C:\Program Files\nodejs\node.exe' 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js' run test:unit
& 'C:\Program Files\nodejs\node.exe' node_modules/vite/bin/vite.js build --outDir C:\holographiclab\runs\w4_fresnel_implementation_01\build_02\assets
```

Earlier integration `final/frontend_typecheck_02/`: native0, `tsc --noEmit`.
Earlier `final/frontend_unit_02/`: native0, exact summary:

```text
 Test Files  39 passed (39)
      Tests  623 passed (623)
   Start at  21:05:55
   Duration  13.72s (import 47%, tests 31%, transform 19%, worker 3%)
```

`build_02/`: native0,53 modules transformed; source hashes before/after match.
The JS bundle is1,207.66kB (gzip318.40kB), CSS44.33kB. The existing warning that
some chunks exceed500kB remains in raw stderr; no splitting, warning suppression,
dependency or configuration change was introduced. `source_asset_identity.json`
binds the exact source and three emitted files. `build_01/`, first typecheck and
622-test run are preserved **superseded** integration evidence: the later W4
allocation-preflight correction added one regression and required these fresh
frontend gates. That earlier evidence is now superseded by the scoped layout/
decoder corrections and current build06 below; it remains preserved. A browser
run must use matching source/assets rather than silently reusing an earlier build.

### Current frontend gates and three demonstrated decoder corrections

`final/frontend_typecheck_05/`: native0, `tsc --noEmit`. The separate post-B11
`final/frontend_typecheck_06/` also exits0 with the unchanged installed
`npm run typecheck` command; its argv/raw output/native result are retained.
`final/frontend_unit_04/`: native0; complete raw output remains unchanged, with
exact summary:

```text
 Test Files  39 passed (39)
      Tests  636 passed (636)
   Start at  21:42:28
   Duration  9.84s (import 52%, tests 28%, transform 18%, worker 2%)
```

`build_06/`: native0,53 modules transformed, source identity unchanged before/
after. The command above used fresh `build_06/assets` instead of `build_02/assets`;
its exact argv is `build_06/invocation.json`. Bundle JS1,208.31kB/gzip318.61kB,
CSS45.22kB/gzip8.78kB; the unchanged greater-than500kB warning remains. Current JS
SHA256=`d9ad6c8b7e2a3f61756985f2b91d28f0826456dab3d6885ef2b1faa1c832406a`;
CSS=`6e746c0ebff28daec2d017605684481d1e030636c9761a018037d0268a359d5a`.
Prior builds and failed browser attempts remain separate evidence, not overwritten.

`frontend/decoder_correction_01/SUMMARY.md` records three native1 **before**
counterexamples and scoped fixes in the two approved new transport files only:

1. A forged R_s=.5 was accepted despite unchanged genuine coefficients/legs.
   The decoder now checks returned coefficient/flux-to-pure-fraction identities,
   independent pure-channel lossless sums and positive-to-zero arithmetic with
   scale-relative tolerances/no absolute floor. It does not solve Fresnel/Snell
   or normalize the received values; raw TIR1+eps remains visible.
2. A reflected frame scaled1+1e-10 with zero-width recentered bounds was accepted
   because uncertainty width was confused with the nominal output allowance.
   Unit/transverse/handedness/direction-frame consistency now uses the unchanged
   nominal128eps policy, independently of1e-8 uncertainty width.
3. Valid individual C-entry intervals of width8e-9 were rejected solely because
   their summed trace interval was1.6e-8. Only the unapproved trace-width ceiling
   was removed; ordered finite enclosure, per-entry widths and all graph/state
   relationships remain enforced. This is a representation-admission correction,
   not numerical output or tolerance relaxation.

Each failed expected-throw/expected-not-to-throw diagnostic remains preserved;
explicit title exclusions are diagnostic selection, not acceptance skips.
`after_final/` runs all67 owned frontend unit cases and
`all15_genuine_resource/` rechecks all15 unchanged genuine DTOs without optical
solves or browser requests. The full installed636-case run above follows them.

The earlier Python4616/one-skip run remains exact evidence for its recorded
source. No numerical implementation changed afterward; a new test's EOF blank
cleanup is AST-identical. The final Python03 result above anchors the current
test bytes; the interrupted02 result is not silently promoted to a pass.

## Independent physical references and scientific controls

`Q/core/README.md` names all actual focused invocations and qualifications.
Latest `core/invocation_08/`: **121 passed in3.21s**, native0:113 new core cases
and8 unchanged W3 architecture cases. The validator's declared10 routes and
seven original weak fixtures pass in `core/validation_02/`, native0. The final
identity replay records unchanged valid wire bytes for five resource scenes;
timing reuse is explicitly distinguished from a new timing measurement.

Independent Decimal90 references use no production scientific helper. They
cover signed/complex coefficients, exact stored-binary64 versus ideal-angle
targets, gauge/world-coherency changes, repeated oblique interfaces, noncoplanar
frames, polarized TIR followed by a phase-sensitive test operator, finite
geometry and accumulated C/frame/point enclosures. The latter operator is a
labelled algebraic validation, not an invented physical receiver/analyzer.
Every relevant reference component must lie in its declared enclosure; an
ordinary absolute tolerance cannot conceal weak-branch loss.

Predeclared metrics: interface atol2e-14/rtol2e-12; conservation abs5e-14;
ordinary accumulated C/power atol2e-13/rtol2e-12; position atol5e-12m/rtol2e-12;
direction/angle atol2e-12/rtol2e-12. All seven original weak amplitudes, powers
and relevant C entries use rtol2e-11/**atol0** with positivity. Original inputs
and criteria were not relaxed. The seven Rp relative errors in the validator
are0 through6.230781757728758e-16. The smallest stored-input labelled-at-atan
case remains Rp=1.3737771894120202e-33, with signed rp=
3.706450039339557e-17; it is not snapped to zero.

Current finite normal slab gives first-interface R=.04,T=.96 and first straight
`r0.T.T`=.9216. The complete finite ledger is:

| Quantity | Actual source-relative fraction |
|---|---:|
| Input |1.0|
| Detected |0.99999999606784|
| D1 incoherent total |0.923076919296|
| R1 incoherent total |0.07692307677184002|
| Stopped/escaped |0.0/0.0|
| Unresolved |3.932160000000004e-09|
| Signed residual |0.0|

Status is **incomplete**. Its17 created branches/15 events/15 segments/9 leaves
follow actual finite receivers and ancestry8. The infinite incoherent slab
series is an independent analytic check, never a replacement for these leaves.
The fixed56-degree Y fixture retains its original receiver positions and
source-frame e1/e2 distinction; representative Rs=.14581593211226546 and
Rp=1.0442342353900138e-5. Equal-index, empty, beam-stop, finite-miss, prism/TIR,
XYZ and explicit root-declared X10/Y25/index1.3 cases retain separate identities.

`core/negative_controls_04/results.json`: all13 deliberately faulted disposable
module copies fail the intended numerical/state/medium assertions (native1),
not setup/import/collection errors. They detect missing flux normalization,
wrong signed rp, weak pruning, unpolarized child reset, lost TIR phase,
double-applied power, missing R traversal, lost queue power, false coherent
receiver addition, infinite-series replacement, wrong reflected handedness,
duplicate terminal power and wrong transmitted medium. Copies are restored;
three production numerical hashes before/after are identical. The original
negative_controls_01 harness import failures(native4) remain **failures**, not
detecting controls; fresh corrected owners02/03/04 do not erase them.

## Backend, transport and owned CPU/resource evidence

`Q/backend/BACKEND_SUMMARY.md` links complete raw focused commands. The initial
43-case transport/tool subset explicitly deselected15 not-yet-ready core cases;
they were included in later integrated runs. Backend full01:306 passed;
full02:307 passed in10.80s. Final affected isolation/architecture subset:22
passed in.69s. All native0. Tests cover all12x12 compute pairs, no-trace
validation while busy, disconnect/cancellation, actual final encoding lifetime,
security/identity/closed responses and independent graph/ledger rejection.
These in-process/server tests do not substitute for actual-browser controls.

Ten genuine encoded samples in `backend/serialized_samples_01/` are3,702–136,363B;
all are strict production replies, not an exhaustive serializer maximum proof.
`core/resources_01/` separately declares five actual long-ID/weak/complex scenes:
maximum138,468B, trace+strict-validation+encoding median44.5799–89.8428ms over
five declared timing samples, Python traced peak1,125,119–1,560,710B. These are
public adapter calls without HTTP. Tracemalloc/native-allocation exclusions and
timing instrumentation prevent whole-process/GPU or browser latency claims.
Final replay reproduced the five exact wires after only invalid-type guards;
the original timings remain qualified reuse, not remeasured final latency.

`Q/frontend/FRONTEND_DELIVERY.md` qualifies `preallocation_final_09/`:15 genuine
DTOs, including32-character IDs, complex TIR and weak powers, decode with no
scientific solve or extra HTTP request. Max genuine numerical record513,176B;
controller metadata peak74,232B.100 passive selections per factory show no
charge growth and disposal returns charges to0. Conservative policy envelope:
2,242,800B persistent/4,455,248B transient, counting retained replacement,
metadata, full1MiB DOM, geometry/labels and transport/preparation overlap.

A separate exact-schema **synthetic resource stress**, not a physically valid
route, has31 branches/32 events/64 segments/16 leaves/four terminators:
276,915B wire,1,438,230B record, projected parse2,227,830B and conservative
4,157,708B persistent/7,360,010B transient. These fit4/8MiB without dropping
certificates. Actual supported convex-body routes have the tighter proved comb
bound. Neither sample arithmetic nor CPU factory charges prove real DOM/heap/
GPU/global usage. Actual browser aggregate16/32MiB counters and release checks
passed under the recorded.47 browser, separately qualified below.

## Preserved failed attempts and corrections

All raw failed/superseded owners remain under Q. No retry count or timeout was
increased to manufacture a pass; in-scope corrections have fresh owners.

- Baseline/frontend startup `spawn EPERM` occurred before tests. The normal
  permission route reran the unchanged installed command; no install/settings.
- Core invocation02:89 passed/3 failed. Two new ownership tests incorrectly
  assumed unpolarized .5 for pure e1/e2; one new architecture check blocked
  required NumPy before its intended assertion. Only those new test assumptions
  were corrected. Later references and the full suite passed.
- First negative-control copy harness omitted repository import ownership and
  exited4. Those failed setup results remain separately classified.
- Frontend generation hit cp950 reading existing UTF8, before selector mutation;
  explicit UTF8 completed the owned work. Early typechecks exposed own mechanical
  name/narrowing/annotation mistakes, corrected only in approved files.
- A new unit fixture echoed old index1 after editing1.2; only its fixture metadata
  was corrected. An outer cp950 console-print failure preserved native child
  results/raw output; later runners use `-X utf8` without persistent changes.
- A genuine transport fixture writer's JSON.stringify discarded signed zero.
  The test now uses the existing canonical stringifyRoutingJSON, retaining the
  production assertion; the genuine signed-zero checks then passed.
- Owned probe root-path/explicit file-list/export-context setup failures and
  preliminary resource formulas remain preserved. Later resource owners count
  actual synthetic64-path geometry, four terminators and long-ID records.
- Build01/full622-unit evidence was superseded by the demonstrated W4
  preallocation correction. Build02/full623-unit results above are the evidence
  for that earlier stage, superseded by build06/full636 above. The original
  greater-than500kB/deprecated-CJS probe warnings
  remain visible; no dependency/configuration suppression followed.

- Browser01/02 numerical assertions passed but review found a blank actual200%
  Playwright screenshot and a real W4 grid defect: both asides were nested into
  the left column while the canvas overflowed. The existing W2/W3 native CDP
  capture path supplies genuine zoom pixels; W4-namespaced wrapper/grid/compact
  controls/header rules fix the actual layout. Earlier pictures/results remain.
- Browser03 caught a genuine785px viewport requirement exceeding769px. After
  scoped layout correction, browser04/05 exposed the new W4 assertion's strict
  `>250` against the unchanged shared250px minimum. The new boundary is now
  `>=250`, consistent with the accepted existing CSS; all original tests and
  other geometry/root-overflow/numeric assertions remain. Exact before/after
  source and reason are in `layout_boundary_correction.json`.
- The first C01 controlled invocation stopped the matrix on two overlapping
  browser network notifications. Those events were not actual simultaneous body
  readers. The new W4 test now journals network events and instruments actual
  getReader/releaseLock ownership, asserting one pending reader and one latest
  coalesced validation. `browser_read_and_capture_correction.json` preserves the
  failed observation and correction. No old helper/assertion, production worker,
  timeout, retry or forced click was changed to manufacture a pass.
- The three native1 decoder counterexamples above remain under their own owners.
  The matrix stopped before old136 execution; fresh full frontend gates/build06
  and frozen matrix07 follow the corrections rather than erasing the stop.
- `recording_review_01/` preserves a failed owned frame-extraction helper:
  installed Playwright ffmpeg lacks the fps filter. The first wrapper exit1 did
  not record a native ffmpeg status and is not a successful extraction. No tool
  was installed. `recording_review_02/` uses supported input seeking and records
  seven native0 extractions at3/8/14/20/26/33/40s, proving the original video hash
  unchanged. Sampled-frame review is not continuous manual playback.

## Recorded production-browser acceptance and identity qualification

Fresh installed discovery/freeze07 bound160 invocations/134 distinct IDs, exact
candidate/test/fixture/source/assets, original Chrome156.0.8078.47, workers1,
retries0 and expected skips0. Browser07 used source-hashed build06. Preserved
old fixtures/tests and the original bounded one-response capture are unchanged.
No second-request substitution, forced click or retry-until-green was used.
All160 conditions passed, required skips/unexpected/flaky results/retries0:

| Group | Passing invocations |
|---|---:|
| W4 layout |1|
| W4 controls |13|
| W4 ordinary |10|
| W3 |20|
| W2 |23|
| W1 |12|
| Legacy |55|
| English |7|
| Legacy controls |19|

The24 W4 conditions cover normal/56-degree/polarized TIR/XYZ results, raw
original response versus full attached DTO, stale invalid edits/event IDs,
camera/selection/scroll no-compute, old navigation/documents, real context loss,
three desktop sizes1366×768/1440×900/1920×1080 and actual200% browser zoom.
Controlled checks cover all12 contenders through actual compute/final encoding
after disconnect, foreign workers, single-flight body-reader ownership/latest
validation, eight original-response transport faults and display-only recovery.
Each owned service exited native0 and left8510 free;8501 was untouched.

`bridge_02_results/results.json` compares19 genuine browser07 original replies
against public offline adapter runs using each captured scene/UUID/digest:
all original bytes match exactly, no complete DTO difference, and independent
Decimal90 intersections/directions/media/frames/C/signed-complex amplitudes,
enclosures and terminal ledgers pass. No added HTTP. Bridge01/build05 remains
earlier qualified evidence; bridge02 belongs to unchanged build06, not another
browser submission or substitute capture.

B08 mixed-mode app-owned retained bytes:10,236,694 before Release,974,880 after.
W4 before-release963,436B consists of numerical508,140B, rendering387,574B
(including measured DOM291,744B) and state67,722B. Seven deliberate calls are
W4,V0,W1,R03,W2,W3,W4; passive inspection/release make no scientific request.
Counters are not RSS/whole heap/GPU. Worker/read controls verify reservation
lifetime through actual settlement; global16/32MiB caps are unchanged.

### Final normal-speed recording; original failure preserved

The original B11 test passed four deliberate traces over42.007s of actions and
a42.6s container. Its observed HTTP+decode252.8ms, decode12.3ms/attachment15.1ms
and120 RAF intervals(min3.9/median4.2/max12.6ms) remain that original sample,
not new latency measurements. However, visual review found first.9216 leaf and
unresolved readouts below the viewport despite correct DOM assertions.
`recording_visual_review_01/review.json` preserves that **visually incomplete**
recording and before-test source; it is not accepted by duration or machine pass.

After all160 finished, `recording_visibility_correction_01/correction.json`
records only B11 passive scrolling/inspection and final Focus. All original
assertions, four intentional traces and42s target remain; other case functions/
shared helpers have byte-identical prefix/suffix proofs. Production sources and
build06 assets are unchanged. Fresh discovery/freeze08 then ran exactly one
affected B11 in `browser_recording_final_01/`: native0, skips/retries0, own cleanup
native0/free8510. This is161 native0 invocations total. The160 original records
retain freeze07 identities; no full matrix run under the new whole-file hash is
claimed, and no unrelated build/unit rerun is substituted for the scoped proof.

The [final genuine original42.64s video](../../../runs/w4_fresnel_implementation_01/browser_recording_final_01/browser/custom_w4_evidence_dir/8b566f20f7286df9fa1230d6/recording/page@4147f7b6783c4bc00c9317780babea57.webm)
has SHA256 `848c387aae9d17c5ae97e07664e4d59a7bb39ea5562ebcd1fcd469620bdad39d`.
Actions42.006s; four explicit traces;120 RAF intervals min4ms, median
4.200000000000728ms, max8.5ms. These are scoped headless observations, not physical
display FPS, GPU timing or universal performance. No speed editing or image
generation was used. `recording_visual_review_02/review.json` records review of
eight original-video frames and two genuine screenshots: normal local R/T,
complete unresolved3.932160000000004e-9/signed residual0, selected first leaf
Power/Source.9216,56-degree stale/recompute/e1/e2, TopView and focused TIR state.
The rightmost terminal-table cell uses local horizontal access; a clipped cell
is not claimed fully visible in its static frame. This engineering inspection
is not continuous manual playback or **user visual acceptance**.

The three approved handoff figures are byte-identical genuine browser07 B01/02/03
captures, with source/target/reply/digest/build receipts in
`figure_sources_01/manifest.json`. They were visually inspected; no edited,
generated, planning mockup or placeholder substitutes were used.

### Resumed2026-10-29 tool drift and final preservation

`resume_preservation_01/summary.json` retains overall **FAIL**: installed Chrome
externally changed156.0.8078.47→156.0.8078.48. Exact frozen executable SHA256
`10d6ee85be41b8b87be6c99a4c4c60c017416a35669f660b5c748b6103a1ec50`
differs from installed `480f275b63d1ea39113cbc8344ac395578acc25b432bd39af5fbc77005179aca`;
both are4,522,648B. `chrome_version_drift.json` records read-only version metadata;
the newer executable was not launched. **Newer-browser acceptance: NOT_RUN.**
No rollback, installation, browser substitution, configuration change or new
browser acceptance was performed. The original strict summary helper/FAIL remain
preserved; this mismatch is not relabelled as current full-freeze success.

The separate read-only `final_acceptance_summary_01/summary.json` exits0 and is
classified `RECORDED_BUILD06_ACCEPTANCE_VERIFIED_WITH_CURRENT_BROWSER_DRIFT`:
it verifies all160+1 original.47 receipts/cleanup, B11-only proof, native gates,
19 original response references and three genuine figures without new HTTP or
browser runs. `current_freeze_comparison=FAIL_SINGLE_DOCUMENTED_BROWSER_DRIFT`;
`newer_browser_acceptance=NOT_RUN`. Its `SUMMARY.md` is a human-readable index,
not authority to change those statuses or publish.

The resumed comparison confirms all189 other frozen source/test/tool identities,
52 build sources/three assets,20 explicit inputs/six helpers,493 protected tracked
files,163 immutable plan files,53 Python distribution metadata trees and7
installed frontend manifests unchanged. Exact47-path scope, baseline main/HEAD/
upstream and empty index also match; approved files/index were stable during the
read-only check. Final Python03 followed that preservation check. Final complete
47-path diff/raw preservation export follows these documentation edits and is
supplied separately for review; its result is not assumed from the earlier audit.
All failed/superseded/interrupted evidence remains preserved. Stop at the user's
visual-review checkpoint; no stage, commit, push or later milestone.

## 2026-10-29 — new Chrome .48 closeout qualification

This is an appended qualification of the approved narrow copy correction. All
earlier checkpoint text, captures, native failures and unknown statuses remain
verbatim history. Let U=`runs/w4_closeout_chrome48_01/`; original Q and immutable
planning P retain their meanings above. `U/preedit_export_01/` preserves the full
47-path candidate before editing, including new files and approved PNG bytes.
`U/preflight_index_01/summary.json` links the original inventory/acceptance and
environment records. `U/historical_identity_02/summary.json` verifies163 planning
files and16,130 original implementation-evidence files; the earlier ordinary-path
scan FAIL and its Windows long-name/key-spelling diagnosis remain preserved.

### Exact scope and newly executed unit/build work

`U/copy_correction_01/receipt.json` identifies exactly three changed files relative
to the accepted candidate: `fresnel_routing_panels.ts`(two visible/aria labels),
`fresnel_routing_panels.test.ts`(one actual-editor binding/passive assertion), and
existing B01 in `fresnel_routing.browser.spec.ts`(same title/assertions plus copy,
visible first leaf versus receiver total, nonzero unresolved and incomplete).
The input IDs `w4-exterior-index`/`w4-interior-index` still bind to
`exterior_medium.refractive_index`/`bodies.0.interior_medium.refractive_index`.
No scientific key/value, request, capture helper, tolerance, fixture, timeout,
retry or launch policy changed. Remaining44 candidate files were unchanged
before the separately authorized append-only handoff additions.

Actual commands from `frontend/bench`, via installed npm, are `npm run typecheck`
and `npm run test:unit`. Native0 output is preserved unedited in
`U/gates/typecheck_01/` and `U/gates/frontend_unit_01/`. The latter reports:

```text
 Test Files  39 passed (39)
      Tests  637 passed (637)
   Duration  12.80s (import 48%, tests 28%, transform 21%, worker 3%)
```

`U/precommit/build01/` preserves native1 `spawn EPERM` during Vite's process
creation. No dependency/config/source/environment repair followed. The normal
permission invocation `U/gates/build_precommit_permission_02/` runs the same owned
verified build command into fresh `U/precommit/build02/`: native0, frontend and
Python sources stable, environment unchanged. Source/served assets are bound by
`precommit/build02/source_asset_identity.json`; the existing large-bundle warning
remains visible. Exact build argv/stdout/stderr/results are retained there and
under U/gates; there is no assumption of the earlier636-case count.

### Declared current-browser selection and native environment proof

Before the first browser acceptance or commit, `U/DECLARED_GATES.json` binds the
new approval, correction, exact selection/exclusions and fresh installed
discovery/freeze. **39 precommit conditions/30 distinct IDs** are requirement
derived: W4-B01…B10; C01; C02; C03 with sequential and W3 held-worker conditions;
C04 DOM preparation plus eight transport faults; seven English old-mode/R03/W1/
Unicode-document cases; representative W2/W3 and W1.1 linked-layer cases; genuine
v1 sequential/two-path/polarization and v2 analyzer-enabled/disabled file
portability; production V0/local-assets smoke. Required skips/retries0/workers1,
existing fixture/timeout/capture policies unchanged. All three desktop sizes and
actual200percent zoom remain in B10; both common-gate directions, twelve
contenders and actual final-encoding disconnect remain in the W4 controls.

The121 nonselected historical per-condition invocations have exact IDs,
candidate/harness/input/environment dependencies and rationale in
`U/selection_preparation01/historical_exclusions.json`. They remain .47 history,
not fresh .48 passes. A new full-length B11 recording is expressly unnecessary;
the42.64s .47 original remains unchanged and does not demonstrate .48 compatibility.

New invocation environments use only child-local `DEBUG=pw:browser,pw:protocol`.
Unchanged installed Playwright's native startup `Browser.getVersion` response
supplies actual launched version; preserved logs also bind executable, launch
arguments/PID and available renderer/environment information. No NODE_OPTIONS,
Playwright hook, capture-method change, browser installation/profile change or
parent/persistent environment mutation was used. Per-invocation pre/post
executable/tool hashes and actual runtime responses must all remain authorized
Chrome156.0.8078.48, including B10's extra zoom launch. Unavailable renderer fields
are NOT_REPORTED, never inferred physical GPU behavior.

Actual `U/precommit/browser01/result.json` records **39 passed conditions/
30 distinct IDs**, required skips/retries0, workers1. All40 native Chrome
launches(including B10's additional actual-zoom launch) report156.0.8078.48.
Each owned service exits native0 and leaves8510 free;8501 was not contacted or
changed. `U/ENVIRONMENT_TRANSITION_PRECOMMIT.json` binds the new approval, old.47
evidence/drift/FAIL, actual current invocations and per-invocation environment
records. Current executable is
`C:\Program Files\Google\Chrome\Application\chrome.exe`, SHA256
`480f275b63d1ea39113cbc8344ac395578acc25b432bd39af5fbc77005179aca`;
Nodev24.15.0, Playwright1.63.0 and Python3.11.9 use their existing installations.
No browser rollback, install or settings change occurred.

Genuine fresh.48 screenshots are under
`U/precommit/browser01/w4_ordinary/W4-B01/browser/custom_w4_evidence_dir/2740e0ce5c9c5327d834fcfd/`:
`corrected_refractive_index_inspector.png`, `normal_slab_interface.png`,
`normal_slab_incomplete_ledger.png`, `normal_slab_first_leaf.png` and
`normal_slab_receiver_total.png`. TIR is
`U/precommit/browser01/w4_ordinary/W4-B03/browser/custom_w4_evidence_dir/2f454df556aca3374bc44811/tir_carried_polarization.png`.
These show actual returned values and current copy; none overwrites the.47
captures or claims a new full-length recording.

### Genuine .48 response/reference and reuse qualification

`U/precommit/bridge_complete02/results.json`: **PASS**,15 captures discovered/
checked,15 offline public-runner calls, exact original bytes equal, no complete
DTO difference, unchanged independent Decimal90 checks all passing, source
unchanged and0 added HTTP. This complete proof includes13 ordinary replies plus
two B10 desktop/actual-zoom replies. Initial `bridge01/` remains a valid13-reply
ordinary subset; complete02 adds the layout captures offline without rerunning
the browser or erasing the subset's provenance.

The new B08.48 mixed-result measurement is10,236,662B before explicit Release,
974,880B after; W4 before-release ownership is963,466B. Available actual renderer
identification for this sample is Google Inc.(Intel),
`ANGLE (Intel, Intel(R) Graphics (0x00007D67) Direct3D11 vs_5_0 ps_5_0, D3D11)`,
WebGL2.0(OpenGL ES3.0 Chromium). Other unavailable per-invocation renderer fields
remain NOT_REPORTED. The earlier.47 ownership numbers stay unchanged above.

These are new .48 replies from the actual submitted scene/UUID/digest, with the
unchanged bounded original-response capture. Offline public-runner byte replay
and unchanged independent Decimal90 references compare complete data without
second optical HTTP requests. Screenshots/HTTP200 alone are not numerical proof.
The DOM-fault condition separately preserves original genuine numerics and manual
display-only recovery. Current app-owned counters and release are scoped to
their actual browser observations; global16/32MiB/local4/8MiB budgets are unchanged
and are not whole-process/V8/GPU memory measurements.

The earlier successful Python03 command/output(**4616passed,1skipped in312.60s**),
same Windows symlink explanation, Decimal90 cases, seven unchanged weak fixtures
and13 detecting controls are **reused**, not newly run here. Scientific/core and
Python-test sources, inputs/settings, interpreter/distribution metadata and
protocol/budget identities are verified through the new raw preflight/build/
freeze receipts; the final full preservation audit is still required before staging. The label-only production file
and two test files are explicitly different; no blanket byte-identical source
claim is made. Python02 remains UNKNOWN and the original .47→.48 strict identity
comparison remains FAIL. New .48 approval/results form a separate transition.

### Conditional publication boundary at this checkpoint

The exact **21-condition clean-postcommit slice** was declared before commit:
W4-B01/B02/B03/B07/B08 plus the same16 compatibility/publication cases. From the
clean single commit it requires a fresh owned build/discovery, actual Python
source and served HTML/JS/CSS hashes, still-.48 runtime, genuine normal/polarized/
TIR response references, copy/incomplete ledger, old modes/documents and normal
owned cleanup. No postcommit pass/push is claimed by this precommit handoff.
Required failure, changed browser identity or advanced remote parent stops push;
no amend, automatic retry, fixture change or weakened assertion is authorized.
Final immutable postcommit/commit/push/three-SHA synchronization receipts are
kept under ignored U and reported at actual closeout, without a second commit
solely to predict or rewrite this checkpoint. All historical evidence survives.
