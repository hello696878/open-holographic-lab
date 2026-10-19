import { afterEach, describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { cloneExperiment } from '../src/contracts';
import { createWaveFieldApparatus } from '../src/wave_field_apparatus';
import { W1_EXAMPLE } from '../src/wave_field_contracts';
import { calculateResearchCameraFit, researchBoundsCorners } from '../src/r03_fig2a_camera';
import { visibleWaveFieldHit, W1_BEAM_DIRECTION, W1_OVERVIEW_DIRECTION, W1_SECTION_DIRECTION } from '../src/scene';
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
  it.each([[1366, 768], [1440, 900], [1920, 1080]])('fits the complete mounted train and magnified calculated field at %ix%i without changing physical bounds', (width, height) => {
    install(); const apparatus = createWaveFieldApparatus(W1_EXAMPLE), physical = apparatus.framingBounds(), original = physical.clone();
    // The 128 x 16um window is 2.048 world units across before M4. Include
    // both its half-sample coordinate offset and the full symmetric span.
    const calculated = new THREE.Box3(new THREE.Vector3(-4.128, -3.096, 0), new THREE.Vector3(4.096, 5.128, 22));
    const bounds = physical.clone().union(calculated), originalBounds = bounds.clone();
    const camera = new THREE.PerspectiveCamera(42, width / height, .01, 100), oldCamera = camera.clone();
    const direction = new THREE.Vector3(...W1_BEAM_DIRECTION).normalize();
    const fit = calculateResearchCameraFit(bounds, camera, 'focus', direction);
    expect(bounds.equals(originalBounds), 'W1_BEAM_FIT_PRESERVES_PRESENTATION_BOUNDS').toBe(true);
    expect(physical.equals(original), 'W1_BEAM_FIT_PRESERVES_PHYSICAL_MOUNTS').toBe(true);
    expect(camera.position.equals(oldCamera.position)).toBe(true); expect(camera.projectionMatrix.equals(oldCamera.projectionMatrix)).toBe(true);
    expect(fit.target.equals(bounds.getCenter(new THREE.Vector3()))).toBe(true);
    expect(fit.position.clone().sub(fit.target).normalize().distanceTo(direction)).toBeLessThan(1e-12);
    camera.position.copy(fit.position); camera.up.copy(fit.up); camera.near = fit.near; camera.far = fit.far;
    camera.lookAt(fit.target); camera.updateProjectionMatrix(); camera.updateMatrixWorld(true);
    const corners = researchBoundsCorners(bounds); expect(corners).toHaveLength(8);
    for (const point of corners) {
      const projected = point.clone().project(camera), depth = -point.clone().applyMatrix4(camera.matrixWorldInverse).z;
      expect(Math.abs(projected.x), 'W1_MAGNIFIED_BEAM_HORIZONTAL_FIT').toBeLessThanOrEqual(fit.usableNDC);
      expect(Math.abs(projected.y), 'W1_MAGNIFIED_BEAM_VERTICAL_FIT').toBeLessThanOrEqual(fit.usableNDC);
      expect(depth).toBeGreaterThan(camera.near); expect(depth).toBeLessThan(camera.far);
    }
    apparatus.dispose();
  });
  it.each([[1366, 768], [1440, 900], [1920, 1080]])('fits a selected magnified section face-on at %ix%i without changing its physical z', (width, height) => {
    const sectionZ = 11.333333333333334;
    // A nonzero presentation-only depth makes every corner independently
    // testable while retaining the actual selected longitudinal center.
    const bounds = new THREE.Box3(new THREE.Vector3(-4.128, -3.096, sectionZ - .01), new THREE.Vector3(4.096, 5.128, sectionZ + .01));
    const original = bounds.clone(), camera = new THREE.PerspectiveCamera(42, width / height, .01, 100);
    const direction = new THREE.Vector3(...W1_SECTION_DIRECTION).normalize();
    expect(direction.dot(new THREE.Vector3(0, 0, 1)), 'W1_SECTION_VIEW_FACES_TRANSVERSE_PLANE').toBeGreaterThan(.999999);
    const fit = calculateResearchCameraFit(bounds, camera, 'focus', direction);
    expect(bounds.equals(original)).toBe(true); expect(fit.target.z, 'W1_SECTION_FIT_RETAINS_LONGITUDINAL_CENTER').toBe(sectionZ);
    expect(fit.position.clone().sub(fit.target).normalize().distanceTo(direction)).toBeLessThan(1e-12);
    camera.position.copy(fit.position); camera.up.copy(fit.up); camera.near = fit.near; camera.far = fit.far;
    camera.lookAt(fit.target); camera.updateProjectionMatrix(); camera.updateMatrixWorld(true);
    const corners = researchBoundsCorners(bounds); expect(corners).toHaveLength(8);
    for (const point of corners) {
      const projected = point.clone().project(camera), depth = -point.clone().applyMatrix4(camera.matrixWorldInverse).z;
      expect(Math.abs(projected.x), 'W1_SELECTED_SECTION_HORIZONTAL_FIT').toBeLessThanOrEqual(fit.usableNDC);
      expect(Math.abs(projected.y), 'W1_SELECTED_SECTION_VERTICAL_FIT').toBeLessThanOrEqual(fit.usableNDC);
      expect(depth).toBeGreaterThan(camera.near); expect(depth).toBeLessThan(camera.far);
    }
  });
  it.each([
    { stage: 'source', z: 0, expectedOccluder: 'source' },
    { stage: 'before:aperture', z: W1_EXAMPLE.components[0].z_m * 100, expectedOccluder: null },
    { stage: 'before:lens', z: W1_EXAMPLE.components[1].z_m * 100, expectedOccluder: null },
    { stage: 'sampled downstream focus', z: 11.333333333333334, expectedOccluder: 'detector' },
    { stage: 'observation', z: W1_EXAMPLE.observation.z_m * 100, expectedOccluder: 'detector' },
  ])('independently identifies actual mounted occlusion at $stage instead of assuming a clear section-view ray', ({ stage, z, expectedOccluder }) => {
    install(); const apparatus = createWaveFieldApparatus(W1_EXAMPLE);
    try {
      const bounds = new THREE.Box3(new THREE.Vector3(-4.128, -3.096, z - .01), new THREE.Vector3(4.096, 5.128, z + .01));
      const camera = new THREE.PerspectiveCamera(42, 1440 / 900, .01, 100);
      const fit = calculateResearchCameraFit(bounds, camera, 'focus', new THREE.Vector3(...W1_SECTION_DIRECTION));
      camera.position.copy(fit.position); camera.up.copy(fit.up); camera.near = fit.near; camera.far = fit.far;
      camera.lookAt(fit.target); camera.updateProjectionMatrix(); camera.updateMatrixWorld(true); apparatus.group.updateWorldMatrix(true, true);
      const target = new THREE.Vector3(0, 1, z), distance = camera.position.distanceTo(target);
      const ray = new THREE.Raycaster(camera.position.clone(), target.clone().sub(camera.position).normalize(), 0, distance);
      ray.camera = camera;
      const blockers = ray.intersectObject(apparatus.group, true).filter(hit => {
        if (hit.distance >= distance - 1e-5 || !(hit.object instanceof THREE.Mesh) || !visibleWaveFieldHit(hit.object, apparatus.group)) return false;
        const material = Array.isArray(hit.object.material) ? hit.object.material[hit.face?.materialIndex ?? 0] : hit.object.material;
        return !material.transparent && material.opacity > 0;
      }).map(hit => ({ component: hit.object.userData.identity ?? 'apparatus', geometry: (hit.object as THREE.Mesh).geometry.type,
        point: hit.point.toArray(), distance: hit.distance }));
      // The actual source barrel and detector backing are opaque counterexamples
      // to a universally clear +Z view. This fixture preserves that geometry;
      // separate display/GPU tests must prove the labelled selected-field overlay.
      expect([...new Set(blockers.map(hit => hit.component))], `W1_ACTUAL_MOUNT_OCCLUSION:${stage}`)
        .toEqual(expectedOccluder === null ? [] : [expectedOccluder]);
    } finally { apparatus.dispose(); }
  });
  it('picks only the visible attached event side and rejects hidden ancestry without mutating the scene', () => {
    const root = new THREE.Group(), layer = new THREE.Group(), outside = new THREE.Group(); root.add(layer);
    const geometry = new THREE.PlaneGeometry(2, 2), material = new THREE.MeshBasicMaterial({ side: THREE.DoubleSide });
    const before = new THREE.Mesh(geometry, material), after = new THREE.Mesh(geometry, material), foreign = new THREE.Mesh(geometry, material);
    before.userData.waveFieldSection = 'section:before:lens'; after.userData.waveFieldSection = 'section:after:lens';
    before.visible = false; layer.add(before, after); outside.add(foreign); root.updateWorldMatrix(true, true);
    const ray = new THREE.Raycaster(new THREE.Vector3(.2, .3, 5), new THREE.Vector3(0, 0, -1));
    const hits = ray.intersectObject(root, true);
    // Three genuinely returns invisible meshes too. Visibility filtering must
    // preserve distinct co-located event identities instead of moving a plane.
    expect(hits.some(hit => hit.object === before), 'W1_RAYCAST_INCLUDES_HIDDEN_NEGATIVE_CONTROL').toBe(true);
    expect(before.position.z).toBe(after.position.z);
    const original = [root, layer, before, after, foreign].map(object => ({ object, parent: object.parent, visible: object.visible,
      position: object.position.toArray(), scale: object.scale.toArray(), matrix: object.matrix.toArray(), children: [...object.children] }));
    const selectable = hits.filter(hit => visibleWaveFieldHit(hit.object, root));
    expect([...new Set(selectable.map(hit => hit.object.userData.waveFieldSection))], 'W1_PICK_CURRENT_VISIBLE_EVENT_SIDE').toEqual(['section:after:lens']);
    expect(visibleWaveFieldHit(before, root)).toBe(false); expect(visibleWaveFieldHit(after, root)).toBe(true); expect(visibleWaveFieldHit(foreign, root)).toBe(false);
    for (const snapshot of original) {
      expect(snapshot.object.parent).toBe(snapshot.parent); expect(snapshot.object.visible).toBe(snapshot.visible);
      expect(snapshot.object.position.toArray()).toEqual(snapshot.position); expect(snapshot.object.scale.toArray()).toEqual(snapshot.scale);
      expect(snapshot.object.matrix.toArray()).toEqual(snapshot.matrix); expect(snapshot.object.children).toEqual(snapshot.children);
    }
    layer.visible = false; expect(visibleWaveFieldHit(after, root), 'W1_PICK_REJECTS_HIDDEN_PARENT').toBe(false);
    layer.visible = true; root.visible = false; expect(visibleWaveFieldHit(after, root), 'W1_PICK_REJECTS_HIDDEN_ATTACHED_ROOT').toBe(false);
    root.visible = true; before.visible = true; after.visible = false;
    expect([...new Set(hits.filter(hit => visibleWaveFieldHit(hit.object, root)).map(hit => hit.object.userData.waveFieldSection))]).toEqual(['section:before:lens']);
    geometry.dispose(); material.dispose();
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
