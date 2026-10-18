/** Presentation-only invariants. No optical model or scientific controller is invoked. */
import { afterEach, describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { createR03Apparatus } from '../src/r03_fig2a_apparatus';

function installCanvas(failAt = -1): HTMLCanvasElement[] {
  const canvases: HTMLCanvasElement[] = [];
  vi.stubGlobal('document', { createElement(kind: string) {
    if (kind !== 'canvas') throw new Error('Unexpected presentation element'); const index = canvases.length;
    const context = { fillRect() {}, fillText() {}, fillStyle: '', font: '', textAlign: '', textBaseline: '' };
    const canvas = { width: 0, height: 0, getContext: () => index === failAt ? null : context } as unknown as HTMLCanvasElement;
    canvases.push(canvas); return canvas;
  } });
  return canvases;
}
function actualBuffers(group: THREE.Group): Set<ArrayBufferLike> {
  const buffers = new Set<ArrayBufferLike>(); group.traverse(object => {
    const geometry = (object as THREE.Mesh).geometry;
    if (geometry) {
      if (geometry.index) buffers.add(geometry.index.array.buffer);
      for (const attribute of [...Object.values(geometry.attributes), ...Object.values(geometry.morphAttributes).flat()])
        buffers.add(attribute instanceof THREE.InterleavedBufferAttribute ? attribute.data.array.buffer : attribute.array.buffer);
    }
    if (object instanceof THREE.InstancedMesh) buffers.add(object.instanceMatrix.array.buffer);
  }); return buffers;
}
function camera(): THREE.PerspectiveCamera { const value = new THREE.PerspectiveCamera(42, 1.5, .01, 100);
  value.position.set(6, 7, 9); value.lookAt(.2, .6, -.5); value.updateProjectionMatrix(); value.updateMatrixWorld(); return value; }
function objects(group: THREE.Group): { geometries: THREE.BufferGeometry[]; materials: THREE.Material[]; textures: THREE.Texture[] } {
  const geometries = new Set<THREE.BufferGeometry>(), materials = new Set<THREE.Material>(), textures = new Set<THREE.Texture>();
  group.traverse(object => { const mesh = object as THREE.Mesh; if (mesh.geometry && !(object instanceof THREE.Sprite)) geometries.add(mesh.geometry);
    const value = mesh.material; if (value) for (const item of Array.isArray(value) ? value : [value]) {
      materials.add(item); const map = (item as THREE.MeshBasicMaterial).map; if (map && object instanceof THREE.Sprite) textures.add(map);
    }
  }); return { geometries: [...geometries], materials: [...materials], textures: [...textures] };
}
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe('lab-first mounted apparatus presentation', () => {
  it('accounts all unique CPU geometry/instance and fixed label backing stores without increasing the cap', () => {
    const canvases = installCanvas(), apparatus = createR03Apparatus();
    const bytes = [...actualBuffers(apparatus.group)].reduce((total, buffer) => total + buffer.byteLength, 0);
    expect(apparatus.geometryBytes, 'UX_ACTUAL_GEOMETRY_OWNERSHIP').toBe(bytes);
    expect(apparatus.labelBytes).toBe(canvases.reduce((n, canvas) => n + canvas.width * canvas.height * 4, 0));
    expect(apparatus.labelBytes).toBe(7 * 128 * 48 * 4); expect(apparatus.ownedBytes).toBe(apparatus.geometryBytes + apparatus.labelBytes);
    expect(apparatus.ownedBytes).toBeLessThanOrEqual(512 * 1024); apparatus.dispose();
    expect(apparatus.ownedBytes).toBe(0); expect(canvases.every(canvas => canvas.width === 0 && canvas.height === 0)).toBe(true);
  });
  it('frames actual assemblies, excluding oversized table, labels, halos and other decorative objects', () => {
    installCanvas(); const apparatus = createR03Apparatus(), baseline = apparatus.framingBounds();
    expect(baseline.getSize(new THREE.Vector3()).x).toBeGreaterThan(7); expect(baseline.min.x).toBeGreaterThan(-4); expect(baseline.max.x).toBeLessThan(5);
    apparatus.group.traverse(object => {
      if (object.userData.r03Decoration === 'table' || object.userData.r03FramingExcluded || object instanceof THREE.Sprite) {
        object.position.set(10000, 10000, 10000); object.scale.setScalar(10000);
      }
    });
    expect(apparatus.framingBounds().equals(baseline), 'UX_ASSEMBLY_NOT_TABLE_FRAMING').toBe(true);
    const qwp = apparatus.framingBounds('qwp'); expect(qwp.getSize(new THREE.Vector3()).x).toBeLessThan(1); expect(qwp.getSize(new THREE.Vector3()).y).toBeGreaterThan(1);
    expect(qwp.getCenter(new THREE.Vector3()).distanceTo(baseline.getCenter(new THREE.Vector3()))).toBeGreaterThan(.1);
    expect(() => apparatus.framingBounds('not-a-component')).toThrow('Unknown'); apparatus.dispose();
  });
  it('returns fresh world-space bounds and respects parent transforms without altering geometry', () => {
    installCanvas(); const apparatus = createR03Apparatus(), before = apparatus.framingBounds('source'), beforeAll = apparatus.framingBounds();
    const offset = new THREE.Vector3(12, 3, -4); apparatus.group.position.copy(offset); const after = apparatus.framingBounds('source');
    expect(after.min.clone().sub(offset).distanceTo(before.min)).toBeLessThan(1e-12);
    expect(after.max.clone().sub(offset).distanceTo(before.max)).toBeLessThan(1e-12);
    after.makeEmpty(); expect(apparatus.framingBounds('source').isEmpty()).toBe(false);
    const all = apparatus.framingBounds(); expect(all.min.clone().sub(offset).distanceTo(beforeAll.min)).toBeLessThan(1e-12); apparatus.dispose();
  });
  it('uses explicit validated-angle mapping and rejects invalid paired updates atomically', () => {
    installCanvas(); const apparatus = createR03Apparatus(); apparatus.setAngles(Math.PI / 2, -Math.PI / 2);
    let state = apparatus.snapshot() as any; expect(state.axisDisplayBasis).toEqual({ x: '+z', y: '-y' });
    for (const [actual, expected] of [[state.axisDirections.qwp, [0, -1, 0]], [state.axisDirections.hwp, [0, 1, 0]]] as [number[], number[]][])
      actual.forEach((value, index) => expect(Math.abs(value - expected[index]), 'UX_AXIS_CONVENTION').toBeLessThan(1e-14));
    const before = state.axisDirections; expect(() => apparatus.setAngles(0, Infinity)).toThrow('Validated');
    expect(() => apparatus.setAngles(NaN, 0)).toThrow('Validated'); expect(() => apparatus.setAngles(3 * Math.PI, 0)).toThrow('Validated');
    state = apparatus.snapshot(); expect((state as any).axisDirections).toEqual(before); apparatus.dispose();
  });
  it('uses static selected-segment emphasis and neutral unknown routing rather than a new physical splitter', () => {
    installCanvas(); const raf = vi.fn(); vi.stubGlobal('requestAnimationFrame', raf); const apparatus = createR03Apparatus();
    apparatus.select('qwp'); let state = apparatus.snapshot() as any;
    expect(state.functionalSegments.filter((segment: any) => segment.highlighted).map((segment: any) => segment.id)).toEqual(['routing-qwp', 'qwp-hwp']);
    apparatus.select('slm'); state = apparatus.snapshot();
    expect(state.functionalSegments.filter((segment: any) => segment.highlighted).map((segment: any) => segment.id)).toEqual(['routing-modulator', 'modulator-routing']);
    const unknown: THREE.Mesh[] = []; apparatus.group.traverse(object => { if (object.userData.r03UnknownConnector) unknown.push(object as THREE.Mesh); });
    expect(unknown).toHaveLength(1); expect((unknown[0].material as THREE.MeshStandardMaterial).transparent).toBe(false);
    expect(state).toMatchObject({ computedRays: false, propagatedFieldSections: false, staticDirections: true }); expect(raf).not.toHaveBeenCalled();
    expect(() => apparatus.select('invented-stage')).toThrow('Unknown'); apparatus.dispose();
  });
  it('keeps concise screen-sized labels, selected priority and nonoverlap across viewport changes without allocating new assets', () => {
    const canvases = installCanvas(), apparatus = createR03Apparatus(), view = camera(), before = apparatus.ownedBytes;
    apparatus.select('qwp'); apparatus.updateLabels(view, 900, 600); let state = apparatus.snapshot() as any;
    expect(state.labels.find((label: any) => label.id === 'qwp').visible).toBe(true);
    const visible = state.labels.filter((label: any) => label.visible);
    let selectedSprite: THREE.Sprite | null = null; apparatus.group.traverse(object => { if (object instanceof THREE.Sprite && object.userData.r03Label === 'qwp') selectedSprite = object; });
    const center = selectedSprite!.getWorldPosition(new THREE.Vector3()), scale = selectedSprite!.getWorldScale(new THREE.Vector3());
    const up = new THREE.Vector3(0, 1, 0).applyQuaternion(view.quaternion).multiplyScalar(scale.y / 2);
    const top = center.clone().add(up).project(view), bottom = center.clone().sub(up).project(view);
    expect(Math.abs(top.y - bottom.y) * 600 / 2, 'UX_PROJECTED_READABLE_LABEL').toBeCloseTo(26, 10);
    for (let i = 0; i < visible.length; i++) for (let j = i + 1; j < visible.length; j++) {
      const a = visible[i].pixelBounds, b = visible[j].pixelBounds;
      expect(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top, 'UX_LABEL_OVERLAP').toBe(true);
    }
    for (let i = 0; i < 100; i++) { apparatus.updateLabels(view, i % 2 ? 320 : 900, i % 2 ? 240 : 600); }
    expect(canvases).toHaveLength(7); expect(apparatus.ownedBytes).toBe(before); state = apparatus.snapshot();
    expect(state.labels.every((label: any) => label.text.length <= 8)).toBe(true); expect(state.labelUpdateCount).toBe(101); apparatus.dispose();
  });
  it('borrows the authoritative SLM texture without recoloring, filtering, or disposing its separate owner', () => {
    installCanvas(); const apparatus = createR03Apparatus(), texture = new THREE.DataTexture(new Uint8Array(1024), 16, 16);
    texture.flipY = true; texture.colorSpace = THREE.SRGBColorSpace; texture.minFilter = texture.magFilter = THREE.NearestFilter;
    const spy = vi.fn(); texture.addEventListener('dispose', spy); const original = { flipY: texture.flipY, colorSpace: texture.colorSpace, minFilter: texture.minFilter, data: texture.image.data };
    apparatus.setPhase(texture); let phase: THREE.Mesh | undefined; apparatus.group.traverse(object => { if (object.userData.r03PhaseFace) phase = object as THREE.Mesh; });
    expect((phase!.material as THREE.MeshBasicMaterial).map).toBe(texture); expect((phase!.material as THREE.MeshBasicMaterial).toneMapped).toBe(false);
    apparatus.select('hwp'); apparatus.updateLabels(camera(), 900, 600); expect(texture.image.data).toBe(original.data);
    expect({ flipY: texture.flipY, colorSpace: texture.colorSpace, minFilter: texture.minFilter }).toEqual({ flipY: original.flipY, colorSpace: original.colorSpace, minFilter: original.minFilter });
    apparatus.dispose(); expect(spy).not.toHaveBeenCalled(); texture.dispose(); expect(spy).toHaveBeenCalledOnce();
  });
  it('idempotently disposes every owned unique geometry/material/label and cleans partial label failures', () => {
    const canvases = installCanvas(), apparatus = createR03Apparatus(), owned = objects(apparatus.group);
    let sharedQuad: THREE.BufferGeometry | null = null; apparatus.group.traverse(object => { if (object instanceof THREE.Sprite) sharedQuad = object.geometry; });
    const sharedDispose = vi.fn(); sharedQuad!.addEventListener('dispose', sharedDispose);
    const spies = [...owned.geometries, ...owned.materials, ...owned.textures].map(object => { const spy = vi.fn(); object.addEventListener('dispose' as never, spy); return spy; });
    apparatus.dispose(); apparatus.dispose(); spies.forEach(spy => expect(spy).toHaveBeenCalledOnce()); expect(sharedDispose).not.toHaveBeenCalled();
    expect(apparatus.group.children).toHaveLength(0); expect(apparatus.geometryCount).toBe(0); expect(canvases.every(c => c.width === 0 && c.height === 0)).toBe(true);
    const partial = installCanvas(3); expect(() => createR03Apparatus()).toThrow('label canvas'); expect(partial).toHaveLength(4);
    expect(partial.every(c => c.width === 0 && c.height === 0)).toBe(true);
  });
});
