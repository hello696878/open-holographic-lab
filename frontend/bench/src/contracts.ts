/** V1 presentation boundary. Optical validation and arithmetic belong to V0. */
export interface GridSpec { ny: number; nx: number; dy: number; dx: number }
export type SourceSpec =
  | { kind: 'uniform'; amplitude: number; phase_rad: number }
  | { kind: 'gaussian'; amplitude: number; phase_rad: number; waist_radius_m: number;
      waist_z_m: number; center_x_m: number; center_y_m: number };
export type ComponentSpec =
  | { id: string; kind: 'circular_aperture'; z_m: number; radius_m: number }
  | { id: string; kind: 'rectangular_aperture'; z_m: number; width_m: number; height_m: number }
  | { id: string; kind: 'thin_lens'; z_m: number; focal_length_m: number };
export interface Experiment {
  schema_version: 1;
  model_contract: 'v0_aligned_scalar_forward_v1';
  wavelength_m: number;
  grid: GridSpec;
  source: SourceSpec;
  components: ComponentSpec[];
  observation: { id: string; z_m: number };
}
export interface RequestEnvelope { request_id: string; experiment: Experiment }
export interface ValidationReply {
  protocol_version: 1; request_id: string; experiment_sha256: string; experiment: Experiment;
}
export interface StageRecord {
  selector: string; z_m: number; norm: number; previous_norm: number | null;
  delta_norm: number | null; transmission_ratio: number | null;
}
export interface DecodedResult {
  readonly requestId: string;
  readonly experimentSha256: string;
  readonly experiment: Experiment;
  readonly stages: readonly StageRecord[];
  /** Owned float64 buffers; presentation consumers must not mutate them. */
  readonly intensity: Float64Array;
  readonly x: Float64Array;
  readonly y: Float64Array;
  readonly intensityMax: number;
}
export type ResultData = DecodedResult;
export interface BenchAPI {
  validate(envelope: RequestEnvelope): Promise<ValidationReply>;
  simulate(envelope: RequestEnvelope): Promise<ArrayBuffer>;
}
export const MAX_RESPONSE_BYTES = 2.25 * 1024 * 1024;
export const MAX_HEADER_BYTES = 16384;
export const MAX_REQUEST_BYTES = 32768;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const SHA = /^[0-9a-f]{64}$/;

function fail(message: string): never { throw new Error(`V1 protocol: ${message}`); }
function record(value: unknown, name: string): Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) fail(`${name}: expected object`);
  return value as Record<string, unknown>;
}
function keys(value: Record<string, unknown>, expected: readonly string[], name: string): void {
  const actual = Object.keys(value);
  if (actual.length !== expected.length || actual.some(k => !expected.includes(k))) fail(`${name}: incorrect keys`);
}
function finite(value: unknown, name: string, nonnegative = false, positive = false): number {
  if (typeof value !== 'number' || !Number.isFinite(value)
      || (nonnegative && value < 0) || (positive && value <= 0)) fail(`${name}: invalid finite number`);
  return value;
}
function integer(value: unknown, name: string, minimum = 0, maximum = Number.MAX_SAFE_INTEGER): number {
  const number = finite(value, name);
  if (!Number.isSafeInteger(number) || number < minimum || number > maximum) fail(`${name}: invalid integer`);
  return number;
}
function identifier(value: unknown, name: string): string {
  if (typeof value !== 'string' || !/^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(value) || value === 'source') {
    fail(`${name}: invalid identifier`);
  }
  return value;
}
function requestId(value: unknown): string {
  if (typeof value !== 'string' || !UUID.test(value)) fail('invalid canonical UUIDv4 request identity');
  return value;
}

