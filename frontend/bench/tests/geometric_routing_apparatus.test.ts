import { describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { W2_PRESETS, type GeometricTraceResult } from '../src/geometric_routing_contracts';
import { W2_WORLD_SCALE, createGeometricRoutingApparatus, prepareGeometricRoutingDisplay, routingDisplayMatrix } from '../src/geometric_routing_apparatus';
import { GeometricRoutingWorkspace, measureRoutingDOMReservation, resolveCurrentRoutingHit, type GeometricRoutingHitIdentity } from '../src/geometric_routing_workspace';

function buffers(group: THREE.Group): Set<ArrayBufferLike> {
  const sources = new Set<ArrayBufferLike>(); group.traverse(object => { const shape = (object as THREE.Mesh).geometry;
    if (shape) { if (shape.index) sources.add(shape.index.array.buffer); for (const attribute of Object.values(shape.attributes)) sources.add(attribute.array.buffer); } }); return sources;
}
function displayFixture(): GeometricTraceResult {
  // Explicit display-ownership records, not a valid API fixture or optical reference.
  return { request_id: '11111111-1111-4111-8111-111111111111', scene_sha256: 'a'.repeat(64),
    branches: [{ id: 'r0' }, { id: 'r0.T' }, { id: 'r0.R' }],
    segments: [{ id: 's0000', branch_id: 'r0', start_m: [0, .08, 0], end_m: [0, .08, .2], relative_weight: 1 },
      { id: 's0001', branch_id: 'r0.T', start_m: [0, .08, .2], end_m: [0, .08, 1], relative_weight: .5 },
      { id: 's0002', branch_id: 'r0.R', start_m: [0, .08, .2], end_m: [.1, .08, .2], relative_weight: 2 ** -31 }],
    hits: [{ id: 'h0000', element_id: 'S1', position_m: [0, .08, .2] }, { id: 'h0001', element_id: 'STOP1', position_m: [.1, .08, .2] }],
    terminals: [{ branch_id: 'r0.T', category: 'escaped', position_m: [0, .08, 1] }, { branch_id: 'r0.R', category: 'resource_truncated', position_m: [.1, .08, .2] }],
  } as unknown as GeometricTraceResult;
}
describe('W2 uniform mounted apparatus and returned path presentation', () => {
  it('requires the current request, scene and hit identity before resolving a calculated hit', () => {
    const result = displayFixture(), selection: GeometricRoutingHitIdentity = Object.freeze({ requestId: result.request_id, sceneSha256: result.scene_sha256, hitId: 'h0001' });
    expect(resolveCurrentRoutingHit(result, selection)).toBe(result.hits[1]);
    expect(resolveCurrentRoutingHit(null, selection)).toBeNull(); expect(resolveCurrentRoutingHit(result, null)).toBeNull();
    expect(resolveCurrentRoutingHit(result, { ...selection, requestId: '22222222-2222-4222-8222-222222222222' })).toBeNull();
    expect(resolveCurrentRoutingHit(result, { ...selection, sceneSha256: 'b'.repeat(64) })).toBeNull();
    expect(resolveCurrentRoutingHit(result, { ...selection, hitId: 'h9999' })).toBeNull();
  });
  it('resolves repeated short hit IDs only from the newly accepted request without copying or changing values', () => {
    const original = displayFixture(), oldSelection = Object.freeze({ requestId: original.request_id, sceneSha256: original.scene_sha256, hitId: 'h0001' });
    const next = { ...original, request_id: '22222222-2222-4222-8222-222222222222',
      hits: original.hits.map(hit => hit.id === 'h0001' ? { ...hit, element_id: 'D2', position_m: [.12345678901234567, .08, .3] as const } : hit) };
    const nextSelection = Object.freeze({ ...oldSelection, requestId: next.request_id }), before = structuredClone({ original, next, oldSelection, nextSelection });
    expect(resolveCurrentRoutingHit(next, oldSelection), 'W2_HIT_SELECTION_MUST_NOT_REUSE_OLD_REQUEST').toBeNull();
    const resolved = resolveCurrentRoutingHit(next, nextSelection); expect(resolved).toBe(next.hits[1]); expect(resolved?.element_id).toBe('D2');
    expect(resolved?.position_m).toBe(next.hits[1].position_m); expect(resolved?.position_m[0]).toBe(.12345678901234567);
    expect({ original, next, oldSelection, nextSelection }).toEqual(before);
  });
  it('clears an obsolete active hit before the cached historical-result render can return', () => {
    const previous = displayFixture(), workspace = Object.create(GeometricRoutingWorkspace.prototype) as any, showHit = vi.fn();
    workspace.controller = { state: { currentResult: null, completedNumerical: null, lastResult: previous } };
    workspace.selectedHitIdentity = { requestId: previous.request_id, sceneSha256: previous.scene_sha256, hitId: 'h0001' };
    workspace.resultIdentity = previous; workspace.resultCurrent = false; workspace.showHit = showHit;
    workspace.updateResult(); expect(workspace.selectedHitIdentity, 'W2_DETACHED_CURRENT_HIT_MUST_CLEAR').toBeNull();
    expect(showHit).toHaveBeenCalledOnce(); expect(workspace.controller.state.lastResult).toBe(previous);
  });
  it('counts DOM node, attribute, input and full-value text reservations with identity de-duplication', () => {
    const text = { nodeType: 3, nodeValue: '-0.000000000000000123456789', childNodes: [] } as unknown as Node;
    const input = { nodeType: 1, tagName: 'INPUT', value: '0.12345678901234567', attributes: [{ name: 'aria-label', value: 'Position / m' }], childNodes: [text] } as unknown as Node;
    const once = measureRoutingDOMReservation([input]); expect(once).toBe(4096 + 256 + 16 + 48 + 2 * ('aria-label'.length + 'Position / m'.length) + 2 * '0.12345678901234567'.length + 256 + 2 * '-0.000000000000000123456789'.length);
    expect(measureRoutingDOMReservation([input, input, text])).toBe(once);
  });
  it('uses isotropic right-handed SI mapping and recognizable equipment without changing source/pose inputs', () => {
    const before = structuredClone(W2_PRESETS.B), apparatus = createGeometricRoutingApparatus(W2_PRESETS.B), snapshot = apparatus.snapshot() as any;
    expect(snapshot.componentCount).toBe(4); expect(snapshot.worldMapping).toContain('isotropic'); expect(snapshot.opticalPicking).toBe(false);
    expect(apparatus.group.children.some(item => item instanceof THREE.HemisphereLight)).toBe(true);
    const key = apparatus.group.children.find(item => item instanceof THREE.DirectionalLight) as THREE.DirectionalLight;
    expect(key).toBeDefined(); expect(key.castShadow).toBe(false);
    for (const element of W2_PRESETS.B.elements) {
      const object = apparatus.group.children.find(object => object.userData.w2ElementId === element.id)!;
      expect(object.position.toArray()).toEqual(element.pose.position_m.map(n => n * W2_WORLD_SCALE)); expect(object.userData.identity).toBe(element.id);
      expect(object.children.some(object => object instanceof THREE.Mesh && object.geometry instanceof THREE.CylinderGeometry)).toBe(true);
    }
    expect(W2_PRESETS.B).toEqual(before); apparatus.select('M2'); expect((apparatus.snapshot() as any).selected).toBe('M2'); expect(() => apparatus.select('unknown')).toThrow(); apparatus.dispose();
  });
  it('implements display RzRyRx in the documented order and prefers returned authoritative frames', () => {
    const matrix = routingDisplayMatrix([Math.PI / 2, Math.PI / 2, 0]);
    expect(new THREE.Vector3(1, 0, 0).applyMatrix4(matrix).distanceTo(new THREE.Vector3(0, 0, -1))).toBeLessThan(1e-14);
    expect(new THREE.Vector3(0, 1, 0).applyMatrix4(matrix).distanceTo(new THREE.Vector3(1, 0, 0))).toBeLessThan(1e-14);
    expect(new THREE.Vector3(0, 0, 1).applyMatrix4(matrix).distanceTo(new THREE.Vector3(0, -1, 0))).toBeLessThan(1e-14);
    const authoritative = routingDisplayMatrix([.2, .3, .4], { element_id: 'M', u: [1, 0, 0], v: [0, 1, 0], n: [0, 0, 1] }); expect(authoritative.equals(new THREE.Matrix4())).toBe(true);
  });
  it('accounts unique actual geometry stores and declared material/node reservations with no borrowed Sprite quad', () => {
    const apparatus = createGeometricRoutingApparatus(W2_PRESETS.C), actual = [...buffers(apparatus.group)].reduce((sum, buffer) => sum + buffer.byteLength, 0), snapshot = apparatus.snapshot() as any;
    expect(apparatus.geometryBytes).toBe(actual); expect(apparatus.labelBytes).toBe(0); expect(apparatus.ownedBytes, 'W2_APPARATUS_OWNERSHIP_ACCOUNTING').toBe(actual + snapshot.metadataReservationBytes);
    expect(apparatus.ownedBytes).toBeLessThanOrEqual(512 * 1024); let sprites = 0; apparatus.group.traverse(object => { if (object instanceof THREE.Sprite) sprites++; }); expect(sprites).toBe(0); apparatus.dispose();
  });
  it('does not let display attachment, selection or camera framing modify optical settings or own borrowed display assets', () => {
    const apparatus = createGeometricRoutingApparatus(W2_PRESETS.A), before = apparatus.ownedBytes, bounds = apparatus.framingBounds(), selected = apparatus.framingBounds('M1');
    expect(selected.getSize(new THREE.Vector3()).x).toBeLessThan(bounds.getSize(new THREE.Vector3()).x);
    const borrowed = new THREE.Group(), geometry = new THREE.BoxGeometry(1, 1, 1), material = new THREE.MeshBasicMaterial(), child = new THREE.Mesh(geometry, material), spy = vi.fn(); geometry.addEventListener('dispose', spy); borrowed.add(child);
    apparatus.setDisplay(borrowed); expect(apparatus.ownedBytes).toBe(before); apparatus.select('D1'); apparatus.setDisplay(null); expect(borrowed.parent).toBeNull();
    apparatus.setDisplay(borrowed); apparatus.dispose(); expect(spy).not.toHaveBeenCalled(); expect(borrowed.parent).toBeNull(); geometry.dispose(); material.dispose();
  });
  it('renders actual submitted segment endpoints and keeps even tiny-weight branches visible without fake receiver extensions', () => {
    const result = displayFixture(), before = structuredClone(result), display = prepareGeometricRoutingDisplay(result), snapshot = display.snapshot() as any;
    expect(snapshot.segmentCount).toBe(3); expect(snapshot.endpoints).toEqual(result.segments.map(segment => ({ id: segment.id, branch: segment.branch_id, start_m: segment.start_m, end_m: segment.end_m })));
    expect(snapshot.visibleBranchIds).toEqual(['r0', 'r0.T', 'r0.R']);
    const routeMeshes: THREE.Mesh[] = []; display.group.traverse(object => { if (object.userData.w2SegmentId === 's0002') routeMeshes.push(object as THREE.Mesh); }); expect(routeMeshes).toHaveLength(2);
    for (const mesh of routeMeshes) { expect(mesh.visible).toBe(true); expect((mesh.material as THREE.MeshBasicMaterial).opacity).toBeGreaterThan(0); expect(mesh.position.toArray()).toEqual([.5, .8, 2]); }
    display.selectBranch('r0.R'); display.selectHit('h0001'); expect((display.snapshot() as any).selectedBranch).toBe('r0.R'); expect(result).toEqual(before); display.dispose();
  });
  it('releases each owned geometry/material exactly once and idempotently removes all rendered paths', () => {
    const display = prepareGeometricRoutingDisplay(displayFixture()), owned = new Set<THREE.BufferGeometry | THREE.Material>();
    display.group.traverse(object => { const mesh = object as THREE.Mesh; if (mesh.geometry) owned.add(mesh.geometry); if (mesh.material) for (const item of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) owned.add(item); });
    const spies = [...owned].map(item => { const spy = vi.fn(); item.addEventListener('dispose' as never, spy); return spy; }); display.dispose(); display.dispose();
    spies.forEach(spy => expect(spy, 'W2_OWNED_DISPLAY_RELEASE').toHaveBeenCalledOnce()); expect(display.ownedBytes).toBe(0); expect(display.group.children).toHaveLength(0);
  });
});
