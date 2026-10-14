"""Real ASGI routes and all seven actual-worker gate holders/contenders."""

import asyncio
import json
import threading

import pytest

from apps.virtual_bench import adapter as legacy, polarization_adapter, two_path_adapter, server
from apps.virtual_bench import polarized_two_path_adapter as adapter
from apps.virtual_bench import polarized_two_path_protocol as protocol
from test_virtual_bench_polarized_two_path_adapter import REQUEST_ID,digested,envelope,sweep_envelope,unpack
from test_virtual_bench_polarization_server import request_for as old_request,real_worker as old_worker
from test_virtual_bench_two_path_server import ControlledExecutor,call
from test_virtual_bench_polarized_two_path_documents import document

OPERATIONS=("sequential","dual","sweep","polarization","polarization_sweep","polarized_two_path","polarized_two_path_sweep")


def request_for(operation):
    if operation=="polarized_two_path":return "/api/v2g/simulate",digested()
    if operation=="polarized_two_path_sweep":return "/api/v2g/sweep",sweep_envelope()
    return old_request(operation)


def real_worker(submission):
    if isinstance(submission,adapter.ValidatedPolarizedTwoPathSweepSubmission):return adapter.sweep_submission(submission)
    if isinstance(submission,adapter.ValidatedPolarizedTwoPathSubmission):return adapter.simulate_submission(submission)
    return old_worker(submission)


@pytest.fixture
def make_app(tmp_path):
    assets=tmp_path/"assets";assets.mkdir()
    (assets/"index.html").write_text("<!doctype html><title>Owned V2g ASGI fixture</title>",encoding="utf-8")
    applications=[]
    def factory(**kwargs):
        app=server.create_app(assets_dir=assets,**kwargs);applications.append(app);return app
    yield factory
    for app in applications:app.state.gate.shutdown()


def controlled_app(make_app,worker):
    return make_app(worker=worker,two_path_worker=worker,sweep_worker=worker,polarization_worker=worker,
        polarization_sweep_worker=worker,polarized_two_path_worker=worker,polarized_two_path_sweep_worker=worker)


async def validate_all(app):
    from test_virtual_bench_two_path_server import legacy_envelope
    from test_virtual_bench_two_path_adapter import envelope as dual_envelope
    from test_virtual_bench_polarization_adapter import envelope as polarization_envelope
    for path,value in (("/api/v1/validate",legacy_envelope()),("/api/v2b/validate",dual_envelope(ny=3,nx=4)),
        ("/api/v2d/validate",polarization_envelope()),("/api/v2g/validate",envelope()),
        ("/api/v2g/validate",sweep_envelope(digested=False)),("/api/v2e/documents/validate",document())):
        assert (await call(app,path,method="POST",value=value))[0]==200
    assert json.loads((await call(app))[2])["busy"] is True


def test_actual_single_and_sweep_validate_without_optics_then_public_workers(make_app,monkeypatch):
    counts={"runner":0,"analyzer":0}
    runner,analyzer=adapter.run_polarized_two_arm,adapter.apply_linear_polarizer
    def run(field,*,spec):counts["runner"]+=1;return runner(field,spec=spec)
    def analyze(field,**kwargs):counts["analyzer"]+=1;return analyzer(field,**kwargs)
    monkeypatch.setattr(adapter,"run_polarized_two_arm",run);monkeypatch.setattr(adapter,"apply_linear_polarizer",analyze)
    app=make_app()
    status,_,body=asyncio.run(call(app,"/api/v2g/validate",method="POST",value=envelope()))
    assert status==200 and counts=={"runner":0,"analyzer":0}
    validation=json.loads(body)
    assert set(validation)=={"protocol_version","message_type","request_id","experiment_sha256","experiment"}
    assert validation["message_type"]=="polarized_two_path_validation"
    status,_,body=asyncio.run(call(app,"/api/v2g/validate",method="POST",value=sweep_envelope(digested=False)))
    assert status==200 and counts=={"runner":0,"analyzer":0}
    assert set(json.loads(body))=={"protocol_version","message_type","request_id","fixed_experiment_sha256","fixed_experiment","phases_rad","sweep_sha256"}
    status,headers,frame=asyncio.run(call(app,"/api/v2g/simulate",method="POST",value=digested()))
    assert status==200 and headers[b"content-type"]==b"application/octet-stream"
    result,_=unpack(frame)
    assert result["experiment_sha256"]==validation["experiment_sha256"] and counts=={"runner":1,"analyzer":2}
    status,headers,body=asyncio.run(call(app,"/api/v2g/sweep",method="POST",value=sweep_envelope()))
    assert status==200 and json.loads(body)["completed_count"]==17 and counts=={"runner":18,"analyzer":36}
    assert headers[b"content-type"]==b"application/json" and app.state.gate.wait_idle(5)


