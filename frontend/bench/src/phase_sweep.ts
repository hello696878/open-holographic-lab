/** Scalar sweep presentation and accounted app-owned byte budgets, not browser heap/GPU claims. */
import type { DecodedResult, GridSpec } from './contracts';
import { MAX_TWO_PATH_HEADER_BYTES, type DecodedTwoPathResult, type DecodedTwoPathSweep } from './two_path_contracts';
export { SWEEP_PHASES_RAD } from './two_path_contracts';
export const OWNED_PERSISTENT_BUDGET_BYTES = 16 * 1024 * 1024;
export const OWNED_TRANSIENT_BUDGET_BYTES = 32 * 1024 * 1024;
/** Conservative phase-wise reachable app-owned bytes, not total heap/GPU memory.
 * retainedOwnedBytes excludes the incoming decoded result. Transport chunks leave
 * ownership when readBoundedResponse returns; its joined frame leaves ownership
 * after complete decoding. Presentation holds pair RGBA, pair canvas stores and
 * at most two one-port conversion buffers. Thus the phases use max, not their sum.
 */
export function estimateDualOperationBytes(grid: GridSpec, retainedOwnedBytes = 0): Readonly<{
  payloadBytes: number; maxFrameBytes: number; transportPeakBytes: number; decodePeakBytes: number;
  preparationPeakBytes: number; peakOwnedBytes: number;
}> {
  if (!Number.isInteger(grid.nx) || !Number.isInteger(grid.ny) || grid.nx < 1 || grid.ny < 1 || grid.nx > 512 || grid.ny > 512
      || !Number.isSafeInteger(retainedOwnedBytes) || retainedOwnedBytes < 0) throw new Error('Invalid bounded grid/retained byte count');
  const pixels = grid.nx * grid.ny;
  const payloadBytes = 8 * (2 * pixels + grid.nx + grid.ny);
  const maxFrameBytes = 16 + MAX_TWO_PATH_HEADER_BYTES + payloadBytes;
  const transportPeakBytes = retainedOwnedBytes + 2 * maxFrameBytes;
  const decodePeakBytes = retainedOwnedBytes + maxFrameBytes + payloadBytes;
  const preparationPeakBytes = retainedOwnedBytes + payloadBytes + 24 * pixels;
  return Object.freeze({ payloadBytes, maxFrameBytes, transportPeakBytes, decodePeakBytes, preparationPeakBytes,
    peakOwnedBytes: Math.max(transportPeakBytes, decodePeakBytes, preparationPeakBytes) });
}
export function sweepPlotPoints(sweep: DecodedTwoPathSweep, port: 0 | 1, range = { min: 0, max: 1 }): readonly {
  index: number; phaseRad: number; value: number | null; x: number; y: number | null; outOfRange: boolean;
}[] {
  if (![0, 1].includes(port) || !Number.isFinite(range.min) || !Number.isFinite(range.max) || range.max <= range.min) throw new Error('Invalid sweep port/range');
  return Object.freeze(sweep.rows.map(row => {
    const value = row.output_fractions[port];
    return Object.freeze({ index: row.index, phaseRad: row.phase_rad, value,
      x: row.phase_rad / sweep.phasesRad.at(-1)!, y: value === null ? null : 1 - (value - range.min) / (range.max - range.min),
      outOfRange: value !== null && (value < range.min || value > range.max) });
  }));
}
/** Deduplicate current/last aliases; includes the one recoverable preparation-failure exception. */
export function countedResultBytes(sequential: DecodedResult | null, dual: DecodedTwoPathResult | null,
    completedNumerical: DecodedTwoPathResult | null, sweep: DecodedTwoPathSweep | null): number {
  const buffers = new Set<ArrayBufferLike>();
  const add = (array: Float64Array | undefined) => { if (array) buffers.add(array.buffer); };
  add(sequential?.intensity); add(sequential?.x); add(sequential?.y);
  for (const result of [dual, completedNumerical]) {
    result?.ports.forEach(port => add(port.intensity)); add(result?.x); add(result?.y);
  }
  const arrayBytes = [...buffers].reduce((total, buffer) => total + buffer.byteLength, 0);
  return arrayBytes + (sweep ? new TextEncoder().encode(JSON.stringify(sweep)).byteLength : 0);
}
