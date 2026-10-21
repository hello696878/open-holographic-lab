/** Test instrumentation only: one bounded clone of the one original fetch. */
export interface W2CaptureIdentity {
  contextId: string; pageId: string; token: string; sceneSha256: string;
  scene: unknown; requestId?: string;
}
export interface W2CaptureRecord {
  contextId: string; pageId: string; token: string; request: any;
  responseStatus: number; byteLength: number; base64: string;
}

/** Self-contained factory so its exact code can be installed before page startup. */
export function createW2ResponseCapture(original: typeof fetch, owner: { contextId: string; pageId: string }) {
  const cap = 524288;
  let armed: W2CaptureIdentity | null = null;
  let pending: Promise<W2CaptureRecord> | null = null;
  let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  let disposed = false, consumed = false, generation = 0, bytesOwned = 0;
  let fetchCount = 0, traceCount = 0, cloneCount = 0;
  const equal = (a: unknown, b: unknown): boolean => {
    if (Object.is(a, b)) return true;
    if (!a || !b || typeof a !== 'object' || typeof b !== 'object' || Array.isArray(a) !== Array.isArray(b)) return false;
    const aa = a as Record<string, unknown>, bb = b as Record<string, unknown>;
    const keys = Object.keys(aa); return keys.length === Object.keys(bb).length && keys.every(key => Object.hasOwn(bb, key) && equal(aa[key], bb[key]));
  };
  const wrapped: typeof fetch = (input, init) => {
    ++fetchCount;
    const promise = original(input, init); // Same Promise; never an async replacement or second HTTP.
    const url = typeof input === 'string' ? input : input instanceof URL ? input.pathname : input.url;
    const path = url.startsWith('http') ? new URL(url).pathname : url;
    if (path !== '/api/w2/trace' || (init?.method ?? 'GET').toUpperCase() !== 'POST') return promise;
    ++traceCount;
    if (!armed || disposed || pending) return promise;
    const identity = armed, epoch = generation; armed = null;
    pending = (async () => {
      const request = JSON.parse(String(init?.body));
      if (!request || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(request.request_id)
          || identity.requestId && identity.requestId !== request.request_id
          || request.scene_sha256 !== identity.sceneSha256 || !equal(request.scene, identity.scene)
          || request.scene?.model_contract !== 'w2_ideal_geometric_routing_v1') throw new Error('Capture request identity mismatch');
      const response = await promise;
      if (disposed || epoch !== generation) throw new Error('Capture was disposed');
      if (!response.ok) throw new Error(`Capture original HTTP ${response.status}`);
      const declared = response.headers.get('content-length');
      if (declared !== null && (!/^[0-9]+$/.test(declared) || Number(declared) > cap)) throw new Error('Capture declared size exceeds cap');
      const clone = response.clone(); ++cloneCount;
      if (!clone.body) throw new Error('Capture original response has no body');
      reader = clone.body.getReader(); const chunks: Uint8Array[] = []; let total = 0;
      try {
        for (;;) {
          const item = await reader.read();
          if (disposed || epoch !== generation) throw new Error('Capture was disposed');
          if (item.done) break;
          total += item.value.byteLength;
          if (total > cap) throw new Error('Capture streaming size exceeds cap');
          chunks.push(item.value); bytesOwned = total;
        }
      } catch (error) {
        // A tee branch's cancellation may wait for the untouched app branch.
        // Request cancellation without coupling this test-slot failure to it.
        void reader.cancel().catch(() => undefined); throw error;
      }
      finally { reader.releaseLock(); reader = null; }
      if (declared !== null && Number(declared) !== total) throw new Error('Capture original response is truncated');
      const bytes = new Uint8Array(total); let offset = 0;
      for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
      chunks.length = 0;
      const body = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
      if (body.protocol_version !== 1 || body.message_type !== 'trace_result'
          || body.model_contract !== 'w2_ideal_geometric_routing_v1'
          || body.request_id !== request.request_id || body.scene_sha256 !== request.scene_sha256
          || !equal(body.scene, request.scene)) throw new Error('Capture original response identity mismatch');
      const parts: string[] = [];
      for (let i = 0; i < bytes.length; i += 16384) parts.push(String.fromCharCode(...bytes.subarray(i, i + 16384)));
      return { ...owner, token: identity.token, request, responseStatus: response.status, byteLength: total, base64: btoa(parts.join('')) };
    })();
    // Instrumentation failure is consumed by consume(); it cannot alter the app's Promise.
    void pending.catch(() => undefined);
    return promise;
  };
  return {
    fetch: wrapped,
    arm(identity: W2CaptureIdentity): void {
      if (disposed || armed || pending) throw new Error('Capture slot is not available');
      if (identity.contextId !== owner.contextId || identity.pageId !== owner.pageId || !identity.token) throw new Error('Capture owner mismatch');
      consumed = false; armed = structuredClone(identity);
    },
    async consume(token: string): Promise<W2CaptureRecord> {
      if (disposed || consumed || !pending) throw new Error('Missing or already consumed original response capture');
      consumed = true;
      try { const record = await pending; if (record.token !== token) throw new Error('Capture token mismatch'); return record; }
      finally { pending = null; armed = null; bytesOwned = 0; }
    },
    dispose(): void {
      disposed = true; ++generation; armed = null; pending = null; bytesOwned = 0;
      if (reader) void reader.cancel().catch(() => undefined);
    },
    snapshot() { return { fetchCount, traceCount, cloneCount, bytesOwned, armed: !!armed, occupied: !!pending, consumed, disposed }; },
  };
}
