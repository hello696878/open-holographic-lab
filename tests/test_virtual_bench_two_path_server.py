"""Actual ASGI routes, one shared worker, and precise disconnect lifetime."""

import asyncio
from concurrent.futures import Executor, Future
import json
import threading

import pytest

from apps.virtual_bench import adapter as legacy, server, two_path_adapter as adapter
from apps.virtual_bench.two_path_protocol import SweepReply
from test_virtual_bench_two_path_adapter import envelope, sweep_envelope, REQUEST_ID


def legacy_envelope():
    return {"request_id": REQUEST_ID, "experiment": {
        "schema_version": 1, "model_contract": "v0_aligned_scalar_forward_v1",
        "wavelength_m": 633e-9, "grid": {"ny": 3, "nx": 4, "dy": 4e-6, "dx": 4e-6},
        "source": {"kind": "uniform", "amplitude": 1.0, "phase_rad": 0.0},
        "components": [], "observation": {"id": "screen", "z_m": 0.0}}}


def request_for(operation):
    if operation == "sequential":
        return "/api/v1/simulate", legacy_envelope()
    if operation == "dual":
        return "/api/v2b/simulate", envelope(ny=3, nx=4)
    return "/api/v2b/sweep", sweep_envelope(envelope(ny=3, nx=4))


async def call(app, path="/api/v1/health", *, method="GET", value=None, raw=None,
               disconnected=None, headers=None, messages=None):
    body = raw if raw is not None else json.dumps(value).encode() if value is not None else b""
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
             "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
             "query_string": b"", "root_path": "", "server": (server.HOST, server.PORT),
             "client": ("127.0.0.1", 12345), "headers": headers if headers is not None else
             [(b"host", server.AUTHORITY.encode()), (b"origin", server.ORIGIN.encode()),
              (b"content-type", b"application/json")]}
    incoming = list(messages) if messages is not None else [{"type": "http.request", "body": body, "more_body": False}]
    messages_out = []

    async def receive():
        if incoming:
            return incoming.pop(0)
        if disconnected is not None:
            await disconnected.wait()
            return {"type": "http.disconnect"}
        await asyncio.Event().wait()

    async def send(message):
        messages_out.append(message)

    await app(scope, receive, send)
    start = next(message for message in messages_out if message["type"] == "http.response.start")
    return start["status"], dict(start["headers"]), b"".join(m.get("body", b"") for m in messages_out if m["type"] == "http.response.body")


@pytest.fixture
def make_app(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "index.html").write_text("<!doctype html><title>V2b owned ASGI fixture</title>", encoding="utf-8")
    applications = []

    def factory(**kwargs):
        app = server.create_app(assets_dir=assets, **kwargs)
        applications.append(app)
        return app

    yield factory
    for app in applications:
        app.state.gate.shutdown()


def test_actual_routes_validation_zero_calls_single_one_and_sweep_seventeen(make_app, monkeypatch):
    calls = []
    original = adapter.run_two_arm

    def run(incident, *, spec):
        calls.append(spec.relative_phase_rad)
        return original(incident, spec=spec)

    monkeypatch.setattr(adapter, "run_two_arm", run)
    app = make_app()
    status, _, body = asyncio.run(call(app, "/api/v2b/validate", method="POST", value=envelope(ny=3,nx=4)))
    assert status == 200 and calls == []
    reply = json.loads(body)
    assert set(reply) == {"protocol_version", "message_type", "request_id", "experiment_sha256", "experiment"}
    assert reply["message_type"] == "two_path_validation"
    status, headers, frame = asyncio.run(call(app, "/api/v2b/simulate", method="POST", value=envelope(ny=3,nx=4)))
    assert status == 200 and frame[:8] == b"OHLAB2P\0" and calls == [.37]
    assert headers[b"content-type"] == b"application/octet-stream"
    status, headers, body = asyncio.run(call(app, "/api/v2b/sweep", method="POST", value=sweep_envelope(envelope(ny=3,nx=4))))
    assert status == 200 and json.loads(body)["completed_count"] == 17 and len(calls) == 18
    assert headers[b"content-type"] == b"application/json"
    assert not app.state.gate.busy


