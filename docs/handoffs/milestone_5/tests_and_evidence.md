# Milestone 5 — Tests and reproducible evidence

Completed 2026-09-23 (Asia/Taipei). Work began on 2026-09-22; original capture
directory names and UTC timestamps are retained. This is shipped M5 candidate
evidence, not replacement M0–M4 measurements or planning-probe evidence.

The accepted baseline was `5b8e278d2f105552d8ef7d951aaa5161c01c801a` on clean
`main`, upstream `origin/main`, ahead/behind 0/0, matching the live remote.
Every command below uses the existing Windows-native repository interpreter
from `C:\holographiclab`. No dependency/environment replacement occurred.
Fresh ignored temporary directories contain only this task's generated data.

## Baseline and final full suite

The baseline had 904 passing cases. The final suite retains them unchanged and
adds 248 configuration cases and 140 artifact cases: 139 pass and one real
file-symlink case is skipped because this Windows account lacks the required
privilege. A separate actual directory-junction rejection test passes. The
skip is a coverage limitation, not evidence that the file-symlink test ran.

The final complete suite ran after all seven isolated negative controls and
the publication refinement. There is no test-count quota or claim of zero
possible gaps. Commands and unedited captured output follow in Appendix A.

## Fixture, comparisons and independent checks

The twelve-case replay matrix uses a rectangular `(3,5)` grid, `dy=10e-6 m`,
`dx=8e-6 m`, wavelength `633e-9 m`, distance `-2e-4`, `0` or `+2e-4 m`,
iterations `0` or `5`, and seed `7` or explicit phase
`linspace(-7,8,15).reshape(3,5)`. The grayscale codes are:

```text
  0  16  32  64 255
128 192   8  48  96
224  16  64 128 192
```

Target intensity is `codes.astype(float64)/255`, actual target amplitude is
the public M2 square root, and explicit uniform source amplitude is
`sqrt(sum(target_amplitude**2)/15)`. Two distinct Boolean regions exercise
fraction and CV; PSNR uses explicit range 1. The test compares saved outputs
with a separate direct public M3 call and then invokes actual replay.
That reference checks wrapper orchestration, not independent optical physics;
the unchanged baseline retains the earlier analytic/direct-DFT validations.

All exact array comparisons require dtype representation, shape and logical
C-order bytes. Finite metric comparisons use binary64 bits; PSNR infinity is
handled separately. No relative/absolute tolerance applies to this exactness
claim, and there is no approximate fallback. Signed float and complex zeros,
finite scalar round trips, C/F/strided/read-only input capture, loaded storage
ownership and nested configuration copies have dedicated cases.

The matrix uses an explicitly synthetic caller SHA (`1` repeated 40 times) to
exercise qualification policy. It does not attest which candidate code ran.
Real example/relocation evidence independently detects the imported checkout,
records baseline HEAD plus `dirty`, and remains unqualified. Postcommit
qualification is deliberately a separate publication check.

| Behavior | Detecting test / evidence |
|---|---|
| All inputs captured before one solver invocation | `test_all_inputs_are_snapshotted_before_solver_and_only_one_solve_occurs` mutates original arrays inside the instrumented solver |
| Exact manifest inventory and whole-file hashes | `test_manifest_hashes_raw_files_with_exact_sorted_inventory`; independently calculated digests and metadata |
| Corruption rejected before decoding/solving | `test_modified_payload_is_detected_before_any_array_decode_or_solver_call`; instrumented decoder/solver |
| Config/metric/complex files all hashed | `test_modified_metadata_and_numerical_files_are_all_hashed` |
| Rehashed wrong metric can pass integrity yet fail semantics | `test_rehashed_wrong_metric_passes_integrity_but_fails_recomputation` |
| Changed valid seed/distance really change results | `test_rehashed_valid_changed_config_fails_actual_numerical_replay`; nondegenerate fixture above |
| Qualification does not imply numerical agreement | `test_same_qualification_with_wrong_rehashed_complex_output_is_comparison_failure` |
| Numerical agreement does not override provenance mismatch | `test_diagnostic_matching_numerics_never_override_provenance_mismatch` |
| Default unqualified comparison is not run | `test_unqualified_replay_does_not_run_solver_by_default`; solver spy |
| Foreign-endian diagnostic execution is blocked, not compared | `test_foreign_endian_bundle_is_inspectable_but_diagnostic_replay_is_not_run`; fully rehashed foreign-endian fixture and solver spy |
| Runtime independently measured; path/CPU count informational | `test_recorded_runtime_is_compared_with_independent_current_runtime`, `test_informational_environment_paths_do_not_control_qualification` |
| Unsafe paths rejected before outside-file reads | `test_unsafe_manifest_paths_fail_before_instrumented_outside_reads`; ten path forms |
| Strict nested schema before solver | `test_rehashed_invalid_config_fails_schema_before_solver` and configuration tests |
| Narrow NPY reader, not only np.load | `test_rehashed_malformed_npy_is_rejected_by_narrow_format_contract`; eleven malformed format cases |
| Same verified bytes decoded, pickle disabled | `test_safe_loader_explicitly_disables_pickle_and_uses_verified_byte_streams`, `test_load_decodes_verified_snapshots_even_if_disk_changes_after_hashing` |
| No clipping of unchanged M4 output | `test_valid_m4_fraction_rounding_above_one_is_preserved_without_clipping`; `1.0000000000000002` roundoff case |
| PNG is optional provenance, not external replay input | `test_optional_original_png_preserves_exact_bytes_and_is_not_replay_input` and fresh-process relocation |

## Transactional failure and bounded Windows refinement

Four injected failures cover artifact writing, fsync, manifest writing and
publication. They assert the original exception object survives, no destination
is published, unrelated files remain untouched, and owned staging is removed.
Separate cases exercise an exclusive-create collision (the foreign file must
not become cleanup-owned), cleanup failure notes and leftover paths, manifest
last/all handles closed, existing file/directory destinations, and a destination
appearing immediately before real Windows rename. Public verify/load/replay
all reject reserved partial directories while private staged validation uses
the shared content checks.

During discovery, ordinary directory rename raised intermittent `WinError 5`
in different fixtures, twice in focused runs and twice in full suites,
including a run outside the sandbox. A separate 100-save probe had no failure.
No handle leak or cause was identified; this is not attributed to antivirus,
the sandbox or any other unverified external cause. The failed observations
are preserved separately below and are not relabeled successful runs.

The bounded refinement remains within the approved publication boundary:
Windows error 5 only, at most four attempts with waits of 10/30/100 ms, only
while the destination is absent, with existence rechecked after each wait.
Exhaustion preserves the first access-denial error; a later different error
propagates as itself. Other errors/platforms do not retry. There is no
overwrite, lock, copy fallback or eventual-success guarantee. Eight direct
retry tests passed, followed by the final full suite. This improves handling
of transient denial without identifying its cause or weakening the tests.

## Seven deliberate negative controls

The driver in Appendix D runs a baseline child and a mutated child for each
control. It changes production functions only in child-process memory, never
tracked source/test files. Pytest call-phase `AssertionError`/`Failed` is
required; collection, setup, teardown and unexpected exception failures do
not count as detection. Each child exits, discarding the mutation.

| Mutation | Intended assertion failures |
|---|---:|
| Default missing distance | 1 |
| Skip artifact digest comparison | 1 |
| Ignore saved-data metric comparison | 1 |
| Load source amplitude into target role | 12 |
| Default missing PSNR range | 1 |
| Read unknown path before validation | 1 |
| Increment replay seed | 6 |

All 29 selected baseline cases passed. Mutants produced 23 intended assertion
failures; six explicit-phase matrix cases were unaffected by the seed-only
mutation and passed. All 14 children completed with the expected outcomes.
All 33 source/test Python files had identical before/after byte hashes;
aggregate inventory SHA-256 was
`6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296`
both times. The full suite was then rerun successfully. The exact final
transcript records selectors, commands, call/phase reports and restoration
checks; an earlier pre-refinement transcript remains an ignored historical
capture and is not the final evidence below.

## Example and fresh-process relocation

The standalone example exercises actual PNG decoding through M2, M3, M4,
save, verify, load and replay. It uses a 64×64 grayscale Gaussian design,
width 60 µm, 8 µm pitches, wavelength 633 nm, distance 5 mm, seed 0 and 50
cycles. Explicit per-target illumination and the 709-pixel disk are printed.
Appendix B contains the exact precommit output: integrity passed, qualification
unqualified, explicit diagnostic mode true, and all 16 comparison checks
passed. The recorded M4 SHA describes HEAD only; dirty M5 code is not falsely
attributed to that exact revision.

The separate relocation probe starts a saving child, waits for exit, copies
the completed bundle, checks all twelve file hashes, deletes only its owned
external PNG fixture and renames only its owned original bundle. A new replay
child starts from a different working directory with only the relocated
bundle and installed code. The original paths are unavailable, process IDs
differ, and all 14 checks pass. Current provenance still comes independently
from the imported `ohlab` checkout. Dirty candidate state remains unqualified.
The complete probe and exact output in Appendix C make this reproducible;
the pytest suite independently covers a fresh-process relocation case too.

After the single approved commit, a fresh default example must capture the
actual clean commit and pass qualified same-environment replay before push.
Its ignored output and the completion report record that result. This
precommit document does not invent its own final SHA or postcommit success.

## Figures and scope preservation

```powershell
.\.venv\Scripts\python.exe -B scripts\make_m5_figures.py
```

Both 2160×1530 explanatory diagrams were visually reviewed and regenerated
twice with identical hashes. They perform no numerical computation and are
not reconstruction evidence.

| Figure | Bytes | SHA-256 |
|---|---:|---|
| `fig01_run_bundle_anatomy.png` | 298711 | `c13002597c80fe523ac041a180491e806ff0dc0c1e5631d9b05469cb5253dd39` |
| `fig02_integrity_and_replay.png` | 284178 | `72a2ab72aca72de39fceff75c8d1501d532ddbeda861c146e2859eca5a50e5d0` |

