import { describe, expect, it, vi } from 'vitest';
import { ClientOperationGate } from '../src/state';
import { R03Controller } from '../src/r03_fig2a_state';
import { R03_DEFAULT, R03_IDENTITY, R03_MODEL, type R03Envelope, type R03API } from '../src/r03_fig2a_contracts';
const sha = 'a'.repeat(64);
const validation = (s: R03Envelope) => ({ protocol_version: 1, message_type: 'r03_ideal_validation', request_id: s.request_id, experiment_sha256: sha, experiment: s.experiment });
/** Stub transport records only; real numerical/API comparison is a separate production gate. */
function wire(s: R03Envelope): any { return { ...validation(s), message_type: 'r03_ideal_result',
  phase: { shape: [16, 16], order: 'C', unwrapped_rad: Array(256).fill(.25), wrapped_rad: Array(256).fill(.25) },
  stages: ['source', 'after_slm', 'after_qwp', 'output'].map(id => ({ id, coherency: [[{ re: .5, im: 0 }, { re: 0, im: 0 }], [{ re: 0, im: 0 }, { re: .5, im: 0 }]],
    stokes: [1, 0, 0, 0], normalized_stokes: [0, 0, 0], polarized_direction: null, degree_of_polarization: 0, eigenvalues: [.5, .5], roundoff_limited: false })),
  population: { infinite_gaussian_degree_of_polarization: .5, assumption: 'Stub transport-only population field.' },
  provenance: { model_contract: R03_MODEL, identity: R03_IDENTITY, rng_algorithm: 'PCG64', rng_normal_sampler: 'Generator.standard_normal', rng_draw_shape: [16, 16], sample_order: 'C', sample_count: 256,
    probability_weight: 1 / 256, measurement: 'probability_mean_uncentered_second_moment', source: 'amplitude*(1,1)/sqrt(2)', element_order: ['SLM', 'QWP', 'HWP'],
    units: { phase: 'rad', coherency: 'amplitude_unit^2', stokes: 'amplitude_unit^2', eigenvalues: 'amplitude_unit^2', normalized_stokes: 'dimensionless', polarized_direction: 'dimensionless', degree_of_polarization: 'dimensionless' }, python_version: 'stub', numpy_version: 'stub' },
  limitations: ['Stub API.', 'No numerical reference.', 'No measured data.', 'No production acceptance.'] }; }
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(yes => { resolve = yes; }); return { promise, resolve }; }
function setup() { const calls: R03Envelope[] = []; let id = 0; const api: R03API = { async validate(s) { return validation(s); }, async simulate(s) { calls.push(s); return wire(s); } };
  const gate = new ClientOperationGate(), actor = new R03Controller({ ...R03_DEFAULT }, api, () => `12345678-1234-4234-8234-${(++id).toString(16).padStart(12, '0')}`, gate);
  return { calls, api, actor, gate }; }
