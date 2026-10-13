"""Execute classified V2f scientific faults in fresh owned isolated copies.

Each actual variant requires original pass -> intended AssertionError -> exact
copied restoration -> restored pass. Setup/import/schema/nonassertion crashes
never count as detections. Only copied new module, new demo or independent
oracle code is changed; production hashes are captured before and afterward.
Ordinary supported-domain exception tests are reported separately, not counted
as mutation variants. No dependencies, browser/server or Git writes are used.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
CORE = "src/ohlab/optics/polarized_interference.py"
REFERENCE = "scripts/validate_v2f_interference.py"
DEMO = "examples/polarized_two_path_interference.py"
PRIMITIVES = "tests/test_polarized_interference_primitives.py"
ANALYTIC = "tests/test_polarized_interference_analytic.py"


@dataclass(frozen=True)
class Control:
    name: str
    classification: str
    fault: str
    test_file: str
    assertion: str
    parameters: dict
    code: str
    affected_file: str = CORE


MIX_WRAPPER = """
_control_original_mix = mix_balanced_jones
def mix_balanced_jones(port_0, port_1, *, matrix):
    values = _control_original_mix(port_0, port_1, matrix=matrix)
    {body}
"""
RETARDER_WRAPPER = """
_control_original_retarder = apply_linear_retarder
def apply_linear_retarder(field, *, axis_angle_rad, retardance_rad):
    {body}
"""
PRODUCTION = "production composition/dependency-binding mutation in copied new module"
CONTROLS = (
    Control("swap_optical_ports", PRODUCTION, "Reverse optical ports without swapping polarization labels.", PRIMITIVES,
            "test_literal_four_component_mixing", {"matrix": "B"}, MIX_WRAPPER.format(body="return values[1], values[0]")),
    Control("swap_polarization_components", PRODUCTION, "Swap x/y components in each actual port.", PRIMITIVES,
            "test_literal_four_component_mixing", {"matrix": "B"}, MIX_WRAPPER.format(body="return tuple(JonesField(x=v.y, y=v.x) for v in values)")),
    Control("omit_x_component", PRODUCTION, "Replace both actual x outputs with exact zero.", PRIMITIVES,
            "test_literal_four_component_mixing", {"matrix": "B"}, MIX_WRAPPER.format(body="return tuple(JonesField(x=ComplexField(data=np.zeros(v.shape, dtype=np.complex128), grid=v.grid, wavelength_m=v.wavelength_m), y=v.y) for v in values)")),
    Control("omit_y_component", PRODUCTION, "Replace both actual y outputs with exact zero.", ANALYTIC,
            "test_pure_y_reduction_to_scalar", {"component": "y"}, MIX_WRAPPER.format(body="return tuple(JonesField(x=v.x, y=ComplexField(data=np.zeros(v.shape, dtype=np.complex128), grid=v.grid, wavelength_m=v.wavelength_m)) for v in values)")),
    Control("wrong_splitter_sign", PRODUCTION, "Use B_dagger where B is requested.", PRIMITIVES,
            "test_literal_four_component_mixing", {"matrix": "B"}, """
_control_original_scalar_mix = mix_balanced
def mix_balanced(port_0, port_1, *, matrix):
    return _control_original_scalar_mix(port_0, port_1, matrix='B_dagger' if matrix == 'B' else matrix)
"""),
    Control("common_phase_only_x", PRODUCTION, "Apply extra arm phase to x but leave y unphased.", ANALYTIC,
            "test_unequal_arm_carrier_is_present_once", {"phase": .37}, """
_control_original_phase = _phase
def _phase(field, phase_rad):
    value = _control_original_phase(field, phase_rad)
    return JonesField(x=value.x, y=field.y)
