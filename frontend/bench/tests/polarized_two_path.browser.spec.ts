/** Installed-browser acceptance of actual production V2f compositions. Controlled faults are explicitly labeled. */
import { test, expect, type Page } from '@playwright/test';
import { mkdirSync, writeFileSync, existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { randomUUID } from 'node:crypto';
import { SWEEP_PHASES_RAD } from '../src/two_path_contracts';
import { SWEEP_ANGLES_RAD } from '../src/polarization_contracts';
import { MAX_POLARIZED_TWO_PATH_DISABLED_RESPONSE_BYTES, MAX_POLARIZED_TWO_PATH_RESPONSE_BYTES,
  MAX_POLARIZED_TWO_PATH_HEADER_BYTES } from '../src/polarized_two_path_contracts';

const root = resolve('../..'), evidenceBase = resolve(root, process.env.V2G_EVIDENCE_DIR ?? 'runs/v2g_acceptance/browser');
const figuresBase = resolve(root, process.env.V2G_FIGURE_DIR ?? 'docs/handoffs/v2g/figures');
let evidence = evidenceBase, figures = figuresBase;
const smoke = process.env.V2G_SMOKE === '1';
const controlledOnly = process.env.V2G_CONTROLLED_ONLY === '1';
const snap = (page: Page): Promise<any> => page.evaluate(() => window.__benchDebug.snapshot());
const pt = async (page: Page): Promise<any> => (await snap(page)).polarizedTwoPath;
const compute = (path: string) => /\/api\/(?:v1|v2b|v2d|v2g)\/(?:simulate|sweep)$/.test(path);
function save(name: string, value: unknown): void { mkdirSync(evidence, { recursive: true }); writeFileSync(resolve(evidence, `${name}.json`), JSON.stringify(value, null, 2), { flag: 'wx' }); }
function saveFrame(name: string, bytes: Buffer): void { mkdirSync(evidence, { recursive: true }); writeFileSync(resolve(evidence, `${name}.bin`), bytes, { flag: 'wx' }); }
function posts(page: Page): string[] { const paths: string[] = []; page.on('request', r => { if (r.method() === 'POST') paths.push(new URL(r.url()).pathname); }); return paths; }
async function frames(page: Page, count = 8): Promise<void> { await page.evaluate(count => new Promise<void>(resolve => {
  let n = 0; const next = () => ++n < count ? requestAnimationFrame(next) : resolve(); requestAnimationFrame(next);
}), count); }
async function ready(page: Page): Promise<void> { await expect.poll(async () => { const s = await pt(page); return !!s.validatedDraft && !s.pendingValidation && !s.pendingSweepValidation && !s.active; }).toBe(true); await expect(page.getByTestId('pt-simulate')).toBeEnabled(); }
async function load(page: Page): Promise<void> { await page.goto('/'); expect((await snap(page)).mode).toBe('sequential'); await page.getByTestId('mode').selectOption('polarized_two_path'); await ready(page); }
async function preset(page: Page, id: string): Promise<void> { await page.getByTestId('pt-preset').selectOption(id); await ready(page); }
async function edit(page: Page, path: string, value: string): Promise<void> { const field = page.getByTestId(`pt-edit-${path.replaceAll('.', '-')}`); await field.fill(value); await field.blur(); await expect.poll(async () => (await pt(page)).pendingValidation).toBe(false); }
// Test-owned instrumentation only. One armed success response is copied; the app receives
// the original fetch promise immediately. A clone is not a native/browser-memory ceiling.
function installSuccessCapture(options: { contextId: string; disabledCap: number; enabledCap: number; headerCap: number }): void {
  const target = '/api/v2g/simulate', original = window.fetch, pageId = crypto.randomUUID();
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
  type Captured = { bytes: Uint8Array; status: number; requestId: string; endpoint: string } | { error: string };
  type Slot = { token: string; claimed: boolean; requestId: string | null; endpoint: string | null;
    done: Promise<Captured> | null; reader: ReadableStreamDefaultReader<Uint8Array> | null; conflict: string | null;
    allocatedCapacityBytes: number; frameBytes: number };
  let slot: Slot | null = null, sequence = 0, consumed = 0, peakCaptureBufferBytes = 0, disposed = false;
  const inventory = () => ({ pendingOrRetained: slot ? 1 : 0, lifetimeSubmissions: sequence, consumedCaptures: consumed,
    retainedCaptureBufferBytes: slot?.allocatedCapacityBytes ?? 0, retainedFrameBytes: slot?.frameBytes ?? 0, peakCaptureBufferBytes,
    maximumCaptureCount: 1, maximumCaptureBufferBytes: options.enabledCap,
    serialization: 'Additional bounded base64/string and transferred Node copies; native clone buffering is not bounded by this inventory', disposed });
  const message = (error: unknown) => error instanceof Error ? error.message : String(error);
  async function capture(response: Response, request: any, entry: Slot): Promise<Captured> {
    let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
    try {
      if (disposed || entry !== slot) throw new Error('Genuine capture disposed before response arrival');
      if (response.status !== 200) throw new Error(`Expected genuine capture HTTP 200, got ${response.status}`);
      const enabled = request.experiment?.analyzer?.enabled, grid = request.experiment?.grid;
      if (typeof enabled !== 'boolean' || ![grid?.nx, grid?.ny].every(n => Number.isInteger(n) && n >= 1 && n <= 128)) throw new Error('Capture submission grid/analyzer mismatch');
      const cap = enabled ? options.enabledCap : options.disabledCap, clone = response.clone();
      if (!clone.body) throw new Error('Genuine success response has no body');
      reader = clone.body.getReader(); entry.reader = reader;
      const declared = clone.headers.get('content-length');
      if (declared !== null && (!/^\d+$/.test(declared) || Number(declared) > cap)) throw new Error('Genuine capture Content-Length exceeds route cap or is invalid');
      const storage = new Uint8Array(cap); let used = 0;
      entry.allocatedCapacityBytes = cap; peakCaptureBufferBytes = Math.max(peakCaptureBufferBytes, cap);
      while (true) {
        const part = await reader.read(); if (part.done) break;
        if (disposed || entry !== slot) throw new Error('Genuine capture disposed before consumption');
        if (part.value.byteLength > cap - used) throw new Error(`Genuine capture exceeds ${cap}-byte route cap while streaming`);
        storage.set(part.value, used); used += part.value.byteLength; entry.frameBytes = used;
      }
      if (declared !== null && used !== Number(declared)) throw new Error('Genuine capture truncated Content-Length');
      if (used < 16) throw new Error('Genuine capture truncated frame prefix');
      const view = new DataView(storage.buffer), length = view.getUint32(8, true), padded = Math.ceil(length / 8) * 8;
      if ([79, 72, 76, 65, 66, 80, 84, 0].some((byte, index) => storage[index] !== byte) || view.getUint32(12, true) !== 0) throw new Error('Genuine capture frame prefix mismatch');
      if (length < 2 || padded > options.headerCap || 16 + padded > used) throw new Error('Genuine capture truncated/oversized header');
      const header = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(storage.subarray(16, 16 + length)));
      if (header.request_id !== request.request_id) throw new Error('Genuine capture response request-ID mismatch');
      const expected = 16 + padded + 8 * ((enabled ? 4 : 2) * grid.nx * grid.ny + grid.nx + grid.ny);
      if (used !== expected) throw new Error('Genuine capture truncated/trailing payload');
      return { bytes: storage.subarray(0, used), status: response.status, requestId: request.request_id, endpoint: entry.endpoint! };
    } catch (error) {
      // A failed clone is never substituted or retried; expose its failure to the test.
      if (reader) void reader.cancel(message(error)).catch(() => undefined);
      return { error: message(error) };
    } finally { if (reader) reader.releaseLock(); entry.reader = null; }
  }
  const wrapped: typeof fetch = (input, init) => {
    const pending = original.call(window, input, init); // Exactly one original HTTP call; return this same promise.
    const endpoint = new URL(input instanceof Request ? input.url : String(input), location.href);
    const method = init?.method ?? (input instanceof Request ? input.method : 'GET');
    if (!disposed && slot && endpoint.origin === location.origin && endpoint.pathname === target && method.toUpperCase() === 'POST') {
      const entry = slot;
      if (entry.claimed) entry.conflict = 'More than one success-path request claimed one armed capture';
      else {
        entry.claimed = true; entry.endpoint = endpoint.href;
        try {
          if (typeof init?.body !== 'string') throw new Error('Capture expected the original string JSON submission');
          const request = JSON.parse(init.body);
          if (!uuid.test(request.request_id)) throw new Error('Capture submission request ID is not canonical UUIDv4');
          entry.requestId = request.request_id;
          entry.done = pending.then(response => capture(response, request, entry), error => ({ error: message(error) }));
        } catch (error) { entry.done = Promise.resolve({ error: message(error) }); }
      }
    }
    return pending;
  };
  window.fetch = wrapped;
  (window as any).__ptSuccessCapture = {
    arm(): string {
      if (disposed || slot) throw new Error('Capture must be live with no retained or pending capture');
      if (++sequence > 32) throw new Error('Test capture lifetime count exceeds 32 submissions');
      const token = `${options.contextId}:${pageId}:${sequence}`;
      slot = { token, claimed: false, requestId: null, endpoint: null, done: null, reader: null, conflict: null, allocatedCapacityBytes: 0, frameBytes: 0 }; return token;
    },
    async take(token: string, requestId: string): Promise<{ base64: string; metadata: object }> {
      const entry = slot;
      if (!entry || entry.token !== token || !entry.claimed || !entry.done) throw new Error('Missing or mismatched genuine success capture');
      try {
        if (entry.requestId !== requestId || entry.endpoint !== new URL(target, location.href).href) throw new Error('Capture context/endpoint/submitted request-ID mismatch');
        const result = await entry.done;
        if (entry.conflict) throw new Error(entry.conflict);
        if ('error' in result) throw new Error(result.error);
        if (result.requestId !== requestId || result.endpoint !== entry.endpoint || result.status !== 200) throw new Error('Capture result correlation/status mismatch');
        const beforeConsumption = inventory();
        const chunks: string[] = [];
        for (let i = 0; i < result.bytes.length; i += 16384) chunks.push(String.fromCharCode(...result.bytes.subarray(i, i + 16384)));
        const base64 = btoa(chunks.join('')); entry.done = null; entry.allocatedCapacityBytes = 0; entry.frameBytes = 0; slot = null; consumed++;
        return { base64, metadata: { contextId: options.contextId, pageId, token, endpoint: result.endpoint, requestId, status: result.status,
          rawByteLength: result.bytes.byteLength, beforeConsumption, afterConsumption: inventory(),
          ownership: 'Logical browser test slot released; transfer/base64 and returned Node Buffer remain separately test-owned, never product-owned budgets' } };
      } finally { entry.done = null; entry.allocatedCapacityBytes = 0; entry.frameBytes = 0; slot = null; }
    },
    dispose(): void {
      disposed = true;
      if (slot?.reader) void slot.reader.cancel('Test capture cleanup').catch(() => undefined);
      if (slot) { slot.done = null; slot.allocatedCapacityBytes = 0; slot.frameBytes = 0; } slot = null;
      if (window.fetch === wrapped) window.fetch = original;
    },
    inventory,
  };
}
async function armSuccess(page: Page): Promise<string> { return page.evaluate(() => (window as any).__ptSuccessCapture.arm()); }
async function successBytes(page: Page, token: string, requestId: string): Promise<Buffer> {
  const captured = await page.evaluate(({ token, requestId }) => (window as any).__ptSuccessCapture.take(token, requestId), { token, requestId });
  const bytes = Buffer.from(captured.base64, 'base64');
  save(`${requestId}_transport_capture`, { ...captured.metadata, returnedNodeBufferBytes: bytes.byteLength,
    timing: 'Test clone/stream/serialization instrumentation may affect timing; this is not a browser/native-memory ceiling' });
  return bytes;
}
async function single(page: Page, label: string): Promise<{ state: any; bytes: Buffer; request: any }> {
  const token = await armSuccess(page);
  const waiting = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v2g/simulate' && r.request().method() === 'POST');
  await page.getByTestId('pt-simulate').click(); const response = await waiting; expect(response.status()).toBe(200);
  const request = JSON.parse(response.request().postData()!), bytes = await successBytes(page, token, request.request_id); saveFrame(label, bytes); save(`${label}_request`, request);
  await expect.poll(async () => (await pt(page)).currentResult?.requestId).toBe(request.request_id);
  return { state: await pt(page), bytes, request };
}
function frame(bytes: Buffer): { header: any; payload: Buffer } {
  expect(bytes.subarray(0, 8).toString('binary')).toBe('OHLABPT\0'); const size = bytes.readUInt32LE(8);
  return { header: JSON.parse(bytes.subarray(16, 16 + size).toString('utf8')), payload: bytes.subarray(16 + Math.ceil(size / 8) * 8) };
}
async function screenshot(page: Page, name: string): Promise<void> { mkdirSync(figures, { recursive: true }); writeFileSync(resolve(figures, name), await page.screenshot({ fullPage: true }), { flag: 'wx' }); }
test.beforeEach(async ({ page, context }, testInfo) => {
  if (!/^[A-Za-z0-9_-]+$/.test(testInfo.testId)) throw new Error('Unsafe test ID for exclusive case evidence');
  mkdirSync(evidenceBase, { recursive: true }); mkdirSync(figuresBase, { recursive: true });
  evidence = resolve(evidenceBase, testInfo.testId); figures = resolve(figuresBase, testInfo.testId);
  mkdirSync(evidence); mkdirSync(figures);
  await context.addInitScript(installSuccessCapture, { contextId: randomUUID(), disabledCap: MAX_POLARIZED_TWO_PATH_DISABLED_RESPONSE_BYTES,
    enabledCap: MAX_POLARIZED_TWO_PATH_RESPONSE_BYTES, headerCap: MAX_POLARIZED_TWO_PATH_HEADER_BYTES });
  await page.route('**/*', route => new URL(route.request().url()).origin === 'http://127.0.0.1:8510' ? route.continue() : route.abort('blockedbyclient'));
});
test.afterEach(async ({ context }) => {
  for (const page of context.pages()) if (!page.isClosed()) await page.evaluate(() => (window as any).__ptSuccessCapture?.dispose());
  evidence = evidenceBase; figures = figuresBase;
});

