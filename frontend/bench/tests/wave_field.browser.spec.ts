/** Genuine installed-browser W1 acceptance; controlled faults are labelled separately. */
import { test, expect, chromium, type Page } from '@playwright/test';
import { mkdirSync, writeFileSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve('../..'), evidence = resolve(root, process.env.W1_EVIDENCE_DIR ?? 'runs/w1_implementation_01/browser');
const snap = (page: Page): Promise<any> => page.evaluate(() => window.__benchDebug.snapshot());
const wave = async (page: Page): Promise<any> => (await snap(page)).waveField;
const science = (path: string): boolean => /\/api\/(?:w1|v1|v2b|v2d|v2g)\/(?:simulate|sweep)$/.test(path) || path === '/api/research/r03-fig2a/simulate';
function save(name: string, value: unknown): void { mkdirSync(evidence, { recursive: true }); writeFileSync(resolve(evidence, name + '.json'), JSON.stringify(value, null, 2), { flag: 'wx' }); }
async function image(page: Page, name: string): Promise<void> { mkdirSync(evidence, { recursive: true }); await page.screenshot({ path: resolve(evidence, name + '.png'), fullPage: false }); }
async function frames(page: Page, count = 12): Promise<void> { await page.evaluate(count => new Promise<void>(resolve => { let n = 0; const next = () => ++n < count ? requestAnimationFrame(next) : resolve(); requestAnimationFrame(next); }), count); }
async function ready(page: Page): Promise<void> { await expect.poll(async () => { const s = await snap(page); return !!s.validatedDraft && !s.pendingValidation && !s.active; }).toBe(true); await expect(page.getByTestId('simulate')).toBeEnabled(); }
async function load(page: Page): Promise<string[]> {
  const calls: string[] = []; await page.route('**/*', route => new URL(route.request().url()).origin === 'http://127.0.0.1:8510' ? route.continue() : route.abort('blockedbyclient'));
  // Capture a bounded clone of the genuine browser response before the app consumes
  // its stream. Chrome155's CDP response.body intermittently loses large frames.
  // This test-owned clone changes no response bytes and is excluded from app ownership.
  await page.addInitScript(() => {
    const original = window.fetch.bind(window), captured: Record<string, Promise<string>> = {};
    (window as any).__w1Captured = captured;
    window.fetch = async (input, init) => {
      const response = await original(input, init);
      if (typeof input === 'string' && input === '/api/w1/simulate' && response.ok) {
        const id = JSON.parse(String(init?.body)).request_id;
        captured[id] = response.clone().arrayBuffer().then(buffer => {
          if (buffer.byteLength > 3344400) throw new Error('Test capture exceeded W1 frame cap');
          const bytes = new Uint8Array(buffer), chunks: string[] = [];
          for (let i = 0; i < bytes.length; i += 16384) chunks.push(String.fromCharCode(...bytes.subarray(i, i + 16384)));
          return btoa(chunks.join(''));
        });
      }
      return response;
    };
  });
  page.on('request', request => { const path = new URL(request.url()).pathname; if (request.method() === 'POST' && science(path)) calls.push(path); });
  await page.goto('/'); await ready(page); await page.getByTestId('w1-view').click(); await page.getByTestId('w1-load-example').click(); await ready(page);
  expect((await wave(page)).enabled).toBe(true); expect(calls).toEqual([]); return calls;
}
function unpack(bytes: Buffer): { header: any; intensity: Float64Array; x: Float64Array; y: Float64Array } {
  expect(bytes.subarray(0, 8).toString('binary')).toBe('OHLABWF\0'); const length = bytes.readUInt32LE(8), offset = 16 + Math.ceil(length / 8) * 8;
  const header = JSON.parse(bytes.subarray(16, 16 + length).toString('utf8')); expect(header.message_type).toBe('w1_wave_field');
  const arrays = header.arrays.map((descriptor: any) => { const result = new Float64Array(descriptor.nbytes / 8); for (let i = 0; i < result.length; i++) result[i] = bytes.readDoubleLE(offset + descriptor.offset_bytes + i * 8); return result; });
  return { header, intensity: arrays[0], x: arrays[1], y: arrays[2] };
}
async function calculate(page: Page): Promise<any> {
  const waiting = page.waitForResponse(response => new URL(response.url()).pathname === '/api/w1/simulate' && response.request().method() === 'POST');
  await page.getByTestId('simulate').click(); const response = await waiting; expect(response.status()).toBe(200); const request = JSON.parse(response.request().postData()!);
  const bytes = Buffer.from(await page.evaluate(async id => { const value = await (window as any).__w1Captured[id]; delete (window as any).__w1Captured[id]; return value; }, request.request_id), 'base64');
  await expect.poll(async () => (await wave(page)).currentResult?.requestId).toBe(request.request_id);
  const state = await wave(page), raw = unpack(bytes), { nx, ny } = request.experiment.grid;
  expect(state.currentResult.experiment).toEqual(request.experiment); expect(raw.header.experiment).toEqual(request.experiment); expect(raw.header.sampling).toEqual(request.sampling);
  expect(state.currentResult.planes).toEqual(raw.header.planes); expect(state.currentResult.stages).toEqual(raw.header.stages); expect(state.currentResult.x).toEqual(Array.from(raw.x)); expect(state.currentResult.y).toEqual(Array.from(raw.y));
  expect(state.selectedIndex).toBe(raw.header.planes.length - 1); expect(state.sectionIntensity).toEqual(Array.from(raw.intensity.subarray((raw.header.planes.length - 1) * nx * ny)));
  expect(state.selectedSample.intensity).toBe(state.sectionIntensity[Math.floor(ny / 2) * nx + Math.floor(nx / 2)]); expect(state.limits).toEqual({ min: 0, max: 3 });
  return { request, raw, state, bytes };
}
async function edit(page: Page, id: string, value: string): Promise<void> { await page.getByTestId(id).fill(value); await page.getByTestId(id).blur(); await ready(page); expect((await wave(page)).currentResult).toBeNull(); }
function relative(a: number[], b: number[]): number { let e = 0, d = 0; a.forEach((v, i) => { e += (v - b[i]) ** 2; d += v * v; }); return Math.sqrt(e / d); }
function percentile(values: number[], q: number): number { const sorted = [...values].sort((a, b) => a - b); return sorted[Math.floor((sorted.length - 1) * q)]; }

for (const [width, height] of [[1366, 768], [1440, 900], [1920, 1080]]) test(`genuine W1 ${width}x${height} sections preserve values and passive inspection`, async ({ page, browser }) => {
  await page.setViewportSize({ width, height }); const calls = await load(page), capture = await calculate(page), { nx, ny } = capture.request.experiment.grid;
  for (const index of [0, 4, 5, 8, 9, 13, 24]) {
    await page.getByTestId('w1-section').selectOption(String(index)); const state = await wave(page);
    expect(state.selectedId).toBe(capture.raw.header.planes[index].id); expect(state.sectionIntensity).toEqual(Array.from(capture.raw.intensity.subarray(index * nx * ny, (index + 1) * nx * ny)));
    await page.getByTestId('w1-column').fill('70'); await page.getByTestId('w1-column').blur(); await page.getByTestId('w1-row').fill('59'); await page.getByTestId('w1-row').blur();
    const selected = await wave(page); expect(selected.selectedSample).toMatchObject({ row: 59, column: 70, x_m: capture.raw.x[70], y_m: capture.raw.y[59], intensity: capture.raw.intensity[index * nx * ny + 59 * nx + 70] });
  }
  await page.getByTestId('w1-full-precision').check(); await expect(page.getByTestId('w1-pixel')).toContainText((await wave(page)).selectedSample.intensity.toPrecision(17));
  await page.getByTestId('w1-cursor').focus(); await page.keyboard.press('Home'); await page.keyboard.press('ArrowRight'); expect((await wave(page)).selectedIndex).toBe(1);
  for (const id of ['w1-top', 'w1-overview', 'w1-focus', 'w1-reset']) await page.getByTestId(id).click();
  await page.getByTestId('w1-glow').uncheck(); await page.getByTestId('w1-glow').check();
  await page.getByTestId('w1-range-max').fill('3'); await page.getByTestId('w1-apply-range').click();
  const actual = await snap(page); expect(actual.ownedMemory.retainedBytes).toBeLessThanOrEqual(16 * 1024 * 1024); expect(actual.scene.owned.controls).toBe(1); expect(actual.scene.owned.resizeObservers).toBe(1);
  expect(calls).toEqual(['/api/w1/simulate']); expect((await wave(page)).currentResult.requestId).toBe(capture.request.request_id);
  const geometry = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth })); expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.width + 1);
  await page.getByTestId('w1-overview').click(); await page.getByTestId('bench-host').evaluate(element => element.scrollIntoView({ block: 'start' })); await frames(page, 30); await image(page, `bench_${width}x${height}`);
  await page.getByTestId('w1-pixel').scrollIntoViewIfNeeded(); await image(page, `section_${width}x${height}`);
  save(`layout_${width}x${height}`, { browser: browser.version(), viewport: { width, height }, request: capture.request, state: await wave(page), scene: (await snap(page)).scene, calls, geometry });
});