"""),
    Control("reverse_retardance_sign", PRODUCTION, "Reverse the supplied relative retardance sign.", ANALYTIC,
            "test_complex_overlap_full_field_and_argument", {"phase": .37}, RETARDER_WRAPPER.format(body="return _control_original_retarder(field, axis_angle_rad=axis_angle_rad, retardance_rad=-retardance_rad)")),
    Control("drop_retarder_common_phase", PRODUCTION, "Apply the forbidden exp(-i*delta/2) compensation.", ANALYTIC,
            "test_common_retarder_phase_is_not_removed", {"phase": .37}, RETARDER_WRAPPER.format(body="""value = _control_original_retarder(field, axis_angle_rad=axis_angle_rad, retardance_rad=retardance_rad)
    factor = complex(math.cos(-retardance_rad/2), math.sin(-retardance_rad/2))
    return JonesField(x=ComplexField(data=value.x.data*factor, grid=value.grid, wavelength_m=value.wavelength_m), y=ComplexField(data=value.y.data*factor, grid=value.grid, wavelength_m=value.wavelength_m))""")),
    Control("reset_terminal_common_phase", PRODUCTION, "Reset each arm terminal field common phase using its first nonzero component.", ANALYTIC,
            "test_common_retarder_phase_is_not_removed", {"phase": .37}, """
_control_original_actions = _actions
def _actions(field, arm, arm_index):
    value, history = _control_original_actions(field, arm, arm_index)
    first = next(complex(v) for part in (value.x.data, value.y.data) for v in part.ravel() if v != 0)
    factor = first.conjugate()/abs(first)
    reset = JonesField(x=ComplexField(data=value.x.data*factor, grid=value.grid, wavelength_m=value.wavelength_m), y=ComplexField(data=value.y.data*factor, grid=value.grid, wavelength_m=value.wavelength_m))
    return reset, tuple(list(history[:-1])+[reset.sampled_norm]) if history else history
"""),
    Control("incoherent_arm_addition", PRODUCTION, "Replace recombination with equal incoherent magnitude outputs.", ANALYTIC,
            "test_complex_overlap_full_field_and_argument", {"phase": .37}, """
_control_original_scalar_mix = mix_balanced
def mix_balanced(port_0, port_1, *, matrix):
    if matrix != 'B_dagger':
        return _control_original_scalar_mix(port_0, port_1, matrix=matrix)
    data = np.sqrt((np.abs(port_0.data)**2 + np.abs(port_1.data)**2)/2).astype(np.complex128)
    return tuple(ComplexField(data=data, grid=port_0.grid, wavelength_m=port_0.wavelength_m) for _ in range(2))
"""),
    Control("scalar_sum_orthogonal_components", "reused public-dependency behavior mutation installed only in copied new module", "Substitute intensity of x+y for orthogonal component square sum on returned fields; this is not a new runner branch.", PRIMITIVES,
            "test_combined_intensity_has_no_scalar_cross_term", {}, """
def _control_wrong_intensity(self):
    return np.abs(self.x.data+self.y.data)**2
JonesField.intensity = property(_control_wrong_intensity)
"""),
    Control("omit_propagation_carrier", PRODUCTION, "Omit propagation entirely on a uniform DC fixture that isolates its carrier.", ANALYTIC,
            "test_unequal_arm_carrier_is_present_once", {"phase": 0.}, """
def propagate_angular_spectrum(field, *, distance_m, pad_factor):
    return field
"""),
    Control("double_propagation_carrier", PRODUCTION, "Multiply the propagated envelope by a second exp(i*k*z) carrier.", ANALYTIC,
            "test_unequal_arm_carrier_is_present_once", {"phase": 0.}, """
_control_original_propagate = propagate_angular_spectrum
def propagate_angular_spectrum(field, *, distance_m, pad_factor):
    value = _control_original_propagate(field, distance_m=distance_m, pad_factor=pad_factor)
    angle = 2*math.pi*distance_m/field.wavelength_m
    return ComplexField(data=value.data*complex(math.cos(angle), math.sin(angle)), grid=field.grid, wavelength_m=field.wavelength_m)
"""),
    Control("normalize_terminal_polarizer_loss", PRODUCTION, "Rescale terminal polarizer output to restore its pre-action norm.", ANALYTIC,
            "test_lossy_arm_original_input_budget", {"phase": .37}, """
