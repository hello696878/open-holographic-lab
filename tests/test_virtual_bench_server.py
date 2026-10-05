"""Stdlib ASGI harness and controlled worker lifetime tests, without listeners.

These tests do not replace genuine HTTP/browser acceptance. Events establish
ordering; bounded waits only prevent a broken implementation hanging the suite.
"""

import asyncio
from concurrent.futures import Executor, Future
import json
import os
from pathlib import Path
import subprocess
import threading

import pytest

from apps.virtual_bench import adapter, server
from apps.virtual_bench.protocol import MAGIC

REQUEST_ID = "12345678-1234-4234-8234-123456789abc"


def payload():
    return {"request_id": REQUEST_ID, "experiment": {
        "schema_version": 1, "model_contract": "v0_aligned_scalar_forward_v1",
        "wavelength_m": 633e-9, "grid": {"ny": 3, "nx": 4, "dy": 5e-6, "dx": 2e-6},
        "source": {"kind": "uniform", "amplitude": 2.0, "phase_rad": 0.0},
        "components": [], "observation": {"id": "screen", "z_m": 0.0}}}


async def call(app, path="/api/v1/health", *, method="GET", body=b"", headers=None,
               messages=None, disconnected=None):
    if headers is None:
        headers = [(b"host", server.AUTHORITY.encode())]
        if method == "POST":
            headers += [(b"origin", server.ORIGIN.encode()), (b"content-type", b"application/json")]
    scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
             "http_version": "1.1", "method": method, "scheme": "http", "path": path,
             "raw_path": path.encode(), "root_path": "", "query_string": b"",
             "headers": headers, "client": ("127.0.0.1", 12345), "server": ("127.0.0.1", 8510)}
    events = list(messages) if messages is not None else [{"type": "http.request", "body": body, "more_body": False}]
    blocked = asyncio.Event()
    captured = []

    async def receive():
        if events:
            return events.pop(0)
        if disconnected is not None:
            await disconnected.wait()
            return {"type": "http.disconnect"}
        await blocked.wait()
        raise AssertionError("unreachable receive")

    async def send(message):
        captured.append(message)

    await app(scope, receive, send)
    start = next(message for message in captured if message["type"] == "http.response.start")
    output = b"".join(message.get("body", b"") for message in captured if message["type"] == "http.response.body")
    return start["status"], dict(start["headers"]), output


def post(app, endpoint="validate", value=None, **kwargs):
    body = json.dumps(payload() if value is None else value, allow_nan=False).encode()
    return asyncio.run(call(app, f"/api/v1/{endpoint}", method="POST", body=body, **kwargs))


@pytest.fixture
def make_app(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "index.html").write_text("<!doctype html><title>owned V1 fixture</title>", encoding="utf-8")
    (assets / "main.js").write_text("console.log('local fixture')", encoding="utf-8")
    apps = []

    def factory(**kwargs):
        app = server.create_app(assets_dir=assets, **kwargs)
        apps.append(app)
        return app

    yield factory
    for app in apps:
        app.state.gate.shutdown()


def test_health_validation_and_actual_v0_frame(make_app, monkeypatch):
    calls = []
    original = adapter.run_experiment

    def counted(experiment, *, record_fields):
        calls.append(record_fields)
        return original(experiment, record_fields=record_fields)

    monkeypatch.setattr(adapter, "run_experiment", counted)
    app = make_app()
    status, headers, body = asyncio.run(call(app))
    assert status == 200
    assert json.loads(body) == {"protocol_version": 1, "status": "ok", "busy": False}
    assert headers[b"cache-control"] == b"no-store"
    assert b"access-control-allow-origin" not in headers
    status, _, body = post(app)
    validated = json.loads(body)
    assert status == 200 and calls == []
    assert set(validated) == {"protocol_version", "request_id", "experiment_sha256", "experiment"}
    assert validated["request_id"] == REQUEST_ID
    status, headers, frame = post(app, "simulate")
    assert status == 200 and headers[b"content-type"] == b"application/octet-stream"
    assert frame.startswith(MAGIC) and calls == [()]
    assert not app.state.gate.busy


