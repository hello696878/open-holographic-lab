/** Genuine production/V2a browser acceptance; controlled failure evidence is separate. */
import { test, expect, type Page } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve('../..');
const evidence = resolve(root, process.env.V2B_EVIDENCE_DIR ?? 'runs/v2b_acceptance_20261006/acceptance/browser');
const api = JSON.parse(readFileSync(resolve(root, process.env.V2B_API_EVIDENCE ?? 'runs/v2b_acceptance_20261006/acceptance/api_evidence.json'), 'utf8'));
const figures = resolve(root, process.env.V2B_FIGURE_DIR ?? 'docs/handoffs/v2b/figures');
const smokeOnly = process.env.V2B_SMOKE === '1';
const partialOnly = process.env.V2B_PARTIAL_ONLY === '1';
const disconnectOnly = process.env.V2B_DISCONNECT_ONLY === '1';
const snap = (page: Page): Promise<any> => page.evaluate(() => window.__benchDebug.snapshot());

async function record(name: string, value: unknown): Promise<void> {
  mkdirSync(evidence, { recursive: true });
  writeFileSync(resolve(evidence, `${name}.json`), JSON.stringify(value, null, 2), { flag: 'wx' });
}
async function settled(page: Page): Promise<void> {
  await page.evaluate(() => new Promise<void>(resolve => {
    let frames = 0; const next = () => ++frames < 60 ? requestAnimationFrame(next) : resolve(); requestAnimationFrame(next);
  }));
}
async function ready(page: Page): Promise<void> {
  await expect.poll(async () => (await snap(page)).twoPath.status).toBe('ready');
  await expect(page.getByTestId('tp-simulate')).toBeEnabled();
}
async function load(page: Page): Promise<void> {
  await page.goto('/');
  await page.getByTestId('mode').selectOption('two_path');
  await ready(page);
}
async function configure(page: Page, label: string): Promise<void> {
  const fixture = api.cases[label];
  if (!fixture) throw new Error(`Required independent API fixture missing: ${label}`);
  await page.getByTestId('tp-source-kind').selectOption(fixture.experiment.source.kind);
  await ready(page);
  for (const [path, text] of Object.entries(fixture.editor_inputs)) {
    const input = page.getByTestId(`tp-edit-${path.replaceAll('.', '-')}`);
    await input.fill(text as string); await input.blur(); await ready(page);
  }
  expect((await snap(page)).twoPath.validatedDraft).toEqual(fixture.experiment);
}
function maxima(result: any): number[] { return result.intensityMax ?? result.ports.map((p: any) => p.intensityMax); }
function textureIds(scene: any): unknown[] { return scene.dualTextureRequestIds ?? []; }
async function simulate(page: Page, label: string): Promise<any> {
  const oldId = (await snap(page)).twoPath.currentResult?.requestId;
  await page.getByTestId('tp-simulate').click();
  await expect.poll(async () => {
    const tp = (await snap(page)).twoPath;
    return !tp.active && tp.currentResult && tp.currentResult.requestId !== oldId;
  }).toBeTruthy();
  const state = await snap(page); const expected = api.cases[label];
  expect(state.twoPath.currentResult.experiment).toEqual(expected.experiment);
  expect(maxima(state.twoPath.currentResult)).toEqual(expected.intensity_max);
  expect(state.twoPath.currentResult.norms).toEqual(expected.norms);
  expect(state.twoPath.currentResult.diagnostics).toEqual(expected.diagnostics);
  expect(textureIds(state.scene)).toEqual([state.twoPath.currentResult.requestId, state.twoPath.currentResult.requestId]);
  return state;
}
async function pick(page: Page, sample: any): Promise<{ x: number; y: number; visible: boolean }> {
  const point = await page.evaluate(({ port, row, column }) => {
    const debug = window.__benchDebug as any;
    const portIndex = port === 'port_0' ? 0 : 1;
    if (debug.dualPixelWorld) {
      const world = debug.dualPixelWorld(portIndex, row, column);
      if (!world) return null;
      return debug.worldToClient(world.x, world.y, world.z);
    }
    const state = debug.snapshot();
    const detector = state.scene.dualDetectors.find((d: any) => (d.port ?? d.id ?? d.portId) === portIndex || (d.port ?? d.id ?? d.portId) === port);
    const grid = state.twoPath.currentResult.experiment.grid;
    const [x, y, z] = detector.position;
    return debug.worldToClient(x + ((column + .5) / grid.nx - .5) * detector.width,
      y + (.5 - (row + .5) / grid.ny) * detector.height, z);
  }, sample);
  expect(point?.visible).toBe(true);
  await page.mouse.click(point!.x, point!.y);
  await expect.poll(async () => (await snap(page)).twoPath.selectedPixel).toMatchObject({ ...sample, port: sample.port === 'port_0' ? 0 : 1 });
  return point!;
}
async function sweep(page: Page): Promise<any> {
  const previousId = (await snap(page)).twoPath.currentSweep?.requestId;
  await page.getByTestId('tp-sweep').click();
  await expect.poll(async () => {
    const tp = (await snap(page)).twoPath;
    return !tp.active && tp.currentSweep && tp.currentSweep.requestId !== previousId;
  }).toBeTruthy();
  return (await snap(page)).twoPath.currentSweep;
}
async function focusPort(page: Page, port: 0 | 1): Promise<void> {
  // Camera gestures only: pan in two orthogonal views to move the orbit target
  // to the detector plane before zooming. A single perspective pan cannot
  // remove the detector's depth offset and can zoom past the sampled plane.
  await page.getByTestId('reset-view').click(); await settled(page);
  const orient = async (theta: number): Promise<void> => {
    const camera = (await snap(page)).scene.camera;
    const offset = camera.position.map((v: number, i: number) => v - camera.target[i]);
    const radius = Math.hypot(...offset); const currentTheta = Math.atan2(offset[0], offset[2]);
    const currentPhi = Math.acos(offset[1] / radius);
    const box = (await page.getByTestId('bench-canvas').boundingBox())!;
    const x = box.x + box.width / 2, y = box.y + box.height / 2;
    await page.mouse.move(x, y); await page.mouse.down();
    await page.mouse.move(x + (currentTheta - theta) * box.height / (2 * Math.PI),
      y + (currentPhi - Math.PI / 2) * box.height / (2 * Math.PI), { steps: 8 });
    await page.mouse.up(); await settled(page);
  };
  const panToPlane = async (): Promise<void> => {
    const state = await snap(page); const camera = state.scene.camera;
    const detector = state.scene.dualDetectors[port];
    const offset = camera.position.map((v: number, i: number) => v - camera.target[i]);
    const radius = Math.hypot(...offset); const view = offset.map((v: number) => -v / radius);
    const rightLength = Math.hypot(view[2], view[0]);
    const right = [-view[2] / rightLength, 0, view[0] / rightLength];
    const up = [right[1] * view[2] - right[2] * view[1], right[2] * view[0] - right[0] * view[2],
      right[0] * view[1] - right[1] * view[0]];
    const error = detector.position.map((v: number, i: number) => v - camera.target[i]);
    const horizontal = error.reduce((a: number, v: number, i: number) => a + v * right[i], 0);
    const vertical = error.reduce((a: number, v: number, i: number) => a + v * up[i], 0);
    const box = (await page.getByTestId('bench-canvas').boundingBox())!;
    const perPixel = 2 * radius * Math.tan(42 * Math.PI / 360) / box.height;
    const x = box.x + box.width / 2, y = box.y + box.height / 2;
    await page.mouse.move(x, y); await page.mouse.down({ button: 'right' });
    await page.mouse.move(x - horizontal / perPixel, y + vertical / perPixel, { steps: 8 });
    await page.mouse.up({ button: 'right' }); await settled(page);
  };
  for (const theta of [0, Math.PI / 2, 0]) {
    await orient(theta); await panToPlane();
  }
  for (let zoom = 0; zoom < 22; zoom++) {
    await page.getByTestId('zoom-in').click();
  }
  await settled(page);
  const final = await snap(page);
  for (let axis = 0; axis < 3; axis++) {
    expect(Math.abs(final.scene.camera.target[axis] - final.scene.dualDetectors[port].position[axis])).toBeLessThan(1e-5);
  }
}
test.beforeEach(async ({ page }) => {
  await page.route('**/*', route => new URL(route.request().url()).origin === 'http://127.0.0.1:8510'
    ? route.continue() : route.abort('blockedbyclient'));
});

