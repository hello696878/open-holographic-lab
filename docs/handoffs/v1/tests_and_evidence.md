# V1 tests and evidence

Evidence date: 2026-10-05 (Asia/Taipei). This records actual initial and final precommit results.
Clean-postcommit publication is a later gate, not predicted here. Ignored raw captures reside in
`runs/v1_acceptance_20261005/`; they are distinct from the earlier planning
probes in `runs/v1_planning_20261004/` and historical V0 measurements.

## Starting state and retained baseline

Accepted SHA: `ce4fe39eee2213dec993e09b25492e01f9d16497`, clean synchronized
`main`. The actual baseline command was

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest -q -p no:cacheprovider --basetemp=runs/v1_acceptance_20261005/pytest_baseline
```

Raw command/stdout/stderr/exit captures are `baseline_*`. Exact concluding lines:

```text
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
1702 passed, 1 skipped in 160.62s (0:02:40)
```

This is the unchanged baseline result, not the final enlarged V1 suite. The
symlink skip remains; no test change or privilege elevation removes it.

## Dependency/source gate

`npm_direct_gate.json` records nonsecret registry/proxy/certificate information
and refreshed exact official metadata. `npm_lock_manifests.json` records every
locked source/integrity/platform/engine/peer/lifecycle declaration.
`npm_constraints_review.json` reports `passed=true`, no problems and optional
native packages preserved. No lifecycle scripts were enabled.

Lock SHA-256:
`d04f0937f5593e57c8e290cf812dba70db14dab4fccae4879d3e088c23cd7f91`.
All sources are HTTPS official npm registry tarballs. There are 74 reviewed
nonroot packages and 49 Windows-installed packages. npm ci actual stdout:

```text
added 49 packages in 14s
```

Native/import probe (`native_probe_corrected_*`) actual stdout:

```json
{"platform":"win32","arch":"x64","node":"v24.15.0","typescript":"6.0.3","viteImport":true,"rolldownNativeImport":true,"lightningcssNativeTransform":true,"playwrightImport":true,"browserLaunched":false,"installScriptsExecuted":false}
```

The original probe failure is preserved separately. The corrected probe is not
an installation repair. `post_npm_preservation.json` confirms unchanged 52
Python distribution versions/metadata/source locations and no protected tracked
file changes at that checkpoint. Final preservation remains a separate gate.

## Frontend typecheck and focused regression tests

Actual commands from `frontend/bench`:

```powershell
& 'C:\Program Files\nodejs\npm.cmd' run --ignore-scripts typecheck
& 'C:\Program Files\nodejs\npm.cmd' run --ignore-scripts test:unit -- tests/state.test.ts tests/mapping.test.ts tests/transport.test.ts
```

`frontend_state_reviewed_typecheck_*` exits 0. The focused regression capture
`frontend_state_reviewed_unit_*` exits 0 with exact summary:

```text
 Test Files  3 passed (3)
      Tests  51 passed (51)
   Start at  13:38:56
   Duration  852ms (import 51%, transform 28%, tests 17%, worker 4%)
```

These tests independently check malformed protocol fixtures, explicit endian
decoding, exact shapes/offsets/identity, original values/nulls, body cancellation,
mixed parity mapping, invalid editor strings, controlled out-of-order replies,
synchronous duplicate suppression, stale attachment and rendering-failure
separation. They do not establish WebGL or browser acceptance.

Earlier sandbox `spawn EPERM` and the first fixture padding assertion are
preserved as tool transcripts. Normal approved subprocess permission allowed
tests to run; lifecycle scripts remained disabled. The fixture was corrected
to guarantee nonzero alignment padding, with the malformed-padding rejection
test retained. These failures are not relabeled as passes or native repairs.

## Initial production build

Actual command: `npm.cmd run --ignore-scripts build`. `frontend_build_1_*`
exits 0; exact output:

```text
> ohlab-virtual-bench@0.1.0 build
> vite build

