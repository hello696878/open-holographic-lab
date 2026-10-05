/** Production-build acceptance. Synthetic displays are explicitly separate from V0 evidence. */
import { test, expect, type Page } from '@playwright/test';
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { Experiment, RequestEnvelope } from '../src/contracts';

const root = resolve('../..');
const evidence = resolve(root, process.env.V1_EVIDENCE_DIR ?? 'runs/v1_acceptance_20261005');
const api = JSON.parse(readFileSync(resolve(evidence, process.env.V1_API_EVIDENCE ?? 'api_evidence_1.json'), 'utf8'));
const figures = resolve(root, 'docs/handoffs/v1/figures');
const smokeOnly = process.env.V1_SMOKE === '1';
const snap = (page: Page): Promise<any> => page.evaluate(() => window.__benchDebug.snapshot());
async function ready(page: Page): Promise<void> {
  await expect.poll(async () => (await snap(page)).status).toBe('ready');
  await expect(page.getByTestId('simulate')).toBeEnabled();
}
async function load(page: Page): Promise<void> { await page.goto('/'); await ready(page); }
async function settled(page: Page): Promise<void> {
  await page.evaluate(() => new Promise<void>(resolve => {
    let frames = 0; const next = () => ++frames < 80 ? requestAnimationFrame(next) : resolve(); requestAnimationFrame(next);
  }));
}
async function preset(page: Page, id: string): Promise<void> { await page.getByTestId('preset').selectOption(id); await ready(page); }
async function edit(page: Page, id: string, value: string): Promise<void> {
  await page.getByTestId(id).fill(value); await page.getByTestId(id).blur(); await ready(page);
}
async function simulate(page: Page, label: string): Promise<any> {
  const previousId = (await snap(page)).currentResult?.requestId;
  await page.getByTestId('simulate').click();
  await expect.poll(async () => {
    const state = await snap(page);
    return !state.active && state.currentResult && state.currentResult.requestId !== previousId;
  }).toBeTruthy();
  await expect.poll(async () => (await snap(page)).currentResult?.experiment).toEqual(api.cases[label].experiment);
  const state = await snap(page);
  expect(state.currentResult.intensityMax).toBe(api.cases[label].intensity_max);
  expect(state.currentResult.stages).toEqual(api.cases[label].stages);
  expect(state.scene.textureRequestId).toBe(state.currentResult.requestId);
  const center = api.cases[label].samples.find((s: any) => s.row === Math.floor(state.candidate.grid.ny / 2)
    && s.column === Math.floor(state.candidate.grid.nx / 2));
  expect(state.selectedPixel.intensity).toBe(center.intensity);
  return state;
}
async function record(name: string, value: unknown): Promise<void> {
  mkdirSync(evidence, { recursive: true });
  writeFileSync(resolve(evidence, `${name}.json`), JSON.stringify(value, null, 2), { flag: 'wx' });
}

test.beforeEach(async ({ page }) => {
  // Applies to ordinary app page requests, not Chrome's own background traffic.
  await page.route('**/*', route => new URL(route.request().url()).origin === 'http://127.0.0.1:8510'
    ? route.continue() : route.abort('blockedbyclient'));
});

test('production V0 lens/readout smoke and local-only assets', async ({ page, browser }) => {
  const external: string[] = []; const posts: string[] = [];
  page.on('request', r => { if (new URL(r.url()).origin !== 'http://127.0.0.1:8510') external.push(r.url());
    if (r.method() === 'POST') posts.push(r.url()); });
  await load(page); expect((await snap(page)).scene.available).toBe(true);
  expect(posts.filter(p => p.endsWith('/simulate'))).toHaveLength(0);
  await preset(page, 'lens'); const result = await simulate(page, 'lens');
  // Default selection is the exact central sample. At a405px display a512 grid
  // has sub-CSS-pixel cells; full manual picking is tested on independent3x4/2x5.
  const sample = (await snap(page)).selectedPixel;
  expect(sample).toMatchObject(api.cases.lens.samples.find((s: any) => s.row === 256 && s.column === 256));
  expect(external).toEqual([]);
  await record(smokeOnly ? 'postcommit_browser_smoke' : 'browser_environment', {
    browserVersion: browser.version(), rendering: result.scene, sample, externalPageRequests: external,
    simulationPosts: posts.filter(p => p.endsWith('/simulate')).length, directV0Match: true,
  });
  if (!smokeOnly) { mkdirSync(figures, { recursive: true }); await page.screenshot({ path: resolve(figures, 'fig01_bench_lens.png'), fullPage: true }); }
});

