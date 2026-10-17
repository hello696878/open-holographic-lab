import { describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { R03_PHASE_DISPLAY_BYTES, phaseColor, prepareR03Display, r03OwnedResults } from '../src/r03_fig2a_display';
import { createR03Apparatus } from '../src/r03_fig2a_apparatus';
import { R03_DEFAULT, type R03Result } from '../src/r03_fig2a_contracts';
function result(): R03Result { return { requestId: 'display-only-fixture', experimentSha256: 'a'.repeat(64), experiment: { ...R03_DEFAULT },
  phase: { shape: [16, 16], order: 'C', unwrapped: new Float64Array(256), wrapped: Float64Array.from({ length: 256 }, (_, i) => i / 256 * 2 * Math.PI) },
  stages: [], population: { infinite_gaussian_degree_of_polarization: null, assumption: 'Display fixture only.' }, provenance: {}, limitations: [] }; }
function canvas(failed = false): HTMLCanvasElement { return { width: 0, height: 0, dataset: {}, setAttribute() {}, getContext() { return failed ? null : {
  putImageData() {}, fillRect() {}, fillText() {}, set fillStyle(_v: string) {}, set font(_v: string) {}, set textAlign(_v: string) {} }; } } as unknown as HTMLCanvasElement; }
describe('phase identity, display ownership and original apparatus', () => {
  it('maps exact known phase endpoints without using RNG, rescaling samples or clamping', () => {
    expect(phaseColor(0)).toEqual([107, 85, 171]); expect(phaseColor(Math.PI)).toEqual([204, 193, 99]);
    expect(phaseColor(2 * Math.PI), 'A_MODULO_ROUNDOFF_ENDPOINT').toEqual(phaseColor(0));
    for (const value of [-1e-20, 2 * Math.PI + 1e-12, Infinity, NaN]) expect(() => phaseColor(value)).toThrow();
  });
  it('uses all 256 response samples in row-major orientation; one canvas/texture share one RGBA source', () => {
    vi.stubGlobal('ImageData', class { constructor(readonly data: Uint8ClampedArray) {} });
    try { const raw = result(), before = raw.phase.wrapped.slice(), display = prepareR03Display(raw, { canvas: () => canvas() });
      expect(display.rgba.slice(0, 4)).toEqual(new Uint8Array([107, 85, 171, 255]));
      expect(Array.from(display.rgba.slice(4 * 128, 4 * 128 + 3)),'A_MASK_ROW_ORDER').toEqual([204, 193, 99]);
      expect(display.texture.image.data).toBe(display.rgba); expect(display.texture.flipY).toBe(true); expect(display.texture.minFilter).toBe(THREE.NearestFilter);
      expect(display.canvas.dataset.requestId).toBe(raw.requestId); expect(display.ownedBytes).toBe(R03_PHASE_DISPLAY_BYTES); expect(raw.phase.wrapped).toEqual(before);
      const disposed = vi.fn(); display.texture.addEventListener('dispose', disposed); display.dispose(); display.dispose(); expect(disposed).toHaveBeenCalledOnce(); expect(display.canvas.width).toBe(0);
    } finally { vi.unstubAllGlobals(); }
  });
  it('cleans partial textures and canvases on a late display failure', () => {
    const spy = vi.fn(), c = canvas(true); expect(() => prepareR03Display(result(), { canvas: () => c, texture(data) { const texture = new THREE.DataTexture(data, 16, 16); texture.addEventListener('dispose', spy); return texture; } })).toThrow('preparation');
    expect(spy, 'A_DISPLAY_ROLLBACK').toHaveBeenCalledOnce(); expect(c.width).toBe(0);
  });
  it('counts actual buffer aliases once, includes both old/new preparation owners and releases explicitly', () => {
    const first = result(), second = result(); expect(r03OwnedResults([first, first, null])).toBe(4096 + 16384);
    expect(r03OwnedResults([first, second])).toBe(2 * (4096 + 16384)); expect(r03OwnedResults([])).toBe(0);
  });
  it('builds recognizable mounted geometry with bounded owned buffers and selectable functional components', () => {
    vi.stubGlobal('document', { createElement: () => canvas() });
    try { const apparatus = createR03Apparatus(); expect(apparatus.ownedBytes).toBeLessThanOrEqual(512 * 1024); expect(apparatus.geometryCount).toBeGreaterThan(12);
      expect(apparatus.snapshot()).toMatchObject({ componentCount: 7, computedRays: false, propagatedFieldSections: false, functionalGuides: true });
      apparatus.select('hwp'); expect(apparatus.snapshot()).toMatchObject({ selected: 'hwp' }); apparatus.dispose(); apparatus.dispose(); expect(apparatus.group.children).toHaveLength(0);
    } finally { vi.unstubAllGlobals(); }
  });
});