vite v8.3.2 building client environment for production...
transforming...
✓ 14 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.54 kB │ gzip:   0.37 kB
dist/assets/index-BYpZVsmx.css    5.59 kB │ gzip:   1.84 kB
dist/assets/index-DTnk_zv8.js   627.37 kB │ gzip: 162.26 kB

✓ built in 347ms
```

This first build precedes later reviewed frontend changes; final acceptance
must rebuild those sources. The retained stderr bundle-size warning does not
establish a performance failure or authorize a framework change.

## Initial genuine HTTP/direct-V0 comparison

Actual command from the repository root:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 scripts\validate_v1_bench.py --output runs\v1_acceptance_20261005\api_evidence_1.json
```

`api_acceptance_1_*` exits 0. `api_evidence_1.json` reports ten passed cases and
exact direct public V0 matching for arrays, axes and scalar stages. Imported
source is `C:\holographiclab\src\ohlab\optics\__init__.py`. Served assets are
hashed against this checkout's built files.

| Actual fixture | HTTP wall seconds | Response bytes | Raw intensity maximum |
|---|---:|---:|---:|
| Free Gaussian | 0.13095069996779785 | 2106592 | 0.860293298357317 |
| Positive lens | 0.15463350003119558 | 2106952 | 6.1575878701940825 |
| 80 µm aperture/lens | 0.1662163000437431 | 2107360 | 1.3783458121954204 |
| Negative lens | 0.14036009996198118 | 2106952 | 0.24024616468451448 |
| Observation 10 mm | 0.12132420000853017 | 2106952 | 3.44124584042096 |
| 40 µm aperture/lens | 0.12851860001683235 | 2107392 | 0.13701204008458018 |
| Dark | 0.11426509998273104 | 2106488 | 0 |
| Asymmetric 3×4 | 0.01566179998917505 | 1320 | 1 |
| Asymmetric 2×5 | 0.017067599983420223 | 1304 | 1 |
| Eight components | 0.7638769999612123 | 2109792 | 1.5757041363201916 |

These values measure the shipped initial adapter/HTTP path, not GPU performance
or universal accuracy. The independent direct solver comparison uses the same
platform/libraries and exact discrete values; it does not reprove continuous
optics convergence. That scientific evidence belongs to V0.

## Final precommit acceptance — 2026-10-05

The final Python run follows the isolated controls and final backend changes.
There are 1,803 cases: 1,702 retained passes, 100 new V1 passes and the unchanged
Windows symlink skip. All captures below retain exact process stdout/stderr;
Markdown represents line endings as text. Byte-original captures remain in
the named ignored files. Commands are recorded as exact subprocess argv.

### python_full_2

Exact argv: `['.\\.venv\\Scripts\\python.exe', '-B', '-X', 'utf8', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--basetemp=runs/v1_acceptance_20261005/pytest_final2']`

```text
........................................................................ [  3%]
........................................................................ [  7%]
........................................................................ [ 11%]
........................................................................ [ 15%]
........................................................................ [ 19%]
........................................................................ [ 23%]
........................................................................ [ 27%]
........................................................................ [ 31%]
........................................................................ [ 35%]
........................................................................ [ 39%]
........................................................................ [ 43%]
........................................................................ [ 47%]
........................................................................ [ 51%]
........................................................................ [ 55%]
........................................................................ [ 59%]
........................................................................ [ 63%]
..s..................................................................... [ 67%]
........................................................................ [ 71%]
........................................................................ [ 75%]
........................................................................ [ 79%]
........................................................................ [ 83%]
........................................................................ [ 87%]
........................................................................ [ 91%]
........................................................................ [ 95%]
........................................................................ [ 99%]
...                                                                      [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
1802 passed, 1 skipped in 122.14s (0:02:02)
```

Exit 0. Stderr:

```text
```

### frontend_typecheck_final2

Exact argv: `['C:\\Program Files\\nodejs\\npm.cmd', 'run', '--ignore-scripts', 'typecheck']`