test('genuine dual known phases and both original readouts use one submitted V2a result', async ({ page, browser }) => {
  test.skip(partialOnly || disconnectOnly);
  const numerical: string[] = []; const external: string[] = [];
  page.on('request', request => {
    if (new URL(request.url()).origin !== 'http://127.0.0.1:8510') external.push(request.url());
    if (request.url().endsWith('/simulate') || request.url().endsWith('/sweep')) numerical.push(request.url());
  });
  await load(page); expect(numerical).toEqual([]);
  const records = [];
  for (const label of smokeOnly ? ['phase_halfpi'] : ['phase_0', 'phase_halfpi', 'phase_pi', 'signed_phase']) {
    await configure(page, label);
    const phaseButton: Record<string, string> = { phase_0: 'tp-phase-0', phase_halfpi: 'tp-phase-halfpi', phase_pi: 'tp-phase-pi' };
    if (phaseButton[label]) { await page.getByTestId(phaseButton[label]).click(); await ready(page); }
    const state = await simulate(page, label);
    for (const port of ['port_0', 'port_1']) {
      const sample = api.cases[label].samples.find((p: any) => p.port === port && p.row === 33 && p.column === 34);
      await pick(page, sample);
    }
    records.push({ label, result: state.twoPath.currentResult, scene: state.scene, selected: (await snap(page)).twoPath.selectedPixel });
    if (label === 'phase_halfpi' && !smokeOnly) {
      mkdirSync(figures, { recursive: true });
      await page.screenshot({ path: resolve(figures, 'fig01_dual_outputs.png'), fullPage: true });
    }
  }
  expect(external).toEqual([]);
  await record(smokeOnly ? 'postcommit_dual_smoke' : 'browser_dual_known_phases', {
    browserVersion: browser.version(), records, numericalRequests: numerical, externalPageRequests: external,
    claim: 'Actual HTTP results and both picked original float64 values matched independently captured public V2a evidence.',
  });
});