The complete seventeen-path inventory is in [code map](code_map.md). Byte
hashes captured for all 100 pre-existing tracked files verify all 97 outside
the three allowed documentation modifications remain unchanged. Existing
numerical source, tests, guards, initializers, dependencies, AGENTS.md,
CLAUDE.md and historical handoffs/figures are preserved. The new tests add
coverage without altering baseline tests. Generated bundles/probes stay in
ignored locations. No M6 work or learning-record changes are included.

Limitations are enumerated in [known limitations](known_limitations.md).
These results establish the stated finite cases on CPython 3.11.9, NumPy
2.4.6, SciPy 1.17.1 and Pillow 12.3.0 on this Windows host. They are not
cross-version, cross-platform, physical-device or universal determinism claims.

## Appendix A — Exact suite captures

Commands exited 0. Captured stdout/stderr is reproduced without edits to
content or whitespace; Markdown uses LF in place of platform CRLF.

### Accepted M4 baseline; 2026-09-22

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --basetemp .pytest_cache/m5-implementation-baseline-20260922-a
```

```text
........................................................................ [  7%]
........................................................................ [ 15%]
........................................................................ [ 23%]
........................................................................ [ 31%]
........................................................................ [ 39%]
........................................................................ [ 47%]
........................................................................ [ 55%]
........................................................................ [ 63%]
........................................................................ [ 71%]
........................................................................ [ 79%]
........................................................................ [ 87%]
........................................................................ [ 95%]
........................................                                 [100%]
904 passed in 7.98s
```

### Final M5 suite; 2026-09-23

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest -q -p no:cacheprovider --basetemp runs/m5-implementation-evidence-20260922/pytest-release-final-a
```

```text
........................................................................ [  5%]
........................................................................ [ 11%]
........................................................................ [ 16%]
........................................................................ [ 22%]
........................................................................ [ 27%]
........................................................................ [ 33%]
........................................................................ [ 39%]
........................................................................ [ 44%]
........................................................................ [ 50%]
........................................................................ [ 55%]
........................................................................ [ 61%]
........................................................................ [ 66%]
..................................................................s..... [ 72%]
........................................................................ [ 78%]
........................................................................ [ 83%]
........................................................................ [ 89%]
........................................................................ [ 94%]
....................................................................     [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
1291 passed, 1 skipped in 16.47s
```

## Appendix B — Exact final precommit example

### Default example; exit 0

```powershell
.\.venv\Scripts\python.exe -B -X utf8 examples\run_bundle.py
```

```text
run directory: C:\holographiclab\runs\m5\example-bae5dadc340e4e8595901be35133c966
schema_version: 1; deterministic numerical fixture; directory UUID is only a label
grid: ny=64, nx=64, dy_m=8e-06, dx_m=8e-06
optics: wavelength_m=6.33e-07, distance_m=0.005
solver: gerchberg_saxton; contract=m3_periodic_lossless_asm_v1; iterations=50; seed=0
target: strict 8-bit grayscale PNG; I=g/255; A=sqrt(I); Gaussian width=60e-06 m
configured uniform source amplitude: 2.93462716737912188e-01 a.u.
source power: 2.25759372549019720e-08 a.u. m^2
target power: 2.25759372549019588e-08 a.u. m^2
signal mask: (row-32)^2+(column-32)^2 <= 225; 709 pixels; PSNR data_range=1
Illumination is explicitly configured for this target; no target normalization is added.
recorded software/environment: {"informational_environment": {"cpu_count": 24, "python_executable": "C:\\holographiclab\\.venv\\Scripts\\python.exe"}, "ohlab_version": "0.1.0.dev0", "required_environment": {"byteorder": "little", "fft": "numpy.fft", "machine": "AMD64", "numpy_version": "2.4.6", "pillow_version": "12.3.0", "platform": "Windows-10-10.0.26100-SP0", "pointer_bits": 64, "processor": "Intel64 Family 6 Model 198 Stepping 2, GenuineIntel", "python_implementation": "CPython", "python_version": "3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]", "scipy_version": "1.17.1"}, "source": {"method": "git", "revision": "5b8e278d2f105552d8ef7d951aaa5161c01c801a", "state": "dirty"}}
independently detected current source: {"method": "git", "revision": "5b8e278d2f105552d8ef7d951aaa5161c01c801a", "state": "dirty"}
artifact integrity: passed
source/environment qualification: unqualified
explicit diagnostic mode: True
numerical comparison: passed
qualification reasons: recorded source state is dirty, expected clean; current source state is dirty, expected clean
individual replay checks: {"derived:phase": true, "derived:reconstruction_intensity": true, "derived:target_amplitude": true, "output:phase": true, "output:reconstruction_field": true, "output:reconstruction_intensity": true, "output:residual_history": true, "output:source_field": true, "replay_metric:intensity_mse": true, "replay_metric:intensity_nmse": true, "replay_metric:intensity_psnr": true, "replay_metric:signal_region_power_fraction": true, "saved_metric:intensity_mse": true, "saved_metric:intensity_nmse": true, "saved_metric:intensity_psnr": true, "saved_metric:signal_region_power_fraction": true}
intensity_mse: 4.81562267041563932e-04
intensity_nmse: 1.11723641621580324e-02
intensity_psnr: 3.31734754969381669e+01
signal_region_power_fraction: 8.38568123674199528e-01
metric parameters: {"intensity_mse": {}, "intensity_nmse": {}, "intensity_psnr": {"data_range": 1.0}, "signal_region_power_fraction": {"mask": "signal_mask.npy"}}
separate M3 squared amplitude residual: 1.71252990524567231e-02
load check: dtype/shape/element bytes unchanged; original temporary PNG no longer exists
SHA-256 establishes integrity relative to the manifest, not authorship or physical accuracy.
```

## Appendix C — Complete fresh-process relocation probe

This exact historical driver deliberately asserts dirty precommit provenance.
It is not directly suitable for the final clean checkout: use the two-line
clean-checkout adaptation below when reproducing there. Do not dirty or
change the checkout merely to manufacture the historical condition.
Save the script at the ignored path shown in the command. It creates
a unique owned directory each time; it does not touch real user inputs.

```python
"""Fresh-process, real-provenance M5 relocation evidence; only owned fixtures."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
PARENT = ROOT / 'runs' / 'm5-implementation-evidence-20260922'
owned = PARENT / ('relocation-' + uuid4().hex)
owned.mkdir()
saving = owned / 'saving'
saving.mkdir()
other = owned / 'different-working-directory'
other.mkdir()
original = saving / 'original-bundle'
copied = owned / 'copied-bundle'
external = saving / 'external-input.png'

save_code = r'''
from pathlib import Path
import json, os, runpy, sys
import numpy as np
from PIL import Image
from ohlab import SamplingGrid
from ohlab.io.images import load_target_intensity
from ohlab.targets import intensity_to_amplitude
from ohlab.io.config import RunConfig
from ohlab.io.artifacts import run_and_save_bundle
root, external, destination = map(Path, sys.argv[1:])
detect = runpy.run_path(str(root / 'examples' / 'run_bundle.py'))['_detect_source_revision']
codes=(np.arange(15,dtype=np.uint8).reshape(3,5)*17).astype(np.uint8)
with Image.fromarray(codes) as image:
    image.save(external,format='PNG')
grid=SamplingGrid(ny=3,nx=5,dy=10e-6,dx=8e-6)
target=load_target_intensity(external,grid=grid)
amplitude=intensity_to_amplitude(target,grid=grid)
source=np.full(grid.shape,np.sqrt(np.sum(amplitude**2)/amplitude.size))
settings={'schema_version':1,'grid':{'ny':3,'nx':5,'dy_m':10e-6,'dx_m':8e-6},
 'optics':{'wavelength_m':633e-9,'distance_m':2e-4},
 'solver':{'algorithm':'gerchberg_saxton','contract':'m3_periodic_lossless_asm_v1',
 'iterations':5,'initialization':{'mode':'seed','seed':7}},
 'metrics':{'intensity_mse':{},'intensity_nmse':{},'intensity_psnr':{'data_range':1.0}}}
provenance=detect()
bundle=run_and_save_bundle(destination,config=RunConfig(settings),target_intensity=target,
 source_amplitude=source,input_png=external,source_revision=provenance)
print(json.dumps({'stage':'saved','pid':os.getpid(),'cwd':str(Path.cwd()),
 'source':provenance,'bundle':str(destination),'metrics':dict(bundle.metrics)},sort_keys=True))
'''
saved = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', save_code,
                        str(ROOT), str(external), str(original)], cwd=saving,
                       capture_output=True, text=True, encoding='utf-8')
print(saved.stdout, end='')
assert saved.returncode == 0, saved.stderr
save_record = json.loads(saved.stdout)
assert external.exists()
shutil.copytree(original, copied)
before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in original.iterdir()}
after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in copied.iterdir()}
assert before == after
# Explicitly verify ownership before removing/moving these generated fixtures.
unavailable = saving / 'original-bundle-unavailable'
for candidate in (external, original, unavailable):
    assert owned.resolve() in candidate.resolve().parents
external.unlink()
original.rename(unavailable)
assert not external.exists() and not original.exists()
print(json.dumps({'stage':'relocated','copied_files':len(after),'all_file_hashes_preserved':True,
 'original_png_available':False,'original_bundle_path_available':False},sort_keys=True))

replay_code = r'''
from pathlib import Path
import json, os, runpy, sys
import ohlab
from ohlab.io.artifacts import load_run_bundle,verify_run_bundle,replay_run_bundle
root,bundle_path=map(Path,sys.argv[1:])
detect=runpy.run_path(str(root/'examples'/'run_bundle.py'))['_detect_source_revision']
current=detect()
bundle=load_run_bundle(bundle_path)
report=replay_run_bundle(bundle_path,source_revision=current,diagnostic=True)
print(json.dumps({'stage':'replayed','pid':os.getpid(),'cwd':str(Path.cwd()),
 'imported_package':ohlab.__file__,'recorded_source':bundle.software['source'],
 'independently_detected_current_source':current,'artifact_integrity':verify_run_bundle(bundle_path).status,
 'qualification':report.qualification,'comparison':report.comparison,
 'diagnostic':True,'checks':dict(report.checks),'metrics':dict(bundle.metrics)},sort_keys=True))
assert report.integrity=='passed' and report.comparison=='passed'
assert report.qualification=='unqualified'
assert bundle.software['source']['state']=='dirty' and current['state']=='dirty'
assert all(report.checks.values())
'''
replayed = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', replay_code,
                          str(ROOT), str(copied)], cwd=other,
                         capture_output=True, text=True, encoding='utf-8')
print(replayed.stdout, end='')
assert replayed.returncode == 0, replayed.stderr
replay_record = json.loads(replayed.stdout)
assert save_record['pid'] != replay_record['pid']
assert save_record['cwd'] != replay_record['cwd']
assert save_record['source'] == replay_record['independently_detected_current_source']
assert save_record['metrics'] == replay_record['metrics']
print('PASS: saving process exited; copied bytes preserved; original paths unavailable; fresh process/new cwd replayed all outputs and metrics.')
```

