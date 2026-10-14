import { describe, expect, it, vi } from 'vitest';
import { parseStrictJSON } from '../src/contracts';
import { polarizedTwoPathPreset } from '../src/polarized_two_path_presets';
import { assertPolarizedTwoPathExperiment, createPolarizedTwoPathFetchAPI, decodePolarizedTwoPathResult,
  fixedPolarizedTwoPathExperiment, freezePolarizedTwoPathExperiment, parsePolarizedTwoPathJSON, SWEEP_PHASES_RAD,
  validatePolarizedTwoPathReply, validatePolarizedTwoPathSweep, validatePolarizedTwoPathSweepReply,
  MAX_POLARIZED_TWO_PATH_RESPONSE_BYTES, MAX_POLARIZED_TWO_PATH_DISABLED_RESPONSE_BYTES,
  type PolarizedTwoPathEnvelope, type PolarizedTwoPathExperiment, type PolarizedTwoPathSweepEnvelope } from '../src/polarized_two_path_contracts';
const id = '12345678-1234-4234-8234-123456789abc', digest = 'a'.repeat(64), sweepDigest = 'b'.repeat(64);
function experiment(enabled = true, n = 0): PolarizedTwoPathExperiment { const value = polarizedTwoPathPreset('orthogonal_analyzed');
  value.analyzer.enabled = enabled; value.analyzer.axis_angle_rad = -7.123456789012345;
  value.grid = n ? { ny: n, nx: n, dy: 5e-6, dx: 2e-6 } : { ny: 3, nx: 4, dy: 5e-6, dx: 2e-6 }; return value; }
function envelope(enabled = true, n = 0): PolarizedTwoPathEnvelope { return { protocol_version: 1, message_type: 'polarized_two_path_submission', request_id: id, experiment_sha256: digest, experiment: experiment(enabled, n) }; }
/** Asymmetric wire fixture, not an optical calculation or a numerical correctness reference. */
function scalar(experiment: PolarizedTwoPathExperiment): any {
  const norms = { inputs: [4, 0], split: [2, 2], propagated: [1.8, 1.9], elements: [1.8, 1.9], combiner: [1.8, 1.9], outputs: [2, 1.7],
    arm_action_norms: [experiment.arm_0.actions.map(() => 1.8), experiment.arm_1.actions.map(() => 1.9)] };
  const totals = Object.fromEntries(['inputs', 'split', 'propagated', 'elements', 'combiner', 'outputs'].map(key => [`${key}_total`, norms[key as keyof typeof norms].reduce((a: any, b: any) => a + b, 0)]));
  const diagnostics = { ...totals, split_delta: totals.split_total - totals.inputs_total, propagation_delta: totals.propagated_total - totals.split_total,
    elements_delta: totals.elements_total - totals.propagated_total, phase_delta: totals.combiner_total - totals.elements_total,
    recombination_delta: totals.outputs_total - totals.combiner_total, total_delta: totals.outputs_total - totals.inputs_total,
    propagation_deltas: [-.19999999999999996, -.10000000000000009], element_deltas: [0, 0], phase_deltas: [0, 0],
    arm_action_deltas: [experiment.arm_0.actions.map(() => 0), experiment.arm_1.actions.map(() => 0)], output_fractions: [.5, .425], total_output_ratio: .925 };
  const analysis = experiment.analyzer.enabled ? { enabled: true, axis_angle_rad: experiment.analyzer.axis_angle_rad,
    ports: [{ id: 'port_0', raw_norm: 2, analyzed_norm: 1, removed_norm: 1, original_input_ratio: .25, raw_output_ratio: .5 },
      { id: 'port_1', raw_norm: 1.7, analyzed_norm: .85, removed_norm: .85, original_input_ratio: .2125, raw_output_ratio: .5 }],
    total_norm: 1.85, total_removed_norm: 1.85, total_original_input_ratio: .25 + .2125 }
    : { enabled: false, axis_angle_rad: experiment.analyzer.axis_angle_rad, ports: null, total_norm: null, total_removed_norm: null, total_original_input_ratio: null };
  return { norms, diagnostics, analysis };
}
function frame(sent = envelope(), change?: (header: any) => void, textChange?: (text: string) => string): ArrayBuffer {
  const { nx, ny, dx, dy } = sent.experiment.grid, count = sent.experiment.analyzer.enabled ? 4 : 2, plane = nx * ny * 8;
  const images = Array.from({ length: count }, (_, role) => Array.from({ length: nx * ny }, (_, i) => (role + 1) * (10 * (Math.floor(i / nx) + 1) + i % nx + 1)));
  const arrays: any[] = images.map((_, i) => ({ name: `${i < 2 ? 'raw' : 'analyzed'}_port_${i % 2}_intensity`, role: 'intensity',
    port_id: `port_${i % 2}`, state: i < 2 ? 'raw' : 'analyzed', dtype: 'float64-le', order: 'C', shape: [ny, nx], offset_bytes: i * plane, nbytes: plane, units: 'amplitude_unit^2' }));
  arrays.push({ name: 'x_m', role: 'coordinate', port_id: null, state: null, dtype: 'float64-le', order: 'C', shape: [nx], offset_bytes: count * plane, nbytes: nx * 8, units: 'm' },
    { name: 'y_m', role: 'coordinate', port_id: null, state: null, dtype: 'float64-le', order: 'C', shape: [ny], offset_bytes: count * plane + nx * 8, nbytes: ny * 8, units: 'm' });
  const header = { protocol_version: 1, message_type: 'polarized_two_path_result', request_id: sent.request_id, experiment_sha256: sent.experiment_sha256,
    experiment: structuredClone(sent.experiment), ...scalar(sent.experiment), arrays, intensity_max: images.map(image => Math.max(...image)) };
  change?.(header); const encoded = new TextEncoder().encode(textChange?.(JSON.stringify(header)) ?? JSON.stringify(header)), start = 16 + Math.ceil(encoded.length / 8) * 8;
  const bytes = new ArrayBuffer(start + 8 * (count * nx * ny + nx + ny)), view = new DataView(bytes);
  new Uint8Array(bytes).set([79, 72, 76, 65, 66, 80, 84, 0]); view.setUint32(8, encoded.length, true); new Uint8Array(bytes).set(encoded, 16);
  [...images.flat(), ...Array.from({ length: nx }, (_, c) => (c - Math.floor(nx / 2)) * dx), ...Array.from({ length: ny }, (_, r) => (r - Math.floor(ny / 2)) * dy)].forEach((value, i) => view.setFloat64(start + 8 * i, value, true)); return bytes;
}
function sweepEnvelope(): PolarizedTwoPathSweepEnvelope { return { protocol_version: 1, message_type: 'polarized_two_path_sweep_submission', request_id: id,
  fixed_experiment_sha256: digest, fixed_experiment: fixedPolarizedTwoPathExperiment(experiment()), phases_rad: SWEEP_PHASES_RAD }; }
