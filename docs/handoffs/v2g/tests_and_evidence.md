# V2g tests and reproducible evidence

Fresh append-only evidence root: `runs/v2g_acceptance_20261014_01/`.
Commands run from `C:\holographiclab` with the existing
`C:\holographiclab\.venv\Scripts\python.exe`. Node is the existing
`C:\Program Files\nodejs\node.exe`; frontend commands run from `frontend/bench`.
No package, lockfile, persistent environment or global configuration change.

## Preconditions and fresh unchanged baselines

Accepted baseline `431346c16e7275f2a4d6798c6efbf689b0056e91`: clean main,
upstream origin/main, synchronized with live remote. Inventory339 tracked
files,53 installed Python distribution version/path/metadata records. Frozen
exact46-path scope and Windows identities are in `frozen_scope01.json`;323
pre-existing files outside the16 permitted modifications remain protected.
Planning inventory SHA-256:
`323a1c02bcadf9f86c694fa8dbc0d2aead07b0ac921ec54c36761eeb7db470bf`.
Planning text SHA-256:
`f2d386ddf9caac2ca4b707b3c5963b3585f640a3ee78a73bd9067bc8a8328bff`.
Neither planning file is modified to authorize paths.

Actual command (read-only baseline, cache and bytecode disabled):

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider --basetemp C:\holographiclab\runs\v2g_acceptance_20261014_01\baseline_tmp -rs
```

Exact final output lines; the complete unedited stream is `baseline_stdout.txt`:

```text
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
2942 passed, 1 skipped in 211.47s (0:03:31)
```

Exit0, empty stderr. The skip remains; no privilege change or assertion edit.
Installed frontend commands:

```powershell
& 'C:\Program Files\nodejs\node.exe' node_modules/typescript/bin/tsc --noEmit --incremental false
& 'C:\Program Files\nodejs\node.exe' node_modules/vitest/vitest.mjs run --cache=false --configLoader native
```

Typecheck exit0/no output. First unit attempt `frontend_unit01_*` failed to
spawn workers with EPERM,14 harness errors and no tests. Normal permitted
retry `frontend_unit02_*` retained identical assertions and passed:

```text
 RUN  v5.0.3 C:/holographiclab/frontend/bench

 Test Files  14 passed (14)
      Tests  222 passed (222)
   Start at  13:03:31
   Duration  4.43s (import 56%, tests 20%, transform 20%, worker 4%)

    Isolate  14 workers spawned · ~159ms startup each (spawn + environment, per file)
             at least ~2.07s faster with isolate: false — reuses workers across files instead of one per file
```

The earlier planning worker-spawn failure remains separately under
`runs/v2g_planning_20261014_01/frontend_unit01_*`; it is not a product/test pass.
A pre-edit fixture helper initially lacked the repository import path;
`preflight_helper_failure.json` records that orchestration error. A separate
continuation added the helper's path and captured six untouched v1 fixtures in
`legacy_v1_before/`. Their canonical bytes/digests are frozen before source
edits and are never regenerated as compatibility expectations.

`opening_contract_record.json` records that the complete normative application
handoff existed while every new executable was still absent. Its opening
SHA-256 was `26508a2fdbcaa27b9630dd779f82495875cfffb13b58042a93559fc940d7e4f3`.

## Evidence interpretation

Direct-public checks compare complete received float64 image/axis bytes and
all scalar checkpoints/history/analyzer records with identical public calls on
this platform. They establish application fidelity, not independent optical
accuracy. Literal Jones/port and bounded finite-sum references form a separate
analytic layer with unchanged explicit tolerances. Browser screenshots show
actual application presentation; they do not replace complete-array checks.
Production, controlled failure, isolated production mutation and reference
self-check results are reported separately. Setup/import/permission failures
are not scientific fault detections. Settings success does not certify a later
numerical solve or qualified replay.

Final acceptance captures and measured outcomes are appended below only after
execution. Precommit validation and later clean-postcommit/publication records
remain distinct; no future gate is claimed on the strength of this baseline.

## Final precommit acceptance — executed 2026-10-14

The explicit one-path amendment is recorded separately in
`approved_scope_amendment01.json` (SHA-256
`cf371e1e5eaba6346744a2a459a83879f4520e106d9d08d351fd16036f5d46aa`).
The original planning files retain their opening hashes. Final scope is47 paths:
17 modifications,30 creations,322 protected pre-existing tracked files. Exact
final list appears below. The sole additional file change is the one-line real
file-controller filename guard; its real Blob/URL regression is in an already
approved new document test. No filename alias/wrapper bypass was introduced.

Final restored Python command, exit0/empty stderr:

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider --basetemp C:\holographiclab\runs\v2g_acceptance_20261014_01\full_python03_restored_tmp -rs
```