test('genuine W1 focal aperture wavelength and distance changes detach and recompute', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 }); const calls = await load(page), first = await calculate(page); await page.getByTestId('w1-overview').click(); await frames(page); await image(page, 'parameters_before');
  const changes: any[] = []; let previous = first;
  for (const [selection, field, value, name] of [['lens', 'edit-components-1-focal_length_m', '40', 'focal'], ['aperture', 'edit-components-0-radius_m', '80', 'aperture'], ['source', 'edit-wavelength_m', '780', 'wavelength'], ['detector', 'edit-observation-z_m', '300', 'distance']]) {
    await page.getByTestId('bench-host').evaluate(element => element.scrollIntoView({ block: 'start' })); await frames(page); const cameraBefore = (await snap(page)).scene.camera; await image(page, `${name}_before`);
    await page.getByTestId('select-' + selection).click(); const beforeCalls = calls.length; await edit(page, field, value); await expect(page.getByTestId('w1-status')).toContainText('STALE'); expect(calls.length).toBe(beforeCalls);
    const next = await calculate(page), change = relative(previous.state.sectionIntensity, next.state.sectionIntensity); expect(change, name).toBeGreaterThan(.02);
    expect((await snap(page)).scene.camera).toEqual(cameraBefore); await page.getByTestId('bench-host').evaluate(element => element.scrollIntoView({ block: 'start' })); await frames(page); await image(page, `${name}_after`);
    changes.push({ name, value, relativeTerminalIntensityL2: change, before: previous.request, after: next.request, stages: next.state.currentResult.stages }); previous = next;
  }
  await page.getByTestId('w1-overview').click(); await frames(page); await image(page, 'parameters_after'); expect(calls).toHaveLength(5); save('parameter_sensitivity', { changes, calls });
});