@pytest.mark.parametrize("headers,status", [
    ([(b"host", b"localhost:8510")], 400),
    ([(b"host", b"127.0.0.1:8501")], 400),
    ([(b"host", b"127.0.0.1:8510"), (b"Host", b"127.0.0.1:8510")], 400),
    ([(b"host", b"127.0.0.1:8510"), (b"origin", b"http://evil.example")], 403),
    ([(b"host", b"127.0.0.1:8510")], 403),
    ([(b"host", b"127.0.0.1:8510"), (b"origin", b"http://127.0.0.1:8510"),
      (b"origin", b"http://127.0.0.1:8510")], 400),
    ([(b"host", b"127.0.0.1:8510"), (b"origin", b"http://127.0.0.1:8510"),
      (b"bad header", b"value")], 400),
    ([(b"host", b"127.0.0.1:8510"), (b"origin", b"http://127.0.0.1:8510"),
      (b"x-bad", b"bad\r\nvalue")], 400),
])
def test_exact_host_origin_and_malformed_duplicate_headers(make_app, headers, status):
    app = make_app(worker=lambda _: pytest.fail("worker reached"))
    result = asyncio.run(call(app, "/api/v1/simulate", method="POST", body=b"{}", headers=headers))
    assert result[0] == status
    assert json.loads(result[2])["request_id"] is None


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":{"q":1,"q":2}}', b'{"a":NaN}',
    b'{"a":Infinity}', b'{"a":-Infinity}', b'{"request_id":"x"', b'\xff'])
def test_strict_stream_json_errors_have_no_partial_solver_result(make_app, raw):
    app = make_app(worker=lambda _: pytest.fail("worker reached"))
    status, _, body = asyncio.run(call(app, "/api/v1/simulate", method="POST", body=raw))
    assert status == 400
    assert json.loads(body)["error"]["code"] == "invalid_json"


def test_finite_json_number_overflow_is_transport_error(make_app):
    app = make_app(worker=lambda _: pytest.fail("worker reached"))
    status, _, body = asyncio.run(call(app, "/api/v1/simulate", method="POST", body=b'{"a":1e999}'))
    assert status == 400 and json.loads(body)["error"]["code"] == "invalid_json"


def test_streamed_byte_cap_and_declared_length_not_only_content_length(make_app):
    app = make_app(worker=lambda _: pytest.fail("worker reached"))
    chunks = [{"type": "http.request", "body": b" " * 16384, "more_body": True},
              {"type": "http.request", "body": b" " * 16385, "more_body": False}]
    status, _, body = asyncio.run(call(app, "/api/v1/simulate", method="POST", messages=chunks))
    assert status == 413 and json.loads(body)["error"]["code"] == "body_too_large"
    headers = [(b"host", server.AUTHORITY.encode()), (b"origin", server.ORIGIN.encode()),
               (b"content-type", b"application/json"), (b"content-length", b"32769")]
    assert post(app, headers=headers)[0] == 413
    headers[-1] = (b"content-length", b"1")
    assert post(app, headers=headers)[0] == 400
    headers.append((b"transfer-encoding", b"chunked"))
    assert post(app, headers=headers)[0] == 400
    headers.pop()
    headers[-1] = (b"content-length", b"-1")
    assert post(app, headers=headers)[0] == 400


def test_body_read_timeout_and_unsupported_content_type(make_app, monkeypatch):
    app = make_app(worker=lambda _: pytest.fail("worker reached"))
    monkeypatch.setattr(server, "BODY_TIMEOUT_SECONDS", 0)
    status, _, body = asyncio.run(call(app, "/api/v1/simulate", method="POST", messages=[
        {"type": "http.request", "body": b"", "more_body": True}]))
    assert status == 408 and json.loads(body)["error"]["code"] == "body_timeout"
    headers = [(b"host", server.AUTHORITY.encode()), (b"origin", server.ORIGIN.encode()),
               (b"content-type", b"text/plain")]
    assert post(app, headers=headers)[0] == 415


def test_invalid_scientific_request_preserves_id_and_fails_before_worker(make_app):
    app = make_app(worker=lambda _: pytest.fail("worker reached"))
    value = payload()
    value["experiment"]["grid"]["ny"] = 513
    status, _, body = post(app, "simulate", value)
    decoded = json.loads(body)
    assert status == 422 and decoded["request_id"] == REQUEST_ID
    assert "1..512" in decoded["error"]["message"]
    assert not app.state.gate.busy


def test_real_v0_arithmetic_failure_is_separate_from_zero_source_and_encoding_failure(make_app):
    app = make_app()
    value = payload()
    value["experiment"]["source"]["amplitude"] = 1e-250
    assert post(app, "validate", value)[0] == 200
    status, _, body = post(app, "simulate", value)
    decoded = json.loads(body)
    assert status == 422 and decoded["error"]["code"] == "numerical_failure"
    assert "norm" in decoded["error"]["message"] and not app.state.gate.busy
    value["experiment"]["source"]["amplitude"] = 0
    assert post(app, "simulate", value)[0] == 200


