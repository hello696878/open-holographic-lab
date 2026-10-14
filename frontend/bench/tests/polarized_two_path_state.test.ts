import { describe, expect, it, vi } from 'vitest';
import { BenchController, ClientOperationGate } from '../src/state';
import { TwoPathController } from '../src/two_path_state';
import { PolarizationController } from '../src/polarization_state';
import { presetExperiment } from '../src/presets';
import { twoPathPreset } from '../src/two_path_presets';
import { polarizationPreset } from '../src/polarization_presets';
import { PolarizedTwoPathController } from '../src/polarized_two_path_state';
import { polarizedTwoPathPreset } from '../src/polarized_two_path_presets';
import { SWEEP_PHASES_RAD, type PolarizedTwoPathAPI, type PolarizedTwoPathEnvelope,
  type PolarizedTwoPathSweepEnvelope, type PolarizedTwoPathValidation, type PolarizedTwoPathSweepValidation } from '../src/polarized_two_path_contracts';
const digest = 'a'.repeat(64), sweepDigest = 'b'.repeat(64);
function ids() { let n = 0; return () => `12345678-1234-4234-8234-${(++n).toString(16).padStart(12, '0')}`; }
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(yes => { resolve = yes; }); return { resolve, promise }; }
function validation(sent: PolarizedTwoPathEnvelope): PolarizedTwoPathValidation { return { protocol_version: 1, message_type: 'polarized_two_path_validation',
  request_id: sent.request_id, experiment_sha256: digest, experiment: sent.experiment }; }
function sweepValidation(sent: PolarizedTwoPathSweepEnvelope): PolarizedTwoPathSweepValidation { return { protocol_version: 1, message_type: 'polarized_two_path_sweep_validation', request_id: sent.request_id,
  fixed_experiment_sha256: digest, fixed_experiment: sent.fixed_experiment, phases_rad: SWEEP_PHASES_RAD, sweep_sha256: sweepDigest }; }