For reproduction on the final clean checkout, replace only these assertions
inside `replay_code` in the ignored probe (the source-equality, process,
path-removal, digest and numerical assertions remain unchanged):

```python
assert report.qualification=='unqualified'
assert bundle.software['source']['state']=='dirty' and current['state']=='dirty'
```

with:

```python
assert report.qualification=='qualified'
assert bundle.software['source']['state']=='clean' and current['state']=='clean'
```

The following output is the original precommit run, not an asserted result
of that clean-checkout adaptation. The required clean-postcommit default
example is recorded separately in the completion report.

### Historical precommit relocation command and exact output; exit 0

```powershell
.\.venv\Scripts\python.exe -B -X utf8 runs\m5-implementation-evidence-20260922\relocation_probe.py
```

```text
{"bundle": "C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\relocation-8a8228749e1e4f148f57e1eefde06c5b\\saving\\original-bundle", "cwd": "C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\relocation-8a8228749e1e4f148f57e1eefde06c5b\\saving", "metrics": {"intensity_mse": 0.023293129689892663, "intensity_nmse": 0.07745252483092388, "intensity_psnr": 16.327721552723563}, "pid": 32484, "source": {"method": "git", "revision": "5b8e278d2f105552d8ef7d951aaa5161c01c801a", "state": "dirty"}, "stage": "saved"}
{"all_file_hashes_preserved": true, "copied_files": 12, "original_bundle_path_available": false, "original_png_available": false, "stage": "relocated"}
{"artifact_integrity": "passed", "checks": {"derived:phase": true, "derived:reconstruction_intensity": true, "derived:target_amplitude": true, "output:phase": true, "output:reconstruction_field": true, "output:reconstruction_intensity": true, "output:residual_history": true, "output:source_field": true, "replay_metric:intensity_mse": true, "replay_metric:intensity_nmse": true, "replay_metric:intensity_psnr": true, "saved_metric:intensity_mse": true, "saved_metric:intensity_nmse": true, "saved_metric:intensity_psnr": true}, "comparison": "passed", "cwd": "C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\relocation-8a8228749e1e4f148f57e1eefde06c5b\\different-working-directory", "diagnostic": true, "imported_package": "C:\\holographiclab\\src\\ohlab\\__init__.py", "independently_detected_current_source": {"method": "git", "revision": "5b8e278d2f105552d8ef7d951aaa5161c01c801a", "state": "dirty"}, "metrics": {"intensity_mse": 0.023293129689892663, "intensity_nmse": 0.07745252483092388, "intensity_psnr": 16.327721552723563}, "pid": 53964, "qualification": "unqualified", "recorded_source": {"method": "git", "revision": "5b8e278d2f105552d8ef7d951aaa5161c01c801a", "state": "dirty"}, "stage": "replayed"}
PASS: saving process exited; copied bytes preserved; original paths unavailable; fresh process/new cwd replayed all outputs and metrics.
```

## Appendix D — Complete final negative-control driver and transcript

Save this driver at the ignored path below; it creates fresh transcripts and
owned pytest temporary directories. Baseline/mutant commands and return
codes appear in the transcript. This is deliberate test evidence: mutant
assertion failures are expected, while the parent driver exits 0 only
when every required outcome and restoration check succeeds.

