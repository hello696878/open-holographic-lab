import { describe, expect, it, vi } from 'vitest';
import { BenchController, ClientOperationGate } from '../src/state';
import { TwoPathController, type PreparedDualPresentation } from '../src/two_path_state';
import { fixedTwoPathExperiment, freezeTwoPathExperiment, SWEEP_PHASES_RAD,
  type TwoPathAPI, type TwoPathEnvelope, type TwoPathExperiment, type TwoPathSweepEnvelope,
  type TwoPathValidationReply } from '../src/two_path_contracts';

const base: TwoPathExperiment = { wavelength_m: 633e-9, grid: { ny: 2, nx: 3, dy: 3e-6, dx: 2e-6 },
  source: { kind: 'uniform', amplitude: 1, phase_rad: 0 },
  two_arm_spec: { arm_0_distance_m: .002, arm_1_distance_m: .003, relative_phase_rad: .37 } };
function ids() { let i = 0; return () => `12345678-1234-4234-8234-${String(++i).padStart(12, '0')}`; }
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { resolve, reject, promise }; }
function validation(envelope: TwoPathEnvelope): TwoPathValidationReply {
  return { protocol_version: 1, message_type: 'two_path_validation', request_id: envelope.request_id,
    experiment_sha256: 'a'.repeat(64), experiment: structuredClone(envelope.experiment) };
}
/** Independent state-transition fixture. It makes no V2a correctness claim. */
function frame(envelope: TwoPathEnvelope): ArrayBuffer {
  const { ny, nx, dx, dy } = envelope.experiment.grid; const plane = ny * nx * 8;
  const a = Array.from({ length: ny * nx }, (_, i) => i + 1); const b = a.map(value => value * 10);
  const header = { protocol_version: 1, message_type: 'two_path_result', request_id: envelope.request_id,
    experiment_sha256: 'a'.repeat(64), experiment: envelope.experiment, ports: ['port_0', 'port_1'],
    norms: { inputs: [4, 0], split: [2, 2], propagated: [2, 2], combiner: [2, 2], outputs: [3, 1] },
    diagnostics: { inputs_total: 4, split_total: 4, propagated_total: 4, combiner_total: 4, outputs_total: 4,
      split_delta: 0, propagation_delta: 0, phase_delta: 0, recombination_delta: 0, total_delta: 0,
      output_fractions: [.75, .25], total_output_ratio: 1 },
    arrays: [
      { name: 'intensity_port_0', role: 'intensity', port_id: 'port_0', dtype: 'float64-le', order: 'C', shape: [ny, nx], offset_bytes: 0, nbytes: plane, units: 'amplitude_unit^2' },
      { name: 'intensity_port_1', role: 'intensity', port_id: 'port_1', dtype: 'float64-le', order: 'C', shape: [ny, nx], offset_bytes: plane, nbytes: plane, units: 'amplitude_unit^2' },
      { name: 'x_m', role: 'coordinate', port_id: null, dtype: 'float64-le', order: 'C', shape: [nx], offset_bytes: 2 * plane, nbytes: nx * 8, units: 'm' },
      { name: 'y_m', role: 'coordinate', port_id: null, dtype: 'float64-le', order: 'C', shape: [ny], offset_bytes: 2 * plane + nx * 8, nbytes: ny * 8, units: 'm' },
    ], intensity_max: [a.at(-1), b.at(-1)] };
  const text = new TextEncoder().encode(JSON.stringify(header)); const start = 16 + Math.ceil(text.length / 8) * 8;
  const bytes = new ArrayBuffer(start + 8 * (2 * ny * nx + nx + ny)); const view = new DataView(bytes);
  new Uint8Array(bytes).set([79, 72, 76, 65, 66, 50, 80, 0]); view.setUint32(8, text.length, true); new Uint8Array(bytes).set(text, 16);
  [...a, ...b, ...Array.from({ length: nx }, (_, c) => (c - Math.floor(nx / 2)) * dx),
    ...Array.from({ length: ny }, (_, r) => (r - Math.floor(ny / 2)) * dy)].forEach((value, i) => view.setFloat64(start + 8 * i, value, true));
  return bytes;
}
function sweepReply(envelope: TwoPathSweepEnvelope, count = 17) {
  return { protocol_version: 1, message_type: 'two_path_sweep_result', request_id: envelope.request_id,
    fixed_experiment_sha256: 'b'.repeat(64), fixed_experiment: envelope.fixed_experiment, phases_rad: envelope.phases_rad,
    status: count === 17 ? 'complete' : 'failed', requested_count: 17, completed_count: count, failed_index: count === 17 ? null : count,
    rows: SWEEP_PHASES_RAD.slice(0, count).map((phase, index) => ({ index, phase_rad: phase, input_norm: 4,
      output_norms: [3, 1], output_fractions: [.75, .25], total_output_ratio: 1, split_delta: 0,
      propagation_delta: 0, phase_delta: 0, recombination_delta: 0, total_delta: 0 })),
    error: count === 17 ? null : { code: 'numerical_failure', message: 'Actual operation failed' } };
}
function immediate() {
  const validations: TwoPathEnvelope[] = []; const singles: TwoPathEnvelope[] = []; const sweeps: TwoPathSweepEnvelope[] = [];
  const api: TwoPathAPI = { async validate(envelope) { validations.push(envelope); return validation(envelope); },
    async simulate(envelope) { singles.push(envelope); return frame(envelope); },
    async sweep(envelope) { sweeps.push(envelope); return { body: sweepReply(envelope), httpStatus: 200 }; } };
  return { api, validations, singles, sweeps };
}