/** Controller fixture: measurement records come from a stub API, never JS optics. */
function scalars(enabled: boolean, angle: number, lengths = [0, 0]): any { return {
  norms: { inputs: [2, 0], split: [1, 1], propagated: [1, 1], elements: [1, 1], combiner: [1, 1], outputs: [1, 1], arm_action_norms: lengths.map(n => Array(n).fill(1)) },
  diagnostics: { inputs_total: 2, split_total: 2, propagated_total: 2, elements_total: 2, combiner_total: 2, outputs_total: 2,
    split_delta: 0, propagation_delta: 0, elements_delta: 0, phase_delta: 0, recombination_delta: 0, total_delta: 0,
    propagation_deltas: [0, 0], element_deltas: [0, 0], phase_deltas: [0, 0], arm_action_deltas: lengths.map(n => Array(n).fill(0)), output_fractions: [.5, .5], total_output_ratio: 1 },
  analysis: enabled ? { enabled: true, axis_angle_rad: angle, ports: [0, 1].map(i => ({ id: `port_${i}`, raw_norm: 1, analyzed_norm: .5, removed_norm: .5, original_input_ratio: .25, raw_output_ratio: .5 })),
    total_norm: 1, total_removed_norm: 1, total_original_input_ratio: .5 } : { enabled: false, axis_angle_rad: angle, ports: null, total_norm: null, total_removed_norm: null, total_original_input_ratio: null } };
}
function frame(sent: PolarizedTwoPathEnvelope): ArrayBuffer {
  const { nx, ny, dx, dy } = sent.experiment.grid, k = sent.experiment.analyzer.enabled ? 4 : 2, plane = nx * ny * 8;
  const arrays: any[] = Array.from({ length: k }, (_, i) => ({ name: `${i < 2 ? 'raw' : 'analyzed'}_port_${i % 2}_intensity`, role: 'intensity', port_id: `port_${i % 2}`,
    state: i < 2 ? 'raw' : 'analyzed', dtype: 'float64-le', order: 'C', shape: [ny, nx], offset_bytes: i * plane, nbytes: plane, units: 'amplitude_unit^2' }));
  arrays.push({ name: 'x_m', role: 'coordinate', port_id: null, state: null, dtype: 'float64-le', order: 'C', shape: [nx], offset_bytes: k * plane, nbytes: nx * 8, units: 'm' },
    { name: 'y_m', role: 'coordinate', port_id: null, state: null, dtype: 'float64-le', order: 'C', shape: [ny], offset_bytes: k * plane + nx * 8, nbytes: ny * 8, units: 'm' });
  const header = { protocol_version: 1, message_type: 'polarized_two_path_result', request_id: sent.request_id, experiment_sha256: sent.experiment_sha256, experiment: sent.experiment,
    ...scalars(sent.experiment.analyzer.enabled, sent.experiment.analyzer.axis_angle_rad, [sent.experiment.arm_0.actions.length, sent.experiment.arm_1.actions.length]), arrays, intensity_max: Array.from({ length: k }, (_, i) => i + 1) };
  const text = new TextEncoder().encode(JSON.stringify(header)), start = 16 + Math.ceil(text.length / 8) * 8, bytes = new ArrayBuffer(start + 8 * (k * nx * ny + nx + ny)), view = new DataView(bytes);
  new Uint8Array(bytes).set([79, 72, 76, 65, 66, 80, 84, 0]); view.setUint32(8, text.length, true); new Uint8Array(bytes).set(text, 16);
  [...Array.from({ length: k }, (_, i) => Array(nx * ny).fill(i + 1)).flat(), ...Array.from({ length: nx }, (_, c) => (c - Math.floor(nx / 2)) * dx), ...Array.from({ length: ny }, (_, r) => (r - Math.floor(ny / 2)) * dy)].forEach((v, i) => view.setFloat64(start + 8 * i, v, true)); return bytes;
}
function sweep(sent: PolarizedTwoPathSweepEnvelope, count = 17): any { return { protocol_version: 1, message_type: 'polarized_two_path_sweep', request_id: sent.request_id,
  fixed_experiment_sha256: sent.fixed_experiment_sha256, sweep_sha256: sweepDigest, fixed_experiment: sent.fixed_experiment, phases_rad: SWEEP_PHASES_RAD,
  status: count === 17 ? 'complete' : 'failed', requested_count: 17, completed_count: count, failed_index: count === 17 ? null : count,
  rows: SWEEP_PHASES_RAD.slice(0, count).map((phase_rad, index) => ({ index, phase_rad, ...scalars(sent.fixed_experiment.analyzer.enabled, sent.fixed_experiment.analyzer.axis_angle_rad,
    [sent.fixed_experiment.arm_0.actions.length, sent.fixed_experiment.arm_1.actions.length]) })), error: count === 17 ? null : { code: 'numerical_failure', message: 'Analyzer point failed' } }; }
function setup(enabled = true) { const initial = polarizedTwoPathPreset(enabled ? 'orthogonal_analyzed' : 'identical'); initial.grid = { ny: 3, nx: 4, dy: 5e-6, dx: 2e-6 };
  const singles: PolarizedTwoPathEnvelope[] = [], sweeps: PolarizedTwoPathSweepEnvelope[] = [], validations: PolarizedTwoPathEnvelope[] = [], sweepValidations: PolarizedTwoPathSweepEnvelope[] = [];
  const api: PolarizedTwoPathAPI = { async validate(sent) { validations.push(sent); return validation(sent); }, async validateSweep(sent) { sweepValidations.push(sent); return sweepValidation(sent); },
    async simulate(sent) { singles.push(sent); return frame(sent); }, async sweep(sent) { sweeps.push(sent); return { body: sweep(sent), httpStatus: 200 }; } };
  const actor = new PolarizedTwoPathController(initial, api, ids()); return { actor, api, singles, sweeps, validations, sweepValidations }; }
