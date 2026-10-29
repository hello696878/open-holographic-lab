"""Actual W4 ASGI routes and the single worker/encoding lifetime.

Custom workers are trusted isolated test seams. Malformed custom bytes are
labelled transport faults; they do not describe genuine production encoding.
"""
import asyncio
import json
import threading

import pytest

from apps.virtual_bench import server
from apps.virtual_bench import fresnel_routing_adapter as adapter
from apps.virtual_bench import fresnel_routing_protocol as protocol
from test_virtual_bench_fresnel_routing_adapter import envelope
from test_virtual_bench_refractive_routing_server import (
    OPERATIONS as OLD_OPERATIONS, request_for as old_request,
    real_worker as old_worker, validate_everything as validate_all,
)
from test_virtual_bench_two_path_server import ControlledExecutor, call

VALIDATE = "/api/w4/validate"
TRACE = "/api/w4/trace"
OPERATIONS = (*OLD_OPERATIONS, "fresnel_routing")
PAIRS = [(active,blocked) for active in OPERATIONS for blocked in OPERATIONS]


def request_for(operation):
    return (TRACE, envelope(trace=True)) if operation == "fresnel_routing" else old_request(operation)


def real_worker(submission):
    if isinstance(submission, adapter.ValidatedFresnelSubmission):
        return adapter.trace_submission(submission)
    return old_worker(submission)


@pytest.fixture
def make_app(tmp_path):
    assets=tmp_path/"assets"
    assets.mkdir()
    (assets/"index.html").write_text("<!doctype html><title>Owned W4 fixture</title>",encoding="utf-8")
    applications=[]
    def factory(**kwargs):
        app=server.create_app(assets_dir=assets,**kwargs)
        applications.append(app)
        return app
    yield factory
    for app in applications:
        app.state.gate.shutdown()


def controlled_app(make_app,worker):
    return make_app(worker=worker,two_path_worker=worker,sweep_worker=worker,
        polarization_worker=worker,polarization_sweep_worker=worker,
        polarized_two_path_worker=worker,polarized_two_path_sweep_worker=worker,
        r03_ideal_worker=worker,wave_field_worker=worker,geometric_routing_worker=worker,refractive_routing_worker=worker,fresnel_routing_worker=worker)


async def validate_everything(app):
    await validate_all(app)
    status,_,body=await call(app,VALIDATE,method="POST",value=envelope())
    assert status==200 and json.loads(body)["message_type"]=="fresnel_scene_validation"


def test_genuine_validation_is_noncomputing_and_trace_uses_new_identity(make_app,monkeypatch):
    calls=[]
    original=adapter.trace_fresnel_scene
    def observe(*args):
        calls.append(args[0])
        return original(*args)
    monkeypatch.setattr(adapter,"trace_fresnel_scene",observe)
    app=make_app()
    status,headers,body=asyncio.run(call(app,VALIDATE,method="POST",value=envelope()))
    validation=json.loads(body)
    assert status==200 and not calls and not app.state.gate.busy
    assert validation["scene_sha256"]==protocol.scene_digest(validation["scene"])
    value=envelope(trace=True)
    status,headers,body=asyncio.run(call(app,TRACE,method="POST",value=value))
    decoded=protocol.decode_trace_result(body,request_id=value["request_id"],scene_sha256=value["scene_sha256"])
    assert status==200 and headers[b"content-type"].startswith(b"application/json")
    assert decoded["status"]=="complete" and len(calls)==1
    assert app.state.gate.wait_idle(5)
    assert asyncio.run(call(app,"/api/v1/validate",method="POST",value=value))[0]==422
    assert asyncio.run(call(app,TRACE,method="POST",value=envelope()))[0]==422


@pytest.mark.parametrize("active,blocked",PAIRS)
def test_w4_and_all_eleven_old_operations_share_actual_gate(make_app,active,blocked):
    started,release=threading.Event(),threading.Event()
    calls=[]
    def held(submission):
        calls.append(submission.request_id)
        started.set()
        assert release.wait(5),"test did not release actual worker"
        return real_worker(submission)
    app=controlled_app(make_app,held)
    async def check():
        path,value=request_for(active)
        first=asyncio.create_task(call(app,path,method="POST",value=value))
        try:
            assert await asyncio.to_thread(started.wait,5)
            other_path,other=request_for(blocked)
            assert (await call(app,other_path,method="POST",value=other))[0]==409,"W4_SHARED_GATE_DETECTED"
            assert len(calls)==1
            await validate_everything(app)
        finally:
            release.set()
        assert (await first)[0]==200
        assert await asyncio.to_thread(app.state.gate.wait_idle,5)
        assert (await call(app,other_path,method="POST",value=other))[0]==200
        assert len(calls)==2
    asyncio.run(check())