```text

> ohlab-virtual-bench@0.1.0 typecheck
> tsc --noEmit

```

Exit 0. Stderr:

```text
```

### frontend_unit_final2

Exact argv: `['C:\\Program Files\\nodejs\\npm.cmd', 'run', '--ignore-scripts', 'test:unit']`

```text

> ohlab-virtual-bench@0.1.0 test:unit
> vitest run


 RUN  v5.0.3 C:/holographiclab/frontend/bench


 Test Files  4 passed (4)
      Tests  65 passed (65)
   Start at  14:02:08
   Duration  805ms (import 62%, transform 20%, tests 14%, worker 4%)

    Isolate  4 workers spawned · ~103ms startup each (spawn + environment, per file)
             at least ~309ms faster with isolate: false — reuses workers across files instead of one per file

```

Exit 0. Stderr:

```text
```

### frontend_build_final

Exact argv: `['C:\\Program Files\\nodejs\\npm.cmd', 'run', '--ignore-scripts', 'build']`

```text

> ohlab-virtual-bench@0.1.0 build
> vite build

vite v8.3.2 building client environment for production...
transforming...
✓ 14 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.54 kB │ gzip:   0.37 kB
dist/assets/index-BYpZVsmx.css    5.59 kB │ gzip:   1.84 kB
dist/assets/index-D20bSrcF.js   628.51 kB │ gzip: 162.53 kB

✓ built in 267ms
```

Exit 0. Stderr:

```text
[plugin builtin:vite-reporter]
(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rolldownOptions.output.codeSplitting to improve chunking: https://rolldown.rs/reference/OutputOptions.codeSplitting
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
```

The reporter line's single trailing space is omitted from this Markdown stderr
copy to pass Git's whitespace check. The original byte capture is unchanged.

### api_acceptance_final

Exact argv: `['.\\.venv\\Scripts\\python.exe', '-B', '-X', 'utf8', 'scripts\\validate_v1_bench.py', '--output', 'runs\\v1_acceptance_20261005\\api_evidence_final.json']`

```text
{
  "passed": true,
  "cases": 10,
  "output": "runs\\v1_acceptance_20261005\\api_evidence_final.json",
  "source_location": "C:\\holographiclab\\src\\ohlab\\optics\\__init__.py",
  "served_asset_sha256": {
    "/assets/index-D20bSrcF.js": "01811c610a64f2cc5342381413c599eaa219d13144a109bcf4a08f6b605e0d6d",
    "/assets/index-BYpZVsmx.css": "9860b50c8f6d440d349631d949eaeb49a3f0d3867b4af66dcb7aa665c39df3cf"
  }
}
```

Exit 0. Stderr:

```text
```

### browser_final

Exact argv: `['..\\..\\.venv\\Scripts\\python.exe', '-B', '-X', 'utf8', '..\\..\\runs\\v1_acceptance_20261005\\child_env.py', '{"V1_EVIDENCE_DIR":"runs/v1_acceptance_20261005/browser_final","V1_API_EVIDENCE":"../api_evidence_final.json"}', 'C:\\Program Files\\nodejs\\npm.cmd', 'run', '--ignore-scripts', 'test:browser', '--', '--output=../../runs/v1_acceptance_20261005/browser_final/screens']`

