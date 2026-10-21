/** Genuine production-browser W2 checks. Controls and test-owned clones are labelled. */
import { test, expect, chromium, type Page, type TestInfo } from '@playwright/test';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { createW2ResponseCapture } from './support/w2_response_capture';

const root = resolve('../..');
const evidence = resolve(root, process.env.W2_EVIDENCE_DIR ?? 'runs/w2_geometric_routing_implementation_01/browser');
const snapshot = (page: Page): Promise<any> => page.evaluate(() => window.__benchDebug.snapshot());
const routing = async (page: Page): Promise<any> => (await snapshot(page)).geometricRouting;
const science = (path: string) => /\/api\/(?:v1|v2b|v2d|v2g|w1)\/(?:simulate|sweep)$/.test(path)
  || path === '/api/research/r03-fig2a/simulate' || path === '/api/w2/trace';
const hash = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex');
function owned(info: TestInfo): string {
  const path = resolve(evidence, hash(Buffer.from(info.testId)).slice(0, 24));
  if (!existsSync(path)) mkdirSync(path, { recursive: true }); return path;
}
function save(info: TestInfo, name: string, value: unknown): void {
  writeFileSync(resolve(owned(info), name + '.json'), JSON.stringify(value, null, 2), { flag: 'wx' });
}
async function image(page: Page, info: TestInfo, name: string): Promise<void> {
  const bytes = await page.screenshot({ fullPage: false });
  writeFileSync(resolve(owned(info), name + '.png'), bytes, { flag: 'wx' });
}
async function frames(page: Page, count = 12): Promise<void> {
  await page.evaluate(count => new Promise<void>(done => { let n = 0; const next = () => ++n >= count ? done() : requestAnimationFrame(next); requestAnimationFrame(next); }), count);
}
async function ready(page: Page): Promise<void> {
  await expect(page.getByTestId('w2-trace')).toBeEnabled();
  await expect.poll(async () => (await routing(page)).status).toBe('ready');
}
async function load(page: Page, info: TestInfo): Promise<string[]> {
  const contextId = `context-${info.testId}`, pageId = `page-${info.testId}`;
  await page.route('**/*', route => new URL(route.request().url()).origin === 'http://127.0.0.1:8510'
    ? route.continue() : route.abort('blockedbyclient'));
  await page.addInitScript({ content: `window.__w2Capture=(${createW2ResponseCapture.toString()})(window.fetch.bind(window),${JSON.stringify({ contextId, pageId })});window.fetch=window.__w2Capture.fetch;` });
  const calls: string[] = [];
  page.on('request', request => { const path = new URL(request.url()).pathname; if (request.method() === 'POST' && science(path)) calls.push(path); });
  await page.goto('/'); await page.getByTestId('geometric-routing-workspace').click(); await ready(page);
  expect((await routing(page)).active).toBe(true); expect(calls).toEqual([]); return calls;
}
async function preset(page: Page, value: 'A' | 'B' | 'C'): Promise<void> {
  await page.getByTestId('w2-preset').selectOption(value); await page.getByTestId('w2-load-preset').click(); await ready(page);
  expect((await routing(page)).currentResult).toBeNull();
}
async function select(page: Page, id: string): Promise<void> {
  await page.getByTestId(`w2-select-${id}`).click(); await expect(page.getByTestId('w2-tab-inspector')).toHaveAttribute('aria-selected', 'true');
}
async function edit(page: Page, field: string, text: string): Promise<void> {
  await page.getByTestId(`w2-${field}`).fill(text); await page.getByTestId(`w2-${field}`).blur(); await ready(page);
  expect((await routing(page)).currentResult).toBeNull(); expect((await routing(page)).display).toBeNull();
}
async function arm(page: Page, info: TestInfo): Promise<string> {
  const state = await routing(page), token = `${info.testId}-${await page.evaluate(() => crypto.randomUUID())}`;
  await page.evaluate(({ state, token, contextId, pageId }) => (window as any).__w2Capture.arm({ contextId, pageId, token,
    sceneSha256: state.validatedDigest, scene: state.candidate }), { state, token, contextId: `context-${info.testId}`, pageId: `page-${info.testId}` });
  return token;
}
async function trace(page: Page, info: TestInfo): Promise<any> {
  const token = await arm(page, info), waiting = page.waitForResponse(response => new URL(response.url()).pathname === '/api/w2/trace');
  await page.getByTestId('w2-trace').click(); const response = await waiting; expect(response.status()).toBe(200);
  const record = await page.evaluate(token => (window as any).__w2Capture.consume(token), token);
  const bytes = Buffer.from(record.base64, 'base64'), result = JSON.parse(bytes.toString('utf8'));
  expect(bytes.byteLength).toBeLessThanOrEqual(524288);
  await expect.poll(async () => (await routing(page)).currentRequestId).toBe(record.request.request_id);
  const state = await routing(page); expect(state.currentResult).toEqual(result);
  expect(result.scene).toEqual(record.request.scene); expect(result.scene_sha256).toBe(record.request.scene_sha256);
  expect(state.display.requestId).toBe(result.request_id); expect(state.display.sceneSha256).toBe(result.scene_sha256);
  expect(state.display.endpoints).toEqual(result.segments.map((segment: any) => ({ id: segment.id, branch: segment.branch_id, start_m: segment.start_m, end_m: segment.end_m })));
  expect(state.resultResource.retainedRawBytes).toBe(0); expect(state.resultResource.retainedResponseTextBytes).toBe(0);
  expect(state.ownedBytes).toBeLessThanOrEqual(2 * 1024 * 1024);
  expect((await snapshot(page)).ownedMemory.retainedBytes).toBeLessThanOrEqual(16 * 1024 * 1024);
  const name = `trace_${result.request_id}`;
  writeFileSync(resolve(owned(info), name + '.json'), bytes, { flag: 'wx' });
  save(info, name + '_identity', { request: record.request, bytes: bytes.length, sha256: hash(bytes), state,
    capture: await page.evaluate(() => (window as any).__w2Capture.snapshot()),
    instrumentation: 'One clone of original fetch response; clone/native buffering and base64/Node copies are test resources, excluded from app ownership.' });
  return result;
}
function close(actual: number, expected: number, scale = 1): void {
  expect(Math.abs(actual - expected)).toBeLessThanOrEqual(2e-13 * Math.max(scale, 1) + 2e-13 * Math.abs(expected));
}
function account(result: any): void {
  close(result.terminals.reduce((sum: number, terminal: any) => sum + terminal.relative_weight, 0), 1);
  expect(Math.abs(result.ledger.signed_residual)).toBeLessThanOrEqual(64 * Number.EPSILON);
}

