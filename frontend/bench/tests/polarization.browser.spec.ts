/** Genuine served-production Jones acceptance; explicit controlled fixtures are separate. */
import { test, expect, type Page } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve('../..');
const evidence = resolve(root, process.env.V2D_EVIDENCE_DIR ?? 'runs/v2d_acceptance/browser');
const api = JSON.parse(readFileSync(resolve(root, process.env.V2D_API_EVIDENCE ?? 'runs/v2d_acceptance/api_evidence.json'), 'utf8'));
const figures = resolve(root, process.env.V2D_FIGURE_DIR ?? 'docs/handoffs/v2d/figures');
const smokeOnly = process.env.V2D_SMOKE === '1';
const partialOnly = process.env.V2D_PARTIAL_ONLY === '1';
const disconnectOnly = process.env.V2D_DISCONNECT_ONLY === '1';
const ordinary = () => !partialOnly && !disconnectOnly;
const snap = (page: Page): Promise<any> => page.evaluate(() => window.__benchDebug.snapshot());
const pl = async (page: Page): Promise<any> => (await snap(page)).polarization;

async function record(name: string, value: unknown): Promise<void> {
  mkdirSync(evidence, { recursive: true });
  writeFileSync(resolve(evidence, `${name}.json`), JSON.stringify(value, null, 2), { flag: 'wx' });
}
async function frames(page: Page, count = 8): Promise<void> {
  await page.evaluate(count => new Promise<void>(resolve => {
    let n = 0; const next = () => ++n < count ? requestAnimationFrame(next) : resolve(); requestAnimationFrame(next);
  }), count);
}
async function ready(page: Page): Promise<void> {
  await expect.poll(async () => { const state = await pl(page); return !state.pendingValidation && !!state.validatedDraft && !state.active; }).toBe(true);
  await expect(page.getByTestId('pl-simulate')).toBeEnabled();
}
async function load(page: Page): Promise<void> {
  await page.goto('/');
  expect((await snap(page)).mode).toBe('sequential');
  await page.getByTestId('mode').selectOption('polarization'); await ready(page);
}
async function edit(page: Page, path: string, value: string): Promise<void> {
  const field = page.getByTestId(`pl-edit-${path.replaceAll('.', '-')}`);
  await field.fill(value); await field.blur();
  await expect.poll(async () => (await pl(page)).pendingValidation).toBe(false);
}
async function configure(page: Page, label: string): Promise<void> {
  const fixture = api.cases[label]; if (!fixture) throw new Error(`Independent actual API fixture absent: ${label}`);
  await page.getByTestId('pl-preset').selectOption(fixture.preset); await ready(page);
  if (fixture.reorder) {
    await page.getByTestId(`pl-select-${fixture.reorder[0]}`).click();
    await page.getByTestId(`pl-${fixture.reorder[1]}`).click(); await ready(page);
  }
  await page.getByTestId('pl-source-kind').selectOption(fixture.experiment.source.kind);
  await expect.poll(async () => (await pl(page)).pendingValidation).toBe(false);
  // Make the selection legal before reducing dimensions; no implicit clamping.
  await edit(page, 'readout.row', '0'); await edit(page, 'readout.column', '0');
  for (const [path, text] of Object.entries(fixture.editor_inputs)) {
    if (path.startsWith('elements.')) {
      const index = Number(path.split('.')[1]), id = fixture.experiment.elements[index].id;
      await page.getByTestId(`pl-select-${id}`).click();
    }
    await edit(page, path, text as string);
  }
  await ready(page);
  expect((await pl(page)).validatedDraft).toEqual(fixture.experiment);
  const selected = fixture.experiment.elements.find((element: any) => element.kind === 'linear_polarizer') ?? fixture.experiment.elements[0];
  if (selected) await page.getByTestId(`pl-select-${selected.id}`).click();
}
async function simulate(page: Page, label?: string): Promise<any> {
  const prior = (await pl(page)).currentResult?.requestId;
  await page.getByTestId('pl-simulate').click();
  await expect.poll(async () => { const state = await pl(page); return !state.active && !!state.currentResult && state.currentResult.requestId !== prior; }).toBe(true);
  const state = await pl(page);
  if (label) {
    const expected = api.cases[label];
    expect(state.currentResult.experiment).toEqual(expected.experiment);
    expect(state.currentResult.stages).toEqual(expected.stages);
    expect(state.currentResult.readout).toEqual(expected.readout);
    expect(state.currentResult.intensityMax).toEqual(expected.intensity_max);
    expect(state.currentResult.orderedStageIds).toEqual(expected.ordered_stage_ids);
  }
  return state;
}
async function runSweep(page: Page): Promise<any> {
  const prior = (await pl(page)).lastSweep?.requestId;
  await page.getByTestId('pl-sweep').click();
  await expect.poll(async () => { const state = await pl(page); return !state.active && !!state.lastSweep && state.lastSweep.requestId !== prior; }).toBe(true);
  return (await pl(page)).lastSweep;
}
function scientificRequests(page: Page): string[] {
  const requests: string[] = [];
  page.on('request', request => { if (request.method() === 'POST' && /\/api\/.*\/(validate|simulate|sweep)$/.test(new URL(request.url()).pathname)) requests.push(new URL(request.url()).pathname); });
  return requests;
}
async function screenshot(page: Page, file: string): Promise<void> {
  mkdirSync(figures, { recursive: true }); await page.screenshot({ path: resolve(figures, file), fullPage: true });
}
function rawMarker(state: any, id: string): { x: number; y: number } {
  const rows = state.trajectories?.stages ?? state.trajectories;
  const row = Array.isArray(rows) ? rows.find((item: any) => (item.stageId ?? item.stage_id) === id) : rows?.[id];
  if (!row?.rawMarker) throw new Error(`Actual fixed-tau marker missing for ${id}`);
  return row.rawMarker;
}

