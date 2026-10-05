"""Demonstrate V1 regression sensitivity using exclusively owned isolated copies.

Run with the project Python from the repository root. Each control first runs
its unchanged selected test, then changes exactly one copied implementation
needle and requires an actual detecting assertion. The production checkout is
never mutated. Copies and complete raw subprocess captures remain in ignored
locations; neither dependencies nor browser binaries are installed or launched.
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
    language: str
    affected_file: str
    needle: str
    replacement: str
    test_file: str
    test_title: str
    demonstrated_fault: str


CONTROLS = (
    Control("nm_conversion", "typescript", "src/state.ts",
            "Number(input) * scale : NaN;",
            "Number(input) * (scale === 1e-9 ? 1e-3 : scale) : NaN;",
            "tests/state.test.ts", "converts units at editor boundary and preserves ordered colocated preset IDs",
            "Nanometre input is incorrectly multiplied by the millimetre factor."),
    Control("mm_conversion", "typescript", "src/state.ts",
            "Number(input) * scale : NaN;",
            "Number(input) * (scale === 1e-3 ? 1e-9 : scale) : NaN;",
            "tests/state.test.ts", "converts units at editor boundary and preserves ordered colocated preset IDs",
            "Millimetre input is incorrectly multiplied by the nanometre factor."),
    Control("axis_swap", "typescript", "src/mapping.ts",
            "const point = { x: 1000 * x_m, y: -1000 * y_m, z: 100 * z_m };",
            "const point = { x: 1000 * y_m, y: -1000 * x_m, z: 100 * z_m };",
            "tests/mapping.test.ts", "world scale reverses y explicitly while preserving independent z scale",
            "World x and y read the opposite physical axis."),
    Control("vertical_texture_flip", "typescript", "src/detector.ts",
            "const outputRow = reverseRows ? ny - 1 - row : row;",
            "const outputRow = row;",
            "tests/detector.test.ts", "reverses only display rows and does not swap columns",
            "Display texture fails to reverse rows for the explicitly unflipped Three UV mapping."),
    Control("ignored_optical_edit", "typescript", "src/state.ts",
            "(owner as Record<string, unknown>)[key] = value;",
            "(owner as Record<string, unknown>)[key] = (owner as Record<string, unknown>)[key];",
            "tests/state.test.ts", "an optical edit removes the current texture immediately and keeps a labeled old snapshot",
            "A deliberate observation-position edit never changes the submitted scientific candidate."),
    Control("stale_attachment", "typescript", "src/state.ts",
            "currentResult: fresh ? result : null",
            "currentResult: result",
            "tests/state.test.ts", "worker result completed after an edit is retained only at its original specification",
            "An old worker result attaches to the edited draft regardless of revision."),
    Control("duplicate_simulation", "typescript", "src/state.ts",
            "if (this.snapshot.active || this.snapshot.pendingValidation || !this.snapshot.validatedDraft",
            "if (this.snapshot.pendingValidation || !this.snapshot.validatedDraft",
            "tests/state.test.ts", "busy is synchronous: repeated intentional clicks send one frozen specification",
            "Removing the synchronous active-submission guard sends two solver requests."),
    Control("normalization_hides_loss", "typescript", "src/detector.ts",
            "(value - limits.min) / (limits.max - limits.min)",
            "value / (Math.max(...intensity) || 1)",
            "tests/detector.test.ts", "preserves sub-float32 numerical values, clamps colors only and keeps a shared scale",
            "Per-result automatic peak normalization replaces the explicit shared color limits."),
    Control("static_plausible_v0_replacement", "python", "apps/virtual_bench/protocol.py",
            "            intensity = result.observation.intensity",
            "            intensity = np.ones_like(result.observation.intensity)",
            "tests/test_virtual_bench_adapter.py",
            "test_simulation_matches_separate_direct_v0_call_and_calls_once[free]",
            "A plausible constant intensity replaces the actual public-V0 field at transport encoding."),
)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def production_hashes() -> dict[str, str]:
    """Hash all current tracked and unignored paths; ignored copies are excluded."""
    result = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                            cwd=ROOT, capture_output=True, check=True)
    records = {}
    for relative in sorted(set(result.stdout.decode("utf-8").split("\0")) - {""}):
        path = ROOT / relative
        if path.is_file():
            records[relative.replace("\\", "/")] = hashlib.sha256(path.read_bytes()).hexdigest()
    return records


def run_capture(command: list[str], cwd: Path, output: Path, stem: str,
                environment: dict[str, str]) -> tuple[int, str, float]:
    """Keep stdout/stderr unedited, and record exact argv/cwd/exit separately."""
    write_json(output / f"{stem}_command.json", {"argv": command, "cwd": str(cwd),
               "environment_overrides": {key: environment[key] for key in ("NO_COLOR", "FORCE_COLOR") if key in environment}})
    started = time.perf_counter()
    completed = subprocess.run(command, cwd=cwd, env=environment, capture_output=True)
    seconds = time.perf_counter() - started
    (output / f"{stem}_stdout.txt").write_bytes(completed.stdout)
    (output / f"{stem}_stderr.txt").write_bytes(completed.stderr)
    write_json(output / f"{stem}_exit.json", {"exit_code": completed.returncode, "seconds": seconds})
    text = ANSI.sub("", completed.stdout.decode("utf-8", errors="replace")
                    + completed.stderr.decode("utf-8", errors="replace"))
    return completed.returncode, text, seconds


def prepare_copy(control: Control, output: Path, owner: str) -> Path:
    if control.language == "typescript":
        isolated = FRONTEND / ".vitest" / "negative_controls" / owner / control.name
        isolated.mkdir(parents=True, exist_ok=False)
        shutil.copytree(FRONTEND / "src", isolated / "src")
        shutil.copytree(FRONTEND / "tests", isolated / "tests")
        shutil.copy2(FRONTEND / "package.json", isolated / "package.json")
        shutil.copy2(FRONTEND / "tsconfig.json", isolated / "tsconfig.json")
    else:
        isolated = output / control.name / "python_copy"
        isolated.mkdir(parents=True, exist_ok=False)
        (isolated / "apps").mkdir()
        shutil.copy2(ROOT / "apps" / "__init__.py", isolated / "apps" / "__init__.py")
        shutil.copytree(ROOT / "apps" / "virtual_bench", isolated / "apps" / "virtual_bench",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (isolated / "tests").mkdir()
        shutil.copy2(ROOT / control.test_file, isolated / control.test_file)
    return isolated


def command_for(control: Control, isolated: Path, npm: Path) -> list[str]:
    if control.language == "typescript":
        return [str(npm), "--ignore-scripts", "run", "test:unit", "--", "--root", str(isolated),
                "--config", str(FRONTEND / "vitest.config.ts"), "--reporter=verbose",
                control.test_file, "-t", re.escape(control.test_title)]
    # Preload and verify the copied module in the SAME process that runs pytest.
    # The numerical core remains the original installed project source.
    preflight = (
        "from pathlib import Path; import apps.virtual_bench.protocol as p; "
        "import ohlab; import pytest; "
        f"assert Path(p.__file__).resolve() == Path({str(isolated / control.affected_file)!r}).resolve(); "
        f"assert Path(ohlab.__file__).resolve().is_relative_to(Path({str(ROOT / 'src')!r}).resolve()); "
        "print('Copied protocol source:', p.__file__); print('Protected core source:', ohlab.__file__); "
        f"raise SystemExit(pytest.main(['-q', '-p', 'no:cacheprovider', '--import-mode=importlib', "
        f"'-c', {str(ROOT / 'pyproject.toml')!r}, "
        f"{str(isolated / control.test_file)!r} + '::{control.test_title}']))"
    )
    return [str(PYTHON), "-B", "-X", "utf8", "-c", preflight]


def run_controls(output: Path) -> int:
    owner = str(uuid.uuid4())
    npm_found = shutil.which("npm.cmd")
    if not npm_found:
        raise RuntimeError("Existing npm.cmd is unavailable; no installation or fallback is authorized")
    if Path(sys.executable).resolve() != PYTHON.resolve():
        raise RuntimeError(f"Expected project interpreter {PYTHON}; got {sys.executable}")
    if not (FRONTEND / "node_modules" / "vitest").is_dir():
        raise RuntimeError("Reviewed project-local Vitest installation is unavailable")
    environment = os.environ.copy()
    environment["NO_COLOR"] = "1"
    environment["FORCE_COLOR"] = "0"
    before = production_hashes()
    write_json(output / "production_before.json", before)
    records: list[dict[str, object]] = []
    failed = False
    try:
        for control in CONTROLS:
            evidence = output / control.name
            evidence.mkdir(exist_ok=False)
            isolated = prepare_copy(control, output, owner)
            copied_path = isolated / control.affected_file
            source = copied_path.read_text(encoding="utf-8")
            if source.count(control.needle) != 1:
                raise RuntimeError(f"{control.name}: exact mutation needle occurs {source.count(control.needle)} times")
            command = command_for(control, isolated, Path(npm_found))
            child_environment = environment.copy()
            if control.language == "python":
                child_environment["PYTHONPATH"] = os.pathsep.join((str(isolated), str(ROOT)))
            baseline_code, baseline_text, baseline_seconds = run_capture(
                command, isolated, evidence, "baseline", child_environment)
            if baseline_code != 0 or not re.search(r"\b1 passed\b", baseline_text):
                raise RuntimeError(f"{control.name}: selected unchanged test did not pass exactly once; see baseline captures")
            copied_path.write_text(source.replace(control.needle, control.replacement, 1), encoding="utf-8")
            write_json(evidence / "mutation.json", {**asdict(control), "isolated_root": str(isolated),
                       "original_sha256": hashlib.sha256(source.encode()).hexdigest(),
                       "mutated_sha256": hashlib.sha256(copied_path.read_bytes()).hexdigest()})
            mutant_code, mutant_text, mutant_seconds = run_capture(
                command, isolated, evidence, "mutant", child_environment)
            if control.language == "typescript":
                detected = (mutant_code != 0 and "AssertionError" in mutant_text
                            and "FAIL" in mutant_text and control.test_title in mutant_text
                            and Path(control.test_file).name in mutant_text)
            else:
                detected = (mutant_code != 0 and "AssertionError" in mutant_text
                            and control.test_title in mutant_text
                            and 'assert arrays["intensity"].tobytes() == expected.observation.intensity.tobytes()' in mutant_text)
            record = {"name": control.name, "demonstrated_fault": control.demonstrated_fault,
                      "affected_file": control.affected_file, "test_title": control.test_title,
                      "baseline_exit": baseline_code, "mutant_exit": mutant_code,
                      "actual_assertion_detected": detected,
                      "baseline_seconds": baseline_seconds, "mutant_seconds": mutant_seconds}
            records.append(record)
            write_json(output / "summary.json", {"owner": owner, "controls": records, "complete": False})
            print(f"{control.name}: baseline={baseline_code}, mutant={mutant_code}, assertion_detected={detected}", flush=True)
            if not detected:
                raise RuntimeError(f"{control.name}: mutation did not fail the required assertion; setup/import failure is not detection")
    except Exception as exc:
        failed = True
        write_json(output / "failure.json", {"type": type(exc).__name__, "message": str(exc)})
        print(f"STOPPED: {exc}", file=sys.stderr, flush=True)
    finally:
        after = production_hashes()
        write_json(output / "production_after.json", after)
        unchanged = before == after
        if not unchanged:
            failed = True
            write_json(output / "production_difference.json", {
                "changed": [path for path in sorted(before.keys() | after.keys()) if before.get(path) != after.get(path)]})
        complete = not failed and len(records) == len(CONTROLS)
        write_json(output / "summary.json", {"owner": owner, "controls": records,
                   "complete": complete, "production_unchanged": unchanged,
                   "production_path_count": len(before), "production_restore_required": False,
                   "copy_policy": "Owned isolated copies retained; production never mutated; complete suites must be rerun by acceptance workflow."})
        print(f"production_unchanged={unchanged}; detected={sum(bool(r['actual_assertion_detected']) for r in records)}/{len(CONTROLS)}", flush=True)
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="Fresh owned location under repository runs/")
    arguments = parser.parse_args()
    output = arguments.output_dir.resolve()
    runs_root = (ROOT / "runs").resolve()
    if not output.is_relative_to(runs_root) or output == runs_root:
        parser.error("--output-dir must be a fresh child of repository runs/")
    output.mkdir(parents=True, exist_ok=False)
    return run_controls(output)


if __name__ == "__main__":
    raise SystemExit(main())