test('genuine mixed retained W1 old modes R03 and documents obey aggregate admission and release', async ({ page }) => {
  const calls = await load(page); await calculate(page); const w1Id = (await wave(page)).currentResult.requestId;
  await page.getByTestId('doc-toggle').click(); await page.getByTestId('doc-title').fill('W1 mixed ownership'); await page.getByTestId('doc-export').click(); await expect(page.getByTestId('doc-download-area')).toBeVisible();
  await page.getByTestId('research-workspace').click(); await expect(page.getByTestId('r03-compute')).toBeEnabled(); await page.getByTestId('r03-compute').click(); await expect.poll(async () => (await snap(page)).idealPolarization.currentResult?.requestId).toBeTruthy();
  expect((await snap(page)).ownedMemory.sharedGeometryAliasBytes).toBe(92);
  await page.getByTestId('ordinary-workspace').click();
  const old = async (mode: string, button: string, key: string) => { await page.getByTestId('mode').selectOption(mode); await expect(page.getByTestId(button)).toBeEnabled(); await page.getByTestId(button).click(); await expect.poll(async () => (await snap(page))[key].currentResult?.requestId).toBeTruthy(); };
  await old('polarization', 'pl-simulate', 'polarization'); await old('polarized_two_path', 'pt-simulate', 'polarizedTwoPath'); await old('two_path', 'tp-simulate', 'twoPath');
  for (const axis of ['nx', 'ny']) { await page.getByTestId(`tp-edit-grid-${axis}`).fill('512'); await page.getByTestId(`tp-edit-grid-${axis}`).blur(); await expect(page.getByTestId('tp-simulate')).toBeEnabled(); }
  const samples: any[] = []; let rejected = false;
  for (let attempt = 0; attempt < 3; attempt++) {
    const before = await snap(page), count = calls.length, priorId = before.twoPath.currentResult?.requestId; await page.getByTestId('tp-simulate').click();
    await expect.poll(async () => { const state = (await snap(page)).twoPath; return !state.active && (!!state.error || !!state.renderError || state.currentResult?.requestId !== priorId); }).toBe(true);
    const after = await snap(page); samples.push({ attempt, before, after, callsBefore: count, callsAfter: calls.length }); expect(after.ownedMemory.retainedBytes).toBeLessThanOrEqual(16 * 1024 * 1024);
    if (/budget|預算/i.test(after.twoPath.error ?? '')) {
      expect(calls.length).toBe(count); expect(after.twoPath.lastResult).toEqual(before.twoPath.lastResult); expect(after.twoPath.completedNumerical).toEqual(before.twoPath.completedNumerical); expect(after.ownedMemory).toEqual(before.ownedMemory); rejected = true; break;
    }
  }
  expect(rejected, 'Actual aggregate overlap must reject before another HTTP calculation').toBe(true); const preserved = await snap(page);
  expect(preserved.waveField.lastResult.requestId).toBe(w1Id); expect(preserved.idealPolarization.lastResult).not.toBeNull(); expect(preserved.polarization.lastResult).not.toBeNull(); expect(preserved.polarizedTwoPath.lastResult).not.toBeNull(); expect(preserved.documents.state.preparedDownload).not.toBeNull();
  const count = calls.length; await page.locator('.release-panel > summary').click(); await page.getByTestId('release-results').click(); const released = await snap(page);
  expect(released.waveField.numericalBytes).toBe(0); expect(released.waveField.displayBytes).toBe(0); expect(released.idealPolarization.lastResult).toBeNull(); expect(released.ownedMemory.scientificBytes).toBe(0); expect(released.documents).toEqual(preserved.documents); expect(released.scene.camera).toEqual(preserved.scene.camera); expect(calls.length).toBe(count);
  for (const key of ['twoPath', 'polarization', 'polarizedTwoPath']) expect(released[key].candidate).toEqual(preserved[key].candidate);
  save('mixed_ownership', { samples, preserved, released, calls, scope: 'Actual retained modes, W1 displays, R03 and prepared document; fixed aggregate admission, no eviction or automatic retry; excludes test-owned response clones and whole heap/GPU memory' });
});

