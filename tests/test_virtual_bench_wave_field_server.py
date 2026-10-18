"""Actual W1 ASGI route and the sole worker's compute/encoding lifetime."""

import asyncio
import json
import threading

import pytest

from apps.virtual_bench import server
from apps.virtual_bench import wave_field_adapter as adapter
from apps.virtual_bench import wave_field_protocol as protocol
from test_virtual_bench_r03_fig2a_server import (
    OPERATIONS as OLD_OPERATIONS, real_worker as old_worker,
    request_for as old_request, validate_all,
)
from test_virtual_bench_two_path_server import ControlledExecutor, call
from test_virtual_bench_wave_field_adapter import envelope, unpack

SIMULATE = "/api/w1/simulate"
OPERATIONS = (*OLD_OPERATIONS, "wave_field")
PAIRS = [("wave_field", kind) for kind in OPERATIONS] + [(kind, "wave_field") for kind in OLD_OPERATIONS]


def request_for(operation):
    return (SIMULATE, envelope()) if operation == "wave_field" else old_request(operation)


def real_worker(submission):
    if isinstance(submission, adapter.ValidatedWaveFieldSubmission):
        return adapter.simulate_submission(submission)
    return old_worker(submission)


@pytest.fixture
def make_app(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "index.html").write_text("<!doctype html><title>Owned W1 fixture</title>", encoding="utf-8")
    applications = []
    def factory(**kwargs):
        app = server.create_app(assets_dir=assets, **kwargs)
        applications.append(app)
        return app
    yield factory
    for app in applications:
        app.state.gate.shutdown()


def controlled_app(make_app, worker):
    return make_app(worker=worker, two_path_worker=worker, sweep_worker=worker,
        polarization_worker=worker, polarization_sweep_worker=worker,
        polarized_two_path_worker=worker, polarized_two_path_sweep_worker=worker,
        r03_ideal_worker=worker, wave_field_worker=worker)


def test_genuine_route_is_distinct_and_old_validation_remains_noncomputing(make_app, monkeypatch):
    calls = []
    original = adapter.sample_wave_field
    def sample(*args, **kwargs):
        calls.append(kwargs["interior_z_m"])
        return original(*args, **kwargs)
    monkeypatch.setattr(adapter, "sample_wave_field", sample)
    app = make_app()
    value = envelope()
    old = {key: value[key] for key in ("request_id", "experiment")}
    assert asyncio.run(call(app, "/api/v1/validate", method="POST", value=old))[0] == 200 and not calls
    status, headers, frame = asyncio.run(call(app, SIMULATE, method="POST", value=value))
    result, _ = unpack(frame)
    assert status == 200 and headers[b"content-type"] == b"application/octet-stream"
    assert result["message_type"] == "w1_wave_field" and calls == [(0.001, 0.005, 0.015)]
    assert app.state.gate.wait_idle(5)
    assert asyncio.run(call(app, "/api/v1/simulate", method="POST", value=value))[0] == 422
    assert asyncio.run(call(app, SIMULATE, method="POST", value=old))[0] == 422
    assert asyncio.run(call(app, "/api/w1/validate", method="POST", value=value))[0] == 404


@pytest.mark.parametrize("active,blocked", PAIRS)
def test_w1_and_all_eight_old_operation_kinds_share_one_actual_gate(make_app, active, blocked):
    started, release = threading.Event(), threading.Event()
    calls = []
    def controlled(submission):
        calls.append(submission.request_id)
        started.set()
        assert release.wait(5), "test did not release actual worker"
        return real_worker(submission)
    app = controlled_app(make_app, controlled)
    async def check():
        path, value = request_for(active)
        first = asyncio.create_task(call(app, path, method="POST", value=value))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            other_path, other = request_for(blocked)
            assert (await call(app, other_path, method="POST", value=other))[0] == 409, "W1_SHARED_GATE_DETECTED"
            assert len(calls) == 1, "W1_SHARED_GATE_DETECTED"
            await validate_all(app)
        finally:
            release.set()
        assert (await first)[0] == 200
        assert await asyncio.to_thread(app.state.gate.wait_idle, 5)
        assert (await call(app, other_path, method="POST", value=other))[0] == 200
        assert len(calls) == 2
    asyncio.run(check())