```text

> ohlab-virtual-bench@0.1.0 test:browser
> playwright test --output=../../runs/v1_acceptance_20261005/browser_final/screens


Running 11 tests using 1 worker

  ok  1 tests\bench.browser.spec.ts:55:1 › production V0 lens/readout smoke and local-only assets (1.6s)
  ok  2 tests\bench.browser.spec.ts:74:1 › camera selection color resize and 3D picking do not alter optics or call API (3.1s)
  ok  3 tests\bench.browser.spec.ts:117:1 › real edits change V0 output; aperture uses shared limits and original norm loss; stale screenshot (3.9s)
  ok  4 tests\bench.browser.spec.ts:138:1 › source fields signed lens rectangle add delete numeric order and z ghost rail (3.1s)
  ok  5 tests\bench.browser.spec.ts:174:1 › rapid submissions remain single and edited pending response stays separately stale (880ms)
  ok  6 tests\bench.browser.spec.ts:190:1 › malformed response and missing backend publish no fabricated success; reload passive; dark genuine (1.4s)
  ok  7 tests\bench.browser.spec.ts:226:1 › independent gray fixture catches extra gamma in actual WebGL and preserves raw float64 (634ms)
  ok  8 tests\bench.browser.spec.ts:249:1 › independent asymmetric 3x4 and 2x5 display cells and original readouts (3.6s)
  ok  9 tests\bench.browser.spec.ts:294:1 › context loss and unsupported WebGL report presentation failure without automatic solve (1.5s)
  ok 10 tests\bench.browser.spec.ts:313:1 › predefined resource replacement sequence retains one active texture and bounded owned resources (7.9s)
  -  11 tests\bench.browser.spec.ts:329:1 › actual browser disconnect keeps running worker busy until controlled completion

  1 skipped
  10 passed (29.0s)
```

Exit 0. Stderr:

```text
(node:48748) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
```

### browser_cancellation_2

Exact argv: `['..\\..\\.venv\\Scripts\\python.exe', '-B', '-X', 'utf8', '..\\..\\runs\\v1_acceptance_20261005\\child_env.py', '{"V1_EVIDENCE_DIR":"runs/v1_acceptance_20261005/browser_cancel02","V1_API_EVIDENCE":"../api_evidence_2.json","V1_CANCELLATION_DIR":"runs/v1_acceptance_20261005/cancellation_2"}', 'C:\\Program Files\\nodejs\\npm.cmd', 'run', '--ignore-scripts', 'test:browser', '--', '--grep=actual browser disconnect', '--output=../../runs/v1_acceptance_20261005/browser_cancel02/screens']`

```text

> ohlab-virtual-bench@0.1.0 test:browser
> playwright test --grep=actual browser disconnect --output=../../runs/v1_acceptance_20261005/browser_cancel02/screens


Running 1 test using 1 worker

  ok 1 tests\bench.browser.spec.ts:329:1 › actual browser disconnect keeps running worker busy until controlled completion (1.8s)

  1 passed (3.1s)
```

Exit 0. Stderr:

```text
(node:16532) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
```

### negative_controls_1

Exact argv: `['.\\.venv\\Scripts\\python.exe', '-B', '-X', 'utf8', 'scripts\\v1_negative_controls.py', '--output-dir', 'runs\\v1_acceptance_20261005\\negative_controls']`

```text
nm_conversion: baseline=0, mutant=1, assertion_detected=True
mm_conversion: baseline=0, mutant=1, assertion_detected=True
axis_swap: baseline=0, mutant=1, assertion_detected=True
vertical_texture_flip: baseline=0, mutant=1, assertion_detected=True
ignored_optical_edit: baseline=0, mutant=1, assertion_detected=True
stale_attachment: baseline=0, mutant=1, assertion_detected=True
duplicate_simulation: baseline=0, mutant=1, assertion_detected=True
normalization_hides_loss: baseline=0, mutant=1, assertion_detected=True
static_plausible_v0_replacement: baseline=0, mutant=1, assertion_detected=True
production_unchanged=True; detected=9/9
```

Exit 0. Stderr:

```text
```

## What the independent checks establish

Python's new 100 tests cover duplicate/nonfinite JSON, cheap limits before V0
construction, genuine exact separate V0 comparison, independently described
frame bytes, ASGI streamed body caps, exact Host/Origin, static traversal/link/
junction rejection and controlled worker lifetime. Event/Future synchronization
covers running worker busy rejection, client disconnect and handler abort,
responsive health/validation, success, numerical/encoding failure, executor
submission failure and cancellation before start. Running Python work is never
described as cancelled merely because its HTTP waiter stopped.