test('genuine W1 late completion stays detached and display/context recovery never propagates', async ({ page }) => {
  const calls = await load(page); await calculate(page); let release!: () => void, received!: () => void;
  const held = new Promise<void>(resolve => release = resolve), started = new Promise<void>(resolve => received = resolve);
  await page.route('**/api/w1/simulate', async route => { const response = await route.fetch(); received(); await held; await route.fulfill({ response }); });
  await page.getByTestId('simulate').click(); await started;
  await page.getByTestId('edit-wavelength_m').fill('700'); await page.getByTestId('edit-wavelength_m').blur();
  await expect.poll(async () => (await snap(page)).pendingValidation).toBe(false); expect((await wave(page)).currentResult).toBeNull(); release();
  await expect.poll(async () => !!(await wave(page)).active).toBe(false); expect((await wave(page)).currentResult).toBeNull(); await page.unroute('**/api/w1/simulate');
  await calculate(page); const before = await wave(page), count = calls.length;
  await page.evaluate(() => { const canvas = document.querySelector<HTMLCanvasElement>('[data-testid="bench-canvas"]')!, extension = canvas.getContext('webgl2')!.getExtension('WEBGL_lose_context')!; (window as any).__w1ContextExtension = extension; extension.loseContext(); });
  await expect.poll(async () => !!(await wave(page)).renderError).toBe(true); expect((await wave(page)).currentResult).toBeNull(); expect((await wave(page)).completedNumerical.requestId).toBe(before.currentResult.requestId);
  await page.evaluate(() => (window as any).__w1ContextExtension.restoreContext());
  await expect.poll(async () => (await snap(page)).scene.contextLost).toBe(false);
  await expect(page.getByTestId('w1-retry-display')).toBeVisible(); await page.getByTestId('w1-retry-display').click(); await expect.poll(async () => (await wave(page)).currentResult?.requestId).toBe(before.currentResult.requestId); expect(calls.length).toBe(count);
  const same = (await wave(page)).sectionIntensity;
  for (let n = 0; n < 3; n++) { await calculate(page); expect((await wave(page)).sectionIntensity).toEqual(same); expect((await snap(page)).ownedMemory.retainedBytes).toBeLessThanOrEqual(16 * 1024 * 1024); }
  await page.locator('.release-panel > summary').click(); await page.getByTestId('release-results').click(); const released = await snap(page); expect(released.waveField.currentResult).toBeNull(); expect(released.waveField.lastResult).toBeNull(); expect(released.waveField.numericalBytes).toBe(0); expect(released.waveField.displayBytes).toBe(0); expect(released.candidate).toEqual(before.currentResult.experiment);
  save('late_context_release', { calls, before, released });
});