@pytest.mark.parametrize("active", OPERATIONS)
@pytest.mark.parametrize("termination", ["disconnect", "handler_cancel"])
def test_disconnect_or_handler_cancellation_never_releases_running_ninth_gate(make_app, active, termination):
    started, release, ended = threading.Event(), threading.Event(), threading.Event()
    def controlled(submission):
        started.set()
        assert release.wait(5)
        try:
            return real_worker(submission)
        finally:
            ended.set()
    app = controlled_app(make_app, controlled)
    async def check():
        disconnected = asyncio.Event()
        path, value = request_for(active)
        first = asyncio.create_task(call(app, path, method="POST", value=value, disconnected=disconnected))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            if termination == "disconnect":
                disconnected.set()
                assert (await first)[0] == 499
            else:
                first.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await first
            assert app.state.gate.busy and not ended.is_set(), "W1_WORKER_LIFETIME_DETECTED"
            for operation in OPERATIONS:
                blocked_path, blocked = request_for(operation)
                assert (await call(app, blocked_path, method="POST", value=blocked))[0] == 409
            await validate_all(app)
        finally:
            release.set()
        assert await asyncio.to_thread(app.state.gate.wait_idle, 5)
        assert ended.is_set()
    asyncio.run(check())


@pytest.mark.parametrize("termination", ["disconnect", "handler_cancel"])
def test_gate_covers_w1_final_encoding_after_request_is_gone(make_app, monkeypatch, termination):
    started, release = threading.Event(), threading.Event()
    original = adapter.encode_result
    def hold(*args, **kwargs):
        started.set()
        assert release.wait(5)
        return original(*args, **kwargs)
    monkeypatch.setattr(adapter, "encode_result", hold)
    app = make_app()
    async def check():
        disconnected = asyncio.Event()
        first = asyncio.create_task(call(app, SIMULATE, method="POST", value=envelope(), disconnected=disconnected))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            if termination == "disconnect":
                disconnected.set()
                assert (await first)[0] == 499
            else:
                first.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await first
            assert app.state.gate.busy, "W1_ENCODING_LIFETIME_DETECTED"
            for operation in OPERATIONS:
                path, value = request_for(operation)
                assert (await call(app, path, method="POST", value=value))[0] == 409
            await validate_all(app)
        finally:
            release.set()
        assert await asyncio.to_thread(app.state.gate.wait_idle, 5)
    asyncio.run(check())


@pytest.mark.parametrize("failure", ["numerical", "encoding", "short_reply", "oversize_reply"])
def test_failure_has_no_partial_result_no_implicit_retry_and_releases_only_finished_work(make_app, failure):
    calls = []
    def fail(submission):
        calls.append(submission.request_id)
        if failure == "numerical":
            raise adapter.NumericalError("controlled section arithmetic")
        if failure == "encoding":
            raise RuntimeError("private encoder internals")
        return b"x" if failure == "short_reply" else b"x"*(protocol.MAX_RESPONSE_BYTES+1)
    app = make_app(wave_field_worker=fail)
    status, _, body = asyncio.run(call(app, SIMULATE, method="POST", value=envelope()))
    assert status == (422 if failure == "numerical" else 500)
    assert json.loads(body)["message_type"] == "w1_wave_field_error"
    assert b"private encoder" not in body and len(calls) == 1
    assert app.state.gate.wait_idle(5)


def test_submit_failure_and_cancel_before_start_release_reservation(make_app):
    executor = ControlledExecutor()
    app = make_app(executor=executor)
    status, _, body = asyncio.run(call(app, SIMULATE, method="POST", value=envelope()))
    assert status == 500 and json.loads(body)["error"]["code"] == "submission_failed"
    assert not app.state.gate.busy
    executor.fail = False
    status, _, body = asyncio.run(call(app, SIMULATE, method="POST", value=envelope()))
    assert status == 503 and json.loads(body)["error"]["code"] == "cancelled_before_start"
    assert not app.state.gate.busy


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'{"a":1e-999}', b'\xff'])
def test_strict_w1_json_and_unchanged_security_headers(make_app, raw):
    app = make_app(wave_field_worker=lambda _: pytest.fail("worker reached"))
    status, headers, body = asyncio.run(call(app, SIMULATE, method="POST", raw=raw))
    assert status == 400 and json.loads(body)["message_type"] == "w1_wave_field_error"
    assert headers[b"cache-control"] == b"no-store" and b"access-control-allow-origin" not in headers
    assert headers[b"x-content-type-options"] == b"nosniff"


def test_body_cap_methods_exact_origin_and_host_remain_enforced(make_app):
    app = make_app()
    assert asyncio.run(call(app, SIMULATE))[0] == 405
    assert asyncio.run(call(app, SIMULATE, method="POST", raw=b" "*32769))[0] == 413
    for key, value, expected in ((b"host", b"localhost:8510", 400), (b"origin", b"https://example.com", 403)):
        headers = [(b"host", server.AUTHORITY.encode()), (b"origin", server.ORIGIN.encode()),
                   (b"content-type", b"application/json")]
        headers = [pair for pair in headers if pair[0] != key] + [(key, value)]
        assert asyncio.run(call(app, SIMULATE, method="POST", value=envelope(), headers=headers))[0] == expected