test('genuine raw/analyzed ports, joint scale, original readouts and 17 independent phase rows', async ({ page, browser }) => {
  test.skip(controlledOnly); await load(page); await preset(page, 'orthogonal_analyzed');
  await edit(page, 'grid.nx', '32'); await edit(page, 'grid.ny', '32'); await edit(page, 'relative_phase_rad', String(Math.PI / 2)); await ready(page);
  const actual = await single(page, smoke ? 'postcommit_single' : 'genuine_orthogonal_analyzed');
  expect(actual.state.currentResult.diagnostics.output_fractions[0]).toBeCloseTo(.5, 13);
  expect(actual.state.currentResult.diagnostics.output_fractions[1]).toBeCloseTo(.5, 13);
  expect(actual.state.currentResult.analysis.total_original_input_ratio).toBeCloseTo(.5, 13);
  expect(actual.state.currentResult.analysis.ports.map((p: any) => p.original_input_ratio)).toEqual(expect.arrayContaining([expect.any(Number), expect.any(Number)]));
  for (const view of ['raw', 'analyzed']) for (const port of [0, 1]) await expect(page.getByTestId(`pt-intensity-${view}-${port}`)).toBeVisible();
  const passive = posts(page), original = actual.state.currentResult;
  await page.getByTestId('pt-view').selectOption('analyzed'); await frames(page);
  expect((await snap(page)).scene.polarizedTwoPath).toMatchObject({ view: 'analyzed', textureRequestIds: [original.requestId, original.requestId], retainedRoles: 4 });
  await page.getByTestId('pt-intensity-analyzed-1').click({ position: { x: 20, y: 20 } });
  const picked = (await pt(page)).selectedPixel, decoded = frame(actual.bytes), role = decoded.header.arrays.find((a: any) => a.name === 'analyzed_port_1_intensity');
  expect(picked.view).toBe('analyzed'); expect(picked.port).toBe(1);
  expect(picked.intensity).toBe(decoded.payload.readDoubleLE(role.offset_bytes + 8 * (picked.row * 32 + picked.column)));
  await page.getByTestId('pt-view').selectOption('raw'); await page.getByTestId('pt-auto-color').click(); await frames(page);
  await page.getByTestId('bench-host').scrollIntoViewIfNeeded(); await frames(page);
  const projected = await page.evaluate(() => { const world = window.__benchDebug.polarizedTwoPathPixelWorld(1, 5, 7); return world ? window.__benchDebug.worldToClient(world.x, world.y, world.z) : null; });
  expect(projected?.visible).toBe(true); await page.mouse.click(projected!.x, projected!.y);
  await expect.poll(async () => (await pt(page)).selectedPixel?.port).toBe(1);
  expect((await pt(page)).selectedPixel).toMatchObject({ view: 'raw', row: 5, column: 7, requestId: original.requestId });
  expect((await pt(page)).currentResult).toEqual(original); expect(passive).toEqual([]);
  if (!smoke) await screenshot(page, 'fig01_raw_and_analyzed_outputs.png');
  const waiting = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v2g/sweep'); await page.getByTestId('pt-sweep').click();
  const response = await waiting; expect(response.status()).toBe(200); const rawSweep = await response.json(); save(smoke ? 'postcommit_sweep_response' : 'genuine_sweep_response', rawSweep);
  await expect.poll(async () => (await pt(page)).lastSweep?.completedCount).toBe(17);
  const sweep = (await pt(page)).lastSweep; expect(sweep.status).toBe('complete'); expect(sweep.rows.map((r: any) => r.index)).toEqual(Array.from({ length: 17 }, (_, i) => i));
  expect(sweep.rows[0].phase_rad).toBe(0); expect(sweep.rows[16].phase_rad).toBe(2 * Math.PI);
  expect(sweep.rows[0].analysis.ports[0].original_input_ratio).toBeCloseTo(.5, 13);
  expect(sweep.rows[8].analysis.ports[1].original_input_ratio).toBeCloseTo(.5, 13);
  const beforeMarker = passive.length; await page.getByTestId('pt-sweep-point-raw0-8').dispatchEvent('click');
  expect((await pt(page)).selectedSweepIndex).toBe(8); expect(passive.length).toBe(beforeMarker);
  if (!smoke) await screenshot(page, 'fig02_actual_phase_sweep.png');
  const selected = await singleSelected(page, smoke ? 'postcommit_selected_phase' : 'genuine_selected_phase');
  expect(selected.currentResult.experiment.relative_phase_rad).toBe(Math.PI);
  save(smoke ? 'postcommit_production_outcome' : 'production_raw_analyzed_sweep', { browserVersion: browser.version(), actual: actual.state, picked, sweep, selected, passive,
    claims: ['actual production public compositions', 'full frames preserved for independent direct-public checker', 'view/scale/pick and marker selection do no optics'] });
});
async function singleSelected(page: Page, label: string): Promise<any> {
  const token = await armSuccess(page);
  const waiting = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v2g/simulate'); await page.getByTestId('pt-simulate-phase').click();
  const response = await waiting; expect(response.status()).toBe(200); const request = JSON.parse(response.request().postData()!);
  saveFrame(label, await successBytes(page, token, request.request_id)); save(`${label}_request`, request); await expect.poll(async () => (await pt(page)).currentResult?.requestId).toBe(request.request_id); return pt(page);
}

