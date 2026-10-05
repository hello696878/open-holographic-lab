import { describe, expect, it, vi } from 'vitest';
import { createFetchAPI, decodeResult, MAX_HEADER_BYTES, MAX_RESPONSE_BYTES, parseStrictJSON,
  readBoundedResponse, validateValidationReply, type Experiment, type RequestEnvelope } from '../src/contracts';

const id = '12345678-1234-4234-8234-123456789abc';
const experiment: Experiment = {
  schema_version: 1, model_contract: 'v0_aligned_scalar_forward_v1', wavelength_m: 633e-9,
  grid: { ny: 3, nx: 4, dy: 5e-6, dx: 2e-6 },
  source: { kind: 'uniform', amplitude: 1, phase_rad: 0 }, components: [],
  observation: { id: 'screen', z_m: 0.02 },
};
const envelope: RequestEnvelope = { request_id: id, experiment };
// Independently specified small protocol fixture, not a production encoder.
function fixture(change?: (header: Record<string, any>) => void, textChange?: (text: string) => string): ArrayBuffer {
  const header = {
    protocol_version: 1, request_id: id, experiment_sha256: 'a'.repeat(64), experiment: structuredClone(experiment),
    stages: [
      { selector: 'source', z_m: 0, norm: 1, previous_norm: null, delta_norm: null, transmission_ratio: null },
      { selector: 'observation', z_m: 0.02, norm: 1, previous_norm: 1, delta_norm: 0, transmission_ratio: 1 },
    ],
    arrays: [
      { name: 'intensity', dtype: 'float64-le', order: 'C', shape: [3, 4], offset_bytes: 0, nbytes: 96, units: 'amplitude_unit^2' },
      { name: 'x_m', dtype: 'float64-le', order: 'C', shape: [4], offset_bytes: 96, nbytes: 32, units: 'm' },
      { name: 'y_m', dtype: 'float64-le', order: 'C', shape: [3], offset_bytes: 128, nbytes: 24, units: 'm' },
    ], intensity_max: 34,
  };
  change?.(header);
  const text = textChange?.(JSON.stringify(header)) ?? JSON.stringify(header);
  const bytes = new TextEncoder().encode(text);
  const start = 16 + Math.ceil(bytes.length / 8) * 8;
  const buffer = new ArrayBuffer(start + 152); const output = new Uint8Array(buffer); const view = new DataView(buffer);
  output.set([79, 72, 76, 65, 66, 86, 49, 0]);
  view.setUint32(8, bytes.length, true); view.setUint32(12, 0, true); output.set(bytes, 16);
  const numbers = [11, 12, 13, 14, 21, 22, 23, 24, 31, 32, 33, 34, -4e-6, -2e-6, 0, 2e-6, -5e-6, 0, 5e-6];
  numbers.forEach((value, index) => view.setFloat64(start + index * 8, value, true));
  return buffer;
}
function payloadStart(buffer: ArrayBuffer): number { return 16 + Math.ceil(new DataView(buffer).getUint32(8, true) / 8) * 8; }

