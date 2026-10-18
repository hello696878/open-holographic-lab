# W1 — Tests and evidence

This record separates current implementation acceptance, historical baseline
measurements, retained failures and the later clean-postcommit publication gate.
Raw streams and manifests remain in fresh ignored task-owned directories;
the three included figures are genuine production-browser captures.

## Executed suites

Evidence root:`runs/w1_implementation_01/`; interpreter remains
`C:\holographiclab\.venv\Scripts\python.exe`.

| Gate | Exact recorded outcome | Raw evidence |
|---|---|---|
| Before edits full Python |3447 passed,1 skipped in156.40s|`baseline_python/stdout.txt`|
| Before edits installed frontend |381 passed|`baseline_frontend_permitted/stdout.txt`|
| Numerical focused final |93 passed in1.40s; no skips|`core/focused_04.txt`|
| Final restored numerical faults |93 passed in1.80s; no skips|`core/negative_03/restored.stdout.txt`|
| New backend plus scoped guard |119 passed in4.73s; no skips|`backend/focused_03/stdout.txt`|
| Existing routes/guard regression |273 passed in11.53s; no skips|`backend/old_routes_01/stdout.txt`|
| Current full Python |3653 passed,1 skipped in168.73s|`full_python_01/stdout.txt`|
| Frontend before final cursor-handler regression |421 passed, 27 files, 11.88s|`frontend_unit_04/stdout.txt`|
| Final installed frontend |422 passed, 27 files, 11.92s|`frontend_unit_final/stdout.txt`|
| Final production typecheck/build |Pass; existing >500kB chunk warning preserved|`typecheck_05/`, `build_04/`|

The sole full-Python skip remains:
`tests/test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately`.
It was not removed by elevation or test changes. Separate focused and full
suite counts overlap and must not be summed as unique tests.

