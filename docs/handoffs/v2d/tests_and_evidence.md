# V2d tests and evidence

Recorded 2026-10-12. Accepted starting commit:
`ff669ab683bcf7b07b4a8ff9073c8557dc6ad1b8`.
This document records executed precommit acceptance, including failed attempts.
All capture paths below are relative to the fresh, owned, ignored directory
`runs/v2d_acceptance_20261012_01/` unless a repository path is explicit.
`*_command.json` contains the exact argument vector and working directory;
`*_exit.json` records exit code and elapsed time; `*_stdout.txt` and
`*_stderr.txt` preserve original bytes. Embedded output blocks are copied
directly from those files without rewriting counts or diagnostic text.

Before implementation, main was clean and synchronized with origin/main;
HEAD and live remote matched the accepted baseline, ahead/behind 0/0.
The baseline inventory covered 271 tracked files and 53 installed distribution
entries, including versions, locations and metadata hashes. Python was the
existing Windows-native `C:\holographiclab\.venv\Scripts\python.exe`, version
3.11.9. No environment was recreated, dependency installed or upgraded, global
Git setting changed, or prior numerical source/history rewritten.

The full final Python result is **2523 passed, 1 skipped**. Final frontend
units are **186 passed**; the full production browser attempt passed **28**
with **5** dedicated controlled cases intentionally skipped. Those controls
were then explicitly run as **12 separate passing browser invocations**.
All **26 isolated fault variants**, covering **21 categories**, produced the
intended assertions and passed after exact restoration. These are distinct
executions and counts, not interchangeable definitions of coverage.

## Baseline and final suites

The Python captures disable bytecode and pytest cache writes and redirect
temporary files to owned evidence. The existing Windows symlink-privilege skip
was preserved; junction coverage remains separate.

### Baseline full Python suite

Capture: `baseline_*`; exit 0.

