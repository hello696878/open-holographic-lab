"""Twelve scientific fault controls in exclusively owned isolated package copies.

Each selected unchanged scientific test first passes in a fresh child process.
Only the copied new interference.py is then mutated. The same assertion must
fail on valid fields/records; import, setup, schema and other exceptions have a
separate failure status and never count as detection. Production source is never
mutated. Exact changes, commands, byte captures and copy restoration remain in
fresh ignored runs/ evidence. No package install, service or browser is used.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
MODULE = "src/ohlab/optics/interference.py"
TEST_FILE = "tests/test_interference_analytic.py"


@dataclass(frozen=True)
class Control:
    name: str
    test_function: str
    parameters: dict[str, object]
    demonstrated_fault: str
    needle: str = ""
    replacement: str = ""
    appended_code: str = ""


def carrier_wrapper(sign: int) -> str:
    """Remove/add just the scalar carrier in copied wrapper; unchanged ASM stays."""
    return f'''
# OWNED DELIBERATE CONTROL: {'omit' if sign < 0 else 'duplicate'} scalar carrier.
_v2a_original_asm = propagate_angular_spectrum
def propagate_angular_spectrum(field, *, distance_m, pad_factor):
    result = _v2a_original_asm(field, distance_m=distance_m, pad_factor=pad_factor)
    angle = {sign} * (2 * math.pi / field.wavelength_m) * distance_m
    factor = complex(math.cos(angle), math.sin(angle))
    return ComplexField(data=result.data * factor, grid=result.grid,
                        wavelength_m=result.wavelength_m)
'''


NORMALIZE_WRAPPER = '''
# OWNED DELIBERATE CONTROL: replace lost arm norm by its pre-travel value.
_v2a_original_asm = propagate_angular_spectrum
def propagate_angular_spectrum(field, *, distance_m, pad_factor):
    result = _v2a_original_asm(field, distance_m=distance_m, pad_factor=pad_factor)
    before = float(np.sum(np.abs(field.data)**2, dtype=np.float64)*field.grid.dx*field.grid.dy)
    after = float(np.sum(np.abs(result.data)**2, dtype=np.float64)*result.grid.dx*result.grid.dy)
    factor = math.sqrt(before/after) if after > 0 else 1.0
    return ComplexField(data=result.data*factor, grid=result.grid,
                        wavelength_m=result.wavelength_m)
'''

COMBINE_NEEDLE = 'outputs = mix_balanced(combiner_0, combiner_1, matrix="B_dagger")'

CONTROLS = (
    Control("half_amplitude_factor", "test_coherent_two_input_hand_coefficients", {"matrix": "B"},
            "Use 0.5 field coefficients instead of 1/sqrt(2).",
            "scale = 1.0 / math.sqrt(2.0)", "scale = 0.5"),
    Control("missing_relative_i", "test_coherent_two_input_hand_coefficients", {"matrix": "B"},
            "Replace crossed ±i coefficients by a real positive coefficient.",
            'reflection = 1j if matrix == "B" else -1j', "reflection = 1.0"),
    Control("wrong_relative_i_sign", "test_coherent_two_input_hand_coefficients", {"matrix": "B"},
            "Conjugate the chosen crossed phase signs while preserving unitary magnitude.",
            'reflection = 1j if matrix == "B" else -1j',
            'reflection = -1j if matrix == "B" else 1j'),
    Control("intensity_addition", "test_equal_arm_complex_sweep_and_ordered_input_fractions", {"phase": 0.0},
            "Add incoherent intensities, replacing both coherent output phases by zero.",
            "mixed_0 = (port_0.data + reflection * port_1.data) * scale\n            mixed_1 = (reflection * port_0.data + port_1.data) * scale",
            "mixed_0 = np.sqrt((np.abs(port_0.data)**2 + np.abs(port_1.data)**2)/2).astype(np.complex128)\n            mixed_1 = mixed_0.copy()"),
    Control("reset_arm_phase", "test_complete_asymmetric_pipeline_independent_direct_dft",
            {"ny": 3, "nx": 4, "z0": .002, "z1": .003},
            "Discard the incoming arm phase before the extra prescribed phase.",
            "rotated = field.data * complex(math.cos(phase), math.sin(phase))",
            "rotated = np.abs(field.data) * complex(math.cos(phase), math.sin(phase))"),
    Control("ignore_prescribed_phase", "test_equal_arm_complex_sweep_and_ordered_input_fractions",
            {"phase": 3.141592653589793}, "Ignore the arm-1 prescribed phase at pi.",
            "rotated = field.data * complex(math.cos(phase), math.sin(phase))",
            "rotated = field.data.copy()"),
    Control("omit_ASM_carrier", "test_unequal_lengths_carrier_absolute_complex_plane_wave",
            {"mode": "DC", "phase": 0.0},
            "Multiply existing ASM output by exp(-ikL), removing its scalar carrier only.",
            appended_code=carrier_wrapper(-1)),
    Control("duplicate_ASM_carrier", "test_unequal_lengths_carrier_absolute_complex_plane_wave",
            {"mode": "DC", "phase": 0.0},
            "Multiply existing ASM output by an additional exp(+ikL).",
            appended_code=carrier_wrapper(1)),
    Control("normalize_arm_after_loss", "test_forward_evanescent_unequal_arms_preserve_loss_full_complex", {},
            "Rescale each propagated arm to hide supported forward-evanescent norm loss.",
            appended_code=NORMALIZE_WRAPPER),
    Control("flip_output_y", "test_complete_asymmetric_pipeline_independent_direct_dft",
            {"ny": 3, "nx": 4, "z0": .002, "z1": .003},
            "Flip output rows while retaining the same physical grid and valid scalar norms.",
            COMBINE_NEEDLE,
            'outputs = tuple(ComplexField(data=np.flip(field.data, axis=0), grid=field.grid, wavelength_m=field.wavelength_m) for field in mix_balanced(combiner_0, combiner_1, matrix="B_dagger"))'),
    Control("swap_output_ports", "test_equal_arm_complex_sweep_and_ordered_input_fractions", {"phase": 0.0},
            "Reverse final port ordering, recomputing each final measured norm normally.",
            COMBINE_NEEDLE,
            'outputs = tuple(reversed(mix_balanced(combiner_0, combiner_1, matrix="B_dagger")))'),
    Control("return_precombiner_fields", "test_equal_arm_complex_sweep_and_ordered_input_fractions", {"phase": 0.0},
            "Return the actual precombiner arm fields instead of coherent recombination.",
            COMBINE_NEEDLE, "outputs = (combiner_0, combiner_1)"),
)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def production_hashes() -> dict[str, str]:
    """Current tracked/unignored inventory, excluding owned ignored evidence."""
    output = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT)
    paths = sorted(set(output.decode("utf-8").split("\0")) - {""})
    return {relative.replace("\\", "/"): hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            for relative in paths if (ROOT / relative).is_file()}


def worker(isolated: Path, name: str) -> int:
    """Exit10 exclusively means the intended scientific AssertionError occurred."""
    control = next(control for control in CONTROLS if control.name == name)
    try:
        sys.path[:0] = [str(isolated / "src"), str(isolated)]
        import ohlab.optics.interference as module
        from scripts import validate_v2a_interference as reference
        if Path(module.__file__).resolve() != (isolated / MODULE).resolve():
            raise RuntimeError(f"wrong interference source: {module.__file__}")
        if Path(reference.__file__).resolve() != (isolated / "scripts/validate_v2a_interference.py").resolve():
            raise RuntimeError(f"wrong reference source: {reference.__file__}")
        spec = importlib.util.spec_from_file_location("v2a_control_scientific_test", isolated / TEST_FILE)
        test = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test)
        print(f"Copied interference source: {module.__file__}", flush=True)
        print(f"Copied independent reference: {reference.__file__}", flush=True)
        print(f"Scientific assertion: {control.test_function}({control.parameters!r})", flush=True)
    except Exception:
        traceback.print_exc()
        print("V2A_CONTROL_SETUP_FAILURE", flush=True)
        return 20
    try:
        # Calling one selected test directly keeps exactly the same independent
        # scientific assertions. All selected cases require no pytest fixtures.
        getattr(test, control.test_function)(**control.parameters)
    except AssertionError:
        traceback.print_exc()
        print("V2A_SCIENTIFIC_ASSERTION_FAILED", flush=True)
        return 10
    except Exception:
        traceback.print_exc()
        print("V2A_CONTROL_NONASSERTION_FAILURE", flush=True)
        return 20
    print("V2A_SCIENTIFIC_ASSERTION_PASSED", flush=True)
    return 0


def capture(command: list[str], isolated: Path, directory: Path, label: str) -> dict[str, object]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    write_json(directory / f"{label}_command.json", {"argv": command, "cwd": str(isolated),
        "child_environment_overrides": {"PYTHONDONTWRITEBYTECODE": "1"}})
    started = time.perf_counter()
    completed = subprocess.run(command, cwd=isolated, env=environment, capture_output=True, timeout=60)
    seconds = time.perf_counter() - started
    (directory / f"{label}_stdout.txt").write_bytes(completed.stdout)
    (directory / f"{label}_stderr.txt").write_bytes(completed.stderr)
    result = {"exit_code": completed.returncode, "wall_seconds": seconds}
    write_json(directory / f"{label}_exit.json", result)
    return result


def run_controls(output: Path) -> dict[str, object]:
    """Run all declared controls while retaining original failures and mutations."""
    expected_python = ROOT / ".venv/Scripts/python.exe"
    if Path(sys.executable).resolve() != expected_python.resolve():
        raise RuntimeError(f"expected existing project interpreter {expected_python}; got {sys.executable}")
    before = production_hashes()
    write_json(output / "production_before.json", before)
    records = []
    try:
        for control in CONTROLS:
            directory = output / control.name
            directory.mkdir(exist_ok=False)
            isolated = directory / "package_copy"
            isolated.mkdir(exist_ok=False)
            shutil.copytree(ROOT / "src/ohlab", isolated / "src/ohlab",
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            (isolated / "tests").mkdir()
            (isolated / "scripts").mkdir()
            shutil.copyfile(ROOT / TEST_FILE, isolated / TEST_FILE)
            shutil.copyfile(ROOT / "scripts/validate_v2a_interference.py", isolated / "scripts/validate_v2a_interference.py")
            copied = isolated / MODULE
            original_bytes = copied.read_bytes()
            original = original_bytes.decode("utf-8")
            if control.needle and original.count(control.needle) != 1:
                raise RuntimeError(f"{control.name}: expected one exact mutation anchor, got {original.count(control.needle)}")
            command = [sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()),
                       "--worker", str(isolated), control.name]
            baseline = capture(command, isolated, directory, "baseline")
            if baseline["exit_code"] != 0:
                raise RuntimeError(f"{control.name}: selected unchanged assertion failed; preserve captures and stop")
            mutated = (original.replace(control.needle, control.replacement, 1)
                       if control.needle else original + "\n" + control.appended_code)
            copied.write_text(mutated, encoding="utf-8")
            (directory / "mutated_interference.py.txt").write_bytes(copied.read_bytes())
            write_json(directory / "mutation.json", {**asdict(control), "affected_file": MODULE,
                "original_sha256": hashlib.sha256(original_bytes).hexdigest(),
                "mutated_sha256": hashlib.sha256(copied.read_bytes()).hexdigest()})
            try:
                mutant = capture(command, isolated, directory, "mutant")
            finally:
                # Restore only the exclusively owned copied file, never production.
                copied.write_bytes(original_bytes)
            stderr = (directory / "mutant_stderr.txt").read_text(encoding="utf-8")
            stdout = (directory / "mutant_stdout.txt").read_text(encoding="utf-8")
            detected = (mutant["exit_code"] == 10 and "V2A_SCIENTIFIC_ASSERTION_FAILED" in stdout
                        and "AssertionError" in stderr and "Not equal to tolerance" in stderr)
            restored = copied.read_bytes() == original_bytes
            record = {"name": control.name, "demonstrated_fault": control.demonstrated_fault,
                "test_file": TEST_FILE, "test_function": control.test_function,
                "test_parameters": control.parameters, "baseline": baseline, "mutant": mutant,
                "scientific_assertion_detected": detected,
                "setup_or_nonassertion_exception_counted": False,
                "copied_module_restored_exactly": restored}
            records.append(record)
            write_json(output / "progress.json", {"controls": records, "complete": False})
            print(f"{control.name}: baseline={baseline['exit_code']}, mutant={mutant['exit_code']}, scientific_assertion={detected}, copy_restored={restored}", flush=True)
            if not detected or not restored:
                raise RuntimeError(f"{control.name}: required scientific detection/restoration failed; see captures")
    finally:
        after = production_hashes()
        write_json(output / "production_after.json", after)
        report = {"controls": records, "declared_controls": len(CONTROLS),
            "production_inventory_count": len(before), "production_unchanged": before == after,
            "production_changes": {p: after.get(p) for p, digest in before.items() if after.get(p) != digest},
            "production_added_paths": sorted(set(after) - set(before)),
            "acceptance_passed": before == after and len(records) == len(CONTROLS)
                and all(r["scientific_assertion_detected"] and r["copied_module_restored_exactly"] for r in records),
            "restoration": "Production was never mutated; each owned copied new module restored byte-for-byte; exact deliberate mutation remains separately retained.",
            "limitations": "Twelve demonstrated scientific faults; no exhaustive sensitivity or physical-validation claim."}
        write_json(output / "negative_control_report.json", report)
    if before != after:
        raise RuntimeError("production inventory changed during controls; preserve state and report")
    return report


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        return worker(Path(sys.argv[2]).resolve(), sys.argv[3])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to((ROOT / "runs").resolve()) or output == (ROOT / "runs").resolve():
        parser.error("negative controls require a fresh owned directory below repository runs/")
    if not output.parent.is_dir():
        parser.error("existing output parent required")
    output.mkdir(exist_ok=False)
    report = run_controls(output)
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["acceptance_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
