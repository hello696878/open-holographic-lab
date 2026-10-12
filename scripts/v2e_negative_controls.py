"""V2e intended-assertion fault controls in fresh owned source copies.

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
    """Stable source anchors are fixed alongside the completed new assertions."""
    module = "apps/virtual_bench/experiment_documents.py"
    unit = "tests/test_virtual_bench_experiment_documents.py"
    server = "tests/test_virtual_bench_document_server.py"
    owned = '             "experiment": experiment.to_dict(),'
    return (
        Control("rounded_scientific_serialization", "numeric_rounding", "python", module, owned,
            '             "experiment": {**experiment.to_dict(), "wavelength_m": float(format(experiment.to_dict()["wavelength_m"], ".14g"))},',
            unit, "test_canonical_bytes_complete_numeric_order_and_existing_digest", "DOCUMENT_NUMERIC_BITS_DETECTED",
            "Round an authoritative nonzero wavelength to fourteen significant digits in the encoded settings."),
        Control("wrong_document_model", "mode_contract", "python", module,
            '    if value["model_contract"] != MODEL_CONTRACTS[mode]:',
            '    if False and value["model_contract"] != MODEL_CONTRACTS[mode]:',
            unit, "test_closed_wrapper_rejects_unsupported_or_missing_contracts", "DOCUMENT_MODE_CONTRACT_DETECTED",
            "Accept unsupported wrapper model metadata despite the closed document contract."),
        Control("reordered_stable_elements", "order_ids", "python", module, owned,
            '             "experiment": ({**experiment.to_dict(), "components": list(reversed(experiment.to_dict()["components"]))} if mode == "sequential" else experiment.to_dict()),',
            unit, "test_order_ids_coefficients_readout_and_excess_elements", "DOCUMENT_ORDER_IDS_DETECTED",
            "Reverse validated sequential components when constructing portable settings."),
        Control("reset_arbitrary_coefficient", "coefficients", "python", module, owned,
            '             "experiment": ({**experiment.to_dict(), "coefficients": {**experiment.to_dict()["coefficients"], "x": {"re": 1.0, "im": 0.0}}} if mode == "polarization" else experiment.to_dict()),',
            unit, "test_order_ids_coefficients_readout_and_excess_elements", "DOCUMENT_COEFFICIENT_BITS_DETECTED",
            "Reset a valid arbitrary complex Jones coefficient in a settings document."),
        Control("duplicate_keys_erased_before_validation", "raw_duplicate", "python", module,
            '    parsed = strict_json_loads(data)', '    parsed = json.loads(data.decode("utf-8"))',
            server, "test_raw_failures_precede_document_or_scientific_validation", "RAW_DUPLICATE_KEYS_DETECTED",
            "Erase duplicate raw keys using ordinary JSON decoding before authoritative document validation."),
        Control("accept_imported_success_fields", "imported_success", "python", module,
            '    if set(value) != names:', '    if not names <= set(value):',
            unit, "test_no_imported_success_result_or_unknown_fields", "IMPORTED_SUCCESS_STATE_DETECTED",
            "Allow unknown complete/results/request/status fields to enter the portable wrapper."),
        Control("document_releases_active_science_gate", "gate_ownership", "python", "apps/virtual_bench/server.py",
            '    async def document_validate(request: Request) -> Response:\n        try:',
            '    async def document_validate(request: Request) -> Response:\n        gate._completed(None)\n        try:',
            server, "test_document_validation_preserves_each_running_worker_and_disconnect_gate", "DOCUMENT_GATE_OWNERSHIP_DETECTED",
            "Release the real shared worker gate from a settings-only validation action while numerical work is held."),
        Control("dynamic_dependency_bypass", "validation_boundary", "python", module,
            'import math\n', 'import math\nimport importlib\n',
            "tests/test_virtual_bench_document_architecture.py", "test_document_module_validation_only_imports_calls_and_no_optical_formulas",
            "DOCUMENT_VALIDATION_BOUNDARY_DETECTED", "Introduce a dynamic-import dependency into the passive document boundary."),
        Control("decimal_underflow_accepted", "decimal_underflow", "python", module,
            '    if not math.isfinite(value) or (value == 0.0 and any(c in "123456789" for c in coefficient)):',
            '    if not math.isfinite(value):',
            unit, "test_nonzero_decimal_underflow_is_rejected_without_tightening_old_parser", "DOCUMENT_NONZERO_UNDERFLOW_DETECTED",
            "Silently accept nonzero decimal tokens that round to binary64 zero."),
        Control("unicode_scalar_limit_doubled", "unicode_scalars", "python", module,
            '        if type(metadata[name]) is not str or len(metadata[name]) > cap:',
            '        if type(metadata[name]) is not str or len(metadata[name]) > 2 * cap:',
            unit, "test_unicode_scalar_lengths_supplementary_combining_chinese_and_exact_text", "DOCUMENT_UNICODE_SCALARS_DETECTED",
            "Accept supplementary-plane metadata beyond its declared Unicode-scalar limit."),
        Control("file_digest_mistaken_for_scientific_digest", "digest_separation", "python", module,
            '    return ValidatedDocument(canonical_bytes=encoded, experiment_sha256=digest)',
            '    return ValidatedDocument(canonical_bytes=encoded, experiment_sha256=__import__("hashlib").sha256(encoded).hexdigest())',
            unit, "test_canonical_bytes_complete_numeric_order_and_existing_digest", "DOCUMENT_DIGEST_CONTRACT_DETECTED",
            "Use the complete document-byte hash as the existing scientific experiment-validation digest."),
    )


def frontend_controls() -> tuple[Control, ...]:
    """Each variant targets a focused behavioral assertion, never a setup error."""
    module = "src/experiment_documents.ts"
    state = "src/experiment_document_state.ts"
    unit = "tests/experiment_documents.test.ts"
    state_unit = "tests/experiment_document_state.test.ts"
    files = "src/experiment_document_files.ts"
    download_test = "keeps prepared URL usable until explicit dismissal and releases repeated downloads"
    drift_test = "detects legal nonzero drift in either authoritative stage"
    stale_original = """  private current(intent: Intent): boolean {
    return !this.disposed && intent.generation === this.generation
      && (intent.kind !== 'import' || intent.contextToken === this.contextToken());
  }"""
    stale_fault = "  private current(intent: Intent): boolean { return !this.disposed; }"
    return (
        Control("untouched_si_reconverted_from_display", "untouched_si", "typescript", "src/numeric_fields.ts",
            "    return !(this.painted && this.painted.text === text && this.painted.fieldKey === fieldKey\n      && this.painted.generation === generation && Object.is(this.painted.authoritativeSI, authoritativeSI));",
            "    return true;", "tests/numeric_fields.test.ts",
            "ignores unchanged shortened display text without a display unit round trip", "UNTOUCHED_SI_BITS_DETECTED",
            "Treat replay of an unchanged shortened cosmetic value as a real edit, permitting a display-to-SI rounding round trip."),
        Control("same_formatted_import_reuses_old_generation", "same_formatted_generation", "typescript", "src/numeric_fields.ts",
            "    this.painted = Object.freeze({ text, fieldKey, generation, authoritativeSI });",
            "    if (this.painted?.text === text) return;\n    this.painted = Object.freeze({ text, fieldKey, generation, authoritativeSI });",
            "tests/numeric_fields.test.ts", "binds same formatted A then B to B generation and exact SI", "SAME_FORMATTED_VALUE_GENERATION_DETECTED",
            "Reuse A's numeric binding when adjacent nonzero B has the same cosmetic string, losing B's generation and exact authoritative SI."),
        Control("frozen_export_relabelled_as_later_draft", "frozen_export", "typescript", state,
            "document: validated.document, revision: intent.revision, requested: false",
            "document: makeExperimentDocument(this.options.currentValidDraft()!.mode, this.options.currentValidDraft()!.experiment, this.snapshot.metadata[this.options.currentValidDraft()!.mode]), revision: intent.revision, requested: false",
            state_unit, "freezes valid draft export at click instead of substituting an old result or later edit", "EXPORT_FROZEN_DRAFT_IDENTITY_DETECTED",
            "Label the prepared export with the later edited draft and metadata rather than the explicit frozen export snapshot."),
        Control("raw_upload_parse_stringified_in_transport", "raw_duplicate", "typescript", module,
            "body: new Uint8Array(bytes).buffer",
            "body: new TextEncoder().encode(JSON.stringify(JSON.parse(new TextDecoder().decode(bytes)))).buffer",
            unit, "sends untouched raw bytes and separates ephemeral scientific header from file identity", "RAW_DUPLICATE_KEYS_DETECTED",
            "Parse/stringify original upload bytes in the browser transport, erasing equivalent duplicate keys before the authoritative parser."),
        Control("first_authoritative_stage_drift_ignored", "two_stage_drift", "typescript", state,
            "    assertDocumentCorrespondence(rawDefinition, first.document);",
            "    // Deliberate isolated fault: omit first raw-definition correspondence.",
            state_unit, drift_test, "TWO_STAGE_NONZERO_DRIFT_DETECTED",
            "Accept a legal nonzero scientific value changed by the first authoritative reply."),
        Control("second_authoritative_stage_drift_ignored", "two_stage_drift", "typescript", state,
            "    assertDocumentCorrespondence(first.document, second.document);",
            "    // Deliberate isolated fault: omit second-stage correspondence.",
            state_unit, drift_test, "TWO_STAGE_NONZERO_DRIFT_DETECTED",
            "Accept a legal nonzero scientific value changed by the final authoritative reply."),
        Control("partial_editor_before_failed_correspondence", "transactional_import", "typescript", state,
            "    assertDocumentCorrespondence(first.document, second.document);",
            "    this.options.prepareApply(second)();\n    assertDocumentCorrespondence(first.document, second.document);",
            state_unit, drift_test, "TRANSACTIONAL_IMPORT_DETECTED",
            "Commit imported editors before final scientific correspondence; a drifting second reply then fails after partial replacement."),
        Control("stale_import_survives_edit_in_both_stages", "stale_generation", "typescript", state,
            stale_original, stale_fault, state_unit, "checks destination token at stage", "STALE_IMPORT_GENERATION_DETECTED",
            "Remove destination context/generation identity checks so held first- and second-stage replies revive previews after an edit, before UI notification or abort."),
        Control("automatic_simulation_during_settings_commit", "zero_compute", "typescript", "src/polarization_state.ts",
            "      ++this.generation; this.validatedHash = transientDigest; this.snapshot = next;",
            "      ++this.generation; this.validatedHash = transientDigest; this.snapshot = next; void this.simulate();",
            state_unit, "prepares all three modes without validation or science, advances eligibility and rejects busy commit", "DOCUMENT_ZERO_COMPUTE_DETECTED",
            "Invoke the actual injected numerical simulate API during explicit settings commit without a separate intentional solve."),
        Control("prepared_download_url_revoked_early", "download_lifetime", "typescript", files,
            "    const url = urlAPI.createObjectURL(blob);",
            "    const url = urlAPI.createObjectURL(blob); urlAPI.revokeObjectURL(url);",
            "tests/experiment_document_files.test.ts", download_test, "DOWNLOAD_LIFETIME_DETECTED",
            "Revoke a prepared Blob URL before the user can use the real download link."),
        Control("prepared_download_urls_leaked", "download_lifetime", "typescript", files,
            "(this.options.urlAPI ?? URL).revokeObjectURL(this.download.url); this.download = null;",
            "this.download = null;",
            "tests/experiment_document_files.test.ts", download_test, "DOWNLOAD_LIFETIME_DETECTED",
            "Drop tracked download ownership without revoking the previously prepared Blob URL."),
        Control("unicode_scalars_counted_as_utf16_units", "unicode_scalars", "typescript", module,
            "    count += 1;", "    count += character.length;", unit,
            "uses Unicode scalars while preserving Chinese supplementary combining and allowed whitespace", "UNICODE_SCALAR_POLICY_DETECTED",
            "Count supplementary-plane characters as two UTF-16 units rather than one Unicode scalar."),
        Control("first_digest_installed_after_final_validation", "digest_separation", "typescript", state,
            "preview: Object.freeze({ ...second, generation: intent.generation, contextToken: intent.contextToken })",
            "preview: Object.freeze({ ...second, experimentSha256: first.experimentSha256, generation: intent.generation, contextToken: intent.contextToken })",
            state_unit, "installs only the final digest and applies documented signed zero behavior", "DOCUMENT_DIGEST_SEPARATION_DETECTED",
            "Install the first response digest rather than the final canonical scientific digest used for restored explicit solving."),
    )


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False, ensure_ascii=False) + "\n")


def production_hashes() -> dict[str, str]:
    result = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                            cwd=ROOT, capture_output=True, check=True)
    return {relative.replace("\\", "/"): hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            for relative in sorted(set(result.stdout.decode().split("\0")) - {""}) if (ROOT / relative).is_file()}


def prepare_copy(control: Control, output: Path, owner: str) -> Path:
    if control.language == "typescript":
        isolated = FRONTEND / ".vitest/v2e_negative_controls" / owner / control.name
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
                "--config", str(isolated / "vitest.control.config.mjs"), "--reporter=verbose",
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
    return (code != 0 and control.assertion_marker in output and control.test_title.split("[")[0] in output
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
        "category_count": len({control.category for control in controls}), "production_unchanged": unchanged, "failure": failure})
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
