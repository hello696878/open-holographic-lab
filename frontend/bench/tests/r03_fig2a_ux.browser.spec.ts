/** Genuine UXV1 acceptance: presentation changes preserve the submitted science. */
import { test, expect, chromium, type Page } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { createHash } from 'node:crypto';

const root = resolve('../..');
const evidenceRoot = resolve(root, process.env.R03_UX_EVIDENCE_DIR ?? 'runs/research_workspace_ux_v1_01/browser/ux');
let evidence = evidenceRoot;
test.beforeEach(async ({}, info) => {
  mkdirSync(evidenceRoot, { recursive: true });
  evidence = resolve(evidenceRoot, createHash('sha256').update(info.testId).digest('hex'));
  mkdirSync(evidence); // Exclusive case destination; preserve any earlier invocation.
});
const actual = (page: Page): Promise<any> => page.evaluate(() => window.__benchDebug.snapshot());
const ideal = async (page: Page): Promise<any> => (await actual(page)).idealPolarization;
const keys = ['source_amplitude', 'mean_phase_rad', 'phase_std_rad', 'seed', 'qwp_angle_rad', 'hwp_angle_rad'] as const;
const defaults = { schema_version: 1, model_contract: 'r03_ideal_statistical_polarization_v1', source_amplitude: 1,
  mean_phase_rad: Math.PI, phase_std_rad: 1.2, qwp_angle_rad: 0, hwp_angle_rad: 0, seed: 20261017 };
