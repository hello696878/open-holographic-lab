/** Display relations and bounded app-owned products, never an optical solver. */
import * as THREE from 'three';
import type { DecodedResult, GridSpec } from './contracts';
import type { DecodedTwoPathResult, DecodedTwoPathSweep } from './two_path_contracts';
import { createArrayDetectorTexture, intensityRGBA, validateColorLimits, type ColorLimits } from './detector';
import type { ComplexPair, DecodedPolarizationResult, DecodedPolarizationSweep } from './polarization_contracts';
import type { DecodedPolarizedTwoPathResult, DecodedPolarizedTwoPathSweep } from './polarized_two_path_contracts';
import { OWNED_PERSISTENT_BUDGET_BYTES, OWNED_TRANSIENT_BUDGET_BYTES } from './phase_sweep';
export const TRAJECTORY_VERTICES = 257;
/** Exact zero test on returned components, independent of squared-intensity underflow. */
export function isDarkSample(sample: ComplexPair): boolean {
  return sample.x.re === 0 && sample.x.im === 0 && sample.y.re === 0 && sample.y.im === 0;
}
/** Dimensionless tau under exp(-i*tau); +x right and +y down. */
export function trajectoryMarker(sample: ComplexPair, tau: number): Readonly<{ x: number; y: number }> {
  if (!Number.isFinite(tau)) throw new Error('Display tau must be finite');
  const c = Math.cos(tau), s = Math.sin(tau);
  return Object.freeze({ x: sample.x.re * c + sample.x.im * s, y: sample.y.re * c + sample.y.im * s });
}
export interface Trajectory { readonly stageId: string; readonly sample: ComplexPair; readonly points: Float64Array;
  readonly dark: boolean; readonly displayLimited: boolean; readonly renderable: boolean }
export function prepareTrajectories(result: DecodedPolarizationResult, commonAmplitudeScale = 1, gain = 1): readonly Trajectory[] {
  validateDisplayScale(commonAmplitudeScale, gain);
  return Object.freeze(result.stages.map(stage => {
    const points = new Float64Array(TRAJECTORY_VERTICES * 2); let renderable = true, maximum = 0;
    for (let i = 0; i < TRAJECTORY_VERTICES; i++) {
      const marker = trajectoryMarker(stage.sample, i / (TRAJECTORY_VERTICES - 1) * 2 * Math.PI);
      const x = marker.x / commonAmplitudeScale * gain, y = marker.y / commonAmplitudeScale * gain;
      // The SVG view also multiplies by 100. Guard that final coordinate
      // conversion, while retaining the original complex optical sample.
      if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(x * 100) || !Number.isFinite(y * 100)) renderable = false;
      else { points[2 * i] = x; points[2 * i + 1] = y; maximum = Math.max(maximum, Math.abs(x), Math.abs(y)); }
    }
    const dark = isDarkSample(stage.sample);
    return Object.freeze({ stageId: stage.stage_id, sample: stage.sample, points, dark, renderable,
      displayLimited: !dark && (!renderable || maximum < 0.005 || maximum > 1) });
  }));
}
export function validateDisplayScale(scale: number, gain: number): void {
  if (!Number.isFinite(scale) || scale <= 0 || !Number.isFinite(gain) || gain < 1 || gain > 1e18) {
    throw new Error('Display amplitude scale must be positive finite; manual gain must be 1..1e18. Optical values are unchanged.');
  }
}
export interface PolarizationResources { readonly textures: readonly [THREE.DataTexture, THREE.DataTexture];
  readonly canvases: readonly [HTMLCanvasElement, HTMLCanvasElement]; readonly trajectories: readonly Trajectory[];
  readonly limits: Readonly<ColorLimits>; readonly commonAmplitudeScale: number; readonly gain: number;
  readonly ownedBytes: number; dispose(): void }
