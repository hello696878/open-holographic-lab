/** Actual production copy audit. User-authored Unicode is data, not interface copy. */
import { test, expect, type Page } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve('../..'), evidence = resolve(root, process.env.ENGLISH_EVIDENCE_DIR ?? 'runs/w1_1_english_completion_01/english_browser');
const snapshot = (page: Page): Promise<any> => page.evaluate(() => window.__benchDebug.snapshot());
const scientific = (url: string): boolean => /\/api\/(?:w1|v1|v2b|v2d|v2g)\/(?:simulate|sweep)$/.test(new URL(url).pathname) || new URL(url).pathname === '/api/research/r03-fig2a/simulate';
function save(name: string, value: unknown): void { mkdirSync(evidence, { recursive: true }); writeFileSync(resolve(evidence, name + '.json'), JSON.stringify(value, null, 2), { flag: 'wx' }); }
async function open(page: Page): Promise<string[]> {
  const calls: string[] = [];
  await page.route('**/*', route => new URL(route.request().url()).origin === 'http://127.0.0.1:8510' ? route.continue() : route.abort('blockedbyclient'));
  page.on('request', request => { if (request.method() === 'POST' && scientific(request.url())) calls.push(new URL(request.url()).pathname); });
  await page.goto('/'); await expect(page.getByTestId('simulate')).toBeEnabled();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en'); await expect(page).toHaveTitle('Open Holographic Lab — Optical Experiments');
  await expect(page.getByTestId('mode').locator('option')).toHaveText(['Sequential Optics', 'Two-Path Interference', 'Jones Polarization', 'Polarized Interference']);
  await expect(page.getByTestId('ordinary-workspace')).toHaveText('Optical Experiments');
  await expect(page.getByTestId('research-workspace')).toHaveText('Ideal Statistical Polarization');
  expect(calls).toEqual([]); return calls;
}
async function audit(page: Page, name: string): Promise<void> {
  const findings = await page.evaluate(() => {
    const han = /\p{Script=Han}/u, failures: { kind: string; text: string; element: string }[] = [];
    const userData = '[data-testid="doc-preview-text"]';
    const visible = (element: Element): boolean => !!element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden';
    const add = (kind: string, text: string, element: Element): void => { if (han.test(text)) failures.push({ kind, text, element: element.id || element.getAttribute('data-testid') || element.tagName }); };
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode, parent = node.parentElement;
      // Input values and this raw settings preview contain user data. Fixed preview
      // labels are independently audited as production source literals.
      if (parent && visible(parent) && !parent.closest(userData) && !parent.closest('script,style,textarea')) add('visible text', node.textContent ?? '', parent);
    }
    for (const element of document.querySelectorAll('*')) if (visible(element)) {
      for (const attribute of ['aria-label', 'aria-description', 'title', 'placeholder', 'alt']) add(attribute, element.getAttribute(attribute) ?? '', element);
      for (const pseudo of ['::before', '::after']) { const content = getComputedStyle(element, pseudo).content; if (content && content !== 'none') add(pseudo, content, element); }
    }
    return failures;
  });
  save(name + '_copy', findings); expect(findings, `Untranslated developer-authored text in ${name}`).toEqual([]);
}
async function image(page: Page, name: string): Promise<void> { mkdirSync(evidence, { recursive: true }); await page.screenshot({ path: resolve(evidence, name + '.png'), fullPage: false }); }

for (const [mode, actor, button, endpoint] of [
  ['sequential', '', 'simulate', '/api/v1/simulate'], ['two_path', 'twoPath', 'tp-simulate', '/api/v2b/simulate'],
  ['polarization', 'polarization', 'pl-simulate', '/api/v2d/simulate'], ['polarized_two_path', 'polarizedTwoPath', 'pt-simulate', '/api/v2g/simulate'],
] as const) test(`English ${mode} navigation, calculated controls and release preserve scientific submission`, async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 }); const calls = await open(page);
  await page.getByTestId('mode').selectOption(mode); await expect(page.getByTestId(button)).toBeEnabled();
  await audit(page, mode + '_ready'); const submitted = page.waitForResponse(response => new URL(response.url()).pathname === endpoint && response.request().method() === 'POST');
  await expect(page.getByTestId(button)).toHaveAccessibleName('Simulate'); await page.getByTestId(button).click();
  const response = await submitted; expect(response.status()).toBe(200); const request = JSON.parse(response.request().postData()!);
  await expect.poll(async () => { const s = await snapshot(page); return (actor ? s[actor] : s).currentResult?.requestId; }).toBe(request.request_id);
  expect(calls).toEqual([endpoint]); await audit(page, mode + '_result'); await image(page, mode + '_1440x900');
  const before = await snapshot(page); expect(before.ownedMemory.retainedBytes).toBeLessThanOrEqual(16 * 1024 * 1024);
  await page.locator('.release-panel > summary').click(); await expect(page.getByTestId('release-results')).toHaveAccessibleName('Release Results');
  await page.getByTestId('release-results').click(); await expect(page.getByTestId('release-status')).toContainText('released across all modes');
  const after = await snapshot(page); expect((actor ? after[actor] : after).currentResult).toBeNull(); expect(calls).toEqual([endpoint]);
  await audit(page, mode + '_released'); save(mode + '_identity', { request, before, after, calls });
});