const scienceCall = (path: string) => /\/api\/(?:v1|v2b|v2d|v2g)\/(?:simulate|sweep)$/.test(path) || path === '/api/research/r03-fig2a/simulate';
function save(name: string, value: unknown): void { mkdirSync(evidence, { recursive: true }); writeFileSync(resolve(evidence, `${name}.json`), JSON.stringify(value, null, 2), { flag: 'wx' }); }
function cameraState(snapshot: any): object { const camera = snapshot.scene.camera; return { position: camera.position, target: camera.target, up: camera.up, near: camera.near, far: camera.far, minDistance: camera.minDistance, maxDistance: camera.maxDistance }; }
async function ready(page: Page): Promise<void> { await expect.poll(async () => { const state = await ideal(page); return !!state.validatedDraft && !state.pendingValidation && !state.active; }).toBe(true); await expect(page.getByTestId('r03-compute')).toBeEnabled(); }
async function load(page: Page): Promise<string[]> {
  const calls: string[] = [];
  await page.route('**/*', route => new URL(route.request().url()).origin === 'http://127.0.0.1:8510' ? route.continue() : route.abort('blockedbyclient'));
  page.on('request', request => { const path = new URL(request.url()).pathname; if (request.method() === 'POST' && path.startsWith('/api/')) calls.push(path); });
  // Test-owned raw clone, capped by the unchanged R03 response contract (128 KiB).
  // Return the original fetch promise; never replay the request or consume the app's stream.
  await page.addInitScript(() => {
    const original = window.fetch.bind(window), captured: Record<string, Promise<string>> = {};
    (window as any).__r03UxCaptured = captured;
    window.fetch = (input, init) => {
      const response = original(input, init);
      if (input === '/api/research/r03-fig2a/simulate' && init?.method === 'POST') {
        const id = JSON.parse(String(init.body)).request_id;
        captured[id] = response.then(reply => {
          if (!reply.ok) throw new Error(`R03 test capture received HTTP ${reply.status}`);
          return reply.clone().arrayBuffer();
        }).then(buffer => {
          if (buffer.byteLength > 131_072) throw new Error('R03 test capture exceeded the response contract cap');
          const bytes = new Uint8Array(buffer), chunks: string[] = [];
          for (let i = 0; i < bytes.length; i += 16384) chunks.push(String.fromCharCode(...bytes.subarray(i, i + 16384)));
          return btoa(chunks.join(''));
        });
      }
      return response;
    };
  });
  await page.goto('/'); await page.getByTestId('research-workspace').click(); await ready(page); return calls;
}
async function compute(page: Page): Promise<any> {
  const pending = page.waitForResponse(response => new URL(response.url()).pathname === '/api/research/r03-fig2a/simulate' && response.request().method() === 'POST').then(async response => {
    expect(response.status()).toBe(200); const requestBytes = response.request().postDataBuffer()!, request = JSON.parse(requestBytes.toString('utf8'));
    const base64 = await page.evaluate(async id => {
      const captured = (window as any).__r03UxCaptured as Record<string, Promise<string>>;
      if (!Object.hasOwn(captured, id)) throw new Error('The genuine R03 response was not captured for this request');
      try { return await captured[id]; } finally { delete captured[id]; }
    }, request.request_id);
    const bytes = Buffer.from(base64, 'base64'); expect(bytes.byteLength).toBeLessThanOrEqual(131_072);
    const raw = JSON.parse(bytes.toString('utf8')), requestSha256 = createHash('sha256').update(requestBytes).digest('hex'), stem = `capture_${requestSha256}`;
    mkdirSync(evidence, { recursive: true }); writeFileSync(resolve(evidence, `${stem}_request.json`), requestBytes, { flag: 'wx' });
    writeFileSync(resolve(evidence, `${stem}_response.bin`), bytes, { flag: 'wx' });
    save(stem, { method: 'Test-owned clone of the genuine browser fetch response; original fetch once; no replay or extra HTTP',
      path: new URL(response.url()).pathname, status: response.status(), contentType: response.headers()['content-type'],
      requestFile: `${stem}_request.json`, requestByteLength: requestBytes.byteLength, requestSha256,
      responseFile: `${stem}_response.bin`, responseByteLength: bytes.byteLength, responseSha256: createHash('sha256').update(bytes).digest('hex'),
      requestId: request.request_id, decodedReplyRequestId: raw.request_id, responseCapBytes: 131_072 });
    expect(raw.request_id).toBe(request.request_id); return { raw, request };
  });
  const [{ raw, request }] = await Promise.all([pending, page.getByTestId('r03-compute').click()]);
  await expect.poll(async () => (await ideal(page)).currentResult?.requestId).toBe(request.request_id);
  const state = await ideal(page); expect(state.currentResult.phase).toEqual(raw.phase); expect(state.currentResult.stages).toEqual(raw.stages);
  expect(state.currentResult.population).toEqual(raw.population); expect(state.currentResult.provenance).toEqual(raw.provenance);
  expect(state.currentResult.experiment).toEqual(request.experiment); expect(state.displayedRequestId).toBe(request.request_id);
  return { request, raw, state };
}
async function fullVisible(page: Page, id: string): Promise<void> {
  await expect(page.getByTestId(id)).toBeVisible(); const box = await page.getByTestId(id).boundingBox(), size = page.viewportSize();
  expect(box).not.toBeNull(); expect(size).not.toBeNull(); expect(box!.x).toBeGreaterThanOrEqual(0); expect(box!.y).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(size!.width + 1); expect(box!.y + box!.height).toBeLessThanOrEqual(size!.height + 1);
}
function framed(snapshot: any): void {
  const framing = snapshot.scene.researchFraming; expect(framing).not.toBeNull(); expect(framing.projectedCorners).toHaveLength(8);
  for (const corner of framing.projectedCorners) { expect(corner.every(Number.isFinite)).toBe(true); expect(Math.abs(corner[0])).toBeLessThanOrEqual(.95); expect(Math.abs(corner[1])).toBeLessThanOrEqual(.95); expect(corner[2]).toBeGreaterThan(-1); expect(corner[2]).toBeLessThan(1); }
}
async function tab(page: Page, name: 'summary' | 'phase' | 'measurements' | 'evidence'): Promise<void> { await page.getByTestId(`r03-tab-${name}`).click(); await expect(page.getByTestId(`r03-tab-${name}`)).toHaveAttribute('aria-selected', 'true'); }
async function resultControlsFit(page: Page): Promise<object> {
  const geometry = await page.evaluate(() => {
    const result = document.querySelector<HTMLElement>('.r03-results')!, bounds = result.getBoundingClientRect();
    return { result: { left: bounds.left, right: bounds.right, clientWidth: result.clientWidth },
      controls: ['.r03-tabs', '.r03-stage', '[data-testid="r03-selected-stage"]', '[role="tabpanel"]:not([hidden])'].map(selector => {
        const element = document.querySelector<HTMLElement>(selector)!, r = element.getBoundingClientRect(); return { selector, left: r.left, right: r.right, width: r.width };
      }) };
  });
  for (const control of geometry.controls) { expect(control.left, control.selector).toBeGreaterThanOrEqual(geometry.result.left); expect(control.right, control.selector).toBeLessThanOrEqual(geometry.result.right + 1); expect(control.width, control.selector).toBeLessThanOrEqual(geometry.result.clientWidth + 1); }
  return geometry;
}