/** Bounded JSON with duplicate-key rejection; does not accept nonfinite numbers. */
export function parseStrictJSON(text: string): unknown {
  let cursor = 0;
  const space = () => { while (/[ \t\r\n]/.test(text[cursor] ?? '') && cursor < text.length) cursor++; };
  const string = (): string => {
    const start = cursor++;
    while (cursor < text.length) {
      if (text[cursor] === '\\') { cursor += 2; continue; }
      if (text[cursor++] === '"') {
        try { return JSON.parse(text.slice(start, cursor)) as string; }
        catch { return fail('invalid JSON string'); }
      }
    }
    return fail('unterminated JSON string');
  };
  const value = (depth: number): unknown => {
    if (depth > 12) fail('JSON nesting exceeds 12');
    space();
    const token = text[cursor];
    if (token === '"') return string();
    if (token === '{') {
      cursor++; space();
      const object = Object.create(null) as Record<string, unknown>;
      if (text[cursor] === '}') { cursor++; return object; }
      for (;;) {
        space(); if (text[cursor] !== '"') fail('expected JSON object key');
        const key = string();
        if (Object.hasOwn(object, key)) fail(`duplicate JSON key ${key}`);
        space(); if (text[cursor++] !== ':') fail('expected JSON colon');
        object[key] = value(depth + 1);
        space(); const next = text[cursor++];
        if (next === '}') return object;
        if (next !== ',') fail('expected JSON object separator');
      }
    }
    if (token === '[') {
      cursor++; space(); const array: unknown[] = [];
      if (text[cursor] === ']') { cursor++; return array; }
      for (;;) {
        array.push(value(depth + 1)); space(); const next = text[cursor++];
        if (next === ']') return array;
        if (next !== ',') fail('expected JSON array separator');
      }
    }
    for (const [literal, result] of [['true', true], ['false', false], ['null', null]] as const) {
      if (text.startsWith(literal, cursor)) { cursor += literal.length; return result; }
    }
    const match = /^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(text.slice(cursor));
    if (!match) return fail('invalid JSON value');
    cursor += match[0].length;
    return finite(Number(match[0]), 'JSON number');
  };
  const result = value(0); space();
  if (cursor !== text.length) fail('trailing JSON content');
  return result;
}

/** Checks schema/type/resource shape only. Python V0 remains authoritative. */
export function assertExperiment(value: unknown): asserts value is Experiment {
  const experiment = record(value, 'experiment');
  keys(experiment, ['schema_version', 'model_contract', 'wavelength_m', 'grid', 'source', 'components', 'observation'], 'experiment');
  if (experiment.schema_version !== 1 || experiment.model_contract !== 'v0_aligned_scalar_forward_v1') fail('experiment version/contract');
  finite(experiment.wavelength_m, 'wavelength_m', false, true);
  const grid = record(experiment.grid, 'grid'); keys(grid, ['ny', 'nx', 'dy', 'dx'], 'grid');
  integer(grid.ny, 'ny', 1, 512); integer(grid.nx, 'nx', 1, 512);
  finite(grid.dy, 'dy', false, true); finite(grid.dx, 'dx', false, true);
  const source = record(experiment.source, 'source');
  if (source.kind === 'uniform') keys(source, ['kind', 'amplitude', 'phase_rad'], 'uniform source');
  else if (source.kind === 'gaussian') {
    keys(source, ['kind', 'amplitude', 'phase_rad', 'waist_radius_m', 'waist_z_m', 'center_x_m', 'center_y_m'], 'gaussian source');
    finite(source.waist_radius_m, 'waist_radius_m', false, true);
    for (const key of ['waist_z_m', 'center_x_m', 'center_y_m']) finite(source[key], key);
  } else fail('unknown source kind');
  finite(source.amplitude, 'amplitude', true); finite(source.phase_rad, 'phase_rad');
  if (!Array.isArray(experiment.components) || experiment.components.length > 8) fail('components: expected array of at most 8');
  const observation = record(experiment.observation, 'observation'); keys(observation, ['id', 'z_m'], 'observation');
  const ids = new Set([identifier(observation.id, 'observation.id')]); let previousZ = 0;
  for (const [index, item] of experiment.components.entries()) {
    const component = record(item, `components[${index}]`);
    let required: string[];
    if (component.kind === 'circular_aperture') {
      required = ['id', 'kind', 'z_m', 'radius_m']; finite(component.radius_m, 'radius_m', false, true);
    } else if (component.kind === 'rectangular_aperture') {
      required = ['id', 'kind', 'z_m', 'width_m', 'height_m'];
      finite(component.width_m, 'width_m', false, true); finite(component.height_m, 'height_m', false, true);
    } else if (component.kind === 'thin_lens') {
      required = ['id', 'kind', 'z_m', 'focal_length_m'];
      if (finite(component.focal_length_m, 'focal_length_m') === 0) fail('focal_length_m: zero');
    } else return fail('unknown component kind');
    keys(component, required, 'component'); const id = identifier(component.id, 'component.id');
    if (ids.has(id)) fail('duplicate component/observation identifier'); ids.add(id);
    const z = finite(component.z_m, 'z_m', true);
    if (z < previousZ) fail('unordered components'); previousZ = z;
  }
  if (finite(observation.z_m, 'observation.z_m', true) < previousZ) fail('observation before last component');
}