Frontend typecheck passes. All 65 unit tests pass after the deliberate faults.
Frame/header/descriptor/axis/max/request/specification/server-digest validation
finishes before state publication; malformed frames cannot publish a texture.
Exact supplied float64 values and V0 scalar records/nulls remain authoritative.

Ten production-browser cases pass; the one displayed skip is the separately
executed synchronization-harness case, which independently passed once.
Thus all eleven distinct required browser scenarios were executed successfully.
The production server contains no test-control route. The actual disconnect
check uses ignored `cancellation_harness.py` and fresh `cancellation_2/` markers:
one first worker waits on an Event, its real browser page closes, another page
validates successfully but a deliberate simulation receives 409 while health
reports busy. Explicit release then lets the first genuine V0 call/encoding
finish successfully; a later deliberate browser submission matches direct V0.
The successful original completion is verified from its request-ID marker,
not inferred from gate release alone. Coordination polling observes markers/
state; it does not guess when computation has finished.

Browser cases exercise actual DOM numeric edits, invalid strings, signed lens,
source controls, rectangular aperture add/delete, order rejection and z rail
ghost/valid release/invalid release; camera controls change the camera while
leaving optics/API counts unchanged. Deterministic reset consumes prior damping.
Repeated identical simulations must finish with a new request ID; an existing
result cannot satisfy replacement acceptance. Held late responses after edits
stay separate, rapid intentional clicks submit once, missing/malformed replies
publish no fabricated result, reload remains passive, and real dark V0 results
stay black with null zero-incident ratios. Context loss/unsupported WebGL are
controlled presentation tests with no automatic numerical retry.

The independent HTTP tool checks **every** intensity/axis byte and each scalar
stage against a separate direct public V0 call. Normal browser checks compare
the echoed specification, maximum, stages and selected original readout.
Synthetic fixtures are display/transport evidence only: they are not optical
solutions. Independent 3×4 and 2×5 fixtures check actual 2D and WebGL grayscale
at corners/interior, real 3D picks, physical aspect and exact numerical readout.
Half-open edges/outside rejection are checked independently in unit tests;
no outside-to-sample clamping is permitted.

Actual Chrome 154.0.8037.95 reports WebGL2 through ANGLE/Intel Graphics/D3D11.
This is the actual reported rendering environment, not a hardware-performance
benchmark. All ordinary app-page nonloopback requests were blocked while
production load/simulation worked; zero external app requests were observed.
That claim excludes Chrome's own background traffic.

Intermediate gray measured GPU and 2D RGBA=[128,128,128,255]. GPU tolerance is
absolute 3 gray-byte levels, relative 0, to allow raster/readback quantization;
observed error was 0. This rejects the approximately 188 extra-transfer result.
2D gray and original float64 readout 5 are exact. Asymmetric GPU colors use the
same absolute 3/relative 0 allowance. z-drag's screen-gesture acceptance uses
absolute 5e-6 m / relative 0; this is pointer/projection tolerance, not V0 numerical
accuracy. Camera reset absolute tolerance is 5e-11 world units / relative 0. All
scientific HTTP arrays/stages use the explicit same-platform exactness claim.

Five predefined cycles exercise preset changes, add/delete, viewport resize
and two genuine result replacements per cycle. `browser_final/browser_resources.json`
records stable owned 8 geometries, 8 materials, 1 texture, 1 control, 6 listeners and 1 resize
observer; renderer observations are 8 geometries, 1 texture, 7 programs at each
comparable endpoint. Request IDs differ at each replacement. Internal caches
need not reach zero; this bounded sequence does not prove lifetime-wide absence
of leaks. Drawing buffers retain DPR<=2 and 4-million-pixel caps.

## Final measured HTTP behavior and input provenance

Imported public core: `C:\holographiclab\src\ohlab\optics\__init__.py`.
The final served assets match the owned final dist byte for byte. These timings
are single wall-clock observations of complete HTTP responses, not benchmarks
of continuous optics or GPU speed.

