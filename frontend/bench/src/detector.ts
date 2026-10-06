/** Display-only products. Original float64 intensity is never changed. */
import * as THREE from 'three';
import type { DecodedResult } from './contracts';
import type { GridSpec } from './contracts';
import type { DecodedTwoPathResult } from './two_path_contracts';

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
  return createArrayDetectorTexture(result.intensity, result.experiment.grid, limits);
}

/** Display texture only; the source float64 array remains authoritative. */
export function createArrayDetectorTexture(intensity: Float64Array, grid: GridSpec, limits: ColorLimits): THREE.DataTexture {
  const { ny, nx } = grid;
  const texture = new THREE.DataTexture(
    intensityRGBA(intensity, ny, nx, limits, true), nx, ny,
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

/** Joint range is an explicit presentation action; it never changes data. */
export function automaticDualColorLimits(result: DecodedTwoPathResult): ColorLimits {
  const maximum = Math.max(result.ports[0].intensityMax, result.ports[1].intensityMax);
  return { min: 0, max: maximum > 0 ? maximum : 1 };
}

export type DualTextureFactory = (intensity: Float64Array, grid: GridSpec,
  limits: ColorLimits, portId: 'port_0' | 'port_1') => THREE.DataTexture;

/** Prepare both outputs before attachment; dispose the first on second failure. */
export function prepareDualTextures(result: DecodedTwoPathResult, limits: ColorLimits,
  factory: DualTextureFactory = createArrayDetectorTexture): {
    textures: readonly [THREE.DataTexture, THREE.DataTexture]; dispose: () => void;
  } {
  let first: THREE.DataTexture | null = null;
  let second: THREE.DataTexture | null = null;
  try {
    first = factory(result.ports[0].intensity, result.experiment.grid, limits, 'port_0');
    second = factory(result.ports[1].intensity, result.experiment.grid, limits, 'port_1');
  } catch (error) { first?.dispose(); second?.dispose(); throw error; }
  const textures = Object.freeze([first, second] as const);
  let disposed = false;
  return { textures, dispose() {
    if (disposed) return;
    disposed = true; for (const texture of textures) texture.dispose();
  } };
}

/** Detached canvas pair. No visible canvas changes until both are usable. */
export function prepareDualCanvases(result: DecodedTwoPathResult, limits: ColorLimits):
  readonly [HTMLCanvasElement, HTMLCanvasElement] {
  const { nx, ny } = result.experiment.grid;
  const canvases: HTMLCanvasElement[] = [];
  try { result.ports.forEach((port, index) => {
    const canvas = document.createElement('canvas');
    canvases.push(canvas);
    canvas.dataset.testid = `tp-intensity-${index}`;
    canvas.setAttribute('aria-label', `輸出埠 ${index} 的原始強度灰階`);
    canvas.width = nx; canvas.height = ny;
    const context = canvas.getContext('2d');
    if (!context) throw new Error(`輸出埠 ${index} 無法準備 2D 顯示。`);
    const bytes = new Uint8ClampedArray(intensityRGBA(port.intensity, ny, nx, limits));
    context.putImageData(new ImageData(bytes, nx, ny), 0, 0);
  }); } catch (error) {
    for (const canvas of canvases) { canvas.width = 0; canvas.height = 0; }
    throw error;
  }
  return Object.freeze(canvases as [HTMLCanvasElement, HTMLCanvasElement]);
}
