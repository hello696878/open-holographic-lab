import { describe, expect, it } from 'vitest';
import { BenchController, type BenchAPI } from '../src/state';
import { cloneExperiment, type Experiment, type RequestEnvelope, type ValidationReply } from '../src/contracts';
import { PRESETS, presetExperiment } from '../src/presets';

const base: Experiment = { schema_version: 1, model_contract: 'v0_aligned_scalar_forward_v1', wavelength_m: 633e-9,
  grid: { ny: 2, nx: 3, dy: 3e-6, dx: 2e-6 }, source: { kind: 'uniform', amplitude: 1, phase_rad: 0 },
  components: [], observation: { id: 'screen', z_m: 0.02 } };
function ids() { let next = 0; return () => `12345678-1234-4234-8234-${String(++next).padStart(12, '0')}`; }
function deferred<T>() {
  let resolve!: (value: T) => void; let reject!: (error: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject };
}
function validated(envelope: RequestEnvelope): ValidationReply {
  return { protocol_version: 1, request_id: envelope.request_id, experiment_sha256: 'a'.repeat(64), experiment: cloneExperiment(envelope.experiment) };
}
// Independent fixed transport fixture for state transitions; no V0 substitute solver.
function resultFrame(envelope: RequestEnvelope, hash = 'a'.repeat(64)): ArrayBuffer {
  const header = { protocol_version: 1, request_id: envelope.request_id, experiment_sha256: hash,
    experiment: envelope.experiment,
    stages: [
      { selector: 'source', z_m: 0, norm: 1, previous_norm: null, delta_norm: null, transmission_ratio: null },
      { selector: 'observation', z_m: envelope.experiment.observation.z_m, norm: 1, previous_norm: 1, delta_norm: 0, transmission_ratio: 1 },
    ], arrays: [
      { name: 'intensity', dtype: 'float64-le', order: 'C', shape: [2, 3], offset_bytes: 0, nbytes: 48, units: 'amplitude_unit^2' },
      { name: 'x_m', dtype: 'float64-le', order: 'C', shape: [3], offset_bytes: 48, nbytes: 24, units: 'm' },
      { name: 'y_m', dtype: 'float64-le', order: 'C', shape: [2], offset_bytes: 72, nbytes: 16, units: 'm' },
    ], intensity_max: 5 };
  const encoded = new TextEncoder().encode(JSON.stringify(header)); const start = 16 + Math.ceil(encoded.length / 8) * 8;
  const frame = new ArrayBuffer(start + 88); const bytes = new Uint8Array(frame); const view = new DataView(frame);
  bytes.set([79, 72, 76, 65, 66, 86, 49, 0]); view.setUint32(8, encoded.length, true); bytes.set(encoded, 16);
  [0, 1, 2, 3, 4, 5, -2e-6, 0, 2e-6, -3e-6, 0].forEach((value, index) => view.setFloat64(start + index * 8, value, true));
  return frame;
}
function immediateAPI() {
  const validations: RequestEnvelope[] = []; const simulations: RequestEnvelope[] = [];
  const api: BenchAPI = { async validate(envelope) { validations.push(envelope); return validated(envelope); },
    async simulate(envelope) { simulations.push(envelope); return resultFrame(envelope); } };
  return { api, validations, simulations };
}

