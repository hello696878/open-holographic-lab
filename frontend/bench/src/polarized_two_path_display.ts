/** Four-image presentation products and phase-wise app-owned byte ledgers. */
import * as THREE from 'three';
import type { DecodedResult, GridSpec } from './contracts';
import type { DecodedTwoPathResult, DecodedTwoPathSweep } from './two_path_contracts';
import type { DecodedPolarizationResult, DecodedPolarizationSweep } from './polarization_contracts';
import type { DecodedPolarizedTwoPathResult, DecodedPolarizedTwoPathSweep } from './polarized_two_path_contracts';
import { createArrayDetectorTexture, intensityRGBA, validateColorLimits, type ColorLimits } from './detector';
import { ownedScientificBytes } from './polarization_display';
export interface PolarizedTwoPathResources { readonly textures: readonly THREE.DataTexture[]; readonly canvases: readonly HTMLCanvasElement[];
  readonly limits: Readonly<ColorLimits>; readonly ownedBytes: number; dispose(): void }
export interface PolarizedTwoPathFactories { texture?: typeof createArrayDetectorTexture; canvas?: () => HTMLCanvasElement }
export function automaticPolarizedTwoPathColorLimits(result: DecodedPolarizedTwoPathResult): ColorLimits {
  const maximum = Math.max(...result.intensityMax); return { min: 0, max: maximum > 0 ? maximum : 1 };
}
/** Prepare every required raw/analyzed port before any visible publication. */
export function preparePolarizedTwoPathResources(result: DecodedPolarizedTwoPathResult, limits: ColorLimits,
    factories: PolarizedTwoPathFactories = {}): PolarizedTwoPathResources {
  validateColorLimits(limits);
  if (result.experiment.analyzer.enabled !== !!result.analyzedPorts) throw new Error('Submitted analyzer and display roles disagree');
  const ports = [...result.rawPorts, ...(result.analyzedPorts ?? [])], textures: THREE.DataTexture[] = [], canvases: HTMLCanvasElement[] = [];
  const disposedTextures = new WeakSet<THREE.DataTexture>();
  const disposePartial = () => { textures.forEach(texture => { if (!disposedTextures.has(texture)) texture.dispose(); });
    canvases.forEach(canvas => { canvas.width = 0; canvas.height = 0; }); };
  try {
    for (const port of ports) { const texture = (factories.texture ?? createArrayDetectorTexture)(port.intensity, result.experiment.grid, limits);
      const onDispose = () => { disposedTextures.add(texture); texture.removeEventListener('dispose', onDispose); }; texture.addEventListener('dispose', onDispose); textures.push(texture); }
    for (const [index, port] of ports.entries()) {
      const canvas = (factories.canvas ?? (() => document.createElement('canvas')))(); canvases.push(canvas);
      canvas.dataset.testid = `pt-intensity-${index}`; canvas.setAttribute('aria-label', `${index < 2 ? 'raw' : 'analyzed'} ${port.id} intensity`);
      const { nx, ny } = result.experiment.grid; canvas.width = nx; canvas.height = ny;
      const context = canvas.getContext('2d'); if (!context) throw new Error(`Polarized two-path image ${index} 2D display preparation failed`);
      context.putImageData(new ImageData(new Uint8ClampedArray(intensityRGBA(port.intensity, ny, nx, limits)), nx, ny), 0, 0);
    }
  } catch (error) { disposePartial(); throw error; }
  const ownedBytes = textures.reduce((n, t) => n + (t.image.data as Uint8Array).byteLength, 0) + canvases.reduce((n, c) => n + 4 * c.width * c.height, 0);
  let disposed = false;
  return { textures: Object.freeze(textures), canvases: Object.freeze(canvases), limits: Object.freeze({ ...limits }), ownedBytes,
    dispose() { if (disposed) return; disposed = true; disposePartial(); } };
}
export function ownedScientificBytes4(values: {
  sequential: readonly (DecodedResult | null)[]; dual: readonly (DecodedTwoPathResult | null)[];
  polarization: readonly (DecodedPolarizationResult | null)[]; polarizedTwoPath: readonly (DecodedPolarizedTwoPathResult | null)[];
  sweeps: readonly (DecodedTwoPathSweep | DecodedPolarizationSweep | DecodedPolarizedTwoPathSweep | null)[];
}): number { return ownedScientificBytes(values.sequential, values.dual, values.polarization, values.sweeps, values.polarizedTwoPath); }
/** Conservative app-owned projections, not total browser/GPU/native memory measurements. */
export function estimatePolarizedTwoPathOperation(grid: GridSpec, analyzerEnabled: boolean, retained: number, operation: 'single' | 'sweep' = 'single') {
  if (!Number.isSafeInteger(grid.nx) || !Number.isSafeInteger(grid.ny) || grid.nx < 1 || grid.ny < 1 || grid.nx > 128 || grid.ny > 128
    || typeof analyzerEnabled !== 'boolean' || !Number.isSafeInteger(retained) || retained < 0) throw new Error('Invalid polarized two-path ownership estimate');
  if (operation === 'sweep') return Object.freeze({ retained, payloadBytes: 0, frameBytes: 65536, persistentProjection: retained + 131072,
    transportPeak: retained + 524288, decodePeak: retained + 524288, preparationPeak: retained + 131072, peakOwnedBytes: retained + 524288 });
  const p = grid.nx * grid.ny, k = analyzerEnabled ? 4 : 2, H = 16384, M = 32768, G = 131072;
  const payloadBytes = 8 * (k * p + grid.nx + grid.ny), frameBytes = 16 + H + payloadBytes;
  const persistentProjection = retained + payloadBytes + M + 8 * k * p + G;
  const transportPeak = retained + 2 * frameBytes, decodePeak = retained + frameBytes + payloadBytes + 2 * M + 2 * H;
  const preparationPeak = persistentProjection + 8 * p;
  return Object.freeze({ retained, payloadBytes, frameBytes, persistentProjection, transportPeak, decodePeak, preparationPeak,
    peakOwnedBytes: Math.max(transportPeak, decodePeak, preparationPeak) });
}
