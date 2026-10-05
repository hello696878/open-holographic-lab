import type { GridSpec } from './contracts';

function requireGrid(grid: GridSpec): void {
  if (!Number.isInteger(grid.nx) || !Number.isInteger(grid.ny) || grid.nx < 1 || grid.ny < 1
      || grid.nx > 512 || grid.ny > 512 || !Number.isFinite(grid.dx) || !Number.isFinite(grid.dy)
      || grid.dx <= 0 || grid.dy <= 0) throw new Error('Expected V1 grid dimensions 1–512 and positive finite pitches in metres');
}
export function worldPosition(x_m: number, y_m: number, z_m: number): { x: number; y: number; z: number } {
  const point = { x: 1000 * x_m, y: -1000 * y_m, z: 100 * z_m };
  if (!Object.values(point).every(Number.isFinite)) throw new Error('Nonfinite world coordinate');
  return point;
}
/** Full pixel-cell edges in physical metres, including the even-axis half-cell offset. */
export function detectorEdges(grid: GridSpec) {
  requireGrid(grid);
  const xMin = (-Math.floor(grid.nx / 2) - 0.5) * grid.dx;
  const xMax = (grid.nx - 1 - Math.floor(grid.nx / 2) + 0.5) * grid.dx;
  const yMin = (-Math.floor(grid.ny / 2) - 0.5) * grid.dy;
  const yMax = (grid.ny - 1 - Math.floor(grid.ny / 2) + 0.5) * grid.dy;
  return { xMin, xMax, yMin, yMax, width: grid.nx * grid.dx, height: grid.ny * grid.dy,
    centerX: ((grid.nx - 1) / 2 - Math.floor(grid.nx / 2)) * grid.dx,
    centerY: ((grid.ny - 1) / 2 - Math.floor(grid.ny / 2)) * grid.dy };
}
function requirePixel(grid: GridSpec, row: number, column: number): void {
  requireGrid(grid);
  if (!Number.isInteger(row) || !Number.isInteger(column) || row < 0 || row >= grid.ny || column < 0 || column >= grid.nx) {
    throw new Error(`Pixel outside detector: row=${row}, column=${column}`);
  }
}
export function pixelCoordinates(grid: GridSpec, row: number, column: number): { x_m: number; y_m: number } {
  requirePixel(grid, row, column);
  return { x_m: (column - Math.floor(grid.nx / 2)) * grid.dx, y_m: (row - Math.floor(grid.ny / 2)) * grid.dy };
}
export function pixelCenterUV(grid: GridSpec, row: number, column: number): { u: number; v: number } {
  requirePixel(grid, row, column);
  return { u: (column + 0.5) / grid.nx, v: 1 - (row + 0.5) / grid.ny };
}
/** Half-open cells: physical left/top included; right/bottom excluded. Never clamp. */
export function pixelFromUV(grid: GridSpec, u: number, v: number): { row: number; column: number } | null {
  requireGrid(grid);
  if (!Number.isFinite(u) || !Number.isFinite(v) || u < 0 || u >= 1 || v <= 0 || v > 1) return null;
  const row = Math.floor((1 - v) * grid.ny); const column = Math.floor(u * grid.nx);
  if (row < 0 || row >= grid.ny || column < 0 || column >= grid.nx) return null;
  return { row, column };
}
