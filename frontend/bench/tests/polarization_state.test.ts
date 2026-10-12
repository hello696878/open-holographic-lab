import { describe, expect, it, vi } from 'vitest';
import { ClientOperationGate } from '../src/state';
import { PolarizationController } from '../src/polarization_state';
import { polarizationPreset } from '../src/polarization_presets';
import { SWEEP_ANGLES_RAD, type PolarizationAPI, type PolarizationEnvelope, type PolarizationSweepEnvelope, type PolarizationValidation } from '../src/polarization_contracts';
const base = polarizationPreset('analyzer'); base.grid = { ny: 1, nx: 2, dy: 3e-6, dx: 2e-6 }; base.readout = { row: 0, column: 1 };
function ids() { let i = 0; return () => `12345678-1234-4234-8234-${String(++i).padStart(12, '0')}`; }
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; }
function validation(envelope: PolarizationEnvelope): PolarizationValidation { return { protocol_version: 1, message_type: 'polarization_validation',
  request_id: envelope.request_id, experiment_sha256: 'a'.repeat(64), experiment: structuredClone(envelope.experiment) }; }
function stages(envelope: PolarizationEnvelope) {
  return ['input', ...envelope.experiment.elements.map(item => item.id)].map((id, index) => ({ stage_id: id,
    kind: index === 0 ? 'input' : envelope.experiment.elements[index - 1].kind, norm: 1, previous_norm: index === 0 ? null : 1,
    delta_norm: index === 0 ? null : 0, adjacent_transmission_ratio: index === 0 ? null : 1, incident_transmission_ratio: 1 }));
}
/** Independent state fixture, not a JavaScript optical computation. */
function frame(envelope: PolarizationEnvelope): ArrayBuffer {
  const { nx, ny, dx, dy } = envelope.experiment.grid, plane = nx * ny * 8, ordered = ['input', ...envelope.experiment.elements.map(item => item.id)];
  const header = { protocol_version: 1, message_type: 'polarization_result', request_id: envelope.request_id, experiment_sha256: 'a'.repeat(64),
    experiment: envelope.experiment, ordered_stage_ids: ordered, stages: stages(envelope).map(stage => ({ ...stage, sample: { x: { re: 1, im: .3 }, y: { re: -.4, im: .5 } } })),
    readout: { ...envelope.experiment.readout, x_m: (envelope.experiment.readout.column - Math.floor(nx / 2)) * dx, y_m: (envelope.experiment.readout.row - Math.floor(ny / 2)) * dy },
    arrays: [
      { name: 'incident_intensity', role: 'intensity', stage_id: 'input', dtype: 'float64-le', order: 'C', shape: [ny, nx], offset_bytes: 0, nbytes: plane, units: 'amplitude_unit^2' },
      { name: 'final_intensity', role: 'intensity', stage_id: ordered.at(-1), dtype: 'float64-le', order: 'C', shape: [ny, nx], offset_bytes: plane, nbytes: plane, units: 'amplitude_unit^2' },
      { name: 'x_m', role: 'coordinate', stage_id: null, dtype: 'float64-le', order: 'C', shape: [nx], offset_bytes: 2 * plane, nbytes: nx * 8, units: 'm' },
      { name: 'y_m', role: 'coordinate', stage_id: null, dtype: 'float64-le', order: 'C', shape: [ny], offset_bytes: 2 * plane + nx * 8, nbytes: ny * 8, units: 'm' },
    ], intensity_max: [1, .5] };
  const text = new TextEncoder().encode(JSON.stringify(header)), start = 16 + Math.ceil(text.length / 8) * 8;
  const bytes = new ArrayBuffer(start + 8 * (2 * nx * ny + nx + ny)), view = new DataView(bytes);
  new Uint8Array(bytes).set([79, 72, 76, 65, 66, 80, 76, 0]); view.setUint32(8, text.length, true); new Uint8Array(bytes).set(text, 16);
  const values = [...Array(nx * ny).fill(1), ...Array(nx * ny).fill(.5), ...Array.from({ length: nx }, (_, c) => (c - Math.floor(nx / 2)) * dx), ...Array.from({ length: ny }, (_, r) => (r - Math.floor(ny / 2)) * dy)];
  values.forEach((value, i) => view.setFloat64(start + 8 * i, value, true)); return bytes;
}
function sweep(envelope: PolarizationSweepEnvelope, count = 13) { return { protocol_version: 1, message_type: 'polarization_sweep_result',
  request_id: envelope.request_id, experiment_sha256: envelope.experiment_sha256, sweep_sha256: 'b'.repeat(64), experiment: envelope.experiment,
  selected_element_id: envelope.selected_element_id, angles_rad: envelope.angles_rad, ordered_stage_ids: ['input', ...envelope.experiment.elements.map(item => item.id)],
  requested_count: 13, completed_count: count, failed_index: count === 13 ? null : count, status: count === 13 ? 'complete' : 'failed',
  rows: SWEEP_ANGLES_RAD.slice(0, count).map((angle, index) => ({ index, axis_angle_rad: angle, stages: stages({ ...envelope, message_type: 'polarization_submission' }),
    final_norm: 1, incident_transmission_ratio: 1, total_delta: 0 })), error: count === 13 ? null : { code: 'numerical_failure', message: 'Actual point failed' } }; }
