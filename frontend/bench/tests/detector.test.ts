import { describe, expect, it } from 'vitest';
import * as THREE from 'three';
import { automaticColorLimits, createDetectorTexture, intensityRGBA } from '../src/detector';
import type { DecodedResult } from '../src/contracts';

function fixture(values: number[], ny: number, nx: number): DecodedResult {
  return {
    requestId: 'fixture', experimentSha256: '0'.repeat(64), stages: [],
    experiment: {
      schema_version: 1, model_contract: 'v0_aligned_scalar_forward_v1', wavelength_m: 633e-9,
      grid: { ny, nx, dy: 5e-6, dx: 2e-6 },
      source: { kind: 'uniform', amplitude: 1, phase_rad: 0 },
      components: [], observation: { id: 'screen', z_m: 0 },
    },
    intensity: new Float64Array(values), x: new Float64Array(nx), y: new Float64Array(ny),
    intensityMax: Math.max(...values),
  };
}

describe('detector display remains separate from float64 data', () => {
  it('maps a hand-calculated intermediate gray without an extra transfer', () => {
    expect([...intensityRGBA(new Float64Array([0, 5, 10]), 1, 3, { min: 0, max: 10 })])
      .toEqual([0, 0, 0, 255, 128, 128, 128, 255, 255, 255, 255, 255]);
  });
  it('reverses only display rows and does not swap columns', () => {
    const values = new Float64Array([1, 2, 3, 4, 5, 6]);
    const bytes = intensityRGBA(values, 2, 3, { min: 0, max: 255 }, true);
    expect([...bytes.filter((_, index) => index % 4 === 0)]).toEqual([4, 5, 6, 1, 2, 3]);
    expect([...values]).toEqual([1, 2, 3, 4, 5, 6]);
  });
  it('maps every corner and interior entry of the independent asymmetric 3x4 fixture', () => {
    const original = [11, 12, 13, 14, 21, 22, 23, 24, 31, 32, 33, 34];
    const values = new Float64Array(original);
    const display = intensityRGBA(values, 3, 4, { min: 0, max: 255 }, true);
    expect([...display.filter((_, index) => index % 4 === 0)])
      .toEqual([31, 32, 33, 34, 21, 22, 23, 24, 11, 12, 13, 14]);
    expect([...values]).toEqual(original);
  });
  it('keeps the complementary 2x5 fixture columns in original left-to-right order', () => {
    const values = new Float64Array([10, 20, 30, 40, 50, 110, 120, 130, 140, 150]);
    const display = intensityRGBA(values, 2, 5, { min: 0, max: 255 }, true);
    expect([...display.filter((_, index) => index % 4 === 0)])
      .toEqual([110, 120, 130, 140, 150, 10, 20, 30, 40, 50]);
  });
  it('preserves sub-float32 numerical values, clamps colors only and keeps a shared scale', () => {
    const values = new Float64Array([1 + 2 ** -50, 20]);
    const original = new Uint8Array(values.buffer).slice();
    expect(intensityRGBA(values, 1, 2, { min: 0, max: 10 })[4]).toBe(255);
    expect(new Uint8Array(values.buffer)).toEqual(original);
    const open = intensityRGBA(new Float64Array([5]), 1, 1, { min: 0, max: 10 });
    const loss = intensityRGBA(new Float64Array([1]), 1, 1, { min: 0, max: 10 });
    expect(open[0]).toBe(128);
    expect(loss[0]).toBe(26);
  });
  it('sets explicit row/filter/mipmap/color-space policy and supports disposal', () => {
    const texture = createDetectorTexture(fixture([0, 5, 10, 2], 2, 2), { min: 0, max: 10 });
    expect(texture.flipY).toBe(false);
    expect(texture.minFilter).toBe(THREE.NearestFilter);
    expect(texture.magFilter).toBe(THREE.NearestFilter);
    expect(texture.generateMipmaps).toBe(false);
    expect(texture.colorSpace).toBe(THREE.SRGBColorSpace);
    expect(texture.image.data).toBeInstanceOf(Uint8Array);
    expect([...(texture.image.data as Uint8Array)]).toEqual([255, 255, 255, 255, 51, 51, 51, 255, 0, 0, 0, 255, 128, 128, 128, 255]);
    let disposed = false;
    texture.addEventListener('dispose', () => { disposed = true; });
    texture.dispose();
    expect(disposed).toBe(true);
  });
  it('shows dark results as black with a valid explicitly requested automatic range', () => {
    const result = fixture([0, 0], 1, 2);
    expect(automaticColorLimits(result)).toEqual({ min: 0, max: 1 });
    expect([...intensityRGBA(result.intensity, 1, 2, { min: 0, max: 10 })])
      .toEqual([0, 0, 0, 255, 0, 0, 0, 255]);
    expect(result.intensityMax).toBe(0);
  });
  it.each([{ min: 0, max: 0 }, { min: -1, max: 1 }, { min: 1, max: 0 }, { min: 0, max: Infinity }])
    ('rejects invalid display limits %j', (limits) => {
      expect(() => intensityRGBA(new Float64Array([1]), 1, 1, limits)).toThrow();
    });
  it.each([NaN, Infinity, -1])('rejects invalid display intensity %s', (value) => {
    expect(() => intensityRGBA(new Float64Array([value]), 1, 1, { min: 0, max: 10 })).toThrow();
  });
});