test('camera selection color resize and 3D picking do not alter optics or call API', async ({ page }) => {
  test.skip(smokeOnly);
  await load(page); await preset(page, 'lens'); await simulate(page, 'lens');
  const before = await snap(page); const calls: string[] = [];
  page.on('request', r => { if (r.method() === 'POST') calls.push(r.url()); });
  await page.getByTestId('zoom-in').click();
  expect((await snap(page)).scene.camera.position).not.toEqual(before.scene.camera.position);
  await page.getByTestId('pan-left').click();
  expect((await snap(page)).scene.camera.target).not.toEqual(before.scene.camera.target);
  await page.getByTestId('reset-view').click();
  const b = (await page.getByTestId('bench-canvas').boundingBox())!;
  await page.mouse.move(b.x + b.width * .45, b.y + b.height * .25); await page.mouse.down();
  await page.mouse.move(b.x + b.width * .60, b.y + b.height * .34, { steps: 12 }); await page.mouse.up();
  await settled(page); expect((await snap(page)).scene.camera.position).not.toEqual(before.scene.camera.position);
  const orbit = (await snap(page)).scene.camera;
  await page.mouse.move(b.x + b.width * .4, b.y + b.height * .3); await page.mouse.down({ button: 'right' });
  await page.mouse.move(b.x + b.width * .45, b.y + b.height * .33, { steps: 10 }); await page.mouse.up({ button: 'right' });
  await settled(page); expect((await snap(page)).scene.camera.target).not.toEqual(orbit.target);
  const pan = (await snap(page)).scene.camera;
  await page.mouse.wheel(0, -80); await settled(page);
  expect((await snap(page)).scene.camera.position).not.toEqual(pan.position);
  await page.getByTestId('reset-view').click(); await settled(page);
  const reset = (await snap(page)).scene.camera;
  reset.position.forEach((v: number, i: number) => expect(v).toBeCloseTo(before.scene.camera.position[i], 10));
  expect(reset.target).toEqual(before.scene.camera.target);
  await page.getByTestId('color-max').fill('0.5'); await page.getByTestId('color-max').blur();
  await expect(page.getByTestId('saturation')).toBeVisible();
  await page.getByTestId('auto-color').click();
  await page.getByTestId('select-source').click(); await page.getByTestId('stage').selectOption('source');
  await page.setViewportSize({ width: 1200, height: 900 });
  await settled(page);
  // Actual ray picking at a noncentral detector sample; independent expected SI coordinate.
  const point = await page.evaluate(() => window.__benchDebug.worldToClient(.200, -.100, 2));
  await page.mouse.click(point!.x, point!.y);
  await expect.poll(async () => (await snap(page)).selectedPixel.column).toBe(306);
  expect((await snap(page)).selectedPixel.row).toBe(281);
  expect((await snap(page)).selection).toBe('screen');
  const after = await snap(page);
  expect(after.candidate).toEqual(before.candidate); expect(after.currentResult.requestId).toBe(before.currentResult.requestId);
  expect(calls).toEqual([]); expect(after.scene.drawingBuffer.dpr).toBeLessThanOrEqual(2);
  expect(after.scene.drawingBuffer.width * after.scene.drawingBuffer.height).toBeLessThanOrEqual(4_000_000);
});

