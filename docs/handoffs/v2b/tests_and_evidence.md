# V2b tests and evidence

Recorded 2026-10-06. Accepted starting revision:
`a215da74cb0f85e8727bbbdffb6408da4d3df3d4`. Initial main was clean and
synchronized with live origin/main. Existing Windows-native project Python,
Node/npm and installed dependencies/lockfile are used unchanged. Evidence
below is freshly executed unless explicitly labelled earlier/intermediate.
Historical V1/V2a handoffs and figures are preserved and do not stand in for
current API/browser acceptance.

Raw argv, stdout, stderr and exit/timing are retained separately under
`runs/v2b_acceptance_20261006/`; structured actual HTTP/browser/fault records
are under its `acceptance/` child. These ignored records are diagnostic
provenance, not a new scientific archive/schema. Embedded stdout is unedited
text, with line endings normalized only for Markdown. Raw files preserve bytes.

## Unchanged baselines

### Python baseline

Working directory: `C:\holographiclab`. Exact argv/configuration:

```json
{
  "argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-X",
    "utf8",
    "-m",
    "pytest",
    "-q",
    "-p",
    "no:cacheprovider",
    "--basetemp=runs/v2b_acceptance_20261006/pytest_baseline",
    "-rs"
  ],
  "cwd": "C:\\holographiclab"
}
```

Exact stdout:

```text
........................................................................ [  3%]
........................................................................ [  7%]
........................................................................ [ 10%]
........................................................................ [ 14%]
........................................................................ [ 17%]
........................................................................ [ 21%]
........................................................................ [ 25%]
........................................................................ [ 28%]
........................................................................ [ 32%]
........................................................................ [ 35%]
........................................................................ [ 39%]
........................................................................ [ 43%]
........................................................................ [ 46%]
........................................................................ [ 50%]
........................................................................ [ 53%]
........................................................................ [ 57%]
........................................................................ [ 60%]
........................................................................ [ 64%]
..............................................................s......... [ 68%]
........................................................................ [ 71%]
........................................................................ [ 75%]
........................................................................ [ 78%]
........................................................................ [ 82%]
........................................................................ [ 86%]
........................................................................ [ 89%]
........................................................................ [ 93%]
........................................................................ [ 96%]
...............................................................          [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
2006 passed, 1 skipped in 110.00s (0:01:50)
```

Exit 0, empty stderr. The one unchanged skip is
`tests/test_run_artifacts.py:1101`: this Windows account lacks symlink privilege;
junction behavior is tested separately. No privilege elevation or test edit was
used to remove it. Total 2007 cases is the recorded baseline, not a test quota.

### Installed frontend baseline

Working directory: `C:\holographiclab\frontend\bench`. Exact argv/configuration:

```json
{
  "argv": [
    "C:\\Program Files\\nodejs\\npm.cmd",
    "run",
    "--ignore-scripts",
    "typecheck"
  ],
  "cwd": "C:\\holographiclab\\frontend\\bench"
}
```
```text

> ohlab-virtual-bench@0.1.0 typecheck
> tsc --noEmit
```
Working directory: `C:\holographiclab\frontend\bench`. Exact argv/configuration:

```json
{
  "argv": [
    "C:\\Program Files\\nodejs\\npm.cmd",
    "run",
    "--ignore-scripts",
    "test:unit",
    "--",
    "--no-cache"
  ],
  "cwd": "C:\\holographiclab\\frontend\\bench"
}
```
```text

> ohlab-virtual-bench@0.1.0 test:unit
> vitest run --no-cache


 RUN  v5.0.3 C:/holographiclab/frontend/bench


 Test Files  4 passed (4)
      Tests  65 passed (65)
   Start at  12:31:53
   Duration  899ms (import 62%, transform 21%, tests 14%, worker 3%)

    Isolate  4 workers spawned · ~113ms startup each (spawn + environment, per file)
             at least ~339ms faster with isolate: false — reuses workers across files instead of one per file
```

Both exit 0; respective stderr files remain available. The 65-test V1 unit
baseline is separate from historical V1 Chrome evidence and the current rerun.

## Retained/new Python and frontend

### First full Python suite

Working directory: `C:\holographiclab`. Exact argv/configuration:

```json
{
  "argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-X",
    "utf8",
    "-m",
    "pytest",
    "-q",
    "-p",
    "no:cacheprovider",
    "--basetemp=runs/v2b_acceptance_20261006/pytest_precommit",
    "-rs"
  ],
  "cwd": "C:\\holographiclab",
  "child_environment_overrides": {
    "PYTHONDONTWRITEBYTECODE": "1"
  }
}
```
```text
........................................................................ [  3%]
........................................................................ [  6%]
........................................................................ [ 10%]
........................................................................ [ 13%]
........................................................................ [ 17%]
........................................................................ [ 20%]
........................................................................ [ 24%]
........................................................................ [ 27%]
........................................................................ [ 31%]
........................................................................ [ 34%]
........................................................................ [ 38%]
........................................................................ [ 41%]
........................................................................ [ 45%]
........................................................................ [ 48%]
........................................................................ [ 51%]
........................................................................ [ 55%]
........................................................................ [ 58%]
........................................................................ [ 62%]
..............................................................s......... [ 65%]
........................................................................ [ 69%]
........................................................................ [ 72%]
........................................................................ [ 76%]
........................................................................ [ 79%]
........................................................................ [ 83%]
........................................................................ [ 86%]
........................................................................ [ 90%]
........................................................................ [ 93%]
........................................................................ [ 96%]
................................................................         [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
2079 passed, 1 skipped in 251.08s (0:04:11)
```

