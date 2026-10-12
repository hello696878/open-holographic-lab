"""Real ASGI V2d routes and the single actual-worker-lifetime cross-mode gate."""

import asyncio
import json
import threading

import pytest

from apps.virtual_bench import adapter as legacy
from apps.virtual_bench import polarization_adapter as adapter
from apps.virtual_bench import polarization_protocol as protocol
from apps.virtual_bench import server, two_path_adapter
from test_virtual_bench_polarization_adapter import (REQUEST_ID, digested, envelope,
                                                     polarizer, retarder, sweep_envelope, unpack)
from test_virtual_bench_two_path_adapter import envelope as dual_envelope
from test_virtual_bench_two_path_server import (ControlledExecutor, call,
                                                legacy_envelope, request_for as old_request)

OPERATIONS = ("sequential", "dual", "sweep", "polarization", "polarization_sweep")


def request_for(operation):
    if operation == "polarization":
        return "/api/v2d/simulate", digested()
    if operation == "polarization_sweep":
        return "/api/v2d/sweep", sweep_envelope()
    path, value = old_request(operation)
    value["request_id"] = REQUEST_ID
    return path, value


def real_worker(submission):
    if isinstance(submission, adapter.ValidatedPolarizationSweepSubmission):
        return adapter.sweep_submission(submission)
    if isinstance(submission, adapter.ValidatedPolarizationSubmission):
        return adapter.simulate_submission(submission)
    if isinstance(submission, legacy.ValidatedSubmission):
        return legacy.simulate_submission(submission)
    if isinstance(submission, two_path_adapter.ValidatedTwoPathSubmission):
        return two_path_adapter.simulate_submission(submission)
    return two_path_adapter.sweep_submission(submission)


@pytest.fixture
def make_app(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "index.html").write_text("<!doctype html><title>Owned V2d ASGI acceptance</title>", encoding="utf-8")
    applications = []
    def factory(**kwargs):
        application = server.create_app(assets_dir=assets, **kwargs)
        applications.append(application)
        return application
    yield factory
    for application in applications:
        application.state.gate.shutdown()


def controlled_app(make_app, worker):
    return make_app(worker=worker, two_path_worker=worker, sweep_worker=worker,
                    polarization_worker=worker, polarization_sweep_worker=worker)


async def validate_all(app):
    for path, value in (("/api/v1/validate", legacy_envelope()),
                        ("/api/v2b/validate", dual_envelope()),
                        ("/api/v2d/validate", envelope())):
        assert (await call(app, path, method="POST", value=value))[0] == 200
    assert json.loads((await call(app))[2])["busy"] is True


def test_actual_routes_validate_zero_actions_then_real_simulation_and_sweep(make_app, monkeypatch):
    calls = []
    original = adapter.apply_linear_polarizer
    def action(field, **kwargs):
        calls.append(kwargs["axis_angle_rad"])
        return original(field, **kwargs)
    monkeypatch.setattr(adapter, "apply_linear_polarizer", action)
    app = make_app()
    status, _, body = asyncio.run(call(app, "/api/v2d/validate", method="POST", value=envelope()))
    assert status == 200 and calls == []
    validation = json.loads(body)
    assert set(validation) == {"protocol_version", "message_type", "request_id", "experiment_sha256", "experiment"}
    assert validation["message_type"] == "polarization_validation"
    value = envelope(); value["experiment_sha256"] = validation["experiment_sha256"]
    status, headers, frame = asyncio.run(call(app, "/api/v2d/simulate", method="POST", value=value))
    assert status == 200 and headers[b"content-type"] == b"application/octet-stream"
    result, _ = unpack(frame)
    assert result["experiment_sha256"] == validation["experiment_sha256"] and calls == [.31]
    status, headers, body = asyncio.run(call(app, "/api/v2d/sweep", method="POST", value=sweep_envelope()))
    assert status == 200 and json.loads(body)["completed_count"] == 13
    assert calls == [.31, *protocol.ANGLES_RAD] and headers[b"content-type"] == b"application/json"
    assert app.state.gate.wait_idle(5)


@pytest.mark.parametrize("active", OPERATIONS)
@pytest.mark.parametrize("blocked", OPERATIONS)
def test_one_actual_gate_all_five_by_five_rejects_without_queue(make_app, active, blocked):
    started, release = threading.Event(), threading.Event()
    calls = []
    def controlled(submission):
        calls.append(submission.request_id)
        started.set()
        assert release.wait(5), "test failed to release worker"
        return real_worker(submission)
    app = controlled_app(make_app, controlled)
    async def check():
        path, value = request_for(active)
        first = asyncio.create_task(call(app, path, method="POST", value=value))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            other_path, other_value = request_for(blocked)
            assert (await call(app, other_path, method="POST", value=other_value))[0] == 409, "SHARED_GATE_DETECTED"
            assert calls == [REQUEST_ID], "SHARED_GATE_DETECTED"
            await validate_all(app)
        finally:
            release.set()
        assert (await first)[0] == 200
        assert await asyncio.to_thread(app.state.gate.wait_idle, 5)
        assert (await call(app, other_path, method="POST", value=other_value))[0] == 200
        assert calls == [REQUEST_ID, REQUEST_ID], "SHARED_GATE_DETECTED"
    asyncio.run(check())


