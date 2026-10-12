/** Actual installed-Chrome downloads/uploads; numerical oracles live outside product files. */
import { test, expect, type Browser, type Page } from '@playwright/test';
import { readFileSync, writeFileSync, mkdirSync, renameSync, existsSync } from 'node:fs';
import { resolve, relative, dirname, isAbsolute } from 'node:path';
import { createHash } from 'node:crypto';

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
async function newPage(browser: Browser) {
  const context = await browser.newContext({ baseURL: 'http://127.0.0.1:8510', viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
  const page = await context.newPage();
  await page.route('**/*', route => new URL(route.request().url()).origin === 'http://127.0.0.1:8510' ? route.continue() : route.abort('blockedbyclient'));
  await page.goto('/'); await expect(page.getByTestId('simulate')).toBeEnabled();
  await page.getByTestId('doc-toggle').click();
  return { context, page };
}
async function upload(page: Page, path: string): Promise<void> {
  await page.getByTestId('doc-file').setInputFiles(path);
  await expect(page.getByTestId('doc-preview')).toBeVisible();
  await expect(page.getByTestId('doc-status')).toHaveAttribute('data-status', 'preview');
}
async function apply(page: Page, mode: Mode): Promise<void> {
  await page.getByTestId('doc-ack').check(); await page.getByTestId('doc-apply').click();
  await expect(page.getByTestId('mode')).toHaveValue(mode);
  await expect(page.getByTestId('doc-status')).toHaveText('設定已還原，尚未模擬');
  await expect(page.getByTestId('doc-preview')).toBeHidden();
}
async function solve(page: Page, mode: Mode, dir: string, label: string) {
  const path = mode === 'sequential' ? '/api/v1/simulate' : mode === 'two_path' ? '/api/v2b/simulate' : '/api/v2d/simulate';
  const waiting = page.waitForResponse(response => new URL(response.url()).pathname === path && response.request().method() === 'POST');
  await page.getByTestId(mode === 'sequential' ? 'simulate' : mode === 'two_path' ? 'tp-simulate' : 'pl-simulate').click();
  const response = await waiting; expect(response.status()).toBe(200);
  const body = await response.body(), request = JSON.parse(response.request().postData()!);
  saveJSON(resolve(dir, `${label}_request.json`), request); save(resolve(dir, `${label}_response.bin`), body);
  await expect.poll(async () => stateFor(await snap(page), mode).currentResult?.requestId).toBe(request.request_id);
  return { body, request };
}
async function download(page: Page, path: string): Promise<Buffer> {
  await page.getByTestId('doc-export').click(); await expect(page.getByTestId('doc-download-area')).toBeVisible();
  await expect(page.getByTestId('doc-status')).toHaveText('下載已準備');
  const waiting = page.waitForEvent('download'); await page.getByTestId('doc-download').click();
  const actual = await waiting; expect(await actual.failure()).toBeNull(); await actual.saveAs(path);
  await expect(page.getByTestId('doc-status')).toHaveText('已要求下載');
  return readFileSync(path);
}

for (const mode of modes) test(`portable ${mode}: real download, closed context, renamed upload, explicit recomputation`, async ({ browser }) => {
  const dir = resolve(evidence, mode); directory(dir);
  const doc = fixtures[mode]; expect(doc.mode).toBe(mode);
  const seed = resolve(dir, 'seed.json'); saveJSON(seed, doc);
  const first = await newPage(browser); let original: Awaited<ReturnType<typeof solve>>;
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
  } finally { await first.context.close(); }
  // No live original context or storageState survives this point.
  mkdirSync(resolve(dir, 'moved')); renameSync(resolve(dir, 'downloaded.json'), resolve(dir, 'moved', 'renamed-settings.json'));
  save(resolve(dir, 'downloaded.json'), downloaded!); // evidence copy; actual uploaded file is renamed/moved.
  expect(sha(readFileSync(resolve(dir, 'moved', 'renamed-settings.json')))).toBe(sha(downloaded!));
  const second = await newPage(browser);
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
  } finally { await second.context.close(); }
  mkdirSync(evidence, { recursive: true });
  const manifestPath = resolve(evidence, 'portability.json');
  const manifest = existsSync(manifestPath) ? JSON.parse(readFileSync(manifestPath, 'utf8')) : { modes: {} };
  manifest.modes[mode] = Object.fromEntries(Object.entries({ original_request: 'original_request.json', original_response: 'original_response.bin',
    restored_request: 'restored_request.json', restored_response: 'restored_response.bin', downloaded: 'downloaded.json',
    moved: 'moved/renamed-settings.json', reexported: 'reexported.json' }).map(([key, file]) => [key, relative(evidence, resolve(dir, file))]));
  writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
});

test('invalid and cancelled import, scalar text, metadata and exact same-label replacements', async ({ browser }) => {
  const dir = resolve(evidence, 'transactions'); directory(dir); const { context, page } = await newPage(browser);
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
  } finally { await context.close(); }
});

test('stale stage-one/stage-two responses and frozen draft export cannot replace newer intent', async ({ browser }) => {
  const dir = resolve(evidence, 'races'); directory(dir); const { context, page } = await newPage(browser);
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
  } finally { await context.close(); }
});

test('controlled document validation stays responsive under a real held worker and Apply rechecks busy', async ({ browser }) => {
  const control = process.env.V2E_CONTROLLED_DIR;
  test.skip(!control, 'Explicit separately launched task-owned held-worker harness only');
  const dir = resolve(evidence, 'held'); directory(dir); const { context, page } = await newPage(browser);
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
  } finally { if (!existsSync(resolve(owned, 'release.flag'))) save(resolve(owned, 'release.flag'), 'release owned worker during cleanup'); await context.close(); }
});