export interface PolarizationFactories {
  texture?: typeof createArrayDetectorTexture;
  canvas?: () => HTMLCanvasElement;
  trajectories?: typeof prepareTrajectories;
}
/** Prepare both images then the later trajectory resources. Any failure cleans every partial allocation. */
export function preparePolarizationResources(result: DecodedPolarizationResult, limits: ColorLimits,
    scale = 1, gain = 1, factories: PolarizationFactories = {}): PolarizationResources {
  validateColorLimits(limits); validateDisplayScale(scale, gain);
  const textures: THREE.DataTexture[] = [], canvases: HTMLCanvasElement[] = [];
  const disposedTextures = new WeakSet<THREE.DataTexture>();
  let trajectories: readonly Trajectory[] = [];
  const disposePartial = () => { textures.forEach(texture => { if (!disposedTextures.has(texture)) texture.dispose(); });
    canvases.forEach(canvas => { canvas.width = 0; canvas.height = 0; }); };
  try {
    for (const intensity of [result.incidentIntensity, result.finalIntensity]) {
      const texture = (factories.texture ?? createArrayDetectorTexture)(intensity, result.experiment.grid, limits);
      const onDispose = () => { disposedTextures.add(texture); texture.removeEventListener('dispose', onDispose); };
      texture.addEventListener('dispose', onDispose); textures.push(texture);
    }
    for (const [index, intensity] of [result.incidentIntensity, result.finalIntensity].entries()) {
      const canvas = (factories.canvas ?? (() => document.createElement('canvas')))(); canvases.push(canvas);
      canvas.dataset.testid = `pl-intensity-${index}`; canvas.setAttribute('aria-label', index === 0 ? '入射原始強度' : '最終原始強度');
      const { nx, ny } = result.experiment.grid; canvas.width = nx; canvas.height = ny;
      const context = canvas.getContext('2d'); if (!context) throw new Error(`Polarization image ${index} 2D display preparation failed`);
      context.putImageData(new ImageData(new Uint8ClampedArray(intensityRGBA(intensity, ny, nx, limits)), nx, ny), 0, 0);
    }
    trajectories = (factories.trajectories ?? prepareTrajectories)(result, scale, gain);
  } catch (error) { disposePartial(); throw error; }
  let disposed = false;
  const ownedBytes = textures.reduce((n, t) => n + (t.image.data as Uint8Array).byteLength, 0)
    + canvases.reduce((n, c) => n + c.width * c.height * 4, 0) + trajectories.reduce((n, t) => n + t.points.byteLength, 0);
  return { textures: Object.freeze(textures as [THREE.DataTexture, THREE.DataTexture]),
    canvases: Object.freeze(canvases as [HTMLCanvasElement, HTMLCanvasElement]), trajectories, ownedBytes,
    limits: Object.freeze({ ...limits }), commonAmplitudeScale: scale, gain,
    dispose() { if (disposed) return; disposed = true; disposePartial(); } };
}
/** One owner used by the existing scene render loop; this class schedules no callbacks. */
export class PolarizationPlayback {
  private update: ((tau: number) => void) | null = null;
  private previousTime: number | null = null;
  private generation = 0;
  private ticks = 0;
  tau = 0;
  playing = false;
  bind(update: (tau: number) => void): void { this.detach(); this.update = update; this.update(this.tau); }
  detach(): void { ++this.generation; this.update = null; this.playing = false; this.previousTime = null; }
  setTau(tau: number): void { if (!Number.isFinite(tau)) throw new Error('Finite display tau required'); this.tau = tau; this.update?.(tau); }
  play(): void { if (this.update) { this.playing = true; this.previousTime = null; } }
  pause(): void { this.playing = false; this.previousTime = null; }
  reset(): void { this.pause(); this.setTau(0); }
  tick(time: number): void {
    if (!this.playing || !this.update) return;
    if (this.previousTime !== null) this.tau = (this.tau + Math.max(0, Math.min(0.1, (time - this.previousTime) / 1000))) % (2 * Math.PI);
    this.previousTime = time; ++this.ticks; this.update(this.tau);
  }
  snapshot(): object { return { tau: this.tau, playing: this.playing, ticks: this.ticks, generation: this.generation, activeOwners: this.update ? 1 : 0, scheduledCallbacks: 0 }; }
}
/** Deduplicated scientific backing stores plus explicit logical metadata charges. */
export function ownedScientificBytes(sequential: DecodedResult | null | readonly (DecodedResult | null)[], dual: readonly (DecodedTwoPathResult | null)[],
    polarization: readonly (DecodedPolarizationResult | null)[], sweeps: readonly (DecodedTwoPathSweep | DecodedPolarizationSweep | DecodedPolarizedTwoPathSweep | null)[],
    polarizedTwoPath: readonly (DecodedPolarizedTwoPathResult | null)[] = []): number {
  const buffers = new Set<ArrayBufferLike>(), results = new Set<object>();
  const add = (array: Float64Array | undefined) => { if (array) buffers.add(array.buffer); };
  const sequentialResults = Array.isArray(sequential) ? sequential : [sequential as DecodedResult | null];
  for (const result of sequentialResults) if (result) { results.add(result); add(result.intensity); add(result.x); add(result.y); }
  for (const result of dual) if (result) { results.add(result); result.ports.forEach(port => add(port.intensity)); add(result.x); add(result.y); }
  for (const result of polarization) if (result) { results.add(result); add(result.incidentIntensity); add(result.finalIntensity); add(result.x); add(result.y); }
  const newResults = new Set<object>();
  for (const result of polarizedTwoPath) if (result) { newResults.add(result); result.rawPorts.forEach(port => add(port.intensity));
    result.analyzedPorts?.forEach(port => add(port.intensity)); add(result.x); add(result.y); }
  const sweepSet = new Set(sweeps.filter((sweep): sweep is DecodedTwoPathSweep | DecodedPolarizationSweep | DecodedPolarizedTwoPathSweep => sweep !== null));
  return [...buffers].reduce((n, buffer) => n + buffer.byteLength, 0) + results.size * 16384
    + newResults.size * 32768
    + [...sweepSet].reduce((n, sweep) => n + new TextEncoder().encode(JSON.stringify(sweep)).byteLength, 0);
}
export function estimateOwnedOperation(kind: 'sequential' | 'two_path' | 'polarization', grid: GridSpec, retained: number,
    operation: 'single' | 'sweep' = 'single'): Readonly<{
  retained: number; payloadBytes: number; frameBytes: number; transportPeak: number; decodePeak: number; preparationPeak: number; peakOwnedBytes: number }> {
  const cap = kind === 'polarization' ? 128 : 512;
  if (!Number.isSafeInteger(grid.nx) || !Number.isSafeInteger(grid.ny) || grid.nx < 1 || grid.ny < 1 || grid.nx > cap || grid.ny > cap
      || !Number.isSafeInteger(retained) || retained < 0) throw new Error('Invalid ownership estimate inputs');
  if (operation === 'sweep') {
    if (kind === 'sequential') throw new Error('Sequential mode has no scalar sweep');
    // JSON sweep cap is independent of image dimensions. Decoded scalar-record
    // logical ownership is charged alongside the joined incoming frame.
    const frameBytes = 65536, transportPeak = retained + 2 * frameBytes, decodePeak = retained + 2 * frameBytes;
    const preparationPeak = retained + frameBytes;
    return Object.freeze({ retained, payloadBytes: 0, frameBytes, transportPeak, decodePeak, preparationPeak,
      peakOwnedBytes: Math.max(transportPeak, decodePeak, preparationPeak) });
  }
  const pixels = grid.nx * grid.ny, paired = kind !== 'sequential';
  const payloadBytes = 8 * ((paired ? 2 : 1) * pixels + grid.nx + grid.ny), frameBytes = 16 + 16384 + payloadBytes;
  const transportPeak = retained + 2 * frameBytes, decodePeak = retained + frameBytes + payloadBytes;
  const preparationPeak = retained + payloadBytes + (paired ? 24 : 12) * pixels + (kind === 'polarization' ? 9 * TRAJECTORY_VERTICES * 16 : 0) + 16384;
  return Object.freeze({ retained, payloadBytes, frameBytes, transportPeak, decodePeak, preparationPeak,
    peakOwnedBytes: Math.max(transportPeak, decodePeak, preparationPeak) });
}
export function assertOwnedBudgets(persistent: number, transient: number): void {
  if (persistent > OWNED_PERSISTENT_BUDGET_BYTES || transient > OWNED_TRANSIENT_BUDGET_BYTES) throw new Error('App-owned buffer budget exceeded; no optical request or new publication.');
}