@pytest.mark.parametrize("termination", ["success", "numerical", "encoding"])
def test_worker_lifetime_busy_responsiveness_completion_and_failure(make_app, termination):
    started = threading.Event()
    release = threading.Event()
    calls = []

    def controlled(submission):
        calls.append(submission.request_id)
        started.set()
        assert release.wait(5), "test did not release worker"
        if termination == "numerical":
            raise adapter.NumericalError("sampled norm is unusable")
        if termination == "encoding":
            raise RuntimeError("private encoding path must not be disclosed")
        return adapter.simulate_submission(submission)

    app = make_app(worker=controlled)

    async def check():
        body = json.dumps(payload()).encode()
        first = asyncio.create_task(call(app, "/api/v1/simulate", method="POST", body=body))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            status, _, busy = await call(app)
            assert status == 200 and json.loads(busy)["busy"] is True
            assert (await call(app, "/api/v1/validate", method="POST", body=body))[0] == 200
            assert (await call(app, "/api/v1/simulate", method="POST", body=body))[0] == 409
            assert calls == [REQUEST_ID]
        finally:
            release.set()
        status, _, output = await first
        assert status == {"success": 200, "numerical": 422, "encoding": 500}[termination]
        if termination == "encoding":
            assert b"private encoding path" not in output
        assert await asyncio.to_thread(app.state.gate.wait_idle, 5)
        assert not app.state.gate.busy
        assert (await call(app, "/api/v1/simulate", method="POST", body=body))[0] == status
        assert calls == [REQUEST_ID, REQUEST_ID]

    asyncio.run(check())


@pytest.mark.parametrize("abort", ["disconnect", "handler_cancel"])
def test_disconnect_or_handler_abort_does_not_cancel_running_python_or_release_gate(make_app, abort):
    started = threading.Event()
    release = threading.Event()
    ended = threading.Event()
    calls = []

    def controlled(submission):
        calls.append(submission.request_id)
        started.set()
        assert release.wait(5), "test did not release worker"
        try:
            return adapter.simulate_submission(submission)
        finally:
            ended.set()

    app = make_app(worker=controlled)

    async def check():
        body = json.dumps(payload()).encode()
        disconnected = asyncio.Event()
        first = asyncio.create_task(call(app, "/api/v1/simulate", method="POST", body=body,
                                         disconnected=disconnected))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            if abort == "disconnect":
                disconnected.set()
                assert (await first)[0] == 499
            else:
                first.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await first
            assert not ended.is_set()
            assert app.state.gate.busy
            assert (await call(app, "/api/v1/simulate", method="POST", body=body))[0] == 409
            assert json.loads((await call(app))[2])["busy"] is True
            assert (await call(app, "/api/v1/validate", method="POST", body=body))[0] == 200
            assert calls == [REQUEST_ID]
        finally:
            release.set()
        assert await asyncio.to_thread(app.state.gate.wait_idle, 5)
        assert ended.is_set() and not app.state.gate.busy
        assert (await call(app, "/api/v1/simulate", method="POST", body=body))[0] == 200
        assert calls == [REQUEST_ID, REQUEST_ID]

    asyncio.run(check())


class ControlledExecutor(Executor):
    def __init__(self, fail=False):
        self.fail = fail
        self.future = None
        self.calls = 0

    def submit(self, function, /, *args, **kwargs):
        self.calls += 1
        if self.fail:
            raise RuntimeError("executor refused submission")
        self.future = Future()
        return self.future

    def shutdown(self, wait=True, *, cancel_futures=False):
        if cancel_futures and self.future is not None:
            self.future.cancel()


def test_executor_submission_failure_releases_reservation_and_later_request_can_submit(make_app):
    executor = ControlledExecutor(fail=True)
    app = make_app(executor=executor)
    status, _, body = post(app, "simulate")
    assert status == 500 and json.loads(body)["error"]["code"] == "submission_failed"
    assert app.state.gate.wait_idle(0) and not app.state.gate.busy
    executor.fail = False
    future = app.state.gate.submit(adapter.validate_submission(payload()))
    assert app.state.gate.busy and executor.calls == 2
    future.set_result(b"completed")
    assert app.state.gate.wait_idle(0) and not app.state.gate.busy