```python
r"""Seven isolated in-memory M5 production mutations; no source/test edits.

Run from the repository root with the existing project interpreter:
    .\.venv\Scripts\python.exe -B -X utf8 runs\m5-implementation-evidence-20260922\negative_controls.py

Each selected baseline and mutant runs in its own process. The parent preserves
complete subprocess stdout/stderr in a new, exclusively created transcript in
this same ignored evidence directory. Temporary pytest fixtures use fresh
owned directories below .pytest_cache. A mutation counts as detected only when
pytest returns 1 and at least one call-phase AssertionError/pytest Failed occurs,
with no collection, setup, teardown or other exception failures. Source/test
byte hashes must be identical before and after every child and the whole run.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import uuid


ROOT = Path(__file__).resolve().parents[2]
MARKER = "M5_NEGATIVE_CONTROL_RESULT "
MATRIX = "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported"
CASES = {
    "missing_distance_default": {
        "description": "Default a missing required optics.distance_m to 0.0 during RunConfig validation.",
        "selector": "tests/test_run_artifacts.py::test_rehashed_invalid_config_fails_schema_before_solver[missing_distance]",
    },
    "digest_skipped": {
        "description": "Disable the artifact SHA-256 comparison while preserving byte-count checks.",
        "selector": "tests/test_run_artifacts.py::test_modified_payload_is_detected_before_any_array_decode_or_solver_call",
    },
    "saved_metric_comparison_ignored": {
        "description": "Force saved-data metric comparison checks true, retaining replay-metric comparisons.",
        "selector": "tests/test_run_artifacts.py::test_rehashed_wrong_metric_passes_integrity_but_fails_recomputation",
    },
    "target_role_loads_source": {
        "description": "Decode verified source_amplitude.npy bytes for the target_amplitude role, preserving compatible shape/dtype.",
        "selector": MATRIX,
    },
    "missing_psnr_range_default": {
        "description": "Default missing required intensity_psnr.data_range to 1.0 during RunConfig validation.",
        "selector": "tests/test_run_artifacts.py::test_rehashed_invalid_config_fails_schema_before_solver[missing_psnr_range]",
    },
    "outside_read_before_path_validation": {
        "description": "Attempt to read an unknown manifest path before the existing allowlist rejection; instrumentation must stop the outside read.",
        "selector": "tests/test_run_artifacts.py::test_unsafe_manifest_paths_fail_before_instrumented_outside_reads[../outside.npy]",
    },
    "replay_seed_incremented": {
        "description": "Forward seed+1 only during replay solves; capture and explicit-phase solves remain unchanged.",
        "selector": MATRIX,
    },
}


def source_hashes() -> dict[str, str]:
    paths = sorted([*ROOT.joinpath("src").rglob("*.py"), *ROOT.joinpath("tests").rglob("*.py")])
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}


def inventory_digest(values: dict[str, str]) -> str:
    payload = json.dumps(values, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))


def replace_function(module, name: str, before: str, after: str) -> None:
    original = inspect.getsource(getattr(module, name))
    if original.count(before) != 1:
        raise RuntimeError(f"mutation anchor for {name!r} must occur exactly once")
    modified = "from __future__ import annotations\n" + original.replace(before, after, 1)
    namespace = {}
    exec(compile(modified, f"<m5-in-memory-negative-control:{name}>", "exec"),
         module.__dict__, namespace)
    setattr(module, name, namespace[name])


def install_mutation(case: str) -> None:
    import ohlab.io.artifacts as artifacts
    import ohlab.io.config as config

    if case == "missing_distance_default":
        replace_function(config, "_validate",
            '    optics = _keys(specification["optics"], {"wavelength_m", "distance_m"}, "optics")',
            '    raw_optics = _mapping(specification["optics"], "optics")\n'
            '    raw_optics.setdefault("distance_m", 0.0)\n'
            '    optics = _keys(raw_optics, {"wavelength_m", "distance_m"}, "optics")')
    elif case == "digest_skipped":
        replace_function(artifacts, "_verified_snapshots",
            '        if hashlib.sha256(data).hexdigest() != entry["sha256"]:',
            '        if False:  # Deliberately omit digest comparison.')
    elif case == "saved_metric_comparison_ignored":
        replace_function(artifacts, "replay_run_bundle",
            '                    checks[f"{prefix}:{name}"] = (actual == expected if math.isinf(expected)\n'
            '                        else struct.pack(">d", actual) == struct.pack(">d", expected))',
            '                    checks[f"{prefix}:{name}"] = True if prefix == "saved_metric" else (\n'
            '                        actual == expected if math.isinf(expected)\n'
            '                        else struct.pack(">d", actual) == struct.pack(">d", expected))')
    elif case == "target_role_loads_source":
        replace_function(artifacts, "_validated_contents",
            'snapshots[f"{role}.npy"]',
            'snapshots["source_amplitude.npy" if role == "target_amplitude" else f"{role}.npy"]')
    elif case == "missing_psnr_range_default":
        replace_function(config, "_validate",
            '        parameters = _keys(value, _METRIC_PARAMETERS[name], f"metrics.{name}")',
            '        if name == "intensity_psnr" and isinstance(value, Mapping):\n'
            '            value = dict(value)\n'
            '            value.setdefault("data_range", 1.0)\n'
            '        parameters = _keys(value, _METRIC_PARAMETERS[name], f"metrics.{name}")')
    elif case == "outside_read_before_path_validation":
        replace_function(artifacts, "_verified_snapshots",
            '        if not isinstance(name, str) or name not in _ALLOWED_FILES:',
            '        if isinstance(name, str) and name not in _ALLOWED_FILES:\n'
            '            (path / name).read_bytes()  # Deliberately premature outside read.\n'
            '        if not isinstance(name, str) or name not in _ALLOWED_FILES:')
    elif case == "replay_seed_incremented":
        original_replay, original_solve = artifacts.replay_run_bundle, artifacts._solve

        def wrong_seed(spec, arrays):
            modified = deepcopy(spec)
            initialization = modified["solver"]["initialization"]
            if initialization["mode"] == "seed":
                initialization["seed"] += 1
            return original_solve(modified, arrays)

        def replay_with_wrong_seed(*args, **kwargs):
            artifacts._solve = wrong_seed
            try:
                return original_replay(*args, **kwargs)
            finally:
                artifacts._solve = original_solve

        artifacts.replay_run_bundle = replay_with_wrong_seed
    else:
        raise RuntimeError(f"unknown mutation {case!r}")


def child(case: str, mode: str, basetemp: Path) -> int:
    import pytest
    from _pytest.outcomes import Failed

    before = source_hashes()
    failures, passed, collection_errors = [], [], []

    class Results:
        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_makereport(self, item, call):
            result = yield
            report = result.get_result()
            if report.failed:
                exc_type = call.excinfo.type if call.excinfo is not None else None
                detected = report.when == "call" and exc_type is not None and issubclass(exc_type, (AssertionError, Failed))
                failures.append({"nodeid": report.nodeid, "phase": report.when,
                                 "exception_type": exc_type.__name__ if exc_type else None,
                                 "assertion_detection": detected})
            elif report.when == "call" and report.passed:
                passed.append(report.nodeid)

        def pytest_collectreport(self, report):
            if report.failed:
                collection_errors.append(report.nodeid)

    if mode == "mutant":
        install_mutation(case)
    code = int(pytest.main(["-q", "--tb=short", "-p", "no:cacheprovider",
                           "--basetemp", str(basetemp), CASES[case]["selector"]], plugins=[Results()]))
    after = source_hashes()
    unchanged = before == after
    if mode == "baseline":
        accepted = code == 0 and bool(passed) and not failures and not collection_errors and unchanged
    else:
        accepted = (code == 1 and bool(failures) and all(f["assertion_detection"] for f in failures)
                    and not collection_errors and unchanged)
    print(MARKER + json.dumps({"case": case, "mode": mode, "pytest_exit": code,
        "passed": passed, "failures": failures, "collection_errors": collection_errors,
        "source_test_file_count": len(before), "before_inventory_sha256": inventory_digest(before),
        "after_inventory_sha256": inventory_digest(after), "changed_paths": changed_paths(before, after),
        "accepted": accepted}, sort_keys=True))
    return 0 if accepted else 2


def parent() -> int:
    evidence = Path(__file__).resolve().parent
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    token = uuid.uuid4().hex
    output = evidence / f"negative_controls_output_{stamp}_{token[:8]}.txt"
    before = source_hashes()
    accepted = True
    summaries = []
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        def emit(value: str) -> None:
            print(value, flush=True)
            stream.write(value + "\n")
            stream.flush()

        emit("M5 IN-MEMORY NEGATIVE CONTROLS")
        emit("Interpreter: " + sys.executable)
        emit("Source/test hashes before: " + json.dumps(before, sort_keys=True))
        for case, details in CASES.items():
            emit("\nCASE " + case + ": " + details["description"])
            for mode in ("baseline", "mutant"):
                basetemp = ROOT / ".pytest_cache" / f"m5-nc-{token}-{case}-{mode}"
                command = [sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()),
                           "--child", case, "--mode", mode, "--basetemp", str(basetemp)]
                emit("COMMAND " + json.dumps(command))
                process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                         encoding="utf-8", timeout=60)
                emit("STDOUT BEGIN\n" + process.stdout + "STDOUT END")
                emit("STDERR BEGIN\n" + process.stderr + "STDERR END")
                emit("CHILD EXIT " + str(process.returncode))
                records = [line[len(MARKER):] for line in process.stdout.splitlines() if line.startswith(MARKER)]
                if process.returncode != 0 or len(records) != 1:
                    accepted = False
                    emit("INVALID EVIDENCE: child failed or did not produce exactly one result record")
                    break
                record = json.loads(records[0])
                summaries.append(record)
                if not record["accepted"]:
                    accepted = False
                    break
            if not accepted:
                break
        after = source_hashes()
        all_unchanged = before == after
        accepted = accepted and all_unchanged and len(summaries) == 2 * len(CASES)
        emit("\nFINAL " + json.dumps({"accepted": accepted, "completed_children": len(summaries),
             "expected_children": 2 * len(CASES), "source_test_file_count": len(before),
             "before_inventory_sha256": inventory_digest(before), "after_inventory_sha256": inventory_digest(after),
             "changed_paths": changed_paths(before, after),
             "mutant_assertion_failures": sum(len(row["failures"]) for row in summaries if row["mode"] == "mutant"),
             "mutant_passing_cases": sum(len(row["passed"]) for row in summaries if row["mode"] == "mutant")}, sort_keys=True))
    print("TRANSCRIPT " + str(output), flush=True)
    return 0 if accepted else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", choices=CASES)
    parser.add_argument("--mode", choices=("baseline", "mutant"))
    parser.add_argument("--basetemp", type=Path)
    arguments = parser.parse_args()
    if arguments.child:
        if arguments.mode is None or arguments.basetemp is None:
            parser.error("--child requires --mode and --basetemp")
        raise SystemExit(child(arguments.child, arguments.mode, arguments.basetemp))
    raise SystemExit(parent())
```

```powershell
.\.venv\Scripts\python.exe -B -X utf8 runs\m5-implementation-evidence-20260922\negative_controls.py
```

Exact final transcript: `negative_controls_output_20260922T161142Z_39ee9876.txt`.

