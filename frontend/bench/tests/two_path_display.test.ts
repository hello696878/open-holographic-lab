import { describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { automaticDualColorLimits, createArrayDetectorTexture, intensityRGBA, prepareDualCanvases, prepareDualTextures } from '../src/detector';
import { detectorEdges, pixelCenterUV, pixelCoordinates, pixelFromUV } from '../src/mapping';
import { countedResultBytes, estimateDualOperationBytes, OWNED_PERSISTENT_BUDGET_BYTES, OWNED_TRANSIENT_BUDGET_BYTES, sweepPlotPoints } from '../src/phase_sweep';
import { BenchScene } from '../src/scene';
import { SWEEP_PHASES_RAD, type DecodedTwoPathResult, type DecodedTwoPathSweep } from '../src/two_path_contracts';

function fixture(ny = 3, nx = 4): DecodedTwoPathResult {
  const a = Array.from({ length: ny * nx }, (_, i) => 10 * (Math.floor(i / nx) + 1) + i % nx + 1);
  const b = a.map(value => value + 90); const grid = { ny, nx, dy: 5e-6, dx: 2e-6 };
  return { requestId: 'fixture', experimentSha256: 'a'.repeat(64),
    experiment: { wavelength_m: 633e-9, grid, source: { kind: 'uniform', amplitude: 1, phase_rad: 0 },
      two_arm_spec: { arm_0_distance_m: .002, arm_1_distance_m: .003, relative_phase_rad: .37 } },
    ports: [{ id: 'port_0', intensity: new Float64Array(a), intensityMax: a.at(-1)! },
      { id: 'port_1', intensity: new Float64Array(b), intensityMax: b.at(-1)! }],
    x: new Float64Array(Array.from({ length: nx }, (_, c) => (c - Math.floor(nx / 2)) * grid.dx)),
    y: new Float64Array(Array.from({ length: ny }, (_, r) => (r - Math.floor(ny / 2)) * grid.dy)),
    norms: { inputs: [4, 0], split: [2, 2], propagated: [2, 2], combiner: [2, 2], outputs: [3, 1] },
    diagnostics: { inputs_total: 4, split_total: 4, propagated_total: 4, combiner_total: 4, outputs_total: 4,
      split_delta: 0, propagation_delta: 0, phase_delta: 0, recombination_delta: 0, total_delta: 0,
      output_fractions: [.75, .25], total_output_ratio: 1 } };
}
describe('ordered dual detector display and accounted ownership', () => {
  it.each([[3, 4], [2, 5]])('maps every distinct port of %sx%s without a reflection/column swap', (ny, nx) => {
    const result = fixture(ny, nx); const pair = prepareDualTextures(result, { min: 0, max: 255 });
    result.ports.forEach((port, index) => {
      const display = pair.textures[index].image.data as Uint8Array;
      for (let row = 0; row < ny; row++) for (let column = 0; column < nx; column++) {
        expect(display[4 * ((ny - 1 - row) * nx + column)]).toBe(port.intensity[row * nx + column]);
        expect(pixelFromUV(result.experiment.grid, ...Object.values(pixelCenterUV(result.experiment.grid, row, column)) as [number, number])).toEqual({ row, column });
        expect(pixelCoordinates(result.experiment.grid, row, column)).toEqual({ x_m: result.x[column], y_m: result.y[row] });
      }
      const edge = detectorEdges(result.experiment.grid);
      // SI pitch products and independent integer-pitch ratio group binary64 differently.
      // Measured discrepancies <=2.220446049250313e-16; rtol=0, atol=4*epsilon.
      expect(Math.abs(edge.width / edge.height - nx * 2 / (ny * 5))).toBeLessThanOrEqual(4 * Number.EPSILON);
      expect(pair.textures[index].flipY).toBe(false); expect(pair.textures[index].magFilter).toBe(THREE.NearestFilter);
      expect(pair.textures[index].colorSpace).toBe(THREE.SRGBColorSpace); expect(pair.textures[index].generateMipmaps).toBe(false);
    });
    pair.dispose();
  });
  it('explicit joint automatic limits and unchanged raw values prevent independent port normalization', () => {
    const result = fixture(); const before = result.ports.map(port => new Uint8Array(port.intensity.buffer).slice());
    const range = automaticDualColorLimits(result); expect(range, 'SHARED_RANGE_DETECTED').toEqual({ min: 0, max: 124 });
    const pair = prepareDualTextures(result, range);
    expect((pair.textures[0].image.data as Uint8Array)[4 * 3], 'SHARED_RANGE_DETECTED').toBe(Math.round(34 / 124 * 255));
    expect((pair.textures[1].image.data as Uint8Array)[4 * 3]).toBe(255);
    result.ports.forEach((port, i) => expect(new Uint8Array(port.intensity.buffer)).toEqual(before[i])); pair.dispose();
  });
  it('dark both outputs remain raw zero while tiny residuals/subfloat32 values survive readout', () => {
    const result = fixture(1, 2); result.ports[0].intensity.fill(0); result.ports[1].intensity.fill(0);
    const dark = { ...result, ports: [{ ...result.ports[0], intensityMax: 0 }, { ...result.ports[1], intensityMax: 0 }] } as DecodedTwoPathResult;
    expect(automaticDualColorLimits(dark)).toEqual({ min: 0, max: 1 }); const pair = prepareDualTextures(dark, automaticDualColorLimits(dark));
    expect([...(pair.textures[0].image.data as Uint8Array)]).toEqual([0, 0, 0, 255, 0, 0, 0, 255]); pair.dispose();
    const original = new Float64Array([1e-300, 1 + 2 ** -50]); intensityRGBA(original, 1, 2, { min: 0, max: 10 });
    expect(original[0]).toBe(1e-300); expect(original[1]).toBe(1 + 2 ** -50);
  });
  it('second texture preparation failure disposes first before either can be published', () => {
    const result = fixture(); const first = createArrayDetectorTexture(result.ports[0].intensity, result.experiment.grid, { min: 0, max: 255 });
    const disposed = vi.fn(); first.addEventListener('dispose', disposed); let calls = 0; let published = null;
    const factory = () => { calls++; if (calls === 2) throw new Error('injected second texture failure'); return first; };
    expect(() => { published = prepareDualTextures(result, { min: 0, max: 255 }, factory); }).toThrow('second texture');
    expect(disposed, 'ATOMIC_SECOND_TEXTURE_DETECTED').toHaveBeenCalledOnce(); expect(published).toBeNull();
  });
  it('detachment clears both real scene materials and releases their separately owned textures', () => {
    // Exercise the actual public scene detachment method on owned Three resources;
    // no WebGL/browser or alternate implementation is needed for this lifetime unit.
    const result = fixture(); const pair = prepareDualTextures(result, { min: 0, max: 255 });
    const disposed = [vi.fn(), vi.fn()]; pair.textures.forEach((texture, i) => texture.addEventListener('dispose', disposed[i]));
    const meshes = pair.textures.map(texture => new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: texture })));
    const scene = Object.create(BenchScene.prototype) as BenchScene;
    const owned = new Set(pair.textures);
    Object.assign(scene, { dualTextures: pair.textures, dualResult: result, dualDetectors: meshes, dualColorKey: '0:255', textures: owned });
    scene.detachDualResult();
    expect(meshes[0].material.map, 'BOTH_TEXTURES_INVALIDATED').toBeNull();
    expect(meshes[1].material.map, 'BOTH_TEXTURES_INVALIDATED').toBeNull();
    expect(owned.size).toBe(0); disposed.forEach(spy => expect(spy).toHaveBeenCalledOnce());
    scene.detachDualResult(); disposed.forEach(spy => expect(spy).toHaveBeenCalledOnce());
    meshes.forEach(mesh => { mesh.geometry.dispose(); mesh.material.dispose(); });
  });
  it('second canvas preparation failure explicitly resets both detached backing stores', () => {
    const canvases: { width: number; height: number; dataset: Record<string, string>; setAttribute: () => void; getContext: () => unknown }[] = [];
    const fakeDocument = { createElement() {
      const index = canvases.length;
      const canvas = { width: 0, height: 0, dataset: {}, setAttribute() {}, getContext() {
        return index === 0 ? { putImageData() {} } : null;
      } };
      canvases.push(canvas); return canvas;
    } };
    try {
      vi.stubGlobal('document', fakeDocument); vi.stubGlobal('ImageData', class { constructor(readonly bytes: Uint8ClampedArray) {} });
      expect(() => prepareDualCanvases(fixture(), { min: 0, max: 255 })).toThrow('1');
      expect(canvases).toHaveLength(2); expect(canvases.map(canvas => [canvas.width, canvas.height]), 'ATOMIC_SECOND_CANVAS_DETECTED').toEqual([[0, 0], [0, 0]]);
    } finally { vi.unstubAllGlobals(); }
  });
  it('Float32-unusable derived schematic geometry fails before prior resources are detached', () => {
    const result = fixture(); const invalid = { ...result.experiment, grid: { ...result.experiment.grid, dx: 1e34 } };
    // Its raw width still fits Float32; derived end*100 exceeds the rendering range.
    const width = invalid.grid.nx * invalid.grid.dx * 1000; expect(Number.isFinite(Math.fround(width))).toBe(true);
    const scene = Object.create(BenchScene.prototype) as BenchScene;
    const old = new THREE.Group(); const detach = vi.fn(), update = vi.fn(), dispose = vi.fn();
    Object.assign(scene, { mode: 'sequential', twoPathExperiment: null, bench: old, rail: new THREE.Group(),
      updateResult: update, detachDualResult: detach, disposeGroup: dispose });
    expect(() => scene.updateTwoPathExperiment(invalid, 'source')).toThrow('3D');
    expect(update, 'SCHEMATIC_PREFLIGHT_DETECTED').not.toHaveBeenCalled(); expect(detach).not.toHaveBeenCalled(); expect(dispose).not.toHaveBeenCalled();
  });
  it('a pair is disposed once and repeated replacements own only its two active textures', () => {
    let active: ReturnType<typeof prepareDualTextures> | null = null; let created = 0; let disposed = 0;
    for (let i = 0; i < 20; i++) {
      const pair = prepareDualTextures(fixture(), { min: 0, max: 255 }, (values, grid, limits) => {
        const texture = createArrayDetectorTexture(values, grid, limits); created++;
        texture.addEventListener('dispose', () => { disposed++; }); return texture;
      });
      active?.dispose(); active = pair; expect(created - disposed).toBe(2);
    }
    active?.dispose(); active?.dispose(); expect(created).toBe(40); expect(disposed).toBe(40);
  });
  it('deduplicates scientific aliases and budgets the one recoverable preparation-failure exception', () => {
    const first = fixture(); const second = fixture();
    const expected = 8 * (2 * 3 * 4 + 3 + 4);
    expect(countedResultBytes(null, first, first, null)).toBe(expected);
    expect(countedResultBytes(null, first, second, null)).toBe(2 * expected);
    expect(2 * 4202496 + 2105344 + 2 * 2097152 + 128 * 1024).toBeLessThan(OWNED_PERSISTENT_BUDGET_BYTES);
  });
  it('bounds route buffers and presentation lifetimes at512 without adding disjoint phases together', () => {
    const estimate = estimateDualOperationBytes({ nx: 512, ny: 512, dx: 4e-6, dy: 4e-6 }, OWNED_PERSISTENT_BUDGET_BYTES);
    expect(estimate.payloadBytes).toBe(4202496); expect(estimate.maxFrameBytes).toBe(4218896);
    expect(estimate.transportPeakBytes).toBe(OWNED_PERSISTENT_BUDGET_BYTES + 2 * 4218896);
    expect(estimate.decodePeakBytes).toBe(OWNED_PERSISTENT_BUDGET_BYTES + 4218896 + 4202496);
    expect(estimate.preparationPeakBytes).toBe(OWNED_PERSISTENT_BUDGET_BYTES + 4202496 + 24 * 512 * 512);
    expect(estimate.peakOwnedBytes).toBe(27271168); expect(estimate.peakOwnedBytes).toBeLessThan(OWNED_TRANSIENT_BUDGET_BYTES);
    expect(() => estimateDualOperationBytes({ nx: 513, ny: 2, dx: 1, dy: 1 })).toThrow();
    expect(() => estimateDualOperationBytes({ nx: 1, ny: 1, dx: 1, dy: 1 }, -1)).toThrow();
  });
  it('plots actual scalar markers without analytic substitution, normalization or filling missing points', () => {
    const sweep = { requestId: 'actual', phasesRad: SWEEP_PHASES_RAD, status: 'failed', completedCount: 2,
      rows: [{ index: 0, phase_rad: 0, output_fractions: [.231, .077] },
        { index: 1, phase_rad: SWEEP_PHASES_RAD[1], output_fractions: [null, null] }] } as unknown as DecodedTwoPathSweep;
    const points = sweepPlotPoints(sweep, 0);
    expect(points).toHaveLength(2); expect(points[0].value).toBe(.231); expect(points[0].y).toBe(1 - .231); expect(points[1].y).toBeNull();
    expect(sweepPlotPoints(sweep, 1)[0].value).toBe(.077); expect(points).not.toHaveLength(17);
  });
});