test('real Gaussian source distance phase edits preserve shared scale and original input diagnostics', async ({ page }) => {
  test.skip(smokeOnly || partialOnly || disconnectOnly); await load(page);
  await configure(page, 'gaussian'); const first = await simulate(page, 'gaussian');
  await configure(page, 'gaussian_changed'); const edited = await snap(page);
  expect(edited.twoPath.currentResult).toBeNull(); expect(textureIds(edited.scene)).toEqual([null, null]);
  const second = await simulate(page, 'gaussian_changed');
  expect(second.twoPath.currentResult.requestId).not.toBe(first.twoPath.currentResult.requestId);
  expect(maxima(second.twoPath.currentResult)).not.toEqual(maxima(first.twoPath.currentResult));
  expect(second.twoPath.colorLimits).toEqual(first.twoPath.colorLimits);
  await configure(page, 'unequal'); const unequal = await simulate(page, 'unequal');
  expect(unequal.twoPath.currentResult.diagnostics.output_fractions[0]).toBeCloseTo(.75, 12);
  expect(unequal.twoPath.currentResult.diagnostics.output_fractions[1]).toBeCloseTo(.25, 12);
  await configure(page, 'lossy'); const lossy = await simulate(page, 'lossy');
  expect(lossy.twoPath.currentResult.diagnostics.total_output_ratio).toBeLessThan(.99);
  expect(lossy.twoPath.currentResult.diagnostics.propagation_delta).toBeLessThan(0);
  await record('browser_real_parameter_and_loss', { first, second, unequal, lossy });
});