```text
M5 IN-MEMORY NEGATIVE CONTROLS
Interpreter: C:\holographiclab\.venv\Scripts\python.exe
Source/test hashes before: {"src/ohlab/__init__.py": "cdc7436c4772b5db4fa3124f0b7966dc7a5768ef449856b694f13a17768d669b", "src/ohlab/algorithms/__init__.py": "05f64a7b30efd0cf45d0a9b77ee293248b67eed0e980fa4c41f3bcd20e2e9fab", "src/ohlab/algorithms/gerchberg_saxton.py": "47cd3bb3cb05df28dcd912622dd27398836cb511b1598d5d953bf8244d74e019", "src/ohlab/field.py": "cace42f5deb0dda9f2d42e5a7ec7327edfa9442e89b33e6d045d6085f3e1d725", "src/ohlab/grid.py": "5448b7e9a2e648a53010d9ca8c0795b98057b325b3958d1de73d6800bad66909", "src/ohlab/io/__init__.py": "effb02996bd3fcea0075235f9ef45b4336958e17db90164d5257a341a94a399b", "src/ohlab/io/artifacts.py": "e1420d261859d9dc4a58b1af78ea16f33f53914b07a17f0215771ef46e3933db", "src/ohlab/io/config.py": "03e383c7c8a9ba9936cc6dde1bedd2c36ad6ebb06b898a240ca54c29fecd439a", "src/ohlab/io/images.py": "60f6c1a9edf9497ffd9a5c344f3bb42411dbfdfdc27afec0a1b1aa02a3dd0be7", "src/ohlab/metrics.py": "a52d87d754287fa05915a4fc8a120b6a092cc913b059176c0b8d9f16e3805c8e", "src/ohlab/propagation.py": "e994154e6ea1847a2862d3c8994fd1223c66e26d15e9fd984debd6fffdd84af8", "src/ohlab/targets.py": "bdc70953ed59134bab007d3e170bde8f5c37227e7fe486406e552e10d01fb915", "src/ohlab/units.py": "e3b9d6984074c3b66a7dd6d70d597eb44ee91f9807d278de2b0e694e727aac16", "src/ohlab/validation.py": "918a52f2cc85f01bf0ac6c5b47d4ccdf9d35e2d3905c37c86e773924804e2ddd", "tests/_helpers.py": "648486d4626c93a59123dbdec695336320792c4f3b7cab94bd5e20a02fb02aee", "tests/conftest.py": "014e39ecbd1f7cc8c961708f8d0aab0db66534ab59504c5d0995ce6a51ec2e9e", "tests/test_fft_conventions.py": "dc090468b62aaf48ddc84ebacf9479556773403e462f9001e7d67d21dadb437b", "tests/test_field.py": "db4daacfe7c69a2d913b9affd7b7bb729922ea0fe0eba4f43d5267ba3e4c0c2a", "tests/test_gerchberg_saxton.py": "ef27b513cd9841f4e00ae5cd5b9587b3f72fb78bbbeccbe1dcd91a0a80798691", "tests/test_gerchberg_saxton_reference.py": "7d51712c52e5fa52ea1bdc7178f648f2fc262b27b5b946961222bf47bbbb86ac", "tests/test_grid.py": "7d6f80ae507e5cfd8bd112c9a0846357418d20e80caac9b9908aa55929a51f99", "tests/test_helpers.py": "f0f44248036c2ab6f9609fc83c0ff0fb03fb640f60caa413bff34c35059b51c8", "tests/test_images.py": "54ccd953ec92065199a4c4e28520a50c9ac35f7f32b4ec258050d7d2874cf76f", "tests/test_metrics.py": "33db81ded7bcbeb3aa25aad25075026bb68be0acf3ae2f5a1c2f36829a27cca6", "tests/test_packaging.py": "f34bc3c46b0fe17eef08cffd90f76364e5f72555ae745a7c638cc6a1625c1426", "tests/test_plane_wave.py": "66a95d62295ad337e9f83347dc9c653bbcdd8099080a3f1f21290e8ddb86b192", "tests/test_propagation.py": "5abca36098438a5125fd21785ab5c2e2d363c610103b6117e05a36b6ad4c3c16", "tests/test_propagation_analytic.py": "72a166abe31d107871717942958ed7870935cd97137ce5eddc8b0a830cea0bba", "tests/test_run_artifacts.py": "13999e8534f09ffd3e322a5892c141522f571fef8eef2c5050ffa9d3d2c987c7", "tests/test_run_config.py": "aeec0852ef632a3c9c6f02b9d129ee167f03db7956a8660b48ca1356ab9927b4", "tests/test_targets.py": "6b067a71244f3257377f429ff03fd834cca39d9998ac599985f68939c9c8540a", "tests/test_units.py": "049f168fd2ccfbc68e88742000f1110076085ed4871c2c145e9649318c0b1abd", "tests/test_validation.py": "151b099e40314b01d57e55b5af2e225afbccf6b4f7a070987bf4310368d5ec25"}

CASE missing_distance_default: Default a missing required optics.distance_m to 0.0 during RunConfig validation.
COMMAND ["C:\\holographiclab\\.venv\\Scripts\\python.exe", "-B", "-X", "utf8", "C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\negative_controls.py", "--child", "missing_distance_default", "--mode", "baseline", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m5-nc-39ee9876b9da4664b864316051cba3a3-missing_distance_default-baseline"]
STDOUT BEGIN
.                                                                        [100%]
1 passed in 0.43s
M5_NEGATIVE_CONTROL_RESULT {"accepted": true, "after_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "before_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "case": "missing_distance_default", "changed_paths": [], "collection_errors": [], "failures": [], "mode": "baseline", "passed": ["tests/test_run_artifacts.py::test_rehashed_invalid_config_fails_schema_before_solver[missing_distance]"], "pytest_exit": 0, "source_test_file_count": 33}
STDOUT END
STDERR BEGIN
STDERR END
CHILD EXIT 0
COMMAND ["C:\\holographiclab\\.venv\\Scripts\\python.exe", "-B", "-X", "utf8", "C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\negative_controls.py", "--child", "missing_distance_default", "--mode", "mutant", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m5-nc-39ee9876b9da4664b864316051cba3a3-missing_distance_default-mutant"]
STDOUT BEGIN
F                                                                        [100%]
================================== FAILURES ===================================
__ test_rehashed_invalid_config_fails_schema_before_solver[missing_distance] __
tests\test_run_artifacts.py:493: in test_rehashed_invalid_config_fails_schema_before_solver
    artifacts.replay_run_bundle(path, source_revision=SOURCE)
src\ohlab\io\artifacts.py:692: in replay_run_bundle
    replayed = _outputs(_solve(spec, arrays))
                        ^^^^^^^^^^^^^^^^^^^^
src\ohlab\io\artifacts.py:286: in _solve
    return gerchberg_saxton(
tests\test_run_artifacts.py:491: in <lambda>
    monkeypatch.setattr(artifacts, "gerchberg_saxton", lambda **kwargs: pytest.fail("invalid schema reached solver"))
                                                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   Failed: invalid schema reached solver
=========================== short test summary info ===========================
FAILED tests/test_run_artifacts.py::test_rehashed_invalid_config_fails_schema_before_solver[missing_distance]
1 failed in 0.53s
M5_NEGATIVE_CONTROL_RESULT {"accepted": true, "after_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "before_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "case": "missing_distance_default", "changed_paths": [], "collection_errors": [], "failures": [{"assertion_detection": true, "exception_type": "Failed", "nodeid": "tests/test_run_artifacts.py::test_rehashed_invalid_config_fails_schema_before_solver[missing_distance]", "phase": "call"}], "mode": "mutant", "passed": [], "pytest_exit": 1, "source_test_file_count": 33}
STDOUT END
STDERR BEGIN
STDERR END
CHILD EXIT 0

CASE digest_skipped: Disable the artifact SHA-256 comparison while preserving byte-count checks.
COMMAND ["C:\\holographiclab\\.venv\\Scripts\\python.exe", "-B", "-X", "utf8", "C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\negative_controls.py", "--child", "digest_skipped", "--mode", "baseline", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m5-nc-39ee9876b9da4664b864316051cba3a3-digest_skipped-baseline"]
STDOUT BEGIN
.                                                                        [100%]
1 passed in 0.35s
M5_NEGATIVE_CONTROL_RESULT {"accepted": true, "after_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "before_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "case": "digest_skipped", "changed_paths": [], "collection_errors": [], "failures": [], "mode": "baseline", "passed": ["tests/test_run_artifacts.py::test_modified_payload_is_detected_before_any_array_decode_or_solver_call"], "pytest_exit": 0, "source_test_file_count": 33}
STDOUT END
STDERR BEGIN
STDERR END
CHILD EXIT 0
COMMAND ["C:\\holographiclab\\.venv\\Scripts\\python.exe", "-B", "-X", "utf8", "C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\negative_controls.py", "--child", "digest_skipped", "--mode", "mutant", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m5-nc-39ee9876b9da4664b864316051cba3a3-digest_skipped-mutant"]
STDOUT BEGIN
F                                                                        [100%]
================================== FAILURES ===================================
__ test_modified_payload_is_detected_before_any_array_decode_or_solver_call ___
tests\test_run_artifacts.py:373: in test_modified_payload_is_detected_before_any_array_decode_or_solver_call
    function(path)
src\ohlab\io\artifacts.py:622: in verify_run_bundle
    return _validated_contents(_public_path(path))[1]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\ohlab\io\artifacts.py:463: in _validated_contents
    arrays[role] = _load_npy(snapshots[f"{role}.npy"], entries[f"{role}.npy"], role, array_shape,
src\ohlab\io\artifacts.py:318: in _load_npy
    array = np.load(stream, allow_pickle=False, mmap_mode=None, max_header_size=10000)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\test_run_artifacts.py:368: in forbidden
    pytest.fail("corrupted bytes reached numerical decoding or the solver")
E   Failed: corrupted bytes reached numerical decoding or the solver
=========================== short test summary info ===========================
FAILED tests/test_run_artifacts.py::test_modified_payload_is_detected_before_any_array_decode_or_solver_call
1 failed in 0.44s
M5_NEGATIVE_CONTROL_RESULT {"accepted": true, "after_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "before_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "case": "digest_skipped", "changed_paths": [], "collection_errors": [], "failures": [{"assertion_detection": true, "exception_type": "Failed", "nodeid": "tests/test_run_artifacts.py::test_modified_payload_is_detected_before_any_array_decode_or_solver_call", "phase": "call"}], "mode": "mutant", "passed": [], "pytest_exit": 1, "source_test_file_count": 33}
STDOUT END
STDERR BEGIN
STDERR END
CHILD EXIT 0

CASE saved_metric_comparison_ignored: Force saved-data metric comparison checks true, retaining replay-metric comparisons.
COMMAND ["C:\\holographiclab\\.venv\\Scripts\\python.exe", "-B", "-X", "utf8", "C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\negative_controls.py", "--child", "saved_metric_comparison_ignored", "--mode", "baseline", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m5-nc-39ee9876b9da4664b864316051cba3a3-saved_metric_comparison_ignored-baseline"]
STDOUT BEGIN
.                                                                        [100%]
1 passed in 0.25s
M5_NEGATIVE_CONTROL_RESULT {"accepted": true, "after_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "before_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "case": "saved_metric_comparison_ignored", "changed_paths": [], "collection_errors": [], "failures": [], "mode": "baseline", "passed": ["tests/test_run_artifacts.py::test_rehashed_wrong_metric_passes_integrity_but_fails_recomputation"], "pytest_exit": 0, "source_test_file_count": 33}
STDOUT END
STDERR BEGIN
STDERR END
CHILD EXIT 0
COMMAND ["C:\\holographiclab\\.venv\\Scripts\\python.exe", "-B", "-X", "utf8", "C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\negative_controls.py", "--child", "saved_metric_comparison_ignored", "--mode", "mutant", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m5-nc-39ee9876b9da4664b864316051cba3a3-saved_metric_comparison_ignored-mutant"]
STDOUT BEGIN
F                                                                        [100%]
================================== FAILURES ===================================
_____ test_rehashed_wrong_metric_passes_integrity_but_fails_recomputation _____
tests\test_run_artifacts.py:602: in test_rehashed_wrong_metric_passes_integrity_but_fails_recomputation
    assert report.checks["saved_metric:intensity_mse"] is False
E   assert True is False
=========================== short test summary info ===========================
FAILED tests/test_run_artifacts.py::test_rehashed_wrong_metric_passes_integrity_but_fails_recomputation
1 failed in 0.46s
M5_NEGATIVE_CONTROL_RESULT {"accepted": true, "after_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "before_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "case": "saved_metric_comparison_ignored", "changed_paths": [], "collection_errors": [], "failures": [{"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_rehashed_wrong_metric_passes_integrity_but_fails_recomputation", "phase": "call"}], "mode": "mutant", "passed": [], "pytest_exit": 1, "source_test_file_count": 33}
STDOUT END
STDERR BEGIN
STDERR END
CHILD EXIT 0

CASE target_role_loads_source: Decode verified source_amplitude.npy bytes for the target_amplitude role, preserving compatible shape/dtype.
COMMAND ["C:\\holographiclab\\.venv\\Scripts\\python.exe", "-B", "-X", "utf8", "C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\negative_controls.py", "--child", "target_role_loads_source", "--mode", "baseline", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m5-nc-39ee9876b9da4664b864316051cba3a3-target_role_loads_source-baseline"]
STDOUT BEGIN
............                                                             [100%]
12 passed in 0.66s
M5_NEGATIVE_CONTROL_RESULT {"accepted": true, "after_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "before_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "case": "target_role_loads_source", "changed_paths": [], "collection_errors": [], "failures": [], "mode": "baseline", "passed": ["tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-0-seed]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-0-explicit_phase]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-5-seed]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-5-explicit_phase]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-0-seed]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-0-explicit_phase]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-5-seed]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-5-explicit_phase]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-0-seed]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-0-explicit_phase]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-5-seed]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-5-explicit_phase]"], "pytest_exit": 0, "source_test_file_count": 33}
STDOUT END
STDERR BEGIN
STDERR END
CHILD EXIT 0
COMMAND ["C:\\holographiclab\\.venv\\Scripts\\python.exe", "-B", "-X", "utf8", "C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\negative_controls.py", "--child", "target_role_loads_source", "--mode", "mutant", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m5-nc-39ee9876b9da4664b864316051cba3a3-target_role_loads_source-mutant"]
STDOUT BEGIN
FFFFFFFFFFFF                                                             [100%]
================================== FAILURES ===================================
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-0-seed] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-0-explicit_phase] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-5-seed] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-5-explicit_phase] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-0-seed] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-0-explicit_phase] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-5-seed] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-5-explicit_phase] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-0-seed] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-0-explicit_phase] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-5-seed] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-5-explicit_phase] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
=========================== short test summary info ===========================
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-0-seed]
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-0-explicit_phase]
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-5-seed]
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-5-explicit_phase]
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-0-seed]
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-0-explicit_phase]
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-5-seed]
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-5-explicit_phase]
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-0-seed]
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-0-explicit_phase]
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-5-seed]
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-5-explicit_phase]
12 failed in 1.28s
M5_NEGATIVE_CONTROL_RESULT {"accepted": true, "after_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "before_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "case": "target_role_loads_source", "changed_paths": [], "collection_errors": [], "failures": [{"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-0-seed]", "phase": "call"}, {"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-0-explicit_phase]", "phase": "call"}, {"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-5-seed]", "phase": "call"}, {"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-5-explicit_phase]", "phase": "call"}, {"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-0-seed]", "phase": "call"}, {"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-0-explicit_phase]", "phase": "call"}, {"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-5-seed]", "phase": "call"}, {"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-5-explicit_phase]", "phase": "call"}, {"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-0-seed]", "phase": "call"}, {"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-0-explicit_phase]", "phase": "call"}, {"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-5-seed]", "phase": "call"}, {"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-5-explicit_phase]", "phase": "call"}], "mode": "mutant", "passed": [], "pytest_exit": 1, "source_test_file_count": 33}
STDOUT END
STDERR BEGIN
STDERR END
CHILD EXIT 0

CASE missing_psnr_range_default: Default missing required intensity_psnr.data_range to 1.0 during RunConfig validation.
COMMAND ["C:\\holographiclab\\.venv\\Scripts\\python.exe", "-B", "-X", "utf8", "C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\negative_controls.py", "--child", "missing_psnr_range_default", "--mode", "baseline", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m5-nc-39ee9876b9da4664b864316051cba3a3-missing_psnr_range_default-baseline"]
STDOUT BEGIN
.                                                                        [100%]
1 passed in 0.31s
M5_NEGATIVE_CONTROL_RESULT {"accepted": true, "after_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "before_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "case": "missing_psnr_range_default", "changed_paths": [], "collection_errors": [], "failures": [], "mode": "baseline", "passed": ["tests/test_run_artifacts.py::test_rehashed_invalid_config_fails_schema_before_solver[missing_psnr_range]"], "pytest_exit": 0, "source_test_file_count": 33}
STDOUT END
STDERR BEGIN
STDERR END
CHILD EXIT 0
COMMAND ["C:\\holographiclab\\.venv\\Scripts\\python.exe", "-B", "-X", "utf8", "C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\negative_controls.py", "--child", "missing_psnr_range_default", "--mode", "mutant", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m5-nc-39ee9876b9da4664b864316051cba3a3-missing_psnr_range_default-mutant"]
STDOUT BEGIN
F                                                                        [100%]
================================== FAILURES ===================================
_ test_rehashed_invalid_config_fails_schema_before_solver[missing_psnr_range] _
tests\test_run_artifacts.py:493: in test_rehashed_invalid_config_fails_schema_before_solver
    artifacts.replay_run_bundle(path, source_revision=SOURCE)
src\ohlab\io\artifacts.py:692: in replay_run_bundle
    replayed = _outputs(_solve(spec, arrays))
                        ^^^^^^^^^^^^^^^^^^^^
src\ohlab\io\artifacts.py:286: in _solve
    return gerchberg_saxton(
tests\test_run_artifacts.py:491: in <lambda>
    monkeypatch.setattr(artifacts, "gerchberg_saxton", lambda **kwargs: pytest.fail("invalid schema reached solver"))
                                                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   Failed: invalid schema reached solver
=========================== short test summary info ===========================
FAILED tests/test_run_artifacts.py::test_rehashed_invalid_config_fails_schema_before_solver[missing_psnr_range]
1 failed in 0.45s
M5_NEGATIVE_CONTROL_RESULT {"accepted": true, "after_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "before_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "case": "missing_psnr_range_default", "changed_paths": [], "collection_errors": [], "failures": [{"assertion_detection": true, "exception_type": "Failed", "nodeid": "tests/test_run_artifacts.py::test_rehashed_invalid_config_fails_schema_before_solver[missing_psnr_range]", "phase": "call"}], "mode": "mutant", "passed": [], "pytest_exit": 1, "source_test_file_count": 33}
STDOUT END
STDERR BEGIN
STDERR END
CHILD EXIT 0

CASE outside_read_before_path_validation: Attempt to read an unknown manifest path before the existing allowlist rejection; instrumentation must stop the outside read.
COMMAND ["C:\\holographiclab\\.venv\\Scripts\\python.exe", "-B", "-X", "utf8", "C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\negative_controls.py", "--child", "outside_read_before_path_validation", "--mode", "baseline", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m5-nc-39ee9876b9da4664b864316051cba3a3-outside_read_before_path_validation-baseline"]
STDOUT BEGIN
.                                                                        [100%]
1 passed in 0.33s
M5_NEGATIVE_CONTROL_RESULT {"accepted": true, "after_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "before_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "case": "outside_read_before_path_validation", "changed_paths": [], "collection_errors": [], "failures": [], "mode": "baseline", "passed": ["tests/test_run_artifacts.py::test_unsafe_manifest_paths_fail_before_instrumented_outside_reads[../outside.npy]"], "pytest_exit": 0, "source_test_file_count": 33}
STDOUT END
STDERR BEGIN
STDERR END
CHILD EXIT 0
COMMAND ["C:\\holographiclab\\.venv\\Scripts\\python.exe", "-B", "-X", "utf8", "C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\negative_controls.py", "--child", "outside_read_before_path_validation", "--mode", "mutant", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m5-nc-39ee9876b9da4664b864316051cba3a3-outside_read_before_path_validation-mutant"]
STDOUT BEGIN
F                                                                        [100%]
================================== FAILURES ===================================
_ test_unsafe_manifest_paths_fail_before_instrumented_outside_reads[../outside.npy] _
tests\test_run_artifacts.py:453: in test_unsafe_manifest_paths_fail_before_instrumented_outside_reads
    artifacts.verify_run_bundle(path)
src\ohlab\io\artifacts.py:622: in verify_run_bundle
    return _validated_contents(_public_path(path))[1]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\ohlab\io\artifacts.py:450: in _validated_contents
    snapshots, entries = _verified_snapshots(path)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^
<m5-in-memory-negative-control:_verified_snapshots>:23: in _verified_snapshots
    ???
C:\Users\jimli\AppData\Local\Programs\Python\Python311\Lib\pathlib.py:1050: in read_bytes
    with self.open(mode='rb') as f:
         ^^^^^^^^^^^^^^^^^^^^
C:\Users\jimli\AppData\Local\Programs\Python\Python311\Lib\pathlib.py:1044: in open
    return io.open(self, mode, buffering, encoding, errors, newline)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\test_run_artifacts.py:447: in guarded_io_open
    pytest.fail(f"attempted outside io.open: {candidate}")
E   Failed: attempted outside io.open: C:\holographiclab\.pytest_cache\m5-nc-39ee9876b9da4664b864316051cba3a3-outside_read_before_path_validation-mutant\test_unsafe_manifest_paths_fai0\run\..\outside.npy
=========================== short test summary info ===========================
FAILED tests/test_run_artifacts.py::test_unsafe_manifest_paths_fail_before_instrumented_outside_reads[../outside.npy]
1 failed in 0.47s
M5_NEGATIVE_CONTROL_RESULT {"accepted": true, "after_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "before_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "case": "outside_read_before_path_validation", "changed_paths": [], "collection_errors": [], "failures": [{"assertion_detection": true, "exception_type": "Failed", "nodeid": "tests/test_run_artifacts.py::test_unsafe_manifest_paths_fail_before_instrumented_outside_reads[../outside.npy]", "phase": "call"}], "mode": "mutant", "passed": [], "pytest_exit": 1, "source_test_file_count": 33}
STDOUT END
STDERR BEGIN
STDERR END
CHILD EXIT 0

CASE replay_seed_incremented: Forward seed+1 only during replay solves; capture and explicit-phase solves remain unchanged.
COMMAND ["C:\\holographiclab\\.venv\\Scripts\\python.exe", "-B", "-X", "utf8", "C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\negative_controls.py", "--child", "replay_seed_incremented", "--mode", "baseline", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m5-nc-39ee9876b9da4664b864316051cba3a3-replay_seed_incremented-baseline"]
STDOUT BEGIN
............                                                             [100%]
12 passed in 0.76s
M5_NEGATIVE_CONTROL_RESULT {"accepted": true, "after_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "before_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "case": "replay_seed_incremented", "changed_paths": [], "collection_errors": [], "failures": [], "mode": "baseline", "passed": ["tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-0-seed]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-0-explicit_phase]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-5-seed]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-5-explicit_phase]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-0-seed]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-0-explicit_phase]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-5-seed]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-5-explicit_phase]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-0-seed]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-0-explicit_phase]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-5-seed]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-5-explicit_phase]"], "pytest_exit": 0, "source_test_file_count": 33}
STDOUT END
STDERR BEGIN
STDERR END
CHILD EXIT 0
COMMAND ["C:\\holographiclab\\.venv\\Scripts\\python.exe", "-B", "-X", "utf8", "C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\negative_controls.py", "--child", "replay_seed_incremented", "--mode", "mutant", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m5-nc-39ee9876b9da4664b864316051cba3a3-replay_seed_incremented-mutant"]
STDOUT BEGIN
F.F.F.F.F.F.                                                             [100%]
================================== FAILURES ===================================
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-0-seed] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-5-seed] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-0-seed] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-5-seed] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-0-seed] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
_ test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-5-seed] _
tests\test_run_artifacts.py:162: in test_twelve_case_same_environment_replay_is_literal_and_individually_reported
    assert report.comparison == "passed"
E   AssertionError: assert 'failed' == 'passed'
E     
E     - passed
E     + failed
=========================== short test summary info ===========================
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-0-seed]
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-5-seed]
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-0-seed]
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-5-seed]
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-0-seed]
FAILED tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-5-seed]
6 failed, 6 passed in 1.14s
M5_NEGATIVE_CONTROL_RESULT {"accepted": true, "after_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "before_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "case": "replay_seed_incremented", "changed_paths": [], "collection_errors": [], "failures": [{"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-0-seed]", "phase": "call"}, {"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-5-seed]", "phase": "call"}, {"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-0-seed]", "phase": "call"}, {"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-5-seed]", "phase": "call"}, {"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-0-seed]", "phase": "call"}, {"assertion_detection": true, "exception_type": "AssertionError", "nodeid": "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-5-seed]", "phase": "call"}], "mode": "mutant", "passed": ["tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-0-explicit_phase]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[-0.0002-5-explicit_phase]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-0-explicit_phase]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0-5-explicit_phase]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-0-explicit_phase]", "tests/test_run_artifacts.py::test_twelve_case_same_environment_replay_is_literal_and_individually_reported[0.0002-5-explicit_phase]"], "pytest_exit": 1, "source_test_file_count": 33}
STDOUT END
STDERR BEGIN
STDERR END
CHILD EXIT 0

FINAL {"accepted": true, "after_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "before_inventory_sha256": "6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296", "changed_paths": [], "completed_children": 14, "expected_children": 14, "mutant_assertion_failures": 23, "mutant_passing_cases": 6, "source_test_file_count": 33}
```