Complete unedited stdout (`full_python03_restored_stdout.txt`):

```text
........................................................................ [  2%]
........................................................................ [  4%]
........................................................................ [  6%]
........................................................................ [  8%]
........................................................................ [ 11%]
........................................................................ [ 13%]
........................................................................ [ 15%]
........................................................................ [ 17%]
........................................................................ [ 19%]
........................................................................ [ 22%]
........................................................................ [ 24%]
........................................................................ [ 26%]
........................................................................ [ 28%]
........................................................................ [ 31%]
........................................................................ [ 33%]
........................................................................ [ 35%]
........................................................................ [ 37%]
........................................................................ [ 39%]
........................................................................ [ 42%]
........................................................................ [ 44%]
........................................................................ [ 46%]
........................................................................ [ 48%]
........................................................................ [ 51%]
........................................................................ [ 53%]
........................................................................ [ 55%]
........................................................................ [ 57%]
.....s.................................................................. [ 59%]
........................................................................ [ 62%]
........................................................................ [ 64%]
........................................................................ [ 66%]
........................................................................ [ 68%]
........................................................................ [ 71%]
........................................................................ [ 73%]
........................................................................ [ 75%]
........................................................................ [ 77%]
........................................................................ [ 79%]
........................................................................ [ 82%]
........................................................................ [ 84%]
........................................................................ [ 86%]
........................................................................ [ 88%]
........................................................................ [ 91%]
........................................................................ [ 93%]
........................................................................ [ 95%]
........................................................................ [ 97%]
........................................................................ [ 99%]
...                                                                      [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
3242 passed, 1 skipped in 331.13s (0:05:31)
```

Final installed frontend typecheck (`final_typecheck02_*`) exit0/empty streams.
Final restored units use the same installed command as baseline; exit0/empty
stderr. Complete unedited stdout (`final_units03_restored_stdout.txt`):

```text

 RUN  v5.0.3 C:/holographiclab/frontend/bench


 Test Files  18 passed (18)
      Tests  304 passed (304)
   Start at  13:59:23
   Duration  5.07s (import 67%, tests 16%, transform 15%, worker 2%)

    Isolate  18 workers spawned · ~121ms startup each (spawn + environment, per file)
             at least ~2.06s faster with isolate: false — reuses workers across files instead of one per file
```

`production_build03_*` built30 modules into fresh owned
`runs/v2g_acceptance_20261014_01/dist_precommit03/`, preserving the existing dist.
Vite's unedited large-chunk warning is retained; no chunk threshold, dependency,
lockfile or build setting was changed to suppress it. Actual JS831.91kB and
CSS11.27kB are build output sizes, not resident-memory measurements.

### Current acceptance layers and actual outcomes

| Layer | Current result | Raw evidence |
|---|---|---|
| New HTTP/public integration |9complete single fixtures,5actual17-point sweeps; exact full arrays/axes/scalars; genuine analyzer-underflow422 after raw-only runner success | `production_api04_final.json`, matching command/streams/exit and complete `_frames/` |
| Legacy HTTP |10sequential;18two-path plus3sweeps;28Jones plus3sweeps; unchanged acceptance functions | `legacy01_v1_api.json`, `legacy01_v2b_api.json`, `legacy02_v2d_api.json` |
| Legacy documents |3mode API and genuine fresh-session browser full-array/scalar checks | `legacy_documents01/`, `legacy_documents_browser02/` |
| Unchanged legacy browser |33passed,6controlled-only skips,3.2min | `browser_legacy02_*` and owned output |
| Current new ordinary browser |10passed,2controlled-only skips,44.5s; includes enabled/disabled fresh-context portability and release/budget/context recovery | `browser_v2g03_*`, `browser_v2g03/`, `browser_v2g_documents03/` |
| Separately controlled HTTP |6first/interior/final failure cases (0/8/16, numerical/unexpected) and2first/second analyzer failures; exact calls, genuine prefixes, terminal gate and explicit recovery | `controlled_api01/summary.json` |
| Separately controlled browser |8selected passes:2actual held/disconnected new workers and6failed prefixes; all7valid contenders409, validation and v1/v2documents responsive | `controlled_browser01/summary.json` |
| Unit production-copy faults |26/26named detections:17Python+9frontend; every original0 -> intendedfault1 -> exactrestore0 | `negative_controls02/summary.json` and78 raw subprocess captures |
| Actual production-main browser-copy faults |3/3named detections: retained buffers, obsolete callback, useful-document disposal; original0 -> fault1 -> exactrestore0; restored served build bytes identical | `browser_main_controls01/summary.json` and9owned phase captures |
| Independently decoded browser frames |36complete new frames compared to identical public source/Jones/V2f/analyzer calls, including genuine portability, held recovery and copied-main variants | `browser_full_public_fidelity01.json` |
| Source/environment audit |47exact pending paths,322protected byte-identical files;53Python records/388recursive metadata files and7frontend metadata files unchanged; declarations/lock unchanged | `scope_environment_audit01.json`; root repeats at staging |

