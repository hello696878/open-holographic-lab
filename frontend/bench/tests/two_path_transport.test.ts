import { describe, expect, it, vi } from 'vitest';
import { decodeResult, type Experiment } from '../src/contracts';
import { createTwoPathFetchAPI, decodeTwoPathResult, fixedTwoPathExperiment, freezeTwoPathExperiment,
  MAX_TWO_PATH_HEADER_BYTES, MAX_TWO_PATH_RESPONSE_BYTES, SWEEP_PHASES_RAD, validateTwoPathSweep,
  type TwoPathEnvelope, type TwoPathExperiment, type TwoPathSweepEnvelope } from '../src/two_path_contracts';

const id = '12345678-1234-4234-8234-123456789abc';
const experiment: TwoPathExperiment = { wavelength_m: 633e-9, grid: { ny: 3, nx: 4, dy: 5e-6, dx: 2e-6 },
  source: { kind: 'uniform', amplitude: 1, phase_rad: 0 },
  two_arm_spec: { arm_0_distance_m: .002, arm_1_distance_m: .003, relative_phase_rad: .37 } };
const envelope: TwoPathEnvelope = { protocol_version: 1, message_type: 'two_path_submission', request_id: id, experiment };
/** Independent asymmetrical bytes, deliberately not an optical solver or production encoder. */
function frame(change?: (header: any) => void, textChange?: (text: string) => string, submitted = envelope): ArrayBuffer {
  const { nx, ny, dx, dy } = submitted.experiment.grid;
  const plane = nx * ny * 8;
  const a = Array.from({ length: nx * ny }, (_, i) => 10 * (Math.floor(i / nx) + 1) + i % nx + 1);
  const b = a.map(value => value + 90);
  const header = { protocol_version: 1, message_type: 'two_path_result', request_id: submitted.request_id,
    experiment_sha256: 'a'.repeat(64), experiment: submitted.experiment, ports: ['port_0', 'port_1'],
    norms: { inputs: [8, 0], split: [4, 4], propagated: [3, 2], combiner: [3, 2], outputs: [4, 1] },
    diagnostics: { inputs_total: 8, split_total: 8, propagated_total: 5, combiner_total: 5, outputs_total: 5,
      split_delta: 0, propagation_delta: -3, phase_delta: 0, recombination_delta: 0, total_delta: -3,
      output_fractions: [.5, .125], total_output_ratio: .625 },
    arrays: [
      { name: 'intensity_port_0', role: 'intensity', port_id: 'port_0', dtype: 'float64-le', order: 'C', shape: [ny, nx], offset_bytes: 0, nbytes: plane, units: 'amplitude_unit^2' },
      { name: 'intensity_port_1', role: 'intensity', port_id: 'port_1', dtype: 'float64-le', order: 'C', shape: [ny, nx], offset_bytes: plane, nbytes: plane, units: 'amplitude_unit^2' },
      { name: 'x_m', role: 'coordinate', port_id: null, dtype: 'float64-le', order: 'C', shape: [nx], offset_bytes: 2 * plane, nbytes: nx * 8, units: 'm' },
      { name: 'y_m', role: 'coordinate', port_id: null, dtype: 'float64-le', order: 'C', shape: [ny], offset_bytes: 2 * plane + nx * 8, nbytes: ny * 8, units: 'm' },
    ], intensity_max: [Math.max(...a), Math.max(...b)] };
  change?.(header);
  const text = textChange?.(JSON.stringify(header)) ?? JSON.stringify(header);
  const encoded = new TextEncoder().encode(text); const start = 16 + Math.ceil(encoded.length / 8) * 8;
  const result = new ArrayBuffer(start + 8 * (2 * nx * ny + nx + ny)); const bytes = new Uint8Array(result); const view = new DataView(result);
  bytes.set([79, 72, 76, 65, 66, 50, 80, 0]); view.setUint32(8, encoded.length, true); bytes.set(encoded, 16);
  const values = [...a, ...b, ...Array.from({ length: nx }, (_, c) => (c - Math.floor(nx / 2)) * dx),
    ...Array.from({ length: ny }, (_, r) => (r - Math.floor(ny / 2)) * dy)];
  values.forEach((value, i) => view.setFloat64(start + 8 * i, value, true));
  return result;
}
const payloadStart = (bytes: ArrayBuffer) => 16 + Math.ceil(new DataView(bytes).getUint32(8, true) / 8) * 8;
function sweepEnvelope(): TwoPathSweepEnvelope {
  return { protocol_version: 1, message_type: 'two_path_sweep_submission', request_id: id,
    fixed_experiment: fixedTwoPathExperiment(experiment), phases_rad: SWEEP_PHASES_RAD };
}
function sweep(count = 17) {
  return { protocol_version: 1, message_type: 'two_path_sweep_result', request_id: id, fixed_experiment_sha256: 'b'.repeat(64),
    fixed_experiment: sweepEnvelope().fixed_experiment, phases_rad: [...SWEEP_PHASES_RAD], status: count === 17 ? 'complete' : 'failed',
    requested_count: 17, completed_count: count, failed_index: count === 17 ? null : count,
    rows: SWEEP_PHASES_RAD.slice(0, count).map((phase, index) => ({ index, phase_rad: phase, input_norm: 8,
      output_norms: [4, 1], output_fractions: [.5, .125], total_output_ratio: .625,
      split_delta: 0, propagation_delta: -3, phase_delta: 0, recombination_delta: 0, total_delta: -3 })),
    error: count === 17 ? null : { code: 'numerical_failure', message: 'Failed at requested point' } };
}

