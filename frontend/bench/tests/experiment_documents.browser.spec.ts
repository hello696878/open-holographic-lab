/** Actual installed-Chrome downloads/uploads; numerical oracles live outside product files. */
import { test, expect, type Browser, type BrowserContext, type Page } from '@playwright/test';
import { readFileSync, writeFileSync, mkdirSync, renameSync, existsSync } from 'node:fs';
import { resolve, relative, dirname, isAbsolute } from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
import { MAX_RESPONSE_BYTES as MAX_V1_RESPONSE_BYTES, MAX_HEADER_BYTES as MAX_V1_HEADER_BYTES,
  MAX_REQUEST_BYTES as MAX_V1_REQUEST_BYTES } from '../src/contracts';
import { MAX_TWO_PATH_RESPONSE_BYTES, MAX_TWO_PATH_HEADER_BYTES, MAX_TWO_PATH_REQUEST_BYTES } from '../src/two_path_contracts';
import { MAX_POLARIZATION_RESPONSE_BYTES, MAX_POLARIZATION_HEADER_BYTES, MAX_POLARIZATION_REQUEST_BYTES } from '../src/polarization_contracts';

type Mode = 'sequential' | 'two_path' | 'polarization';
const modes: Mode[] = ['sequential', 'two_path', 'polarization'];
const root = resolve('../..');
const evidence = resolve(root, process.env.V2E_EVIDENCE_DIR ?? 'runs/v2e_acceptance/browser');
const figures = resolve(root, process.env.V2E_FIGURE_DIR ?? 'docs/handoffs/v2e/figures');
const fixtureManifestPath = resolve(root, process.env.V2E_FIXTURES ?? 'runs/v2e_acceptance/fixtures.json');
const fixtureDirectory = dirname(fixtureManifestPath);
const fixtureManifest = JSON.parse(readFileSync(fixtureManifestPath, 'utf8'));
const fixtures = Object.fromEntries(modes.map(mode => {
  const canonicalFile = fixtureManifest[mode]?.canonical_file;
  if (typeof canonicalFile !== 'string' || isAbsolute(canonicalFile)) throw new Error(`Canonical fixture path missing or not relative: ${mode}`);
  const path = resolve(fixtureDirectory, canonicalFile), within = relative(fixtureDirectory, path);
  if (!within || within === '..' || within.startsWith('..\\') || within.startsWith('../') || isAbsolute(within)) {
    throw new Error(`Canonical fixture must remain within its evidence directory: ${mode}`);
  }
  const document = JSON.parse(readFileSync(path, 'utf8'));
  expect(document.mode, `Canonical fixture mode: ${mode}`).toBe(mode);
  return [mode, document];
})) as Record<Mode, any>;
const snap = (page: Page): Promise<any> => page.evaluate(() => window.__benchDebug.snapshot());
const stateFor = (state: any, mode: Mode) => mode === 'sequential' ? state : mode === 'two_path' ? state.twoPath : state.polarization;
const sha = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex');
const compute = (url: string) => /\/api\/(?:v1|v2b|v2d)\/(?:simulate|sweep)$/.test(new URL(url).pathname);
function save(path: string, value: string | Buffer): void { writeFileSync(path, value, { flag: 'wx' }); }
function saveJSON(path: string, value: unknown): void { save(path, JSON.stringify(value, null, 2)); }
function directory(path: string): void { if (existsSync(path)) throw new Error(`Preserve existing evidence: ${path}`); mkdirSync(path, { recursive: true }); }
function bits(value: number): string { const bytes = Buffer.alloc(8); bytes.writeDoubleLE(value); return bytes.toString('hex'); }
function sameSettings(a: any, b: any, path = 'document'): void {
  if (typeof a === 'number') { expect(typeof b, path).toBe('number'); if (a === 0 && b === 0) return; expect(bits(b), path).toBe(bits(a)); return; }
  if (Array.isArray(a)) { expect(Array.isArray(b), path).toBe(true); expect(b.length, path).toBe(a.length); a.forEach((v, i) => sameSettings(v, b[i], `${path}[${i}]`)); return; }
  if (a && typeof a === 'object') { expect(Object.keys(b).sort(), path).toEqual(Object.keys(a).sort()); for (const k of Object.keys(a)) sameSettings(a[k], b[k], `${path}.${k}`); return; }
  expect(b, path).toBe(a);
}
function frame(bytes: Buffer) {
  const n = bytes.readUInt32LE(8), header = JSON.parse(bytes.subarray(16, 16 + n).toString('utf8'));
  const { request_id, ...scientific } = header;
  return { requestId: request_id, scientific, payload: bytes.subarray(16 + Math.ceil(n / 8) * 8) };
}
type CaptureRoute = { endpoint: string; cap: number; headerCap: number; requestCap: number; maxAxis: number;
  magic: string; planes: number; messageType: string | null };