Numerical command from repository root:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_optics_wave_field.py tests/test_optics_wave_field_analytic.py tests/test_optics_wave_field_architecture.py
```

Full suite uses the existing interpreter with `-m pytest -q`; root execution
records contain exact argv and raw output. The old science remains protected;
the sole existing-test change is the named public W1 architecture allowance.

## Final source-identified numerical probe

```powershell
.\.venv\Scripts\python.exe -B -X utf8 scripts/validate_w1_wave_field.py --output runs/w1_implementation_01/core/validation_final_01
```

Report:`core/validation_final_01/report.json`; imported source
`C:\holographiclab\src\ohlab\optics\wave_field.py`, SHA256
`156c5681ebbc2d65dee722b7840f84c0809530edc6abcd7208169c48ab43b657`.
Python3.11.9 / NumPy2.4.6. It records all eight dense DFT reference matrices,
all25 comparisons each, eleven full-complex Gaussian/lens comparisons, two
fixed-geometry sampling comparisons, canonical stages and all default sections.

- Worst complex DFT relative L2:1.8348661564757353e-12; bound2e-11, component
  rtol2e-11/atol2e-11×incident peak.
- Free Gaussian30/60/120mm:1.1463e-7/2.2930e-7/4.5857e-7; bound1e-6.
- Signed lens:worst5.8137e-6; bound5e-5. Full phase/prefactor retained.
- Default aperture transmission0.993236290167812; signed aperture norm delta
  −2.7198491033363077e-10 amplitude-unit²m². The terminal canonical norm is
  3.994040105561577e-8 with signed propagation delta+1.9852334701272664e-23;
  this positive residual is retained, not clamped or called gain/absorption.
- Clean260µm default pitch/window intensity differences0.66230268%/0.60580818%.
  Strong80µm clipping at128² gives16.26456123%/15.85189745%; retained limitation.
- Free220mm Gaussian complex discrepancy1.7872757946645653e-5; not substituted
  for the adequate-window120mm acceptance.

Three warmed untraced sampler times75.9327/67.4650/61.4378ms; median67.4650ms
meets the predeclared local0.5s bound. A separate traced run reports current
4,351,985B and peak9,103,459B. Current process working-set snapshots are
39,804,928B before and44,212,224B after. They are different measures, not
whole-process lifetime peak, HTTP time, GPU frame time or whole-browser memory.
The result intensity allocation is3,276,800B; axes2,048B; retained canonical
three anchors plus terminal complex data1,048,576B.

## Negative controls and preserved failures

```powershell
.\.venv\Scripts\python.exe -B -X utf8 scripts/w1_negative_controls.py --output runs/w1_implementation_01/core/negative_03
```

This run preserves an unchanged copied positive,14 deliberately mutated copies
of only the new W1 wrapper, exact child commands/output/source hashes, protected
source/test hashes before/after, and the restored93-test pass. Only the intended
scientific/ownership AssertionError counts; schema/import/timeout failures do
not count. Production source and tests are never mutated for these controls.

Detected faults:wrong upstream anchor; absolute instead of interval z; doubled
propagation distance; aperture on its before side; omitted after-lens phase;
double lens phase; collapsed same-z stages; per-plane normalization hiding loss;
reversed rows; x/y transpose; endpoint interpolation; fabricated unperturbed
Gaussian; duplicate V0 execution; replacing the canonical terminal object with
a recomputed field even when its bytes happen to agree.

Backend `fault_gate_02/report.json` independently records a copied-server
premature-release fault during real W1 encoding and actual ASGI disconnect.
Positive and restored cases pass; the intended shared-gate assertion fails in
the fault;201 production-file hashes remain unchanged. It opens no ports.
Frontend `frontend/fault_controls_02/summary.json` independently detects seven
copied-source faults: stale attachment, view-context-triggered recomputation, per-sheet
normalization, row reversal, fabricated source reuse, same-z event collapse and
obsolete resource leakage. All seven fail their intended assertions, production
hashes remain unchanged, and the restored 40 focused W1 frontend tests pass.
That earlier normal frontend suite includes 40 W1 and 381 retained tests.
The additional actual cursor-handler regression below brings the final suite
to 41 W1 and 381 retained tests; earlier raw measurements remain unchanged.

Initial numerical `focused_01.txt` retains22 failures/52 passes from invalid
new fixture construction and an incorrect default-tiny-span test premise.
Only new fixtures were corrected; later93-test result is separate evidence.
Backend initial setup/tamper-constructor failures are preserved under
`backend/focused_01` and `focused_02`; the final encoder test still uses all17
intentional low-level tamper variants after public constructors gained checks.
Do not omit those records or relabel setup failures as numerical failures.

## Literal approved W1 inventory and frozen planning identity

The frozen approved inventory contains exactly **40 repository paths: 8 modifications and 32 creations**. `M` means modify; `A` means create. This is the literal approval inventory, not a claim that pending acceptance or publication gates have completed. Repository root: `C:\holographiclab`.

| Action | Exact repository-relative path |
|---|---|
| M | `README.md` |
| M | `docs/math_conventions.md` |
| M | `docs/milestones.md` |
| M | `apps/virtual_bench/server.py` |
| M | `tests/test_virtual_bench_architecture.py` |
| M | `frontend/bench/src/main.ts` |
| M | `frontend/bench/src/scene.ts` |
| M | `frontend/bench/src/styles.css` |
| A | `src/ohlab/optics/wave_field.py` |
| A | `apps/virtual_bench/wave_field_adapter.py` |
| A | `apps/virtual_bench/wave_field_protocol.py` |
| A | `tests/test_optics_wave_field.py` |
| A | `tests/test_optics_wave_field_analytic.py` |
| A | `tests/test_optics_wave_field_architecture.py` |
| A | `tests/test_virtual_bench_wave_field_adapter.py` |
| A | `tests/test_virtual_bench_wave_field_protocol.py` |
| A | `tests/test_virtual_bench_wave_field_server.py` |
| A | `tests/test_virtual_bench_wave_field_architecture.py` |
| A | `frontend/bench/src/wave_field_contracts.ts` |
| A | `frontend/bench/src/wave_field_state.ts` |
| A | `frontend/bench/src/wave_field_display.ts` |
| A | `frontend/bench/src/wave_field_apparatus.ts` |
| A | `frontend/bench/src/wave_field_workspace.ts` |
| A | `frontend/bench/tests/wave_field_transport.test.ts` |
| A | `frontend/bench/tests/wave_field_state.test.ts` |
| A | `frontend/bench/tests/wave_field_display.test.ts` |
| A | `frontend/bench/tests/wave_field_apparatus.test.ts` |
| A | `frontend/bench/tests/wave_field.browser.spec.ts` |
| A | `scripts/validate_w1_wave_field.py` |
| A | `scripts/w1_negative_controls.py` |
| A | `scripts/w1_controlled_acceptance_server.py` |
| A | `docs/handoffs/w1/implementation_summary.md` |
| A | `docs/handoffs/w1/code_map.md` |
| A | `docs/handoffs/w1/math_used.md` |
| A | `docs/handoffs/w1/tests_and_evidence.md` |
| A | `docs/handoffs/w1/known_limitations.md` |
| A | `docs/handoffs/w1/tutor_context.md` |
| A | `docs/handoffs/w1/figures/fig01_calculated_bench.png` |
| A | `docs/handoffs/w1/figures/fig02_parameter_after.png` |
| A | `docs/handoffs/w1/figures/fig03_section_coordinates.png` |

The two original planning files remain byte-identical to their frozen copies. SHA-256 values were rechecked while preparing this appendix:

| Planning file | Bytes | SHA-256 |
|---|---:|---|
| `runs/w1_feasibility_01/W1_PROPOSAL.md` | 23226 | `f7f90c8ad0f51ae27081d866d8b9f6724cf8c6c509dfb157a4fc7267d85a92b2` |
| `runs/w1_feasibility_01/implementation_inventory.json` | 9087 | `de6ba6e822e40b36addba271fecce0346afa61a4e91104e5f08ea3bf5ff7d0f1` |

The recorded accepted starting baseline was `dd0b1a65f2f5daccafe019af83133a66d97aa1e1`, clean synchronized `main` tracking `origin/main` in `runs/w1_implementation_01/preflight.json`. The newer implementation approval governs conditional publication; the planning files were preserved unchanged.

## Exact recorded Python validation output

### Unchanged accepted baseline

Working directory: `C:\holographiclab`. Recorded exit code: **0**.

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider
```