test('W2-B01 placed finite mirror produces genuine ninety degree fold and original response hit', async ({ page }, info) => {
  const calls = await load(page, info), result = await trace(page, info);
  expect(result.hits.map((hit: any) => hit.element_id)).toEqual(['M1', 'D1']);
  const terminal = result.terminals[0]; expect(terminal.category).toBe('detected'); close(terminal.cumulative_length_m, .4);
  terminal.position_m.forEach((v: number, k: number) => close(v, [.2, .08, .2][k])); account(result);
  await page.getByTestId(`w2-hit-${result.hits.at(-1).id}`).click();
  await image(page, info, 'folded_receiver_hit'); expect(calls).toEqual(['/api/w2/trace']);
});

test('W2-B02 second mirror pose edit detaches paths and explicit Trace changes hit to finite receiver miss', async ({ page }, info) => {
  const calls = await load(page, info); await preset(page, 'B'); const first = await trace(page, info);
  expect(first.hits.map((hit: any) => hit.element_id)).toEqual(['M1', 'M2', 'D1']); close(first.terminals[0].cumulative_length_m, .6);
  await page.getByTestId(`w2-hit-${first.hits.at(-1).id}`).click();
  await expect(page.getByTestId('w2-selected-hit')).toContainText(`Current Calculated Hit / ${first.hits.at(-1).id} / D1`);
  await expect(page.getByTestId('w2-selected-hit')).toContainText(first.request_id);
  await select(page, 'M2'); const before = (await routing(page)).candidate; await edit(page, 'rotation-y', '145');
  await expect(page.getByTestId('w2-selected-hit')).toHaveText('No current hit — trace the updated scene.');
  expect((await routing(page)).selectedHit).toBeNull();
  await page.getByTestId('w2-tab-data').click();
  await expect(page.getByTestId('w2-result-state')).toContainText('Previous trace — does not match the current draft');
  await expect(page.getByTestId('w2-identity')).toContainText(first.request_id);
  await expect(page.getByTestId('w2-identity')).toContainText(first.scene_sha256);
  await expect(page.getByTestId(`w2-hit-${first.hits.at(-1).id}`)).toBeDisabled();
  const after = (await routing(page)).candidate;
  expect(after.elements[0]).toEqual(before.elements[0]); expect(after.elements[2]).toEqual(before.elements[2]);
  expect(after.elements[1].pose.position_m).toEqual(before.elements[1].pose.position_m);
  expect(after.elements[1].pose.rotation_xyz_rad[0]).toBe(before.elements[1].pose.rotation_xyz_rad[0]);
  expect(calls).toEqual(['/api/w2/trace']); const changed = await trace(page, info);
  expect(changed.terminals[0].category).toBe('escaped'); expect(changed.hits.some((hit: any) => hit.element_id === 'D1')).toBe(false);
  await page.getByTestId('w2-tab-inspector').click();
  await expect(page.getByTestId('w2-selected-hit')).toContainText(changed.request_id);
  await expect(page.getByTestId('w2-selected-hit')).not.toContainText(first.request_id);
  await expect(page.getByTestId('w2-selected-hit')).not.toContainText('/ D1');
  await page.getByTestId('w2-tab-data').click();
  const p = changed.terminals[0].position_m; close(p[0], .45189355868851083); close(p[1], .08); close(p[2], .8920718646027535);
  close(Math.hypot(p[0], p[1] - .08, p[2]), 1); account(changed); await image(page, info, 'pose_edit_finite_miss');
  expect(calls).toEqual(['/api/w2/trace', '/api/w2/trace']);
});

