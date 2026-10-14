import { describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { createArrayDetectorTexture, intensityRGBA } from '../src/detector';
import { pixelCoordinates, pixelFromUV, pixelCenterUV } from '../src/mapping';
import { assertOwnedBudgets } from '../src/polarization_display';
import { OWNED_PERSISTENT_BUDGET_BYTES, OWNED_TRANSIENT_BUDGET_BYTES } from '../src/phase_sweep';
import { polarizedTwoPathPreset } from '../src/polarized_two_path_presets';
import { automaticPolarizedTwoPathColorLimits, estimatePolarizedTwoPathOperation, ownedScientificBytes4,
  preparePolarizedTwoPathResources } from '../src/polarized_two_path_display';
import type { DecodedPolarizedTwoPathResult } from '../src/polarized_two_path_contracts';
function fixture(enabled = true): DecodedPolarizedTwoPathResult {
  const experiment = polarizedTwoPathPreset(enabled ? 'orthogonal_analyzed' : 'identical'); experiment.grid = { ny: 3, nx: 4, dy: 5e-6, dx: 2e-6 };
  const ports = (start: number) => [0, 1].map(i => ({ id: `port_${i}`, intensity: new Float64Array(Array.from({ length: 12 }, (_, p) => (start + i) * (p + 1))), intensityMax: 12 * (start + i) }));
  return { requestId: 'fixture', experimentSha256: 'a'.repeat(64), experiment, rawPorts: ports(1), analyzedPorts: enabled ? ports(3) : null,
    x: new Float64Array([-4e-6, -2e-6, 0, 2e-6]), y: new Float64Array([-5e-6, 0, 5e-6]), intensityMax: enabled ? [12, 24, 36, 48] : [12, 24],
    norms: {}, diagnostics: {}, analysis: { enabled, axis_angle_rad: experiment.analyzer.axis_angle_rad } } as unknown as DecodedPolarizedTwoPathResult;
}
function canvases(fail = -1) { const values: any[] = []; return { values, factory() { const index = values.length;
  const canvas = { width: 0, height: 0, dataset: {}, setAttribute() {}, getContext() { return index === fail ? null : { putImageData() {} }; } }; values.push(canvas); return canvas as unknown as HTMLCanvasElement; } }; }
describe('joint V2g display and fixed app-owned accounting', () => {
  it.each([false, true])('prepares all %s roles before publication with identical scales and untouched float64 data', enabled => {
    const result = fixture(enabled), seen: number[] = [], limits: { min: number; max: number }[] = [], source = canvases();
    const before = result.rawPorts[0].intensity.slice(); vi.stubGlobal('ImageData', class { constructor(readonly data: Uint8ClampedArray) {} });
    try { const resources = preparePolarizedTwoPathResources(result, { min: 0, max: 48 }, { canvas: source.factory,
      texture(intensity, grid, range) { seen.push(intensity[0]); limits.push({ ...range }); return createArrayDetectorTexture(intensity, grid, range); } });
      expect(seen, 'PT_DISPLAY_ROLE_ORDER').toEqual(enabled ? [1, 2, 3, 4] : [1, 2]); expect(limits).toEqual(Array(enabled ? 4 : 2).fill({ min: 0, max: 48 }));
      expect(resources.ownedBytes).toBe((enabled ? 4 : 2) * 12 * 8); expect(result.rawPorts[0].intensity).toEqual(before);
      expect(resources.canvases.map(canvas => canvas.dataset.testid)).toEqual(enabled ? ['pt-intensity-0', 'pt-intensity-1', 'pt-intensity-2', 'pt-intensity-3'] : ['pt-intensity-0', 'pt-intensity-1']);
      resources.dispose(); resources.dispose(); expect(source.values.every(canvas => canvas.width === 0 && canvas.height === 0)).toBe(true);
    } finally { vi.unstubAllGlobals(); }
  });
  it.each([0, 1, 2, 3])('cleans every partial texture when texture %s fails', failed => {
    const created: THREE.DataTexture[] = [], disposals: ReturnType<typeof vi.fn>[] = [];
    expect(() => preparePolarizedTwoPathResources(fixture(), { min: 0, max: 48 }, { texture(intensity, grid, range) {
      if (created.length === failed) throw new Error('later texture'); const texture = createArrayDetectorTexture(intensity, grid, range), dispose = vi.fn();
      texture.addEventListener('dispose', dispose); created.push(texture); disposals.push(dispose); return texture; } })).toThrow('later texture');
    expect(created).toHaveLength(failed); disposals.forEach(spy => expect(spy, 'PT_PARTIAL_DISPLAY_CLEANUP').toHaveBeenCalledOnce());
  });
  it.each([0, 1, 2, 3])('cleans all textures and already-created canvases when canvas %s fails', failed => {
    const source = canvases(failed), disposals: ReturnType<typeof vi.fn>[] = []; vi.stubGlobal('ImageData', class {});
    try { expect(() => preparePolarizedTwoPathResources(fixture(), { min: 0, max: 48 }, { canvas: source.factory,
      texture(intensity, grid, range) { const texture = createArrayDetectorTexture(intensity, grid, range), dispose = vi.fn(); texture.addEventListener('dispose', dispose); disposals.push(dispose); return texture; } })).toThrow('preparation failed');
      expect(disposals).toHaveLength(4); disposals.forEach(spy => expect(spy, 'PT_PARTIAL_DISPLAY_CLEANUP').toHaveBeenCalledOnce());
      expect(source.values.every(canvas => canvas.width === 0 && canvas.height === 0)).toBe(true);
    } finally { vi.unstubAllGlobals(); }
  });
  it('idempotently releases externally detached textures without losing the remaining pair', () => {
    const source = canvases(); vi.stubGlobal('ImageData', class {});
    try { const resources = preparePolarizedTwoPathResources(fixture(), { min: 0, max: 48 }, { canvas: source.factory }), spies = resources.textures.map(() => vi.fn());
      resources.textures.forEach((texture, i) => texture.addEventListener('dispose', spies[i])); resources.textures[2].dispose(); resources.dispose(); resources.dispose();
      spies.forEach(spy => expect(spy).toHaveBeenCalledOnce());
    } finally { vi.unstubAllGlobals(); }
  });
  it('uses one explicit automatic maximum over raw and analyzed roles, retaining original weak readouts', () => {
    const result = fixture(); result.rawPorts[0].intensity[0] = 2.5e-19;
    expect(automaticPolarizedTwoPathColorLimits(result), 'PT_JOINT_SCALE').toEqual({ min: 0, max: 48 });
    expect(intensityRGBA(result.rawPorts[0].intensity, 3, 4, { min: 0, max: 48 })[0]).toBe(0);
    expect(result.rawPorts[0].intensity[0], 'PT_ORIGINAL_WEAK_READOUT').toBe(2.5e-19);
    for (const [row, column] of [[0, 0], [2, 3], [1, 2]]) { const uv = pixelCenterUV(result.experiment.grid, row, column), picked = pixelFromUV(result.experiment.grid, uv.u, uv.v);
      expect(picked).toEqual({ row, column }); expect(pixelCoordinates(result.experiment.grid, row, column)).toEqual({ x_m: result.x[column], y_m: result.y[row] }); }
  });
  it('derives actual conditional frame and phase-wise maxima without changing fixed budgets', () => {
    const grid = { nx: 128, ny: 128, dx: 4e-6, dy: 4e-6 }, disabled = estimatePolarizedTwoPathOperation(grid, false, 0), enabled = estimatePolarizedTwoPathOperation(grid, true, 0);
    expect(disabled.payloadBytes).toBe(264192); expect(disabled.frameBytes).toBe(280592); expect(disabled.persistentProjection).toBe(690176); expect(disabled.peakOwnedBytes).toBe(821248);
    expect(enabled.payloadBytes).toBe(526336); expect(enabled.frameBytes).toBe(542736); expect(enabled.persistentProjection).toBe(1214464);
    expect(enabled.transportPeak).toBe(1085472); expect(enabled.decodePeak).toBe(1167376); expect(enabled.preparationPeak).toBe(1345536);
    expect(OWNED_PERSISTENT_BUDGET_BYTES).toBe(16 * 1024 ** 2); expect(OWNED_TRANSIENT_BUDGET_BYTES).toBe(32 * 1024 ** 2);
    expect(() => assertOwnedBudgets(OWNED_PERSISTENT_BUDGET_BYTES + enabled.persistentProjection, enabled.peakOwnedBytes), 'PT_FIXED_BUDGET_REJECTION').toThrow('budget');
    expect(estimatePolarizedTwoPathOperation(grid, true, 100, 'sweep').persistentProjection).toBe(131172);
    expect(estimatePolarizedTwoPathOperation(grid, false, 100, 'sweep').peakOwnedBytes).toBe(524388);
  });
  it('deduplicates numerical buffers and metadata aliases across result/recovery references', () => {
    const result = fixture(), owners = { sequential: [], dual: [], polarization: [], polarizedTwoPath: [result, result], sweeps: [] };
    const buffers = new Set([result.x.buffer, result.y.buffer, ...result.rawPorts.map(p => p.intensity.buffer), ...result.analyzedPorts!.map(p => p.intensity.buffer)]);
    expect(ownedScientificBytes4(owners), 'PT_OWNERSHIP_ALIAS_COUNT').toBe([...buffers].reduce((n, b) => n + b.byteLength, 0) + 32768);
    expect(ownedScientificBytes4({ ...owners, polarizedTwoPath: [] }), 'PT_RELEASE_BUFFER_OWNERS').toBe(0);
  });
});