test('asymmetric actual port arrays preserve common transverse axes aspect and unlit shared grayscale', async ({ page }) => {
  test.skip(smokeOnly || partialOnly || disconnectOnly); await load(page); const records = [];
  for (const label of ['asymmetric_3x4', 'asymmetric_2x5']) {
    await configure(page, label); const state = await simulate(page, label);
    await page.getByTestId('reset-view').click(); await settled(page);
    await page.getByTestId('tp-color-max').fill('1'); await page.getByTestId('tp-color-max').blur(); await settled(page);
    for (const sample of api.cases[label].samples) {
      await pick(page, sample);
      const index = sample.port === 'port_0' ? 0 : 1;
      const rgba = await page.getByTestId(`tp-intensity-${index}`).evaluate((canvas: HTMLCanvasElement, p: any) =>
        Array.from(canvas.getContext('2d')!.getImageData(p.column, p.row, 1, 1).data), sample);
      const gray = Math.round(255 * Math.min(1, sample.intensity));
      expect(rgba).toEqual([gray, gray, gray, 255]);
    }
    for (const port of [0, 1] as const) {
      await focusPort(page, port);
      const { ny, nx } = api.cases[label].experiment.grid;
      for (const [row, column] of [[0, 0], [ny - 1, nx - 1], [1, 1]]) {
        const sample = api.cases[label].samples.find((p: any) => p.port === `port_${port}` && p.row === row && p.column === column);
        const point = await pick(page, sample); const gray = Math.round(255 * Math.min(1, sample.intensity));
        const rendered = await page.getByTestId('bench-canvas').evaluate(async (canvas: HTMLCanvasElement, p: any) => {
        await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
        const gl = canvas.getContext('webgl2')!; const box = canvas.getBoundingClientRect(); const pixel = new Uint8Array(4);
        gl.readPixels(Math.floor((p.x - box.left) * canvas.width / box.width),
          canvas.height - 1 - Math.floor((p.y - box.top) * canvas.height / box.height), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixel);
        return Array.from(pixel);
        }, point);
        for (const channel of rendered.slice(0, 3)) expect(Math.abs(channel - gray)).toBeLessThanOrEqual(3);
      }
    }
    for (const detector of state.scene.dualDetectors) {
      const grid = api.cases[label].experiment.grid;
      expect(detector.width / detector.height).toBeCloseTo(grid.nx * grid.dx / (grid.ny * grid.dy), 12);
      expect(detector.texture).toMatchObject({ flipY: false, generateMipmaps: false, colorSpace: 'srgb' });
    }
    expect(state.scene.renderer.toneMapping).toBe(0);
    records.push({ label, selected: (await snap(page)).twoPath.selectedPixel, scene: (await snap(page)).scene });
  }
  await record('browser_asymmetric_actual_dual_mapping', records);
});

test('presentation controls never calculate and scientific edits detach both textures immediately', async ({ page }) => {
  test.skip(smokeOnly || partialOnly || disconnectOnly); await load(page); await configure(page, 'phase_halfpi'); await simulate(page, 'phase_halfpi');
  const before = await snap(page); const posts: string[] = [];
  page.on('request', request => { if (request.method() === 'POST') posts.push(request.url()); });
  await page.getByTestId('zoom-in').click(); await page.getByTestId('pan-left').click(); await page.getByTestId('reset-view').click();
  await page.getByTestId('tp-color-max').fill('.25'); await page.getByTestId('tp-color-max').blur();
  await page.getByTestId('tp-auto-color').click(); await page.setViewportSize({ width: 1300, height: 950 });
  await settled(page); expect(posts).toEqual([]);
  const view = await snap(page); expect(view.twoPath.currentResult.requestId).toBe(before.twoPath.currentResult.requestId);
  expect(view.twoPath.colorLimits.max).toBe(Math.max(...api.cases.phase_halfpi.intensity_max));
  await page.getByTestId('tp-edit-two_arm_spec-relative_phase_rad').fill('-');
  const stale = await snap(page); expect(stale.twoPath.currentResult).toBeNull(); expect(textureIds(stale.scene)).toEqual([null, null]);
  expect(stale.twoPath.lastResult.experiment).toEqual(api.cases.phase_halfpi.experiment);
  await expect(page.getByTestId('tp-result-status')).toContainText(/過期|stale/i);
  await page.getByTestId('tp-previous-result').locator('summary').click();
  await expect(page.getByTestId('tp-previous-result').locator('pre')).toContainText(stale.twoPath.lastResult.requestId);
  mkdirSync(figures, { recursive: true });
  await page.screenshot({ path: resolve(figures, 'fig03_stale_cross_mode.png'), fullPage: true });
  await record('browser_presentation_and_stale', { before, view, stale, posts });
});

