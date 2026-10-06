/** V2b transient transport. Python public V0/V2a remains authoritative. */
import { parseStrictJSON, readBoundedResponse, structuralEqual, type GridSpec, type SourceSpec } from './contracts';

export interface TwoArmSpecification {
  arm_0_distance_m: number; arm_1_distance_m: number; relative_phase_rad: number;
}
export interface TwoPathExperiment {
  wavelength_m: number; grid: GridSpec; source: SourceSpec; two_arm_spec: TwoArmSpecification;
}
export interface FixedTwoPathExperiment {
  wavelength_m: number; grid: GridSpec; source: SourceSpec; arm_0_distance_m: number; arm_1_distance_m: number;
}
export interface TwoPathEnvelope {
  protocol_version: 1; message_type: 'two_path_submission'; request_id: string; experiment: TwoPathExperiment;
}
export interface TwoPathValidationReply {
  protocol_version: 1; message_type: 'two_path_validation'; request_id: string;
  experiment_sha256: string; experiment: TwoPathExperiment;
}
export const SWEEP_PHASES_RAD: readonly number[] = Object.freeze([
  0, 0.39269908169872414, 0.7853981633974483, 1.1780972450961724,
  1.5707963267948966, 1.9634954084936207, 2.356194490192345, 2.748893571891069,
  3.141592653589793, 3.5342917352885173, 3.9269908169872414, 4.319689898685965,
  4.71238898038469, 5.105088062083414, 5.497787143782138, 5.890486225480862,
  6.283185307179586,
]);
export interface TwoPathSweepEnvelope {
  protocol_version: 1; message_type: 'two_path_sweep_submission'; request_id: string;
  fixed_experiment: FixedTwoPathExperiment; phases_rad: readonly number[];
}
export type NormPair = readonly [number, number];
export interface TwoPathNorms {
  inputs: NormPair; split: NormPair; propagated: NormPair; combiner: NormPair; outputs: NormPair;
}
export interface TwoPathDiagnostics {
  inputs_total: number; split_total: number; propagated_total: number; combiner_total: number; outputs_total: number;
  split_delta: number; propagation_delta: number; phase_delta: number; recombination_delta: number; total_delta: number;
  output_fractions: readonly [number | null, number | null]; total_output_ratio: number | null;
}
export interface DecodedTwoPathResult {
  readonly requestId: string; readonly experimentSha256: string; readonly experiment: TwoPathExperiment;
  readonly ports: readonly [Readonly<{ id: 'port_0'; intensity: Float64Array; intensityMax: number }>,
    Readonly<{ id: 'port_1'; intensity: Float64Array; intensityMax: number }>];
  readonly x: Float64Array; readonly y: Float64Array;
  readonly norms: TwoPathNorms; readonly diagnostics: TwoPathDiagnostics;
}
export interface SweepRow {
  readonly index: number; readonly phase_rad: number; readonly input_norm: number;
  readonly output_norms: NormPair; readonly output_fractions: readonly [number | null, number | null];
  readonly total_output_ratio: number | null; readonly split_delta: number; readonly propagation_delta: number;
  readonly phase_delta: number; readonly recombination_delta: number; readonly total_delta: number;
}
export interface DecodedTwoPathSweep {
  readonly requestId: string; readonly fixedExperimentSha256: string; readonly fixedExperiment: FixedTwoPathExperiment;
  readonly phasesRad: readonly number[]; readonly status: 'complete' | 'failed'; readonly requestedCount: 17;
  readonly completedCount: number; readonly failedIndex: number | null; readonly rows: readonly SweepRow[];
  readonly error: Readonly<{ code: string; message: string }> | null; readonly httpStatus: number;
}
export interface TwoPathAPI {
  validate(envelope: TwoPathEnvelope): Promise<TwoPathValidationReply>;
  simulate(envelope: TwoPathEnvelope): Promise<ArrayBuffer>;
  sweep(envelope: TwoPathSweepEnvelope): Promise<{ body: unknown; httpStatus: number }>;
}
export const MAX_TWO_PATH_REQUEST_BYTES = 32768;
export const MAX_TWO_PATH_HEADER_BYTES = 16384;
export const MAX_TWO_PATH_RESPONSE_BYTES = 4218896;
export const MAX_TWO_PATH_SWEEP_BYTES = 65536;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const SHA = /^[0-9a-f]{64}$/;
function fail(message: string): never { throw new Error(`V2b protocol: ${message}`); }
function record(value: unknown, name: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(`${name}: expected object`);
  return value as Record<string, unknown>;
}
function keys(value: Record<string, unknown>, expected: readonly string[], name: string): void {
  const actual = Object.keys(value);
  if (actual.length !== expected.length || actual.some(k => !expected.includes(k))) fail(`${name}: incorrect keys`);
}
function finite(value: unknown, name: string, nonnegative = false, positive = false): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || nonnegative && value < 0 || positive && value <= 0) {
    fail(`${name}: invalid finite number`);
  }
  return value;
}
function integer(value: unknown, name: string, low = 0, high = Number.MAX_SAFE_INTEGER): number {
  const n = finite(value, name);
  if (!Number.isSafeInteger(n) || n < low || n > high) fail(`${name}: invalid integer`);
  return n;
}
function identity(value: unknown): string {
  if (typeof value !== 'string' || !UUID.test(value)) fail('invalid canonical UUIDv4');
  return value;
}
function hash(value: unknown): string {
  if (typeof value !== 'string' || !SHA.test(value)) fail('invalid specification hash');
  return value;
}
function frozen<T>(value: T): T {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.values(value).forEach(item => frozen(item)); Object.freeze(value);
  }
  return value;
}
/** Browser phase -0 becomes +0 before request identity; every nonzero phase is retained. */
export function freezeTwoPathExperiment(experiment: TwoPathExperiment): TwoPathExperiment {
  const copy = structuredClone(experiment);
  if (copy.source.phase_rad === 0) copy.source.phase_rad = 0;
  if (copy.two_arm_spec.relative_phase_rad === 0) copy.two_arm_spec.relative_phase_rad = 0;
  return frozen(copy);
}
export function cloneTwoPathExperiment(experiment: TwoPathExperiment): TwoPathExperiment { return structuredClone(experiment); }
export function fixedTwoPathExperiment(experiment: TwoPathExperiment): FixedTwoPathExperiment {
  const copy = freezeTwoPathExperiment(experiment);
  return frozen({ wavelength_m: copy.wavelength_m, grid: copy.grid, source: copy.source,
    arm_0_distance_m: copy.two_arm_spec.arm_0_distance_m, arm_1_distance_m: copy.two_arm_spec.arm_1_distance_m });
}
function sampling(value: Record<string, unknown>, cap: number): void {
  finite(value.wavelength_m, 'wavelength_m', false, true);
  const grid = record(value.grid, 'grid'); keys(grid, ['ny', 'nx', 'dy', 'dx'], 'grid');
  integer(grid.ny, 'ny', 1, cap); integer(grid.nx, 'nx', 1, cap);
  finite(grid.dx, 'dx', false, true); finite(grid.dy, 'dy', false, true);
  const source = record(value.source, 'source');
  if (source.kind === 'uniform') keys(source, ['kind', 'amplitude', 'phase_rad'], 'uniform source');
  else if (source.kind === 'gaussian') {
    keys(source, ['kind', 'amplitude', 'phase_rad', 'waist_radius_m', 'waist_z_m', 'center_x_m', 'center_y_m'], 'gaussian source');
    finite(source.waist_radius_m, 'waist_radius_m', false, true);
    for (const name of ['waist_z_m', 'center_x_m', 'center_y_m']) finite(source[name], name);
  } else fail('unsupported source kind');
  finite(source.amplitude, 'amplitude', true); finite(source.phase_rad, 'source phase_rad');
}
export function assertTwoPathExperiment(value: unknown): asserts value is TwoPathExperiment {
  const experiment = record(value, 'experiment');
  keys(experiment, ['wavelength_m', 'grid', 'source', 'two_arm_spec'], 'experiment'); sampling(experiment, 512);
  const spec = record(experiment.two_arm_spec, 'two_arm_spec');
  keys(spec, ['arm_0_distance_m', 'arm_1_distance_m', 'relative_phase_rad'], 'two_arm_spec');
  finite(spec.arm_0_distance_m, 'arm_0_distance_m', true); finite(spec.arm_1_distance_m, 'arm_1_distance_m', true);
  finite(spec.relative_phase_rad, 'relative_phase_rad');
}
function assertFixed(value: unknown): asserts value is FixedTwoPathExperiment {
  const fixed = record(value, 'fixed_experiment');
  keys(fixed, ['wavelength_m', 'grid', 'source', 'arm_0_distance_m', 'arm_1_distance_m'], 'fixed_experiment'); sampling(fixed, 128);
  finite(fixed.arm_0_distance_m, 'arm_0_distance_m', true); finite(fixed.arm_1_distance_m, 'arm_1_distance_m', true);
}
export function validateTwoPathReply(value: unknown, submitted: TwoPathEnvelope): TwoPathValidationReply {
  const reply = record(value, 'validation reply');
  keys(reply, ['protocol_version', 'message_type', 'request_id', 'experiment_sha256', 'experiment'], 'validation reply');
  if (reply.protocol_version !== 1 || reply.message_type !== 'two_path_validation') fail('validation version/type');
  const request = identity(reply.request_id);
  if (request !== identity(submitted.request_id)) fail('validation request identity mismatch');
  assertTwoPathExperiment(reply.experiment);
  if (!structuralEqual(reply.experiment, submitted.experiment)) fail('validation experiment echo mismatch');
  // Server-originated -0 may remain represented; this is not a browser serialization claim.
  return frozen({ protocol_version: 1, message_type: 'two_path_validation', request_id: request,
    experiment_sha256: hash(reply.experiment_sha256), experiment: structuredClone(reply.experiment) });
}
function pair(value: unknown, name: string): NormPair {
  if (!Array.isArray(value) || value.length !== 2) fail(`${name}: expected ordered pair`);
  return Object.freeze([finite(value[0], name, true), finite(value[1], name, true)]) as NormPair;
}
function ratio(value: unknown, name: string, denominator: number): number | null {
  if (denominator === 0) { if (value !== null) fail(`${name}: expected null at zero input`); return null; }
  return finite(value, name, true);
}
function diagnostics(value: unknown, norms: TwoPathNorms): TwoPathDiagnostics {
  const data = record(value, 'diagnostics');
  const totals = ['inputs_total', 'split_total', 'propagated_total', 'combiner_total', 'outputs_total'] as const;
  const deltas = ['split_delta', 'propagation_delta', 'phase_delta', 'recombination_delta', 'total_delta'] as const;
  keys(data, [...totals, ...deltas, 'output_fractions', 'total_output_ratio'], 'diagnostics');
  const names = ['inputs', 'split', 'propagated', 'combiner', 'outputs'] as const;
  for (let i = 0; i < totals.length; i++) {
    const expected = norms[names[i]][0] + norms[names[i]][1];
    if (finite(data[totals[i]], totals[i], true) !== expected) fail(`${totals[i]} scalar consistency`);
  }
  const total = totals.map(name => data[name] as number);
  const differences = [total[1] - total[0], total[2] - total[1], total[3] - total[2], total[4] - total[3], total[4] - total[0]];
  deltas.forEach((name, i) => { if (finite(data[name], name) !== differences[i]) fail(`${name} scalar consistency`); });
  if (!Array.isArray(data.output_fractions) || data.output_fractions.length !== 2) fail('output_fractions pair');
  const fractions = data.output_fractions.map((value, i) => {
    const parsed = ratio(value, 'output_fractions', total[0]);
    if (parsed !== (total[0] === 0 ? null : norms.outputs[i] / total[0])) fail('original-input fraction consistency');
    return parsed;
  });
  const totalRatio = ratio(data.total_output_ratio, 'total_output_ratio', total[0]);
  if (totalRatio !== (total[0] === 0 ? null : total[4] / total[0])) fail('total_output_ratio consistency');
  return frozen({ ...data, output_fractions: fractions, total_output_ratio: totalRatio }) as unknown as TwoPathDiagnostics;
}
/** Complete ordered decoding precedes publication. No stage norm is reduced from display arrays. */
export function decodeTwoPathResult(frame: ArrayBuffer, submitted: TwoPathEnvelope): DecodedTwoPathResult {
  if (!(frame instanceof ArrayBuffer) || frame.byteLength < 16 || frame.byteLength > MAX_TWO_PATH_RESPONSE_BYTES) fail('frame length/cap');
  assertTwoPathExperiment(submitted.experiment); identity(submitted.request_id);
  const bytes = new Uint8Array(frame); const view = new DataView(frame);
  if ([79, 72, 76, 65, 66, 50, 80, 0].some((byte, i) => bytes[i] !== byte)) fail('magic');
  if (view.getUint32(12, true) !== 0) fail('reserved bytes');
  const headerLength = view.getUint32(8, true);
  if (headerLength < 2 || headerLength > MAX_TWO_PATH_HEADER_BYTES) fail('header length/cap');
  const start = 16 + Math.ceil(headerLength / 8) * 8;
  if (start > frame.byteLength) fail('truncated header');
  for (let i = 16 + headerLength; i < start; i++) if (bytes[i] !== 0) fail('nonzero padding');
  let text: string;
  try { text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes.subarray(16, 16 + headerLength)); }
  catch { return fail('invalid UTF-8 header'); }
  const header = record(parseStrictJSON(text), 'header');
  keys(header, ['protocol_version', 'message_type', 'request_id', 'experiment_sha256', 'experiment', 'ports', 'norms', 'diagnostics', 'arrays', 'intensity_max'], 'header');
  if (header.message_type !== 'two_path_result' || header.protocol_version !== 1) fail('result type/version');
  const reply = validateTwoPathReply({ protocol_version: 1, message_type: 'two_path_validation',
    request_id: header.request_id, experiment_sha256: header.experiment_sha256, experiment: header.experiment }, submitted);
  if (!structuralEqual(header.ports, ['port_0', 'port_1'])) fail('ordered port identities');
  const normRecord = record(header.norms, 'norms'); keys(normRecord, ['inputs', 'split', 'propagated', 'combiner', 'outputs'], 'norms');
  const norms = frozen(Object.fromEntries(Object.entries(normRecord).map(([name, value]) => [name, pair(value, name)]))) as unknown as TwoPathNorms;
  if (norms.inputs[1] !== 0) fail('fixed second input must be zero');
  const checkedDiagnostics = diagnostics(header.diagnostics, norms);
  const { nx, ny, dx, dy } = reply.experiment.grid;
  const planeBytes = nx * ny * 8;
  const expected = [
    { name: 'intensity_port_0', role: 'intensity', port_id: 'port_0', shape: [ny, nx], offset: 0, nbytes: planeBytes, units: 'amplitude_unit^2' },
    { name: 'intensity_port_1', role: 'intensity', port_id: 'port_1', shape: [ny, nx], offset: planeBytes, nbytes: planeBytes, units: 'amplitude_unit^2' },
    { name: 'x_m', role: 'coordinate', port_id: null, shape: [nx], offset: 2 * planeBytes, nbytes: nx * 8, units: 'm' },
    { name: 'y_m', role: 'coordinate', port_id: null, shape: [ny], offset: 2 * planeBytes + nx * 8, nbytes: ny * 8, units: 'm' },
  ];
  if (!Array.isArray(header.arrays) || header.arrays.length !== 4) fail('four array descriptors required');
  if (frame.byteLength !== start + 8 * (2 * ny * nx + nx + ny)) fail('exact payload length/trailing bytes');
  const arrays: Float64Array[] = [];
  expected.forEach((description, index) => {
    const descriptor = record((header.arrays as unknown[])[index], 'descriptor');
    keys(descriptor, ['name', 'role', 'port_id', 'dtype', 'order', 'shape', 'offset_bytes', 'nbytes', 'units'], 'descriptor');
    if (descriptor.name !== description.name || descriptor.role !== description.role || descriptor.port_id !== description.port_id
        || descriptor.dtype !== 'float64-le' || descriptor.order !== 'C' || descriptor.units !== description.units
        || !structuralEqual(descriptor.shape, description.shape)) fail('descriptor role/port/dtype/order/shape/units');
    if (integer(descriptor.offset_bytes, 'offset') !== description.offset || integer(descriptor.nbytes, 'nbytes') !== description.nbytes) fail('descriptor gap/overlap/alignment/size');
    const array = new Float64Array(description.nbytes / 8);
    for (let i = 0; i < array.length; i++) array[i] = finite(view.getFloat64(start + description.offset + i * 8, true), description.name, index < 2);
    arrays.push(array);
  });
  const [i0, i1, x, y] = arrays;
  for (let c = 0; c < nx; c++) if (x[c] !== (c - Math.floor(nx / 2)) * dx) fail('x coordinate mismatch');
  for (let r = 0; r < ny; r++) if (y[r] !== (r - Math.floor(ny / 2)) * dy) fail('y coordinate mismatch');
  const maxima = pair(header.intensity_max, 'intensity_max');
  [i0, i1].forEach((array, index) => {
    let maximum = 0; for (const value of array) maximum = Math.max(maximum, value);
    if (maximum !== maxima[index]) fail(`port ${index} intensity maximum mismatch`);
  });
  return Object.freeze({ requestId: reply.request_id, experimentSha256: reply.experiment_sha256, experiment: reply.experiment,
    ports: Object.freeze([Object.freeze({ id: 'port_0' as const, intensity: i0, intensityMax: maxima[0] }),
      Object.freeze({ id: 'port_1' as const, intensity: i1, intensityMax: maxima[1] })]) as DecodedTwoPathResult['ports'],
    x, y, norms, diagnostics: checkedDiagnostics });
}
function errorDetail(value: unknown): Readonly<{ code: string; message: string }> {
  const data = record(value, 'error'); keys(data, ['code', 'message'], 'error');
  if (typeof data.code !== 'string' || !/^[a-z][a-z0-9_]{0,63}$/.test(data.code)
      || typeof data.message !== 'string' || data.message.length > 300) fail('bounded error code/message');
  return Object.freeze({ code: data.code, message: data.message });
}
export function validateTwoPathSweep(value: unknown, submitted: TwoPathSweepEnvelope, httpStatus: number): DecodedTwoPathSweep {
  const data = record(value, 'sweep reply');
  keys(data, ['protocol_version', 'message_type', 'request_id', 'fixed_experiment_sha256', 'fixed_experiment', 'phases_rad', 'status', 'requested_count', 'completed_count', 'failed_index', 'rows', 'error'], 'sweep reply');
  if (data.protocol_version !== 1 || data.message_type !== 'two_path_sweep_result') fail('sweep type/version');
  const request = identity(data.request_id);
  if (request !== identity(submitted.request_id)) fail('sweep request identity mismatch');
  assertFixed(data.fixed_experiment);
  if (!structuralEqual(data.fixed_experiment, submitted.fixed_experiment)) fail('sweep fixed experiment echo mismatch');
  if (!structuralEqual(data.phases_rad, SWEEP_PHASES_RAD) || !structuralEqual(data.phases_rad, submitted.phases_rad)) fail('sweep exact phase list');
  if (data.requested_count !== 17) fail('sweep requested count');
  const count = integer(data.completed_count, 'completed_count', 0, 17);
  if (!Array.isArray(data.rows) || data.rows.length !== count) fail('sweep row count');
  if (data.status === 'complete') {
    if (httpStatus !== 200 || count !== 17 || data.failed_index !== null || data.error !== null) fail('complete sweep status/count/error');
  } else if (data.status === 'failed') {
    if (![422, 500].includes(httpStatus) || count >= 17 || integer(data.failed_index, 'failed_index', 0, 16) !== count) fail('failed sweep status/prefix');
    errorDetail(data.error);
  } else fail('sweep status');
  const rows: SweepRow[] = data.rows.map((value, index) => {
    const row = record(value, 'sweep row');
    keys(row, ['index', 'phase_rad', 'input_norm', 'output_norms', 'output_fractions', 'total_output_ratio', 'split_delta', 'propagation_delta', 'phase_delta', 'recombination_delta', 'total_delta'], 'sweep row');
    if (row.index !== index || finite(row.phase_rad, 'phase_rad') !== SWEEP_PHASES_RAD[index]) fail('genuine contiguous sweep index/phase');
    const input = finite(row.input_norm, 'input_norm', true); const output = pair(row.output_norms, 'output_norms');
    if (!Array.isArray(row.output_fractions) || row.output_fractions.length !== 2) fail('sweep fraction pair');
    const fractions = row.output_fractions.map((item, port) => {
      const value = ratio(item, 'output fraction', input);
      if (value !== (input === 0 ? null : output[port] / input)) fail('sweep original-input fractions'); return value;
    });
    const totalRatio = ratio(row.total_output_ratio, 'total ratio', input);
    if (totalRatio !== (input === 0 ? null : (output[0] + output[1]) / input)) fail('sweep total ratio');
    for (const name of ['split_delta', 'propagation_delta', 'phase_delta', 'recombination_delta', 'total_delta']) finite(row[name], name);
    if (row.total_delta !== output[0] + output[1] - input) fail('sweep signed total delta');
    return frozen({ ...row, output_norms: output, output_fractions: fractions, total_output_ratio: totalRatio }) as unknown as SweepRow;
  });
  return frozen({ requestId: request, fixedExperimentSha256: hash(data.fixed_experiment_sha256),
    fixedExperiment: structuredClone(data.fixed_experiment), phasesRad: [...SWEEP_PHASES_RAD], status: data.status,
    requestedCount: 17, completedCount: count, failedIndex: data.failed_index as number | null, rows,
    error: data.error === null ? null : errorDetail(data.error), httpStatus });
}
export function createTwoPathFetchAPI(fetchImpl: typeof fetch = globalThis.fetch.bind(globalThis)): TwoPathAPI {
  const post = async (endpoint: string, envelope: TwoPathEnvelope | TwoPathSweepEnvelope, cap: number, mime: string) => {
    identity(envelope.request_id);
    const body = JSON.stringify(envelope);
    if (new TextEncoder().encode(body).byteLength > MAX_TWO_PATH_REQUEST_BYTES) fail('request body cap');
    const response = await fetchImpl(`/api/v2b/${endpoint}`, { method: 'POST', credentials: 'same-origin', redirect: 'error',
      headers: { 'Content-Type': 'application/json', Accept: mime }, body });
    const type = response.headers.get('content-type')?.split(';', 1)[0].trim();
    if (!response.ok && endpoint === 'sweep' && [422, 500].includes(response.status) && type === 'application/json') {
      const bytes = await readBoundedResponse(response, MAX_TWO_PATH_SWEEP_BYTES);
      const parsed = parseStrictJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
      if (record(parsed, 'error reply').message_type === 'two_path_sweep_result') return { bytes, status: response.status };
      const detail = errorDetail(record(parsed, 'error reply').error);
      throw new Error(`HTTP ${response.status}: ${detail.message}`);
    }
    if (!response.ok) {
      const bytes = await readBoundedResponse(response, MAX_TWO_PATH_HEADER_BYTES);
      let message = `HTTP ${response.status}`;
      if (type === 'application/json') {
        try { message += `: ${errorDetail(record(parseStrictJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes)), 'error reply').error).message}`; }
        catch { /* Preserve HTTP failure without an invented success. */ }
      }
      throw new Error(message);
    }
    if (type !== mime) { await response.body?.cancel('V2b MIME mismatch'); fail('HTTP content-type'); }
    return { bytes: await readBoundedResponse(response, cap), status: response.status };
  };
  return {
    async validate(envelope) {
      const { bytes } = await post('validate', envelope, MAX_TWO_PATH_HEADER_BYTES, 'application/json');
      return validateTwoPathReply(parseStrictJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes)), envelope);
    },
    async simulate(envelope) { return (await post('simulate', envelope, MAX_TWO_PATH_RESPONSE_BYTES, 'application/octet-stream')).bytes; },
    async sweep(envelope) {
      const { bytes, status } = await post('sweep', envelope, MAX_TWO_PATH_SWEEP_BYTES, 'application/json');
      return { body: parseStrictJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes)), httpStatus: status };
    },
  };
}