test('W2-B03 ideal half splitter and added stop preserve both branch identities and terminal weights', async ({ page }, info) => {
  const calls = await load(page, info); await preset(page, 'C'); await select(page, 'STOP1'); await page.getByTestId('w2-remove').click(); await ready(page);
  const split = await trace(page, info); expect(split.terminals.map((terminal: any) => terminal.relative_weight)).toEqual([.5, .5]);
  expect(split.terminals.every((terminal: any) => terminal.category === 'detected')).toBe(true); account(split);
  await page.getByTestId('w2-add-kind').selectOption('beam_stop'); await page.getByTestId('w2-add').click(); await ready(page);
  await edit(page, 'position-x', '.1'); await edit(page, 'position-z', '.2'); await edit(page, 'rotation-y', '-90');
  const blocked = await trace(page, info); expect(blocked.branches.map((branch: any) => [branch.id, branch.parent_id])).toEqual(split.branches.map((branch: any) => [branch.id, branch.parent_id]));
  expect(blocked.terminals.find((terminal: any) => terminal.branch_id === 'r0.T')).toEqual(split.terminals.find((terminal: any) => terminal.branch_id === 'r0.T'));
  const reflected = blocked.terminals.find((terminal: any) => terminal.branch_id === 'r0.R');
  expect(reflected.category).toBe('absorbed'); expect(reflected.relative_weight).toBe(.5); close(reflected.cumulative_length_m, .3);
  expect(blocked.ledger.detected_weight).toBe(.5); expect(blocked.ledger.absorbed_weight).toBe(.5); account(blocked);
  expect(blocked.hits.some((hit: any) => hit.element_id === 'DR')).toBe(false);
  await image(page, info, 'split_and_blocked_branches'); expect(calls).toHaveLength(2);
});

test('W2-B04 three dimensional route local coordinates and raw response agree with independent references', async ({ page }, info) => {
  const calls = await load(page, info); await select(page, 'M1'); await edit(page, 'rotation-x', '30');
  await select(page, 'D1'); await edit(page, 'position-x', '.15'); await edit(page, 'position-y', String(.08 + Math.sqrt(6) / 20));
  await edit(page, 'position-z', '.25'); await edit(page, 'rotation-y', '0'); const result = await trace(page, info);
  const reflected = result.hits[0].outgoing[0].direction;
  [.75, Math.sqrt(6) / 4, .25].forEach((value, k) => close(reflected[k], value));
  expect(result.terminals[0].category).toBe('detected'); close(result.terminals[0].cumulative_length_m, .4);
  result.hits.at(-1).local_uv_m.forEach((value: number) => close(value, 0)); account(result); expect(calls).toHaveLength(1);
});

test('W2-B05 viewing stays passive and edited or late results never attach to a new draft', async ({ page }, info) => {
  const calls = await load(page, info); const first = await trace(page, info);
  for (const id of ['w2-top', 'w2-focus', 'w2-orbit', 'w2-reset']) await page.getByTestId(id).click();
  await page.getByTestId('w2-branch').selectOption('r0'); await select(page, 'M1');
  const unchanged = await routing(page); expect(unchanged.currentRequestId).toBe(first.request_id); expect(calls).toHaveLength(1);
  await edit(page, 'rotation-y', '-35'); expect((await routing(page)).previousRequestId).toBe(first.request_id);
  let release!: () => void; const held = new Promise<void>(done => { release = done; });
  await page.route('**/api/w2/trace', async route => { const response = await route.fetch(); await held; await route.fulfill({ response }); });
  const waiting = page.waitForRequest('**/api/w2/trace'); await page.getByTestId('w2-trace').click(); await waiting;
  await page.getByTestId('w2-rotation-y').fill('-30'); await page.getByTestId('w2-rotation-y').blur(); release();
  await expect.poll(async () => (await snapshot(page)).resultRelease.busy).toBe(false); await ready(page);
  const final = await routing(page); expect(final.currentResult).toBeNull(); expect(final.display).toBeNull(); expect(final.previousRequestId).not.toBe(first.request_id);
  expect(calls).toHaveLength(2); save(info, 'passive_and_late', { calls, final, control: 'Test-owned delayed delivery of the genuine original backend response, no synthetic scientific bytes.' });
});

test('W2-B06 ambiguous finite edges fail without fabricated successful paths', async ({ page }, info) => {
  const calls = await load(page, info); await trace(page, info); await select(page, 'D1'); await edit(page, 'position-y', '.105');
  const waiting = page.waitForResponse('**/api/w2/trace'); await page.getByTestId('w2-trace').click(); const response = await waiting;
  expect(response.status()).toBe(422); await expect(page.getByTestId('w2-error')).toBeVisible();
  const final = await routing(page); expect(final.currentResult).toBeNull(); expect(final.display).toBeNull();
  save(info, 'ambiguous_edge', { status: response.status(), final, calls }); expect(calls).toHaveLength(2);
});

test('W2-B07 domain escape and bounded truncation keep every terminal weight and incomplete status', async ({ page }, info) => {
  const calls = await load(page, info);
  await select(page, 'M1'); await page.getByTestId('w2-remove').click(); await ready(page);
  await select(page, 'D1'); await page.getByTestId('w2-remove').click(); await ready(page);
  const escaped = await trace(page, info); expect(escaped.hits).toEqual([]); expect(escaped.terminals[0].category).toBe('escaped');
  close(escaped.terminals[0].cumulative_length_m, 1); account(escaped);
  await preset(page, 'B'); await select(page, 'D1'); await page.getByTestId('w2-remove').click(); await ready(page);
  await select(page, 'M1'); await edit(page, 'position-z', '-.1'); await edit(page, 'rotation-y', '0');
  await select(page, 'M2'); await edit(page, 'position-x', '0'); await edit(page, 'position-z', '.1'); await edit(page, 'rotation-y', '0');
  const capped = await trace(page, info); expect(capped.status).toBe('incomplete'); expect(capped.hits).toHaveLength(32);
  expect(capped.terminals[0].reason).toBe('interaction_cap'); expect(capped.ledger.truncated_weight).toBe(1);
  expect(capped.ledger.absorbed_weight).toBe(0); close(capped.terminals[0].cumulative_length_m, 6.3); account(capped); expect(calls).toHaveLength(2);
});