Exit 0; stderr empty. This 2079-pass measurement precedes final isolated controls
and restored-suite closeout. The separate final restored-suite result below preserves this earlier measurement.

### Final restored full Python suite

The restored production source remained unchanged through the isolated faults.
The complete suite was then rerun, retaining the same Windows skip:

Working directory: `C:\holographiclab`. Exact argv/configuration:

```json
{
  "argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-X",
    "utf8",
    "-m",
    "pytest",
    "-q",
    "-p",
    "no:cacheprovider",
    "--basetemp=runs/v2b_acceptance_20261006/pytest_restored_final",
    "-rs"
  ],
  "cwd": "C:\\holographiclab",
  "child_environment_overrides": {
    "PYTHONDONTWRITEBYTECODE": "1"
  }
}
```
```text
........................................................................ [  3%]
........................................................................ [  6%]
........................................................................ [ 10%]
........................................................................ [ 13%]
........................................................................ [ 17%]
........................................................................ [ 20%]
........................................................................ [ 24%]
........................................................................ [ 27%]
........................................................................ [ 31%]
........................................................................ [ 34%]
........................................................................ [ 38%]
........................................................................ [ 41%]
........................................................................ [ 45%]
........................................................................ [ 48%]
........................................................................ [ 51%]
........................................................................ [ 55%]
........................................................................ [ 58%]
........................................................................ [ 62%]
..............................................................s......... [ 65%]
........................................................................ [ 69%]
........................................................................ [ 72%]
........................................................................ [ 76%]
........................................................................ [ 79%]
........................................................................ [ 83%]
........................................................................ [ 86%]
........................................................................ [ 90%]
........................................................................ [ 93%]
........................................................................ [ 96%]
................................................................         [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
2079 passed, 1 skipped in 256.93s (0:04:16)
```

Exit 0, empty stderr. This is the final restored full-suite measurement, distinct
from the earlier 2079-pass first acceptance run. No scientific tolerance/test
change followed the camera-only browser fixture correction.

### Current final typecheck/unit batch

Working directory: `C:\holographiclab\frontend\bench`. Exact argv/configuration:

```json
{
  "argv": [
    "C:\\Program Files\\nodejs\\npm.cmd",
    "run",
    "--ignore-scripts",
    "typecheck"
  ],
  "cwd": "C:\\holographiclab\\frontend\\bench",
  "child_environment_overrides": {
    "PYTHONDONTWRITEBYTECODE": "1"
  }
}
```
```text

> ohlab-virtual-bench@0.1.0 typecheck
> tsc --noEmit
```
Working directory: `C:\holographiclab\frontend\bench`. Exact argv/configuration:

```json
{
  "argv": [
    "C:\\Program Files\\nodejs\\npm.cmd",
    "run",
    "--ignore-scripts",
    "test:unit",
    "--",
    "--no-cache"
  ],
  "cwd": "C:\\holographiclab\\frontend\\bench",
  "child_environment_overrides": {
    "PYTHONDONTWRITEBYTECODE": "1"
  }
}
```
```text

> ohlab-virtual-bench@0.1.0 test:unit
> vitest run --no-cache


 RUN  v5.0.3 C:/holographiclab/frontend/bench


 Test Files  7 passed (7)
      Tests  129 passed (129)
   Start at  12:57:19
   Duration  2.45s (import 55%, transform 21%, tests 20%, worker 4%)

    Isolate  7 workers spawned · ~185ms startup each (spawn + environment, per file)
             at least ~1.11s faster with isolate: false — reuses workers across files instead of one per file
```

Both exit 0. 129 tests in 7 files include the retained 65 plus new transport,
state, resource, signed-zero, dual-display atomic failure and delayed
selected-phase edit/mode race cases. No original unit assertion was weakened.

### Production build

Working directory: `C:\holographiclab\frontend\bench`. Exact argv/configuration:

```json
{
  "argv": [
    "C:\\Program Files\\nodejs\\npm.cmd",
    "run",
    "--ignore-scripts",
    "build"
  ],
  "cwd": "C:\\holographiclab\\frontend\\bench",
  "child_environment_overrides": {
    "PYTHONDONTWRITEBYTECODE": "1"
  }
}
```
```text

> ohlab-virtual-bench@0.1.0 build
> vite build

vite v8.3.2 building client environment for production...
transforming...
✓ 18 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.55 kB │ gzip:   0.37 kB
dist/assets/index-DEqdnGkW.css    7.18 kB │ gzip:   2.22 kB
dist/assets/index-CxC9Fft6.js   678.56 kB │ gzip: 177.26 kB

✓ built in 277ms
```

Exit 0. Exact stderr is retained in `precommit_build_final_stderr.txt`.
The reporter emitted the existing large-minified-chunk warning (>500kB).
No split/dependency/framework change was made to hide it. The earlier successful
build's separate output remains in `precommit_build_*`; its asset identity is
not attributed to this later build.

## Independent HTTP scientific/transport evidence

Working directory: `C:\holographiclab`. Exact argv/configuration:

```json
{
  "argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-X",
    "utf8",
    "scripts/validate_v2b_bench.py",
    "--output",
    "runs/v2b_acceptance_20261006/acceptance/api_evidence.json"
  ],
  "cwd": "C:\\holographiclab",
  "child_environment_overrides": {
    "PYTHONDONTWRITEBYTECODE": "1"
  }
}
```
```text
{
  "passed": true,
  "output": "runs\\v2b_acceptance_20261006\\acceptance\\api_evidence.json",
  "case_count": 18,
  "sweep_count": 3,
  "controlled_partial": null
}
```

Exit 0; empty stderr. `acceptance/api_evidence.json` captures 18 actual single
HTTP responses,3 actual 17-point sweeps, provenance and served asset hashes.
The validator independently decodes OHLAB2P and invokes unchanged public V0
sample_source/public V2a run_two_arm on identical complete submitted inputs.
It never imports the application encoder/decoder/adapter as its oracle.
All transported intensity cells, both coordinate arrays, ten norms and every
derived scalar matched exactly, not only selected pixels or visual appearance.
Browser editor inputs are captured once-converted values so 633*1e-9 is not
silently replaced by a separately rounded literal 633e-9.

Fixtures are equal-arm 0/pi/2/pi, signed/unwrapped extra phase, Gaussian and real
source/distance/phase edits, common phase, zero input, unequal carrier, asymmetric
3x4/2x5 physical grids, mixed evanescence,512x512 maximum, and both sides of
near-dark 0/pi. Direct exact comparisons preserve V2a residuals rather than
thresholding them. Analytic bound is rtol=2e-13 and atol=2e-13 scaled by input
intensity for images; fractions use rtol=atol=2e-13. These UI/integration bounds
do not weaken or modify the retained stricter V2a scientific tests.

| Measurement | Actual result |
|---|---:|
| Worst input-scaled analytic intensity discrepancy |5.551115123125783e-16|
| Common-phase worst absolute intensity discrepancy |2.220446049250313e-16|
| Unequal carrier port fractions |0.7499999999999993,0.24999999999999994|
| Mixed-evanescent total output/input |0.5372364078808002|
| Maximum 512x512 frame / strict route cap |4,204,360 /4,218,896 bytes|
| Maximum fixture header |1844 bytes|
| Uniform sweep endpoint fraction closure |2.002967142162725e-32|
| Unequal sweep endpoint fraction closure |4.440892098500626e-16|
| Lossy sweep endpoint fraction closure |1.1102230246251565e-16|

At±1e-4 from 0, the actual dark-port maximum is
2.4999999979166654e-9; at pi-1e-4 and pi+1e-4 it is respectively
2.4999999979333397e-9 and 2.4999999979210938e-9. Bright maxima remain
0.9999999974999998. Actual endpoint arrays/rows are retained independently;
no deduplication or forced bit identity is performed.
Sweep response sizes are 7354,7420 and 8047 bytes; measured request wall times
0.09889829996973276,0.09245499991811812 and 0.02830630005337298 seconds
respectively. These local timings do not establish universal performance.
The independently rederived upper bound uses 16-byte preamble +16384-byte
maximum aligned header +2*512*512*8 +2*512*8 =4,218,896 bytes.
Legacy success cap 2,359,296 bytes remains unchanged.

The same validator verifies request/domain/wire failures including 513-axis
rejection, non-loopback origin, oversized sweep grid and genuine finite 1e300
source amplitude causing numerical overflow with HTTP 422. It checks strict
schema/discriminator/identity/array roles/little-endian bytes/padding/no gaps/
finite values/common axes and complete payload length. Read-only validation
makes no sample/solver calls in independently counted adapter tests.

Current legacy API rerun used the original validator/assertions:

Working directory: `C:\holographiclab`. Exact argv/configuration:

```json
{
  "argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-X",
    "utf8",
    "scripts/validate_v1_bench.py",
    "--output",
    "runs/v2b_acceptance_20261006/acceptance/api_v1.json"
  ],
  "cwd": "C:\\holographiclab",
  "child_environment_overrides": {
    "PYTHONDONTWRITEBYTECODE": "1"
  }
}
```
```text
{
  "passed": true,
  "cases": 10,
  "output": "runs\\v2b_acceptance_20261006\\acceptance\\api_v1.json",
  "source_location": "C:\\holographiclab\\src\\ohlab\\optics\\__init__.py",
  "served_asset_sha256": {
    "/assets/index-vCZLBHdc.js": "e26619905e4315e2f346e300a3acf032f9a0109af35ba80ac4e78668c9298751",
    "/assets/index-DEqdnGkW.css": "1c120ef513f3ac629ee8b23d9bfb487ca52dadfd22345e1fc23aed3af18de8b8"
  }
}
```

All 10 direct V0 cases passed, with served assets/source locations verified.
This early asset report points to the earlier production build and remains
preserved separately. The final production asset/source refresh also passed:

Working directory: `C:\holographiclab`. Exact argv/configuration:

```json
{
  "argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-X",
    "utf8",
    "scripts/validate_v2b_bench.py",
    "--output",
    "runs/v2b_acceptance_20261006/acceptance/api_v2b_final.json"
  ],
  "cwd": "C:\\holographiclab",
  "child_environment_overrides": {
    "PYTHONDONTWRITEBYTECODE": "1"
  }
}
```
```text
{
  "passed": true,
  "output": "runs\\v2b_acceptance_20261006\\acceptance\\api_v2b_final.json",
  "case_count": 18,
  "sweep_count": 3,
  "controlled_partial": null
}
```
Working directory: `C:\holographiclab`. Exact argv/configuration:

```json
{
  "argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-X",
    "utf8",
    "scripts/validate_v1_bench.py",
    "--output",
    "runs/v2b_acceptance_20261006/acceptance/api_v1_final.json"
  ],
  "cwd": "C:\\holographiclab",
  "child_environment_overrides": {
    "PYTHONDONTWRITEBYTECODE": "1"
  }
}
```
```text
{
  "passed": true,
  "cases": 10,
  "output": "runs\\v2b_acceptance_20261006\\acceptance\\api_v1_final.json",
  "source_location": "C:\\holographiclab\\src\\ohlab\\optics\\__init__.py",
  "served_asset_sha256": {
    "/assets/index-CxC9Fft6.js": "f2e3823ad9d052a0befd351d3e03493af828a98e34068bd5f965ee8ed95f50e2",
    "/assets/index-DEqdnGkW.css": "1c120ef513f3ac629ee8b23d9bfb487ca52dadfd22345e1fc23aed3af18de8b8"
  }
}
```

Both exit 0, empty stderr; final actual V2b 18 single/3 sweep and legacy 10 cases
passed. Served JavaScript SHA256 is
f2e3823ad9d052a0befd351d3e03493af828a98e34068bd5f965ee8ed95f50e2;
CSS SHA256 is 1c120ef513f3ac629ee8b23d9bfb487ca52dadfd22345e1fc23aed3af18de8b8.
Both assets matched the checkout's final production build. Imported optics
sources belonged to C:\holographiclab\src; no copied fault module was served.
Final package/protected-file verification remains an explicit closeout gate.

## Production Chrome and actual failure lifetimes

Actual installed Chrome 154.0.8037.95 used WebGL2 via ANGLE/Intel Direct3D11.
Page requests were confined to the task-owned http://127.0.0.1:8510 service.
No hosted/mock screenshot or synthetic analytic image stands in for genuine
V2b numerical/browser results. The retained V1 synthetic transport/display
fixtures are still labelled synthetic and make no optical correctness claim.
The legacy spec has only the approved screenshot-location line changed;
all legacy assertions, case semantics and wire checks are retained.

The first ordinary production batch had 18 passes and 2 controlled skips.
Its exact output is retained as `precommit_browser_1_stdout.txt`; the new
asymmetric GPU acceptance added afterward is not retroactively claimed there.
The second batch preserved 17 passes,3 controlled skips and one failing new
camera setup (`precommit_browser_2_*`). A single perspective pan followed by
zoom approached the old orbit target behind the small detector plane; the
requested pixel was behind the camera. The first isolated correction then
passed focus but the next fixture retained the zoomed view and failed a raw
pick (`isolated_asymmetric_1_*`). These are new acceptance-camera setup errors,
not demonstrated numerical/GPU mapping faults and not counted negative-control
detections. Correction uses only real camera gestures in orthogonal views,
then resets the view between fixtures. All 44 original raw/2D grayscale samples
and 12 actual WebGL samples remain, with the same RGB tolerance 3.

Corrected isolated actual-browser result:

Working directory: `C:\holographiclab\frontend\bench`. Exact argv/configuration:

```json
{
  "argv": [
    "C:\\Program Files\\nodejs\\npm.cmd",
    "run",
    "--ignore-scripts",
    "test:browser",
    "--",
    "tests/two_path.browser.spec.ts",
    "--grep=asymmetric actual port arrays",
    "--output=../../runs/v2b_acceptance_20261006/acceptance/isolated_asymmetric_2/screens"
  ],
  "cwd": "C:\\holographiclab\\frontend\\bench",
  "child_environment_overrides": {
    "PYTHONDONTWRITEBYTECODE": "1",
    "V2B_EVIDENCE_DIR": "runs/v2b_acceptance_20261006/acceptance/isolated_asymmetric_2",
    "V2B_API_EVIDENCE": "runs/v2b_acceptance_20261006/acceptance/api_evidence.json",
    "V2B_FIGURE_DIR": "docs/handoffs/v2b/figures"
  }
}
```
```text

> ohlab-virtual-bench@0.1.0 test:browser
> playwright test tests/two_path.browser.spec.ts --grep=asymmetric actual port arrays --output=../../runs/v2b_acceptance_20261006/acceptance/isolated_asymmetric_2/screens


Running 1 test using 1 worker

  ok 1 tests\two_path.browser.spec.ts:193:1 › asymmetric actual port arrays preserve common transverse axes aspect and unlit shared grayscale (20.8s)

  1 passed (22.3s)
```

Exit 0. Its stderr preserves the Node NO_COLOR/FORCE_COLOR warning.
The final whole production-browser rerun then passed:

Working directory: `C:\holographiclab\frontend\bench`. Exact argv/configuration:

```json
{
  "argv": [
    "C:\\Program Files\\nodejs\\npm.cmd",
    "run",
    "--ignore-scripts",
    "test:browser",
    "--",
    "--output=../../runs/v2b_acceptance_20261006/acceptance/browser_3/screens"
  ],
  "cwd": "C:\\holographiclab\\frontend\\bench",
  "child_environment_overrides": {
    "PYTHONDONTWRITEBYTECODE": "1",
    "V1_EVIDENCE_DIR": "runs/v2b_acceptance_20261006/acceptance/legacy_browser_3",
    "V1_API_EVIDENCE": "../api_v1_final.json",
    "V1_FIGURE_DIR": "runs/v2b_acceptance_20261006/acceptance/v1_figures_3",
    "V2B_EVIDENCE_DIR": "runs/v2b_acceptance_20261006/acceptance/browser_3",
    "V2B_API_EVIDENCE": "runs/v2b_acceptance_20261006/acceptance/api_v2b_final.json",
    "V2B_FIGURE_DIR": "docs/handoffs/v2b/figures"
  }
}
```
```text

> ohlab-virtual-bench@0.1.0 test:browser
> playwright test --output=../../runs/v2b_acceptance_20261006/acceptance/browser_3/screens


Running 21 tests using 1 worker

  ok  1 tests\bench.browser.spec.ts:55:1 › production V0 lens/readout smoke and local-only assets (1.5s)
  ok  2 tests\bench.browser.spec.ts:74:1 › camera selection color resize and 3D picking do not alter optics or call API (3.3s)
  ok  3 tests\bench.browser.spec.ts:117:1 › real edits change V0 output; aperture uses shared limits and original norm loss; stale screenshot (4.0s)
  ok  4 tests\bench.browser.spec.ts:138:1 › source fields signed lens rectangle add delete numeric order and z ghost rail (3.4s)
  ok  5 tests\bench.browser.spec.ts:174:1 › rapid submissions remain single and edited pending response stays separately stale (1.3s)
  ok  6 tests\bench.browser.spec.ts:190:1 › malformed response and missing backend publish no fabricated success; reload passive; dark genuine (1.9s)
  ok  7 tests\bench.browser.spec.ts:226:1 › independent gray fixture catches extra gamma in actual WebGL and preserves raw float64 (1.0s)
  ok  8 tests\bench.browser.spec.ts:249:1 › independent asymmetric 3x4 and 2x5 display cells and original readouts (4.5s)
  ok  9 tests\bench.browser.spec.ts:294:1 › context loss and unsupported WebGL report presentation failure without automatic solve (1.6s)
  ok 10 tests\bench.browser.spec.ts:313:1 › predefined resource replacement sequence retains one active texture and bounded owned resources (8.6s)
  -  11 tests\bench.browser.spec.ts:329:1 › actual browser disconnect keeps running worker busy until controlled completion
  ok 12 tests\two_path.browser.spec.ts:144:1 › genuine dual known phases and both original readouts use one submitted V2a result (9.4s)
  ok 13 tests\two_path.browser.spec.ts:175:1 › real Gaussian source distance phase edits preserve shared scale and original input diagnostics (10.4s)
  ok 14 tests\two_path.browser.spec.ts:193:1 › asymmetric actual port arrays preserve common transverse axes aspect and unlit shared grayscale (21.5s)
  ok 15 tests\two_path.browser.spec.ts:234:1 › presentation controls never calculate and scientific edits detach both textures immediately (3.5s)
  ok 16 tests\two_path.browser.spec.ts:255:1 › rapid genuine submissions and away-back mode changes reject held cross-mode attachments (2.9s)
  ok 17 tests\two_path.browser.spec.ts:273:1 › real dark outputs malformed error recovery signed-zero policy and passive reload (5.2s)
  ok 18 tests\two_path.browser.spec.ts:300:1 › real seventeen-point sweep displays actual markers with no chart-click computation (3.0s)
  -  19 tests\two_path.browser.spec.ts:315:1 › controlled partial failure retains only genuine prefix and never labels sweep complete
  -  20 tests\two_path.browser.spec.ts:331:1 › actual two-path browser disconnect holds all numerical routes until genuine worker completion
  ok 21 tests\two_path.browser.spec.ts:374:1 › context loss preserves numerical completion and repeated mode replacement ownership is bounded (14.5s)

  3 skipped
  18 passed (1.7m)
```

Exact stderr:

```text
(node:34556) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
```

Exit 0; wall time 105.567923399969 seconds. All 10 retained V1 and 8 V2b ordinary
cases passed. The 3 skipped controlled cases require separate child-service
harness modes; the independently executed partial/disconnect results below
supply those actual checks, rather than treating skipped cases as passed.
This final batch regenerated all three approved genuine UI screenshots;
previous versions were preserved separately in ignored evidence. Files are
fig01_dual_outputs.png, fig02_phase_sweep.png and fig03_stale_cross_mode.png.
The stale capture expands the separately labelled original request/specification
and prior images after verifying both current textures are detached.

### Genuine partial sweep failure

The ignored controlled helper uses the real production app/gate and monkeypatches
only the child's app runner alias. Each sweep resets its own counter; first 3
public calls/results are genuine, the fourth wrapper raises before numerical
work. It provides no production fault endpoint. Independent direct API evidence
and genuine Chrome each inspect 422, status failed, genuine contiguous 3-row
prefix, failed_index 3, requested_count 17, bounded error and unmistakable failed/
partial label. No row is fabricated or missing point connected as complete.

Working directory: `C:\holographiclab`. Exact argv/configuration:

```json
{
  "argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-X",
    "utf8",
    "scripts/validate_v2b_bench.py",
    "--controlled-partial-index",
    "3",
    "--output",
    "runs/v2b_acceptance_20261006/acceptance/partial_api_1.json"
  ],
  "cwd": "C:\\holographiclab",
  "child_environment_overrides": {
    "PYTHONDONTWRITEBYTECODE": "1"
  }
}
```
```text
{
  "passed": true,
  "output": "runs\\v2b_acceptance_20261006\\acceptance\\partial_api_1.json",
  "case_count": 0,
  "sweep_count": 0,
  "controlled_partial": 3
}
```
Working directory: `C:\holographiclab\frontend\bench`. Exact argv/configuration:

```json
{
  "argv": [
    "C:\\Program Files\\nodejs\\npm.cmd",
    "run",
    "--ignore-scripts",
    "test:browser",
    "--",
    "tests/two_path.browser.spec.ts",
    "--grep=controlled partial failure",
    "--output=../../runs/v2b_acceptance_20261006/acceptance/browser_partial_1/screens"
  ],
  "cwd": "C:\\holographiclab\\frontend\\bench",
  "child_environment_overrides": {
    "PYTHONDONTWRITEBYTECODE": "1",
    "V2B_EVIDENCE_DIR": "runs/v2b_acceptance_20261006/acceptance/browser_partial_1",
    "V2B_API_EVIDENCE": "runs/v2b_acceptance_20261006/acceptance/api_evidence.json",
    "V2B_PARTIAL_ONLY": "1",
    "V2B_PARTIAL_EVIDENCE": "runs/v2b_acceptance_20261006/acceptance/partial_api_1.json"
  }
}
```
```text

> ohlab-virtual-bench@0.1.0 test:browser
> playwright test tests/two_path.browser.spec.ts --grep=controlled partial failure --output=../../runs/v2b_acceptance_20261006/acceptance/browser_partial_1/screens


Running 1 test using 1 worker

  ok 1 tests\two_path.browser.spec.ts:256:1 › controlled partial failure retains only genuine prefix and never labels sweep complete (2.7s)

  1 passed (4.0s)
```

Both exit 0; actual API reply is retained at `acceptance/partial_api_1.json`.

### Actual browser disconnect

The disposable child helper holds an actual operation before its numerical
work, exposes task-owned filesystem start/release/completion markers, then
executes the genuine worker. A real page is closed while it runs; a second real
page validates and probes all numerical routes. Busy 409 persists until observed
worker completion; health/validation stay responsive; a later deliberate dual
operation matches the public V2a oracle. Closing a page is an attachment
interruption, not a scientific success/failure response. Cases were separately
executed for sequential, dual and sweep; actual runner counts are 1,1 and 17.

Working directory: `C:\holographiclab\frontend\bench`. Exact argv/configuration:

```json
{
  "server_argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-X",
    "utf8",
    "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\controlled_acceptance_server.py",
    "--mode",
    "disconnect",
    "--operation",
    "sequential",
    "--evidence-dir",
    "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_sequential_1"
  ],
  "server_pid": 32352,
  "browser_argv": [
    "C:\\Program Files\\nodejs\\npm.cmd",
    "run",
    "--ignore-scripts",
    "test:browser",
    "--",
    "tests/bench.browser.spec.ts",
    "--grep=actual browser disconnect",
    "--output=C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_sequential_1\\screens"
  ],
  "cwd": "C:\\holographiclab\\frontend\\bench",
  "child_overrides": {
    "V1_EVIDENCE_DIR": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_sequential_1\\browser_v1",
    "V1_API_EVIDENCE": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\api_v1.json",
    "V1_FIGURE_DIR": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_sequential_1\\unused_figures",
    "V2B_EVIDENCE_DIR": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_sequential_1\\browser_v2b",
    "V2B_API_EVIDENCE": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\api_evidence.json",
    "V1_CANCELLATION_DIR": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_sequential_1"
  }
}
```
```text

> ohlab-virtual-bench@0.1.0 test:browser
> playwright test tests/bench.browser.spec.ts --grep=actual browser disconnect --output=C:\holographiclab\runs\v2b_acceptance_20261006\acceptance\disconnect_sequential_1\screens


Running 1 test using 1 worker

  ok 1 tests\bench.browser.spec.ts:329:1 › actual browser disconnect keeps running worker busy until controlled completion (2.1s)

  1 passed (3.3s)
```
Working directory: `C:\holographiclab\frontend\bench`. Exact argv/configuration:

```json
{
  "server_argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-X",
    "utf8",
    "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\controlled_acceptance_server.py",
    "--mode",
    "disconnect",
    "--operation",
    "dual",
    "--evidence-dir",
    "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_dual_2"
  ],
  "server_pid": 46440,
  "browser_argv": [
    "C:\\Program Files\\nodejs\\npm.cmd",
    "run",
    "--ignore-scripts",
    "test:browser",
    "--",
    "tests/two_path.browser.spec.ts",
    "--grep=actual two-path browser disconnect",
    "--output=C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_dual_2\\screens"
  ],
  "cwd": "C:\\holographiclab\\frontend\\bench",
  "child_overrides": {
    "V1_EVIDENCE_DIR": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_dual_2\\browser_v1",
    "V1_API_EVIDENCE": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\api_v1.json",
    "V1_FIGURE_DIR": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_dual_2\\unused_figures",
    "V2B_EVIDENCE_DIR": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_dual_2\\browser_v2b",
    "V2B_API_EVIDENCE": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\api_evidence.json",
    "V2B_DISCONNECT_ONLY": "1",
    "V2B_DISCONNECT_DIR": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_dual_2",
    "V2B_DISCONNECT_OPERATION": "dual"
  }
}
```
```text

> ohlab-virtual-bench@0.1.0 test:browser
> playwright test tests/two_path.browser.spec.ts --grep=actual two-path browser disconnect --output=C:\holographiclab\runs\v2b_acceptance_20261006\acceptance\disconnect_dual_2\screens


Running 1 test using 1 worker

  ok 1 tests\two_path.browser.spec.ts:298:1 › actual two-path browser disconnect holds all numerical routes until genuine worker completion (5.3s)

  1 passed (6.8s)
```
Working directory: `C:\holographiclab\frontend\bench`. Exact argv/configuration:

```json
{
  "server_argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-X",
    "utf8",
    "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\controlled_acceptance_server.py",
    "--mode",
    "disconnect",
    "--operation",
    "sweep",
    "--evidence-dir",
    "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_sweep_2"
  ],
  "server_pid": 43376,
  "browser_argv": [
    "C:\\Program Files\\nodejs\\npm.cmd",
    "run",
    "--ignore-scripts",
    "test:browser",
    "--",
    "tests/two_path.browser.spec.ts",
    "--grep=actual two-path browser disconnect",
    "--output=C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_sweep_2\\screens"
  ],
  "cwd": "C:\\holographiclab\\frontend\\bench",
  "child_overrides": {
    "V1_EVIDENCE_DIR": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_sweep_2\\browser_v1",
    "V1_API_EVIDENCE": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\api_v1.json",
    "V1_FIGURE_DIR": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_sweep_2\\unused_figures",
    "V2B_EVIDENCE_DIR": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_sweep_2\\browser_v2b",
    "V2B_API_EVIDENCE": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\api_evidence.json",
    "V2B_DISCONNECT_ONLY": "1",
    "V2B_DISCONNECT_DIR": "C:\\holographiclab\\runs\\v2b_acceptance_20261006\\acceptance\\disconnect_sweep_2",
    "V2B_DISCONNECT_OPERATION": "sweep"
  }
}
```
```text

> ohlab-virtual-bench@0.1.0 test:browser
> playwright test tests/two_path.browser.spec.ts --grep=actual two-path browser disconnect --output=C:\holographiclab\runs\v2b_acceptance_20261006\acceptance\disconnect_sweep_2\screens


Running 1 test using 1 worker

  ok 1 tests\two_path.browser.spec.ts:298:1 › actual two-path browser disconnect holds all numerical routes until genuine worker completion (5.6s)

  1 passed (6.9s)
```

All exit 0. Fresh markers, raw child-service logs and service-closed proofs are
kept alongside these capture files. Earlier incomplete orchestration records
remain separate and do not replace these passed checks.

## Isolated deliberate faults

The harness copies integration source/tests into owned ignored directories.
Each selected original regression must pass, the deliberate copied mutation
must fail the named identifying assertion, exact source bytes are restored,
and the same restored regression must pass. Setup/import/timeouts are failures
of the harness, not successful fault detection. Production source/test hashes
are compared before and after; no production server/browser is launched or
implementation mutated by this script. Python uses the existing repository
interpreter and checks copied integration import location after pytest plugin
rewrite. Frontend uses the existing Vitest/Three packages, never installs.

| Category / variants | Identifying assertion |
|---|---|
| Phase / distance UI unit error |UNIT_PHASE_DETECTED / UNIT_DISTANCE_DETECTED|
| Port swap |PORT_SWAP_DETECTED|
| Duplicate second output |DUPLICATE_PORT_DETECTED|
| Ignored relative phase |IGNORE_PHASE_DETECTED|
| Surviving-output denominator |INPUT_DENOMINATOR_DETECTED|
| Independent port normalization |SHARED_RANGE_DETECTED|
| Only one texture invalidated |BOTH_TEXTURES_INVALIDATED|
| Away/back stale attachment |CROSS_MODE_STALE_DETECTED|
| Duplicate single / sweep invocation |SINGLE_CALL_COUNT_DETECTED / SWEEP_CALL_COUNT_DETECTED|
| Fabricated analytic sweep rows |FABRICATED_SWEEP_DETECTED|
| Premature gate release after disconnect |GATE_ABORT_DETECTED|
| Extra atomic second-texture failure |ATOMIC_SECOND_TEXTURE_DETECTED|

The fabricated-row fault still makes 17 solver calls but substitutes unit-survival
cos-squared/sin-squared rows for the unequal-carrier outputs. Independent actual
row assertions fail; counting alone cannot establish scalar correctness. The
unit tests separately reject call replacement/deduplication and require actual
17 calls, including independent endpoint calls. The texture-detachment fault
uses actual BenchScene.prototype and real Three materials/textures without
WebGL, so leaving the second material map attached is detected directly.
Atomic-second-resource tests also inject canvas/commit failures, require cleanup,
retain prior result and numerical completion, and prohibit automatic submission.