## Appendix E — Discovery failures and the bounded response

These earlier candidate runs failed. Their outputs are preserved rather than
substituted with the final passing suite. The first capture was recovered
from displayed tool output, including localized mojibake; it is labeled
as such rather than presented as an original raw stdout byte capture.
The repeated focused run used native Windows CP950 output, decoded
strictly with CP950 here; later commands explicitly use UTF-8.
Subsequent captured files retain original output text. Tool console
wrappers and sandbox escalation notices are not pytest output.

### First expanded artifact run; failed

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --basetemp .pytest_cache/m5-artifacts-agent-final-2b540c87 tests/test_run_artifacts.py

Working directory: C:\holographiclab
Exit code: 1
Provenance: exact decoded process text returned by exec_command and its write_stdin completion, concatenated at the chunk boundary. The localized Windows error characters are retained as the tool displayed them; the original undecoded stdout/stderr bytes were not separately captured for this development run.
```

```text
........................................................................ [ 54%]
..............F......................................s.....              [100%]
================================== FAILURES ===================================
______ test_informational_environment_paths_do_not_control_qualification ______

tmp_path = WindowsPath('C:/holographiclab/.pytest_cache/m5-artifacts-agent-final-2b540c87/test_informational_environment0')

    def test_informational_environment_paths_do_not_control_qualification(tmp_path):
        path = tmp_path / "run"