describe('explicit scientific submission state', () => {
  it('initial passive validation, selection and presentation failure perform no simulation', async () => {
    const { api, validations, simulations } = immediateAPI(); const controller = new BenchController(base, api, ids());
    expect(validations).toHaveLength(0); expect(simulations).toHaveLength(0);
    await controller.validateInitial(); await controller.validateInitial(); expect(validations).toHaveLength(1);
    controller.select('screen'); controller.reportRenderFailure('WebGL unavailable'); controller.clearRenderFailure();
    expect(validations).toHaveLength(1); expect(simulations).toHaveLength(0); expect(controller.state.status).toBe('ready');
  });
  it('converts units at editor boundary and preserves ordered colocated preset IDs', async () => {
    const { api, simulations } = immediateAPI(); const controller = new BenchController(base, api, ids());
    await controller.edit('wavelength_m', '532', 1e-9); expect(controller.state.candidate.wavelength_m).toBe(532 * 1e-9);
    await controller.edit('observation.z_m', '30', 1e-3); expect(controller.state.candidate.observation.z_m).toBe(0.03);
    await controller.edit('grid.nx', '3', 1, true); expect(controller.state.candidate.grid.nx).toBe(3);
    expect(simulations).toHaveLength(0);
    const preset = presetExperiment('aperture');
    expect(preset.components.map(c => [c.id, c.z_m])).toEqual([['aperture', 0], ['lens', 0]]);
    expect(PRESETS.map(p => p.id)).toEqual(['free', 'lens', 'aperture']);
    expect(preset.grid).toEqual({ ny: 512, nx: 512, dy: 4e-6, dx: 4e-6 });
    expect(preset.wavelength_m).toBe(633e-9);
    expect(preset.components[0]).toEqual({ id: 'aperture', kind: 'circular_aperture', z_m: 0, radius_m: 80e-6 });
    preset.components.pop(); expect(presetExperiment('aperture').components).toHaveLength(2);
  });
  it('busy is synchronous: repeated intentional clicks send one frozen specification', async () => {
    const running = deferred<ArrayBuffer>(); const calls: RequestEnvelope[] = [];
    const api: BenchAPI = { async validate(envelope) { return validated(envelope); }, simulate(envelope) { calls.push(envelope); return running.promise; } };
    const initial = cloneExperiment(base); const controller = new BenchController(initial, api, ids()); await controller.validateInitial();
    const first = controller.simulate(); expect(controller.state.active).not.toBeNull();
    const second = controller.simulate(); expect(calls).toHaveLength(1); expect(await second).toBe(false);
    initial.observation.z_m = 99; expect(calls[0].experiment.observation.z_m).toBe(0.02);
    expect(Object.isFrozen(calls[0].experiment.observation)).toBe(true);
    running.resolve(resultFrame(calls[0])); expect(await first).toBe(true);
    expect(controller.state.currentResult?.requestId).toBe(calls[0].request_id);
    expect(controller.state.lastResult?.intensity[5]).toBe(5); expect(controller.state.active).toBeNull();
  });
  it('an optical edit removes the current texture immediately and keeps a labeled old snapshot', async () => {
    const { api, simulations } = immediateAPI(); const controller = new BenchController(base, api, ids()); await controller.validateInitial();
    await controller.simulate(); const old = controller.state.lastResult;
    const edit = controller.edit('observation.z_m', '40', 1e-3);
    expect(controller.state.currentResult).toBeNull(); expect(controller.state.lastResult).toBe(old);
    expect(old?.experiment.observation.z_m).toBe(0.02); expect(simulations).toHaveLength(1);
    await edit; expect(controller.state.validatedDraft?.observation.z_m).toBe(0.04);
  });
  it('blank/partial/nonfinite editor text stays separate and cannot submit', async () => {
    const { api, validations, simulations } = immediateAPI(); const controller = new BenchController(base, api, ids()); await controller.validateInitial();
    await controller.simulate(); const last = controller.state.lastResult;
    for (const text of ['', '-', '1e', 'Infinity', '0x10', '1e999']) {
      await controller.edit('observation.z_m', text, 1e-3);
      expect(controller.state.invalidEdits['observation.z_m']).toBe(text);
      expect(controller.state.candidate.observation.z_m).toBe(0.02);
      expect(controller.state.currentResult).toBeNull(); expect(controller.state.lastResult).toBe(last);
      expect(await controller.simulate()).toBe(false);
    }
    expect(validations).toHaveLength(1); expect(simulations).toHaveLength(1);
    await controller.edit('observation.z_m', '20', 1e-3);
    expect(controller.state.invalidEdits).toEqual({}); expect(controller.state.status).toBe('ready');
  });
  it('out-of-order validation cannot overwrite a newer draft', async () => {
    const requests: { envelope: RequestEnvelope; task: ReturnType<typeof deferred<ValidationReply>> }[] = [];
    const api: BenchAPI = { validate(envelope) { const task = deferred<ValidationReply>(); requests.push({ envelope, task }); return task.promise; },
      async simulate() { throw new Error('must not simulate'); } };
    const controller = new BenchController(base, api, ids());
    const older = controller.edit('observation.z_m', '40', 1e-3);
    const newer = controller.edit('observation.z_m', '30', 1e-3);
    requests[1].task.resolve(validated(requests[1].envelope)); await newer;
    requests[0].task.resolve(validated(requests[0].envelope)); await older;
    expect(controller.state.validatedDraft?.observation.z_m).toBe(0.03); expect(controller.state.pendingValidation).toBe(false);
  });
  it('invalid text invalidates an already pending response generation', async () => {
    const task = deferred<ValidationReply>(); let submitted!: RequestEnvelope;
    const api: BenchAPI = { validate(envelope) { submitted = envelope; return task.promise; }, async simulate() { throw new Error('must not simulate'); } };
    const controller = new BenchController(base, api, ids()); const pending = controller.validateInitial();
    await controller.edit('observation.z_m', ''); task.resolve(validated(submitted)); await pending;
    expect(controller.state.validatedDraft).toBeNull(); expect(await controller.simulate()).toBe(false);
  });
  it('worker result completed after an edit is retained only at its original specification', async () => {
    const task = deferred<ArrayBuffer>(); let submitted!: RequestEnvelope;
    const api: BenchAPI = { async validate(envelope) { return validated(envelope); }, simulate(envelope) { submitted = envelope; return task.promise; } };
    const controller = new BenchController(base, api, ids()); await controller.validateInitial(); const running = controller.simulate();
    await controller.edit('observation.z_m', '40', 1e-3);
    expect(controller.state.status).toBe('simulating'); task.resolve(resultFrame(submitted)); await running;
    expect(controller.state.currentResult).toBeNull(); expect(controller.state.lastResult?.experiment.observation.z_m).toBe(0.02);
    expect(controller.state.validatedDraft?.observation.z_m).toBe(0.04);
  });
  it('a malformed success publishes no partial result and releases only client busy', async () => {
    const task = deferred<ArrayBuffer>(); let submitted!: RequestEnvelope;
    const api: BenchAPI = { async validate(envelope) { return validated(envelope); }, simulate(envelope) { submitted = envelope; return task.promise; } };
    const controller = new BenchController(base, api, ids()); await controller.validateInitial(); const running = controller.simulate();
    const wrong = cloneExperiment(submitted.experiment); wrong.observation.z_m = 0.03;
    task.resolve(resultFrame({ ...submitted, experiment: wrong })); expect(await running).toBe(false);
    expect(controller.state.error).toContain('echo mismatch'); expect(controller.state.active).toBeNull();
    expect(controller.state.currentResult).toBeNull(); expect(controller.state.lastResult).toBeNull();
  });
  it('old numerical completion cannot clear a newer invalid-draft diagnostic', async () => {
    const task = deferred<ArrayBuffer>(); let submitted!: RequestEnvelope;
    const api: BenchAPI = { async validate(envelope) {
      if (envelope.experiment.observation.z_m < 0) throw new Error('observation.z_m must be nonnegative');
      return validated(envelope);
    }, simulate(envelope) { submitted = envelope; return task.promise; } };
    const controller = new BenchController(base, api, ids()); await controller.validateInitial(); const running = controller.simulate();
    await controller.edit('observation.z_m', '-1', 1e-3);
    task.resolve(resultFrame(submitted)); await running;
    expect(controller.state.error).toContain('nonnegative'); expect(controller.state.status).toBe('error');
    expect(controller.state.currentResult).toBeNull(); expect(controller.state.lastResult?.experiment.observation.z_m).toBe(0.02);
  });
  it('failed transport never retries and a subsequent deliberate submission can succeed', async () => {
    let count = 0;
    const api: BenchAPI = { async validate(envelope) { return validated(envelope); }, async simulate(envelope) {
      count++; if (count === 1) throw new Error('backend missing'); return resultFrame(envelope);
    } };
    const controller = new BenchController(base, api, ids()); await controller.validateInitial();
    expect(await controller.simulate()).toBe(false); expect(count).toBe(1); expect(controller.state.error).toBe('backend missing');
    expect(await controller.simulate()).toBe(true); expect(count).toBe(2);
    controller.reportRenderFailure('context lost'); expect(controller.state.lastResult).not.toBeNull(); expect(count).toBe(2);
  });
  it('a presentation subscriber failure preserves completed numerical state without another solve', async () => {
    const { api, simulations } = immediateAPI(); const controller = new BenchController(base, api, ids());
    controller.subscribe(state => { if (state.lastResult) throw new Error('view could not paint'); });
    await controller.validateInitial(); expect(await controller.simulate()).toBe(true);
    expect(controller.state.renderError).toBe('view could not paint'); expect(controller.state.error).toBeNull();
    expect(controller.state.lastResult?.intensityMax).toBe(5); expect(controller.state.currentResult).not.toBeNull();
    expect(simulations).toHaveLength(1);
  });
  it('well-formed response hashes must agree with the immutable validated submission', async () => {
    const api: BenchAPI = { async validate(envelope) { return validated(envelope); },
      async simulate(envelope) { return resultFrame(envelope, 'b'.repeat(64)); } };
    const controller = new BenchController(base, api, ids()); await controller.validateInitial();
    expect(await controller.simulate()).toBe(false); expect(controller.state.error).toContain('hash differs');
    expect(controller.state.lastResult).toBeNull(); expect(controller.state.currentResult).toBeNull();
  });
  it('subscriptions are immediate and a fresh reload actor contains no saved result', async () => {
    const { api, simulations } = immediateAPI(); const controller = new BenchController(base, api, ids());
    let notifications = 0; const unsubscribe = controller.subscribe(() => notifications++);
    expect(notifications).toBe(1); await controller.validateInitial(); await controller.simulate();
    unsubscribe(); const before = notifications; controller.select('screen'); expect(notifications).toBe(before);
    const reload = new BenchController(base, api, ids()); expect(reload.state.active).toBeNull(); expect(reload.state.lastResult).toBeNull();
    expect(simulations).toHaveLength(1);
  });
});