@pytest.mark.parametrize("active",OPERATIONS)
@pytest.mark.parametrize("termination",["disconnect","handler_cancel"])
def test_disconnect_or_handler_cancel_preserves_actual_twelfth_gate(make_app,active,termination):
    started,release,ended=threading.Event(),threading.Event(),threading.Event()
    def held(submission):
        started.set()
        assert release.wait(5)
        try:
            return real_worker(submission)
        finally:
            ended.set()
    app=controlled_app(make_app,held)
    async def check():
        disconnected=asyncio.Event()
        path,value=request_for(active)
        first=asyncio.create_task(call(app,path,method="POST",value=value,disconnected=disconnected))
        try:
            assert await asyncio.to_thread(started.wait,5)
            if termination=="disconnect":
                disconnected.set()
                assert (await first)[0]==499
            else:
                first.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await first
            assert app.state.gate.busy and not ended.is_set(),"W4_WORKER_LIFETIME_DETECTED"
            for operation in OPERATIONS:
                path,value=request_for(operation)
                assert (await call(app,path,method="POST",value=value))[0]==409
            await validate_everything(app)
        finally:
            release.set()
        assert await asyncio.to_thread(app.state.gate.wait_idle,5)
        assert ended.is_set()
    asyncio.run(check())


@pytest.mark.parametrize("termination",["disconnect","handler_cancel"])
def test_gate_covers_actual_w4_final_encoding_after_handler_departure(make_app,monkeypatch,termination):
    started,release=threading.Event(),threading.Event()
    original=adapter.encode_trace_result
    def hold(*args,**kwargs):
        started.set()
        assert release.wait(5)
        return original(*args,**kwargs)
    monkeypatch.setattr(adapter,"encode_trace_result",hold)
    app=make_app()
    async def check():
        disconnected=asyncio.Event()
        first=asyncio.create_task(call(app,TRACE,method="POST",value=envelope(trace=True),disconnected=disconnected))
        try:
            assert await asyncio.to_thread(started.wait,5)
            if termination=="disconnect":
                disconnected.set()
                assert (await first)[0]==499
            else:
                first.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await first
            assert app.state.gate.busy,"W4_ENCODING_LIFETIME_DETECTED"
            for operation in OPERATIONS:
                path,value=request_for(operation)
                assert (await call(app,path,method="POST",value=value))[0]==409
            await validate_everything(app)
        finally:
            release.set()
        assert await asyncio.to_thread(app.state.gate.wait_idle,5)
    asyncio.run(check())


@pytest.mark.parametrize("name,code",[("NumericalAmbiguityError","numerical_ambiguity"),
                                     ("UnsupportedNumericalInputError","unsupported_numerical_input"),
                                     ("MediumStateAmbiguityError","medium_state_ambiguity"),
                                     ("UnsupportedPolarizationNumericsError","unsupported_polarization_numerics")])
@pytest.mark.parametrize("path",[VALIDATE,TRACE])
def test_pure_scene_arithmetic_failure_is_distinct_and_never_acquires_gate(make_app,monkeypatch,name,code,path):
    value=envelope(trace=path==TRACE)
    def fail(_):
        raise getattr(adapter,name)("controlled scene arithmetic admission failure")
    monkeypatch.setattr(adapter,"validate_fresnel_scene",fail)
    monkeypatch.setattr(adapter,"trace_fresnel_scene",lambda *_:pytest.fail("invalid scene traced"))
    app=make_app()
    status,_,body=asyncio.run(call(app,path,method="POST",value=value))
    assert status==422 and json.loads(body)["code"]==code
    assert not app.state.gate.busy


@pytest.mark.parametrize("failure,expected_status,expected_code",[
    ("ambiguity",422,"numerical_ambiguity"),
    ("unsupported",422,"unsupported_numerical_input"),
    ("medium",422,"medium_state_ambiguity"),
    ("encoding",500,"trace_failed"),
    ("short",500,"response_too_large"),
    ("oversize",500,"response_too_large"),
])
def test_distinct_failures_publish_no_partial_trace_or_retry(make_app,failure,expected_status,expected_code):
    calls=[]
    def fail(submission):
        calls.append(submission.request_id)
        if failure=="ambiguity":
            raise adapter.FresnelNumericalError("declared ambiguity",code="numerical_ambiguity")
        if failure=="unsupported":
            raise adapter.FresnelNumericalError("declared unsupported input",code="unsupported_numerical_input")
        if failure=="medium":
            raise adapter.FresnelNumericalError("declared medium ambiguity",code="medium_state_ambiguity")
        if failure=="encoding":
            raise RuntimeError("private internals")
        return b"x" if failure=="short" else b"x"*(protocol.MAX_RESPONSE_BYTES+1)
    app=make_app(fresnel_routing_worker=fail)
    status,_,body=asyncio.run(call(app,TRACE,method="POST",value=envelope(trace=True)))
    reply=json.loads(body)
    assert status==expected_status and reply["code"]==expected_code
    assert reply["message_type"]=="fresnel_routing_error" and "branches" not in reply
    assert b"private internals" not in body and len(calls)==1
    assert app.state.gate.wait_idle(5)


