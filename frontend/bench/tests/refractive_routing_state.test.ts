import { describe, expect, it, vi } from 'vitest';
import { ClientOperationGate } from '../src/state';
import { RefractiveRoutingController } from '../src/refractive_routing_state';
import { W3_NO_BODY_LIMITS, W3_MODEL, W3_WEIGHT_MODEL, W3_PRESETS, type RefractiveScene, type RefractiveTraceRequest, type RefractiveValidationRequest } from '../src/refractive_routing_contracts';

const initial: RefractiveScene = { schema_version: 1, model_contract: W3_MODEL,
  source: { id: 'source', origin_m: [0, .08, 0], direction: [0, 0, 1], relative_weight: 1 },
  exterior_medium: { id: 'exterior', refractive_index: 1 }, bodies: [], elements: [{ id: 'D1', kind: 'receiver', pose: { position_m: [0, .08, .2], rotation_xyz_rad: [0, 0, 0] }, aperture: { kind: 'disk', radius_m: .025 } }] };
const frames = [{ element_id: 'D1', u: [1, 0, 0], v: [0, 1, 0], n: [0, 0, 1] }];
const validate = (request: RefractiveValidationRequest) => ({ protocol_version: 1, message_type: 'refractive_scene_validation', request_id: request.request_id, model_contract: W3_MODEL, scene_sha256: 'a'.repeat(64), scene: request.scene, legacy_surface_frames: frames, weight_model: W3_WEIGHT_MODEL, media: [request.scene.exterior_medium], body_faces: [], limits: W3_NO_BODY_LIMITS });
function frame(request: RefractiveTraceRequest): ArrayBuffer {
  // Constant direct-hit actor fixture, not a scientific reference or hidden solver.
  const result = { protocol_version: 1, message_type: 'trace_result', ...request, model_contract: W3_MODEL, surface_frames: frames, limits: W3_NO_BODY_LIMITS, status: 'complete',
    branches: [{ id: 'r0', parent_id: null, parent_hit_id: null, origin_m: [0, .08, 0], initial_direction: [0, 0, 1], relative_weight: 1, start_cumulative_m: 0, start_interaction_count: 0, outcome: 'detected' }],
    segments: [{ id: 's0000', branch_id: 'r0', start_m: [0, .08, 0], end_m: [0, .08, .2], direction: [0, 0, 1], relative_weight: 1, length_m: .2, cumulative_end_m: .2, hit_id: 'h0000' }],
    hits: [{ id: 'h0000', segment_id: 's0000', branch_id: 'r0', element_id: 'D1', position_m: [0, .08, .2], local_uv_m: [0, 0], incident_direction: [0, 0, 1], incoming_weight: 1, outgoing: [], segment_length_m: .2, cumulative_length_m: .2,
      numerical_bounds: { t_parameter_interval_m: [.19, .21], position_intervals_m: [[-1e-16, 1e-16], [.0799, .0801], [.1999, .2001]], local_uv_intervals_m: [[-1e-16, 1e-16], [-1e-16, 1e-16]], plane_residual_m: 0 } }],
    terminals: [{ branch_id: 'r0', category: 'detected', element_id: 'D1', hit_id: 'h0000', position_m: [0, .08, .2], cumulative_length_m: .2, relative_weight: 1, reason: 'receiver_hit' }],
    ledger: { input_weight: 1, detected_weight: 1, absorbed_weight: 0, escaped_weight: 0, truncated_weight: 0, signed_residual: 0 },
    diagnostics: { predicate_policy: 'binary64_outward_intervals_v1', max_direction_norm_residual: 0, max_frame_orthogonality_residual: 0, max_plane_residual_m: 0, max_point_error_bound_m: .0001 } };
  // Shape conversion of a constant no-body actor fixture, not a scientific solver.
  const converted = { ...result, message_type: 'refractive_trace_result', weight_model: W3_WEIGHT_MODEL,
    media: [request.scene.exterior_medium], body_faces: [], legacy_surface_frames: result.surface_frames,
    branches: result.branches.map(({parent_hit_id,...rest})=>({...rest,parent_event_id:parent_hit_id,initial_medium_id:'exterior',initial_refractive_index:1})),
    segments: result.segments.map(({hit_id,...rest})=>({...rest,event_id:hit_id,medium_id:'exterior',refractive_index:1})),
    events: result.hits.map(({element_id,numerical_bounds,...rest})=>({...rest,target:{kind:'element',element_id},classification:'receiver_hit',incident_medium_id:'exterior',incident_refractive_index:1,
      numerical_bounds:{...numerical_bounds,incident_direction_intervals:[[0,0],[0,0],[1,1]],outgoing_direction_intervals:[],cumulative_length_interval_m:[.19,.21]}})),
    terminals: result.terminals.map(({hit_id,...rest})=>({...rest,event_id:hit_id,medium_id:'exterior',refractive_index:1})) } as any;
  delete converted.surface_frames; delete converted.hits;
  return new TextEncoder().encode(JSON.stringify(converted)).buffer;
}
async function setup(traceImpl: (request: RefractiveTraceRequest) => Promise<ArrayBuffer> = async request => frame(request)) {
  const gate = new ClientOperationGate(), admit = vi.fn(), trace = vi.fn(traceImpl), validateAPI = vi.fn(async (request: RefractiveValidationRequest) => validate(request));
  let ordinal = 0; const idFactory = () => `11111111-1111-4111-8111-${String(++ordinal).padStart(12, '0')}`;
  const controller = new RefractiveRoutingController(initial, { gate, admit, idFactory, api: { validate: validateAPI, trace } });
  const commit = vi.fn(), rollback = vi.fn(), finalize = vi.fn(); controller.bindPresentation(() => ({ commit, dispose: rollback, finalize }));
  await controller.activate(); return { controller, gate, admit, trace, validateAPI, commit, rollback, finalize };
}
describe('W3 explicit trace, stale ownership and display transaction actor', () => {
  it('validates without tracing and makes selection/viewing passive while one explicit Trace uses shared mode/kind', async () => {
    const s = await setup(), before = structuredClone(s.controller.state.candidate); expect(s.trace).not.toHaveBeenCalled(); expect(s.validateAPI).toHaveBeenCalledOnce();
    for (let i = 0; i < 8; i++) s.controller.select(i % 2 ? 'source' : 'D1');
    expect(s.trace, 'W3_VIEWING_MUST_NOT_TRACE').not.toHaveBeenCalled();
    s.controller.bindPresentation(() => ({ commit: () => { expect(s.gate.active?.mode).toBe('refractive_routing'); expect(s.gate.active?.kind).toBe('trace'); }, dispose() {}, finalize() {} }));
    expect(await s.controller.trace()).toBe(true); expect(s.trace).toHaveBeenCalledOnce(); expect(s.controller.state.currentResult?.terminals[0].category).toBe('detected');
    expect(s.controller.state.candidate).toEqual(before); expect(s.gate.busy).toBe(false); s.controller.dispose();
  });
  it('acquires before await, blocks duplicates and other modes, and holds until genuine completion', async () => {
    let resolve!: (bytes: ArrayBuffer) => void, submitted!: RefractiveTraceRequest;
    const s = await setup(request => { submitted = request; return new Promise(done => { resolve = done; }); });
    const pending = s.controller.trace(); expect(s.gate.busy).toBe(true); expect(await s.controller.trace()).toBe(false); expect(s.controller.releaseResults()).toBe(false);
    expect(s.gate.acquire('other', 'sequential', 'single')).toBe(false); s.gate.release('wrong'); expect(s.gate.busy).toBe(true);
    resolve(frame(submitted)); expect(await pending).toBe(true); expect(s.trace).toHaveBeenCalledOnce(); expect(s.gate.busy).toBe(false);
    s.gate.acquire('old', 'polarized_two_path', 'sweep'); expect(await s.controller.trace()).toBe(false); expect(s.trace).toHaveBeenCalledOnce(); s.gate.release('old'); s.controller.dispose();
  });
  it('rejects a duplicate Trace synchronously before a second scientific request can start', async () => {
    const releases: { request: RefractiveTraceRequest; resolve: (frame: ArrayBuffer) => void }[] = [];
    const s = await setup(request => new Promise(resolve => { releases.push({ request, resolve }); }));
    const first = s.controller.trace(), duplicate = s.controller.trace();
    expect(s.trace, 'W3_DUPLICATE_TRACE_SCIENTIFIC_REQUEST').toHaveBeenCalledOnce();
    expect(await duplicate).toBe(false); releases[0].resolve(frame(releases[0].request)); expect(await first).toBe(true); s.controller.dispose();
  });
  it('detaches edits immediately, keeps old request ownership and rejects late attachment after away/back', async () => {
    let resolve!: (bytes: ArrayBuffer) => void, submitted!: RefractiveTraceRequest;
    const s = await setup(request => { submitted = request; return new Promise(done => { resolve = done; }); });
    const pending = s.controller.trace(); await s.controller.edit('elements.0.aperture.radius_m', '.03'); s.controller.deactivate(); await s.controller.activate();
    expect(submitted.scene.elements[0].aperture).toEqual({ kind: 'disk', radius_m: .025 }); resolve(frame(submitted)); expect(await pending).toBe(true);
    expect(s.controller.state.currentResult, 'W3_LATE_ROUTE_MUST_NOT_ATTACH').toBeNull(); expect(s.controller.state.lastResult?.scene).toEqual(initial);
    expect(s.commit).not.toHaveBeenCalled(); expect(s.controller.retryPresentation()).toBe(false); expect(s.trace).toHaveBeenCalledOnce(); s.controller.dispose();
  });
  it('preserves untouched binary64 components, rejects invalid text and releases only result ownership', async () => {
    const s = await setup(); await s.controller.trace(); const result = s.controller.state.currentResult; expect(result).not.toBeNull();
    const before = s.controller.state.candidate, oldAngle = before.elements[0].pose.rotation_xyz_rad[1];
    await s.controller.edit('elements.0.pose.position_m.0', '0.12345678901234567'); expect(Object.is(s.controller.state.candidate.elements[0].pose.rotation_xyz_rad[1], oldAngle)).toBe(true);
    expect(s.controller.state.candidate.source).toEqual(before.source); expect(s.controller.state.currentResult).toBeNull();
    await s.controller.edit('source.origin_m.0', '1e-'); const invalid = s.controller.state.invalidEdits, draft = s.controller.state.candidate;
    expect(await s.controller.trace()).toBe(false); expect(s.controller.releaseResults()).toBe(true); expect(s.controller.state.invalidEdits).toBe(invalid); expect(s.controller.state.candidate).toBe(draft); expect(s.controller.ownedNumericalBytes()).toBe(0);
    expect(s.controller.ownedStateBytes()).toBeGreaterThan(0); expect(s.trace).toHaveBeenCalledOnce(); s.controller.dispose();
  });
  it('keeps numerical success separate from display failure and permits only explicit fresh display recovery', async () => {
    const s = await setup(); s.controller.bindPresentation(() => { throw new Error('Deliberate display preparation fault'); });
    expect(await s.controller.trace()).toBe(true); expect(s.controller.state.error).toBeNull(); expect(s.controller.state.renderError).toContain('preparation fault'); expect(s.controller.state.completedNumerical).not.toBeNull();
    s.controller.bindPresentation(() => ({ commit: s.commit, dispose: s.rollback, finalize: s.finalize })); expect(s.controller.retryPresentation()).toBe(true);
    const numerical = s.controller.state.currentResult; s.controller.invalidatePresentation('Context lost'); expect(s.controller.state.completedNumerical).toBe(numerical); expect(s.controller.state.currentResult).toBeNull();
    expect(s.controller.retryPresentation()).toBe(true); expect(s.trace, 'W3_NO_AUTOMATIC_REPLAY').toHaveBeenCalledOnce();
    await s.controller.edit('elements.0.aperture.radius_m', '.04'); expect(s.controller.retryPresentation()).toBe(false); s.controller.dispose();
  });
  it('retains a completion subscriber failure without preparing display until explicit recovery', async () => {
    const s = await setup(), prepare = vi.fn(() => ({ commit: s.commit, dispose: s.rollback, finalize: s.finalize }));
    s.controller.bindPresentation(prepare);
    let publishedResult: typeof s.controller.state.completedNumerical = null, failures = 0;
    const off = s.controller.subscribe(state => {
      if (state.completedNumerical && !state.currentResult && failures === 0) {
        publishedResult = state.completedNumerical; ++failures; throw new Error('Deliberate completion subscriber fault');
      }
    });
    expect(await s.controller.trace()).toBe(true);
    const retained = s.controller.state.completedNumerical, original = structuredClone(retained);
    expect(failures).toBe(1); expect(retained).toBe(publishedResult);
    expect(retained?.request_id).toBe(s.trace.mock.calls[0][0].request_id);
    expect(s.controller.state.currentResult).toBeNull(); expect(s.controller.state.lastResult).toBeNull();
    expect(s.controller.state.renderError).toContain('completion subscriber fault'); expect(s.controller.state.error).toBeNull();
    expect(prepare).not.toHaveBeenCalled(); expect(s.commit).not.toHaveBeenCalled(); expect(s.finalize).not.toHaveBeenCalled(); expect(s.rollback).not.toHaveBeenCalled();
    expect(s.controller.canRetryPresentation).toBe(true); expect(s.gate.busy).toBe(false); expect(s.trace).toHaveBeenCalledOnce();
    expect(s.controller.retryPresentation()).toBe(true); expect(prepare).toHaveBeenCalledExactlyOnceWith(retained);
    expect(s.controller.state.currentResult).toBe(retained); expect(s.controller.state.currentResult).toEqual(original);
    expect(s.controller.state.lastResult).toBe(retained); expect(s.controller.state.completedNumerical).toBeNull();
    expect(s.controller.state.renderError).toBeNull(); expect(s.controller.state.error).toBeNull();
    expect(s.commit).toHaveBeenCalledOnce(); expect(s.finalize).toHaveBeenCalledOnce(); expect(s.rollback).not.toHaveBeenCalled();
    expect(s.trace).toHaveBeenCalledOnce(); expect(s.validateAPI).toHaveBeenCalledOnce(); off(); s.controller.dispose();
  });
  it('retains the new completion when a replacement subscriber fails while the old display exists', async () => {
    const s = await setup(), prepare = vi.fn(() => ({ commit: s.commit, dispose: s.rollback, finalize: s.finalize }));
    s.controller.bindPresentation(prepare); expect(await s.controller.trace()).toBe(true);
    const previous = s.controller.state.currentResult; expect(previous).not.toBeNull();
    let publishedResult: typeof s.controller.state.completedNumerical = null, failures = 0;
    const off = s.controller.subscribe(state => {
      if (state.completedNumerical && state.completedNumerical !== previous && failures === 0) {
        publishedResult = state.completedNumerical; ++failures; throw new Error('Deliberate replacement completion fault');
      }
    });
    expect(await s.controller.trace()).toBe(true);
    const retained = s.controller.state.completedNumerical, original = structuredClone(retained);
    expect(failures).toBe(1); expect(retained).toBe(publishedResult); expect(retained).not.toBe(previous);
    expect(retained?.request_id).toBe(s.trace.mock.calls[1][0].request_id); expect(retained?.request_id).not.toBe(previous?.request_id);
    expect(s.controller.state.currentResult).toBeNull(); expect(s.controller.state.lastResult).toBe(previous);
    expect(s.controller.state.renderError).toContain('replacement completion fault'); expect(s.controller.state.error).toBeNull();
    expect(prepare).toHaveBeenCalledOnce(); expect(s.commit).toHaveBeenCalledOnce(); expect(s.finalize).toHaveBeenCalledOnce(); expect(s.rollback).not.toHaveBeenCalled();
    expect(s.controller.canRetryPresentation).toBe(true); expect(s.gate.busy).toBe(false); expect(s.trace).toHaveBeenCalledTimes(2);
    expect(s.controller.retryPresentation()).toBe(true); expect(prepare).toHaveBeenCalledTimes(2); expect(prepare).toHaveBeenLastCalledWith(retained);
    expect(s.controller.state.currentResult).toBe(retained); expect(s.controller.state.currentResult).toEqual(original);
    expect(s.controller.state.lastResult).toBe(retained); expect(s.controller.state.completedNumerical).toBeNull();
    expect(s.controller.state.renderError).toBeNull(); expect(s.controller.state.error).toBeNull();
    expect(s.commit).toHaveBeenCalledTimes(2); expect(s.finalize).toHaveBeenCalledTimes(2); expect(s.rollback).not.toHaveBeenCalled();
    expect(s.trace).toHaveBeenCalledTimes(2); expect(s.validateAPI).toHaveBeenCalledOnce(); off(); s.controller.dispose();
  });
  it('rolls back a subscriber failure and does not turn it into a numerical request failure', async () => {
    const s = await setup(), off = s.controller.subscribe(state => { if (state.currentResult) throw new Error('Deliberate subscriber fault'); });
    expect(await s.controller.trace()).toBe(true); expect(s.rollback).toHaveBeenCalledOnce(); expect(s.controller.state.currentResult).toBeNull(); expect(s.controller.state.completedNumerical).not.toBeNull(); expect(s.controller.state.error).toBeNull();
    off(); expect(s.controller.retryPresentation()).toBe(true); expect(s.trace).toHaveBeenCalledOnce(); s.controller.dispose();
  });
  it('refuses before submission when shared admission fails and preserves the previous complete result', async () => {
    const s = await setup(); await s.controller.trace(); const old = s.controller.state.currentResult, draft = s.controller.state.candidate;
    s.admit.mockImplementation(() => { throw new Error('16 MiB retained budget'); }); expect(await s.controller.trace()).toBe(false);
    expect(s.trace).toHaveBeenCalledOnce(); expect(s.controller.state.currentResult).toBe(old); expect(s.controller.state.candidate).toBe(draft); expect(s.controller.state.error).toContain('budget'); s.controller.dispose();
  });
  it('does not publish malformed transport and releases the actual operation without retry', async () => {
    const s = await setup(async () => new TextEncoder().encode('{}').buffer); expect(await s.controller.trace()).toBe(false);
    expect(s.controller.state.currentResult).toBeNull(); expect(s.controller.state.completedNumerical).toBeNull(); expect(s.controller.state.error).toContain('closed keys'); expect(s.gate.busy).toBe(false); expect(s.trace).toHaveBeenCalledOnce(); s.controller.dispose();
  });
  it('retains successive raw source components while the intermediate draft is invalid and never normalizes', async () => {
    const s=await setup(); await s.controller.edit('source.direction.0','.6');
    expect(s.controller.state.candidate.source.direction).toEqual([.6,0,1]); expect(s.controller.state.validatedDraft).toBeNull();
    await s.controller.edit('source.direction.2','.8'); expect(s.controller.state.candidate.source.direction).toEqual([.6,0,.8]);
    expect(s.trace).not.toHaveBeenCalled(); s.controller.dispose();
  });
  it('body pose/index edits preserve source and detached identity even when validation rejects geometry', async () => {
    const s=await setup(); await s.controller.trace(); const old=s.controller.state.currentResult;
    await s.controller.replaceCandidate(W3_PRESETS.B); const source=s.controller.state.candidate.source;
    await s.controller.edit('bodies.0.interior_medium.refractive_index','1.3'); await s.controller.edit('bodies.0.pose.rotation_xyz_rad.1','10',Math.PI/180);
    expect(s.controller.state.candidate.source).toEqual(source); expect(s.controller.state.candidate.bodies[0].interior_medium.refractive_index).toBe(1.3);
    expect(s.controller.state.currentResult).toBeNull(); expect(s.controller.state.lastResult).toBe(old); expect(s.controller.canRetryPresentation).toBe(false); expect(s.trace).toHaveBeenCalledOnce();s.controller.dispose();
  });
  it('preserves completed numerical identity and unrelated invalid text across model deactivation and shape changes', async () => {
    const s=await setup();s.controller.bindPresentation(()=>{throw new Error('Controlled unavailable display');});await s.controller.trace();
    const retained=s.controller.state.completedNumerical;s.controller.deactivate();expect(s.controller.state.lastResult).toBe(retained);expect(s.controller.state.currentResult).toBeNull();
    await s.controller.replaceCandidate(W3_PRESETS.B);await s.controller.edit('source.direction.0','1e-');
    await s.controller.changeBodyKind('rectangular_block');expect(s.controller.state.invalidEdits['source.direction.0']).toBe('1e-');
    await s.controller.removeBody();expect(s.controller.state.invalidEdits['source.direction.0']).toBe('1e-');expect(s.trace).toHaveBeenCalledOnce();s.controller.dispose();
  });
  it('keeps the genuine completed identity recoverable when final framing reports a display failure', async () => {
    const s=await setup();s.controller.bindPresentation(()=>({commit(){},dispose(){},finalize(){s.controller.reportPresentationFailure('Controlled final framing failure');}}));
    expect(await s.controller.trace()).toBe(true);expect(s.controller.state.currentResult).toBeNull();expect(s.controller.state.completedNumerical).not.toBeNull();expect(s.controller.canRetryPresentation).toBe(true);
    s.controller.bindPresentation(()=>({commit(){},dispose(){},finalize(){}}));expect(s.controller.retryPresentation()).toBe(true);expect(s.controller.state.currentResult).not.toBeNull();expect(s.trace).toHaveBeenCalledOnce();s.controller.dispose();
  });
  it('reserves the complete bounded validation phase and rejects actual metadata over budget without eviction', async () => {
    const s=await setup();await s.controller.trace();const old=s.controller.state.lastResult;
    s.admit.mockClear();s.admit.mockImplementation((persistent:number,transient:number)=>{if(persistent!==4*1024*1024||transient!==8*1024*1024)throw new Error('Controlled actual validation metadata budget');});
    await s.controller.edit('elements.0.aperture.radius_m','.03');expect(s.admit.mock.calls[0]).toEqual([4*1024*1024,8*1024*1024]);
    expect(s.validateAPI).toHaveBeenCalledTimes(2);expect(s.controller.state.error).toContain('actual validation metadata budget');expect(s.controller.state.validatedDraft).toBeNull();
    expect(s.controller.state.lastResult).toBe(old);expect(s.controller.state.candidate.elements[0].aperture).toEqual({kind:'disk',radius_m:.03});expect(s.trace).toHaveBeenCalledOnce();s.controller.dispose();
  });
  it('disposal cannot release another or still-running operation or attach its delayed response', async () => {
    let resolve!: (bytes: ArrayBuffer) => void, submitted!: RefractiveTraceRequest;
    const s = await setup(request => { submitted = request; return new Promise(done => { resolve = done; }); });
    const pending = s.controller.trace(); s.controller.dispose(); expect(s.gate.busy).toBe(true); expect(s.controller.ownedNumericalBytes()).toBe(0);
    resolve(frame(submitted)); expect(await pending).toBe(false); expect(s.commit).not.toHaveBeenCalled(); expect(s.controller.ownedNumericalBytes()).toBe(0); expect(s.gate.busy).toBe(false);
  });
});
