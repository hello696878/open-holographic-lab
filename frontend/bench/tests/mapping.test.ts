import { describe, expect, it } from 'vitest';
import { detectorEdges, pixelCenterUV, pixelCoordinates, pixelFromUV, worldPosition } from '../src/mapping';

describe('independent physical detector fixtures', () => {
  const mixed = { ny: 3, nx: 4, dy: 5e-6, dx: 2e-6 };
  it('uses full anisotropic cell edges and even-axis half-cell center', () => {
    const edge = detectorEdges(mixed);
    expect(edge.xMin).toBeCloseTo(-5e-6, 16); expect(edge.xMax).toBeCloseTo(3e-6, 16);
    expect(edge.yMin).toBeCloseTo(-7.5e-6, 16); expect(edge.yMax).toBeCloseTo(7.5e-6, 16);
    expect(edge.centerX).toBe(-1e-6); expect(edge.centerY).toBe(0);
    expect(edge.width / edge.height).toBeCloseTo(8 / 15, 15);
    expect(pixelCoordinates(mixed, 0, 0)).toEqual({ x_m: -4e-6, y_m: -5e-6 });
    expect(pixelCoordinates(mixed, 2, 3)).toEqual({ x_m: 2e-6, y_m: 5e-6 });
  });
  it('also handles odd x and even y independently', () => {
    const grid = { ny: 2, nx: 5, dy: 3e-6, dx: 7e-6 };
    const edge = detectorEdges(grid);
    expect(edge.centerX).toBe(0); expect(edge.centerY).toBe(-1.5e-6);
    expect(edge.xMin).toBe(-17.5e-6); expect(edge.xMax).toBe(17.5e-6);
    expect(edge.yMin).toBe(-4.5e-6); expect(edge.yMax).toBe(1.5e-6);
    expect(pixelCoordinates(grid, 0, 0)).toEqual({ x_m: -14e-6, y_m: -3e-6 });
    expect(pixelCoordinates(grid, 1, 4)).toEqual({ x_m: 14e-6, y_m: 0 });
  });
  it('maps every independent row/column center without a y transpose', () => {
    const values = [[11, 12, 13, 14], [21, 22, 23, 24], [31, 32, 33, 34]];
    for (let row = 0; row < 3; row++) for (let column = 0; column < 4; column++) {
      const uv = pixelCenterUV(mixed, row, column);
      expect(pixelFromUV(mixed, uv.u, uv.v)).toEqual({ row, column });
      expect(values[row][column]).toBe(10 * (row + 1) + column + 1);
    }
    expect(pixelFromUV(mixed, 0.125, 5 / 6)).toEqual({ row: 0, column: 0 });
    expect(pixelFromUV(mixed, 0.875, 1 / 6)).toEqual({ row: 2, column: 3 });
    expect(pixelFromUV(mixed, 0.375, 0.5)).toEqual({ row: 1, column: 1 });
  });
  it('uses explicit half-open edges and never clamps an outside click', () => {
    expect(pixelFromUV(mixed, 0, 1)).toEqual({ row: 0, column: 0 });
    expect(pixelFromUV(mixed, 0.999999, 0.000001)).toEqual({ row: 2, column: 3 });
    for (const [u, v] of [[1, 0.5], [0.5, 0], [-Number.EPSILON, 0.5], [1 + Number.EPSILON, 0.5],
      [0.5, 1 + Number.EPSILON], [0.5, -Number.EPSILON], [NaN, 0.5], [0.5, Infinity]]) {
      expect(pixelFromUV(mixed, u, v)).toBeNull();
    }
    expect(pixelFromUV(mixed, 0.25, 0.5)).toEqual({ row: 1, column: 1 });
  });
  it('world scale reverses y explicitly while preserving independent z scale', () => {
    expect(worldPosition(2e-3, 3e-3, 40e-3)).toEqual({ x: 2, y: -3, z: 4 });
    expect(() => worldPosition(Infinity, 0, 0)).toThrow('Nonfinite');
    expect(() => pixelCoordinates(mixed, 3, 0)).toThrow('outside');
    expect(() => pixelCenterUV(mixed, 0, 0.5)).toThrow('outside');
    expect(() => detectorEdges({ ...mixed, nx: 513 })).toThrow('grid');
  });
  it('the default 512 detector is not incorrectly centered on its surface', () => {
    const edge = detectorEdges({ ny: 512, nx: 512, dx: 4e-6, dy: 4e-6 });
    expect(edge.xMin).toBeCloseTo(-1026e-6, 15); expect(edge.xMax).toBeCloseTo(1022e-6, 15);
    expect(edge.centerX).toBe(-2e-6); expect(edge.centerY).toBe(-2e-6);
  });
});
