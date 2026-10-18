"""Explicit owned W1 acceptance child; production has no fault endpoints.

The existing server retains its one fixed loopback listener and actual-worker
gate. Optional disk-marker holds occur inside genuine work or final encoding.
Malformed transport is an explicitly labelled child-only fault, not a valid
scientific result or a presentation-failure substitute. Browser-owned Three.js
fault injection is separate and must be recorded by the browser acceptance.
Import is passive: no listener, thread or computation starts before main().
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
OPERATIONS = ("sequential", "dual", "sweep", "polarization", "polarization_sweep",
              "polarized_two_path", "polarized_two_path_sweep", "ideal", "wave_field")


def main() -> int:
    """Launch only an explicitly requested task-owned loopback acceptance child."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("observe", "hold", "hold_encoding", "malformed"), required=True)
    parser.add_argument("--operation", choices=OPERATIONS, default="wave_field")
    parser.add_argument("--assets-dir", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        parser.error("Use the existing project interpreter")
    evidence, assets = args.evidence_dir.resolve(), args.assets_dir.resolve()
    runs = (ROOT / "runs").resolve()
    if evidence.exists() or evidence == runs or not evidence.is_relative_to(runs):
        parser.error("Use a fresh owned evidence directory under runs")
    if not assets.is_relative_to(runs) or not (assets / "index.html").is_file():
        parser.error("Use verified owned production assets under runs")
    if args.mode in {"hold_encoding", "malformed"} and args.operation != "wave_field":
        parser.error("Encoding and malformed-frame controls are W1-only")
    evidence.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(ROOT))
    from apps.virtual_bench import adapter as legacy, two_path_adapter as dual
    from apps.virtual_bench import polarization_adapter as pol, polarized_two_path_adapter as pt
    from apps.virtual_bench import r03_fig2a_adapter as ideal, wave_field_adapter as wave, server

    originals = {"sequential": legacy.simulate_submission, "dual": dual.simulate_submission,
                 "sweep": dual.sweep_submission, "polarization": pol.simulate_submission,
                 "polarization_sweep": pol.sweep_submission, "polarized_two_path": pt.simulate_submission,
                 "polarized_two_path_sweep": pt.sweep_submission, "ideal": ideal.simulate_submission,
                 "wave_field": wave.simulate_submission}
    original_encode = wave.encode_result
    release, stopping = threading.Event(), threading.Event()
    first = True
    active_request = None
    app_holder = []

    def marker(name, record):
        if Path(name).name != name:
            raise ValueError("Owned marker must be a basename")
        with (evidence / name).open("x", encoding="utf-8") as output:
            json.dump(record, output, indent=2, allow_nan=False)
            output.flush()
            os.fsync(output.fileno())

    def wait_for_release(phase, request_id):
        marker("started.json", {"operation": args.operation, "request_id": request_id,
            "phase": phase, "waiting": True, "worker_started": True, "gate_busy": app_holder[0].state.gate.busy,
            "monotonic_s": time.monotonic(),
            "classification": "controlled wait inside actual worker lifetime"})
        if not release.wait(60):
            marker("timeout.json", {"reason": "No explicit disk release within 60 seconds"})
            raise RuntimeError("Controlled coordination timeout; acceptance not established")

    def encode(*values, **kwargs):
        nonlocal first
        if args.mode == "hold_encoding" and first:
            first = False
            wait_for_release("encoding", active_request)
        return original_encode(*values, **kwargs)

    def perform(operation, submission):
        nonlocal first, active_request
        active_request = submission.request_id
        held = args.mode == "hold" and operation == args.operation and first
        if held:
            first = False
            wait_for_release("before_genuine_computation", submission.request_id)
        start = time.perf_counter()
        result, error = None, None
        try:
            result = originals[operation](submission)
            if args.mode == "malformed" and operation == args.operation and first:
                first = False
                result = result[:-8]
            return result
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            raise
        finally:
            body = getattr(result, "body", result)
            record = {"operation": operation, "request_id": submission.request_id,
                "elapsed_s": time.perf_counter()-start, "response_bytes": len(body) if isinstance(body, bytes) else None,
                "outcome": "failure" if error else "success" if getattr(result, "status_code", 200) == 200 else "controlled_failed_sweep",
                "exception": error, "gate_busy_before_future_terminal": app_holder[0].state.gate.busy,
                "classification": "controlled child; genuine public work except explicitly selected hold/frame fault",
                "mode": args.mode, "monotonic_s": time.monotonic(),
                "marker_scope": "worker-finally precedes Future callback; verify gate release independently"}
            marker(f"operation_{submission.request_id}.json", record)
            active_request = None
            if held or args.mode == "hold_encoding" and operation == args.operation and not (evidence / "completed.json").exists():
                marker("completed.json", record)

    original_factory = server.create_app
    def owned_factory():
        app = original_factory(assets_dir=assets,
            worker=lambda submission: perform("sequential", submission),
            two_path_worker=lambda submission: perform("dual", submission),
            sweep_worker=lambda submission: perform("sweep", submission),
            polarization_worker=lambda submission: perform("polarization", submission),
            polarization_sweep_worker=lambda submission: perform("polarization_sweep", submission),
            polarized_two_path_worker=lambda submission: perform("polarized_two_path", submission),
            polarized_two_path_sweep_worker=lambda submission: perform("polarized_two_path_sweep", submission),
            r03_ideal_worker=lambda submission: perform("ideal", submission),
            wave_field_worker=lambda submission: perform("wave_field", submission))
        app_holder.append(app)
        return app

    def monitor():
        while not stopping.wait(0.025):
            if (evidence / "release").is_file() or (evidence / "release.flag").is_file():
                release.set()
    marker("owner.json", {"pid": os.getpid(), "mode": args.mode, "operation": args.operation,
        "assets_dir": str(assets), "host": "127.0.0.1", "port": 8510,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    wave.encode_result, server.create_app = encode, owned_factory
    watcher = threading.Thread(target=monitor, name="w1-owned-marker", daemon=True)
    watcher.start()
    try:
        exit_code = server.main()
        return 1 if (evidence / "timeout.json").exists() else exit_code
    finally:
        stopping.set()
        release.set()
        watcher.join(timeout=2)
        wave.encode_result, server.create_app = original_encode, original_factory


if __name__ == "__main__":
    raise SystemExit(main())