test.beforeEach(async ({ page }) => {
  await page.route('**/*', route => new URL(route.request().url()).origin === 'http://127.0.0.1:8510' ? route.continue() : route.abort('blockedbyclient'));
});

test('genuine QWP HWP and common phase retain actual complex samples at shared fixed tau', async ({ page, browser }) => {
  test.skip(!ordinary()); const posts = scientificRequests(page); await load(page);
  expect(posts.filter(path => /\/(simulate|sweep)$/.test(path))).toEqual([]);
  const records = [];
  for (const label of smokeOnly ? ['qwp'] : ['qwp', 'qwp_shifted', 'hwp', 'complex_coefficients']) {
    await configure(page, label); const state = await simulate(page, label);
    await page.getByTestId('pl-reset').click(); await frames(page);
    const actual = await pl(page); const sample = state.currentResult.stages.at(-1).sample;
    expect(sample).toEqual(api.cases[label].stages.at(-1).sample);
    if (label === 'qwp' || label === 'qwp_shifted') {
      const marker = rawMarker(actual, 'w1'), expected = api.cases[label].fixed_tau0_expected;
      expect(Math.abs(marker.x - expected[0])).toBeLessThanOrEqual(2e-15);
      expect(Math.abs(marker.y - expected[1])).toBeLessThanOrEqual(2e-15);
      expect(state.currentResult.intensityMax[0]).toBeCloseTo(state.currentResult.intensityMax[1], 13);
    }
    expect(state.currentResult.stages[0].sample).not.toEqual(state.currentResult.stages.at(-1).sample);
    records.push({ label, state: actual });
    if (label === 'qwp' && !smokeOnly) { await page.getByTestId('pl-stage').selectOption('w1'); await screenshot(page, 'fig01_complex_transformation.png'); }
  }
  await record(smokeOnly ? 'postcommit_polarization_complex_smoke' : 'browser_genuine_complex_and_common_phase',
    { browserVersion: browser.version(), records, requests: posts, fixedTauAtol: 2e-15,
      claim: 'Actual public V2c HTTP samples and independently evaluated phase-sensitive markers; equal intensity alone is insufficient.' });
});

