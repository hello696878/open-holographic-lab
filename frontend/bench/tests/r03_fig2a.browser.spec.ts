/** Genuine production A acceptance; controlled presentation/HTTP faults are labelled separately. */
import { test, expect, type Page, type Route } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { R03_IDENTITY } from '../src/r03_fig2a_contracts';
const root = resolve('../..');
const evidence = resolve(root, process.env.R03_EVIDENCE_DIR ?? 'runs/research_workspace_ux_v1_01/browser/ideal');
const figures = resolve(root, process.env.R03_FIGURE_DIR ?? resolve(evidence, 'figures'));
const smoke = process.env.R03_SMOKE === '1';
test.use({ viewport: { width: 1760, height: 1100 }, video: { mode: 'on', size: { width: 1280, height: 800 } } });
function save(name: string, value: unknown): void { mkdirSync(evidence, { recursive: true }); writeFileSync(resolve(evidence, `${name}.json`), JSON.stringify(value, null, 2), { flag: 'wx' }); }
const snapshot = (page: Page): Promise<any> => page.evaluate(() => window.__benchDebug.snapshot());
const ideal = async (page: Page): Promise<any> => (await snapshot(page)).idealPolarization;
const computing = (path: string) => /\/api\/(?:v1|v2b|v2d|v2g)\/(?:simulate|sweep)$/.test(path) || path === '/api/research/r03-fig2a/simulate';
async function ready(page: Page): Promise<void> { await expect.poll(async () => { const state = await ideal(page); return !!state.validatedDraft && !state.pendingValidation && !state.active; }).toBe(true); await expect(page.getByTestId('r03-compute')).toBeEnabled(); }
async function load(page: Page): Promise<void> { await page.goto('/'); await page.getByTestId('research-workspace').click(); await ready(page); }
async function edit(page: Page, key: string, text: string): Promise<void> { const field = page.getByTestId(`r03-edit-${key}`); if (!await field.isVisible()) await page.getByTestId('r03-all-parameters').click(); await field.fill(text); await field.blur(); await expect.poll(async () => (await ideal(page)).pendingValidation).toBe(false); }
async function releaseResults(page: Page): Promise<void> {
  if (await page.getByTestId('r03-workspace').isVisible()) { await page.getByTestId('release-results').click(); return; }
  const details = page.locator('.release-panel');
  if (!await details.evaluate(node => (node as HTMLDetailsElement).open)) await details.locator('summary').click();
  await page.getByTestId('release-results').click();
}
async function compute(page: Page, label: string): Promise<any> {
  const waiting = page.waitForResponse(response => new URL(response.url()).pathname === '/api/research/r03-fig2a/simulate' && response.request().method() === 'POST');
  await page.getByTestId('r03-compute').click(); const response = await waiting; expect(response.status()).toBe(200);
  const raw = await response.json(), request = JSON.parse(response.request().postData()!); save(`${label}_request`, request); save(`${label}_response`, raw);
  await expect.poll(async () => (await ideal(page)).completedNumerical?.requestId).toBe(request.request_id); return { raw, request };
}
test.beforeEach(async ({ page }) => { await page.route('**/*', route => new URL(route.request().url()).origin === 'http://127.0.0.1:8510' ? route.continue() : route.abort('blockedbyclient')); });
test('genuine mounted ideal workspace uses one finite response for mask and all readouts', async ({ page, browser }, info) => {
  await load(page); await page.getByTestId('r03-tab-evidence').click(); await expect(page.getByRole('heading', { name: R03_IDENTITY, exact: true })).toBeVisible();
  await page.getByTestId('r03-tab-phase').click();
  await expect(page.getByTestId('r03-viewport')).toBeVisible(); expect((await snapshot(page)).scene.researchActive).toBe(true);
  const calls: string[] = []; page.on('request', request => { const path = new URL(request.url()).pathname; if (request.method() === 'POST' && computing(path)) calls.push(path); });
  const actual = await compute(page, smoke ? 'postcommit_actual' : 'actual'), state = await ideal(page);
  expect(calls).toEqual(['/api/research/r03-fig2a/simulate']); expect(state.currentResult.phase).toEqual(actual.raw.phase);
  expect(state.currentResult.stages).toEqual(actual.raw.stages); expect(state.currentResult.population).toEqual(actual.raw.population);
  expect(state.currentResult.provenance).toEqual(actual.raw.provenance); expect(state.currentResult.experiment).toEqual(actual.request.experiment);
  expect(state.displayedRequestId).toBe(actual.request.request_id); expect(state.phaseDisplayBytes).toBe(2048);
  expect(state.apparatus).toMatchObject({ componentCount: 7, phaseVisible: true, computedRays: false, propagatedFieldSections: false });
  expect(state.apparatus.ownedBytes).toBeLessThanOrEqual(512 * 1024);
  const pixels = await page.getByTestId('r03-phase').evaluate((canvas: HTMLCanvasElement) => Array.from(canvas.getContext('2d')!.getImageData(0, 0, 16, 16).data));
  expect(pixels).toEqual(state.phaseRGBA); expect(pixels).toHaveLength(1024);
  await page.getByTestId('r03-phase').click({ position: { x: 2, y: 2 } }); expect((await ideal(page)).selectedSample).toBe(0);
  await expect(page.getByTestId('r03-sample')).toContainText(actual.raw.phase.wrapped_rad[0].toPrecision(17));
  await page.getByTestId('r03-select-qwp').click(); await page.getByTestId('r03-reset-view').click();
  const view = page.getByTestId('r03-viewport'); const rect = await view.boundingBox(); expect(rect!.width).toBeGreaterThan(650); expect(rect!.height).toBeGreaterThanOrEqual(490);
  await page.mouse.move(rect!.x + rect!.width / 2, rect!.y + 200); await page.mouse.down(); await page.mouse.move(rect!.x + rect!.width / 2 + 25, rect!.y + 210, { steps: 5 }); await page.mouse.up();
  await page.getByTestId('r03-reset-view').click(); expect(calls).toHaveLength(1); expect((await ideal(page)).currentResult.phase).toEqual(actual.raw.phase);
  mkdirSync(figures, { recursive: true }); await page.screenshot({ path: resolve(figures, 'fig01_ideal_ensemble_workspace_and_readout.png'), fullPage: true });
  await edit(page, 'seed', '17'); expect((await ideal(page)).currentResult).toBeNull(); await expect(page.getByTestId('r03-phase')).toBeHidden();
  expect((await ideal(page)).apparatus.phaseVisible).toBe(false); expect(calls).toHaveLength(1);
  await edit(page, 'phase_std_rad', 'invalid'); await expect(page.getByTestId('r03-compute')).toBeDisabled(); const draft = await ideal(page);
  const camera = (await snapshot(page)).scene.camera; await releaseResults(page); const released = await ideal(page);
  expect(released.candidate).toEqual(draft.candidate); expect(released.invalidEdits).toEqual(draft.invalidEdits); expect(released.phaseDisplayBytes).toBe(0); expect(released.numericalBytes).toBe(0);
  expect((await snapshot(page)).scene.camera).toEqual(camera); expect(calls).toHaveLength(1);
  save(smoke ? 'postcommit_browser_outcome' : 'genuine_browser_outcome', { browserVersion: browser.version(), actual, state, pixels, released, computeCalls: calls,
    recording: await page.video()?.path(), testOutputDirectory: info.outputDir, claim: 'Actual production ideal A only; no experimental comparison.' });
});