```text
........................................................................ [  2%]
........................................................................ [  4%]
........................................................................ [  6%]
........................................................................ [  8%]
........................................................................ [ 10%]
........................................................................ [ 12%]
........................................................................ [ 14%]
........................................................................ [ 16%]
........................................................................ [ 18%]
........................................................................ [ 20%]
........................................................................ [ 22%]
........................................................................ [ 25%]
........................................................................ [ 27%]
........................................................................ [ 29%]
........................................................................ [ 31%]
........................................................................ [ 33%]
........................................................................ [ 35%]
........................................................................ [ 37%]
........................................................................ [ 39%]
........................................................................ [ 41%]
........................................................................ [ 43%]
........................................................................ [ 45%]
........................................................................ [ 48%]
........................................................................ [ 50%]
........................................................................ [ 52%]
........................................................................ [ 54%]
........................................................................ [ 56%]
..................................s..................................... [ 58%]
........................................................................ [ 60%]
........................................................................ [ 62%]
........................................................................ [ 64%]
........................................................................ [ 66%]
........................................................................ [ 68%]
........................................................................ [ 70%]
........................................................................ [ 73%]
........................................................................ [ 75%]
........................................................................ [ 77%]
........................................................................ [ 79%]
........................................................................ [ 81%]
........................................................................ [ 83%]
........................................................................ [ 85%]
........................................................................ [ 87%]
........................................................................ [ 89%]
........................................................................ [ 91%]
........................................................................ [ 93%]
........................................................................ [ 96%]
........................................................................ [ 98%]
................................................................         [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
3447 passed, 1 skipped in 156.40s (0:02:36)
```