test('W2-B08 mixed old modes documents R03 W1 and routing obey aggregate admission release and recovery', async ({ page }, info) => {
  const calls = await load(page, info); await page.getByTestId('ordinary-workspace').click();
  await expect(page.getByTestId('simulate')).toBeEnabled(); await page.getByTestId('simulate').click();
  await expect.poll(async () => (await snapshot(page)).currentResult?.requestId ?? null).not.toBeNull();
  await page.getByTestId('doc-toggle').click(); await page.getByTestId('doc-title').fill('W2 retained document'); await page.getByTestId('doc-notes').fill('Keep this draft and prepared download.');
  await page.getByTestId('doc-export').click(); await expect(page.getByTestId('doc-download')).toBeVisible();
  await page.getByTestId('w1-view').click(); await page.getByTestId('w1-load-example').click(); await expect(page.getByTestId('simulate')).toBeEnabled();
  await page.getByTestId('simulate').click(); await expect.poll(async () => (await snapshot(page)).waveField.currentResult?.requestId ?? null).not.toBeNull();
  await page.getByTestId('research-workspace').click(); await expect(page.getByTestId('r03-compute')).toBeEnabled(); await page.getByTestId('r03-compute').click();
  await expect.poll(async () => (await snapshot(page)).idealPolarization.currentResult?.requestId ?? null).not.toBeNull();
  await page.getByTestId('geometric-routing-workspace').click(); await ready(page); await trace(page, info);
  const before = await snapshot(page); expect(before.ownedMemory.waveFieldBytes).toBeGreaterThan(0); expect(before.ownedMemory.idealWorkspaceBytes).toBeGreaterThan(0);
  await select(page, 'M1'); await page.getByTestId('w2-rotation-y').fill('-');
  const invalid = (await routing(page)).candidate;
  await page.locator('.release-panel > summary').click(); await page.getByTestId('release-results').click();
  const after = await snapshot(page); expect(after.geometricRouting.currentResult).toBeNull(); expect(after.geometricRouting.numericalBytes).toBe(0);
  expect(after.geometricRouting.candidate).toEqual(invalid); await expect(page.getByTestId('w2-rotation-y')).toHaveValue('-');
  expect(after.documents.state).toEqual(before.documents.state); expect(after.ownedMemory.retainedBytes).toBeLessThan(before.ownedMemory.retainedBytes);
  const count = calls.length; await page.getByTestId('ordinary-workspace').click(); await expect(page.getByTestId('doc-title')).toHaveValue('W2 retained document');
  expect(calls).toHaveLength(count); save(info, 'mixed_release', { before, after, calls });
});

test('W2-B09 display context recovery preserves numerical ownership without optical replay', async ({ page }, info) => {
  const calls = await load(page, info), result = await trace(page, info);
  await page.getByTestId('bench-canvas').evaluate(canvas => { const extension = (canvas as HTMLCanvasElement).getContext('webgl2')!.getExtension('WEBGL_lose_context');
    if (!extension) throw new Error('Required WebGL context-loss control unavailable'); (window as any).__w2LostContext = extension; extension.loseContext(); });
  await expect.poll(async () => (await routing(page)).completedRequestId).toBe(result.request_id);
  expect((await routing(page)).currentResult).toBeNull(); await page.evaluate(() => (window as any).__w2LostContext.restoreContext());
  await expect.poll(async () => (await snapshot(page)).scene.contextLost).toBe(false);
  await page.getByTestId('w2-retry-display').click(); await expect.poll(async () => (await routing(page)).currentRequestId).toBe(result.request_id);
  expect((await routing(page)).currentResult).toEqual(result);
  expect(calls).toEqual(['/api/w2/trace']); save(info, 'context_recovery', { final: await snapshot(page), calls });
});

for (const [width, height] of [[1366, 768], [1440, 900], [1920, 1080]]) {
  test(`W2-B10 English layout ${width}x${height} keeps full precision and local scrolling`, async ({ page }, info) => {
    await page.setViewportSize({ width, height }); const calls = await load(page, info); const result = await trace(page, info);
    const region = page.getByTestId('w2-terminals'); await region.focus(); await page.keyboard.press('ArrowRight'); await frames(page);
    const data = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
      cells: [...document.querySelectorAll('.w2-table-scroll td')].map(cell => ({ value: cell.textContent, whiteSpace: getComputedStyle(cell).whiteSpace })),
      english: !/[\u3400-\u9fff]/.test(document.body.innerText), canvas: document.querySelector('[data-testid="bench-canvas"]')!.getBoundingClientRect().toJSON() }));
    expect(data.scrollWidth).toBeLessThanOrEqual(width + 1); expect(data.cells.length).toBeGreaterThan(0); expect(data.cells.every(cell => cell.whiteSpace === 'nowrap')).toBe(true);
    expect(data.english).toBe(true); expect(data.canvas.width).toBeGreaterThan(300); expect(data.canvas.height).toBeGreaterThan(250);
    expect((await routing(page)).currentResult).toEqual(result); expect(calls).toHaveLength(1);
    await image(page, info, `layout_${width}x${height}`); save(info, 'layout', data);
  });
}