@pytest.mark.parametrize("active", ["sequential", "dual", "sweep"])
@pytest.mark.parametrize("blocked", ["sequential", "dual", "sweep"])
def test_one_gate_cross_product_rejects_without_queue_and_keeps_validation_responsive(make_app, active, blocked):
    started, release = threading.Event(), threading.Event()
    calls = []

    def controlled(submission):
        calls.append(submission.request_id)
        started.set()
        assert release.wait(5)
        if isinstance(submission, legacy.ValidatedSubmission):
            return legacy.simulate_submission(submission)
        if isinstance(submission, adapter.ValidatedTwoPathSubmission):
            return adapter.simulate_submission(submission)
        return adapter.sweep_submission(submission)

    app = make_app(worker=controlled, two_path_worker=controlled, sweep_worker=controlled)

    async def check():
        path, value = request_for(active)
        first = asyncio.create_task(call(app, path, method="POST", value=value))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            blocked_path, blocked_value = request_for(blocked)
            assert (await call(app, blocked_path, method="POST", value=blocked_value))[0] == 409
            assert calls == [REQUEST_ID]
            assert json.loads((await call(app))[2])["busy"] is True
            assert (await call(app, "/api/v2b/validate", method="POST", value=envelope()))[0] == 200
            assert (await call(app, "/api/v1/validate", method="POST", value=legacy_envelope()))[0] == 200
        finally:
            release.set()
        assert (await first)[0] == 200
        assert await asyncio.to_thread(app.state.gate.wait_idle, 5)
        assert (await call(app, blocked_path, method="POST", value=blocked_value))[0] == 200
        assert calls == [REQUEST_ID, REQUEST_ID]

    asyncio.run(check())


@pytest.mark.parametrize("active", ["dual", "sweep"])
@pytest.mark.parametrize("abort", ["disconnect", "handler_cancel"])
def test_actual_abort_holds_shared_gate_until_python_finishes(make_app, active, abort):
    started, release, ended = threading.Event(), threading.Event(), threading.Event()
    calls = []

    def controlled(submission):
        calls.append(submission.request_id)
        started.set()
        assert release.wait(5)
        try:
            return (adapter.simulate_submission(submission) if isinstance(submission, adapter.ValidatedTwoPathSubmission)
                    else adapter.sweep_submission(submission))
        finally:
            ended.set()

    app = make_app(two_path_worker=controlled, sweep_worker=controlled)

    async def check():
        path, value = request_for(active)
        disconnected = asyncio.Event()
        first = asyncio.create_task(call(app, path, method="POST", value=value, disconnected=disconnected))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            if abort == "disconnect":
                disconnected.set()
                assert (await first)[0] == 499
            else:
                first.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await first
            assert not ended.is_set() and app.state.gate.busy, "GATE_ABORT_DETECTED"
            for operation in ("sequential", "dual", "sweep"):
                other_path, other_value = request_for(operation)
                assert (await call(app, other_path, method="POST", value=other_value))[0] == 409, "GATE_ABORT_DETECTED"
            assert calls == [REQUEST_ID], "GATE_ABORT_DETECTED"
            assert (await call(app, "/api/v2b/validate", method="POST", value=envelope()))[0] == 200
        finally:
            release.set()
        assert await asyncio.to_thread(app.state.gate.wait_idle, 5)
        assert ended.is_set() and not app.state.gate.busy
        assert (await call(app, "/api/v2b/simulate", method="POST", value=envelope()))[0] == 200

    asyncio.run(check())