for (const [width, height] of [[1366, 768], [1440, 900], [1920, 1080]]) {
  test(`bounded ${width}x${height} default view and contextual data inspection make no scientific requests`, async ({ page, browser }) => {
    await page.setViewportSize({ width, height }); const calls = await load(page); const empty = await actual(page);
    expect(empty.idealPolarization.candidate).toEqual(defaults); expect(empty.idealPolarization.selection).toBe('slm'); expect(empty.idealPolarization.currentResult).toBeNull();
    await fullVisible(page, 'r03-compute'); await fullVisible(page, 'r03-status'); framed(empty);
    const capture = await compute(page); expect(capture.request.experiment).toEqual(defaults); const success = await actual(page);
    expect(cameraState(success)).toEqual(cameraState(empty)); expect(success.scene.researchFraming.fitCount).toBe(empty.scene.researchFraming.fitCount);
    await fullVisible(page, 'r03-compute'); await fullVisible(page, 'r03-status');
    const metrics = await page.evaluate(() => ({ width: innerWidth, height: innerHeight, dpr: devicePixelRatio, scale: visualViewport?.scale,
      scrollX, scrollY, scrollWidth: document.documentElement.scrollWidth, scrollHeight: document.documentElement.scrollHeight }));
    expect(metrics.dpr).toBe(1); expect(metrics.scale).toBe(1); expect(metrics.scrollWidth).toBeLessThanOrEqual(width + 1);
    expect(metrics.scrollHeight).toBeLessThanOrEqual(height + 1); expect(metrics.scrollY).toBe(0);
    const bounds = await page.getByTestId('r03-viewport').boundingBox(); expect(bounds!.width).toBeGreaterThan(500); expect(bounds!.height).toBeGreaterThan(420);
    mkdirSync(evidence, { recursive: true }); writeFileSync(resolve(evidence, `workspace_${width}x${height}.png`), await page.screenshot({ fullPage: false }), { flag: 'wx' });
    const beforeVisual = calls.slice(), immutable = (await ideal(page)).currentResult;
    const contextual: [string, readonly string[], string | null][] = [
      ['source', ['source_amplitude'], 'source'], ['input_hwp', [], 'source'], ['router', [], null],
      ['slm', ['mean_phase_rad', 'phase_std_rad', 'seed'], 'after_slm'], ['qwp', ['qwp_angle_rad'], 'after_qwp'],
      ['hwp', ['hwp_angle_rad'], 'output'], ['measurement', [], 'output'],
    ];
    for (const [component, visible, stage] of contextual) {
      const before = await actual(page); await page.getByTestId(`r03-select-${component}`).click();
      for (const key of keys) { const field = page.getByTestId(`r03-edit-${key}`); if (visible.includes(key)) await expect(field).toBeVisible(); else await expect(field).toBeHidden(); }
      expect(cameraState(await actual(page))).toEqual(cameraState(before)); expect((await actual(page)).scene.researchFraming.fitCount).toBe(before.scene.researchFraming.fitCount);
      await tab(page, 'measurements'); await expect(page.getByTestId('r03-selected-stage')).toHaveValue(stage ?? '');
      expect(await page.getByTestId('r03-selected-stage').locator('option').evaluateAll(nodes => nodes.map(n => (n as HTMLOptionElement).value))).toEqual(['', 'source', 'after_slm', 'after_qwp', 'output']);
      expect((await ideal(page)).currentResult).toEqual(immutable);
    }
    await page.getByTestId('r03-all-parameters').click(); for (const key of keys) { await page.getByTestId(`r03-edit-${key}`).scrollIntoViewIfNeeded(); await expect(page.getByTestId(`r03-edit-${key}`)).toBeVisible(); }
    await page.getByTestId('r03-select-slm').click(); await page.getByTestId('r03-edit-mean_phase_rad').focus(); await page.getByTestId('r03-edit-mean_phase_rad').blur();
    expect((await ideal(page)).candidate).toEqual(defaults); expect((await ideal(page)).currentResult).toEqual(immutable);
    await tab(page, 'phase'); await expect(page.getByTestId('r03-phase')).toBeVisible(); const phase = await ideal(page);
    const pixels = await page.getByTestId('r03-phase').evaluate((canvas: HTMLCanvasElement) => Array.from(canvas.getContext('2d')!.getImageData(0, 0, 16, 16).data));
    expect(pixels).toEqual(phase.phaseRGBA); expect(pixels).toHaveLength(1024);
    await page.getByTestId('r03-phase').click({ position: { x: 2, y: 2 } }); expect((await ideal(page)).selectedSample).toBe(0);
    await expect(page.getByTestId('r03-sample')).toContainText(capture.raw.phase.wrapped_rad[0].toPrecision(17));
    await tab(page, 'measurements'); await page.getByTestId('r03-selected-stage').selectOption('output'); await page.getByTestId('r03-full-precision').check();
    const measurementsGeometry = await resultControlsFit(page);
    const values = await page.locator('[role="tabpanel"]:visible').innerText();
    const displayed = values.replaceAll('−', '-').match(/[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?/gi)?.map(Number) ?? [];
    for (const value of capture.raw.stages[3].stokes) expect(displayed.some(v => Object.is(v, value) || v === 0 && value === 0)).toBe(true);
    await tab(page, 'evidence'); await expect(page.getByTestId('r03-result-identity')).toContainText(capture.request.request_id);
    await expect(page.getByTestId('r03-result-identity')).toContainText(capture.request.experiment_sha256);
    const evidenceGeometry = await resultControlsFit(page);
    await tab(page, 'summary'); expect((await ideal(page)).currentResult).toEqual(immutable);
    const beforeResize = await actual(page); await page.setViewportSize({ width: width - 16, height: height - 8 });
    await expect.poll(async () => (await actual(page)).scene.camera.aspect).not.toBe(beforeResize.scene.camera.aspect);
    expect(cameraState(await actual(page))).toEqual(cameraState(beforeResize)); expect((await actual(page)).scene.researchFraming.fitCount).toBe(beforeResize.scene.researchFraming.fitCount);
    await page.setViewportSize({ width, height });
    for (const [id, view] of [['r03-overview-view', 'overview'], ['r03-top-view', 'top'], ['r03-focus-selected', 'focus'], ['r03-reset-view', 'overview']]) {
      const previous = await actual(page); await page.getByTestId(id).click(); const next = await actual(page);
      expect(next.scene.researchFraming.view).toBe(view); expect(next.scene.researchFraming.fitCount).toBe(previous.scene.researchFraming.fitCount + 1); framed(next);
      expect(next.idealPolarization.currentResult).toEqual(immutable);
    }
    expect(calls).toEqual(beforeVisual); expect(calls.filter(scienceCall)).toEqual(['/api/research/r03-fig2a/simulate']);
    expect((await actual(page)).scene.owned.controls).toBe(1); expect((await actual(page)).scene.owned.resizeObservers).toBe(1);
    save(`desktop_${width}x${height}`, { viewport: { width, height }, browserVersion: browser.version(), metrics, empty, success,
      actual: capture, final: await actual(page), pixels, apiCalls: calls, measurementsGeometry, evidenceGeometry, defaultAutomaticView: true, noHandFramingBeforeScreenshot: true });
  });
}

test('invalid draft text survives contextual panels and repeated view/navigation cycles retain bounded owners', async ({ page }) => {
  const calls = await load(page); await compute(page); await page.getByTestId('r03-select-slm').click();
  const before = await ideal(page); await page.getByTestId('r03-edit-seed').fill('invalid-seed'); await page.getByTestId('r03-edit-seed').blur();
  await expect(page.getByTestId('r03-compute')).toBeDisabled(); const invalid = await ideal(page); expect(invalid.currentResult).toBeNull(); expect(invalid.candidate).toEqual(before.candidate);
  for (const component of ['qwp', 'source', 'hwp', 'router', 'slm']) await page.getByTestId(`r03-select-${component}`).click();
  await expect(page.getByTestId('r03-edit-seed')).toHaveValue('invalid-seed'); expect((await ideal(page)).invalidEdits).toEqual(invalid.invalidEdits);
  for (const name of ['summary', 'phase', 'measurements', 'evidence'] as const) await tab(page, name);
  const camera = cameraState(await actual(page)); const owned = await ideal(page), counts = calls.filter(scienceCall).slice();
  const cycles = [];
  for (let i = 0; i < 5; i++) {
    await page.getByTestId('ordinary-workspace').click(); expect((await actual(page)).scene.researchLabelCallbacks).toBe(0);
    await page.getByTestId('research-workspace').click(); await expect.poll(async () => (await ideal(page)).pendingValidation).toBe(false);
    const current = await actual(page); expect(current.scene.researchLabelCallbacks).toBe(1); expect(current.scene.owned.controls).toBe(1); expect(current.scene.owned.resizeObservers).toBe(1);
    expect(cameraState(current)).toEqual(camera); expect(current.idealPolarization.invalidEdits).toEqual(invalid.invalidEdits);
    expect(current.idealPolarization.ownedBytes).toBe(owned.ownedBytes); expect(current.idealPolarization.numericalBytes).toBe(owned.numericalBytes);
    cycles.push(current);
  }
  await page.getByTestId('r03-select-slm').click(); await expect(page.getByTestId('r03-edit-seed')).toHaveValue('invalid-seed');
  await page.getByTestId('release-results').click(); const released = await ideal(page);
  expect(released.candidate).toEqual(invalid.candidate); expect(released.invalidEdits).toEqual(invalid.invalidEdits);
  expect(released.numericalBytes).toBe(0); expect(released.phaseDisplayBytes).toBe(0); expect(cameraState(await actual(page))).toEqual(camera);
  expect(calls.filter(scienceCall)).toEqual(counts); save('contextual_invalid_cycles', { invalid, cycles, released, apiCalls: calls });
});

test('actual Chrome 200 percent browser zoom uses accessible stacked and keyboard navigation', async ({}, info) => {
  const profile = info.outputPath('actual-zoom-profile'); mkdirSync(resolve(profile, 'Default'), { recursive: true });
  writeFileSync(resolve(profile, 'Default/Preferences'), JSON.stringify({ partition: { default_zoom_level: { x: Math.log(2) / Math.log(1.2) } } }), { flag: 'wx' });
  const context = await chromium.launchPersistentContext(profile, { channel: 'chrome', headless: true, viewport: null, deviceScaleFactor: undefined,
    baseURL: 'http://127.0.0.1:8510', args: ['--window-size=1440,900'] });
  try {
    const page = context.pages()[0] ?? await context.newPage(); const calls = await load(page);
    const zoom = await page.evaluate(() => ({ innerWidth, innerHeight, outerWidth, outerHeight, devicePixelRatio, visualViewportScale: visualViewport?.scale, scrollWidth: document.documentElement.scrollWidth }));
    expect(zoom.devicePixelRatio).toBe(2); expect(zoom.visualViewportScale).toBe(1); expect(zoom.innerWidth).toBeLessThan(740); expect(zoom.outerWidth).toBeGreaterThanOrEqual(1400);
    expect(zoom.scrollWidth).toBeLessThanOrEqual(zoom.innerWidth + 1);
    const toolbarGeometry = await page.evaluate(() => ['ordinary-workspace', 'research-workspace', 'r03-status', 'r03-compute', 'release-results'].map(id => {
      const rect = document.querySelector(`[data-testid="${id}"]`)!.getBoundingClientRect(); return { id, left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom };
    }));
    for (const control of toolbarGeometry) { expect(control.left, control.id).toBeGreaterThanOrEqual(0); expect(control.right, control.id).toBeLessThanOrEqual(zoom.innerWidth); expect(control.top, control.id).toBeGreaterThanOrEqual(0); expect(control.bottom, control.id).toBeLessThanOrEqual(zoom.innerHeight); }
    await page.getByTestId('r03-all-parameters').click(); for (const key of keys) { await page.getByTestId(`r03-edit-${key}`).scrollIntoViewIfNeeded(); await expect(page.getByTestId(`r03-edit-${key}`)).toBeVisible(); }
    await page.getByTestId('r03-compute').scrollIntoViewIfNeeded(); const capture = await compute(page);
    await tab(page, 'phase'); await expect(page.getByTestId('r03-phase')).toBeVisible(); await page.getByTestId('r03-phase').click({ position: { x: 2, y: 2 } });
    await expect(page.getByTestId('r03-sample')).toContainText(capture.raw.phase.wrapped_rad[0].toPrecision(17));
    await tab(page, 'measurements'); await page.getByTestId('r03-selected-stage').selectOption('after_qwp'); await page.getByTestId('r03-full-precision').check();
    const measurementsGeometry = await resultControlsFit(page);
    await page.getByTestId('r03-tab-evidence').focus(); await page.keyboard.press('Enter'); await expect(page.getByTestId('r03-tab-evidence')).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByTestId('r03-result-identity')).toContainText(capture.request.request_id);
    const evidenceGeometry = await resultControlsFit(page);
    await page.getByTestId('r03-select-qwp').focus(); await page.keyboard.press('Enter'); await page.getByTestId('r03-edit-qwp_angle_rad').scrollIntoViewIfNeeded(); await expect(page.getByTestId('r03-edit-qwp_angle_rad')).toBeVisible();
    await page.getByTestId('r03-focus-selected').scrollIntoViewIfNeeded(); await page.getByTestId('r03-focus-selected').click(); framed(await actual(page));
    expect((await ideal(page)).currentResult.phase).toEqual(capture.raw.phase); expect(calls.filter(scienceCall)).toHaveLength(1);
    mkdirSync(evidence, { recursive: true }); const session = await context.newCDPSession(page), layoutMetrics = await session.send('Page.getLayoutMetrics');
    const nativeScreenshot = await session.send('Page.captureScreenshot', { format: 'png', fromSurface: true, captureBeyondViewport: false });
    writeFileSync(resolve(evidence, 'actual_200percent_native.png'), Buffer.from(nativeScreenshot.data, 'base64'), { flag: 'wx' });
    const final = await actual(page); await page.getByTestId('ordinary-workspace').click(); await expect(page.getByTestId('mode')).toBeVisible();
    expect(await page.evaluate(() => getComputedStyle(document.body).overflowY)).not.toBe('hidden');
    save('actual_200percent', { zoom, actual: capture, final, apiCalls: calls, toolbarGeometry, measurementsGeometry, evidenceGeometry, layoutMetrics,
      method: 'Actual isolated Chrome profile content zoom; native CDP screenshot without clip, resize, compositing, CSS or device/pinch scale emulation', profile });
  } finally { await context.close(); }
});