test('real full Gaussian, complex coefficients and stable ordered actions remain effective', async ({ page }) => {
  test.skip(smoke || controlledOnly); await load(page); await preset(page, 'identical');
  await page.getByTestId('pt-source-kind').selectOption('gaussian'); await ready(page);
  for (const [path, value] of Object.entries({ 'grid.nx': '17', 'grid.ny': '16', 'source.waist_radius_m': '0.000041', 'source.waist_z_m': '-0.0007',
    'source.center_x_m': '0.000012', 'source.center_y_m': '-0.000008', 'source.phase_rad': '.37', 'coefficients.x.re': '.7', 'coefficients.x.im': '.2',
    'coefficients.y.re': '-.3', 'coefficients.y.im': '.4', 'relative_phase_rad': '-7.123456789012345', 'arm_0.distance_m': '.0013', 'arm_1.distance_m': '.0021' })) await edit(page, path, value);
  for (const port of [0, 1]) {
    await page.getByTestId(`pt-add-kind-${port}`).selectOption('linear_retarder'); await page.getByTestId(`pt-add-${port}`).click(); await ready(page);
    await page.getByTestId(`pt-add-kind-${port}`).selectOption('linear_polarizer'); await page.getByTestId(`pt-add-${port}`).click(); await ready(page);
  }
  const before = await pt(page), id = before.candidate.arm_0.actions[1].id;
  await page.getByTestId(`pt-up-${id}`).click(); await ready(page); expect((await pt(page)).candidate.arm_0.actions.map((a: any) => a.id)).toEqual(before.candidate.arm_0.actions.map((a: any) => a.id).reverse());
  await edit(page, 'arm_0.actions.0.axis_angle_rad', '.42'); await edit(page, 'arm_0.actions.1.axis_angle_rad', '-.31');
  await edit(page, 'arm_1.actions.0.axis_angle_rad', '.17'); await edit(page, 'arm_1.actions.1.axis_angle_rad', '-.29');
  const retarder = (await pt(page)).candidate.arm_0.actions[1].id; await page.getByTestId(`pt-hwp-${retarder}`).click(); await ready(page);
  await page.getByTestId('pt-analyzer-enabled').check(); await ready(page); await edit(page, 'analyzer.axis_angle_rad', '.61'); await ready(page);
  const actual = await single(page, 'genuine_full_gaussian_actions'); expect(actual.state.currentResult.experiment.source.waist_z_m).toBe(-.0007);
  expect(actual.state.currentResult.norms.arm_action_norms.map((a: any[]) => a.length)).toEqual([2, 2]);
  const remove = (await pt(page)).candidate.arm_1.actions[1].id; await page.getByTestId(`pt-delete-${remove}`).click(); await ready(page);
  expect((await pt(page)).currentResult).toBeNull(); expect((await pt(page)).lastResult.requestId).toBe(actual.state.currentResult.requestId);
  expect((await pt(page)).candidate.arm_1.actions[0].id).toBe(before.candidate.arm_1.actions[0].id);
  save('production_gaussian_action_order', { before, actual: actual.state, afterDelete: await pt(page) });
});

