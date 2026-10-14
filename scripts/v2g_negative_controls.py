"""V2g intended-assertion fault controls in fresh owned source copies.

Every selected original must pass; each deliberate copied mutation must reach
its named assertion; exact copied-source restoration must pass. Setup/import,
syntax and timeout failures are not detections. Production hashes are verified.
No browser/server starts, dependency installs or production mutations occur.
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
FRONTEND = ROOT / "frontend/bench"
PYTHON = ROOT / ".venv/Scripts/python.exe"
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


def python_controls() -> tuple[Control, ...]:
    """Copied application mutations; unchanged public scientific sources are reused."""
    adapter = "apps/virtual_bench/polarized_two_path_adapter.py"
    protocol = "apps/virtual_bench/polarized_two_path_protocol.py"
    documents = "apps/virtual_bench/experiment_documents.py"
    tests = "tests/test_virtual_bench_polarized_two_path_"
    def variant(name, category, file, needle, replacement, test_kind, title, marker, fault):
        return Control(name, category, "python", file, needle, replacement,
                       tests + test_kind + ".py", title, marker, fault)
    incident = ("return JonesField.from_scalar(scalar, x_coefficient=experiment.coefficients[0],\n"
                "                                  y_coefficient=experiment.coefficients[1])")
    full = "test_complete_public_arrays_axes_norms_histories_and_nonmutation"
    mapping = "test_static_mapping_matches_exact_public_actions_order_parameters_and_common_phase"
    normalization = ("measured = apply_linear_polarizer(raw, axis_angle_rad=experiment.analyzer.axis_angle_rad)\n"
                     "                analyzed_norm = measured.sampled_norm")
    normalized = ("measured = apply_linear_polarizer(raw, axis_angle_rad=experiment.analyzer.axis_angle_rad)\n"
        "                scale = math.sqrt(raw.sampled_norm / measured.sampled_norm)\n"
        "                measured = JonesField(x=type(measured.x)(data=measured.x.data * scale, grid=measured.grid, wavelength_m=measured.wavelength_m),\n"
        "                                      y=type(measured.y)(data=measured.y.data * scale, grid=measured.grid, wavelength_m=measured.wavelength_m))\n"
        "                analyzed_norm = measured.sampled_norm")
    return (
        variant("normalize_coefficients", "coefficient mapping", adapter, incident,
            "scale = math.sqrt(sum(abs(value)**2 for value in experiment.coefficients))\n    "
            + incident.replace("experiment.coefficients[0]", "experiment.coefficients[0] / scale").replace("experiment.coefficients[1]", "experiment.coefficients[1] / scale"),
            "adapter", full, "V2G_DIRECT_PUBLIC_DETECTED", "Normalize arbitrary submitted Jones coefficients before incident construction."),
        variant("swap_polarization_coefficients", "coefficient mapping", adapter, incident,
            incident.replace("experiment.coefficients[0]", "experiment.coefficients[2]").replace("experiment.coefficients[1]", "experiment.coefficients[0]").replace("experiment.coefficients[2]", "experiment.coefficients[1]"),
            "adapter", full, "V2G_DIRECT_PUBLIC_DETECTED", "Exchange x/y coefficient roles while retaining the original specification."),
        variant("drop_terminal_action", "ordered public action mapping", adapter,
            "actions=tuple(action.public_action() for action in self.actions))",
            "actions=tuple(action.public_action() for action in self.actions[:-1]))", "adapter", mapping,
            "V2G_ACTION_MAPPING_DETECTED", "Drop the last declared action from each public arm mapping."),
        variant("reverse_terminal_actions", "ordered public action mapping", adapter,
            "actions=tuple(action.public_action() for action in self.actions))",
            "actions=tuple(action.public_action() for action in reversed(self.actions)))", "adapter", mapping,
            "V2G_ACTION_MAPPING_DETECTED", "Reverse noncommuting terminal actions in the mapped public arms."),
        variant("drop_common_phase", "common phase mapping", adapter,
            "relative_phase_rad=self.relative_phase_rad if phase_rad is None else phase_rad)",
            "relative_phase_rad=0.0)", "analytic", "test_identical_arms_analytic_original_input_fractions",
            "V2G_COMMON_PHASE_DETECTED", "Omit the common extra arm-1 phase from the public specification."),
        variant("negate_retarder_parameter", "ordered public action mapping", adapter,
            "return RetarderAction(axis_angle_rad=self.axis_angle_rad, retardance_rad=self.retardance_rad)",
            "return RetarderAction(axis_angle_rad=self.axis_angle_rad, retardance_rad=-self.retardance_rad)",
            "adapter", mapping, "V2G_ACTION_MAPPING_DETECTED", "Reverse the submitted full public retarder phase parameter."),
        variant("swap_raw_ports", "raw/analyzed role encoding", adapter,
            "raw_images = tuple(output.intensity for output in result.outputs)",
            "raw_images = tuple(output.intensity for output in reversed(result.outputs))", "adapter", full,
            "V2G_DIRECT_PUBLIC_DETECTED", "Exchange actual raw port image roles without changing their labels."),
        variant("analyzed_as_raw", "raw/analyzed role encoding", adapter,
            "raw_images = tuple(output.intensity for output in result.outputs)",
            "raw_images = tuple(output.intensity for output in (analyzed if analyzed is not None else result.outputs))", "adapter", full,
            "V2G_DIRECT_PUBLIC_DETECTED", "Replace raw images with downstream analyzed images while retaining raw labels."),
        variant("intensity_only_analyzer", "analyzer measurement fidelity", adapter,
            "analyzed_images = None if analyzed is None else tuple(output.intensity for output in analyzed)",
            "analyzed_images = None if analyzed is None else tuple(output.intensity * math.cos(experiment.analyzer.axis_angle_rad)**2 for output in result.outputs)",
            "adapter", full, "V2G_ANALYZER_PUBLIC_DETECTED", "Replace phase-sensitive Jones projection images with intensity-only cosine scaling."),
        variant("normalize_analyzer_loss", "analyzer measurement fidelity", adapter, normalization, normalized,
            "analytic", "test_orthogonal_arms_separate_analyzers_retain_projection_loss", "V2G_ANALYZER_LOSS_DETECTED",
            "Rescale each analyzed Jones output to its raw norm, erasing the measured downstream loss."),
        variant("duplicate_single_runner", "actual computation count", adapter,
            "result = run_polarized_two_arm(incident, spec=experiment.public_spec(phase_rad))",
            "run_polarized_two_arm(incident, spec=experiment.public_spec(phase_rad))\n    result = run_polarized_two_arm(incident, spec=experiment.public_spec(phase_rad))",
            "adapter", "test_single_exact_public_orchestration_count", "V2G_SINGLE_CALLS_DETECTED", "Run the unchanged public V2f solver twice for one single intent."),
        variant("fabricate_sweep_from_first_phase", "actual computation count", adapter,
            "result, norms, diagnostics, analysis, analyzed = _measure(incident, submission.experiment, phase)",
            "result, norms, diagnostics, analysis, analyzed = _measure(incident, submission.experiment, 0.0)",
            "adapter", "test_sweep_seventeen_actual_public_rows_one_incident_and_independent_endpoints", "V2G_SWEEP_CALLS_DETECTED",
            "Calculate every reported sweep row at zero phase while preserving the requested phase labels."),
        variant("duplicate_final_endpoint", "actual computation count", adapter,
            "result, norms, diagnostics, analysis, analyzed = _measure(incident, submission.experiment, phase)",
            "result, norms, diagnostics, analysis, analyzed = _measure(incident, submission.experiment, 0.0 if index == 16 else phase)",
            "adapter", "test_sweep_seventeen_actual_public_rows_one_incident_and_independent_endpoints", "V2G_SWEEP_CALLS_DETECTED",
            "Use the first endpoint phase for the last labeled endpoint instead of calculating 2*pi independently."),
        variant("false_completed_prefix_count", "atomic failed sweep", protocol,
            '"completed_count": len(rows), "failed_index": failed_index, "rows": rows, "error": error}',
            '"completed_count": len(rows) + (1 if failed else 0), "failed_index": failed_index, "rows": rows, "error": error}',
            "server", "test_actual_sweep_prefix_http_status_and_genuine_rows", "V2G_HTTP_PREFIX_DETECTED",
            "Count the failed measurement point as completed despite retaining only its genuine preceding rows."),
        variant("release_server_gate_early", "actual worker lifetime", "apps/virtual_bench/server.py",
            "future.add_done_callback(self._completed)\n        return future",
            "future.add_done_callback(self._completed)\n        self._completed(future)\n        return future",
            "server", "test_abort_keeps_actual_worker_gate_until_terminal_completion[disconnect-polarized_two_path]",
            "V2G_WORKER_LIFETIME_DETECTED", "Release the shared computation reservation immediately after submission, before the actual worker terminates."),
        variant("accept_new_mode_as_v1", "document version policy", documents,
            "if version == DOCUMENT_VERSION:", 'if version == DOCUMENT_VERSION and mode != "polarized_two_path":',
            "documents", "test_exact_version_mode_acceptance_matrix_and_error_codes", "V2G_DOCUMENT_VERSION_DETECTED",
            "Route a new-mode version-1 document through the new-mode branch instead of rejecting its mode/version pair."),
        variant("rewrite_legacy_exports_as_v2", "document version policy", documents,
            'owned = {"document_format": DOCUMENT_FORMAT, "document_version": version,',
            'owned = {"document_format": DOCUMENT_FORMAT, "document_version": 2,',
            "documents", "test_old_v1_bytes_match_pre_edit_frozen_canonical_hashes", "V2G_LEGACY_CANONICAL_DETECTED",
            "Rewrite accepted old version-1 canonical exports as version 2, violating pre-edit frozen byte identities."),
    )


def frontend_controls() -> tuple[Control, ...]:
    """Result-only release variants join protocol and scientific identity faults."""
    state = "src/polarized_two_path_state.ts"
    documents = "src/experiment_documents.ts"
    tests = "tests/polarized_two_path_"
    def variant(name, category, file, needle, replacement, kind, title, marker, fault):
        return Control(name, category, "typescript", file, needle, replacement, tests + kind + ".test.ts", title, marker, fault)
    edit = ("pendingValidation: false, pendingSweepValidation: false, revision: this.snapshot.revision + 1, currentResult: null, currentSweep: null, error: null, renderError: null });")
    release = "this.publish({ lastResult: null, currentResult: null, completedNumerical: null, lastSweep: null, currentSweep: null,"
    admission = "try { this.beforeOperation('single', active.experiment); } catch (error) { this.publish({ error: messageOf(error) }); return false; }"
    return (
        variant("analyzer_edit_as_view_only", "scientific identity and atomic state", state, edit,
            "pendingValidation: false, pendingSweepValidation: false, revision: this.snapshot.revision, currentResult: this.snapshot.currentResult, currentSweep: this.snapshot.currentSweep, error: null, renderError: null });",
            "state", "analyzer enablement and saved angle are scientific edits, not presentation switches", "PT_ANALYZER_EDIT_SCIENTIFIC",
            "Keep scientific revision and attached results unchanged after a saved analyzer-angle edit."),
        variant("attach_stale_pair", "scientific identity and atomic state", state,
            "if (!this.fresh(active)) { this.publish({ active: null, completedNumerical: result, currentResult: null }); return true; }",
            "if (!this.fresh(active)) { this.publish({ active: null, completedNumerical: result, currentResult: result }); return true; }",
            "state", "late and away/back outcomes never attach to another draft", "PT_STALE_PAIR_DETECTED",
            "Attach a late numerical pair after mode departure and reentry instead of retaining it only as an ineligible completion."),
        variant("publish_after_presentation_failure", "scientific identity and atomic state", state,
            "if (generation === this.resultsGeneration) this.publish({ active: null, completedNumerical: result, renderError: message }); return false;",
            "if (generation === this.resultsGeneration) this.publish({ active: null, currentResult: result, completedNumerical: result, renderError: message }); return false;",
            "state", "keeps prior whole presentation on late preparation failure and retries without science", "PT_ATOMIC_PAIR_DETECTED",
            "Relabel a new failed-presentation outcome as the current whole result while old presentation resources remain."),
        variant("release_hides_but_retains_buffers", "explicit result release", state, release,
            "this.publish({ lastResult: this.snapshot.lastResult, currentResult: null, completedNumerical: this.snapshot.completedNumerical, lastSweep: null, currentSweep: null,",
            "state", "release drops every retained result/recovery/sweep owner and explicit retry handles", "PT_RELEASE_BUFFER_OWNERS",
            "Hide current results while retaining numerical backing owners and a completed presentation-retry handle."),
        variant("released_callback_reattaches", "explicit result release", state,
            "const eligible = () => generation === this.resultsGeneration && revision === this.snapshot.revision",
            "const eligible = () => revision === this.snapshot.revision",
            "state", "an old delayed presentation cannot resurrect explicitly released numerics", "PT_RELEASE_DELAYED_PRESENTATION",
            "Remove result-generation eligibility so an old prepared callback can resurrect explicitly released numerical data."),
        variant("release_resets_scientific_revision", "explicit result release", state, release,
            "this.publish({ revision: this.snapshot.revision + 1, lastResult: null, currentResult: null, completedNumerical: null, lastSweep: null, currentSweep: null,",
            "state", "all four controllers preserve exact valid and invalid drafts and identity during repeated release", "PT_RELEASE_DRAFT_PRESERVATION",
            "Change scientific draft revision during result-only release, invalidating preserved document context."),
        variant("implicit_eviction_after_budget_rejection", "fixed-budget rejection and recovery", state, admission,
            "try { this.beforeOperation('single', active.experiment); } catch (error) { this.releaseResults(); this.publish({ error: messageOf(error) }); return false; }",
            "state", "budget rejection retains old outcomes with no eviction or retry; release permits a later deliberate run", "PT_BUDGET_NO_EVICTION_RETRY",
            "Automatically evict retained numerical data when admission rejects an operation."),
        variant("automatic_retry_after_budget_rejection", "fixed-budget rejection and recovery", state, admission,
            "try { this.beforeOperation('single', active.experiment); } catch (error) { this.publish({ error: messageOf(error) }); void this.api.simulate(envelope); return false; }",
            "state", "budget rejection retains old outcomes with no eviction or retry; release permits a later deliberate run", "PT_BUDGET_NO_EVICTION_RETRY",
            "Issue an invisible scientific request despite a fixed-budget rejection."),
        variant("drop_disabled_document_angle", "document inactive-setting fidelity", documents,
            "model_contract: POLARIZED_TWO_PATH_DOCUMENT_MODEL, experiment: structuredClone(data.experiment), metadata });",
            "model_contract: POLARIZED_TWO_PATH_DOCUMENT_MODEL, experiment: { ...structuredClone(data.experiment), analyzer: { ...data.experiment.analyzer, axis_angle_rad: data.experiment.analyzer.enabled ? data.experiment.analyzer.axis_angle_rad : 0 } }, metadata });",
            "documents", "retains every exact setting with analyzer enabled=", "PT_DISABLED_DOCUMENT_ANGLE",
            "Replace a disabled analyzer's authoritative saved angle with zero when owning/exporting/importing the new document."),
    )


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False, ensure_ascii=False) + "\n")


def production_hashes() -> dict[str, str]:
    # Root separately verifies the complete frozen inventory. Executables and
    # dependency declarations are frozen; concurrently authored docs are excluded.
    paths = {Path(__file__).resolve()}
    paths.update((ROOT / "src/ohlab").rglob("*.py"))
    for folder, pattern in (("apps", "*.py"), ("tests", "*.py"), ("scripts", "*.py"),
                            ("frontend/bench/src", "*"), ("frontend/bench/tests", "*.ts")):
        paths.update(path for path in (ROOT / folder).rglob(pattern) if path.is_file())
    paths.update(ROOT / name for name in ("pyproject.toml", "frontend/bench/package.json", "frontend/bench/package-lock.json"))
    for control in python_controls() + frontend_controls():
        base = FRONTEND if control.language == "typescript" else ROOT
        paths.update((base / control.affected_file, base / control.test_file))
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths) if path.is_file()}


def prepare_copy(control: Control, output: Path, owner: str) -> Path:
    if control.language == "typescript":
        isolated = FRONTEND / ".vitest/v2g_negative_controls" / owner / control.name
        isolated.mkdir(parents=True, exist_ok=False)
        for name in ("src", "tests"): shutil.copytree(FRONTEND / name, isolated / name)
        for name in ("package.json", "tsconfig.json"): shutil.copy2(FRONTEND / name, isolated / name)
        (isolated / "vitest.control.config.mjs").write_text(
            "export default {cacheDir:" + json.dumps(str(isolated / ".cache").replace("\\", "/"))
            + ",test:{environment:'node',include:['tests/**/*.test.ts'],maxWorkers:1}};\n", encoding="utf-8")
    else:
        isolated = output / control.name / "python_copy"
        (isolated / "apps").mkdir(parents=True, exist_ok=False)
        shutil.copy2(ROOT / "apps/__init__.py", isolated / "apps/__init__.py")
        shutil.copytree(ROOT / "apps/virtual_bench", isolated / "apps/virtual_bench", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (isolated / "tests").mkdir()
        for path in sorted((ROOT / "tests").glob("test_virtual_bench*.py")):
            shutil.copy2(path, isolated / "tests" / path.name)
    return isolated


def command_for(control: Control, isolated: Path, node: str, phase: str) -> list[str]:
    if control.language == "typescript":
        return [node, str(FRONTEND / "node_modules/vitest/vitest.mjs"), "run", "--root", str(isolated),
                "--config", str(isolated / "vitest.control.config.mjs"), "--configLoader", "native", "--cache=false", "--reporter=verbose",
                control.test_file, "-t", re.escape(control.test_title)]
    selected = ["-q", "-p", "no:cacheprovider", "--import-mode=importlib", f"--basetemp={isolated / ('pytest_' + phase)}",
                "-c", str(ROOT / "pyproject.toml"), f"{isolated / control.test_file}::{control.test_title}"]
    module = control.affected_file.removesuffix(".py").replace("/", ".")
    actual = isolated / control.affected_file
    source = "\n".join(("from pathlib import Path", "import importlib,sys,pytest,ohlab",
        f"sys.path.insert(0,{str(isolated / 'tests')!r})", "class SourceProbe:", "    def pytest_configure(self,config):",
        f"        module=importlib.import_module({module!r})", f"        assert Path(module.__file__).resolve()==Path({str(actual)!r}).resolve()",
        f"        assert Path(ohlab.__file__).resolve().is_relative_to(Path({str(ROOT / 'src')!r}).resolve())",
        "        print('Copied integration source:',module.__file__)", "        print('Protected numerical source:',ohlab.__file__)",
        f"raise SystemExit(pytest.main({selected!r},plugins=[SourceProbe()]))"))
    return [str(PYTHON), "-B", "-X", "utf8", "-c", source]


def capture(command: list[str], cwd: Path, output: Path, label: str, environment: dict[str, str]) -> tuple[int, str]:
    write_json(output / f"{label}_command.json", {"argv": command, "cwd": str(cwd), "child_only_overrides":
        {key: environment[key] for key in ("NO_COLOR", "FORCE_COLOR", "PYTHONDONTWRITEBYTECODE")}})
    started = time.perf_counter()
    try:
        result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, timeout=60)
    except subprocess.TimeoutExpired as exc:
        (output / f"{label}_stdout.txt").write_bytes(exc.stdout or b"")
        (output / f"{label}_stderr.txt").write_bytes(exc.stderr or b"")
        write_json(output / f"{label}_exit.json", {"exit_code": None, "timeout_s": 60, "wall_s": time.perf_counter() - started})
        raise RuntimeError(f"{label} timed out; timeout is not fault detection") from exc
    (output / f"{label}_stdout.txt").write_bytes(result.stdout)
    (output / f"{label}_stderr.txt").write_bytes(result.stderr)
    write_json(output / f"{label}_exit.json", {"exit_code": result.returncode, "wall_s": time.perf_counter() - started})
    return result.returncode, ANSI.sub("", result.stdout.decode("utf-8", errors="replace") + result.stderr.decode("utf-8", errors="replace"))


def selected_passed(code: int, output: str) -> bool:
    return code == 0 and bool(re.search(r"\b[1-9]\d* (?:passed|passing)\b", output))


def intended_failure(control: Control, code: int, output: str) -> bool:
    diagnostic = re.compile(r"^(?:E\s+.*|AssertionError:.*|Failed:.*)" + re.escape(control.assertion_marker), re.MULTILINE)
    return (code != 0 and diagnostic.search(output) is not None and control.test_title.split("[")[0] in output
            and ("AssertionError" in output or "Failed: " + control.assertion_marker in output)
            and not any(value in output for value in ("ERROR collecting", "INTERNALERROR", "SyntaxError", "Failed to load url", "Cannot find module")))


def run_controls(output: Path, requested: list[str] | None = None) -> int:
    controls = python_controls() + frontend_controls()
    if not controls: raise RuntimeError("Control anchors are not complete; an empty run is not acceptance")
    if requested:
        unknown = set(requested) - {control.name for control in controls}
        if unknown: raise ValueError(f"Unknown named controls: {sorted(unknown)}")
        controls = tuple(control for control in controls if control.name in requested)
    node = shutil.which("node.exe") or shutil.which("node")
    if not node or not (FRONTEND / "node_modules/vitest/vitest.mjs").is_file():
        raise RuntimeError("Existing installed Node/Vitest unavailable; no install/fallback authorized")
    environment = os.environ.copy()
    environment.update(NO_COLOR="1", FORCE_COLOR="0", PYTHONDONTWRITEBYTECODE="1")
    owner = uuid.uuid4().hex; before = production_hashes(); write_json(output / "production_before.json", before)
    records, failure = [], None
    try:
        for control in controls:
            destination = output / control.name; destination.mkdir(exist_ok=False)
            isolated = prepare_copy(control, output, owner); path = isolated / control.affected_file
            original = path.read_bytes(); source = original.decode("utf-8").replace("\r\n", "\n")
            if source.count(control.needle) != 1:
                raise RuntimeError(f"{control.name}: mutation anchor must occur exactly once, found {source.count(control.needle)}")
            child = environment.copy()
            if control.language == "python": child["PYTHONPATH"] = os.pathsep.join((str(isolated), str(ROOT)))
            baseline_code, baseline_output = capture(command_for(control, isolated, node, "baseline"), isolated, destination, "baseline", child)
            if not selected_passed(baseline_code, baseline_output): raise RuntimeError(f"{control.name}: selected original did not pass")
            try:
                path.write_text(source.replace(control.needle, control.replacement, 1), encoding="utf-8")
                write_json(destination / "mutation.json", {**asdict(control), "isolated_root": str(isolated),
                    "original_sha256": hashlib.sha256(original).hexdigest(), "fault_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
                fault_code, fault_output = capture(command_for(control, isolated, node, "fault"), isolated, destination, "fault", child)
                intended = intended_failure(control, fault_code, fault_output)
            finally:
                path.write_bytes(original)
            restored_code, restored_output = capture(command_for(control, isolated, node, "restored"), isolated, destination, "restored", child)
            record = {"name": control.name, "category": control.category, "baseline_exit": baseline_code, "fault_exit": fault_code,
                      "intended_assertion_detected": intended, "copied_source_restored_exactly": path.read_bytes() == original,
                      "restored_exit": restored_code, "restored_passed": selected_passed(restored_code, restored_output),
                      "fault_failed_cases": [int(value) for value in re.findall(r"\b(\d+) failed\b", fault_output)]}
            records.append(record)
            write_json(output / f"progress_{len(records):02d}.json", {"owner": owner, "complete": False, "controls": records})
            print(f"{control.name}: original={baseline_code}, fault={fault_code}, intended_assertion={intended}, restored={restored_code}", flush=True)
            if not intended or not record["copied_source_restored_exactly"] or not record["restored_passed"]:
                raise RuntimeError(f"{control.name}: intended assertion/restoration gate failed; setup failures are not detections")
    except Exception as exc:
        failure = {"type": type(exc).__name__, "message": str(exc)}; write_json(output / "failure.json", failure)
        print(f"STOPPED: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
    after = production_hashes(); write_json(output / "production_after.json", after)
    unchanged = before == after; complete = failure is None and unchanged and len(records) == len(controls)
    write_json(output / "summary.json", {"owner": owner, "complete": complete, "controls": records, "requested_subset": requested,
        "detected_variants": sum(record["intended_assertion_detected"] for record in records), "variant_count": len(controls),
        "category_count": len({control.category for control in controls}), "production_unchanged": unchanged,
        "production_hash_scope": "all src/ohlab/apps/tests/scripts Python, frontend src and tests, pyproject and frontend package/lock; concurrently authored documentation excluded and complete inventory checked separately by root",
        "failure": failure})
    print(f"production_unchanged={unchanged}; intended_variants={sum(record['intended_assertion_detected'] for record in records)}/{len(controls)}", flush=True)
    return 0 if complete else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--only", action="append", help="Explicit named diagnostic subset; omitted means all declared controls")
    args = parser.parse_args(); output = args.output_dir.resolve()
    if Path(sys.executable).resolve() != PYTHON.resolve(): parser.error("Use existing repository interpreter")
    if output.exists() or output == ROOT / "runs" or not output.is_relative_to(ROOT / "runs"):
        parser.error("Use a fresh owned ignored directory under repository runs")
    output.mkdir(parents=True, exist_ok=False)
    return run_controls(output, args.only)


if __name__ == "__main__":
    raise SystemExit(main())