The six ordinary legacy skips are: V1actual disconnect; old document held-worker
Apply; old Jones partial and disconnect; old two-path partial and disconnect.
They are explicitly controlled-only cases, not unexecuted ordinary assertions.
The two new ordinary skips are partial-prefix and held/disconnect tests; their
separate six/two runs above pass. These counts are separate and are not summed
into a misleading single suite total. The Windows symlink skip remains unchanged.

All original old scientific/browser/document acceptance assertions remain
unchanged. Only the two approved old architecture guards receive exact public
import permissions plus explicit forbidden new numerical calls from documents.
The full seven-by-seven gate matrix, same-kind/cross-kind cases, analyzer/encoding
lifetime, disconnect/cancel/submission/worker failures run in Python without a
listener. Backend worker completion, not HTTP waiter lifetime, owns the gate.

HTTP evidence invokes the unchanged old acceptance functions. An ignored
`AssetRoot` harness redirects only their local dist-file lookups to the owned
production assets; it does not change numerical source or assertions. Original
legacy source hashes and served bytes are recorded. All36 new browser frames
are independently decoded outside the app; complete arrays are present in raw
binary captures, not inferred from screenshots or rounded text.

### Independent mathematics and measured limits

The unchanged V2f literal Jones/port, complete bounded finite-sum and weak
references passed separately from direct-public equality. Actual maxima:
- ordinary complex error/Ain:3.376611507232129e-16;
- output fraction absolute error:6.661338147750939e-16;
- analyzer fraction absolute error:2.220446049250313e-16;
- direct-sum complex error/Ain:7.783100087124842e-16;
- direct norm error/Nin:4.042360219746071e-16;
- selected near-dark relative error:9.466330862652152e-16;
- literal block unitarity maximum absolute error:2.220446049250313e-16.

Tolerances are unchanged and input-scaled as documented in `math_used.md`.
This is finite discrete-model evidence, not continuum/vector electromagnetic
accuracy. The smaller-quadrature limitation remains. Both0/2*pi endpoints were
calculated independently: identical-arm output1 norm differed by
3.2816613657194084e-40; asymmetric output norms differed by
[-5.169878828456423e-26,1.2924697071141057e-26]. Orthogonal and zero fixtures'
reported endpoint norms matched exactly on this run; no universal exact-periodicity
claim follows. Finite sampled extrema are not continuous visibility.

Actual128x128 disabled/enabled payloads were264192/526336 bytes, complete frames
266728/529624 bytes, unpadded headers2517/3266 bytes, below the declared
280592/542736 and padded-header16384 caps. Actual asymmetric header was4169
bytes. Closed descriptors, ordered roles, bool/type/finiteness, little-endian
payload, shape/offset/length/padding/maxima, identities and conditional analyzer
agreement are separately covered by adapter/protocol/frontend tests. Complete
public scalars use typed comparisons; False cannot pass as numeric zero.

Single source/Jones/runner/analyzer counts are1/1/1/(0or2); enabled sweep counts
are1/1/17/34. Controlled analyzer0/1 failures attempt1/2 analyzers after one
successful runner and publish no raw-only success. A genuine public norm-underflow
fixture also fails atomically; no tolerance change, component deletion or retry.
Display failure after successful measurement is distinct and explicitly retryable
without optics. Controlled DOM, second-screen map and readout mutation-then-throw,
fourth-canvas failure and measured oversized geometry all preserve/restore whole
presentation; actual WebGL loss/restoration and explicit presentation retry pass.

### Fixed-budget production observation and release

The genuine all-mode run retained four actual numerical results and three scalar
sweeps. It also retained a successful new numerical completion whose later
presentation exceeded the fixed budget; this is reported separately from a later
EARLY admission rejection. Before that next rejected attempt, app-owned ledger:
scientific11,443,866;canvas2,097,152;geometry8,376;total13,549,394 bytes. The next
admission rejected before HTTP, preserving every owner and making no automatic
retry. No limits were raised and no results were silently evicted.