test('genuine weak signal, numerical failure and stale late responses require deliberate recovery', async ({ page }) => {
  test.skip(smoke || controlledOnly); await load(page); await preset(page, 'identical');
  await edit(page, 'arm_0.distance_m', '0'); await edit(page, 'arm_1.distance_m', '0'); await edit(page, 'relative_phase_rad', '1e-9'); await ready(page);
  const weak = await single(page, 'genuine_weak'); expect(weak.state.currentResult.diagnostics.output_fractions[1]).toBeGreaterThan(0);
  expect(Math.abs(weak.state.currentResult.diagnostics.output_fractions[1] / 2.5e-19 - 1)).toBeLessThanOrEqual(2e-13);
  await edit(page, 'source.amplitude', '1e300'); await ready(page); const requestPaths = posts(page);
  await page.getByTestId('pt-simulate').click(); await expect.poll(async () => (await pt(page)).active).toBeNull();
  const numerical = await pt(page); expect(numerical.error).toBeTruthy(); expect(numerical.currentResult).toBeNull();
  expect(requestPaths.filter(compute)).toHaveLength(1); await preset(page, 'identical');
  await edit(page, 'grid.nx', '32'); await edit(page, 'grid.ny', '32'); await edit(page, 'arm_0.distance_m', '0'); await edit(page, 'arm_1.distance_m', '0');
  await edit(page, 'source.amplitude', '1e-150'); await page.getByTestId('pt-analyzer-enabled').check(); await ready(page);
  await edit(page, 'analyzer.axis_angle_rad', String(Math.PI / 2)); await ready(page);
  const analyzerWait = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v2g/simulate'); await page.getByTestId('pt-simulate').click();
  const analyzerResponse = await analyzerWait; expect(analyzerResponse.status()).toBe(422); const analyzerReply = await analyzerResponse.json();
  await expect.poll(async () => (await pt(page)).active).toBeNull(); const analyzerFailure = await pt(page);
  expect(analyzerFailure.currentResult).toBeNull(); expect(analyzerFailure.error).toBeTruthy(); expect(analyzerReply.error.message).toMatch(/analy|underflow|port/i);
  expect(requestPaths.filter(compute)).toHaveLength(2); await preset(page, 'identical');
  let received = false, release!: () => void; const held = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/v2g/simulate', async route => { const reply = await route.fetch(); received = true; await held; await route.fulfill({ response: reply }); }, { times: 1 });
  await page.getByTestId('pt-simulate').evaluate((button: HTMLButtonElement) => { button.click(); button.click(); });
  await expect.poll(() => received).toBe(true); await expect(page.getByTestId('release-results')).toBeDisabled();
  const count = (await snap(page)).resultRelease.count; await page.getByTestId('release-results').dispatchEvent('click'); expect((await snap(page)).resultRelease.count).toBe(count);
  await page.getByTestId('mode').selectOption('sequential'); await page.getByTestId('mode').selectOption('two_path');
  await page.getByTestId('mode').selectOption('polarization'); await page.getByTestId('mode').selectOption('polarized_two_path'); release();
  await expect.poll(async () => (await pt(page)).active).toBeNull(); await ready(page); expect((await pt(page)).currentResult).toBeNull();
  expect(requestPaths.filter(compute)).toHaveLength(3); const recovered = await single(page, 'genuine_stale_recovery');
  save('production_weak_failure_stale_recovery', { weak: weak.state, numerical, analyzerFailure, analyzerReply, recovered: recovered.state, requestPaths });
});

test('controlled later preparation rollback and actual context loss retain whole numerical outcomes', async ({ page }) => {
  test.skip(smoke || controlledOnly); await load(page); await preset(page, 'orthogonal_analyzed'); const original = await single(page, 'genuine_before_display_fault');
  const before = await snap(page), requests = posts(page);
  await page.evaluate(() => {
    const prototype = HTMLCanvasElement.prototype as any, original = prototype.getContext; let calls = 0;
    prototype.getContext = function(kind: string, ...args: unknown[]) {
      if (kind === '2d' && ++calls === 4) { prototype.getContext = original; throw new Error('Controlled fourth-canvas preparation failure'); }
      return original.call(this, kind, ...args);
    }; (window as any).__restoreV2gCanvas = () => { prototype.getContext = original; };
  });
  await page.getByTestId('pt-simulate').click(); await expect.poll(async () => (await pt(page)).active).toBeNull(); await page.evaluate(() => (window as any).__restoreV2gCanvas());
  const failed = await pt(page); expect(failed.renderError).toBeTruthy(); expect(failed.completedNumerical.requestId).not.toBe(original.request.request_id);
  expect(failed.currentResult.requestId).toBe(original.request.request_id); expect((await snap(page)).scene.polarizedTwoPath.textureRequestIds).toEqual([original.request.request_id, original.request.request_id]);
  expect((await snap(page)).scene.owned).toEqual(before.scene.owned); expect(requests.filter(compute)).toHaveLength(1);
  await page.getByTestId('pt-retry-display').click(); await expect.poll(async () => (await pt(page)).currentResult?.requestId).toBe(failed.completedNumerical.requestId);
  expect(requests.filter(compute)).toHaveLength(1); const restored = await pt(page);
  await page.getByTestId('bench-canvas').evaluate((canvas: HTMLCanvasElement) => {
    const extension = canvas.getContext('webgl2')!.getExtension('WEBGL_lose_context'); if (!extension) throw new Error('Required context-loss extension unavailable');
    (window as any).__v2gContextLossExtension = extension; extension.loseContext();
  });
  await expect(page.getByTestId('pt-render-error')).toBeVisible(); const lost = await pt(page); expect(lost.completedNumerical).not.toBeNull(); expect(requests.filter(compute)).toHaveLength(1);
  await page.evaluate(() => (window as any).__v2gContextLossExtension.restoreContext());
  await expect.poll(async () => (await snap(page)).scene.contextLost).toBe(false);
  expect((await pt(page)).currentResult).toBeNull(); expect((await pt(page)).completedNumerical).toEqual(lost.completedNumerical);
  expect(requests.filter(compute)).toHaveLength(1); await page.getByTestId('pt-retry-display').click();
  await expect.poll(async () => (await pt(page)).currentResult?.requestId).toBe(restored.currentResult.requestId);
  expect(requests.filter(compute)).toHaveLength(1); const contextRecovered = await pt(page);
  save('controlled_display_rollback_actual_context_loss', { before, failed, restored, lost, contextRecovered, requests, classification: 'real production numerical results, temporary browser-only fourth-canvas fault; genuine WebGL loss/restore and explicit display retry without optics' });
});

