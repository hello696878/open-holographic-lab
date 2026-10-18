/** Mounted linear train. World x=1000x_m, y=1−1000y_m, z=100z_m; unequal scales are presentation only. */
import * as THREE from 'three';
import type { Experiment } from './contracts';
import { W1_APPARATUS_CAP, requireWaveFieldExperiment } from './wave_field_contracts';
export interface WaveFieldApparatus {
  readonly group: THREE.Group; readonly ownedBytes: number; readonly geometryBytes: number; readonly labelBytes: number;
  /** Three's global Sprite quad is borrowed and can already be charged by retained R03. */
  readonly borrowedGeometryBuffers: readonly ArrayBufferLike[]; readonly borrowedGeometryBytes: number;
  setDisplay(group: THREE.Group | null, detector: THREE.DataTexture | null): void;
  select(id: string): void; framingBounds(id?: string): THREE.Box3;
  updateLabels(camera: THREE.PerspectiveCamera, width: number, height: number): void;
  snapshot(): object; dispose(): void;
}
export function createWaveFieldApparatus(experiment: Experiment): WaveFieldApparatus {
  requireWaveFieldExperiment(experiment);
  const dimensions = [experiment.grid.nx * experiment.grid.dx * 1000, experiment.grid.ny * experiment.grid.dy * 1000,
    experiment.observation.z_m * 100, ...experiment.components.map(component => component.z_m * 100)];
  const aperture = experiment.components[0];
  if (aperture.kind === 'circular_aperture') dimensions.push(aperture.radius_m * 1000);
  else if (aperture.kind === 'rectangular_aperture') dimensions.push(aperture.width_m * 1000, aperture.height_m * 1000);
  if (dimensions.some(value => !Number.isFinite(value) || !Number.isFinite(Math.fround(value)) || value !== 0 && Math.fround(value) === 0))
    throw new Error('W1 physical geometry exceeds usable 3D arithmetic; settings were not resized or changed.');
  const group = new THREE.Group(), geometry = new Set<THREE.BufferGeometry>(), borrowed = new Set<THREE.BufferGeometry>(),
    materials = new Set<THREE.Material>(), textures = new Set<THREE.CanvasTexture>(), canvases: HTMLCanvasElement[] = [];
  const components = new Map<string, THREE.Group>(), halos = new Map<string, THREE.Mesh>();
  const labels: { id: string; sprite: THREE.Sprite; anchor: THREE.Vector3; canvas: HTMLCanvasElement; bounds: {left:number;right:number;top:number;bottom:number}|null }[] = [];
  const instances: THREE.InstancedMesh[] = [];
  let disposed = false, selected = 'source', attached: THREE.Group | null = null;
  const g = <T extends THREE.BufferGeometry>(value: T) => { geometry.add(value); return value; };
  const m = <T extends THREE.Material>(value: T) => { materials.add(value); return value; };
  const dark = m(new THREE.MeshStandardMaterial({ color: '#223846', metalness: .55, roughness: .35 }));
  const silver = m(new THREE.MeshStandardMaterial({ color: '#b9cbd1', metalness: .8, roughness: .28 }));
  const black = m(new THREE.MeshStandardMaterial({ color: '#09161d', roughness: .65 }));
  const glass = m(new THREE.MeshStandardMaterial({ color: '#74bfc9', metalness: .12, roughness: .16, transparent: true, opacity: .27, side: THREE.DoubleSide, depthWrite: false }));
  const unit = g(new THREE.BoxGeometry(1, 1, 1)), post = g(new THREE.CylinderGeometry(.055, .065, .72, 12));
  const ring = g(new THREE.TorusGeometry(.76, .075, 8, 48)), face = g(new THREE.CircleGeometry(.68, 48));
  function mesh(parent: THREE.Object3D, shape: THREE.BufferGeometry, material: THREE.Material, position: [number, number, number], scale: [number, number, number] = [1, 1, 1]) {
    const value = new THREE.Mesh(shape, material); value.position.set(...position); value.scale.set(...scale); parent.add(value); return value;
  }
  function assembly(id: string, z: number) {
    const value = new THREE.Group(); value.userData.waveFieldComponent = id; value.position.z = z * 100; group.add(value); components.set(id, value);
    mesh(value, unit, dark, [0, .08, 0], [.82, .13, .68]); mesh(value, post, silver, [0, .48, 0]);
    const halo = mesh(value, g(new THREE.TorusGeometry(.62, .021, 6, 40)), m(new THREE.MeshBasicMaterial({ color: '#e5c77f', toneMapped: false })), [0, .018, 0]);
    halo.rotation.x = Math.PI / 2; halo.userData.waveFieldFramingExcluded = true; halos.set(id, halo); return value;
  }
  function label(parent: THREE.Group, id: string, title: string, height = 2.05) {
    const canvas = document.createElement('canvas'); canvas.width = 128; canvas.height = 48; canvases.push(canvas);
    const context = canvas.getContext('2d'); if (!context) throw new Error('W1 mounted label canvas unavailable');
    context.fillStyle = '#6d8c99'; context.fillRect(0, 0, 128, 48); context.fillStyle = '#102632'; context.fillRect(2, 2, 124, 44);
    context.font = '600 25px system-ui'; context.textAlign = 'center'; context.textBaseline = 'middle'; context.fillStyle = '#eef5f4'; context.fillText(title, 64, 25, 120);
    const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace; textures.add(texture);
    const sprite = new THREE.Sprite(m(new THREE.SpriteMaterial({ map: texture, depthTest: false, depthWrite: false })));
    borrowed.add(sprite.geometry); sprite.position.set(0, height, 0); sprite.scale.set(.96, .36, 1); sprite.userData.identity = id;
    parent.add(sprite); labels.push({ id, sprite, anchor: sprite.position.clone(), canvas, bounds: null });
  }
  let detectorFace: THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial>;
  const cleanup = () => { if (disposed) return; disposed = true; attached?.removeFromParent(); attached = null;
    group.removeFromParent(); group.clear(); geometry.forEach(shape => shape.dispose()); materials.forEach(value => value.dispose()); textures.forEach(value => value.dispose());
    canvases.forEach(canvas => { canvas.width = canvas.height = 0; }); geometry.clear(); borrowed.clear(); materials.clear(); textures.clear(); };
  try {
    group.add(new THREE.HemisphereLight('#bde6f4', '#1a343c', 2.7));
    const key = new THREE.DirectionalLight('#edf9ff', 3.8); key.position.set(-5, 8, 4); group.add(key);
    const rim = new THREE.DirectionalLight('#76c0c8', 1.8); rim.position.set(4, 5, -6); group.add(rim);
    const end = experiment.observation.z_m * 100, tableLength = Math.max(end + 4, 5);
    mesh(group, unit, m(new THREE.MeshStandardMaterial({ color: '#132b36', metalness: .35, roughness: .62 })), [0, -.07, end / 2], [4.8, .15, tableLength]);
    mesh(group, unit, black, [0, -.19, end / 2], [4.9, .14, tableLength + .08]);
    const countZ = Math.min(96, Math.ceil(tableLength / .36)), countX = 11, holes = new THREE.InstancedMesh(g(new THREE.CylinderGeometry(.022, .022, .015, 8)), black, countZ * countX), matrix = new THREE.Matrix4();
    let at = 0; for (let row = 0; row < countZ; row++) for (let column = 0; column < countX; column++) {
      matrix.makeTranslation(-2 + column * .4, .015, end / 2 - tableLength / 2 + .2 + row * (tableLength - .4) / Math.max(countZ - 1, 1)); holes.setMatrixAt(at++, matrix);
    } group.add(holes); instances.push(holes);
    const source = assembly('source', 0);
    mesh(source, unit, dark, [0, 1, -.63], [.92, .64, 1.25]); mesh(source, unit, silver, [0, 1.34, -.65], [.85, .055, 1.2]);
    for (let index = 0; index < 7; index++) mesh(source, unit, silver, [0, 1.38, -1.13 + index * .16], [.73, .025, .035]);
    const barrel = mesh(source, g(new THREE.CylinderGeometry(.23, .23, .25, 24)), silver, [0, 1, -.115]); barrel.rotation.x = Math.PI / 2;
    mesh(source, g(new THREE.CircleGeometry(.18, 32)), m(new THREE.MeshBasicMaterial({ color: '#e9ad55', toneMapped: false })), [0, 1, 0]); label(source, 'source', 'LASER');
    const apertureSpec = experiment.components[0], aperture = assembly(apertureSpec.id, apertureSpec.z_m);
    mesh(aperture, ring, silver, [0, 1, 0]);
    if (apertureSpec.kind === 'circular_aperture') {
      const radius = apertureSpec.radius_m * 1000;
      mesh(aperture, g(new THREE.RingGeometry(radius, Math.max(.68, radius * 1.1), 48)), black, [0, 1, 0]);
    } else if (apertureSpec.kind === 'rectangular_aperture') {
      const w = apertureSpec.width_m * 1000, h = apertureSpec.height_m * 1000, ow = Math.max(1.36, w * 1.1), oh = Math.max(1.36, h * 1.1);
      mesh(aperture, unit, black, [-(ow + w) / 4, 1, 0], [(ow - w) / 2, oh, .025]);
      mesh(aperture, unit, black, [(ow + w) / 4, 1, 0], [(ow - w) / 2, oh, .025]);
      for (const sign of [-1, 1]) mesh(aperture, unit, black, [0, 1 + sign * (oh + h) / 4, 0], [w, (oh - h) / 2, .025]);
    } label(aperture, apertureSpec.id, 'APERTURE');
    const lensSpec = experiment.components[1], lens = assembly(lensSpec.id, lensSpec.z_m);
    mesh(lens, ring, dark, [0, 1, 0]); const lensRim = mesh(lens, ring, silver, [0, 1, .025]); lensRim.scale.setScalar(.88);
    mesh(lens, face, glass, [0, 1, 0]); mesh(lens, unit, dark, [.84, 1, 0], [.18, .2, .2]); label(lens, lensSpec.id, 'THIN LENS');
    const observation = assembly(experiment.observation.id, experiment.observation.z_m), width = experiment.grid.nx * experiment.grid.dx * 1000,
      height = experiment.grid.ny * experiment.grid.dy * 1000;
    mesh(observation, unit, dark, [0, 1, .16], [width + .22, height + .22, .27]);
    detectorFace = new THREE.Mesh(g(new THREE.PlaneGeometry(width, height)), m(new THREE.MeshBasicMaterial({ color: '#34515c', side: THREE.DoubleSide, toneMapped: false })));
    detectorFace.position.set(((experiment.grid.nx - 1) / 2 - Math.floor(experiment.grid.nx / 2)) * experiment.grid.dx * 1000,
      1 - ((experiment.grid.ny - 1) / 2 - Math.floor(experiment.grid.ny / 2)) * experiment.grid.dy * 1000, 0);
    detectorFace.userData.waveFieldDetector = true; observation.add(detectorFace); label(observation, experiment.observation.id, 'DETECTOR', 1 + height / 2 + .45);
    for (const [id, assembly] of components) assembly.traverse(object => { object.userData.identity = id; });
  } catch (error) { cleanup(); throw error; }
  const buffers = new Set<ArrayBufferLike>();
  [...geometry, ...borrowed].forEach(shape => { if (shape.index) buffers.add(shape.index.array.buffer); Object.values(shape.attributes).forEach(a => buffers.add(a.array.buffer)); });
  const borrowedSources = new Set<ArrayBufferLike>();
  for (const shape of borrowed) { if (shape.index) borrowedSources.add(shape.index.array.buffer);
    Object.values(shape.attributes).forEach(attribute => borrowedSources.add(attribute instanceof THREE.InterleavedBufferAttribute ? attribute.data.array.buffer : attribute.array.buffer)); }
  const borrowedBuffers = Object.freeze([...borrowedSources]), borrowedBytes = borrowedBuffers.reduce((n, buffer) => n + buffer.byteLength, 0);
  instances.forEach(instance => buffers.add(instance.instanceMatrix.array.buffer));
  const geometryBytes = [...buffers].reduce((n, buffer) => n + buffer.byteLength, 0), labelBytes = canvases.reduce((n, canvas) => n + canvas.width * canvas.height * 4, 0);
  if (geometryBytes + labelBytes > W1_APPARATUS_CAP) { cleanup(); throw new Error('W1 mounted resources exceed 512 KiB reservation'); }
  function select(id: string) { if (!components.has(id)) throw new Error('Unknown W1 component selection'); selected = id; halos.forEach((halo, key) => { halo.visible = id === key; }); }
  select('source');
  const projected = new THREE.Vector3(), point = new THREE.Vector3();
  return { group, get ownedBytes() { return disposed ? 0 : geometryBytes + labelBytes; }, get geometryBytes() { return disposed ? 0 : geometryBytes; },
    get labelBytes() { return disposed ? 0 : labelBytes; }, select,
    get borrowedGeometryBuffers() { return disposed ? Object.freeze([]) : borrowedBuffers; }, get borrowedGeometryBytes() { return disposed ? 0 : borrowedBytes; },
    setDisplay(display, texture) { if (disposed) throw new Error('W1 apparatus disposed'); if (display !== attached) { attached?.removeFromParent(); attached = display; if (display) group.add(display); }
      detectorFace.material.map = texture; detectorFace.material.color.set(texture ? '#ffffff' : '#34515c'); detectorFace.material.needsUpdate = true; },
    framingBounds(id) {
      if (disposed) throw new Error('W1 apparatus disposed'); if (id && !components.has(id)) throw new Error('Unknown W1 component');
      group.updateWorldMatrix(true, true); const bounds = new THREE.Box3(), part = new THREE.Box3();
      for (const component of id ? [components.get(id)!] : components.values()) component.traverse(object => {
        if (!(object instanceof THREE.Mesh) || object instanceof THREE.Sprite || object.userData.waveFieldFramingExcluded) return;
        if (!object.geometry.boundingBox) object.geometry.computeBoundingBox(); if (object.geometry.boundingBox) bounds.union(part.copy(object.geometry.boundingBox).applyMatrix4(object.matrixWorld));
      }); return bounds;
    },
    updateLabels(camera, width, height) {
      group.updateWorldMatrix(true, true); camera.updateMatrixWorld(true);
      const occupied: { left: number; right: number; top: number; bottom: number }[] = [];
      for (const label of [...labels].sort((a, b) => Number(b.id === selected) - Number(a.id === selected))) {
        label.bounds = null;
        point.copy(label.anchor); label.sprite.parent!.localToWorld(point); const depth = -point.clone().applyMatrix4(camera.matrixWorldInverse).z;
        projected.copy(point).project(camera); label.sprite.visible = depth > camera.near && projected.z >= -1 && projected.z <= 1;
        if (!label.sprite.visible) continue;
        const size = 25, pad = 5, pw = size * 128 / 48;
        const x = Math.max(pw / 2 + pad, Math.min(width - pw / 2 - pad, (projected.x + 1) * width / 2));
        let y = Math.max(size / 2 + pad, Math.min(height - size / 2 - pad, (1 - projected.y) * height / 2));
        const initialY = y;
        const overlaps = (at: number) => occupied.some(rect => x - pw / 2 - 3 < rect.right && x + pw / 2 + 3 > rect.left && at - size / 2 - 3 < rect.bottom && at + size / 2 + 3 > rect.top);
        // Move only labels in a bounded screen-space lane; exact mounted/field positions never move.
        for (const offset of [0, -32, 32, -64, 64, -96, 96]) {
          const candidate = initialY + offset; if (candidate >= size / 2 + pad && candidate <= height - size / 2 - pad && !overlaps(candidate)) { y = candidate; break; }
        }
        if (overlaps(y)) { label.sprite.visible = false; continue; }
        projected.set(2 * x / width - 1, 1 - 2 * y / height, projected.z).unproject(camera); label.sprite.position.copy(label.sprite.parent!.worldToLocal(projected));
        const wh = 2 * depth * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) * size / height; label.sprite.scale.set(wh * 128 / 48, wh, 1);
        label.bounds = { left: x - pw / 2 - 3, right: x + pw / 2 + 3, top: y - size / 2 - 3, bottom: y + size / 2 + 3 }; occupied.push(label.bounds);
      }
    },
    snapshot() { return { disposed, selected, componentCount: components.size, ownedBytes: disposed ? 0 : geometryBytes + labelBytes,
      geometryBytes: disposed ? 0 : geometryBytes, labelBytes: disposed ? 0 : labelBytes,
      borrowedGeometryBytes: disposed ? 0 : borrowedBytes, borrowedGeometryCount: borrowed.size,
      components: [...components].map(([id, item]) => ({ id, z_m: item.position.z / 100, position: item.position.toArray() })),
      displayAttached: attached !== null, detectorTextureAttached: detectorFace.material.map !== null,
      labels: labels.map(label => ({ id: label.id, visible: label.sprite.visible, pixelBounds: label.bounds })),
      worldMapping: { x: '1000*x_m', y: '1-1000*y_m', z: '100*z_m' }, mountedGeometry: 'schematic dimensions; exact longitudinal centers', computedRays: false }; },
    dispose: cleanup };
}