>       _save(path)

tests\test_run_artifacts.py:670: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
tests\test_run_artifacts.py:96: in _save
    return artifacts.run_and_save_bundle(path, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\ohlab\io\artifacts.py:570: in run_and_save_bundle
    _publish(stage, destination)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

stage = WindowsPath('C:/holographiclab/.pytest_cache/m5-artifacts-agent-final-2b540c87/test_informational_environment0/.ohlab-partial-qqav76d8')
destination = WindowsPath('C:/holographiclab/.pytest_cache/m5-artifacts-agent-final-2b540c87/test_informational_environment0/run')

    def _publish(stage: Path, destination: Path) -> None:
>       os.rename(stage, destination)
E       PermissionError: [WinError 5] �s���Q�ڡC: 'C:\\holographiclab\\.pytest_cache\\m5-artifacts-agent-final-2b540c87\\test_informational_environment0\\.ohlab-partial-qqav76d8' -> 'C:\\holographiclab\\.pytest_cache\\m5-artifacts-agent-final-2b540c87\\test_informational_environment0\\run'

src\ohlab\io\artifacts.py:480: PermissionError
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:935: this Windows account lacks symlink privilege; junction is tested separately
FAILED tests/test_run_artifacts.py::test_informational_environment_paths_do_not_control_qualification
1 failed, 129 passed, 1 skipped in 7.39s
```

### Repeated focused artifact run; failed

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --basetemp .pytest_cache/m5-artifacts-agent-captured-9a863c0d tests/test_run_artifacts.py
```

```text
.......................................................................F [ 54%]
.....................................................s.....              [100%]
================================== FAILURES ===================================
_ test_rehashed_malformed_npy_is_rejected_by_narrow_format_contract[wrong_shape] _

tmp_path = WindowsPath('C:/holographiclab/.pytest_cache/m5-artifacts-agent-captured-9a863c0d/test_rehashed_malformed_npy_is5')
malformation = 'wrong_shape'

    @pytest.mark.parametrize("malformation", ["object", "structured", "npz", "truncated", "trailing", "wrong_shape", "wrong_dtype", "non_native", "fortran", "version2", "oversized_header"])
    def test_rehashed_malformed_npy_is_rejected_by_narrow_format_contract(tmp_path, malformation):
        path = tmp_path / "run"
>       _save(path)

tests\test_run_artifacts.py:542: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
tests\test_run_artifacts.py:96: in _save
    return artifacts.run_and_save_bundle(path, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\ohlab\io\artifacts.py:570: in run_and_save_bundle
    _publish(stage, destination)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

stage = WindowsPath('C:/holographiclab/.pytest_cache/m5-artifacts-agent-captured-9a863c0d/test_rehashed_malformed_npy_is5/.ohlab-partial-r4tlkxzc')
destination = WindowsPath('C:/holographiclab/.pytest_cache/m5-artifacts-agent-captured-9a863c0d/test_rehashed_malformed_npy_is5/run')

    def _publish(stage: Path, destination: Path) -> None:
>       os.rename(stage, destination)
E       PermissionError: [WinError 5] 存取被拒。: 'C:\\holographiclab\\.pytest_cache\\m5-artifacts-agent-captured-9a863c0d\\test_rehashed_malformed_npy_is5\\.ohlab-partial-r4tlkxzc' -> 'C:\\holographiclab\\.pytest_cache\\m5-artifacts-agent-captured-9a863c0d\\test_rehashed_malformed_npy_is5\\run'

src\ohlab\io\artifacts.py:480: PermissionError
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:935: this Windows account lacks symlink privilege; junction is tested separately
FAILED tests/test_run_artifacts.py::test_rehashed_malformed_npy_is_rejected_by_narrow_format_contract[wrong_shape]
1 failed, 129 passed, 1 skipped in 6.82s
```

### Full candidate suite before bounded retry; failed

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 -m pytest -q -p no:cacheprovider --basetemp runs/m5-implementation-evidence-20260922/pytest-final-a
```

```text
........................................................................ [  5%]
........................................................................ [ 11%]
........................................................................ [ 16%]
........................................................................ [ 22%]
........................................................................ [ 28%]
........................................................................ [ 33%]
........................................................................ [ 39%]
........................................................................ [ 44%]
........................................................................ [ 50%]
........................................................................ [ 56%]
........................................................................ [ 61%]
....................F................................................... [ 67%]
.........................................................s.............. [ 72%]
........................................................................ [ 78%]
........................................................................ [ 84%]
........................................................................ [ 89%]
........................................................................ [ 95%]
...........................................................              [100%]
================================== FAILURES ===================================
_ test_input_capture_preserves_bits_and_does_not_mutate_or_share_layouts[strided] _

tmp_path = WindowsPath('C:/holographiclab/runs/m5-implementation-evidence-20260922/pytest-final-a/test_input_capture_preserves_b2')
layout = 'strided'

    @pytest.mark.parametrize("layout", ["c", "fortran", "strided", "readonly"])
    def test_input_capture_preserves_bits_and_does_not_mutate_or_share_layouts(tmp_path, layout):
        target, source, initial, signal, cv = _inputs()
        target[0, 0] = -0.0
        initial[0, 0] = -0.0
        arrays = [target, source, initial, signal, cv]
        if layout == "fortran":
            arrays = [np.asfortranarray(array) for array in arrays]
        elif layout == "strided":
            views = []
            for array in arrays:
                backing = np.zeros((6, 10), dtype=array.dtype)
                backing[::2, ::2] = array
                views.append(backing[::2, ::2])
            arrays = views
        elif layout == "readonly":
            for array in arrays:
                array.setflags(write=False)
        before = [_snapshot(array) for array in arrays]
        target, source, initial, signal, cv = arrays
>       bundle = artifacts.run_and_save_bundle(tmp_path / "run", config=RunConfig(_settings("explicit_phase")), target_intensity=target, source_amplitude=source, initial_phase=initial, signal_mask=signal, cv_mask=cv, source_revision=SOURCE)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests\test_run_artifacts.py:250: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
src\ohlab\io\artifacts.py:570: in run_and_save_bundle
    _publish(stage, destination)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

stage = WindowsPath('C:/holographiclab/runs/m5-implementation-evidence-20260922/pytest-final-a/test_input_capture_preserves_b2/.ohlab-partial-9os7uv39')
destination = WindowsPath('C:/holographiclab/runs/m5-implementation-evidence-20260922/pytest-final-a/test_input_capture_preserves_b2/run')

    def _publish(stage: Path, destination: Path) -> None:
>       os.rename(stage, destination)
E       PermissionError: [WinError 5] 存取被拒。: 'C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\pytest-final-a\\test_input_capture_preserves_b2\\.ohlab-partial-9os7uv39' -> 'C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\pytest-final-a\\test_input_capture_preserves_b2\\run'

src\ohlab\io\artifacts.py:480: PermissionError
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:935: this Windows account lacks symlink privilege; junction is tested separately
FAILED tests/test_run_artifacts.py::test_input_capture_preserves_bits_and_does_not_mutate_or_share_layouts[strided]
1 failed, 1281 passed, 1 skipped in 15.60s
```

### Full candidate suite outside sandbox before bounded retry; failed

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest -q -p no:cacheprovider --basetemp runs/m5-implementation-evidence-20260922/pytest-unrestricted-a
```

```text
........................................................................ [  5%]
........................................................................ [ 11%]
........................................................................ [ 16%]
........................................................................ [ 22%]
........................................................................ [ 28%]
........................................................................ [ 33%]
........................................................................ [ 39%]
........................................................................ [ 44%]
........................................................................ [ 50%]
........................................................................ [ 56%]
........................................................................ [ 61%]
........................................................................ [ 67%]
..............F..........................................s.............. [ 72%]
........................................................................ [ 78%]
........................................................................ [ 84%]
........................................................................ [ 89%]
........................................................................ [ 95%]
...........................................................              [100%]
================================== FAILURES ===================================
_ test_unqualified_replay_does_not_run_solver_by_default[different_revision] __

tmp_path = WindowsPath('C:/holographiclab/runs/m5-implementation-evidence-20260922/pytest-unrestricted-a/test_unqualified_replay_does_n1')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x00000178FF4AE650>
reason = 'different_revision'

    @pytest.mark.parametrize("reason", ["missing", "different_revision", "dirty"])
    def test_unqualified_replay_does_not_run_solver_by_default(tmp_path, monkeypatch, reason):
        path = tmp_path / "run"
>       _save(path)

tests\test_run_artifacts.py:626: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
tests\test_run_artifacts.py:96: in _save
    return artifacts.run_and_save_bundle(path, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\ohlab\io\artifacts.py:570: in run_and_save_bundle
    _publish(stage, destination)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

stage = WindowsPath('C:/holographiclab/runs/m5-implementation-evidence-20260922/pytest-unrestricted-a/test_unqualified_replay_does_n1/.ohlab-partial-zvz4639o')
destination = WindowsPath('C:/holographiclab/runs/m5-implementation-evidence-20260922/pytest-unrestricted-a/test_unqualified_replay_does_n1/run')

    def _publish(stage: Path, destination: Path) -> None:
>       os.rename(stage, destination)
E       PermissionError: [WinError 5] 存取被拒。: 'C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\pytest-unrestricted-a\\test_unqualified_replay_does_n1\\.ohlab-partial-zvz4639o' -> 'C:\\holographiclab\\runs\\m5-implementation-evidence-20260922\\pytest-unrestricted-a\\test_unqualified_replay_does_n1\\run'

src\ohlab\io\artifacts.py:480: PermissionError
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:935: this Windows account lacks symlink privilege; junction is tested separately
FAILED tests/test_run_artifacts.py::test_unqualified_replay_does_not_run_solver_by_default[different_revision]
1 failed, 1281 passed, 1 skipped in 15.80s
```

### Independent 100-save probe, before retry refinement

This probe did not reproduce the denial and cannot establish its cause.
It never retries a failed destination and only creates owned fixtures.
This output predates the publication refinement. Rerunning the same
probe on final source calls the current `_publish`, including its
bounded internal retry; it does not recreate the historical version.

```python
"""Bounded diagnostic of ordinary Windows publication; no automatic retries."""
from pathlib import Path
import ctypes
from ctypes import wintypes
import json
import runpy
import sys
from uuid import uuid4

from ohlab.io import artifacts

root = Path(__file__).resolve().parents[2]
fixtures = runpy.run_path(str(root / 'tests' / 'test_run_artifacts.py'))
owned = root / 'runs' / 'm5-implementation-evidence-20260922' / ('publication-' + uuid4().hex)
owned.mkdir()
original_publish = artifacts._publish
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                              wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
kernel.CreateFileW.restype = wintypes.HANDLE
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
kernel.CloseHandle.restype = wintypes.BOOL

def probe_delete_access(path):
    assert owned.resolve() in path.resolve().parents
    handle = kernel.CreateFileW(str(path), 0x00010000, 7, None, 3, 0x02000000, None)
    if handle == ctypes.c_void_p(-1).value:
        return ctypes.get_last_error()
    kernel.CloseHandle(handle)
    return 0

def observed_publish(stage, destination):
    try:
        original_publish(stage, destination)
    except PermissionError as exc:
        print(json.dumps({'event':'rename_denied','winerror':exc.winerror,
                          'stage':str(stage),'destination_exists':destination.exists(),
                          'delete_access_errors':{path.name:probe_delete_access(path)
                                                  for path in [stage,*stage.iterdir()]}},sort_keys=True))
        raise

artifacts._publish = observed_publish
failures = []
for index in range(100):
    destination = owned / ('run-' + str(index))
    try:
        fixtures['_save'](destination)
    except PermissionError as exc:
        failures.append({'index':index,'winerror':exc.winerror,'notes':getattr(exc,'__notes__',[])})
print(json.dumps({'attempted_independent_saves':100,'successes':100-len(failures),
                  'failures':failures,'retry_of_failed_destination':False,
                  'remaining_partials':[p.name for p in owned.glob('.ohlab-partial-*')]},sort_keys=True))
```

### Probe command and exact output; exit 0

```powershell
.\.venv\Scripts\python.exe -B -X utf8 runs\m5-implementation-evidence-20260922\publication_probe.py
```

```text
{"attempted_independent_saves": 100, "failures": [], "remaining_partials": [], "retry_of_failed_destination": false, "successes": 100}
```

### Focused retry-safety validation

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --basetemp .pytest_cache/m5-artifact-retry-focused-final-84fe3ab1 tests/test_run_artifacts.py -k windows_rename_retry
```

```text
........                                                                 [100%]
8 passed, 131 deselected in 0.52s
```

This focused tool output is transcribed exactly. A subsequent complete suite
passed 1290 cases with one skip in 17.37s before final review identified
the foreign-endian report-status issue. That earlier pass is preserved
in ignored `accepted-final-pytest-output.txt`; it is superseded by
Appendix A for final source verification.

Final review found diagnostic foreign-endian loading could skip numerical
execution yet report `failed`. It now reports `not_run`, retains the
unqualified state and failed native-byte-order gate, and does not cast.
A valid fully rehashed foreign-endian bundle and a solver spy cover this
case. The final controls and full suite followed that correction.

## Appendix F — Resumed publication verification, 2026-09-29

The earlier publication attempt stopped when automatic approval review could
not stage the final evidence clarification because of an account usage limit.
No commit or push was made then. The user requested continuation on September
29. This section supplements the original September 22–23 evidence; it does
not replace the historical timings or claim those runs happened today.

On resumption, branch `main`, HEAD, upstream and live remote still matched
accepted baseline `5b8e278d2f105552d8ef7d951aaa5161c01c801a`, ahead/behind 0/0.
The 33 source/test files retained aggregate byte-inventory SHA-256
`6db5bda83f73097b881ebcbfb19d2b68ca60ca370efe923af8edd624fa90f296`.
All 97 protected pre-existing files remained unchanged. The only unstaged
change was the reviewed historical-probe reproduction clarification.

Current required runtime fields matched those printed in Appendix B. The
fresh complete suite below exited 0. No source/test change or dependency
installation preceded this rerun. The single skip remains the unavailable
Windows file-symlink privilege; the real junction test passed.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest -q -p no:cacheprovider --basetemp runs/m5-implementation-evidence-20260922/pytest-resume-20260929-a
```

```text
........................................................................ [  5%]
........................................................................ [ 11%]
........................................................................ [ 16%]
........................................................................ [ 22%]
........................................................................ [ 27%]
........................................................................ [ 33%]
........................................................................ [ 39%]
........................................................................ [ 44%]
........................................................................ [ 50%]
........................................................................ [ 55%]
........................................................................ [ 61%]
........................................................................ [ 66%]
..................................................................s..... [ 72%]
........................................................................ [ 78%]
........................................................................ [ 83%]
........................................................................ [ 89%]
........................................................................ [ 94%]
....................................................................     [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
1291 passed, 1 skipped in 16.11s
```

Review preserved 22 trailing-whitespace lines inside exact test transcripts;
`git diff --cached --check` reports those lines. There are no other whitespace
findings. Stripping them would alter the requested unedited evidence.

The approved next steps remain one M5 commit, a fresh clean-commit qualified
example before push, normal publication to origin/main, and agreement among
local HEAD, live remote main and the GitHub API. Their actual results belong
in ignored captures and the completion report, not an inferred precommit SHA.
M6 remains unstarted.