First run `acceptance/negative_controls_1` stopped at Windows Vitest child-spawn
EPERM before any mutant;0 detections, production unchanged. Normal approved
execution permission was then used for existing child processes. Second run
`negative_controls_2` detected 13 variants/restored them, then its unmutated gate
baseline stopped on PytestAssertRewriteWarning for AnyIO imported before plugin
rewrite (warnings-as-errors remains enabled). That warning is not counted as a
fault detection. Moving only the copied source-location probe into pytest's
post-plugin configure hook fixed the harness setup. Both failed outputs remain.
No dependency, tolerance or production fix was used to obtain the final run.

Final fresh run:

Working directory: `C:\holographiclab`. Exact argv/configuration:

```json
{
  "argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-X",
    "utf8",
    "scripts/v2b_negative_controls.py",
    "--output-dir",
    "runs/v2b_acceptance_20261006/acceptance/negative_controls_3"
  ],
  "cwd": "C:\\holographiclab",
  "child_environment_overrides": {}
}
```
```text
phase_unit_conversion: baseline=0, mutant=1, intended_assertion=True, restored=0
distance_unit_conversion: baseline=0, mutant=1, intended_assertion=True, restored=0
independent_port_normalization: baseline=0, mutant=1, intended_assertion=True, restored=0
only_one_texture_detached: baseline=0, mutant=1, intended_assertion=True, restored=0
cross_mode_stale_attachment: baseline=0, mutant=1, intended_assertion=True, restored=0
atomic_second_texture_failure: baseline=0, mutant=1, intended_assertion=True, restored=0
port_swap: baseline=0, mutant=1, intended_assertion=True, restored=0
duplicate_second_output: baseline=0, mutant=1, intended_assertion=True, restored=0
ignored_phase: baseline=0, mutant=1, intended_assertion=True, restored=0
surviving_output_denominator: baseline=0, mutant=1, intended_assertion=True, restored=0
duplicate_single_runner: baseline=0, mutant=1, intended_assertion=True, restored=0
duplicate_sweep_runner: baseline=0, mutant=1, intended_assertion=True, restored=0
fabricated_analytic_sweep_rows: baseline=0, mutant=1, intended_assertion=True, restored=0
premature_abort_gate_release: baseline=0, mutant=1, intended_assertion=True, restored=0
production_unchanged=True; detected=14/14
```

Exit 0; empty stderr;14/14 variants across 12 categories detected, every copied
restoration passed, production_unchanged=True. Exact per-child argv/environment
(nonsecret overrides only), stdout/stderr/exit, fault source descriptions and
before/after hashes are kept in `acceptance/negative_controls_3/`. No complete
environment dump, credentials or persistent setting modification occurred.

Reproduce with a fresh ignored destination (existing output is never overwritten):

```powershell
.\.venv\Scripts\python.exe -B -X utf8 scripts\v2b_negative_controls.py --output-dir runs\v2b_acceptance_20261006\acceptance\negative_controls_fresh
```

## Ownership, preservation and pending publication

Deterministic real-browser cycles include sequential-to-dual mode changes,
repeated dual results, actual sweep replacement, resizing, shared ranges and
stale detachment. Unit cases directly verify second-resource cleanup and owned
buffer accounting. The 16 MiB persistent/32 MiB transient budgets count retained
arrays/axes/scalar data and owned display/transport preparation; they exclude
total JS heap, process/GPU memory and internal renderer caches. A failed atomic
presentation may retain new completed numerical data and the old recoverable
result as an explicitly counted bounded exception. No unbounded history grows.
Fresh `acceptance/browser_3/browser_dual_resources_and_context_loss.json`
records four real ownership cycles: each active dual result has 15 geometries,
15 materials and 2 owned textures; stale detachment leaves 0 textures while the
geometry/material counts remain bounded at 15. Controls 1, event listeners 6 and
resize observers 1 remain constant. This records application ownership, not a
claim that renderer cache/GPU/tab memory becomes zero. Context-loss completion
preserves numerical state, reports presentation error and triggers 0 new
numerical requests in its monitored recovery section.

Protected tracked-file and installed-distribution inventories were captured
before edits. Current comparison in `inventory_intermediate_2.json` confirms 217 protected
pre-existing tracked files have no changes, packages/metadata and Node versions
are unchanged, and lockfile SHA256 remains
d04f0937f5593e57c8e290cf812dba70db14dab4fccae4879d3e088c23cd7f91.
The starting distribution inventory has 53 metadata entries for 52 package names.
Final strict `inventory_precommit.json` confirms all 36 approved changed paths
(12 modifications, 24 creations) are present, with no unexpected path; all 217
protected files and the same package/metadata/source inventories remain
unchanged. Before staging, branch remains expected main with 0/0 divergence,
HEAD remains the accepted baseline, index is empty and git diff --check passes.
No numerical/scientific test, historical handoff, dependency or lockfile
alteration is hidden by the allowlist.

After the approved single commit, rebuild assets from committed sources with
the existing packages, verify clean tracked state/source/served assets, and run
fresh V1/V2b Chrome smoke using V1_SMOKE=1 and V2B_SMOKE=1 plus fresh evidence
paths. The V2b smoke performs one actual 17-point sweep and checks both original
readouts/complete specification against the independent direct public V2a
capture. Close task-owned browsers/services and recheck ports. Push only after
these checks; record matching local/live-origin/GitHub API SHA and final clean
state in ignored publication evidence and completion report. No successful
commit/push/postcommit result is predicted here. V2c/later work is not started.