// A scalar is one visual token; these checks use actual server results, not substituted readout fixtures.
const nowrapRegion = (page: Page) => page.getByRole('region', { name: 'Four-stage numerical comparison, horizontally scrollable', exact: true });
const exactScalar = (value: number | null): string => value === null ? 'undefined (null)' : Object.is(value, -0) ? '−0' : value.toPrecision(17);
async function readoutLines(page: Page): Promise<any[]> {
  return nowrapRegion(page).locator('table').evaluate((table: HTMLTableElement) => Array.from(table.rows).slice(1).flatMap(row => Array.from(row.cells).slice(1).map(cell => {
    const range = document.createRange(); range.selectNodeContents(cell); const rects = Array.from(range.getClientRects()).filter(rect => rect.width > 0 && rect.height > 0);
    return { text: cell.textContent, lineTops: [...new Set(rects.map(rect => Math.round(rect.top)))], fontSize: parseFloat(getComputedStyle(cell).fontSize),
      whiteSpace: getComputedStyle(cell).whiteSpace, overflowWrap: getComputedStyle(cell).overflowWrap };
  })));
}
async function inspectNowrap(page: Page, calls: string[], capture: any, name: string, screenshot?: string, requireOverflow = false): Promise<object> {
  const beforeCalls = calls.slice(), before = await ideal(page); await tab(page, 'measurements');
  await page.getByTestId('r03-full-precision').uncheck(); await page.getByTestId('r03-full-precision').check();
  const region = nowrapRegion(page), table = region.locator('table'); await expect(region).toHaveAttribute('tabindex', '0');
  const expectedRows = capture.raw.stages.map((stage: any, index: number) => [['Source', 'SLM', 'QWP', 'Output'][index], exactScalar(stage.stokes[0]), exactScalar(stage.degree_of_polarization)]);
  await expect(table.locator('th')).toHaveText(['Stage', 'S₀', 'DoP']);
  expect(await table.evaluate((element: HTMLTableElement) => Array.from(element.rows).slice(1).map(row => Array.from(row.cells).map(cell => cell.textContent)))).toEqual(expectedRows);
  const lines = await readoutLines(page); expect(lines).toHaveLength(8);
  for (const cell of lines) { expect(cell.lineTops, cell.text).toHaveLength(1); expect(cell.fontSize, cell.text).toBeGreaterThanOrEqual(13); }
  await region.scrollIntoViewIfNeeded();
  if (screenshot) { mkdirSync(evidence, { recursive: true }); writeFileSync(resolve(evidence, screenshot), await page.screenshot({ fullPage: false }), { flag: 'wx' }); }
  const viewportBefore = await page.getByTestId('r03-viewport').boundingBox(), cameraBefore = cameraState(await actual(page));
  const scrollBefore = await page.evaluate(() => ({ x: scrollX, y: scrollY }));
  const maximum = await region.evaluate(element => element.scrollWidth - element.clientWidth); expect(maximum).toBeGreaterThanOrEqual(0); if (requireOverflow) expect(maximum).toBeGreaterThan(0);
  await region.hover(); await page.mouse.wheel(10000, 0);
  await expect.poll(() => region.evaluate(element => element.scrollLeft)).toBeGreaterThanOrEqual(maximum - 1);
  const pointerScroll = await region.evaluate(element => element.scrollLeft);
  await page.mouse.wheel(-10000, 0); await expect.poll(() => region.evaluate(element => element.scrollLeft)).toBe(0);
  await region.focus(); await expect(region).toBeFocused(); for (let i = 0; i < 14; i++) await page.keyboard.press('ArrowRight');
  await expect.poll(() => region.evaluate(element => element.scrollLeft)).toBeGreaterThanOrEqual(maximum - 1);
  const access = await region.evaluate(element => {
    const bounds = element.getBoundingClientRect(), rows = Array.from(element.querySelector('table')!.rows).slice(1);
    return { left: bounds.left, right: bounds.right, clientWidth: element.clientWidth, scrollWidth: element.scrollWidth, scrollLeft: element.scrollLeft,
      cells: rows.map(row => { const range = document.createRange(); range.selectNodeContents(row.cells[2]); const number = range.getBoundingClientRect(), stage = row.cells[0].getBoundingClientRect();
        return { stage: row.cells[0].textContent, stageLeft: stage.left, stageRight: stage.right, numberLeft: number.left, numberRight: number.right }; }) };
  });
  for (const cell of access.cells) { expect(cell.stageLeft).toBeGreaterThanOrEqual(access.left - 1); expect(cell.numberLeft).toBeGreaterThanOrEqual(cell.stageRight - 1); expect(cell.numberRight).toBeLessThanOrEqual(access.right + 1); }
  expect(await page.getByTestId('r03-viewport').boundingBox()).toEqual(viewportBefore); expect(cameraState(await actual(page))).toEqual(cameraBefore);
  expect(await page.evaluate(() => ({ x: scrollX, y: scrollY }))).toEqual(scrollBefore);
  const rootGeometry = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth }));
  expect(rootGeometry.scrollWidth).toBeLessThanOrEqual(rootGeometry.width + 1);
  await tab(page, 'summary'); await tab(page, 'evidence'); await tab(page, 'measurements');
  expect(await table.evaluate((element: HTMLTableElement) => Array.from(element.rows).slice(1).map(row => Array.from(row.cells).map(cell => cell.textContent)))).toEqual(expectedRows);
  const after = await ideal(page); expect(after.currentResult).toEqual(before.currentResult); expect(after.phaseRGBA).toEqual(before.phaseRGBA);
  expect(after.candidate).toEqual(before.candidate); expect(after.revision).toBe(before.revision); expect(after.attachmentEpoch).toBe(before.attachmentEpoch); expect(calls).toEqual(beforeCalls);
  const result = { expectedRows, lines, maximum, pointerScroll, access, rootGeometry, apiCalls: calls, immutableResult: after.currentResult };
  save(name, result); return result;
}

