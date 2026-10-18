import { afterEach, describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { cloneExperiment } from '../src/contracts';
import { createWaveFieldApparatus } from '../src/wave_field_apparatus';
import { W1_EXAMPLE } from '../src/wave_field_contracts';
import { calculateResearchCameraFit, researchBoundsCorners } from '../src/r03_fig2a_camera';
import { W1_OVERVIEW_DIRECTION } from '../src/scene';
import { createR03Apparatus } from '../src/r03_fig2a_apparatus';

function install(fail = -1) {
  const canvases: HTMLCanvasElement[] = [];
  vi.stubGlobal('document', { createElement() { const index = canvases.length, context = { fillRect() {}, fillText() {}, fillStyle: '', font: '', textAlign: '', textBaseline: '' };
    const canvas = { width: 0, height: 0, getContext: () => index === fail ? null : context } as unknown as HTMLCanvasElement; canvases.push(canvas); return canvas; } }); return canvases;
}
function buffers(group: THREE.Group) {
  const sources = new Set<ArrayBufferLike>(); group.traverse(object => { const shape = (object as THREE.Mesh).geometry;
    if (shape) { if (shape.index) sources.add(shape.index.array.buffer); Object.values(shape.attributes).forEach(attribute => sources.add(attribute.array.buffer)); }
    if (object instanceof THREE.InstancedMesh) sources.add(object.instanceMatrix.array.buffer); }); return sources;
}
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });
describe('W1 recognizable mounted train, exact planes and cleanup', () => {
  it('places the four mounted components at original longitudinal positions and preserves co-located identities', () => {
    install(); const experiment = cloneExperiment(W1_EXAMPLE); experiment.components[1].z_m = .03;
    const apparatus = createWaveFieldApparatus(experiment), snapshot = apparatus.snapshot() as any;
    expect(snapshot.componentCount).toBe(4); expect(snapshot.components.map((component: any) => [component.id, component.z_m])).toEqual([
      ['source', 0], ['aperture', .03], ['lens', .03], ['detector', .22] ]);
    expect(snapshot.worldMapping).toEqual({ x: '1000*x_m', y: '1-1000*y_m', z: '100*z_m' }); expect(snapshot.computedRays).toBe(false);
    const source = apparatus.group.children.find(object => object.userData.waveFieldComponent === 'source')!;
    expect(source.children.some(object => object instanceof THREE.Mesh && object.geometry instanceof THREE.CylinderGeometry)).toBe(true);
    apparatus.select('lens'); expect((apparatus.snapshot() as any).selected).toBe('lens'); expect(() => apparatus.select('invented')).toThrow('Unknown'); apparatus.dispose();
  });
  it('accounts unique actual geometry/instance/label sources under 512 KiB, without including borrowed field textures', () => {
    const canvases = install(), apparatus = createWaveFieldApparatus(W1_EXAMPLE), actual = [...buffers(apparatus.group)].reduce((n, buffer) => n + buffer.byteLength, 0);
    expect(apparatus.geometryBytes).toBe(actual); expect(apparatus.labelBytes).toBe(4 * 128 * 48 * 4);
    expect(apparatus.ownedBytes).toBe(actual + apparatus.labelBytes); expect(apparatus.ownedBytes).toBeLessThanOrEqual(512 * 1024);
    const group = new THREE.Group(), texture = new THREE.DataTexture(new Uint8Array(64), 4, 4), dispose = vi.fn(); texture.addEventListener('dispose', dispose);
    apparatus.setDisplay(group, texture); const before = apparatus.ownedBytes; apparatus.setDisplay(null, null); expect(apparatus.ownedBytes).toBe(before);
    apparatus.dispose(); expect(dispose).not.toHaveBeenCalled(); expect(canvases.every(canvas => canvas.width === 0 && canvas.height === 0)).toBe(true); texture.dispose();
  });
  it('frames mounted assemblies independently from table/labels and preserves camera/display ownership on selection', () => {
    install(); const apparatus = createWaveFieldApparatus(W1_EXAMPLE), all = apparatus.framingBounds(), lens = apparatus.framingBounds('lens');
    expect(all.getSize(new THREE.Vector3()).z).toBeGreaterThan(22); expect(lens.getSize(new THREE.Vector3()).z).toBeLessThan(1);
    const camera = new THREE.PerspectiveCamera(42, 1.5, .01, 100); camera.position.set(10, 12, 26); camera.lookAt(0, 1, 11); camera.updateMatrixWorld(true);
    const before = apparatus.ownedBytes;
    for (let i = 0; i < 20; i++) { apparatus.select(i % 2 ? 'aperture' : 'lens'); apparatus.updateLabels(camera, i % 2 ? 320 : 900, 600); }
    expect(apparatus.ownedBytes).toBe(before); expect(apparatus.framingBounds().equals(all)).toBe(true);
    const moved = new THREE.Vector3(2, 4, 8); apparatus.group.position.copy(moved); expect(apparatus.framingBounds().min.sub(moved).distanceTo(all.min)).toBeLessThan(1e-12); apparatus.dispose();
  });
  it('does not dispose borrowed scientific presentation and idempotently releases every owned asset', () => {
    install(); const apparatus = createWaveFieldApparatus(W1_EXAMPLE), owned = new Set<THREE.BufferGeometry | THREE.Material | THREE.Texture>();
    apparatus.group.traverse(object => { const mesh = object as THREE.Mesh; if (mesh.geometry && !(object instanceof THREE.Sprite)) owned.add(mesh.geometry);
      if (mesh.material) for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) { owned.add(material); const map = (material as THREE.MeshBasicMaterial).map; if (map) owned.add(map); } });
    const spies = [...owned].map(object => { const spy = vi.fn(); object.addEventListener('dispose' as never, spy); return spy; });
    const borrowed = new THREE.Group(), child = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial()), borrowedDispose = vi.fn(); child.geometry.addEventListener('dispose', borrowedDispose); borrowed.add(child);
    apparatus.setDisplay(borrowed, null); apparatus.dispose(); apparatus.dispose(); expect(borrowed.parent).toBeNull(); expect(borrowedDispose).not.toHaveBeenCalled();
    spies.forEach(spy => expect(spy, 'W1_MOUNT_RESOURCE_LEAK').toHaveBeenCalledOnce()); expect(apparatus.ownedBytes).toBe(0); expect(apparatus.group.children).toHaveLength(0); child.geometry.dispose();
  });
  it('cleans partial construction after a late mounted-label failure without leaking canvases', () => {
    const canvases = install(2); expect(() => createWaveFieldApparatus(W1_EXAMPLE)).toThrow('label canvas'); expect(canvases).toHaveLength(3);
    expect(canvases.every(canvas => canvas.width === 0 && canvas.height === 0)).toBe(true);
  });
  it('fits the long linear train side-on with readable nonoverlapping labels and complete projected bounds', () => {
    install(); const apparatus = createWaveFieldApparatus(W1_EXAMPLE);
    for (const [width, height] of [[900, 480], [810, 460], [1200, 650], [480, 340]]) {
      const camera = new THREE.PerspectiveCamera(42, width / height, .01, 100), bounds = apparatus.framingBounds();
      const fit = calculateResearchCameraFit(bounds, camera, 'focus', new THREE.Vector3(...W1_OVERVIEW_DIRECTION));
      camera.position.copy(fit.position); camera.up.copy(fit.up); camera.near = fit.near; camera.far = fit.far; camera.lookAt(fit.target); camera.updateProjectionMatrix(); camera.updateMatrixWorld(true);
      for (const point of researchBoundsCorners(bounds)) { const projected = point.project(camera); expect(Math.abs(projected.x)).toBeLessThanOrEqual(.88); expect(Math.abs(projected.y)).toBeLessThanOrEqual(.88); }
      apparatus.updateLabels(camera, width, height); const labels = (apparatus.snapshot() as any).labels.filter((label: any) => label.visible);
      expect(labels).toHaveLength(4);
      for (let a = 0; a < labels.length; a++) for (let b = a + 1; b < labels.length; b++) {
        const one = labels[a].pixelBounds, two = labels[b].pixelBounds;
        expect(one.right <= two.left || two.right <= one.left || one.bottom <= two.top || two.bottom <= one.top, 'W1_READABLE_MOUNT_LABELS').toBe(true);
      }
    } apparatus.dispose();
  });
  it('exposes the actual shared Three Sprite buffers so retained W1 and R03 are charged once without disposing their borrowed owner', () => {
    install(); const wave = createWaveFieldApparatus(W1_EXAMPLE), ideal = createR03Apparatus();
    const waveSources = buffers(wave.group), idealSources = buffers(ideal.group), shared = new Set([...waveSources].filter(buffer => idealSources.has(buffer)));
    expect(shared.size).toBeGreaterThan(0); expect(new Set(wave.borrowedGeometryBuffers), 'W1_R03_ACTUAL_SHARED_SPRITE_BUFFERS').toEqual(shared);
    const bytes = [...shared].reduce((n, buffer) => n + buffer.byteLength, 0); expect(wave.borrowedGeometryBytes).toBe(bytes);
    const actualJointGeometry = [...new Set([...waveSources, ...idealSources])].reduce((n, buffer) => n + buffer.byteLength, 0);
    expect(wave.ownedBytes + ideal.ownedBytes - wave.borrowedGeometryBytes, 'W1_R03_ALIAS_CHARGED_ONCE')
      .toBe(actualJointGeometry + wave.labelBytes + ideal.labelBytes);
    let borrowed: THREE.BufferGeometry | null = null;
    wave.group.traverse(object => { if (object instanceof THREE.Sprite) borrowed = object.geometry; });
    const dispose = vi.fn(); borrowed!.addEventListener('dispose', dispose); wave.dispose(); ideal.dispose();
    expect(dispose, 'W1_R03_BORROWED_GLOBAL_NOT_DISPOSED').not.toHaveBeenCalled();
    expect(wave.borrowedGeometryBytes).toBe(0); expect(wave.borrowedGeometryBuffers).toEqual([]); expect([...shared].every(buffer => buffer.byteLength > 0)).toBe(true);
  });
});
