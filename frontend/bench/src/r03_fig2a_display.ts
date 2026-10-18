/** Quantitative phase encoding and actual CPU-owned display buffers; no polarization solver. */
import * as THREE from 'three';
import { R03_RESPONSE_CAP, type R03Result } from './r03_fig2a_contracts';
export const R03_APPARATUS_CAP = 512 * 1024;
export const R03_PHASE_DISPLAY_BYTES = 2048;
export const R03_RESULT_METADATA_RESERVATION = 16384;
export const R03_TRANSPORT_RESERVATION = 8 * R03_RESPONSE_CAP;
const stops = [[107, 85, 171], [76, 139, 194], [57, 170, 166], [204, 193, 99], [223, 131, 104], [160, 95, 149], [107, 85, 171]];
export function phaseColor(angle: number): readonly [number, number, number] {
  if (!Number.isFinite(angle) || angle < 0 || angle > 2 * Math.PI) throw new Error('Phase color requires wrapped radians in [0,2π], including the preserved modulo-roundoff endpoint');
  const scaled = angle / (2 * Math.PI) * 6, index = Math.min(5, Math.floor(scaled)), fraction = scaled - index;
  return stops[index].map((v, i) => Math.round(v + fraction * (stops[index + 1][i] - v))) as [number, number, number];
}
export const R03_PHASE_GRADIENT = `linear-gradient(90deg, ${stops.map(v => `rgb(${v.join(',')})`).join(',')})`;
export interface R03Display { readonly result: R03Result; readonly canvas: HTMLCanvasElement; readonly texture: THREE.DataTexture;
  readonly rgba: Uint8Array; readonly ownedBytes: number; dispose(): void }
export function prepareR03Display(result: R03Result, factories: { canvas?: () => HTMLCanvasElement; texture?: (rgba: Uint8Array) => THREE.DataTexture } = {}): R03Display {
  const rgba = new Uint8Array(16 * 16 * 4); let texture: THREE.DataTexture | null = null, canvas: HTMLCanvasElement | null = null;
  try {
    if (result.phase.wrapped.length !== 256) throw new Error('Submitted phase shape');
    result.phase.wrapped.forEach((angle, index) => { rgba.set(phaseColor(angle), 4 * index); rgba[4 * index + 3] = 255; });
    texture = factories.texture?.(rgba) ?? new THREE.DataTexture(rgba, 16, 16, THREE.RGBAFormat, THREE.UnsignedByteType);
    texture.minFilter = texture.magFilter = THREE.NearestFilter; texture.generateMipmaps = false; texture.flipY = true;
    texture.colorSpace = THREE.SRGBColorSpace; texture.needsUpdate = true;
    canvas = factories.canvas?.() ?? document.createElement('canvas'); canvas.dataset.testid = 'r03-phase';
    canvas.dataset.requestId = result.requestId; canvas.width = canvas.height = 16;
    canvas.setAttribute('aria-label', 'Submitted wrapped phase mask, row 0 top, column 0 left, radians');
    const context = canvas.getContext('2d'); if (!context) throw new Error('Ideal phase display preparation failed: 2D canvas unavailable');
    context.putImageData(new ImageData(new Uint8ClampedArray(rgba), 16, 16), 0, 0);
  } catch (error) { texture?.dispose(); if (canvas) canvas.width = canvas.height = 0; throw error; }
  let disposed = false; const ownedCanvas = canvas, ownedTexture = texture;
  return { result, canvas: ownedCanvas, texture: ownedTexture, rgba, ownedBytes: R03_PHASE_DISPLAY_BYTES,
    dispose() { if (disposed) return; disposed = true; ownedTexture.dispose(); ownedCanvas.width = ownedCanvas.height = 0; } };
}
/** Metadata reservation is explicit, not a claim to measure V8 object overhead or the whole heap. */
export function r03OwnedResults(results: readonly (R03Result | null)[]): number {
  const unique = new Set(results.filter((result): result is R03Result => result !== null)), buffers = new Set<ArrayBufferLike>();
  unique.forEach(result => { buffers.add(result.phase.unwrapped.buffer); buffers.add(result.phase.wrapped.buffer); });
  return [...buffers].reduce((sum, buffer) => sum + buffer.byteLength, 0) + unique.size * R03_RESULT_METADATA_RESERVATION;
}
export function r03ResultSnapshot(result: R03Result | null): object | null { return result ? {
  requestId: result.requestId, experimentSha256: result.experimentSha256, experiment: { ...result.experiment },
  phase: { shape: [16, 16], order: 'C', unwrapped_rad: Array.from(result.phase.unwrapped), wrapped_rad: Array.from(result.phase.wrapped) },
  stages: structuredClone(result.stages), population: { ...result.population }, provenance: structuredClone(result.provenance), limitations: [...result.limitations],
} : null; }
export function formatR03Number(value: number | null): string { return value === null ? 'undefined' : Object.is(value, -0) ? '−0' : value.toPrecision(10); }
/** Readout only: never use these strings as editable or submitted values. */
export function formatR03Readout(value: number | null, fullPrecision = false): string {
  return value === null ? 'undefined (null)' : Object.is(value, -0) ? '−0' : value.toPrecision(fullPrecision ? 17 : 5);
}
