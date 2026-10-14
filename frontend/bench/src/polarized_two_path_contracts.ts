/** Closed V2g transport. Optics and public measurements remain in Python. */
import { parseStrictJSON, readBoundedResponse, structuralEqual, type GridSpec, type SourceSpec } from './contracts';
import { SWEEP_PHASES_RAD } from './two_path_contracts';
import type { ComplexPair } from './polarization_contracts';
export { SWEEP_PHASES_RAD } from './two_path_contracts';
export type PolarizedTwoPathAction = { id: string; kind: 'linear_polarizer'; axis_angle_rad: number }
  | { id: string; kind: 'linear_retarder'; axis_angle_rad: number; retardance_rad: number };
export interface PolarizedTwoPathArm { distance_m: number; actions: PolarizedTwoPathAction[] }
export interface PolarizedTwoPathExperiment {
  schema_version: 1; model_contract: 'v2g_ideal_polarized_two_path_v1'; wavelength_m: number; grid: GridSpec;
  source: SourceSpec; coefficients: ComplexPair; arm_0: PolarizedTwoPathArm; arm_1: PolarizedTwoPathArm;
  relative_phase_rad: number; analyzer: { enabled: boolean; axis_angle_rad: number };
}
export type FixedPolarizedTwoPathExperiment = Omit<PolarizedTwoPathExperiment, 'relative_phase_rad'>;
export interface PolarizedTwoPathEnvelope { protocol_version: 1; message_type: 'polarized_two_path_submission';
  request_id: string; experiment_sha256: string | null; experiment: PolarizedTwoPathExperiment }
export interface PolarizedTwoPathSweepEnvelope { protocol_version: 1; message_type: 'polarized_two_path_sweep_submission';
  request_id: string; fixed_experiment_sha256: string | null; fixed_experiment: FixedPolarizedTwoPathExperiment; phases_rad: readonly number[] }
export interface PolarizedTwoPathValidation { protocol_version: 1; message_type: 'polarized_two_path_validation';
  request_id: string; experiment_sha256: string; experiment: PolarizedTwoPathExperiment }
export interface PolarizedTwoPathSweepValidation { protocol_version: 1; message_type: 'polarized_two_path_sweep_validation';
  request_id: string; fixed_experiment_sha256: string; fixed_experiment: FixedPolarizedTwoPathExperiment;
  phases_rad: readonly number[]; sweep_sha256: string }
export type NormPair = readonly [number, number];
export type RatioPair = readonly [number | null, number | null];
export interface PolarizedTwoPathNorms { inputs: NormPair; split: NormPair; propagated: NormPair; elements: NormPair;
  combiner: NormPair; outputs: NormPair; arm_action_norms: readonly [readonly number[], readonly number[]] }
export interface PolarizedTwoPathDiagnostics {
  inputs_total: number; split_total: number; propagated_total: number; elements_total: number; combiner_total: number; outputs_total: number;
  split_delta: number; propagation_delta: number; elements_delta: number; phase_delta: number; recombination_delta: number; total_delta: number;
  propagation_deltas: NormPair; element_deltas: NormPair; phase_deltas: NormPair;
  arm_action_deltas: readonly [readonly number[], readonly number[]]; output_fractions: RatioPair; total_output_ratio: number | null;
}
export interface PolarizedTwoPathAnalysisPort { id: 'port_0' | 'port_1'; raw_norm: number; analyzed_norm: number; removed_norm: number;
  original_input_ratio: number | null; raw_output_ratio: number | null }
export type PolarizedTwoPathAnalysis = Readonly<{ enabled: false; axis_angle_rad: number; ports: null; total_norm: null;
  total_removed_norm: null; total_original_input_ratio: null }> | Readonly<{ enabled: true; axis_angle_rad: number;
  ports: readonly [PolarizedTwoPathAnalysisPort, PolarizedTwoPathAnalysisPort]; total_norm: number;
  total_removed_norm: number; total_original_input_ratio: number | null }>;