test('real order coefficients source and element editing preserve loss and explicit original identity', async ({ page }) => {
  test.skip(!ordinary() || smokeOnly); await load(page); const records = [];
  for (const label of ['crossed', 'middle', 'middle_reordered', 'arbitrary', 'gaussian']) {
    await configure(page, label); const state = await simulate(page, label); records.push({ label, state });
  }
  expect(records[1].state.currentResult.stages.at(-1).incident_transmission_ratio).toBeCloseTo(.25, 13);
  expect(records[0].state.currentResult.stages.at(-1).incident_transmission_ratio).toBeLessThan(1e-30);
  expect(records[2].state.currentResult.stages.at(-1).incident_transmission_ratio).toBeLessThan(1e-30);
  expect(records[3].state.currentResult.stages.at(-1).incident_transmission_ratio).toBeCloseTo(.5, 13);
  await configure(page, 'middle'); await simulate(page, 'middle');
  const requests = scientificRequests(page), before = await pl(page);
  await page.getByTestId('pl-select-pm').click(); await page.getByTestId('pl-stage').selectOption('pm');
  expect(requests).toEqual([]); expect((await pl(page)).currentResult.requestId).toBe(before.currentResult.requestId);
  await edit(page, 'elements.1.axis_angle_rad', '.42'); await ready(page);
  const stale = await pl(page); expect(stale.currentResult).toBeNull(); expect(stale.lastResult.experiment).toEqual(api.cases.middle.experiment);
  await expect(page.getByTestId('pl-result-status')).toContainText(/原|先前|previous|original|stale/i);
  await page.getByTestId('pl-previous-result').locator('summary').click();
  await expect(page.getByTestId('pl-previous-result').locator('pre')).toContainText(stale.lastResult.requestId);
  await expect(page.getByTestId('pl-previous-result').locator('pre')).toContainText('incident_transmission_ratio');
  // A normal scroll exposes the retained original stage losses in the capture.
  await page.getByTestId('pl-previous-result').locator('pre').evaluate(node => { node.scrollTop = node.scrollHeight; });
  await screenshot(page, 'fig03_order_loss_stale.png');
  await page.getByTestId('pl-add-kind').selectOption('linear_retarder'); await page.getByTestId('pl-add').click(); await ready(page);
  let state = await pl(page); const added = state.candidate.elements.at(-1);
  await page.getByTestId('pl-qwp').click(); await ready(page); expect((await pl(page)).candidate.elements.at(-1).retardance_rad).toBe(Math.PI / 2);
  await page.getByTestId('pl-hwp').click(); await ready(page); expect((await pl(page)).candidate.elements.at(-1).retardance_rad).toBe(Math.PI);
  await page.getByTestId('pl-delete').click(); await ready(page); state = await pl(page);
  expect(state.candidate.elements.some((element: any) => element.id === added.id)).toBe(false);
  expect(state.candidate.elements.map((element: any) => element.id)).toEqual(['p1', 'pm', 'p2']);
  expect(await page.locator('[data-testid^="pl-edit-"][data-testid*="z_m"]').count()).toBe(0);
  await record('browser_order_loss_and_actual_editors', { records, stale, afterAddDelete: state, viewRequests: requests });
});

test('genuine thirteen-point full-train sweep has passive inspection and one explicit apply simulation', async ({ page }) => {
  test.skip(!ordinary()); await load(page); await configure(page, 'analyzer'); const posts = scientificRequests(page);
  const actual = await runSweep(page), expected = api.sweeps.analyzer.reply;
  expect(actual.rows).toEqual(expected.rows); expect(actual.anglesRad).toEqual(expected.angles_rad);
  expect(actual.requestedCount).toBe(13); expect(actual.completedCount).toBe(13); expect(actual.status).toBe('complete');
  expect(posts.filter(path => path.endsWith('/sweep'))).toHaveLength(1);
  const beforeSelection = posts.length;
  await page.getByTestId('pl-sweep-point-4').click(); await frames(page);
  expect(posts).toHaveLength(beforeSelection);
  await page.getByTestId('pl-apply-angle').click();
  await expect.poll(async () => { const state = await pl(page); return !state.active && !!state.currentResult; }).toBe(true);
  const final = await pl(page);
  expect(final.currentResult.experiment.elements[0].axis_angle_rad).toBe(expected.angles_rad[4]);
  expect(posts.filter(path => path.endsWith('/simulate'))).toHaveLength(1);
  if (!smokeOnly) await screenshot(page, 'fig02_angle_sweep.png');
  await record(smokeOnly ? 'postcommit_polarization_genuine_sweep' : 'browser_genuine_thirteen_point_sweep', { actual, final, requests: posts });
});