test('real edits change V0 output; aperture uses shared limits and original norm loss; stale screenshot', async ({ page }) => {
  test.skip(smokeOnly);
  await load(page); await preset(page, 'lens'); const open = await simulate(page, 'lens');
  await page.getByTestId('select-lens').click(); await edit(page, 'edit-components-0-focal_length_m', '-20');
  await simulate(page, 'negative_lens');
  await preset(page, 'lens'); await page.getByTestId('select-screen').click(); await edit(page, 'edit-observation-z_m', '10');
  await simulate(page, 'observation_10mm');
  await preset(page, 'aperture'); const clipped = await simulate(page, 'aperture_lens');
  expect(clipped.colorLimits).toEqual({ min: 0, max: 10 });
  expect(clipped.currentResult.stages.at(-1).norm).toBeLessThan(open.currentResult.stages.at(-1).norm);
  await page.screenshot({ path: resolve(figures, 'fig02_aperture_result.png'), fullPage: true });
  await page.getByTestId('select-aperture').click(); await edit(page, 'edit-components-0-radius_m', '40');
  await simulate(page, 'small_aperture');
  await page.getByTestId('select-screen').click(); await page.getByTestId('edit-observation-z_m').fill('-');
  const stale = await snap(page); expect(stale.currentResult).toBeNull(); expect(stale.scene.textureRequestId).toBeNull();
  expect(stale.lastResult.experiment.observation.z_m).toBe(.020);
  await expect(page.getByTestId('result-status')).toContainText('已過期');
  await expect(page.getByTestId('result-spec')).toContainText('20.00000');
  await page.screenshot({ path: resolve(figures, 'fig03_stale_result.png'), fullPage: true });
});

test('source fields signed lens rectangle add delete numeric order and z ghost rail', async ({ page }) => {
  test.skip(smokeOnly); await load(page);
  const simulations: string[] = []; page.on('request', r => { if (r.url().endsWith('/simulate')) simulations.push(r.url()); });
  await edit(page, 'edit-source-phase_rad', '.3'); await edit(page, 'edit-source-center_x_m', '2');
  await edit(page, 'edit-source-center_y_m', '-5'); await edit(page, 'edit-source-waist_radius_m', '90');
  await edit(page, 'edit-source-waist_z_m', '-1');
  await page.getByTestId('source-kind').selectOption('uniform'); await ready(page);
  await edit(page, 'edit-source-amplitude', '.7');
  await page.getByTestId('source-kind').selectOption('gaussian'); await ready(page);
  await page.getByTestId('add-kind').selectOption('rectangular_aperture'); await page.getByTestId('add').click(); await ready(page);
  await edit(page, 'edit-components-0-width_m', '120'); await edit(page, 'edit-components-0-height_m', '75');
  expect((await snap(page)).candidate.components[0]).toMatchObject({ width_m: 120 * 1e-6, height_m: 75 * 1e-6 });
  await page.getByTestId('delete').click(); await ready(page);
  await preset(page, 'aperture'); await page.getByTestId('select-aperture').click();
  await page.getByTestId('edit-components-0-z_m').fill('1'); await page.getByTestId('edit-components-0-z_m').blur();
  await expect(page.getByTestId('simulate')).toBeDisabled(); // Cannot silently sort past the lens at z=0.
  expect((await snap(page)).candidate.components.map((c: any) => c.id)).toEqual(['aperture', 'lens']);
  await edit(page, 'edit-components-0-z_m', '0');
  await preset(page, 'lens'); await page.getByTestId('select-lens').click(); await page.getByTestId('reset-view').click();
  const original = await snap(page);
  async function drag(targetZ: number, valid: boolean): Promise<void> {
    const rail = (await snap(page)).scene.rail;
    const start = await page.evaluate(p => window.__benchDebug.worldToClient(...p as [number, number, number]), rail.position);
    const end = await page.evaluate(p => window.__benchDebug.worldToClient(p[0], 0, p[1] * 100), [rail.position[0], targetZ]);
    await page.mouse.move(start!.x, start!.y); await page.mouse.down();
    await page.mouse.move(end!.x, end!.y, { steps: 15 });
    const ghost = await snap(page); expect(ghost.scene.rail.dragging).toBe(true);
    expect(ghost.candidate).toEqual((await snap(page)).validatedDraft);
    await page.mouse.up();
    if (valid) { await ready(page); expect((await snap(page)).candidate.components[0].z_m).toBeCloseTo(targetZ, 5); }
    else expect((await snap(page)).candidate).toEqual(original.candidate);
  }
  await drag(-.005, false); await drag(.005, true);
  expect(simulations).toEqual([]);
});