test('controlled DOM and second-screen mutations roll back complete presentation; measured geometry growth rejects', async ({ page }) => {
  test.skip(smoke || controlledOnly); test.setTimeout(120_000);
  await load(page); await preset(page, 'orthogonal_analyzed'); await single(page, 'genuine_before_commit_faults');
  await page.getByTestId('pt-intensity-raw-1').click({ position: { x: 20, y: 20 } });
  const outcomes = [];
  for (const kind of ['dom', 'scene', 'readout'] as const) {
    const before = await snap(page), markup = await page.locator('#pt-current-content').innerHTML(), requests = posts(page);
    if (kind === 'dom') await page.evaluate(() => {
      const prototype = Element.prototype, original = prototype.replaceChildren;
      prototype.replaceChildren = function(...nodes: (Node | string)[]) {
        original.apply(this, nodes);
        if (this.id === 'pt-current-content') { prototype.replaceChildren = original; throw new Error('Controlled failure after real result DOM replacement'); }
      };
    });
    else if (kind === 'scene') await page.evaluate(() => {
      const prototype = Array.prototype as any, original = prototype.entries; let oldMaps: unknown[] | null = null;
      prototype.entries = function() {
        const iterator = original.call(this), meshes = this;
        const pair = Array.isArray(meshes) && meshes.length === 2 && meshes.every((mesh: any, index: number) => mesh?.userData?.polarizedTwoPathPort === index);
        if (pair && !oldMaps) oldMaps = meshes.map((mesh: any) => mesh.material.map);
        return { [Symbol.iterator]() { return this; }, next() {
          const item = iterator.next();
          if (pair && item.done && oldMaps && meshes.some((mesh: any, index: number) => mesh.material.map !== oldMaps![index])) {
            prototype.entries = original;
            throw new Error('Controlled failure after real second-screen map mutation');
          }
          return item;
        } };
      };
    });
    else await page.evaluate(() => {
      const descriptor = Object.getOwnPropertyDescriptor(Node.prototype, 'textContent')!;
      Object.defineProperty(Node.prototype, 'textContent', { ...descriptor, set(value: string | null) {
        descriptor.set!.call(this, value);
        if (this instanceof HTMLElement && this.id === 'pt-pixel-readout') {
          Object.defineProperty(Node.prototype, 'textContent', descriptor); throw new Error('Controlled failure after real readout mutation');
        }
      } });
    });
    const waiting = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v2g/simulate'); await page.getByTestId('pt-simulate').click();
    const response = await waiting; expect(response.status()).toBe(200); saveFrame(`genuine_${kind}_commit_failure`, await response.body());
    await expect.poll(async () => (await pt(page)).active).toBeNull(); const failed = await snap(page);
    expect(failed.polarizedTwoPath.renderError).toMatch(/Controlled failure/); expect(failed.polarizedTwoPath.currentResult).toEqual(before.polarizedTwoPath.currentResult);
    expect(failed.polarizedTwoPath.selectedPixel).toEqual(before.polarizedTwoPath.selectedPixel);
    expect(failed.scene.polarizedTwoPath.textureRequestIds).toEqual(before.scene.polarizedTwoPath.textureRequestIds); expect(failed.scene.owned).toEqual(before.scene.owned);
    expect(await page.locator('#pt-current-content').innerHTML()).toBe(markup); expect(requests.filter(compute)).toHaveLength(1);
    await page.getByTestId('pt-retry-display').click(); await expect.poll(async () => (await pt(page)).currentResult?.requestId).toBe(failed.polarizedTwoPath.completedNumerical.requestId);
    expect(requests.filter(compute)).toHaveLength(1); outcomes.push({ kind, before, failed, restored: await snap(page), requests });
  }
  const beforeGeometry = await snap(page), requests = posts(page);
  await page.evaluate(() => {
    const NativeFloat32Array = globalThis.Float32Array;
    globalThis.Float32Array = new Proxy(NativeFloat32Array, { construct(target, args) {
      if (Array.isArray(args[0]) && args[0].length > 32) {
        globalThis.Float32Array = NativeFloat32Array;
        const actual = new NativeFloat32Array(65536); actual.set(args[0]); return actual;
      }
      return Reflect.construct(target, args);
    } }); (window as any).__restoreV2gGeometry = () => { globalThis.Float32Array = NativeFloat32Array; };
  });
  await edit(page, 'arm_0.distance_m', '.002001'); await page.evaluate(() => (window as any).__restoreV2gGeometry());
  const geometryFailure = await snap(page); expect(geometryFailure.polarizedTwoPath.renderError).toMatch(/131072-byte reservation/);
  expect(geometryFailure.scene.owned.geometrySourceBytes).toBe(beforeGeometry.scene.owned.geometrySourceBytes);
  expect(geometryFailure.scene.owned.geometries).toBe(beforeGeometry.scene.owned.geometries); expect(geometryFailure.scene.camera).toEqual(beforeGeometry.scene.camera);
  expect(requests.filter(compute)).toEqual([]);
  const recovered = await single(page, 'genuine_geometry_failure_recovery');
  save('controlled_commit_rollback_and_geometry_reservation', { outcomes, beforeGeometry, geometryFailure, recovered: recovered.state,
    classification: 'temporary browser-only DOM/material mutation-then-throw controls and one actual oversized geometry backing buffer; no optical mutation or budget increase' });
});