After preparing a useful document, total was13,551,702 bytes including2,308 document
bytes. Explicit all-mode release left scientific/canvas/texture/trajectory bytes0,
geometry8,376 and documents2,308, total10,684, one live control owner and unchanged
camera. Every valid/invalid draft, revision, attachment identity, stable IDs/order,
metadata, preview/prepared URL and subsequent download behavior remained. No
scientific or document request occurred during release; repeated release is
harmless. A later deliberate512two-path simulation succeeded, total8,423,868 bytes.
These are declared app-owned buffers/logical charges, not Chrome process memory
or synchronous garbage collection. Fixed budgets remain16MiB persistent/32MiB
transient. Controlled budget/unit fixtures are distinct from this production run.

### Portability, screenshots and failure provenance

For both analyzer-enabled and analyzer-disabled nondefault angle settings, a real
new-mode download was followed by closing the original context, moving/renaming
the actual file, opening a fresh storage-isolated context, authoritative two-stage
preview and acknowledged Apply with zero optics, then deliberate recomputation
under a fresh UUID. Complete scientific definitions/nonzero bits, full received
arrays, axes, checkpoints, ratios and canonical reexport match. Enabling analysis
after the disabled import uses its preserved0.6100000000000001rad angle. Metadata
remains literal. Result release preserves both preview and useful download.

The three genuine inspected PNGs are byte-identical copies from`screenshots02/`;
`genuine_screenshots01.json` records source, dimensions, sizes and hashes. They
show four raw/analyzed roles at one scale, an actual complete17-point sweep and
fresh-context v2 restored-unsimulated settings. They are not generated optics,
old screenshots or numerical correctness evidence by themselves.

Preserved attempts/corrections, never relabeled as passes:
- baseline/focused unit worker EPERM and original planning failure, followed by
  normal permitted worker execution with identical assertions;
- `backend_focused01_*`:314pass/10new-reference-fixture failures; corrected only
  omitted inherited arm1HWP and phase-zero real weak fixture, unchanged tolerances;
- frontend generic/readonly test type errors and one new expected-diagnostic
  mismatch; corrected within approved new implementation/tests;
- `legacy_api01_*`:an evidence AssetRoot path-like reporting error after old
  assertions; added helper `__fspath__`, reran unchanged Jones acceptance;
- `browser_legacy01_*`:32pass/1Chrome response-body capture error/6controlled
  skips; fresh unchanged assertion run02passed33/6;
- `browser_v2g01_*`:4pass/6fail/1controlledskip. The real filename guard conflict
  caused the explicit one-path amendment. Separate controls captured the WebGL
  extension too late, consumed a scene fault before the intended new commit,
  and expected late HTTP instead of the observed early budget rejection. The
  corrected fixtures still require their intended failures and whole rollback;
- `negative_controls01/`:25/26classification gate; last actual assertion detected
  the disabled angle but the harness expected the wrong marker. Corrected only
  its declared marker, fresh26/26 run02; no weakened assertion;
- owned-service cleanup initially saw a restricted process-query false absence.
  Verification of known launcher/runtime PIDs under normal permission corrected
  it; only exact task-command processes were closed. All raw helper captures remain.

No Conda/WSL/environment rebuild, pip/npm install, dependency/lock upgrade, global
Git/profile/pip settings, TLS/proxy workaround or unrelated service/port8501 action
occurred. Process-specific evidence environment mappings are copies; parent and
persistent settings are unchanged. Scientific source/tests/math/exports, M5,
Streamlit, instructions and historical evidence remain byte-identical.

### Reproduction and terminal publication gate

From`frontend/bench`, installed tools:

```powershell
& 'C:\Program Files\nodejs\node.exe' node_modules/typescript/bin/tsc --noEmit --incremental false
& 'C:\Program Files\nodejs\node.exe' node_modules/vitest/vitest.mjs run --cache=false --configLoader native
& 'C:\Program Files\nodejs\node.exe' node_modules/vite/bin/vite.js build --outDir C:/holographiclab/runs/NEW-V2G-OWNED-DIST --emptyOutDir
```

Use a fresh resolved task-owned output; never empty an unverified directory or
replace assets used by another service. Normal user launch builds default dist
and invokes the existing server entry as documented in README. This acceptance
uses ignored`manage_service.py` only to bind an owned fresh asset root through
existing`create_app/main`, record imported source/HEAD/assets and close verified
launcher/runtime PIDs. Controlled scripts are passive on import and are never a
production fallback or fault endpoint. Fixed127.0.0.1:8510 occupancy is a blocker.