describe('independent ordered OHLAB2P framing', () => {
  it('decodes distinct asymmetric ports, owned float64 axes, raw maxima and retained original norms', () => {
    const bytes = frame(); const decoded = decodeTwoPathResult(bytes, envelope);
    expect([...decoded.ports[0].intensity]).toEqual([11, 12, 13, 14, 21, 22, 23, 24, 31, 32, 33, 34]);
    expect([...decoded.ports[1].intensity]).toEqual([101, 102, 103, 104, 111, 112, 113, 114, 121, 122, 123, 124]);
    expect(decoded.ports.map(port => [port.id, port.intensityMax])).toEqual([['port_0', 34], ['port_1', 124]]);
    expect([...decoded.x]).toEqual([-4e-6, -2e-6, 0, 2e-6]); expect([...decoded.y]).toEqual([-5e-6, 0, 5e-6]);
    expect(decoded.norms.outputs).toEqual([4, 1]); expect(decoded.diagnostics.output_fractions).toEqual([.5, .125]);
    expect(decoded.ports[0].intensity.reduce((a, b) => a + b, 0) * experiment.grid.dx * experiment.grid.dy).not.toBe(4);
    new DataView(bytes).setFloat64(payloadStart(bytes), 999, true); expect(decoded.ports[0].intensity[0]).toBe(11);
    expect(Object.isFrozen(decoded.experiment.two_arm_spec)).toBe(true);
  });
  it.each([
    ['type', (h: any) => { h.message_type = 'two_path_validation'; }],
    ['version', (h: any) => { h.protocol_version = 2; }],
    ['identity', (h: any) => { h.request_id = '22345678-1234-4234-8234-123456789abc'; }],
    ['echo', (h: any) => { h.experiment = { ...h.experiment, wavelength_m: 532e-9 }; }],
    ['port order', (h: any) => { h.ports.reverse(); }],
    ['port descriptor', (h: any) => { h.arrays[1].port_id = 'port_0'; }],
    ['duplicate output role', (h: any) => { h.arrays[1].name = 'intensity_port_0'; }],
    ['role', (h: any) => { h.arrays[0].role = 'coordinate'; }],
    ['dtype', (h: any) => { h.arrays[0].dtype = 'float32-le'; }],
    ['shape', (h: any) => { h.arrays[1].shape = [4, 3]; }],
    ['gap', (h: any) => { h.arrays[1].offset_bytes += 8; }],
    ['overlap', (h: any) => { h.arrays[1].offset_bytes -= 8; }],
    ['units', (h: any) => { h.arrays[0].units = 'watts'; }],
    ['max', (h: any) => { h.intensity_max[1] = 123; }],
    ['surviving denominator', (h: any) => { h.diagnostics.output_fractions = [.8, .2]; }],
    ['signed delta', (h: any) => { h.diagnostics.propagation_delta = 3; }],
    ['extra', (h: any) => { h.extra = true; }],
  ])('rejects %s before returning either output', (_name, mutate) => {
    expect(() => decodeTwoPathResult(frame(mutate), envelope)).toThrow('V2b protocol');
  });
  it('rejects malformed second array without partial publication, nonfinite values, coordinates and trailing bytes', () => {
    let result = null;
    const broken = frame(); new DataView(broken).setFloat64(payloadStart(broken) + 96, NaN, true);
    expect(() => { result = decodeTwoPathResult(broken, envelope); }).toThrow('intensity_port_1'); expect(result).toBeNull();
    const badAxis = frame(); new DataView(badAxis).setFloat64(payloadStart(badAxis) + 192, -5e-6, true);
    expect(() => decodeTwoPathResult(badAxis, envelope)).toThrow('x coordinate');
    const original = frame(); const trailing = new Uint8Array(original.byteLength + 1); trailing.set(new Uint8Array(original));
    expect(() => decodeTwoPathResult(trailing.buffer, envelope)).toThrow('trailing');
    expect(() => decodeTwoPathResult(frame(undefined, text => text.replace('"protocol_version":1', '"protocol_version":1,"protocol_version":1')), envelope)).toThrow('duplicate');
    expect(() => decodeTwoPathResult(frame(undefined, text => text.replace('"wavelength_m":6.33e-7', '"wavelength_m":1e999')), envelope)).toThrow();
  });
  it('rejects reserved bytes, truncated header, padding, caps and invalid UTF8', () => {
    const reserved = frame(); new DataView(reserved).setUint32(12, 1, true); expect(() => decodeTwoPathResult(reserved, envelope)).toThrow('reserved');
    const huge = frame(); new DataView(huge).setUint32(8, MAX_TWO_PATH_HEADER_BYTES + 1, true); expect(() => decodeTwoPathResult(huge, envelope)).toThrow('header');
    const text = frame(); new Uint8Array(text)[16] = 255; expect(() => decodeTwoPathResult(text, envelope)).toThrow('UTF-8');
    expect(() => decodeTwoPathResult(frame().slice(0, 20), envelope)).toThrow('truncated');
    const padded = frame(undefined, text => text + ' '.repeat((1 - text.length % 8 + 8) % 8));
    new Uint8Array(padded)[16 + new DataView(padded).getUint32(8, true)] = 1;
    expect(() => decodeTwoPathResult(padded, envelope)).toThrow('padding');
    expect(() => decodeTwoPathResult(new ArrayBuffer(MAX_TWO_PATH_RESPONSE_BYTES + 1), envelope)).toThrow('cap');
  });
  it('keeps legacy and two-path frames mutually ineligible and derives the exact 512 cap', () => {
    const legacy: Experiment = { schema_version: 1, model_contract: 'v0_aligned_scalar_forward_v1',
      wavelength_m: experiment.wavelength_m, grid: experiment.grid, source: experiment.source, components: [], observation: { id: 'screen', z_m: 0 } };
    expect(() => decodeResult(frame(), { request_id: id, experiment: legacy })).toThrow('magic');
    const oldMagic = frame(); new Uint8Array(oldMagic).set([79, 72, 76, 65, 66, 86, 49, 0]);
    expect(() => decodeTwoPathResult(oldMagic, envelope)).toThrow('magic');
    expect(16 + MAX_TWO_PATH_HEADER_BYTES + 8 * (2 * 512 * 512 + 512 + 512)).toBe(MAX_TWO_PATH_RESPONSE_BYTES);
  });
});