test('explicit all-mode release drops every result owner and keeps drafts, invalid text, documents and camera', async ({ page }) => {
  test.skip(controlledOnly);
  await page.addInitScript(() => {
    const prototype = EventTarget.prototype, original = prototype.addEventListener;
    prototype.addEventListener = function(type: string, callback: EventListenerOrEventListenerObject | null, options?: boolean | AddEventListenerOptions) {
      if (type === 'click' && this instanceof HTMLCanvasElement && this.dataset.testid === 'pt-intensity-raw-0' && typeof callback === 'function') {
        (window as any).__releasedV2gCanvas = this; (window as any).__oldV2gPresentationClick = callback;
        prototype.addEventListener = original;
      }
      original.call(this, type, callback, options);
    };
  });
  await load(page); await preset(page, 'orthogonal_analyzed'); await single(page, smoke ? 'postcommit_before_release' : 'genuine_before_release');
  await page.getByTestId('documents').evaluate((node: HTMLDetailsElement) => { node.open = true; });
  await page.getByTestId('doc-title').fill('釋放保留設定 😀'); await page.getByTestId('doc-notes').fill('文件與相機不可被釋放。');
  await page.getByTestId('doc-export').click(); await expect(page.getByTestId('doc-download-area')).toBeVisible();
  const prepared = await snap(page);
  await page.evaluate(() => { const canvas = (window as any).__releasedV2gCanvas as HTMLCanvasElement; (window as any).__oldV2gPresentationRect = canvas.getBoundingClientRect().toJSON(); });
  await edit(page, 'coefficients.x.re', '-');
  await page.getByTestId('zoom-in').click(); await page.getByTestId('pan-left').click(); await frames(page, 20);
  const before = await snap(page), requests = posts(page);
  await page.locator('.release-panel summary').click(); await page.getByTestId('release-results').click(); await frames(page);
  const after = await snap(page);
  for (const key of ['candidate', 'validatedDraft', 'invalidEdits', 'revision', 'attachmentEpoch']) expect(after.polarizedTwoPath[key]).toEqual(before.polarizedTwoPath[key]);
  for (const key of ['candidate', 'validatedDraft', 'invalidEdits', 'revision']) { expect(after[key]).toEqual(before[key]); expect(after.twoPath[key]).toEqual(before.twoPath[key]); expect(after.polarization[key]).toEqual(before.polarization[key]); }
  expect(after.documents, 'V2G_RELEASE_USEFUL_DOCUMENT_DETECTED').toEqual(before.documents); expect(after.scene.camera).toEqual(before.scene.camera); expect(after.ownedMemory.documentBytes).toBe(before.ownedMemory.documentBytes);
  expect(after.ownedMemory.scientificBytes, 'V2G_RELEASE_ALL_OWNERS_DETECTED').toBe(0); expect(after.scene.owned.textureSourceBytes).toBe(0); expect(after.scene.owned.controls).toBe(1);
  for (const state of [after, after.twoPath, after.polarization, after.polarizedTwoPath]) { expect(state.lastResult).toBeNull(); expect(state.currentResult).toBeNull(); if ('completedNumerical' in state) expect(state.completedNumerical).toBeNull(); if ('lastSweep' in state) expect(state.lastSweep).toBeNull(); }
  expect(after.polarization.animation.activeOwners).toBe(0); expect(after.scene.polarization.frameCallbacks).toBe(0);
  expect(requests).toEqual([]); await expect(page.getByTestId('pt-edit-coefficients-x-re')).toHaveValue('-');
  await page.evaluate(() => {
    const canvas = (window as any).__releasedV2gCanvas as HTMLCanvasElement, callback = (window as any).__oldV2gPresentationClick as EventListener;
    if (!canvas || !callback) throw new Error('Actual earlier presentation callback was not captured');
    const rect = (window as any).__oldV2gPresentationRect;
    canvas.getBoundingClientRect = () => new DOMRect(rect.x, rect.y, rect.width, rect.height);
    callback.call(canvas, new MouseEvent('click', { clientX: rect.x + rect.width / 2, clientY: rect.y + rect.height / 2 }));
  });
  expect((await pt(page)).selectedPixel, 'V2G_RELEASE_OLD_CALLBACK_DETECTED').toBeNull(); expect((await snap(page)).ownedMemory.scientificBytes).toBe(0);
  await page.getByTestId('release-results').click(); expect((await snap(page)).ownedMemory.scientificBytes).toBe(0); expect(requests).toEqual([]);
  await page.getByTestId('pt-edit-coefficients-x-re').fill('1'); await page.getByTestId('pt-edit-coefficients-x-re').blur(); await ready(page);
  const recovered = await single(page, smoke ? 'postcommit_after_release' : 'genuine_after_release');
  expect(recovered.state.currentResult.requestId).not.toBe(prepared.polarizedTwoPath.currentResult.requestId);
  save(smoke ? 'postcommit_release_recovery' : 'production_release_recovery', { before, after, recovered: recovered.state, requests,
    classification: 'actual result ownership/release; preserved prepared document, invalid editor, metadata and live camera; detached canvas callback cannot reattach' });
});

test('separately controlled first/interior/final sweep failure contains only genuine complete prefixes', async ({ page }) => {
  const path = process.env.V2G_PARTIAL_EVIDENCE; test.skip(!path, 'Requires explicitly launched separately owned controlled server; no production fault endpoint.');
  const expected = JSON.parse(readFileSync(resolve(root, path!), 'utf8'));
  await load(page); await preset(page, 'orthogonal_analyzed'); const requests = posts(page);
  await page.getByTestId('pt-sweep').click(); await expect.poll(async () => !!(await pt(page)).lastSweep).toBe(true); const actual = (await pt(page)).lastSweep;
  const reply = expected.reply ?? expected; expect(actual.status).toBe('failed'); expect(actual.completedCount).toBe(reply.completed_count);
  expect(actual.rows).toEqual(reply.rows); expect(actual.failedIndex).toBe(reply.failed_index);
  expect(actual.rows.map((row: any) => row.index)).toEqual(Array.from({ length: actual.completedCount }, (_, i) => i));
  expect(requests.filter(compute)).toEqual(['/api/v2g/sweep']); await expect(page.getByTestId('pt-sweep-status')).toContainText('FAILED / PARTIAL');
  save(`controlled_partial_${actual.failedIndex}`, { actual, requests });
});