With an explicitly owned service running, from repository root:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 scripts/validate_v2g_bench.py --assets-dir runs/NEW-V2G-OWNED-DIST --output runs/NEW-V2G-API.json
.\.venv\Scripts\python.exe -B -X utf8 scripts/v2g_negative_controls.py --output-dir runs/NEW-V2G-CONTROLS
```

Actual browser command uses installed`node_modules/@playwright/test/cli.js test`
with fresh child-only V2G_EVIDENCE_DIR, V2G_DOCUMENT_EVIDENCE_DIR and V2G_FIGURE_DIR;
exact argv/cwd/overrides/streams/exits are in capture files. New controlled runs
also set V2G_PARTIAL_EVIDENCE or V2G_HELD_DIR/OPERATION and select one gated test.
`controlled_browser_batch.py` and`browser_main_controls.py` contain the executed
bounded recipes; the latter builds only isolated frontend copies. No installation
or network asset retrieval is part of a reproduction command.

Precommit gates above are executed. One approved commit is next, followed by a
fresh clean-postcommit owned build, source/served-asset check, all-four-mode smoke,
new real single/17-point sweep, fresh-context v2 portability/recompute, v1behavior
and release/deliberate recompute. Push is forbidden until those later checks pass.
Postcommit/publication records remain in fresh ignored captures and completion
report, not a predicted tracked claim or amended commit. No later stage starts.

### Exact final amended path inventory

1. `README.md`
2. `docs/roadmap.md`
3. `docs/milestones.md`
4. `apps/virtual_bench/server.py`
5. `apps/virtual_bench/experiment_documents.py`
6. `tests/test_virtual_bench_architecture.py`
7. `tests/test_virtual_bench_document_architecture.py`
8. `frontend/bench/src/main.ts`
9. `frontend/bench/src/scene.ts`
10. `frontend/bench/src/styles.css`
11. `frontend/bench/src/state.ts`
12. `frontend/bench/src/two_path_state.ts`
13. `frontend/bench/src/polarization_state.ts`
14. `frontend/bench/src/polarization_display.ts`
15. `frontend/bench/src/experiment_documents.ts`
16. `frontend/bench/src/experiment_document_state.ts`
17. `frontend/bench/src/experiment_document_files.ts`
18. `apps/virtual_bench/polarized_two_path_adapter.py`
19. `apps/virtual_bench/polarized_two_path_protocol.py`
20. `tests/test_virtual_bench_polarized_two_path_adapter.py`
21. `tests/test_virtual_bench_polarized_two_path_protocol.py`
22. `tests/test_virtual_bench_polarized_two_path_server.py`
23. `tests/test_virtual_bench_polarized_two_path_architecture.py`
24. `tests/test_virtual_bench_polarized_two_path_analytic.py`
25. `tests/test_virtual_bench_polarized_two_path_documents.py`
26. `frontend/bench/src/polarized_two_path_contracts.ts`
27. `frontend/bench/src/polarized_two_path_state.ts`
28. `frontend/bench/src/polarized_two_path_presets.ts`
29. `frontend/bench/src/polarized_two_path_display.ts`
30. `frontend/bench/tests/polarized_two_path_transport.test.ts`
31. `frontend/bench/tests/polarized_two_path_state.test.ts`
32. `frontend/bench/tests/polarized_two_path_display.test.ts`
33. `frontend/bench/tests/polarized_two_path_documents.test.ts`
34. `frontend/bench/tests/polarized_two_path.browser.spec.ts`
35. `frontend/bench/tests/polarized_two_path_documents.browser.spec.ts`
36. `scripts/validate_v2g_bench.py`
37. `scripts/v2g_negative_controls.py`
38. `scripts/v2g_controlled_acceptance_server.py`
39. `docs/handoffs/v2g/implementation_summary.md`
40. `docs/handoffs/v2g/code_map.md`
41. `docs/handoffs/v2g/math_used.md`
42. `docs/handoffs/v2g/tests_and_evidence.md`
43. `docs/handoffs/v2g/known_limitations.md`
44. `docs/handoffs/v2g/tutor_context.md`
45. `docs/handoffs/v2g/figures/fig01_raw_and_analyzed_outputs.png`
46. `docs/handoffs/v2g/figures/fig02_actual_phase_sweep.png`
47. `docs/handoffs/v2g/figures/fig03_v2_import_unsimulated.png`