test('actual asymmetric float64 intensity picking does not relabel the submitted complex sample', async ({ page }) => {
  test.skip(!ordinary() || smokeOnly); await load(page); await configure(page, 'asymmetric'); await simulate(page, 'asymmetric');
  const before = await pl(page), requests = scientificRequests(page);
  const canvas = page.getByTestId('pl-intensity-1'), box = (await canvas.boundingBox())!;
  await canvas.click({ position: { x: box.width * .125, y: box.height / 6 } });
  const picked = await pl(page);
  const selected = api.cases.asymmetric.samples.find((sample: any) => sample.view === 1 && sample.row === 0 && sample.column === 0);
  expect(picked.selectedPixel).toMatchObject(selected);
  expect(picked.currentResult.readout).toEqual(before.currentResult.readout);
  expect(picked.currentResult.stages).toEqual(before.currentResult.stages);
  for (const view of [0, 1]) {
    const sample = api.cases.asymmetric.samples.find((sample: any) => sample.view === view && sample.row === 0 && sample.column === 0);
    const rgba = await page.getByTestId(`pl-intensity-${view}`).evaluate((canvas: HTMLCanvasElement) => Array.from(canvas.getContext('2d')!.getImageData(0, 0, 1, 1).data));
    const gray = Math.round(255 * Math.min(1, sample.intensity / 10)); expect(rgba).toEqual([gray, gray, gray, 255]);
  }
  await expect(page.getByTestId('pl-sample')).toContainText(/1/);
  expect(requests).toEqual([]);
  await edit(page, 'readout.row', '0'); await edit(page, 'readout.column', '0'); await ready(page);
  expect((await pl(page)).currentResult).toBeNull();
  const fresh = await simulate(page);
  expect(fresh.currentResult.readout).toMatchObject({ row: 0, column: 0 });
  expect(fresh.currentResult.stages.at(-1).sample).not.toEqual(before.currentResult.stages.at(-1).sample);
  expect(requests.filter(path => path.endsWith('/simulate'))).toHaveLength(1);
  await record('browser_fixed_sample_and_raw_intensity', { before, picked, fresh, requests });
});

test('dark and selected weak public samples remain distinct and display actions send no scientific requests', async ({ page }) => {
  test.skip(!ordinary() || smokeOnly); await load(page); const records = [];
  for (const label of ['dark', 'both_zero', 'dark_sample', 'weak_pi2']) {
    await configure(page, label); await simulate(page, label);
    await page.getByTestId('pl-stage').selectOption(api.cases[label].ordered_stage_ids.at(-1));
    const state = await pl(page); records.push({ label, state });
    const sample = state.currentResult.stages.at(-1).sample;
    const dark = [sample.x.re, sample.x.im, sample.y.re, sample.y.im].every(value => value === 0);
    expect(dark).toBe(label !== 'weak_pi2');
    if (dark) await expect(page.getByTestId('pl-stage-note')).toContainText(/未定義|no defined/i);
    else { expect(sample.y.re).not.toBe(0); await expect(page.getByTestId('pl-stage-note')).not.toContainText(/no defined polarization state/i); }
  }
  const requests = scientificRequests(page), original = (await pl(page)).currentResult;
  await page.getByTestId('pl-display-gain').fill('1000000'); await page.getByTestId('pl-display-gain').blur();
  await page.getByTestId('pl-tau').fill(String(Math.PI / 2)); await page.getByTestId('pl-tau').blur();
  const startTau = (await pl(page)).animation.tau;
  await page.getByTestId('pl-play').click(); await frames(page, 20); await page.getByTestId('pl-play').click();
  const paused = (await pl(page)).animation; expect(paused.playing).toBe(false); expect(paused.tau).not.toBe(startTau);
  await frames(page); expect((await pl(page)).animation.ticks).toBe(paused.ticks);
  await page.getByTestId('pl-reset').click(); await page.getByTestId('reset-view').click(); await page.getByTestId('zoom-in').click();
  expect((await pl(page)).animation).toMatchObject({ tau: 0, playing: false });
  await page.getByTestId('pl-stage').selectOption('input');
  await page.getByTestId('pl-color-max').fill('2'); await page.getByTestId('pl-color-max').blur(); await frames(page);
  expect(requests).toEqual([]); const viewed = await pl(page);
  expect(viewed.currentResult).toEqual(original);
  await record('browser_dark_weak_and_passive_animation', { records, viewed, requests,
    claim: 'Genuine finite weak data and explicit presentation magnification; no arbitrary weak-visibility claim.' });
});