test('W2-B10 actual Chrome 200 percent zoom preserves complete-value keyboard and pointer access', async ({}, info) => {
  const profile = info.outputPath('w2-actual-zoom-profile'); mkdirSync(resolve(profile, 'Default'), { recursive: true });
  writeFileSync(resolve(profile, 'Default/Preferences'), JSON.stringify({ partition: { default_zoom_level: { x: Math.log(2) / Math.log(1.2) } } }), { flag: 'wx' });
  const context = await chromium.launchPersistentContext(profile, { channel: 'chrome', headless: true, viewport: null,
    deviceScaleFactor: undefined, baseURL: 'http://127.0.0.1:8510', args: ['--window-size=1440,900'] });
  try {
    const page = context.pages()[0] ?? await context.newPage(), calls = await load(page, info); const result = await trace(page, info);
    const zoom = await page.evaluate(() => ({ innerWidth, outerWidth, devicePixelRatio, scale: visualViewport?.scale, scrollWidth: document.documentElement.scrollWidth }));
    expect(zoom.devicePixelRatio).toBe(2); expect(zoom.scale).toBe(1); expect(zoom.innerWidth).toBeLessThan(740); expect(zoom.outerWidth).toBeGreaterThanOrEqual(1400);
    expect(zoom.scrollWidth).toBeLessThanOrEqual(zoom.innerWidth + 1);
    await page.getByTestId('w2-terminals').scrollIntoViewIfNeeded(); const region = page.getByTestId('w2-terminals'); await region.focus();
    await page.keyboard.press('Home'); await page.keyboard.press('ArrowRight'); await frames(page);
    const before = await region.evaluate(node => ({ left: node.scrollLeft, width: node.clientWidth, full: node.scrollWidth,
      cells: [...node.querySelectorAll('td')].map(cell => ({ text: cell.textContent, space: getComputedStyle(cell).whiteSpace })) }));
    const box = await region.boundingBox(); expect(box).not.toBeNull(); await page.mouse.move(box!.x + box!.width / 2, box!.y + 30); await page.mouse.wheel(240, 0); await frames(page);
    expect(before.cells.every(cell => cell.space === 'nowrap')).toBe(true);
    if (before.full > before.width) expect(await region.evaluate(node => node.scrollLeft)).toBeGreaterThan(0);
    expect((await routing(page)).currentResult).toEqual(result); expect(calls).toHaveLength(1);
    const cdp = await context.newCDPSession(page), shot = await cdp.send('Page.captureScreenshot', { format: 'png', fromSurface: true, captureBeyondViewport: false });
    writeFileSync(resolve(owned(info), 'actual_200percent.png'), Buffer.from(shot.data, 'base64'), { flag: 'wx' });
    save(info, 'actual_zoom', { zoom, table: before, calls, isolatedProfileOnly: true, method: 'Chrome content zoom in a disposable task-owned profile; no CSS, pinch, device-scale emulation or changes to the user profile.' });
  } finally { await context.close(); }
});

test('W2-B10 normal speed recording shows edits explicit tracing hits misses split stop and ledger', async ({ browser }, info) => {
  const context = await browser.newContext({ baseURL: 'http://127.0.0.1:8510', viewport: { width: 1440, height: 900 },
    recordVideo: { dir: resolve(owned(info), 'recording'), size: { width: 1440, height: 900 } } });
  const page = await context.newPage(), started = Date.now();
  try {
    const calls = await load(page, info); await page.waitForTimeout(1200); await preset(page, 'B'); await page.waitForTimeout(1200);
    const first = await trace(page, info); await page.waitForTimeout(2500); await page.getByTestId('w2-hit-' + first.hits.at(-1).id).click();
    await page.getByTestId('w2-top').click(); await page.waitForTimeout(1800); await page.getByTestId('w2-orbit').click(); await page.waitForTimeout(1800);
    await select(page, 'M2'); await edit(page, 'rotation-y', '145'); await page.waitForTimeout(2300); const miss = await trace(page, info);
    expect(miss.terminals[0].category).toBe('escaped'); await page.waitForTimeout(2500); await image(page, info, 'recording_miss');
    await preset(page, 'C'); await page.waitForTimeout(1800); const split = await trace(page, info); await page.waitForTimeout(2500);
    await page.getByTestId('w2-branch').selectOption('r0.T'); await page.waitForTimeout(1800); await page.getByTestId('w2-branch').selectOption('r0.R'); await page.waitForTimeout(1800);
    await page.getByTestId('w2-branch').selectOption(''); await image(page, info, 'recording_split_ledger');
    const remaining = 36_000 - (Date.now() - started); if (remaining > 0) await page.waitForTimeout(remaining);
    const final = await snapshot(page), rendering = final.scene.geometricRouting;
    expect(Date.now() - started).toBeGreaterThanOrEqual(30_000); expect(Date.now() - started).toBeLessThanOrEqual(60_000);
    expect(rendering.frameIntervalsMs.length).toBeGreaterThan(30); expect(rendering.rendererSubmissionMs.length).toBeGreaterThan(30);
    expect(rendering.rendererCount).toBe(1); expect(rendering.controlsCount).toBe(1); expect(rendering.rafCount).toBe(1);
    expect(calls).toEqual(['/api/w2/trace', '/api/w2/trace', '/api/w2/trace']);
    save(info, 'recording_observations', { browser: browser.version(), elapsedSeconds: (Date.now() - started) / 1000,
      first, miss, split, final, calls, timingScope: 'Browser RAF intervals and CPU renderer submission only; not GPU time or guaranteed FPS.' });
  } finally { await context.close(); }
});

