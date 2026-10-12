import { describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { intensityRGBA, createArrayDetectorTexture } from '../src/detector';
import { pixelCenterUV, pixelFromUV, pixelCoordinates } from '../src/mapping';
import { assertOwnedBudgets, estimateOwnedOperation, isDarkSample, ownedScientificBytes, PolarizationPlayback,
  preparePolarizationResources, prepareTrajectories, trajectoryMarker, validateDisplayScale } from '../src/polarization_display';
import { polarizationPreset } from '../src/polarization_presets';
import type { ComplexPair, DecodedPolarizationResult } from '../src/polarization_contracts';
import type { DecodedResult } from '../src/contracts';
import type { DecodedTwoPathResult } from '../src/two_path_contracts';
import { BenchScene } from '../src/scene';
function fixture(ny = 3, nx = 4): DecodedPolarizationResult {
  const experiment = polarizationPreset('qwp'); experiment.grid = { ny, nx, dy: 5e-6, dx: 2e-6 }; experiment.readout = { row: ny - 1, column: nx - 1 };
  const a = 1 / Math.sqrt(2), incident = { x: { re: a, im: 0 }, y: { re: a, im: 0 } }, final = { x: { re: a, im: 0 }, y: { re: 0, im: a } };
  return { requestId: 'fixture', experimentSha256: 'a'.repeat(64), experiment, orderedStageIds: ['input', 'w1'],
    readout: { ...experiment.readout, x_m: (nx - 1 - Math.floor(nx / 2)) * experiment.grid.dx, y_m: (ny - 1 - Math.floor(ny / 2)) * experiment.grid.dy },
    stages: [incident, final].map((sample, index) => ({ stage_id: index === 0 ? 'input' : 'w1', kind: index === 0 ? 'input' : 'linear_retarder',
      norm: 4, previous_norm: index === 0 ? null : 4, delta_norm: index === 0 ? null : 0, adjacent_transmission_ratio: index === 0 ? null : 1,
      incident_transmission_ratio: 1, sample })), incidentIntensity: new Float64Array(Array.from({ length: ny * nx }, (_, i) => i + 1)),
    finalIntensity: new Float64Array(Array.from({ length: ny * nx }, (_, i) => (i + 1) / 10)),
    x: new Float64Array(Array.from({ length: nx }, (_, c) => (c - Math.floor(nx / 2)) * experiment.grid.dx)),
    y: new Float64Array(Array.from({ length: ny }, (_, r) => (r - Math.floor(ny / 2)) * experiment.grid.dy)), intensityMax: [ny * nx, ny * nx / 10] };
}
function close(actual: number, expected: number, marker: string, atol = 2e-15): void { expect(Math.abs(actual - expected), marker).toBeLessThanOrEqual(atol); }
function canvasFactory(fail = -1): { factory: () => HTMLCanvasElement; canvases: any[] } {
  const canvases: any[] = [];
  return { canvases, factory() { const index = canvases.length; const canvas = { width: 0, height: 0, dataset: {}, setAttribute() {},
    getContext() { return index === fail ? null : { putImageData() {} }; } }; canvases.push(canvas); return canvas as unknown as HTMLCanvasElement; } };
}
describe('actual complex presentation and bounded resources', () => {
  it('preserves common phase at shared fixed tau with independent marker expectations', () => {
    const a = 1 / Math.sqrt(2), sample = { x: { re: a, im: 0 }, y: { re: 0, im: a } };
    const shifted = { x: { re: .5, im: .5 }, y: { re: -.5, im: .5 } };
    const originalMarker = trajectoryMarker(sample, 0), shiftedMarker = trajectoryMarker(shifted, 0);
    close(originalMarker.x, a, 'DISPLAY_COMMON_PHASE_FIXED_TAU'); close(originalMarker.y, 0, 'DISPLAY_COMMON_PHASE_FIXED_TAU');
    close(shiftedMarker.x, .5, 'DISPLAY_COMMON_PHASE_FIXED_TAU'); close(shiftedMarker.y, -.5, 'DISPLAY_COMMON_PHASE_FIXED_TAU');
    const phases = [0, Math.PI / 2, Math.PI, 3 * Math.PI / 2], expected = [[a, 0], [0, a], [-a, 0], [0, -a]];
    phases.forEach((tau, i) => { const marker = trajectoryMarker(sample, tau); close(marker.x, expected[i][0], 'IMAGINARY_COMPONENT_DETECTED'); close(marker.y, expected[i][1], 'IMAGINARY_COMPONENT_DETECTED'); });
  });
  it('classifies exact dark from all complex parts while nonzero tiny intensity-underflow samples remain nonzero', () => {
    const dark = { x: { re: -0, im: 0 }, y: { re: 0, im: 0 } }, tiny = { x: { re: 1e-200, im: 0 }, y: { re: 0, im: 0 } };
    expect(isDarkSample(dark)).toBe(true); expect(1e-200 * 1e-200).toBe(0);
    expect(isDarkSample(tiny), 'DISPLAY_NONZERO_TINY_NOT_DARK').toBe(false);
    const result = fixture(), sample = { ...result, stages: [{ ...result.stages[0], sample: tiny }], incidentIntensity: new Float64Array([1, 0]) };
    const trajectory = prepareTrajectories(sample)[0]; expect(trajectory.dark, 'DISPLAY_NONZERO_TINY_NOT_DARK').toBe(false);
    expect(trajectory.displayLimited).toBe(true); expect(trajectory.sample.x.re).toBe(1e-200); expect(trajectory.points[0]).toBe(1e-200);
  });
  it('uses equal shared scales and retains loss rather than normalizing each trajectory or intensity', () => {
    const result = fixture(), incident = { x: { re: 1, im: 0 }, y: { re: 0, im: 0 } }, lost = { x: { re: .5, im: 0 }, y: { re: 0, im: 0 } };
    const trajectories = prepareTrajectories({ ...result, stages: [{ ...result.stages[0], sample: incident }, { ...result.stages[1], sample: lost }] });
    expect(trajectories[0].points[0], 'POLARIZER_LOSS_SHARED_SCALE').toBe(1); expect(trajectories[1].points[0], 'POLARIZER_LOSS_SHARED_SCALE').toBe(.5);
    const rgba = intensityRGBA(new Float64Array([1, .25]), 1, 2, { min: 0, max: 1 }); expect(rgba[0]).toBe(255); expect(rgba[4], 'POLARIZER_LOSS_SHARED_SCALE').toBe(64);
    const asymmetric: ComplexPair = { x: { re: 2, im: 1 }, y: { re: -.5, im: 3 } };
    const marker = trajectoryMarker(asymmetric, Math.PI / 2); close(marker.x, 1, 'COMPONENT_SWAP_DETECTED'); close(marker.y, 3, 'COMPONENT_SWAP_DETECTED');
  });
  it('prepares actual paired resources with one declared shared intensity range and unchanged raw values', () => {
    const result = fixture(), before = [result.incidentIntensity.slice(), result.finalIntensity.slice()], limits = { min: 0, max: 10 };
    const seen: { min: number; max: number }[] = [], { factory } = canvasFactory();
    vi.stubGlobal('ImageData', class { constructor(readonly data: Uint8ClampedArray) {} });
    try {
      const resources = preparePolarizationResources(result, limits, 1, 1, { canvas: factory,
        texture(intensity, grid, range) { seen.push({ ...range }); return createArrayDetectorTexture(intensity, grid, range); } });
      expect(seen, 'POLARIZER_LOSS_SHARED_SCALE').toEqual([limits, limits]);
      expect(result.incidentIntensity).toEqual(before[0]); expect(result.finalIntensity).toEqual(before[1]);
      expect(resources.ownedBytes).toBe(16 * 12 + 2 * 257 * 16);
      expect(resources.commonAmplitudeScale).toBe(1); expect(resources.gain).toBe(1); expect(resources.limits).toEqual(limits);
      const disposed = [vi.fn(), vi.fn()]; resources.textures.forEach((texture, index) => texture.addEventListener('dispose', disposed[index]));
      resources.textures[0].dispose(); // Actual scene detachment can precede the presentation owner's teardown.
      resources.dispose(); resources.dispose(); disposed.forEach(spy => expect(spy).toHaveBeenCalledOnce());
    } finally { vi.unstubAllGlobals(); }
  });
  it('keeps effective trajectory scale and colors with old resources when later changed-display preparation fails', () => {
    const result = fixture(), { factory } = canvasFactory(); vi.stubGlobal('ImageData', class { constructor(readonly data: Uint8ClampedArray) {} });
    try {
      const old = preparePolarizationResources(result, { min: 0, max: 10 }, 2, 3, { canvas: factory });
      expect(() => preparePolarizationResources(result, { min: 0, max: 1 }, 4, 5, { canvas: factory,
        trajectories() { throw new Error('later changed-display failure'); } })).toThrow('later');
      expect(old.commonAmplitudeScale).toBe(2); expect(old.gain).toBe(3); expect(old.limits).toEqual({ min: 0, max: 10 });
      close(old.trajectories[0].points[0], result.stages[0].sample.x.re / 2 * 3, 'ATOMIC_LATE_RESOURCE_DETECTED'); old.dispose();
    } finally { vi.unstubAllGlobals(); }
  });
  it('guards nonfinite derived display positions without editing actual optical values', () => {
    const result = fixture(); const sample = { x: { re: Number.MAX_VALUE, im: Number.MAX_VALUE }, y: { re: 0, im: 0 } };
    const trajectory = prepareTrajectories({ ...result, stages: [{ ...result.stages[0], sample }] })[0];
    expect(trajectory.renderable).toBe(false); expect(trajectory.displayLimited).toBe(true); expect(trajectory.sample.x.re).toBe(Number.MAX_VALUE);
    const finiteBeforeSVG = { x: { re: 1, im: 0 }, y: { re: 0, im: 0 } };
    const converted = prepareTrajectories({ ...result, stages: [{ ...result.stages[0], sample: finiteBeforeSVG }] }, 1e-289, 1e18)[0];
    expect(Number.isFinite(1 / 1e-289 * 1e18)).toBe(true);
    expect(converted.renderable).toBe(false); expect(converted.displayLimited).toBe(true); expect(converted.sample.x.re).toBe(1);
    expect(() => validateDisplayScale(0, 1)).toThrow(); expect(() => validateDisplayScale(1, 1e19)).toThrow();
  });
  it('maps both images without row/column or component swaps and never changes raw float64', () => {
    const result = fixture(); const original = result.finalIntensity.slice();
    const texture = createArrayDetectorTexture(result.finalIntensity, result.experiment.grid, { min: 0, max: 10 });
    for (let row = 0; row < 3; row++) for (let column = 0; column < 4; column++) {
      const { u, v } = pixelCenterUV(result.experiment.grid, row, column);
      expect(pixelFromUV(result.experiment.grid, u, v)).toEqual({ row, column });
      expect(pixelCoordinates(result.experiment.grid, row, column)).toEqual({ x_m: result.x[column], y_m: result.y[row] });
      expect((texture.image.data as Uint8Array)[4 * ((2 - row) * 4 + column)]).toBe(Math.round(result.finalIntensity[row * 4 + column] / 10 * 255));
    }
    expect(result.finalIntensity).toEqual(original); expect(texture.flipY).toBe(false); expect(texture.magFilter).toBe(THREE.NearestFilter); texture.dispose();
  });
  it.each(['second texture', 'second canvas', 'later trajectory'])('cleans every prepared resource on %s failure before publication', failure => {
    const result = fixture(), textures: THREE.DataTexture[] = [], disposals: ReturnType<typeof vi.fn>[] = [];
    const { factory, canvases } = canvasFactory(failure === 'second canvas' ? 1 : -1);
    let calls = 0, published = null;
    const textureFactory = () => { if (++calls === 2 && failure === 'second texture') throw new Error('second texture');
      const texture = new THREE.DataTexture(new Uint8Array(4), 1, 1), spy = vi.fn(); texture.addEventListener('dispose', spy); textures.push(texture); disposals.push(spy); return texture; };
    vi.stubGlobal('ImageData', class { constructor(readonly data: Uint8ClampedArray) {} });
    try {
      expect(() => { published = preparePolarizationResources(result, { min: 0, max: 10 }, 1, 1,
        { texture: textureFactory, canvas: factory, trajectories: failure === 'later trajectory' ? () => { throw new Error('later trajectory'); } : undefined }); }).toThrow();
      expect(published, 'ATOMIC_LATE_RESOURCE_DETECTED').toBeNull(); disposals.forEach(spy => expect(spy, 'ATOMIC_LATE_RESOURCE_DETECTED').toHaveBeenCalledOnce());
      expect(canvases.map(canvas => [canvas.width, canvas.height]), 'ATOMIC_LATE_RESOURCE_DETECTED').toEqual(canvases.map(() => [0, 0]));
    } finally { vi.unstubAllGlobals(); }
  });
  it('owns exactly one callback, stops obsolete trajectory updates and never schedules animation itself', () => {
    const playback = new PolarizationPlayback(), old = vi.fn(), next = vi.fn(), raf = vi.fn(), fetcher = vi.fn();
    vi.stubGlobal('requestAnimationFrame', raf); vi.stubGlobal('fetch', fetcher);
    try {
      playback.bind(old); playback.play(); playback.tick(100); playback.tick(200); const oldCalls = old.mock.calls.length;
      playback.bind(next); playback.play(); playback.tick(300); playback.tick(400);
      expect(old.mock.calls.length, 'ANIMATION_TEARDOWN_DETECTED').toBe(oldCalls); expect(next).toHaveBeenCalledTimes(3);
      playback.detach(); const nextCalls = next.mock.calls.length; playback.tick(500); playback.play(); playback.tick(600);
      expect(next.mock.calls.length, 'ANIMATION_TEARDOWN_DETECTED').toBe(nextCalls); expect((playback.snapshot() as any).activeOwners).toBe(0);
      expect(raf, 'VIEW_ACTION_NO_OPTICS').not.toHaveBeenCalled(); expect(fetcher, 'VIEW_ACTION_NO_OPTICS').not.toHaveBeenCalled();
      playback.reset(); expect(playback.tau).toBe(0);
    } finally { vi.unstubAllGlobals(); }
  });
  it('deduplicates actual all-mode cap buffers, failed numerical overlap and phase budgets without raising limits', () => {
    const grid = { ny: 512, nx: 512, dy: 4e-6, dx: 4e-6 }, plane = () => new Float64Array(512 * 512), axis = () => new Float64Array(512);
    const sequential = { intensity: plane(), x: axis(), y: axis() } as DecodedResult;
    const dual = () => ({ ports: [{ intensity: plane() }, { intensity: plane() }], x: axis(), y: axis() }) as unknown as DecodedTwoPathResult;
    const d1 = dual(), d2 = dual(), p1 = fixture(128, 128), p2 = fixture(128, 128);
    const scientific = ownedScientificBytes(sequential, [d1, d1, d2], [p1, p1, p2], []);
    const expected = (512 * 512 + 2 * 512) * 8 + 2 * (2 * 512 * 512 + 2 * 512) * 8 + 2 * (2 * 128 * 128 + 2 * 128) * 8 + 5 * 16384;
    expect(scientific).toBe(expected);
    const displayedPrior = { intensity: plane(), x: axis(), y: axis() } as DecodedResult;
    expect(ownedScientificBytes([sequential, displayedPrior, displayedPrior], [d1, d2], [p1, p2], []) - scientific)
      .toBe((512 * 512 + 2 * 512) * 8 + 16384);
    // Current and prior canvas pairs are mutually exclusive in renderTwoPath.
    // Active pair canvases + active pair texture sources =16P persistent.
    // Atomic new/old overlap and conversion buffers belong to preparationPeak.
    const visible = 512 * 512 * 16, retained = scientific + visible + 2 * 65536;
    expect(retained).toBeLessThan(16 * 1024 * 1024);
    for (const kind of ['sequential', 'two_path', 'polarization'] as const) {
      const estimate = estimateOwnedOperation(kind, kind === 'polarization' ? p1.experiment.grid : grid, retained);
      expect(estimate.peakOwnedBytes).toBe(Math.max(estimate.transportPeak, estimate.decodePeak, estimate.preparationPeak));
      expect(estimate.peakOwnedBytes).toBeLessThan(32 * 1024 * 1024); expect(() => assertOwnedBudgets(retained, estimate.peakOwnedBytes)).not.toThrow();
    }
    expect(estimateOwnedOperation('polarization', p1.experiment.grid, retained).frameBytes).toBe(280592);
    expect(() => assertOwnedBudgets(16 * 1024 * 1024 + 1, 0)).toThrow(); expect(() => assertOwnedBudgets(0, 32 * 1024 * 1024 + 1)).toThrow();
  });
  it('charges scalar sweep transport independently of tiny image dimensions', () => {
    for (const kind of ['two_path', 'polarization'] as const) {
      const estimate = estimateOwnedOperation(kind, { ny: 1, nx: 1, dy: 1e-6, dx: 1e-6 }, 1234, 'sweep');
      expect(estimate.frameBytes).toBe(65536); expect(estimate.transportPeak).toBe(1234 + 131072);
      expect(estimate.decodePeak).toBe(1234 + 131072); expect(estimate.peakOwnedBytes).toBe(1234 + 131072);
    }
  });
  it('counts actual CPU geometry attributes and index aliases separately from GPU memory', () => {
    const geometry = new THREE.BufferGeometry(), positions = new Float32Array(12), indices = new Uint16Array([0, 1, 2]);
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('normal', new THREE.BufferAttribute(positions, 3)); geometry.setIndex(new THREE.BufferAttribute(indices, 1));
    const scene = Object.create(BenchScene.prototype) as BenchScene; Object.assign(scene, { geometries: new Set([geometry]) });
    expect(scene.ownedGeometryBuffers().reduce((n, buffer) => n + buffer.byteLength, 0)).toBe(positions.byteLength + indices.byteLength);
    geometry.dispose();
  });
  it('preserves and counts distinct scene A canvas B state C owners and fails closed before another allocation', () => {
    const plane = () => new Float64Array(512 * 512), axis = () => new Float64Array(512);
    const sequential = () => ({ intensity: plane(), x: axis(), y: axis() }) as DecodedResult;
    const sceneA = sequential(), canvasB = sequential(), stateC = sequential();
    const dual = () => ({ ports: [{ intensity: plane() }, { intensity: plane() }], x: axis(), y: axis() }) as unknown as DecodedTwoPathResult;
    const d1 = dual(), d2 = dual(), p1 = fixture(128, 128), p2 = fixture(128, 128);
    const twoOwners = ownedScientificBytes([sceneA, canvasB], [d1, d2], [p1, p2], []) + 8 * 512 * 512 + 2 * 65536;
    const incoming = (512 * 512 + 2 * 512) * 8 + 16384;
    const allOwners = ownedScientificBytes([sceneA, canvasB, stateC], [d1, d2], [p1, p2], []) + 8 * 512 * 512 + 2 * 65536;
    expect(allOwners).toBe(twoOwners + incoming); expect(allOwners).toBeGreaterThan(16 * 1024 * 1024);
    const estimate = estimateOwnedOperation('sequential', { ny: 512, nx: 512, dx: 4e-6, dy: 4e-6 }, twoOwners);
    expect(() => assertOwnedBudgets(twoOwners + estimate.payloadBytes + 16384, estimate.peakOwnedBytes)).toThrow('budget');
    expect(sceneA.intensity.byteLength).toBe(512 * 512 * 8); expect(canvasB.intensity.byteLength).toBe(512 * 512 * 8);
  });
});