test('rapid genuine submissions and away-back mode changes reject held cross-mode attachments', async ({ page }) => {
  test.skip(smokeOnly || partialOnly || disconnectOnly); await load(page); await configure(page, 'phase_halfpi');
  let release!: () => void; let started!: () => void; let calls = 0;
  const held = new Promise<void>(r => { release = r; }); const seen = new Promise<void>(r => { started = r; });
  await page.route('**/api/v2b/simulate', async route => {
    calls++; const actual = await route.fetch(); started(); await held; await route.fulfill({ response: actual });
  });
  await page.getByTestId('tp-simulate').evaluate((button: HTMLButtonElement) => { button.click(); button.click(); button.click(); });
  await seen; expect(calls).toBe(1);
  await page.getByTestId('mode').selectOption('sequential'); await page.getByTestId('mode').selectOption('two_path');
  release(); await expect.poll(async () => (await snap(page)).twoPath.active).toBeNull();
  const stale = await snap(page); expect(stale.twoPath.currentResult).toBeNull(); expect(textureIds(stale.scene)).toEqual([null, null]);
  expect(stale.twoPath.lastResult.experiment).toEqual(api.cases.phase_halfpi.experiment);
  expect(calls).toBe(1); await page.unroute('**/api/v2b/simulate');
  await ready(page); await simulate(page, 'phase_halfpi');
  await record('browser_held_cross_mode', { stale, calls, deliberateRecovery: (await snap(page)).twoPath.currentResult });
});

test('real dark outputs malformed error recovery signed-zero policy and passive reload', async ({ page }) => {
  test.skip(smokeOnly || partialOnly || disconnectOnly); await load(page); await configure(page, 'phase_0');
  await page.getByTestId('tp-edit-two_arm_spec-relative_phase_rad').fill('-0');
  await page.getByTestId('tp-edit-two_arm_spec-relative_phase_rad').blur(); await ready(page);
  expect(await page.evaluate(() => Object.is((window.__benchDebug.snapshot() as any).twoPath.validatedDraft.two_arm_spec.relative_phase_rad, -0))).toBe(false);
  await page.route('**/api/v2b/simulate', route => route.fulfill({ status: 200, contentType: 'application/octet-stream', body: Buffer.from('malformed') }));
  await page.getByTestId('tp-simulate').click(); await expect.poll(async () => (await snap(page)).twoPath.error).toBeTruthy();
  expect((await snap(page)).twoPath.currentResult).toBeNull(); expect(textureIds((await snap(page)).scene)).toEqual([null, null]);
  await page.unroute('**/api/v2b/simulate');
  await page.getByTestId('tp-edit-source-amplitude').fill('1e300');
  await page.getByTestId('tp-edit-source-amplitude').blur(); await ready(page);
  await page.getByTestId('tp-simulate').click();
  await expect.poll(async () => (await snap(page)).twoPath.error).toBeTruthy();
  expect((await snap(page)).twoPath.currentResult).toBeNull(); expect(textureIds((await snap(page)).scene)).toEqual([null, null]);
  await configure(page, 'dark'); const dark = await simulate(page, 'dark');
  expect(dark.twoPath.currentResult.diagnostics.output_fractions).toEqual([null, null]);
  await page.getByTestId('tp-auto-color').click(); expect((await snap(page)).twoPath.colorLimits).toEqual({ min: 0, max: 1 });
  for (const index of [0, 1]) {
    const rgba = await page.getByTestId(`tp-intensity-${index}`).evaluate((canvas: HTMLCanvasElement) =>
      Array.from(canvas.getContext('2d')!.getImageData(0, 0, 1, 1).data)); expect(rgba).toEqual([0, 0, 0, 255]);
  }
  const numerical: string[] = []; page.on('request', request => { if (request.url().endsWith('/simulate') || request.url().endsWith('/sweep')) numerical.push(request.url()); });
  await page.reload(); await expect(page.getByTestId('mode')).toHaveValue('sequential');
  expect(numerical).toEqual([]); expect((await snap(page)).twoPath.lastResult).toBeNull();
  await record('browser_dark_error_reload', { dark, numerical, reloaded: await snap(page) });
});