describe('two-path explicit submission actor', () => {
  it('unit conversion occurs once and nonzero signed phase is never wrapped', async () => {
    const { api, singles } = immediate(); const actor = new TwoPathController(base, api, ids());
    await actor.edit('two_arm_spec.arm_0_distance_m', '7', 1e-3);
    expect(actor.state.candidate.two_arm_spec.arm_0_distance_m, 'UNIT_DISTANCE_DETECTED').toBe(7 * 1e-3);
    await actor.edit('two_arm_spec.relative_phase_rad', '-17.123456789012345');
    expect(actor.state.candidate.two_arm_spec.relative_phase_rad, 'UNIT_PHASE_DETECTED').toBe(-17.123456789012345);
    expect(singles).toHaveLength(0); await actor.simulate(); expect(singles[0].experiment.two_arm_spec).toEqual(actor.state.candidate.two_arm_spec);
  });
  it('signed-zero request policy precedes validation and submitted identity', async () => {
    const { api, validations, singles } = immediate(); const actor = new TwoPathController(base, api, ids());
    await actor.edit('two_arm_spec.relative_phase_rad', '-0'); await actor.edit('source.phase_rad', '-0'); await actor.simulate();
    for (const envelope of [...validations, ...singles]) {
      expect(Object.is(envelope.experiment.two_arm_spec.relative_phase_rad, -0)).toBe(false);
      expect(Object.is(envelope.experiment.source.phase_rad, -0)).toBe(false);
    }
    expect(singles).toHaveLength(1);
  });
  it('initial validation, selection and render-error reporting invoke no numerical operation', async () => {
    const { api, validations, singles, sweeps } = immediate(); const actor = new TwoPathController(base, api, ids());
    await actor.validateInitial(); await actor.validateInitial(); actor.select('port_1'); actor.reportRenderFailure('context lost'); actor.clearRenderFailure();
    expect(validations).toHaveLength(1); expect(singles).toHaveLength(0); expect(sweeps).toHaveLength(0);
  });
  it('one frozen simulation survives rapid clicks and releases shared busy at settlement', async () => {
    const { api, singles } = immediate(); const held = deferred<ArrayBuffer>();
    api.simulate = envelope => { singles.push(envelope); return held.promise; };
    const initial = structuredClone(base); const actor = new TwoPathController(initial, api, ids()); await actor.validateInitial();
    const first = actor.simulate(); const second = actor.simulate();
    expect(singles, 'DUPLICATE_SUBMIT_DETECTED').toHaveLength(1); expect(await second).toBe(false); expect(actor.gate.busy).toBe(true);
    initial.two_arm_spec.relative_phase_rad = 99; expect(singles[0].experiment.two_arm_spec.relative_phase_rad).toBe(.37);
    held.resolve(frame(singles[0])); expect(await first).toBe(true); expect(actor.gate.busy).toBe(false);
    expect(actor.state.currentResult?.ports[1].intensity[5]).toBe(60); expect(actor.state.lastResult).toBe(actor.state.completedNumerical);
  });
  it('scientific edits invalidate the completed pair immediately while retaining original prior identity', async () => {
    const { api, singles } = immediate(); const actor = new TwoPathController(base, api, ids()); await actor.validateInitial(); await actor.simulate();
    const previous = actor.state.lastResult; const edit = actor.edit('two_arm_spec.relative_phase_rad', '-');
    expect(actor.state.currentResult, 'BOTH_TEXTURES_INVALIDATED').toBeNull(); expect(actor.state.lastResult).toBe(previous);
    expect(previous?.experiment.two_arm_spec.relative_phase_rad).toBe(.37); await edit;
    expect(await actor.simulate()).toBe(false); expect(singles).toHaveLength(1);
  });
  it('away-and-back mode changes reject late attachment without aborting or clearing the shared operation', async () => {
    const { api, singles } = immediate(); const held = deferred<ArrayBuffer>(); api.simulate = envelope => { singles.push(envelope); return held.promise; };
    const prepare = vi.fn(() => ({ commit() {}, dispose() {} })); const actor = new TwoPathController(base, api, ids(), new ClientOperationGate(), prepare);
    await actor.validateInitial(); const running = actor.simulate(); actor.deactivate(); await actor.activate();
    expect(actor.gate.busy).toBe(true); expect(await actor.simulate()).toBe(false);
    held.resolve(frame(singles[0])); expect(await running).toBe(true);
    expect(actor.state.currentResult, 'CROSS_MODE_STALE_DETECTED').toBeNull(); expect(prepare).not.toHaveBeenCalled();
    expect(actor.state.lastResult?.requestId).toBe(singles[0].request_id); expect(actor.gate.busy).toBe(false);
  });
  it('old validation cannot resurrect attachment after mode switch or newer invalid text', async () => {
    const { api } = immediate(); const pending: { envelope: TwoPathEnvelope; task: ReturnType<typeof deferred<TwoPathValidationReply>> }[] = [];
    api.validate = envelope => { const task = deferred<TwoPathValidationReply>(); pending.push({ envelope, task }); return task.promise; };
    const actor = new TwoPathController(base, api, ids()); const first = actor.validateInitial(); actor.deactivate();
    pending[0].task.resolve(validation(pending[0].envelope)); await first; expect(actor.state.validatedDraft).toBeNull();
    const second = actor.activate(); await actor.edit('two_arm_spec.relative_phase_rad', '');
    pending[1].task.resolve(validation(pending[1].envelope)); await second; expect(actor.state.validatedDraft).toBeNull();
  });
  it('a malformed frame publishes neither port and a deliberate recovery succeeds without retry', async () => {
    const { api, singles } = immediate(); let fail = true;
    api.simulate = async envelope => { singles.push(envelope); if (fail) return new ArrayBuffer(4); return frame(envelope); };
    const actor = new TwoPathController(base, api, ids()); await actor.validateInitial();
    expect(await actor.simulate()).toBe(false); expect(actor.state.lastResult).toBeNull(); expect(singles).toHaveLength(1);
    fail = false; expect(await actor.simulate()).toBe(true); expect(singles).toHaveLength(2);
  });
  it('atomic presentation preparation failure preserves previous completion and successful numerical evidence', async () => {
    const { api, singles } = immediate(); const commit = vi.fn(); const dispose = vi.fn(); const finalize = vi.fn();
    let fail = false; const preparer = () => { if (fail) throw new Error('second output preparation failed'); return { commit, dispose, finalize }; };
    const actor = new TwoPathController(base, api, ids(), new ClientOperationGate(), preparer); await actor.validateInitial(); await actor.simulate();
    const previous = actor.state.lastResult; fail = true;
    expect(await actor.simulate()).toBe(true);
    expect(actor.state.lastResult, 'ATOMIC_SECOND_TEXTURE_DETECTED').toBe(previous); expect(actor.state.currentResult).toBeNull();
    expect(actor.state.completedNumerical?.requestId).not.toBe(previous?.requestId); expect(actor.state.error).toBeNull();
    expect(actor.state.renderError).toContain('second output'); expect(commit).toHaveBeenCalledTimes(1); expect(finalize).toHaveBeenCalledTimes(1);
    expect(singles).toHaveLength(2); expect(actor.gate.busy).toBe(false);
    fail = false; await actor.simulate(); expect(actor.state.lastResult).toBe(actor.state.completedNumerical); expect(actor.state.currentResult).toBe(actor.state.lastResult);
  });
  it('committing a prepared view failure disposes new resources and does not classify numerics as failed', async () => {
    const { api } = immediate(); const dispose = vi.fn();
    const transaction: PreparedDualPresentation = { commit() { throw new Error('presentation commit failed'); }, dispose };
    const actor = new TwoPathController(base, api, ids(), new ClientOperationGate(), () => transaction); await actor.validateInitial();
    expect(await actor.simulate()).toBe(true); expect(dispose).toHaveBeenCalledOnce(); expect(actor.state.completedNumerical).not.toBeNull();
    expect(actor.state.currentResult).toBeNull(); expect(actor.state.error).toBeNull(); expect(actor.state.renderError).toContain('commit failed');
  });
  it('single, sweep and legacy actors share one client slot, including presentation listener failures', async () => {
    const { api, singles, sweeps } = immediate(); const held = deferred<ArrayBuffer>(); api.simulate = envelope => { singles.push(envelope); return held.promise; };
    const gate = new ClientOperationGate(); gate.subscribe(() => { throw new Error('view failure'); });
    const actor = new TwoPathController(base, api, ids(), gate); await actor.validateInitial();
    const legacySpec = { schema_version: 1 as const, model_contract: 'v0_aligned_scalar_forward_v1' as const,
      wavelength_m: base.wavelength_m, grid: base.grid, source: base.source, components: [], observation: { id: 'screen', z_m: 0 } };
    let legacyCalls = 0;
    const legacy = new BenchController(legacySpec, { async validate(envelope) { return { protocol_version: 1, request_id: envelope.request_id,
      experiment_sha256: 'a'.repeat(64), experiment: envelope.experiment }; }, async simulate() { legacyCalls++; throw new Error('controlled legacy transport failure'); } }, ids(), gate);
    await legacy.validateInitial(); const running = actor.simulate(); expect(await actor.runSweep()).toBe(false); expect(await legacy.simulate()).toBe(false);
    expect(sweeps).toHaveLength(0); expect(legacyCalls).toBe(0); held.resolve(frame(singles[0])); await running;
    expect(await legacy.simulate()).toBe(false); expect(legacyCalls).toBe(1); expect(gate.busy).toBe(false);
    expect(await actor.runSweep()).toBe(true); expect(sweeps).toHaveLength(1);
  });
  it('legacy mode epochs reject pending validation and unfinished text stays unvalidated on reactivation', async () => {
    const legacySpec = { schema_version: 1 as const, model_contract: 'v0_aligned_scalar_forward_v1' as const,
      wavelength_m: base.wavelength_m, grid: base.grid, source: base.source, components: [], observation: { id: 'screen', z_m: 0 } };
    const held = deferred<any>(); let validations = 0; let captured: any;
    const actor = new BenchController(legacySpec, { validate(envelope) { validations++; captured = envelope; return held.promise; },
      async simulate() { throw new Error('No implicit numerical operation'); } }, ids());
    const validating = actor.validateInitial(); actor.deactivate();
    held.resolve({ protocol_version: 1, request_id: captured.request_id, experiment_sha256: 'a'.repeat(64), experiment: captured.experiment });
    await validating; expect(actor.state.validatedDraft, 'CROSS_MODE_STALE_DETECTED').toBeNull();
    await actor.edit('observation.z_m', '-'); await actor.activate();
    expect(validations).toBe(1); expect(actor.state.validatedDraft).toBeNull(); expect(await actor.simulate()).toBe(false);
  });
  it('sweep freezes fixed inputs, returns only actual rows and chart selection does not compute', async () => {
    const { api, singles, sweeps } = immediate(); const actor = new TwoPathController(base, api, ids()); await actor.validateInitial();
    expect(await actor.runSweep()).toBe(true); expect(sweeps).toHaveLength(1);
    expect(sweeps[0].fixed_experiment).toEqual(fixedTwoPathExperiment(base)); expect(sweeps[0].phases_rad).toEqual(SWEEP_PHASES_RAD);
    expect(sweeps[0].fixed_experiment).not.toHaveProperty('two_arm_spec'); expect(actor.state.lastSweep?.rows).toHaveLength(17);
    actor.selectSweepPoint(3); expect(singles).toHaveLength(0); expect(sweeps).toHaveLength(1);
    expect(await actor.simulateSelectedPhase()).toBe(true); expect(singles).toHaveLength(1);
    expect(singles[0].experiment.two_arm_spec.relative_phase_rad).toBe(SWEEP_PHASES_RAD[3]);
  });
  it('failed sweep remains a failed operation with unmistakable genuine-prefix state', async () => {
    const { api, sweeps } = immediate(); api.sweep = async envelope => { sweeps.push(envelope); return { body: sweepReply(envelope, 3), httpStatus: 422 }; };
    const actor = new TwoPathController(base, api, ids()); await actor.validateInitial();
    expect(await actor.runSweep()).toBe(false); expect(actor.state.lastSweep?.status).toBe('failed');
    expect(actor.state.lastSweep?.rows).toHaveLength(3); expect(actor.state.error).toContain('3/17'); expect(sweeps).toHaveLength(1);
  });
  it.each(['edit', 'mode'])('selected-phase action cannot resume after an intervening %s during validation', async change => {
    const { api, singles } = immediate(); const actor = new TwoPathController(base, api, ids());
    await actor.validateInitial(); await actor.runSweep(); actor.selectSweepPoint(3);
    const pending: { envelope: TwoPathEnvelope; task: ReturnType<typeof deferred<TwoPathValidationReply>> }[] = [];
    api.validate = envelope => { const task = deferred<TwoPathValidationReply>(); pending.push({ envelope, task }); return task.promise; };
    const requested = actor.simulateSelectedPhase();
    let newer: Promise<void>;
    if (change === 'edit') newer = actor.edit('source.amplitude', '.5');
    else { actor.deactivate(); newer = actor.activate(); }
    // Make the later draft valid before the original action's validation settles.
    pending[1].task.resolve(validation(pending[1].envelope)); await newer;
    pending[0].task.resolve(validation(pending[0].envelope));
    expect(await requested, 'SELECTED_PHASE_RACE_DETECTED').toBe(false);
    expect(singles, 'SELECTED_PHASE_RACE_DETECTED').toHaveLength(0); expect(actor.gate.busy).toBe(false);
  });
  it('sweep crossing mode boundaries stays stale and suppresses duplicate rapid sweep clicks', async () => {
    const { api, sweeps } = immediate(); const held = deferred<{ body: unknown; httpStatus: number }>();
    api.sweep = envelope => { sweeps.push(envelope); return held.promise; };
    const actor = new TwoPathController(base, api, ids()); await actor.validateInitial();
    const running = actor.runSweep(); expect(await actor.runSweep()).toBe(false); expect(await actor.simulate()).toBe(false);
    expect(sweeps, 'DUPLICATE_SUBMIT_DETECTED').toHaveLength(1); actor.deactivate(); await actor.activate();
    held.resolve({ body: sweepReply(sweeps[0]), httpStatus: 200 }); expect(await running).toBe(true);
    expect(actor.state.currentSweep, 'CROSS_MODE_STALE_DETECTED').toBeNull(); expect(actor.state.lastSweep?.status).toBe('complete');
  });
  it('oversized sweep grid sends zero requests and reload actor retains no prior result', async () => {
    const { api, sweeps } = immediate(); const large = freezeTwoPathExperiment({ ...base, grid: { ...base.grid, nx: 129 } });
    const actor = new TwoPathController(large, api, ids()); await actor.validateInitial(); expect(await actor.runSweep()).toBe(false);
    expect(sweeps).toHaveLength(0); expect(actor.state.error).toContain('128');
    const reload = new TwoPathController(base, api, ids()); expect(reload.state.lastResult).toBeNull(); expect(reload.state.lastSweep).toBeNull(); expect(reload.state.active).toBeNull();
  });
});
