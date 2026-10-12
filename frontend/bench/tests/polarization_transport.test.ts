import { describe, expect, it, vi } from 'vitest';
import { decodeResult, parseStrictJSON } from '../src/contracts';
import { assertPolarizationExperiment, createPolarizationFetchAPI, decodePolarizationResult, freezePolarizationExperiment,
  MAX_POLARIZATION_HEADER_BYTES, MAX_POLARIZATION_RESPONSE_BYTES, SWEEP_ANGLES_RAD, validatePolarizationReply, validatePolarizationSweep,
  type PolarizationEnvelope, type PolarizationExperiment, type PolarizationSweepEnvelope } from '../src/polarization_contracts';
const id = '12345678-1234-4234-8234-123456789abc';
const experiment: PolarizationExperiment = { schema_version: 1, model_contract: 'v2d_ideal_jones_same_plane_v1', wavelength_m: 633e-9,
  grid: { ny: 3, nx: 4, dy: 5e-6, dx: 2e-6 }, source: { kind: 'uniform', amplitude: 1, phase_rad: .37 },
  coefficients: { x: { re: 2, im: .3 }, y: { re: -.4, im: .8 } },
  elements: [{ id: 'p1', kind: 'linear_polarizer', axis_angle_rad: -.12345678901234567 }], readout: { row: 2, column: 3 } };
const envelope: PolarizationEnvelope = { protocol_version: 1, message_type: 'polarization_submission', request_id: id,
  experiment, experiment_sha256: 'a'.repeat(64) };