test('W2-B11 invalid edits repeated hit IDs presets and release bind only the current accepted identity', async ({ page }, info) => {
  const calls = await load(page, info), first = await trace(page, info), oldHit = first.hits.at(-1);
  await page.getByTestId(`w2-hit-${oldHit.id}`).click();
  await select(page, 'M1');
  await expect(page.getByTestId('w2-selected-hit')).toContainText(`Current Calculated Hit / ${oldHit.id} / D1`);
  expect((await routing(page)).candidate).toEqual(first.scene); expect(calls).toHaveLength(1);
  await select(page, 'D1'); await page.getByTestId('w2-position-x').fill('-');
  await expect(page.getByTestId('w2-trace')).toBeDisabled();
  await expect(page.getByTestId('w2-selected-hit')).toHaveText('No current hit — trace the updated scene.');
  expect((await routing(page)).selectedHitIdentity).toBeNull();
  await page.getByTestId('w2-tab-data').click();
  await expect(page.getByTestId('w2-result-state')).toContainText('Previous trace — does not match the current draft');
  await expect(page.getByTestId('w2-identity')).toContainText(first.request_id);
  await expect(page.getByTestId('w2-identity')).toContainText(first.scene_sha256);
  await expect(page.getByTestId(`w2-hit-${oldHit.id}`)).toBeDisabled();
  await page.getByTestId('w2-tab-inspector').click(); await edit(page, 'position-x', '.21');
  const next = await trace(page, info), hit = next.hits.at(-1);
  expect(hit.id).toBe(oldHit.id); expect(next.request_id).not.toBe(first.request_id); expect(next.scene_sha256).not.toBe(first.scene_sha256);
  expect(hit.position_m).not.toEqual(oldHit.position_m); await page.getByTestId(`w2-hit-${hit.id}`).click();
  const details = page.getByTestId('w2-selected-hit');
  await expect(details).toContainText(next.request_id); await expect(details).toContainText(next.scene_sha256);
  await expect(details).not.toContainText(first.request_id);
  await expect(details).toContainText(`Position / m: (${hit.position_m.map(String).join(', ')})`);
  expect((await routing(page)).selectedHitIdentity).toEqual({ requestId: next.request_id, sceneSha256: next.scene_sha256, hitId: hit.id });
  await preset(page, 'B'); await page.getByTestId('w2-tab-inspector').click();
  await expect(details).toHaveText('No current hit — trace the updated scene.'); expect((await routing(page)).selectedHit).toBeNull();
  await page.getByTestId('w2-tab-data').click(); await expect(page.getByTestId('w2-identity')).toContainText(next.request_id);
  await page.locator('.release-panel > summary').click(); await page.getByTestId('release-results').click();
  await page.getByTestId('w2-tab-inspector').click(); await expect(details).toHaveText('No current hit — trace the updated scene.');
  const final = await routing(page); expect(final.selectedHitIdentity).toBeNull(); expect(final.previousRequestId).toBeNull(); expect(final.numericalBytes).toBe(0);
  expect(calls).toEqual(['/api/w2/trace', '/api/w2/trace']); save(info, 'identity_regressions', { first, next, final, calls });
});

test('W2-B11 context header restores every existing mode and R03 with passive navigation', async ({ page }, info) => {
  const calls = await load(page, info), initial = (await routing(page)).candidate;
  const header = () => page.locator('.header-detail').evaluate(node => [node.firstChild!.nodeValue, node.querySelector('span')!.textContent]);
  const routingHeader = ['Geometric Rays · Finite Ideal Surfaces', 'Relative Weights · Explicit Trace'];
  const originalHeader = ['Monochromatic · Scalar · Aligned Forward Optics', 'Local Operation / Explicit Submission'];
  expect(await header()).toEqual(routingHeader);
  for (const id of ['w2-top', 'w2-orbit', 'w2-focus', 'w2-reset', 'w2-tab-data', 'w2-tab-inspector']) await page.getByTestId(id).click();
  await select(page, 'M1'); expect((await routing(page)).candidate).toEqual(initial);
  for (const mode of ['sequential', 'two_path', 'polarization', 'polarized_two_path']) {
    await page.getByTestId('ordinary-workspace').click(); await page.getByTestId('mode').selectOption(mode);
    expect(await header()).toEqual(originalHeader);
    await page.getByTestId('geometric-routing-workspace').click(); await ready(page); expect(await header()).toEqual(routingHeader);
  }
  await page.getByTestId('research-workspace').click(); expect(await header()).toEqual(originalHeader);
  await page.getByTestId('geometric-routing-workspace').click(); await ready(page); expect(await header()).toEqual(routingHeader);
  expect((await routing(page)).candidate).toEqual(initial); expect(calls).toEqual([]);
  save(info, 'context_header', { routingHeader, originalHeader, calls, final: await routing(page) });
});

