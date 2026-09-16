# Milestone 2 — Tests and evidence

Current implementation evidence, **2026-09-16**, from accepted baseline
`157d1d6c9f5c433671a62da9b60512c8f007298b`. Older M0/M1 evidence is preserved
in its original documents; this record does not replace historical numbers.

## Environment and starting state

Before implementation: clean `main`, upstream `origin/main`, ahead/behind
`0/0`. HEAD, origin/main and live `git ls-remote` main all matched the
accepted baseline. SHA-256 values for all 56 pre-existing tracked files were
captured before editing.

| Component | Actually used |
|---|---|
| Interpreter | `C:\holographiclab\.venv\Scripts\python.exe` |
| Python | 3.11.9 |
| Platform | Windows-10-10.0.26100-SP0 |
| NumPy | 2.4.6 |
| SciPy | 1.17.1 |
| pytest | 9.1.1 |
| Pillow | 12.3.0 |
| matplotlib | 3.11.1 |

No dependencies were installed/upgraded, no environment was rebuilt and no
global Git settings were changed. `images = ["pillow>=10.0"]` is a source
declaration; only the installed version above was tested. Installed editable
distribution metadata was not regenerated.

All commands below run from `C:\holographiclab` with the existing interpreter.
No bytecode or pytest cache provider is needed. File-based pytest fixtures use
a fresh ignored directory under `.pytest_cache` because the default
`C:\Users\jimli\AppData\Local\Temp\pytest-of-jimli` root denied access.

## Baseline and final full suite

Baseline command, exit 0:

~~~powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
~~~

Unedited output:

~~~text
........................................................................ [ 22%]
........................................................................ [ 44%]
........................................................................ [ 66%]
........................................................................ [ 89%]
...................................                                      [100%]
323 passed in 2.24s
~~~

Final full-suite command, after isolated negative controls were restored,
explicit image-buffer closing was strengthened and metadata presence was
verified with separate ICC/sRGB fixtures, exit 0:

~~~powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --basetemp .pytest_cache/m2-full-20260916-b
~~~

Unedited output:

~~~text
........................................................................ [ 14%]
........................................................................ [ 29%]
........................................................................ [ 43%]
........................................................................ [ 58%]
........................................................................ [ 73%]
........................................................................ [ 87%]
...........................................................              [100%]
491 passed in 3.65s
~~~

The actual increase is **168 cases**, with no test-count quota:

| Coverage | Cases |
|---|---:|
| Accepted pre-M2 baseline, retained | 323 |
| `tests/test_targets.py` | 70 new |
| `tests/test_images.py` | 47 new |
| New C06/C07 guard cases in `tests/test_fft_conventions.py` | 51 new |
| Final suite | 491 |

All old test files outside the allowlist are byte-identical. AST comparison
of the 16 pre-existing functions in `test_fft_conventions.py` found only the
approved C06 body change; the C07 body, C08 export assertion, numerical tests,
decorators and numerical helper functions are unchanged. C06 still runs as
part of the retained baseline coverage, now with the approved narrow exception.

During development, the first guard-focused run had 68 passes and 9 setup
errors due to the default temp-root permissions. A fresh local `--basetemp`
resolved that environment issue; the final focused guard run had 78 passes
in 0.18 s. One initial image-import test expected `ModuleNotFoundError` for
a blocked Pillow extension, but Python's `from` import presented an
`ImportError`. The test was corrected to retain the extension-specific
diagnosis and forbid relabeling it as a missing extra; the loader was already
preserving that error. No numerical threshold was loosened. Final image-only
coverage passed 47 cases, and the later full suite includes the strengthened
explicit-close assertions. Review also found that Pillow omits an sRGB chunk
when an ICC profile is saved alongside it. The metadata test now uses separate
ICC and sRGB fixtures and asserts that the claimed tags are present before
comparing all returned rasters. This kept the test count unchanged.

## Acceptance-to-test map

