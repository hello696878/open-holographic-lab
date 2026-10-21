/** W2 owned transport records and presentation metadata. No optical tracing in the browser. */
import { parseStrictJSON, readBoundedResponse } from './contracts';

export const W2_MODEL = 'w2_ideal_geometric_routing_v1' as const;
export const W2_REQUEST_CAP = 32 * 1024;
export const W2_RESPONSE_CAP = 512 * 1024;
export const W2_RETAINED_RESERVATION = 2 * 1024 * 1024;
export const W2_TRANSIENT_RESERVATION = 4 * 1024 * 1024;
export const W2_APPARATUS_CAP = 512 * 1024;
export const W2_LIMITS = Object.freeze({ max_elements: 16, max_interactions: 32, max_branches: 63,
  max_records: 256, max_hits: 128, max_segments: 256, trace_radius_m: 1, max_distance_m: 10 });
export type RoutingVector = readonly [number, number, number];
export type RoutingUV = readonly [number, number];
export type RoutingKind = 'mirror' | 'ideal_splitter_50_50' | 'beam_stop' | 'receiver';
export type RoutingCategory = 'detected' | 'absorbed' | 'escaped' | 'resource_truncated';
export interface RoutingElement {
  readonly id: string; readonly kind: RoutingKind;
  readonly pose: Readonly<{ position_m: RoutingVector; rotation_xyz_rad: RoutingVector }>;
  readonly aperture: Readonly<{ kind: 'disk'; radius_m: number } | { kind: 'rectangle'; width_m: number; height_m: number }>;
}
export interface GeometricScene {
  readonly schema_version: 1; readonly model_contract: typeof W2_MODEL;
  readonly source: Readonly<{ id: 'source'; origin_m: RoutingVector; direction: RoutingVector; relative_weight: 1 }>;
  readonly elements: readonly RoutingElement[];
}
export interface RoutingSurfaceFrame { readonly element_id: string; readonly u: RoutingVector; readonly v: RoutingVector; readonly n: RoutingVector }
export interface GeometricValidationRequest { readonly request_id: string; readonly scene: GeometricScene }
export interface GeometricTraceRequest extends GeometricValidationRequest { readonly scene_sha256: string }
export interface GeometricValidationReply extends GeometricValidationRequest {
  readonly protocol_version: 1; readonly message_type: 'scene_validation'; readonly model_contract: typeof W2_MODEL;
  readonly scene_sha256: string; readonly surface_frames: readonly RoutingSurfaceFrame[];
}
export interface RoutingBranch {
  readonly id: string; readonly parent_id: string | null; readonly parent_hit_id: string | null;
  readonly origin_m: RoutingVector; readonly initial_direction: RoutingVector; readonly relative_weight: number;
  readonly start_cumulative_m: number; readonly start_interaction_count: number; readonly outcome: RoutingCategory | 'split';
}
export interface RoutingSegment {
  readonly id: string; readonly branch_id: string; readonly start_m: RoutingVector; readonly end_m: RoutingVector;
  readonly direction: RoutingVector; readonly relative_weight: number; readonly length_m: number;
  readonly cumulative_end_m: number; readonly hit_id: string | null;
}
export interface RoutingOutgoing { readonly branch_id: string; readonly direction: RoutingVector; readonly relative_weight: number }
export interface RoutingHit {
  readonly id: string; readonly segment_id: string; readonly branch_id: string; readonly element_id: string;
  readonly position_m: RoutingVector; readonly local_uv_m: RoutingUV; readonly incident_direction: RoutingVector;
  readonly incoming_weight: number; readonly outgoing: readonly RoutingOutgoing[];
  readonly segment_length_m: number; readonly cumulative_length_m: number;
  readonly numerical_bounds: Readonly<{ t_parameter_interval_m: RoutingUV; position_intervals_m: readonly RoutingUV[];
    local_uv_intervals_m: readonly RoutingUV[]; plane_residual_m: number }>;
}
export interface RoutingTerminal {
  readonly branch_id: string; readonly category: RoutingCategory; readonly element_id: string | null; readonly hit_id: string | null;
  readonly position_m: RoutingVector; readonly cumulative_length_m: number; readonly relative_weight: number;
  readonly reason: 'receiver_hit' | 'stop_hit' | 'domain_exit' | 'interaction_cap' | 'distance_cap' | 'branch_cap' | 'record_cap';
}
export interface GeometricTraceResult extends GeometricTraceRequest {
  readonly protocol_version: 1; readonly message_type: 'trace_result'; readonly model_contract: typeof W2_MODEL;
  readonly surface_frames: readonly RoutingSurfaceFrame[]; readonly limits: typeof W2_LIMITS;
  readonly status: 'complete' | 'incomplete'; readonly branches: readonly RoutingBranch[];
  readonly segments: readonly RoutingSegment[]; readonly hits: readonly RoutingHit[]; readonly terminals: readonly RoutingTerminal[];
  readonly ledger: Readonly<{ input_weight: number; detected_weight: number; absorbed_weight: number; escaped_weight: number;
    truncated_weight: number; signed_residual: number }>;
  readonly diagnostics: Readonly<{ predicate_policy: 'binary64_outward_intervals_v1'; max_direction_norm_residual: number;
    max_frame_orthogonality_residual: number; max_plane_residual_m: number; max_point_error_bound_m: number }>;
}
export interface GeometricRoutingAPI {
  validate(request: GeometricValidationRequest): Promise<unknown>;
  trace(request: GeometricTraceRequest): Promise<ArrayBuffer>;
}
export interface RoutingResourceBreakdown {
  readonly wireBytes: number; readonly scalarBytes: number; readonly stringBytes: number;
  readonly containerReservationBytes: number; readonly retainedBytes: number;
  readonly retainedRawBytes: 0; readonly retainedResponseTextBytes: 0;
}
const resourceCharges = new WeakMap<GeometricTraceResult, RoutingResourceBreakdown>();
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const SHA = /^[0-9a-f]{64}$/;
const ELEMENT_ID = /^[A-Za-z][A-Za-z0-9_-]{0,63}$/;
const BRANCH_ID = /^r0(?:\.[TR]){0,31}$/;
const categories: readonly string[] = ['detected', 'absorbed', 'escaped', 'resource_truncated'];
const epsilon = Number.EPSILON;
function fail(text: string): never { throw new Error(`W2 protocol: ${text}`); }
function object(value: unknown, name: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(`${name}: expected object`);
  return value as Record<string, unknown>;
}
function keys(value: Record<string, unknown>, expected: readonly string[], name: string): void {
  const actual = Object.keys(value);
  if (actual.length !== expected.length || actual.some(key => !expected.includes(key))) fail(`${name}: incorrect closed keys`);
}
function finite(value: unknown, name: string, minimum = -Infinity, maximum = Infinity): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < minimum || value > maximum) fail(`${name}: finite number outside supported range`);
  return value as number;
}
function integer(value: unknown, name: string, maximum: number): number {
  const number = finite(value, name, 0, maximum); if (!Number.isSafeInteger(number)) fail(`${name}: expected integer`); return number;
}
function text(value: unknown, name: string, pattern: RegExp): string {
  if (typeof value !== 'string' || !pattern.test(value)) fail(`${name}: invalid identity`); return value as string;
}
function vector(value: unknown, name: string, size = 3): readonly number[] {
  if (!Array.isArray(value) || value.length !== size) fail(`${name}: expected ${size}-vector`);
  return (value as unknown[]).map((number, index) => finite(number, `${name}[${index}]`));
}
function unit(value: unknown, name: string, tolerance = 128 * epsilon): void {
  const v = vector(value, name); if (Math.abs(Math.hypot(...v) - 1) > tolerance) fail(`${name}: nonunit direction`);
}
function near(a: number, b: number): boolean { return Math.abs(a - b) <= 2e-13 * Math.max(1, Math.abs(a), Math.abs(b)); }
function sameVector(a: readonly number[], b: readonly number[]): boolean { return a.length === b.length && a.every((n, k) => n === b[k]); }
/** W2 preserves signed zero in stored source/pose records as well as their values. */
export function routingStructuralEqual(a: unknown, b: unknown): boolean {
  if (Object.is(a, b)) return true;
  if (!a || !b || typeof a !== 'object' || typeof b !== 'object' || Array.isArray(a) !== Array.isArray(b)) return false;
  const keysA = Object.keys(a), keysB = Object.keys(b);
  return keysA.length === keysB.length && keysA.every(key => Object.hasOwn(b, key) && routingStructuralEqual((a as Record<string, unknown>)[key], (b as Record<string, unknown>)[key]));
}
function assertSame(a: unknown, b: unknown, name: string): void { if (!routingStructuralEqual(a, b)) fail(`${name}: identity mismatch`); }
function interval(value: unknown, actual: number, name: string): void {
  const bound = vector(value, name, 2); if (bound[0] > actual || bound[1] < actual || bound[0] > bound[1]) fail(`${name}: interval does not enclose value`);
}
function freeze<T>(value: T): T {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
}
/** Schema/admission checks only. Authoritative finite predicates remain on the backend. */
export function assertGeometricScene(value: unknown): asserts value is GeometricScene {
  const scene = object(value, 'scene'); keys(scene, ['schema_version', 'model_contract', 'source', 'elements'], 'scene');
  if (scene.schema_version !== 1 || scene.model_contract !== W2_MODEL) fail('scene version/model');
  const source = object(scene.source, 'source'); keys(source, ['id', 'origin_m', 'direction', 'relative_weight'], 'source');
  if (source.id !== 'source' || source.relative_weight !== 1) fail('single source identity/weight');
  vector(source.origin_m, 'source origin').forEach(n => finite(n, 'source coordinate', -10, 10)); unit(source.direction, 'source direction', 32 * epsilon);
  if (!Array.isArray(scene.elements) || scene.elements.length > W2_LIMITS.max_elements) fail('element count');
  const ids = new Set(['source']);
  scene.elements.forEach((item, index) => {
    const element = object(item, `element ${index}`); keys(element, ['id', 'kind', 'pose', 'aperture'], 'element');
    const id = text(element.id, 'element ID', ELEMENT_ID); if (ids.has(id)) fail('duplicate/reserved element ID'); ids.add(id);
    if (!['mirror', 'ideal_splitter_50_50', 'beam_stop', 'receiver'].includes(String(element.kind))) fail('unsupported optical element');
    const pose = object(element.pose, 'pose'); keys(pose, ['position_m', 'rotation_xyz_rad'], 'pose'); vector(pose.position_m, 'position');
    vector(pose.rotation_xyz_rad, 'rotation').forEach(n => finite(n, 'stored rotation / rad', -Math.PI, Math.PI));
    const aperture = object(element.aperture, 'aperture');
    if (aperture.kind === 'disk') { keys(aperture, ['kind', 'radius_m'], 'disk'); finite(aperture.radius_m, 'radius / m', 1e-6, .25); }
    else if (aperture.kind === 'rectangle') { keys(aperture, ['kind', 'width_m', 'height_m'], 'rectangle'); finite(aperture.width_m, 'width / m', 1e-6, .25); finite(aperture.height_m, 'height / m', 1e-6, .25); }
    else fail('unsupported finite aperture');
  });
}
export function freezeGeometricScene(scene: GeometricScene): GeometricScene { assertGeometricScene(scene); return freeze(structuredClone(scene)); }
/** Draft edits may be numerically invalid; retaining their owned values does not validate them. */
export function freezeRoutingDraft(scene: GeometricScene): GeometricScene { return freeze(structuredClone(scene)); }
function validateFrames(value: unknown, scene: GeometricScene): void {
  if (!Array.isArray(value) || value.length !== scene.elements.length) fail('complete surface frames');
  const expected = new Set(scene.elements.map(element => element.id)), seen = new Set<string>();
  for (const item of value) {
    const frame = object(item, 'surface frame'); keys(frame, ['element_id', 'u', 'v', 'n'], 'surface frame');
    const id = text(frame.element_id, 'frame element', ELEMENT_ID); if (!expected.has(id) || seen.has(id)) fail('frame element relationships'); seen.add(id);
    for (const axis of ['u', 'v', 'n']) unit(frame[axis], `frame ${axis}`, 64 * epsilon);
    const u = frame.u as number[], v = frame.v as number[], n = frame.n as number[];
    const dot = (a: number[], b: number[]) => a.reduce((sum, number, k) => sum + number * b[k], 0);
    if ([dot(u, v), dot(u, n), dot(v, n)].some(number => Math.abs(number) > 64 * epsilon)) fail('nonorthogonal returned frame');
    const cross = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
    if (cross.some((number, k) => Math.abs(number - n[k]) > 64 * epsilon)) fail('returned frame handedness');
  }
}
export function validateGeometricValidation(value: unknown, submitted: GeometricValidationRequest): GeometricValidationReply {
  const reply = object(value, 'validation reply'); keys(reply, ['protocol_version', 'message_type', 'request_id', 'model_contract', 'scene_sha256', 'scene', 'surface_frames'], 'validation reply');
  text(submitted.request_id, 'submitted request', UUID);
  if (reply.protocol_version !== 1 || reply.message_type !== 'scene_validation' || reply.model_contract !== W2_MODEL || reply.request_id !== submitted.request_id) fail('validation identity');
  text(reply.scene_sha256, 'scene SHA256', SHA); assertGeometricScene(reply.scene); assertSame(reply.scene, submitted.scene, 'validation scene echo');
  validateFrames(reply.surface_frames, reply.scene); return freeze(reply) as unknown as GeometricValidationReply;
}
/** Strict JSON retains the existing duplicate-key parser and adds nonzero-token underflow rejection. */
export function parseRoutingJSON(textValue: string): unknown {
  let inside = false;
  for (let cursor = 0; cursor < textValue.length; cursor++) {
    const c = textValue[cursor]; if (inside) { if (c === '\\') cursor++; else if (c === '"') inside = false; continue; }
    if (c === '"') { inside = true; continue; }
    if (c === '-' || c >= '0' && c <= '9') {
      const token = /^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(textValue.slice(cursor));
      if (token) { if (Number(token[0]) === 0 && /[1-9]/.test(token[0].split(/[eE]/, 1)[0])) fail('nonzero numeric token underflow'); cursor += token[0].length - 1; }
    }
  }
  return parseStrictJSON(textValue);
}
function decodeJSON(frame: ArrayBuffer, cap: number): unknown {
  if (!(frame instanceof ArrayBuffer) || frame.byteLength < 2 || frame.byteLength > cap) fail('response byte cap/length');
  let content: string; try { content = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(frame); } catch { return fail('invalid UTF-8'); }
  return parseRoutingJSON(content);
}
/** Full graph validation is metadata verification, never a second optical intersection solver. */
export function decodeGeometricTrace(frame: ArrayBuffer, submitted: GeometricTraceRequest, expectedFrames?: readonly RoutingSurfaceFrame[]): GeometricTraceResult {
  const raw = object(decodeJSON(frame, W2_RESPONSE_CAP), 'trace reply');
  keys(raw, ['protocol_version', 'message_type', 'request_id', 'model_contract', 'scene_sha256', 'scene', 'surface_frames', 'limits', 'status', 'branches', 'segments', 'hits', 'terminals', 'ledger', 'diagnostics'], 'trace reply');
  text(submitted.request_id, 'submitted request', UUID); text(submitted.scene_sha256, 'submitted digest', SHA); assertGeometricScene(submitted.scene);
  if (raw.protocol_version !== 1 || raw.message_type !== 'trace_result' || raw.model_contract !== W2_MODEL || raw.request_id !== submitted.request_id || raw.scene_sha256 !== submitted.scene_sha256) fail('trace identity');
  assertGeometricScene(raw.scene); assertSame(raw.scene, submitted.scene, 'submitted scene echo'); validateFrames(raw.surface_frames, raw.scene);
  if (expectedFrames) assertSame(raw.surface_frames, expectedFrames, 'validated authoritative frames');
  assertSame(raw.limits, W2_LIMITS, 'fixed limits'); if (raw.status !== 'complete' && raw.status !== 'incomplete') fail('trace status');
  for (const [name, maximum] of [['branches', 63], ['segments', 256], ['hits', 128], ['terminals', 63]] as const) {
    if (!Array.isArray(raw[name]) || (raw[name] as unknown[]).length > maximum) fail(`${name}: record count`);
  }
  if ((raw.segments as unknown[]).length + (raw.hits as unknown[]).length > 256 || !(raw.branches as unknown[]).length) fail('combined records/root');
  const result = raw as unknown as GeometricTraceResult;
  const elements = new Map(result.scene.elements.map(element => [element.id, element]));
  const branches = new Map<string, RoutingBranch>(), segments = new Map<string, RoutingSegment>(), hits = new Map<string, RoutingHit>(), terminals = new Map<string, RoutingTerminal>();
  for (const branch of result.branches) {
    keys(object(branch, 'branch'), ['id', 'parent_id', 'parent_hit_id', 'origin_m', 'initial_direction', 'relative_weight', 'start_cumulative_m', 'start_interaction_count', 'outcome'], 'branch');
    text(branch.id, 'branch ID', BRANCH_ID); if (branches.has(branch.id)) fail('duplicate branch');
    vector(branch.origin_m, 'branch origin'); unit(branch.initial_direction, 'branch initial direction'); finite(branch.relative_weight, 'branch weight', Number.MIN_VALUE, 1);
    finite(branch.start_cumulative_m, 'branch start distance', 0, 10); integer(branch.start_interaction_count, 'inherited interaction count', 32);
    if (![...categories, 'split'].includes(branch.outcome)) fail('branch outcome');
    if (branch.id === 'r0') {
      if (branches.size || branch.parent_id !== null || branch.parent_hit_id !== null || branch.relative_weight !== 1 || branch.start_cumulative_m !== 0 || branch.start_interaction_count !== 0) fail('root branch identity');
      assertSame(branch.origin_m, submitted.scene.source.origin_m, 'root origin'); assertSame(branch.initial_direction, submitted.scene.source.direction, 'root direction');
    } else {
      text(branch.parent_id, 'branch parent', BRANCH_ID); text(branch.parent_hit_id, 'branch parent hit', /^h\d{4}$/);
      if (!branches.has(branch.parent_id!) || ![`${branch.parent_id}.T`, `${branch.parent_id}.R`].includes(branch.id)) fail('branch parent/order/child identity');
    }
    branches.set(branch.id, branch);
  }
  for (const [ordinal, segment] of result.segments.entries()) {
    keys(object(segment, 'segment'), ['id', 'branch_id', 'start_m', 'end_m', 'direction', 'relative_weight', 'length_m', 'cumulative_end_m', 'hit_id'], 'segment');
    text(segment.id, 'segment ID', /^s\d{4}$/); if (segment.id !== `s${String(ordinal).padStart(4, '0')}` || segments.has(segment.id) || !branches.has(segment.branch_id)) fail('duplicate/foreign/unstable segment');
    vector(segment.start_m, 'segment start'); vector(segment.end_m, 'segment end'); unit(segment.direction, 'segment direction');
    finite(segment.relative_weight, 'segment weight', Number.MIN_VALUE, 1); finite(segment.length_m, 'segment length', Number.MIN_VALUE, 10); finite(segment.cumulative_end_m, 'cumulative distance', 0, 10 + 2e-12);
    if (!near(Math.hypot(...segment.end_m.map((n, k) => n - segment.start_m[k])), segment.length_m)) fail('geometric segment length');
    if (segment.hit_id !== null) text(segment.hit_id, 'segment hit', /^h\d{4}$/); segments.set(segment.id, segment);
  }
  for (const [ordinal, hit] of result.hits.entries()) {
    keys(object(hit, 'hit'), ['id', 'segment_id', 'branch_id', 'element_id', 'position_m', 'local_uv_m', 'incident_direction', 'incoming_weight', 'outgoing', 'segment_length_m', 'cumulative_length_m', 'numerical_bounds'], 'hit');
    text(hit.id, 'hit ID', /^h\d{4}$/); if (hit.id !== `h${String(ordinal).padStart(4, '0')}` || hits.has(hit.id) || !elements.has(hit.element_id) || !branches.has(hit.branch_id)) fail('duplicate/foreign/unstable hit');
    const segment = segments.get(hit.segment_id); if (!segment || segment.hit_id !== hit.id || segment.branch_id !== hit.branch_id) fail('hit/segment relationship');
    vector(hit.position_m, 'hit position'); vector(hit.local_uv_m, 'local UV', 2); unit(hit.incident_direction, 'incident direction');
    assertSame(hit.position_m, segment.end_m, 'hit endpoint'); assertSame(hit.incident_direction, segment.direction, 'hit incident direction');
    if (hit.incoming_weight !== segment.relative_weight || hit.segment_length_m !== segment.length_m || hit.cumulative_length_m !== segment.cumulative_end_m) fail('hit/segment scalar relationship');
    const bound = object(hit.numerical_bounds, 'numerical bounds'); keys(bound, ['t_parameter_interval_m', 'position_intervals_m', 'local_uv_intervals_m', 'plane_residual_m'], 'numerical bounds');
    const parameter = vector(bound.t_parameter_interval_m, 't interval', 2); if (parameter[0] > parameter[1] || parameter[0] <= 0) fail('forward t interval');
    for (const [name, coordinate, size] of [['position_intervals_m', hit.position_m, 3], ['local_uv_intervals_m', hit.local_uv_m, 2]] as const) {
      const values = bound[name]; if (!Array.isArray(values) || values.length !== size) fail('interval shape'); coordinate.forEach((n, k) => interval((values as unknown[])[k], n, name));
    }
    finite(bound.plane_residual_m, 'signed plane residual'); if (!Array.isArray(hit.outgoing) || hit.outgoing.length > 2) fail('outgoing cardinality');
    for (const outgoing of hit.outgoing) { keys(object(outgoing, 'outgoing'), ['branch_id', 'direction', 'relative_weight'], 'outgoing'); unit(outgoing.direction, 'outgoing direction'); finite(outgoing.relative_weight, 'outgoing weight', Number.MIN_VALUE, 1); if (!branches.has(outgoing.branch_id)) fail('outgoing unknown branch'); }
    const kind = elements.get(hit.element_id)!.kind;
    if (kind === 'mirror' && (hit.outgoing.length !== 1 || hit.outgoing[0].branch_id !== hit.branch_id || hit.outgoing[0].relative_weight !== hit.incoming_weight)) fail('mirror must preserve same branch and weight');
    if (kind === 'ideal_splitter_50_50' && hit.outgoing.length !== 0) {
      if (hit.outgoing.length !== 2 || hit.outgoing[0].branch_id !== `${hit.branch_id}.T` || hit.outgoing[1].branch_id !== `${hit.branch_id}.R`
        || hit.outgoing.some(outgoing => outgoing.relative_weight !== hit.incoming_weight / 2) || !sameVector(hit.outgoing[0].direction, hit.incident_direction)) fail('atomic T/R half split');
    }
    if ((kind === 'receiver' || kind === 'beam_stop') && hit.outgoing.length) fail('terminating face has outgoing path'); hits.set(hit.id, hit);
  }
  for (const segment of segments.values()) if (segment.hit_id !== null && !hits.has(segment.hit_id)) fail('missing segment hit');
  const breadthFirst = ['r0'];
  for (let cursor = 0; cursor < breadthFirst.length; cursor++) {
    const branch = branches.get(breadthFirst[cursor]); if (!branch) fail('missing BFS branch');
    if (branch.outcome === 'split') breadthFirst.push(`${branch.id}.T`, `${branch.id}.R`);
    if (breadthFirst.length > 63) fail('branch graph allocation cap');
  }
  assertSame(result.branches.map(branch => branch.id), breadthFirst, 'BFS T-before-R branch order');
  for (const terminal of result.terminals) {
    keys(object(terminal, 'terminal'), ['branch_id', 'category', 'element_id', 'hit_id', 'position_m', 'cumulative_length_m', 'relative_weight', 'reason'], 'terminal');
    const branch = branches.get(terminal.branch_id); if (!branch || terminals.has(terminal.branch_id) || !categories.includes(terminal.category) || branch.outcome !== terminal.category || terminal.relative_weight !== branch.relative_weight) fail('terminal branch/weight/outcome');
    vector(terminal.position_m, 'terminal position'); finite(terminal.cumulative_length_m, 'terminal distance', 0, 10 + 2e-12);
    if (terminal.hit_id !== null) {
      const hit = hits.get(terminal.hit_id), birthHit = terminal.category === 'resource_truncated' && terminal.hit_id === branch.parent_hit_id
        && !result.segments.some(segment => segment.branch_id === branch.id);
      if (!hit || !birthHit && hit.branch_id !== terminal.branch_id || hit.element_id !== terminal.element_id
        || !sameVector(terminal.position_m, hit.position_m) || terminal.cumulative_length_m !== hit.cumulative_length_m) fail('terminal hit identity');
    }
    else if (terminal.element_id !== null) fail('terminal element without actual hit');
    if (terminal.category === 'detected' || terminal.category === 'absorbed') {
      const kind = terminal.category === 'detected' ? 'receiver' : 'beam_stop', reason = terminal.category === 'detected' ? 'receiver_hit' : 'stop_hit';
      if (!terminal.hit_id || elements.get(terminal.element_id!)?.kind !== kind || terminal.reason !== reason) fail('fabricated detection/absorption');
    } else if (terminal.category === 'escaped') { if (terminal.hit_id !== null || terminal.element_id !== null || terminal.reason !== 'domain_exit') fail('fake escape hit'); }
    else if (!['interaction_cap', 'distance_cap', 'branch_cap', 'record_cap'].includes(terminal.reason)) fail('resource reason');
    const radius = Math.hypot(...terminal.position_m.map((n, k) => n - submitted.scene.source.origin_m[k]));
    if (radius > 1 + 2e-12 || terminal.category === 'escaped' && !near(radius, 1)) fail('terminal trace-domain bound');
    terminals.set(terminal.branch_id, terminal);
  }
  for (const branch of branches.values()) {
    const path = result.segments.filter(segment => segment.branch_id === branch.id);
    let point = branch.origin_m, direction = branch.initial_direction, cumulative = branch.start_cumulative_m, count = branch.start_interaction_count;
    for (const [index, segment] of path.entries()) {
      if (!sameVector(point, segment.start_m) || !sameVector(direction, segment.direction) || segment.relative_weight !== branch.relative_weight || !near(cumulative + segment.length_m, segment.cumulative_end_m)) fail('branch segment continuity/weight/distance');
      point = segment.end_m; cumulative = segment.cumulative_end_m;
      if (segment.hit_id !== null) {
        const hit = hits.get(segment.hit_id)!; ++count;
        if (count > 32) fail('inherited interaction cap');
        const kind = elements.get(hit.element_id)!.kind;
        if (kind === 'mirror') direction = hit.outgoing[0].direction;
        else if (index !== path.length - 1) fail('path continues after terminating/split face');
      } else if (index !== path.length - 1) fail('path continues after bounded endpoint');
    }
    if (branch.id !== 'r0') {
      const parent = branches.get(branch.parent_id!)!, hit = hits.get(branch.parent_hit_id!);
      if (!hit || hit.branch_id !== parent.id || parent.outcome !== 'split' || elements.get(hit.element_id)?.kind !== 'ideal_splitter_50_50') fail('child parent split');
      const outgoing = hit.outgoing.find(entry => entry.branch_id === branch.id); if (!outgoing || outgoing.relative_weight !== branch.relative_weight || !sameVector(outgoing.direction, branch.initial_direction)
        || !sameVector(hit.position_m, branch.origin_m) || hit.cumulative_length_m !== branch.start_cumulative_m) fail('child state inheritance');
      const inherited = parent.start_interaction_count + result.hits.filter(entry => entry.branch_id === parent.id).length;
      if (branch.start_interaction_count !== inherited) fail('inherited interaction reset');
    }
    const terminal = terminals.get(branch.id), lastHit = path.at(-1)?.hit_id ? hits.get(path.at(-1)!.hit_id!) : undefined;
    if (branch.outcome === 'split') {
      if (terminal || !lastHit || lastHit.outgoing.length !== 2 || !branches.has(`${branch.id}.T`) || !branches.has(`${branch.id}.R`)) fail('unpaired split/terminal parent');
    } else {
      if (!terminal || !sameVector(terminal.position_m, point) || !near(terminal.cumulative_length_m, cumulative)) fail('terminal final state');
      if ((terminal.category === 'detected' || terminal.category === 'absorbed') && terminal.hit_id !== lastHit?.id) fail('terminal is not actual final hit');
      if (terminal.category === 'escaped' && (!path.length || path.at(-1)!.hit_id !== null)) fail('escape requires an actual domain endpoint');
      if (terminal.reason === 'interaction_cap' && count !== 32) fail('interaction cap before inherited limit');
      if (terminal.reason === 'distance_cap' && !near(cumulative, 10)) fail('distance cap before distance limit');
      if (lastHit && elements.get(lastHit.element_id)?.kind === 'ideal_splitter_50_50' && lastHit.outgoing.length === 0 && terminal.category !== 'resource_truncated') fail('lost split allocation');
    }
  }
  const ledger = object(result.ledger, 'ledger'); keys(ledger, ['input_weight', 'detected_weight', 'absorbed_weight', 'escaped_weight', 'truncated_weight', 'signed_residual'], 'ledger');
  const sums = categories.map(category => result.terminals.filter(terminal => terminal.category === category).reduce((sum, terminal) => sum + terminal.relative_weight, 0));
  if (ledger.input_weight !== 1) fail('input ledger weight');
  for (const [index, key] of ['detected_weight', 'absorbed_weight', 'escaped_weight', 'truncated_weight'].entries()) if (finite(ledger[key], key, 0, 1) !== sums[index]) fail('terminal ledger mismatch');
  const residual = 1 - sums.reduce((a, b) => a + b, 0);
  if (finite(ledger.signed_residual, 'signed residual') !== residual || Math.abs(residual) > 64 * epsilon) fail('lost/doubled terminal weight');
  if ((result.status === 'incomplete') !== result.terminals.some(terminal => terminal.category === 'resource_truncated')) fail('hidden resource truncation');
  const diagnostic = object(result.diagnostics, 'diagnostics'); keys(diagnostic, ['predicate_policy', 'max_direction_norm_residual', 'max_frame_orthogonality_residual', 'max_plane_residual_m', 'max_point_error_bound_m'], 'diagnostics');
  if (diagnostic.predicate_policy !== 'binary64_outward_intervals_v1') fail('predicate policy');
  for (const key of Object.keys(diagnostic).filter(key => key !== 'predicate_policy')) finite(diagnostic[key], key, 0);
  finite(diagnostic.max_direction_norm_residual, 'direction residual', 0, 128 * epsilon); finite(diagnostic.max_frame_orthogonality_residual, 'frame residual', 0, 64 * epsilon);
  freeze(result); resourceCharges.set(result, chargeStructure(result, frame.byteLength)); return result;
}
/** Explicit app-owned record reservation, not a claim about engine heap or native/GPU memory. */
function chargeStructure(value: unknown, wireBytes: number, exclude: readonly unknown[] = []): RoutingResourceBreakdown {
  let scalarBytes = 0, stringBytes = 0, containerReservationBytes = 4096;
  const seen = new Set<object>();
  const ignore = (item: unknown): void => { if (item && typeof item === 'object' && !seen.has(item)) { seen.add(item); Object.values(item).forEach(ignore); } };
  exclude.forEach(ignore);
  const visit = (item: unknown): void => {
    if (typeof item === 'number') scalarBytes += 8;
    else if (typeof item === 'string') stringBytes += item.length * 2;
    else if (typeof item === 'boolean' || item === null) scalarBytes += 8;
    else if (Array.isArray(item)) { if (seen.has(item)) return; seen.add(item); containerReservationBytes += 64 + item.length * 16; item.forEach(visit); }
    else if (item && typeof item === 'object') { if (seen.has(item)) return; seen.add(item); const entries = Object.entries(item); containerReservationBytes += 96 + entries.length * 24;
      entries.forEach(([key, child]) => { stringBytes += key.length * 2; visit(child); }); }
  }; visit(value);
  return Object.freeze({ wireBytes, scalarBytes, stringBytes, containerReservationBytes, retainedBytes: scalarBytes + stringBytes + containerReservationBytes,
    retainedRawBytes: 0, retainedResponseTextBytes: 0 });
}
export function routingResourceBreakdown(result: GeometricTraceResult): RoutingResourceBreakdown { return resourceCharges.get(result) ?? chargeStructure(result, 0); }
/** Owned numerical draft/frame/request/record metadata, with identity de-duplication. Not total heap. */
export function routingMetadataReservation(value: unknown, exclude: readonly unknown[] = []): number { return chargeStructure(value, 0, exclude).retainedBytes; }
export function routingOwnedResults(results: readonly (GeometricTraceResult | null)[]): number { return [...new Set(results.filter((result): result is GeometricTraceResult => !!result))].reduce((sum, result) => sum + routingResourceBreakdown(result).retainedBytes, 0); }
export function estimateGeometricRoutingOperation() {
  return Object.freeze({ persistentBytes: W2_RETAINED_RESERVATION, transientBytes: W2_TRANSIENT_RESERVATION,
    requestBytes: W2_REQUEST_CAP, responseBytes: W2_RESPONSE_CAP, includes: 'Incoming raw chunks/join, UTF-16 parse text, immutable record reservation, geometry/labels and preparation overlap; actual shared admission still required.' });
}
export function createGeometricRoutingFetchAPI(fetchImpl: typeof fetch = globalThis.fetch.bind(globalThis)): GeometricRoutingAPI {
  const post = async (endpoint: 'validate' | 'trace', request: GeometricValidationRequest | GeometricTraceRequest): Promise<ArrayBuffer> => {
    text(request.request_id, 'request UUID', UUID); const body = stringifyRoutingJSON(request);
    if (new TextEncoder().encode(body).byteLength > W2_REQUEST_CAP) fail('request body cap');
    const response = await fetchImpl(`/api/w2/${endpoint}`, { method: 'POST', credentials: 'same-origin', redirect: 'error', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body });
    const mime = response.headers.get('content-type')?.split(';', 1)[0].trim();
    if (!response.ok) {
      const bytes = await readBoundedResponse(response, W2_REQUEST_CAP); let message = `HTTP ${response.status}`;
      try { const error = object(decodeJSON(bytes, W2_REQUEST_CAP), 'error'); keys(error, ['protocol_version', 'message_type', 'request_id', 'model_contract', 'error'], 'error');
        if (error.protocol_version !== 1 || error.message_type !== 'routing_error' || error.model_contract !== W2_MODEL || error.request_id !== request.request_id) fail('error identity');
        const detail = object(error.error, 'error detail'); keys(detail, ['code', 'message'], 'error detail');
        if (typeof detail.message === 'string' && detail.message.length <= 300) message += `: ${detail.message}`;
      } catch { /* Preserve actual HTTP status when an error body is invalid. */ }
      throw new Error(message);
    }
    if (mime !== 'application/json') { await response.body?.cancel('W2 rejected content type'); fail('HTTP content type'); }
    return readBoundedResponse(response, W2_RESPONSE_CAP);
  };
  return { async validate(request) { return decodeJSON(await post('validate', request), W2_RESPONSE_CAP); }, trace(request) { return post('trace', request); } };
}
/** Closed DTO writer keeps -0 rather than JSON.stringify's silent conversion to +0. */
export function stringifyRoutingJSON(value: unknown): string {
  const encode = (item: unknown, depth: number): string => {
    if (depth > 12) fail('request JSON nesting');
    if (item === null) return 'null';
    if (typeof item === 'number') { finite(item, 'request JSON number'); return Object.is(item, -0) ? '-0.0' : String(item); }
    if (typeof item === 'string' || typeof item === 'boolean') return JSON.stringify(item);
    if (Array.isArray(item)) return `[${item.map(child => encode(child, depth + 1)).join(',')}]`;
    if (item && typeof item === 'object') return `{${Object.entries(item).map(([key, child]) => `${JSON.stringify(key)}:${encode(child, depth + 1)}`).join(',')}}`;
    return fail('unsupported request JSON value');
  }; return encode(value, 0);
}
const element = (id: string, kind: RoutingKind, position: RoutingVector, y: number): RoutingElement => ({ id, kind, pose: { position_m: position, rotation_xyz_rad: [0, y, 0] }, aperture: { kind: 'disk', radius_m: .025 } });
const scene = (elements: readonly RoutingElement[]): GeometricScene => freezeGeometricScene({ schema_version: 1, model_contract: W2_MODEL,
  source: { id: 'source', origin_m: [0, .08, 0], direction: [0, 0, 1], relative_weight: 1 }, elements });
export const W2_PRESETS = Object.freeze({
  A: scene([element('M1', 'mirror', [0, .08, .2], -Math.PI / 4), element('D1', 'receiver', [.2, .08, .2], -Math.PI / 2)]),
  B: scene([element('M1', 'mirror', [0, .08, .2], -Math.PI / 4), element('M2', 'mirror', [.2, .08, .2], 3 * Math.PI / 4), element('D1', 'receiver', [.2, .08, .4], Math.PI)]),
  C: scene([element('S1', 'ideal_splitter_50_50', [0, .08, .2], -Math.PI / 4), element('DT', 'receiver', [0, .08, .4], Math.PI),
    element('DR', 'receiver', [.2, .08, .2], -Math.PI / 2), element('STOP1', 'beam_stop', [.1, .08, .2], -Math.PI / 2)]),
});
