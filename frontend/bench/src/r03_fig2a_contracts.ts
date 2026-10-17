/** A-only bounded transport. No browser RNG, measured-data conversion or optical solver. */
import { parseStrictJSON, readBoundedResponse, structuralEqual } from './contracts';

export const R03_IDENTITY = 'Ideal statistical polarization — independent theoretical model';
export const R03_MODEL = 'r03_ideal_statistical_polarization_v1';
export const R03_REQUEST_CAP = 32768;
export const R03_RESPONSE_CAP = 131072;
export const R03_STAGE_IDS = Object.freeze(['source', 'after_slm', 'after_qwp', 'output'] as const);
export type R03StageId = typeof R03_STAGE_IDS[number];
export interface R03Experiment {
  schema_version: 1; model_contract: typeof R03_MODEL; source_amplitude: number; mean_phase_rad: number;
  phase_std_rad: number; qwp_angle_rad: number; hwp_angle_rad: number; seed: number;
}
export const R03_DEFAULT: Readonly<R03Experiment> = Object.freeze({ schema_version: 1, model_contract: R03_MODEL,
  source_amplitude: 1, mean_phase_rad: Math.PI, phase_std_rad: 1.2, qwp_angle_rad: 0, hwp_angle_rad: 0, seed: 20261017 });
export interface R03Envelope { protocol_version: 1; message_type: 'r03_ideal_submission'; request_id: string;
  experiment: R03Experiment; experiment_sha256: string | null }
export interface R03Validation { protocol_version: 1; message_type: 'r03_ideal_validation'; request_id: string;
  experiment: R03Experiment; experiment_sha256: string }
export interface R03Complex { readonly re: number; readonly im: number }
export interface R03Stage { readonly id: R03StageId; readonly coherency: readonly (readonly R03Complex[])[];
  readonly stokes: readonly number[]; readonly normalized_stokes: readonly number[] | null;
  readonly polarized_direction: readonly number[] | null; readonly degree_of_polarization: number | null;
  readonly eigenvalues: readonly number[]; readonly roundoff_limited: boolean }