test('controlled display/HTTP failures, manual recovery and seven legacy operation gates stay separate', async ({ page }) => {
  test.skip(smoke, 'Postcommit smoke runs the fresh full A identity case; controlled precommit faults remain distinct.'); await load(page);
  const calls: string[] = []; page.on('request', request => { const path = new URL(request.url()).pathname; if (request.method() === 'POST' && computing(path)) calls.push(path); });
  await compute(page, 'controlled_prior');
  await page.evaluate(() => { const original = HTMLCanvasElement.prototype.getContext; (window as any).__r03OriginalContext = original;
    HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, ...args: any[]) { if (this.dataset.testid === 'r03-phase') return null;
      return (original as any).apply(this, args); } as typeof original; });
  await edit(page, 'source_amplitude', '1.1'); await ready(page); const failed = await compute(page, 'controlled_display_failure');
  await expect(page.getByTestId('r03-display-error')).toBeVisible(); expect((await ideal(page)).error).toBeNull(); expect((await ideal(page)).currentResult).toBeNull();
  expect((await ideal(page)).completedNumerical.requestId).toBe(failed.request.request_id); expect(calls).toHaveLength(2);
  mkdirSync(figures, { recursive: true }); await page.screenshot({ path: resolve(figures, 'fig03_stale_failure_and_recovery.png'), fullPage: true });
  await page.evaluate(() => { HTMLCanvasElement.prototype.getContext = (window as any).__r03OriginalContext; delete (window as any).__r03OriginalContext; });
  await page.getByTestId('r03-retry-display').click(); await expect(page.getByTestId('r03-display-error')).toBeHidden();
  expect((await ideal(page)).currentResult.phase).toEqual(failed.raw.phase); expect(calls).toHaveLength(2);
  await page.evaluate(() => { const canvas = document.querySelector<HTMLCanvasElement>('[data-testid="bench-canvas"]')!;
    const extension = canvas.getContext('webgl2')!.getExtension('WEBGL_lose_context'); if (!extension) throw new Error('Required controlled WebGL context-loss extension unavailable');
    (window as any).__r03ContextRecovery = extension; extension.loseContext(); });
  await expect.poll(async () => (await snapshot(page)).scene.contextLost).toBe(true); expect((await ideal(page)).currentResult).toBeNull();
  await page.evaluate(() => { (window as any).__r03ContextRecovery.restoreContext(); delete (window as any).__r03ContextRecovery; });
  await expect.poll(async () => (await snapshot(page)).scene.contextLost).toBe(false); await expect(page.getByTestId('r03-retry-display')).toBeVisible();
  expect((await ideal(page)).currentResult).toBeNull(); await page.getByTestId('r03-retry-display').click();
  expect((await ideal(page)).currentResult.requestId).toBe(failed.request.request_id); expect(calls).toHaveLength(2);
  const controlledHTTP = async (route: Route) => route.fulfill({ status: 422, contentType: 'application/json', body: JSON.stringify({ protocol_version: 1,
    message_type: 'r03_ideal_error', request_id: null, error: { code: 'controlled_numerical_failure', message: 'Controlled rejection; no result and no replay.' } }) });
  await page.route('**/api/research/r03-fig2a/simulate', controlledHTTP); await edit(page, 'phase_std_rad', '1.4'); await ready(page);
  await page.getByTestId('r03-compute').click(); await expect(page.getByTestId('r03-error')).toContainText('Controlled rejection'); expect(calls).toHaveLength(3);
  await page.unroute('**/api/research/r03-fig2a/simulate', controlledHTTP);
  await edit(page, 'phase_std_rad', '1.5'); await ready(page); let release!: () => void; const held = new Promise<void>(yes => { release = yes; });
  await page.route('**/api/research/r03-fig2a/simulate', async route => { await held; await route.continue(); });
  await page.getByTestId('r03-compute').click(); await expect.poll(async () => !!(await ideal(page)).active).toBe(true); await page.getByTestId('ordinary-workspace').click();
  for (const [mode, ids] of [['sequential', ['simulate']], ['two_path', ['tp-simulate', 'tp-sweep']], ['polarization', ['pl-simulate', 'pl-sweep']], ['polarized_two_path', ['pt-simulate', 'pt-sweep']]] as const) {
    await page.getByTestId('mode').selectOption(mode); for (const id of ids) await expect(page.getByTestId(id)).toBeDisabled();
  }
  await expect(page.getByTestId('release-results')).toBeDisabled(); expect(calls).toHaveLength(4);
  const settled = page.waitForResponse(response => new URL(response.url()).pathname === '/api/research/r03-fig2a/simulate'); release(); expect((await settled).status()).toBe(200);
  await expect.poll(async () => (await snapshot(page)).resultRelease.busy).toBe(false); await page.getByTestId('research-workspace').click(); await ready(page);
  expect((await ideal(page)).currentResult).toBeNull(); expect(calls.filter(path => path !== '/api/research/r03-fig2a/simulate')).toEqual([]);
  await releaseResults(page); save('controlled_browser_outcome', { controlledDisplayFailure: failed, final: await ideal(page), computeCalls: calls,
    claims: ['Controlled phase canvas failure cleaned partial resources', 'WebGL context restoration required explicit display recovery', 'Manual display recovery made no computation', 'Controlled HTTP422 is not success', 'All seven old client operation kinds blocked while A owns shared gate', 'Backend Future lifetime independently tested'] });
});
