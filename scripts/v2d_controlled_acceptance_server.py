"""Explicit task-owned controlled browser service; never a production fallback.

No listener, thread, monkeypatch or application instance is created on import.
The ordinary production application provides all routes/security/shared-gate
behavior. Controls exist only in this explicitly invoked child and owned disk
markers; no fault/release endpoint is added. Stop only the child you launched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """Bind only the fixed production loopback port when it is unoccupied."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("partial", "disconnect"), required=True)
    parser.add_argument("--operation", choices=("sequential", "dual", "sweep", "polarization", "polarization_sweep"), default="polarization_sweep")
    parser.add_argument("--failure-index", type=int, choices=(0, 3, 12), default=3)
    parser.add_argument("--failure-kind", choices=("numerical", "unexpected"), default="numerical")
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        parser.error("Use the existing repository interpreter")
    if args.mode == "partial" and args.operation not in ("sweep", "polarization_sweep"):
        parser.error("A partial control requires a sweep operation")
    if args.operation == "sweep" and args.failure_index == 12:
        parser.error("The legacy last point is index16; this harness's index12 is the V2d last-point control")
    evidence = args.evidence_dir.resolve()
    if evidence == ROOT / "runs" or not evidence.is_relative_to(ROOT / "runs"):
        parser.error("Use a fresh owned child inside repository runs")
    try:
        evidence.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("Evidence destination already exists; preserve it")

    # Explicit invocation is the only path that imports/patches optional app
    # workers. Ordinary production code never imports this harness.
    sys.path.insert(0, str(ROOT))
    import uvicorn
    from apps.virtual_bench import adapter as legacy, polarization_adapter as pol, server, two_path_adapter as dual

    def marker(name: str, value: dict) -> None:
        if Path(name).name != name: raise RuntimeError("Invalid owned marker name")
        with (evidence / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.flush(); os.fsync(stream.fileno())

    original_train = pol._run_train
    original_polarizer, original_retarder = pol.apply_linear_polarizer, pol.apply_linear_retarder
    original_dual_runner = dual.run_two_arm
    originals = {"sequential": legacy.simulate_submission, "dual": dual.simulate_submission,
                 "sweep": dual.sweep_submission, "polarization": pol.simulate_submission,
                 "polarization_sweep": pol.sweep_submission}
    calls: list[dict] = []
    dual_phases: list[float] = []
    point_attempts = 0
    current_operation: str | None = None
    release, stopping = threading.Event(), threading.Event()
    first = True

    def controlled_failure(index: int) -> None:
        if args.failure_kind == "numerical":
            raise ValueError(f"Controlled acceptance domain failure before requested point {index}")
        raise RuntimeError(f"Controlled unexpected failure before requested point {index}")

    def train(incident, experiment, *, selected_element_id=None, axis_angle_rad=None, include_samples=True):
        nonlocal point_attempts
        if current_operation == "polarization_sweep":
            index = point_attempts; point_attempts += 1
            if args.mode == "partial" and args.operation == current_operation and index == args.failure_index:
                controlled_failure(index)
        return original_train(incident, experiment, selected_element_id=selected_element_id,
                              axis_angle_rad=axis_angle_rad, include_samples=include_samples)

    def polarizer(field, *, axis_angle_rad):
        result = original_polarizer(field, axis_angle_rad=axis_angle_rad)
        calls.append({"kind": "linear_polarizer", "axis_angle_rad": axis_angle_rad})
        return result

    def retarder(field, *, axis_angle_rad, retardance_rad):
        result = original_retarder(field, axis_angle_rad=axis_angle_rad, retardance_rad=retardance_rad)
        calls.append({"kind": "linear_retarder", "axis_angle_rad": axis_angle_rad, "retardance_rad": retardance_rad})
        return result

    def dual_runner(incident, *, spec):
        nonlocal point_attempts
        if current_operation == "sweep":
            index = point_attempts; point_attempts += 1
            if args.mode == "partial" and args.operation == current_operation and index == args.failure_index:
                controlled_failure(index)
        result = original_dual_runner(incident, spec=spec)
        dual_phases.append(spec.relative_phase_rad)
        return result

    def perform(operation: str, submission):
        nonlocal first, current_operation, point_attempts
        controlled = args.mode == "disconnect" and args.operation == operation and first
        if controlled:
            first = False
            marker("started.json", {"request_id": submission.request_id, "operation": operation,
                   "waiting": True, "worker_started": True, "monotonic_s": time.monotonic(),
                   "scope": "controlled wait before genuine public numerical work, inside the actual production gate"})
            if not release.wait(60):
                marker("timeout.json", {"request_id": submission.request_id, "reason": "worker not explicitly released within60seconds"})
                raise RuntimeError("Controlled coordination timed out; no acceptance success claimed")
        # The real gate excludes overlap, so these records have one worker owner.
        calls.clear(); dual_phases.clear(); point_attempts = 0; current_operation = operation
        try:
            result = originals[operation](submission)
        except BaseException as exc:
            if controlled:
                marker("completed.json", {"request_id": submission.request_id, "operation": operation,
                       "outcome": "failure", "error_type": type(exc).__name__, "monotonic_s": time.monotonic()})
            raise
        finally:
            current_operation = None
        status = result.status_code if hasattr(result, "status_code") else 200
        body = result.body if hasattr(result, "body") else result
        record = {"request_id": submission.request_id, "operation": operation,
                  "outcome": "success" if status == 200 else "controlled_failed_sweep", "status_code": status,
                  "response_bytes": len(body), "point_attempts": point_attempts,
                  "actual_public_element_calls": len(calls), "public_element_calls": list(calls),
                  "actual_public_runner_calls": len(dual_phases), "runner_wrapper_phases": list(dual_phases),
                  "monotonic_s": time.monotonic()}
        marker(f"operation_{submission.request_id}.json", record)
        if controlled: marker("completed.json", record)
        return result

    pol._run_train = train; pol.apply_linear_polarizer = polarizer; pol.apply_linear_retarder = retarder
    dual.run_two_arm = dual_runner
    app = server.create_app(worker=lambda submission: perform("sequential", submission),
                            two_path_worker=lambda submission: perform("dual", submission),
                            sweep_worker=lambda submission: perform("sweep", submission),
                            polarization_worker=lambda submission: perform("polarization", submission),
                            polarization_sweep_worker=lambda submission: perform("polarization_sweep", submission))
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind((server.HOST, server.PORT)); listener.listen(16); listener.setblocking(False)
    except OSError:
        listener.close(); app.state.gate.shutdown()
        pol._run_train = original_train; pol.apply_linear_polarizer = original_polarizer; pol.apply_linear_retarder = original_retarder
        dual.run_two_arm = original_dual_runner
        print("Acceptance port8510 unavailable; no existing service was changed", file=sys.stderr)
        return 2

    def watch_release() -> None:
        while not stopping.wait(.02):
            if (evidence / "release.flag").is_file():
                release.set(); return

    marker("harness.json", {"owned_test_harness": True, "origin": server.ORIGIN, "mode": args.mode,
           "operation": args.operation, "controlled_failed_index": args.failure_index if args.mode == "partial" else None,
           "failure_kind": args.failure_kind if args.mode == "partial" else None, "production_test_control_routes": False,
           "source_sha256": {str(Path(module.__file__).resolve()): hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
                             for module in (server, pol, dual)}, "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    watcher = threading.Thread(target=watch_release, name="v2d-owned-acceptance-release", daemon=True)
    watcher.start()
    config = uvicorn.Config(app, host=server.HOST, port=server.PORT, workers=1, reload=False,
                            loop="asyncio", http="h11", proxy_headers=False, ws="none", limit_concurrency=16,
                            timeout_keep_alive=2, server_header=False, access_log=False)
    try:
        uvicorn.Server(config).run(sockets=[listener])
    except KeyboardInterrupt:
        pass
    finally:
        listener.close(); stopping.set(); watcher.join(timeout=1)
        app.state.gate.shutdown()
        pol._run_train = original_train; pol.apply_linear_polarizer = original_polarizer; pol.apply_linear_retarder = original_retarder
        dual.run_two_arm = original_dual_runner
    return 1 if (evidence / "timeout.json").exists() else 0


if __name__ == "__main__":
    raise SystemExit(main())