test('controlled nonzero tiny sample with zero squared intensity is not exact darkness', async ({ page }) => {
  test.skip(!ordinary() || smokeOnly); await load(page); await configure(page, 'identity');
  await page.route('**/api/v2d/simulate', async route => {
    const response = await route.fetch(), original = await response.body();
    const length = original.readUInt32LE(8), header = JSON.parse(original.subarray(16, 16 + length).toString('utf8'));
    const payloadStart = 16 + Math.ceil(length / 8) * 8, payload = Buffer.from(original.subarray(payloadStart));
    header.stages[0].sample = { x: { re: 1e-200, im: 0 }, y: { re: 0, im: 0 } };
    const { ny, nx } = header.experiment.grid, { row, column } = header.readout;
    for (const offset of [0, ny * nx * 8]) payload.writeDoubleLE(0, offset + (row * nx + column) * 8);
    const text = Buffer.from(JSON.stringify(header)), start = 16 + Math.ceil(text.length / 8) * 8;
    const frame = Buffer.alloc(start + payload.length); original.copy(frame, 0, 0, 8); frame.writeUInt32LE(text.length, 8); text.copy(frame, 16); payload.copy(frame, start);
    await route.fulfill({ status: 200, contentType: 'application/octet-stream', body: frame });
  });
  await simulate(page); const state = await pl(page);
  expect(state.currentResult.stages[0].sample.x.re).toBe(1e-200);
  const rows = state.trajectories?.stages ?? state.trajectories, trajectory = Array.isArray(rows) ? rows[0] : rows.input;
  expect(trajectory.dark).toBe(false);
  await expect(page.getByTestId('pl-sample')).toContainText('1e-200');
  await expect(page.getByTestId('pl-stage-note')).not.toContainText(/no defined polarization state/i);
  await record('browser_controlled_tiny_underflow_sample', { state,
    claim: 'Supplemental bounded transport/presentation fixture: selected nonzero complex component, selected intensity zero, usable rest-of-field norm. Not a new production source or genuine solver result.' });
});

test('invalid text numerical failure malformed reply and signed zero require deliberate recovery', async ({ page }) => {
  test.skip(!ordinary() || smokeOnly); await load(page); await configure(page, 'analyzer'); await simulate(page, 'analyzer');
  await edit(page, 'elements.0.axis_angle_rad', '-'); expect((await pl(page)).currentResult).toBeNull();
  await expect(page.getByTestId('pl-simulate')).toBeDisabled();
  await edit(page, 'elements.0.axis_angle_rad', '-0'); await ready(page);
  expect(await page.evaluate(() => Object.is((window.__benchDebug.snapshot() as any).polarization.validatedDraft.elements[0].axis_angle_rad, -0))).toBe(false);
  await edit(page, 'elements.0.axis_angle_rad', '-17.123456789012344'); await ready(page);
  expect((await pl(page)).validatedDraft.elements[0].axis_angle_rad).toBe(-17.123456789012344);
  await edit(page, 'source.amplitude', '1e300'); await ready(page); const requests = scientificRequests(page);
  await page.getByTestId('pl-simulate').click(); await expect.poll(async () => (await pl(page)).active).toBeNull();
  await expect(page.getByTestId('pl-error')).toBeVisible(); const numericalFailure = await pl(page);
  expect(requests.filter(path => path.endsWith('/simulate'))).toHaveLength(1);
  await configure(page, 'analyzer');
  await page.route('**/api/v2d/simulate', async route => { const response = await route.fetch(); const bytes = await response.body(); bytes[0] = 0; await route.fulfill({ status: 200, contentType: 'application/octet-stream', body: bytes }); }, { times: 1 });
  await page.getByTestId('pl-simulate').click(); await expect.poll(async () => (await pl(page)).active).toBeNull();
  const malformed = await pl(page); expect(malformed.currentResult).toBeNull(); expect(malformed.error).toBeTruthy();
  const recovered = await simulate(page, 'analyzer');
  await record('browser_invalid_numerical_malformed_recovery', { numericalFailure, malformed, recovered, requests });
});

test('rapid clicks and away-and-back across all modes reject an actual held late result', async ({ page }) => {
  test.skip(!ordinary() || smokeOnly); await load(page); await configure(page, 'qwp');
  let release!: () => void; const held = new Promise<void>(resolve => { release = resolve; }); let received = false;
  await page.route('**/api/v2d/simulate', async route => { const response = await route.fetch(); received = true; await held; await route.fulfill({ response }); }, { times: 1 });
  const requests = scientificRequests(page);
  await page.getByTestId('pl-simulate').evaluate((button: HTMLButtonElement) => { button.click(); button.click(); });
  await expect.poll(() => received).toBe(true); const pending = await pl(page); expect(pending.active).toBeTruthy();
  await page.getByTestId('mode').selectOption('sequential'); await page.getByTestId('mode').selectOption('two_path');
  await page.getByTestId('mode').selectOption('polarization'); release();
  await expect.poll(async () => (await pl(page)).active).toBeNull(); await ready(page);
  const stale = await pl(page); expect(stale.currentResult).toBeNull();
  expect(requests.filter(path => path.endsWith('/simulate'))).toEqual(['/api/v2d/simulate']);
  const recovered = await simulate(page, 'qwp');
  await record('browser_rapid_click_cross_mode_staleness', { pending, stale, recovered, requests });
});