test('W2-B11 targeted recording shows cleared stale hit missed retrace and current identity', async ({ browser }, info) => {
  const context = await browser.newContext({ baseURL: 'http://127.0.0.1:8510', viewport: { width: 1440, height: 900 },
    recordVideo: { dir: resolve(owned(info), 'recording'), size: { width: 1440, height: 900 } } });
  const page = await context.newPage(), started = Date.now();
  try {
    const calls = await load(page, info); await preset(page, 'B'); const first = await trace(page, info);
    await page.getByTestId(`w2-hit-${first.hits.at(-1).id}`).click(); await page.waitForTimeout(1600);
    await select(page, 'M2'); await edit(page, 'rotation-y', '145');
    await expect(page.getByTestId('w2-selected-hit')).toHaveText('No current hit — trace the updated scene.');
    await image(page, info, 'edited_no_current_hit'); await page.waitForTimeout(2200);
    const miss = await trace(page, info); expect(miss.terminals[0].category).toBe('escaped');
    await page.getByTestId('w2-tab-inspector').click(); await expect(page.getByTestId('w2-selected-hit')).not.toContainText('/ D1');
    await image(page, info, 'missed_receiver_current_identity'); await page.waitForTimeout(2000);
    await preset(page, 'B'); const current = await trace(page, info), hit = current.hits.at(-1);
    await page.getByTestId(`w2-hit-${hit.id}`).click();
    const region = page.getByRole('region', { name: 'Full calculated hit values', exact: true });
    const values = [`Position / m: (${hit.position_m.map(String).join(', ')})`, `Receiver/surface local UV / m: (${hit.local_uv_m.map(String).join(', ')})`,
      `Incident direction: (${hit.incident_direction.map(String).join(', ')})`, `Cumulative geometric distance / m: ${String(hit.cumulative_length_m)}`, `Incoming relative weight: ${String(hit.incoming_weight)}`];
    for (const value of values) await expect(region).toContainText(value);
    await expect(region).toContainText(current.request_id); await expect(region).toContainText(current.scene_sha256);
    await image(page, info, 'current_successful_hit_identity'); await image(page, info, 'corrected_w2_header');
    await region.focus(); await page.keyboard.press('ArrowRight'); await frames(page);
    const access = await region.evaluate(node => ({ width: node.clientWidth, full: node.scrollWidth, left: node.scrollLeft,
      paragraphs: [...node.querySelectorAll('p')].map(p => ({ text: p.textContent, whiteSpace: getComputedStyle(p).whiteSpace })),
      rootWidth: document.documentElement.scrollWidth, viewport: innerWidth }));
    if (access.full > access.width) expect(access.left).toBeGreaterThan(0);
    const box = await region.boundingBox(); expect(box).not.toBeNull(); await page.mouse.move(box!.x + box!.width / 2, box!.y + 20); await page.mouse.wheel(240, 0); await frames(page);
    expect(access.paragraphs.every(p => p.whiteSpace === 'nowrap')).toBe(true); expect(access.rootWidth).toBeLessThanOrEqual(access.viewport + 1);
    expect((await routing(page)).currentResult).toEqual(current); expect(calls).toEqual(['/api/w2/trace', '/api/w2/trace', '/api/w2/trace']);
    await image(page, info, 'current_hit_scrolled_full_value_access'); await page.waitForTimeout(1800);
    save(info, 'targeted_recording', { browser: browser.version(), elapsedSeconds: (Date.now() - started) / 1000, first, miss, current, values, access, calls, final: await routing(page) });
  } finally { await context.close(); }
});

test('W2-C01 genuine held routing worker rejects all ten computation contenders and double Trace', async ({ page }, info) => {
  const directory = process.env.W2_HELD_DIR; test.skip(!directory, 'Requires a separately owned actual-worker hold child.');
  const calls = await load(page, info); await page.getByTestId('w2-trace').click();
  await expect.poll(() => { try { return JSON.parse(readFileSync(resolve(directory!, 'started.json'), 'utf8')).operation; } catch { return null; } }).toBe('routing');
  await expect(page.getByTestId('w2-trace')).toBeDisabled(); expect(calls).toHaveLength(1);
  const health = await fetch('http://127.0.0.1:8510/api/v1/health'); expect((await health.json() as any).busy).toBe(true);
  const requests = JSON.parse(readFileSync(process.env.W2_CONTENDER_FIXTURES!, 'utf8'));
  const responses = [];
  for (const item of requests) {
    const response = await fetch('http://127.0.0.1:8510' + item.path, { method: 'POST', headers: { Origin: 'http://127.0.0.1:8510', 'Content-Type': 'application/json' }, body: JSON.stringify(item.payload) });
    expect(response.status, item.path).toBe(409); responses.push({ path: item.path, status: response.status });
  }
  expect(responses).toHaveLength(10); writeFileSync(resolve(directory!, 'release.flag'), 'Release this task-owned worker.', { flag: 'wx' });
  await expect.poll(async () => (await routing(page)).currentRequestId).not.toBeNull();
  save(info, 'held_all_contenders', { calls, responses, final: await snapshot(page), completed: JSON.parse(readFileSync(resolve(directory!, 'completed.json'), 'utf8')) });
});