const DOCUMENT_CAPTURE_ROUTES: Record<Mode, CaptureRoute> = {
  sequential: { endpoint: '/api/v1/simulate', cap: MAX_V1_RESPONSE_BYTES, headerCap: MAX_V1_HEADER_BYTES,
    requestCap: MAX_V1_REQUEST_BYTES, maxAxis: 512, magic: 'OHLABV1\0', planes: 1, messageType: null },
  two_path: { endpoint: '/api/v2b/simulate', cap: MAX_TWO_PATH_RESPONSE_BYTES, headerCap: MAX_TWO_PATH_HEADER_BYTES,
    requestCap: MAX_TWO_PATH_REQUEST_BYTES, maxAxis: 512, magic: 'OHLAB2P\0', planes: 2, messageType: 'two_path_result' },
  polarization: { endpoint: '/api/v2d/simulate', cap: MAX_POLARIZATION_RESPONSE_BYTES, headerCap: MAX_POLARIZATION_HEADER_BYTES,
    requestCap: MAX_POLARIZATION_REQUEST_BYTES, maxAxis: 128, magic: 'OHLABPL\0', planes: 2, messageType: 'polarization_result' },
};
// Test-owned transport instrumentation. The application receives the original fetch promise;
// clone/tee buffering and serialization can affect timing and are not product-owned memory.
function installDocumentSuccessCapture(options: { contextId: string; origin: string; routes: Record<string, CaptureRoute> }): void {
  const original = window.fetch, pageId = crypto.randomUUID();
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
  type Identity = { contextId: string; pageId: string };
  type Captured = { bytes: Uint8Array; status: number; responseURL: string } | { error: string };
  type Slot = { token: string; route: CaptureRoute; claimed: boolean; taking: boolean; claims: number;
    requestId: string | null; requestJSON: string | null; endpoint: string; done: Promise<Captured> | null;
    reader: ReadableStreamDefaultReader<Uint8Array> | null; conflict: string | null; capacity: number; frameBytes: number };
  type Failure = { token: string; requestId: string | null; endpoint: string; error: string };
  let slot: Slot | null = null, failure: Failure | null = null, arms = 0, consumed = 0, peak = 0, disposed = false;
  const message = (error: unknown) => error instanceof Error ? error.message : String(error);
  const inventory = () => ({ contextId: options.contextId, pageId, pendingOrRetained: slot ? 1 : 0,
    failedCaptures: failure ? 1 : 0, lifetimeArms: arms, consumedCaptures: consumed,
    retainedCaptureBufferBytes: slot?.capacity ?? 0, retainedFrameBytes: slot?.frameBytes ?? 0,
    retainedRequestJSONBytes: slot?.requestJSON ? new TextEncoder().encode(slot.requestJSON).byteLength : 0,
    peakCaptureBufferBytes: peak, maximumCaptureCount: 1, maximumLifetimeArms: 1, disposed });
  const identity = (expected: Identity) => {
    if (expected.contextId !== options.contextId || expected.pageId !== pageId) throw new Error('Document capture context/page identity mismatch');
  };
  const release = (entry: Slot, reason: string) => {
    const reader = entry.reader; entry.reader = null;
    if (reader) {
      // A tee cancellation can wait for the application's original branch. Do not block
      // context termination on it; release this test reader and close the actual context.
      try { void reader.cancel(reason).catch(error => { entry.conflict = `Capture cancellation failed: ${message(error)}`; }); }
      catch (error) { entry.conflict = `Capture cancellation failed: ${message(error)}`; }
      try { reader.releaseLock(); } catch (error) { entry.conflict = `Capture reader cleanup failed: ${message(error)}`; }
    }
    entry.done = null; entry.capacity = 0; entry.frameBytes = 0; entry.requestJSON = null;
    if (slot === entry) slot = null;
  };
  const failed = (entry: Slot, error: unknown): Captured => {
    const text = message(error); entry.conflict = entry.conflict ?? text;
    if (!disposed) failure = { token: entry.token, requestId: entry.requestId, endpoint: entry.endpoint, error: entry.conflict };
    release(entry, text); return { error: entry.conflict };
  };
  async function capture(response: Response, request: any, entry: Slot): Promise<Captured> {
    let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
    try {
      if (disposed || slot !== entry || entry.conflict) throw new Error(entry.conflict ?? 'Document capture disposed before response arrival');
      if (response.status !== 200 || response.url !== entry.endpoint) throw new Error('Document capture response status/endpoint mismatch');
      const grid = request.experiment?.grid, route = entry.route;
      if (![grid?.nx, grid?.ny].every(value => Number.isInteger(value) && value >= 1 && value <= route.maxAxis)) throw new Error('Document capture submitted grid exceeds route limits');
      // This runs before the first await and before the application can consume its body.
      const clone = response.clone();
      if (!clone.body) throw new Error('Document capture success response has no body');
      reader = clone.body.getReader(); entry.reader = reader;
      const declared = clone.headers.get('content-length');
      if (declared !== null && (!/^\d+$/.test(declared) || Number(declared) > route.cap)) throw new Error('Document capture Content-Length invalid or exceeds route cap');
      const storage = new Uint8Array(route.cap); let used = 0;
      entry.capacity = route.cap; peak = Math.max(peak, route.cap);
      while (true) {
        const part = await reader.read();
        if (disposed || slot !== entry || entry.conflict) throw new Error(entry.conflict ?? 'Document capture disposed while reading');
        if (part.done) break;
        if (part.value.byteLength > route.cap - used) throw new Error('Document capture exceeds route cap while streaming');
        storage.set(part.value, used); used += part.value.byteLength; entry.frameBytes = used;
      }
      if (declared !== null && used !== Number(declared)) throw new Error('Document capture truncated Content-Length');
      if (used < 16) throw new Error('Document capture truncated frame prefix');
      const view = new DataView(storage.buffer), length = view.getUint32(8, true), padded = Math.ceil(length / 8) * 8;
      if ([...route.magic].some((character, index) => storage[index] !== character.charCodeAt(0)) || view.getUint32(12, true) !== 0) throw new Error('Document capture frame magic/reserved mismatch');
      if (length < 2 || length > route.headerCap || padded > route.headerCap || 16 + padded > used) throw new Error('Document capture truncated/oversized header');
      for (let index = 16 + length; index < 16 + padded; index++) if (storage[index] !== 0) throw new Error('Document capture nonzero header padding');
      const header = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(storage.subarray(16, 16 + length)));
      if (header.protocol_version !== 1 || header.request_id !== request.request_id || header.request_id !== entry.requestId
          || (route.messageType === null ? 'message_type' in header : header.message_type !== route.messageType)) throw new Error('Document capture frame response identity/type mismatch');
      if (header.experiment?.grid?.nx !== grid.nx || header.experiment?.grid?.ny !== grid.ny) throw new Error('Document capture response grid differs from submission');
      if (used !== 16 + padded + 8 * (route.planes * grid.nx * grid.ny + grid.nx + grid.ny)) throw new Error('Document capture truncated/trailing payload');
      return { bytes: storage.subarray(0, used), status: response.status, responseURL: response.url };
    } catch (error) { return failed(entry, error); }
    finally {
      if (reader && entry.reader === reader) { reader.releaseLock(); entry.reader = null; }
    }
  }
  const wrapped: typeof fetch = (input, init) => {
    const pending = original.call(window, input, init); // Exactly one original call; return this same promise immediately.
    const entry = slot;
    if (disposed || !entry) return pending;
    let endpoint: URL;
    try { endpoint = new URL(input instanceof Request ? input.url : String(input), location.href); }
    catch { return pending; } // An unrelated invalid request keeps its original fetch behavior.
    const method = String(init?.method ?? (input instanceof Request ? input.method : 'GET'));
    if (endpoint.href === entry.endpoint && method.toUpperCase() === 'POST') {
      entry.claims++;
      if (entry.claimed) failed(entry, new Error('Duplicate request claimed one armed document capture'));
      else {
        entry.claimed = true;
        try {
          if (typeof init?.body !== 'string' || init.body.length > entry.route.requestCap) throw new Error('Document capture expected bounded original string JSON submission');
          if (new TextEncoder().encode(init.body).byteLength > entry.route.requestCap) throw new Error('Document capture request exceeds route cap');
          const request = JSON.parse(init.body);
          if (typeof request?.request_id !== 'string' || !uuid.test(request.request_id)) throw new Error('Document capture submitted request ID is not canonical UUIDv4');
          entry.requestId = request.request_id; entry.requestJSON = init.body;
          entry.done = pending.then(response => capture(response, request, entry), error => failed(entry, error));
        } catch (error) { failed(entry, error); }
      }
    }
    return pending;
  };
  window.fetch = wrapped;
  (window as any).__documentSuccessCapture = {
    inventory,
    arm(expected: Identity & { mode: string }): string {
      identity(expected);
      if (disposed || slot || failure || arms !== 0) {
        if (slot) failed(slot, new Error('Duplicate arm or retained document capture'));
        throw new Error('Document capture requires one live, unused context');
      }
      if (typeof expected.mode !== 'string' || !Object.hasOwn(options.routes, expected.mode)) throw new Error('Document capture mode/origin mismatch');
      const route = options.routes[expected.mode];
      if (!route || location.origin !== options.origin) throw new Error('Document capture mode/origin mismatch');
      const token = `${options.contextId}:${pageId}:${++arms}`;
      slot = { token, route, claimed: false, taking: false, claims: 0, requestId: null, requestJSON: null,
        endpoint: new URL(route.endpoint, options.origin).href, done: null, reader: null, conflict: null, capacity: 0, frameBytes: 0 };
      return token;
    },
    async take(expected: Identity & { token: string; requestId: string; endpoint: string }): Promise<{ base64: string; metadata: any }> {
      let entry: Slot | null = slot;
      try {
        identity(expected);
        if (disposed) throw new Error('Document capture is disposed');
        if (!entry) {
          if (failure?.token === expected.token) {
            const recorded = failure; failure = null;
            if (recorded.requestId !== expected.requestId || recorded.endpoint !== expected.endpoint) throw new Error('Failed document capture correlation mismatch');
            throw new Error(recorded.error);
          }
          throw new Error('Missing document success capture');
        }
        if (entry.token !== expected.token || entry.requestId !== expected.requestId || entry.endpoint !== expected.endpoint
            || !entry.claimed || !entry.done || typeof expected.requestId !== 'string' || !uuid.test(expected.requestId)) throw new Error('Document capture token/endpoint/submitted request identity mismatch');
        if (entry.taking) throw new Error('Duplicate document capture consumption');
        entry.taking = true;
        const pending = entry.done, requestJSON = entry.requestJSON, result = await pending;
        if ('error' in result) throw new Error(result.error);
        if (disposed || slot !== entry || entry.conflict || entry.claims !== 1 || result.status !== 200 || result.responseURL !== expected.endpoint) throw new Error(entry.conflict ?? 'Document capture changed during consumption');
        const beforeConsumption = inventory(), chunks: string[] = [];
        for (let index = 0; index < result.bytes.byteLength; index += 16384) chunks.push(String.fromCharCode(...result.bytes.subarray(index, index + 16384)));
        const base64 = btoa(chunks.join('')), rawByteLength = result.bytes.byteLength;
        release(entry, 'Document capture consumed'); consumed++; failure = null;
        return { base64, metadata: { contextId: options.contextId, pageId, token: expected.token, endpoint: expected.endpoint,
          requestId: expected.requestId, submittedRequestJSON: requestJSON, status: result.status, responseURL: result.responseURL,
          matchedOriginalFetchCalls: entry.claims, rawByteLength, beforeConsumption, afterConsumption: inventory(),
          ownership: 'One logical test slot; clone/tee, serialization and returned Node copies are additional test ownership, not product-owned memory or a whole-browser ceiling' } };
      } catch (error) {
        if (entry) failed(entry, error);
        if (failure?.token === expected.token) failure = null;
        throw error;
      } finally { if (entry) release(entry, 'Document capture take finished'); }
    },
    dispose(expected: Identity): { before: object; after: object; conflict: string | null } {
      identity(expected); const before = inventory();
      let conflict = disposed ? 'Duplicate document capture cleanup' : slot || failure ? 'Pending, failed or retained capture at context cleanup' : null;
      if (window.fetch !== wrapped) conflict = 'Document capture fetch ownership changed before cleanup';
      disposed = true;
      if (slot) release(slot, 'Document capture context cleanup');
      failure = null;
      if (window.fetch === wrapped) window.fetch = original;
      return { before, after: inventory(), conflict };
    },
  };
}
const captureContexts = new WeakMap<BrowserContext, { contextId: string; dir: string; armed: boolean }>();
const capturePages = new WeakMap<Page, { contextId: string; pageId: string }>();
async function closeCapturedContext(context: BrowserContext): Promise<void> {
  const owner = captureContexts.get(context), conflicts: unknown[] = [], pages: unknown[] = [];
  let actualContextClosed = false;
  try {
    if (!owner) throw new Error('Document capture context cleanup owner missing');
    for (const page of context.pages()) {
      if (page.isClosed()) continue;
      try {
        const known = capturePages.get(page);
        const result = await page.evaluate(({ contextId, pageId }) => {
          const capture = (window as any).__documentSuccessCapture;
          if (!capture) { if (location.href === 'about:blank' && pageId === null) return null; throw new Error('Document capture missing during context cleanup'); }
          const state = capture.inventory();
          return capture.dispose({ contextId, pageId: pageId ?? state.pageId });
        }, { contextId: owner.contextId, pageId: known?.pageId ?? null });
        pages.push(result); capturePages.delete(page);
        if (result && (result.conflict || result.after.pendingOrRetained || result.after.failedCaptures
            || result.after.retainedCaptureBufferBytes || !result.after.disposed)) throw new Error(result.conflict ?? 'Document capture cleanup left ownership');
      } catch (error) { conflicts.push(error); }
    }
  } finally {
    captureContexts.delete(context);
    try { await context.close(); actualContextClosed = true; } catch (error) { conflicts.push(error); }
    if (owner) saveJSON(resolve(owner.dir, `context_${owner.contextId}_capture_cleanup.json`), {
      contextId: owner.contextId, armed: owner.armed, actualContextClosed, pages,
      conflicts: conflicts.map(error => error instanceof Error ? error.message : String(error)),
    });
  }
  if (conflicts.length) throw new AggregateError(conflicts, 'Document success-capture context cleanup failed');
}
async function capturedDocumentBytes(page: Page, mode: Mode, token: string, requestJSON: string, dir: string, label: string): Promise<Buffer> {
  const owner = capturePages.get(page); if (!owner) throw new Error('Document capture page owner missing');
  const request = JSON.parse(requestJSON), endpoint = new URL(DOCUMENT_CAPTURE_ROUTES[mode].endpoint, 'http://127.0.0.1:8510').href;
  const captured = await page.evaluate(expected => (window as any).__documentSuccessCapture.take(expected), { ...owner, token, requestId: request.request_id, endpoint });
  if (captured.metadata.contextId !== owner.contextId || captured.metadata.pageId !== owner.pageId || captured.metadata.token !== token
      || captured.metadata.requestId !== request.request_id || captured.metadata.endpoint !== endpoint || captured.metadata.status !== 200
      || captured.metadata.submittedRequestJSON !== requestJSON || captured.metadata.matchedOriginalFetchCalls !== 1) throw new Error('Transferred document capture identity differs from actual original request');
  const bytes = Buffer.from(captured.base64, 'base64');
  if (bytes.toString('base64') !== captured.base64 || bytes.byteLength !== captured.metadata.rawByteLength
      || bytes.byteLength > DOCUMENT_CAPTURE_ROUTES[mode].cap) throw new Error('Transferred document capture length differs from original bounded frame');
  if (captured.metadata.afterConsumption.pendingOrRetained !== 0 || captured.metadata.afterConsumption.failedCaptures !== 0
      || captured.metadata.afterConsumption.retainedCaptureBufferBytes !== 0 || captured.metadata.afterConsumption.retainedFrameBytes !== 0
      || captured.metadata.afterConsumption.retainedRequestJSONBytes !== 0) throw new Error('Consumed document capture retained test ownership');
  saveJSON(resolve(dir, `${label}_capture.json`), { ...captured.metadata, rawSHA256: sha(bytes),
    submittedRequestSHA256: sha(Buffer.from(requestJSON, 'utf8')), returnedNodeBufferBytes: bytes.byteLength,
    timing: 'Original-response clone/tee and serialization instrumentation can change buffering/timing; these test-owned buffers are not product memory measurements' });
  return bytes;
}
async function newPage(browser: Browser, dir: string) {
  const context = await browser.newContext({ baseURL: 'http://127.0.0.1:8510', viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
  const contextId = randomUUID(); captureContexts.set(context, { contextId, dir, armed: false });
  try {
    await context.addInitScript(installDocumentSuccessCapture, { contextId, origin: 'http://127.0.0.1:8510', routes: DOCUMENT_CAPTURE_ROUTES });
    const page = await context.newPage();
    await page.route('**/*', route => new URL(route.request().url()).origin === 'http://127.0.0.1:8510' ? route.continue() : route.abort('blockedbyclient'));
    await page.goto('/'); await expect(page.getByTestId('simulate')).toBeEnabled();
    await page.getByTestId('doc-toggle').click();
    const identity = await page.evaluate(() => (window as any).__documentSuccessCapture.inventory());
    if (identity.contextId !== contextId || typeof identity.pageId !== 'string'
        || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(identity.pageId)
        || identity.pendingOrRetained !== 0) throw new Error('Document context/page capture installation mismatch');
    capturePages.set(page, { contextId, pageId: identity.pageId });
    return { context, page };
  } catch (error) {
    try { await closeCapturedContext(context); } catch (cleanup) { throw new AggregateError([error, cleanup], 'Document context initialization and cleanup failed'); }
    throw error;
  }
}
async function upload(page: Page, path: string): Promise<void> {
  await page.getByTestId('doc-file').setInputFiles(path);
  await expect(page.getByTestId('doc-preview')).toBeVisible();
  await expect(page.getByTestId('doc-status')).toHaveAttribute('data-status', 'preview');
}
async function apply(page: Page, mode: Mode): Promise<void> {
  await page.getByTestId('doc-ack').check(); await page.getByTestId('doc-apply').click();
  await expect(page.getByTestId('mode')).toHaveValue(mode);
  await expect(page.getByTestId('doc-status')).toHaveText('Settings Restored; Simulation Not Run');
  await expect(page.getByTestId('doc-preview')).toBeHidden();
}
async function solve(page: Page, mode: Mode, dir: string, label: string) {
  const path = mode === 'sequential' ? '/api/v1/simulate' : mode === 'two_path' ? '/api/v2b/simulate' : '/api/v2d/simulate';
  const owner = captureContexts.get(page.context()), identity = capturePages.get(page);
  if (!owner || !identity || owner.armed) throw new Error('Document capture requires its own unused actual context/page');
  const token = await page.evaluate(expected => (window as any).__documentSuccessCapture.arm(expected), { ...identity, mode }); owner.armed = true;
  const waiting = page.waitForResponse(response => new URL(response.url()).pathname === path && response.request().method() === 'POST');
  await page.getByTestId(mode === 'sequential' ? 'simulate' : mode === 'two_path' ? 'tp-simulate' : 'pl-simulate').click();
  const response = await waiting; expect(response.status()).toBe(200);
  const requestJSON = response.request().postData()!, request = JSON.parse(requestJSON);
  const body = await capturedDocumentBytes(page, mode, token, requestJSON, dir, label);
  saveJSON(resolve(dir, `${label}_request.json`), request); save(resolve(dir, `${label}_response.bin`), body);
  await expect.poll(async () => stateFor(await snap(page), mode).currentResult?.requestId).toBe(request.request_id);
  return { body, request };
}
async function download(page: Page, path: string): Promise<Buffer> {
  await page.getByTestId('doc-export').click(); await expect(page.getByTestId('doc-download-area')).toBeVisible();
  await expect(page.getByTestId('doc-status')).toHaveText('Download Prepared');
  const waiting = page.waitForEvent('download'); await page.getByTestId('doc-download').click();
  const actual = await waiting; expect(await actual.failure()).toBeNull(); await actual.saveAs(path);
  await expect(page.getByTestId('doc-status')).toHaveText('Download Requested');
  return readFileSync(path);
}

for (const mode of modes) test(`portable ${mode}: real download, closed context, renamed upload, explicit recomputation`, async ({ browser }) => {
  const dir = resolve(evidence, mode); directory(dir);
  const doc = fixtures[mode]; expect(doc.mode).toBe(mode);
  const seed = resolve(dir, 'seed.json'); saveJSON(seed, doc);
  const first = await newPage(browser, dir); let original: Awaited<ReturnType<typeof solve>>;
  let downloaded: Buffer;
  try {
    const posts: string[] = []; first.page.on('request', r => { if (r.method() === 'POST') posts.push(r.url()); });
    const before = await snap(first.page);
    await upload(first.page, seed);
    expect((await snap(first.page)).mode).toBe(before.mode);
    expect(posts.filter(compute)).toHaveLength(0);
    expect(posts.filter(u => u.endsWith('/api/v2e/documents/validate'))).toHaveLength(2);
    await apply(first.page, mode); sameSettings(doc.experiment, stateFor(await snap(first.page), mode).validatedDraft);
    expect(posts.filter(compute)).toHaveLength(0);
    original = await solve(first.page, mode, dir, 'original');
    downloaded = await download(first.page, resolve(dir, 'downloaded.json'));
    const exported = JSON.parse(downloaded.toString('utf8')); sameSettings(doc, exported);
    expect(Object.keys(exported).sort()).toEqual(['document_format', 'document_version', 'experiment', 'metadata', 'mode', 'model_contract'].sort());
    expect(posts.filter(compute)).toHaveLength(1);
    if (mode === 'sequential') { mkdirSync(figures, { recursive: true }); await first.page.screenshot({ path: resolve(figures, 'fig01_export_settings.png'), fullPage: true }); }
  } finally { await closeCapturedContext(first.context); }
  // No live original context or storageState survives this point.
  mkdirSync(resolve(dir, 'moved')); renameSync(resolve(dir, 'downloaded.json'), resolve(dir, 'moved', 'renamed-settings.json'));
  save(resolve(dir, 'downloaded.json'), downloaded!); // evidence copy; actual uploaded file is renamed/moved.
  expect(sha(readFileSync(resolve(dir, 'moved', 'renamed-settings.json')))).toBe(sha(downloaded!));
  const second = await newPage(browser, dir);
  try {
    const posts: string[] = []; second.page.on('request', r => { if (r.method() === 'POST') posts.push(r.url()); });
    const before = await snap(second.page);
    expect(await second.page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
    await upload(second.page, resolve(dir, 'moved', 'renamed-settings.json'));
    const preview = await snap(second.page);
    expect(preview.mode).toBe(before.mode);
    for (const other of modes) sameSettings(stateFor(before, other).candidate, stateFor(preview, other).candidate);
    expect(posts.filter(compute)).toHaveLength(0);
    expect(posts.filter(u => u.endsWith('/api/v2e/documents/validate'))).toHaveLength(2);
    expect(await second.page.getByTestId('doc-ack').isChecked()).toBe(false);
    if (mode === 'polarization') await second.page.screenshot({ path: resolve(figures, 'fig02_import_preview.png'), fullPage: true });
    await apply(second.page, mode);
    const restored = await snap(second.page);
    sameSettings(doc.experiment, stateFor(restored, mode).validatedDraft);
    for (const other of modes.filter(m => m !== mode)) sameSettings(stateFor(before, other).candidate, stateFor(restored, other).candidate);
    expect(stateFor(restored, mode).currentResult).toBeNull(); expect(posts.filter(compute)).toHaveLength(0);
    if (mode === 'two_path') await second.page.screenshot({ path: resolve(figures, 'fig03_restored_unsimulated.png'), fullPage: true });
    await second.page.getByTestId('zoom-in').click(); await second.page.getByTestId('pan-left').click(); await second.page.getByTestId('reset-view').click();
    // Switching modes, selecting a component, and editing only metadata must preserve every imported SI leaf.
    const away = mode === 'sequential' ? 'two_path' : 'sequential';
    await second.page.getByTestId('mode').selectOption(away);
    await expect(second.page.getByTestId(away === 'sequential' ? 'simulate' : 'tp-simulate')).toBeEnabled();
    await second.page.getByTestId('mode').selectOption(mode);
    await expect(second.page.getByTestId(mode === 'sequential' ? 'simulate' : mode === 'two_path' ? 'tp-simulate' : 'pl-simulate')).toBeEnabled();
    await second.page.getByTestId(mode === 'sequential' ? `select-${doc.experiment.components[1].id}`
      : mode === 'two_path' ? 'tp-select-arm_0' : `pl-select-${doc.experiment.elements[1].id}`).click();
    await second.page.getByTestId('doc-title').fill(`${doc.metadata.title}（暫存）`);
    await second.page.getByTestId('doc-notes').fill(`${doc.metadata.notes}\n只改備註`);
    const passive = await snap(second.page);
    for (const other of modes) sameSettings(stateFor(restored, other).candidate, stateFor(passive, other).candidate);
    sameSettings(doc.experiment, stateFor(passive, mode).validatedDraft);
    expect(stateFor(passive, mode).revision).toBe(stateFor(restored, mode).revision);
    expect(stateFor(passive, mode).currentResult).toBeNull(); expect(posts.filter(compute)).toHaveLength(0);
    await second.page.getByTestId('doc-title').fill(doc.metadata.title);
    await second.page.getByTestId('doc-notes').fill(doc.metadata.notes);
    const field = second.page.getByTestId(mode === 'sequential' ? 'edit-wavelength_m' : mode === 'two_path' ? 'tp-edit-wavelength_m' : 'pl-edit-wavelength_m');
    await field.focus(); await field.dispatchEvent('input'); await field.blur();
    if (mode === 'polarization') { await second.page.getByTestId('pl-tau').fill('0.8123456789'); await second.page.getByTestId('pl-tau').dispatchEvent('change'); }
    sameSettings(doc.experiment, stateFor(await snap(second.page), mode).candidate);
    expect(stateFor(await snap(second.page), mode).revision).toBe(stateFor(restored, mode).revision);
    expect(posts.filter(compute)).toHaveLength(0);
    const result = await solve(second.page, mode, dir, 'restored');
    sameSettings(original!.request.experiment, result.request.experiment);
    const a = frame(original!.body), b = frame(result.body);
    expect(b.requestId).not.toBe(a.requestId); expect(b.scientific).toEqual(a.scientific); expect(b.payload.equals(a.payload)).toBe(true);
    const reexported = await download(second.page, resolve(dir, 'reexported.json'));
    expect(reexported.equals(downloaded!)).toBe(true);
    await second.page.getByTestId('doc-dismiss').click();
    const ownership = (await snap(second.page)).documents.ownership;
    expect(ownership.urls).toBe(0); expect(ownership.activeReaders).toBe(0); expect(ownership.activeFetches).toBe(0);
    saveJSON(resolve(dir, 'outcome.json'), { mode, originalContextClosed: true, freshStorage: true, actualDownloadConsumed: true,
      renamedMovedBytesUnchanged: true, originalSHA256: sha(original!.body), restoredSHA256: sha(result.body),
      payloadSHA256: sha(b.payload), documentSHA256: sha(downloaded!), payloadExact: true, scientificHeaderExact: true,
      canonicalIdempotent: true, passiveModeCycleSelectionMetadataPreserved: true, explicitSimulationPosts: posts.filter(compute).length, ownership });
  } finally { await closeCapturedContext(second.context); }
  mkdirSync(evidence, { recursive: true });
  const manifestPath = resolve(evidence, 'portability.json');
  const manifest = existsSync(manifestPath) ? JSON.parse(readFileSync(manifestPath, 'utf8')) : { modes: {} };
  manifest.modes[mode] = Object.fromEntries(Object.entries({ original_request: 'original_request.json', original_response: 'original_response.bin',
    restored_request: 'restored_request.json', restored_response: 'restored_response.bin', downloaded: 'downloaded.json',
    moved: 'moved/renamed-settings.json', reexported: 'reexported.json' }).map(([key, file]) => [key, relative(evidence, resolve(dir, file))]));
  writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
});

test('invalid and cancelled import, scalar text, metadata and exact same-label replacements', async ({ browser }) => {
  const dir = resolve(evidence, 'transactions'); directory(dir); const { context, page } = await newPage(browser, dir);
  try {
    const a = structuredClone(fixtures.sequential), b = structuredClone(a);
    a.experiment.components[1].focal_length_m = -0.020000000000000004;
    b.experiment.components[1].focal_length_m = -0.020000000000000007;
    const ap = resolve(dir, 'a.json'), bp = resolve(dir, 'b.json'); saveJSON(ap, a); saveJSON(bp, b);
    await upload(page, ap); await apply(page, 'sequential');
    await page.getByTestId(`select-${a.experiment.components[1].id}`).click();
    const focal = page.getByTestId('edit-components-1-focal_length_m'), painted = await focal.inputValue();
    await upload(page, bp); await apply(page, 'sequential');
    await page.getByTestId(`select-${b.experiment.components[1].id}`).click();
    expect(await focal.inputValue()).toBe(painted); await focal.focus(); await focal.dispatchEvent('input'); await focal.blur();
    sameSettings(b.experiment, (await snap(page)).candidate);
    const before = await snap(page), posts: string[] = [];
    page.on('request', r => { if (r.method() === 'POST') posts.push(r.url()); });
    const invalid = resolve(dir, 'invalid.json'); save(invalid, '{"document_format":"x","document_format":"y"}');
    await page.getByTestId('doc-file').setInputFiles(invalid); await expect(page.getByTestId('doc-error')).toBeVisible();
    sameSettings(before.candidate, (await snap(page)).candidate); expect((await snap(page)).mode).toBe(before.mode);
    await upload(page, ap); await page.getByTestId('doc-cancel').click();
    sameSettings(before.candidate, (await snap(page)).candidate); await expect(page.getByTestId('doc-preview')).toBeHidden();
    const scienceBefore = stateFor(await snap(page), 'sequential');
    await page.getByTestId('doc-title').fill('中文😀e\u0301 <b>純文字</b>');
    await page.getByTestId('doc-notes').fill('備註\n\t不含結果');
    const metadataAfter = stateFor(await snap(page), 'sequential');
    sameSettings(scienceBefore.candidate, metadataAfter.candidate); expect(metadataAfter.revision).toBe(scienceBefore.revision);
    expect(posts.filter(compute)).toHaveLength(0);
    await page.getByTestId('doc-title').fill('😀'.repeat(120)); await expect(page.getByTestId('doc-error')).toBeHidden();
    await page.getByTestId('doc-title').fill('😀'.repeat(121)); await expect(page.getByTestId('doc-export')).toBeDisabled();
    await page.getByTestId('doc-title').fill('有效標題');
    const untouched = structuredClone((await snap(page)).candidate);
    await page.getByTestId('edit-wavelength_m').fill('647'); await page.getByTestId('edit-wavelength_m').blur();
    await expect(page.getByTestId('simulate')).toBeEnabled();
    const edited = (await snap(page)).candidate; const expected = structuredClone(untouched); expected.wavelength_m = 647 * 1e-9;
    sameSettings(expected, edited); expect(posts.filter(compute)).toHaveLength(0);
    saveJSON(resolve(dir, 'outcome.json'), { identicalPaintedText: painted, secondImportBits: bits(b.experiment.components[1].focal_length_m),
      invalidCancelPreserved: true, unicodeScalar120Accepted121Rejected: true, metadataNoScientificInvalidation: true, oneFieldIsolation: true });
  } finally { await closeCapturedContext(context); }
});

test('stale stage-one/stage-two responses and frozen draft export cannot replace newer intent', async ({ browser }) => {
  const dir = resolve(evidence, 'races'); directory(dir); const { context, page } = await newPage(browser, dir);
  try {
    mkdirSync(resolve(dir, 'a')); mkdirSync(resolve(dir, 'b'));
    const first = resolve(dir, 'a', 'same.json'), second = resolve(dir, 'b', 'same.json');
    const a = structuredClone(fixtures.sequential), b = structuredClone(a); b.metadata.title = a.metadata.title.replace('設', '測');
    expect(b.metadata.title).not.toBe(a.metadata.title);
    saveJSON(first, a); saveJSON(second, b);
    expect(readFileSync(first).byteLength).toBe(readFileSync(second).byteLength);
    let held = 0, release: (() => void) | null = null; const cancelled = new Set<number>();
    await page.route('**/api/v2e/documents/validate', async route => {
      const response = await route.fetch(); const index = ++held;
      if (index === 1 || index === 3) await new Promise<void>(resolve => { release = resolve; });
      try { await route.fulfill({ response }); } catch (error) { if (!cancelled.has(index)) throw error; }
    });
    await page.getByTestId('doc-file').setInputFiles(first); await expect.poll(() => held).toBe(1);
    await page.getByTestId('doc-cancel').click(); cancelled.add(1); release!();
    await page.getByTestId('doc-file').setInputFiles(second); await expect.poll(() => held).toBe(3);
    await page.getByTestId('doc-cancel').click(); cancelled.add(3); release!();
    await expect(page.getByTestId('doc-preview')).toBeHidden();
    await page.unroute('**/api/v2e/documents/validate');
    await upload(page, first); await apply(page, 'sequential');
    const captured = structuredClone((await snap(page)).validatedDraft);
    let exported: (() => void) | null = null;
    await page.route('**/api/v2e/documents/validate', async route => {
      const response = await route.fetch(); await new Promise<void>(resolve => { exported = resolve; }); await route.fulfill({ response });
    });
    await page.getByTestId('doc-export').click(); await expect.poll(() => !!exported).toBe(true);
    await page.getByTestId('edit-wavelength_m').fill('647'); await expect(page.getByTestId('simulate')).toBeEnabled();
    exported!(); await expect(page.getByTestId('doc-download-area')).toBeVisible();
    const waiting = page.waitForEvent('download'); await page.getByTestId('doc-download').click();
    const actual = await waiting; await actual.saveAs(resolve(dir, 'frozen.json'));
    sameSettings(captured, JSON.parse(readFileSync(resolve(dir, 'frozen.json'), 'utf8')).experiment);
    expect((await snap(page)).candidate.wavelength_m).not.toBe(captured.wavelength_m);
    await page.getByTestId('doc-dismiss').click(); expect((await snap(page)).documents.ownership.urls).toBe(0);
    saveJSON(resolve(dir, 'outcome.json'), { staleFirstAndSecondRepliesDiscarded: true, frozenDraftExportRetained: true });
  } finally { await closeCapturedContext(context); }
});

test('controlled document validation stays responsive under a real held worker and Apply rechecks busy', async ({ browser }) => {
  const control = process.env.V2E_CONTROLLED_DIR;
  test.skip(!control, 'Explicit separately launched task-owned held-worker harness only');
  const dir = resolve(evidence, 'held'); directory(dir); const { context, page } = await newPage(browser, dir);
  const owned = resolve(root, control!), operation = process.env.V2E_CONTROLLED_OPERATION!;
  const mode: Mode = operation === 'sequential' ? 'sequential' : operation === 'dual' || operation === 'sweep' ? 'two_path' : 'polarization';
  try {
    const seed = resolve(dir, 'seed.json'); saveJSON(seed, fixtures[mode]); await upload(page, seed); await apply(page, mode);
    const waiting = resolve(dir, 'replacement.json'); saveJSON(waiting, fixtures[mode]); await upload(page, waiting);
    await page.getByTestId('doc-ack').check(); await expect(page.getByTestId('doc-apply')).toBeEnabled();
    if (operation === 'polarization_sweep') await page.getByTestId(`pl-select-${fixtures.polarization.experiment.elements[1].id}`).click();
    await page.getByTestId(operation === 'sequential' ? 'simulate' : operation === 'dual' ? 'tp-simulate' : operation === 'sweep' ? 'tp-sweep' : operation === 'polarization' ? 'pl-simulate' : 'pl-sweep').click();
    await expect.poll(() => existsSync(resolve(owned, 'started.json'))).toBe(true);
    await expect(page.getByTestId('doc-apply')).toBeDisabled();
    const before = stateFor(await snap(page), mode).candidate;
    await page.getByTestId('doc-apply').dispatchEvent('click'); sameSettings(before, stateFor(await snap(page), mode).candidate);
    // Raw validation while busy does not own/release the compute gate.
    await upload(page, seed); expect((await snap(page)).documents.state.preview).toBeTruthy();
    const health = await page.evaluate(async () => (await fetch('/api/v1/health')).json()); expect(health.busy).toBe(true);
    save(resolve(owned, 'release.flag'), 'explicit task-owned release');
    await expect.poll(() => existsSync(resolve(owned, 'completed.json'))).toBe(true);
    await expect.poll(async () => (await page.evaluate(async () => (await fetch('/api/v1/health')).json())).busy).toBe(false);
    saveJSON(resolve(dir, 'outcome.json'), { operation, documentValidationWhileBusy: true, busyApplyRejected: true, actualWorkerCompleted: true });
  } finally { if (!existsSync(resolve(owned, 'release.flag'))) save(resolve(owned, 'release.flag'), 'release owned worker during cleanup'); await closeCapturedContext(context); }
});