_control_original_polarizer = apply_linear_polarizer
def apply_linear_polarizer(field, *, axis_angle_rad):
    value = _control_original_polarizer(field, axis_angle_rad=axis_angle_rad)
    factor = math.sqrt(field.sampled_norm/value.sampled_norm)
    return JonesField(x=ComplexField(data=value.x.data*factor, grid=value.grid, wavelength_m=value.wavelength_m), y=ComplexField(data=value.y.data*factor, grid=value.grid, wavelength_m=value.wavelength_m))
"""),
    Control("filtered_outputs_returned_as_raw", PRODUCTION, "Return downstream analyzed fields as the purported raw outputs with internally matching output norm records.", ANALYTIC,
            "test_orthogonal_arms_analyzers_are_separate", {"phase": .37}, """
from dataclasses import replace as _control_replace
_control_original_runner = run_polarized_two_arm
def run_polarized_two_arm(incident, *, spec):
    result = _control_original_runner(incident, spec=spec)
    values = tuple(apply_linear_polarizer(f, axis_angle_rad=math.pi/4) for f in result.outputs)
    norms = _control_replace(result.norms, outputs=tuple(f.sampled_norm for f in values))
    return PolarizedTwoArmResult(spec=result.spec, outputs=values, norms=norms)
"""),
    Control("silently_delete_unsupported_tiny_component", PRODUCTION, "Erase an entire represented tiny component before scalar domain validation.", "", "tiny_domain_detector", {}, """
_control_original_jones_mix = mix_balanced_jones
def mix_balanced_jones(port_0, port_1, *, matrix):
    def sanitized(value):
        parts = []
        for part in (value.x, value.y):
            data = np.zeros_like(part.data) if np.max(np.abs(part.data)) < 1e-150 else part.data
            parts.append(ComplexField(data=data, grid=value.grid, wavelength_m=value.wavelength_m))
        return JonesField(x=parts[0], y=parts[1])
    return _control_original_jones_mix(sanitized(port_0), sanitized(port_1), matrix=matrix)
"""),
    Control("reverse_terminal_action_order", PRODUCTION, "Reverse ordered terminal Jones actions in both arms.", ANALYTIC,
            "test_terminal_action_order_is_noncommuting", {}, """
_control_original_actions = _actions
def _actions(field, arm, arm_index):
    changed = PolarizationArm(distance_m=arm.distance_m, actions=tuple(reversed(arm.actions)))
    return _control_original_actions(field, changed, arm_index)
"""),
    Control("normalize_downstream_analyzer_loss", "demonstration implementation mutation in copied new example", "Normalize downstream analyzer output while leaving raw outputs unchanged.", "", "demo_detector", {}, """
from ohlab import ComplexField as _ControlComplexField
from ohlab.optics.polarization import JonesField as _ControlJonesField
_control_original_polarizer = apply_linear_polarizer
def apply_linear_polarizer(field, *, axis_angle_rad):
    value = _control_original_polarizer(field, axis_angle_rad=axis_angle_rad)
    factor = math.sqrt(field.sampled_norm/value.sampled_norm)
    return _ControlJonesField(x=_ControlComplexField(data=value.x.data*factor, grid=value.grid, wavelength_m=value.wavelength_m), y=_ControlComplexField(data=value.y.data*factor, grid=value.grid, wavelength_m=value.wavelength_m))
""", affected_file=DEMO),
    Control("missing_overlap_conjugation", "independent-reference self-check mutation; runner has no overlap branch", "Omit conjugation of the genuinely complex first-arm Jones state.", "", "overlap_detector", {}, """
def overlap(j0, j1):
    return complex(np.sum(j0*j1))
""", affected_file=REFERENCE),
    Control("discard_overlap_argument", "independent-reference self-check mutation; runner has no overlap branch", "Replace complex overlap by its absolute magnitude.", "", "overlap_detector", {}, """
def overlap(j0, j1):
    return complex(abs(np.sum(np.conj(j0)*j1)))