describe('one independent ensemble actor and shared computation owner', () => {
  it('validation/view actions never compute; one explicit intent yields one immutable identity', async () => {
    const { actor, calls } = setup(); await actor.activate(); actor.select('qwp'); expect(calls).toHaveLength(0); await actor.simulate();
    expect(calls).toHaveLength(1); expect(actor.state.currentResult?.requestId).toBe(calls[0].request_id); expect(Object.isFrozen(calls[0].experiment)).toBe(true);
    actor.select('slm'); expect(calls).toHaveLength(1);
  });
  it('invalid text and underflow detach the mask immediately without fabricating zero', async () => {
    const { actor, calls } = setup(); await actor.activate(); await actor.simulate(); await actor.edit('source_amplitude', '1e-999');
    expect(actor.state.currentResult).toBeNull(); expect(actor.state.invalidEdits.source_amplitude).toBe('1e-999'); expect(actor.state.candidate.source_amplitude).toBe(1);
    expect(await actor.simulate()).toBe(false); expect(calls).toHaveLength(1);
  });
  it('edits during a pending calculation reject late attachment, without a second RNG/mask', async () => {
    const { actor, api, calls } = setup(), held = deferred<unknown>(), prepare = vi.fn(() => ({ commit() {}, dispose() {} }));
    api.simulate = async sent => { calls.push(sent); return held.promise; }; actor.setResultPreparer(prepare); await actor.activate(); const running = actor.simulate();
    await actor.edit('seed', '17'); held.resolve(wire(calls[0])); await running;
    expect(prepare, 'A_STALE_MASK').not.toHaveBeenCalled(); expect(actor.state.currentResult).toBeNull(); expect(actor.state.completedNumerical?.experiment.seed).toBe(20261017); expect(calls).toHaveLength(1);
    await actor.edit('seed', '20261017'); expect(actor.canRetryPresentation).toBe(false); expect(actor.retryPresentation()).toBe(false); expect(calls).toHaveLength(1);
  });
  it('workspace away/back is a new attachment epoch even when settings are equal', async () => {
    const { actor, api, calls } = setup(), held = deferred<unknown>(); api.simulate = async s => { calls.push(s); return held.promise; }; await actor.activate();
    const running = actor.simulate(); actor.deactivate(); await actor.activate(); held.resolve(wire(calls[0])); await running; expect(actor.state.currentResult).toBeNull(); expect(actor.gate.busy).toBe(false);
    expect(actor.canRetryPresentation).toBe(false); expect(actor.retryPresentation()).toBe(false);
  });
  it('display failure preserves completed science and prior display; manual recovery never resubmits', async () => {
    const { actor, calls } = setup(); let fail = false; const dispose = vi.fn(); actor.setResultPreparer(() => ({ commit() { if (fail) throw new Error('Controlled canvas failure'); }, dispose }));
    await actor.activate(); await actor.simulate(); const prior = actor.state.currentResult; fail = true; await actor.simulate();
    expect(actor.state.currentResult).toBe(prior); expect(actor.state.completedNumerical).not.toBe(prior); expect(actor.state.error).toBeNull(); expect(actor.state.renderError).toContain('canvas');
    fail = false; expect(actor.retryPresentation()).toBe(true); expect(calls).toHaveLength(2); expect(actor.state.currentResult).toBe(actor.state.completedNumerical);
  });
  it('rechecks state after preparation before any commit', async () => {
    const { actor } = setup(), commit = vi.fn(), dispose = vi.fn(); actor.setResultPreparer(() => { actor.deactivate(); return { commit, dispose }; });
    await actor.activate(); await actor.simulate(); expect(commit, 'A_ATOMIC_PREPARE_RECHECK').not.toHaveBeenCalled(); expect(dispose).toHaveBeenCalledOnce();
    expect(actor.state.active, 'A_ABORTED_PRESENTATION_SETTLES').toBeNull(); expect(actor.gate.busy).toBe(false); expect(actor.retryPresentation()).toBe(false);
    expect(actor.releaseResults()).toBe(true); actor.setResultPreparer(() => ({ commit() {}, dispose() {} })); await actor.activate(); expect(await actor.simulate()).toBe(true);
  });
  it('settles an intent when commit itself changes the attachment epoch', async () => {
    const { actor } = setup(), dispose = vi.fn(); actor.setResultPreparer(() => ({ commit() { actor.deactivate(); }, dispose }));
    await actor.activate(); await actor.simulate(); expect(dispose).toHaveBeenCalledOnce(); expect(actor.state.active).toBeNull();
    expect(actor.gate.busy).toBe(false); expect(actor.state.currentResult).toBeNull(); expect(actor.retryPresentation()).toBe(false);
  });
  it('renderer loss/restoration leaves only the eligible completed result manually recoverable', async () => {
    const { actor, calls } = setup(); await actor.activate(); await actor.simulate(); const result = actor.state.currentResult;
    actor.invalidatePresentation('WebGL context lost'); expect(actor.state.currentResult).toBeNull(); expect(actor.canRetryPresentation).toBe(true);
    actor.reportRenderFailure('Renderer restored; explicit presentation required'); expect(actor.retryPresentation()).toBe(true);
    expect(actor.state.currentResult).toBe(result); expect(calls).toHaveLength(1);
    actor.deactivate(); await actor.activate(); actor.reportRenderFailure('Renderer restored'); expect(actor.canRetryPresentation).toBe(false); expect(actor.retryPresentation()).toBe(false);
  });
  it.each([['sequential', 'single'], ['two_path', 'single'], ['two_path', 'sweep'], ['polarization', 'single'], ['polarization', 'sweep'], ['polarized_two_path', 'single'], ['polarized_two_path', 'sweep']] as const)('joins existing %s/%s client slot in both directions', async (owner, kind) => {
    const { actor, gate, calls, api } = setup(); await actor.activate(); expect(gate.acquire('legacy', owner, kind)).toBe(true); expect(await actor.simulate()).toBe(false); gate.release('legacy');
    const held = deferred<unknown>(); api.simulate = async s => { calls.push(s); return held.promise; }; const running = actor.simulate(); expect(gate.acquire('legacy', owner, kind)).toBe(false);
    expect(actor.releaseResults()).toBe(false); held.resolve(wire(calls[0])); await running; expect(gate.busy).toBe(false);
  });
  it('resource admission fails before a request and never evicts earlier results', async () => {
    const { actor, calls } = setup(); await actor.activate(); await actor.simulate(); const previous = actor.state.currentResult;
    actor.setOperationAdmission(() => { throw new Error('Owned budget exceeded'); }); expect(await actor.simulate()).toBe(false);
    expect(calls).toHaveLength(1); expect(actor.state.currentResult).toBe(previous); expect(actor.state.error).toContain('budget');
  });
  it('explicit release preserves draft, invalid text and selection; no replay', async () => {
    const { actor, calls } = setup(); await actor.activate(); await actor.simulate(); actor.select('hwp'); await actor.edit('phase_std_rad', 'bad');
    const before = actor.state; expect(actor.releaseResults()).toBe(true); expect(actor.state.candidate).toBe(before.candidate); expect(actor.state.invalidEdits).toBe(before.invalidEdits);
    expect(actor.state.selection).toBe('hwp'); expect(actor.state.completedNumerical).toBeNull(); expect(calls).toHaveLength(1);
  });
});