| Case | HTTP seconds | Direct V0 seconds | Frame bytes | Raw maximum |
|---|---:|---:|---:|---:|
| free | 0.1259405999444425 | 0.09330780000891536 | 2106592 | 0.860293298357317 |
| lens | 0.14589690003776923 | 0.11853289999999106 | 2106952 | 6.1575878701940825 |
| aperture_lens | 0.16093799995724112 | 0.13735810003709048 | 2107360 | 1.3783458121954204 |
| negative_lens | 0.16112279996741563 | 0.11443780001718551 | 2106952 | 0.24024616468451448 |
| observation_10mm | 0.15651490003801882 | 0.11731599998893216 | 2106952 | 3.44124584042096 |
| small_aperture | 0.19356689997948706 | 0.1428592999582179 | 2107408 | 0.13054174191396373 |
| dark | 0.12875530001474544 | 0.07905010000104085 | 2106488 | 0.0 |
| asymmetric_3x4 | 0.01753499999176711 | 0.0008063000277616084 | 1320 | 1.0 |
| asymmetric_2x5 | 0.027404799999203533 | 0.000487400044221431 | 1304 | 1.0 |
| max_eight | 0.7524846000014804 | 0.7050283999997191 | 2109792 | 1.5757041363201916 |

The earlier initial 40 µm fixture used literal 40e-6; the final editor-compatible
fixture uses 40*1e-6, exactly the disclosed editor SI conversion. Those floats
are 4e-5 and 3.9999999999999996e-5 respectively. An inclusive discrete hard-aperture
boundary can classify samples differently at that one-ULP boundary, so its
measured maximum changes from 0.13701204008458018 to 0.13054174191396373.
Both measurements and exact inputs remain recorded separately. No scientific
clamping, smoothing, normalization or unexplained replacement was introduced.

Largest measured eight-component frame is below 2.25 MiB; the 512² payload is
2,105,344 bytes. Header cap 16,384 plus prefix/alignment bounds the theoretical
frame to 2,121,744 bytes. Body cap 32,768 bytes, streamed request timeout 5 seconds,
grid 1..512/axis and 8 components are enforced before expensive construction.

## Detecting negative controls and production preservation

All nine controls ran selected green baselines then failed real assertions:
nm conversion, mm conversion, physical axis swap, vertical texture flip,
ignored optical edit, stale attachment, duplicate simulation, per-result
normalization hiding loss and plausible constant intensity replacing V0 output.
`negative_controls/summary.json` gives exact affected copied files/test titles;
each directory retains argv/cwd, mutation, baseline/mutant stdout/stderr/exit.
There were no setup/import failures counted as detections. All 211 tracked or
unignored files present then had unchanged hashes before/after; production was
never mutated and required no restoration. Complete suites were rerun afterward.

## Genuine screenshots and exact scope

All three are actual app captures with genuine returned V0 data, visually
reviewed. Cosmetic coplanar depth bias removes lens/aperture z-fighting without
changing physical/world positions or parameter order.

- `figures/fig01_bench_lens.png`: actual 512² positive lens, maximum 6.1575878701940825.
- `figures/fig02_aperture_result.png`: actual 80 µm aperture/lens, shared 0–10 range,
  retained full-window norm loss, maximum 1.3783458121954204.
- `figures/fig03_stale_result.png`: actual last 40 µm aperture result keeps original
 20 mm observation; invalid current edit detaches bench texture and disables solve.

`precommit_inventory.json` verifies exactly 44 paths, 167 protected files unchanged,
52 Python versions/metadata/source locations unchanged (including editable
PKG-INFO), unchanged reviewed lock hash and no unexpected paths. Source,
contracts, root exports, old tests/guards, Streamlit apps, engineering guides,
historical handoffs and environments are preserved.

Exact approved changed-path inventory:

```text
.gitignore
README.md
apps/virtual_bench/__init__.py
apps/virtual_bench/adapter.py
apps/virtual_bench/protocol.py
apps/virtual_bench/server.py
docs/handoffs/v1/code_map.md
docs/handoffs/v1/figures/fig01_bench_lens.png
docs/handoffs/v1/figures/fig02_aperture_result.png
docs/handoffs/v1/figures/fig03_stale_result.png
docs/handoffs/v1/implementation_summary.md
docs/handoffs/v1/known_limitations.md
docs/handoffs/v1/math_used.md
docs/handoffs/v1/tests_and_evidence.md
docs/handoffs/v1/tutor_context.md
docs/milestones.md
docs/roadmap.md
frontend/bench/index.html
frontend/bench/package-lock.json
frontend/bench/package.json
frontend/bench/playwright.config.ts
frontend/bench/src/contracts.ts
frontend/bench/src/detector.ts
frontend/bench/src/main.ts
frontend/bench/src/mapping.ts
frontend/bench/src/presets.ts
frontend/bench/src/scene.ts
frontend/bench/src/state.ts
frontend/bench/src/styles.css
frontend/bench/tests/bench.browser.spec.ts
frontend/bench/tests/detector.test.ts
frontend/bench/tests/mapping.test.ts
frontend/bench/tests/state.test.ts
frontend/bench/tests/transport.test.ts
frontend/bench/tsconfig.json
frontend/bench/vite.config.ts
frontend/bench/vitest.config.ts
pyproject.toml
scripts/v1_negative_controls.py
scripts/validate_v1_bench.py
tests/test_virtual_bench_adapter.py
tests/test_virtual_bench_architecture.py
tests/test_virtual_bench_protocol.py
tests/test_virtual_bench_server.py
```

## Retained unsuccessful attempts and limits

Original native-probe failure came from a helper assuming named exports on a
require-resolved CJS Playwright module; inspected actual default export and
corrected the helper without installation/tool repair. Sandbox Vite process
spawn EPERM was retried through ordinary approved execution permission. Earlier
agent first failures retained as transcripts are identified as transcripts.

Backend initial failures are retained in `runs/v1_backend_20261005_001/` and
`_002/`: legitimate internal Windows static-index separators, incorrectly
assumed pointwise aperture-peak decrease and overlong generated pytest IDs.
Only new V1 code/fixtures were corrected. Final focused 100 tests passed; the
retained full suite subsequently passed twice.

Browser attempts 1–3 retain failed fixture/click/language/reset assumptions:
sub-CSS-pixel 512-grid click, one-ULP editor conversion expectations, stale label
wording and genuine pending camera damping. Deterministic camera reset was
fixed; small-grid actual picking/GPU checks were strengthened. Attempt 4 retains
an unexplained worker exit 3221226505 before its gray case; no cause is inferred,
no tool/native repair or dependency change occurred. Attempts 5 and final passed
the complete production scenarios. Earlier Ctrl+C CLI shutdowns showed an
asyncio/KeyboardInterrupt traceback after orderly shutdown; the new V1 CLI now
handles that signal while retaining actual gate shutdown. Terminal Ctrl+C may
still report a tool-shell exit 1; that is not claimed as application exit 0.

Vite retains its >500 kB bundle warning. Playwright retains the inherited
NO_COLOR/FORCE_COLOR warning. Neither warning was hidden with global settings.
No browser download, dependency substitution, lifecycle enablement or other
environment repair occurred.

## Clean-postcommit publication boundary

At this documentation checkpoint, precommit acceptance is complete.
One approved commit follows the final diff/index review. Only owned dist is
then recreated from committed sources; lock/tracked state, source/served-asset
and fresh genuine browser/direct-V0 readout smoke must pass before normal push.
The resulting commit/live remote/GitHub API agreement and final clean state
belong in fresh ignored evidence and the completion report. They are not
predicted here and require no amendment of this milestone commit.