test('real seventeen-point sweep displays actual markers with no chart-click computation', async ({ page }) => {
  test.skip(partialOnly || disconnectOnly); await load(page); await configure(page, 'phase_0');
  let calls = 0; page.on('request', request => { if (request.url().endsWith('/sweep')) calls++; });
  const actual = await sweep(page); const expected = api.sweeps.phase_0.reply;
  expect(actual.status).toBe('complete'); expect(actual.rows).toEqual(expected.rows);
  expect(actual.requestedCount ?? actual.requested_count).toBe(17);
  expect(actual.completedCount ?? actual.completed_count).toBe(17); expect(calls).toBe(1);
  const posts: string[] = []; page.on('request', request => { if (request.method() === 'POST') posts.push(request.url()); });
  const chart = page.getByTestId('tp-sweep-chart'); await chart.click({ position: { x: 40, y: 40 } });
  expect(posts).toEqual([]);
  await expect(page.getByTestId('tp-sweep-status')).toContainText(/17/);
  if (!smokeOnly) { mkdirSync(figures, { recursive: true }); await page.screenshot({ path: resolve(figures, 'fig02_phase_sweep.png'), fullPage: true }); }
  await record(smokeOnly ? 'postcommit_real_sweep' : 'browser_real_sweep', { actual, calls, chartClickPosts: posts });
});

test('controlled partial failure retains only genuine prefix and never labels sweep complete', async ({ page }) => {
  const partial = process.env.V2B_PARTIAL_EVIDENCE;
  test.skip(!partial, 'Requires the separately task-owned controlled failure harness; production contains no test-control endpoint.');
  const expected = JSON.parse(readFileSync(resolve(root, partial!), 'utf8')).controlled_partial_failure.reply;
  await load(page); await configure(page, 'phase_0'); await page.getByTestId('tp-sweep').click();
  await expect.poll(async () => (await snap(page)).twoPath.active).toBeNull();
  const state = await snap(page); const actual = state.twoPath.lastSweep;
  expect(actual.status).toBe('failed'); expect(actual.rows).toEqual(expected.rows);
  expect(actual.completedCount ?? actual.completed_count).toBe(expected.completed_count);
  expect(actual.failedIndex ?? actual.failed_index).toBe(expected.failed_index);
  expect(state.twoPath.error).toBeTruthy();
  await expect(page.getByTestId('tp-sweep-status')).toContainText(/失敗|部分|failed|partial/i);
  await record('browser_controlled_partial_failure', { expected, actual, state,
    claim: 'Failure was deliberately controlled after genuine V2a prefix rows; this does not replace ordinary production numerical acceptance.' });
});