export interface PolarizedTwoPathPort { readonly id: 'port_0' | 'port_1'; readonly intensity: Float64Array; readonly intensityMax: number }
export interface DecodedPolarizedTwoPathResult {
  readonly requestId: string; readonly experimentSha256: string; readonly experiment: PolarizedTwoPathExperiment;
  readonly norms: PolarizedTwoPathNorms; readonly diagnostics: PolarizedTwoPathDiagnostics; readonly analysis: PolarizedTwoPathAnalysis;
  readonly rawPorts: readonly [PolarizedTwoPathPort, PolarizedTwoPathPort];
  readonly analyzedPorts: readonly [PolarizedTwoPathPort, PolarizedTwoPathPort] | null;
  readonly x: Float64Array; readonly y: Float64Array; readonly intensityMax: readonly number[];
}
export interface PolarizedTwoPathSweepRow { readonly index: number; readonly phase_rad: number; readonly norms: PolarizedTwoPathNorms;
  readonly diagnostics: PolarizedTwoPathDiagnostics; readonly analysis: PolarizedTwoPathAnalysis }
export interface DecodedPolarizedTwoPathSweep { readonly requestId: string; readonly fixedExperimentSha256: string;
  readonly sweepSha256: string; readonly fixedExperiment: FixedPolarizedTwoPathExperiment; readonly phasesRad: readonly number[];
  readonly status: 'complete' | 'failed'; readonly requestedCount: 17; readonly completedCount: number; readonly failedIndex: number | null;
  readonly rows: readonly PolarizedTwoPathSweepRow[]; readonly error: Readonly<{ code: string; message: string }> | null; readonly httpStatus: number }
export interface PolarizedTwoPathAPI { validate(envelope: PolarizedTwoPathEnvelope): Promise<PolarizedTwoPathValidation>;
  validateSweep(envelope: PolarizedTwoPathSweepEnvelope): Promise<PolarizedTwoPathSweepValidation>;
  simulate(envelope: PolarizedTwoPathEnvelope): Promise<ArrayBuffer>;
  sweep(envelope: PolarizedTwoPathSweepEnvelope): Promise<{ body: unknown; httpStatus: number }> }
