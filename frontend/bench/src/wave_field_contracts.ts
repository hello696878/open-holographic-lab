/** W1 transport and geometry metadata only. No optical calculation lives in the browser. */
import { assertExperiment, freezeExperiment, parseStrictJSON, readBoundedResponse, structuralEqual,
  type Experiment, type StageRecord } from './contracts';

export const W1_MAX_AXIS = 128;
export const W1_MAX_SECTIONS = 25;
export const W1_MAX_HEADER_BYTES = 65536;
export const W1_MAX_RESPONSE_BYTES = 3344400;
export const W1_METADATA_BYTES = 65536;
export const W1_APPARATUS_CAP = 512 * 1024;
/** Explicit opt-in example. Never replaces an existing draft without its named user action. */
export const W1_EXAMPLE: Experiment = freezeExperiment({ schema_version: 1, model_contract: 'v0_aligned_scalar_forward_v1',
  wavelength_m: 633e-9, grid: { nx: 128, ny: 128, dx: 16e-6, dy: 16e-6 },
  source: { kind: 'gaussian', amplitude: 1, phase_rad: .31, waist_radius_m: 160e-6, waist_z_m: 0, center_x_m: 0, center_y_m: 0 },
  components: [{ id: 'aperture', kind: 'circular_aperture', z_m: .03, radius_m: 260e-6 },
    { id: 'lens', kind: 'thin_lens', z_m: .06, focal_length_m: .08 }], observation: { id: 'detector', z_m: .22 } });
