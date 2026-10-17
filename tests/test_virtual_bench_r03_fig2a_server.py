"""Real A routes share the existing seven-operation actual-worker gate."""

import asyncio
import json
import threading

import pytest

from apps.virtual_bench import r03_fig2a_adapter as adapter
from apps.virtual_bench import r03_fig2a_protocol as protocol
from apps.virtual_bench import server
from test_virtual_bench_r03_fig2a_adapter import envelope
from test_virtual_bench_polarized_two_path_server import (
    OPERATIONS as OLD_OPERATIONS, real_worker as old_worker,
    request_for as old_request, validate_all as old_validate_all,
)
from test_virtual_bench_two_path_server import ControlledExecutor, call
from test_virtual_bench_polarized_two_path_documents import document

VALIDATE = "/api/research/r03-fig2a/validate"
SIMULATE = "/api/research/r03-fig2a/simulate"
OPERATIONS = (*OLD_OPERATIONS, "ideal")
PAIRS = [("ideal", operation) for operation in OPERATIONS] + [(operation, "ideal") for operation in OLD_OPERATIONS]


def request_for(operation):
    return (SIMULATE, envelope(digested=True)) if operation == "ideal" else old_request(operation)


def real_worker(submission):
    if isinstance(submission, adapter.ValidatedIdealSubmission):
        return adapter.simulate_submission(submission)
    return old_worker(submission)


@pytest.fixture
def make_app(tmp_path):
    assets = tmp_path / "assets"; assets.mkdir()
    (assets / "index.html").write_text("<!doctype html><title>Owned ideal workspace fixture</title>", encoding="utf-8")
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
        r03_ideal_worker=worker)


async def validate_all(app):
    await old_validate_all(app)
    status, _, body = await call(app, VALIDATE, method="POST", value=envelope())
    assert status == 200 and json.loads(body)["message_type"] == "r03_ideal_validation"
    assert app.state.gate.busy


def test_real_validate_is_noncomputing_and_single_compute_has_bound_complete_identity(make_app, monkeypatch):
    calls = []
    original = adapter.run_ideal_polarization
    def run(spec):
        calls.append(spec)
        return original(spec)
    monkeypatch.setattr(adapter, "run_ideal_polarization", run)
    app = make_app()
    status, _, body = asyncio.run(call(app, VALIDATE, method="POST", value=envelope()))
    validated = json.loads(body)
    assert status == 200 and not calls and not app.state.gate.busy
    assert set(validated) == {"protocol_version", "message_type", "request_id", "experiment_sha256", "experiment"}
    status, headers, body = asyncio.run(call(app, SIMULATE, method="POST", value=envelope(digested=True)))
    actual = json.loads(body)
    assert status == 200 and headers[b"content-type"] == b"application/json"
    assert len(calls) == 1 and app.state.gate.wait_idle(5)
    assert actual["experiment_sha256"] == validated["experiment_sha256"]
    assert actual["request_id"] == validated["request_id"]
    assert len(actual["phase"]["wrapped_rad"]) == 256


@pytest.mark.parametrize("active,blocked", PAIRS)
def test_new_actual_gate_both_directions_all_seven_old_routes_no_queue(make_app, active, blocked):
    started, release = threading.Event(), threading.Event()
    calls = []
    def controlled(submission):
        calls.append(submission.request_id); started.set()
        assert release.wait(5)
        return real_worker(submission)
    app = controlled_app(make_app, controlled)
    async def check():
        path, value = request_for(active)
        first = asyncio.create_task(call(app, path, method="POST", value=value))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            other_path, other_value = request_for(blocked)
            assert (await call(app, other_path, method="POST", value=other_value))[0] == 409, "R03_SHARED_GATE_DETECTED"
            assert len(calls) == 1, "R03_SHARED_GATE_DETECTED"
            await validate_all(app)
        finally:
            release.set()
        assert (await first)[0] == 200
        assert await asyncio.to_thread(app.state.gate.wait_idle, 5)
        assert (await call(app, other_path, method="POST", value=other_value))[0] == 200
        assert len(calls) == 2
    asyncio.run(check())


@pytest.mark.parametrize("active", OPERATIONS)
@pytest.mark.parametrize("abort", ["disconnect", "handler_cancel"])
def test_disconnect_or_waiter_cancel_cannot_release_running_gate_for_new_or_old_work(make_app, active, abort):
    started, release, ended = threading.Event(), threading.Event(), threading.Event()
    def controlled(submission):
        started.set(); assert release.wait(5)
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
                disconnected.set(); assert (await first)[0] == 499
            else:
                first.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await first
            assert app.state.gate.busy and not ended.is_set(), "R03_WORKER_LIFETIME_DETECTED"
            for operation in OPERATIONS:
                blocked_path, blocked_value = request_for(operation)
                assert (await call(app, blocked_path, method="POST", value=blocked_value))[0] == 409
            await validate_all(app)
        finally:
            release.set()
        assert await asyncio.to_thread(app.state.gate.wait_idle, 5)
        assert ended.is_set()
    asyncio.run(check())


