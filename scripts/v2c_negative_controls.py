"""Scientific V2c faults in fresh owned copies; production is never mutated.

Each selected unchanged independent test passes, its copied calculation is
deliberately changed, the intended scientific assertion must fail on valid
fields, and exact copied restoration must pass again. Import/setup/validation
exceptions are recorded separately and never count as detection. Run only with
the existing project interpreter. This script installs nothing and runs no UI.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
CORE = "src/ohlab/optics/polarization.py"
MODEL_TEST = "tests/test_polarization_model.py"
ANALYTIC_TEST = "tests/test_polarization_analytic.py"


@dataclass(frozen=True)
class Control:
    name: str
    test_file: str
    test_function: str
    parameters: dict[str, object]
    demonstrated_fault: str
    affected_file: str = CORE
    needle: str = ""
    replacement: str = ""
    appended_code: str = ""


NORMALIZE = '''
# OWNED DELIBERATE FAULT: erase ideal polarizer loss.
_original_polarizer = apply_linear_polarizer
def apply_linear_polarizer(field, *, axis_angle_rad):
    result = _original_polarizer(field, axis_angle_rad=axis_angle_rad)
    factor = math.sqrt(field.sampled_norm / result.sampled_norm)
    return _from_data(result.x.data * factor, result.y.data * factor, field.x)
'''
SWAP = '''
# OWNED DELIBERATE FAULT: swap transverse components without changing metadata.
_original_retarder = apply_linear_retarder
def apply_linear_retarder(field, *, axis_angle_rad, retardance_rad):
    result = _original_retarder(field, axis_angle_rad=axis_angle_rad, retardance_rad=retardance_rad)
    return JonesField(x=result.y, y=result.x)
'''
COMMON_PHASE = '''
# OWNED DELIBERATE FAULT: choose a different retarder common phase.
_original_retarder = apply_linear_retarder
def apply_linear_retarder(field, *, axis_angle_rad, retardance_rad):
    result = _original_retarder(field, axis_angle_rad=axis_angle_rad, retardance_rad=retardance_rad)
    factor = complex(math.cos(-retardance_rad/2), math.sin(-retardance_rad/2))
    return _from_data(result.x.data * factor, result.y.data * factor, field.x)
'''
WEAK_INTENSITY = '''
# OWNED DELIBERATE FAULT: clip a returned weak intensity after valid construction.
_original_intensity = JonesField.intensity.fget
def _clipped_intensity(self):
    result = _original_intensity(self)
    result[result < 1e-13] = 0.0
    return result
JonesField.intensity = property(_clipped_intensity)
'''
WEAK_RATIO = '''
# OWNED DELIBERATE FAULT: clip a positive weak ratio after valid-field checks.
_original_ratio = transmission_ratio
def transmission_ratio(incident, transmitted):
    result = _original_ratio(incident, transmitted)
    return 0.0 if result is not None and 0 < result < 1e-13 else result
'''
ORDER_NEEDLE = '''polarizer_then_retarder = apply_linear_retarder(
        apply_linear_polarizer(source, axis_angle_rad=0),
        axis_angle_rad=math.pi/4, retardance_rad=math.pi/2,
    )'''
ORDER_REPLACEMENT = '''polarizer_then_retarder = apply_linear_polarizer(
        apply_linear_retarder(source, axis_angle_rad=math.pi/4, retardance_rad=math.pi/2),
        axis_angle_rad=0,
    )'''

CONTROLS = (
    Control("scalar_sum_intensity", MODEL_TEST, "test_total_intensity_sums_orthogonal_component_intensities", {},
            "Compute intensity of the scalar sum instead of orthogonal component squares.",
            needle="intensity = np.abs(x_data) ** 2 + np.abs(y_data) ** 2",
            replacement="intensity = np.abs(x_data + y_data) ** 2"),
    Control("cos_squared_amplitude", ANALYTIC_TEST, "test_malus_sweep_all_declared_angles", {"degrees": 30},
            "Use squared axis coefficients for the projected field amplitude.",
            needle="projected = c * field.x.data + s * field.y.data",
            replacement="projected = c * c * field.x.data + s * s * field.y.data"),
    Control("missing_imaginary_qwp", ANALYTIC_TEST, "test_qwp_axis_zero_preserves_imaginary_phase", {},
            "Remove the imaginary quarter-wave phase.",
            needle="phase = complex(math.cos(delta), math.sin(delta))",
            replacement="phase = complex(math.cos(delta), 0.0)"),
    Control("reversed_retardance_sign", ANALYTIC_TEST, "test_qwp_axis_zero_preserves_imaginary_phase", {},
            "Conjugate the declared relative retardance phase.",
            needle="phase = complex(math.cos(delta), math.sin(delta))",
            replacement="phase = complex(math.cos(delta), -math.sin(delta))"),
    Control("wrong_axis_convention", ANALYTIC_TEST, "test_hwp_nontrivial_axis_preserves_selected_phase", {},
            "Reverse the retarder axis angle without changing the selected expectation.",
            needle="    phase = complex(math.cos(delta), math.sin(delta))",
            replacement="    s = -s\n    phase = complex(math.cos(delta), math.sin(delta))"),
    Control("reversed_element_order", ANALYTIC_TEST, "test_noncommuting_order_has_distinct_complex_outputs", {},
            "Reverse the actual explicit composition in the copied new test, preserving its independent literal expected field.",
            affected_file=ANALYTIC_TEST, needle=ORDER_NEEDLE, replacement=ORDER_REPLACEMENT),
    Control("normalize_polarizer_loss", ANALYTIC_TEST, "test_malus_sweep_all_declared_angles", {"degrees": 30},
            "Rescale the actual polarizer output to restore incident norm.", appended_code=NORMALIZE),
    Control("drop_x_component", ANALYTIC_TEST, "test_retarder_expanded_complex_reference_inverse_and_norm", {"theta": .61, "delta": -.83},
            "Drop the actual retarder x output.",
            needle="x_data = c * axis - s * phase * perpendicular", replacement="x_data = np.zeros_like(axis)"),
    Control("drop_y_component", ANALYTIC_TEST, "test_retarder_expanded_complex_reference_inverse_and_norm", {"theta": .61, "delta": -.83},
            "Drop the actual retarder y output.",
            needle="y_data = s * axis + c * phase * perpendicular", replacement="y_data = np.zeros_like(axis)"),
    Control("swap_xy_components", ANALYTIC_TEST, "test_retarder_expanded_complex_reference_inverse_and_norm", {"theta": .61, "delta": -.83},
            "Swap x/y outputs while retaining compatible valid field records.", appended_code=SWAP),
    Control("reset_input_common_phase", MODEL_TEST, "test_from_scalar_preserves_arbitrary_common_and_relative_phase", {},
            "Discard the scalar envelope phase in both actual components.",
            needle="x_data = cx * scalar.data\n                y_data = cy * scalar.data",
            replacement="x_data = cx * np.abs(scalar.data)\n                y_data = cy * np.abs(scalar.data)"),
    Control("reset_coefficient_relative_phase", MODEL_TEST, "test_from_scalar_preserves_arbitrary_common_and_relative_phase", {},
            "Replace the complex y coefficient by its magnitude.",
            needle="y_data = cy * scalar.data", replacement="y_data = abs(cy) * scalar.data"),
    Control("retarder_common_phase_variant", ANALYTIC_TEST, "test_qwp_rotated_axis_preserves_selected_common_phase", {},
            "Multiply the actual retarder outputs by exp(-i*delta/2); intensity equivalence is insufficient.", appended_code=COMMON_PHASE),
    Control("truncate_weak_intensity", ANALYTIC_TEST, "test_weak_extinction_retains_positive_components_and_diagnostics", {"offset": -1e-9},
            "Zero the selected weak returned intensity on otherwise valid fields.", appended_code=WEAK_INTENSITY),
    Control("truncate_weak_ratio", ANALYTIC_TEST, "test_weak_extinction_retains_positive_components_and_diagnostics", {"offset": 1e-9},
            "Zero the selected positive weak transmission ratio on valid fields.", appended_code=WEAK_RATIO),
)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def production_hashes() -> dict[str, str]:
    output = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT)
    paths = sorted(set(output.decode("utf-8").split("\0")) - {""})
    return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths if (ROOT/p).is_file()}


def worker(isolated: Path, name: str) -> int:
    """Exit 10 means exclusively the selected scientific AssertionError."""
    control = next(c for c in CONTROLS if c.name == name)
    try:
        sys.path[:0] = [str(isolated/"src"), str(isolated)]
        import ohlab.optics.polarization as core
        if Path(core.__file__).resolve() != (isolated/CORE).resolve():
            raise RuntimeError(f"wrong copied source: {core.__file__}")
        spec = importlib.util.spec_from_file_location("v2c_scientific_assertions", isolated/control.test_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assertion = getattr(module, control.test_function)
        print(f"Source: {core.__file__}", flush=True)
        print(f"Scientific assertion: {control.test_function}({control.parameters!r})", flush=True)
    except Exception:
        traceback.print_exc()
        print("V2C_CONTROL_SETUP_FAILURE", flush=True)
        return 20
    try:
        assertion(**control.parameters)
    except AssertionError:
        traceback.print_exc()
        print("V2C_SCIENTIFIC_ASSERTION_FAILED", flush=True)
        return 10
    except Exception:
        traceback.print_exc()
        print("V2C_CONTROL_NONASSERTION_FAILURE", flush=True)
        return 20
    print("V2C_SCIENTIFIC_ASSERTION_PASSED", flush=True)
    return 0


def capture(command: list[str], cwd: Path, output: Path, label: str) -> dict[str, object]:
    write_json(output/f"{label}_command.json", {"argv": command, "cwd": str(cwd)})
    started = time.perf_counter()
    result = subprocess.run(command, cwd=cwd, capture_output=True, timeout=60)
    (output/f"{label}_stdout.txt").write_bytes(result.stdout)
    (output/f"{label}_stderr.txt").write_bytes(result.stderr)
    record = {"exit_code": result.returncode, "wall_seconds": time.perf_counter()-started}
    write_json(output/f"{label}_exit.json", record)
    return record


def run_controls(output: Path) -> dict[str, object]:
    expected = ROOT/".venv/Scripts/python.exe"
    if Path(sys.executable).resolve() != expected.resolve():
        raise RuntimeError(f"expected existing interpreter {expected}; got {sys.executable}")
    before = production_hashes()
    write_json(output/"production_before.json", before)
    records = []
    try:
        for control in CONTROLS:
            directory = output/control.name
            directory.mkdir()
            isolated = directory/"package_copy"
            isolated.mkdir()
            shutil.copytree(ROOT/"src/ohlab", isolated/"src/ohlab", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            (isolated/"tests").mkdir()
            for test in (MODEL_TEST, ANALYTIC_TEST):
                shutil.copyfile(ROOT/test, isolated/test)
            copied = isolated/control.affected_file
            original_bytes = copied.read_bytes()
            original = original_bytes.decode("utf-8")
            if control.needle and original.count(control.needle) != 1:
                raise RuntimeError(f"{control.name}: mutation anchor count {original.count(control.needle)}; expected one")
            command = [sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()), "--worker", str(isolated), control.name]
            baseline = capture(command, isolated, directory, "baseline")
            if baseline["exit_code"] != 0:
                raise RuntimeError(f"{control.name}: original assertion failed; retain captures and stop")
            mutated = original.replace(control.needle, control.replacement, 1) if control.needle else original+"\n"+control.appended_code
            copied.write_text(mutated, encoding="utf-8")
            (directory/"mutated_source.py.txt").write_bytes(copied.read_bytes())
            write_json(directory/"mutation.json", {**asdict(control), "original_sha256": hashlib.sha256(original_bytes).hexdigest(), "mutated_sha256": hashlib.sha256(copied.read_bytes()).hexdigest()})
            try:
                mutant = capture(command, isolated, directory, "mutant")
            finally:
                copied.write_bytes(original_bytes)
            exact = copied.read_bytes() == original_bytes
            restored = capture(command, isolated, directory, "restored")
            stdout = (directory/"mutant_stdout.txt").read_text(encoding="utf-8")
            stderr = (directory/"mutant_stderr.txt").read_text(encoding="utf-8")
            detected = mutant["exit_code"] == 10 and "V2C_SCIENTIFIC_ASSERTION_FAILED" in stdout and "AssertionError" in stderr
            record = {"name": control.name, "demonstrated_fault": control.demonstrated_fault,
                      "affected_file": control.affected_file, "test_file": control.test_file,
                      "scientific_assertion": control.test_function, "parameters": control.parameters,
                      "baseline": baseline, "mutant": mutant, "restored": restored,
                      "scientific_assertion_detected": detected, "copied_source_restored_exactly": exact,
                      "setup_or_validation_failure_counted": False}
            records.append(record)
            write_json(output/"progress.json", {"controls": records, "complete": False})
            print(f"{control.name}: original={baseline['exit_code']} mutant={mutant['exit_code']} restored={restored['exit_code']} scientific_detection={detected} exact_restoration={exact}", flush=True)
            if not detected or not exact or restored["exit_code"] != 0:
                raise RuntimeError(f"{control.name}: required scientific detection/restoration failed; retain actual evidence")
    finally:
        after = production_hashes()
        write_json(output/"production_after.json", after)
        report = {"controls": records, "declared_variants": len(CONTROLS), "executed_variants": len(records),
                  "production_inventory_count": len(before), "production_unchanged": before == after,
                  "acceptance_passed": before == after and len(records) == len(CONTROLS)
                    and all(r['scientific_assertion_detected'] and r['copied_source_restored_exactly'] and r['restored']['exit_code']==0 for r in records),
                  "restoration": "Only owned copied source mutated/restored; production never mutated.",
                  "limitations": "Specific finite-case scientific detections; no exhaustive correctness or arbitrary weak-signal guarantee."}
        write_json(output/"negative_control_report.json", report)
    if before != after:
        raise RuntimeError("Production inventory changed during controls; preserve state and stop")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--worker", nargs=2, metavar=("ISOLATED", "CONTROL"))
    args = parser.parse_args()
    if args.worker:
        return worker(Path(args.worker[0]), args.worker[1])
    if args.output_dir is None:
        parser.error("--output-dir must name a fresh owned ignored location")
    output = args.output_dir.resolve()
    runs = (ROOT/"runs").resolve()
    if not output.is_relative_to(runs) or output == runs:
        raise ValueError(f"Controls require a fresh owned location below {runs}")
    output.mkdir(parents=True, exist_ok=False)
    report = run_controls(output)
    print(json.dumps({"executed_variants": report['executed_variants'], "acceptance_passed": report['acceptance_passed'], "production_unchanged": report['production_unchanged']}, indent=2))
    return 0 if report['acceptance_passed'] else 1


if __name__ == "__main__":
    raise SystemExit(main())