test('W2-C02 genuine routing encoding hold survives browser disconnect until actual completion', async ({ page, context }, info) => {
  const directory = process.env.W2_HELD_ENCODING_DIR; test.skip(!directory, 'Requires a separately owned actual-encoding hold child.');
  const calls = await load(page, info); await page.getByTestId('w2-trace').click();
  await expect.poll(() => existsSync(resolve(directory!, 'started.json'))).toBe(true); await context.close();
  expect((await (await fetch('http://127.0.0.1:8510/api/v1/health')).json() as any).busy).toBe(true);
  const requests = JSON.parse(readFileSync(process.env.W2_CONTENDER_FIXTURES!, 'utf8')), responses = [];
  for (const item of requests) {
    const response = await fetch('http://127.0.0.1:8510' + item.path, { method: 'POST', headers: { Origin: 'http://127.0.0.1:8510', 'Content-Type': 'application/json' }, body: JSON.stringify(item.payload) });
    expect(response.status, item.path).toBe(409); responses.push({ path: item.path, status: response.status });
  }
  expect(responses).toHaveLength(10);
  writeFileSync(resolve(directory!, 'release.flag'), 'Release this task-owned encoder.', { flag: 'wx' });
  await expect.poll(async () => (await (await fetch('http://127.0.0.1:8510/api/v1/health')).json() as any).busy).toBe(false);
  save(info, 'encoding_disconnect', { calls, responses, completed: JSON.parse(readFileSync(resolve(directory!, 'completed.json'), 'utf8')) }); expect(calls).toHaveLength(1);
});

test('W2-C03 foreign older operation holds actual worker while W2 validation stays noncomputing', async ({ page }, info) => {
  const directory = process.env.W2_FOREIGN_HELD_DIR; test.skip(!directory, 'Requires an owned older-operation hold child and declared valid request.');
  const requests = JSON.parse(readFileSync(process.env.W2_CONTENDER_FIXTURES!, 'utf8')), foreign = requests.find((item: any) => item.path === '/api/v1/simulate');
  const pending = fetch('http://127.0.0.1:8510' + foreign.path, { method: 'POST', headers: { Origin: 'http://127.0.0.1:8510', 'Content-Type': 'application/json' }, body: JSON.stringify(foreign.payload) });
  await expect.poll(() => existsSync(resolve(directory!, 'started.json'))).toBe(true);
  const calls = await load(page, info); const waiting = page.waitForResponse('**/api/w2/trace'); await page.getByTestId('w2-trace').click(); expect((await waiting).status()).toBe(409);
  await expect(page.getByTestId('w2-error')).toBeVisible(); expect((await routing(page)).currentResult).toBeNull();
  writeFileSync(resolve(directory!, 'release.flag'), 'Release this task-owned older operation.', { flag: 'wx' }); expect((await pending).status).toBe(200);
  await expect.poll(async () => (await (await fetch('http://127.0.0.1:8510/api/v1/health')).json() as any).busy).toBe(false);
  save(info, 'foreign_worker', { calls, final: await snapshot(page) });
});

test('W2-C04 wrong identity or malformed child transport never publishes or replays a route', async ({ page }, info) => {
  test.skip(!process.env.W2_TRANSPORT_FAULT, 'Requires a clearly labelled malformed/wrongidentity controlled child.');
  const calls = await load(page, info), waiting = page.waitForResponse('**/api/w2/trace'); await page.getByTestId('w2-trace').click(); expect((await waiting).status()).toBe(200);
  await expect(page.getByTestId('w2-error')).toBeVisible(); const state = await routing(page); expect(state.currentResult).toBeNull(); expect(state.display).toBeNull();
  expect(calls).toEqual(['/api/w2/trace']); save(info, 'transport_fault', { calls, state, fault: process.env.W2_TRANSPORT_FAULT });
});

test('W2-C04 controlled DOM preparation failure retains genuine numerics for manual display-only recovery', async ({ page }, info) => {
  const calls = await load(page, info);
  const token = await arm(page, info);
  await page.evaluate(() => {
    const original = Element.prototype.append; let fired = false;
    Element.prototype.append = function (...nodes) {
      if (!fired && this.getAttribute('data-testid') === 'w2-terminals' && nodes.some(node => node instanceof HTMLTableElement)) {
        fired = true; Element.prototype.append = original; throw new Error('Controlled W2 result DOM preparation fault');
      }
      return original.apply(this, nodes);
    };
  });
  const waiting = page.waitForResponse('**/api/w2/trace'); await page.getByTestId('w2-trace').click(); expect((await waiting).status()).toBe(200);
  const captured = await page.evaluate(token => (window as any).__w2Capture.consume(token), token), bytes = Buffer.from(captured.base64, 'base64');
  const original = JSON.parse(bytes.toString('utf8'));
  writeFileSync(resolve(owned(info), 'original_numerical_response.json'), bytes, { flag: 'wx' });
  await expect.poll(async () => (await routing(page)).completedRequestId).not.toBeNull();
  const completed = await routing(page); expect(completed.currentResult).toBeNull(); expect(completed.renderError).toContain('Controlled');
  await page.getByTestId('w2-retry-display').click(); await expect.poll(async () => (await routing(page)).currentRequestId).toBe(completed.completedRequestId);
  expect((await routing(page)).currentResult).toEqual(original);
  expect(calls).toEqual(['/api/w2/trace']); save(info, 'dom_display_failure', { before: completed, after: await routing(page), calls, classification: 'Controlled browser DOM presentation fault; original numerical response unchanged.' });
});