for (const [width, height] of [[1366, 768], [1440, 900], [1920, 1080]]) {
  test(`readout-nowrap ${width}x${height} keeps exact scalars readable with local pointer and keyboard scrolling`, async ({ page }) => {
    await page.setViewportSize({ width, height }); const calls = await load(page); const capture = await compute(page);
    await inspectNowrap(page, calls, capture, `nowrap_${width}x${height}`, width === 1440 ? 'full_precision_1440x900.png' : undefined, true);
    if (width === 1440) {
      const cell = nowrapRegion(page).locator('table').locator('tr').nth(1).locator('td').nth(1), text = await cell.textContent();
      const originalNodes = await cell.evaluateHandle(element => Array.from(element.childNodes)), immutable = await ideal(page), beforeCalls = calls.slice();
      try {
        await cell.evaluate(element => { const scalar = element.textContent!; element.replaceChildren(document.createTextNode(scalar.slice(0, 9)), document.createElement('br'), document.createTextNode(scalar.slice(9))); });
        expect(await cell.textContent()).toBe(text); const broken = await readoutLines(page); expect(broken.some(value => value.lineTops.length > 1)).toBe(true);
        save('nowrap_negative_control', { method: 'Temporary page-only BR inside one scalar, preserving its exact textContent and production CSP; original child nodes restored before final checks', text, broken });
      } finally { await cell.evaluate((element, nodes) => element.replaceChildren(...nodes), originalNodes); await originalNodes.dispose(); }
      expect(await cell.textContent()).toBe(text);
      for (const cell of await readoutLines(page)) expect(cell.lineTops, cell.text).toHaveLength(1);
      const restored = await ideal(page); expect(restored.currentResult).toEqual(immutable.currentResult); expect(restored.phaseRGBA).toEqual(immutable.phaseRGBA); expect(restored.candidate).toEqual(immutable.candidate);
      expect(restored.revision).toBe(immutable.revision); expect(restored.attachmentEpoch).toBe(immutable.attachmentEpoch); expect(calls).toEqual(beforeCalls);
    }
    expect(calls.filter(scienceCall)).toEqual(['/api/research/r03-fig2a/simulate']);
  });
}