@pytest.mark.parametrize("active",OPERATIONS)
@pytest.mark.parametrize("blocked",OPERATIONS)
def test_one_actual_gate_all_seven_by_seven_rejects_without_queue(make_app,active,blocked):
    started,release=threading.Event(),threading.Event();calls=[]
    def controlled(submission):
        calls.append(submission.request_id);started.set()
        assert release.wait(5),"test did not release actual worker"
        return real_worker(submission)
    app=controlled_app(make_app,controlled)
    async def check():
        path,value=request_for(active)
        first=asyncio.create_task(call(app,path,method="POST",value=value))
        try:
            assert await asyncio.to_thread(started.wait,5)
            other_path,other=request_for(blocked)
            assert (await call(app,other_path,method="POST",value=other))[0]==409,"V2G_SHARED_GATE_DETECTED"
            assert len(calls)==1,"V2G_SHARED_GATE_DETECTED"
            await validate_all(app)
        finally:release.set()
        assert (await first)[0]==200
        assert await asyncio.to_thread(app.state.gate.wait_idle,5)
        assert (await call(app,other_path,method="POST",value=other))[0]==200
        assert len(calls)==2,"V2G_SHARED_GATE_DETECTED"
    asyncio.run(check())


@pytest.mark.parametrize("active",OPERATIONS)
@pytest.mark.parametrize("abort",["disconnect","handler_cancel"])
def test_abort_keeps_actual_worker_gate_until_terminal_completion(make_app,active,abort):
    started,release,ended=threading.Event(),threading.Event(),threading.Event()
    def controlled(submission):
        started.set();assert release.wait(5)
        try:return real_worker(submission)
        finally:ended.set()
    app=controlled_app(make_app,controlled)
    async def check():
        path,value=request_for(active);disconnected=asyncio.Event()
        first=asyncio.create_task(call(app,path,method="POST",value=value,disconnected=disconnected))
        try:
            assert await asyncio.to_thread(started.wait,5)
            if abort=="disconnect":
                disconnected.set();assert (await first)[0]==499
            else:
                first.cancel()
                with pytest.raises(asyncio.CancelledError):await first
            assert app.state.gate.busy and not ended.is_set(),"V2G_WORKER_LIFETIME_DETECTED"
            for operation in OPERATIONS:
                path2,value2=request_for(operation)
                assert (await call(app,path2,method="POST",value=value2))[0]==409,"V2G_WORKER_LIFETIME_DETECTED"
            await validate_all(app)
        finally:release.set()
        assert await asyncio.to_thread(app.state.gate.wait_idle,5)
        assert ended.is_set() and not app.state.gate.busy
    asyncio.run(check())


@pytest.mark.parametrize("operation",["polarized_two_path","polarized_two_path_sweep"])
@pytest.mark.parametrize("stage",["analyzer","encoding"])
def test_gate_covers_downstream_analyzers_and_final_encoding_through_disconnect(make_app,monkeypatch,operation,stage):
    started,release=threading.Event(),threading.Event()
    name="apply_linear_polarizer" if stage=="analyzer" else "encode_result" if operation=="polarized_two_path" else "encode_sweep_reply"
    original=getattr(adapter,name)
    def hold(*args,**kwargs):
        started.set();assert release.wait(5);return original(*args,**kwargs)
    monkeypatch.setattr(adapter,name,hold)
    app=make_app()
    async def check():
        path,value=request_for(operation);disconnected=asyncio.Event()
        first=asyncio.create_task(call(app,path,method="POST",value=value,disconnected=disconnected))
        try:
            assert await asyncio.to_thread(started.wait,5)
            disconnected.set();assert (await first)[0]==499
            assert app.state.gate.busy,"V2G_ENCODING_LIFETIME_DETECTED"
            for other in OPERATIONS:
                p,v=request_for(other)
                assert (await call(app,p,method="POST",value=v))[0]==409,"V2G_ENCODING_LIFETIME_DETECTED"
            await validate_all(app)
        finally:release.set()
        assert await asyncio.to_thread(app.state.gate.wait_idle,5)
    asyncio.run(check())


@pytest.mark.parametrize("operation",["polarized_two_path","polarized_two_path_sweep"])
@pytest.mark.parametrize("failure",["numerical","encoding","invalid_reply","oversize_reply"])
def test_worker_failure_gate_release_and_explicit_subsequent_recovery(make_app,operation,failure):
    fail=[True]
    def controlled(submission):
        if fail[0]:
            if failure=="numerical":raise adapter.NumericalError("controlled arithmetic")
            if failure=="encoding":raise RuntimeError("private encoder detail")
            body=b"x" if failure=="invalid_reply" else b"x"*(protocol.MAX_RESPONSE_BYTES+1)
            return body if operation=="polarized_two_path" else protocol.SweepReply(status_code=200,body=body)
        return real_worker(submission)
    app=make_app(polarized_two_path_worker=controlled,polarized_two_path_sweep_worker=controlled)
    path,value=request_for(operation)
    status,_,body=asyncio.run(call(app,path,method="POST",value=value))
    assert status==(422 if failure=="numerical" else 500) and b"private encoder detail" not in body
    assert app.state.gate.wait_idle(5) and not app.state.gate.busy
    fail[0]=False
    assert asyncio.run(call(app,path,method="POST",value=value))[0]==200