test('later presentation failure keeps numerical completion and original result without automatic resubmission', async ({ page }) => {
  test.skip(!ordinary() || smokeOnly); await load(page); await configure(page, 'qwp'); await simulate(page, 'qwp');
  const before = await pl(page), beforeScene = (await snap(page)).scene, requests = scientificRequests(page);
  const installFault = () => page.evaluate(() => {
    const prototype = HTMLCanvasElement.prototype as any, original = prototype.getContext;
    const NativeFloat64Array = globalThis.Float64Array; let calls = 0;
    prototype.getContext = function(kind: string, ...args: unknown[]) {
      if (kind === '2d') ++calls;
      return original.call(this, kind, ...args);
    };
    globalThis.Float64Array = new Proxy(NativeFloat64Array, { construct(target, args) {
      if (calls >= 2 && args[0] === 257 * 2) {
        prototype.getContext = original; globalThis.Float64Array = NativeFloat64Array;
        throw new Error('Controlled later trajectory preparation failure after both intensity canvases');
      }
      return Reflect.construct(target, args);
    } });
    (window as any).__restoreV2dCanvas = () => { prototype.getContext = original; globalThis.Float64Array = NativeFloat64Array; };
  });
  await installFault();
  await page.getByTestId('pl-simulate').click(); await expect.poll(async () => (await pl(page)).active).toBeNull();
  await page.evaluate(() => (window as any).__restoreV2dCanvas());
  const failed = await pl(page); expect(failed.renderError).toBeTruthy();
  expect(failed.completedNumerical.requestId).not.toBe(before.currentResult.requestId);
  expect(failed.currentResult.requestId).toBe(before.currentResult.requestId);
  const failedScene = (await snap(page)).scene; expect(failedScene.owned).toEqual(beforeScene.owned);
  expect(failedScene.polarization.textureRequestIds).toEqual([before.currentResult.requestId, before.currentResult.requestId]);
  expect(requests.filter(path => path.endsWith('/simulate'))).toHaveLength(1);
  await expect(page.getByTestId('pl-render-error')).toBeVisible();
  await page.getByTestId('pl-retry-display').click();
  await expect.poll(async () => (await pl(page)).currentResult?.requestId).toBe(failed.completedNumerical.requestId);
  const numericalRecovered = await pl(page); expect(numericalRecovered.renderError).toBeNull();
  expect(requests).toEqual(['/api/v2d/simulate']);
  const svgState = () => page.getByTestId('pl-trajectories').locator('svg[data-stage-id="w1"]').evaluate(svg => {
    const marker = svg.querySelector('[data-marker="w1"]')!;
    return { cx: marker.getAttribute('cx'), cy: marker.getAttribute('cy'), points: svg.querySelector('polyline')?.getAttribute('points') };
  });
  const beforeGain = await pl(page), beforeSVG = await svgState(), beforeGainScene = (await snap(page)).scene;
  expect(beforeGain.trajectories.map((row: any) => row.gain)).toEqual([1, 1]);
  await installFault(); await page.getByTestId('pl-display-gain').fill('2'); await page.getByTestId('pl-display-gain').blur();
  await expect(page.getByTestId('pl-render-error')).toBeVisible();
  await page.evaluate(() => (window as any).__restoreV2dCanvas()); await frames(page);
  const displayFailed = await pl(page), failedSVG = await svgState(), displayFailedScene = (await snap(page)).scene;
  expect(displayFailed.requestedDisplay.gain).toBe(2); expect(displayFailed.renderError).toBeTruthy();
  expect(displayFailed.currentResult).toEqual(beforeGain.currentResult); expect(displayFailed.trajectories).toEqual(beforeGain.trajectories);
  expect(failedSVG).toEqual(beforeSVG); expect(displayFailedScene.owned).toEqual(beforeGainScene.owned);
  expect(requests).toEqual(['/api/v2d/simulate']);
  await page.getByTestId('pl-retry-display').click();
  await expect.poll(async () => (await pl(page)).renderError).toBeNull();
  const recovered = await pl(page), recoveredSVG = await svgState();
  expect(recovered.currentResult.requestId).toBe(beforeGain.currentResult.requestId);
  expect(recovered.trajectories.map((row: any) => row.gain)).toEqual([2, 2]);
  expect(Number(recoveredSVG.cx)).toBeCloseTo(2 * Number(beforeSVG.cx), 13);
  expect(Number(recoveredSVG.cy)).toBeCloseTo(2 * Number(beforeSVG.cy), 13);
  expect(recoveredSVG.points).not.toEqual(beforeSVG.points); expect(requests).toEqual(['/api/v2d/simulate']);
  await record('browser_controlled_late_resource_rollback', { before, beforeScene, failed, failedScene, numericalRecovered,
    beforeGain, beforeSVG, beforeGainScene, displayFailed, failedSVG, displayFailedScene, recovered, recoveredSVG, requests,
    claim: 'Browser-only later resource faults preserve original numerical identity and effective SVG settings; explicit display retry reuses genuine numerics and sends no scientific request.' });
});

