import { describe, expect, it, vi } from 'vitest';
import { W2_LIMITS, W2_MODEL, W2_PRESETS, W2_RESPONSE_CAP, assertGeometricScene, createGeometricRoutingFetchAPI,
  decodeGeometricTrace, freezeGeometricScene, parseRoutingJSON, routingOwnedResults, routingResourceBreakdown,
  stringifyRoutingJSON, routingStructuralEqual, validateGeometricValidation, type GeometricScene, type GeometricTraceRequest } from '../src/geometric_routing_contracts';

const id = '11111111-1111-4111-8111-111111111111', digest = 'a'.repeat(64);
function fixture() {
  // Independently specified direct hit, not a production tracer or optical reference helper.
  const scene: GeometricScene = { schema_version: 1, model_contract: W2_MODEL, source: { id: 'source', origin_m: [0, .08, 0], direction: [0, 0, 1], relative_weight: 1 },
    elements: [{ id: 'D1', kind: 'receiver', pose: { position_m: [0, .08, .2], rotation_xyz_rad: [0, 0, 0] }, aperture: { kind: 'disk', radius_m: .025 } }] };
  const frames = [{ element_id: 'D1', u: [1, 0, 0], v: [0, 1, 0], n: [0, 0, 1] }];
  const request: GeometricTraceRequest = { request_id: id, scene_sha256: digest, scene };
  const result = { protocol_version: 1, message_type: 'trace_result', request_id: id, model_contract: W2_MODEL, scene_sha256: digest, scene, surface_frames: frames, limits: W2_LIMITS, status: 'complete',
    branches: [{ id: 'r0', parent_id: null, parent_hit_id: null, origin_m: [0, .08, 0], initial_direction: [0, 0, 1], relative_weight: 1, start_cumulative_m: 0, start_interaction_count: 0, outcome: 'detected' }],
    segments: [{ id: 's0000', branch_id: 'r0', start_m: [0, .08, 0], end_m: [0, .08, .2], direction: [0, 0, 1], relative_weight: 1, length_m: .2, cumulative_end_m: .2, hit_id: 'h0000' }],
    hits: [{ id: 'h0000', segment_id: 's0000', branch_id: 'r0', element_id: 'D1', position_m: [0, .08, .2], local_uv_m: [0, 0], incident_direction: [0, 0, 1], incoming_weight: 1,
      outgoing: [], segment_length_m: .2, cumulative_length_m: .2, numerical_bounds: { t_parameter_interval_m: [.1999999999999999, .2000000000000001], position_intervals_m: [[-1e-17, 1e-17], [.0799999999999999, .0800000000000001], [.1999999999999999, .2000000000000001]], local_uv_intervals_m: [[-1e-17, 1e-17], [-1e-17, 1e-17]], plane_residual_m: 0 } }],
    terminals: [{ branch_id: 'r0', category: 'detected', element_id: 'D1', hit_id: 'h0000', position_m: [0, .08, .2], cumulative_length_m: .2, relative_weight: 1, reason: 'receiver_hit' }],
    ledger: { input_weight: 1, detected_weight: 1, absorbed_weight: 0, escaped_weight: 0, truncated_weight: 0, signed_residual: 0 },
    diagnostics: { predicate_policy: 'binary64_outward_intervals_v1', max_direction_norm_residual: 0, max_frame_orthogonality_residual: 0, max_plane_residual_m: 0, max_point_error_bound_m: 1e-16 } };
  const validation = { protocol_version: 1, message_type: 'scene_validation', request_id: id, model_contract: W2_MODEL, scene_sha256: digest, scene, surface_frames: frames };
  return { request, result, validation };
}
const bytes = (value: unknown) => new TextEncoder().encode(JSON.stringify(value)).buffer;
function splitFixture() {
  const base = fixture(), q = Math.SQRT1_2;
  const scene = structuredClone(W2_PRESETS.C) as unknown as any; scene.elements = scene.elements.filter((element: any) => element.kind !== 'beam_stop');
  const result: any = structuredClone(base.result); result.scene = scene;
  result.surface_frames = [{ element_id: 'S1', u: [q, 0, q], v: [0, 1, 0], n: [-q, 0, q] }, { element_id: 'DT', u: [-1, 0, 0], v: [0, 1, 0], n: [0, 0, -1] }, { element_id: 'DR', u: [0, 0, 1], v: [0, 1, 0], n: [-1, 0, 0] }];
  result.branches[0].outcome = 'split';
  result.branches.push(...['T', 'R'].map((side, k) => ({ id: `r0.${side}`, parent_id: 'r0', parent_hit_id: 'h0000', origin_m: [0, .08, .2], initial_direction: k ? [1, 0, 0] : [0, 0, 1], relative_weight: .5, start_cumulative_m: .2, start_interaction_count: 1, outcome: 'detected' })));
  result.hits[0].element_id = 'S1'; result.hits[0].outgoing = [{ branch_id: 'r0.T', direction: [0, 0, 1], relative_weight: .5 }, { branch_id: 'r0.R', direction: [1, 0, 0], relative_weight: .5 }];
  for (const [k, side, elementId, endpoint, direction] of [[1, 'T', 'DT', [0, .08, .4], [0, 0, 1]], [2, 'R', 'DR', [.2, .08, .2], [1, 0, 0]]] as const) {
    result.segments.push({ id: `s000${k}`, branch_id: `r0.${side}`, start_m: [0, .08, .2], end_m: endpoint, direction, relative_weight: .5, length_m: .2, cumulative_end_m: .4, hit_id: `h000${k}` });
    const hit = structuredClone(base.result.hits[0]); Object.assign(hit, { id: `h000${k}`, segment_id: `s000${k}`, branch_id: `r0.${side}`, element_id: elementId, position_m: endpoint, incident_direction: direction, incoming_weight: .5, cumulative_length_m: .4 });
    hit.numerical_bounds.position_intervals_m = endpoint.map(number => [number - 1e-15, number + 1e-15]); result.hits.push(hit);
  }
  result.terminals = [1, 2].map((k, index) => ({ branch_id: `r0.${index ? 'R' : 'T'}`, category: 'detected', element_id: index ? 'DR' : 'DT', hit_id: `h000${k}`, position_m: result.hits[k].position_m, cumulative_length_m: .4, relative_weight: .5, reason: 'receiver_hit' }));
  return { request: { ...base.request, scene }, result };
}
function immediateChildCapFixture() {
  // Synthetic schema stress only: this tests inherited topology/birth-hit
  // ownership, not physically reachable mirror positions or reflection law.
  const f = splitFixture(), result: any = structuredClone(f.result);
  result.scene.elements = [{ id: 'M1', kind: 'mirror', pose: { position_m: [0, .08, .005], rotation_xyz_rad: [0, 0, 0] }, aperture: { kind: 'disk', radius_m: .025 } },
    { id: 'S1', kind: 'ideal_splitter_50_50', pose: { position_m: [0, .08, .16], rotation_xyz_rad: [0, 0, 0] }, aperture: { kind: 'disk', radius_m: .025 } }];
  result.surface_frames = ['M1', 'S1'].map(element_id => ({ element_id, u: [1, 0, 0], v: [0, 1, 0], n: [0, 0, 1] }));
  const outgoing = [{ branch_id: 'r0.T', direction: [0, 0, 1], relative_weight: .5 }, { branch_id: 'r0.R', direction: [0, 0, -1], relative_weight: .5 }];
  result.segments = []; result.hits = [];
  for (let k = 0; k < 32; k++) {
    const point = [0, .08, (k + 1) * .005], start = [0, .08, k * .005], length = point[2] - start[2], suffix = String(k).padStart(4, '0');
    result.segments.push({ id: `s${suffix}`, branch_id: 'r0', start_m: start, end_m: point, direction: [0, 0, 1], relative_weight: 1, length_m: length, cumulative_end_m: point[2], hit_id: `h${suffix}` });
    result.hits.push({ id: `h${suffix}`, segment_id: `s${suffix}`, branch_id: 'r0', element_id: k === 31 ? 'S1' : 'M1', position_m: point, local_uv_m: [0, 0], incident_direction: [0, 0, 1], incoming_weight: 1,
      outgoing: k === 31 ? outgoing : [{ branch_id: 'r0', direction: [0, 0, 1], relative_weight: 1 }], segment_length_m: length, cumulative_length_m: point[2],
      numerical_bounds: { t_parameter_interval_m: [length - 1e-16, length + 1e-16], position_intervals_m: point.map(n => [n - 1e-16, n + 1e-16]), local_uv_intervals_m: [[-1e-16, 1e-16], [-1e-16, 1e-16]], plane_residual_m: 0 } });
  }
  result.branches.slice(1).forEach((branch: any, k: number) => Object.assign(branch, { parent_hit_id: 'h0031', origin_m: [0, .08, .16], initial_direction: outgoing[k].direction, start_cumulative_m: .16, start_interaction_count: 32, outcome: 'resource_truncated' }));
  result.terminals = result.branches.slice(1).map((branch: any) => ({ branch_id: branch.id, category: 'resource_truncated', element_id: 'S1', hit_id: 'h0031', position_m: [0, .08, .16], cumulative_length_m: .16, relative_weight: .5, reason: 'interaction_cap' }));
  result.status = 'incomplete'; result.ledger = { input_weight: 1, detected_weight: 0, absorbed_weight: 0, escaped_weight: 0, truncated_weight: 1, signed_residual: 0 };
  return { request: { ...f.request, scene: result.scene }, result };
}
describe('W2 strict original response identity and graph ownership', () => {
  it('accepts the independently specified complete graph and owns every immutable record without retaining raw/text', () => {
    const f = fixture(), raw = bytes(f.result), result = decodeGeometricTrace(raw, f.request);
    expect(result.scene).toEqual(f.request.scene); expect(Object.isFrozen(result.hits[0].numerical_bounds.position_intervals_m)).toBe(true);
    const charge = routingResourceBreakdown(result); expect(charge.retainedRawBytes).toBe(0); expect(charge.retainedResponseTextBytes).toBe(0); expect(charge.wireBytes).toBe(raw.byteLength);
    expect(charge.retainedBytes).toBe(charge.scalarBytes + charge.stringBytes + charge.containerReservationBytes);
    expect(routingOwnedResults([result, result, null])).toBe(charge.retainedBytes); expect(routingOwnedResults([])).toBe(0);
    new Uint8Array(raw).fill(0); expect(result.hits[0].position_m[2]).toBe(.2);
  });
  it('requires validation and trace to echo UUID, opaque digest, complete scene and authoritative frame identity', () => {
    const f = fixture(); expect(validateGeometricValidation(f.validation, f.request).scene_sha256).toBe(digest);
    for (const mutate of [
      (x: any) => x.request_id = '22222222-2222-4222-8222-222222222222', (x: any) => x.scene_sha256 = 'b'.repeat(64),
      (x: any) => x.scene.source.origin_m[0] = .01, (x: any) => x.model_contract = 'old_mode', (x: any) => x.surface_frames[0].n = [0, 0, -1],
    ]) { const value = structuredClone(f.result); mutate(value); expect(() => decodeGeometricTrace(bytes(value), f.request), 'W2_RESPONSE_IDENTITY').toThrow(); }
    const incorrectFrames = structuredClone(f.result.surface_frames); incorrectFrames[0].u = [-1, 0, 0]; incorrectFrames[0].n = [0, 0, -1];
    expect(() => decodeGeometricTrace(bytes(f.result), f.request, incorrectFrames as any)).toThrow('authoritative frames');
  });
  it.each([
    ['foreign hit element', (r: any) => r.hits[0].element_id = 'invented'],
    ['missing actual hit', (r: any) => r.hits = []],
    ['fake detection at stop', (r: any) => r.scene.elements[0].kind = 'beam_stop'],
    ['wrong endpoint', (r: any) => r.hits[0].position_m[0] = .1],
    ['wrong length', (r: any) => r.segments[0].length_m = .4],
    ['reset inheritance', (r: any) => r.branches[0].start_interaction_count = 1],
    ['duplicate terminal', (r: any) => r.terminals.push(r.terminals[0])],
    ['lost weight', (r: any) => r.terminals[0].relative_weight = .5],
    ['wrong ledger', (r: any) => r.ledger.absorbed_weight = 1],
    ['hidden truncation', (r: any) => r.status = 'incomplete'],
    ['non-enclosing interval', (r: any) => r.hits[0].numerical_bounds.position_intervals_m[2] = [.3, .4]],
    ['uncertified forward interval', (r: any) => r.hits[0].numerical_bounds.t_parameter_interval_m[0] = 0],
    ['zero physical segment', (r: any) => r.segments[0].length_m = 0],
    ['nonunit direction', (r: any) => r.segments[0].direction = [0, 0, 2]],
    ['extra closed key', (r: any) => r.hits[0].ignored = true],
    ['changed fixed cap', (r: any) => r.limits.max_records = 300],
  ])('rejects %s before publishing any graph', (_name, mutate) => {
    const f = fixture(), value = structuredClone(f.result); mutate(value); expect(() => decodeGeometricTrace(bytes(value), f.request), 'W2_FULL_GRAPH_TRUST_BOUNDARY').toThrow();
  });
  it('rejects duplicate keys, underflow, nonfinite, invalid UTF8, trailing bytes and response caps', () => {
    expect(() => parseRoutingJSON('{"x":1,"x":2}')).toThrow('duplicate'); expect(() => parseRoutingJSON('{"x":1e-999}')).toThrow('underflow');
    expect(parseRoutingJSON('{"x":0e-999,"text":"1e-999"}')).toEqual({ x: 0, text: '1e-999' });
    expect(() => parseRoutingJSON('{"x":1e999}')).toThrow(); const f = fixture();
    expect(() => decodeGeometricTrace(new Uint8Array([0xff, 0xff]).buffer, f.request)).toThrow('UTF-8');
    expect(() => decodeGeometricTrace(new TextEncoder().encode(`${JSON.stringify(f.result)} {}`).buffer, f.request)).toThrow('trailing');
    expect(() => decodeGeometricTrace(new ArrayBuffer(W2_RESPONSE_CAP + 1), f.request)).toThrow('cap');
  });
  it('preserves signed zero in W2 source/pose JSON and exact echoed identity without changing old schemas', () => {
    const scene = structuredClone(W2_PRESETS.A) as any; scene.source.origin_m[0] = -0; scene.elements[0].pose.rotation_xyz_rad[0] = -0;
    const value = parseRoutingJSON(stringifyRoutingJSON(scene)) as any; expect(Object.is(value.source.origin_m[0], -0)).toBe(true); expect(Object.is(value.elements[0].pose.rotation_xyz_rad[0], -0)).toBe(true);
    expect(routingStructuralEqual(value, scene)).toBe(true); expect(routingStructuralEqual({ x: 0 }, { x: -0 })).toBe(false);
    const f = fixture(); (f.request.scene as any).source.origin_m[0] = -0; const result = structuredClone(f.result); (result.scene as any).source.origin_m[0] = 0;
    expect(() => decodeGeometricTrace(bytes(result), f.request)).toThrow('scene echo');
  });
  it('rejects unsupported source/scene declarations without normalizing or changing caller-owned data', () => {
    const scene = structuredClone(W2_PRESETS.A), before = structuredClone(scene); assertGeometricScene(scene); const owned = freezeGeometricScene(scene);
    expect(owned).toEqual(before); expect(owned.source).not.toBe(scene.source); expect(scene).toEqual(before);
    for (const mutate of [(s: any) => s.source.direction[2] = 2, (s: any) => s.elements[0].aperture.radius_m = 0, (s: any) => s.elements[1].id = s.elements[0].id, (s: any) => s.elements[0].pose.rotation_xyz_rad[0] = 4]) {
      const invalid = structuredClone(scene); mutate(invalid); expect(() => assertGeometricScene(invalid)).toThrow();
    }
  });
  it('requires atomic half-weight children, inherited state, BFS order and exactly one terminal per leaf', () => {
    const f = splitFixture(); expect(decodeGeometricTrace(bytes(f.result), f.request).ledger.detected_weight).toBe(1);
    for (const mutate of [
      (r: any) => r.branches.pop(), (r: any) => r.branches[1].start_interaction_count = 0,
      (r: any) => [r.branches[1], r.branches[2]] = [r.branches[2], r.branches[1]],
      (r: any) => r.hits[0].outgoing[1].relative_weight = 1,
      (r: any) => r.branches[1].origin_m = [.1, .08, .2],
      (r: any) => r.terminals.push({ ...r.terminals[0], branch_id: 'r0', relative_weight: 1 }),
    ]) { const value = structuredClone(f.result); mutate(value); expect(() => decodeGeometricTrace(bytes(value), f.request), 'W2_ATOMIC_SPLIT_ACCOUNTING').toThrow(); }
  });
  it('accepts an immediately capped child at its exact parent birth hit but rejects a foreign prior hit', () => {
    const f = immediateChildCapFixture(), decoded = decodeGeometricTrace(bytes(f.result), f.request);
    expect(decoded.hits).toHaveLength(32); expect(decoded.terminals.map(terminal => terminal.hit_id)).toEqual(['h0031', 'h0031']); expect(decoded.ledger.truncated_weight).toBe(1);
    const invalid = structuredClone(f.result); invalid.terminals[0].hit_id = 'h0030'; invalid.terminals[0].element_id = 'M1'; expect(() => decodeGeometricTrace(bytes(invalid), f.request)).toThrow('terminal hit');
  });
  it('uses exactly one original request and enforces streaming byte/source MIME/error policies', async () => {
    const f = fixture(), fetcher = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => new Response(JSON.stringify(f.result), { headers: { 'content-type': 'application/json' } }));
    const api = createGeometricRoutingFetchAPI(fetcher); const raw = await api.trace(f.request); expect(decodeGeometricTrace(raw, f.request).request_id).toBe(id);
    expect(fetcher).toHaveBeenCalledOnce(); expect(fetcher.mock.calls[0][0]).toBe('/api/w2/trace');
    const wrongMime = createGeometricRoutingFetchAPI(vi.fn(async () => new Response('{}', { headers: { 'content-type': 'text/plain' } }))); await expect(wrongMime.trace(f.request)).rejects.toThrow('content type');
    const oversized = createGeometricRoutingFetchAPI(vi.fn(async () => new Response(new Uint8Array(W2_RESPONSE_CAP + 1), { headers: { 'content-type': 'application/json' } }))); await expect(oversized.trace(f.request)).rejects.toThrow('cap');
    const busy = createGeometricRoutingFetchAPI(vi.fn(async () => new Response(JSON.stringify({ protocol_version: 1, message_type: 'routing_error', request_id: id, model_contract: W2_MODEL, error: { code: 'busy', message: 'The actual worker is occupied.' } }), { status: 409, headers: { 'content-type': 'application/json' } }))); await expect(busy.trace(f.request)).rejects.toThrow('HTTP 409');
  });
});
