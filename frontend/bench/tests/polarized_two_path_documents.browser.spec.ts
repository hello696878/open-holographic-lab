/** Genuine v2 downloads and fresh-context portability; old v1 specs remain unchanged. */
import { test, expect, type Browser, type Page } from '@playwright/test';
import { readFileSync, writeFileSync, mkdirSync, renameSync, existsSync } from 'node:fs';
import { resolve, relative } from 'node:path';
import { createHash } from 'node:crypto';

const root = resolve('../..'), evidence = resolve(root, process.env.V2G_DOCUMENT_EVIDENCE_DIR ?? 'runs/v2g_acceptance/documents_browser');
const figures = resolve(root, process.env.V2G_FIGURE_DIR ?? 'docs/handoffs/v2g/figures');
const snap = (page: Page): Promise<any> => page.evaluate(() => window.__benchDebug.snapshot());
const science = (url: string) => /\/api\/(?:v1|v2b|v2d|v2g)\/(?:simulate|sweep)$/.test(new URL(url).pathname);
const sha = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex');
const bits = (value: number) => { const b = Buffer.alloc(8); b.writeDoubleLE(value); return b.toString('hex'); };
function save(path: string, value: string | Buffer): void { writeFileSync(path, value, { flag: 'wx' }); }
function saveJSON(path: string, value: unknown): void { save(path, JSON.stringify(value, null, 2)); }
function directory(path: string): void { if (existsSync(path)) throw new Error(`Preserve existing evidence: ${path}`); mkdirSync(path, { recursive: true }); }
function same(a: any, b: any, path = 'settings'): void {
  if (typeof a === 'number') { expect(typeof b, path).toBe('number'); if (a === 0 && b === 0) return; expect(bits(b), path).toBe(bits(a)); return; }
  if (Array.isArray(a)) { expect(Array.isArray(b), path).toBe(true); expect(b.length, path).toBe(a.length); a.forEach((v, i) => same(v, b[i], `${path}[${i}]`)); return; }
  if (a && typeof a === 'object') { expect(Object.keys(b).sort(), path).toEqual(Object.keys(a).sort()); Object.keys(a).forEach(k => same(a[k], b[k], `${path}.${k}`)); return; }
  expect(b, path).toBe(a);
}
function fixture(enabled: boolean): any {
  return { document_format: 'ohlab_virtual_experiment', document_version: 2, mode: 'polarized_two_path', model_contract: 'v2g_ideal_polarized_two_path_v1',
    metadata: { title: `偏振兩路 ${enabled ? '分析啟用' : '分析停用'} 😀`, notes: 'signed Gaussian waist; ordered IDs; e\u0301；保留設定，不保存結果。' },
    experiment: { schema_version: 1, model_contract: 'v2g_ideal_polarized_two_path_v1', wavelength_m: 647.0000000000001e-9,
      grid: { ny: 16, nx: 17, dy: 4.3e-6, dx: 3.7e-6 }, source: { kind: 'gaussian', amplitude: .73, phase_rad: .37000000000000005,
        waist_radius_m: 41e-6, waist_z_m: -.0007000000000000001, center_x_m: 12e-6, center_y_m: -8e-6 },
      coefficients: { x: { re: .7, im: .2 }, y: { re: -.3, im: .4 } },
      arm_0: { distance_m: .0013000000000000002, actions: [{ id: 'p0', kind: 'linear_polarizer', axis_angle_rad: .42000000000000004 },
        { id: 'r0', kind: 'linear_retarder', axis_angle_rad: -.31, retardance_rad: Math.PI / 2 }] },
      arm_1: { distance_m: .0021000000000000003, actions: [{ id: 'r1', kind: 'linear_retarder', axis_angle_rad: .17, retardance_rad: Math.PI },
        { id: 'p1', kind: 'linear_polarizer', axis_angle_rad: -.29 }] }, relative_phase_rad: -7.123456789012344,
      analyzer: { enabled, axis_angle_rad: .6100000000000001 } } };
}
async function open(browser: Browser): Promise<{ context: Awaited<ReturnType<Browser['newContext']>>; page: Page }> {
  const context = await browser.newContext({ baseURL: 'http://127.0.0.1:8510', viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
  const page = await context.newPage(); await page.route('**/*', route => new URL(route.request().url()).origin === 'http://127.0.0.1:8510' ? route.continue() : route.abort('blockedbyclient'));
  await page.goto('/'); await expect(page.getByTestId('simulate')).toBeEnabled(); await page.getByTestId('doc-toggle').click(); return { context, page };
}
async function upload(page: Page, path: string): Promise<void> { await page.getByTestId('doc-file').setInputFiles(path); await expect(page.getByTestId('doc-preview')).toBeVisible(); await expect(page.getByTestId('doc-status')).toHaveAttribute('data-status', 'preview'); }
async function apply(page: Page): Promise<void> { await page.getByTestId('doc-ack').check(); await page.getByTestId('doc-apply').click(); await expect(page.getByTestId('mode')).toHaveValue('polarized_two_path'); await expect(page.getByTestId('doc-status')).toHaveText('設定已還原，尚未模擬'); }
async function solve(page: Page, dir: string, label: string): Promise<{ request: any; bytes: Buffer }> {
  const waiting = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v2g/simulate' && r.request().method() === 'POST');
  await page.getByTestId('pt-simulate').click(); const response = await waiting; expect(response.status()).toBe(200);
  const request = JSON.parse(response.request().postData()!), bytes = await response.body(); saveJSON(resolve(dir, `${label}_request.json`), request); save(resolve(dir, `${label}_response.bin`), bytes);
  await expect.poll(async () => (await snap(page)).polarizedTwoPath.currentResult?.requestId).toBe(request.request_id); return { request, bytes };
}
async function download(page: Page, path: string, prepare = true): Promise<Buffer> {
  if (prepare) { await page.getByTestId('doc-export').click(); await expect(page.getByTestId('doc-download-area')).toBeVisible(); }
  const waiting = page.waitForEvent('download'); await page.getByTestId('doc-download').click(); const actual = await waiting;
  expect(await actual.failure()).toBeNull(); await actual.saveAs(path); return readFileSync(path);
}
function frame(bytes: Buffer): { requestId: string; scientific: any; payload: Buffer } {
  expect(bytes.subarray(0, 8).toString('binary')).toBe('OHLABPT\0'); const n = bytes.readUInt32LE(8), header = JSON.parse(bytes.subarray(16, 16 + n).toString('utf8'));
  const { request_id, ...scientific } = header; return { requestId: request_id, scientific, payload: bytes.subarray(16 + Math.ceil(n / 8) * 8) };
}

for (const enabled of [true, false]) test(`v2 genuine portability analyzer ${enabled ? 'enabled' : 'disabled with saved nondefault angle'}`, async ({ browser }) => {
  const label = enabled ? 'enabled' : 'disabled', dir = resolve(evidence, label); directory(dir); const doc = fixture(enabled), seed = resolve(dir, 'seed.json'); saveJSON(seed, doc);
  const first = await open(browser); let original!: Awaited<ReturnType<typeof solve>>, downloaded!: Buffer;
  try {
    const requests: string[] = []; first.page.on('request', r => { if (r.method() === 'POST') requests.push(r.url()); });
    await upload(first.page, seed); expect(requests.filter(science)).toHaveLength(0); expect(requests.filter(u => u.endsWith('/api/v2e/documents/validate'))).toHaveLength(2);
    await apply(first.page); same(doc.experiment, (await snap(first.page)).polarizedTwoPath.validatedDraft); expect(requests.filter(science)).toHaveLength(0);
    original = await solve(first.page, dir, 'original'); downloaded = await download(first.page, resolve(dir, 'downloaded.json'));
    const exported = JSON.parse(downloaded.toString('utf8')); same(doc, exported); expect(Object.keys(exported).sort()).toEqual(['document_format', 'document_version', 'mode', 'model_contract', 'experiment', 'metadata'].sort());
    // Release must preserve both an import preview and an already prepared, useful download URL.
    await upload(first.page, seed); const before = await snap(first.page), count = requests.length;
    await first.page.locator('.release-panel summary').click(); await first.page.getByTestId('release-results').click();
    const after = await snap(first.page); same(after.documents.state.preview, before.documents.state.preview);
    expect(after.documents.state.preparedDownload).toEqual(before.documents.state.preparedDownload); expect(after.documents.ownership).toEqual(before.documents.ownership);
    expect(after.polarizedTwoPath.candidate).toEqual(before.polarizedTwoPath.candidate); expect(after.ownedMemory.scientificBytes).toBe(0); expect(requests.length).toBe(count);
    const releasedDownload = await download(first.page, resolve(dir, 'after-release-download.json'), false); expect(releasedDownload.equals(downloaded)).toBe(true);
    expect(requests.filter(science)).toHaveLength(1);
  } finally { await first.context.close(); }
  // The actual downloaded file moves only after the original browser context is closed.
  mkdirSync(resolve(dir, 'moved')); renameSync(resolve(dir, 'downloaded.json'), resolve(dir, 'moved', 'renamed-experiment.json'));
  save(resolve(dir, 'downloaded.json'), downloaded); expect(sha(readFileSync(resolve(dir, 'moved', 'renamed-experiment.json')))).toBe(sha(downloaded));
  const second = await open(browser);
  try {
    const requests: string[] = []; second.page.on('request', r => { if (r.method() === 'POST') requests.push(r.url()); });
    expect(await second.page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
    const before = await snap(second.page); await upload(second.page, resolve(dir, 'moved', 'renamed-experiment.json'));
    const preview = await snap(second.page); expect(preview.mode).toBe('sequential'); same(before.polarizedTwoPath.candidate, preview.polarizedTwoPath.candidate);
    expect(requests.filter(science)).toHaveLength(0); expect(requests.filter(u => u.endsWith('/api/v2e/documents/validate'))).toHaveLength(2);
    await apply(second.page); const restored = await snap(second.page); same(doc.experiment, restored.polarizedTwoPath.validatedDraft);
    expect(restored.polarizedTwoPath.currentResult).toBeNull(); expect(restored.polarizedTwoPath.lastSweep).toBeNull(); expect(requests.filter(science)).toHaveLength(0);
    await expect(second.page.getByTestId('pt-edit-source-waist_z_m')).toHaveValue(String(doc.experiment.source.waist_z_m));
    await expect(second.page.getByTestId('pt-edit-analyzer-axis_angle_rad')).toHaveValue(String(doc.experiment.analyzer.axis_angle_rad));
    if (enabled) { mkdirSync(figures, { recursive: true }); await second.page.screenshot({ path: resolve(figures, 'fig03_v2_import_unsimulated.png'), fullPage: true }); }
    await second.page.getByTestId('zoom-in').click(); await second.page.getByTestId('pt-select-r0').click();
    await second.page.getByTestId('mode').selectOption('sequential'); await second.page.getByTestId('mode').selectOption('polarized_two_path'); await expect(second.page.getByTestId('pt-simulate')).toBeEnabled();
    same(doc.experiment, (await snap(second.page)).polarizedTwoPath.validatedDraft); expect(requests.filter(science)).toHaveLength(0);
    const actual = await solve(second.page, dir, 'restored'), a = frame(original.bytes), b = frame(actual.bytes);
    expect(b.requestId).not.toBe(a.requestId); same(original.request.experiment, actual.request.experiment);
    expect(b.scientific).toEqual(a.scientific); expect(b.payload.equals(a.payload)).toBe(true);
    const reexported = await download(second.page, resolve(dir, 'reexported.json')); expect(reexported.equals(downloaded)).toBe(true);
    if (!enabled) {
      expect((await snap(second.page)).polarizedTwoPath.currentResult.analysis).toMatchObject({ enabled: false, axis_angle_rad: doc.experiment.analyzer.axis_angle_rad, ports: null, total_norm: null });
      await expect(second.page.getByTestId('pt-analysis-absent')).toBeVisible(); await expect(second.page.getByTestId('pt-intensity-analyzed-0')).toHaveCount(0);
      await second.page.getByTestId('pt-analyzer-enabled').check(); await expect(second.page.getByTestId('pt-simulate')).toBeEnabled();
      expect((await snap(second.page)).polarizedTwoPath.candidate.analyzer.axis_angle_rad).toBe(doc.experiment.analyzer.axis_angle_rad);
      const analyzed = await solve(second.page, dir, 'enabled_after_import'); expect((await snap(second.page)).polarizedTwoPath.currentResult.analysis.axis_angle_rad).toBe(doc.experiment.analyzer.axis_angle_rad);
      expect(analyzed.request.experiment.analyzer).toEqual({ enabled: true, axis_angle_rad: doc.experiment.analyzer.axis_angle_rad });
    }
    saveJSON(resolve(dir, 'outcome.json'), { analyzerEnabled: enabled, originalContextClosed: true, freshStorageIsolatedContext: true, actualDownloadUsed: true,
      movedRenamedBytesUnchanged: true, exactNonzeroNumberBits: true, canonicalIdempotent: true, fullScientificHeaderExact: true, fullPayloadExact: true,
      originalRequestId: a.requestId, restoredRequestId: b.requestId, payloadSHA256: sha(b.payload), documentSHA256: sha(downloaded),
      disabledSavedAnglePreserved: !enabled, requests, source: doc.experiment.source, actions: [doc.experiment.arm_0.actions, doc.experiment.arm_1.actions] });
  } finally { await second.context.close(); }
  const manifest = resolve(evidence, 'portability.json'), saved = existsSync(manifest) ? JSON.parse(readFileSync(manifest, 'utf8')) : { cases: {} };
  saved.cases[label] = Object.fromEntries(['original_response.bin', 'restored_response.bin', 'original_request.json', 'restored_request.json', 'downloaded.json', 'reexported.json', 'moved/renamed-experiment.json']
    .map(file => [file, relative(evidence, resolve(dir, file))])); writeFileSync(manifest, JSON.stringify(saved, null, 2));
});

test('new v2 mismatch rejected while invalid editors and metadata survive repeated result release', async ({ browser }) => {
  const dir = resolve(evidence, 'matrix_release'); directory(dir); const { context, page } = await open(browser);
  try {
    const doc = fixture(false), seed = resolve(dir, 'seed.json'); saveJSON(seed, doc); await upload(page, seed); await apply(page);
    const bad = structuredClone(doc); bad.document_version = 1; const path = resolve(dir, 'wrong-v1.json'); saveJSON(path, bad);
    const before = await snap(page); await page.getByTestId('doc-file').setInputFiles(path); await expect(page.getByTestId('doc-error')).toBeVisible();
    same(before.polarizedTwoPath.candidate, (await snap(page)).polarizedTwoPath.candidate);
    await page.getByTestId('pt-edit-source-waist_z_m').fill('-'); await page.getByTestId('pt-edit-source-waist_z_m').blur();
    await page.getByTestId('doc-title').fill('保留 metadata 😀'); await page.getByTestId('doc-notes').fill('無效文字也是草稿的一部分。');
    const invalid = await snap(page), requests: string[] = []; page.on('request', r => { if (r.method() === 'POST') requests.push(r.url()); });
    await page.locator('.release-panel summary').click(); await page.getByTestId('release-results').click(); await page.getByTestId('release-results').click();
    const released = await snap(page); same(invalid.polarizedTwoPath.candidate, released.polarizedTwoPath.candidate);
    expect(released.polarizedTwoPath.invalidEdits).toEqual(invalid.polarizedTwoPath.invalidEdits); expect(released.documents).toEqual(invalid.documents);
    await expect(page.getByTestId('pt-edit-source-waist_z_m')).toHaveValue('-'); expect(requests).toEqual([]);
    saveJSON(resolve(dir, 'outcome.json'), { mismatchRejected: true, invalid, released, requests });
  } finally { await context.close(); }
});