function sweep(count = 17, status = 422): any { const sent = sweepEnvelope(); return { protocol_version: 1, message_type: 'polarized_two_path_sweep', request_id: id,
  fixed_experiment_sha256: digest, sweep_sha256: sweepDigest, fixed_experiment: sent.fixed_experiment, phases_rad: SWEEP_PHASES_RAD, status: count === 17 ? 'complete' : 'failed',
  requested_count: 17, completed_count: count, failed_index: count === 17 ? null : count, rows: SWEEP_PHASES_RAD.slice(0, count).map((phase_rad, index) => ({ index, phase_rad, ...scalar(experiment()) })),
  error: count === 17 ? null : { code: status === 422 ? 'numerical_failure' : 'sweep_failed', message: 'Actual requested measurement failed' } }; }
describe('closed OHLABPT conditional transport', () => {
  it.each([false, true])('owns all actual ordered roles with analyzer enabled=%s', enabled => {
    const sent = envelope(enabled), bytes = frame(sent), result = decodePolarizedTwoPathResult(bytes, sent);
    expect(result.rawPorts[0].intensity[11], 'PT_ROLE_SWAP_DETECTED').toBe(34); expect(result.rawPorts[1].intensity[11]).toBe(68);
    expect(result.analyzedPorts?.[0].intensity[11] ?? null).toBe(enabled ? 102 : null); expect(result.intensityMax).toEqual(enabled ? [34, 68, 102, 136] : [34, 68]);
    expect(result.analysis.enabled).toBe(enabled); expect(result.analysis.axis_angle_rad).toBe(sent.experiment.analyzer.axis_angle_rad);
    expect([...result.x]).toEqual([-4e-6, -2e-6, 0, 2e-6]); expect([...result.y]).toEqual([-5e-6, 0, 5e-6]);
    new Uint8Array(bytes).fill(0); expect(result.rawPorts[0].intensity[0]).toBe(11); expect(Object.isFrozen(result.norms.arm_action_norms)).toBe(true);
  });
  it.each([
    ['version', (h: any) => { h.protocol_version = 2; }], ['mode', (h: any) => { h.message_type = 'two_path_result'; }],
    ['identity', (h: any) => { h.request_id = '22345678-1234-4234-8234-123456789abc'; }], ['hash', (h: any) => { h.experiment_sha256 = sweepDigest; }],
    ['coefficient', (h: any) => { h.experiment.coefficients.x.re = 2; }], ['disabledangle', (h: any) => { h.analysis.axis_angle_rad = 0; }],
    ['selfdescribedanalysis', (h: any) => { h.analysis.enabled = false; }], ['role order', (h: any) => { [h.arrays[0], h.arrays[1]] = [h.arrays[1], h.arrays[0]]; }],
    ['analysis role', (h: any) => { h.arrays[2].state = 'raw'; }], ['missing role', (h: any) => { h.arrays.splice(3, 1); }],
    ['dtype', (h: any) => { h.arrays[0].dtype = 'float32-le'; }], ['shape', (h: any) => { h.arrays[0].shape.reverse(); }],
    ['offset', (h: any) => { h.arrays[1].offset_bytes += 8; }], ['length', (h: any) => { h.arrays[0].nbytes -= 8; }],
    ['units', (h: any) => { h.arrays[0].units = 'watts'; }], ['maximum', (h: any) => { h.intensity_max[0] = 33; }],
    ['history', (h: any) => { h.norms.arm_action_norms[1] = []; }], ['history endpoint', (h: any) => { h.norms.arm_action_norms[1][0] = 1; }],
    ['delta', (h: any) => { h.diagnostics.total_delta = 0; }], ['armdelta', (h: any) => { h.diagnostics.propagation_deltas[0] = .2; }],
    ['actiondelta', (h: any) => { h.diagnostics.arm_action_deltas[1][0] = 1; }], ['undefined ratio', (h: any) => { h.diagnostics.output_fractions[0] = null; }],
    ['raw norm', (h: any) => { h.analysis.ports[1].raw_norm = 1; }], ['loss', (h: any) => { h.analysis.ports[1].removed_norm = 0; }],
    ['erased positive ratio', (h: any) => { h.diagnostics.output_fractions[0] = 0; }],
    ['port order', (h: any) => { h.analysis.ports.reverse(); }], ['analysis total', (h: any) => { h.analysis.total_norm = 2; }],
    ['extra', (h: any) => { h.extra = true; }],
  ])('rejects %s before attaching any outcome', (_name, change) => { let attached = null; expect(() => { attached = decodePolarizedTwoPathResult(frame(envelope(), change), envelope()); }).toThrow('V2g protocol'); expect(attached).toBeNull(); });
  it('rejects analysis invented on a disabled request and nonfinite/negative payloads', () => {
    const sent = envelope(false); expect(() => decodePolarizedTwoPathResult(frame(sent, h => { h.analysis.ports = []; }), sent)).toThrow('disabled');
    for (const bad of [NaN, Infinity, -1]) { const bytes = frame(); const start = 16 + Math.ceil(new DataView(bytes).getUint32(8, true) / 8) * 8;
      new DataView(bytes).setFloat64(start, bad, true); expect(() => decodePolarizedTwoPathResult(bytes, envelope())).toThrow(); }
  });
  it('retains null zero-input ratios and exact zero-numerator public ratios', () => {
    const zero = frame(envelope(), h => {
      for (const key of ['inputs', 'split', 'propagated', 'elements', 'combiner', 'outputs']) h.norms[key] = [0, 0]; h.norms.arm_action_norms = [[], [0]];
      for (const key of Object.keys(h.diagnostics)) { if (key === 'arm_action_deltas') h.diagnostics[key] = [[], [0]];
        else if (key === 'output_fractions') h.diagnostics[key] = [null, null]; else if (key === 'total_output_ratio') h.diagnostics[key] = null;
        else if (Array.isArray(h.diagnostics[key])) h.diagnostics[key] = [0, 0]; else h.diagnostics[key] = 0; }
      h.analysis.ports.forEach((p: any) => { p.raw_norm = p.analyzed_norm = p.removed_norm = 0; p.original_input_ratio = p.raw_output_ratio = null; });
      h.analysis.total_norm = h.analysis.total_removed_norm = 0; h.analysis.total_original_input_ratio = null; h.intensity_max = [0, 0, 0, 0];
    });
    const start = 16 + Math.ceil(new DataView(zero).getUint32(8, true) / 8) * 8; new Uint8Array(zero).fill(0, start, start + 4 * 12 * 8);
    const result = decodePolarizedTwoPathResult(zero, envelope()); expect(result.diagnostics.output_fractions).toEqual([null, null]); expect(result.analysis.total_original_input_ratio).toBeNull();
    const sent = envelope(false), dark = frame(sent, h => { h.norms.outputs = [0, 1.7]; h.diagnostics.outputs_total = 1.7;
      h.diagnostics.recombination_delta = 1.7 - h.diagnostics.combiner_total; h.diagnostics.total_delta = 1.7 - h.diagnostics.inputs_total;
      h.diagnostics.output_fractions = [0, .425]; h.diagnostics.total_output_ratio = .425; });
    expect(decodePolarizedTwoPathResult(dark, sent).diagnostics.output_fractions[0]).toBe(0);
    expect(() => decodePolarizedTwoPathResult(frame(sent, h => { h.norms.outputs[0] = 0; h.diagnostics.outputs_total = 1.7;
      h.diagnostics.recombination_delta = 1.7 - h.diagnostics.combiner_total; h.diagnostics.total_delta = 1.7 - h.diagnostics.inputs_total;
      h.diagnostics.total_output_ratio = .425; }), sent)).toThrow('ratio domain');
  });
  it('derives framing caps, strict padding, exact length and canonical axes', () => {
    for (const enabled of [false, true]) { const sent = envelope(enabled, 128), bytes = frame(sent), header = new DataView(bytes).getUint32(8, true), payload = 8 * ((enabled ? 4 : 2) * 128 ** 2 + 256);
      expect(payload).toBe(enabled ? 526336 : 264192); expect(bytes.byteLength).toBe(16 + Math.ceil(header / 8) * 8 + payload);
      expect(16 + 16384 + payload).toBe(enabled ? MAX_POLARIZED_TWO_PATH_RESPONSE_BYTES : MAX_POLARIZED_TWO_PATH_DISABLED_RESPONSE_BYTES); }
    const reserved = frame(); new DataView(reserved).setUint32(12, 1, true); expect(() => decodePolarizedTwoPathResult(reserved, envelope())).toThrow('reserved');
    const magic = frame(); new Uint8Array(magic)[6] = 76; expect(() => decodePolarizedTwoPathResult(magic, envelope())).toThrow('magic');
    const utf = frame(); new Uint8Array(utf)[16] = 255; expect(() => decodePolarizedTwoPathResult(utf, envelope())).toThrow('UTF-8');
    const extra = new Uint8Array(frame().byteLength + 8); extra.set(new Uint8Array(frame())); expect(() => decodePolarizedTwoPathResult(extra.buffer, envelope())).toThrow('length');
    const padding = frame(envelope(), undefined, text => text + ' '); const length = new DataView(padding).getUint32(8, true);
    if (length % 8) { new Uint8Array(padding)[16 + length] = 1; expect(() => decodePolarizedTwoPathResult(padding, envelope())).toThrow('padding'); }
    const axis = frame(), start = 16 + Math.ceil(new DataView(axis).getUint32(8, true) / 8) * 8; new DataView(axis).setFloat64(start + 4 * 12 * 8, 0, true); expect(() => decodePolarizedTwoPathResult(axis, envelope())).toThrow('coordinate');
    expect(() => decodePolarizedTwoPathResult(frame(envelope(), undefined, text => text.replace('"protocol_version":1', '"protocol_version":1,"protocol_version":1')), envelope())).toThrow('duplicate');
    expect(() => decodePolarizedTwoPathResult(new ArrayBuffer(MAX_POLARIZED_TWO_PATH_RESPONSE_BYTES + 1), envelope())).toThrow('cap');
  });
  it('retains complete Gaussian and unwrapped coefficients/phases while canonicalizing only zero', () => {
    const value = experiment(false); value.source = { kind: 'gaussian', amplitude: 2.3, phase_rad: -31, waist_radius_m: 40e-6, waist_z_m: -.001, center_x_m: 3e-6, center_y_m: -4e-6 };
    value.coefficients.x.re = 2.3; value.coefficients.y.im = Number.MIN_VALUE; value.relative_phase_rad = -17.123456789012345;
    value.arm_0.distance_m = -0; const frozen = freezePolarizedTwoPathExperiment(value); assertPolarizedTwoPathExperiment(frozen);
    expect(Object.is(frozen.arm_0.distance_m, -0)).toBe(false); expect(frozen.coefficients.y.im).toBe(Number.MIN_VALUE);
    expect(frozen.source).toEqual(value.source); expect(frozen.relative_phase_rad).toBe(value.relative_phase_rad);
    for (const mutation of [(x: any) => { x.arm_0.actions = [{ id: 'hwp1', kind: 'linear_polarizer', axis_angle_rad: 0 }]; },
      (x: any) => { x.arm_1.actions[0].id = 'input'; }, (x: any) => { x.arm_0.distance_m = -1; }, (x: any) => { x.analyzer.enabled = 1; },
      (x: any) => { x.analyzer.axis_angle_rad = NaN; }, (x: any) => { delete x.source.waist_z_m; }, (x: any) => { x.grid.nx = 129; }]) {
      const broken = structuredClone(value); mutation(broken); expect(() => assertPolarizedTwoPathExperiment(broken)).toThrow(); }
  });
  it('adds nonzero-decimal underflow rejection locally without changing the old parser', () => {
    expect(parseStrictJSON('{"x":1e-999}')).toEqual({ x: 0 }); expect(() => parsePolarizedTwoPathJSON('{"x":1e-999}')).toThrow('underflow');
    expect(parsePolarizedTwoPathJSON('{"x":0e-999,"text":"1e-999","tiny":5e-324}')).toEqual({ x: 0, text: '1e-999', tiny: Number.MIN_VALUE });
  });
  it.each([0, 8, 16])('retains genuine contiguous %s-row prefixes including supplementary error scalars', count => {
    const body = sweep(count); body.error.message = '😀'.repeat(300); const result = validatePolarizedTwoPathSweep(body, sweepEnvelope(), 422, sweepDigest);
    expect(result.completedCount).toBe(count); expect(result.failedIndex).toBe(count); expect(result.rows.map(row => row.index)).toEqual(Array.from({ length: count }, (_, i) => i));
  });
  it('validates distinct sweep validation, complete endpoints, actual rows and digest binding', () => {
    const body = sweep(), sent = sweepEnvelope(), reply = { protocol_version: 1, message_type: 'polarized_two_path_sweep_validation', request_id: id,
      fixed_experiment_sha256: digest, fixed_experiment: sent.fixed_experiment, phases_rad: SWEEP_PHASES_RAD, sweep_sha256: sweepDigest };
    expect(validatePolarizedTwoPathSweepReply(reply, { ...sent, fixed_experiment_sha256: null }).sweep_sha256).toBe(sweepDigest);
    const result = validatePolarizedTwoPathSweep(body, sent, 200, sweepDigest); expect(result.rows).toHaveLength(17); expect(result.rows[0].phase_rad).toBe(0); expect(result.rows[16].phase_rad).toBe(2 * Math.PI);
    for (const mutation of [(x: any) => { x.rows[8].index = 9; }, (x: any) => { x.rows[16].phase_rad = 0; }, (x: any) => { x.phases_rad = x.phases_rad.slice(1); },
      (x: any) => { x.fixed_experiment.analyzer.axis_angle_rad = 0; }, (x: any) => { x.sweep_sha256 = 'c'.repeat(64); }, (x: any) => { x.rows[3].analysis.ports.reverse(); }]) {
      const broken = structuredClone(body); mutation(broken); expect(() => validatePolarizedTwoPathSweep(broken, sent, 200, sweepDigest), 'PT_SWEEP_FABRICATION_DETECTED').toThrow(); }
    expect(() => validatePolarizedTwoPathSweep(sweep(8, 500), sent, 422)).toThrow('kind');
    expect(() => validatePolarizedTwoPathReply({ protocol_version: 1, message_type: 'polarized_two_path_validation', request_id: id, experiment_sha256: sweepDigest, experiment: experiment() }, envelope())).toThrow('SHA');
  });
  it('uses only bounded same-origin endpoints with no retry and preserves partial HTTP status', async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify(sweep(8)), { status: 422, headers: { 'content-type': 'application/json' } }));
    const response = await createPolarizedTwoPathFetchAPI(fetcher as typeof fetch).sweep(sweepEnvelope());
    expect(response.httpStatus).toBe(422); expect(fetcher).toHaveBeenCalledOnce(); const options = fetcher.mock.calls as unknown as [string, RequestInit][];
    expect(options[0][0]).toBe('/api/v2g/sweep'); expect(options[0][1].redirect).toBe('error'); expect(options[0][1].credentials).toBe('same-origin');
    await expect(createPolarizedTwoPathFetchAPI(async () => new Response('wrong', { headers: { 'content-type': 'text/html' } })).simulate(envelope())).rejects.toThrow('content-type');
  });
});
