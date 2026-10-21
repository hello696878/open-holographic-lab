"""Opt-in task-owned W2 acceptance child, using the unchanged production gate.

No listener, worker or optical work starts on import. Holds occur inside genuine
public work or genuine final encoding; malformed/wrong-identity bytes are
explicit child-only transport faults, never production scientific results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import ntpath
import os
from pathlib import Path
import stat
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
OPERATIONS = ("sequential", "dual", "sweep", "polarization", "polarization_sweep",
              "polarized_two_path", "polarized_two_path_sweep", "ideal",
              "wave_field", "routing")
MODES = ("observe", "hold", "hold_encoding", "malformed", "wrongidentity")


def _normalized(path: Path) -> str:
    return ntpath.normcase(ntpath.normpath(str(path)))


def _owned_path(value: Path, owner: Path, *, absent: bool) -> Path:
    """Check Windows lexical containment and every reparse ancestor first."""
    if not value.is_absolute():
        raise ValueError("Use an absolute task-owned path")
    path = Path(os.path.abspath(value))
    root = Path(os.path.abspath(owner))
    normalized, parent = _normalized(path), _normalized(root)
    if normalized == parent or ntpath.commonpath((normalized, parent)) != parent:
        raise ValueError("Path must be a child of the project-owned runs root")
    cursor = path
    while True:
        try:
            metadata = cursor.lstat()
        except FileNotFoundError:
            metadata = None
        if metadata is not None and (cursor.is_symlink() or
                getattr(metadata, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError("Linked/reparse evidence or assets are forbidden")
        if _normalized(cursor) == parent:
            break
        cursor = cursor.parent
    if absent and path.exists():
        raise ValueError("Evidence must be fresh; preserve all earlier artifacts")
    return path


def main() -> int:
    """Start only the explicit owned loopback child; all holds are bounded."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--operation", choices=OPERATIONS, default="routing")
    parser.add_argument("--assets-dir", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        parser.error("Use the existing project interpreter only")
    if args.mode == "hold_encoding" and args.operation not in {"routing", "wave_field"}:
        parser.error("Encoding holds support only routing or the existing W1 encoder")
    if args.mode in {"malformed", "wrongidentity"} and args.operation != "routing":
        parser.error("Transport fault controls are W2-only")
    try:
        evidence = _owned_path(args.evidence_dir, ROOT / "runs", absent=True)
        assets = _owned_path(args.assets_dir, ROOT / "runs", absent=False)
        index = _owned_path(assets / "index.html", ROOT / "runs", absent=False)
        if not assets.is_dir() or not index.is_file():
            raise ValueError("Use verified owned production assets with index.html")
        for entry in assets.rglob("*"):
            _owned_path(entry, ROOT / "runs", absent=False)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    evidence.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(ROOT))
    from apps.virtual_bench import adapter as legacy, two_path_adapter as dual
    from apps.virtual_bench import polarization_adapter as pol, polarized_two_path_adapter as pt
    from apps.virtual_bench import r03_fig2a_adapter as ideal, wave_field_adapter as wave
    from apps.virtual_bench import geometric_routing_adapter as routing
    from apps.virtual_bench import geometric_routing_protocol as protocol, server

    originals = {"sequential": legacy.simulate_submission, "dual": dual.simulate_submission,
        "sweep": dual.sweep_submission, "polarization": pol.simulate_submission,
        "polarization_sweep": pol.sweep_submission,
        "polarized_two_path": pt.simulate_submission, "polarized_two_path_sweep": pt.sweep_submission,
        "ideal": ideal.simulate_submission, "wave_field": wave.simulate_submission,
        "routing": routing.trace_submission}
    original_factory, original_routing_encode, original_wave_encode = (
        server.create_app, routing.encode_trace_result, wave.encode_result)
    release, stopping = threading.Event(), threading.Event()
    first = True
    active_request = None
    app_holder = []

    def marker(name: str, record: object) -> None:
        if Path(name).name != name:
            raise ValueError("Owned marker must be a basename")
        with (evidence / name).open("x", encoding="utf-8") as output:
            json.dump(record, output, indent=2, allow_nan=False)
            output.flush()
            os.fsync(output.fileno())

    def wait_for_release(phase: str, request_id: str) -> None:
        marker("started.json", {"operation": args.operation, "request_id": request_id,
            "phase": phase, "waiting": True, "worker_started": True,
            "gate_busy": app_holder[0].state.gate.busy, "monotonic_s": time.monotonic(),
            "classification": "controlled wait inside actual production worker lifetime"})
        if not release.wait(60):
            marker("timeout.json", {"reason": "No explicit owned disk release within60seconds"})
            raise RuntimeError("Controlled coordination timeout; acceptance is not established")

    def routing_encode(*values, **kwargs):
        nonlocal first
        if args.mode == "hold_encoding" and args.operation == "routing" and first:
            first = False
            wait_for_release("encoding", active_request)
        return original_routing_encode(*values, **kwargs)

    def wave_encode(*values, **kwargs):
        nonlocal first
        if args.mode == "hold_encoding" and args.operation == "wave_field" and first:
            first = False
            wait_for_release("encoding", active_request)
        return original_wave_encode(*values, **kwargs)

    def perform(operation, submission):
        nonlocal first, active_request
        active_request = submission.request_id
        held = args.mode == "hold" and operation == args.operation and first
        if held:
            first = False
            wait_for_release("before_genuine_computation", submission.request_id)
        start = time.perf_counter()
        result, genuine, error, fault = None, None, None, None
        try:
            result = originals[operation](submission)
            body = getattr(result, "body", result)
            genuine = body if isinstance(body, bytes) else None
            if operation == "routing" and args.mode in {"malformed", "wrongidentity"} and first:
                first = False
                with (evidence / ("genuine_" + submission.request_id + ".json")).open("xb") as output:
                    output.write(body)
                if args.mode == "malformed":
                    result = body[:-1]
                    fault = "truncate final byte of genuine closed JSON"
                else:
                    changed = json.loads(body)
                    wrong = "00000000-0000-4000-8000-000000000001"
                    if wrong == submission.request_id:
                        wrong = "00000000-0000-4000-8000-000000000002"
                    changed["request_id"] = wrong
                    result = protocol.json_bytes(changed)
                    fault = "replace genuine response UUID with another canonical UUID"
            return result
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            raise
        finally:
            body = getattr(result, "body", result)
            marker("operation_" + submission.request_id + ".json", {
                "operation": operation, "request_id": submission.request_id,
                "elapsed_s": time.perf_counter() - start,
                "response_bytes": len(body) if isinstance(body, bytes) else None,
                "genuine_sha256": hashlib.sha256(genuine).hexdigest() if genuine is not None else None,
                "returned_sha256": hashlib.sha256(body).hexdigest() if isinstance(body, bytes) else None,
                "outcome": "failure" if error else "transport_fault" if fault else
                    "success" if getattr(result, "status_code", 200) == 200 else "controlled_failed_sweep",
                "exception": error, "fault": fault, "mode": args.mode,
                "gate_busy_before_future_terminal": app_holder[0].state.gate.busy,
                "classification": "controlled child; genuine public work except explicitly selected hold/transport fault",
                "monotonic_s": time.monotonic(),
                "marker_scope": "worker-finally precedes Future callback; verify idle independently"})
            if held or (args.mode == "hold_encoding" and operation == args.operation
                        and not (evidence / "completed.json").exists()):
                marker("completed.json", {"operation": operation, "request_id": submission.request_id,
                    "mode": args.mode, "genuine_work_returned": error is None,
                    "future_terminal_not_yet_observed": True})
            active_request = None

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
            wave_field_worker=lambda submission: perform("wave_field", submission),
            geometric_routing_worker=lambda submission: perform("routing", submission))
        app_holder.append(app)
        return app

    def monitor():
        while not stopping.wait(.025):
            if (evidence / "release").is_file() or (evidence / "release.flag").is_file():
                release.set()

    marker("owner.json", {"pid": os.getpid(), "mode": args.mode, "operation": args.operation,
        "assets_dir": str(assets), "evidence_dir": str(evidence),
        "host": "127.0.0.1", "port": 8510, "parent_pid": os.getppid(),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "classification": "explicit task-owned controlled production-service child"})
    server.create_app, routing.encode_trace_result, wave.encode_result = owned_factory, routing_encode, wave_encode
    watcher = threading.Thread(target=monitor, name="w2-owned-marker", daemon=True)
    watcher.start()
    try:
        from scripts.w2_acceptance import owned_server_lifetime
        with owned_server_lifetime(evidence):
            code = server.main()
        return 1 if (evidence / "timeout.json").exists() else code
    finally:
        stopping.set()
        release.set()
        watcher.join(timeout=2)
        server.create_app, routing.encode_trace_result, wave.encode_result = (
            original_factory, original_routing_encode, original_wave_encode)


if __name__ == "__main__":
    raise SystemExit(main())