export interface R03Result {
  readonly requestId: string; readonly experimentSha256: string; readonly experiment: R03Experiment;
  readonly phase: Readonly<{ shape: readonly [16, 16]; order: 'C'; unwrapped: Float64Array; wrapped: Float64Array }>;
  readonly stages: readonly R03Stage[];
  readonly population: Readonly<{ infinite_gaussian_degree_of_polarization: number | null; assumption: string }>;
  readonly provenance: Readonly<Record<string, unknown>>; readonly limitations: readonly string[];
}
export interface R03API { validate(envelope: R03Envelope): Promise<unknown>; simulate(envelope: R03Envelope): Promise<unknown> }
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const SHA = /^[0-9a-f]{64}$/;
function fail(message: string): never { throw new Error(`Ideal polarization protocol: ${message}`); }
function record(value: unknown, name: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(`${name}: expected object`);
  return value as Record<string, unknown>;
}
function keys(value: Record<string, unknown>, expected: readonly string[], name: string): void {
  if (Object.keys(value).length !== expected.length || Object.keys(value).some(k => !expected.includes(k))) fail(`${name}: incorrect keys`);
}
function finite(value: unknown, name: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) fail(`${name}: expected finite number`); return value;
}
function bounded(value: unknown, name: string, low: number, high: number): number {
  const number = finite(value, name); if (number < low || number > high) fail(`${name}: expected ${low}..${high}`); return number;
}
function text(value: unknown, name: string, cap = 600): string {
  if (typeof value !== 'string' || value.length === 0 || value.length > cap) fail(`${name}: bounded text`); return value;
}
function requestId(value: unknown): string { if (typeof value !== 'string' || !UUID.test(value)) fail('canonical UUIDv4'); return value; }
function digest(value: unknown): string { if (typeof value !== 'string' || !SHA.test(value)) fail('configuration SHA256'); return value; }
function vector(value: unknown, length: number, name: string): readonly number[] {
  if (!Array.isArray(value) || value.length !== length) fail(`${name}: expected length ${length}`);
  return Object.freeze(value.map(v => finite(v, name)));
}
function nullableVector(value: unknown, name: string): readonly number[] | null { return value === null ? null : vector(value, 3, name); }
export function freezeR03Experiment(value: R03Experiment): R03Experiment {
  const copy = structuredClone(value); for (const key of Object.keys(copy) as (keyof R03Experiment)[]) {
    if (typeof copy[key] === 'number' && copy[key] === 0) (copy as unknown as Record<string, unknown>)[key] = 0;
  }
  return Object.freeze(copy);
}
export function assertR03Experiment(value: unknown): asserts value is R03Experiment {
  const item = record(value, 'experiment'); keys(item, ['schema_version', 'model_contract', 'source_amplitude', 'mean_phase_rad',
    'phase_std_rad', 'qwp_angle_rad', 'hwp_angle_rad', 'seed'], 'experiment');
  if (item.schema_version !== 1 || item.model_contract !== R03_MODEL) fail('model/version');
  bounded(item.source_amplitude, 'source_amplitude', 0, 1e6); bounded(item.phase_std_rad, 'phase_std_rad', 0, Math.PI);
  for (const name of ['mean_phase_rad', 'qwp_angle_rad', 'hwp_angle_rad']) bounded(item[name], name, -2 * Math.PI, 2 * Math.PI);
  if (!Number.isSafeInteger(item.seed) || Number(item.seed) < 0 || Number(item.seed) > 0xffffffff) fail('seed: integer 0..2^32-1');
}
export function validateR03Reply(value: unknown, sent: R03Envelope): R03Validation {
  const data = record(value, 'validation'); keys(data, ['protocol_version', 'message_type', 'request_id', 'experiment_sha256', 'experiment'], 'validation');
  if (data.protocol_version !== 1 || data.message_type !== 'r03_ideal_validation') fail('validation type/version');
  if (requestId(data.request_id) !== requestId(sent.request_id)) fail('request identity');
  assertR03Experiment(data.experiment); if (!structuralEqual(data.experiment, sent.experiment)) fail('complete settings identity');
  const sha = digest(data.experiment_sha256); if (sent.experiment_sha256 !== null && sha !== digest(sent.experiment_sha256)) fail('settings digest identity');
  return Object.freeze({ protocol_version: 1, message_type: 'r03_ideal_validation', request_id: data.request_id as string,
    experiment_sha256: sha, experiment: freezeR03Experiment(data.experiment) });
}
function stage(value: unknown, id: R03StageId): R03Stage {
  const item = record(value, 'stage'); keys(item, ['id', 'coherency', 'stokes', 'normalized_stokes', 'polarized_direction',
    'degree_of_polarization', 'eigenvalues', 'roundoff_limited'], 'stage');
  if (item.id !== id || typeof item.roundoff_limited !== 'boolean') fail('stage order/roundoff flag');
  if (!Array.isArray(item.coherency) || item.coherency.length !== 2) fail('coherency 2x2');
  const coherency = Object.freeze(item.coherency.map(row => {
    if (!Array.isArray(row) || row.length !== 2) fail('coherency row'); return Object.freeze(row.map(value => {
      const c = record(value, 'coherency entry'); keys(c, ['re', 'im'], 'complex entry');
      return Object.freeze({ re: finite(c.re, 'coherency real'), im: finite(c.im, 'coherency imaginary') });
    }));
  }));
  const stokes = vector(item.stokes, 4, 'full Stokes'), normalized = nullableVector(item.normalized_stokes, 'normalized Stokes'),
    direction = nullableVector(item.polarized_direction, 'polarized direction'), eigenvalues = vector(item.eigenvalues, 2, 'eigenvalues');
  if (stokes[0] < 0) fail('negative S0');
  const dop = item.degree_of_polarization === null ? null : finite(item.degree_of_polarization, 'DoP');
  if (stokes[0] === 0 && (dop !== null || normalized !== null || direction !== null)) fail('dark undefined observables must be null');
  if (stokes[0] > 0 && (dop === null || normalized === null)) fail('nonzero S0 observables');
  if (dop !== null && (dop < 0 || dop > 1 + 64 * Number.EPSILON || dop > 1 && !item.roundoff_limited)) fail('DoP domain/roundoff flag');
  return Object.freeze({ id, coherency, stokes, normalized_stokes: normalized, polarized_direction: direction,
    degree_of_polarization: dop, eigenvalues, roundoff_limited: item.roundoff_limited });
}
/** Structural/identity checks only. The public Python model remains the scientific authority. */
export function decodeR03Result(value: unknown, sent: R03Envelope): R03Result {
  const data = record(value, 'result'); keys(data, ['protocol_version', 'message_type', 'request_id', 'experiment_sha256', 'experiment',
    'phase', 'stages', 'population', 'provenance', 'limitations'], 'result');
  if (data.protocol_version !== 1 || data.message_type !== 'r03_ideal_result') fail('result type/version');
  const reply = validateR03Reply({ protocol_version: 1, message_type: 'r03_ideal_validation', request_id: data.request_id,
    experiment_sha256: data.experiment_sha256, experiment: data.experiment }, sent);
  const phase = record(data.phase, 'phase'); keys(phase, ['shape', 'order', 'unwrapped_rad', 'wrapped_rad'], 'phase');
  if (!structuralEqual(phase.shape, [16, 16]) || phase.order !== 'C') fail('phase shape/order');
  const unwrapped = new Float64Array(vector(phase.unwrapped_rad, 256, 'unwrapped phase'));
  const wrapped = new Float64Array(vector(phase.wrapped_rad, 256, 'wrapped phase'));
  // NumPy may represent mod(-smallest_subnormal, 2π) as exactly 2π. Preserve it.
  for (const angle of wrapped) if (angle < 0 || angle > 2 * Math.PI) fail('wrapped phase domain');
  if (!Array.isArray(data.stages) || data.stages.length !== 4) fail('four algebraic stages');
  const stages = Object.freeze(data.stages.map((item, i) => stage(item, R03_STAGE_IDS[i])));
  const population = record(data.population, 'population'); keys(population, ['infinite_gaussian_degree_of_polarization', 'assumption'], 'population');
  const predicted = population.infinite_gaussian_degree_of_polarization === null ? null
    : bounded(population.infinite_gaussian_degree_of_polarization, 'population DoP', 0, 1);
  if ((reply.experiment.source_amplitude === 0) !== (predicted === null)) fail('dark population identity');
  const provenance = record(data.provenance, 'provenance');
  keys(provenance, ['model_contract', 'identity', 'rng_algorithm', 'rng_normal_sampler', 'rng_draw_shape', 'sample_order', 'sample_count',
    'probability_weight', 'measurement', 'source', 'element_order', 'units', 'python_version', 'numpy_version'], 'provenance');
  if (provenance.model_contract !== R03_MODEL || provenance.identity !== R03_IDENTITY || provenance.rng_algorithm !== 'PCG64'
      || provenance.rng_normal_sampler !== 'Generator.standard_normal' || !structuralEqual(provenance.rng_draw_shape, [16, 16])
      || provenance.sample_order !== 'C' || provenance.sample_count !== 256 || provenance.probability_weight !== 1 / 256
      || provenance.measurement !== 'probability_mean_uncentered_second_moment'
      || !structuralEqual(provenance.element_order, ['SLM', 'QWP', 'HWP'])) fail('provenance/model identity');
  text(provenance.source, 'source'); text(provenance.python_version, 'Python version', 80); text(provenance.numpy_version, 'NumPy version', 80);
  const units = record(provenance.units, 'units'); keys(units, ['phase', 'coherency', 'stokes', 'eigenvalues', 'normalized_stokes', 'polarized_direction', 'degree_of_polarization'], 'units');
  if (units.phase !== 'rad' || ['coherency', 'stokes', 'eigenvalues'].some(k => units[k] !== 'amplitude_unit^2')
      || ['normalized_stokes', 'polarized_direction', 'degree_of_polarization'].some(k => units[k] !== 'dimensionless')) fail('units');
  if (!Array.isArray(data.limitations) || data.limitations.length !== 4) fail('limitations');
  const limitations = Object.freeze(data.limitations.map(v => text(v, 'limitation', 1000)));
  return Object.freeze({ requestId: reply.request_id, experimentSha256: reply.experiment_sha256, experiment: reply.experiment,
    phase: Object.freeze({ shape: Object.freeze([16, 16]) as readonly [16, 16], order: 'C', unwrapped, wrapped }), stages,
    population: Object.freeze({ infinite_gaussian_degree_of_polarization: predicted, assumption: text(population.assumption, 'population assumption') }),
    provenance: Object.freeze(structuredClone(provenance)), limitations });
}
export function createR03FetchAPI(fetchImpl: typeof fetch = globalThis.fetch.bind(globalThis)): R03API {
  const post = async (operation: 'validate' | 'simulate', envelope: R03Envelope): Promise<unknown> => {
    requestId(envelope.request_id); assertR03Experiment(envelope.experiment);
    if (envelope.experiment_sha256 !== null) digest(envelope.experiment_sha256);
    const body = JSON.stringify(envelope); if (new TextEncoder().encode(body).byteLength > R03_REQUEST_CAP) fail('request cap');
    const response = await fetchImpl(`/api/research/r03-fig2a/${operation}`, { method: 'POST', credentials: 'same-origin', redirect: 'error',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body });
    const mime = response.headers.get('content-type')?.split(';', 1)[0].trim();
    if (mime !== 'application/json') { await response.body?.cancel('Ideal polarization content-type'); fail(`HTTP ${response.status} content-type`); }
    const bytes = await readBoundedResponse(response, response.ok ? R03_RESPONSE_CAP : R03_REQUEST_CAP);
    const value = parseStrictJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
    if (!response.ok) { const error = record(record(value, 'error reply').error, 'error');
      throw new Error(`HTTP ${response.status}: ${text(error.message, 'error message', 300)}`); }
    return value;
  };
  return { validate: envelope => post('validate', envelope), simulate: envelope => post('simulate', envelope) };
}