describe('strict independent OHLABV1 fixture', () => {
  it('preserves original float64 values, coordinates, raw max and immutable echoed spec', () => {
    const buffer = fixture(); const decoded = decodeResult(buffer, envelope);
    expect([...decoded.intensity]).toEqual([11, 12, 13, 14, 21, 22, 23, 24, 31, 32, 33, 34]);
    expect([...decoded.x]).toEqual([-4e-6, -2e-6, 0, 2e-6]); expect([...decoded.y]).toEqual([-5e-6, 0, 5e-6]);
    expect(decoded.intensityMax).toBe(34); expect(decoded.stages[0].transmission_ratio).toBeNull();
    expect(Object.isFrozen(decoded.experiment.grid)).toBe(true);
    new DataView(buffer).setFloat64(payloadStart(buffer), 999, true);
    expect(decoded.intensity[0]).toBe(11);
  });
  it('does not replace V0 stage norms by a new intensity reduction', () => {
    const result = decodeResult(fixture(), envelope);
    expect(result.stages.at(-1)?.norm).toBe(1);
    expect(result.intensity.reduce((a, b) => a + b, 0) * 2e-6 * 5e-6).not.toBe(1);
  });
  it.each([
    ['version', (h: any) => { h.protocol_version = 2; }],
    ['identity', (h: any) => { h.request_id = '22345678-1234-4234-8234-123456789abc'; }],
    ['echo', (h: any) => { h.experiment.observation.z_m = 0.03; }],
    ['hash', (h: any) => { h.experiment_sha256 = 'not a hash'; }],
    ['unknown header key', (h: any) => { h.extra = 1; }],
    ['dtype', (h: any) => { h.arrays[0].dtype = 'float64'; }],
    ['order', (h: any) => { h.arrays[0].order = 'F'; }],
    ['shape', (h: any) => { h.arrays[0].shape = [4, 3]; }],
    ['units', (h: any) => { h.arrays[0].units = 'watts'; }],
    ['gap', (h: any) => { h.arrays[1].offset_bytes = 104; }],
    ['overlap', (h: any) => { h.arrays[1].offset_bytes = 88; }],
    ['alignment', (h: any) => { h.arrays[1].offset_bytes = 97; }],
    ['unsafe integer', (h: any) => { h.arrays[1].offset_bytes = Number.MAX_SAFE_INTEGER + 1; }],
    ['nbytes', (h: any) => { h.arrays[1].nbytes = 24; }],
    ['missing array', (h: any) => { h.arrays.pop(); }],
    ['max mismatch', (h: any) => { h.intensity_max = 35; }],
    ['stage chain', (h: any) => { h.stages[1].previous_norm = 2; }],
    ['stage selector', (h: any) => { h.stages[1].selector = 'source'; }],
    ['undefined ratio', (h: any) => { h.stages[0].transmission_ratio = 0; }],
    ['delta', (h: any) => { h.stages[1].delta_norm = 1; }],
  ])('rejects %s before returning a result', (_name, mutate) => {
    expect(() => decodeResult(fixture(mutate), envelope)).toThrow('V1 protocol');
  });
  it('rejects magic, reserved bytes, invalid UTF8, bounds, padding and trailing payload', () => {
    const magic = fixture(); new Uint8Array(magic)[0] = 0; expect(() => decodeResult(magic, envelope)).toThrow('magic');
    const reserved = fixture(); new DataView(reserved).setUint32(12, 1, true); expect(() => decodeResult(reserved, envelope)).toThrow('reserved');
    const utf8 = fixture(); new Uint8Array(utf8)[16] = 255; expect(() => decodeResult(utf8, envelope)).toThrow('UTF-8');
    const headerCap = fixture(); new DataView(headerCap).setUint32(8, MAX_HEADER_BYTES + 1, true);
    expect(() => decodeResult(headerCap, envelope)).toThrow('header length');
    const truncated = fixture().slice(0, 20); expect(() => decodeResult(truncated, envelope)).toThrow('truncated');
    const padded = fixture(undefined, text => text + ' '.repeat((1 - text.length % 8 + 8) % 8));
    const headerEnd = 16 + new DataView(padded).getUint32(8, true);
    expect(headerEnd).toBeLessThan(payloadStart(padded)); new Uint8Array(padded)[headerEnd] = 1;
    expect(() => decodeResult(padded, envelope)).toThrow('padding');
    const original = fixture(); const trailing = new Uint8Array(original.byteLength + 8); trailing.set(new Uint8Array(original));
    expect(() => decodeResult(trailing.buffer, envelope)).toThrow('trailing');
    expect(() => decodeResult(new ArrayBuffer(MAX_RESPONSE_BYTES + 1), envelope)).toThrow('length/cap');
  });
  it('rejects negative/nonfinite intensity and finite but wrong axes', () => {
    for (const bad of [-1, NaN, Infinity]) {
      const frame = fixture(); new DataView(frame).setFloat64(payloadStart(frame), bad, true);
      expect(() => decodeResult(frame, envelope)).toThrow('intensity');
    }
    const swapped = fixture(); new DataView(swapped).setFloat64(payloadStart(swapped) + 96, -5e-6, true);
    expect(() => decodeResult(swapped, envelope)).toThrow('coordinate mismatch');
  });
  it('preserves dark zeros and null zero-incident ratios', () => {
    const frame = fixture(h => {
      h.intensity_max = 0;
      h.stages = [
        { selector: 'source', z_m: 0, norm: 0, previous_norm: null, delta_norm: null, transmission_ratio: null },
        { selector: 'observation', z_m: 0.02, norm: 0, previous_norm: 0, delta_norm: 0, transmission_ratio: null },
      ];
    });
    new Uint8Array(frame, payloadStart(frame), 96).fill(0);
    const result = decodeResult(frame, envelope);
    expect(result.intensityMax).toBe(0); expect(result.stages[1].transmission_ratio).toBeNull();
    expect([...result.intensity].every(x => x === 0)).toBe(true);
  });
  it('rejects duplicate JSON keys, overflow numbers and JSON outside the header', () => {
    expect(() => decodeResult(fixture(undefined, text => text.replace('{', '{"protocol_version":1,')), envelope)).toThrow('duplicate');
    expect(() => parseStrictJSON('{"x":1e999}')).toThrow('finite');
    expect(() => parseStrictJSON('{"x":1} false')).toThrow('trailing');
    expect(() => parseStrictJSON('{"x":01}')).toThrow();
    expect(parseStrictJSON('{"s":"escaped \\\" quote","a":[true,false,null,-1.25e2]}')).toEqual({ s: 'escaped " quote', a: [true, false, null, -125] });
  });
  it('validation replies require full specification identity, not just HTTP200 or UUID', () => {
    const reply = { protocol_version: 1, request_id: id, experiment_sha256: 'a'.repeat(64), experiment };
    expect(validateValidationReply(reply, envelope).experiment).toEqual(experiment);
    expect(() => validateValidationReply({ ...reply, experiment: { ...experiment, wavelength_m: 532e-9 } }, envelope)).toThrow('echo');
  });
});

