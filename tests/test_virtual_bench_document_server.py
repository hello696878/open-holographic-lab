"""Real ASGI document-route security and unchanged five-worker ownership."""

import asyncio
import builtins
import json
from pathlib import Path
import threading

import pytest

from apps.virtual_bench import experiment_documents as documents, server
from test_virtual_bench_experiment_documents import document, ordinary_submission, raw, MODES, REQUEST_ID
from test_virtual_bench_polarization_server import OPERATIONS, request_for, real_worker
from test_virtual_bench_two_path_server import call

ENDPOINT = "/api/v2e/documents/validate"


@pytest.fixture
def make_app(tmp_path):
    assets = tmp_path / "owned_assets"
    assets.mkdir()
    (assets / "index.html").write_text("<!doctype html><title>V2e owned fixture</title>", encoding="utf-8")
    apps = []
    def factory(**kwargs):
        app = server.create_app(assets_dir=assets, **kwargs)
        apps.append(app)
        return app
    yield factory
    for app in apps: app.state.gate.shutdown()


def post(app, value=None, **kwargs):
    return asyncio.run(call(app, ENDPOINT, method="POST", raw=raw(document() if value is None else value), **kwargs))


@pytest.mark.parametrize("mode", MODES)
def test_document_success_exact_canonical_body_header_and_normal_mode_validation(make_app, mode):
    app = make_app()
    value = document(mode)
    status, headers, body = post(app, value)
    normal = ordinary_submission(value)
    expected = {**value, "experiment": normal.experiment.to_dict()}
    expected_bytes = (json.dumps(expected, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
    assert status == 200 and headers[b"content-type"] == b"application/json"
    assert body == expected_bytes, "DOCUMENT_NUMERIC_BITS_DETECTED"
    assert headers[b"x-ohlab-experiment-sha256"].decode() == normal.experiment_sha256, "DOCUMENT_DIGEST_CONTRACT_DETECTED"
    assert headers[b"cache-control"] == b"no-store" and headers[b"x-content-type-options"] == b"nosniff"
    assert b"access-control-allow-origin" not in headers
    assert not app.state.gate.busy
    assert asyncio.run(call(app, ENDPOINT, method="POST", raw=body))[2] == body


@pytest.mark.parametrize("encoded", [b'{"x":1,"\\u0078":2}', b'{"x":{"a":1,"a":2}}',
    b'\xff', b'\xef\xbb\xbf{}', b'{', b'{"x":NaN}', b'{"x":Infinity}',
    b'{"x":1e999}', b'{"x":1e-999}', b'['*3000, b'['*1500+b'0'+b']'*1500,
    b'{"x":'+b'8'*5000+b'}', b'{"x":'+b'8'*400+b'}'],
    ids=["escaped_duplicate", "nested_duplicate", "invalid_utf8", "bom", "truncated", "nan",
         "infinity", "overflow", "underflow", "recursion", "complete_recursion", "unusable_integer", "overflow_integer"])
def test_raw_failures_precede_document_or_scientific_validation(make_app, monkeypatch, encoded):
    app = make_app()
    def forbidden(*args, **kwargs): pytest.fail("RAW_DUPLICATE_KEYS_DETECTED")
    monkeypatch.setattr(documents, "validate_document", forbidden)
    status, _, body = asyncio.run(call(app, ENDPOINT, method="POST", raw=encoded))
    assert status == 400 and json.loads(body)["error"]["code"] == "invalid_json", "RAW_DUPLICATE_KEYS_DETECTED"


def test_document_second_numeric_decode_recursion_is_raw_400_before_mode(make_app, monkeypatch):
    app = make_app()
    encoded = raw(document())
    original = json.loads
    calls = []
    def controlled(*args, **kwargs):
        calls.append(kwargs)
        if "parse_int" in kwargs:
            raise RecursionError("controlled numeric decoder recursion")
        return original(*args, **kwargs)
    def forbidden(*args, **kwargs): pytest.fail("DOCUMENT_PARSER_RECURSION_DETECTED: mode constructor reached")
    monkeypatch.setattr(documents.json, "loads", controlled)
    monkeypatch.setattr(documents, "validate_sequential", forbidden)
    status, _, body = asyncio.run(call(app, ENDPOINT, method="POST", raw=encoded))
    assert status == 400, "DOCUMENT_PARSER_RECURSION_DETECTED"
    assert original(body)["error"]["code"] == "invalid_json", "DOCUMENT_PARSER_RECURSION_DETECTED"
    assert len(calls) == 2 and not app.state.gate.busy


@pytest.mark.parametrize("mutation,code", [
    (lambda d: d.update(document_version=True), "unsupported_document_version"),
    (lambda d: d.update(mode="unknown"), "unsupported_document_mode"),
    (lambda d: d.update(model_contract="unknown"), "unsupported_model_contract"),
    (lambda d: d.update(results=[]), "invalid_document"),
    (lambda d: d["metadata"].update(title="x"*121), "invalid_metadata"),
    (lambda d: d["experiment"]["grid"].update(nx=513), "invalid_experiment"),
    (lambda d: d.update(extra=[None]*2048), "document_structure_limit")])
def test_expected_document_failures_are_bounded_422_generic_errors(make_app, mutation, code):
    app = make_app()
    value = document(); mutation(value)
    status, headers, body = post(app, value)
    decoded = json.loads(body)
    assert status == 422 and set(decoded) == {"protocol_version", "request_id", "error"}
    assert decoded["protocol_version"] == 1 and decoded["request_id"] is None
    assert decoded["error"]["code"] == code and len(decoded["error"]["message"]) <= 300
    assert b"x-ohlab-experiment-sha256" not in headers and not app.state.gate.busy


def test_oversized_canonical_output_and_unexpected_error_are_not_partial_success(make_app, monkeypatch):
    app = make_app()
    original = documents.validate_document
    def oversized(*args): raise documents.DocumentError("canonical_document_too_large", "canonical output too large")
    monkeypatch.setattr(documents, "validate_document", oversized)
    status, headers, body = post(app)
    assert status == 422 and json.loads(body)["error"]["code"] == "canonical_document_too_large"
    assert b"x-ohlab-experiment-sha256" not in headers
    def broken(*args): raise RuntimeError("private validation detail")
    monkeypatch.setattr(documents, "validate_document", broken)
    status, _, body = post(app)
    assert status == 500 and json.loads(body)["error"]["code"] == "document_failed"
    assert b"private validation detail" not in body
    monkeypatch.setattr(documents, "validate_document", original)
    assert post(app)[0] == 200


def test_document_validation_never_uses_gate_executor_or_disk(make_app, monkeypatch):
    app = make_app()
    def forbidden(*args, **kwargs): pytest.fail("DOCUMENT_ZERO_COMPUTE_DETECTED")
    monkeypatch.setattr(app.state.gate, "submit", forbidden)
    monkeypatch.setattr(app.state.gate, "_completed", forbidden)
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    for mode in MODES:
        assert post(app, document(mode))[0] == 200, "DOCUMENT_ZERO_COMPUTE_DETECTED"
    assert not app.state.gate.busy


@pytest.mark.parametrize("active", OPERATIONS)
@pytest.mark.parametrize("abort", [False, True])
def test_document_validation_preserves_each_running_worker_and_disconnect_gate(make_app, active, abort):
    started, release, ended = threading.Event(), threading.Event(), threading.Event()
    calls = []
    def controlled(submission):
        calls.append(submission.request_id); started.set()
        assert release.wait(10), "test did not release owned worker"
        try: return real_worker(submission)
        finally: ended.set()
    app = make_app(worker=controlled, two_path_worker=controlled, sweep_worker=controlled,
                   polarization_worker=controlled, polarization_sweep_worker=controlled)
    async def check():
        endpoint, value = request_for(active)
        disconnected = asyncio.Event()
        first = asyncio.create_task(call(app, endpoint, method="POST", value=value, disconnected=disconnected))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            if abort:
                disconnected.set()
                assert (await first)[0] == 499
            for mode in MODES:
                status, _, _ = await call(app, ENDPOINT, method="POST", raw=raw(document(mode)))
                assert status == 200 and app.state.gate.busy and not ended.is_set(), "DOCUMENT_GATE_OWNERSHIP_DETECTED"
            assert json.loads((await call(app))[2])["busy"] is True, "DOCUMENT_GATE_OWNERSHIP_DETECTED"
            for operation in OPERATIONS:
                blocked_path, blocked_value = request_for(operation)
                assert (await call(app, blocked_path, method="POST", value=blocked_value))[0] == 409, "DOCUMENT_GATE_OWNERSHIP_DETECTED"
            assert calls == [value["request_id"]], "DOCUMENT_GATE_OWNERSHIP_DETECTED"
        finally:
            release.set()
        if not abort: assert (await first)[0] == 200
        assert await asyncio.to_thread(app.state.gate.wait_idle, 5)
        assert ended.is_set() and not app.state.gate.busy
        assert (await call(app, ENDPOINT, method="POST", raw=raw(document())))[0] == 200
    asyncio.run(check())


def test_document_route_framing_caps_mime_timeout_and_disconnect(make_app, monkeypatch):
    app = make_app()
    encoded = raw(document())
    assert asyncio.run(call(app, ENDPOINT, method="POST", raw=encoded+b" "*(32768-len(encoded))))[0] == 200
    for path in (ENDPOINT, "/api/v1/validate", "/api/v2b/validate", "/api/v2d/validate"):
        status, _, body = asyncio.run(call(app, path, method="POST", raw=b" "*32769))
        assert status == 413 and json.loads(body)["error"]["code"] == "body_too_large"
    headers = [(b"host", server.AUTHORITY.encode()), (b"origin", server.ORIGIN.encode()), (b"content-type", b"application/json")]
    for extra in ([(b"content-length", b"32769")], [(b"content-length", b"1")],
                  [(b"content-length", b"01x")], [(b"transfer-encoding", b"gzip")],
                  [(b"transfer-encoding", b"chunked"), (b"content-length", b"1")]):
        status, _, _ = post(app, headers=headers+extra)
        assert status == (413 if extra == [(b"content-length", b"32769")] else 400)
    chunks = [{"type": "http.request", "body": b" "*16384, "more_body": True},
              {"type": "http.request", "body": b" "*16385, "more_body": False}]
    assert asyncio.run(call(app, ENDPOINT, method="POST", messages=chunks))[0] == 413
    for content_type in (b"text/plain", b"application/json; charset=latin1", b"application/octet-stream"):
        assert post(app, headers=headers[:-1]+[(b"content-type", content_type)])[0] == 415
    assert post(app, headers=headers[:-1]+[(b"content-type", b" Application/JSON; Charset=UTF-8 ")])[0] == 200
    monkeypatch.setattr(server, "BODY_TIMEOUT_SECONDS", 0)
    status, _, body = asyncio.run(call(app, ENDPOINT, method="POST", messages=[{"type":"http.request","body":b"","more_body":True}]))
    assert status == 408 and json.loads(body)["error"]["code"] == "body_timeout"
    monkeypatch.setattr(server, "BODY_TIMEOUT_SECONDS", 5)
    status, _, body = asyncio.run(call(app, ENDPOINT, method="POST", messages=[{"type": "http.disconnect"}]))
    assert status == 499 and json.loads(body)["error"]["code"] == "disconnected"


@pytest.mark.parametrize("headers,status", [
    ([(b"host", b"localhost:8510")], 400),
    ([(b"host", b"127.0.0.1:8510")], 403),
    ([(b"host", b"127.0.0.1:8510"), (b"origin", b"http://evil.example")], 403),
    ([(b"host", b"127.0.0.1:8510"), (b"Host", b"127.0.0.1:8510")], 400)])
def test_existing_host_origin_boundary_and_method_protections(make_app, headers, status):
    app = make_app()
    assert post(app, headers=headers)[0] == status
    assert asyncio.run(call(app, ENDPOINT))[0] == 405
    assert asyncio.run(call(app, "/api/v2e/documents/other", method="POST", raw=b"{}"))[0] == 404


@pytest.mark.parametrize("path,mode", [("/api/v1/validate", "sequential"),
    ("/api/v2b/validate", "two_path"), ("/api/v2d/validate", "polarization")])
def test_new_document_underflow_and_text_rules_do_not_tighten_old_routes(make_app, path, mode):
    app = make_app()
    normal = ordinary_submission(document(mode, gaussian=False))
    scientific = normal.experiment.to_dict()
    if mode == "sequential": envelope = {"request_id": REQUEST_ID, "experiment": scientific}
    else:
        envelope = {"protocol_version": 1, "message_type": "two_path_submission" if mode == "two_path" else "polarization_submission",
                    "request_id": REQUEST_ID, "experiment": scientific}
        if mode == "polarization": envelope["experiment_sha256"] = None
    encoded = json.dumps(envelope).encode().replace(b'"phase_rad": 8.71', b'"phase_rad": 1e-999')
    assert asyncio.run(call(app, path, method="POST", raw=encoded))[0] == 200