export function structuralEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object') return false;
  if (Array.isArray(a) || Array.isArray(b)) {
    return Array.isArray(a) && Array.isArray(b) && a.length === b.length && a.every((v, i) => structuralEqual(v, b[i]));
  }
  const left = a as Record<string, unknown>; const right = b as Record<string, unknown>;
  return Object.keys(left).length === Object.keys(right).length
    && Object.keys(left).every(key => Object.hasOwn(right, key) && structuralEqual(left[key], right[key]));
}
export function cloneExperiment(experiment: Experiment): Experiment { return structuredClone(experiment); }
function deepFreeze<T>(value: T): T {
  if (value !== null && typeof value === 'object' && !Object.isFrozen(value)) {
    for (const item of Object.values(value)) deepFreeze(item);
    Object.freeze(value);
  }
  return value;
}
export function freezeExperiment(experiment: Experiment): Experiment { return deepFreeze(cloneExperiment(experiment)); }

export function validateValidationReply(value: unknown, submitted: RequestEnvelope): ValidationReply {
  const reply = record(value, 'validation reply');
  keys(reply, ['protocol_version', 'request_id', 'experiment_sha256', 'experiment'], 'validation reply');
  if (reply.protocol_version !== 1) fail('validation protocol_version');
  const id = requestId(reply.request_id);
  if (id !== submitted.request_id) fail('validation request identity mismatch');
  if (typeof reply.experiment_sha256 !== 'string' || !SHA.test(reply.experiment_sha256)) fail('invalid experiment hash');
  assertExperiment(reply.experiment);
  if (!structuralEqual(reply.experiment, submitted.experiment)) fail('validation experiment echo mismatch');
  return Object.freeze({ protocol_version: 1, request_id: id,
    experiment_sha256: reply.experiment_sha256, experiment: freezeExperiment(reply.experiment) });
}