test('actual all-mode ownership reaches fixed admission budget, then explicit release recovers without eviction or retry', async ({ page }) => {
  test.skip(smoke || controlledOnly); test.setTimeout(120_000); await page.goto('/');
  const waitOld = async (id: string, path: string) => {
    await expect(page.getByTestId(id)).toBeEnabled(); const waiting = page.waitForResponse(r => new URL(r.url()).pathname === path);
    await page.getByTestId(id).click(); expect((await waiting).status()).toBe(200);
    await expect.poll(async () => { const s = await snap(page); return !(s.active || s.twoPath.active || s.polarization.active || s.polarizedTwoPath.active); }).toBe(true);
  };
  await waitOld('simulate', '/api/v1/simulate');
  await page.getByTestId('edit-wavelength_m').fill('-'); await page.getByTestId('edit-wavelength_m').blur();
  await page.getByTestId('mode').selectOption('two_path'); await expect(page.getByTestId('tp-simulate')).toBeEnabled();
  await waitOld('tp-sweep', '/api/v2b/sweep');
  for (const axis of ['nx', 'ny']) { await page.getByTestId(`tp-edit-grid-${axis}`).fill('512'); await page.getByTestId(`tp-edit-grid-${axis}`).blur(); await expect(page.getByTestId('tp-simulate')).toBeEnabled(); }
  await waitOld('tp-simulate', '/api/v2b/simulate');
  await page.getByTestId('mode').selectOption('polarization'); await expect(page.getByTestId('pl-simulate')).toBeEnabled();
  for (const axis of ['nx', 'ny']) { await page.getByTestId(`pl-edit-grid-${axis}`).fill('128'); await page.getByTestId(`pl-edit-grid-${axis}`).blur(); await expect(page.getByTestId('pl-simulate')).toBeEnabled(); }
  await waitOld('pl-simulate', '/api/v2d/simulate'); await page.getByTestId('pl-select-p1').click(); await waitOld('pl-sweep', '/api/v2d/sweep');
  await page.getByTestId('pl-edit-source-phase_rad').fill('-'); await page.getByTestId('pl-edit-source-phase_rad').blur();
  await page.getByTestId('mode').selectOption('polarized_two_path'); await ready(page); await preset(page, 'orthogonal_analyzed');
  await edit(page, 'grid.nx', '128'); await edit(page, 'grid.ny', '128'); await ready(page); await single(page, 'genuine_allmode_retained');
  await waitOld('pt-sweep', '/api/v2g/sweep'); await edit(page, 'coefficients.y.im', '-');
  await page.getByTestId('mode').selectOption('two_path'); await expect(page.getByTestId('tp-simulate')).toBeEnabled();
  await waitOld('tp-simulate', '/api/v2b/simulate');
  const before = await snap(page); for (const s of [before, before.twoPath, before.polarization, before.polarizedTwoPath]) expect(s.lastResult).not.toBeNull();
  for (const s of [before.twoPath, before.polarization, before.polarizedTwoPath]) expect(s.lastSweep).not.toBeNull();
  expect(before.ownedMemory.retainedBytes).toBeLessThanOrEqual(16 * 1024 * 1024); const requests = posts(page);
  await page.getByTestId('tp-simulate').click(); await expect.poll(async () => (await snap(page)).twoPath.error).toMatch(/budget/i);
  await expect.poll(async () => (await snap(page)).twoPath.active).toBeNull(); const failed = await snap(page);
  expect(failed.twoPath.completedNumerical).toEqual(before.twoPath.completedNumerical);
  expect(failed.twoPath.lastResult).toEqual(before.twoPath.lastResult); expect(failed.ownedMemory.scientificBytes).toBe(before.ownedMemory.scientificBytes);
  for (const [key, old] of [['lastResult', before.lastResult], ['polarization', before.polarization.lastResult], ['polarizedTwoPath', before.polarizedTwoPath.lastResult]] as const) {
    const current = key === 'lastResult' ? failed.lastResult : failed[key].lastResult; expect(current.requestId).toBe(old.requestId);
  }
  expect(requests.filter(compute)).toEqual([]); await frames(page, 20); expect(requests.filter(compute)).toHaveLength(0);
  await page.getByTestId('documents').evaluate((node: HTMLDetailsElement) => { node.open = true; });
  await page.getByTestId('doc-title').fill('all-mode fixed-budget recovery'); await page.getByTestId('doc-notes').fill('保留所有草稿與下載，不自動重算。');
  await page.getByTestId('doc-export').click(); await expect(page.getByTestId('doc-download-area')).toBeVisible();
  await page.getByTestId('tp-edit-two_arm_spec-arm_0_distance_m').fill('-'); await page.getByTestId('tp-edit-two_arm_spec-arm_0_distance_m').blur();
  const pendingRelease = await snap(page), count = requests.length;
  await page.locator('.release-panel summary').click(); await page.getByTestId('release-results').click(); const after = await snap(page);
  const stateList = (s: any) => [s, s.twoPath, s.polarization, s.polarizedTwoPath];
  for (let i = 0; i < 4; i++) {
    const a = stateList(pendingRelease)[i], b = stateList(after)[i];
    for (const key of ['candidate', 'validatedDraft', 'invalidEdits', 'revision']) expect(b[key]).toEqual(a[key]);
    expect(b.currentResult).toBeNull(); expect(b.lastResult).toBeNull(); if ('lastSweep' in b) expect(b.lastSweep).toBeNull(); if ('completedNumerical' in b) expect(b.completedNumerical).toBeNull();
  }
  expect(after.ownedMemory.scientificBytes).toBe(0); expect(after.scene.owned.textureSourceBytes).toBe(0);
  expect(after.documents).toEqual(pendingRelease.documents); expect(after.scene.camera).toEqual(pendingRelease.scene.camera);
  expect(requests.length).toBe(count); await frames(page, 20); expect(requests.length).toBe(count);
  await page.getByTestId('tp-edit-two_arm_spec-arm_0_distance_m').fill('2'); await page.getByTestId('tp-edit-two_arm_spec-arm_0_distance_m').blur();
  await waitOld('tp-simulate', '/api/v2b/simulate'); const recovered = await snap(page); expect(recovered.twoPath.currentResult).not.toBeNull(); expect(recovered.twoPath.renderError).toBeNull();
  expect(requests.filter(compute)).toHaveLength(1);
  save('production_allmode_fixed_budget_release', { before, failed, pendingRelease, after, recovered, requests,
    classification: 'actual production maximum-grid overlap; fixed early admission rejects the subsequent attempt before HTTP and preserves all existing owners; explicit release then one later deliberate solve, no eviction or automatic retry' });
});

