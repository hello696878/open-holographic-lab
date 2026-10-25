import { describe, expect, it } from 'vitest';
import { createW2ResponseCapture, type W2CaptureIdentity } from './support/w2_response_capture';

const id = '60000000-0000-4000-8000-000000000001';
const scene = { model_contract: 'w2_ideal_geometric_routing_v1', source: { origin_m: [0, 0, 0] }, elements: [] };
const identity: W2CaptureIdentity = { contextId: 'context', pageId: 'page', token: 'token', sceneSha256: 'a'.repeat(64), scene, requestId: id };
const request = { request_id: id, scene_sha256: identity.sceneSha256, scene };
const body = { protocol_version: 1, message_type: 'trace_result', model_contract: scene.model_contract, ...request };
const args = ['/api/w2/trace', { method: 'POST', body: JSON.stringify(request) }] as const;
function fixture(response = new Response(JSON.stringify(body))) {
  const promise = Promise.resolve(response); let calls = 0;
  const capture = createW2ResponseCapture((() => { ++calls; return promise; }) as typeof fetch, { contextId: 'context', pageId: 'page' });
  capture.arm(identity); return { capture, promise, calls: () => calls };
}
describe('bounded original W2 response capture instrumentation', () => {
  it('configures W3 exact endpoint model message and cap without changing original-fetch ownership', async () => {
    const w3scene = { ...scene, model_contract: 'w3_ideal_refractive_routing_v1' }, w3request = { ...request, scene: w3scene };
    const body = { protocol_version: 1, message_type: 'refractive_trace_result', model_contract: w3scene.model_contract, ...w3request };
    const promise = Promise.resolve(new Response(JSON.stringify(body))); let count = 0;
    const c = createW2ResponseCapture((() => { ++count; return promise; }) as typeof fetch, { contextId: 'context', pageId: 'page' },
      { endpoint: '/api/w3/trace', modelContract: w3scene.model_contract, messageType: 'refractive_trace_result', cap: 4096 });
    c.arm({ ...identity, scene: w3scene });
    expect(c.fetch('/api/w3/trace', { method: 'POST', body: JSON.stringify(w3request) })).toBe(promise);
    expect(Buffer.from((await c.consume('token')).base64, 'base64').toString()).toBe(JSON.stringify(body));
    expect(count).toBe(1); expect(c.snapshot()).toMatchObject({ traceCount: 1, cloneCount: 1, bytesOwned: 0 }); c.dispose();
  });
  it('leaves nonselected endpoints untouched and rejects W3 message/model and configured byte overflow', async () => {
    const w3scene = { ...scene, model_contract: 'w3_ideal_refractive_routing_v1' }, w3request = { ...request, scene: w3scene };
    for (const fault of ['model', 'message', 'cap']) {
      const response = new Response(JSON.stringify({ ...body, ...w3request, model_contract: fault === 'model' ? 'wrong' : w3scene.model_contract, message_type: fault === 'message' ? 'trace_result' : 'refractive_trace_result' }));
      const promise = Promise.resolve(response); let calls = 0;
      const c = createW2ResponseCapture((() => { ++calls; return promise; }) as typeof fetch, { contextId: 'context', pageId: 'page' },
        { endpoint: '/api/w3/trace', modelContract: w3scene.model_contract, messageType: 'refractive_trace_result', cap: fault === 'cap' ? 2 : 4096 });
      expect(c.fetch(...args)).toBe(promise); expect(c.snapshot().traceCount).toBe(0);
      c.arm({ ...identity, scene: w3scene }); c.fetch('/api/w3/trace', { method: 'POST', body: JSON.stringify(w3request) });
      await expect(c.consume('token')).rejects.toThrow(fault === 'cap' ? 'size exceeds cap' : 'identity');
      expect(calls).toBe(2); expect((await promise).status).toBe(200); c.dispose();
    }
  });
  it('returns the exact original Promise, invokes fetch once and consumes exact bytes once', async () => {
    const x = fixture(); expect(x.capture.fetch(...args)).toBe(x.promise);
    const record = await x.capture.consume('token'); expect(x.calls()).toBe(1);
    expect(Buffer.from(record.base64, 'base64').toString()).toBe(JSON.stringify(body));
    expect(record.request).toEqual(request); expect(x.capture.snapshot()).toMatchObject({ bytesOwned: 0, occupied: false, cloneCount: 1 });
    await expect(x.capture.consume('token')).rejects.toThrow('already consumed'); x.capture.dispose();
  });
  it('rejects a wrong page, duplicate arm and missing capture without fetching', async () => {
    const x = fixture(); expect(() => x.capture.arm(identity)).toThrow('not available');
    await expect(x.capture.consume('token')).rejects.toThrow('Missing'); expect(x.calls()).toBe(0); x.capture.dispose();
    expect(() => x.capture.arm({ ...identity, pageId: 'wrong' })).toThrow();
    const y = createW2ResponseCapture(fetch, { contextId: 'different', pageId: 'page' });
    expect(() => y.arm(identity)).toThrow('owner'); y.dispose();
  });
  it('rejects an identity fault without replacing the app response', async () => {
    const x = fixture(new Response(JSON.stringify({ ...body, request_id: 'wrong' })));
    const original = x.capture.fetch(...args); expect(original).toBe(x.promise);
    await expect(x.capture.consume('token')).rejects.toThrow('identity');
    expect((await original).status).toBe(200); expect(x.calls()).toBe(1); x.capture.dispose();
  });
  it('rejects a mismatched original request and never makes a substitute request', async () => {
    const x = fixture(); x.capture.fetch(args[0], { ...args[1], body: JSON.stringify({ ...request, scene_sha256: 'b'.repeat(64) }) });
    await expect(x.capture.consume('token')).rejects.toThrow('request identity'); expect(x.calls()).toBe(1); x.capture.dispose();
  });
  it('rejects declared and streaming oversize separately', async () => {
    for (const response of [new Response('{}', { headers: { 'content-length': '524289' } }), new Response('x'.repeat(524289))]) {
      const x = fixture(response); x.capture.fetch(...args);
      await expect(x.capture.consume('token')).rejects.toThrow('size exceeds cap'); expect(x.calls()).toBe(1);
      // The original branch is still readable and was not consumed by capture.
      expect((await (await x.promise).arrayBuffer()).byteLength).toBe(response.headers.has('content-length') ? 2 : 524289);
      x.capture.dispose();
    }
  });
  it('rejects truncated original bytes, bad UTF8 and malformed JSON', async () => {
    for (const response of [new Response('{}', { headers: { 'content-length': '100' } }), new Response(new Uint8Array([255])), new Response('{')]) {
      const x = fixture(response); x.capture.fetch(...args); await expect(x.capture.consume('token')).rejects.toThrow(); x.capture.dispose();
    }
  });
  it('separates dispose and token failure from successful original HTTP', async () => {
    const x = fixture(); x.capture.fetch(...args); await expect(x.capture.consume('wrong')).rejects.toThrow('token'); x.capture.dispose();
    const y = fixture(); y.capture.fetch(...args); y.capture.dispose(); await expect(y.capture.consume('token')).rejects.toThrow('Missing');
    expect(y.capture.snapshot().bytesOwned).toBe(0);
  });
});