test('genuine W1 actual Chrome 200 percent zoom retains readout and local table access', async ({}, info) => {
  const profile = info.outputPath('actual-zoom-profile'); mkdirSync(resolve(profile, 'Default'), { recursive: true }); writeFileSync(resolve(profile, 'Default/Preferences'), JSON.stringify({ partition: { default_zoom_level: { x: Math.log(2) / Math.log(1.2) } } }), { flag: 'wx' });
  const context = await chromium.launchPersistentContext(profile, { channel: 'chrome', headless: true, viewport: null, deviceScaleFactor: undefined, baseURL: 'http://127.0.0.1:8510', args: ['--window-size=1440,900'] });
  try { const page = context.pages()[0] ?? await context.newPage(), calls = await load(page); await calculate(page); await page.getByTestId('w1-full-precision').check();
    const zoom = await page.evaluate(() => ({ width: innerWidth, outerWidth, dpr: devicePixelRatio, scale: visualViewport?.scale, scrollWidth: document.documentElement.scrollWidth })); expect(zoom.dpr).toBe(2); expect(zoom.scale).toBe(1); expect(zoom.width).toBeLessThan(740); expect(zoom.scrollWidth).toBeLessThanOrEqual(zoom.width + 1);
    const region = page.getByRole('region', { name: '實際截面與 norm，可水平捲動' }); await region.focus(); await page.keyboard.press('End'); await page.keyboard.press('ArrowRight');
    const table = await region.evaluate(element => ({ left: element.scrollLeft, width: element.clientWidth, content: element.scrollWidth, cells: [...element.querySelectorAll('td')].slice(0, 8).map(cell => ({ text: cell.textContent, whiteSpace: getComputedStyle(cell).whiteSpace })) })); expect(table.cells.every(cell => cell.whiteSpace === 'nowrap')).toBe(true);
    await page.getByTestId('w1-pixel').scrollIntoViewIfNeeded(); const cdp = await context.newCDPSession(page), shot = await cdp.send('Page.captureScreenshot', { format: 'png', fromSurface: true, captureBeyondViewport: false }); mkdirSync(evidence, { recursive: true }); writeFileSync(resolve(evidence, 'actual_200percent.png'), Buffer.from(shot.data, 'base64'), { flag: 'wx' }); expect(calls).toEqual(['/api/w1/simulate']); save('actual_200percent', { zoom, table, calls, state: await wave(page) });
  } finally { await context.close(); }
});

