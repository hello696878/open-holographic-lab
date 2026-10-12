/** Distinct bounded transport. Scientific calculations remain in the public Python API. */
import { parseStrictJSON, readBoundedResponse, structuralEqual, type GridSpec } from './contracts';
export interface ComplexValue { re: number; im: number }
export interface ComplexPair { x: ComplexValue; y: ComplexValue }
export type PolarizationSource = { kind: 'uniform'; amplitude: number; phase_rad: number }
  | { kind: 'gaussian'; amplitude: number; phase_rad: number; waist_radius_m: number; center_x_m: number; center_y_m: number };
export type PolarizationElement = { id: string; kind: 'linear_polarizer'; axis_angle_rad: number }
  | { id: string; kind: 'linear_retarder'; axis_angle_rad: number; retardance_rad: number };
export interface PolarizationExperiment {
  schema_version: 1; model_contract: 'v2d_ideal_jones_same_plane_v1'; wavelength_m: number;
  grid: GridSpec; source: PolarizationSource; coefficients: ComplexPair; elements: PolarizationElement[];
  readout: { row: number; column: number };
}
export interface PolarizationEnvelope { protocol_version: 1; message_type: 'polarization_submission';
  request_id: string; experiment: PolarizationExperiment; experiment_sha256: string | null }
export interface PolarizationSweepEnvelope extends Omit<PolarizationEnvelope, 'message_type'> {
  message_type: 'polarization_sweep_submission'; selected_element_id: string; angles_rad: readonly number[];
}
export interface PolarizationValidation { protocol_version: 1; message_type: 'polarization_validation';
  request_id: string; experiment_sha256: string; experiment: PolarizationExperiment }
export interface PolarizationScalarStage { stage_id: string; kind: 'input' | PolarizationElement['kind']; norm: number;
  previous_norm: number | null; delta_norm: number | null; adjacent_transmission_ratio: number | null;
  incident_transmission_ratio: number | null }
export interface PolarizationStage extends PolarizationScalarStage { sample: ComplexPair }
export interface DecodedPolarizationResult {
  readonly requestId: string; readonly experimentSha256: string; readonly experiment: PolarizationExperiment;
  readonly orderedStageIds: readonly string[]; readonly stages: readonly PolarizationStage[];
  readonly readout: Readonly<{ row: number; column: number; x_m: number; y_m: number }>;
  readonly incidentIntensity: Float64Array; readonly finalIntensity: Float64Array; readonly x: Float64Array; readonly y: Float64Array;
  readonly intensityMax: readonly [number, number];
}
export interface PolarizationSweepRow { index: number; axis_angle_rad: number; stages: readonly PolarizationScalarStage[];
  final_norm: number; incident_transmission_ratio: number | null; total_delta: number }
export interface DecodedPolarizationSweep { readonly requestId: string; readonly experimentSha256: string; readonly sweepSha256: string;
  readonly experiment: PolarizationExperiment; readonly selectedElementId: string; readonly anglesRad: readonly number[];
  readonly orderedStageIds: readonly string[]; readonly requestedCount: 13; readonly completedCount: number;
  readonly status: 'complete' | 'failed'; readonly failedIndex: number | null; readonly rows: readonly PolarizationSweepRow[];
  readonly error: Readonly<{ code: string; message: string }> | null; readonly httpStatus: number }
export interface PolarizationAPI { validate(envelope: PolarizationEnvelope): Promise<PolarizationValidation>;
  simulate(envelope: PolarizationEnvelope): Promise<ArrayBuffer>;
  sweep(envelope: PolarizationSweepEnvelope): Promise<{ body: unknown; httpStatus: number }> }