def test_genuine_encoder_failure_is_500_not_a_successful_miss(make_app,monkeypatch):
    def fail(*args,**kwargs):
        raise ValueError("controlled invalid complete graph")
    monkeypatch.setattr(adapter,"encode_trace_result",fail)
    app=make_app()
    status,_,body=asyncio.run(call(app,TRACE,method="POST",value=envelope(trace=True)))
    assert status==500 and json.loads(body)["code"]=="trace_failed"
    assert app.state.gate.wait_idle(5)


def test_labelled_trusted_custom_worker_fault_is_rejected_by_transport_not_claimed_genuine(make_app):
    app=make_app(fresnel_routing_worker=lambda _:b"{}")
    status,_,body=asyncio.run(call(app,TRACE,method="POST",value=envelope(trace=True)))
    assert status==200,"custom workers are the explicit trusted injection seam"
    with pytest.raises(ValueError):
        protocol.decode_trace_result(body)
    assert app.state.gate.wait_idle(5)


def test_submit_failure_or_cancel_before_start_releases_only_finished_reservation(make_app):
    executor=ControlledExecutor()
    app=make_app(executor=executor)
    status,_,body=asyncio.run(call(app,TRACE,method="POST",value=envelope(trace=True)))
    assert status==500 and json.loads(body)["code"]=="submission_failed"
    assert not app.state.gate.busy
    executor.fail=False
    status,_,body=asyncio.run(call(app,TRACE,method="POST",value=envelope(trace=True)))
    assert status==503 and json.loads(body)["code"]=="cancelled_before_start"
    assert not app.state.gate.busy


@pytest.mark.parametrize("raw",[b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}',b'{"a":1e-999}',b"\xff"])
@pytest.mark.parametrize("path",[VALIDATE,TRACE])
def test_strict_raw_json_is_rejected_before_worker_with_original_security_headers(make_app,path,raw):
    app=make_app(fresnel_routing_worker=lambda _:pytest.fail("worker reached"))
    status,headers,body=asyncio.run(call(app,path,method="POST",raw=raw))
    assert status==400 and json.loads(body)["message_type"]=="fresnel_routing_error"
    assert headers[b"cache-control"]==b"no-store" and b"access-control-allow-origin" not in headers
    assert headers[b"x-content-type-options"]==b"nosniff"


@pytest.mark.parametrize("path",[VALIDATE,TRACE])
def test_body_methods_origin_host_and_wrong_digest_remain_closed(make_app,path):
    app=make_app()
    assert asyncio.run(call(app,path))[0]==405
    assert asyncio.run(call(app,path,method="POST",raw=b" "*32769))[0]==413
    for key,value,expected in ((b"host",b"localhost:8510",400),(b"origin",b"https://example.com",403)):
        headers=[(b"host",server.AUTHORITY.encode()),(b"origin",server.ORIGIN.encode()),(b"content-type",b"application/json")]
        headers=[pair for pair in headers if pair[0]!=key]+[(key,value)]
        request=envelope(trace=path==TRACE)
        assert asyncio.run(call(app,path,method="POST",value=request,headers=headers))[0]==expected
    value=envelope(trace=True)
    value["scene_sha256"]="0"*64
    assert asyncio.run(call(app,TRACE,method="POST",value=value))[0]==422


def test_actual_finite_body_validation_and_trace_share_exact_owned_scene(make_app,monkeypatch):
    from test_virtual_bench_fresnel_routing_protocol import body_scene,REQUEST_ID
    calls=[]
    original=adapter.trace_fresnel_scene
    def observe(value):
        calls.append(value)
        return original(value)
    monkeypatch.setattr(adapter,"trace_fresnel_scene",observe)
    app=make_app()
    request={"request_id":REQUEST_ID,"scene":body_scene()}
    status,_,body=asyncio.run(call(app,VALIDATE,method="POST",value=request))
    assert status==200
    admitted=protocol.decode_validation_reply(body)
    assert len(admitted["body_faces"])==6 and not calls and not app.state.gate.busy
    request.update(scene=admitted["scene"],scene_sha256=admitted["scene_sha256"])
    status,_,body=asyncio.run(call(app,TRACE,method="POST",value=request))
    assert status==200
    result=protocol.decode_trace_result(body,request_id=REQUEST_ID,scene_sha256=request["scene_sha256"])
    assert len(calls)==1 and result["status"]=="incomplete"
    assert [part["id"] for part in result["branches"][:3]]==["r0","r0.R","r0.T"]
    assert result["ledger"]["unresolved_power"]>0