Cwd: `C:\holographiclab`.

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' '-B' '-m' 'pytest' '-q' '-p' 'no:cacheprovider' '--basetemp' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\baseline_tmp' '-rs'
```

Unedited full stdout:

```text
........................................................................ [  3%]
........................................................................ [  6%]
........................................................................ [  9%]
........................................................................ [ 12%]
........................................................................ [ 15%]
........................................................................ [ 18%]
........................................................................ [ 21%]
........................................................................ [ 24%]
........................................................................ [ 27%]
........................................................................ [ 30%]
........................................................................ [ 33%]
........................................................................ [ 36%]
........................................................................ [ 39%]
........................................................................ [ 42%]
........................................................................ [ 45%]
........................................................................ [ 48%]
........................................................................ [ 51%]
........................................................................ [ 54%]
........................................................................ [ 58%]
........................................................................ [ 61%]
........................................................................ [ 64%]
........................................................................ [ 67%]
...................................................s.................... [ 70%]
........................................................................ [ 73%]
........................................................................ [ 76%]
........................................................................ [ 79%]
........................................................................ [ 82%]
........................................................................ [ 85%]
........................................................................ [ 88%]
........................................................................ [ 91%]
........................................................................ [ 94%]
........................................................................ [ 97%]
.....................................................                    [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
2356 passed, 1 skipped in 176.00s (0:02:55)
```

Stderr: empty (0 bytes).

### Baseline frontend typecheck

Capture: `frontend_typecheck_baseline_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/typescript/bin/tsc' '--noEmit'
```

Stdout: empty (0 bytes).

Stderr: empty (0 bytes).

### Baseline unit runner permission failure

`frontend_unit_baseline` exited 1 before any tests ran: seven worker setup
errors reported child-process spawn EPERM. This is an execution-permission
failure, not a failing scientific assertion. The original logs were retained.
The normal permission retry kept installed tools, tests, assertions and worker
policy. No dependency installation or isolation-policy change followed the
runner's advisory output.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/vitest/vitest.mjs' 'run' '--config' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\vitest.baseline.config.mjs'
```

| Preserved original stream | Bytes | SHA-256 |
|---|---:|---|
| `frontend_unit_baseline_stdout.txt` | 156 | `14993a069eeae561f3b29404b4c617cbd4909d3a5662cb22874a1838423982e5` |
| `frontend_unit_baseline_stderr.txt` | 13974 | `cc189d93db478c0d871f50af725432905872bb83a6a50ea80816fe32f4e3c72f` |

### Baseline frontend units after normal permission retry

Capture: `frontend_unit_baseline_retry_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/vitest/vitest.mjs' 'run' '--config' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\vitest.baseline.config.mjs'
```

Unedited full stdout:

```text

 RUN  v5.0.3 C:/holographiclab/frontend/bench


 Test Files  7 passed (7)
      Tests  129 passed (129)
   Start at  12:04:50
   Duration  2.61s (import 56%, transform 21%, tests 18%, worker 5%)

    Isolate  7 workers spawned · ~206ms startup each (spawn + environment, per file)
             at least ~1.24s faster with isolate: false — reuses workers across files instead of one per file

```

Stderr: empty (0 bytes).

The owned `vitest.baseline.config.mjs` and
`vitest.frontend_work.config.mjs` retain Node environment,
`tests/**/*.test.ts`, and `maxWorkers: 1`. Only the cache destination is
redirected into the owned capture tree. Advice about disabling isolation was
not adopted.

`final_suite2` is the authoritative final Python run, after four additional
standalone sweep angle-type regressions. The earlier successful
`final_suite` remains preserved:
`2519 passed, 1 skipped in 168.32s (0:02:48)`.
Neither run changed or bypassed the symlink skip.

### Final complete Python suite

Capture: `final_suite2_*`; exit 0.

Cwd: `C:\holographiclab`.

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' '-B' '-m' 'pytest' '-q' '-p' 'no:cacheprovider' '--basetemp' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\final_tmp2' '-rs'
```

Unedited full stdout:

```text
........................................................................ [  2%]
........................................................................ [  5%]
........................................................................ [  8%]
........................................................................ [ 11%]
........................................................................ [ 14%]
........................................................................ [ 17%]
........................................................................ [ 19%]
........................................................................ [ 22%]
........................................................................ [ 25%]
........................................................................ [ 28%]
........................................................................ [ 31%]
........................................................................ [ 34%]
........................................................................ [ 37%]
........................................................................ [ 39%]
........................................................................ [ 42%]
........................................................................ [ 45%]
........................................................................ [ 48%]
........................................................................ [ 51%]
........................................................................ [ 54%]
........................................................................ [ 57%]
........................................................................ [ 59%]
........................................................................ [ 62%]
...................................................s.................... [ 65%]
........................................................................ [ 68%]
........................................................................ [ 71%]
........................................................................ [ 74%]
........................................................................ [ 77%]
........................................................................ [ 79%]
........................................................................ [ 82%]
........................................................................ [ 85%]
........................................................................ [ 88%]
........................................................................ [ 91%]
........................................................................ [ 94%]
........................................................................ [ 96%]
........................................................................ [ 99%]
....                                                                     [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
2523 passed, 1 skipped in 240.61s (0:04:00)
```

Stderr: empty (0 bytes).

### Final complete frontend units

Capture: `frontend_unit_final_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/vitest/vitest.mjs' 'run' '--config' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\vitest.frontend_work.config.mjs'
```

Unedited full stdout:

```text

 RUN  v5.0.3 C:/holographiclab/frontend/bench


 Test Files  10 passed (10)
      Tests  186 passed (186)
   Start at  12:47:40
   Duration  2.25s (import 59%, tests 19%, transform 18%, worker 3%)

    Isolate  10 workers spawned · ~109ms startup each (spawn + environment, per file)
             at least ~985ms faster with isolate: false — reuses workers across files instead of one per file

```

Stderr: empty (0 bytes).

### Final frontend typecheck

Capture: `frontend_typecheck_final4_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/typescript/bin/tsc' '--noEmit'
```

Stdout: empty (0 bytes).

Stderr: empty (0 bytes).

### Final production build

Capture: `frontend_build_precommit4_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\npm.cmd' 'run' '--ignore-scripts' 'build'
```

Unedited full stdout:

```text

> ohlab-virtual-bench@0.1.0 build
> vite build

vite v8.3.2 building client environment for production...
transforming...
✓ 22 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.55 kB │ gzip:   0.38 kB
dist/assets/index-D3ozh25N.css    8.58 kB │ gzip:   2.46 kB
dist/assets/index-Csv-NYm8.js   740.94 kB │ gzip: 190.62 kB

✓ built in 305ms
```

Unedited full stderr:

```text
[plugin builtin:vite-reporter] 
(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rolldownOptions.output.codeSplitting to improve chunking: https://rolldown.rs/reference/OutputOptions.codeSplitting
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
```

The existing large-bundle warning remains an acknowledged limitation.
No dependency update, warning suppression or unrelated bundle refactor was
performed. The final built frontend contains `index-Csv-NYm8.js` and
`index-D3ozh25N.css`.

## Preserved development failures and bounded corrections

These failures are separate from final suites and deliberate fault controls.
Their original command, exit and log files remain; no historical capture was
overwritten.

- `backend_focused01`: 96 passed in 1.39s.
- `backend_focused02`: 28 failed, 131 passed in 3.22s. New server-test fixtures
  initially compared legacy operation request IDs against the polarization
  request ID, and expected 403 for a rejected Host where the existing server
  returns 400. New fixture expectations were corrected to actual submitted
  identity and unchanged host/origin behavior; security was not relaxed.
  `backend_focused03` then passed 159 tests in 2.84s; later architecture and
  lifetime additions passed 169 in `backend_focused05` (2.32s).
  `backend_legacy_gate` passed 75 unchanged legacy server/architecture tests
  in 2.47s.
- `frontend_unit_work`: one failed, 180 passed. The new resource fixture
  initially counted mutually exclusive old/current canvas stores together in
  persistent retention, obtaining 17543168 bytes against 16777216. It was
  corrected to follow actual resource ownership, with candidate overlap
  counted in preparation. Persistent/transient limits were not increased.
  Subsequent tests added real geometry accounting and effective-setting
  rollback coverage; the complete final units are reproduced above.
- A real standalone protocol probe showed that False compared equal to angle
  0.0, allowing a boolean in the encoder's angle sequence. The encoder now
  validates real, nonboolean angle values before sequence equality. Four new
  cases cover False, None, "0", and []. This is a protocol boundary correction;
  V2c numerical operations and tolerances did not change.

The large initial fixture-failure output remains byte-preserved by identity,
rather than being replaced by a clean rerun.

Cwd: `C:\holographiclab`.

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' '-B' '-m' 'pytest' '-q' '-p' 'no:cacheprovider' '--basetemp' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\backend_tmp02' 'tests/test_virtual_bench_polarization_adapter.py' 'tests/test_virtual_bench_polarization_protocol.py' 'tests/test_virtual_bench_polarization_server.py' 'tests/test_virtual_bench_polarization_architecture.py' 'tests/test_virtual_bench_architecture.py'
```

| Preserved original stream | Bytes | SHA-256 |
|---|---:|---|
| `backend_focused02_stdout.txt` | 100984 | `de5a46c75dc1569d15a253edb9fadcb4e8750d8afc9cba4689ef1f06a6787a92` |
| `backend_focused02_stderr.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `frontend_unit_work_stdout.txt` | 813 | `bf5076cae4098e90cef02389759204d6dfef73ba56059a885fbfacb14fb39917` |
| `frontend_unit_work_stderr.txt` | 1089 | `baad4df9c6a2f52da88f0a42a7d6942cd056d3ccb59cdd99385217b54556db4e` |

### Pre-fix standalone angle-type reproducer

Capture: `backend_protocol_angle_reproducer01_*`; exit 1.

Cwd: `C:\holographiclab`.

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' '-B' '-m' 'pytest' '-q' '-p' 'no:cacheprovider' '--basetemp' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\backend_protocol_angle_reproducer_tmp01' 'tests/test_virtual_bench_polarization_protocol.py' '-k' 'test_standalone_sweep_encoder_rejects_non_real_angle_values'
```

Unedited full stdout:

```text
F...                                                                     [100%]
================================== FAILURES ===================================
___ test_standalone_sweep_encoder_rejects_non_real_angle_values[bool-zero] ____

replacement = False

    @pytest.mark.parametrize("replacement", [False, None, "0", []], ids=["bool-zero", "null", "string", "list"])
    def test_standalone_sweep_encoder_rejects_non_real_angle_values(replacement):
        submission = adapter.validate_sweep_submission(sweep_envelope())
        rows = json.loads(adapter.sweep_submission(submission).body)["rows"]
        angles = list(protocol.ANGLES_RAD)
        angles[6] = replacement
>       with pytest.raises((TypeError, ValueError)):
E       Failed: DID NOT RAISE any of (TypeError, ValueError)

tests\test_virtual_bench_polarization_protocol.py:159: Failed
=========================== short test summary info ===========================
FAILED tests/test_virtual_bench_polarization_protocol.py::test_standalone_sweep_encoder_rejects_non_real_angle_values[bool-zero]
1 failed, 3 passed, 27 deselected in 0.57s
```

Stderr: empty (0 bytes).

### Corrected protocol focused suite

Capture: `backend_protocol_final01_*`; exit 0.

Cwd: `C:\holographiclab`.

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' '-B' '-m' 'pytest' '-q' '-p' 'no:cacheprovider' '--basetemp' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\backend_protocol_final_tmp01' 'tests/test_virtual_bench_polarization_protocol.py'
```

Unedited full stdout:

```text
...............................                                          [100%]
31 passed in 0.35s
```

Stderr: empty (0 bytes).

## Independent API and analytic validation

The normal service was launched only on http://127.0.0.1:8510 using
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 -m apps.virtual_bench.server.
It retains exclusive fixed-port binding, host/origin checks and the one shared
worker gate. There is no alternate-port fallback or controlled fault endpoint
in that production service.

precommit_served_finalsource.json records checkout-owned imported modules,
actual source hashes, idle health, and byte equality between every served
asset and its built file. The final-source API recapture follows the standalone
protocol correction and uses the final built frontend. Earlier api_v1.json,
api_v2b.json and api_v2d.json remain original captures; current results are
separate api_v1_final.json, api_v2b_final.json and api_v2d_final.json.

The V2d validator independently decodes the HTTP binary frame and scalar sweep
JSON. It imports public V2c scientific operations, but does not import the V2d
adapter, encoder, protocol decoder or frontend decoder. It checks magic,
padding, descriptor roles, byte order, shapes, offsets, bounded complete frame,
actual readout coordinates, submitted experiment/SHA, ordered stage identities,
all stage scalars and both real/imaginary sample components. Direct-public
comparisons use identical inputs on the same platform and require exact
float64 array/scalar/sample equality. Those comparisons validate transport and
composition; separate analytic references avoid using public functions as
their sole scientific oracle.

### Final-source V1 direct API validation

Capture: `api_v1_final_*`; exit 0.

Cwd: `C:\holographiclab`.

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' '-B' '-X' 'utf8' 'scripts/validate_v1_bench.py' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\api_v1_final.json'
```

Unedited full stdout:

```text
{
  "passed": true,
  "cases": 10,
  "output": "C:\\holographiclab\\runs\\v2d_acceptance_20261012_01\\api_v1_final.json",
  "source_location": "C:\\holographiclab\\src\\ohlab\\optics\\__init__.py",
  "served_asset_sha256": {
    "/assets/index-Csv-NYm8.js": "f0cf6a416ea78003bdc6bc4a336abc825dabff07af722de1e8c59730d757c1f7",
    "/assets/index-D3ozh25N.css": "9cd9ffd0ce2ff822ec93bf85ad2d86535b4925c02f65b4e261c22b9520037bc5"
  }
}
```

Stderr: empty (0 bytes).

### Final-source V2B direct API validation

Capture: `api_v2b_final_*`; exit 0.

Cwd: `C:\holographiclab`.

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' '-B' '-X' 'utf8' 'scripts/validate_v2b_bench.py' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\api_v2b_final.json'
```

Unedited full stdout:

```text
{
  "passed": true,
  "output": "C:\\holographiclab\\runs\\v2d_acceptance_20261012_01\\api_v2b_final.json",
  "case_count": 18,
  "sweep_count": 3,
  "controlled_partial": null
}
```

Stderr: empty (0 bytes).

### Final-source V2D direct API validation

Capture: `api_v2d_final_*`; exit 0.

Cwd: `C:\holographiclab`.

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' '-B' '-X' 'utf8' 'scripts/validate_v2d_bench.py' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\api_v2d_final.json'
```

Unedited full stdout:

```text
{
  "passed": true,
  "output": "C:\\holographiclab\\runs\\v2d_acceptance_20261012_01\\api_v2d_final.json",
  "cases": 28,
  "sweeps": 3,
  "controlled_partial_index": null
}
```

Stderr: empty (0 bytes).

### Measured scientific evidence and tolerances

The unchanged scripts/validate_v2c_polarization.py analytic validator was
called with a 64×64 grid, dy=4.1e-6 m, dx=3.7e-6 m, wavelength
633e-9 m, and input norm 6.213632e-08. It covers literal P(0), P(π/2),
QWP(0), HWP(π/8), QWP(π/4), all 13 Malus angles, noncommuting element order,
actual polarizer loss, arbitrary unnormalized complex coefficients, source
common phase, asymmetric spatial fields, polarizer idempotence, retarder
unitarity/inverse, and dark-input undefined ratios.

The selected near-extinction offsets [-1e-6, -1e-9, 0, 1e-9, 1e-6] rad
use an independent Decimal reference at the exact submitted binary64 angle,
80 decimal digits and 38 series terms. Weak nonzero components are not rounded
to zero. This is finite-case numerical evidence, not arbitrary weak-signal
visibility or hardware certification.

| Quantity | Relative tolerance | Absolute tolerance |
|---|---:|---:|
| Complex components | 2e-14 | 2e-14 × input amplitude |
| Intensity | 2e-13 | 2e-13 × input amplitude squared |
| Norm | 2e-13 | 2e-13 × input norm |
| Ratio | 2e-13 | 2e-13 |
| Unitarity entries | 0 | 2e-15 |
| Selected weak components/intensity/ratio | 2e-14 | 1e-48 |
| Selected weak norm | 2e-14 | 1e-48 × input norm |

Measured maxima from api_v2d_final.json (independent_analytic_v2c.maxima):

| Metric | Measured maximum |
|---|---:|
| `complex_input_scaled_error` | 2.479436791899844e-16 |
| `malus_absolute_error` | 2.220446049250313e-16 |
| `unitarity_entry_error` | 4.440892098500626e-16 |
| `inverse_input_scaled_error` | 4.512643077139003e-16 |
| `common_phase_covariance_input_scaled_error` | 2.479436791899844e-16 |
| `polarizer_idempotence_input_scaled_error` | 1.142963886598413e-16 |
| `retarder_relative_norm_error` | 4.640716422278097e-16 |
| `selected_weak_relative_error` | 2.0194839179460514e-16 |

Phase-preserving constructor maximum absolute error was exactly 0.0;
independently doubled amplitude gave ratio 4.0; dark-input ratio was null;
NumPy settings were preserved. Environment: Python 3.11.9, NumPy 2.4.6,
SciPy 1.17.1. The reference and numerical source hashes are recorded in the
API provenance, including:

| Source | SHA-256 |
|---|---|
| src/ohlab/optics/polarization.py | 48779f28cc194488bc8ac11e96196f848663ec16e86c9f1f97388af88b801de2 |
| scripts/validate_v2c_polarization.py | ce155695031a69e591ba65b29671f433b82c90289e395dfe3f079eb881b7dc73 |
| scripts/validate_v2d_bench.py | 399e7e5871c8b1412b3c9e93c7aee4566c40e25678fd7590b28bcad997fc8351 |

The final direct API run contains 28 genuine single cases and three genuine
13-point sweeps (analyzer, middle, maximum_eight), each independently restarting
the full public train from the original incident field. The captured sweeps
were 8468, 14718 and 31448 bytes respectively. A maximum-eight-elements
captured result has nine stage sample records, a 5231-byte header and a
269440-byte complete frame. Enforced limits are 16384 header bytes,
264192 payload bytes, 280592 complete-frame bytes, 32768 request bytes and
65536 sweep-JSON bytes. The largest captured frame is a measured case,
not an assertion that the cap was reached exactly.

Negative HTTP checks were actually queried: grid axis 129 → 422, unsupported
Gaussian waist_z → 422, foreign origin → 403, 32769-byte body → 413, and a
real overflowing numerical input → 422. Complete inputs/results and source
locations are retained in the final API JSON.

## Actual production browser acceptance

The installed Node executable and installed Playwright CLI were used directly;
no package download or browser installation was performed. Browser evidence
records Chrome 154.0.8037.98, viewport 1440×1000, device scale 1. Child-process
configuration redirects all evidence and legacy V1/V2b screenshot outputs
to fresh ignored directories. Historical tracked figures are not overwritten.
Only the three explicitly approved new V2d PNG paths receive accepted captures.

### First full browser attempt: failed, preserved

production01_browser exited 1: one failed, 27 passed, five controlled-only
skips. The genuine sweep marker click timed out because a decorative SVG
polyline intercepted pointer events. The original full output, failure
screenshot and error context remain under production01_browser/. The product
polyline was changed to pointer-events: none; the click assertion was not
forced or weakened. This attempt is not relabelled as passing.

### Original failed full production browser attempt

Capture: `production01_browser_*`; exit 1.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/@playwright/test/cli.js' 'test' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\production01_browser\test-results'
```

Unedited full stdout:

```text

Running 33 tests using 1 worker

  ok  1 tests\bench.browser.spec.ts:55:1 › production V0 lens/readout smoke and local-only assets (2.2s)
  ok  2 tests\bench.browser.spec.ts:74:1 › camera selection color resize and 3D picking do not alter optics or call API (3.2s)
  ok  3 tests\bench.browser.spec.ts:117:1 › real edits change V0 output; aperture uses shared limits and original norm loss; stale screenshot (4.3s)
  ok  4 tests\bench.browser.spec.ts:138:1 › source fields signed lens rectangle add delete numeric order and z ghost rail (3.6s)
  ok  5 tests\bench.browser.spec.ts:174:1 › rapid submissions remain single and edited pending response stays separately stale (1.2s)
  ok  6 tests\bench.browser.spec.ts:190:1 › malformed response and missing backend publish no fabricated success; reload passive; dark genuine (1.7s)
  ok  7 tests\bench.browser.spec.ts:226:1 › independent gray fixture catches extra gamma in actual WebGL and preserves raw float64 (882ms)
  ok  8 tests\bench.browser.spec.ts:249:1 › independent asymmetric 3x4 and 2x5 display cells and original readouts (4.3s)
  ok  9 tests\bench.browser.spec.ts:294:1 › context loss and unsupported WebGL report presentation failure without automatic solve (1.7s)
  ok 10 tests\bench.browser.spec.ts:313:1 › predefined resource replacement sequence retains one active texture and bounded owned resources (8.6s)
  -  11 tests\bench.browser.spec.ts:329:1 › actual browser disconnect keeps running worker busy until controlled completion
  ok 12 tests\polarization.browser.spec.ts:103:1 › genuine QWP HWP and common phase retain actual complex samples at shared fixed tau (14.7s)
  ok 13 tests\polarization.browser.spec.ts:127:1 › real order coefficients source and element editing preserve loss and explicit original identity (23.4s)
  x  14 tests\polarization.browser.spec.ts:158:1 › genuine thirteen-point full-train sweep has passive inspection and one explicit apply simulation (1.0m)
  ok 15 tests\polarization.browser.spec.ts:176:1 › actual asymmetric float64 intensity picking does not relabel the submitted complex sample (4.8s)
  ok 16 tests\polarization.browser.spec.ts:202:1 › dark and selected weak public samples remain distinct and display actions send no scientific requests (12.2s)
  ok 17 tests\polarization.browser.spec.ts:231:1 › controlled nonzero tiny sample with zero squared intensity is not exact darkness (3.0s)
  ok 18 tests\polarization.browser.spec.ts:254:1 › invalid text numerical failure malformed reply and signed zero require deliberate recovery (7.4s)
  ok 19 tests\polarization.browser.spec.ts:274:1 › rapid clicks and away-and-back across all modes reject an actual held late result (4.3s)
  ok 20 tests\polarization.browser.spec.ts:290:1 › later presentation failure keeps numerical completion and original result without automatic resubmission (3.9s)
  ok 21 tests\polarization.browser.spec.ts:350:1 › repeated play pause replacement mode switches and actual context loss preserve bounded owners (13.9s)
  -  22 tests\polarization.browser.spec.ts:384:1 › controlled actual failed sweep keeps only genuine contiguous rows
  -  23 tests\polarization.browser.spec.ts:398:1 › actual polarization browser disconnect holds all five operations until genuine worker completion
  ok 24 tests\two_path.browser.spec.ts:144:1 › genuine dual known phases and both original readouts use one submitted V2a result (8.1s)
  ok 25 tests\two_path.browser.spec.ts:175:1 › real Gaussian source distance phase edits preserve shared scale and original input diagnostics (8.9s)
  ok 26 tests\two_path.browser.spec.ts:193:1 › asymmetric actual port arrays preserve common transverse axes aspect and unlit shared grayscale (18.6s)
  ok 27 tests\two_path.browser.spec.ts:234:1 › presentation controls never calculate and scientific edits detach both textures immediately (2.9s)
  ok 28 tests\two_path.browser.spec.ts:255:1 › rapid genuine submissions and away-back mode changes reject held cross-mode attachments (2.6s)
  ok 29 tests\two_path.browser.spec.ts:273:1 › real dark outputs malformed error recovery signed-zero policy and passive reload (4.6s)
  ok 30 tests\two_path.browser.spec.ts:300:1 › real seventeen-point sweep displays actual markers with no chart-click computation (2.5s)
  -  31 tests\two_path.browser.spec.ts:315:1 › controlled partial failure retains only genuine prefix and never labels sweep complete
  -  32 tests\two_path.browser.spec.ts:331:1 › actual two-path browser disconnect holds all numerical routes until genuine worker completion
  ok 33 tests\two_path.browser.spec.ts:374:1 › context loss preserves numerical completion and repeated mode replacement ownership is bounded (12.5s)


  1) tests\polarization.browser.spec.ts:158:1 › genuine thirteen-point full-train sweep has passive inspection and one explicit apply simulation 

    Test timeout of 60000ms exceeded.

    Error: locator.click: Test timeout of 60000ms exceeded.
    Call log:
      - waiting for getByTestId('pl-sweep-point-4')
        - locator resolved to <circle r="4" tabindex="0" role="button" fill="#087f89" cx="278.3333333333333" cy="62.499999999999986" data-testid="pl-sweep-point-4"></circle>
      - attempting click action
        2 × waiting for element to be visible, enabled and stable
          - element is visible, enabled and stable
          - scrolling into view if needed
          - done scrolling
          - <polyline fill="none" stroke="#087f89" points="55,190 110.83333333333333,178.6121593216773 166.66666666666666,147.5 222.5,104.99999999999999 278.3333333333333,62.499999999999986 334.1666666666667,31.38784067832276 390,20 445.83333333333337,31.38784067832276 501.66666666666663,62.499999999999986 557.5,104.99999999999999 613.3333333333334,147.5 669.1666666666666,178.6121593216773 725,190"></polyline> intercepts pointer events
        - retrying click action
        - waiting 20ms
        2 × waiting for element to be visible, enabled and stable
          - element is visible, enabled and stable
          - scrolling into view if needed
          - done scrolling
          - <polyline fill="none" stroke="#087f89" points="55,190 110.83333333333333,178.6121593216773 166.66666666666666,147.5 222.5,104.99999999999999 278.3333333333333,62.499999999999986 334.1666666666667,31.38784067832276 390,20 445.83333333333337,31.38784067832276 501.66666666666663,62.499999999999986 557.5,104.99999999999999 613.3333333333334,147.5 669.1666666666666,178.6121593216773 725,190"></polyline> intercepts pointer events
        - retrying click action
          - waiting 100ms
        109 × waiting for element to be visible, enabled and stable
            - element is visible, enabled and stable
            - scrolling into view if needed
            - done scrolling
            - <polyline fill="none" stroke="#087f89" points="55,190 110.83333333333333,178.6121593216773 166.66666666666666,147.5 222.5,104.99999999999999 278.3333333333333,62.499999999999986 334.1666666666667,31.38784067832276 390,20 445.83333333333337,31.38784067832276 501.66666666666663,62.499999999999986 557.5,104.99999999999999 613.3333333333334,147.5 669.1666666666666,178.6121593216773 725,190"></polyline> intercepts pointer events
          - retrying click action
            - waiting 500ms


      163 |   expect(posts.filter(path => path.endsWith('/sweep'))).toHaveLength(1);
      164 |   const beforeSelection = posts.length;
    > 165 |   await page.getByTestId('pl-sweep-point-4').click(); await frames(page);
          |                                              ^
      166 |   expect(posts).toHaveLength(beforeSelection);
      167 |   await page.getByTestId('pl-apply-angle').click();
      168 |   await expect.poll(async () => { const state = await pl(page); return !state.active && !!state.currentResult; }).toBe(true);
        at C:\holographiclab\frontend\bench\tests\polarization.browser.spec.ts:165:46

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    ..\..\runs\v2d_acceptance_20261012_01\production01_browser\test-results\polarization.browser-genui-f9325-e-explicit-apply-simulation\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    Error Context: ..\..\runs\v2d_acceptance_20261012_01\production01_browser\test-results\polarization.browser-genui-f9325-e-explicit-apply-simulation\error-context.md

  1 failed
    tests\polarization.browser.spec.ts:158:1 › genuine thirteen-point full-train sweep has passive inspection and one explicit apply simulation 
  5 skipped
  27 passed (4.1m)
```

Unedited full stderr:

```text
(node:48680) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
(node:21980) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
```

### Full browser acceptance after the pointer correction

production02_browser is the complete normal-service run: 28 passed and five
controlled-only skips. It reruns existing V1 and V2b browser assertions
alongside ten ordinary V2d scenarios. Browser-only tiny-sample and allocation
fault supplements are explicitly identified below; they are not presented as
genuine solver-generated samples.

### Complete production browser acceptance

Capture: `production02_browser_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/@playwright/test/cli.js' 'test' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\production02_browser\test-results'
```

Unedited full stdout:

```text

Running 33 tests using 1 worker

  ok  1 tests\bench.browser.spec.ts:55:1 › production V0 lens/readout smoke and local-only assets (1.5s)
  ok  2 tests\bench.browser.spec.ts:74:1 › camera selection color resize and 3D picking do not alter optics or call API (3.2s)
  ok  3 tests\bench.browser.spec.ts:117:1 › real edits change V0 output; aperture uses shared limits and original norm loss; stale screenshot (3.7s)
  ok  4 tests\bench.browser.spec.ts:138:1 › source fields signed lens rectangle add delete numeric order and z ghost rail (2.8s)
  ok  5 tests\bench.browser.spec.ts:174:1 › rapid submissions remain single and edited pending response stays separately stale (876ms)
  ok  6 tests\bench.browser.spec.ts:190:1 › malformed response and missing backend publish no fabricated success; reload passive; dark genuine (1.4s)
  ok  7 tests\bench.browser.spec.ts:226:1 › independent gray fixture catches extra gamma in actual WebGL and preserves raw float64 (661ms)
  ok  8 tests\bench.browser.spec.ts:249:1 › independent asymmetric 3x4 and 2x5 display cells and original readouts (3.2s)
  ok  9 tests\bench.browser.spec.ts:294:1 › context loss and unsupported WebGL report presentation failure without automatic solve (915ms)
  ok 10 tests\bench.browser.spec.ts:313:1 › predefined resource replacement sequence retains one active texture and bounded owned resources (7.6s)
  -  11 tests\bench.browser.spec.ts:329:1 › actual browser disconnect keeps running worker busy until controlled completion
  ok 12 tests\polarization.browser.spec.ts:103:1 › genuine QWP HWP and common phase retain actual complex samples at shared fixed tau (12.1s)
  ok 13 tests\polarization.browser.spec.ts:127:1 › real order coefficients source and element editing preserve loss and explicit original identity (20.4s)
  ok 14 tests\polarization.browser.spec.ts:158:1 › genuine thirteen-point full-train sweep has passive inspection and one explicit apply simulation (4.3s)
  ok 15 tests\polarization.browser.spec.ts:176:1 › actual asymmetric float64 intensity picking does not relabel the submitted complex sample (5.0s)
  ok 16 tests\polarization.browser.spec.ts:202:1 › dark and selected weak public samples remain distinct and display actions send no scientific requests (14.5s)
  ok 17 tests\polarization.browser.spec.ts:231:1 › controlled nonzero tiny sample with zero squared intensity is not exact darkness (3.4s)
  ok 18 tests\polarization.browser.spec.ts:254:1 › invalid text numerical failure malformed reply and signed zero require deliberate recovery (7.8s)
  ok 19 tests\polarization.browser.spec.ts:274:1 › rapid clicks and away-and-back across all modes reject an actual held late result (4.5s)
  ok 20 tests\polarization.browser.spec.ts:290:1 › later presentation failure keeps numerical completion and original result without automatic resubmission (4.7s)
  ok 21 tests\polarization.browser.spec.ts:350:1 › repeated play pause replacement mode switches and actual context loss preserve bounded owners (16.7s)
  -  22 tests\polarization.browser.spec.ts:384:1 › controlled actual failed sweep keeps only genuine contiguous rows
  -  23 tests\polarization.browser.spec.ts:398:1 › actual polarization browser disconnect holds all five operations until genuine worker completion
  ok 24 tests\two_path.browser.spec.ts:144:1 › genuine dual known phases and both original readouts use one submitted V2a result (9.5s)
  ok 25 tests\two_path.browser.spec.ts:175:1 › real Gaussian source distance phase edits preserve shared scale and original input diagnostics (10.6s)
  ok 26 tests\two_path.browser.spec.ts:193:1 › asymmetric actual port arrays preserve common transverse axes aspect and unlit shared grayscale (21.9s)
  ok 27 tests\two_path.browser.spec.ts:234:1 › presentation controls never calculate and scientific edits detach both textures immediately (3.6s)
  ok 28 tests\two_path.browser.spec.ts:255:1 › rapid genuine submissions and away-back mode changes reject held cross-mode attachments (3.1s)
  ok 29 tests\two_path.browser.spec.ts:273:1 › real dark outputs malformed error recovery signed-zero policy and passive reload (5.3s)
  ok 30 tests\two_path.browser.spec.ts:300:1 › real seventeen-point sweep displays actual markers with no chart-click computation (3.2s)
  -  31 tests\two_path.browser.spec.ts:315:1 › controlled partial failure retains only genuine prefix and never labels sweep complete
  -  32 tests\two_path.browser.spec.ts:331:1 › actual two-path browser disconnect holds all numerical routes until genuine worker completion
  ok 33 tests\two_path.browser.spec.ts:374:1 › context loss preserves numerical completion and repeated mode replacement ownership is bounded (15.4s)

  5 skipped
  28 passed (3.2m)
```

Unedited full stderr:

```text
(node:31200) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
```

Exact nonsecret child-only redirection for that run:

```json
{
  "V1_EVIDENCE_DIR": "C:\\holographiclab\\runs\\v2d_acceptance_20261012_01\\production02_browser\\v1",
  "V1_API_EVIDENCE": "C:\\holographiclab\\runs\\v2d_acceptance_20261012_01\\api_v1.json",
  "V1_FIGURE_DIR": "C:\\holographiclab\\runs\\v2d_acceptance_20261012_01\\production02_browser\\figures_v1",
  "V2B_EVIDENCE_DIR": "C:\\holographiclab\\runs\\v2d_acceptance_20261012_01\\production02_browser\\v2b",
  "V2B_API_EVIDENCE": "C:\\holographiclab\\runs\\v2d_acceptance_20261012_01\\api_v2b.json",
  "V2B_FIGURE_DIR": "C:\\holographiclab\\runs\\v2d_acceptance_20261012_01\\production02_browser\\figures_v2b",
  "V2D_EVIDENCE_DIR": "C:\\holographiclab\\runs\\v2d_acceptance_20261012_01\\production02_browser\\v2d",
  "V2D_API_EVIDENCE": "C:\\holographiclab\\runs\\v2d_acceptance_20261012_01\\api_v2d.json",
  "V2D_FIGURE_DIR": "C:\\holographiclab\\runs\\v2d_acceptance_20261012_01\\production02_browser\\figures_v2d"
}
```

### Final-source genuine figure recapture

After the standalone encoder type guard and a screenshot-only normal scroll
inside the previous-result panel, all three genuine figure scenarios were
rerun against final-source API captures. No scenario assertion was changed by
the scroll. production02_browser remains the original complete suite;
production03_finalsource_figures is a fresh three-scenario recapture, not a
second claim of 28 tests. The retained-result panel now visibly exposes the
original 0.25 transmission and original angle near 0.785 versus edited 0.42.
All three accepted PNGs were visually inspected and copied byte-for-byte from
the genuine served production UI, without synthetic substitution or pixel
editing.

### Final-source genuine figure scenarios

Capture: `production03_finalsource_figures_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/@playwright/test/cli.js' 'test' 'tests/polarization.browser.spec.ts' '--grep' 'genuine QWP|real order coefficients|genuine thirteen-point' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\production03_finalsource_figures\test-results'
```

Unedited full stdout:

```text

Running 3 tests using 1 worker

  ok 1 tests\polarization.browser.spec.ts:103:1 › genuine QWP HWP and common phase retain actual complex samples at shared fixed tau (14.1s)
  ok 2 tests\polarization.browser.spec.ts:127:1 › real order coefficients source and element editing preserve loss and explicit original identity (23.5s)
  ok 3 tests\polarization.browser.spec.ts:160:1 › genuine thirteen-point full-train sweep has passive inspection and one explicit apply simulation (4.5s)

  3 passed (43.4s)
```

Unedited full stderr:

```text
(node:26916) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
```

| Approved new figure | Dimensions | Bytes | SHA-256 |
|---|---:|---:|---|
| `docs/handoffs/v2d/figures/fig01_complex_transformation.png` | 1440×3444 | 237295 | `ba3158fec01a690a52008ef67089efc46e8c69c546942223d4c2d2d91c008e5e` |
| `docs/handoffs/v2d/figures/fig02_angle_sweep.png` | 1440×3867 | 259766 | `0dda5da1ed406d910261900ff878e4ffd05a3f9c071b8560526265e145c78a14` |
| `docs/handoffs/v2d/figures/fig03_order_loss_stale.png` | 1440×2023 | 173397 | `b2eee3b0687094db0f7f3c41a2914a78140f9b7e45ffe3378c5651aac07b8a7c` |

figures_provenance.json records the exact source and destination for each
PNG and its visual-inspection result. fig03_order_loss_stale.png uses only
normal scrolling to expose existing content.

### Reproducing browser redirection with installed tools

Use a fresh owned directory and an explicitly launched normal service. First
create fresh API evidence with the three validator commands above. The task's
captured coordination driver is reproducible locally as follows; it is ignored
execution evidence, not a new production dependency:

~~~powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -X utf8 runs/v2d_acceptance_20261012_01/browser_driver.py <fresh-full-label> --api-suffix _final
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -X utf8 runs/v2d_acceptance_20261012_01/browser_driver.py <fresh-figure-label> --api-suffix _final --test-file tests/polarization.browser.spec.ts --grep 'genuine QWP|real order coefficients|genuine thirteen-point'
~~~

The underlying installed command is exactly the recorded Node/CLI invocation
above. Its output-directory flag is --output, not --output-dir.
For reproduction without the ignored driver, the same child-only setup is:

~~~python
import os
from pathlib import Path
import subprocess

root = Path(r"C:\holographiclab")
evidence = root / "runs/v2d_acceptance_20261012_01"
fresh = evidence / "<fresh-owned-browser-label>"
fresh.mkdir(exist_ok=False)
child_env = os.environ.copy()
for key in tuple(child_env):
    if key.startswith(("V1_", "V2B_", "V2D_")):
        child_env.pop(key)
for prefix, version in (("V1", "v1"), ("V2B", "v2b"), ("V2D", "v2d")):
    child_env[prefix + "_EVIDENCE_DIR"] = str(fresh / version)
    child_env[prefix + "_API_EVIDENCE"] = str(evidence / ("api_" + version + "_final.json"))
    child_env[prefix + "_FIGURE_DIR"] = str(fresh / ("figures_" + version))
subprocess.run(
    [r"C:\Program Files\nodejs\node.exe", "node_modules/@playwright/test/cli.js",
     "test", "--output", str(fresh / "test-results")],
    cwd=root / "frontend/bench", env=child_env, check=True,
)
~~~

No parent environment mapping is modified, and no complete environment or
credentials are recorded. The normal service is not automatically replaced by
a controlled child; the controlled driver never silently falls back to normal
production execution.

## Actual browser numerical identity and presentation observations

The observations below come from production02_browser/v2d/browser_*.json,
with final-source genuine phase, order and sweep scenarios additionally
recaptured under production03_finalsource_figures/v2d/. Values are actual
captured outputs; scientific norms are SI-grid amplitude integrals, not
calibrated watts.

### Complex phase, stage loss and original identity

browser_genuine_complex_and_common_phase.json: at shared fixed tau=0, the
QWP raw marker was (0.7071067811865475, 4.329780281177466e-17).
After a genuine common source-phase shift, it was
(0.5, -0.49999999999999994). Maximum literal error was
5.551115123125783e-17 against rtol=0, atol=2e-15.
The original diagonal input components were real 1/sqrt(2); the final y
component was almost purely positive imaginary. With the source phase shift,
input x/y were 0.5+0.5i and final y was -0.49999999999999994+0.5i.
Incident/final maxima stayed near one, respectively
[0.9999999999999998, 0.9999999999999998] and [1.0000000000000002, 1.0];
equal intensities did not erase common phase. HWP final sample components were
0.7071067811865475 + 1.7934537145592996e-17i and
0.7071067811865476 - 4.3297802811774664e-17i.
A genuine arbitrary complex, unnormalized case retained maxima [5.58, 5.58].

browser_order_loss_and_actual_editors.json: crossed-polarizer transmission
was 3.749399456654644e-33, adding the middle polarizer gave
0.25000000000000006, and reordering it gave 9.373498641636613e-34.
The coefficient-2 case gave 0.5000000000000001 transmission with the actual
Jones incident denominator; the Gaussian 128×128 case gave 1.0.
Editing made the current result stale (currentResult=null) while preserving
the previous experiment, order, stage losses, sample identity and request ID.
Presentation scales are common across compared stages/images; neither
per-stage amplitude nor per-image peak normalization hides physical loss.

### Exact dark, weak nonzero and underflow distinction

browser_dark_weak_and_passive_animation.json: genuine zero-amplitude source
and zero coefficients gave exact zero parts, zero norm and undefined ratios
(null). A genuine off-center Gaussian readout had exact zero sampled parts
and was dark while the full field retained norm 3.9269876637763073e-11 and
ratio 1.0. At the genuine π/2 analyzer angle, nonzero samples remained:
x real 3.749399456654644e-33, y real 6.123233995736766e-17, both imaginary
parts zero. Final norm was 2.4572064279131873e-40, input norm 6.5536e-08,
ratio 3.749399456654644e-33, delta -6.5536e-08; dark=false and
displayLimited=true. No epsilon-dark rule was used.

browser_controlled_tiny_underflow_sample.json is an explicitly synthetic
transport supplement fulfilled in the browser from a real frame. Its selected
sample alone has x real 1e-200, all other parts zero, while selected-pixel
intensity is 0; readout is row/column 32 at (0,0) m. The rest of the usable
frame retains field norm 6.5536e-08 and maxima [1,1]. The UI reported
dark=false, displayLimited=true, renderable=true, raw marker (1e-200,0).
It proves exact component-based darkness despite intensity underflow.
It is not labelled a new genuine optical solver case, and does not promise
visible rendering for arbitrarily small nonzero signals.

### Passive sample picking, sweep inspection and staleness

browser_fixed_sample_and_raw_intensity.json: submitted complex readout was
row 1, column 3, (x,y)=(4e-6,0) m. Picking the final intensity pixel at
row 0, column 0 showed (x,y)=(-8e-6,-4e-6) m and raw intensity
0.056134762834133704, without changing the submitted complex sample or
sending a scientific request. After explicit readout edits and one Simulate,
the complex x component changed from 0.6025566517240063 to
0.16753322481545818, with y respectively
3.689595374193754e-17 + 0.6025566517240063i and
1.0258451376054239e-17 + 0.16753322481545818i.
The explicit edit sequence recorded two validations and one simulation;
picking before those edits sent zero POSTs.

browser_genuine_thirteen_point_sweep.json: all 13 actual radians from
-1.5707963267948966 to +1.5707963267948966, including zero, completed.
Endpoint ratios were both 3.749399456654644e-33; center ratio was 1.0.
Inspecting point 4 was passive. One explicit Apply set the actual angle to
-0.5235987755982988 and produced one validation and one simulation, following
one sweep. No fabricated cos-squared rows or diagnostic replay were used.

browser_rapid_click_cross_mode_staleness.json: one held request
1c7dec14-556a-4d85-9279-b2e2e75a8819 stayed an original previous result after
switching away/back; it was not relabelled current. Explicit recovery produced
new request e4415610-a98b-48a6-b6c3-d60b3b1e72bc. Observed requests were
one held simulation, three mode validations and one deliberate recovery
simulation. There was no automatic resimulation.

## Actual resource ownership and animation

Browser accounting covers actual owned scientific buffers with alias
deduplication, retained header allowances, serialized scalar sweeps, canvas
backing stores, active texture source bytes, trajectory float64 arrays and
owned geometry. It excludes arbitrary JS/browser heap, GPU allocation, driver
memory and calibrated whole-process peaks. The persistent cap remains
16777216 bytes (16 MiB); the transient cap remains 33554432 bytes (32 MiB).
Displayed transport/decode/preparation phases are conservative calculated
next-operation estimates from owned resources, not sampled process-memory
measurements.

browser_order_loss_and_actual_editors.json observed a maximum retained
557808 bytes in the 128×128 Gaussian case:

| Owned component | Bytes |
|---|---:|
| Scientific retained buffers/header accounting | 280576 |
| Actual canvas stores | 131072 |
| Active texture-source bytes | 131072 |
| Float64 trajectories | 8224 |
| Owned geometry | 6864 |
| Total | 557808 |

Its calculated next transport/decode/preparation peaks were 1118992, 1102592
and 1268608 bytes. The largest captured trajectory group had four stage
records (16448 bytes) and geometry 13440 bytes. Browser runs did not retain
all modes' maximum-cap results simultaneously; meaningful unit tests cover
all-mode worst-retention accounting, alias deduplication and candidate overlap.
These limits are not inferred from this single Gaussian observation.

browser_actual_resources_animation_and_context_loss.json completed three
attach/play/detach cycles. Every active scene owned eight geometries, eight
materials, two textures, one controls instance, six listeners and one resize
observer, with 6864 geometry-source bytes and 32768 texture-source bytes.
The active budget was
82944 + 32768 + 32768 + 8224 + 6864 = 163568 bytes;
its calculated next-operation peak was 381824 bytes. Detached sequential mode
owned six geometries, six materials, zero textures, one controls instance,
six listeners and one observer, with 5164 geometry bytes and zero texture
source bytes.

The single shared render-loop callback had one active polarization owner,
zero additional scheduled callbacks, and zero owners after detach. Ticks
remained 47→47, 94→94, and 149→149 after detach, proving obsolete polarization
owners stopped advancing. Reset restored tau=0 and playing=false; no
independent animation RAF was introduced. The passive-animation scenario
recorded zero scientific requests while changing stage/gain, playing, pausing
and resetting (ticks 37, owner 1, scheduled callbacks 0 after reset).

A real WebGL context loss cleared current presentation, retained the completed
numerical result separately, and left zero polarization animation owners.
The capture's later reload requested /api/v1/validate and /api/v2d/validate;
it sent no Simulate or Sweep. This is not falsely reported as an entirely
empty network log.

### Late resource failure and effective-setting rollback

browser_controlled_late_resource_rollback.json injected a browser-only
Float64 trajectory allocation failure after two real canvases had already
been prepared. Production numerical work completed genuinely. Previous
presentation request d4a2ec00-ced8-4300-8e0e-99325041ba2b remained visible
while newly completed numerical request 81f58af0-32fc-4c0a-ad0c-f63350565fb9
was retained separately. Retained overlap was 246512 bytes; calculated next
peak was 464768 bytes. An explicit presentation retry adopted the new
numerical result without another optics request.

A second injected redraw failure changed requested gain from 1 to 2, while
published trajectory gains remained [1,1]. Original marker, polylines, scene
ownership and effective scale were preserved. Marker SVG coordinates were
unchanged at (70.71067811865474, 4.3297802811774655e-15).
An explicit retry restored effective gains [2,2] and marker coordinates
(141.42135623730948, 8.659560562354931e-15) with the same result identity.
The entire capture logged exactly one /api/v2d/simulate request. The injected
constructor fault was restored after throwing. This is explicitly controlled
browser resource evidence, not a production fault API or automatic diagnostic
replay.

## Intended-assertion negative controls

scripts/v2d_negative_controls.py creates isolated copies under the fresh
owned evidence tree. Each original selected assertion passes, one documented
mutation is applied only in that copy, the intended named assertion fails,
the copied source is restored byte-for-byte, and the same selected assertion
passes again. Production hashes before/after are equal. Syntax, import,
setup or dependency failures do not count as successful detections.
The completed second run covers 13 Python and 13 TypeScript mutations, 26
variants across 21 categories. negative_controls02/summary.json records
complete=true, production_unchanged=true, failure=null.
The earlier completed negative_controls01 is preserved separately.

This second run followed the standalone protocol-angle guard and preceded the
normal screenshot scroll, which does not change these targeted fault assertions.
The complete final Python and frontend suites above followed source fixes.
The screenshot edit did not change test assertions.

### All isolated negative controls, original/fault/restored

Capture: `fault_controls02_*`; exit 0.

Cwd: `C:\holographiclab`.

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' '-B' '-X' 'utf8' 'scripts/v2d_negative_controls.py' '--output-dir' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\negative_controls02'
```

Unedited full stdout:

```text
swapped_complex_components: original=0, fault=1, intended_assertion=True, restored=0
erased_imaginary_component: original=0, fault=1, intended_assertion=True, restored=0
reversed_axis_sign: original=0, fault=1, intended_assertion=True, restored=0
scalar_envelope_denominator: original=0, fault=1, intended_assertion=True, restored=0
source_common_phase_reset: original=0, fault=1, intended_assertion=True, restored=0
duplicated_single_sampling: original=0, fault=1, intended_assertion=True, restored=0
duplicated_sweep_train: original=0, fault=1, intended_assertion=True, restored=0
cumulative_sweep: original=0, fault=1, intended_assertion=True, restored=0
fabricated_cos_squared_sweep: original=0, fault=1, intended_assertion=True, restored=0
broadened_architecture_allowlist: original=0, fault=1, intended_assertion=True, restored=0
private_numerical_import: original=0, fault=1, intended_assertion=True, restored=0
private_import_elsewhere: original=0, fault=1, intended_assertion=True, restored=0
premature_disconnect_gate_release: original=0, fault=1, intended_assertion=True, restored=0
axis_degree_conversion: original=0, fault=1, intended_assertion=True, restored=0
display_common_phase_reset: original=0, fault=1, intended_assertion=True, restored=0
intensity_underflow_dark: original=0, fault=1, intended_assertion=True, restored=0
obsolete_animation_callback: original=0, fault=1, intended_assertion=True, restored=0
per_stage_amplitude_normalization: original=0, fault=1, intended_assertion=True, restored=0
per_image_peak_normalization: original=0, fault=1, intended_assertion=True, restored=0
cross_mode_epoch_ignored: original=0, fault=1, intended_assertion=True, restored=0
edited_sample_identity_ignored: original=0, fault=1, intended_assertion=True, restored=0
duplicated_browser_submission: original=0, fault=1, intended_assertion=True, restored=0
late_resource_partial_cleanup: original=0, fault=1, intended_assertion=True, restored=0
premature_presentation_publication: original=0, fault=1, intended_assertion=True, restored=0
view_selection_revalidates: original=0, fault=1, intended_assertion=True, restored=0
animation_sends_optics: original=0, fault=1, intended_assertion=True, restored=0
production_unchanged=True; intended_variants=26/26
```

Stderr: empty (0 bytes).

| Variant | Category | Intended assertion marker | Original / fault / restored exit |
|---|---|---|---|
| `swapped_complex_components` | `component_swap` | `COMPLEX_PHASE_DETECTED` | 0 / 1 / 0 |
| `erased_imaginary_component` | `imaginary_phase` | `COMPLEX_PHASE_DETECTED` | 0 / 1 / 0 |
| `reversed_axis_sign` | `angle_sign` | `ANGLE_SIGN_DETECTED` | 0 / 1 / 0 |
| `scalar_envelope_denominator` | `incident_denominator` | `JONES_DENOMINATOR_DETECTED` | 0 / 1 / 0 |
| `source_common_phase_reset` | `common_phase_source` | `COMMON_PHASE_RESET_DETECTED` | 0 / 1 / 0 |
| `duplicated_single_sampling` | `duplicate_single` | `SINGLE_CALL_COUNT_DETECTED` | 0 / 1 / 0 |
| `duplicated_sweep_train` | `duplicate_sweep` | `SWEEP_CALL_COUNT_DETECTED` | 0 / 1 / 0 |
| `cumulative_sweep` | `sweep_restart` | `SWEEP_RESTART_INCIDENT_DETECTED` | 0 / 1 / 0 |
| `fabricated_cos_squared_sweep` | `fabricated_sweep` | `SWEEP_GENUINE_ROWS_DETECTED` | 0 / 1 / 0 |
| `broadened_architecture_allowlist` | `architecture_allowlist` | `ARCHITECTURE_ALLOWLIST_DETECTED` | 0 / 1 / 0 |
| `private_numerical_import` | `architecture_private` | `PRIVATE_IMPORT_DETECTED` | 0 / 1 / 0 |
| `private_import_elsewhere` | `architecture_private` | `PRIVATE_IMPORT_ELSEWHERE_DETECTED` | 0 / 1 / 0 |
| `premature_disconnect_gate_release` | `worker_lifetime` | `WORKER_LIFETIME_DETECTED` | 0 / 1 / 0 |
| `axis_degree_conversion` | `angle_units` | `UNIT_AXIS_DETECTED` | 0 / 1 / 0 |
| `display_common_phase_reset` | `common_phase_display` | `DISPLAY_COMMON_PHASE_FIXED_TAU` | 0 / 1 / 0 |
| `intensity_underflow_dark` | `exact_dark` | `DISPLAY_NONZERO_TINY_NOT_DARK` | 0 / 1 / 0 |
| `obsolete_animation_callback` | `animation_teardown` | `ANIMATION_TEARDOWN_DETECTED` | 0 / 1 / 0 |
| `per_stage_amplitude_normalization` | `loss_display_scale` | `POLARIZER_LOSS_SHARED_SCALE` | 0 / 1 / 0 |
| `per_image_peak_normalization` | `loss_display_scale` | `POLARIZER_LOSS_SHARED_SCALE` | 0 / 1 / 0 |
| `cross_mode_epoch_ignored` | `cross_mode_identity` | `CROSS_MODE_STALE_DETECTED` | 0 / 1 / 0 |
| `edited_sample_identity_ignored` | `sample_identity` | `SAMPLE_IDENTITY_DETECTED` | 0 / 1 / 0 |
| `duplicated_browser_submission` | `duplicate_single` | `DUPLICATE_OPERATION_DETECTED` | 0 / 1 / 0 |
| `late_resource_partial_cleanup` | `atomic_resources` | `ATOMIC_LATE_RESOURCE_DETECTED` | 0 / 1 / 0 |
| `premature_presentation_publication` | `atomic_resources` | `ATOMIC_LATE_RESOURCE_DETECTED` | 0 / 1 / 0 |
| `view_selection_revalidates` | `passive_view` | `VIEW_ACTION_NO_OPTICS` | 0 / 1 / 0 |
| `animation_sends_optics` | `passive_view` | `VIEW_ACTION_NO_OPTICS` | 0 / 1 / 0 |

Each variant directory preserves mutation.json, exact mutation text,
affected copied source path, original/fault SHA-256, selected test and original,
fault and restored output. TypeScript's reporter can repeat one failed test
in two locations; repeated fault_failed_cases entries are not additional
variants. The broadened-allowlist group produced two intended assertion
failures; that is one documented variant. Controls include global private
imports, common-phase resets at source/display, actual x/y/imaginary
corruption, wrong incident denominator, degree/radian error, duplicated
sampling/train, cumulative/fabricated sweeps, stale mode/sample identity,
exact dark misclassification, obsolete animation owner, per-stage/per-image
loss hiding, premature worker release, late cleanup/publication, passive view
requests and animation-triggered optics requests.

## Explicit controlled service acceptance

The committed standalone scripts/v2d_controlled_acceptance_server.py is
passive on import. It runs only when explicitly invoked as a disposable owned
child, at exclusive loopback port 8510. It wraps genuine production workers
inside the actual shared gate, retains normal host/origin/body security, and
exposes no HTTP fault or release route. Production create_app() is never
automatically changed into this harness. Every child was closed using its
exact owned process handle after confirmed idle health; no unrelated service
was managed.

Partial mode fails immediately before the requested point's genuine public
train. Earlier rows are genuine computations and must remain an exact prefix.
Disconnect mode waits inside the actual worker/gate, the browser closes the
real response connection, then an owned filesystem release.flag explicitly
releases genuine public computation and encoding. The test does not claim
cancellation kills the numerical thread or releases the gate prematurely.

### Genuine failed prefixes, including numerical and unexpected failures

All six V2d partial combinations passed both the direct API validator and one
real browser scenario; the legacy V2b index-3 control also passed. The table
records real replies and child counters, not fabricated UI statuses.

| Capture label | HTTP / error | Completed / failed index | Point attempts | Genuine public calls | API / browser exit |
|---|---|---:|---:|---:|---|
| `pol_num0` | 422 / `numerical_failure` | 0 / 0 | 1 | 0 | 0 / 0 |
| `pol_unexpected0` | 500 / `sweep_failed` | 0 / 0 | 1 | 0 | 0 / 0 |
| `pol_numerical3_retry` | 422 / `numerical_failure` | 3 / 3 | 4 | 3 | 0 / 0 |
| `pol_unexpected3_retry` | 500 / `sweep_failed` | 3 / 3 | 4 | 3 | 0 / 0 |
| `pol_numerical12_retry` | 422 / `numerical_failure` | 12 / 12 | 13 | 12 | 0 / 0 |
| `pol_unexpected12_retry` | 500 / `sweep_failed` | 12 / 12 | 13 | 12 | 0 / 0 |
| `legacy_partial3_retry` | 422 / `numerical_failure` | 3 / 3 | 4 | 3 | 0 / 0 |

V2d calls in the table are actual polarizer/retarder application counts for
the one-element analyzer. Legacy calls are actual run_two_arm calls.
Each V2d prefix retains submitted experiment/SHA, selected element, actual
angle sequence, requested_count=13, ordered stages, stage losses, total delta,
completion count and failure index. Missing suffix rows are neither filled
nor marked complete, and there is no implicit numerical retry.

Evidence for each label: controlled_service_<label>/api_partial.json,
controlled_service_<label>/harness/operation_<request_id>.json,
controlled_browser_<label>/v2d/browser_controlled_partial_<index>_<code>.json
(or unchanged V2b partial JSON). API and browser call records are separate
genuine invocations, so counters are not added together as one request.
The exact API/browser argument vectors, stdout/stderr and exits are preserved
in controlled_api_<label>_* and controlled_browser_<label>_*.

The completed browser invocation outputs are reproduced below.

### Controlled browser: pol_num0

Capture: `controlled_browser_pol_num0_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/@playwright/test/cli.js' 'test' 'tests/polarization.browser.spec.ts' '--grep' 'controlled actual failed sweep' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\controlled_browser_pol_num0\test-results'
```

Unedited full stdout:

```text

Running 1 test using 1 worker

  ok 1 tests\polarization.browser.spec.ts:384:1 › controlled actual failed sweep keeps only genuine contiguous rows (4.3s)

  1 passed (5.6s)
```

Stderr preserved as `controlled_browser_pol_num0_stderr.txt` (164 bytes; SHA-256 `83e6ac9898c8ecc002f62dc3137c4ce6150ce614e169e86c2c1bd4dd107e20ab`).

### Controlled browser: pol_unexpected0

Capture: `controlled_browser_pol_unexpected0_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/@playwright/test/cli.js' 'test' 'tests/polarization.browser.spec.ts' '--grep' 'controlled actual failed sweep' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\controlled_browser_pol_unexpected0\test-results'
```

Unedited full stdout:

```text

Running 1 test using 1 worker

  ok 1 tests\polarization.browser.spec.ts:384:1 › controlled actual failed sweep keeps only genuine contiguous rows (4.1s)

  1 passed (5.4s)
```

Stderr preserved as `controlled_browser_pol_unexpected0_stderr.txt` (164 bytes; SHA-256 `85d29f33c9b2981a8f0945a4ebc94f9a24ff9c6d641b34175c0be361a5bf5550`).

### Controlled browser: pol_numerical3_retry

Capture: `controlled_browser_pol_numerical3_retry_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/@playwright/test/cli.js' 'test' 'tests/polarization.browser.spec.ts' '--grep' 'controlled actual failed sweep' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\controlled_browser_pol_numerical3_retry\test-results'
```

Unedited full stdout:

```text

Running 1 test using 1 worker

  ok 1 tests\polarization.browser.spec.ts:384:1 › controlled actual failed sweep keeps only genuine contiguous rows (4.4s)

  1 passed (5.7s)
```

Stderr preserved as `controlled_browser_pol_numerical3_retry_stderr.txt` (164 bytes; SHA-256 `c6df6263abdf24d7c2bc218b136bac94907265ca5183c00144ef408279466b3a`).

### Controlled browser: pol_unexpected3_retry

Capture: `controlled_browser_pol_unexpected3_retry_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/@playwright/test/cli.js' 'test' 'tests/polarization.browser.spec.ts' '--grep' 'controlled actual failed sweep' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\controlled_browser_pol_unexpected3_retry\test-results'
```

Unedited full stdout:

```text

Running 1 test using 1 worker

  ok 1 tests\polarization.browser.spec.ts:384:1 › controlled actual failed sweep keeps only genuine contiguous rows (4.2s)

  1 passed (5.6s)
```

Stderr preserved as `controlled_browser_pol_unexpected3_retry_stderr.txt` (164 bytes; SHA-256 `a3f11f5699c865914bc0284d91214b37be660541054a37653db0074462e28885`).

### Controlled browser: pol_numerical12_retry

Capture: `controlled_browser_pol_numerical12_retry_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/@playwright/test/cli.js' 'test' 'tests/polarization.browser.spec.ts' '--grep' 'controlled actual failed sweep' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\controlled_browser_pol_numerical12_retry\test-results'
```

Unedited full stdout:

```text

Running 1 test using 1 worker

  ok 1 tests\polarization.browser.spec.ts:384:1 › controlled actual failed sweep keeps only genuine contiguous rows (4.4s)

  1 passed (5.7s)
```

Stderr preserved as `controlled_browser_pol_numerical12_retry_stderr.txt` (164 bytes; SHA-256 `6cec4c365eafda701a698c1cd3f35ab3a46ff0e9027c28eae11f3be4481bef3a`).

### Controlled browser: pol_unexpected12_retry

Capture: `controlled_browser_pol_unexpected12_retry_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/@playwright/test/cli.js' 'test' 'tests/polarization.browser.spec.ts' '--grep' 'controlled actual failed sweep' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\controlled_browser_pol_unexpected12_retry\test-results'
```

Unedited full stdout:

```text

Running 1 test using 1 worker

  ok 1 tests\polarization.browser.spec.ts:384:1 › controlled actual failed sweep keeps only genuine contiguous rows (4.3s)

  1 passed (5.6s)
```

Stderr preserved as `controlled_browser_pol_unexpected12_retry_stderr.txt` (164 bytes; SHA-256 `9a02ef4cca3fb9e0a2314e51b1c30a3d27eac8028a5e0a25a6dd8128de29ab70`).

### Controlled browser: legacy_partial3_retry

Capture: `controlled_browser_legacy_partial3_retry_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/@playwright/test/cli.js' 'test' 'tests/two_path.browser.spec.ts' '--grep' 'controlled partial failure' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\controlled_browser_legacy_partial3_retry\test-results'
```

Unedited full stdout:

```text

Running 1 test using 1 worker

  ok 1 tests\two_path.browser.spec.ts:315:1 › controlled partial failure retains only genuine prefix and never labels sweep complete (2.6s)

  1 passed (3.6s)
```

Stderr preserved as `controlled_browser_legacy_partial3_retry_stderr.txt` (164 bytes; SHA-256 `6a072e3e9a9a3c6fe9632190e534f2491f42481ad7dc62046aaca5a7892fba6c`).

### Real disconnect and terminal-completion gate lifetime

All five worker classes were separately held and disconnected in a real
browser. Every controlled browser invocation exited 0. Health remained busy
while the actual worker was held and became idle only after genuine numerical
work and result encoding reached terminal completion. Explicit recovery was
then checked against independent public evidence.

| Held/disconnected worker | Terminal HTTP status | Encoded bytes | Sweep attempts | Actual counted public work |
|---|---:|---:|---:|---|
| `sequential` | 200 | 2106592 | 0 | V0 worker; no Jones/two-arm counter |
| `dual` | 200 | 68392 | 0 | 1 two-arm runs |
| `sweep` | 200 | 7354 | 17 | 17 two-arm runs |
| `polarization` | 200 | 68384 | 0 | 1 element applications |
| `polarization_sweep` | 200 | 8468 | 13 | 13 element applications |

Browser route coverage is reported precisely: the unchanged sequential
browser checks rejection of the V1 simulation route; unchanged dual/sweep
browser cases check V1 simulation, V2b simulation and V2b sweep; each new
polarization/polarization-sweep case checks all five computation routes return
409 while held. Validation remains usable. The new Python server matrix
separately covers all 25 holder/contender pairs, all five actual worker classes
under disconnect and handler cancellation, and encoding lifetime. Legacy
browser subsets are not falsely described as all-five route matrices.

For each holder, harness/started.json, completed.json, release file, browser
request/status evidence and cleanup record demonstrate the actual sequence.
A disposable service's forced termination exit after acceptance is not confused
with its browser/API acceptance exit. Every completed cleanup records
acceptance_exit=0, idle health, and no_unrelated_service_managed=true.

### Controlled real-browser disconnect: sequential

Capture: `controlled_browser_disconnect_sequential_retry_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/@playwright/test/cli.js' 'test' 'tests/bench.browser.spec.ts' '--grep' 'actual browser disconnect keeps' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\controlled_browser_disconnect_sequential_retry\test-results'
```

Unedited full stdout:

```text

Running 1 test using 1 worker

  ok 1 tests\bench.browser.spec.ts:329:1 › actual browser disconnect keeps running worker busy until controlled completion (2.3s)

  1 passed (3.1s)
```

Stderr preserved as `controlled_browser_disconnect_sequential_retry_stderr.txt` (164 bytes; SHA-256 `8befdc05f6d760b4562b1e81816fef658c0dbb1cec8295b0c7e6cbe10d95e416`).

### Controlled real-browser disconnect: dual

Capture: `controlled_browser_disconnect_dual_retry_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/@playwright/test/cli.js' 'test' 'tests/two_path.browser.spec.ts' '--grep' 'actual two-path browser disconnect' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\controlled_browser_disconnect_dual_retry\test-results'
```

Unedited full stdout:

```text

Running 1 test using 1 worker

  ok 1 tests\two_path.browser.spec.ts:331:1 › actual two-path browser disconnect holds all numerical routes until genuine worker completion (5.2s)

  1 passed (6.3s)
```

Stderr preserved as `controlled_browser_disconnect_dual_retry_stderr.txt` (164 bytes; SHA-256 `50e21c86b3df61238d0d4b476ae5d17db541dd3401343c691b7543aad5a1cbcd`).

### Controlled real-browser disconnect: sweep

Capture: `controlled_browser_disconnect_sweep_retry_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/@playwright/test/cli.js' 'test' 'tests/two_path.browser.spec.ts' '--grep' 'actual two-path browser disconnect' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\controlled_browser_disconnect_sweep_retry\test-results'
```

Unedited full stdout:

```text

Running 1 test using 1 worker

  ok 1 tests\two_path.browser.spec.ts:331:1 › actual two-path browser disconnect holds all numerical routes until genuine worker completion (5.2s)

  1 passed (6.5s)
```

Stderr preserved as `controlled_browser_disconnect_sweep_retry_stderr.txt` (164 bytes; SHA-256 `7fc1061d94ebd4e73f5554be43de88690d8f4e87485accd418a7652b9e9d771f`).

### Controlled real-browser disconnect: polarization

Capture: `controlled_browser_disconnect_polarization_retry_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/@playwright/test/cli.js' 'test' 'tests/polarization.browser.spec.ts' '--grep' 'actual polarization browser disconnect' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\controlled_browser_disconnect_polarization_retry\test-results'
```

Unedited full stdout:

```text

Running 1 test using 1 worker

  ok 1 tests\polarization.browser.spec.ts:400:1 › actual polarization browser disconnect holds all five operations until genuine worker completion (7.7s)

  1 passed (8.8s)
```

Stderr preserved as `controlled_browser_disconnect_polarization_retry_stderr.txt` (163 bytes; SHA-256 `531e7f417b946f691ba8631d2e0d5a7a73bfa0f54a98d185695d5c66c80607b1`).

### Controlled real-browser disconnect: polarization_sweep

Capture: `controlled_browser_disconnect_polarization_sweep_retry_*`; exit 0.

Cwd: `C:\holographiclab\frontend\bench`.

```powershell
& 'C:\Program Files\nodejs\node.exe' 'node_modules/@playwright/test/cli.js' 'test' 'tests/polarization.browser.spec.ts' '--grep' 'actual polarization browser disconnect' '--output' 'C:\holographiclab\runs\v2d_acceptance_20261012_01\controlled_browser_disconnect_polarization_sweep_retry\test-results'
```

Unedited full stdout:

```text

Running 1 test using 1 worker

  ok 1 tests\polarization.browser.spec.ts:400:1 › actual polarization browser disconnect holds all five operations until genuine worker completion (7.8s)

  1 passed (8.6s)
```

Stderr preserved as `controlled_browser_disconnect_polarization_sweep_retry_stderr.txt` (164 bytes; SHA-256 `ba1775e4ae7fabf15f26b2d459b58c7140d5b28802986eac967d66ef1cfa8be5`).

### Preserved port conflict and explicit retry

controlled_batch01.json preserves an interrupted batch: after pol_unexpected0
passed, the next exclusive bind encountered Windows WinError 10048. That is
local-port availability failure, not numerical failure or an assertion pass.
The original batch/error output was retained. The explicit retry waits for
exclusive availability of the same fixed port; it does not enable address
reuse, select a fallback port, or terminate another port owner. Each subsequent
child has its own fresh label and evidence.
controlled_batch_retry01.json records ten requested retries, all exit 0,
failure=null. With the separately completed pol_num0 and initial
pol_unexpected0, all twelve requested controlled browser invocations are
complete: seven partial-prefix scenarios and five disconnect holders.

### Exact controlled CLI and browser selection

The committed harness's accepted arguments are:

~~~powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -X utf8 scripts/v2d_controlled_acceptance_server.py --mode partial --operation polarization_sweep --failure-index 3 --failure-kind numerical --evidence-dir runs/<fresh-owned>/harness
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -X utf8 scripts/v2d_controlled_acceptance_server.py --mode disconnect --operation polarization --evidence-dir runs/<fresh-owned>/harness
~~~

Partial mode accepts indices 0/3/12 and numerical/unexpected.
Disconnect holders accept sequential, dual, sweep, polarization, or
polarization_sweep. Run only one owned service at a time and require exclusive
fixed-port availability. An unavailable port is a stop/retry condition,
not authorization to kill its owner or change production binding.

The task's ignored local coordination driver reproduces child ownership,
readiness, explicit API/browser selection and cleanup:

~~~powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -X utf8 runs/v2d_acceptance_20261012_01/controlled_driver.py <fresh-partial-label> --mode partial --operation polarization_sweep --index 3 --kind numerical
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -X utf8 runs/v2d_acceptance_20261012_01/controlled_driver.py <fresh-disconnect-label> --mode disconnect --operation polarization
~~~

For V2d partial browser selection it copies the environment, adds
V2D_PARTIAL_ONLY=1 and V2D_PARTIAL_EVIDENCE=<fresh api_partial.json>, and
runs the installed Playwright CLI on tests/polarization.browser.spec.ts with
--grep 'controlled actual failed sweep' and a fresh --output directory.
The API validator is explicitly invoked with --controlled-partial-index
and selected --failure-kind against that controlled child.
For V2d disconnect it instead adds V2D_DISCONNECT_ONLY=1,
V2D_DISCONNECT_DIR=<owned harness directory> and
V2D_DISCONNECT_OPERATION=polarization|polarization_sweep, and selects
--grep 'actual polarization browser disconnect'.
All evidence/figure paths remain child-only redirects as in the normal driver.
Legacy controls use existing V1 cancellation or V2b partial/disconnect variables
and unchanged browser scenarios. There is no automatic test fallback or hidden
production mutation hook.

## Evidence limits and final publication gates

Scientific validation concerns deterministic, fully coherent monochromatic
Jones fields in one common plane/basis, with ideal linear elements and selected
finite inputs. It does not establish hardware fidelity, calibrated power,
propagation between elements, broadband/mixed-state polarization, persistence,
or visibility of arbitrarily weak fields. Browser resource evidence measures
owned buffers/stores/resources and bounded accounting, not full browser/GPU
memory. Synthetic tiny-sample and allocation-fault supplements are labelled
separately from genuine solver/browser scenarios. Explicit controlled children
are separate from ordinary production execution.

The precommit source/build proof, final-source API recapture, complete normal
browser suite, separately executed controls, final complete Python/frontend
suites and genuine inspected screenshots are completed above. Historical
captures and failed attempts remain intact. Later milestones were not begun.

The exact approved 35-path scope/protected inventory, one approved commit,
clean-postcommit rebuild, source/asset ownership and three-mode browser smoke,
normal push, and local/remote/GitHub
API SHA equality are release gates owned by the root workflow. At drafting,
publication was still pending; no commit/push or clean-postcommit success is
inferred from these precommit results. Actual release outcomes must be
reported separately after execution without rewriting these measurements.