test('repeated play pause replacement mode switches and actual context loss preserve bounded owners', async ({ page }) => {
  test.skip(!ordinary() || smokeOnly); await load(page); const observations = [];
  for (let cycle = 0; cycle < 3; cycle++) {
    await configure(page, 'qwp'); await simulate(page, 'qwp'); const requests = scientificRequests(page);
    for (let repeat = 0; repeat < 3; repeat++) { await page.getByTestId('pl-play').click(); await frames(page); await page.getByTestId('pl-play').click(); }
    await page.getByTestId('pl-reset').click(); const active = await pl(page), activeScene = (await snap(page)).scene;
    expect(active.animation.activeOwners).toBeLessThanOrEqual(1);
    expect(activeScene.polarization.frameCallbacks).toBe(1); expect(activeScene.owned.textures).toBe(2);
    expect(active.budget.retainedBytes).toBe(active.budget.scientificBytes + active.budget.canvasBytes + active.budget.textureBytes + active.budget.trajectoryBytes + active.budget.geometryBytes);
    expect(active.budget.retainedBytes).toBeLessThanOrEqual(16 * 1024 * 1024);
    expect(active.budget.persistent).toBe(16 * 1024 * 1024); expect(active.budget.transient).toBe(32 * 1024 * 1024);
    if (active.budget.transientEstimate) expect(active.budget.transientEstimate.peakOwnedBytes).toBeLessThanOrEqual(active.budget.transient);
    await page.getByTestId('mode').selectOption('sequential'); await frames(page, 12);
    const detached = await pl(page), detachedScene = (await snap(page)).scene;
    expect(detached.animation.activeOwners).toBe(0); expect(detachedScene.polarization.frameCallbacks).toBe(0); const ticks = detached.animation.ticks;
    await frames(page, 12); expect((await pl(page)).animation.ticks).toBe(ticks);
    await page.getByTestId('mode').selectOption('two_path'); await page.getByTestId('mode').selectOption('polarization'); await ready(page);
    expect(requests.filter(path => /\/(simulate|sweep)$/.test(path))).toEqual([]);
    observations.push({ active, activeScene, detached, detachedScene });
  }
  expect(observations.map(row => row.activeScene.owned)).toEqual(Array(3).fill(observations[0].activeScene.owned));
  expect(observations.map(row => row.detachedScene.owned)).toEqual(Array(3).fill(observations[0].detachedScene.owned));
  await configure(page, 'qwp'); await simulate(page, 'qwp'); const requests = scientificRequests(page);
  await page.getByTestId('bench-canvas').evaluate((canvas: HTMLCanvasElement) => {
    const extension = canvas.getContext('webgl2')!.getExtension('WEBGL_lose_context');
    if (!extension) throw new Error('Required actual WebGL context-loss extension unavailable'); extension.loseContext();
  });
  await expect(page.getByTestId('pl-render-error')).toBeVisible(); const loss = await pl(page);
  expect(loss.completedNumerical).not.toBeNull(); expect(loss.animation.activeOwners).toBe(0); expect(requests).toEqual([]);
  await page.reload(); expect((await snap(page)).mode).toBe('sequential');
  await page.getByTestId('mode').selectOption('polarization'); await ready(page); expect((await pl(page)).currentResult).toBeNull();
  await record('browser_actual_resources_animation_and_context_loss', { observations, loss, requests });
});

test('controlled actual failed sweep keeps only genuine contiguous rows', async ({ page }) => {
  const partial = process.env.V2D_PARTIAL_EVIDENCE;
  test.skip(!partial, 'Requires separately task-owned controlled child; ordinary production contains no fault endpoint.');
  const expected = JSON.parse(readFileSync(resolve(root, partial!), 'utf8')).controlled_partial_failure.reply;
  await load(page); await configure(page, 'analyzer'); const requests = scientificRequests(page), actual = await runSweep(page);
  expect(actual.status).toBe('failed'); expect(actual.rows).toEqual(expected.rows); expect(actual.completedCount).toBe(expected.completed_count);
  expect(actual.failedIndex).toBe(expected.failed_index); expect(actual.error).toEqual(expected.error);
  expect(actual.rows.map((row: any) => row.index)).toEqual(Array.from({ length: expected.completed_count }, (_, index) => index));
  await expect(page.getByTestId('pl-sweep-status')).toContainText(/失敗|部分|failed|partial/i);
  expect(requests.filter(path => path.endsWith('/sweep'))).toHaveLength(1);
  await record(`browser_controlled_partial_${expected.failed_index}_${expected.error.code}`, { expected, actual, requests,
    claim: 'Controlled child failure after actual public V2c prefix computations; separate from unmodified production acceptance.' });
});