test('English research panels and full precision preserve the one finite realization', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 }); const calls = await open(page);
  await page.getByTestId('research-workspace').click(); await expect(page.getByTestId('r03-compute')).toBeEnabled();
  await audit(page, 'research_ready'); const pending = page.waitForResponse(response => new URL(response.url()).pathname === '/api/research/r03-fig2a/simulate');
  await page.getByTestId('r03-compute').click(); const response = await pending; expect(response.status()).toBe(200); const body = await response.json();
  await expect.poll(async () => (await snapshot(page)).idealPolarization.currentResult?.requestId).toBe(body.request_id);
  const before = (await snapshot(page)).idealPolarization.currentResult;
  for (const name of ['summary', 'phase', 'measurements', 'evidence']) {
    await page.getByTestId('r03-tab-' + name).click(); await audit(page, 'research_' + name);
    const tabs = await page.locator('.r03-tabs button').evaluateAll(buttons => buttons.map(button => ({ text: button.textContent, width: button.clientWidth, scrollWidth: button.scrollWidth })));
    for (const tab of tabs) expect(tab.scrollWidth, `Complete English tab label: ${tab.text}`).toBeLessThanOrEqual(tab.width + 1);
  }
  await page.getByTestId('r03-tab-measurements').click(); await page.getByTestId('r03-full-precision').check();
  await audit(page, 'research_full_precision'); await image(page, 'research_1440x900');
  expect((await snapshot(page)).idealPolarization.currentResult).toEqual(before); expect(calls).toEqual(['/api/research/r03-fig2a/simulate']);
});

test('English W1 panels and validation errors make no implicit scientific requests', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 }); const calls = await open(page);
  await page.getByTestId('w1-view').click(); await page.getByTestId('w1-load-example').click(); await expect(page.getByTestId('simulate')).toBeEnabled();
  await audit(page, 'w1_ready'); const pending = page.waitForResponse(response => new URL(response.url()).pathname === '/api/w1/simulate');
  await page.getByTestId('simulate').click(); const response = await pending; expect(response.status()).toBe(200); const request = JSON.parse(response.request().postData()!);
  await expect.poll(async () => (await snapshot(page)).waveField.currentResult?.requestId).toBe(request.request_id);
  const before = (await snapshot(page)).waveField.currentResult;
  for (const name of ['profile', 'display', 'evidence', 'parameters']) { await page.getByTestId('w1-tab-' + name).click(); await audit(page, 'w1_' + name); }
  await page.getByTestId('w1-tab-profile').click(); await image(page, 'w1_1440x900');
  expect((await snapshot(page)).waveField.currentResult).toEqual(before); expect(calls).toEqual(['/api/w1/simulate']);
  await page.getByTestId('w1-tab-display').click(); await page.getByTestId('w1-range-min').fill('4'); await page.getByTestId('w1-range-max').fill('3');
  await page.getByTestId('w1-apply-range').click(); await expect(page.getByTestId('w1-error')).toBeVisible();
  await expect(page.getByTestId('w1-error')).toContainText('Color limits must be finite and satisfy 0 ≤ minimum < maximum.'); await audit(page, 'w1_specific_display_error');
  expect(calls).toEqual(['/api/w1/simulate']);
});

test('English document controls preserve non-English user titles and notes byte for byte', async ({ page }) => {
  const calls = await open(page); await page.getByTestId('doc-toggle').click();
  const title = '使用者的實驗 — Ελληνικά', notes = '保留原始備註\nλ = 633 nm · 日本語';
  await page.getByTestId('doc-title').fill(title); await page.getByTestId('doc-notes').fill(notes);
  await page.getByTestId('doc-export').click(); await expect(page.getByTestId('doc-status')).toHaveText('Download Prepared');
  const pending = page.waitForEvent('download'); await page.getByTestId('doc-download').click(); const download = await pending;
  mkdirSync(evidence, { recursive: true }); const path = resolve(evidence, 'unicode_user_document.json'); await download.saveAs(path);
  const bytes = readFileSync(path), doc = JSON.parse(bytes.toString('utf8')); expect(doc.metadata.title).toBe(title); expect(doc.metadata.notes).toBe(notes);
  await page.getByTestId('doc-file').setInputFiles({ name: 'unicode-settings.json', mimeType: 'application/json', buffer: bytes });
  await expect(page.getByTestId('doc-status')).toHaveAttribute('data-status', 'preview'); await expect(page.getByTestId('doc-preview-text')).toContainText(title);
  await audit(page, 'unicode_user_preview'); await expect(page.getByTestId('doc-apply')).toHaveAccessibleName('Replace Settings and Apply');
  await page.getByTestId('doc-ack').check(); await page.getByTestId('doc-apply').click();
  await expect(page.getByTestId('doc-status')).toHaveText('Settings Restored; Simulation Not Run');
  await expect(page.getByTestId('doc-title')).toHaveValue(title); await expect(page.getByTestId('doc-notes')).toHaveValue(notes); expect(calls).toEqual([]);
  await audit(page, 'unicode_user_applied');
});