/** Strict bounded frame decoder. No partial buffers or state are published. */
export function decodeResult(frame: ArrayBuffer, submitted: RequestEnvelope): DecodedResult {
  if (!(frame instanceof ArrayBuffer) || frame.byteLength < 16 || frame.byteLength > MAX_RESPONSE_BYTES) fail('received frame length/cap');
  requestId(submitted.request_id); assertExperiment(submitted.experiment);
  const bytes = new Uint8Array(frame); const view = new DataView(frame);
  const magic = [79, 72, 76, 65, 66, 86, 49, 0];
  if (magic.some((byte, index) => bytes[index] !== byte)) fail('magic');
  if (view.getUint32(12, true) !== 0) fail('reserved bytes');
  const headerLength = view.getUint32(8, true);
  if (headerLength < 2 || headerLength > MAX_HEADER_BYTES) fail('header length/cap');
  const payloadStart = 16 + Math.ceil(headerLength / 8) * 8;
  if (payloadStart > frame.byteLength) fail('truncated header');
  for (let i = 16 + headerLength; i < payloadStart; i++) if (bytes[i] !== 0) fail('nonzero alignment padding');
  let text: string;
  try { text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes.subarray(16, 16 + headerLength)); }
  catch { return fail('invalid UTF-8 header'); }
  const header = record(parseStrictJSON(text), 'header');
  keys(header, ['protocol_version', 'request_id', 'experiment_sha256', 'experiment', 'stages', 'arrays', 'intensity_max'], 'header');
  const reply = validateValidationReply({ protocol_version: header.protocol_version, request_id: header.request_id,
    experiment_sha256: header.experiment_sha256, experiment: header.experiment }, submitted);
  const { nx, ny, dx, dy } = reply.experiment.grid;
  const expectedStages: [string, number][] = [['source', 0]];
  for (const component of reply.experiment.components) {
    expectedStages.push([`before:${component.id}`, component.z_m], [`after:${component.id}`, component.z_m]);
  }
  expectedStages.push(['observation', reply.experiment.observation.z_m]);
  if (!Array.isArray(header.stages) || header.stages.length !== expectedStages.length) fail('stage count');
  const stages: StageRecord[] = [];
  for (const [index, item] of header.stages.entries()) {
    const stage = record(item, 'stage');
    keys(stage, ['selector', 'z_m', 'norm', 'previous_norm', 'delta_norm', 'transmission_ratio'], 'stage');
    if (stage.selector !== expectedStages[index][0] || finite(stage.z_m, 'stage z_m', true) !== expectedStages[index][1]) fail('stage order/position');
    const norm = finite(stage.norm, 'stage norm', true);
    const previous = index === 0 ? null : stages[index - 1].norm;
    if (stage.previous_norm !== previous) fail('stage norm chain');
    const expectedDelta = previous === null ? null : norm - previous;
    const expectedRatio = previous === null || previous === 0 ? null : norm / previous;
    if (stage.delta_norm !== expectedDelta || stage.transmission_ratio !== expectedRatio) fail('stage derived values/nulls');
    if (expectedDelta !== null) finite(stage.delta_norm, 'delta_norm');
    if (expectedRatio !== null) finite(stage.transmission_ratio, 'transmission_ratio', true);
    stages.push(Object.freeze({ selector: stage.selector as string, z_m: stage.z_m as number,
      norm, previous_norm: stage.previous_norm as number | null,
      delta_norm: stage.delta_norm as number | null, transmission_ratio: stage.transmission_ratio as number | null }));
  }
  if (!Array.isArray(header.arrays) || header.arrays.length !== 3) fail('required array descriptors');
  const descriptorValues = [
    { name: 'intensity', shape: [ny, nx], offset: 0, nbytes: ny * nx * 8, units: 'amplitude_unit^2' },
    { name: 'x_m', shape: [nx], offset: ny * nx * 8, nbytes: nx * 8, units: 'm' },
    { name: 'y_m', shape: [ny], offset: ny * nx * 8 + nx * 8, nbytes: ny * 8, units: 'm' },
  ];
  const arrays: Float64Array[] = [];
  const expectedPayloadLength = 8 * (ny * nx + nx + ny);
  if (frame.byteLength !== payloadStart + expectedPayloadLength) fail('exact payload length/trailing bytes');
  for (const [index, expected] of descriptorValues.entries()) {
    const descriptor = record(header.arrays[index], 'descriptor');
    keys(descriptor, ['name', 'dtype', 'order', 'shape', 'offset_bytes', 'nbytes', 'units'], 'descriptor');
    if (descriptor.name !== expected.name || descriptor.dtype !== 'float64-le' || descriptor.order !== 'C'
        || descriptor.units !== expected.units || !structuralEqual(descriptor.shape, expected.shape)) fail('descriptor name/dtype/order/shape/units');
    const offset = integer(descriptor.offset_bytes, 'offset_bytes');
    const nbytes = integer(descriptor.nbytes, 'nbytes');
    if (offset % 8 !== 0 || nbytes % 8 !== 0 || offset !== expected.offset || nbytes !== expected.nbytes) fail('descriptor alignment/gap/overlap/size');
    const array = new Float64Array(nbytes / 8);
    for (let i = 0; i < array.length; i++) array[i] = finite(view.getFloat64(payloadStart + offset + 8 * i, true), expected.name, index === 0);
    arrays.push(array);
  }
  const [intensity, x, y] = arrays;
  for (let c = 0; c < nx; c++) if (x[c] !== (c - Math.floor(nx / 2)) * dx) fail('x coordinate mismatch');
  for (let r = 0; r < ny; r++) if (y[r] !== (r - Math.floor(ny / 2)) * dy) fail('y coordinate mismatch');
  let maximum = 0;
  for (const number of intensity) if (number > maximum) maximum = number;
  if (finite(header.intensity_max, 'intensity_max', true) !== maximum) fail('declared intensity maximum mismatch');
  return Object.freeze({ requestId: reply.request_id, experimentSha256: reply.experiment_sha256,
    experiment: reply.experiment, stages: Object.freeze(stages), intensity, x, y, intensityMax: maximum });
}