describe('bounded HTTP transport without retries', () => {
  it('cancels a streamed over-cap response even without Content-Length', async () => {
    const cancel = vi.fn();
    const response = new Response(new ReadableStream({ start(controller) { controller.enqueue(new Uint8Array(20)); }, cancel }));
    await expect(readBoundedResponse(response, 10)).rejects.toThrow('cap'); expect(cancel).toHaveBeenCalledOnce();
  });
  it('rejects declared mismatch and wrong MIME with one fetch only', async () => {
    await expect(readBoundedResponse(new Response('x', { headers: { 'Content-Length': '2' } }), 10)).rejects.toThrow('mismatch');
    const fetcher = vi.fn(async () => new Response('not binary', { headers: { 'Content-Type': 'text/html' } }));
    await expect(createFetchAPI(fetcher as typeof fetch).simulate(envelope)).rejects.toThrow('content-type');
    expect(fetcher).toHaveBeenCalledOnce();
  });
  it('releases bodies rejected by declared cap or MIME instead of retaining their streams', async () => {
    const declaredCancel = vi.fn();
    const response = new Response(new ReadableStream({ cancel: declaredCancel }), { headers: { 'Content-Length': '999' } });
    await expect(readBoundedResponse(response, 10)).rejects.toThrow('content-length/cap');
    expect(declaredCancel).toHaveBeenCalledOnce();
    const mimeCancel = vi.fn();
    const fetcher = vi.fn(async () => new Response(new ReadableStream({ cancel: mimeCancel }), { headers: { 'Content-Type': 'text/html' } }));
    await expect(createFetchAPI(fetcher as typeof fetch).simulate(envelope)).rejects.toThrow('content-type');
    expect(mimeCancel).toHaveBeenCalledOnce();
  });
  it('surfaces bounded HTTP failure without automatically replaying simulation', async () => {
    const fetcher = vi.fn(async () => new Response('{"protocol_version":1,"error":{"code":"busy","message":"worker is busy"}}',
      { status: 409, headers: { 'Content-Type': 'application/json' } }));
    await expect(createFetchAPI(fetcher as typeof fetch).simulate(envelope)).rejects.toThrow('HTTP 409: worker is busy');
    expect(fetcher).toHaveBeenCalledOnce();
  });
});