function immediate() {
  const validations: PolarizationEnvelope[] = [], singles: PolarizationEnvelope[] = [], sweeps: PolarizationSweepEnvelope[] = [];
  const api: PolarizationAPI = { async validate(envelope) { validations.push(envelope); return validation(envelope); },
    async simulate(envelope) { singles.push(envelope); return frame(envelope); },
    async sweep(envelope) { sweeps.push(envelope); return { body: sweep(envelope), httpStatus: 200 }; } };
  return { api, validations, singles, sweeps };
}
describe('explicit polarization operation actor', () => {
  it('keeps authoritative signed radians and arbitrary coefficients, invalidates on invalid text without computing', async () => {
    const { api, singles, validations } = immediate(), actor = new PolarizationController(base, api, ids());
    await actor.edit('elements.0.axis_angle_rad', '-17.123456789012345'); await actor.edit('coefficients.x.re', '2');
    await actor.edit('coefficients.y.im', '-0'); expect(Object.is(actor.state.candidate.coefficients.y.im, -0)).toBe(false);
    expect(actor.state.candidate.elements[0].axis_angle_rad, 'UNIT_AXIS_DETECTED').toBe(-17.123456789012345);
    await actor.simulate(); expect(singles[0].experiment.coefficients.x.re).toBe(2); expect(singles[0].experiment_sha256).toBe('a'.repeat(64));
    const count = validations.length, old = actor.state.lastResult; await actor.edit('readout.row', '-');
    expect(actor.state.currentResult).toBeNull(); expect(actor.state.lastResult).toBe(old); expect(validations).toHaveLength(count); expect(await actor.simulate()).toBe(false);
  });
  it('initial validation and viewing stage/selection/errors never compute or revalidate', async () => {
    const { api, singles, sweeps, validations } = immediate(), actor = new PolarizationController(base, api, ids());
    await actor.validateInitial(); await actor.validateInitial(); await actor.simulate(); actor.select('p1'); actor.selectStage('p1'); actor.reportRenderFailure('context lost'); actor.reportRenderFailure(null);
    expect(validations, 'VIEW_ACTION_NO_OPTICS').toHaveLength(1); expect(singles, 'VIEW_ACTION_NO_OPTICS').toHaveLength(1); expect(sweeps, 'VIEW_ACTION_NO_OPTICS').toHaveLength(0);
  });
  it('acquires the actual shared slot synchronously and rejects rapid duplicates across all modes', async () => {
    const { api, singles } = immediate(), held = deferred<ArrayBuffer>(); api.simulate = envelope => { singles.push(envelope); return held.promise; };
    const gate = new ClientOperationGate(), actor = new PolarizationController(base, api, ids(), gate); await actor.validateInitial();
    const first = actor.simulate(); expect(await actor.simulate(), 'DUPLICATE_OPERATION_DETECTED').toBe(false);
    expect(singles, 'DUPLICATE_OPERATION_DETECTED').toHaveLength(1); expect(gate.acquire('other', 'two_path', 'sweep')).toBe(false);
    held.resolve(frame(singles[0])); expect(await first).toBe(true); expect(gate.busy).toBe(false);
    expect(singles, 'DUPLICATE_OPERATION_DETECTED').toHaveLength(1);
  });
  it('away-and-back generation rejects late attachment and leaves the gate held until settlement', async () => {
    const { api, singles } = immediate(), held = deferred<ArrayBuffer>(); api.simulate = envelope => { singles.push(envelope); return held.promise; };
    const actor = new PolarizationController(base, api, ids()), prepare = vi.fn(() => ({ commit() {}, dispose() {} })); actor.setResultPreparer(prepare);
    await actor.validateInitial(); const running = actor.simulate(); actor.deactivate(); await actor.activate();
    expect(actor.gate.busy).toBe(true); held.resolve(frame(singles[0])); await running;
    expect(actor.state.currentResult, 'CROSS_MODE_STALE_DETECTED').toBeNull(); expect(prepare, 'CROSS_MODE_STALE_DETECTED').not.toHaveBeenCalled();
    expect(actor.state.lastResult?.requestId).toBe(singles[0].request_id); expect(actor.gate.busy).toBe(false);
  });
  it('new sample edit cannot relabel held or earlier completed complex samples', async () => {
    const { api, singles } = immediate(), held = deferred<ArrayBuffer>(); api.simulate = envelope => { singles.push(envelope); return held.promise; };
    const actor = new PolarizationController(base, api, ids()); await actor.validateInitial(); const running = actor.simulate();
    await actor.edit('readout.column', '0', true); held.resolve(frame(singles[0])); await running;
    expect(actor.state.currentResult, 'SAMPLE_IDENTITY_DETECTED').toBeNull(); expect(actor.state.lastResult?.readout.column, 'SAMPLE_IDENTITY_DETECTED').toBe(1);
    expect(actor.state.candidate.readout.column).toBe(0);
  });
  it('rejects obsolete validations after invalid edits and deactivation', async () => {
    const { api } = immediate(), held = deferred<PolarizationValidation>(); let sent: PolarizationEnvelope | undefined;
    api.validate = envelope => { sent = envelope; return held.promise; }; const actor = new PolarizationController(base, api, ids());
    const pending = actor.validateInitial(); actor.deactivate(); await actor.edit('coefficients.x.re', ''); held.resolve(validation(sent!)); await pending;
    expect(actor.state.validatedDraft).toBeNull(); expect(actor.state.pendingValidation).toBe(false);
  });
  it('keeps prior complete presentation atomic on later failure and retries only display explicitly', async () => {
    const { api, singles } = immediate(), actor = new PolarizationController(base, api, ids()); let fail = false;
    const commits = vi.fn(), disposals = vi.fn(); actor.setResultPreparer(() => ({ commit() { if (fail) throw new Error('later presentation resource'); commits(); }, dispose: disposals }));
    await actor.validateInitial(); await actor.simulate(); const prior = actor.state.currentResult; fail = true; await actor.simulate();
    expect(actor.state.currentResult, 'ATOMIC_LATE_RESOURCE_DETECTED').toBe(prior); expect(actor.state.lastResult).toBe(prior);
    expect(actor.state.completedNumerical?.requestId).not.toBe(prior?.requestId); expect(disposals).toHaveBeenCalledOnce(); expect(singles).toHaveLength(2);
    fail = false; expect(actor.retryPresentation()).toBe(true); expect(singles, 'VIEW_ACTION_NO_OPTICS').toHaveLength(2); expect(actor.state.currentResult).toBe(actor.state.completedNumerical);
  });
  it('malformed response is numerical/transport failure with explicit recovery and no automatic retry', async () => {
    const { api, singles } = immediate(); let bad = true; api.simulate = async envelope => { singles.push(envelope); return bad ? new ArrayBuffer(3) : frame(envelope); };
    const actor = new PolarizationController(base, api, ids()); await actor.validateInitial(); expect(await actor.simulate()).toBe(false);
    expect(actor.state.lastResult).toBeNull(); expect(singles).toHaveLength(1); bad = false; expect(await actor.simulate()).toBe(true); expect(singles).toHaveLength(2);
  });
  it('sweep freezes full ordered spec and selecting rows is passive, applying is a separate one-run intent', async () => {
    const { api, singles, sweeps } = immediate(), actor = new PolarizationController(base, api, ids()); await actor.validateInitial(); actor.select('p1');
    expect(await actor.runSweep()).toBe(true); expect(sweeps).toHaveLength(1); expect(sweeps[0].angles_rad).toEqual(SWEEP_ANGLES_RAD);
    actor.selectSweepPoint(3); expect(singles).toHaveLength(0); expect(sweeps).toHaveLength(1);
    expect(await actor.applySelectedAngleAndSimulate()).toBe(true); expect(singles).toHaveLength(1);
    expect(singles[0].experiment.elements[0].axis_angle_rad).toBe(SWEEP_ANGLES_RAD[3]); expect(actor.state.lastSweep?.experiment.elements[0].axis_angle_rad).toBe(0);
  });
  it('invalid/nonpolarizer/empty selection sends no sweep and failed rows remain visibly partial', async () => {
    const { api, sweeps } = immediate(), actor = new PolarizationController(base, api, ids()); await actor.validateInitial(); expect(await actor.runSweep()).toBe(false); expect(sweeps).toHaveLength(0);
    actor.select('p1'); api.sweep = async envelope => { sweeps.push(envelope); return { body: sweep(envelope, 3), httpStatus: 422 }; };
    expect(await actor.runSweep()).toBe(false); expect(actor.state.lastSweep?.rows).toHaveLength(3); expect(actor.state.error).toContain('FAILED / PARTIAL');
    await actor.replaceCandidate({ ...base, elements: [] }); expect(await actor.runSweep()).toBe(false); expect(sweeps).toHaveLength(1);
  });
  it('admission failure occurs before any operation request and selection leaves the specification unchanged', async () => {
    const { api, singles, sweeps } = immediate(), actor = new PolarizationController(base, api, ids()); await actor.validateInitial(); const before = actor.state.candidate;
    actor.select('p1'); expect(actor.state.candidate).toBe(before); actor.setOperationAdmission(() => { throw new Error('owned budget'); });
    expect(await actor.simulate()).toBe(false); expect(await actor.runSweep()).toBe(false); expect(singles).toHaveLength(0); expect(sweeps).toHaveLength(0);
  });
});