def test_gate_includes_final_ideal_encoding_after_disconnect(make_app, monkeypatch):
    started, release = threading.Event(), threading.Event()
    original = adapter.encode_result
    def hold(*args, **kwargs):
        started.set(); assert release.wait(5)
        return original(*args, **kwargs)
    monkeypatch.setattr(adapter, "encode_result", hold)
    app = make_app()
    async def check():
        disconnected = asyncio.Event()
        first = asyncio.create_task(call(app, SIMULATE, method="POST", value=envelope(digested=True), disconnected=disconnected))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            disconnected.set(); assert (await first)[0] == 499
            assert app.state.gate.busy, "R03_ENCODING_LIFETIME_DETECTED"
            for operation in OPERATIONS:
                path, value = request_for(operation)
                assert (await call(app, path, method="POST", value=value))[0] == 409
            await validate_all(app)
        finally:
            release.set()
        assert await asyncio.to_thread(app.state.gate.wait_idle, 5)
    asyncio.run(check())


@pytest.mark.parametrize("failure", ["numerical", "encoding", "invalid_reply", "oversize_reply"])
def test_failure_types_release_gate_and_require_another_deliberate_submission(make_app, failure):
    failing = [True]
    def controlled(submission):
        if failing[0]:
            if failure == "numerical":
                raise adapter.NumericalError("controlled arithmetic")
            if failure == "encoding":
                raise RuntimeError("private internal serializer detail")
            return b"x" if failure == "invalid_reply" else b"x" * (protocol.MAX_RESPONSE_BYTES + 1)
        return real_worker(submission)
    app = make_app(r03_ideal_worker=controlled)
    status, _, body = asyncio.run(call(app, SIMULATE, method="POST", value=envelope(digested=True)))
    assert status == (422 if failure == "numerical" else 500)
    assert json.loads(body)["message_type"] == "r03_ideal_error"
    assert b"private internal" not in body and app.state.gate.wait_idle(5)
    failing[0] = False
    assert asyncio.run(call(app, SIMULATE, method="POST", value=envelope(digested=True)))[0] == 200


def test_submission_failure_and_cancel_before_start_release_existing_gate(make_app):
    executor = ControlledExecutor(); app = make_app(executor=executor)
    status, _, body = asyncio.run(call(app, SIMULATE, method="POST", value=envelope(digested=True)))
    assert status == 500 and json.loads(body)["error"]["code"] == "submission_failed"
    assert not app.state.gate.busy
    executor.fail = False
    status, _, body = asyncio.run(call(app, SIMULATE, method="POST", value=envelope(digested=True)))
    assert status == 503 and json.loads(body)["error"]["code"] == "cancelled_before_start"
    assert not app.state.gate.busy


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'{"a":1e-999}', b'\xff'])
def test_strict_body_and_security_policy_applies_to_new_routes(make_app, raw):
    app = make_app(r03_ideal_worker=lambda _: pytest.fail("worker reached"))
    status, headers, body = asyncio.run(call(app, SIMULATE, method="POST", raw=raw))
    assert status == 400 and json.loads(body)["message_type"] == "r03_ideal_error"
    assert headers[b"cache-control"] == b"no-store" and headers[b"x-content-type-options"] == b"nosniff"
    assert b"access-control-allow-origin" not in headers


def test_methods_body_limits_exact_host_origin_and_closed_documents_are_preserved(make_app):
    app = make_app()
    for path in (VALIDATE, SIMULATE):
        assert asyncio.run(call(app, path))[0] == 405
        assert asyncio.run(call(app, path, method="POST", raw=b" " * 32769))[0] == 413
    for key, value, expected in ((b"host", b"localhost:8510", 400), (b"origin", b"https://example.com", 403)):
        headers = [(b"host", server.AUTHORITY.encode()), (b"origin", server.ORIGIN.encode()),
                   (b"content-type", b"application/json")]
        headers = [item for item in headers if item[0] != key] + [(key, value)]
        assert asyncio.run(call(app, SIMULATE, method="POST", value=envelope(digested=True), headers=headers))[0] == expected
    assert asyncio.run(call(app, "/api/v2e/documents/validate", method="POST", value=envelope()))[0] == 422
    assert asyncio.run(call(app, "/api/v2e/documents/validate", method="POST", value=document()))[0] == 200
    for operation in OLD_OPERATIONS:
        path, value = request_for(operation)
        assert asyncio.run(call(app, SIMULATE, method="POST", value=value))[0] == 422
        assert asyncio.run(call(app, path, method="POST", value=envelope(digested=True)))[0] == 422