| Property | Main regression evidence |
|---|---|
| Fixed /255, endpoints and lowest code | T01; `test_image_known_pixels_intensity_and_amplitude`, `test_image_all_256_code_values` |
| All 256 codes against independent high precision | T02 |
| Intensity versus amplitude | T03 |
| Cross-image brightness | T04; `test_image_brightness_not_normalized_per_image` |
| Rectangular/mixed-parity orientation and grid preservation | T05; `test_image_orientation_grid_and_source_unchanged` |
| Supplied normalized floats and zero target | T06/T07; `test_image_blank_is_valid_zero` |
| C layout, writability, nonmutation, ownership, determinism | T08/T09; image orientation/repeat-call tests |
| Type/dtype/native byte order/subclass/shape/range/finiteness | T10–T17; image path/grid/size tests |
| Content versus filename extension | `test_image_content_not_suffix`; disguised non-PNG tests |
| Bit-depth/color rejection | low-bit source tests; RGB/RGBA/LA/P/I;16 PNG cases; L/F TIFF cases |
| Metadata cannot transform target | presence-checked gamma/EXIF/DPI/ICC and separate sRGB rasters compared with identical plain raster |
| Transparency and both APNG cases | three dedicated rejection tests, including decodable single-frame APNG |
| Declared size before payload read/decoder invocation | header-only spy forbids any later read or Pillow open on mismatch |
| Retained decoded-array shape check | patched decoder-array boundary presents a wrong final shape |
| Verification versus actual pixel decoding | bad IDAT CRC; separately, CRC-valid invalid zlib data passes `verify()` then fails `load()` |
| Filesystem exceptions retained | real absent/directory paths and injected read failure preserve original type/object |
| Resources close on success/failure | tracked file/stream closure and explicit image `close()` calls; Windows unlink |
| Decoder protections retained | existing MAX_IMAGE_PIXELS error and unchanged LOAD_TRUNCATED_IMAGES settings |
| Optional import isolation | fresh subprocesses block PIL and PIL._imaging before core imports and loader use |
| Narrow C06 + unchanged RNG guard | permitted/forbidden path, absolute/relative/alias/nested forms, all other forbidden roots, actual C07 snippet cases |

The 1-frame APNG fixture is integrity-verified and fully decoded independently
before testing rejection; it has `n_frames == 1` and `is_animated == False`.
The malformed-pixel fixture is readable and passes CRC verification before
triggering a chained pixel-decoding error. These tests exercise specific
documented behavior, not every possible malformed PNG.

The subprocesses demonstrate that root/core/targets and even the loader module
can be imported before Pillow is needed. They do not uninstall packages,
refresh editable metadata or establish all-version compatibility.

## Numerical measurement

Independent references use exact integer/255 ratios and 80-digit Decimal
square roots, never either production converter. Reference tolerances are
`rtol=2e-15, atol=0`; the square relation uses `rtol=5e-15, atol=0`.
Black endpoints are exact, and nonzero encoded intensity is at least `1/255`.
These bounds describe the code sweep and the supplied normalized test cases,
not an exhaustive study of every float64 value.

Exact PowerShell probe, exit 0:

~~~powershell
@'
from decimal import Decimal, localcontext
import numpy as np
from ohlab.grid import SamplingGrid
from ohlab.targets import grayscale8_to_intensity, intensity_to_amplitude
grid = SamplingGrid(ny=16, nx=16, dy=5e-6, dx=3.74e-6)
codes = np.arange(256, dtype=np.uint8).reshape(grid.shape)
with localcontext() as context:
    context.prec = 80
    ratios = [Decimal(int(code)) / Decimal(255) for code in codes.flat]
    ref_i = np.array([float(value) for value in ratios]).reshape(grid.shape)
    ref_a = np.array([float(value.sqrt()) for value in ratios]).reshape(grid.shape)
