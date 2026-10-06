"""Detect bounded V2b integration faults using exclusively owned isolated copies.

Each original selected regression must pass exactly once before its copied
implementation is mutated. Only its identifying assertion is detection. All
copy restorations and production-file hashes are verified; no server/browser
or dependency installation is performed by this script.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "bench"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


@dataclass(frozen=True)
class Control:
    name: str
    category: str
    language: str
    affected_file: str
    needle: str
    replacement: str
    test_file: str
    test_title: str
    assertion_marker: str
    demonstrated_fault: str


ADAPTER_TEST = "tests/test_virtual_bench_two_path_adapter.py"
PROTOCOL_FILE = "apps/virtual_bench/two_path_protocol.py"
ADAPTER_FILE = "apps/virtual_bench/two_path_adapter.py"
CONTROLS = (
    Control("phase_unit_conversion", "unit_conversion", "typescript", "src/two_path_state.ts",
            "const value = numericText.test(input) ? Number(input) * scale : NaN;",
            "const value = numericText.test(input) ? Number(input) * (scale === 1 ? Math.PI / 180 : scale) : NaN;",
            "tests/two_path_state.test.ts", "unit conversion occurs once and nonzero signed phase is never wrapped", "UNIT_PHASE_DETECTED",
            "Authoritative radians are incorrectly interpreted as degrees."),
    Control("distance_unit_conversion", "unit_conversion", "typescript", "src/two_path_state.ts",
            "const value = numericText.test(input) ? Number(input) * scale : NaN;",
            "const value = numericText.test(input) ? Number(input) * (scale === 1e-3 ? 1e-6 : scale) : NaN;",
            "tests/two_path_state.test.ts", "unit conversion occurs once and nonzero signed phase is never wrapped", "UNIT_DISTANCE_DETECTED",
            "An arm length entered in millimetres is multiplied by the micrometre factor."),
    Control("independent_port_normalization", "independent_port_normalization", "typescript", "src/detector.ts",
            "first = factory(result.ports[0].intensity, result.experiment.grid, limits, 'port_0');",
            "first = factory(result.ports[0].intensity, result.experiment.grid, { min: 0, max: result.ports[0].intensityMax }, 'port_0');",
            "tests/two_path_display.test.ts", "explicit joint automatic limits and unchanged raw values prevent independent port normalization", "SHARED_RANGE_DETECTED",
            "The dimmer port is independently peak-normalized instead of using the common explicit range."),
    Control("only_one_texture_detached", "only_one_texture_detached", "typescript", "src/scene.ts",
            "for (const mesh of this.dualDetectors ?? []) {",
            "for (const mesh of (this.dualDetectors ?? []).slice(0, 1)) {",
            "tests/two_path_display.test.ts", "detachment clears both real scene materials and releases their separately owned textures", "BOTH_TEXTURES_INVALIDATED",
            "Only port 0 material is detached; port 1 keeps an obsolete texture reference."),
    Control("cross_mode_stale_attachment", "cross_mode_stale_attachment", "typescript", "src/two_path_state.ts",
            "this.snapshot.revision === active.revision && this.snapshot.attachmentEpoch === active.attachmentEpoch",
            "this.snapshot.revision === active.revision",
            "tests/two_path_state.test.ts", "away-and-back mode changes reject late attachment without aborting or clearing the shared operation", "CROSS_MODE_STALE_DETECTED",
            "Switching away and back no longer invalidates an otherwise identical late response."),
    Control("atomic_second_texture_failure", "atomic_second_texture_failure", "typescript", "src/detector.ts",
            "} catch (error) { first?.dispose(); second?.dispose(); throw error; }",
            "} catch (error) { second?.dispose(); throw error; }",
            "tests/two_path_display.test.ts", "second texture preparation failure disposes first before either can be published", "ATOMIC_SECOND_TEXTURE_DETECTED",
            "Failure while preparing port 1 leaks the newly prepared port 0 resource."),
    Control("port_swap", "port_swap", "python", PROTOCOL_FILE,
            "intensities = tuple(output.intensity for output in result.outputs)",
            "intensities = tuple(output.intensity for output in reversed(result.outputs))",
            ADAPTER_TEST, "test_ordered_ports_not_swapped_and_second_output_not_duplicated", "PORT_SWAP_DETECTED",
            "The ordered port payloads are swapped while the identities remain port_0/port_1."),
    Control("duplicate_second_output", "duplicate_second_output", "python", PROTOCOL_FILE,
            '("intensity_port_1", "intensity", "port_1", intensities[1],',
            '("intensity_port_1", "intensity", "port_1", intensities[0],',
            ADAPTER_TEST, "test_ordered_ports_not_swapped_and_second_output_not_duplicated", "DUPLICATE_PORT_DETECTED",
            "Port 1 transports port 0 intensity instead of its independently measured output."),
    Control("ignored_phase", "ignored_phase", "python", ADAPTER_FILE,
            "result = run_two_arm(incident, spec=experiment.spec)",
            "result = run_two_arm(incident, spec=TwoArmSpec(arm_0_distance_m=experiment.spec.arm_0_distance_m, arm_1_distance_m=experiment.spec.arm_1_distance_m, relative_phase_rad=0.0))",
            ADAPTER_TEST, "test_nonzero_phase_is_used_without_wrapping", "IGNORE_PHASE_DETECTED",
            "The valid nonzero extra phase is replaced by zero in the numerical call."),
    Control("surviving_output_denominator", "surviving_output_denominator", "python", PROTOCOL_FILE,
            "return {name: getattr(result.norms, name) for name in names}",
            "return {name: tuple(v / result.norms.outputs_total for v in result.norms.outputs) if name == 'output_fractions' and result.norms.outputs_total else getattr(result.norms, name) for name in names}",
            ADAPTER_TEST, "test_original_input_denominator_retains_actual_evanescent_loss", "INPUT_DENOMINATOR_DETECTED",
            "Fractions divide by surviving output norm, hiding actual forward propagation loss."),
    Control("duplicate_single_runner", "duplicate_invocation", "python", ADAPTER_FILE,
            "        result = run_two_arm(incident, spec=experiment.spec)",
            "        run_two_arm(incident, spec=experiment.spec)\n        result = run_two_arm(incident, spec=experiment.spec)",
            ADAPTER_TEST, "test_single_direct_equivalence_validation_zero_sampling_once_runner_once[False]", "SINGLE_CALL_COUNT_DETECTED",
            "One intentional single request invokes the public solver twice."),
    Control("duplicate_sweep_runner", "duplicate_invocation", "python", ADAPTER_FILE,
            "            result = run_two_arm(incident, spec=spec)",
            "            run_two_arm(incident, spec=spec)\n            result = run_two_arm(incident, spec=spec)",
            ADAPTER_TEST, "test_sweep_actual_seventeen_invocations_and_independent_endpoint_values", "SWEEP_CALL_COUNT_DETECTED",
            "Each requested sweep phase invokes the public solver twice."),
    Control("fabricated_analytic_sweep_rows", "fabricated_analytic_sweep", "python", PROTOCOL_FILE,
            '"output_norms": list(norms.outputs), "output_fractions": list(norms.output_fractions),',
            '"output_norms": [norms.inputs_total * __import__("math").cos(phase_rad / 2) ** 2, norms.inputs_total * __import__("math").sin(phase_rad / 2) ** 2], "output_fractions": list(norms.output_fractions),',
            ADAPTER_TEST, "test_sweep_actual_seventeen_invocations_and_independent_endpoint_values", "FABRICATED_SWEEP_DETECTED",
            "Unit-survival analytic curves replace the measured unequal-mode output norms, despite actual solver calls."),
    Control("premature_abort_gate_release", "premature_abort_gate_release", "python", "apps/virtual_bench/server.py",
            "        if disconnected in done:\n            return None",
            "        if disconnected in done:\n            request.app.state.gate._completed(future)\n            return None",
            "tests/test_virtual_bench_two_path_server.py", "test_actual_abort_holds_shared_gate_until_python_finishes[disconnect-dual]", "GATE_ABORT_DETECTED",
            "The HTTP disconnect releases the shared gate while controlled Python work is still running."),
)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def production_hashes() -> dict[str, str]:
    result = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                            cwd=ROOT, capture_output=True, check=True)
    records = {}
    for relative in sorted(set(result.stdout.decode("utf-8").split("\0")) - {""}):
        path = ROOT / relative
        if path.is_file():
            records[relative.replace("\\", "/")] = hashlib.sha256(path.read_bytes()).hexdigest()
    return records


def prepare_copy(control: Control, output: Path, owner: str) -> Path:
    if control.language == "typescript":
        isolated = FRONTEND / ".vitest" / "v2b_negative_controls" / owner / control.name
        isolated.mkdir(parents=True, exist_ok=False)
        shutil.copytree(FRONTEND / "src", isolated / "src")
        shutil.copytree(FRONTEND / "tests", isolated / "tests")
        shutil.copy2(FRONTEND / "package.json", isolated / "package.json")
        shutil.copy2(FRONTEND / "tsconfig.json", isolated / "tsconfig.json")
    else:
        isolated = output / control.name / "python_copy"
        isolated.mkdir(parents=True, exist_ok=False)
        (isolated / "apps").mkdir()
        shutil.copy2(ROOT / "apps/__init__.py", isolated / "apps/__init__.py")
        shutil.copytree(ROOT / "apps/virtual_bench", isolated / "apps/virtual_bench",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (isolated / "tests").mkdir()
        for path in sorted((ROOT / "tests").glob("test_virtual_bench*.py")):
            shutil.copy2(path, isolated / "tests" / path.name)
    return isolated


def command_for(control: Control, isolated: Path, npm: Path) -> list[str]:
    if control.language == "typescript":
        return [str(npm), "run", "--ignore-scripts", "test:unit", "--", "--root", str(isolated),
                "--config", str(FRONTEND / "vitest.config.ts"), "--reporter=verbose",
                control.test_file, "-t", re.escape(control.test_title)]
    module_name = control.affected_file.removesuffix(".py").replace("/", ".")
    # Verify the copied integration module and original installed numerical core
    # in the exact process that invokes the selected regression.
    selected = ["-q", "-p", "no:cacheprovider", "--import-mode=importlib",
                f"--basetemp={isolated / 'pytest_temp'}", "-c", str(ROOT / "pyproject.toml"),
                f"{isolated / control.test_file}::{control.test_title}"]
    # Optional ASGI imports must follow pytest's assertion-rewrite/plugin setup;
    # otherwise preloading anyio triggers the project's warnings-as-errors gate.
    preflight = "\n".join((
        "from pathlib import Path", "import importlib, sys, pytest", "import ohlab",
        f"sys.path.insert(0, {str(isolated / 'tests')!r})", "class SourceProbe:",
        "    def pytest_configure(self, config):",
        f"        module = importlib.import_module({module_name!r})",
        f"        assert Path(module.__file__).resolve() == Path({str(isolated / control.affected_file)!r}).resolve()",
        f"        assert Path(ohlab.__file__).resolve().is_relative_to(Path({str(ROOT / 'src')!r}).resolve())",
        "        print('Copied integration source:', module.__file__)",
        "        print('Protected numerical source:', ohlab.__file__)",
        f"raise SystemExit(pytest.main({selected!r}, plugins=[SourceProbe()]))",
    ))
    return [str(PYTHON), "-B", "-X", "utf8", "-c", preflight]


def capture(command: list[str], cwd: Path, output: Path, label: str,
            environment: dict[str, str]) -> tuple[int, str]:
    write_json(output / f"{label}_command.json", {"argv": command, "cwd": str(cwd),
               "child_process_overrides": {name: environment[name] for name in ("NO_COLOR", "FORCE_COLOR", "PYTHONDONTWRITEBYTECODE")}})
    started = time.perf_counter()
    completed = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, timeout=60)
    (output / f"{label}_stdout.txt").write_bytes(completed.stdout)
    (output / f"{label}_stderr.txt").write_bytes(completed.stderr)
    write_json(output / f"{label}_exit.json", {"exit_code": completed.returncode, "wall_seconds": time.perf_counter() - started})
    combined = ANSI.sub("", completed.stdout.decode("utf-8", errors="replace") + completed.stderr.decode("utf-8", errors="replace"))
    return completed.returncode, combined


def run_controls(output: Path) -> int:
    npm = shutil.which("npm.cmd")
    if not npm or not (FRONTEND / "node_modules/vitest").is_dir():
        raise RuntimeError("Expected installed Node/npm/Vitest unavailable; no install or fallback is authorized")
    if Path(sys.executable).resolve() != PYTHON.resolve():
        raise RuntimeError("Use the existing project interpreter")
    owner = str(uuid.uuid4())
    environment = os.environ.copy()
    environment.update(NO_COLOR="1", FORCE_COLOR="0", PYTHONDONTWRITEBYTECODE="1")
    before = production_hashes()
    write_json(output / "production_before.json", before)
    records = []
    failure = None
    try:
        for control in CONTROLS:
            evidence = output / control.name
            evidence.mkdir(exist_ok=False)
            isolated = prepare_copy(control, output, owner)
            path = isolated / control.affected_file
            original = path.read_bytes()
            source = original.decode("utf-8").replace("\r\n", "\n")
            if source.count(control.needle) != 1:
                raise RuntimeError(f"{control.name}: mutation needle must occur once, got {source.count(control.needle)}")
            command = command_for(control, isolated, Path(npm))
            child = environment.copy()
            if control.language == "python":
                child["PYTHONPATH"] = os.pathsep.join((str(isolated), str(ROOT)))
            baseline_code, baseline_text = capture(command, isolated, evidence, "baseline", child)
            if baseline_code != 0 or not re.search(r"\b1 passed\b", baseline_text):
                raise RuntimeError(f"{control.name}: selected original test did not pass exactly once")
            restored = False
            try:
                path.write_text(source.replace(control.needle, control.replacement, 1), encoding="utf-8")
                write_json(evidence / "mutation.json", {**asdict(control), "isolated_root": str(isolated),
                           "original_sha256": hashlib.sha256(original).hexdigest(),
                           "mutant_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
                mutant_code, mutant_text = capture(command, isolated, evidence, "mutant", child)
                detected = mutant_code != 0 and "AssertionError" in mutant_text and control.assertion_marker in mutant_text
                detected = detected and control.test_title.split("[")[0] in mutant_text
                if control.language == "typescript":
                    detected = detected and "FAIL" in mutant_text
            finally:
                path.write_bytes(original)
                restored = path.read_bytes() == original
            restored_code, restored_text = capture(command, isolated, evidence, "restored", child)
            record = {"name": control.name, "category": control.category, "baseline_exit": baseline_code,
                      "mutant_exit": mutant_code, "intended_assertion_detected": bool(detected),
                      "copied_source_restored_exactly": restored, "restored_exit": restored_code,
                      "restored_test_passed": restored_code == 0 and bool(re.search(r"\b1 passed\b", restored_text))}
            records.append(record)
            write_json(output / "summary.json", {"owner": owner, "complete": False, "controls": records})
            print(f"{control.name}: baseline={baseline_code}, mutant={mutant_code}, intended_assertion={bool(detected)}, restored={restored_code}", flush=True)
            if not detected or not restored or not record["restored_test_passed"]:
                raise RuntimeError(f"{control.name}: intended assertion/restoration gate failed; setup/import failure is not detection")
    except Exception as exc:
        failure = {"type": type(exc).__name__, "message": str(exc)}
        write_json(output / "failure.json", failure)
        print(f"STOPPED: {exc}", file=sys.stderr, flush=True)
    after = production_hashes()
    write_json(output / "production_after.json", after)
    unchanged = before == after
    if not unchanged:
        write_json(output / "production_difference.json", {"before": before, "after": after})
    complete = failure is None and unchanged and len(records) == len(CONTROLS)
    write_json(output / "summary.json", {"owner": owner, "complete": complete, "controls": records,
               "detected": sum(record["intended_assertion_detected"] for record in records),
               "control_variants": len(CONTROLS), "category_count": len({control.category for control in CONTROLS}),
               "production_unchanged": unchanged, "failure": failure})
    print(f"production_unchanged={unchanged}; detected={sum(record['intended_assertion_detected'] for record in records)}/{len(CONTROLS)}", flush=True)
    return 0 if complete else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    destination = args.output_dir.resolve()
    if not destination.is_relative_to((ROOT / "runs").resolve()) or destination.exists():
        parser.error("Use a fresh owned ignored destination inside repository runs")
    destination.mkdir(parents=True, exist_ok=False)
    return run_controls(destination)


if __name__ == "__main__":
    raise SystemExit(main())