@pytest.mark.parametrize("operation",["polarized_two_path","polarized_two_path_sweep"])
def test_submission_failure_and_cancelled_before_start_release(make_app,operation):
    executor=ControlledExecutor();app=make_app(executor=executor)
    path,value=request_for(operation)
    status,_,body=asyncio.run(call(app,path,method="POST",value=value))
    assert status==500 and json.loads(body)["error"]["code"]=="submission_failed" and not app.state.gate.busy
    executor.fail=False
    status,_,body=asyncio.run(call(app,path,method="POST",value=value))
    assert status==503 and json.loads(body)["error"]["code"]=="cancelled_before_start" and not app.state.gate.busy


@pytest.mark.parametrize("index",[0,8,16])
@pytest.mark.parametrize("error_type,status",[(ValueError,422),(RuntimeError,500)])
def test_actual_sweep_prefix_http_status_and_genuine_rows(make_app,monkeypatch,index,error_type,status):
    original=adapter.run_polarized_two_arm;calls=[]
    def fail(field,*,spec):
        calls.append(spec.relative_phase_rad)
        if len(calls)==index+1:raise error_type("controlled point failure")
        return original(field,spec=spec)
    monkeypatch.setattr(adapter,"run_polarized_two_arm",fail)
    app=make_app()
    actual,headers,body=asyncio.run(call(app,"/api/v2g/sweep",method="POST",value=sweep_envelope()))
    reply=json.loads(body)
    assert actual==status and headers[b"content-type"]==b"application/json"
    assert reply["completed_count"]==reply["failed_index"]==len(reply["rows"])==index,"V2G_HTTP_PREFIX_DETECTED"
    assert calls==list(protocol.PHASES_RAD[:index+1]) and app.state.gate.wait_idle(5)


@pytest.mark.parametrize("operation",["polarized_two_path","polarized_two_path_sweep"])
def test_final_encoding_failure_is_generic_not_fabricated_failed_point(make_app,monkeypatch,operation):
    def fail(*a,**k):raise ValueError("private final encoder detail")
    monkeypatch.setattr(adapter,"encode_result" if operation=="polarized_two_path" else "encode_sweep_reply",fail)
    app=make_app();path,value=request_for(operation)
    status,_,body=asyncio.run(call(app,path,method="POST",value=value));reply=json.loads(body)
    assert status==500 and reply["message_type"]=="polarized_two_path_error" and reply["error"]["code"]=="simulation_failed"
    assert "rows" not in reply and b"private" not in body and app.state.gate.wait_idle(5)


@pytest.mark.parametrize("raw",[b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}',b'{"a":1e-999}',b'\xff',b'\xef\xbb\xbf{}'])
def test_strict_new_json_security_headers_and_methods_preserved(make_app,raw):
    app=make_app(polarized_two_path_worker=lambda _:pytest.fail("worker reached"))
    status,headers,body=asyncio.run(call(app,"/api/v2g/simulate",method="POST",raw=raw))
    assert status==400 and json.loads(body)["message_type"]=="polarized_two_path_error"
    assert headers[b"cache-control"]==b"no-store" and headers[b"x-content-type-options"]==b"nosniff"
    assert b"access-control-allow-origin" not in headers
    assert asyncio.run(call(app,"/api/v2g/simulate"))[0]==405
    assert asyncio.run(call(app,"/api/v2g/validate",method="POST",raw=b" "*32769))[0]==413


def test_new_digest_and_old_envelope_cross_mode_rejection(make_app):
    app=make_app()
    assert asyncio.run(call(app,"/api/v2g/simulate",method="POST",value=envelope()))[0]==422
    assert asyncio.run(call(app,"/api/v2g/validate",method="POST",value=digested()))[0]==422
    for operation in OPERATIONS[:5]:
        path,value=request_for(operation)
        assert asyncio.run(call(app,"/api/v2g/simulate",method="POST",value=value))[0]==422
        assert asyncio.run(call(app,path,method="POST",value=digested()))[0]==422


@pytest.mark.parametrize("header,expected",[((b"host",b"localhost:8510"),400),((b"origin",b"https://example.com"),403)])
def test_exact_host_origin_boundary_unchanged(make_app,header,expected):
    app=make_app();headers=[(b"host",server.AUTHORITY.encode()),(b"origin",server.ORIGIN.encode()),(b"content-type",b"application/json")]
    headers=[pair for pair in headers if pair[0]!=header[0]]+[header]
    assert asyncio.run(call(app,"/api/v2g/simulate",method="POST",value=digested(),headers=headers))[0]==expected