export const MAX_POLARIZATION_REQUEST_BYTES = 32768;
export const MAX_POLARIZATION_HEADER_BYTES = 16384;
export const MAX_POLARIZATION_RESPONSE_BYTES = 280592;
export const MAX_POLARIZATION_SWEEP_BYTES = 65536;
export const SWEEP_ANGLES_DEG = Object.freeze([-90, -75, -60, -45, -30, -15, 0, 15, 30, 45, 60, 75, 90]);
export const SWEEP_ANGLES_RAD = Object.freeze(SWEEP_ANGLES_DEG.map(degree => degree * (Math.PI / 180)));
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const SHA = /^[0-9a-f]{64}$/;
function fail(message: string): never { throw new Error(`V2d protocol: ${message}`); }
function record(value: unknown, name: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(`${name}: expected object`);
  return value as Record<string, unknown>;
}
function keys(value: Record<string, unknown>, expected: readonly string[], name: string): void {
  if (Object.keys(value).length !== expected.length || Object.keys(value).some(key => !expected.includes(key))) fail(`${name}: incorrect keys`);
}
function finite(value: unknown, name: string, nonnegative = false, positive = false): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || nonnegative && value < 0 || positive && value <= 0) fail(`${name}: invalid finite number`);
  return value;
}
function integer(value: unknown, name: string, low: number, high: number): number {
  const n = finite(value, name); if (!Number.isSafeInteger(n) || n < low || n > high) fail(`${name}: invalid integer`); return n;
}
function requestId(value: unknown): string { if (typeof value !== 'string' || !UUID.test(value)) fail('canonical UUIDv4'); return value; }
function hash(value: unknown): string { if (typeof value !== 'string' || !SHA.test(value)) fail('specification SHA'); return value; }
export function freezePolarization<T>(value: T): T {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) { Object.values(value).forEach(item => freezePolarization(item)); Object.freeze(value); }
  return value;
}
/** New browser zeros become +0 before identity; all other finite values stay exact. */
export function freezePolarizationExperiment(experiment: PolarizationExperiment): PolarizationExperiment {
  const copy = structuredClone(experiment);
  const zeros = (object: Record<string, unknown>) => { for (const [key, value] of Object.entries(object)) {
    if (typeof value === 'number' && value === 0) object[key] = 0;
    else if (value && typeof value === 'object') zeros(value as Record<string, unknown>);
  } };
  zeros(copy as unknown as Record<string, unknown>); return freezePolarization(copy);
}
function complexPair(value: unknown): ComplexPair {
  const data = record(value, 'complex pair'); keys(data, ['x', 'y'], 'complex pair');
  const component = (input: unknown): ComplexValue => { const c = record(input, 'complex component'); keys(c, ['re', 'im'], 'complex component');
    return Object.freeze({ re: finite(c.re, 'real component'), im: finite(c.im, 'imaginary component') }); };
  return Object.freeze({ x: component(data.x), y: component(data.y) });
}
/** Schema/shape checks only; public Python source validation remains authoritative. */
export function assertPolarizationExperiment(value: unknown): asserts value is PolarizationExperiment {
  const data = record(value, 'experiment'); keys(data, ['schema_version', 'model_contract', 'wavelength_m', 'grid', 'source', 'coefficients', 'elements', 'readout'], 'experiment');
  if (data.schema_version !== 1 || data.model_contract !== 'v2d_ideal_jones_same_plane_v1') fail('experiment version/contract');
  finite(data.wavelength_m, 'wavelength', false, true);
  const grid = record(data.grid, 'grid'); keys(grid, ['ny', 'nx', 'dy', 'dx'], 'grid');
  const ny = integer(grid.ny, 'ny', 1, 128), nx = integer(grid.nx, 'nx', 1, 128);
  finite(grid.dx, 'dx', false, true); finite(grid.dy, 'dy', false, true);
  const source = record(data.source, 'source');
  if (source.kind === 'uniform') keys(source, ['kind', 'amplitude', 'phase_rad'], 'uniform source');
  else if (source.kind === 'gaussian') {
    keys(source, ['kind', 'amplitude', 'phase_rad', 'waist_radius_m', 'center_x_m', 'center_y_m'], 'Gaussian source');
    finite(source.waist_radius_m, 'waist radius', false, true); finite(source.center_x_m, 'center x'); finite(source.center_y_m, 'center y');
  } else fail('source kind');
  finite(source.amplitude, 'source amplitude', true); finite(source.phase_rad, 'source phase'); complexPair(data.coefficients);
  if (!Array.isArray(data.elements) || data.elements.length > 8) fail('elements cap');
  const ids = new Set(['input']);
  for (const value of data.elements) {
    const item = record(value, 'element');
    if (item.kind === 'linear_polarizer') keys(item, ['id', 'kind', 'axis_angle_rad'], 'polarizer');
    else if (item.kind === 'linear_retarder') { keys(item, ['id', 'kind', 'axis_angle_rad', 'retardance_rad'], 'retarder'); finite(item.retardance_rad, 'retardance'); }
    else fail('element kind');
    if (typeof item.id !== 'string' || !/^[A-Za-z][A-Za-z0-9_-]{0,31}$/.test(item.id) || ids.has(item.id)) fail('unique element ID');
    ids.add(item.id); finite(item.axis_angle_rad, 'axis angle');
  }
  const readout = record(data.readout, 'readout'); keys(readout, ['row', 'column'], 'readout');
  integer(readout.row, 'readout row', 0, ny - 1); integer(readout.column, 'readout column', 0, nx - 1);
}
export function validatePolarizationReply(value: unknown, submitted: PolarizationEnvelope | PolarizationSweepEnvelope): PolarizationValidation {
  const data = record(value, 'validation reply'); keys(data, ['protocol_version', 'message_type', 'request_id', 'experiment_sha256', 'experiment'], 'validation reply');
  if (data.protocol_version !== 1 || data.message_type !== 'polarization_validation') fail('validation version/type');
  if (requestId(data.request_id) !== requestId(submitted.request_id)) fail('request identity mismatch');
  assertPolarizationExperiment(data.experiment);
  if (!structuralEqual(data.experiment, submitted.experiment)) fail('complete specification identity mismatch');
  const digest = hash(data.experiment_sha256);
  if (submitted.experiment_sha256 !== null && digest !== submitted.experiment_sha256) fail('validated specification SHA mismatch');
  return freezePolarization({ protocol_version: 1, message_type: 'polarization_validation', request_id: data.request_id as string,
    experiment_sha256: digest, experiment: structuredClone(data.experiment) });
}
const stageFields = ['stage_id', 'kind', 'norm', 'previous_norm', 'delta_norm', 'adjacent_transmission_ratio', 'incident_transmission_ratio'];
function stageRecords(value: unknown, experiment: PolarizationExperiment, samples: boolean): readonly PolarizationScalarStage[] {
  if (!Array.isArray(value) || value.length !== experiment.elements.length + 1 || value.length > 9) fail('stage count');
  const stages: PolarizationScalarStage[] = [];
  for (const [index, item] of value.entries()) {
    const stage = record(item, 'stage'); keys(stage, samples ? [...stageFields, 'sample'] : stageFields, 'stage');
    if (stage.stage_id !== (index === 0 ? 'input' : experiment.elements[index - 1].id)
        || stage.kind !== (index === 0 ? 'input' : experiment.elements[index - 1].kind)) fail('stage order/kind identity');
    const norm = finite(stage.norm, 'stage norm', true), previous = index === 0 ? null : stages[index - 1].norm;
    if (stage.previous_norm !== previous || stage.delta_norm !== (previous === null ? null : norm - previous)) fail('signed norm chain');
    const ratio = (value: unknown, denominator: number | null, name: string) => {
      if (denominator === null || denominator === 0) { if (value !== null) fail(`${name}: undefined must be null`); }
      else finite(value, name, true); // Public ratio values are authoritative, never recomputed in JavaScript.
    };
    ratio(stage.adjacent_transmission_ratio, previous, 'adjacent ratio');
    ratio(stage.incident_transmission_ratio, index === 0 ? norm : stages[0].norm, 'incident ratio');
    if (index === 0 && norm !== 0 && stage.incident_transmission_ratio !== 1) fail('input public self-ratio must be one');
    stages.push(freezePolarization({ ...stage, ...(samples ? { sample: complexPair(stage.sample) } : {}) }) as unknown as PolarizationScalarStage);
  }
  return Object.freeze(stages);
}
export function decodePolarizationResult(frame: ArrayBuffer, submitted: PolarizationEnvelope): DecodedPolarizationResult {
  if (!(frame instanceof ArrayBuffer) || frame.byteLength < 16 || frame.byteLength > MAX_POLARIZATION_RESPONSE_BYTES) fail('frame length/cap');
  assertPolarizationExperiment(submitted.experiment); requestId(submitted.request_id); hash(submitted.experiment_sha256);
  const bytes = new Uint8Array(frame), view = new DataView(frame);
  if ([79, 72, 76, 65, 66, 80, 76, 0].some((byte, index) => bytes[index] !== byte)) fail('magic');
  if (view.getUint32(12, true) !== 0) fail('reserved bytes');
  const length = view.getUint32(8, true), start = 16 + Math.ceil(length / 8) * 8;
  if (length < 2 || length > MAX_POLARIZATION_HEADER_BYTES || start > frame.byteLength) fail('header length/cap');
  for (let i = 16 + length; i < start; i++) if (bytes[i] !== 0) fail('nonzero padding');
  let text: string;
  try { text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes.subarray(16, 16 + length)); }
  catch { return fail('invalid UTF-8'); }
  const header = record(parseStrictJSON(text), 'header');
  keys(header, ['protocol_version', 'message_type', 'request_id', 'experiment_sha256', 'experiment', 'ordered_stage_ids', 'stages', 'readout', 'arrays', 'intensity_max'], 'header');
  if (header.protocol_version !== 1 || header.message_type !== 'polarization_result') fail('result version/type');
  const reply = validatePolarizationReply({ protocol_version: 1, message_type: 'polarization_validation', request_id: header.request_id,
    experiment_sha256: header.experiment_sha256, experiment: header.experiment }, submitted);
  const ordered = ['input', ...reply.experiment.elements.map(item => item.id)];
  if (!structuralEqual(header.ordered_stage_ids, ordered)) fail('ordered stage identities');
  const stages = stageRecords(header.stages, reply.experiment, true) as readonly PolarizationStage[];
  const readout = record(header.readout, 'readout'); keys(readout, ['row', 'column', 'x_m', 'y_m'], 'readout');
  if (readout.row !== reply.experiment.readout.row || readout.column !== reply.experiment.readout.column) fail('selected sample identity');
  finite(readout.x_m, 'sample x'); finite(readout.y_m, 'sample y');
  const { nx, ny, dx, dy } = reply.experiment.grid, plane = nx * ny * 8;
  const expected = [
    { name: 'incident_intensity', role: 'intensity', stage_id: 'input', shape: [ny, nx], offset: 0, nbytes: plane, units: 'amplitude_unit^2' },
    { name: 'final_intensity', role: 'intensity', stage_id: ordered.at(-1), shape: [ny, nx], offset: plane, nbytes: plane, units: 'amplitude_unit^2' },
    { name: 'x_m', role: 'coordinate', stage_id: null, shape: [nx], offset: 2 * plane, nbytes: nx * 8, units: 'm' },
    { name: 'y_m', role: 'coordinate', stage_id: null, shape: [ny], offset: 2 * plane + nx * 8, nbytes: ny * 8, units: 'm' },
  ];
  if (!Array.isArray(header.arrays) || header.arrays.length !== 4) fail('four array descriptors');
  if (frame.byteLength !== start + 8 * (2 * nx * ny + nx + ny)) fail('exact payload length/trailing bytes');
  const arrays = expected.map((description, index) => {
    const item = record((header.arrays as unknown[])[index], 'descriptor');
    keys(item, ['name', 'role', 'stage_id', 'dtype', 'order', 'shape', 'offset_bytes', 'nbytes', 'units'], 'descriptor');
    if (item.name !== description.name || item.role !== description.role || item.stage_id !== description.stage_id
        || item.dtype !== 'float64-le' || item.order !== 'C' || item.units !== description.units
        || !structuralEqual(item.shape, description.shape)) fail('descriptor role/stage/dtype/order/shape/units');
    if (item.offset_bytes !== description.offset || item.nbytes !== description.nbytes) fail('descriptor gap/overlap/size');
    const array = new Float64Array(description.nbytes / 8);
    for (let i = 0; i < array.length; i++) array[i] = finite(view.getFloat64(start + description.offset + i * 8, true), description.name, index < 2);
    return array;
  });
  const [incidentIntensity, finalIntensity, x, y] = arrays;
  for (let c = 0; c < nx; c++) if (x[c] !== (c - Math.floor(nx / 2)) * dx) fail('x coordinate mismatch');
  for (let r = 0; r < ny; r++) if (y[r] !== (r - Math.floor(ny / 2)) * dy) fail('y coordinate mismatch');
  if (readout.x_m !== x[reply.experiment.readout.column] || readout.y_m !== y[reply.experiment.readout.row]) fail('selected sample physical coordinates');
  if (!Array.isArray(header.intensity_max) || header.intensity_max.length !== 2) fail('intensity maxima pair');
  const maxima = [incidentIntensity, finalIntensity].map((array, index) => {
    let maximum = 0; for (const value of array) maximum = Math.max(maximum, value);
    if (finite((header.intensity_max as unknown[])[index], 'intensity maximum', true) !== maximum) fail('intensity maximum mismatch'); return maximum;
  });
  return Object.freeze({ requestId: reply.request_id, experimentSha256: reply.experiment_sha256, experiment: reply.experiment,
    orderedStageIds: Object.freeze(ordered), stages, readout: Object.freeze({ ...readout }) as DecodedPolarizationResult['readout'],
    incidentIntensity, finalIntensity, x, y, intensityMax: Object.freeze(maxima) as readonly [number, number] });
}
function errorDetail(value: unknown): Readonly<{ code: string; message: string }> {
  const error = record(value, 'error'); keys(error, ['code', 'message'], 'error');
  if (typeof error.code !== 'string' || !/^[a-z][a-z0-9_]{0,63}$/.test(error.code)
      || typeof error.message !== 'string' || error.message.length < 1 || error.message.length > 300) fail('bounded error code/message');
  return Object.freeze({ code: error.code, message: error.message });
}
export function validatePolarizationSweep(value: unknown, submitted: PolarizationSweepEnvelope, httpStatus: number): DecodedPolarizationSweep {
  hash(submitted.experiment_sha256);
  const data = record(value, 'sweep reply'); keys(data, ['protocol_version', 'message_type', 'status', 'request_id', 'experiment_sha256', 'sweep_sha256',
    'experiment', 'selected_element_id', 'angles_rad', 'ordered_stage_ids', 'requested_count', 'rows', 'completed_count', 'failed_index', 'error'], 'sweep reply');
  if (data.protocol_version !== 1 || data.message_type !== 'polarization_sweep_result') fail('sweep version/type');
  const reply = validatePolarizationReply({ protocol_version: 1, message_type: 'polarization_validation', request_id: data.request_id,
    experiment_sha256: data.experiment_sha256, experiment: data.experiment }, submitted);
  if (data.selected_element_id !== submitted.selected_element_id
      || !reply.experiment.elements.some(item => item.id === data.selected_element_id && item.kind === 'linear_polarizer')) fail('sweep selected polarizer identity');
  if (!structuralEqual(data.angles_rad, SWEEP_ANGLES_RAD) || !structuralEqual(data.angles_rad, submitted.angles_rad)) fail('exact thirteen angles');
  const ordered = ['input', ...reply.experiment.elements.map(item => item.id)];
  if (!structuralEqual(data.ordered_stage_ids, ordered) || data.requested_count !== 13) fail('sweep stage identities/count');
  const count = integer(data.completed_count, 'completed count', 0, 13);
  if (!Array.isArray(data.rows) || data.rows.length !== count) fail('sweep row count');
  if (data.status === 'complete') {
    if (httpStatus !== 200 || count !== 13 || data.failed_index !== null || data.error !== null) fail('complete sweep status/count/error');
  } else if (data.status === 'failed') {
    if (![422, 500].includes(httpStatus) || count === 13 || data.failed_index !== count) fail('failed contiguous prefix');
    const error = errorDetail(data.error);
    if (error.code !== (httpStatus === 422 ? 'numerical_failure' : 'sweep_failed')) fail('failed HTTP/error kind');
  } else fail('sweep status');
  const rows = data.rows.map((value, index) => {
    const row = record(value, 'sweep row'); keys(row, ['index', 'axis_angle_rad', 'stages', 'final_norm', 'incident_transmission_ratio', 'total_delta'], 'sweep row');
    if (row.index !== index || row.axis_angle_rad !== SWEEP_ANGLES_RAD[index]) fail('genuine contiguous row angle/index');
    const stages = stageRecords(row.stages, reply.experiment, false), final = stages.at(-1)!;
    if (row.final_norm !== final.norm || row.incident_transmission_ratio !== final.incident_transmission_ratio
        || row.total_delta !== final.norm - stages[0].norm) fail('final scalar identity/signed total delta');
    finite(row.total_delta, 'total delta');
    return freezePolarization({ ...row, stages }) as unknown as PolarizationSweepRow;
  });
  return freezePolarization({ requestId: reply.request_id, experimentSha256: reply.experiment_sha256, sweepSha256: hash(data.sweep_sha256),
    experiment: reply.experiment, selectedElementId: submitted.selected_element_id, anglesRad: [...SWEEP_ANGLES_RAD], orderedStageIds: ordered,
    requestedCount: 13, completedCount: count, status: data.status as 'complete' | 'failed', failedIndex: data.failed_index as number | null,
    rows, error: data.error === null ? null : errorDetail(data.error), httpStatus });
}
export function createPolarizationFetchAPI(fetchImpl: typeof fetch = globalThis.fetch.bind(globalThis)): PolarizationAPI {
  const post = async (endpoint: string, envelope: PolarizationEnvelope | PolarizationSweepEnvelope, cap: number, mime: string) => {
    requestId(envelope.request_id); assertPolarizationExperiment(envelope.experiment);
    const body = JSON.stringify(envelope); if (new TextEncoder().encode(body).byteLength > MAX_POLARIZATION_REQUEST_BYTES) fail('request cap');
    const response = await fetchImpl(`/api/v2d/${endpoint}`, { method: 'POST', credentials: 'same-origin', redirect: 'error',
      headers: { 'Content-Type': 'application/json', Accept: mime }, body });
    const type = response.headers.get('content-type')?.split(';', 1)[0].trim();
    if (!response.ok && endpoint === 'sweep' && [422, 500].includes(response.status) && type === 'application/json') {
      const bytes = await readBoundedResponse(response, MAX_POLARIZATION_SWEEP_BYTES);
      const parsed = parseStrictJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
      if (record(parsed, 'error reply').message_type === 'polarization_sweep_result') return { bytes, status: response.status };
      throw new Error(`HTTP ${response.status}: ${errorDetail(record(parsed, 'error reply').error).message}`);
    }
    if (!response.ok) {
      const bytes = await readBoundedResponse(response, MAX_POLARIZATION_HEADER_BYTES); let message = `HTTP ${response.status}`;
      if (type === 'application/json') { try { message += `: ${errorDetail(record(parseStrictJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes)), 'error reply').error).message}`; } catch { /* Actual status remains visible. */ } }
      throw new Error(message);
    }
    if (type !== mime) { await response.body?.cancel('V2d MIME mismatch'); fail('HTTP content-type'); }
    return { bytes: await readBoundedResponse(response, cap), status: response.status };
  };
  return {
    async validate(envelope) { const { bytes } = await post('validate', envelope, MAX_POLARIZATION_HEADER_BYTES, 'application/json');
      return validatePolarizationReply(parseStrictJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes)), envelope); },
    async simulate(envelope) { return (await post('simulate', envelope, MAX_POLARIZATION_RESPONSE_BYTES, 'application/octet-stream')).bytes; },
    async sweep(envelope) { const { bytes, status } = await post('sweep', envelope, MAX_POLARIZATION_SWEEP_BYTES, 'application/json');
      return { body: parseStrictJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes)), httpStatus: status }; },
  };
}
