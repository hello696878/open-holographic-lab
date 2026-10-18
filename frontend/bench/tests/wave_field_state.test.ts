import { describe, expect, it, vi } from 'vitest';
import { BenchController, ClientOperationGate } from '../src/state';
import { cloneExperiment, type BenchAPI } from '../src/contracts';
import { WaveFieldController } from '../src/wave_field_state';
import { waveFieldPlan, W1_EXAMPLE, type WaveFieldRequest } from '../src/wave_field_contracts';

/** Constant transport fixture for actor ownership tests, not an optical reference. */
function frame(request: WaveFieldRequest): ArrayBuffer {
  const plan = waveFieldPlan(request.experiment, request.sampling), { nx, ny, dx, dy } = request.experiment.grid, pixels = nx * ny;
  const stages = plan.filter(p => p.stage !== 'interior').map((p, i) => ({ selector: p.stage, z_m: p.z_m, norm: 1,
    previous_norm: i ? 1 : null, delta_norm: i ? 0 : null, transmission_ratio: i ? 1 : null }));
  const planes = plan.map(p => ({ ...p, norm: 1, previous_norm: p.stage === 'source' ? null : 1,
    delta_norm: p.stage === 'source' ? null : 0, transmission_ratio: p.stage === 'source' ? null : 1, on_axis_intensity: 1, max_intensity: 1 }));
  const n = plan.length * pixels;
  const header = { protocol_version: 1, message_type: 'w1_wave_field', request_id: request.request_id, experiment_sha256: 'a'.repeat(64), experiment: request.experiment,
    sampling: request.sampling, ordered_section_ids: plan.map(p => p.id), planes, stages,
    arrays: [{ name: 'intensities', dtype: 'float64-le', order: 'C', shape: [plan.length, ny, nx], offset_bytes: 0, nbytes: n * 8, units: 'amplitude_unit^2' },
      { name: 'x_m', dtype: 'float64-le', order: 'C', shape: [nx], offset_bytes: n * 8, nbytes: nx * 8, units: 'm' },
      { name: 'y_m', dtype: 'float64-le', order: 'C', shape: [ny], offset_bytes: (n + nx) * 8, nbytes: ny * 8, units: 'm' }] };
  const json = new TextEncoder().encode(JSON.stringify(header)), offset = 16 + Math.ceil(json.length / 8) * 8, output = new ArrayBuffer(offset + (n + nx + ny) * 8), view = new DataView(output);
  new Uint8Array(output).set([79, 72, 76, 65, 66, 87, 70, 0]); view.setUint32(8, json.length, true); new Uint8Array(output).set(json, 16);
  for (let i = 0; i < n; i++) view.setFloat64(offset + i * 8, 1, true);
  for (let i = 0; i < nx; i++) view.setFloat64(offset + (n + i) * 8, (i - Math.floor(nx / 2)) * dx, true);
  for (let i = 0; i < ny; i++) view.setFloat64(offset + (n + nx + i) * 8, (i - Math.floor(ny / 2)) * dy, true); return output;
}
async function setup(api = vi.fn(async (request: WaveFieldRequest) => frame(request)), admit = vi.fn()) {
  const experiment = cloneExperiment(W1_EXAMPLE); experiment.grid = { nx: 4, ny: 3, dx: 16e-6, dy: 17e-6 };
  let count = 0; const id = () => `11111111-1111-4111-8111-${String(++count).padStart(12, '0')}`;
  const oldAPI: BenchAPI = { validate: async request => ({ protocol_version: 1, request_id: request.request_id, experiment_sha256: 'a'.repeat(64), experiment: request.experiment }), simulate: vi.fn() };
  const gate = new ClientOperationGate(), bench = new BenchController(experiment, oldAPI, id, gate); await bench.validateInitial();
  const actor = new WaveFieldController(bench, { api: { simulate: api }, idFactory: id, admit });
  const commit = vi.fn(), dispose = vi.fn(), finalize = vi.fn(); actor.bindPresentation(() => ({ commit, dispose, finalize })); actor.setContext(true, true);
  return { actor, bench, gate, api, admit, oldAPI, commit, dispose, finalize };
}
describe('W1 single-operation observer and attachment ownership', () => {
  it('observes existing validated settings, executes once and separates view changes from computation', async () => {
    const s = await setup(), before = structuredClone(s.bench.state.candidate); expect(s.api).not.toHaveBeenCalled();
    expect(await s.actor.simulate()).toBe(true); expect(s.api).toHaveBeenCalledOnce(); expect(s.commit).toHaveBeenCalledOnce(); expect(s.finalize).toHaveBeenCalledOnce();
    const current = s.actor.state.currentResult; expect(current).not.toBeNull();
    for (let i = 0; i < 20; i++) s.bench.select(i % 2 ? 'lens' : 'source');
    s.actor.setContext(true, true); expect(s.actor.state.currentResult).toBe(current); expect(s.api, 'W1_VIEW_ACTION_NO_PROPAGATION').toHaveBeenCalledOnce();
    expect(s.bench.state.candidate).toEqual(before); expect(s.oldAPI.simulate).not.toHaveBeenCalled(); s.actor.dispose();
  });
  it('detaches immediately on an optical edit, rejects late replies and never reattaches after away/back', async () => {
    let resolve!: (value: ArrayBuffer) => void, submitted!: WaveFieldRequest;
    const api = vi.fn((request: WaveFieldRequest) => { submitted = request; return new Promise<ArrayBuffer>(done => { resolve = done; }); });
    const s = await setup(api); const pending = s.actor.simulate(); expect(s.gate.busy).toBe(true);
    await s.bench.edit('wavelength_m', '7e-7'); s.actor.setContext(true, false); s.actor.setContext(true, true);
    resolve(frame(submitted)); expect(await pending).toBe(true); expect(s.actor.state.currentResult, 'W1_STALE_ATTACHMENT').toBeNull();
    expect(s.actor.state.lastResult?.experiment.wavelength_m).toBe(633e-9); expect(s.commit).not.toHaveBeenCalled(); expect(s.api).toHaveBeenCalledOnce(); expect(s.gate.busy).toBe(false);
    expect(s.actor.retryPresentation()).toBe(false); s.actor.dispose();
  });
  it('shares the exact old gate, acquires before await and never releases another operation', async () => {
    const s = await setup(); expect(s.gate.acquire('other', 'polarized_two_path', 'sweep')).toBe(true);
    expect(await s.actor.simulate()).toBe(false); expect(s.api).not.toHaveBeenCalled(); s.gate.release('wrong'); expect(s.gate.busy).toBe(true);
    s.gate.release('other'); expect(await s.actor.simulate()).toBe(true); expect(s.gate.busy).toBe(false); s.actor.dispose();
  });
  it('keeps the gate through response/decode/display and refuses concurrent or release requests', async () => {
    let resolve!: (value: ArrayBuffer) => void, submitted!: WaveFieldRequest;
    const s = await setup(vi.fn((request: WaveFieldRequest) => { submitted = request; return new Promise<ArrayBuffer>(done => { resolve = done; }); }));
    const pending = s.actor.simulate(); expect(await s.actor.simulate()).toBe(false); expect(s.actor.releaseResults()).toBe(false);
    expect(s.gate.active?.mode).toBe('sequential'); expect(s.gate.active?.kind).toBe('single');
    s.actor.bindPresentation(() => ({ commit: () => expect(s.gate.busy, 'W1_PREMATURE_CLIENT_GATE_RELEASE').toBe(true), dispose() {}, finalize() {} }));
    resolve(frame(submitted)); expect(await pending).toBe(true); expect(s.api).toHaveBeenCalledOnce(); expect(s.gate.busy).toBe(false); s.actor.dispose();
  });
  it('reserves before submission and preserves earlier results/draft on budget rejection without eviction or retry', async () => {
    const s = await setup(); expect(await s.actor.simulate()).toBe(true); const previous = s.actor.state.currentResult, draft = s.bench.state.candidate;
    s.admit.mockImplementation(() => { throw new Error('16 MiB persistent budget'); }); expect(await s.actor.simulate()).toBe(false);
    expect(s.api).toHaveBeenCalledOnce(); expect(s.actor.state.currentResult).toBe(previous); expect(s.bench.state.candidate).toBe(draft); expect(s.actor.state.error).toContain('budget');
    expect(s.actor.releaseResults()).toBe(true); expect(s.actor.ownedNumericalBytes()).toBe(0); expect(s.bench.state.candidate).toBe(draft); s.actor.dispose();
  });
  it('retains complete numerical data on preparation failure and allows explicit presentation-only recovery', async () => {
    const s = await setup(); const fault = vi.fn(() => { throw new Error('deliberate display preparation fault'); }); s.actor.bindPresentation(fault);
    expect(await s.actor.simulate()).toBe(true); expect(s.actor.state.currentResult).toBeNull(); expect(s.actor.state.completedNumerical).not.toBeNull();
    expect(s.actor.state.error).toBeNull(); expect(s.actor.state.renderError).toContain('preparation fault'); expect(s.actor.canRetryPresentation).toBe(true);
    s.actor.bindPresentation(() => ({ commit: s.commit, dispose: s.dispose, finalize: s.finalize })); expect(s.actor.retryPresentation()).toBe(true);
    expect(s.actor.state.currentResult).not.toBeNull(); expect(s.api, 'W1_NO_DIAGNOSTIC_REPLAY').toHaveBeenCalledOnce(); s.actor.dispose();
  });
  it('rolls back a subscriber failure instead of publishing a partial attached result', async () => {
    const s = await setup(); const off = s.actor.subscribe(state => { if (state.currentResult) throw new Error('deliberate subscriber display fault'); });
    expect(await s.actor.simulate()).toBe(true); expect(s.dispose, 'W1_DISPLAY_TRANSACTION_ROLLBACK').toHaveBeenCalledOnce();
    expect(s.actor.state.currentResult).toBeNull(); expect(s.actor.state.lastResult).toBeNull(); expect(s.actor.state.completedNumerical).not.toBeNull(); expect(s.actor.state.error).toBeNull();
    off(); expect(s.actor.retryPresentation()).toBe(true); expect(s.api).toHaveBeenCalledOnce(); s.actor.dispose();
  });
  it('rejects transport corruption without partial display and keeps explicit current/draft ownership on context loss', async () => {
    const s = await setup(); await s.actor.simulate(); const numerical = s.actor.state.currentResult;
    s.actor.reportPresentationFailure('context lost'); expect(s.actor.state.currentResult).toBeNull(); expect(s.actor.state.completedNumerical).toBe(numerical);
    s.actor.reportPresentationFailure(null); expect(s.api).toHaveBeenCalledOnce(); expect(s.actor.retryPresentation()).toBe(true);
    const old = s.actor.state.currentResult; s.api.mockResolvedValueOnce(new ArrayBuffer(2)); expect(await s.actor.simulate()).toBe(false);
    expect(s.actor.state.currentResult).toBe(old); expect(s.actor.state.error).toContain('frame length'); s.actor.dispose();
  });
  it('disposes result ownership during a pending request without releasing its operation early or attaching its late reply', async () => {
    let resolve!: (value: ArrayBuffer) => void, submitted!: WaveFieldRequest;
    const s = await setup(vi.fn((request: WaveFieldRequest) => { submitted = request; return new Promise<ArrayBuffer>(done => { resolve = done; }); }));
    const pending = s.actor.simulate(); s.actor.dispose(); expect(s.gate.busy, 'W1_DISPOSE_DOES_NOT_RELEASE_RUNNING_OPERATION').toBe(true);
    expect(s.actor.ownedNumericalBytes()).toBe(0); resolve(frame(submitted)); expect(await pending).toBe(false);
    expect(s.commit).not.toHaveBeenCalled(); expect(s.actor.state.lastResult).toBeNull(); expect(s.actor.ownedNumericalBytes()).toBe(0); expect(s.gate.busy).toBe(false);
  });
  it('recovers a later viewing-subscriber failure from the same completed result without replaying science', async () => {
    const s = await setup(); await s.actor.simulate(); const completed = s.actor.state.currentResult;
    let fail = false; const off = s.actor.subscribe(state => { if (fail && state.currentResult) throw new Error('later viewing subscriber fault'); });
    fail = true; s.bench.select('lens'); expect(s.actor.state.currentResult, 'W1_LATER_VIEW_FAILURE_DETACHES').toBeNull();
    expect(s.actor.state.completedNumerical).toBe(completed); expect(s.actor.canRetryPresentation, 'W1_LATER_VIEW_FAILURE_RECOVERABLE').toBe(true);
    off(); expect(s.actor.retryPresentation()).toBe(true); expect(s.actor.state.currentResult).toBe(completed);
    expect(s.api, 'W1_LATER_VIEW_RECOVERY_NO_REPLAY').toHaveBeenCalledOnce(); s.actor.dispose();
  });
});
