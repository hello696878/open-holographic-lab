import { describe, expect, it, vi } from 'vitest';
import { cloneExperiment } from '../src/contracts';
import { buildWaveFieldSampling, createWaveFieldFetchAPI, decodeWaveFieldResult, estimateWaveFieldOperation, waveFieldOwnedResults,
  waveFieldPlan, waveFieldSection, W1_EXAMPLE, W1_MAX_RESPONSE_BYTES, type WaveFieldRequest } from '../src/wave_field_contracts';

/** Protocol fixture only, deliberately asymmetric; not evidence of optical propagation. */
function fixture(edit?: (header: any, intensity: number[]) => void) {
  const experiment = cloneExperiment(W1_EXAMPLE); experiment.grid = { nx: 4, ny: 3, dx: .1, dy: .2 };
  const request: WaveFieldRequest = { request_id: '11111111-1111-4111-8111-111111111111', experiment, sampling: { interior_z_m: [.015, .04, .1] } };
  const plan = waveFieldPlan(experiment, request.sampling), events = plan.filter(plane => plane.stage !== 'interior');
  const stages = events.map((plane, index) => { const norm = index < 2 ? 12 : 6, previous = index ? index < 3 ? 12 : 6 : null;
    return { selector: plane.stage, z_m: plane.z_m, norm, previous_norm: previous, delta_norm: previous === null ? null : norm - previous,
      transmission_ratio: previous === null ? null : norm / previous }; });
  const intensity = plan.flatMap((_plane, index) => Array.from({ length: 12 }, (_, pixel) => (index + 1) * .1 + pixel * .01));
  const planes = plan.map((plane, index) => { const event = stages.find(stage => stage.selector === plane.stage), anchor = stages.find(stage => stage.selector === plane.anchor_selector)!;
    const norm = event?.norm ?? anchor.norm, previous = event ? event.previous_norm : anchor.norm;
    return { ...plane, norm, previous_norm: previous, delta_norm: previous === null ? null : norm - previous,
      transmission_ratio: previous === null || previous === 0 ? null : norm / previous,
      on_axis_intensity: intensity[index * 12 + 6], max_intensity: intensity[index * 12 + 11] }; });
  const header = { protocol_version: 1, message_type: 'w1_wave_field', request_id: request.request_id, experiment_sha256: 'a'.repeat(64), experiment,
    sampling: request.sampling, ordered_section_ids: plan.map(plane => plane.id), planes, stages,
    arrays: [{ name: 'intensities', dtype: 'float64-le', order: 'C', shape: [plan.length, 3, 4], offset_bytes: 0, nbytes: intensity.length * 8, units: 'amplitude_unit^2' },
      { name: 'x_m', dtype: 'float64-le', order: 'C', shape: [4], offset_bytes: intensity.length * 8, nbytes: 32, units: 'm' },
      { name: 'y_m', dtype: 'float64-le', order: 'C', shape: [3], offset_bytes: intensity.length * 8 + 32, nbytes: 24, units: 'm' }] };
  edit?.(header, intensity);
  const json = new TextEncoder().encode(JSON.stringify(header)), offset = 16 + Math.ceil(json.length / 8) * 8;
  const frame = new ArrayBuffer(offset + 8 * (intensity.length + 7)), bytes = new Uint8Array(frame), view = new DataView(frame);
  bytes.set([79, 72, 76, 65, 66, 87, 70, 0]); view.setUint32(8, json.length, true); bytes.set(json, 16);
  [...intensity, ...Array.from({ length: 4 }, (_, i) => (i - 2) * .1), ...Array.from({ length: 3 }, (_, i) => (i - 1) * .2)]
    .forEach((value, index) => view.setFloat64(offset + index * 8, value, true));
  return { frame, request, intensity, header };
}
describe('W1 bounded exact transport', () => {
  it('allocates explicit 3/2/14 interiors and preserves six ordered event identities, even at co-located coordinates', () => {
    const sampling = buildWaveFieldSampling(W1_EXAMPLE); expect(sampling.interior_z_m).toHaveLength(19);
    expect(sampling.interior_z_m.filter(z => z < .03)).toHaveLength(3); expect(sampling.interior_z_m.filter(z => z > .03 && z < .06)).toHaveLength(2);
    const plan = waveFieldPlan(W1_EXAMPLE, sampling); expect(plan).toHaveLength(25);
    expect(plan.filter(plane => plane.z_m === .03).map(plane => plane.stage)).toEqual(['before:aperture', 'after:aperture']);
    const zero = cloneExperiment(W1_EXAMPLE); zero.components.forEach(component => component.z_m = 0); zero.observation.z_m = 0;
    expect(buildWaveFieldSampling(zero).interior_z_m).toEqual([]); expect(waveFieldPlan(zero, { interior_z_m: [] })).toHaveLength(6);
  });
  it('retains raw little-endian values, authoritative canonical norms and deduplicated borrowed section views', () => {
    const { frame, request, intensity } = fixture(), result = decodeWaveFieldResult(frame, request);
    expect(Array.from(result.intensities)).toEqual(intensity); expect(result.planes.at(-1)!.norm).toBe(6);
    expect(result.x).toEqual(Float64Array.from([-.2, -.1, 0, .1])); expect(result.y).toEqual(Float64Array.from([-.2, 0, .2]));
    expect(waveFieldSection(result, 1).buffer).toBe(result.intensities.buffer); expect(waveFieldSection(result, 1)[0]).toBe(intensity[12]);
    expect(waveFieldOwnedResults([result, result])).toBe(result.intensities.byteLength + 56 + 65536); expect(Object.isFrozen(result.experiment)).toBe(true);
    expect(() => waveFieldSection(result, -1)).toThrow('Unknown');
  });
  it.each([
    ['wrong discriminator', (h: any) => { h.message_type = 'v1'; }], ['wrong frozen settings', (h: any) => { h.experiment = { ...h.experiment, wavelength_m: 1e-6 }; }],
    ['collapsed colocated side', (h: any) => { h.ordered_section_ids[3] = h.ordered_section_ids[2]; }], ['wrong upstream anchor', (h: any) => { h.planes[4].anchor_selector = 'source'; }],
    ['wrong signed residual', (h: any) => { h.stages[2].delta_norm = 0; }], ['new unknown field', (h: any) => { h.planes[0].normalized = true; }],
    ['big-endian declaration', (h: any) => { h.arrays[0].dtype = 'float64-be'; }], ['overlapping arrays', (h: any) => { h.arrays[1].offset_bytes = 0; }],
    ['false maximum', (h: any) => { h.planes[0].max_intensity = 0; }], ['negative raw sample', (_h: any, values: number[]) => { values[0] = -1; }],
    ['nonfinite raw sample', (_h: any, values: number[]) => { values[0] = Infinity; }],
  ])('rejects %s before publication', (_name, edit) => { const { frame, request } = fixture(edit); expect(() => decodeWaveFieldResult(frame, request)).toThrow('W1 protocol'); });
  it('rejects partial/trailing/magic/padding frames and physical orientation corruption', () => {
    const { frame, request } = fixture(); expect(() => decodeWaveFieldResult(frame.slice(0, -1), request)).toThrow('length');
    const trailing = new Uint8Array(frame.byteLength + 1); trailing.set(new Uint8Array(frame)); expect(() => decodeWaveFieldResult(trailing.buffer, request)).toThrow('length');
    const wrong = frame.slice(0); new Uint8Array(wrong)[0] = 0; expect(() => decodeWaveFieldResult(wrong, request)).toThrow('magic');
    const axis = frame.slice(0), view = new DataView(axis); view.setFloat64(axis.byteLength - 8, -.2, true); expect(() => decodeWaveFieldResult(axis, request)).toThrow('y coordinate');
  });
  it('applies W1-only caps without mutating or resizing the existing draft and bounds allocation phases', () => {
    const over = cloneExperiment(W1_EXAMPLE); over.grid.nx = 129; const before = structuredClone(over);
    expect(() => buildWaveFieldSampling(over)).toThrow('≤128'); expect(over).toEqual(before);
    expect(() => waveFieldPlan(W1_EXAMPLE, { interior_z_m: [.03] })).toThrow('open');
    expect(() => waveFieldPlan(W1_EXAMPLE, { interior_z_m: [.01, .01] })).toThrow('distinct');
    const estimate = estimateWaveFieldOperation(W1_EXAMPLE); expect(estimate.payloadBytes).toBe(3276800 + 2048);
    expect(estimate.persistentBytes).toBeLessThanOrEqual(6 * 1024 * 1024); expect(estimate.frameBytes).toBeLessThanOrEqual(W1_MAX_RESPONSE_BYTES);
  });
  it('uses one bounded same-origin POST with no retry, queue, alternate endpoint or wrong MIME acceptance', async () => {
    const { frame, request } = fixture(), fetch = vi.fn(async (_url: string, _options?: RequestInit) => new Response(frame, { headers: { 'Content-Type': 'application/octet-stream' } }));
    const api = createWaveFieldFetchAPI(fetch as typeof globalThis.fetch); expect(await api.simulate(request)).toEqual(frame);
    expect(fetch).toHaveBeenCalledOnce(); expect(fetch.mock.calls[0][0]).toBe('/api/w1/simulate');
    const failed = vi.fn(async () => new Response('{}', { status: 503, headers: { 'Content-Type': 'application/json' } }));
    await expect(createWaveFieldFetchAPI(failed as typeof globalThis.fetch).simulate(request)).rejects.toThrow('HTTP 503'); expect(failed).toHaveBeenCalledOnce();
  });
});