Raw record: `runs/w1_implementation_01/baseline_python/stdout.txt`.

### Implemented W1 full Python suite

Working directory: `C:\holographiclab`. Recorded exit code: **0**.

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' -m pytest -q
```

```text
........................................................................ [  1%]
........................................................................ [  3%]
........................................................................ [  5%]
........................................................................ [  7%]
........................................................................ [  9%]
........................................................................ [ 11%]
........................................................................ [ 13%]
........................................................................ [ 15%]
........................................................................ [ 17%]
........................................................................ [ 19%]
........................................................................ [ 21%]
........................................................................ [ 23%]
........................................................................ [ 25%]
........................................................................ [ 27%]
........................................................................ [ 29%]
........................................................................ [ 31%]
........................................................................ [ 33%]
........................................................................ [ 35%]
........................................................................ [ 37%]
........................................................................ [ 39%]
........................................................................ [ 41%]
........................................................................ [ 43%]
........................................................................ [ 45%]
........................................................................ [ 47%]
........................................................................ [ 49%]
........................................................................ [ 51%]
........................................................................ [ 53%]
........................................................................ [ 55%]
.......................................................s................ [ 57%]
........................................................................ [ 59%]
........................................................................ [ 61%]
........................................................................ [ 63%]
........................................................................ [ 65%]
........................................................................ [ 66%]
........................................................................ [ 68%]
........................................................................ [ 70%]
........................................................................ [ 72%]
........................................................................ [ 74%]
........................................................................ [ 76%]
........................................................................ [ 78%]
........................................................................ [ 80%]
........................................................................ [ 82%]
........................................................................ [ 84%]
........................................................................ [ 86%]
........................................................................ [ 88%]
........................................................................ [ 90%]
........................................................................ [ 92%]
........................................................................ [ 94%]
........................................................................ [ 96%]
........................................................................ [ 98%]
......................................................                   [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
3653 passed, 1 skipped in 168.73s (0:02:48)
```

Raw record: `runs/w1_implementation_01/full_python_01/stdout.txt`. Both recorded runs retain the same existing Windows symlink-privilege skip at `tests/test_run_artifacts.py:1101`; junction behavior is tested separately. No privilege elevation or test change removed it.

## Exact recorded installed frontend unit output

Working directory: `C:\holographiclab\frontend\bench`. Recorded exit code: **0**.

```powershell
& 'C:/Program Files/nodejs/node.exe' node_modules/vitest/vitest.mjs run
```

```text

 RUN  v5.0.3 C:/holographiclab/frontend/bench


 Test Files  27 passed (27)
      Tests  421 passed (421)
   Start at  15:37:54
   Duration  11.88s (import 60%, tests 19%, transform 18%, worker 3%)

    Isolate  27 workers spawned · ~198ms startup each (spawn + environment, per file)
             at least ~5.16s faster with isolate: false — reuses workers across files instead of one per file

```

Raw record: `runs/w1_implementation_01/frontend_unit_04/stdout.txt`. The complete output above is retained verbatim, including the runner's informational worker message; no suggested configuration change was applied.

## Recorded frontend typecheck and production build

### Typecheck 05

Working directory: `C:\holographiclab\frontend\bench`. Recorded exit code: **0**.

```powershell
& 'C:/Program Files/nodejs/node.exe' node_modules/typescript/bin/tsc --noEmit
```

Recorded stdout and stderr were both empty. This check exited successfully. Evidence: `runs/w1_implementation_01/typecheck_05/`.

### Build 04

Working directory: `C:\holographiclab\frontend\bench`. Recorded exit code: **0**.

```powershell
& 'C:/Program Files/nodejs/node.exe' node_modules/vite/bin/vite.js build
```

```text
vite v8.3.2 building client environment for production...
transforming...
✓ 41 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.55 kB │ gzip:   0.38 kB
dist/assets/index-BYd5jl_n.css   24.36 kB │ gzip:   5.50 kB
dist/assets/index-CpUHPoh1.js   958.08 kB │ gzip: 251.35 kB

✓ built in 381ms
```

The build succeeded and retained the existing large-chunk warning. The excerpt
below omits only the logger header's trailing space; exact raw stderr remains
unchanged in `runs/w1_implementation_01/build_04/stderr.txt`:

```text
[plugin builtin:vite-reporter]
(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rolldownOptions.output.codeSplitting to improve chunking: https://rolldown.rs/reference/OutputOptions.codeSplitting
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
```

Evidence: `runs/w1_implementation_01/build_04/`. The warning was not hidden by changing chunk limits, dependencies or build configuration.

## Recorded protected-source and environment verification

The existing `runs/w1_implementation_01/before_closeout_corrected_protection.json` records the following checkpoint; it is not substituted for the final publication verification:

- **396 pre-existing tracked files outside the eight allowed modifications were unchanged.**
- **4,210 historical evidence files** remained byte/hash-identical across their recorded roots.
- **53 pre-existing Python distributions** retained their versions and complete recorded metadata.
- **7 frontend package metadata files** remained unchanged.
- Both frozen planning files were unchanged; the staged-path inventory at that checkpoint was empty.

| Preserved historical evidence root | Files |
|---|---:|
| `runs/research_workspace_ux_v1_01` | 3379 |
| `runs/r03_fig2a_readiness_01` | 84 |
| `runs/r03_fig2a_semantics_01` | 27 |
| `runs/r03_ideal_polarization_impl_01` | 612 |
| `runs/w1_feasibility_01` | 108 |

The protection record listed only the eight approved tracked modifications and allowlisted creations then present. At that checkpoint its pending-path count was 37; the three approved handoff figures were not yet represented there. This appendix does not infer later file state, browser completion, recording acceptance, commit, push or postcommit success from that earlier record.

This appendix was assembled read-only from the named existing records. No test, build, service, installation, production edit or Git mutation was executed to produce it.

## Shipped product and visual evidence

Final production assets were built from the current implementation with the
installed toolchain and copied into the owned `assets_04/` directory. The
task-owned service identity records actual Python source locations/hashes and
served assets. `http_identity_04/report.json` verifies every served asset byte
and five independently constructed public-V0 comparisons: default, focal40mm,
aperture80µm, wavelength780nm and observation300mm. Every terminal raw intensity
byte and complete canonical stage diagnostic agrees with ordinary HTTP V0 and
independent public V0. Full complex identity is proved by the core tests; HTTP
does not transport complex fields and cannot alone prove that stronger claim.

- JavaScript `assets/index-CpUHPoh1.js` SHA256
  `4a9ec3287fc98d699dabac0a11b872ca33637ec1a78d91547c21f2903ae6f8d2`.
- CSS `assets/index-BYd5jl_n.css` SHA256
  `dff642245d7a4b6fb91e85539e385e9b264e3b5afdc50573501f081fc33ca355`.
- HTML SHA256
  `3e1a683f209b78b0c4cfe4b43a59f54ff2b3c2063ea6ebe8cefe22f366901694`.

`precommit_complete/w1/stdout.txt` records **8 passed (1.2m)**, no skips/retries:
1366×768,1440×900,1920×1080, independent parameter sensitivity, mixed retained
owners/documents, late/context/release, actual200% Chrome zoom and recording.
The final recording-only test adds a genuine pointer sample and Focus action:
`recording_final/recording/stdout.txt` records **1 passed (35.2s)**, no skips/retries.
It retains the exact-value, complete-viewport, freshness and request-count
assertions. `typecheck_final/` passes after those test-only additions.

Each desktop case compares selected full raw float64 sections and asymmetric
row59/column70 coordinates to the received binary frame. Passive cursor,
camera, precision, range and glow actions make no additional scientific POST.
The actual200% zoom uses a fresh disposable Chrome profile; it is browser zoom,
not a CSS transform or resized screenshot. It checks DPR2, visual scale1,
bounded page width, no scalar wrapping and keyboard table access.

The fixed-camera matched pairs in `precommit_complete/w1/evidence/` retain
the0–3 shared scale. They change one parameter at each successive step:

| Change | Terminal intensity relative L2 change |
|---|---:|
| Focal length80→40mm |0.7645122457957002|
| Aperture radius260→80µm, after focal edit |0.6169204673139451|
| Wavelength633→780nm, after those edits |0.2628365157248954|
| Observation220→300mm, after those edits |0.36035749330545996|

These are distinct informative sampled fixtures, not a claim that every
parameter edit visibly affects every optical train. Strong clipping remains
the documented numerical counterexample.

The final genuine unaccelerated recording is:
`runs/w1_implementation_01/recording_final/recording/evidence/recording/page@bb3422d6f8b844a6ba6a3ddf9a8fd3d9.webm`.
It is33.44s at original1440×900,2,700,425B, SHA256
`5588b184e0ba2a4f4d7515209a6f04664e3c5767f3682a1a37bd4fe55ee806c9`.
Root inspected original decoded frames1/4/8/10/11/12/14/16/20/24/28/32s:
configuration, explicit submission, moving snapping cursor, complete inspector
at10–12s, lens edit/stale detachment, explicit recomputation, visibly shifted
bright focal region, top/focus/reset and actual orbit. This is a meaningful
visible difference at a retained scale, separate from numerical correctness.
`visual_review_final.json`, the recording manifest and viewport/sample checkpoint
preserve the review provenance. No compositing, acceleration or synthetic
replacement is used.

Included figures are original copies:

- `figures/fig01_calculated_bench.png`:final1440×900 mounted bench/cursor.
- `figures/fig02_parameter_after.png`:focal40mm case; matched before remains
  separately in ignored evidence.
- `figures/fig03_section_coordinates.png`:complete inspector and exact pointer
  readout from the final recording run.

## Measured runtime and declared resource ownership

Chrome155.0.8059.82; WebGL2; vendorGoogle Inc.(Intel); renderer
`ANGLE (Intel, Intel(R) Graphics (0x00007D67) Direct3D11 vs_5_0 ps_5_0, D3D11)`.
Final recording renderer CPU-submission p95=2.800000011920929ms (bound8ms),
RAF-interval p95=6.100000000002183ms (bound33.4ms). These are local CPU/RAF
observations, not full GPU-frame timings or universal FPS guarantees.

The three shipped desktop first computations measure HTTP+decode150.5,
158.89999997615814 and103.40000003576279ms, median150.5ms, versus the
predeclared1s local bound. Decode7.9/11.6/7.3ms and atomic attachment
27.5/30.6/34.3ms are separate observations. Backend sampler timing/tracing
above is a different measurement, not this request latency.

Default W1 declared ownership=5,382,604B; aggregate with retained ordinary
canvas/geometry=5,585,168B. The actual mixed W1/R03/old-modes/prepared-document
case retains14,259,474B and rejects the next excessive overlap before HTTP,
preserving previous results, draft, document and camera. Both factories borrow
the same two Sprite backing buffers:92B is deducted once when R03 also retains
labels. The cross-factory unit and actual mixed-browser ledger verify alias
deduplication; global borrowed geometry is never disposed by either owner.

The16MiB persistent/32MiB transient policies include declared retained arrays,
wire/decoding, active display buffers, plots, geometry, documents and old/new
preparation overlap. Debug/browser evidence verifies one renderer/control/
observer/RAF, obsolete resource release, context recovery and explicit global
result release. Drafts and useful prepared documents survive release. Test-owned
bounded response clones, JS object/string overhead and total heap/GPU/driver
allocations are outside this declared buffer accounting, not claimed measured.

## Retained precommit tooling and capture failures

All failed raw records remain under the same owned evidence root:

- Initial frontend sandbox process creation failed withEPERM; the authorized
  installed suite then ran through normal permission. A cp950 wrapper-print
  failure was corrected to UTF-8 without changing test behavior.
- Initial new-browser configuration used unsupported per-describe video
  settings. The final case owns its explicit video browser context instead.
- Initial new-browser captures hit Chrome's missing response-body CDP data;
  the new W1 test captures a bounded clone of the actual fetch response and
  preserves all payload assertions. Its clone makes no extra request and
  changes no returned bytes. Initial context-extension reacquisition and a
  collapsed release-panel locator were corrected in the new test only.
- Earlier33.56s and34.08s recordings did not visibly establish inspector
  demonstration despite later DOM viewport assertions. They remain preserved;
  they are not the accepted recording. The final test uses real wheel input,
  a normal pixel pick, exact-value assertion and contemporaneous screenshot
  before the unchanged hold. No forced clicks, assertion removal, larger
  timeouts or test-runner retries were introduced.
- `precommit_complete/legacy/` retains **2 failed,8 skipped,53 passed (4.4m)**.
  Both failures are `Network.getResponseBody: No data found for resource with
  given identifier` in unchanged old document/two-port tests, before their
  comparisons. The exact unchanged two cases pass once in
  `capture_diagnostic_01/diagnostic/` (**2 passed (7.7s)**). They were not edited
  or reported as scientific assertion failures. Final legacy gate results are
  recorded separately below; earlier failures are not erased.
- `backend/legacy_control01/stopped_before_launch.json` preserves a frozen
  source-hash mismatch detected before any listener/browser launch after the
  new recording assertion changed. A fresh manifest is used rather than
  restoring old code or overwriting the stopped evidence.
- The first protection helper received Git's collapsed untracked directory
  `docs/handoffs/w1/`; explicit `--untracked-files=all` fixed its inventory
  enumeration. No protected-file mismatch occurred.

## Publication boundary

The approved commit is `feat(w1): visualize computed wave-field sections`.
`runs/w1_implementation_01/postcommit_gate.py` defines a single fresh required
gate, frozen by hash before commit. It requires clean main, exact40-path
commit/source identities and the unchanged baseline parent, then typechecks
and rebuilds from committed sources, verifies imported source paths and served
asset hashes, compares five independent V0 terminal cases, executes a fresh
1440×900 W1 simulation/cross-section check and22 unchanged R03/mode/document
smoke cases, rechecks protection and closes only its owned loopback service.

No test retry is configured. Any required postcommit failure stops before push
without amendment, history rewriting or automatic repeat. This committed
handoff states the gate and precommit evidence; its later actual outcome and
local/live-remote/GitHub API equality are recorded in ignored gate/publication
manifests and the completion report. It does not pre-claim those later actions.

## Final retained-browser gate and controlled coverage

The unchanged final precommit_strict/legacy/ gate records **55 passed (4.4m),
8 skipped**, exit0, one worker, zero retries, unchanged60000ms timeout. These
eight are existing separately controlled harness conditions, not removed cases:

`	ext
  -  11 tests\bench.browser.spec.ts:329:1 › actual browser disconnect keeps running worker busy until controlled completion
  -  17 tests\experiment_documents.browser.spec.ts:254:1 › controlled document validation stays responsive under a real held worker and Apply rechecks busy
  -  28 tests\polarization.browser.spec.ts:386:1 › controlled actual failed sweep keeps only genuine contiguous rows
  -  29 tests\polarization.browser.spec.ts:400:1 › actual polarization browser disconnect holds all five operations until genuine worker completion
  -  39 tests\polarized_two_path.browser.spec.ts:283:1 › separately controlled first/interior/final sweep failure contains only genuine complete prefixes
  -  41 tests\polarized_two_path.browser.spec.ts:350:1 › separately controlled actual-browser disconnect holds all seven operations, while documents remain noncomputing
  -  59 tests\two_path.browser.spec.ts:315:1 › controlled partial failure retains only genuine prefix and never labels sweep complete
  -  60 tests\two_path.browser.spec.ts:331:1 › actual two-path browser disconnect holds all numerical routes until genuine worker completion
`

The current W1 held-encoding child records **1 passed (4.7s)** in
precommit_strict/held/. Actual browser disconnect leaves health busy until
its disk-held real encoding completes; the browser then independently observes
release. w1_held_evidence_02/completed.json retains the real success frame,
worker-finally timing and busy-before-Future-terminal observation. Its owned
service closes gracefully. The stronger backend tests separately check both
directions of all nine shared operations and encoding/cancellation lifetime.

The final frozen ackend/legacy_control03/summary.json covers all eight
reserved case IDs in **19 genuine controlled-browser executions:19 passed,
0 skipped,0 flaky,0 retries**. Variants include old Sequential disconnect,
dual partial sweep/disconnect, polarization prefixes0/3/12 and both worker
kinds, polarized-two-path prefixes0/8/16 and both worker kinds, and document
responsiveness under five held operations. Each verifies actual served assets,
source/environment identities, exactly one pass, graceful owned closure and
port8510 free before proceeding. control02 earlier19-pass evidence is
retained separately; final acceptance uses control03.

The new cursor-handler regression was added after this controlled run; among
executable/test files only that already-approved new unit-test file changed, not production source,
browser assertions, assets, or any legacy tests. Its restored/current unit
results and copied-handler fault evidence are recorded below.

## Final actual-cursor negative control and restored frontend

The handoff review distinguished view-context recomputation from a cursor
handler fault. The additional approved display-test regression invokes the
actual `WaveFieldWorkspace.prototype.select` reached by the cursor/section
bindings, stubbing only owned controller/resource/readout collaborators. It
asserts returned section identity, unchanged raw values and zero numerical
submissions. It does not replace the existing real-browser pointer/keyboard
coverage or use a mirrored test-only selection algorithm.

`frontend/cursor_fault_01/summary.json` records an unchanged copied-handler
positive pass and one copied workspace mutation adding `controller.simulate()`
inside that actual handler. Only the intended `W1_CURSOR_NO_PROPAGATION`
AssertionError counts; the control detects it. No production file is mutated.
The exact reviewed draft is a byte-identical suffix of the approved display
test. Complete copied-test bytes differ only by Windows CRLF conversion:
canonical LF text is identical. The overstrong initial byte-identity assertion
is preserved in `frontend/cursor_identity_bytecheck_failure.json`; the evidence
copy was not rewritten or called byte-identical.

Restored four W1 unit files: **41 passed**, no skips, under
`frontend/cursor_restored_unit_09/`. Final full installed suite below: **422
passed**, including all381 retained tests. `typecheck_closeout/` passes after
the addition. Frozen frontend manifest04 confirms the sole executable/test
change since the final production-browser controls is this new regression;
all six owned production sources and other three owned unit files are unchanged.
No scientific core/backend or production asset changed, so their source-
identified numerical and browser evidence is retained rather than relabelled
as a later rerun.

Exact final frontend command (cwd `C:\holographiclab\frontend\bench`):

```powershell
& "C:\Program Files\nodejs\node.exe" node_modules/vitest/vitest.mjs run
```

Unedited stdout:

```text

 RUN  v5.0.3 C:/holographiclab/frontend/bench


 Test Files  27 passed (27)
      Tests  422 passed (422)
   Start at  15:56:42
   Duration  11.92s (import 63%, tests 18%, transform 17%, worker 2%)

    Isolate  27 workers spawned · ~188ms startup each (spawn + environment, per file)
             at least ~4.89s faster with isolate: false — reuses workers across files instead of one per file

```

Full raw stderr is empty. Exact final typecheck uses the same Node executable
with `node_modules/typescript/bin/tsc --noEmit`; stdout/stderr are empty, exit0.

The final literal scope/protection checkpoint is
`precommit_final_protection.json`:40 pending approved paths,396 pre-existing
tracked files outside the eight modifications unchanged,4210 historical files
unchanged,53 Python distribution versions/metadata and seven frontend package
metadata files unchanged. Planning hashes remain exact. Staging must match
all40 paths, eight M and32 A, with no unstaged or untracked residual. The
subsequent staging manifest and complete diff preserve that actual check.