export async function readBoundedResponse(response: Response, cap: number): Promise<ArrayBuffer> {
  const declared = response.headers.get('content-length');
  if (declared !== null && (!/^\d+$/.test(declared) || !Number.isSafeInteger(Number(declared)) || Number(declared) > cap)) {
    await response.body?.cancel('V1 declared response cap');
    fail('HTTP content-length/cap');
  }
  if (!response.body) fail('missing response body');
  const reader = response.body.getReader(); const chunks: Uint8Array[] = []; let length = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read(); if (done) break;
      length += value.byteLength;
      if (length > cap) { await reader.cancel('V1 response cap'); fail('streamed response cap'); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  if (declared !== null && Number(declared) !== length) fail('HTTP content-length mismatch');
  const bytes = new Uint8Array(length); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return bytes.buffer;
}

export function createFetchAPI(fetchImpl: typeof fetch = globalThis.fetch.bind(globalThis)): BenchAPI {
  const post = async (endpoint: string, envelope: RequestEnvelope, mime: string, cap: number): Promise<ArrayBuffer> => {
    requestId(envelope.request_id);
    const body = JSON.stringify(envelope);
    if (new TextEncoder().encode(body).byteLength > MAX_REQUEST_BYTES) fail('request body cap');
    const response = await fetchImpl(`/api/v1/${endpoint}`, { method: 'POST', credentials: 'same-origin',
      redirect: 'error', headers: { 'Content-Type': 'application/json', Accept: mime }, body });
    const contentType = response.headers.get('content-type')?.split(';', 1)[0].trim();
    if (!response.ok) {
      const errorBytes = await readBoundedResponse(response, MAX_HEADER_BYTES);
      let message = `HTTP ${response.status}`;
      if (contentType === 'application/json') {
        try {
          const data = record(parseStrictJSON(new TextDecoder('utf-8', { fatal: true }).decode(errorBytes)), 'error');
          const error = record(data.error, 'error detail');
          if (typeof error.message === 'string') message += `: ${error.message.slice(0, 300)}`;
        } catch { /* Keep the actual HTTP status when the error body is malformed. */ }
      }
      throw new Error(message);
    }
    if (contentType !== mime) { await response.body?.cancel('V1 rejected content-type'); fail('HTTP content-type'); }
    return readBoundedResponse(response, cap);
  };
  return {
    async validate(envelope) {
      const bytes = await post('validate', envelope, 'application/json', MAX_HEADER_BYTES);
      return validateValidationReply(parseStrictJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes)), envelope);
    },
    simulate(envelope) { return post('simulate', envelope, 'application/octet-stream', MAX_RESPONSE_BYTES); },
  };
}