export const MAX_POLARIZED_TWO_PATH_REQUEST_BYTES = 32768;
export const MAX_POLARIZED_TWO_PATH_HEADER_BYTES = 16384;
export const MAX_POLARIZED_TWO_PATH_DISABLED_RESPONSE_BYTES = 280592;
export const MAX_POLARIZED_TWO_PATH_RESPONSE_BYTES = 542736;
export const MAX_POLARIZED_TWO_PATH_SWEEP_BYTES = 65536;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const SHA = /^[0-9a-f]{64}$/;
const checkpoints = ['inputs', 'split', 'propagated', 'elements', 'combiner', 'outputs'] as const;
function fail(message: string): never { throw new Error(`V2g protocol: ${message}`); }
function record(value: unknown, name: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(`${name}: expected object`); return value as Record<string, unknown>;
}
function keys(value: Record<string, unknown>, expected: readonly string[], name: string): void {
  if (Object.keys(value).length !== expected.length || Object.keys(value).some(key => !expected.includes(key))) fail(`${name}: incorrect keys`);
}
function finite(value: unknown, name: string, nonnegative = false, positive = false): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || nonnegative && value < 0 || positive && value <= 0) fail(`${name}: invalid finite number`); return value;
}
function integer(value: unknown, name: string, low: number, high: number): number {
  const n = finite(value, name); if (!Number.isSafeInteger(n) || n < low || n > high) fail(`${name}: invalid integer`); return n;
}
function requestId(value: unknown): string { if (typeof value !== 'string' || !UUID.test(value)) fail('canonical UUIDv4'); return value; }
function hash(value: unknown): string { if (typeof value !== 'string' || !SHA.test(value)) fail('specification SHA'); return value; }
export function freezePolarizedTwoPath<T>(value: T): T {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) { Object.values(value).forEach(freezePolarizedTwoPath); Object.freeze(value); } return value;
}
export function freezePolarizedTwoPathExperiment(experiment: PolarizedTwoPathExperiment): PolarizedTwoPathExperiment {
  const copy = structuredClone(experiment);
  const zeros = (object: Record<string, unknown>) => { for (const [key, value] of Object.entries(object)) {
    if (typeof value === 'number' && value === 0) object[key] = 0;
    else if (value && typeof value === 'object') zeros(value as Record<string, unknown>);
  } }; zeros(copy as unknown as Record<string, unknown>); return freezePolarizedTwoPath(copy);
}
export function fixedPolarizedTwoPathExperiment(experiment: PolarizedTwoPathExperiment): FixedPolarizedTwoPathExperiment {
  const { relative_phase_rad: _phase, ...fixed } = freezePolarizedTwoPathExperiment(experiment); return freezePolarizedTwoPath(fixed);
}
/** Local extra check for nonzero decimal tokens that binary64 would erase. Legacy parsing is unchanged. */
export function parsePolarizedTwoPathJSON(text: string): unknown {
  const parsed = parseStrictJSON(text); let index = 0;
  while (index < text.length) {
    if (text[index] === '"') { index++; while (index < text.length) { if (text[index] === '\\') { index += 2; continue; } if (text[index++] === '"') break; } continue; }
    const match = /^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(text.slice(index));
    if (match) { const token = match[0]; if (Number(token) === 0 && /[1-9]/.test(token.split(/[eE]/, 1)[0])) fail('nonzero decimal underflow'); index += token.length; }
    else index++;
  } return parsed;
}
/** Static shape/domain checks only; the existing Python public validators are authoritative. */
export function assertPolarizedTwoPathExperiment(value: unknown): asserts value is PolarizedTwoPathExperiment {
  const data = record(value, 'experiment'); keys(data, ['schema_version', 'model_contract', 'wavelength_m', 'grid', 'source', 'coefficients', 'arm_0', 'arm_1', 'relative_phase_rad', 'analyzer'], 'experiment');
  if (data.schema_version !== 1 || data.model_contract !== 'v2g_ideal_polarized_two_path_v1') fail('experiment version/contract');
  finite(data.wavelength_m, 'wavelength', false, true);
  const grid = record(data.grid, 'grid'); keys(grid, ['ny', 'nx', 'dy', 'dx'], 'grid');
  integer(grid.ny, 'ny', 1, 128); integer(grid.nx, 'nx', 1, 128); finite(grid.dx, 'dx', false, true); finite(grid.dy, 'dy', false, true);
  const source = record(data.source, 'source');
  if (source.kind === 'uniform') keys(source, ['kind', 'amplitude', 'phase_rad'], 'uniform source');
  else if (source.kind === 'gaussian') { keys(source, ['kind', 'amplitude', 'phase_rad', 'waist_radius_m', 'waist_z_m', 'center_x_m', 'center_y_m'], 'Gaussian source');
    finite(source.waist_radius_m, 'waist radius', false, true); for (const key of ['waist_z_m', 'center_x_m', 'center_y_m']) finite(source[key], key);
  } else fail('source kind');
  finite(source.amplitude, 'amplitude', true); finite(source.phase_rad, 'source phase');
  const coefficients = record(data.coefficients, 'coefficients'); keys(coefficients, ['x', 'y'], 'coefficients');
  for (const axis of ['x', 'y']) { const c = record(coefficients[axis], axis); keys(c, ['re', 'im'], axis); finite(c.re, `${axis} real`); finite(c.im, `${axis} imaginary`); }
  const ids = new Set(['input', 'splitter', 'combiner', 'arm_0', 'arm_1', 'port_0', 'port_1', 'analyzer']);
  for (const name of ['arm_0', 'arm_1']) {
    const arm = record(data[name], name); keys(arm, ['distance_m', 'actions'], name); finite(arm.distance_m, `${name} distance`, true);
    if (!Array.isArray(arm.actions) || arm.actions.length > 2) fail('two ordered actions per arm');
    for (const value of arm.actions) { const action = record(value, 'action');
      if (action.kind === 'linear_polarizer') keys(action, ['id', 'kind', 'axis_angle_rad'], 'polarizer');
      else if (action.kind === 'linear_retarder') { keys(action, ['id', 'kind', 'axis_angle_rad', 'retardance_rad'], 'retarder'); finite(action.retardance_rad, 'retardance'); }
      else fail('action kind');
      if (typeof action.id !== 'string' || !/^[A-Za-z][A-Za-z0-9_-]{0,31}$/.test(action.id) || ids.has(action.id)) fail('unique action ID');
      ids.add(action.id); finite(action.axis_angle_rad, 'axis angle');
    }
  }
  finite(data.relative_phase_rad, 'relative phase'); const analyzer = record(data.analyzer, 'analyzer'); keys(analyzer, ['enabled', 'axis_angle_rad'], 'analyzer');
  if (typeof analyzer.enabled !== 'boolean') fail('exact analyzer boolean'); finite(analyzer.axis_angle_rad, 'saved analyzer angle');
}
function assertFixed(value: unknown): asserts value is FixedPolarizedTwoPathExperiment {
  const fixed = record(value, 'fixed experiment'); keys(fixed, ['schema_version', 'model_contract', 'wavelength_m', 'grid', 'source', 'coefficients', 'arm_0', 'arm_1', 'analyzer'], 'fixed experiment');
  assertPolarizedTwoPathExperiment({ ...fixed, relative_phase_rad: 0 });
}
export function validatePolarizedTwoPathReply(value: unknown, submitted: PolarizedTwoPathEnvelope): PolarizedTwoPathValidation {
  const data = record(value, 'validation'); keys(data, ['protocol_version', 'message_type', 'request_id', 'experiment_sha256', 'experiment'], 'validation');
  if (data.protocol_version !== 1 || data.message_type !== 'polarized_two_path_validation') fail('validation version/type');
  if (requestId(data.request_id) !== requestId(submitted.request_id)) fail('request identity'); assertPolarizedTwoPathExperiment(data.experiment);
  if (!structuralEqual(data.experiment, submitted.experiment)) fail('complete specification identity');
  const digest = hash(data.experiment_sha256); if (submitted.experiment_sha256 !== null && digest !== hash(submitted.experiment_sha256)) fail('validated specification SHA mismatch');
  return freezePolarizedTwoPath({ protocol_version: 1, message_type: 'polarized_two_path_validation', request_id: data.request_id as string,
    experiment_sha256: digest, experiment: structuredClone(data.experiment) });
}
export function validatePolarizedTwoPathSweepReply(value: unknown, submitted: PolarizedTwoPathSweepEnvelope): PolarizedTwoPathSweepValidation {
  const data = record(value, 'sweep validation'); keys(data, ['protocol_version', 'message_type', 'request_id', 'fixed_experiment_sha256', 'fixed_experiment', 'phases_rad', 'sweep_sha256'], 'sweep validation');
  if (data.protocol_version !== 1 || data.message_type !== 'polarized_two_path_sweep_validation') fail('sweep validation version/type');
  if (requestId(data.request_id) !== requestId(submitted.request_id)) fail('sweep request identity'); assertFixed(data.fixed_experiment);
  if (!structuralEqual(data.fixed_experiment, submitted.fixed_experiment) || !structuralEqual(data.phases_rad, SWEEP_PHASES_RAD)
      || !structuralEqual(data.phases_rad, submitted.phases_rad)) fail('complete fixed specification/phases identity');
  const digest = hash(data.fixed_experiment_sha256); if (submitted.fixed_experiment_sha256 !== null && digest !== hash(submitted.fixed_experiment_sha256)) fail('fixed specification SHA mismatch');
  return freezePolarizedTwoPath({ protocol_version: 1, message_type: 'polarized_two_path_sweep_validation', request_id: data.request_id as string,
    fixed_experiment_sha256: digest, fixed_experiment: structuredClone(data.fixed_experiment), phases_rad: [...SWEEP_PHASES_RAD], sweep_sha256: hash(data.sweep_sha256) });
}
function pair(value: unknown, name: string, nonnegative = true): NormPair {
  if (!Array.isArray(value) || value.length !== 2) fail(`${name}: pair required`); return Object.freeze([finite(value[0], name, nonnegative), finite(value[1], name, nonnegative)]);
}
function ratio(value: unknown, denominator: number, name: string, numerator?: number): number | null {
  if (denominator === 0) { if (value !== null) fail(`${name}: zero denominator requires null`); return null; }
  const result = finite(value, name, true);
  if (numerator === 0 && result !== 0 || numerator !== undefined && numerator > 0 && result === 0) fail(`${name}: zero/nonzero public ratio domain`);
  return result; // Public Python ratios are authoritative; no JS optical recomputation.
}
function measurement(value: { norms: unknown; diagnostics: unknown; analysis: unknown }, experiment: FixedPolarizedTwoPathExperiment):
    { norms: PolarizedTwoPathNorms; diagnostics: PolarizedTwoPathDiagnostics; analysis: PolarizedTwoPathAnalysis } {
  const n = record(value.norms, 'norms'); keys(n, [...checkpoints, 'arm_action_norms'], 'norms');
  const norms = Object.fromEntries(checkpoints.map(key => [key, pair(n[key], key)])) as unknown as PolarizedTwoPathNorms;
  if (!Array.isArray(n.arm_action_norms) || n.arm_action_norms.length !== 2) fail('two action histories');
  norms.arm_action_norms = Object.freeze(n.arm_action_norms.map((v, i) => {
    if (!Array.isArray(v) || v.length !== experiment[i === 0 ? 'arm_0' : 'arm_1'].actions.length) fail('action history length');
    const history = Object.freeze(v.map(item => finite(item, 'action norm', true)));
    if (norms.elements[i] !== (history.at(-1) ?? norms.propagated[i])) fail('same-reduction action endpoint'); return history;
  })) as unknown as PolarizedTwoPathNorms['arm_action_norms'];
  if (norms.inputs[1] !== 0 || norms.combiner[0] !== norms.elements[0]) fail('untouched checkpoint identity');
  const d = record(value.diagnostics, 'diagnostics');
  const totals = checkpoints.map(key => `${key}_total`), deltas = ['split_delta', 'propagation_delta', 'elements_delta', 'phase_delta', 'recombination_delta', 'total_delta'];
  keys(d, [...totals, ...deltas, 'propagation_deltas', 'element_deltas', 'phase_deltas', 'arm_action_deltas', 'output_fractions', 'total_output_ratio'], 'diagnostics');
  checkpoints.forEach(key => { const expected = norms[key][0] + norms[key][1]; if (finite(d[`${key}_total`], 'checkpoint total', true) !== expected) fail('same-reduction checkpoint total'); });
  const steps: readonly [string, keyof PolarizedTwoPathNorms, keyof PolarizedTwoPathNorms][] = [['split_delta', 'split', 'inputs'], ['propagation_delta', 'propagated', 'split'],
    ['elements_delta', 'elements', 'propagated'], ['phase_delta', 'combiner', 'elements'], ['recombination_delta', 'outputs', 'combiner'], ['total_delta', 'outputs', 'inputs']];
  for (const [key, after, before] of steps) if (finite(d[key], key) !== (d[`${after}_total`] as number) - (d[`${before}_total`] as number)) fail('signed checkpoint delta');
  for (const [key, after, before] of [['propagation_deltas', 'propagated', 'split'], ['element_deltas', 'elements', 'propagated'], ['phase_deltas', 'combiner', 'elements']] as const) {
    const values = pair(d[key], key, false); if (values.some((v, i) => v !== norms[after][i] - norms[before][i])) fail('signed per-arm delta');
  }
  if (!Array.isArray(d.arm_action_deltas) || d.arm_action_deltas.length !== 2) fail('action delta histories');
  d.arm_action_deltas.forEach((v, i) => { if (!Array.isArray(v) || v.length !== norms.arm_action_norms[i].length) fail('action delta length');
    v.forEach((change, j) => { if (finite(change, 'action delta') !== norms.arm_action_norms[i][j] - (j ? norms.arm_action_norms[i][j - 1] : norms.propagated[i])) fail('signed action delta'); }); });
  const input = d.inputs_total as number;
  if (!Array.isArray(d.output_fractions) || d.output_fractions.length !== 2) fail('output fraction pair');
  d.output_fractions.forEach((item, index) => ratio(item, input, 'output fraction', norms.outputs[index])); ratio(d.total_output_ratio, input, 'total output ratio', d.outputs_total as number);
  const a = record(value.analysis, 'analysis'); keys(a, ['enabled', 'axis_angle_rad', 'ports', 'total_norm', 'total_removed_norm', 'total_original_input_ratio'], 'analysis');
  if (a.enabled !== experiment.analyzer.enabled || a.axis_angle_rad !== experiment.analyzer.axis_angle_rad) fail('submitted analyzer identity');
  if (!experiment.analyzer.enabled) { if ([a.ports, a.total_norm, a.total_removed_norm, a.total_original_input_ratio].some(item => item !== null)) fail('disabled analysis must be absent'); }
  else {
    if (!Array.isArray(a.ports) || a.ports.length !== 2) fail('analysis port pair');
    const ports = a.ports.map((item, i) => { const p = record(item, 'analysis port'); keys(p, ['id', 'raw_norm', 'analyzed_norm', 'removed_norm', 'original_input_ratio', 'raw_output_ratio'], 'analysis port');
      if (p.id !== `port_${i}` || finite(p.raw_norm, 'raw norm', true) !== norms.outputs[i]) fail('analysis raw port identity');
      const analyzed = finite(p.analyzed_norm, 'analyzed norm', true); if (finite(p.removed_norm, 'removed norm') !== norms.outputs[i] - analyzed) fail('signed analyzer loss');
      ratio(p.original_input_ratio, input, 'original input ratio', analyzed); ratio(p.raw_output_ratio, norms.outputs[i], 'raw output ratio', analyzed); return p;
    });
    if (finite(a.total_norm, 'analysis total', true) !== (ports[0].analyzed_norm as number) + (ports[1].analyzed_norm as number)
      || finite(a.total_removed_norm, 'removed total') !== (ports[0].removed_norm as number) + (ports[1].removed_norm as number)) fail('analysis scalar totals');
    ratio(a.total_original_input_ratio, input, 'analyzed original input total', a.total_norm as number);
    if (input !== 0 && a.total_original_input_ratio !== (ports[0].original_input_ratio as number) + (ports[1].original_input_ratio as number)) fail('sum of public analyzer fractions');
  }
  return freezePolarizedTwoPath({ norms, diagnostics: structuredClone(d) as unknown as PolarizedTwoPathDiagnostics, analysis: structuredClone(a) as PolarizedTwoPathAnalysis });
}
export function decodePolarizedTwoPathResult(frame: ArrayBuffer, submitted: PolarizedTwoPathEnvelope): DecodedPolarizedTwoPathResult {
  if (!(frame instanceof ArrayBuffer) || frame.byteLength < 16 || frame.byteLength > MAX_POLARIZED_TWO_PATH_RESPONSE_BYTES) fail('frame length/cap');
  assertPolarizedTwoPathExperiment(submitted.experiment); requestId(submitted.request_id); hash(submitted.experiment_sha256);
  const bytes = new Uint8Array(frame), view = new DataView(frame);
  if ([79, 72, 76, 65, 66, 80, 84, 0].some((byte, index) => bytes[index] !== byte)) fail('magic');
  if (view.getUint32(12, true) !== 0) fail('reserved bytes');
  const length = view.getUint32(8, true), padded = Math.ceil(length / 8) * 8, start = 16 + padded;
  if (length < 2 || padded > MAX_POLARIZED_TWO_PATH_HEADER_BYTES || start > frame.byteLength) fail('header length/cap');
  for (let i = 16 + length; i < start; i++) if (bytes[i] !== 0) fail('nonzero padding');
  let text: string; try { text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes.subarray(16, 16 + length)); } catch { return fail('invalid UTF-8'); }
  const header = record(parsePolarizedTwoPathJSON(text), 'header');
  keys(header, ['protocol_version', 'message_type', 'request_id', 'experiment_sha256', 'experiment', 'norms', 'diagnostics', 'analysis', 'arrays', 'intensity_max'], 'header');
  if (header.protocol_version !== 1 || header.message_type !== 'polarized_two_path_result') fail('result version/type');
  const reply = validatePolarizedTwoPathReply({ protocol_version: 1, message_type: 'polarized_two_path_validation', request_id: header.request_id,
    experiment_sha256: header.experiment_sha256, experiment: header.experiment }, submitted);
  const scalars = measurement({ norms: header.norms, diagnostics: header.diagnostics, analysis: header.analysis }, reply.experiment);
  const { nx, ny, dx, dy } = reply.experiment.grid, count = submitted.experiment.analyzer.enabled ? 4 : 2, plane = nx * ny * 8;
  const cap = count === 4 ? MAX_POLARIZED_TWO_PATH_RESPONSE_BYTES : MAX_POLARIZED_TWO_PATH_DISABLED_RESPONSE_BYTES;
  if (frame.byteLength > cap || frame.byteLength !== start + 8 * (count * nx * ny + nx + ny)) fail('conditional payload length/cap/trailing bytes');
  const descriptions = Array.from({ length: count }, (_, i) => ({ name: `${i < 2 ? 'raw' : 'analyzed'}_port_${i % 2}_intensity`,
    role: 'intensity', port_id: `port_${i % 2}`, state: i < 2 ? 'raw' : 'analyzed', shape: [ny, nx], offset: i * plane, nbytes: plane, units: 'amplitude_unit^2' }));
  descriptions.push({ name: 'x_m', role: 'coordinate', port_id: null as unknown as string, state: null as unknown as string, shape: [nx], offset: count * plane, nbytes: nx * 8, units: 'm' },
    { name: 'y_m', role: 'coordinate', port_id: null as unknown as string, state: null as unknown as string, shape: [ny], offset: count * plane + nx * 8, nbytes: ny * 8, units: 'm' });
  if (!Array.isArray(header.arrays) || header.arrays.length !== count + 2) fail('conditional array inventory');
  const arrays = descriptions.map((description, index) => { const item = record((header.arrays as unknown[])[index], 'descriptor');
    keys(item, ['name', 'role', 'port_id', 'state', 'dtype', 'order', 'shape', 'offset_bytes', 'nbytes', 'units'], 'descriptor');
    if (item.name !== description.name || item.role !== description.role || item.port_id !== description.port_id || item.state !== description.state
      || item.dtype !== 'float64-le' || item.order !== 'C' || item.units !== description.units || !structuralEqual(item.shape, description.shape)) fail('descriptor role/port/state/dtype/order/shape/units');
    if (item.offset_bytes !== description.offset || item.nbytes !== description.nbytes) fail('descriptor gap/overlap/size');
    const array = new Float64Array(description.nbytes / 8); for (let i = 0; i < array.length; i++) array[i] = finite(view.getFloat64(start + description.offset + 8 * i, true), description.name, index < count); return array;
  });
  const x = arrays[count], y = arrays[count + 1];
  for (let c = 0; c < nx; c++) if (x[c] !== (c - Math.floor(nx / 2)) * dx) fail('x coordinate mismatch');
  for (let r = 0; r < ny; r++) if (y[r] !== (r - Math.floor(ny / 2)) * dy) fail('y coordinate mismatch');
  if (!Array.isArray(header.intensity_max) || header.intensity_max.length !== count) fail('intensity maxima inventory');
  const maxima = arrays.slice(0, count).map((array, index) => { let maximum = 0; for (const value of array) maximum = Math.max(maximum, value);
    if (finite((header.intensity_max as unknown[])[index], 'intensity maximum', true) !== maximum) fail('intensity maximum mismatch'); return maximum; });
  const ports = (offset: number) => Object.freeze([0, 1].map(i => Object.freeze({ id: `port_${i}`, intensity: arrays[offset + i], intensityMax: maxima[offset + i] }))) as unknown as readonly [PolarizedTwoPathPort, PolarizedTwoPathPort];
  return Object.freeze({ requestId: reply.request_id, experimentSha256: reply.experiment_sha256, experiment: reply.experiment, ...scalars,
    rawPorts: ports(0), analyzedPorts: count === 4 ? ports(2) : null, x, y, intensityMax: Object.freeze(maxima) });
}
function errorDetail(value: unknown): Readonly<{ code: string; message: string }> {
  const error = record(value, 'error'); keys(error, ['code', 'message'], 'error');
  if (typeof error.code !== 'string' || !/^[a-z][a-z0-9_]{0,63}$/.test(error.code) || typeof error.message !== 'string'
    || [...error.message].length < 1 || [...error.message].length > 300 || [...error.message].some(c => { const n = c.codePointAt(0)!; return n >= 0xd800 && n <= 0xdfff; })) fail('bounded error code/message');
  return Object.freeze({ code: error.code, message: error.message });
}
export function validatePolarizedTwoPathSweep(value: unknown, submitted: PolarizedTwoPathSweepEnvelope, httpStatus: number,
    expectedSweepSha256?: string): DecodedPolarizedTwoPathSweep {
  hash(submitted.fixed_experiment_sha256); const data = record(value, 'sweep');
  keys(data, ['protocol_version', 'message_type', 'request_id', 'fixed_experiment_sha256', 'sweep_sha256', 'fixed_experiment', 'phases_rad', 'status', 'requested_count', 'completed_count', 'failed_index', 'rows', 'error'], 'sweep');
  if (data.protocol_version !== 1 || data.message_type !== 'polarized_two_path_sweep') fail('sweep version/type');
  const reply = validatePolarizedTwoPathSweepReply({ ...Object.fromEntries(['protocol_version', 'request_id', 'fixed_experiment_sha256', 'fixed_experiment', 'phases_rad', 'sweep_sha256'].map(key => [key, data[key]])), message_type: 'polarized_two_path_sweep_validation' }, submitted);
  if (expectedSweepSha256 !== undefined && reply.sweep_sha256 !== hash(expectedSweepSha256)) fail('validated sweep SHA mismatch');
  if (data.requested_count !== 17) fail('seventeen requested points'); const count = integer(data.completed_count, 'completed count', 0, 17);
  let error: Readonly<{ code: string; message: string }> | null = null;
  if (data.status === 'complete') { if (httpStatus !== 200 || count !== 17 || data.failed_index !== null || data.error !== null) fail('complete sweep status'); }
  else if (data.status === 'failed') { if (![422, 500].includes(httpStatus) || count >= 17 || data.failed_index !== count) fail('failed contiguous prefix'); error = errorDetail(data.error);
    if (error.code !== (httpStatus === 422 ? 'numerical_failure' : 'sweep_failed')) fail('failure kind/status');
  } else fail('sweep status');
  if (!Array.isArray(data.rows) || data.rows.length !== count) fail('genuine row count');
  const rows = data.rows.map((value, index) => { const row = record(value, 'row'); keys(row, ['index', 'phase_rad', 'norms', 'diagnostics', 'analysis'], 'row');
    if (row.index !== index || row.phase_rad !== SWEEP_PHASES_RAD[index]) fail('contiguous actual phase rows');
    return freezePolarizedTwoPath({ index, phase_rad: SWEEP_PHASES_RAD[index], ...measurement({ norms: row.norms, diagnostics: row.diagnostics, analysis: row.analysis }, reply.fixed_experiment) }); });
  return freezePolarizedTwoPath({ requestId: reply.request_id, fixedExperimentSha256: reply.fixed_experiment_sha256, sweepSha256: reply.sweep_sha256,
    fixedExperiment: reply.fixed_experiment, phasesRad: [...SWEEP_PHASES_RAD], status: data.status as 'complete' | 'failed', requestedCount: 17,
    completedCount: count, failedIndex: data.failed_index as number | null, rows, error, httpStatus });
}
export function createPolarizedTwoPathFetchAPI(fetchImpl: typeof fetch = globalThis.fetch.bind(globalThis)): PolarizedTwoPathAPI {
  const post = async (endpoint: string, envelope: PolarizedTwoPathEnvelope | PolarizedTwoPathSweepEnvelope, cap: number, mime: string) => {
    requestId(envelope.request_id);
    if (envelope.message_type === 'polarized_two_path_submission') assertPolarizedTwoPathExperiment(envelope.experiment);
    else { assertFixed(envelope.fixed_experiment); if (!structuralEqual(envelope.phases_rad, SWEEP_PHASES_RAD)) fail('seventeen exact phases'); }
    const body = JSON.stringify(envelope); if (new TextEncoder().encode(body).byteLength > MAX_POLARIZED_TWO_PATH_REQUEST_BYTES) fail('request cap');
    const response = await fetchImpl(`/api/v2g/${endpoint}`, { method: 'POST', credentials: 'same-origin', redirect: 'error', headers: { 'Content-Type': 'application/json', Accept: mime }, body });
    const type = response.headers.get('content-type')?.split(';', 1)[0].trim();
    if (!response.ok && endpoint === 'sweep' && [422, 500].includes(response.status) && type === 'application/json') {
      const bytes = await readBoundedResponse(response, MAX_POLARIZED_TWO_PATH_SWEEP_BYTES), parsed = parsePolarizedTwoPathJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
      if (record(parsed, 'sweep error').message_type === 'polarized_two_path_sweep') return { bytes, status: response.status };
      throw new Error(`HTTP ${response.status}: ${errorDetail(record(parsed, 'error').error).message}`);
    }
    if (!response.ok) { const bytes = await readBoundedResponse(response, MAX_POLARIZED_TWO_PATH_HEADER_BYTES); let message = `HTTP ${response.status}`;
      if (type === 'application/json') { try { message += `: ${errorDetail(record(parsePolarizedTwoPathJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes)), 'error').error).message}`; } catch { /* Preserve actual HTTP status. */ } } throw new Error(message);
    }
    if (type !== mime) { await response.body?.cancel('V2g MIME mismatch'); fail('HTTP content-type'); }
    return { bytes: await readBoundedResponse(response, cap), status: response.status };
  };
  return {
    async validate(envelope) { const { bytes } = await post('validate', envelope, MAX_POLARIZED_TWO_PATH_HEADER_BYTES, 'application/json'); return validatePolarizedTwoPathReply(parsePolarizedTwoPathJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes)), envelope); },
    async validateSweep(envelope) { const { bytes } = await post('validate', envelope, MAX_POLARIZED_TWO_PATH_HEADER_BYTES, 'application/json'); return validatePolarizedTwoPathSweepReply(parsePolarizedTwoPathJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes)), envelope); },
    async simulate(envelope) { return (await post('simulate', envelope, MAX_POLARIZED_TWO_PATH_RESPONSE_BYTES, 'application/octet-stream')).bytes; },
    async sweep(envelope) { const { bytes, status } = await post('sweep', envelope, MAX_POLARIZED_TWO_PATH_SWEEP_BYTES, 'application/json'); return { body: parsePolarizedTwoPathJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes)), httpStatus: status }; },
  };
}