@pytest.mark.parametrize("active", OPERATIONS)
@pytest.mark.parametrize("abort", ["disconnect", "handler_cancel"])
def test_abort_holds_gate_for_every_actual_worker_until_terminal_completion(make_app, active, abort):
    started, release, ended = threading.Event(), threading.Event(), threading.Event()
    calls = []
    def controlled(submission):
        calls.append(submission.request_id)
        started.set()
        assert release.wait(5)
        try:
            return real_worker(submission)
        finally:
            ended.set()
    app = controlled_app(make_app, controlled)
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
                with pytest.raises(asyncio.CancelledError): await first
            assert not ended.is_set() and app.state.gate.busy, "WORKER_LIFETIME_DETECTED"
            for operation in OPERATIONS:
                other_path, other_value = request_for(operation)
                assert (await call(app, other_path, method="POST", value=other_value))[0] == 409, "WORKER_LIFETIME_DETECTED"
            assert calls == [REQUEST_ID], "WORKER_LIFETIME_DETECTED"
            await validate_all(app)
        finally:
            release.set()
        assert await asyncio.to_thread(app.state.gate.wait_idle, 5)
        assert ended.is_set() and not app.state.gate.busy
        assert (await call(app, path, method="POST", value=value))[0] == 200
    asyncio.run(check())


@pytest.mark.parametrize("operation", ["polarization", "polarization_sweep"])
@pytest.mark.parametrize("abort", ["disconnect", "handler_cancel"])
def test_gate_includes_real_result_encoding_after_numerics_and_abort(make_app, monkeypatch, operation, abort):
    encoding, release = threading.Event(), threading.Event()
    name = "encode_result" if operation == "polarization" else "encode_sweep_reply"
    original = getattr(adapter, name)
    def encode(*args, **kwargs):
        encoding.set()
        assert release.wait(5)
        return original(*args, **kwargs)
    monkeypatch.setattr(adapter, name, encode)
    app = make_app()
    async def check():
        path, value = request_for(operation)
        disconnected = asyncio.Event()
        first = asyncio.create_task(call(app, path, method="POST", value=value, disconnected=disconnected))
        try:
            assert await asyncio.to_thread(encoding.wait, 5)
            if abort == "disconnect":
                disconnected.set()
                assert (await first)[0] == 499
            else:
                first.cancel()
                with pytest.raises(asyncio.CancelledError): await first
            assert app.state.gate.busy, "ENCODING_LIFETIME_DETECTED"
            for other in OPERATIONS:
                other_path, other_value = request_for(other)
                assert (await call(app, other_path, method="POST", value=other_value))[0] == 409, "ENCODING_LIFETIME_DETECTED"
            await validate_all(app)
        finally:
            release.set()
        assert await asyncio.to_thread(app.state.gate.wait_idle, 5)
    asyncio.run(check())


@pytest.mark.parametrize("operation", ["polarization", "polarization_sweep"])
@pytest.mark.parametrize("termination", ["numerical", "encoding", "invalid_reply", "oversize_reply"])
def test_failure_releases_actual_gate_and_explicit_recovery(make_app, operation, termination):
    fail = [True]
    def controlled(submission):
        if fail[0]:
            if termination == "numerical": raise adapter.NumericalError("controlled arithmetic")
            if termination == "encoding": raise RuntimeError("private encoder detail")
            body = b"x" if termination == "invalid_reply" else b"x"*(protocol.MAX_RESPONSE_BYTES+1)
            return body if operation == "polarization" else protocol.SweepReply(status_code=200, body=body)
        return real_worker(submission)
    app = make_app(polarization_worker=controlled, polarization_sweep_worker=controlled)
    path, value = request_for(operation)
    status, _, body = asyncio.run(call(app, path, method="POST", value=value))
    assert status == (422 if termination == "numerical" else 500)
    assert b"private encoder detail" not in body
    assert app.state.gate.wait_idle(5) and not app.state.gate.busy
    fail[0] = False
    assert asyncio.run(call(app, path, method="POST", value=value))[0] == 200


@pytest.mark.parametrize("operation", ["polarization", "polarization_sweep"])
def test_submission_failure_and_before_start_cancellation_release(make_app, operation):
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


