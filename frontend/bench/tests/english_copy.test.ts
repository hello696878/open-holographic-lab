import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import ts from 'typescript';

const han = /\p{Script=Han}/u;
function untranslatedLiterals(source: string): string[] {
  const file = ts.createSourceFile('copy.ts', source, ts.ScriptTarget.Latest, true);
  const found: string[] = [];
  const visit = (node: ts.Node): void => {
    if ((ts.isStringLiteralLike(node) || ts.isTemplateHead(node) || ts.isTemplateMiddle(node) || ts.isTemplateTail(node)) && han.test(node.text)) {
      const line = file.getLineAndCharacterOfPosition(node.getStart(file)).line + 1;
      found.push(`${line}: ${node.text}`);
    }
    ts.forEachChild(node, visit);
  };
  visit(file); return found;
}

describe('sole supported product language: English', () => {
  it('audits every production TypeScript literal, including templates and escaped copy', () => {
    const root = resolve('src'), files = readdirSync(root).filter(name => name.endsWith('.ts'));
    expect(files.length).toBeGreaterThan(30);
    const failures = files.flatMap(name => untranslatedLiterals(readFileSync(resolve(root, name), 'utf8')).map(value => `${name}:${value}`));
    expect(failures, 'Developer-authored product strings must be English; user documents and Unicode test fixtures are not production-copy sources.').toEqual([]);
  });
  it('detects deliberate untranslated copy while ignoring source comments and mathematical symbols', () => {
    expect(untranslatedLiterals('// 中文 source comment\nconst note = "S₀ · µm · π";')).toEqual([]);
    expect(untranslatedLiterals('const label = "模擬";')).toHaveLength(1);
    expect(untranslatedLiterals('const label = "\\u6a21\\u64ec";')).toHaveLength(1);
    expect(untranslatedLiterals('const label = `計算 ${id} 完成`;')).toHaveLength(2);
  });
  it('uses actual English HTML language, title, description and generated CSS copy', () => {
    const html = readFileSync(resolve('index.html'), 'utf8'), css = readFileSync(resolve('src/styles.css'), 'utf8');
    expect(html).toMatch(/<html\s+lang="en">/);
    expect(html.match(/<title>(.*?)<\/title>/s)?.[1]).toBe('Open Holographic Lab — Optical Experiments');
    expect(html.match(/name="description"\s+content="([^"]+)"/)?.[1]).toContain('optical');
    expect(han.test(html)).toBe(false);
    const generated = [...css.matchAll(/content\s*:\s*(['"])(.*?)\1/gs)].map(match => match[2]);
    expect(generated.length).toBeGreaterThan(0); expect(generated.filter(text => han.test(text))).toEqual([]);
  });
});