test('rapid submissions remain single and edited pending response stays separately stale', async ({ page }) => {
  test.skip(smokeOnly); await load(page);
  let release!: () => void; let seen!: () => void; let calls = 0;
  const held = new Promise<void>(r => { release = r; }); const started = new Promise<void>(r => { seen = r; });
  await page.route('**/api/v1/simulate', async route => {
    calls++; const actual = await route.fetch(); seen(); await held; await route.fulfill({ response: actual });
  });
  await page.getByTestId('simulate').evaluate((button: HTMLButtonElement) => { button.click(); button.click(); button.click(); });
  await started; expect(calls).toBe(1); expect((await snap(page)).active).not.toBeNull();
  await page.getByTestId('edit-source-amplitude').fill('.5');
  await expect.poll(async () => (await snap(page)).pendingValidation).toBe(false);
  release(); await expect.poll(async () => (await snap(page)).active).toBeNull();
  const result = await snap(page); expect(result.lastResult.experiment.source.amplitude).toBe(1);
  expect(result.currentResult).toBeNull(); expect(result.scene.textureRequestId).toBeNull(); expect(calls).toBe(1);
});

test('malformed response and missing backend publish no fabricated success; reload passive; dark genuine', async ({ page }) => {
  test.skip(smokeOnly); await load(page);
  await page.route('**/api/v1/simulate', route => route.fulfill({ status: 200, contentType: 'application/octet-stream', body: Buffer.from('bad') }));
  await page.getByTestId('simulate').click(); await expect(page.getByTestId('error')).toBeVisible();
  expect((await snap(page)).lastResult).toBeNull(); expect((await snap(page)).scene.textureRequestId).toBeNull();
  await page.unroute('**/api/v1/simulate');
  await page.route('**/api/v1/simulate', route => route.abort('connectionrefused'));
  await page.getByTestId('simulate').click(); await expect(page.getByTestId('error')).toContainText('Failed to fetch');
  expect((await snap(page)).lastResult).toBeNull(); await page.unroute('**/api/v1/simulate');
  await edit(page, 'edit-source-amplitude', '0'); const dark = await simulate(page, 'dark');
  expect(dark.currentResult.intensityMax).toBe(0); expect(dark.currentResult.stages.at(-1).transmission_ratio).toBeNull();
  const rgba = await page.getByTestId('intensity-canvas').evaluate((canvas: HTMLCanvasElement) =>
    Array.from(canvas.getContext('2d')!.getImageData(0, 0, 1, 1).data)); expect(rgba).toEqual([0, 0, 0, 255]);
  const requests: string[] = []; page.on('request', r => { if (r.url().endsWith('/simulate')) requests.push(r.url()); });
  await page.reload(); await ready(page); expect(requests).toEqual([]); expect((await snap(page)).lastResult).toBeNull();
});