@pytest.mark.parametrize("operation", ["dual", "sweep"])
@pytest.mark.parametrize("termination", ["numerical", "encoding", "invalid_reply"])
def test_failures_release_shared_gate_and_recover_deliberately(make_app, operation, termination):
    failures = [True]

    def controlled(submission):
        if failures[0]:
            if termination == "numerical": raise legacy.NumericalError("controlled numerical arithmetic")
            if termination == "encoding": raise RuntimeError("private encoder detail")
            return b"bad" if operation == "dual" else SweepReply(status_code=200, body=b"x")
        return adapter.simulate_submission(submission) if operation == "dual" else adapter.sweep_submission(submission)

    app = make_app(two_path_worker=controlled, sweep_worker=controlled)
    path, value = request_for(operation)
    status, _, body = asyncio.run(call(app, path, method="POST", value=value))
    assert status == (422 if termination == "numerical" else 500)
    assert b"private encoder detail" not in body
    assert app.state.gate.wait_idle(5) and not app.state.gate.busy
    failures[0] = False
    assert asyncio.run(call(app, path, method="POST", value=value))[0] == 200


def test_numerical_sweep_failure_is_non2xx_genuine_prefix_and_gate_released(make_app, monkeypatch):
    calls = []
    original = adapter.run_two_arm

    def fail_third(incident, *, spec):
        calls.append(spec.relative_phase_rad)
        if len(calls) == 3:
            raise ValueError("controlled third phase failure")
        return original(incident, spec=spec)

    monkeypatch.setattr(adapter, "run_two_arm", fail_third)
    app = make_app()
    status, headers, body = asyncio.run(call(app, "/api/v2b/sweep", method="POST", value=sweep_envelope()))
    reply = json.loads(body)
    assert status == 422 and headers[b"content-type"] == b"application/json"
    assert reply["status"] == "failed" and reply["completed_count"] == reply["failed_index"] == 2
    assert len(reply["rows"]) == 2 and len(calls) == 3
    assert reply["error"] == {"code": "numerical_failure", "message": "controlled third phase failure"}
    assert app.state.gate.wait_idle(5)


class ControlledExecutor(Executor):
    def __init__(self):
        self.fail = True
        self.future = None

    def submit(self, function, /, *args, **kwargs):
        if self.fail:
            raise RuntimeError("submission refused")
        self.future = Future()
        self.future.cancel()
        return self.future

    def shutdown(self, wait=True, *, cancel_futures=False):
        if self.future is not None:
            self.future.cancel()


@pytest.mark.parametrize("operation", ["dual", "sweep"])
def test_submission_failure_and_before_start_cancel_release(make_app, operation):
    executor = ControlledExecutor()
    app = make_app(executor=executor)
    path, value = request_for(operation)
    status, _, body = asyncio.run(call(app, path, method="POST", value=value))
    assert status == 500 and json.loads(body)["error"]["code"] == "submission_failed"
    assert not app.state.gate.busy
    executor.fail = False
    status, _, body = asyncio.run(call(app, path, method="POST", value=value))
    assert status == 503 and json.loads(body)["error"]["code"] == "cancelled_before_start"
    assert not app.state.gate.busy


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'\xff'])
def test_new_routes_retain_strict_json_no_solver_and_security_headers(make_app, raw):
    app = make_app(two_path_worker=lambda _: pytest.fail("worker reached"))
    status, headers, body = asyncio.run(call(app, "/api/v2b/simulate", method="POST", raw=raw))
    assert status == 400 and json.loads(body)["message_type"] == "two_path_error"
    assert b"access-control-allow-origin" not in headers and headers[b"cache-control"] == b"no-store"


def test_legacy_and_two_path_envelopes_cannot_be_confused_and_request_cap_retained(make_app):
    app = make_app()
    assert asyncio.run(call(app, "/api/v2b/simulate", method="POST", value=legacy_envelope()))[0] == 422
    assert asyncio.run(call(app, "/api/v1/simulate", method="POST", value=envelope()))[0] == 422
    assert asyncio.run(call(app, "/api/v2b/sweep", method="POST", value=envelope()))[0] == 422
    assert asyncio.run(call(app, "/api/v2b/simulate", method="POST", raw=b" "*32769))[0] == 413
    assert asyncio.run(call(app, "/api/v2b/simulate"))[0] == 405
    assert asyncio.run(call(app, "/api/v1/simulate", method="POST", value=legacy_envelope()))[2].startswith(b"OHLABV1\0")