@pytest.mark.parametrize("failed_index", [0, 3, 12])
@pytest.mark.parametrize("error_type,status", [(ValueError, 422), (RuntimeError, 500)])
def test_actual_failed_sweep_schema_status_genuine_prefix_and_gate_release(make_app, monkeypatch, failed_index, error_type, status):
    original, calls = adapter._run_train, []
    def fail(incident, experiment, **kwargs):
        calls.append(kwargs["axis_angle_rad"])
        if len(calls) == failed_index+1: raise error_type("controlled point failure")
        return original(incident, experiment, **kwargs)
    monkeypatch.setattr(adapter, "_run_train", fail)
    app = make_app()
    actual_status, headers, body = asyncio.run(call(app, "/api/v2d/sweep", method="POST", value=sweep_envelope()))
    value = json.loads(body)
    assert actual_status == status and headers[b"content-type"] == b"application/json"
    assert value["completed_count"] == value["failed_index"] == failed_index and len(value["rows"]) == failed_index
    assert len(calls) == failed_index+1 and calls == list(protocol.ANGLES_RAD[:failed_index+1])
    assert value["error"]["code"] == ("numerical_failure" if status == 422 else "sweep_failed")
    assert app.state.gate.wait_idle(5)


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'\xff'])
def test_strict_json_and_security_headers_preserved(make_app, raw):
    app = make_app(polarization_worker=lambda _: pytest.fail("worker reached"))
    status, headers, body = asyncio.run(call(app, "/api/v2d/simulate", method="POST", raw=raw))
    assert status == 400 and json.loads(body)["message_type"] == "polarization_error"
    assert b"access-control-allow-origin" not in headers
    assert headers[b"cache-control"] == b"no-store" and headers[b"x-content-type-options"] == b"nosniff"


def test_digest_required_and_legacy_envelopes_routes_caps_and_methods_preserved(make_app):
    app = make_app()
    for value in (envelope(), legacy_envelope(), dual_envelope()):
        assert asyncio.run(call(app, "/api/v2d/simulate", method="POST", value=value))[0] == 422
    assert asyncio.run(call(app, "/api/v2d/simulate", method="POST", raw=b" "*32769))[0] == 413
    assert asyncio.run(call(app, "/api/v2d/simulate"))[0] == 405
    assert asyncio.run(call(app, "/api/v2d/sweep", method="POST", value=digested()))[0] == 422
    assert asyncio.run(call(app, "/api/v1/simulate", method="POST", value=legacy_envelope()))[2].startswith(b"OHLABV1\0")
    assert asyncio.run(call(app, "/api/v2b/simulate", method="POST", value=dual_envelope()))[2].startswith(b"OHLAB2P\0")
    assert asyncio.run(call(app, "/api/v1/simulate", method="POST", value=digested()))[0] == 422
    assert asyncio.run(call(app, "/api/v2b/simulate", method="POST", value=digested()))[0] == 422


@pytest.mark.parametrize("header,expected", [((b"host", b"localhost:8510"), 400), ((b"origin", b"https://example.com"), 403)])
def test_exact_loopback_host_origin_boundary_unchanged(make_app, header, expected):
    app = make_app()
    headers = [(b"host", server.AUTHORITY.encode()), (b"origin", server.ORIGIN.encode()), (b"content-type", b"application/json")]
    headers = [pair for pair in headers if pair[0] != header[0]] + [header]
    status, _, _ = asyncio.run(call(app, "/api/v2d/simulate", method="POST", value=digested(), headers=headers))
    assert status == expected


@pytest.mark.parametrize("operation", ["polarization", "polarization_sweep"])
def test_actual_final_encoder_failure_is_separate_from_genuine_failed_prefix(make_app, monkeypatch, operation):
    calls = []
    original = adapter.apply_linear_polarizer
    def action(field, **kwargs):
        calls.append(kwargs["axis_angle_rad"])
        return original(field, **kwargs)
    def failure(*args, **kwargs):
        raise ValueError("controlled private final encoder detail")
    monkeypatch.setattr(adapter, "apply_linear_polarizer", action)
    monkeypatch.setattr(adapter, "encode_result" if operation == "polarization" else "encode_sweep_reply", failure)
    app = make_app()
    path, value = request_for(operation)
    status, _, body = asyncio.run(call(app, path, method="POST", value=value))
    reply = json.loads(body)
    assert status == 500 and reply["message_type"] == "polarization_error"
    assert reply["error"]["code"] == "simulation_failed" and "private" not in reply["error"]["message"]
    assert calls == ([.31] if operation == "polarization" else list(protocol.ANGLES_RAD))
    assert "rows" not in reply and app.state.gate.wait_idle(5)
