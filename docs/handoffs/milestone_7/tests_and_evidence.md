# Milestone 7 — Tests and reproducible evidence

Recorded **2026-09-30** (Asia/Taipei), from accepted M6 revision
`cc93c949da23de4a6f98acc0c4954c3c2d7f6849`. Root engineering verified clean,
synchronized `main`, expected upstream and live remote before edits. No
dependencies, server configuration or persistent environment settings are
changed by M7. The existing interpreter remains
`C:\holographiclab\.venv\Scripts\python.exe`.

**Precommit acceptance is complete within the recorded scope.** Baseline,
model/design-I/O and controller tests, installed AppTest, retained M6
compatibility, six detecting negative controls, the asymmetric example,
boundary probe, final full suite and required real-browser interactions have
completed below. The clean-postcommit UI generation/strict replay gate remains
pending; no published M7 revision or successful publication is claimed here.

Raw captures live under ignored `runs/m7_acceptance_20260930/`. Essential
results and reproduction procedures are embedded here. Captured output is retained as decoded text, with Markdown LF
line endings distinguished from the original Windows byte representation.

## Baseline — exit 0

Exact command:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest -q -p no:cacheprovider --basetemp=runs/m7_acceptance_20260930/pytest_baseline
```

Exact `baseline.txt` output:

```text
........................................................................ [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
........................................................................ [ 20%]
........................................................................ [ 25%]
........................................................................ [ 30%]
........................................................................ [ 36%]
........................................................................ [ 41%]
........................................................................ [ 46%]
........................................................................ [ 51%]
........................................................................ [ 56%]
........................................................................ [ 61%]
..................................................................s..... [ 67%]
........................................................................ [ 72%]
........................................................................ [ 77%]
........................................................................ [ 82%]
........................................................................ [ 87%]
........................................................................ [ 92%]
........................................................................ [ 97%]
.............................                                            [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
1396 passed, 1 skipped in 79.07s (0:01:19)
```

The 1397 baseline cases comprise 1396 passes and the existing Windows
file-symlink privilege skip. The separate real-junction check does not replace
that skipped case. Previous M6 timings remain historical measurements.

## Acceptance layers

| Layer | Status | Required evidence |
|---|---|---|
| Pure model and design I/O | 117 passed in 0.31s | Strict schemas, independent membership/edge cases, reversal, overwrite, bits/ownership, JSON, safe publication and real M5 array/replay integration |
| Existing M6 compatibility | 105 passed in 33.36s | Existing controller, AppTest and architecture tests unchanged; separate initial path-selection error retained below |
| Real controller/API integration + architecture | 38 passed in 1.67s, then 1 added focused case passed in 0.41s | Final suite contains 28 controller and 11 architecture cases; timing captures are separate runs |
| Installed Streamlit AppTest | 18 passed in 66.23s | Selection versus edit, preview-only reruns, imports/order/modes, stale identity, explicit actions and diagnostic reset |
| Actual loopback browser | Passed within the finite recorded cases | Editing/export/reimport, same-name changed-content import, invalid-import recovery, generation, real rapid/busy receipt, stale identity, association failure/recovery, reload/reopen and strict/diagnostic replay |
| Six negative controls | Six faults detected by nine intended assertion failures | Four mixed-parity transpose cases and one each for five other faults; all 49 source/test Python hashes unchanged |
| Asymmetric standalone example | Passed, captured below | All three shapes, overlap/fractional values, exact design/raster/target round trip; actual metrics and explicit dirty diagnostic replay |
| Final full suite | 1570 passed, 1 skipped in 111.67s | 1397 retained baseline cases + 174 new M7 cases; original file-symlink privilege skip retained |
| Protected scope | Passed | Exactly 24 approved paths; 125 protected baseline files and 53 installed distributions unchanged |
| Clean-postcommit UI gate | Deferred | Fresh clean Designer run, exact target comparison, strict qualified replay, independence from external design storage |

## Model, design I/O and existing M6 compatibility

The model/I/O run completed with exit 0. It includes strict nested validation,
immutable ownership, output dtype/layout, exact fractional values and signed
zero; hand masks and independent `Fraction` references; segment reversal and
required-arithmetic failure/error-state restoration; strict bounded JSON;
exclusive destinations, injected fsync/rename/write failures, resource closure,
collision refusal and cleanup diagnostics. A real M5 round trip preserves the
fractional target and remains replayable when its external design is absent.
These are tested cases, not an exhaustive filesystem or geometry guarantee.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest -q tests/test_target_design.py tests/test_design_io.py -p no:cacheprovider --basetemp runs/m7_acceptance_20260930/pytest_model_io_01
```

```text
........................................................................ [ 61%]
.............................................                            [100%]
117 passed in 0.31s
```

The first M6 compatibility command mistakenly named nonexistent files. It ran
no tests and is not counted as coverage or a passing check:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/test_workbench.py tests/test_streamlit_app.py tests/test_workbench_presentation.py -q -p no:cacheprovider --basetemp=runs/m7_acceptance_20260930/pytest_m6_compatibility
```

Exact `m6_compatibility.txt`:

```text

no tests ran in 0.00s
ERROR: file or directory not found: tests/test_workbench.py

```

The corrected command selected the three existing M6 test files, without
editing them, and completed with exit 0:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/test_workbench_controller.py tests/test_workbench_streamlit.py tests/test_workbench_architecture.py -q -p no:cacheprovider --basetemp=runs/m7_acceptance_20260930/pytest_m6_compatibility_02
```

Exact `m6_compatibility_02.txt`:

```text
........................................................................ [ 68%]
.................................                                        [100%]
105 passed in 33.36s
```

## Geometry, bits and independent references

The independently hand-enumerated disk is centered at `(0,0)`, radius 2 on a
5 × 7 canvas (`x=-3..3`, `y=-2..2`), with intensity 0.3 and zero background:

```text
0001000
0011100
0111110
0011100
0001000
```

Tests compare the resulting shape, dtype and C-order element bytes exactly.
Additional hand masks cover rectangular mixed parity and orientation;
`np.nextafter` probes each side of selected inclusive boundaries. A width-2
centered rectangle explicitly covers three x centers. Round-cap and coincident
segment fixtures are independently enumerated. Exact rational membership
references use `fractions.Fraction` for safely separated represented fixtures,
including ten additional segment placements/widths. Neither the rational nor
hand-mask reference calls the production membership helper/rasterizer.

The binary64 reversal case is a different, deliberately boundary-sensitive
probe. On CPython 3.11.9 and NumPy 2.4.6, ordinary scalar projection for
`A=(-1.3,-0.2), B=(2.7,1.3), P=(0,0)` gave adjacent represented squared distances
`0.07246575342465754` and `0.07246575342465755`. The represented width
`0.5383892771022006` produces a threshold equal to the first. Production's
internal lexicographic ordering gives origin intensity `0.3` and identical
C-order raster bytes for both stored endpoint orientations; the two stored
`x0_px` fields remain `-1.3` and `2.7` respectively. No epsilon is introduced.
This establishes the reported environment/fixture, not universal boundary bits.

Reproduction command (save the exact embedded probe at the shown ignored path):

```powershell
.\.venv\Scripts\python.exe -B -X utf8 runs/m7_acceptance_20260930/boundary_probe.py
```

Exact probe code:

```python
import sys
import numpy as np
from ohlab.target_design import TargetDesign2D, rasterize_target_design

A = (-1.3, -0.2)
B = (2.7, 1.3)

def distance(a, b):
    ax, ay = map(np.float64, a)
    bx, by = map(np.float64, b)
    dx, dy = bx - ax, by - ay
    t = ((0.0 - ax) * dx + (0.0 - ay) * dy) / (dx * dx + dy * dy)
    t = min(1.0, max(0.0, t))
    return (0.0 - (ax + t * dx))**2 + (0.0 - (ay + t * dy))**2

def design(a, b, width):
    return TargetDesign2D({
        "schema_version": 1,
        "rasterizer_version": "center_sample_overwrite_v1",
        "coordinate_system": "centered_pixels_y_down_v1",
        "canvas": {"ny": 5, "nx": 7},
        "background_intensity": 0.0,
        "objects": [{"id": "1" * 32, "type": "segment", "intensity": 0.3,
                     "parameters": {"x0_px": a[0], "y0_px": a[1], "x1_px": b[0],
                                    "y1_px": b[1], "width_px": width}}],
    })

f, r = distance(A, B), distance(B, A)
w = float(2 * np.sqrt(f))
threshold = (np.float64(w) / 2.0)**2
print("Python", sys.version.split()[0], "NumPy", np.__version__)
for name, value in (("forward", f), ("reverse", r), ("width", w), ("threshold", threshold)):
    print(name, repr(float(value)), float(value).hex())
print("straddles", bool(f <= threshold < r))
first, second = design(A, B, w), design(B, A, w)
raster_a, raster_b = rasterize_target_design(first), rasterize_target_design(second)
print("production_forward_origin", repr(float(raster_a[2, 3])))
print("production_reverse_origin", repr(float(raster_b[2, 3])))
print("production_reversal_C_bytes_equal", raster_a.tobytes() == raster_b.tobytes())
print("stored_forward_x0", first.to_dict()["objects"][0]["parameters"]["x0_px"])
print("stored_reverse_x0", second.to_dict()["objects"][0]["parameters"]["x0_px"])
```

Exact `boundary_probe_output.txt`:

```text
Python 3.11.9 NumPy 2.4.6
forward 0.07246575342465754 0x1.28d1d9909f59fp-4
reverse 0.07246575342465755 0x1.28d1d9909f5a0p-4
width 0.5383892771022006 0x1.13a7c2635791bp-1
threshold 0.07246575342465754 0x1.28d1d9909f59fp-4
straddles True
production_forward_origin 0.3
production_reverse_origin 0.3
production_reversal_C_bytes_equal True
stored_forward_x0 -1.3
stored_reverse_x0 2.7
```

Membership masks, preserved scalar/array bits, shape, dtype, C-order storage and
reversed endpoint equivalence are exact discrete claims. These tests do not use
`allclose` to hide mismatched masks or assigned values; relative/absolute
numerical tolerances are inapplicable to those byte comparisons. Required
arithmetic errors raise rather than being converted into approximate equality.
No M0–M6 tolerance or numerical threshold changes. The rational references do
not imply that every binary64 boundary equals an exact-real boundary.

## Controller, installed AppTest and final full suite

The controller/API checks call the actual public functions. The final set
covers canvas-authoritative shape, canonical design identity, selection versus
edits, direct fractional target bytes, exactly one M5 call, and all failure
boundaries: zero target, unusable geometry, snapshot write failure, subsequent
M5 failure with retained snapshot, and presentation failure after publication.
External-design cases include missing, malformed, valid-but-mismatched and
matching JSON. Numerical inspection/replay remains independent of that file.
Architecture checks keep UI/plotting/filesystem/solver responsibilities apart
and leave existing guards unchanged.

The earlier combined controller/architecture command and exit-0 output:

```powershell
& .\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/test_designer_controller.py tests/test_designer_architecture.py -q -p no:cacheprovider --basetemp .pytest_cache/m7-controller-agent-01 2>&1 | Tee-Object -FilePath runs/m7_acceptance_20260930/controller-architecture-discovery-01.txt
$designerTestExit = $LASTEXITCODE
exit $designerTestExit
```

```text
......................................                                   [100%]
38 passed in 1.67s
```

Peer review then added a direct regression for changing the bundle path through
the associated-design action: diagnostic opt-in must be revoked even when its
external design is missing. Exact focused command and exit-0 output:

```powershell
& .\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/test_designer_controller.py::test_association_changed_bundle_revokes_diagnostic_even_when_design_missing -q -p no:cacheprovider --basetemp .pytest_cache/m7-association-agent-01 2>&1 | Tee-Object -FilePath runs/m7_acceptance_20260930/association-revocation-focused.txt
$designerTestExit = $LASTEXITCODE
exit $designerTestExit
```

```text
.                                                                        [100%]
1 passed in 0.41s
```

### Installed AppTest discovery and completed rerun

The first AppTest discovery run recorded one failure and 16 passes. It is
retained as discovery evidence, separate from intentional negative controls.
The failed assertion was a **test expectation error**: an explicit replay
already uses the inherited M6 load path and intentionally clears the original
`submitted` record. The corrected test separates direct generation followed by
mode change (retain that submission) from replay followed by mode change
(retain the loaded bundle/settings with `submitted=None`). It does not change
that existing replay contract to satisfy the incorrect assertion.

Separately, peer review corrected return-to-Designer widget rehydration and
selection/association diagnostic-status resets. The later passing run contains
18 cases, including mode-return canvas/selection coherence. The final full
suite below uses the completed source/test state; the older discovery output
is not relabelled as a pass.

Exact initial command/output:

```powershell
& .\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/test_designer_streamlit.py -q -p no:cacheprovider --basetemp .pytest_cache/m7-ui-agent-01 2>&1 | Tee-Object -FilePath runs/m7_acceptance_20260930/apptest-discovery-01.txt
$designerTestExit = $LASTEXITCODE
exit $designerTestExit
```

```text
...............F.                                                        [100%]
================================== FAILURES ===================================
_ test_mode_change_preserves_saved_design_identity_revokes_diagnostic_and_status _

local_ui = (WindowsPath('C:/holographiclab/.pytest_cache/m7-ui-agent-01/test_mode_change_preserves_sav0/runs'), {'run_and_save_bu...{'revision': 'dddddddddddddddddddddddddddddddddddddddd', 'state': 'dirty', 'method': 'caller'}, 'diagnostic': True})]})

    def test_mode_change_preserves_saved_design_identity_revokes_diagnostic_and_status(local_ui):
        at = _app()
        _import(at)
        state = _generate(at)
        path, submitted = state.saved_path, state.submitted
        at.checkbox(key="diagnostic_enabled").check().run()
        _button(at, "diagnostic").click().run()
        assert state.comparison == "passed" and state.qualification == "unqualified"
        at.selectbox(key="draft_target_kind").set_value("builtin").run()
        _clean(at)
        assert not at.checkbox(key="diagnostic_enabled").value
        assert state.comparison == "not_run" and state.qualification == "not_evaluated"
>       assert state.bundle.path == path and state.submitted is submitted
E       assert (WindowsPath('C:/holographiclab/.pytest_cache/m7-ui-agent-01/test_mode_change_preserves_sav0/runs/m7/7039413766c341f09c65ac827a9225d0') == WindowsPath('C:/holographiclab/.pytest_cache/m7-ui-agent-01/test_mode_change_preserves_sav0/runs/m7/7039413766c341f09c65ac827a9225d0') and None is SubmittedRun(token='502b01043cf24ab09f4376953ebdfa2b', destination=WindowsPath('C:/holographiclab/.pytest_cache/m7-ui-...e_v1",\n  "schema_version": 1\n}\n'), design_sha256='fad8745c0523d754f9ad8f5c81e3e2178f40a642f3b494a21b3554b92469b975'))
E        +  where WindowsPath('C:/holographiclab/.pytest_cache/m7-ui-agent-01/test_mode_change_preserves_sav0/runs/m7/7039413766c341f09c65ac827a9225d0') = _RunBundle(path=WindowsPath('C:/holographiclab/.pytest_cache/m7-ui-agent-01/test_mode_change_preserves_sav0/runs/m7/70...n    "method": "caller",\n    "revision": "dddddddddddddddddddddddddddddddddddddddd",\n    "state": "dirty"\n  }\n}\n').path
E        +    where _RunBundle(path=WindowsPath('C:/holographiclab/.pytest_cache/m7-ui-agent-01/test_mode_change_preserves_sav0/runs/m7/70...n    "method": "caller",\n    "revision": "dddddddddddddddddddddddddddddddddddddddd",\n    "state": "dirty"\n  }\n}\n') = WorkbenchState(offered_nonce='3e93904683624eac830b349846f859ca', busy=False, pending=None, consumed_tokens={'98bfa266e..._at=None, design_snapshot_path=None, association_status='not_evaluated', association_error=None, association_path=None).bundle
E        +  and   None = WorkbenchState(offered_nonce='3e93904683624eac830b349846f859ca', busy=False, pending=None, consumed_tokens={'98bfa266e..._at=None, design_snapshot_path=None, association_status='not_evaluated', association_error=None, association_path=None).submitted

tests\test_designer_streamlit.py:348: AssertionError
---------------------------- Captured stderr call -----------------------------
2026-09-30 14:07:56.310 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
------------------------------ Captured log call ------------------------------
WARNING  streamlit.runtime.scriptrunner_utils.script_run_context:script_run_context.py:479 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
=========================== short test summary info ===========================
FAILED tests/test_designer_streamlit.py::test_mode_change_preserves_saved_design_identity_revokes_diagnostic_and_status
1 failed, 16 passed in 64.28s (0:01:04)
```

Exact completed command/output (exit 0):

```powershell
& .\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/test_designer_streamlit.py -q -p no:cacheprovider --basetemp .pytest_cache/m7-ui-agent-02 2>&1 | Tee-Object -FilePath runs/m7_acceptance_20260930/apptest-focused-02.txt
$designerTestExit = $LASTEXITCODE
exit $designerTestExit
```

```text
..................                                                       [100%]
18 passed in 66.23s (0:01:06)
```

### Final full suite — exit 0

The final suite ran after the six negative controls, without source/test
changes after those controls. It retained the original 1397 M6 cases and
added **174 M7 cases**: 117 model/design-I/O, 28 controller, 18 installed
AppTest and 11 architecture. The result is **1570 passed, 1 skipped**, 1571
cases total. The existing Windows file-symlink privilege skip is unchanged.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp=runs/m7_acceptance_20260930/pytest_final
```

Exact `final_suite.txt`, SHA-256
`36acc0b3d6c5d92000b4e3b98e3657e4d4687f64051669c6d1b174a73cdab69e`:

```text
........................................................................ [  4%]
........................................................................ [  9%]
........................................................................ [ 13%]
........................................................................ [ 18%]
........................................................................ [ 22%]
........................................................................ [ 27%]
........................................................................ [ 32%]
........................................................................ [ 36%]
........................................................................ [ 41%]
........................................................................ [ 45%]
........................................................................ [ 50%]
........................................................................ [ 54%]
........................................................................ [ 59%]
........................................................................ [ 64%]
..............s......................................................... [ 68%]
........................................................................ [ 73%]
........................................................................ [ 77%]
........................................................................ [ 82%]
........................................................................ [ 87%]
........................................................................ [ 91%]
........................................................................ [ 96%]
...........................................................              [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
1570 passed, 1 skipped in 111.67s (0:01:51)
```

## Six deliberate negative controls — completed

Each isolated child process injected one in-memory fault, then ran the named
unmodified detecting test. No production/test file was edited; mutations were
discarded when each child exited. The harness checks call-phase
`AssertionError`, expected failure count, no other failures and unchanged
source/test hashes. Setup or collection errors are not accepted detections.
The six controls produced nine intended assertion failures:

| Fault | Detecting case | Intended failures |
|---|---|---|
| Swap x/y inputs to membership | Four mixed-parity asymmetric/origin cases | 4 |
| Assign square-root amplitude as intensity | Hand-enumerated radius-2 disk and exact fractional samples | 1 |
| Normalize by the target peak | The same independent fractional-intensity mask | 1 |
| Reverse the stored object traversal | Exact later overwrite, including signed zero | 1 |
| Invoke M5 twice, suppressing the second destination collision | Exactly-one-call controller assertion | 1 |
| Render old arrays with current draft settings | Saved-result settings/identity assertion after an edit | 1 |

`negative-controls-final01-before.json` and `...-after.json` contain the same
49-file inventory from `src/**/*.py`, `apps/**/*.py` and `tests/**/*.py`.
Both capture files have SHA-256
`bd879a06d8bcff8c1edbb3b17e5bd4cdaf2de14ec1e3401dbbde6c61cef60937`.
A read-only check while assembling this document also found every current
listed file equal to its recorded hash. This is a bounded source/test window,
not an assertion about unlisted documents, generated data or future edits.

The driver exits 0 only after detecting all expected faults and verifying
restoration. Individual pytest calls deliberately exit 1. Raw transcript
SHA-256 is `8aaaff1dfbe8ba58df9e7fca34f6de482d14435ee1c4a7ce7e1cb4dc250dabe6`;
driver SHA-256 is `467a37f9e1826e84a0235c0535bd179e391389093bb56b361bf52f5107b455cd`.
The complete code/output below preserve pytest's own abbreviations and the
captured bare-mode Streamlit warning; no warning filtering is introduced.

Original command:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 runs/m7_acceptance_20260930/negative_controls.py --tag final01
```

To reproduce, save the exact embedded driver at that ignored path and use a
fresh tag if its output filenames already exist. The driver uses exclusive
creation rather than overwriting retained transcripts. The final production
suite above ran afterward.

Exact driver:

```python
"""Six isolated in-memory M7 faults; source and test files are never edited."""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

CASES = {
    "transpose_xy": ("tests/test_target_design.py::test_mixed_parity_asymmetric_xy_and_origin", 4),
    "intensity_as_amplitude": ("tests/test_target_design.py::test_hand_computable_disk_mask_and_fractional_intensity", 1),
    "peak_normalization": ("tests/test_target_design.py::test_hand_computable_disk_mask_and_fractional_intensity", 1),
    "ignored_object_order": ("tests/test_target_design.py::test_later_object_overwrites_including_exact_signed_zero", 1),
    "duplicate_generation": ("tests/test_designer_controller.py::test_designer_exact_fractional_target_direct_m5_and_one_save", 1),
    "stale_result_relabeling": ("tests/test_designer_streamlit.py::test_selection_alone_does_not_mark_saved_result_stale_but_content_edit_does", 1),
}


def inventory():
    paths = sorted({*ROOT.glob("src/**/*.py"), *ROOT.glob("apps/**/*.py"), *ROOT.glob("tests/**/*.py")})
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def replace_function(module, function_name, before, after, *, label):
    source = inspect.getsource(getattr(module, function_name))
    assert source.count(before) == 1, (label, "mutation anchor must occur exactly once")
    print("MUTATION " + json.dumps({"module": module.__name__, "function": function_name,
                                    "before": before, "after": after}), flush=True)
    exec(compile(source.replace(before, after), "<M7 in-memory fault: " + label + ">", "exec"), module.__dict__)


def mutate(name):
    if name in {"transpose_xy", "intensity_as_amplitude", "peak_normalization", "ignored_object_order"}:
        import ohlab.target_design as model
        changes = {
            "transpose_xy": ("mask = _membership(obj, x, y)", "mask = _membership(obj, y, x)"),
            "intensity_as_amplitude": ('result[mask] = obj["intensity"]', 'result[mask] = np.sqrt(obj["intensity"])'),
            "peak_normalization": ("    return result\n", "    return result / np.max(result)\n"),
            "ignored_object_order": ('for obj in spec["objects"]:', 'for obj in reversed(spec["objects"]):'),
        }
        replace_function(model, "rasterize_target_design", *changes[name], label=name)
    elif name == "duplicate_generation":
        from apps import workbench as wb
        anchor = "            # Publication success is committed to session state before cleanup\n"
        # Deliberately repeat the public M5 writer while still busy. Suppressing
        # the no-overwrite error keeps the first successful result visible so
        # the independent exactly-one-call assertion must detect this fault.
        duplicate = '''            try:
                run_and_save_bundle(
                    submitted.destination, config=submitted.config, target_intensity=intensity,
                    source_amplitude=source, input_png=png_path, source_revision=detect_source_revision(),
                )
            except FileExistsError:
                pass
'''
        replace_function(wb, "execute_pending_run", anchor, duplicate + anchor, label=name)
    elif name == "stale_result_relabeling":
        from types import SimpleNamespace
        from apps import streamlit_app as ui, workbench as wb
        original = ui._render_result
        def relabel(state, draft):
            saved = state.bundle
            if saved is None or state.submitted is None:
                return original(state, draft)
            state.bundle = SimpleNamespace(arrays=saved.arrays, metrics=saved.metrics,
                                           config=wb._draft_config(draft), software=saved.software, path=saved.path)
            try:
                return original(state, draft)
            finally:
                state.bundle = saved
        print("MUTATION " + json.dumps({"module": "apps.streamlit_app", "function": "_render_result",
                                        "fault": "render existing saved arrays using current draft RunConfig"}), flush=True)
        ui._render_result = relabel
    else:
        raise AssertionError(name)


def child(name, tag):
    import pytest
    before = inventory()
    reports, exceptions = [], []
    class Outcomes:
        def pytest_configure(self, config):
            # Plugins register before UI imports anyio; warnings remain errors.
            mutate(name)
        def pytest_runtest_makereport(self, item, call):
            if call.excinfo is not None:
                exceptions.append({"nodeid": item.nodeid, "when": call.when,
                                   "type": call.excinfo.typename})
        def pytest_runtest_logreport(self, report):
            reports.append({"nodeid": report.nodeid, "when": report.when, "outcome": report.outcome})
    selector, expected_count = CASES[name]
    arguments = [selector, "-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", f".pytest_cache/m7-negative-{tag}-{name}"]
    print("PYTEST_ARGS " + json.dumps(arguments), flush=True)
    code = int(pytest.main(arguments, plugins=[Outcomes()]))
    failures = [row for row in reports if row["outcome"] == "failed"]
    intended = [row for row in failures if row["when"] == "call" and
                (row["nodeid"] == selector or row["nodeid"].startswith(selector + "["))]
    same = inventory() == before
    assertion_only = len(exceptions) == expected_count and all(row["when"] == "call" and row["type"] == "AssertionError" for row in exceptions)
    accepted = code == 1 and len(intended) == len(failures) == expected_count and assertion_only and same
    record = {"control": name, "pytest_exit": code, "intended_assertion_failures": len(intended),
              "failures": failures, "exceptions": exceptions, "source_test_hashes_unchanged": same,
              "hashed_files": len(before), "accepted_detection": accepted}
    print("CONTROL_RESULT " + json.dumps(record, sort_keys=True), flush=True)
    return 0 if accepted else 2


def exclusive_write(path, payload):
    with path.open("xb") as stream:
        stream.write(payload)


def parent(tag):
    before = inventory()
    exclusive_write(EVIDENCE / f"negative-controls-{tag}-before.json", (json.dumps(before, indent=2, sort_keys=True) + "\n").encode())
    transcript = [("PARENT_COMMAND " + subprocess.list2cmdline([sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()), "--tag", tag]) + "\n").encode()]
    all_ok = True
    for name in CASES:
        command = [sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()), "--child", name, "--tag", tag]
        heading = ("COMMAND " + subprocess.list2cmdline(command) + "\n").encode()
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONUTF8"] = "1"
        result = subprocess.run(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        exclusive_write(EVIDENCE / f"negative-control-{tag}-{name}-output.txt", result.stdout)
        transcript.extend((heading, result.stdout))
        sys.stdout.buffer.write(heading + result.stdout)
        sys.stdout.flush()
        same = inventory() == before
        all_ok = all_ok and result.returncode == 0 and same
        if not same:
            print("HASH_WINDOW_CHANGED: stopping; do not restore others' edits.", flush=True)
            break
    after = inventory()
    exclusive_write(EVIDENCE / f"negative-controls-{tag}-after.json", (json.dumps(after, indent=2, sort_keys=True) + "\n").encode())
    final = {"all_expected_controls_detected": all_ok, "source_test_hashes_unchanged": before == after,
             "hashed_files": len(before), "restoration": "fresh child in-memory mutations discarded; no tracked file edits"}
    ending = ("FINAL_RESULT " + json.dumps(final, sort_keys=True) + "\n").encode()
    transcript.append(ending)
    exclusive_write(EVIDENCE / f"negative-controls-{tag}-transcript.txt", b"".join(transcript))
    sys.stdout.buffer.write(ending)
    sys.stdout.flush()
    return 0 if all_ok else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", choices=CASES)
    parser.add_argument("--tag", default="final01")
    args = parser.parse_args()
    assert args.tag and all(char.isalnum() or char in "_-" for char in args.tag)
    raise SystemExit(child(args.child, args.tag) if args.child else parent(args.tag))
```

Exact transcript:

```text
PARENT_COMMAND C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 C:\holographiclab\runs\m7_acceptance_20260930\negative_controls.py --tag final01
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 C:\holographiclab\runs\m7_acceptance_20260930\negative_controls.py --child transpose_xy --tag final01
PYTEST_ARGS ["tests/test_target_design.py::test_mixed_parity_asymmetric_xy_and_origin", "-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", ".pytest_cache/m7-negative-final01-transpose_xy"]
MUTATION {"module": "ohlab.target_design", "function": "rasterize_target_design", "before": "mask = _membership(obj, x, y)", "after": "mask = _membership(obj, y, x)"}
FFFF                                                                     [100%]
================================== FAILURES ===================================
E   AssertionError: assert b'\x00\x00\x0...0\x00\x00\x00' == b'\x00\x00\x0...0\x00\x00\x00'
      
      At index 96 diff: b'\x00' != b'3'
      Use -v to get more diff
C:\holographiclab\tests\test_target_design.py:38: AssertionError: assert b'\x00\x00\x0...0\x00\x00\x00' == b'\x00\x00\x0...0\x00\x00\x00'
E   AssertionError: assert b'\x00\x00\x0...0\x00\x00\x00' == b'\x00\x00\x0...0\x00\x00\x00'
      
      At index 112 diff: b'\x00' != b'3'
      Use -v to get more diff
C:\holographiclab\tests\test_target_design.py:38: AssertionError: assert b'\x00\x00\x0...0\x00\x00\x00' == b'\x00\x00\x0...0\x00\x00\x00'
E   AssertionError: assert b'\x00\x00\x0...0\x00\x00\x00' == b'\x00\x00\x0...0\x00\x00\x00'
      
      At index 112 diff: b'\x00' != b'3'
      Use -v to get more diff
C:\holographiclab\tests\test_target_design.py:38: AssertionError: assert b'\x00\x00\x0...0\x00\x00\x00' == b'\x00\x00\x0...0\x00\x00\x00'
E   AssertionError: assert b'\x00\x00\x0...0\x00\x00\x00' == b'\x00\x00\x0...0\x00\x00\x00'
      
      At index 96 diff: b'\x00' != b'3'
      Use -v to get more diff
C:\holographiclab\tests\test_target_design.py:38: AssertionError: assert b'\x00\x00\x0...0\x00\x00\x00' == b'\x00\x00\x0...0\x00\x00\x00'
=========================== short test summary info ===========================
FAILED tests/test_target_design.py::test_mixed_parity_asymmetric_xy_and_origin[shape0]
FAILED tests/test_target_design.py::test_mixed_parity_asymmetric_xy_and_origin[shape1]
FAILED tests/test_target_design.py::test_mixed_parity_asymmetric_xy_and_origin[shape2]
FAILED tests/test_target_design.py::test_mixed_parity_asymmetric_xy_and_origin[shape3]
4 failed in 0.06s
CONTROL_RESULT {"accepted_detection": true, "control": "transpose_xy", "exceptions": [{"nodeid": "tests/test_target_design.py::test_mixed_parity_asymmetric_xy_and_origin[shape0]", "type": "AssertionError", "when": "call"}, {"nodeid": "tests/test_target_design.py::test_mixed_parity_asymmetric_xy_and_origin[shape1]", "type": "AssertionError", "when": "call"}, {"nodeid": "tests/test_target_design.py::test_mixed_parity_asymmetric_xy_and_origin[shape2]", "type": "AssertionError", "when": "call"}, {"nodeid": "tests/test_target_design.py::test_mixed_parity_asymmetric_xy_and_origin[shape3]", "type": "AssertionError", "when": "call"}], "failures": [{"nodeid": "tests/test_target_design.py::test_mixed_parity_asymmetric_xy_and_origin[shape0]", "outcome": "failed", "when": "call"}, {"nodeid": "tests/test_target_design.py::test_mixed_parity_asymmetric_xy_and_origin[shape1]", "outcome": "failed", "when": "call"}, {"nodeid": "tests/test_target_design.py::test_mixed_parity_asymmetric_xy_and_origin[shape2]", "outcome": "failed", "when": "call"}, {"nodeid": "tests/test_target_design.py::test_mixed_parity_asymmetric_xy_and_origin[shape3]", "outcome": "failed", "when": "call"}], "hashed_files": 49, "intended_assertion_failures": 4, "pytest_exit": 1, "source_test_hashes_unchanged": true}
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 C:\holographiclab\runs\m7_acceptance_20260930\negative_controls.py --child intensity_as_amplitude --tag final01
PYTEST_ARGS ["tests/test_target_design.py::test_hand_computable_disk_mask_and_fractional_intensity", "-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", ".pytest_cache/m7-negative-final01-intensity_as_amplitude"]
MUTATION {"module": "ohlab.target_design", "function": "rasterize_target_design", "before": "result[mask] = obj[\"intensity\"]", "after": "result[mask] = np.sqrt(obj[\"intensity\"])"}
F                                                                        [100%]
================================== FAILURES ===================================
E   AssertionError: assert b'\x00\x00\x0...0\x00\x00\x00' == b'\x00\x00\x0...0\x00\x00\x00'
      
      At index 24 diff: b'r' != b'3'
      Use -v to get more diff
C:\holographiclab\tests\test_target_design.py:38: AssertionError: assert b'\x00\x00\x0...0\x00\x00\x00' == b'\x00\x00\x0...0\x00\x00\x00'
=========================== short test summary info ===========================
FAILED tests/test_target_design.py::test_hand_computable_disk_mask_and_fractional_intensity
1 failed in 0.05s
CONTROL_RESULT {"accepted_detection": true, "control": "intensity_as_amplitude", "exceptions": [{"nodeid": "tests/test_target_design.py::test_hand_computable_disk_mask_and_fractional_intensity", "type": "AssertionError", "when": "call"}], "failures": [{"nodeid": "tests/test_target_design.py::test_hand_computable_disk_mask_and_fractional_intensity", "outcome": "failed", "when": "call"}], "hashed_files": 49, "intended_assertion_failures": 1, "pytest_exit": 1, "source_test_hashes_unchanged": true}
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 C:\holographiclab\runs\m7_acceptance_20260930\negative_controls.py --child peak_normalization --tag final01
PYTEST_ARGS ["tests/test_target_design.py::test_hand_computable_disk_mask_and_fractional_intensity", "-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", ".pytest_cache/m7-negative-final01-peak_normalization"]
MUTATION {"module": "ohlab.target_design", "function": "rasterize_target_design", "before": "    return result\n", "after": "    return result / np.max(result)\n"}
F                                                                        [100%]
================================== FAILURES ===================================
E   AssertionError: assert b'\x00\x00\x0...0\x00\x00\x00' == b'\x00\x00\x0...0\x00\x00\x00'
      
      At index 24 diff: b'\x00' != b'3'
      Use -v to get more diff
C:\holographiclab\tests\test_target_design.py:38: AssertionError: assert b'\x00\x00\x0...0\x00\x00\x00' == b'\x00\x00\x0...0\x00\x00\x00'
=========================== short test summary info ===========================
FAILED tests/test_target_design.py::test_hand_computable_disk_mask_and_fractional_intensity
1 failed in 0.19s
CONTROL_RESULT {"accepted_detection": true, "control": "peak_normalization", "exceptions": [{"nodeid": "tests/test_target_design.py::test_hand_computable_disk_mask_and_fractional_intensity", "type": "AssertionError", "when": "call"}], "failures": [{"nodeid": "tests/test_target_design.py::test_hand_computable_disk_mask_and_fractional_intensity", "outcome": "failed", "when": "call"}], "hashed_files": 49, "intended_assertion_failures": 1, "pytest_exit": 1, "source_test_hashes_unchanged": true}
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 C:\holographiclab\runs\m7_acceptance_20260930\negative_controls.py --child ignored_object_order --tag final01
PYTEST_ARGS ["tests/test_target_design.py::test_later_object_overwrites_including_exact_signed_zero", "-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", ".pytest_cache/m7-negative-final01-ignored_object_order"]
MUTATION {"module": "ohlab.target_design", "function": "rasterize_target_design", "before": "for obj in spec[\"objects\"]:", "after": "for obj in reversed(spec[\"objects\"]):"}
F                                                                        [100%]
================================== FAILURES ===================================
E   AssertionError: assert b'\x9a\x99\x9...\x99\x99\xb9?' == b'\x9a\x99\x9...\x99\x99\xb9?'
      
      At index 80 diff: b'3' != b'\x00'
      Use -v to get more diff
C:\holographiclab\tests\test_target_design.py:38: AssertionError: assert b'\x9a\x99\x9...\x99\x99\xb9?' == b'\x9a\x99\x9...\x99\x99\xb9?'
=========================== short test summary info ===========================
FAILED tests/test_target_design.py::test_later_object_overwrites_including_exact_signed_zero
1 failed in 0.19s
CONTROL_RESULT {"accepted_detection": true, "control": "ignored_object_order", "exceptions": [{"nodeid": "tests/test_target_design.py::test_later_object_overwrites_including_exact_signed_zero", "type": "AssertionError", "when": "call"}], "failures": [{"nodeid": "tests/test_target_design.py::test_later_object_overwrites_including_exact_signed_zero", "outcome": "failed", "when": "call"}], "hashed_files": 49, "intended_assertion_failures": 1, "pytest_exit": 1, "source_test_hashes_unchanged": true}
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 C:\holographiclab\runs\m7_acceptance_20260930\negative_controls.py --child duplicate_generation --tag final01
PYTEST_ARGS ["tests/test_designer_controller.py::test_designer_exact_fractional_target_direct_m5_and_one_save", "-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", ".pytest_cache/m7-negative-final01-duplicate_generation"]
MUTATION {"module": "apps.workbench", "function": "execute_pending_run", "before": "            # Publication success is committed to session state before cleanup\n", "after": "            try:\n                run_and_save_bundle(\n                    submitted.destination, config=submitted.config, target_intensity=intensity,\n                    source_amplitude=source, input_png=png_path, source_revision=detect_source_revision(),\n                )\n            except FileExistsError:\n                pass\n            # Publication success is committed to session state before cleanup\n"}
F                                                                        [100%]
================================== FAILURES ===================================
E   AssertionError: assert [WindowsPath(...b64730e5b13')] == [WindowsPath(...b64730e5b13')]
      
      Left contains one more item: WindowsPath('C:/holographiclab/.pytest_cache/m7-negative-final01-duplicate_generation/test_designer_exact_fractional0/runs/m7/4fa81b2be54d4948a3268b64730e5b13')
      Use -v to get more diff
C:\holographiclab\tests\test_designer_controller.py:100: AssertionError: assert [WindowsPath(...b64730e5b13')] == [WindowsPath(...b64730e5b13')]
=========================== short test summary info ===========================
FAILED tests/test_designer_controller.py::test_designer_exact_fractional_target_direct_m5_and_one_save
1 failed in 0.45s
CONTROL_RESULT {"accepted_detection": true, "control": "duplicate_generation", "exceptions": [{"nodeid": "tests/test_designer_controller.py::test_designer_exact_fractional_target_direct_m5_and_one_save", "type": "AssertionError", "when": "call"}], "failures": [{"nodeid": "tests/test_designer_controller.py::test_designer_exact_fractional_target_direct_m5_and_one_save", "outcome": "failed", "when": "call"}], "hashed_files": 49, "intended_assertion_failures": 1, "pytest_exit": 1, "source_test_hashes_unchanged": true}
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 C:\holographiclab\runs\m7_acceptance_20260930\negative_controls.py --child stale_result_relabeling --tag final01
PYTEST_ARGS ["tests/test_designer_streamlit.py::test_selection_alone_does_not_mark_saved_result_stale_but_content_edit_does", "-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", ".pytest_cache/m7-negative-final01-stale_result_relabeling"]
MUTATION {"module": "apps.streamlit_app", "function": "_render_result", "fault": "render existing saved arrays using current draft RunConfig"}
F                                                                        [100%]
================================== FAILURES ===================================
E   AssertionError: assert [{'grid': {'d...ion': 1, ...}] == [{'grid': {'d...ion': 1, ...}]
      
      At index 0 diff: {'grid': {'dx_m': 8e-06, 'dy_m': 8e-06, 'nx': 5, 'ny': 4}, 'metrics': {'intensity_mse': {}, 'intensity_nmse': {}, 'intensity_psnr': {'data_range': 1.0}}, 'optics': {'distance_m': 0.0, 'wavelength_m': 6.33e-07}, 'schema_version': 1, 'solver': {'algorithm': 'gerchberg_saxton', 'contract': 'm3_periodic_lossless_asm_v1', 'initialization': {'mode': 'seed', 'seed': 17}, 'iterations': 0}} != {'grid': {'dx_m': 8e-06, 'dy_m': 8e-06, 'nx': 5, 'ny': 4}, 'metrics': {'intensity_mse': {}, 'intensity_nmse': {}, 'intensity_psnr': {'data_range': 1.0}}, 'optics': {'dista...
      
      ...Full output truncated (2 lines hidden), use '-vv' to show
---------------------------- Captured stderr call -----------------------------
2026-09-30 14:15:55.560 WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.

------------------------------ Captured log call ------------------------------
WARNING  streamlit.runtime.scriptrunner_utils.script_run_context:script_run_context.py:479 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
C:\holographiclab\tests\test_designer_streamlit.py:155: AssertionError: assert [{'grid': {'d...ion': 1, ...}] == [{'grid': {'d...ion': 1, ...}]
=========================== short test summary info ===========================
FAILED tests/test_designer_streamlit.py::test_selection_alone_does_not_mark_saved_result_stale_but_content_edit_does
1 failed in 6.43s
CONTROL_RESULT {"accepted_detection": true, "control": "stale_result_relabeling", "exceptions": [{"nodeid": "tests/test_designer_streamlit.py::test_selection_alone_does_not_mark_saved_result_stale_but_content_edit_does", "type": "AssertionError", "when": "call"}], "failures": [{"nodeid": "tests/test_designer_streamlit.py::test_selection_alone_does_not_mark_saved_result_stale_but_content_edit_does", "outcome": "failed", "when": "call"}], "hashed_files": 49, "intended_assertion_failures": 1, "pytest_exit": 1, "source_test_hashes_unchanged": true}
FINAL_RESULT {"all_expected_controls_detected": true, "hashed_files": 49, "restoration": "fresh child in-memory mutations discarded; no tracked file edits", "source_test_hashes_unchanged": true}
```

## Asymmetric example — completed

The standalone `examples/design_target.py` uses a 48 × 64 zero-background
canvas and these fixed objects, in order; IDs are respectively 32 repeated
`1`, `2` and `3` characters:

| Primitive | Pixel parameters | Intensity |
|---|---|---|
| Disk | center `(-9,-4)`, radius `10` | `0.3` |
| Rectangle | center `(3,2)`, width `20`, height `12` | `0.65` |
| Segment | endpoints `(-18,13)`, `(19,-10)`, width `4` | `0.45` |

The overlap order produces counts `2449,246,188,189` at intensities
`0,0.3,0.45,0.65`. It uses `dy=10e-6 m`, `dx=8e-6 m`, wavelength `633e-9 m`,
distance `0.005 m`, seed 0, 20 cycles and PSNR range 1. A saved editable copy is
loaded and rasterized, compared exactly, then captured as a separate submitted
snapshot and passed to M5 with `input_png=None`. Reloaded M5 target bytes also
match. UUID paths vary on another invocation; the fixed design/raster are
reproducible under the declared environment. No path is overwritten.

The captured design JSON SHA-256 is
`f05b1e1072c95c8933f6c503c94a0333418dc579e0758d35b10b230087932c2a`;
the target C-order element-byte SHA-256 is
`a0cc6e081ad448a9086ace160eb3b5c15c0519abfecd634acff93d0380f6d4b0`.
These hash different representations and are not interchangeable.

Exact command, completed with exit 0:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 examples/design_target.py --runs-root runs/m7_acceptance_20260930/example_01 --diagnostic
```

Exact `example_01.txt`:

```text
editable copy: C:\holographiclab\runs\m7_acceptance_20260930\example_01\designs\bbba2f33ab3341089b6ad891044a2598.json
submitted design snapshot: C:\holographiclab\runs\m7_acceptance_20260930\example_01\designs\submissions\c0b89fa2d5244ccfa11d99fb07b21ad9.json
completed bundle: C:\holographiclab\runs\m7_acceptance_20260930\example_01\m7\c0b89fa2d5244ccfa11d99fb07b21ad9
design JSON SHA-256: f05b1e1072c95c8933f6c503c94a0333418dc579e0758d35b10b230087932c2a
target C-order bytes SHA-256: a0cc6e081ad448a9086ace160eb3b5c15c0519abfecd634acff93d0380f6d4b0
design reload raster and saved target: exact dtype/shape/C-order bytes match
config: {"grid": {"dx_m": 8e-06, "dy_m": 1e-05, "nx": 64, "ny": 48}, "metrics": {"intensity_mse": {}, "intensity_nmse": {}, "intensity_psnr": {"data_range": 1.0}}, "optics": {"distance_m": 0.005, "wavelength_m": 6.33e-07}, "schema_version": 1, "solver": {"algorithm": "gerchberg_saxton", "contract": "m3_periodic_lossless_asm_v1", "initialization": {"mode": "seed", "seed": 0}, "iterations": 20}}
target levels/counts: [[0.0, 2449], [0.3, 246], [0.45, 188], [0.65, 189]]
explicit uniform source amplitude: 3.02576823922454441e-01
recorded source: {"method": "git", "revision": "cc93c949da23de4a6f98acc0c4954c3c2d7f6849", "state": "dirty"}
current source: {"method": "git", "revision": "cc93c949da23de4a6f98acc0c4954c3c2d7f6849", "state": "dirty"}
strict integrity / qualification / comparison: passed / unqualified / not_run
strict reasons: recorded source state is dirty, expected clean; current source state is dirty, expected clean
intensity_mse: 1.72204192742301675e-03
intensity_nmse: 3.77696585527425785e-02
intensity_psnr: 2.76395627876692593e+01
separate M3 amplitude residual: initial=1.18988626441086098e+00; final=7.45193280962366811e-02; entries=21
Hard-edged target example: no Gaussian quality threshold or general convergence claim.
explicit diagnostic integrity / qualification / comparison: passed / unqualified / passed
diagnostic checks: {"derived:phase": true, "derived:reconstruction_intensity": true, "derived:target_amplitude": true, "output:phase": true, "output:reconstruction_field": true, "output:reconstruction_intensity": true, "output:residual_history": true, "output:source_field": true, "replay_metric:intensity_mse": true, "replay_metric:intensity_nmse": true, "replay_metric:intensity_psnr": true, "saved_metric:intensity_mse": true, "saved_metric:intensity_nmse": true, "saved_metric:intensity_psnr": true}
```

The actual intensity MSE is approximately `0.00172204`, NMSE `0.0377697`, and
PSNR `27.6396 dB`. The separate squared-amplitude residual decreases from about
`1.18989` to `0.0745193` across 21 retained samples. These are observations, not
an acceptance threshold for arbitrary hard-edged designs. Source amplitude is
explicitly chosen for this target, rather than normalized inside GS. Candidate
source is honestly dirty: strict replay is `passed / unqualified / not_run`;
only the explicitly requested diagnostic call returns comparison `passed`,
without upgrading qualification.

## Real browser and screenshots — precommit checks completed

The existing listener on port 8501 (PID 32420) was not task-owned and was
preserved. The task-owned server used **127.0.0.1:8502**, with CORS/XSRF enabled
and telemetry, file watching, run-on-save and fast reruns disabled. The checked-in
configuration was unchanged. The recorded launcher was PID 51756, started at
2026-09-30T14:15:57.6476695+08:00. Chrome drove the real application; installed
AppTest results are not substituted for these interactions.

The following completed observations are supported by DOM captures under the
same ignored evidence directory. The final parent-browser checks below complete
the same-name changed-content import and invalid-import recovery cases.

| Actual interaction | Observed result | Retained captures |
|---|---|---|
| Add/edit/reorder/delete | All three primitives added; disk radius 2; intensity edited between 0.3 and zero; rectangle 3×2; both reorder directions and deletion exercised | `browser-01-disk-radius.txt` through `browser-10-deleted-confirmed.txt` |
| Download and explicit reimport | Actual `target-design.json` download contained 669 canonical bytes; reimport restored 0.3 after a 0.8 draft edit | `browser-11-download.txt` through `browser-13-download-reimport-confirmed.txt` |
| Fresh session, import and save editable copy | Original 8×10 fixture imported; desired preview and saved-copy path shown before generation | `browser-51-fresh-session.txt` through `browser-55-preview-before-generation.txt` |
| Generate and real rapid/busy receipt | One accepted submission, one rejected consumed-nonce submission, one busy browser-trigger receipt, one snapshot and one M5 publication | `browser-56-iterations-two.txt` through `browser-58-completed-one-run.txt`; event record below |
| Selection and later content edit | Selection alone did not mark the saved result stale; changing rectangle intensity 0.6 to 0.4 showed the previous-submission warning while saved target/config retained their original identity | `browser-59-selection-only.txt` through `browser-61-stale-content-confirmed.txt` |
| Strict then explicitly enabled diagnostic replay | Strict: `passed / unqualified / not_run`; explicit diagnostic: `passed / unqualified / passed` | `browser-62-strict-candidate-request.txt`, `browser-63-strict-candidate-complete.txt`, `browser-64-diagnostic-candidate-complete.txt` |
| External association failures and recovery | Missing snapshot, duplicate-key invalid JSON and mismatched raster each preserved the current rectangle-0.4 editor; restoring the original snapshot allowed matching association | `browser-65-association-missing.txt`, `browser-67-association-invalid.txt`, `browser-69-association-mismatch.txt`, `browser-71-association-match.txt` |
| Numerical replay independent of editable JSON | Explicit diagnostic comparison passed during the external-unavailable interval and with mismatched external design; original snapshot restored bit-exactly and all numerical bundle file hashes unchanged | `browser-66-diagnostic-with-external-unavailable.txt`, `browser-70-diagnostic-with-mismatched-design.txt`; verification record below |
| Reload and explicit reopen | Fresh session showed default built-in 64×64/N=50 with no generation; explicit reopening retained saved 8×10/N=2 data and reported `passed / not_evaluated / not_run` | `browser-72-reload-fresh-session.txt`, `browser-73-reopened-explicit-no-replay.txt` |
| Same-name upload/import and invalid recovery | Both 928-byte `same.json` inputs required explicit import; changed content replaced 0.3 with 0.9, invalid JSON preserved the editor, and explicit valid reimport restored 0.3 and cleared the error | `browser-parent-01-original-upload-no-import.txt` through `browser-parent-12-recovery-import-complete.txt`; final import report below |

Both strict and diagnostic operations are labelled `Last operation: replay`.
A quick observation predicate expecting a different diagnostic operation name
was false; the actual diagnostic capture showed all three intended statuses.
This was an observation-predicate error, not an application replay failure.

### Same-name changed content and invalid-import recovery

Two delegated uploads in tab `1191378016` did not complete: their permission
requests were dismissed before a decision, with **no explicit denial and no
actual import**. `browser-test-02-upload-attempt.json` and
`browser-test-03-upload-retry.json` retain those failures. The final editor
remained an empty 64×64 canvas with background zero and no selected object;
`browser-test-04-final-agent-state.txt`/`.png` and
`browser-test-05-agent-close.json` record that state and closure. There was no
generation or replay in those attempts, and they are not counted as acceptance.

The user then explicitly confirmed browser upload permission. The parent used
the normal file chooser in actual tab `1191378028`, without changing browser
security settings or using a workaround. All four parent chooser attempts
completed; their exact timing records are `browser-parent-original-attempt.json`,
`browser-parent-changed-attempt.json`, `browser-parent-invalid-attempt.json` and
`browser-parent-recovery-attempt.json`. Some chooser calls still took minutes;
no cause beyond the observed permission/transport behavior is asserted.

The original and changed inputs shared basename `same.json` and encoded size
928 bytes, but their SHA-256 hashes and disk intensities differed. Uploading the
changed file alone kept the current editor at 0.3; explicit Import changed it
to 0.9. Importing duplicate-key JSON displayed the error while preserving the
8×10 canvas, background 0.125, selected disk `11111111`, center `(1,-1)`, radius
2 and intensity 0.9. Uploading the original alone retained that editor and
error; explicit Import restored 0.3 and cleared the error. No Generate or
replay action occurred and no saved-result panel appeared in this sequence.

The unedited final report is:

```json
{
  "actual_parent_tab": "1191378028",
  "same_basename": "same.json",
  "encoded_sizes": [
    928,
    928
  ],
  "input_sha256": [
    "e0c160329b4f28efb8c6c92bb8c13eabd3efb174d0ea9812c752373e41a10f34",
    "ac387dd1b4d7f74ae968f7f1d80942c381bd43db9c6af3899dcd6a6ae1a53571"
  ],
  "file_selection_alone_preserves_editor": true,
  "same_name_changed_content_explicit_import": "0.3 -> 0.9",
  "invalid_duplicate_key_preserves_canvas_selection_geometry_intensity": true,
  "explicit_valid_reimport_recovers_and_clears_error": true,
  "no_automatic_generation_or_replay": true,
  "delegated_attempts": "Two dismissed permission requests, no imports; preserved separately",
  "parent_permission": "Normal browser file chooser; user confirmed permission allowed; no settings changed"
}
```

The following exact verifier reads the captured DOM and fixture bytes; it does
not drive a browser or imply an import when only a fixture exists. Save it at
the recorded path and use the reproduction command below with those captures.
The actual interaction sequence above remains the browser evidence.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 runs/m7_acceptance_20260930/verify_browser_imports.py
```

```python
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parent
def capture(name):
    return (root / name).read_text(encoding="utf-8")
original = capture("browser-parent-03-original-import-complete.txt")
before = capture("browser-parent-04-changed-upload-before-import.txt")
changed = capture("browser-parent-06-changed-import-complete.txt")
invalid = capture("browser-parent-09-invalid-import-preserved-editor.txt")
recovery_before = capture("browser-parent-10-recovery-upload-before-import.txt")
recovered = capture("browser-parent-12-recovery-import-complete.txt")
fixed = ['spinbutton "畫布列數 ny": "8"', 'spinbutton "畫布欄數 nx": "10"',
         'spinbutton "背景強度 Background intensity": "0.125"',
         'combobox "物件順序（後者覆寫）": 1. disk · 11111111',
         'spinbutton "cx (px)": "1"', 'spinbutton "cy (px)": "-1"',
         'spinbutton "半徑 Radius (px)": "2"']
assert all(all(line in text for line in fixed) for text in [original,before,changed,invalid,recovery_before,recovered])
assert all('spinbutton "物件強度 Object intensity": "0.3"' in text for text in [original,before,recovered])
assert all('spinbutton "物件強度 Object intensity": "0.9"' in text for text in [changed,invalid,recovery_before])
assert "duplicate key 'schema_version'" in invalid and "duplicate key" not in recovered
assert all('heading "已儲存結果 Saved result"' not in text for text in [original,before,changed,invalid,recovered])
files = [root / "browser_fixtures" / part / "same.json" for part in ["original","changed"]]
data = [path.read_bytes() for path in files]
assert len(data[0]) == len(data[1]) and data[0] != data[1]
assert all('generic "same.json, 0.9KB"' in text for text in [before,changed,recovery_before,recovered])
record = {"actual_parent_tab": "1191378028", "same_basename": "same.json",
          "encoded_sizes": list(map(len,data)), "input_sha256": [hashlib.sha256(d).hexdigest() for d in data],
          "file_selection_alone_preserves_editor": True, "same_name_changed_content_explicit_import": "0.3 -> 0.9",
          "invalid_duplicate_key_preserves_canvas_selection_geometry_intensity": True,
          "explicit_valid_reimport_recovers_and_clears_error": True, "no_automatic_generation_or_replay": True,
          "delegated_attempts": "Two dismissed permission requests, no imports; preserved separately",
          "parent_permission": "Normal browser file chooser; user confirmed permission allowed; no settings changed"}
(root / "browser_parent_import_verification.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
print(json.dumps(record,indent=2))
```

### Browser fixture and saved numerical identity

The actual browser submission was the original 8×10 fixture with background
0.125 and ordered disk, rectangle and segment intensities 0.3, 0.6 and 0.45.
Both pitches were 8 μm, wavelength 633 nm, distance 5 mm, N=2 and seed 0;
PSNR used explicit data range 1. The bundle is
`runs/m7/926a9649ca0748d188eb637789d41a0a`, with the separate submitted design
at `runs/designs/submissions/926a9649ca0748d188eb637789d41a0a.json`.
The 11 numerical bundle files contain no fabricated input PNG. Pillow is
therefore null in this array-input bundle's required environment.

The following unedited verification record captures the complete design,
actual saved configuration, source/environment, exact target-byte match and
file hashes. Its source state is honestly dirty at the accepted M6 revision.

```json
{
  "bundle": "C:\\holographiclab\\runs\\m7\\926a9649ca0748d188eb637789d41a0a",
  "snapshot": "C:\\holographiclab\\runs\\designs\\submissions\\926a9649ca0748d188eb637789d41a0a.json",
  "integrity": "passed",
  "shape": [
    8,
    10
  ],
  "dtype": "float64",
  "target_bytes_match_design_raster": true,
  "target_sha256": "e95e2064c70df60aa306bc9c6eb20eeab46df6b1c0551742fff7221c59e33043",
  "design_sha256": "e0c160329b4f28efb8c6c92bb8c13eabd3efb174d0ea9812c752373e41a10f34",
  "design": {
    "background_intensity": 0.125,
    "canvas": {
      "nx": 10,
      "ny": 8
    },
    "coordinate_system": "centered_pixels_y_down_v1",
    "objects": [
      {
        "id": "11111111111111111111111111111111",
        "intensity": 0.3,
        "parameters": {
          "cx_px": 1.0,
          "cy_px": -1.0,
          "radius_px": 2.0
        },
        "type": "disk"
      },
      {
        "id": "22222222222222222222222222222222",
        "intensity": 0.6,
        "parameters": {
          "cx_px": -1.0,
          "cy_px": 0.0,
          "height_px": 2.0,
          "width_px": 3.0
        },
        "type": "rectangle"
      },
      {
        "id": "33333333333333333333333333333333",
        "intensity": 0.45,
        "parameters": {
          "width_px": 1.5,
          "x0_px": -3.0,
          "x1_px": 3.0,
          "y0_px": -2.0,
          "y1_px": 2.0
        },
        "type": "segment"
      }
    ],
    "rasterizer_version": "center_sample_overwrite_v1",
    "schema_version": 1
  },
  "config": {
    "grid": {
      "dx_m": 8e-06,
      "dy_m": 8e-06,
      "nx": 10,
      "ny": 8
    },
    "metrics": {
      "intensity_mse": {},
      "intensity_nmse": {},
      "intensity_psnr": {
        "data_range": 1.0
      }
    },
    "optics": {
      "distance_m": 0.005,
      "wavelength_m": 6.33e-07
    },
    "schema_version": 1,
    "solver": {
      "algorithm": "gerchberg_saxton",
      "contract": "m3_periodic_lossless_asm_v1",
      "initialization": {
        "mode": "seed",
        "seed": 0
      },
      "iterations": 2
    }
  },
  "software": {
    "informational_environment": {
      "cpu_count": 24,
      "python_executable": "C:\\holographiclab\\.venv\\Scripts\\python.exe"
    },
    "ohlab_version": "0.1.0.dev0",
    "required_environment": {
      "byteorder": "little",
      "fft": "numpy.fft",
      "machine": "AMD64",
      "numpy_version": "2.4.6",
      "pillow_version": null,
      "platform": "Windows-10-10.0.26100-SP0",
      "pointer_bits": 64,
      "processor": "Intel64 Family 6 Model 198 Stepping 2, GenuineIntel",
      "python_implementation": "CPython",
      "python_version": "3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]",
      "scipy_version": "1.17.1"
    },
    "source": {
      "method": "git",
      "revision": "cc93c949da23de4a6f98acc0c4954c3c2d7f6849",
      "state": "dirty"
    }
  },
  "bundle_file_hashes": {
    "config.json": "f7134f0c0afd85396abe5653d63c34c739d181d404739cacf57ad9bc0b7c8f1b",
    "manifest.json": "b79919443b70c4a7fa2a07df0ea382870ff61f9b4252487b8d8579300ab95224",
    "metrics.json": "d2cb9f706c1474806808c1bf3d370b75510c8ef227660bf8e77d08516f53d288",
    "phase.npy": "61c69cac8705982b873b94a02d67a7d28299d654473bf0f6b1e70fafeafc622b",
    "reconstruction_field.npy": "399bec5b9c13bf9416f443e46d87a67c68d69f95ad72e6c286ab550431d66edc",
    "reconstruction_intensity.npy": "6170b0e61e87d1aaabe35b062380c2205a72a132a0a9d3edc35d871a322c0fc0",
    "residual_history.npy": "2befc0b8b980c15b840830a4255f1c1d8ccd50f0259065f6792763def6dba555",
    "source_amplitude.npy": "38ce335997e5bfd4e98a4bdb17496523dd2df3adea2524dfe6f2d62fdddc2977",
    "source_field.npy": "d7f392808c870abc4ddcea7725d0f3479ae3e178c4e64075a0392f436ce04134",
    "target_amplitude.npy": "120a77b6112bf44dde5346a3830a49a5a586af73632eb5a3e6c0171f2a161301",
    "target_intensity.npy": "cfb0e12ec001d49638dad67364a576b15a332487f4576545f0345f18ab253aae"
  }
}
```

To reproduce the owned JSON fixtures, save the following captured preparation
script as `runs/m7_acceptance_20260930/prepare_browser_fixtures.py` and run it
with the existing interpreter. Its destination must be absent; do not overwrite
the recorded fixtures. The two same-name files deliberately have equal byte
length but different content. Fixture creation alone does not demonstrate an
import interaction.

```python
from pathlib import Path
import json
from ohlab.target_design import TargetDesign2D
from ohlab.io.designs import design_to_json

root = Path(__file__).parent / 'browser_fixtures'
root.mkdir(exist_ok=False)
spec = {'schema_version': 1, 'rasterizer_version': 'center_sample_overwrite_v1',
        'coordinate_system': 'centered_pixels_y_down_v1', 'canvas': {'ny': 8, 'nx': 10},
        'background_intensity': 0.125, 'objects': [
            {'id': '1'*32, 'type': 'disk', 'parameters': {'cx_px': 1., 'cy_px': -1., 'radius_px': 2.}, 'intensity': .3},
            {'id': '2'*32, 'type': 'rectangle', 'parameters': {'cx_px': -1., 'cy_px': 0., 'width_px': 3., 'height_px': 2.}, 'intensity': .6},
            {'id': '3'*32, 'type': 'segment', 'parameters': {'x0_px': -3., 'y0_px': -2., 'x1_px': 3., 'y1_px': 2., 'width_px': 1.5}, 'intensity': .45}]}
for name, intensity in [('original', .3), ('changed', .9)]:
    folder = root / name
    folder.mkdir()
    spec['objects'][0]['intensity'] = intensity
    (folder/'same.json').write_bytes(design_to_json(TargetDesign2D(spec)))
(root/'invalid.json').write_bytes(b'{"schema_version": 1, "schema_version": 1}')
print(root)
print('Same names and byte lengths:', len((root/'original/same.json').read_bytes()), len((root/'changed/same.json').read_bytes()))
```

The read-only numerical verification script below was run after the actual UI
generation. It writes its requested report outside the bundle; it neither
creates a run nor substitutes for browser interaction.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 runs/m7_acceptance_20260930/verify_browser_bundle.py runs/m7/926a9649ca0748d188eb637789d41a0a --output runs/m7_acceptance_20260930/browser_bundle_verification.json
```

```python
from pathlib import Path
import argparse
import hashlib
import json
from ohlab.io.artifacts import load_run_bundle, verify_run_bundle
from ohlab.io.designs import load_design, design_to_json
from ohlab.target_design import rasterize_target_design

p = argparse.ArgumentParser()
p.add_argument('bundle', type=Path)
p.add_argument('--output', required=True, type=Path)
args = p.parse_args()
bundle = load_run_bundle(args.bundle)
snapshot = Path('runs/designs/submissions')/(args.bundle.name+'.json')
design = load_design(snapshot)
raster = rasterize_target_design(design)
saved = bundle.arrays['target_intensity']
match = raster.shape==saved.shape and raster.dtype==saved.dtype and raster.tobytes(order='C')==saved.tobytes(order='C')
record = {'bundle':str(bundle.path), 'snapshot':str(snapshot.absolute()), 'integrity':verify_run_bundle(args.bundle).status,
          'shape':list(saved.shape), 'dtype':str(saved.dtype), 'target_bytes_match_design_raster':match,
          'target_sha256':hashlib.sha256(saved.tobytes(order='C')).hexdigest(),
          'design_sha256':hashlib.sha256(design_to_json(design)).hexdigest(),
          'design':design.to_dict(), 'config':bundle.config.to_dict(), 'software':bundle.software,
          'bundle_file_hashes': {str(f.relative_to(bundle.path)):hashlib.sha256(f.read_bytes()).hexdigest()
                                for f in bundle.path.rglob('*') if f.is_file()}}
args.output.write_text(json.dumps(record,indent=2)+'\n', encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k not in {'design','software','bundle_file_hashes'}},indent=2))
assert match and record['integrity']=='passed'
```

### Observed rapid/busy event sequence

A process-local observer wrapped the unchanged public submission, design-save
and M5-save calls and Streamlit's received-rerun method. A documented **five
second pause in the accepted callback** exposed the transport window. The
second click was a real Chrome event, not a synthetic call or a claimed
inference from a disabled button. The first submission was accepted at
07:16:54.426718 UTC; the old-nonce browser trigger reached the server while
busy at 07:16:54.655398 UTC and its later callback was rejected at
07:16:59.479355 UTC. The journal then recorded one snapshot and one completed
M5 save, ending at 07:17:00.087504 UTC, with matching submitted/saved target
hashes. These finite observations prove the stated sequence, not durable
exactly-once behavior across crashes, other sessions or all event schedules.

The unedited report is:

```json
{
  "accepted_submissions": 1,
  "rejected_submissions": 1,
  "busy_trigger_requests": 1,
  "snapshot_count": 1,
  "bundle_count": 1,
  "accepted": [
    {
      "accepted": true,
      "accepted_count": 1,
      "busy": true,
      "captured_nonce": "3653eacd9dcc4ca982a0c183826594e3",
      "design_sha256": "e0c160329b4f28efb8c6c92bb8c13eabd3efb174d0ea9812c752373e41a10f34",
      "destination": "C:\\holographiclab\\runs\\m7\\926a9649ca0748d188eb637789d41a0a",
      "event": "submit_result",
      "monotonic_ns": 25870984000000,
      "offered_nonce": "fc275ddfc78c44c39156ad113b297848",
      "target_kind": "designer",
      "thread": "ScriptRunner.scriptThread",
      "utc": "2026-09-30T07:16:54.426718+00:00"
    }
  ],
  "rejected": [
    {
      "accepted": false,
      "accepted_count": 1,
      "busy": true,
      "captured_nonce": "3653eacd9dcc4ca982a0c183826594e3",
      "design_sha256": "e0c160329b4f28efb8c6c92bb8c13eabd3efb174d0ea9812c752373e41a10f34",
      "destination": "C:\\holographiclab\\runs\\m7\\926a9649ca0748d188eb637789d41a0a",
      "event": "submit_result",
      "monotonic_ns": 25876046000000,
      "offered_nonce": "fc275ddfc78c44c39156ad113b297848",
      "target_kind": "designer",
      "thread": "ScriptRunner.scriptThread",
      "utc": "2026-09-30T07:16:59.479355+00:00"
    }
  ],
  "queued_busy": [
    {
      "busy": true,
      "caller": "_handle_rerun_script_request",
      "client_state_present": true,
      "effective_config": {
        "browser.gatherUsageStats": false,
        "runner.fastReruns": false,
        "server.address": "127.0.0.1",
        "server.enableCORS": true,
        "server.enableXsrfProtection": true,
        "server.fileWatcherType": "none",
        "server.port": 8502,
        "server.runOnSave": false
      },
      "event": "rerun_request_received",
      "is_auto_rerun": false,
      "monotonic_ns": 25871218000000,
      "offered_nonce": "fc275ddfc78c44c39156ad113b297848",
      "pending_nonce": "3653eacd9dcc4ca982a0c183826594e3",
      "session_id": "639e5bef-cc60-44e4-a98c-565d625ad67d",
      "thread": "MainThread",
      "triggered_widgets": [
        {
          "id": "$$ID-2815932a0eb9e698b9eae377b65ec38e-generate_3653eacd9dcc4ca982a0c183826594e3",
          "value_kind": "trigger_value"
        }
      ],
      "utc": "2026-09-30T07:16:54.655398+00:00"
    }
  ],
  "instrumentation": "Unchanged application; process-local observer and5second callback pause; actual Chrome double click",
  "numerical_bundle_hashes_unchanged": true,
  "external_snapshot_restored": true
}
```

The exact observer is retained below. The invocation was:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 runs/m7_acceptance_20260930/browser_queued_event_harness.py --pause-seconds 5 --port 8502
```

The journal is `browser-queued-events-35d2fdacb58a47248b869a5d96b8ed56.jsonl`.
This instrumented candidate run is distinct from the required ordinary clean
postcommit app run; it does not claim that later gate has passed.

```python
"""Real unchanged Streamlit app with process-local M7 event observations.

Only root launches this owned loopback server and sends actual browser events.
A documented callback pause exposes the accepted-but-not-disabled transport
window. No synthetic browser event, source edit or successful result is added.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import threading
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pause-seconds", type=float, default=3.0)
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    if not 0.0 < args.pause_seconds <= 10.0:
        parser.error("pause-seconds must be positive and at most10")
    if not 1024 <= args.port <= 65535:
        parser.error("port must be in1024..65535")
    from apps import workbench as wb
    from streamlit import config
    from streamlit.runtime.app_session import AppSession
    from streamlit.web import cli

    log = EVIDENCE / ("browser-queued-events-" + uuid4().hex + ".jsonl")
    with log.open("xb"):
        pass
    lock = threading.Lock()
    counts = {"accepted": 0, "snapshot_started": 0, "snapshot_completed": 0,
              "save_started": 0, "save_completed": 0}

    def record(event, **details):
        item = {"event": event, "utc": datetime.now(timezone.utc).isoformat(),
                "monotonic_ns": time.monotonic_ns(), "thread": threading.current_thread().name, **details}
        with lock, log.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()

    original_submit = wb.submit_generate
    def observed_submit(state, draft, *, offered_nonce, runs_root):
        record("submit_attempt", captured_nonce=offered_nonce, target_kind=draft.target_kind,
               offered_nonce=state.offered_nonce, busy=state.busy, pending=state.pending is not None)
        accepted = original_submit(state, draft, offered_nonce=offered_nonce, runs_root=runs_root)
        if accepted:
            counts["accepted"] += 1
        record("submit_result", captured_nonce=offered_nonce, accepted=accepted,
               offered_nonce=state.offered_nonce, busy=state.busy, target_kind=draft.target_kind,
               destination=None if state.pending is None else str(state.pending.destination),
               design_sha256=None if state.pending is None else state.pending.design_sha256,
               accepted_count=counts["accepted"])
        if accepted:
            record("controlled_callback_pause_start", busy=state.busy, consumed_nonce=offered_nonce, seconds=args.pause_seconds)
            time.sleep(args.pause_seconds)
            record("controlled_callback_pause_end", busy=state.busy, consumed_nonce=offered_nonce)
        return accepted
    wb.submit_generate = observed_submit

    original_snapshot = wb.save_design
    def observed_snapshot(path, *, design):
        counts["snapshot_started"] += 1
        record("snapshot_started", path=str(path), count=counts["snapshot_started"])
        try:
            result = original_snapshot(path, design=design)
        except BaseException as exc:
            record("snapshot_failed", path=str(path), exception_type=type(exc).__name__, message=str(exc))
            raise
        counts["snapshot_completed"] += 1
        record("snapshot_completed", path=str(result), count=counts["snapshot_completed"],
               sha256=hashlib.sha256(Path(result).read_bytes()).hexdigest())
        return result
    wb.save_design = observed_snapshot

    original_save = wb.run_and_save_bundle
    def observed_save(path, **kwargs):
        target = kwargs["target_intensity"]
        target_hash = hashlib.sha256(target.tobytes(order="C")).hexdigest()
        counts["save_started"] += 1
        input_png = kwargs.get("input_png")
        record("save_started", path=str(path), count=counts["save_started"], input_png=None if input_png is None else str(input_png),
               target_shape=list(target.shape), target_dtype=target.dtype.str, target_sha256=target_hash)
        try:
            bundle = original_save(path, **kwargs)
        except BaseException as exc:
            record("save_failed", path=str(path), exception_type=type(exc).__name__, message=str(exc))
            raise
        counts["save_completed"] += 1
        saved = bundle.arrays["target_intensity"]
        record("save_completed", path=str(bundle.path), count=counts["save_completed"],
               manifest_exists=(bundle.path / "manifest.json").is_file(),
               saved_target_sha256=hashlib.sha256(saved.tobytes(order="C")).hexdigest())
        return bundle
    wb.run_and_save_bundle = observed_save

    original_rerun = AppSession.request_rerun
    def observed_rerun(self, client_state):
        try:
            state = self._session_state["workbench"]
        except KeyError:
            state = None
        triggers = []
        if client_state is not None:
            for widget in client_state.widget_states.widgets:
                if widget.WhichOneof("value") == "trigger_value" and widget.trigger_value:
                    triggers.append({"id": widget.id, "value_kind": "trigger_value"})
        record("rerun_request_received", session_id=self.id, caller=sys._getframe(1).f_code.co_name,
               client_state_present=client_state is not None,
               is_auto_rerun=None if client_state is None else client_state.is_auto_rerun,
               busy=None if state is None else state.busy,
               offered_nonce=None if state is None else state.offered_nonce,
               pending_nonce=None if state is None or state.pending is None else state.pending.token,
               triggered_widgets=triggers,
               effective_config={name: config.get_option(name) for name in (
                   "server.address", "server.port", "server.enableCORS", "server.enableXsrfProtection",
                   "server.runOnSave", "server.fileWatcherType", "runner.fastReruns", "browser.gatherUsageStats")})
        return original_rerun(self, client_state)
    AppSession.request_rerun = observed_rerun

    record("harness_started", app=str(ROOT / "apps" / "streamlit_app.py"), pause_seconds=args.pause_seconds,
           instrumentation="process-local observers and callback pause; actual browser events only")
    print("BROWSER_EVENT_LOG " + str(log), flush=True)
    cli.main(args=["run", str(ROOT / "apps" / "streamlit_app.py"),
                   "--server.address=127.0.0.1", f"--server.port={args.port}", "--server.headless=true",
                   "--server.enableCORS=true", "--server.enableXsrfProtection=true", "--server.runOnSave=false",
                   "--server.fileWatcherType=none", "--runner.fastReruns=false", "--browser.gatherUsageStats=false"],
             prog_name="streamlit")


if __name__ == "__main__":
    main()
```

### Genuine captured viewports

Both figures were visually reviewed and are actual normal Chrome viewports,
1707×889 pixels. The browser tool supplied JPEG pixels; they were decoded and
saved as PNG with identical decoded pixels, without resizing, cropping,
compositing, annotation, zoom change or viewport override.

- [Designer preview](figures/fig01_designer_preview.png): the original 8×10
  desired raster before generation, disk intensity 0.3, background 0.125 and
  the editable-copy path.
- [Saved result](figures/fig02_designer_saved_result.png): the original saved
  target with maximum 0.6 remains displayed while the rectangle draft is 0.4
  and the previous-submission warning is visible.

A viewport captures only what is visible; numerical correctness, complete
history and interactions are established separately by the recorded tests,
DOM captures and bundle verification. These are not optical correctness proofs.
The exact capture metadata is:

```json
[
  {
    "source": "preview-final-native-capture",
    "destination": "docs\\handoffs\\milestone_7\\figures\\fig01_designer_preview.png",
    "size": [
      1707,
      889
    ],
    "original_sha256": "c5d0a2c87a78077862ebbbde6ec7e19cbcfa9ffeed55bce50713e21dc5ba9667",
    "png_sha256": "2a84d6d8d6f88920520cdb9c9d59e1f7f926ac15f3fe84da4e1558be202a4b31",
    "operation": "Native browser JPEG decoded then PNG saved; identical decoded pixels; no resize/crop/composite/annotation",
    "viewport": "Normal Chrome viewport; no viewport override or zoom change"
  },
  {
    "source": "saved-result-final-native-capture",
    "destination": "docs\\handoffs\\milestone_7\\figures\\fig02_designer_saved_result.png",
    "size": [
      1707,
      889
    ],
    "original_sha256": "e2c0a13e70d2cd94d71001e63a99d63666dd1c90f80fe9326f52b0efc48930ed",
    "png_sha256": "483abb0b63870e6f8346c8b20efb4ef38c5bc59a7aaf0308fbead0daf391a8d6",
    "operation": "Native browser JPEG decoded then PNG saved; identical decoded pixels; no resize/crop/composite/annotation",
    "viewport": "Normal Chrome viewport; no viewport override or zoom change"
  }
]
```

The file-transfer/chooser tooling experienced long calls (reported
215/303/1330/715 seconds). A deliberately short 10-second wait-only attempt
timed out; resetting browser control recovered a fresh Chrome session. The
cause was not established, and this is not evidence of a numerical or app
failure. At the recorded checkpoint, server stderr contained its startup
message. No broader claim of an error-free host or future session is made.

## Scope and environment check — completed

The recorded candidate inventory contains exactly the 24 approved paths,
with no missing or extra path. All 125 protected files from the 131-file
baseline match their recorded hashes; all 53 installed distribution records
are unchanged. This check is separate from the later staged-index and clean
publication checks. The exact report is:

```json
{
  "allowed_count": 24,
  "protected_count": 125,
  "changed_protected": [],
  "environment_unchanged": true,
  "distribution_count": 53,
  "changed_paths": [
    "README.md",
    "apps/designer.py",
    "apps/presentation.py",
    "apps/streamlit_app.py",
    "apps/workbench.py",
    "docs/handoffs/milestone_7/code_map.md",
    "docs/handoffs/milestone_7/figures/fig01_designer_preview.png",
    "docs/handoffs/milestone_7/figures/fig02_designer_saved_result.png",
    "docs/handoffs/milestone_7/implementation_summary.md",
    "docs/handoffs/milestone_7/known_limitations.md",
    "docs/handoffs/milestone_7/math_used.md",
    "docs/handoffs/milestone_7/tests_and_evidence.md",
    "docs/handoffs/milestone_7/tutor_context.md",
    "docs/math_conventions.md",
    "docs/milestones.md",
    "docs/roadmap.md",
    "examples/design_target.py",
    "src/ohlab/io/designs.py",
    "src/ohlab/target_design.py",
    "tests/test_design_io.py",
    "tests/test_designer_architecture.py",
    "tests/test_designer_controller.py",
    "tests/test_designer_streamlit.py",
    "tests/test_target_design.py"
  ],
  "outside_allowlist": [],
  "missing_allowed": []
}
```

## Publication gate — pending after completed precommit acceptance

The approved commit is `feat(m7): add 2D target designer`. Candidate source
remains honestly dirty/unqualified; precommit strict replay can remain
`not_run`, and explicit diagnostic comparison never upgrades qualification.
After the single milestone commit, restart the ordinary app from the clean
checkout. Through the real UI, make a fresh small Designer run, compare its
saved target to the submitted design by shape/dtype/C-order bytes and require
strict **passed / qualified / passed** with diagnostics off. Demonstrate replay
independence from external design storage using only owned disposable data.

Actual postcommit captures and completion details remain in ignored evidence
and the final report, avoiding self-referential documentation commits. A
failed required gate stops the push. Normal push then requires matching local,
live-remote and GitHub API SHAs, a clean working tree and cleanup of only
task-owned browser/server processes. No later milestone begins.