/** Independent synthetic bytes, no production encoder/decoder import. Display-only evidence. */
function syntheticFrame(envelope: RequestEnvelope, values: number[], sha: string): Buffer {
  const spec = envelope.experiment; const { nx, ny, dx, dy } = spec.grid;
  const norm = 1;
  const points = [['source', 0], ...spec.components.flatMap(c => [[`before:${c.id}`, c.z_m], [`after:${c.id}`, c.z_m]]), ['observation', spec.observation.z_m]];
  const stages = points.map(([selector, z_m], i) => ({ selector, z_m, norm, previous_norm: i ? norm : null,
    delta_norm: i ? 0 : null, transmission_ratio: i ? 1 : null }));
  const arrays = [{ name: 'intensity', dtype: 'float64-le', order: 'C', shape: [ny, nx], offset_bytes: 0, nbytes: ny * nx * 8, units: 'amplitude_unit^2' },
    { name: 'x_m', dtype: 'float64-le', order: 'C', shape: [nx], offset_bytes: ny * nx * 8, nbytes: nx * 8, units: 'm' },
    { name: 'y_m', dtype: 'float64-le', order: 'C', shape: [ny], offset_bytes: (ny * nx + nx) * 8, nbytes: ny * 8, units: 'm' }];
  const header = Buffer.from(JSON.stringify({ protocol_version: 1, request_id: envelope.request_id, experiment_sha256: sha,
    experiment: spec, stages, arrays, intensity_max: values.reduce((a, b) => Math.max(a, b), 0) }));
  const start = 16 + Math.ceil(header.length / 8) * 8;
  const bytes = Buffer.alloc(start + 8 * (ny * nx + nx + ny)); bytes.write('OHLABV1\0'); bytes.writeUInt32LE(header.length, 8); header.copy(bytes, 16);
  [...values, ...Array.from({ length: nx }, (_, c) => (c - Math.floor(nx / 2)) * dx),
    ...Array.from({ length: ny }, (_, r) => (r - Math.floor(ny / 2)) * dy)].forEach((v, i) => bytes.writeDoubleLE(v, start + i * 8));
  return bytes;
}

test('independent gray fixture catches extra gamma in actual WebGL and preserves raw float64', async ({ page }) => {
  test.skip(smokeOnly); await load(page);
  await page.route('**/api/v1/simulate', async route => {
    const envelope = route.request().postDataJSON(); const g = envelope.experiment.grid;
    const validated = await (await route.fetch({ url: 'http://127.0.0.1:8510/api/v1/validate' })).json();
    return route.fulfill({ status: 200, contentType: 'application/octet-stream', body: syntheticFrame(envelope, Array(g.nx * g.ny).fill(5), validated.experiment_sha256) });
  });
  await page.getByTestId('simulate').click(); await expect.poll(async () => (await snap(page)).currentResult?.intensityMax).toBe(5);
  const color = await page.evaluate(async () => {
    await new Promise<void>(r => requestAnimationFrame(() => requestAnimationFrame(() => r())));
    const point = window.__benchDebug.worldToClient(.2, -.1, 2)!;
    const canvas = document.querySelector<HTMLCanvasElement>('[data-testid="bench-canvas"]')!;
    const rect = canvas.getBoundingClientRect(); const gl = canvas.getContext('webgl2')!;
    const bytes = new Uint8Array(4); gl.readPixels(Math.floor((point.x - rect.left) * canvas.width / rect.width),
      canvas.height - 1 - Math.floor((point.y - rect.top) * canvas.height / rect.height), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, bytes);
    const other = document.querySelector<HTMLCanvasElement>('[data-testid="intensity-canvas"]')!.getContext('2d')!.getImageData(256, 256, 1, 1);
    return { gpu: Array.from(bytes), canvas2d: Array.from(other.data) };
  });
  for (const channel of color.gpu.slice(0, 3)) expect(Math.abs(channel - 128)).toBeLessThanOrEqual(3);
  expect(color.canvas2d).toEqual([128, 128, 128, 255]); expect((await snap(page)).selectedPixel.intensity).toBe(5);
  await record('browser_synthetic_gray', { ...color, tolerance: 'RGBA RGB128 +/-3 GPU; exact2D128; no V0 correctness claim' });
});