test('actual two-path browser disconnect holds all numerical routes until genuine worker completion', async ({ page, context }) => {
  const directory = process.env.V2B_DISCONNECT_DIR;
  test.skip(!directory, 'Requires the separate task-owned Event/Future harness; production has no test-control endpoint.');
  const owned = resolve(root, directory!); const operation = process.env.V2B_DISCONNECT_OPERATION ?? 'dual';
  await load(page); await configure(page, 'phase_0');
  await page.getByTestId(operation === 'sweep' ? 'tp-sweep' : 'tp-simulate').click();
  await expect.poll(() => { try { return JSON.parse(readFileSync(resolve(owned, 'started.json'), 'utf8')).waiting; } catch { return false; } }).toBe(true);
  const started = JSON.parse(readFileSync(resolve(owned, 'started.json'), 'utf8'));
  expect(started.operation).toBe(operation); await page.close();
  const other = await context.newPage();
  await other.route('**/*', route => new URL(route.request().url()).origin === 'http://127.0.0.1:8510'
    ? route.continue() : route.abort('blockedbyclient'));
  await load(other); await configure(other, 'phase_0');
  const actual = await other.evaluate(async ({ experiment, phases }) => {
    const legacy = { schema_version: 1, model_contract: 'v0_aligned_scalar_forward_v1',
      wavelength_m: experiment.wavelength_m, grid: experiment.grid, source: experiment.source,
      components: [], observation: { id: 'screen', z_m: 0 } };
    const envelope = { protocol_version: 1, message_type: 'two_path_submission', request_id: crypto.randomUUID(), experiment };
    const fixed = { wavelength_m: experiment.wavelength_m, grid: experiment.grid, source: experiment.source,
      arm_0_distance_m: experiment.two_arm_spec.arm_0_distance_m, arm_1_distance_m: experiment.two_arm_spec.arm_1_distance_m };
    const requests = [
      { path: '/api/v1/simulate', body: { request_id: crypto.randomUUID(), experiment: legacy } },
      { path: '/api/v2b/simulate', body: envelope },
      { path: '/api/v2b/sweep', body: { protocol_version: 1, message_type: 'two_path_sweep_submission', request_id: crypto.randomUUID(), fixed_experiment: fixed, phases_rad: phases } },
    ];
    const statuses = [];
    for (const request of requests) { const response = await fetch(request.path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request.body) });
      statuses.push({ path: request.path, status: response.status, error: await response.json() }); }
    const validation = await fetch('/api/v2b/validate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...envelope, request_id: crypto.randomUUID() }) });
    return { statuses, validationStatus: validation.status, health: await (await fetch('/api/v1/health')).json() };
  }, { experiment: api.cases.phase_0.experiment, phases: api.sweeps.phase_0.reply.phases_rad });
  expect(actual.statuses.map(r => r.status)).toEqual([409, 409, 409]); expect(actual.validationStatus).toBe(200); expect(actual.health.busy).toBe(true);
  writeFileSync(resolve(owned, 'release.flag'), 'explicit controlled release after browser disconnect', { flag: 'wx' });
  await expect.poll(() => other.evaluate(async () => (await (await fetch('/api/v1/health')).json()).busy)).toBe(false);
  const completed = JSON.parse(readFileSync(resolve(owned, 'completed.json'), 'utf8'));
  expect(completed).toMatchObject({ request_id: started.request_id, outcome: 'success', operation,
    actual_public_runner_calls: operation === 'sweep' ? 17 : 1 });
  await simulate(other, 'phase_0');
  await record(`browser_disconnect_${operation}`, { started, actual, completed, laterDirectV2aResult: (await snap(other)).twoPath.currentResult,
    claim: 'Actual client close retained the shared gate; only the original genuine numerical worker completion released it.' });
  await other.close();
});

test('context loss preserves numerical completion and repeated mode replacement ownership is bounded', async ({ page }) => {
  test.skip(smokeOnly || partialOnly || disconnectOnly); await load(page); const sequence = [];
  for (let cycle = 0; cycle < 4; cycle++) {
    await configure(page, 'phase_halfpi'); await simulate(page, 'phase_halfpi'); await simulate(page, 'phase_halfpi');
    await sweep(page); await page.getByTestId('tp-color-max').fill(String(cycle + 1)); await page.getByTestId('tp-color-max').blur();
    await page.setViewportSize({ width: cycle % 2 ? 1300 : 1440, height: 1000 }); await settled(page);
    const dual = await snap(page); expect(dual.scene.owned.textures).toBe(2);
    expect(dual.twoPath.retainedBytes).toBeLessThanOrEqual(16 * 1024 * 1024);
    await page.getByTestId('tp-edit-two_arm_spec-relative_phase_rad').fill('-');
    expect((await snap(page)).scene.owned.textures).toBe(0);
    await page.getByTestId('mode').selectOption('sequential'); await page.getByTestId('mode').selectOption('two_path');
    sequence.push({ dual: dual.scene.owned, switched: (await snap(page)).scene.owned });
  }
  expect(sequence.map(s => s.dual)).toEqual(Array(4).fill(sequence[0].dual));
  expect(sequence.map(s => s.switched)).toEqual(Array(4).fill(sequence[0].switched));
  await configure(page, 'phase_halfpi'); await simulate(page, 'phase_halfpi');
  let calls = 0; page.on('request', request => { if (request.url().endsWith('/simulate') || request.url().endsWith('/sweep')) calls++; });
  await page.getByTestId('bench-canvas').evaluate((canvas: HTMLCanvasElement) => {
    const extension = canvas.getContext('webgl2')!.getExtension('WEBGL_lose_context');
    if (!extension) throw new Error('Required controlled context-loss extension unavailable'); extension.loseContext();
  });
  await expect(page.getByTestId('tp-render-error')).toBeVisible();
  const loss = await snap(page); expect(loss.twoPath.completedNumerical).not.toBeNull(); expect(calls).toBe(0);
  await record('browser_dual_resources_and_context_loss', { sequence, loss, calls });
});