describe('immutable polarized two-path controller and explicit release', () => {
  it('validation is passive and one explicit simulation publishes a whole identity', async () => {
    const { actor, singles, sweeps } = setup(); await actor.validateInitial(); expect(singles).toHaveLength(0); expect(sweeps).toHaveLength(0);
    expect(await actor.simulate()).toBe(true); expect(singles).toHaveLength(1); expect(actor.state.currentResult?.requestId).toBe(singles[0].request_id);
    actor.selectView('analyzed'); actor.select('port_1'); expect(singles).toHaveLength(1); expect(actor.state.viewSelection).toBe('analyzed');
  });
  it('analyzer enablement and saved angle are scientific edits, not presentation switches', async () => {
    const { actor, singles } = setup(false); await actor.validateInitial(); await actor.simulate(); const revision = actor.state.revision;
    await actor.edit('analyzer.axis_angle_rad', '-3.123456789012345');
    expect(actor.state.revision, 'PT_ANALYZER_EDIT_SCIENTIFIC').toBe(revision + 1); expect(actor.state.currentResult, 'PT_ANALYZER_EDIT_SCIENTIFIC').toBeNull();
    expect(actor.state.candidate.analyzer.axis_angle_rad).toBe(-3.123456789012345); await actor.setAnalyzerEnabled(true); await actor.simulate();
    expect(singles).toHaveLength(2); expect(singles[1].experiment.analyzer.axis_angle_rad, 'PT_DISABLED_ANGLE_RETAINED').toBe(-3.123456789012345);
  });
  it('blocks duplicate numerical intents and retains the shared gate until settlement', async () => {
    const { actor, api, singles } = setup(), held = deferred<ArrayBuffer>(); api.simulate = sent => { singles.push(sent); return held.promise; };
    await actor.validateInitial(); const running = actor.simulate(); expect(await actor.simulate()).toBe(false); expect(actor.gate.acquire('other', 'sequential', 'single')).toBe(false);
    expect(actor.releaseResults()).toBe(false); held.resolve(frame(singles[0])); await running; expect(actor.gate.busy).toBe(false); expect(singles).toHaveLength(1);
  });
  it('late and away/back outcomes never attach to another draft', async () => {
    const { actor, api, singles } = setup(), held = deferred<ArrayBuffer>(), prepare = vi.fn(() => ({ commit() {}, dispose() {} }));
    actor.setResultPreparer(prepare); api.simulate = sent => { singles.push(sent); return held.promise; }; await actor.validateInitial();
    const running = actor.simulate(); actor.deactivate(); await actor.activate(); held.resolve(frame(singles[0])); await running;
    expect(actor.state.currentResult, 'PT_STALE_PAIR_DETECTED').toBeNull(); expect(prepare, 'PT_STALE_PAIR_DETECTED').not.toHaveBeenCalled();
    expect(actor.state.completedNumerical?.requestId).toBe(singles[0].request_id); expect(actor.gate.busy).toBe(false);
  });
  it('keeps prior whole presentation on late preparation failure and retries without science', async () => {
    const { actor, singles } = setup(); let fail = false; const dispose = vi.fn(); actor.setResultPreparer(() => ({ commit() { if (fail) throw new Error('late whole pair preparation'); }, dispose }));
    await actor.validateInitial(); await actor.simulate(); const prior = actor.state.currentResult; fail = true; await actor.simulate();
    expect(actor.state.currentResult, 'PT_ATOMIC_PAIR_DETECTED').toBe(prior); expect(actor.state.lastResult).toBe(prior); expect(actor.state.completedNumerical).not.toBe(prior);
    expect(actor.state.renderError).toContain('whole pair'); expect(dispose).toHaveBeenCalledOnce(); fail = false; expect(actor.retryPresentation()).toBe(true); expect(singles).toHaveLength(2);
  });
  it('rechecks eligibility after resource preparation and before commit', async () => {
    const { actor } = setup(), commit = vi.fn(), dispose = vi.fn(); await actor.validateInitial(); actor.setResultPreparer(() => {
      actor.deactivate(); return { commit, dispose }; }); await actor.simulate();
    expect(commit, 'PT_PREPARATION_IDENTITY_RECHECK').not.toHaveBeenCalled(); expect(dispose).toHaveBeenCalledOnce(); expect(actor.state.currentResult).toBeNull();
  });
  it('measurement failure is not raw-only success and does not automatically retry', async () => {
    const { actor, api, singles } = setup(); api.simulate = async sent => { singles.push(sent); throw new Error('HTTP 422: analyzer port_1 underflow'); };
    await actor.validateInitial(); expect(await actor.simulate()).toBe(false); expect(actor.state.currentResult).toBeNull(); expect(actor.state.completedNumerical).toBeNull(); expect(singles).toHaveLength(1); expect(actor.gate.busy).toBe(false);
  });
  it('sweep validation freezes full settings and selecting a completed marker never computes', async () => {
    const { actor, singles, sweeps, sweepValidations } = setup(); await actor.validateInitial(); expect(await actor.runSweep()).toBe(true);
    expect(sweepValidations[0].fixed_experiment_sha256).toBeNull(); expect(sweeps[0].fixed_experiment_sha256).toBe(digest);
    expect(sweeps).toHaveLength(1); expect(actor.state.currentSweep?.rows).toHaveLength(17); actor.selectSweepPoint(16); expect(singles).toHaveLength(0);
    expect(await actor.applySelectedPhaseAndSimulate()).toBe(true); expect(singles).toHaveLength(1); expect(singles[0].experiment.relative_phase_rad).toBe(2 * Math.PI);
  });
  it('pending sweep validation blocks duplicates and cannot queue after an edit, release or busy contender', async () => {
    for (const change of ['edit', 'release', 'busy'] as const) { const { actor, api, sweeps, sweepValidations } = setup(), held = deferred<PolarizedTwoPathSweepValidation>();
      api.validateSweep = sent => { sweepValidations.push(sent); return held.promise; }; await actor.validateInitial(); const running = actor.runSweep(); expect(await actor.runSweep()).toBe(false);
      if (change === 'edit') await actor.edit('relative_phase_rad', '2'); else if (change === 'release') actor.releaseResults(); else actor.gate.acquire('other', 'two_path', 'single');
      held.resolve(sweepValidation(sweepValidations[0])); expect(await running, 'PT_SWEEP_NO_QUEUE').toBe(false); expect(sweeps).toHaveLength(0); actor.gate.release('other'); }
  });
  it.each([0, 8, 16])('failed point %s publishes only its genuine incomplete prefix', async count => {
    const { actor, api } = setup(); api.sweep = async sent => ({ body: sweep(sent, count), httpStatus: 422 }); await actor.validateInitial(); expect(await actor.runSweep()).toBe(false);
    expect(actor.state.currentSweep?.rows).toHaveLength(count); expect(actor.state.currentSweep?.status).toBe('failed'); expect(actor.state.error).toContain(`PARTIAL ${count}/17`);
  });
  it('release drops every retained result/recovery/sweep owner and explicit retry handles', async () => {
    const { actor, singles } = setup(); await actor.validateInitial(); await actor.simulate(); await actor.runSweep(); actor.selectSweepPoint(2);
    const draft = actor.state.candidate, validated = actor.state.validatedDraft, revision = actor.state.revision, epoch = actor.state.attachmentEpoch;
    expect(actor.releaseResults()).toBe(true);
    for (const key of ['lastResult', 'currentResult', 'completedNumerical', 'lastSweep', 'currentSweep', 'selectedSweepIndex'] as const) expect(actor.state[key], 'PT_RELEASE_BUFFER_OWNERS').toBeNull();
    expect(actor.retryPresentation(), 'PT_RELEASE_BUFFER_OWNERS').toBe(false); expect(singles).toHaveLength(1);
    expect(actor.state.candidate).toBe(draft); expect(actor.state.validatedDraft).toBe(validated); expect(actor.state.revision).toBe(revision); expect(actor.state.attachmentEpoch).toBe(epoch);
  });
  it('an old delayed presentation cannot resurrect explicitly released numerics', async () => {
    const { actor } = setup(); await actor.validateInitial(); actor.setResultPreparer(() => { throw new Error('defer display'); }); await actor.simulate();
    const commit = vi.fn(), dispose = vi.fn(); actor.setResultPreparer(() => { expect(actor.releaseResults()).toBe(true); return { commit, dispose }; });
    expect(actor.retryPresentation(), 'PT_RELEASE_DELAYED_PRESENTATION').toBe(false); expect(commit, 'PT_RELEASE_DELAYED_PRESENTATION').not.toHaveBeenCalled(); expect(dispose).toHaveBeenCalledOnce();
    expect(actor.state.completedNumerical, 'PT_RELEASE_DELAYED_PRESENTATION').toBeNull(); expect(actor.state.currentResult).toBeNull();
  });
  it('all four controllers preserve exact valid and invalid drafts and identity during repeated release', async () => {
    const gate = new ClientOperationGate(), actors = [new BenchController(presetExperiment('free'), undefined, ids(), gate),
      new TwoPathController(twoPathPreset('uniform64'), undefined, ids(), gate), new PolarizationController(polarizationPreset('identity'), undefined, ids(), gate),
      new PolarizedTwoPathController(polarizedTwoPathPreset('identical'), undefined, ids(), gate)];
    for (const actor of actors) { (actor as any).restoreValidatedSettings(actor.state.candidate, digest); const valid = actor.state.validatedDraft;
      // Controlled reference owners exercise release, not optics or transport correctness.
      const populate = () => { const state = actor.state, owner = { buffer: new Float64Array([1, 2, 3]) };
        (actor as any).snapshot = Object.freeze({ ...state, lastResult: owner, currentResult: owner,
          ...('completedNumerical' in state ? { completedNumerical: owner, lastSweep: { rows: [owner] }, currentSweep: { rows: [owner] }, selectedSweepIndex: 0 } : {}) }); };
      const assertReleased = () => { expect(actor.state.lastResult, 'PT_RELEASE_BUFFER_OWNERS').toBeNull(); expect(actor.state.currentResult, 'PT_RELEASE_BUFFER_OWNERS').toBeNull();
        if ('completedNumerical' in actor.state) for (const key of ['completedNumerical', 'lastSweep', 'currentSweep', 'selectedSweepIndex'] as const) expect(actor.state[key], 'PT_RELEASE_BUFFER_OWNERS').toBeNull(); };
      populate(); expect(actor.releaseResults()).toBe(true); assertReleased(); expect(actor.state.validatedDraft, 'PT_RELEASE_DRAFT_PRESERVATION').toBe(valid);
      await actor.edit('source.amplitude', 'invalid'); const before = actor.state, generation = actor.resultGeneration;
      populate(); expect(actor.releaseResults()).toBe(true); assertReleased(); expect(actor.releaseResults()).toBe(true);
      for (const key of ['candidate', 'validatedDraft', 'invalidEdits', 'revision', 'attachmentEpoch', 'selection'] as const) expect(actor.state[key], 'PT_RELEASE_DRAFT_PRESERVATION').toBe(before[key]);
      expect(actor.resultGeneration).toBe(generation + 2); gate.acquire('held', 'polarized_two_path', 'single'); expect(actor.releaseResults()).toBe(false); gate.release('held');
    }
  });
  it('busy state is rechecked at release execution', () => {
    const { actor } = setup(); let reads = 0; Object.defineProperty(actor.gate, 'busy', { get() { return ++reads > 1; } });
    const before = actor.state; expect(actor.releaseResults(), 'PT_RELEASE_BUSY_RECHECK').toBe(false); expect(actor.state).toBe(before); expect(actor.resultGeneration).toBe(0);
  });
  it('budget rejection retains old outcomes with no eviction or retry; release permits a later deliberate run', async () => {
    const { actor, singles } = setup(); await actor.validateInitial(); await actor.simulate(); const prior = actor.state.currentResult; let over = true;
    actor.setOperationAdmission(() => { if (over) throw new Error('fixed owned budget exceeded'); }); expect(await actor.simulate()).toBe(false);
    expect(actor.state.currentResult, 'PT_BUDGET_NO_EVICTION_RETRY').toBe(prior); expect(actor.state.lastResult, 'PT_BUDGET_NO_EVICTION_RETRY').toBe(prior); expect(singles, 'PT_BUDGET_NO_EVICTION_RETRY').toHaveLength(1);
    actor.releaseResults(); over = false; expect(singles, 'PT_BUDGET_NO_EVICTION_RETRY').toHaveLength(1); expect(await actor.simulate()).toBe(true); expect(singles, 'PT_BUDGET_NO_EVICTION_RETRY').toHaveLength(2);
  });
  it('invalid nonzero underflow text is preserved and disabled publication resets an absent analyzed view', async () => {
    const { actor } = setup(); await actor.validateInitial(); await actor.simulate(); actor.selectView('analyzed'); await actor.setAnalyzerEnabled(false); await actor.simulate();
    expect(actor.state.viewSelection).toBe('raw'); await actor.edit('source.amplitude', '1e-999'); expect(actor.state.invalidEdits['source.amplitude']).toBe('1e-999'); expect(actor.state.validatedDraft).toBeNull();
  });
});
