"""Explicit task-owned controlled service, separate from genuine production.

Import is passive. Only explicit execution patches worker call sites in this
child process. Controls use owned disk markers; no fault route, public bind,
second executor, dependency installation or production fallback is introduced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
OPERATIONS = ("sequential", "dual", "sweep", "polarization", "polarization_sweep", "polarized_two_path", "polarized_two_path_sweep")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("observe", "partial", "disconnect", "analyzer"), required=True)
    parser.add_argument("--operation", choices=OPERATIONS, default="polarized_two_path_sweep")
    parser.add_argument("--failure-index", type=int, choices=(0, 8, 16), default=8)
    parser.add_argument("--failure-kind", choices=("numerical", "unexpected"), default="numerical")
    parser.add_argument("--analyzer-port", type=int, choices=(0, 1), default=1)
    parser.add_argument("--assets-dir", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve(): parser.error("Use the existing project interpreter")
    evidence, assets = args.evidence_dir.resolve(), args.assets_dir.resolve()
    if evidence.exists() or evidence == ROOT / "runs" or not evidence.is_relative_to(ROOT / "runs"):
        parser.error("Use a fresh owned ignored evidence directory under runs")
    if not assets.is_relative_to(ROOT / "runs") or not (assets / "index.html").is_file(): parser.error("Use verified owned production assets under runs")
    if args.mode == "partial" and args.operation != "polarized_two_path_sweep": parser.error("V2g point controls require its own sweep")
    if args.mode == "analyzer" and not args.operation.startswith("polarized_two_path"): parser.error("Analyzer controls target only V2g")
    evidence.mkdir(parents=True, exist_ok=False)

    sys.path.insert(0, str(ROOT))
    from apps.virtual_bench import adapter as legacy, two_path_adapter as dual
    from apps.virtual_bench import polarization_adapter as pol, polarized_two_path_adapter as pt, server

    def marker(name: str, value: dict) -> None:
        if Path(name).name != name: raise ValueError("Owned marker must be a basename")
        with (evidence / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.flush(); os.fsync(stream.fileno())

    original_sample, original_runner, original_analyzer = pt.sample_source, pt.run_polarized_two_arm, pt.apply_linear_polarizer
    original_jones_descriptor = pt.JonesField.__dict__["from_scalar"]
    original_jones = pt.JonesField.from_scalar
    originals = {"sequential": legacy.simulate_submission, "dual": dual.simulate_submission, "sweep": dual.sweep_submission,
                 "polarization": pol.simulate_submission, "polarization_sweep": pol.sweep_submission,
                 "polarized_two_path": pt.simulate_submission, "polarized_two_path_sweep": pt.sweep_submission}
    release, stopping = threading.Event(), threading.Event()
    active: str | None = None
    counts = {"sample_attempts": 0, "jones_constructions": 0, "runner_attempts": 0, "runner_completed": 0, "analyzer_attempts": 0, "analyzer_completed": 0}
    phases: list[float] = []
    first = True

    def fail(message: str) -> None:
        if args.failure_kind == "numerical": raise ValueError(message)
        raise RuntimeError(message)

    def sample(*values, **kwargs):
        counts["sample_attempts"] += 1
        return original_sample(*values, **kwargs)

    def runner(*values, **kwargs):
        index = counts["runner_attempts"]; counts["runner_attempts"] += 1
        if args.mode == "partial" and active == args.operation and index == args.failure_index:
            fail(f"Controlled V2g point failure before runner at index {index}")
        result = original_runner(*values, **kwargs)
        counts["runner_completed"] += 1; phases.append(kwargs["spec"].relative_phase_rad)
        return result

    def jones(cls, *values, **kwargs):
        counts["jones_constructions"] += 1
        return original_jones(*values, **kwargs)

    def analyzer(*values, **kwargs):
        index = counts["analyzer_attempts"]; counts["analyzer_attempts"] += 1
        if args.mode == "analyzer" and active == args.operation and index == args.analyzer_port:
            fail(f"Controlled downstream analyzer failure at port {args.analyzer_port}")
        result = original_analyzer(*values, **kwargs)
        counts["analyzer_completed"] += 1
        return result

    def perform(operation: str, submission):
        nonlocal active, first
        held = args.mode == "disconnect" and operation == args.operation and first
        if held:
            first = False
            marker("started.json", {"operation": operation, "request_id": submission.request_id,
                "waiting": True, "worker_started": True,
                "scope": "controlled wait inside actual production worker gate before genuine work", "monotonic_s": time.monotonic()})
            if not release.wait(60):
                marker("timeout.json", {"reason": "No explicit release marker within60seconds"})
                raise RuntimeError("Controlled coordination timeout; no acceptance success")
        for key in counts: counts[key] = 0
        phases.clear(); active = operation; error = None; result = None
        try:
            result = originals[operation](submission)
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            raise
        finally:
            active = None
            body = getattr(result, "body", result)
            status = getattr(result, "status_code", 200) if error is None else None
            record = {"operation": operation, "request_id": submission.request_id, "counts": dict(counts), "actual_runner_phases": list(phases),
                      "exception": error, "monotonic_s": time.monotonic(), "classification": "controlled child, genuine public work except explicit injected failure/wait",
                      "status_code": status, "outcome": "failure" if error else "success" if status == 200 else "controlled_failed_sweep",
                      "response_bytes": len(body) if isinstance(body, bytes) else None,
                      "counter_scope": "sample/runner/analyzer observe V2g adapter callsites; Jones observes the shared public class, including legacy polarization when selected",
                      "marker_scope": "worker-finally marker precedes Future terminal callback; verify subsequent gate admission independently"}
            marker(f"operation_{submission.request_id}.json", record)
            if held: marker("completed.json", record)
        return result

    pt.sample_source, pt.run_polarized_two_arm, pt.apply_linear_polarizer = sample, runner, analyzer
    pt.JonesField.from_scalar = classmethod(jones)
    factory = server.create_app

    def owned_factory():
        return factory(assets_dir=assets,
            worker=lambda submission: perform("sequential", submission),
            two_path_worker=lambda submission: perform("dual", submission),
            sweep_worker=lambda submission: perform("sweep", submission),
            polarization_worker=lambda submission: perform("polarization", submission),
            polarization_sweep_worker=lambda submission: perform("polarization_sweep", submission),
            polarized_two_path_worker=lambda submission: perform("polarized_two_path", submission),
            polarized_two_path_sweep_worker=lambda submission: perform("polarized_two_path_sweep", submission))

    # Reuse the existing main's fixed exclusive loopback bind and all policies.
    # No listener/socket is opened until main is explicitly invoked below.
    server.create_app = owned_factory

    def monitor():
        while not stopping.wait(.025):
            if (evidence / "release").is_file() or (evidence / "release.flag").is_file(): release.set()
    watcher = threading.Thread(target=monitor, name="v2g-owned-marker", daemon=True)
    marker("owner.json", {"pid": os.getpid(), "mode": args.mode, "operation": args.operation, "assets_dir": str(assets),
        "host": "127.0.0.1", "port": 8510, "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "failure_index": args.failure_index, "failure_kind": args.failure_kind, "analyzer_port": args.analyzer_port})
    watcher.start()
    try:
        return server.main()
    finally:
        stopping.set(); release.set(); watcher.join(timeout=2)
        pt.sample_source, pt.run_polarized_two_arm, pt.apply_linear_polarizer = original_sample, original_runner, original_analyzer
        pt.JonesField.from_scalar = original_jones_descriptor
        server.create_app = factory


if __name__ == "__main__":
    raise SystemExit(main())