test('readout-nowrap real decimal, scientific notation and dark undefined states preserve authoritative strings', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 }); const calls = await load(page); await tab(page, 'measurements');
  await page.getByTestId('r03-full-precision').check(); await expect(nowrapRegion(page)).toHaveCount(0); expect(calls.filter(scienceCall)).toEqual([]);
  for (const [name, amplitude] of [['long_decimal', '0.3333333333333333'], ['small_exponent', '1e-6'], ['dark_null', '0']]) {
    await page.getByTestId('r03-select-source').click(); await page.getByTestId('r03-edit-source_amplitude').fill(amplitude); await ready(page);
    const capture = await compute(page); expect(capture.request.experiment.source_amplitude).toBe(Number(amplitude));
    if (name === 'small_exponent') expect(capture.raw.stages.every((stage: any) => exactScalar(stage.stokes[0]).includes('e-'))).toBe(true);
    if (name === 'dark_null') expect(capture.raw.stages.every((stage: any) => stage.degree_of_polarization === null && stage.normalized_stokes === null && stage.polarized_direction === null)).toBe(true);
    await inspectNowrap(page, calls, capture, `nowrap_${name}`);
  }
  expect(calls.filter(scienceCall)).toHaveLength(3);
});

test('readout-nowrap actual Chrome 200 percent zoom retains complete-value keyboard and pointer access', async ({}, info) => {
  const profile = info.outputPath('nowrap-actual-zoom-profile'); mkdirSync(resolve(profile, 'Default'), { recursive: true });
  writeFileSync(resolve(profile, 'Default/Preferences'), JSON.stringify({ partition: { default_zoom_level: { x: Math.log(2) / Math.log(1.2) } } }), { flag: 'wx' });
  const context = await chromium.launchPersistentContext(profile, { channel: 'chrome', headless: true, viewport: null, deviceScaleFactor: undefined,
    baseURL: 'http://127.0.0.1:8510', args: ['--window-size=1440,900'] });
  try {
    const page = context.pages()[0] ?? await context.newPage(), calls = await load(page);
    const zoom = await page.evaluate(() => ({ innerWidth, innerHeight, outerWidth, outerHeight, devicePixelRatio, visualViewportScale: visualViewport?.scale }));
    expect(zoom.devicePixelRatio).toBe(2); expect(zoom.visualViewportScale).toBe(1); expect(zoom.innerWidth).toBeLessThan(740); expect(zoom.outerWidth).toBeGreaterThanOrEqual(1400);
    const capture = await compute(page); await inspectNowrap(page, calls, capture, 'nowrap_actual_200percent');
    const region = nowrapRegion(page); await region.scrollIntoViewIfNeeded(); await region.focus();
    const toolbarBottom = await page.locator('.r03-toolbar').evaluate(element => element.getBoundingClientRect().bottom), regionTop = (await region.boundingBox())!.y;
    const beforeScreenshotScroll = await page.evaluate(() => ({ windowY: scrollY, regionTop: document.querySelector('.r03-measurement-table')!.getBoundingClientRect().top }));
    if (regionTop < toolbarBottom + 8) await page.evaluate(offset => window.scrollBy(0, offset), regionTop - toolbarBottom - 12);
    await expect.poll(async () => (await region.boundingBox())!.y).toBeGreaterThanOrEqual(toolbarBottom + 4);
    const afterScreenshotScroll = await page.evaluate(() => ({ windowY: scrollY, regionTop: document.querySelector('.r03-measurement-table')!.getBoundingClientRect().top }));
    const headers = await region.locator('th').evaluateAll(elements => elements.map(element => { const rect = element.getBoundingClientRect(); return { text: element.textContent, top: rect.top, bottom: rect.bottom }; }));
    for (const header of headers) { expect(header.top).toBeGreaterThanOrEqual(toolbarBottom + 4); expect(header.bottom).toBeLessThanOrEqual(zoom.innerHeight); }
    const session = await context.newCDPSession(page), browser = await session.send('Browser.getVersion');
    const native = await session.send('Page.captureScreenshot', { format: 'png', fromSurface: true, captureBeyondViewport: false });
    mkdirSync(evidence, { recursive: true }); writeFileSync(resolve(evidence, 'full_precision_actual_200percent_scrolled.png'), Buffer.from(native.data, 'base64'), { flag: 'wx' });
    await region.hover(); await page.mouse.wheel(-10000, 0); await expect.poll(() => region.evaluate(element => element.scrollLeft)).toBe(0);
    const left = await session.send('Page.captureScreenshot', { format: 'png', fromSurface: true, captureBeyondViewport: false });
    writeFileSync(resolve(evidence, 'full_precision_actual_200percent_left.png'), Buffer.from(left.data, 'base64'), { flag: 'wx' });
    save('nowrap_actual_zoom_identity', { zoom, browser, toolbarBottom, headers, beforeScreenshotScroll, afterScreenshotScroll,
      method: 'Actual isolated Chrome profile content zoom; native screenshots with window.scrollBy only for vertical screenshot alignment; horizontal table access exercised by genuine wheel and keyboard, without CSS, pinch or device scale emulation', profile });
    expect(calls.filter(scienceCall)).toEqual(['/api/research/r03-fig2a/simulate']);
  } finally { await context.close(); }
});
