"""Named integration/display faults in owned isolated copies, never production.

Every selected original must pass, its isolated fault must reach the intended
named assertion, and exact byte restoration must pass again. Import/setup,
warning, timeout and unrelated protocol failures are not detections. This
tool starts neither a browser nor a service and installs no packages.
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


ADAPTER = "apps/virtual_bench/polarization_adapter.py"
ADAPTER_TEST = "tests/test_virtual_bench_polarization_adapter.py"
ARCHITECTURE_TEST = "tests/test_virtual_bench_polarization_architecture.py"
SWEEP_TEST = "test_sweep_104_public_calls_restarts_incident_and_rows_are_actual_full_train"
LITERAL_TEST = "test_literal_qwp_hwp_order_and_preserved_complex_common_phase"
LOSS_TEST = "test_arbitrary_coefficients_use_jones_denominator_and_actual_loss_and_angle_sign"
FABRICATED_ROWS = '''            # Deliberate isolated fault: genuine calls followed by fabricated scalar rows.
            for j, stage in enumerate(stages[1:], 1):
                previous = stages[j - 1]["norm"]
                stage["norm"] = stages[0]["norm"] * __import__("math").cos(angle) ** 2
                stage["previous_norm"] = previous
                stage["delta_norm"] = stage["norm"] - previous
                stage["adjacent_transmission_ratio"] = None if previous == 0 else stage["norm"] / previous
                stage["incident_transmission_ratio"] = None if stages[0]["norm"] == 0 else stage["norm"] / stages[0]["norm"]
'''


def python_controls() -> tuple[Control, ...]:
    return (
        Control("swapped_complex_components", "component_swap", "python", ADAPTER,
            'getattr(field, name).data[experiment.row, experiment.column]',
            'getattr(field, "y" if name == "x" else "x").data[experiment.row, experiment.column]',
            ADAPTER_TEST, LITERAL_TEST, "COMPLEX_PHASE_DETECTED", "Swap x/y readout components while retaining submitted identities."),
        Control("erased_imaginary_component", "imaginary_phase", "python", ADAPTER,
            'return {"re": float(value.real), "im": float(value.imag)}',
            'return {"re": float(value.real), "im": 0.0}', ADAPTER_TEST, LITERAL_TEST,
            "COMPLEX_PHASE_DETECTED", "Discard the genuine QWP imaginary component in transport."),
        Control("reversed_axis_sign", "angle_sign", "python", ADAPTER,
            'return apply_linear_polarizer(field, axis_angle_rad=axis)',
            'return apply_linear_polarizer(field, axis_angle_rad=-axis)', ADAPTER_TEST, LOSS_TEST,
            "ANGLE_SIGN_DETECTED", "Negate the declared +x toward +y element angle."),
        Control("scalar_envelope_denominator", "incident_denominator", "python", ADAPTER,
            '"incident_transmission_ratio": transmission_ratio(incident, field)}',
            '"incident_transmission_ratio": transmission_ratio(incident, field) if element is None else field.sampled_norm / sample_source(experiment.source_plane).power}',
            ADAPTER_TEST, LOSS_TEST, "JONES_DENOMINATOR_DETECTED", "Normalize downstream ratios by the scalar envelope, hiding arbitrary coefficient scaling."),
        Control("source_common_phase_reset", "common_phase_source", "python", ADAPTER,
            '    scalar = sample_source(experiment.source_plane)',
            '    source = experiment.source_plane.to_dict()\n    source["source"]["phase_rad"] = 0.0\n    scalar = sample_source(SequentialExperiment.from_dict(source))',
            ADAPTER_TEST, LITERAL_TEST, "COMMON_PHASE_RESET_DETECTED", "Erase submitted source common phase before constructing Jones components."),
        Control("duplicated_single_sampling", "duplicate_single", "python", ADAPTER,
            '        incident = _incident(experiment)',
            '        _incident(experiment)\n        incident = _incident(experiment)', ADAPTER_TEST,
            "test_single_samples_and_constructs_once_then_exact_element_count", "SINGLE_CALL_COUNT_DETECTED",
            "One intentional single operation samples and constructs twice."),
        Control("duplicated_sweep_train", "duplicate_sweep", "python", ADAPTER,
            '            final, stages = _run_train(incident, submission.experiment,',
            '            _run_train(incident, submission.experiment, selected_element_id=submission.selected_element_id, axis_angle_rad=angle, include_samples=False)\n            final, stages = _run_train(incident, submission.experiment,',
            ADAPTER_TEST, SWEEP_TEST, "SWEEP_CALL_COUNT_DETECTED", "Invoke every full train twice, yielding208 rather than104 actual public actions."),
        Control("cumulative_sweep", "sweep_restart", "python", ADAPTER,
            '            del final\n', '            incident = final\n', ADAPTER_TEST, SWEEP_TEST,
            "SWEEP_RESTART_INCIDENT_DETECTED", "Start each angle from the preceding final field instead of the original incident."),
        Control("fabricated_cos_squared_sweep", "fabricated_sweep", "python", ADAPTER,
            '            rows.append({"index": index, "axis_angle_rad": angle, "stages": stages,',
            FABRICATED_ROWS + '            rows.append({"index": index, "axis_angle_rad": angle, "stages": stages,',
            ADAPTER_TEST, SWEEP_TEST, "SWEEP_GENUINE_ROWS_DETECTED", "Replace genuine full-train stage scalars with a cos-squared curve despite104 real calls."),
        Control("broadened_architecture_allowlist", "architecture_allowlist", "python", "tests/test_virtual_bench_architecture.py",
            'if path.name == "polarization_adapter.py" else set()', 'if True else set()',
            ARCHITECTURE_TEST, "test_guard_rejects_broadened_dependency_elsewhere", "ARCHITECTURE_ALLOWLIST_DETECTED",
            "Permit the otherwise legitimate polarization module in unauthorized backend files."),
        Control("private_numerical_import", "architecture_private", "python", ADAPTER,
            'from ohlab.optics import SequentialExperiment, sample_source',
            'from ohlab.optics import SequentialExperiment, sample_source\nfrom ohlab.optics.polarization import _geometry',
            ARCHITECTURE_TEST, "test_polarization_adapter_imports_public_operations_and_duplicates_no_solver", "PRIVATE_IMPORT_DETECTED",
            "Import a forbidden private numerical helper through the adapter."),
        Control("private_import_elsewhere", "architecture_private", "python", "apps/virtual_bench/server.py",
            'from __future__ import annotations',
            'from __future__ import annotations\nfrom ohlab.optics.polarization import _geometry',
            ARCHITECTURE_TEST, "test_all_backend_files_import_only_public_scientific_symbols", "PRIVATE_IMPORT_ELSEWHERE_DETECTED",
            "Import an existing private numerical helper in an otherwise ordinary backend module."),
        Control("premature_disconnect_gate_release", "worker_lifetime", "python", "apps/virtual_bench/server.py",
            '        if disconnected in done:\n            return None',
            '        if disconnected in done:\n            request.app.state.gate._completed(future)\n            return None',
            "tests/test_virtual_bench_polarization_server.py",
            "test_abort_holds_gate_for_every_actual_worker_until_terminal_completion[disconnect-polarization]",
            "WORKER_LIFETIME_DETECTED", "Release the one worker gate at HTTP disconnect while real Python work remains blocked."),
    )


def frontend_controls() -> tuple[Control, ...]:
    display = "src/polarization_display.ts"
    state = "src/polarization_state.ts"
    display_test = "tests/polarization_display.test.ts"
    state_test = "tests/polarization_state.test.ts"
    freshness = '''    return this.snapshot.revision === active.revision && this.snapshot.attachmentEpoch === active.attachmentEpoch
      && !this.snapshot.pendingValidation && !Object.keys(this.snapshot.invalidEdits).length && structuralEqual(this.snapshot.validatedDraft, active.experiment);'''
    return (
        Control("axis_degree_conversion", "angle_units", "typescript", state,
            'value = numericText.test(trimmed) ? Number(trimmed) : NaN;',
            'value = numericText.test(trimmed) ? Number(trimmed) * (path.includes("axis_angle_rad") ? Math.PI / 180 : 1) : NaN;',
            state_test, "keeps authoritative signed radians and arbitrary coefficients, invalidates on invalid text without computing",
            "UNIT_AXIS_DETECTED", "Treat authoritative entered radians as degrees before submission."),
        Control("display_common_phase_reset", "common_phase_display", "typescript", display,
            '  const c = Math.cos(tau), s = Math.sin(tau);',
            '  tau -= Math.atan2(sample.x.im, sample.x.re);\n  const c = Math.cos(tau), s = Math.sin(tau);',
            display_test, "preserves common phase at shared fixed tau with independent marker expectations",
            "DISPLAY_COMMON_PHASE_FIXED_TAU", "Erase common phase when showing the actual sample at the same fixed tau."),
        Control("intensity_underflow_dark", "exact_dark", "typescript", display,
            '  return sample.x.re === 0 && sample.x.im === 0 && sample.y.re === 0 && sample.y.im === 0;',
            '  return sample.x.re ** 2 + sample.x.im ** 2 + sample.y.re ** 2 + sample.y.im ** 2 === 0;',
            display_test, "classifies exact dark from all complex parts while nonzero tiny intensity-underflow samples remain nonzero",
            "DISPLAY_NONZERO_TINY_NOT_DARK", "Relabel a nonzero1e-200 returned sample dark because its squared intensity underflows."),
        Control("obsolete_animation_callback", "animation_teardown", "typescript", display,
            'detach(): void { ++this.generation; this.update = null; this.playing = false; this.previousTime = null; }',
            'detach(): void { ++this.generation; this.playing = false; this.previousTime = null; }',
            display_test, "owns exactly one callback, stops obsolete trajectory updates and never schedules animation itself",
            "ANIMATION_TEARDOWN_DETECTED", "Keep an obsolete callback after detach so later play revives detached trajectory updates."),
        Control("per_stage_amplitude_normalization", "loss_display_scale", "typescript", display,
            '      const x = marker.x / commonAmplitudeScale * gain, y = marker.y / commonAmplitudeScale * gain;',
            '      const ownScale = Math.max(Math.abs(stage.sample.x.re), Math.abs(stage.sample.x.im), Math.abs(stage.sample.y.re), Math.abs(stage.sample.y.im)) || 1;\n      const x = marker.x / ownScale * gain, y = marker.y / ownScale * gain;',
            display_test, "uses equal shared scales and retains loss rather than normalizing each trajectory or intensity",
            "POLARIZER_LOSS_SHARED_SCALE", "Normalize every stage to its own amplitude and visually conceal actual polarizer loss."),
        Control("per_image_peak_normalization", "loss_display_scale", "typescript", display,
            'const texture = (factories.texture ?? createArrayDetectorTexture)(intensity, result.experiment.grid, limits);',
            'const texture = (factories.texture ?? createArrayDetectorTexture)(intensity, result.experiment.grid, { min: 0, max: Math.max(...intensity) });',
            display_test, "prepares actual paired resources with one declared shared intensity range and unchanged raw values",
            "POLARIZER_LOSS_SHARED_SCALE", "Use a separate measured maximum for each actual intensity texture instead of the declared common range."),
        Control("cross_mode_epoch_ignored", "cross_mode_identity", "typescript", state,
            freshness, freshness.replace(' && this.snapshot.attachmentEpoch === active.attachmentEpoch', ''),
            state_test, "away-and-back generation rejects late attachment and leaves the gate held until settlement",
            "CROSS_MODE_STALE_DETECTED", "Attach a late result after leaving and returning to the same unchanged experiment."),
        Control("edited_sample_identity_ignored", "sample_identity", "typescript", state,
            freshness,
            '    return this.snapshot.attachmentEpoch === active.attachmentEpoch && !this.snapshot.pendingValidation && !Object.keys(this.snapshot.invalidEdits).length;',
            state_test, "new sample edit cannot relabel held or earlier completed complex samples",
            "SAMPLE_IDENTITY_DETECTED", "Ignore the readout revision and full experiment identity when a held older sample finishes."),
        Control("duplicated_browser_submission", "duplicate_single", "typescript", state,
            '      const result = decodePolarizationResult(await this.api.simulate(envelope), envelope);',
            '      const result = decodePolarizationResult(await this.api.simulate(envelope), envelope);\n      await this.api.simulate(envelope);',
            state_test, "acquires the actual shared slot synchronously and rejects rapid duplicates across all modes",
            "DUPLICATE_OPERATION_DETECTED", "Send a second actual API request after decoding one intentional operation."),
        Control("late_resource_partial_cleanup", "atomic_resources", "typescript", display,
            '  const disposePartial = () => { textures.forEach(texture =>',
            '  const disposePartial = () => { textures.slice(1).forEach(texture =>',
            display_test, "cleans every prepared resource on later trajectory failure before publication",
            "ATOMIC_LATE_RESOURCE_DETECTED", "Leak the first already prepared texture when the later trajectory resource fails."),
        Control("premature_presentation_publication", "atomic_resources", "typescript", state,
            'currentResult: previous && structuralEqual(previous.experiment, result.experiment) ? previous : null, renderError: message',
            'currentResult: result, renderError: message',
            state_test, "keeps prior complete presentation atomic on later failure and retries only display explicitly",
            "ATOMIC_LATE_RESOURCE_DETECTED", "Publish the new result identity despite a failed presentation commit."),
        Control("view_selection_revalidates", "passive_view", "typescript", state,
            '    this.publish({ selection: id });',
            '    this.publish({ selection: id }); void this.validateCandidate();',
            state_test, "initial validation and viewing stage/selection/errors never compute or revalidate",
            "VIEW_ACTION_NO_OPTICS", "Revalidate the optical specification when only selecting an existing element."),
        Control("animation_sends_optics", "passive_view", "typescript", display,
            '    this.previousTime = time; ++this.ticks; this.update(this.tau);',
            '    void fetch("/api/v2d/simulate", { method: "POST" });\n    this.previousTime = time; ++this.ticks; this.update(this.tau);',
            display_test, "owns exactly one callback, stops obsolete trajectory updates and never schedules animation itself",
            "VIEW_ACTION_NO_OPTICS", "Send a scientific request from a display-only animation tick; the unit captures fetch without network."),
    )


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def production_hashes() -> dict[str, str]:
    result = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT, capture_output=True, check=True)
    return {relative.replace("\\", "/"): hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            for relative in sorted(set(result.stdout.decode().split("\0")) - {""}) if (ROOT / relative).is_file()}


def prepare_copy(control: Control, output: Path, owner: str) -> Path:
    if control.language == "typescript":
        isolated = FRONTEND / ".vitest/v2d_negative_controls" / owner / control.name
        isolated.mkdir(parents=True, exist_ok=False)
        for name in ("src", "tests"): shutil.copytree(FRONTEND / name, isolated / name)
        for name in ("package.json", "tsconfig.json"): shutil.copy2(FRONTEND / name, isolated / name)
        # Plain config avoids an incidental configuration-bundler subprocess;
        # the installed test policy/environment/worker count are unchanged.
        (isolated / "vitest.control.config.mjs").write_text(
            "export default {cacheDir:" + json.dumps(str(isolated / ".cache").replace("\\", "/"))
            + ",test:{environment:'node',include:['tests/**/*.test.ts'],maxWorkers:1}};\n", encoding="utf-8")
    else:
        isolated = output / control.name / "python_copy"
        (isolated / "apps").mkdir(parents=True, exist_ok=False)
        shutil.copy2(ROOT / "apps/__init__.py", isolated / "apps/__init__.py")
        shutil.copytree(ROOT / "apps/virtual_bench", isolated / "apps/virtual_bench", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (isolated / "tests").mkdir()
        for path in sorted((ROOT / "tests").glob("test_virtual_bench*.py")): shutil.copy2(path, isolated / "tests" / path.name)
    return isolated


def command_for(control: Control, isolated: Path, node: str) -> list[str]:
    if control.language == "typescript":
        return [node, str(FRONTEND / "node_modules/vitest/vitest.mjs"), "run", "--root", str(isolated),
                "--config", str(isolated / "vitest.control.config.mjs"), "--reporter=verbose", control.test_file, "-t", re.escape(control.test_title)]
    selected = ["-q", "-p", "no:cacheprovider", "--import-mode=importlib", f"--basetemp={isolated / 'pytest_temp'}", "-c", str(ROOT / "pyproject.toml"),
                f"{isolated / control.test_file}::{control.test_title}"]
    affected = control.affected_file
    module = affected.removesuffix(".py").replace("/", ".") if affected.startswith("apps/") else "test_virtual_bench_architecture"
    actual = isolated / affected
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
    start = time.perf_counter()
    result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, timeout=60)
    (output / f"{label}_stdout.txt").write_bytes(result.stdout); (output / f"{label}_stderr.txt").write_bytes(result.stderr)
    write_json(output / f"{label}_exit.json", {"exit_code": result.returncode, "wall_s": time.perf_counter() - start})
    return result.returncode, ANSI.sub("", result.stdout.decode("utf-8", errors="replace") + result.stderr.decode("utf-8", errors="replace"))


def selected_passed(code: int, text: str) -> bool:
    return code == 0 and bool(re.search(r"\b[1-9]\d* (?:passed|passing)\b", text))


def run_controls(output: Path, requested: list[str] | None = None) -> int:
    if Path(sys.executable).resolve() != PYTHON.resolve(): raise RuntimeError("Use the existing repository interpreter")
    controls = python_controls() + frontend_controls()
    if requested:
        unknown = set(requested) - {item.name for item in controls}
        if unknown: raise ValueError(f"Unknown named controls: {sorted(unknown)}")
        controls = tuple(item for item in controls if item.name in requested)
    node = shutil.which("node.exe") or shutil.which("node")
    if not node or not (FRONTEND / "node_modules/vitest/vitest.mjs").is_file():
        raise RuntimeError("Expected installed Node/Vitest unavailable; no installation or fallback authorized")
    environment = os.environ.copy(); environment.update(NO_COLOR="1", FORCE_COLOR="0", PYTHONDONTWRITEBYTECODE="1")
    owner = uuid.uuid4().hex; before = production_hashes(); write_json(output / "production_before.json", before)
    records, failure = [], None
    try:
        for control in controls:
            destination = output / control.name; destination.mkdir(exist_ok=False)
            isolated = prepare_copy(control, output, owner); path = isolated / control.affected_file
            original = path.read_bytes(); text = original.decode("utf-8").replace("\r\n", "\n")
            if text.count(control.needle) != 1: raise RuntimeError(f"{control.name}: mutation needle must occur exactly once, found{text.count(control.needle)}")
            command = command_for(control, isolated, node); child = environment.copy()
            if control.language == "python": child["PYTHONPATH"] = os.pathsep.join((str(isolated), str(ROOT)))
            baseline_code, baseline_text = capture(command, isolated, destination, "baseline", child)
            if not selected_passed(baseline_code, baseline_text): raise RuntimeError(f"{control.name}: selected original did not pass")
            try:
                path.write_text(text.replace(control.needle, control.replacement, 1), encoding="utf-8")
                write_json(destination / "mutation.json", {**asdict(control), "isolated_root": str(isolated),
                           "original_sha256": hashlib.sha256(original).hexdigest(), "fault_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
                mutant_code, mutant_text = capture(command, isolated, destination, "mutant", child)
                intended = mutant_code != 0 and control.assertion_marker in mutant_text and control.test_title.split("[")[0] in mutant_text
                intended = intended and ("AssertionError" in mutant_text or "Failed: " + control.assertion_marker in mutant_text)
                intended = intended and "ERROR collecting" not in mutant_text and "INTERNALERROR" not in mutant_text
            finally:
                path.write_bytes(original)
            restored_code, restored_text = capture(command, isolated, destination, "restored", child)
            record = {"name": control.name, "category": control.category, "baseline_exit": baseline_code, "mutant_exit": mutant_code,
                      "intended_assertion_detected": bool(intended), "copied_source_restored_exactly": path.read_bytes() == original,
                      "restored_exit": restored_code, "restored_passed": selected_passed(restored_code, restored_text),
                      "fault_failed_cases": [int(value) for value in re.findall(r"\b(\d+) failed\b", mutant_text)]}
            records.append(record); write_json(output / "summary.json", {"owner": owner, "complete": False, "controls": records})
            print(f"{control.name}: original={baseline_code}, fault={mutant_code}, intended_assertion={bool(intended)}, restored={restored_code}", flush=True)
            if not intended or not record["copied_source_restored_exactly"] or not record["restored_passed"]:
                raise RuntimeError(f"{control.name}: intended-assertion/restoration gate failed; setup failures are not detection")
    except Exception as exc:
        failure = {"type": type(exc).__name__, "message": str(exc)}; write_json(output / "failure.json", failure)
        print(f"STOPPED: {exc}", file=sys.stderr, flush=True)
    after = production_hashes(); write_json(output / "production_after.json", after)
    unchanged = before == after; complete = failure is None and unchanged and len(records) == len(controls)
    write_json(output / "summary.json", {"owner": owner, "complete": complete, "controls": records, "requested_subset": requested,
        "detected_variants": sum(record["intended_assertion_detected"] for record in records), "variant_count": len(controls),
        "category_count": len({item.category for item in controls}), "production_unchanged": unchanged, "failure": failure})
    print(f"production_unchanged={unchanged}; intended_variants={sum(record['intended_assertion_detected'] for record in records)}/{len(controls)}", flush=True)
    return 0 if complete else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--only", action="append", help="Explicit named subset for troubleshooting; omitted means all declared controls")
    args = parser.parse_args(); output = args.output_dir.resolve()
    if output.exists() or output == ROOT / "runs" or not output.is_relative_to(ROOT / "runs"):
        parser.error("Use a fresh owned ignored directory under repository runs")
    output.mkdir(parents=True, exist_ok=False)
    return run_controls(output, args.only)


if __name__ == "__main__":
    raise SystemExit(main())