test('separately controlled actual-browser disconnect holds all seven operations, while documents remain noncomputing', async ({ page, context }) => {
  const directory = process.env.V2G_HELD_DIR; test.skip(!directory, 'Requires a separately launched task-owned held-worker child; production has no fault or release endpoint.');
  test.setTimeout(90_000);
  const requested = process.env.V2G_HELD_OPERATION ?? 'single';
  const operation = requested === 'single' ? 'polarized_two_path' : requested === 'sweep' ? 'polarized_two_path_sweep' : requested;
  if (!['polarized_two_path', 'polarized_two_path_sweep'].includes(operation)) throw new Error('V2G_HELD_OPERATION must select one of the two approved new operations');
  const owned = resolve(root, directory!), releasePath = resolve(owned, 'release');
  if (!owned.startsWith(resolve(root, 'runs') + '\\') && !owned.startsWith(resolve(root, 'runs') + '/')) throw new Error('Held evidence must stay inside the owned repository runs directory');
  const release = () => { if (!existsSync(releasePath)) writeFileSync(releasePath, 'Explicit release after required actual browser disconnect and gate checks', { flag: 'wx' }); };
  let other: Page | null = null;
  try {
    await load(page); await preset(page, 'orthogonal_analyzed'); const experiment = (await pt(page)).validatedDraft;
    mkdirSync(evidence, { recursive: true }); const seed = resolve(evidence, `held_${operation}_settings.json`);
    writeFileSync(seed, JSON.stringify({ document_format: 'ohlab_virtual_experiment', document_version: 2, mode: 'polarized_two_path',
      model_contract: 'v2g_ideal_polarized_two_path_v1', experiment, metadata: { title: 'held worker document preview', notes: '設定驗證與套用不執行光學。' } }), { flag: 'wx' });
    await page.getByTestId('documents').evaluate((node: HTMLDetailsElement) => { node.open = true; });
    await page.getByTestId('doc-file').setInputFiles(seed); await expect(page.getByTestId('doc-preview')).toBeVisible();
    await page.getByTestId('doc-ack').check(); await expect(page.getByTestId('doc-apply')).toBeEnabled();
    const before = await snap(page), requests = posts(page);
    await page.getByTestId(operation === 'polarized_two_path' ? 'pt-simulate' : 'pt-sweep').click();
    await expect.poll(() => { try { return JSON.parse(readFileSync(resolve(owned, 'started.json'), 'utf8')).operation; } catch { return null; } }).toBe(operation);
    const started = JSON.parse(readFileSync(resolve(owned, 'started.json'), 'utf8'));
    await expect(page.getByTestId('doc-apply')).toBeDisabled(); await expect(page.getByTestId('release-results')).toBeDisabled();
    await page.getByTestId('doc-apply').dispatchEvent('click'); await page.getByTestId('release-results').dispatchEvent('click');
    const rechecked = await snap(page); expect(rechecked.polarizedTwoPath.candidate).toEqual(before.polarizedTwoPath.candidate);
    expect(rechecked.polarizedTwoPath.revision).toBe(before.polarizedTwoPath.revision); expect(rechecked.polarizedTwoPath.attachmentEpoch).toBe(before.polarizedTwoPath.attachmentEpoch);
    expect(rechecked.resultRelease.count).toBe(before.resultRelease.count); expect(rechecked.polarizedTwoPath.active).not.toBeNull();
    // Two-stage document validation remains responsive during the actual held worker.
    await page.getByTestId('doc-file').setInputFiles(seed); await expect(page.getByTestId('doc-preview')).toBeVisible();
    await page.getByTestId('doc-ack').check(); await expect(page.getByTestId('doc-apply')).toBeDisabled();
    expect(requests.filter(compute)).toEqual([operation === 'polarized_two_path' ? '/api/v2g/simulate' : '/api/v2g/sweep']);
    const busyPreview = await snap(page); expect(busyPreview.documents.state.preview.document.document_version).toBe(2);
    expect(await page.evaluate(async () => (await (await fetch('/api/v1/health')).json()).busy)).toBe(true);
    await page.close();
    other = await context.newPage(); await other.route('**/*', route => new URL(route.request().url()).origin === 'http://127.0.0.1:8510' ? route.continue() : route.abort('blockedbyclient'));
    await other.goto('/'); await expect(other.getByTestId('simulate')).toBeEnabled();
    const rejected = await other.evaluate(async ({ experiment, phases, angles }) => {
      const post = async (path: string, body: unknown) => {
        const response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        const contentType = response.headers.get('content-type') ?? '';
        return { path, status: response.status, body: contentType.includes('json') ? await response.json() : { unexpected_non_json_bytes: (await response.arrayBuffer()).byteLength } };
      };
      const source = { kind: 'uniform', amplitude: 1, phase_rad: 0 }, grid = { ny: 3, nx: 4, dy: 4e-6, dx: 4e-6 };
      const legacy = { schema_version: 1, model_contract: 'v0_aligned_scalar_forward_v1', wavelength_m: 633e-9, grid, source, components: [], observation: { id: 'screen', z_m: 0 } };
      const dual = { wavelength_m: 633e-9, grid, source, two_arm_spec: { arm_0_distance_m: .002, arm_1_distance_m: .002, relative_phase_rad: 0 } };
      const pol = { schema_version: 1, model_contract: 'v2d_ideal_jones_same_plane_v1', wavelength_m: 633e-9, grid, source,
        coefficients: { x: { re: 1, im: 0 }, y: { re: 0, im: 0 } }, elements: [{ id: 'p1', kind: 'linear_polarizer', axis_angle_rad: 0 }], readout: { row: 0, column: 0 } };
      const ptRequest = { protocol_version: 1, message_type: 'polarized_two_path_submission', request_id: crypto.randomUUID(), experiment_sha256: null, experiment };
      const { relative_phase_rad: _phase, ...fixed } = experiment;
      const sweepRequest = { protocol_version: 1, message_type: 'polarized_two_path_sweep_submission', request_id: crypto.randomUUID(), fixed_experiment_sha256: null, fixed_experiment: fixed, phases_rad: phases };
      const polRequest = { protocol_version: 1, message_type: 'polarization_submission', request_id: crypto.randomUUID(), experiment_sha256: null, experiment: pol };
      const validation = [await post('/api/v1/validate', { request_id: crypto.randomUUID(), experiment: legacy }),
        await post('/api/v2b/validate', { protocol_version: 1, message_type: 'two_path_submission', request_id: crypto.randomUUID(), experiment: dual }),
        await post('/api/v2d/validate', polRequest), await post('/api/v2g/validate', ptRequest), await post('/api/v2g/validate', sweepRequest)];
      const v2Document = { document_format: 'ohlab_virtual_experiment', document_version: 2, mode: 'polarized_two_path', model_contract: 'v2g_ideal_polarized_two_path_v1',
        experiment, metadata: { title: 'responsive while disconnected worker holds gate', notes: '' } };
      const document = await post('/api/v2e/documents/validate', v2Document);
      const legacyDocument = await post('/api/v2e/documents/validate', { document_format: 'ohlab_virtual_experiment', document_version: 1,
        mode: 'sequential', model_contract: 'v0_aligned_scalar_forward_v1', experiment: legacy, metadata: { title: 'legacy settings validation while busy', notes: '' } });
      const operations = [
        ['/api/v1/simulate', { request_id: crypto.randomUUID(), experiment: legacy }],
        ['/api/v2b/simulate', { protocol_version: 1, message_type: 'two_path_submission', request_id: crypto.randomUUID(), experiment: dual }],
        ['/api/v2b/sweep', { protocol_version: 1, message_type: 'two_path_sweep_submission', request_id: crypto.randomUUID(), fixed_experiment:
          { wavelength_m: dual.wavelength_m, grid, source, arm_0_distance_m: .002, arm_1_distance_m: .002 }, phases_rad: phases }],
        ['/api/v2d/simulate', { ...polRequest, request_id: crypto.randomUUID(), experiment_sha256: validation[2].body.experiment_sha256 }],
        ['/api/v2d/sweep', { ...polRequest, message_type: 'polarization_sweep_submission', request_id: crypto.randomUUID(), experiment_sha256: validation[2].body.experiment_sha256, selected_element_id: 'p1', angles_rad: angles }],
        ['/api/v2g/simulate', { ...ptRequest, request_id: crypto.randomUUID(), experiment_sha256: validation[3].body.experiment_sha256 }],
        ['/api/v2g/sweep', { ...sweepRequest, request_id: crypto.randomUUID(), fixed_experiment_sha256: validation[4].body.fixed_experiment_sha256 }],
      ] as const;
      const contenders = []; for (const [path, body] of operations) contenders.push(await post(path, body));
      return { validation, document, legacyDocument, contenders, health: await (await fetch('/api/v1/health')).json() };
    }, { experiment, phases: [...SWEEP_PHASES_RAD], angles: [...SWEEP_ANGLES_RAD] });
    expect(rejected.validation.map((row: any) => row.status)).toEqual([200, 200, 200, 200, 200]); expect(rejected.document.status).toBe(200); expect(rejected.legacyDocument.status).toBe(200);
    expect(rejected.contenders.map((row: any) => row.status)).toEqual([409, 409, 409, 409, 409, 409, 409]); expect(rejected.health.busy).toBe(true);
    expect(existsSync(resolve(owned, 'completed.json'))).toBe(false); release();
    await expect.poll(() => existsSync(resolve(owned, 'completed.json'))).toBe(true);
    await expect.poll(async () => other!.evaluate(async () => (await (await fetch('/api/v1/health')).json()).busy)).toBe(false);
    const completed = JSON.parse(readFileSync(resolve(owned, 'completed.json'), 'utf8')), points = operation === 'polarized_two_path' ? 1 : 17;
    expect(completed.request_id).toBe(started.request_id); expect(completed.operation).toBe(operation); expect(completed.exception).toBeNull();
    expect(completed.counts).toEqual({ sample_attempts: 1, jones_constructions: 1, runner_attempts: points, runner_completed: points, analyzer_attempts: 2 * points, analyzer_completed: 2 * points });
    expect(completed.actual_runner_phases).toEqual(operation === 'polarized_two_path' ? [experiment.relative_phase_rad] : [...SWEEP_PHASES_RAD]);
    await other.getByTestId('mode').selectOption('polarized_two_path'); await ready(other); await preset(other, 'orthogonal_analyzed');
    const recovered = await single(other, `genuine_held_${operation}_recovery`);
    expect(recovered.request.request_id).not.toBe(started.request_id);
    save(`controlled_browser_held_${operation}`, { started, before, rechecked, busyPreview, actualInitiatingPageClosed: true, rejected, completed, recovered: recovered.state,
      classification: 'separately owned held-worker child; actual initiating browser page disconnected; all seven valid contenders rejected until actual worker/Future completion; documents and validation execute no optics' });
  } finally { release(); if (other && !other.isClosed()) await other.close(); }
});