describe('browser canonicalization and genuine scalar sweep wire', () => {
  it('canonicalizes browser source and relative -0 before identity while preserving signed nonzero phases', () => {
    const input = structuredClone(experiment); input.source.phase_rad = -0; input.two_arm_spec.relative_phase_rad = -0;
    const canonical = freezeTwoPathExperiment(input);
    expect(Object.is(canonical.source.phase_rad, +0)).toBe(true); expect(Object.is(canonical.two_arm_spec.relative_phase_rad, +0)).toBe(true);
    const negative = -17.123456789012345; input.two_arm_spec.relative_phase_rad = negative;
    expect(freezeTwoPathExperiment(input).two_arm_spec.relative_phase_rad).toBe(negative);
    expect(Object.is(input.source.phase_rad, -0)).toBe(true);
  });
  it('keeps distinct actual endpoints and exact contiguous scalar rows with no images', () => {
    const reply = validateTwoPathSweep(sweep(), sweepEnvelope(), 200);
    expect(reply.rows).toHaveLength(17); expect(reply.rows[0].phase_rad).toBe(0); expect(reply.rows[16].phase_rad).toBe(2 * Math.PI);
    expect(reply.fixedExperiment).not.toHaveProperty('relative_phase_rad'); expect(reply.status).toBe('complete');
  });
  it.each([422, 500])('retains a genuine failed prefix only with non2xx HTTP %s', status => {
    const reply = validateTwoPathSweep(sweep(3), sweepEnvelope(), status);
    expect(reply.status).toBe('failed'); expect(reply.completedCount).toBe(3); expect(reply.failedIndex).toBe(3);
    expect(reply.rows.map(row => row.index)).toEqual([0, 1, 2]);
    expect(() => validateTwoPathSweep(sweep(3), sweepEnvelope(), 200)).toThrow('failed sweep');
  });
  it.each([
    (s: any) => { s.rows[1].index = 2; }, (s: any) => { s.rows[1].phase_rad = 0; },
    (s: any) => { s.rows[1].output_fractions = [.8, .2]; }, (s: any) => { s.requested_count = 16; },
    (s: any) => { s.phases_rad.pop(); }, (s: any) => { s.fixed_experiment.arm_0_distance_m = .004; },
    (s: any) => { s.rows[0].array = [1, 2]; }, (s: any) => { s.error = { code: 'bad', message: 'x'.repeat(301) }; },
  ])('rejects a malformed/changed sweep before publication', mutate => {
    const reply = structuredClone(sweep()); mutate(reply); expect(() => validateTwoPathSweep(reply, sweepEnvelope(), 200)).toThrow('V2b protocol');
  });
  it('reads failed-sweep prefixes on422, rejects oversized/wrongMIME bodies and never retries', async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify(sweep(3)), { status: 422, headers: { 'Content-Type': 'application/json' } }));
    const reply = await createTwoPathFetchAPI(fetcher as typeof fetch).sweep(sweepEnvelope());
    expect(validateTwoPathSweep(reply.body, sweepEnvelope(), reply.httpStatus).completedCount).toBe(3); expect(fetcher).toHaveBeenCalledOnce();
    const wrong = vi.fn(async () => new Response('x', { headers: { 'Content-Type': 'text/html' } }));
    await expect(createTwoPathFetchAPI(wrong as typeof fetch).simulate(envelope)).rejects.toThrow('content-type'); expect(wrong).toHaveBeenCalledOnce();
  });
});