intensity = grayscale8_to_intensity(codes, grid=grid)
amplitude = intensity_to_amplitude(intensity, grid=grid)
for name, actual, expected in [
    ("intensity vs Decimal g/255", intensity, ref_i),
    ("amplitude vs Decimal sqrt(g/255)", amplitude, ref_a),
    ("amplitude squared vs intensity", amplitude**2, intensity),
]:
    error = np.abs(actual - expected)
    nonzero = expected != 0
    print(f"{name}: max_abs={error.max():.17g}, max_rel_nonzero={(error[nonzero] / np.abs(expected[nonzero])).max():.17g}")
for code in (128, 1):
    print(f"g={code}: I={intensity.flat[code]:.17g}, A={amplitude.flat[code]:.17g}")
print("outputs C-contiguous/native-float64/writeable:",
      all(a.flags.c_contiguous and a.dtype == np.dtype(np.float64) and a.dtype.isnative and a.flags.writeable for a in (intensity, amplitude)))

'@ | & .\.venv\Scripts\python.exe -B -X utf8 -
~~~

Unedited output:

~~~text
intensity vs Decimal g/255: max_abs=0, max_rel_nonzero=0
amplitude vs Decimal sqrt(g/255): max_abs=1.1102230246251565e-16, max_rel_nonzero=2.1499376424746289e-16
amplitude squared vs intensity: max_abs=1.1102230246251565e-16, max_rel_nonzero=2.211772431870429e-16
g=128: I=0.50196078431372548, A=0.70849190843207621
g=1: I=0.0039215686274509803, A=0.062622429108514954
outputs C-contiguous/native-float64/writeable: True
~~~

## Targeted negative controls

Each mutation ran in a fresh subprocess against actual pytest cases. The
driver changed functions or source text only in memory; it never wrote a
mutated production/test file. A `finally` block restored monkeypatches and
process exit removed the mutated state. SHA-256 inventories of all 29
source/test files were identical before and after. The subsequent explicit
image-close and metadata-fixture improvements were intentional final changes,
not leftover mutations; the final full-suite output above includes both.

| Mutation | Expected failure observed |
|---|---|
| Divide by per-image peak instead of 255 | T04: 1 call failure |
| Omit square root | T03: 1 call failure |
| Return transposed amplitude | T05: 4 call failures |
| Remove bit-depth/color check, leaving decoded-mode validation | 2-bit and 4-bit sources: 2 call failures; 1-bit case deselected intentionally |
| Supply core field source with `from . import io` appended | Actual C06 scan: 1 call failure |

All five mutated pytest runs exited 1, with no setup/teardown errors. The
verification driver returned 0 only because the intended failures were
observed. This finite set demonstrates detection of these mutations and
does not establish zero possible test gaps.

For reproduction, copy the complete driver below to
`.pytest_cache/m2-negative-controls-20260916/driver.py` (create that ignored
directory if needed), then run:

~~~powershell
.\.venv\Scripts\python.exe -B -X utf8 .pytest_cache/m2-negative-controls-20260916/driver.py
~~~

The parent captures raw child outputs and before/after hash inventories only
inside that ignored directory. Rerun the normal full suite afterward.