/** Asymmetric transport fixture; scalar diagnostics intentionally are not a JS optical calculation. */
function frame(change?: (header: any) => void, textChange?: (text: string) => string): ArrayBuffer {
  const { nx, ny, dx, dy } = experiment.grid, plane = nx * ny * 8;
  const incident = Array.from({ length: nx * ny }, (_, i) => 10 * (Math.floor(i / nx) + 1) + i % nx + 1), final = incident.map(value => value / 10);
  const header = { protocol_version: 1, message_type: 'polarization_result', request_id: id, experiment_sha256: envelope.experiment_sha256,
    experiment: structuredClone(experiment), ordered_stage_ids: ['input', 'p1'], stages: [
      { stage_id: 'input', kind: 'input', norm: 4, previous_norm: null, delta_norm: null, adjacent_transmission_ratio: null,
        incident_transmission_ratio: 1, sample: { x: { re: 2, im: 3 }, y: { re: -4, im: 5 } } },
      { stage_id: 'p1', kind: 'linear_polarizer', norm: 1, previous_norm: 4, delta_norm: -3, adjacent_transmission_ratio: .25,
        incident_transmission_ratio: .25, sample: { x: { re: .2, im: .3 }, y: { re: -.4, im: .5 } } },
    ], readout: { ...experiment.readout, x_m: 2e-6, y_m: 5e-6 }, arrays: [
      { name: 'incident_intensity', role: 'intensity', stage_id: 'input', dtype: 'float64-le', order: 'C', shape: [ny, nx], offset_bytes: 0, nbytes: plane, units: 'amplitude_unit^2' },
      { name: 'final_intensity', role: 'intensity', stage_id: 'p1', dtype: 'float64-le', order: 'C', shape: [ny, nx], offset_bytes: plane, nbytes: plane, units: 'amplitude_unit^2' },
      { name: 'x_m', role: 'coordinate', stage_id: null, dtype: 'float64-le', order: 'C', shape: [nx], offset_bytes: 2 * plane, nbytes: nx * 8, units: 'm' },
      { name: 'y_m', role: 'coordinate', stage_id: null, dtype: 'float64-le', order: 'C', shape: [ny], offset_bytes: 2 * plane + nx * 8, nbytes: ny * 8, units: 'm' },
    ], intensity_max: [34, 3.4] };
  change?.(header); const text = textChange?.(JSON.stringify(header)) ?? JSON.stringify(header);
  const encoded = new TextEncoder().encode(text), start = 16 + Math.ceil(encoded.length / 8) * 8;
  const bytes = new ArrayBuffer(start + 8 * (2 * nx * ny + nx + ny)), view = new DataView(bytes);
  new Uint8Array(bytes).set([79, 72, 76, 65, 66, 80, 76, 0]); view.setUint32(8, encoded.length, true); new Uint8Array(bytes).set(encoded, 16);
  [...incident, ...final, ...Array.from({ length: nx }, (_, c) => (c - Math.floor(nx / 2)) * dx),
    ...Array.from({ length: ny }, (_, r) => (r - Math.floor(ny / 2)) * dy)].forEach((value, i) => view.setFloat64(start + 8 * i, value, true));
  return bytes;
}
function sweepEnvelope(): PolarizationSweepEnvelope { return { ...envelope, message_type: 'polarization_sweep_submission', selected_element_id: 'p1', angles_rad: SWEEP_ANGLES_RAD }; }
function sweep(count = 13, http = 422): any {
  const single = decodePolarizationResult(frame(), envelope);
  const stages = single.stages.map(({ sample: _sample, ...stage }) => stage);
  return { protocol_version: 1, message_type: 'polarization_sweep_result', request_id: id, experiment_sha256: envelope.experiment_sha256,
    sweep_sha256: 'b'.repeat(64), experiment, selected_element_id: 'p1', angles_rad: SWEEP_ANGLES_RAD, ordered_stage_ids: ['input', 'p1'], requested_count: 13,
    status: count === 13 ? 'complete' : 'failed', completed_count: count, failed_index: count === 13 ? null : count,
    rows: SWEEP_ANGLES_RAD.slice(0, count).map((angle, index) => ({ index, axis_angle_rad: angle, stages, final_norm: 1, incident_transmission_ratio: .25, total_delta: -3 })),
    error: count === 13 ? null : { code: http === 422 ? 'numerical_failure' : 'sweep_failed', message: 'Actual computation failed' } };
}
describe('independent OHLABPL transport', () => {
  it('keeps ordered raw float64 data, actual complex pairs and selected physical sample identity', () => {
    const bytes = frame(), result = decodePolarizationResult(bytes, envelope);
    expect([...result.incidentIntensity]).toEqual([11, 12, 13, 14, 21, 22, 23, 24, 31, 32, 33, 34]);
    expect(result.finalIntensity[11]).toBe(3.4); expect([...result.x]).toEqual([-4e-6, -2e-6, 0, 2e-6]);
    expect(result.stages[1].sample, 'COMPONENT_SWAP_DETECTED').toEqual({ x: { re: .2, im: .3 }, y: { re: -.4, im: .5 } });
    expect(result.stages[1].sample.y.im, 'IMAGINARY_COMPONENT_DETECTED').toBe(.5);
    expect(result.readout, 'SAMPLE_IDENTITY_DETECTED').toEqual({ row: 2, column: 3, x_m: 2e-6, y_m: 5e-6 });
    expect(result.stages[0].norm).toBe(4); expect(result.stages[1].norm).toBe(1);
    expect(Object.isFrozen(result.stages[1].sample)).toBe(true); new Uint8Array(bytes).fill(0); expect(result.incidentIntensity[0]).toBe(11);
  });
  it.each([
    ['message type', (h: any) => { h.message_type = 'two_path_result'; }], ['version', (h: any) => { h.protocol_version = 2; }],
    ['UUID', (h: any) => { h.request_id = '22345678-1234-4234-8234-123456789abc'; }], ['known SHA', (h: any) => { h.experiment_sha256 = 'b'.repeat(64); }],
    ['full spec', (h: any) => { h.experiment.coefficients.x.re = 1; }], ['stage order', (h: any) => { h.ordered_stage_ids.reverse(); }],
    ['late stage', (h: any) => { h.stages[1].stage_id = 'p2'; }], ['input self ratio', (h: any) => { h.stages[0].incident_transmission_ratio = .5; }],
    ['nonfinite component', (h: any) => { h.stages[1].sample.y.im = null; }], ['sample index', (h: any) => { h.readout.row = 1; }],
    ['sample coordinate', (h: any) => { h.readout.x_m = 0; }], ['role', (h: any) => { h.arrays[0].role = 'coordinate'; }],
    ['stage descriptor', (h: any) => { h.arrays[1].stage_id = 'input'; }], ['dtype', (h: any) => { h.arrays[0].dtype = 'float32-le'; }],
    ['shape', (h: any) => { h.arrays[0].shape.reverse(); }], ['gap', (h: any) => { h.arrays[1].offset_bytes += 8; }],
    ['overlap', (h: any) => { h.arrays[1].offset_bytes -= 8; }], ['units', (h: any) => { h.arrays[0].units = 'watts'; }],
    ['max', (h: any) => { h.intensity_max[1] = 3; }], ['signed delta', (h: any) => { h.stages[1].delta_norm = 3; }],
    ['undefined ratio', (h: any) => { h.stages[0].adjacent_transmission_ratio = 1; }], ['extra', (h: any) => { h.extra = true; }],
  ])('rejects %s before any publication', (_name, change) => { let result = null;
    expect(() => { result = decodePolarizationResult(frame(change), envelope); }).toThrow('V2d protocol'); expect(result).toBeNull(); });
  it('fails closed on legacy magic, malformed JSON, UTF8, reserved/padding/trailing bytes and caps', () => {
    expect(() => decodeResult(frame(), { request_id: id, experiment: {} as any })).toThrow();
    const reserved = frame(); new DataView(reserved).setUint32(12, 1, true); expect(() => decodePolarizationResult(reserved, envelope)).toThrow('reserved');
    const utf8 = frame(); new Uint8Array(utf8)[16] = 255; expect(() => decodePolarizationResult(utf8, envelope)).toThrow('UTF-8');
    const legacy = frame(); new Uint8Array(legacy)[5] = 50; expect(() => decodePolarizationResult(legacy, envelope)).toThrow('magic');
    const trailing = new Uint8Array(frame().byteLength + 8); trailing.set(new Uint8Array(frame())); expect(() => decodePolarizationResult(trailing.buffer, envelope)).toThrow('trailing');
    expect(() => decodePolarizationResult(frame(undefined, text => text.replace('"protocol_version":1', '"protocol_version":1,"protocol_version":1')), envelope)).toThrow('duplicate');
    expect(() => decodePolarizationResult(new ArrayBuffer(MAX_POLARIZATION_RESPONSE_BYTES + 1), envelope)).toThrow('cap');
    const header = frame(); new DataView(header).setUint32(8, MAX_POLARIZATION_HEADER_BYTES + 1, true); expect(() => decodePolarizationResult(header, envelope)).toThrow('cap');
    const padding = frame(undefined, text => text + ' '); const length = new DataView(padding).getUint32(8, true);
    if (length % 8) { new Uint8Array(padding)[16 + length] = 1; expect(() => decodePolarizationResult(padding, envelope)).toThrow('padding'); }
    expect(() => parseStrictJSON('{"x":1e999}')).toThrow();
  });
  it('retains nonzero tiny selected sample even when its pixel intensity is zero', () => {
    const bytes = frame(h => { h.stages[1].sample = { x: { re: 1e-200, im: 0 }, y: { re: 0, im: 0 } }; h.intensity_max[1] = 3.3; });
    const start = 16 + Math.ceil(new DataView(bytes).getUint32(8, true) / 8) * 8;
    new DataView(bytes).setFloat64(start + 96 + 11 * 8, 0, true);
    const result = decodePolarizationResult(bytes, envelope); expect(result.stages[1].sample.x.re, 'DISPLAY_NONZERO_TINY_NOT_DARK').toBe(1e-200);
    expect(result.finalIntensity[11]).toBe(0); expect(result.stages[1].norm).toBe(1);
  });
  it('validates exact request shapes and canonicalizes only zero while retaining arbitrary coefficients', () => {
    const input = structuredClone(experiment); input.source.phase_rad = -0; input.elements[0].axis_angle_rad = -17.123456789012345;
    const result = freezePolarizationExperiment(input); expect(Object.is(result.source.phase_rad, -0)).toBe(false);
    expect(result.elements[0].axis_angle_rad, 'UNIT_AXIS_DETECTED').toBe(-17.123456789012345); expect(result.coefficients.x.re).toBe(2);
    expect(() => assertPolarizationExperiment({ ...input, source: { ...input.source, waist_z_m: 0 } })).toThrow('keys');
    expect(() => assertPolarizationExperiment({ ...input, readout: { row: true, column: 0 } })).toThrow();
    expect(() => validatePolarizationReply({ protocol_version: 1, message_type: 'polarization_validation', request_id: id,
      experiment_sha256: 'b'.repeat(64), experiment }, envelope)).toThrow('SHA');
    expect(() => decodePolarizationResult(frame(), { ...envelope, experiment_sha256: null })).toThrow('SHA');
  });
  it.each([0, 3, 12])('accepts only genuine contiguous %s-row numerical prefixes', count => {
    const result = validatePolarizationSweep(sweep(count), sweepEnvelope(), 422); expect(result.completedCount).toBe(count); expect(result.failedIndex).toBe(count);
    expect(result.rows.map(row => row.index)).toEqual(Array.from({ length: count }, (_, i) => i));
  });
  it('validates complete thirteen endpoints and rejects mismatched identities, fabricated rows and typed failures', () => {
    const result = validatePolarizationSweep(sweep(), sweepEnvelope(), 200); expect(result.rows).toHaveLength(13);
    expect(result.rows[0].axis_angle_rad).toBe(-Math.PI / 2); expect(result.rows[12].axis_angle_rad).toBe(Math.PI / 2);
    for (const change of [(s: any) => { s.selected_element_id = 'p2'; }, (s: any) => { s.experiment.readout = { row: 1, column: 2 }; },
      (s: any) => { s.rows[3].index = 4; }, (s: any) => { s.angles_rad = s.angles_rad.slice(1); }, (s: any) => { s.rows[0].total_delta = 3; }]) {
      const fixture = structuredClone(sweep()); change(fixture); expect(() => validatePolarizationSweep(fixture, sweepEnvelope(), 200)).toThrow();
    }
    const failed = sweep(3); failed.error.message = ''; expect(() => validatePolarizationSweep(failed, sweepEnvelope(), 422)).toThrow('bounded');
    expect(() => validatePolarizationSweep(sweep(3, 500), sweepEnvelope(), 422)).toThrow('kind');
  });
  it('uses exact bounded same-origin endpoints without retry and retains typed partial responses', async () => {
    const fetcher = vi.fn(async (_url: unknown, options: any) => new Response(JSON.stringify(sweep(3)), { status: 422, headers: { 'content-type': 'application/json' } }));
    const api = createPolarizationFetchAPI(fetcher as typeof fetch), reply = await api.sweep(sweepEnvelope());
    expect(reply.httpStatus).toBe(422); expect(fetcher).toHaveBeenCalledOnce(); expect(fetcher.mock.calls[0][0]).toBe('/api/v2d/sweep');
    expect(fetcher.mock.calls[0][1].redirect).toBe('error'); expect(fetcher.mock.calls[0][1].credentials).toBe('same-origin');
    const bad = createPolarizationFetchAPI(vi.fn(async () => new Response('bad', { headers: { 'content-type': 'text/html' } })) as typeof fetch);
    await expect(bad.simulate(envelope)).rejects.toThrow('content-type');
  });
});