test('independent asymmetric 3x4 and 2x5 display cells and original readouts', async ({ page }) => {
  test.skip(smokeOnly); await load(page);
  // Optical fixture construction is through the ordinary numeric controls.
  await page.getByTestId('select-screen').click(); await edit(page, 'edit-observation-z_m', '0');
  await edit(page, 'edit-grid-dx', '2'); await edit(page, 'edit-grid-dy', '5');
  await page.route('**/api/v1/simulate', async route => {
    const envelope = route.request().postDataJSON(); const { nx, ny } = envelope.experiment.grid;
    const values = Array.from({ length: nx * ny }, (_, i) => 10 * (Math.floor(i / nx) + 1) + i % nx + 1);
    const validated = await (await route.fetch({ url: 'http://127.0.0.1:8510/api/v1/validate' })).json();
    return route.fulfill({ status: 200, contentType: 'application/octet-stream', body: syntheticFrame(envelope, values, validated.experiment_sha256) });
  });
  const checks = [];
  for (const [ny, nx] of [[3, 4], [2, 5]]) {
    await edit(page, 'edit-grid-ny', String(ny)); await edit(page, 'edit-grid-nx', String(nx));
    await page.getByTestId('color-max').fill('40'); await page.getByTestId('color-max').blur();
    await page.getByTestId('simulate').click(); await expect.poll(async () => (await snap(page)).currentResult?.shape).toEqual([ny, nx]);
    await page.getByTestId('reset-view').click();
    for (let i = 0; i < 22; i++) await page.getByTestId('zoom-in').click();
    await settled(page);
    const canvas = page.getByTestId('intensity-canvas'); const box = (await canvas.boundingBox())!;
    for (const [row, column] of [[0, 0], [ny - 1, nx - 1], [1, 1]]) {
      await canvas.click({ position: { x: (column + .5) / nx * box.width, y: (row + .5) / ny * box.height } });
      const p = (await snap(page)).selectedPixel;
      expect(p).toMatchObject({ row, column, intensity: 10 * (row + 1) + column + 1,
        x_m: (column - Math.floor(nx / 2)) * (2 * 1e-6), y_m: (row - Math.floor(ny / 2)) * (5 * 1e-6) });
      const point = await page.evaluate(p => window.__benchDebug.worldToClient(p.x_m * 1000, -p.y_m * 1000, 0), p);
      await page.mouse.click(point!.x, point!.y);
      expect((await snap(page)).selectedPixel).toMatchObject({ row, column, intensity: p.intensity });
      const rgba = await page.evaluate(point => {
        const canvas = document.querySelector<HTMLCanvasElement>('[data-testid="bench-canvas"]')!;
        const box = canvas.getBoundingClientRect(); const gl = canvas.getContext('webgl2')!; const data = new Uint8Array(4);
        gl.readPixels(Math.floor((point.x - box.left) * canvas.width / box.width),
          canvas.height - 1 - Math.floor((point.y - box.top) * canvas.height / box.height), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, data);
        return Array.from(data);
      }, point!);
      for (const channel of rgba.slice(0, 3)) expect(Math.abs(channel - Math.round(p.intensity / 40 * 255))).toBeLessThanOrEqual(3);
      checks.push(p);
    }
    const scene = (await snap(page)).scene;
    expect(scene.detector.width / scene.detector.height).toBeCloseTo(nx * 2 / (ny * 5), 12);
    expect(scene.detector.texture).toMatchObject({ flipY: false, generateMipmaps: false, colorSpace: 'srgb' });
  }
  await record('browser_synthetic_asymmetric', checks);
});

test('context loss and unsupported WebGL report presentation failure without automatic solve', async ({ page, context }) => {
  test.skip(smokeOnly); await load(page); await simulate(page, 'free');
  let calls = 0; page.on('request', r => { if (r.url().endsWith('/simulate')) calls++; });
  await page.getByTestId('bench-canvas').evaluate((canvas: HTMLCanvasElement) => {
    const ext = canvas.getContext('webgl2')!.getExtension('WEBGL_lose_context'); if (!ext) throw new Error('Required controlled context-loss extension unavailable');
    ext.loseContext();
  });
  await expect(page.getByTestId('render-error')).toBeVisible(); expect((await snap(page)).lastResult).not.toBeNull(); expect(calls).toBe(0);
  const unsupported = await context.newPage();
  await unsupported.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, kind: any, ...args: any[]) {
      return kind === 'webgl2' ? null : (original as any).call(this, kind, ...args);
    } as typeof original;
  });
  await load(unsupported); await expect(unsupported.getByTestId('render-error')).toBeVisible();
  expect((await snap(unsupported)).scene.available).toBe(false); expect((await snap(unsupported)).lastResult).toBeNull(); await unsupported.close();
});

