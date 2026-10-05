/** Display-only products. Original float64 intensity is never changed. */
import * as THREE from 'three';
import type { DecodedResult } from './contracts';

export interface ColorLimits { min: number; max: number }
export const INITIAL_COLOR_LIMITS: Readonly<ColorLimits> = Object.freeze({ min: 0, max: 10 });

export function validateColorLimits(limits: ColorLimits): void {
  if (!Number.isFinite(limits.min) || !Number.isFinite(limits.max)
      || limits.min < 0 || limits.max <= limits.min) {
    throw new RangeError('色階必須有限，且 0 ≤ 下限 < 上限。');
  }
}

/** Byte values are explicitly sRGB-coded gray; reverse rows only for Three UVs. */
export function intensityRGBA(
  intensity: Float64Array, ny: number, nx: number, limits: ColorLimits,
  reverseRows = false,
): Uint8Array {
  validateColorLimits(limits);
  if (!Number.isInteger(ny) || !Number.isInteger(nx) || ny < 1 || nx < 1
      || intensity.length !== ny * nx) throw new RangeError('強度陣列尺寸不一致。');
  const bytes = new Uint8Array(ny * nx * 4);
  for (let row = 0; row < ny; row += 1) {
    for (let column = 0; column < nx; column += 1) {
      const value = intensity[row * nx + column];
      if (!Number.isFinite(value) || value < 0) throw new RangeError('強度必須有限且非負。');
      const gray = Math.round(255 * Math.min(1, Math.max(0,
        (value - limits.min) / (limits.max - limits.min))));
      const outputRow = reverseRows ? ny - 1 - row : row;
      const offset = 4 * (outputRow * nx + column);
      bytes[offset] = gray;
      bytes[offset + 1] = gray;
      bytes[offset + 2] = gray;
      bytes[offset + 3] = 255;
    }
  }
  return bytes;
}

/** Caller owns and must dispose this texture once it leaves the active scene. */
export function createDetectorTexture(result: DecodedResult, limits: ColorLimits): THREE.DataTexture {
  const { ny, nx } = result.experiment.grid;
  const texture = new THREE.DataTexture(
    intensityRGBA(result.intensity, ny, nx, limits, true), nx, ny,
    THREE.RGBAFormat, THREE.UnsignedByteType,
  );
  texture.flipY = false;
  texture.magFilter = THREE.NearestFilter;
  texture.minFilter = THREE.NearestFilter;
  texture.generateMipmaps = false;
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.needsUpdate = true;
  return texture;
}

/** Ordinary result panel uses the same byte mapping, with original top row first. */
export function drawDetector(canvas: HTMLCanvasElement, result: DecodedResult, limits: ColorLimits): void {
  const context = canvas.getContext('2d');
  if (!context) throw new Error('無法建立強度圖的 2D 顯示。');
  const { ny, nx } = result.experiment.grid;
  canvas.width = nx;
  canvas.height = ny;
  const bytes = new Uint8ClampedArray(intensityRGBA(result.intensity, ny, nx, limits));
  context.putImageData(new ImageData(bytes, nx, ny), 0, 0);
}

export function automaticColorLimits(result: DecodedResult): ColorLimits {
  // Zero is a valid dark result; only display limits need a nonzero interval.
  return { min: 0, max: result.intensityMax > 0 ? result.intensityMax : 1 };
}