~~~python
"""Reproduce five isolated, in-memory M2 negative controls; never edit source.

Run from C:\\holographiclab with its existing interpreter:
  .\\.venv\\Scripts\\python.exe -B -X utf8 .pytest_cache/m2-negative-controls-20260916/driver.py
Each child process injects one mutation after pytest collection. Its exit ends
the mutated state; parent-side hashes cover every src/ and tests/ file.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import textwrap


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(__file__).resolve().parent
CASES = {
    "peak_normalization": (
        "tests/test_targets.py::test_t04_brightness_is_preserved_across_targets", 1
    ),
    "omit_square_root": (
        "tests/test_targets.py::test_t03_midgray_is_intensity_not_amplitude", 1
    ),
    "transpose_output": (
        "tests/test_targets.py::test_t05_rectangular_mixed_parity_orientation", 4
    ),
    "decoded_mode_only": (
        "tests/test_images.py::test_image_rejects_low_bit_source_even_when_decoded_as_l", 2
    ),
    "core_imports_io": (
        "tests/test_fft_conventions.py::test_c06_numerical_core_imports_no_ui_or_io_library", 1
    ),
}


def hashes() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for directory in (ROOT / "src", ROOT / "tests")
        for path in sorted(directory.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def child(case: str) -> int:
    import pytest

    class Mutation:
        def __init__(self) -> None:
            self.patch = pytest.MonkeyPatch()
            self.reports = []

        def replace_function(self, module, name: str, old: str, new: str, tests) -> None:
            original = getattr(module, name)
            source = textwrap.dedent(inspect.getsource(original))
            assert source.count(old) == 1, f"mutation site is not unique: {old!r}"
            changed = source.replace(old, new, 1)
            namespace = {}
            exec(compile(changed, f"<in-memory:{case}:{name}>", "exec"), module.__dict__, namespace)
            mutant = namespace[name]
            self.patch.setattr(module, name, mutant)
            for test_module in tests:
                if getattr(test_module, name, None) is original:
                    self.patch.setattr(test_module, name, mutant)
            print(f"MUTATION {module.__name__}.{name}: {old!r} -> {new!r}", flush=True)

        def pytest_collection_modifyitems(self, config, items) -> None:
            tests = {item.module for item in items}
            if case in ("peak_normalization", "omit_square_root", "transpose_output"):
                from ohlab import targets
                if case == "peak_normalization":
                    self.replace_function(targets, "grayscale8_to_intensity",
                                          "intensity /= 255.0", "intensity /= np.max(intensity)", tests)
                elif case == "omit_square_root":
                    self.replace_function(targets, "intensity_to_amplitude",
                                          "np.sqrt(amplitude, out=amplitude)", "# omitted square root", tests)
                else:
                    self.replace_function(targets, "intensity_to_amplitude",
                                          "return amplitude", 'return amplitude.T.copy(order="C")', tests)
            elif case == "decoded_mode_only":
                from ohlab.io import images
                deselected = [item for item in items if item.callspec.params["bits"] not in (2, 4)]
                items[:] = [item for item in items if item.callspec.params["bits"] in (2, 4)]
                config.hook.pytest_deselected(items=deselected)
                self.replace_function(images, "_validate_header",
                                      "if bit_depth != 8 or color_type != 0:", "if False:", tests)
            else:
                field_path = (ROOT / "src/ohlab/field.py").resolve()
                original_read_text = Path.read_text

                def read_injected_source(path, *args, **kwargs):
                    source = original_read_text(path, *args, **kwargs)
                    if path.resolve() == field_path:
                        return source + "\nfrom . import io\n"
                    return source

                self.patch.setattr(Path, "read_text", read_injected_source)
                print("MUTATION field.py source supplied to actual C06: appended 'from . import io' in memory", flush=True)

        def pytest_runtest_logreport(self, report) -> None:
            self.reports.append(report)

    plugin = Mutation()
    selector, expected_failures = CASES[case]
    args = ["-q", "--tb=short", "-p", "no:cacheprovider", "--basetemp",
            str(EVIDENCE / f"temp-{case}"), selector]
    print("PYTEST ARGS " + json.dumps(args), flush=True)
    try:
        result = int(pytest.main(args, plugins=[plugin]))
    finally:
        plugin.patch.undo()
    call_failures = [report for report in plugin.reports if report.when == "call" and report.failed]
    other_failures = [report for report in plugin.reports if report.when != "call" and report.failed]
    proven = result == 1 and len(call_failures) == expected_failures and not other_failures
    print(f"NEGATIVE CONTROL VERIFIED: {proven}; pytest exit={result}; "
          f"call failures={len(call_failures)}; setup/teardown failures={len(other_failures)}", flush=True)
    return 0 if proven else 1


def parent() -> int:
    before = hashes()
    (EVIDENCE / "hashes-before.json").write_text(json.dumps(before, indent=2) + "\n", encoding="utf-8")
    transcript = []
    success = True
    for case in CASES:
        command = [sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()), "--case", case]
        transcript.append("COMMAND\n" + subprocess.list2cmdline(command) + "\n")
        completed = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, encoding="utf-8")
        (EVIDENCE / f"{case}.txt").write_text(completed.stdout, encoding="utf-8")
        transcript.append(completed.stdout)
        transcript.append(f"DRIVER CHILD EXIT: {completed.returncode}\n\n")
        print(f"{case}: verification driver exit {completed.returncode}", flush=True)
        success = success and completed.returncode == 0
    after = hashes()
    (EVIDENCE / "hashes-after.json").write_text(json.dumps(after, indent=2) + "\n", encoding="utf-8")
    unchanged = before == after
    result = f"SOURCE/TEST HASHES UNCHANGED: {unchanged}; files={len(before)}\n"
    transcript.append(result)
    (EVIDENCE / "transcript.txt").write_text("".join(transcript), encoding="utf-8")
    print(result, end="", flush=True)
    return 0 if success and unchanged else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=CASES)
    selected = parser.parse_args().case
    raise SystemExit(child(selected) if selected else parent())
~~~

Complete unedited child-command/pytest transcript:

~~~text
COMMAND
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 C:\holographiclab\.pytest_cache\m2-negative-controls-20260916\driver.py --case peak_normalization
PYTEST ARGS ["-q", "--tb=short", "-p", "no:cacheprovider", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m2-negative-controls-20260916\\temp-peak_normalization", "tests/test_targets.py::test_t04_brightness_is_preserved_across_targets"]
MUTATION ohlab.targets.grayscale8_to_intensity: 'intensity /= 255.0' -> 'intensity /= np.max(intensity)'
F                                                                        [100%]
================================== FAILURES ===================================
_______________ test_t04_brightness_is_preserved_across_targets _______________
tests\test_targets.py:106: in test_t04_brightness_is_preserved_across_targets
    np.testing.assert_allclose(dim_intensity, 64 / 255, rtol=2e-15, atol=0.0)
E   AssertionError: 
E   Not equal to tolerance rtol=2e-15, atol=0
E   
E   Mismatched elements: 6 / 6 (100%)
E   First 5 mismatches are at indices:
E    [0, 0]: 1.0 (ACTUAL), 0.25098039215686274 (DESIRED)
E    [0, 1]: 1.0 (ACTUAL), 0.25098039215686274 (DESIRED)
E    [0, 2]: 1.0 (ACTUAL), 0.25098039215686274 (DESIRED)
E    [1, 0]: 1.0 (ACTUAL), 0.25098039215686274 (DESIRED)
E    [1, 1]: 1.0 (ACTUAL), 0.25098039215686274 (DESIRED)
E   Max absolute difference among violations: 0.74901961
E   Max relative difference among violations: 2.984375
E    ACTUAL: array([[1., 1., 1.],
E          [1., 1., 1.]])
E    DESIRED: array(0.25098)
=========================== short test summary info ===========================
FAILED tests/test_targets.py::test_t04_brightness_is_preserved_across_targets
1 failed in 0.17s
NEGATIVE CONTROL VERIFIED: True; pytest exit=1; call failures=1; setup/teardown failures=0
DRIVER CHILD EXIT: 0

COMMAND
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 C:\holographiclab\.pytest_cache\m2-negative-controls-20260916\driver.py --case omit_square_root
PYTEST ARGS ["-q", "--tb=short", "-p", "no:cacheprovider", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m2-negative-controls-20260916\\temp-omit_square_root", "tests/test_targets.py::test_t03_midgray_is_intensity_not_amplitude"]
MUTATION ohlab.targets.intensity_to_amplitude: 'np.sqrt(amplitude, out=amplitude)' -> '# omitted square root'
F                                                                        [100%]
================================== FAILURES ===================================
_________________ test_t03_midgray_is_intensity_not_amplitude _________________
tests\test_targets.py:93: in test_t03_midgray_is_intensity_not_amplitude
    np.testing.assert_allclose(
E   AssertionError: 
E   Not equal to tolerance rtol=2e-15, atol=0
E   
E   Mismatched elements: 6 / 6 (100%)
E   First 5 mismatches are at indices:
E    [0, 0]: 0.5019607843137255 (ACTUAL), 0.7084919084320762 (DESIRED)
E    [0, 1]: 0.5019607843137255 (ACTUAL), 0.7084919084320762 (DESIRED)
E    [0, 2]: 0.5019607843137255 (ACTUAL), 0.7084919084320762 (DESIRED)
E    [1, 0]: 0.5019607843137255 (ACTUAL), 0.7084919084320762 (DESIRED)
E    [1, 1]: 0.5019607843137255 (ACTUAL), 0.7084919084320762 (DESIRED)
E   Max absolute difference among violations: 0.20653112
E   Max relative difference among violations: 0.29150809
E    ACTUAL: array([[0.501961, 0.501961, 0.501961],
E          [0.501961, 0.501961, 0.501961]])
E    DESIRED: array([[0.708492, 0.708492, 0.708492],
E          [0.708492, 0.708492, 0.708492]])
=========================== short test summary info ===========================
FAILED tests/test_targets.py::test_t03_midgray_is_intensity_not_amplitude - A...
1 failed in 0.22s
NEGATIVE CONTROL VERIFIED: True; pytest exit=1; call failures=1; setup/teardown failures=0
DRIVER CHILD EXIT: 0

COMMAND
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 C:\holographiclab\.pytest_cache\m2-negative-controls-20260916\driver.py --case transpose_output
PYTEST ARGS ["-q", "--tb=short", "-p", "no:cacheprovider", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m2-negative-controls-20260916\\temp-transpose_output", "tests/test_targets.py::test_t05_rectangular_mixed_parity_orientation"]
MUTATION ohlab.targets.intensity_to_amplitude: 'return amplitude' -> 'return amplitude.T.copy(order="C")'
FFFF                                                                     [100%]
================================== FAILURES ===================================
____________ test_t05_rectangular_mixed_parity_orientation[shape0] ____________
tests\test_targets.py:121: in test_t05_rectangular_mixed_parity_orientation
    assert intensity.shape == amplitude.shape == shape
E   assert (2, 3) == (3, 2)
E     
E     At index 0 diff: 2 != 3
E     Use -v to get more diff
____________ test_t05_rectangular_mixed_parity_orientation[shape1] ____________
tests\test_targets.py:121: in test_t05_rectangular_mixed_parity_orientation
    assert intensity.shape == amplitude.shape == shape
E   assert (3, 2) == (2, 3)
E     
E     At index 0 diff: 3 != 2
E     Use -v to get more diff
____________ test_t05_rectangular_mixed_parity_orientation[shape2] ____________
tests\test_targets.py:121: in test_t05_rectangular_mixed_parity_orientation
    assert intensity.shape == amplitude.shape == shape
E   assert (3, 4) == (4, 3)
E     
E     At index 0 diff: 3 != 4
E     Use -v to get more diff
____________ test_t05_rectangular_mixed_parity_orientation[shape3] ____________
tests\test_targets.py:121: in test_t05_rectangular_mixed_parity_orientation
    assert intensity.shape == amplitude.shape == shape
E   assert (4, 3) == (3, 4)
E     
E     At index 0 diff: 4 != 3
E     Use -v to get more diff
=========================== short test summary info ===========================
FAILED tests/test_targets.py::test_t05_rectangular_mixed_parity_orientation[shape0]
FAILED tests/test_targets.py::test_t05_rectangular_mixed_parity_orientation[shape1]
FAILED tests/test_targets.py::test_t05_rectangular_mixed_parity_orientation[shape2]
FAILED tests/test_targets.py::test_t05_rectangular_mixed_parity_orientation[shape3]
4 failed in 0.24s
NEGATIVE CONTROL VERIFIED: True; pytest exit=1; call failures=4; setup/teardown failures=0
DRIVER CHILD EXIT: 0

COMMAND
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 C:\holographiclab\.pytest_cache\m2-negative-controls-20260916\driver.py --case decoded_mode_only
PYTEST ARGS ["-q", "--tb=short", "-p", "no:cacheprovider", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m2-negative-controls-20260916\\temp-decoded_mode_only", "tests/test_images.py::test_image_rejects_low_bit_source_even_when_decoded_as_l"]
MUTATION ohlab.io.images._validate_header: 'if bit_depth != 8 or color_type != 0:' -> 'if False:'
FF                                                                       [100%]
================================== FAILURES ===================================
______ test_image_rejects_low_bit_source_even_when_decoded_as_l[2-\x1b] _______
tests\test_images.py:170: in test_image_rejects_low_bit_source_even_when_decoded_as_l
    with pytest.raises(ValueError, match="bit depth 8"):
E   Failed: DID NOT RAISE ValueError
____ test_image_rejects_low_bit_source_even_when_decoded_as_l[4-\x05\xaf] _____
tests\test_images.py:170: in test_image_rejects_low_bit_source_even_when_decoded_as_l
    with pytest.raises(ValueError, match="bit depth 8"):
E   Failed: DID NOT RAISE ValueError
=========================== short test summary info ===========================
FAILED tests/test_images.py::test_image_rejects_low_bit_source_even_when_decoded_as_l[2-\x1b]
FAILED tests/test_images.py::test_image_rejects_low_bit_source_even_when_decoded_as_l[4-\x05\xaf]
2 failed, 1 deselected in 0.23s
NEGATIVE CONTROL VERIFIED: True; pytest exit=1; call failures=2; setup/teardown failures=0
DRIVER CHILD EXIT: 0

COMMAND
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 C:\holographiclab\.pytest_cache\m2-negative-controls-20260916\driver.py --case core_imports_io
PYTEST ARGS ["-q", "--tb=short", "-p", "no:cacheprovider", "--basetemp", "C:\\holographiclab\\.pytest_cache\\m2-negative-controls-20260916\\temp-core_imports_io", "tests/test_fft_conventions.py::test_c06_numerical_core_imports_no_ui_or_io_library"]
MUTATION field.py source supplied to actual C06: appended 'from . import io' in memory
F                                                                        [100%]
================================== FAILURES ===================================
_____________ test_c06_numerical_core_imports_no_ui_or_io_library _____________
tests\test_fft_conventions.py:325: in test_c06_numerical_core_imports_no_ui_or_io_library
    _assert_import_boundaries(
tests\test_fft_conventions.py:104: in _assert_import_boundaries
    assert in_io or not imports_io, (
E   AssertionError: field.py imports I/O module 'ohlab.io' into the numerical core
E   assert (False or not True)
=========================== short test summary info ===========================
FAILED tests/test_fft_conventions.py::test_c06_numerical_core_imports_no_ui_or_io_library
1 failed in 0.18s
NEGATIVE CONTROL VERIFIED: True; pytest exit=1; call failures=1; setup/teardown failures=0
DRIVER CHILD EXIT: 0

SOURCE/TEST HASHES UNCHANGED: True; files=29
~~~

## Demo and figure regeneration

Default headless demo, exit 0:

~~~powershell
.\.venv\Scripts\python.exe -B examples/load_target.py --no-show
~~~

Unedited output:

~~~text
source: deterministic synthetic 8-bit grayscale PNG
grid: shape=(5, 8), dx=3.74e-06 m, dy=5e-06 m
intensity: float64, range=[0, 1]
amplitude: float64, range=[0, 1]
max |A_target**2 - I_target|: 5.55111512312578270e-17
relation check: passed (rtol=1e-14, atol=1e-15)
Target phase remains unspecified; these outputs are intensity and amplitude.
~~~

The explicit-path route was also exercised with a temporary 3-by-5 grayscale
PNG and arguments `--input <temporary PNG> --ny 3 --nx 5 --dx-m 4e-6
--dy-m 7e-6 --no-show`; residual `5.55111512312578270e-17`, exit 0.
The placeholder denotes a runtime temporary path, not a committed input file.
The default command without `--no-show` opens the figure; interactive GUI
and VS Code execution were not separately automated.

Figure command, exit 0:

~~~powershell
.\.venv\Scripts\python.exe -B scripts/make_m2_figures.py
~~~

Unedited output from final regeneration:

~~~text
wrote docs/handoffs/milestone_2/figures/fig01_code_intensity_amplitude.png
wrote docs/handoffs/milestone_2/figures/fig02_rectangular_orientation.png
wrote docs/handoffs/milestone_2/figures/fig03_cross_image_brightness.png
verified: lossless PNG/array agreement and amplitude-squared relation
verified: fixed cross-image intensity ratio 2 and amplitude ratio sqrt(2)
maximum amplitude-squared residual: 1.11022302462515654e-16
relation tolerances: rtol=1e-14, atol=1e-15
~~~

All three images were visually inspected: readable labels, correct asymmetric
corner/origin orientation, fixed display scales, no clipping or overlap.
Two initial generations had identical hashes; final regeneration after the
resource-close improvement was checked against the same hashes.

| File | Dimensions | Bytes | SHA-256 |
|---|---|---:|---|
| `fig01_code_intensity_amplitude.png` | 2160 x 1155 | 210174 | `3bf6874ffdc0f24d65a42957a51b616d12b3ba020a86750f31366f82577286ee` |
| `fig02_rectangular_orientation.png` | 1950 x 1035 | 140234 | `7abc77e282d2a8a5b5e57f2bd2b1df375a462cf280375bfa7594597f193efb62` |
| `fig03_cross_image_brightness.png` | 1680 x 1275 | 143758 | `19a07c68f2859b215eef2e7a90ab117935b40656acbb43015e80a6fccbdf3501` |

Figures use synthetic inputs through the public APIs. Lossless PNG/array
agreement and ratio checks help verify those illustrations; the independent
Decimal and literal-byte regressions supply independent numerical evidence.

## Scope preservation and publication procedure

Exactly the approved 22 paths are delivered: 6 pre-existing modifications and
16 additions. All 50 pre-existing tracked paths outside that allowlist match
their initial SHA-256 hashes, including field/grid/propagation/validation/units,
historical handoffs/corrections, old figures, AGENTS.md and CLAUDE.md.
The root initializer's executable AST is unchanged after excluding its module
docstring. Parsed TOML differs only by the approved images extra.

Publication uses one normal commit
`feat(m2): load strict grayscale target images`, with only the approved paths
staged, followed by a normal push to the existing origin/main. Local HEAD,
live `git ls-remote origin refs/heads/main` and the GitHub API commit SHA are
checked after publication, together with the final clean working-tree state.
The completion report supplies those post-commit values; they cannot be
embedded in their own commit without creating a circular reference.

No later milestone, phase retrieval, unrelated fix, historical reconciliation,
environment rebuild or teaching-record change is included.

## Decoder references checked for this implementation

- [Pillow PNG/APNG documentation](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#apng-sequences):
  APNG MIME identity distinguishes a one-frame APNG from static PNG.
- [Pillow Image.verify](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.verify):
  integrity verification does not decode pixels; reopening precedes loading.
- [Pillow PNG plugin source](https://pillow.readthedocs.io/en/stable/_modules/PIL/PngImagePlugin.html):
  source bit depth cannot be inferred from decoded `L` alone.
- Installed `PIL/Image.py` and `PIL/ImageFile.py` were read during review:
  explicit `close()` releases image storage, so the loader uses
  `contextlib.closing` rather than relying only on the image context manager.