export interface WaveFieldSampling { readonly interior_z_m: readonly number[] }
export interface WaveFieldRequest { readonly request_id: string; readonly experiment: Experiment; readonly sampling: WaveFieldSampling }
export interface WaveFieldPlane {
  readonly id: string; readonly stage: string; readonly z_m: number;
  readonly anchor_selector: string; readonly anchor_z_m: number; readonly separation_m: number;
  readonly norm: number; readonly previous_norm: number | null; readonly delta_norm: number | null;
  readonly transmission_ratio: number | null; readonly comparison: 'previous_stage' | 'upstream_anchor';
  readonly on_axis_intensity: number; readonly max_intensity: number;
}
export interface WaveFieldResult {
  readonly requestId: string; readonly experimentSha256: string; readonly experiment: Experiment;
  readonly sampling: WaveFieldSampling; readonly planes: readonly WaveFieldPlane[]; readonly stages: readonly StageRecord[];
  /** One owned C-order float64 stack. Section slices borrow this backing buffer. */
  readonly intensities: Float64Array; readonly x: Float64Array; readonly y: Float64Array;
}
export interface WaveFieldAPI { simulate(envelope: WaveFieldRequest): Promise<ArrayBuffer> }
type PlanEntry = Pick<WaveFieldPlane, 'id' | 'stage' | 'z_m' | 'anchor_selector' | 'anchor_z_m' | 'separation_m' | 'comparison'>;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const fail = (message: string): never => { throw new Error(`W1 protocol: ${message}`); };
function object(value: unknown, name: string): Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) fail(`${name}: expected object`);
  return value as Record<string, unknown>;
}
function keys(value: Record<string, unknown>, expected: readonly string[], name: string): void {
  const actual = Object.keys(value); if (actual.length !== expected.length || actual.some(key => !expected.includes(key))) fail(`${name}: incorrect keys`);
}
function number(value: unknown, name: string, nonnegative = false): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || nonnegative && value < 0) fail(`${name}: expected finite${nonnegative ? ' nonnegative' : ''} number`);
  return value as number;
}
/** W1's policy is additional to V0, and never changes the ordinary 512-axis policy. */
export function requireWaveFieldExperiment(experiment: Experiment): void {
  assertExperiment(experiment);
  if (experiment.grid.nx > W1_MAX_AXIS || experiment.grid.ny > W1_MAX_AXIS) throw new Error('Computed Sections requires each grid axis ≤128; settings were not resized. Ordinary Sequential remains available.');
  if (experiment.source.kind !== 'gaussian' || experiment.components.length !== 2
      || !['circular_aperture', 'rectangular_aperture'].includes(experiment.components[0].kind)
      || experiment.components[1].kind !== 'thin_lens') throw new Error('Computed Sections supports exactly Gaussian → one circular/rectangular aperture → one thin lens → observation, in stored order. Settings were not changed.');
}
/** Metadata-only allocation; the explicit positions, not an implied continuous field, are submitted. */
export function buildWaveFieldSampling(experiment: Experiment): WaveFieldSampling {
  requireWaveFieldExperiment(experiment);
  const edges = [0, experiment.components[0].z_m, experiment.components[1].z_m, experiment.observation.z_m];
  const spans = edges.slice(1).map((end, index) => end - edges[index]), total = spans.reduce((a, b) => a + b, 0);
  if (!total) return Object.freeze({ interior_z_m: Object.freeze([]) });
  const raw = spans.map(span => span / total * 19), counts = raw.map(Math.floor);
  const priority = [0, 1, 2].filter(index => spans[index] > 0).sort((a, b) => (raw[b] - counts[b]) - (raw[a] - counts[a]) || a - b);
  for (let left = 19 - counts.reduce((a, b) => a + b, 0), i = 0; left > 0; left--, i++) counts[priority[i % priority.length]]++;
  const positions: number[] = [];
  counts.forEach((count, index) => { for (let j = 1; j <= count; j++) positions.push(edges[index] + spans[index] * j / (count + 1)); });
  const sampling = Object.freeze({ interior_z_m: Object.freeze(positions) }); waveFieldPlan(experiment, sampling); return sampling;
}
export function waveFieldPlan(experiment: Experiment, sampling: WaveFieldSampling): readonly PlanEntry[] {
  requireWaveFieldExperiment(experiment);
  keys(object(sampling, 'sampling'), ['interior_z_m'], 'sampling');
  if (!sampling || !Array.isArray(sampling.interior_z_m) || sampling.interior_z_m.length > 19) fail('interior positions cap/array');
  const [aperture, lens] = experiment.components, end = experiment.observation.z_m;
  const z = sampling.interior_z_m;
  z.forEach((value, index) => {
    number(value, 'interior z', true);
    if (value <= 0 || value >= end || value === aperture.z_m || value === lens.z_m || index > 0 && value <= z[index - 1]) fail('interior positions must be strictly ordered, distinct, and inside open propagation intervals');
  });
  const plan: PlanEntry[] = [];
  const event = (stage: string, at: number, anchor: string, anchorZ: number) => plan.push(Object.freeze({ id: `section:${stage}`, stage, z_m: at,
    anchor_selector: anchor, anchor_z_m: anchorZ, separation_m: at - anchorZ, comparison: 'previous_stage' }));
  const gap = (start: number, stop: number, anchor: string) => z.forEach((at, index) => { if (at > start && at < stop) plan.push(Object.freeze({
    id: `section:interior:${String(index).padStart(3, '0')}`, stage: 'interior', z_m: at, anchor_selector: anchor, anchor_z_m: start,
    separation_m: at - start, comparison: 'upstream_anchor' })); });
  event('source', 0, 'source', 0); gap(0, aperture.z_m, 'source');
  event(`before:${aperture.id}`, aperture.z_m, 'source', 0); event(`after:${aperture.id}`, aperture.z_m, `after:${aperture.id}`, aperture.z_m);
  gap(aperture.z_m, lens.z_m, `after:${aperture.id}`); event(`before:${lens.id}`, lens.z_m, `after:${aperture.id}`, aperture.z_m);
  event(`after:${lens.id}`, lens.z_m, `after:${lens.id}`, lens.z_m); gap(lens.z_m, end, `after:${lens.id}`);
  event('observation', end, `after:${lens.id}`, lens.z_m);
  if (plan.length !== z.length + 6 || plan.length > W1_MAX_SECTIONS) fail('required event/section allocation');
  return Object.freeze(plan);
}
export function waveFieldSection(result: WaveFieldResult, index: number): Float64Array {
  if (!Number.isInteger(index) || index < 0 || index >= result.planes.length) throw new RangeError('Unknown calculated section');
  const pixels = result.experiment.grid.nx * result.experiment.grid.ny;
  return result.intensities.subarray(index * pixels, (index + 1) * pixels);
}
export function waveFieldOwnedResults(results: readonly (WaveFieldResult | null)[]): number {
  const buffers = new Set<ArrayBufferLike>(), unique = new Set<WaveFieldResult>();
  for (const result of results) if (result) { unique.add(result); for (const array of [result.intensities, result.x, result.y]) buffers.add(array.buffer); }
  return [...buffers].reduce((sum, buffer) => sum + buffer.byteLength, 0) + unique.size * W1_METADATA_BYTES;
}
export function estimateWaveFieldOperation(experiment: Experiment) {
  const sampling = buildWaveFieldSampling(experiment), sections = waveFieldPlan(experiment, sampling).length;
  const { nx, ny } = experiment.grid, pixels = nx * ny;
  const payloadBytes = 8 * (sections * pixels + nx + ny), frameBytes = 16 + W1_MAX_HEADER_BYTES + payloadBytes;
  // Stack + every section's RGBA source + detector + inspector/canvas + bounded curtains,
  // mounted geometry/labels, metadata and axial arrays. Includes aliases only once.
  const persistentBytes = payloadBytes + sections * pixels * 4 + pixels * 12 + sections * (nx + ny) * 8
    + W1_APPARATUS_CAP + W1_METADATA_BYTES + sections * 128;
  const transientBytes = Math.max(2 * frameBytes, frameBytes + payloadBytes, persistentBytes + pixels * 8);
  if (persistentBytes > 6 * 1024 * 1024) fail('internal 6 MiB incoming reservation exceeded');
  return Object.freeze({ sections, payloadBytes, frameBytes, persistentBytes, transientBytes });
}
/** Validate the complete frame and every identity before exposing any numerical array. */
export function decodeWaveFieldResult(frame: ArrayBuffer, submitted: WaveFieldRequest): WaveFieldResult {
  if (!(frame instanceof ArrayBuffer) || frame.byteLength < 16 || frame.byteLength > W1_MAX_RESPONSE_BYTES) fail('frame length/cap');
  if (!UUID.test(submitted.request_id)) fail('request identity');
  const plan = waveFieldPlan(submitted.experiment, submitted.sampling), view = new DataView(frame), bytes = new Uint8Array(frame);
  if ([79, 72, 76, 65, 66, 87, 70, 0].some((value, index) => bytes[index] !== value)) fail('magic');
  if (view.getUint32(12, true) !== 0) fail('reserved bytes');
  const headerLength = view.getUint32(8, true), payloadStart = 16 + Math.ceil(headerLength / 8) * 8;
  if (headerLength < 2 || headerLength > W1_MAX_HEADER_BYTES || payloadStart > frame.byteLength) fail('header length/cap');
  for (let i = 16 + headerLength; i < payloadStart; i++) if (bytes[i] !== 0) fail('alignment padding');
  let text: string;
  try { text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes.subarray(16, 16 + headerLength)); }
  catch { return fail('invalid UTF-8'); }
  const header = object(parseStrictJSON(text), 'header');
  keys(header, ['protocol_version', 'message_type', 'request_id', 'experiment_sha256', 'experiment', 'sampling', 'ordered_section_ids', 'planes', 'stages', 'arrays'], 'header');
  if (header.protocol_version !== 1 || header.message_type !== 'w1_wave_field' || header.request_id !== submitted.request_id) fail('discriminator/request identity');
  if (typeof header.experiment_sha256 !== 'string' || !/^[0-9a-f]{64}$/.test(header.experiment_sha256)) fail('experiment digest');
  assertExperiment(header.experiment);
  if (!structuralEqual(header.experiment, submitted.experiment) || !structuralEqual(header.sampling, submitted.sampling)) fail('frozen experiment/sampling echo');
  if (!structuralEqual(header.ordered_section_ids, plan.map(plane => plane.id))) fail('section order/identities');
  const stagesExpected = plan.filter(plane => plane.stage !== 'interior');
  if (!Array.isArray(header.stages) || header.stages.length !== stagesExpected.length) fail('canonical stage count');
  const stages: StageRecord[] = [];
  (header.stages as unknown[]).forEach((item, index) => {
    const stage = object(item, 'stage'); keys(stage, ['selector', 'z_m', 'norm', 'previous_norm', 'delta_norm', 'transmission_ratio'], 'stage');
    if (stage.selector !== stagesExpected[index].stage || stage.z_m !== stagesExpected[index].z_m) fail('canonical stage identity');
    const norm = number(stage.norm, 'stage norm', true), previous = index ? stages[index - 1].norm : null;
    if (stage.previous_norm !== previous || stage.delta_norm !== (previous === null ? null : norm - previous)
        || stage.transmission_ratio !== (previous === null || previous === 0 ? null : norm / previous)) fail('canonical signed norm chain');
    if (stage.delta_norm !== null) number(stage.delta_norm, 'signed delta');
    if (stage.transmission_ratio !== null) number(stage.transmission_ratio, 'ratio', true);
    stages.push(Object.freeze({ selector: stage.selector as string, z_m: stage.z_m as number, norm, previous_norm: previous,
      delta_norm: stage.delta_norm as number | null, transmission_ratio: stage.transmission_ratio as number | null }));
  });
  if (!Array.isArray(header.planes) || header.planes.length !== plan.length) fail('section count');
  const planes: WaveFieldPlane[] = (header.planes as unknown[]).map((item, index) => {
    const plane = object(item, 'plane'); keys(plane, ['id', 'stage', 'z_m', 'anchor_selector', 'anchor_z_m', 'separation_m', 'norm', 'previous_norm', 'delta_norm', 'transmission_ratio', 'comparison', 'on_axis_intensity', 'max_intensity'], 'plane');
    for (const key of Object.keys(plan[index]) as (keyof PlanEntry)[]) if (plane[key] !== plan[index][key]) fail(`section ${key}/upstream provenance`);
    const norm = number(plane.norm, 'section norm', true), axis = number(plane.on_axis_intensity, 'on-axis intensity', true), maximum = number(plane.max_intensity, 'section maximum', true);
    if (plan[index].stage === 'interior') {
      const anchor = stages.find(stage => stage.selector === plane.anchor_selector)!;
      if (plane.previous_norm !== anchor.norm || plane.delta_norm !== norm - anchor.norm
          || plane.transmission_ratio !== (anchor.norm === 0 ? null : norm / anchor.norm)) fail('interior signed anchor comparison');
    } else {
      const stage = stages.find(stage => stage.selector === plane.stage)!;
      if (['norm', 'previous_norm', 'delta_norm', 'transmission_ratio'].some(key => plane[key] !== stage[key as keyof StageRecord])) fail('canonical event diagnostics');
    }
    if (plane.delta_norm !== null) number(plane.delta_norm, 'signed section delta');
    if (plane.transmission_ratio !== null) number(plane.transmission_ratio, 'section ratio', true);
    return Object.freeze({ ...plane, norm, on_axis_intensity: axis, max_intensity: maximum }) as unknown as WaveFieldPlane;
  });
  const { nx, ny, dx, dy } = submitted.experiment.grid, pixels = nx * ny, k = planes.length;
  const expected = [ { name: 'intensities', shape: [k, ny, nx], offset: 0, length: k * pixels, units: 'amplitude_unit^2' },
    { name: 'x_m', shape: [nx], offset: k * pixels * 8, length: nx, units: 'm' },
    { name: 'y_m', shape: [ny], offset: (k * pixels + nx) * 8, length: ny, units: 'm' } ];
  if (!Array.isArray(header.arrays) || header.arrays.length !== 3) fail('required array descriptors');
  if (frame.byteLength !== payloadStart + 8 * (k * pixels + nx + ny)) fail('exact frame length/trailing bytes');
  const arrays = expected.map((entry, index) => {
    const descriptor = object((header.arrays as unknown[])[index], 'array'); keys(descriptor, ['name', 'dtype', 'order', 'shape', 'offset_bytes', 'nbytes', 'units'], 'array');
    if (descriptor.name !== entry.name || descriptor.dtype !== 'float64-le' || descriptor.order !== 'C' || descriptor.units !== entry.units
        || !structuralEqual(descriptor.shape, entry.shape) || descriptor.offset_bytes !== entry.offset || descriptor.nbytes !== entry.length * 8) fail('array dtype/shape/offset/size/units');
    const array = new Float64Array(entry.length);
    for (let i = 0; i < entry.length; i++) array[i] = number(view.getFloat64(payloadStart + entry.offset + i * 8, true), entry.name, index === 0);
    return array;
  });
  const [intensities, x, y] = arrays;
  for (let column = 0; column < nx; column++) if (x[column] !== (column - Math.floor(nx / 2)) * dx) fail('x coordinate/orientation');
  for (let row = 0; row < ny; row++) if (y[row] !== (row - Math.floor(ny / 2)) * dy) fail('y coordinate/orientation');
  planes.forEach((plane, index) => {
    let maximum = 0; for (let i = index * pixels; i < (index + 1) * pixels; i++) maximum = Math.max(maximum, intensities[i]);
    if (maximum !== plane.max_intensity || intensities[index * pixels + Math.floor(ny / 2) * nx + Math.floor(nx / 2)] !== plane.on_axis_intensity) fail('section raw maximum/on-axis identity');
  });
  return Object.freeze({ requestId: submitted.request_id, experimentSha256: header.experiment_sha256 as string, experiment: freezeExperiment(submitted.experiment),
    sampling: Object.freeze({ interior_z_m: Object.freeze([...submitted.sampling.interior_z_m]) }), planes: Object.freeze(planes), stages: Object.freeze(stages), intensities, x, y });
}
export function createWaveFieldFetchAPI(fetchImpl: typeof fetch = globalThis.fetch.bind(globalThis)): WaveFieldAPI {
  return { async simulate(envelope) {
    if (!UUID.test(envelope.request_id)) fail('request identity'); waveFieldPlan(envelope.experiment, envelope.sampling);
    const body = JSON.stringify(envelope); if (new TextEncoder().encode(body).byteLength > 32768) fail('request body cap');
    const response = await fetchImpl('/api/w1/simulate', { method: 'POST', credentials: 'same-origin', redirect: 'error',
      headers: { 'Content-Type': 'application/json', Accept: 'application/octet-stream' }, body });
    const mime = response.headers.get('content-type')?.split(';', 1)[0].trim();
    if (!response.ok) {
      const bytes = await readBoundedResponse(response, W1_MAX_HEADER_BYTES); let detail = '';
      if (mime === 'application/json') try { const json = object(parseStrictJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes)), 'error');
        const error = object(json.error, 'error detail'); if (typeof error.message === 'string') detail = `: ${error.message.slice(0, 300)}`; } catch { /* Preserve HTTP status. */ }
      throw new Error(`HTTP ${response.status}${detail}`);
    }
    if (mime !== 'application/octet-stream') { await response.body?.cancel('W1 content-type'); fail('HTTP content-type'); }
    return readBoundedResponse(response, W1_MAX_RESPONSE_BYTES);
  } };
}