def test_supported_future_cancellation_before_start_releases_without_running_worker():
    executor = ControlledExecutor()
    calls = []
    gate = server.ComputationGate(lambda value: calls.append(value), executor)
    try:
        first = gate.submit(adapter.validate_submission(payload()))
        assert gate.busy
        with pytest.raises(server.BusyError):
            gate.submit(adapter.validate_submission(payload()))
        assert first.cancel() is True
        assert calls == [] and gate.wait_idle(0) and not gate.busy
        second = gate.submit(adapter.validate_submission(payload()))
        second.set_result(b"done")
        assert calls == [] and gate.wait_idle(0) and not gate.busy
    finally:
        gate.shutdown()


def test_before_start_cancellation_is_a_bounded_api_failure(make_app):
    class CancellingExecutor(ControlledExecutor):
        def submit(self, function, /, *args, **kwargs):
            future = super().submit(function, *args, **kwargs)
            future.cancel()
            return future

    app = make_app(executor=CancellingExecutor(), worker=lambda _: pytest.fail("worker reached"))
    status, _, body = post(app, "simulate")
    assert status == 503
    assert json.loads(body)["error"]["code"] == "cancelled_before_start"
    assert not app.state.gate.busy


def test_simultaneous_disconnect_and_worker_exception_is_consumed_without_warning(make_app):
    class FailingExecutor(ControlledExecutor):
        def submit(self, function, /, *args, **kwargs):
            future = super().submit(function, *args, **kwargs)
            future.set_exception(RuntimeError("synthetic encoding failure"))
            return future

    app = make_app(executor=FailingExecutor())

    async def check():
        errors = []
        loop = asyncio.get_running_loop()
        previous = loop.get_exception_handler()
        loop.set_exception_handler(lambda loop, context: errors.append(context))
        disconnected = asyncio.Event()
        disconnected.set()
        try:
            status, _, _ = await call(app, "/api/v1/simulate", method="POST",
                                      body=json.dumps(payload()).encode(), disconnected=disconnected)
            assert status in (499, 500)
            assert not app.state.gate.busy
            # One explicit loop turn collects done callbacks, not a timing guess.
            ready = loop.create_future()
            loop.call_soon(ready.set_result, None)
            await ready
            assert errors == []
        finally:
            loop.set_exception_handler(previous)

    asyncio.run(check())


@pytest.mark.parametrize("path", ["/../outside.js", "/assets/../../outside.js", "/.env", "/main.js.map",
    "/C:/secret.txt", "/main\\other.js", "/missing", "/api/v1/unknown"])
def test_owned_static_directory_does_not_expose_other_paths(make_app, path):
    app = make_app()
    status, _, body = asyncio.run(call(app, path))
    assert status == 404
    assert b"C:" not in body and b"Traceback" not in body


def test_serves_regular_build_only_and_security_headers(make_app):
    app = make_app()
    status, headers, body = asyncio.run(call(app, "/"))
    assert status == 200 and b"owned V1 fixture" in body
    assert headers[b"x-content-type-options"] == b"nosniff"
    assert b"script-src 'self'" in headers[b"content-security-policy"]
    assert b"'unsafe-eval'" not in headers[b"content-security-policy"]
    assert asyncio.run(call(app, "/main.js"))[0] == 200
    assert asyncio.run(call(app, "/api/v1/simulate"))[0] == 405


def test_real_directory_link_cannot_serve_outside_or_be_asset_root(tmp_path):
    assets = tmp_path / "assets"
    outside = tmp_path / "outside"
    assets.mkdir()
    outside.mkdir()
    (assets / "index.html").write_text("owned", encoding="utf-8")
    (outside / "index.html").write_text("private", encoding="utf-8")
    (outside / "private.js").write_text("private", encoding="utf-8")
    link = assets / "link"
    if os.name == "nt":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)],
                                capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        link.symlink_to(outside, target_is_directory=True)
    try:
        with pytest.raises(RuntimeError, match="Build V1"):
            server.create_app(assets_dir=link)
        app = server.create_app(assets_dir=assets)
        try:
            assert asyncio.run(call(app, "/link/private.js"))[0] == 404
            assert asyncio.run(call(app, "/link/index.html"))[0] == 404
        finally:
            app.state.gate.shutdown()
    finally:
        if os.name == "nt":
            link.rmdir()  # Remove the known owned junction itself, not its target.
        else:
            link.unlink()


def test_missing_assets_is_actionable_import_does_not_start_service(tmp_path):
    with pytest.raises(RuntimeError, match="Build V1 frontend assets"):
        server.create_app(assets_dir=tmp_path / "missing")
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(RuntimeError, match="Build V1 frontend assets"):
        server.create_app(assets_dir=empty)