test('predefined resource replacement sequence retains one active texture and bounded owned resources', async ({ page }) => {
  test.skip(smokeOnly); await load(page); const records = [];
  for (let cycle = 0; cycle < 5; cycle++) {
    await preset(page, 'aperture'); await page.getByTestId('add-kind').selectOption('thin_lens'); await page.getByTestId('add').click(); await ready(page);
    await page.getByTestId('delete').click(); await ready(page);
    await page.setViewportSize({ width: cycle % 2 ? 1300 : 1440, height: 1000 });
    await preset(page, 'lens'); const first = await simulate(page, 'lens'); const second = await simulate(page, 'lens');
    expect(second.currentResult.requestId).not.toBe(first.currentResult.requestId);
    await expect.poll(async () => (await snap(page)).scene.renderer.textures).toBe(1);
    const scene = (await snap(page)).scene; expect(scene.owned.textures).toBe(1); records.push(scene);
  }
  expect(records.map(r => r.owned)).toEqual(Array(5).fill(records[0].owned));
  expect(records.map(r => r.renderer.geometries)).toEqual(Array(5).fill(records[0].renderer.geometries));
  await record('browser_resources', records);
});

test('actual browser disconnect keeps running worker busy until controlled completion', async ({ page, context }) => {
  const directory = process.env.V1_CANCELLATION_DIR;
  test.skip(!directory, 'Requires the separately launched owned synchronization harness; production has no test-control endpoint.');
  const owned = resolve(root, directory!);
  await load(page); await page.getByTestId('simulate').click();
  await expect.poll(() => page.evaluate(async () => (await (await fetch('/api/v1/health')).json()).busy)).toBe(true);
  await expect.poll(() => {
    try { return JSON.parse(readFileSync(resolve(owned, 'started.json'), 'utf8')).waiting; }
    catch { return false; }
  }).toBe(true);
  const held = JSON.parse(readFileSync(resolve(owned, 'started.json'), 'utf8'));
  expect(held.waiting).toBe(true);
  await page.close(); // Disconnect the actual client while genuine Python work is held.
  const second = await context.newPage();
  await second.route('**/*', route => new URL(route.request().url()).origin === 'http://127.0.0.1:8510'
    ? route.continue() : route.abort('blockedbyclient'));
  await load(second); // Authoritative validation remains responsive during the first worker.
  const busy = await second.evaluate(async () => {
    const state = window.__benchDebug.snapshot() as any;
    const response = await fetch('/api/v1/simulate', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request_id: crypto.randomUUID(), experiment: state.validatedDraft }) });
    return { status: response.status, error: await response.json(), health: await (await fetch('/api/v1/health')).json() };
  });
  expect(busy.status).toBe(409); expect(busy.health.busy).toBe(true);
  writeFileSync(resolve(owned, 'release.flag'), 'explicit controlled release', { flag: 'wx' });
  await expect.poll(() => second.evaluate(async () => (await (await fetch('/api/v1/health')).json()).busy)).toBe(false);
  const firstCompletion = JSON.parse(readFileSync(resolve(owned, 'completed.json'), 'utf8'));
  expect(firstCompletion).toMatchObject({ request_id: held.request_id, outcome: 'success' });
  expect(firstCompletion.response_bytes).toBeGreaterThan(16);
  const completed = await simulate(second, 'free');
  await record('browser_cancellation_lifetime', { held, rejectedWhileDisconnected: busy,
    firstCompletion,
    laterRequestId: completed.currentResult.requestId, laterDirectV0Match: true,
    claim: 'Browser disconnect did not cancel Python computation or release its gate; only controlled real completion did.' });
  await second.close();
});