test.describe('W1 genuine unaccelerated recording', () => {
  test('configuration explicit calculation cursor stale edit and changed beam recording', async ({ browser }) => {
    const context = await browser.newContext({ baseURL: 'http://127.0.0.1:8510', viewport: { width: 1440, height: 900 }, recordVideo: { dir: resolve(evidence, 'recording'), size: { width: 1440, height: 900 } } });
    const page = await context.newPage(); try {
    const started = Date.now(), calls = await load(page); await page.waitForTimeout(1500); const first = await calculate(page); await page.getByTestId('w1-overview').click(); await page.getByTestId('bench-host').scrollIntoViewIfNeeded(); await page.waitForTimeout(2500);
    for (const key of ['Home', 'ArrowRight', 'ArrowRight', 'ArrowRight', 'End', 'ArrowLeft']) { await page.getByTestId('w1-cursor').focus(); await page.keyboard.press(key); await page.waitForTimeout(600); }
    await page.getByTestId('w1-section').selectOption('13'); await page.getByTestId('w1-full-precision').check();
    await page.mouse.move(12, 450); await page.mouse.wheel(0, 700); await frames(page, 30);
    await page.locator('.w1-inspector').evaluate(element => element.scrollIntoView({ block: 'start' }));
    await expect(page.getByTestId('w1-cross-section')).toBeInViewport({ ratio: 1 }); await expect(page.getByTestId('w1-pixel')).toBeInViewport();
    // A real pointer pick visibly updates the inspected sample. Save the same
    // production viewport independently of Chrome's video screencast stream.
    const inspectBox = await page.getByTestId('w1-cross-section').boundingBox(); expect(inspectBox).not.toBeNull();
    await page.getByTestId('w1-cross-section').click({ position: { x: 70.5 / 128 * inspectBox!.width, y: 59.5 / 128 * inspectBox!.height } });
    expect((await wave(page)).selectedSample).toMatchObject({ row: 59, column: 70, intensity: first.raw.intensity[13 * 128 * 128 + 59 * 128 + 70] });
    await frames(page, 30); await image(page, 'recording_cross_section');
    save('recording_cross_section_viewport', await page.evaluate(() => ({ scrollY, inspector: document.querySelector('.w1-inspector')!.getBoundingClientRect().toJSON(), canvas: document.querySelector('[data-testid="w1-cross-section"]')!.getBoundingClientRect().toJSON() })));
    await page.waitForTimeout(2500);
    await page.getByTestId('select-lens').click(); await edit(page, 'edit-components-1-focal_length_m', '40'); await page.getByTestId('w1-status').scrollIntoViewIfNeeded(); await expect(page.getByTestId('w1-status')).toContainText('STALE'); await page.waitForTimeout(2000);
    const after = await calculate(page); expect(relative(first.state.sectionIntensity, after.state.sectionIntensity)).toBeGreaterThan(.1); await page.getByTestId('w1-overview').click(); await page.getByTestId('bench-host').scrollIntoViewIfNeeded(); await page.waitForTimeout(3000);
    await page.getByTestId('w1-top').click(); await page.waitForTimeout(1500); await page.getByTestId('w1-focus').click(); await page.waitForTimeout(1500); await page.getByTestId('w1-reset').click(); await page.waitForTimeout(1500);
    const box = await page.getByTestId('bench-canvas').boundingBox(); await page.mouse.move(box!.x + box!.width * .4, box!.y + box!.height * .5); await page.mouse.down(); await page.mouse.move(box!.x + box!.width * .55, box!.y + box!.height * .42, { steps: 35 }); await page.mouse.up(); await page.waitForTimeout(1500); await page.getByTestId('w1-reset').click();
    const remaining = 33_000 - (Date.now() - started); if (remaining > 0) await page.waitForTimeout(remaining); const state = await snap(page), runtime = state.scene.waveField;
    expect(runtime.frameIntervalsMs.length).toBeGreaterThan(30); expect(percentile(runtime.frameIntervalsMs, .95)).toBeLessThanOrEqual(33.4); expect(percentile(runtime.rendererSubmissionMs, .95)).toBeLessThanOrEqual(8); expect(calls).toEqual(['/api/w1/simulate', '/api/w1/simulate']);
    save('recording_observations', { browser: browser.version(), elapsedSeconds: (Date.now() - started) / 1000, viewport: { width: 1440, height: 900 }, calls, before: first.state, after: after.state, scene: state.scene, ownedMemory: state.ownedMemory, rendererSubmissionP95Ms: percentile(runtime.rendererSubmissionMs, .95), rafIntervalP95Ms: percentile(runtime.frameIntervalsMs, .95), timingScope: 'CPU renderer submission and browser RAF intervals; not complete GPU-frame time or universal FPS' });
    } finally { await context.close(); }
  });
});

test('controlled W1 actual-browser disconnect retains worker through genuine completion', async ({ page, context }) => {
  const directory = process.env.W1_HELD_DIR; test.skip(!directory, 'Requires separately owned held-worker child; production has no fault or release endpoint.'); const owned = resolve(root, directory!);
  const calls = await load(page); await page.getByTestId('simulate').click(); await expect.poll(() => { try { return JSON.parse(readFileSync(resolve(owned, 'started.json'), 'utf8')).operation; } catch { return null; } }).toBe('wave_field');
  await context.close(); const response = await fetch('http://127.0.0.1:8510/api/v1/health'); expect((await response.json() as any).busy).toBe(true); writeFileSync(resolve(owned, 'release.flag'), 'Release only recorded task-owned worker.', { flag: 'wx' });
  await expect.poll(async () => (await (await fetch('http://127.0.0.1:8510/api/v1/health')).json() as any).busy).toBe(false); expect(calls).toEqual(['/api/w1/simulate']); save('controlled_disconnect', { directory, calls, completion: JSON.parse(readFileSync(resolve(owned, 'completed.json'), 'utf8')) });
});