""", affected_file=REFERENCE),
)


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def production_hashes() -> dict[str, str]:
    paths = list((ROOT / "src/ohlab").rglob("*.py"))
    paths += [ROOT / p for p in (CORE, REFERENCE, DEMO, "scripts/v2f_negative_controls.py", PRIMITIVES, ANALYTIC,
                                "tests/test_polarized_interference_model.py", "tests/test_polarized_interference_architecture.py")]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}


def worker(isolated: Path, name: str) -> int:
    """Exit10 exclusively means an intended scientific AssertionError."""
    control = next(c for c in CONTROLS if c.name == name)
    try:
        sys.path[:0] = [str(isolated / "src"), str(isolated)]
        import ohlab.optics.polarized_interference as core
        import scripts.validate_v2f_interference as reference
        if Path(core.__file__).resolve() != (isolated / CORE).resolve():
            raise RuntimeError(f"wrong source imported: {core.__file__}")
        if Path(reference.__file__).resolve() != (isolated / REFERENCE).resolve():
            raise RuntimeError(f"wrong reference imported: {reference.__file__}")
        if control.test_file:
            module_spec = importlib.util.spec_from_file_location("v2f_scientific_assertions", isolated / control.test_file)
            module = importlib.util.module_from_spec(module_spec)
            module_spec.loader.exec_module(module)
            assertion = getattr(module, control.assertion)
        elif control.assertion == "tiny_domain_detector":
            def assertion():
                incident = reference.make_jones(1, 1e-200)
                before = incident.y.data.tobytes()
                assert incident.sampled_norm > 0 and (incident.y.data != 0).all()
                try:
                    core.mix_balanced_jones(incident, reference.make_jones(0, 0), matrix="B")
                except ValueError:
                    assert incident.y.data.tobytes() == before
                else:
                    raise AssertionError("represented unsupported tiny component was silently erased/accepted")
        elif control.assertion == "overlap_detector":
            def assertion():
                import numpy as np
                j0, j1 = np.array([1, 1j]) / math.sqrt(2), np.array([1, 1]) / math.sqrt(2)
                gamma = reference.overlap(j0, j1)
                np.testing.assert_allclose(gamma, (1 - 1j) / 2, rtol=0, atol=2e-15)
                term = (complex(0, 1) * gamma).real
                np.testing.assert_allclose(((1 + term) / 2, (1 - term) / 2), (.75, .25), rtol=2e-13, atol=2e-13)
        elif control.assertion == "demo_detector":
            import examples.polarized_two_path_interference as example
            if Path(example.__file__).resolve() != (isolated / DEMO).resolve():
                raise RuntimeError(f"wrong example imported: {example.__file__}")
            def assertion():
                example.compute_demo(n=32, measure=False)
        else:
            raise RuntimeError(f"unknown control assertion {control.assertion}")
        print(f"Source: {core.__file__}\nClassification: {control.classification}\nAssertion: {control.assertion}({control.parameters!r})", flush=True)
    except Exception:
        traceback.print_exc()
        print("V2F_CONTROL_SETUP_FAILURE", flush=True)
        return 20
    try:
        assertion(**control.parameters)
    except AssertionError:
        traceback.print_exc()
        print("V2F_SCIENTIFIC_ASSERTION_FAILED", flush=True)
        return 10
    except Exception:
        traceback.print_exc()
        print("V2F_CONTROL_NONASSERTION_FAILURE", flush=True)
        return 20
    print("V2F_SCIENTIFIC_ASSERTION_PASSED", flush=True)
    return 0


def capture(command: list[str], cwd: Path, directory: Path, label: str) -> dict:
    write_json(directory / f"{label}_command.json", {"argv": command, "cwd": str(cwd)})
    started = time.perf_counter()
    result = subprocess.run(command, cwd=cwd, capture_output=True, timeout=90)
    (directory / f"{label}_stdout.txt").write_bytes(result.stdout)
    (directory / f"{label}_stderr.txt").write_bytes(result.stderr)
    record = {"exit_code": result.returncode, "wall_seconds": time.perf_counter() - started}
    write_json(directory / f"{label}_exit.json", record)
    return record


def run_controls(output: Path) -> dict:
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        raise RuntimeError(f"use the existing project interpreter, got {sys.executable}")
    before = production_hashes()
    write_json(output / "production_before.json", before)
    rows = []
    try:
        for control in CONTROLS:
            directory = output / control.name
            directory.mkdir()
            isolated = directory / "package_copy"
            shutil.copytree(ROOT / "src/ohlab", isolated / "src/ohlab", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            for relative in (REFERENCE, DEMO, PRIMITIVES, ANALYTIC):
                target = isolated / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            target = isolated / control.affected_file
            original = target.read_bytes()
            command = [sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()), "--worker", str(isolated), control.name]
            baseline = capture(command, isolated, directory, "original")
            if baseline["exit_code"] != 0:
                raise RuntimeError(f"{control.name}: original assertion failed; retain evidence")
            mutation = original + b"\n# OWNED DELIBERATE SCIENTIFIC FAULT\n" + control.code.encode("utf-8")
            target.write_bytes(mutation)
            (directory / "mutated_source.py.txt").write_bytes(mutation)
            write_json(directory / "mutation.json", {**asdict(control), "original_sha256": hashlib.sha256(original).hexdigest(),
                                                    "mutated_sha256": hashlib.sha256(mutation).hexdigest()})
            try:
                mutant = capture(command, isolated, directory, "mutant")
            finally:
                target.write_bytes(original)
            exact = target.read_bytes() == original
            restored = capture(command, isolated, directory, "restored")
            stdout = (directory / "mutant_stdout.txt").read_text(encoding="utf-8")
            stderr = (directory / "mutant_stderr.txt").read_text(encoding="utf-8")
            detected = mutant["exit_code"] == 10 and "V2F_SCIENTIFIC_ASSERTION_FAILED" in stdout and "AssertionError" in stderr
            row = {"name": control.name, "classification": control.classification, "fault": control.fault,
                   "affected_file": control.affected_file, "assertion": control.assertion, "parameters": control.parameters,
                   "original": baseline, "mutant": mutant, "restored": restored,
                   "intended_scientific_assertion_detected": detected, "copied_source_restored_exactly": exact,
                   "restored_sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "setup_or_nonassertion_failure_counted": False}
            rows.append(row)
            print(f"{control.name}: original={baseline['exit_code']} mutant={mutant['exit_code']} restored={restored['exit_code']} intended_detection={detected} exact_restoration={exact}", flush=True)
            if not detected or not exact or restored["exit_code"] != 0:
                raise RuntimeError(f"{control.name}: required detection/restoration failed; preserve actual captures")
    finally:
        after = production_hashes()
        write_json(output / "production_after.json", after)
        report = {"actual_variants": rows, "declared_variants": len(CONTROLS), "executed_variants": len(rows),
                  "production_hashes_unchanged": before == after, "hashed_production_files": len(before),
                  "acceptance_passed": before == after and len(rows) == len(CONTROLS) and all(r["intended_scientific_assertion_detected"] and r["copied_source_restored_exactly"] and r["restored"]["exit_code"] == 0 for r in rows),
                  "classification_counts": {kind: sum(r["classification"] == kind for r in rows) for kind in sorted({r["classification"] for r in rows})},
                  "ordinary_exception_tests": "Supported-domain tests in the new regression suite/validator are separate acceptance, not mutation detections. The deliberate tiny-erasure variant specifically must violate that exception contract.",
                  "restoration": "Only owned copies changed; original production code never mutated. Exact original copied bytes restored before restored assertion.",
                  "limitations": "Finite-case scientific detections; copied dependency-binding faults exercise the new composition's use of public operations; overlap self-checks are not production branches; no gap-free correctness claim."}
        write_json(output / "negative_control_report.json", report)
    if not report["acceptance_passed"]:
        raise RuntimeError("Required fault-control acceptance or production preservation failed")
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
    if not output.is_relative_to((ROOT / "runs").resolve()) or output == (ROOT / "runs").resolve():
        raise ValueError("evidence must be in a fresh owned child of repository runs")
    output.mkdir(parents=True, exist_ok=False)
    report = run_controls(output)
    print(json.dumps({"acceptance_passed": report["acceptance_passed"], "executed_variants": report["executed_variants"],
                      "classification_counts": report["classification_counts"], "production_hashes_unchanged": report["production_hashes_unchanged"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