test('actual polarization browser disconnect holds all five operations until genuine worker completion', async ({ page, context }) => {
  const directory = process.env.V2D_DISCONNECT_DIR;
  test.skip(!directory, 'Requires separate task-owned controlled worker child; production has no release endpoint.');
  const owned = resolve(root, directory!), operation = process.env.V2D_DISCONNECT_OPERATION ?? 'polarization';
  await load(page); await configure(page, 'analyzer');
  await page.getByTestId(operation === 'polarization_sweep' ? 'pl-sweep' : 'pl-simulate').click();
  await expect.poll(() => { try { return JSON.parse(readFileSync(resolve(owned, 'started.json'), 'utf8')).waiting; } catch { return false; } }).toBe(true);
  const started = JSON.parse(readFileSync(resolve(owned, 'started.json'), 'utf8')); expect(started.operation).toBe(operation);
  await page.close(); const other = await context.newPage(); await load(other); await configure(other, 'analyzer');
  const rejected = await other.evaluate(async ({ experiment, digest, angles }) => {
    const request = { protocol_version: 1, message_type: 'polarization_submission', request_id: crypto.randomUUID(), experiment, experiment_sha256: digest };
    const source = { kind: 'uniform', amplitude: 1, phase_rad: 0 };
    const legacy = { schema_version: 1, model_contract: 'v0_aligned_scalar_forward_v1', wavelength_m: 633e-9,
      grid: { ny: 3, nx: 4, dy: 4e-6, dx: 4e-6 }, source, components: [], observation: { id: 'screen', z_m: 0 } };
    const dual = { wavelength_m: 633e-9, grid: legacy.grid, source, two_arm_spec: { arm_0_distance_m: .002, arm_1_distance_m: .002, relative_phase_rad: 0 } };
    const fixed = { wavelength_m: dual.wavelength_m, grid: dual.grid, source, arm_0_distance_m: .002, arm_1_distance_m: .002 };
    const operations = [
      ['/api/v1/simulate', { request_id: crypto.randomUUID(), experiment: legacy }],
      ['/api/v2b/simulate', { protocol_version: 1, message_type: 'two_path_submission', request_id: crypto.randomUUID(), experiment: dual }],
      ['/api/v2b/sweep', { protocol_version: 1, message_type: 'two_path_sweep_submission', request_id: crypto.randomUUID(), fixed_experiment: fixed, phases_rad: Array.from({ length: 17 }, (_, i) => i * (2 * Math.PI / 16)) }],
      ['/api/v2d/simulate', request], ['/api/v2d/sweep', { ...request, message_type: 'polarization_sweep_submission', selected_element_id: 'p1', angles_rad: angles }],
    ];
    const statuses = [];
    for (const [path, body] of operations) { const response = await fetch(path as string, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); statuses.push({ path, status: response.status, error: await response.json() }); }
    const validation = await fetch('/api/v2d/validate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request) });
    return { statuses, validationStatus: validation.status, health: await (await fetch('/api/v1/health')).json() };
  }, { experiment: api.cases.analyzer.experiment, digest: api.cases.analyzer.experiment_sha256, angles: api.sweeps.analyzer.reply.angles_rad });
  expect(rejected.statuses.map((row: any) => row.status)).toEqual([409, 409, 409, 409, 409]);
  expect(rejected.validationStatus).toBe(200); expect(rejected.health.busy).toBe(true);
  writeFileSync(resolve(owned, 'release.flag'), 'explicit release after actual browser disconnect', { flag: 'wx' });
  await expect.poll(() => other.evaluate(async () => (await (await fetch('/api/v1/health')).json()).busy)).toBe(false);
  const completed = JSON.parse(readFileSync(resolve(owned, 'completed.json'), 'utf8'));
  expect(completed).toMatchObject({ request_id: started.request_id, operation, outcome: 'success', actual_public_element_calls: operation === 'polarization_sweep' ? 13 : 1 });
  const recovered = await simulate(other, 'analyzer');
  await record(`browser_actual_disconnect_${operation}`, { started, rejected, completed, recovered }); await other.close();
});
