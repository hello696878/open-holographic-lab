/** Mounted W2 equipment and returned geometry only. Mesh picking is interaction, never optics. */
import * as THREE from 'three';
import { W2_APPARATUS_CAP, assertGeometricScene, type GeometricScene, type GeometricTraceResult,
  type RoutingSurfaceFrame, type RoutingVector } from './geometric_routing_contracts';

export const W2_WORLD_SCALE = 10;
export interface GeometricRoutingApparatus {
  readonly group: THREE.Group; readonly ownedBytes: number; readonly geometryBytes: number; readonly labelBytes: number;
  select(id: string): void; setDisplay(group: THREE.Group | null): void; framingBounds(id?: string): THREE.Box3;
  setLabelsVisible(visible: boolean): void;
  updateLabels(camera: THREE.PerspectiveCamera, width: number, height: number): void;
  snapshot(): object; dispose(): void;
}
export interface GeometricRoutingDisplay {
  readonly group: THREE.Group; readonly result: GeometricTraceResult; readonly ownedBytes: number; readonly geometryBytes: number;
  selectBranch(id: string | null): void; selectHit(id: string | null): void; framingBounds(): THREE.Box3; snapshot(): object; dispose(): void;
}
interface Owner {
  group: THREE.Group; geometry: Set<THREE.BufferGeometry>; materials: Set<THREE.Material>; disposed: boolean;
}
function geometryBytes(geometries: Set<THREE.BufferGeometry>): number {
  const buffers = new Set<ArrayBufferLike>();
  for (const geometry of geometries) {
    if (geometry.index) buffers.add(geometry.index.array.buffer);
    for (const attribute of Object.values(geometry.attributes)) buffers.add(attribute instanceof THREE.InterleavedBufferAttribute ? attribute.data.array.buffer : attribute.array.buffer);
  }
  return [...buffers].reduce((sum, buffer) => sum + buffer.byteLength, 0);
}
function dispose(owner: Owner): void {
  if (owner.disposed) return; owner.disposed = true; owner.group.removeFromParent(); owner.group.clear();
  owner.geometry.forEach(geometry => geometry.dispose()); owner.materials.forEach(material => material.dispose()); owner.geometry.clear(); owner.materials.clear();
}
function ownedGeometry<T extends THREE.BufferGeometry>(owner: Owner, geometry: T): T { owner.geometry.add(geometry); return geometry; }
function material<T extends THREE.Material>(owner: Owner, item: T): T { owner.materials.add(item); return item; }
function standard(owner: Owner, color: string, metalness = .25, roughness = .5): THREE.MeshStandardMaterial {
  return material(owner, new THREE.MeshStandardMaterial({ color, metalness, roughness, side: THREE.DoubleSide }));
}
function mesh(parent: THREE.Group, geometry: THREE.BufferGeometry, item: THREE.Material, position: readonly number[], scale: readonly number[]): THREE.Mesh {
  const result = new THREE.Mesh(geometry, item); result.position.set(position[0], position[1], position[2]); result.scale.set(scale[0], scale[1], scale[2]); parent.add(result); return result;
}
function world(point: RoutingVector): THREE.Vector3 { return new THREE.Vector3(...point).multiplyScalar(W2_WORLD_SCALE); }
/** Only a display conversion. The authoritative returned frame is preferred when available. */
export function routingDisplayMatrix(rotation: RoutingVector, frame?: RoutingSurfaceFrame): THREE.Matrix4 {
  if (frame) return new THREE.Matrix4().makeBasis(new THREE.Vector3(...frame.u), new THREE.Vector3(...frame.v), new THREE.Vector3(...frame.n));
  return new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(rotation[0], rotation[1], rotation[2], 'ZYX'));
}
export function createGeometricRoutingApparatus(scene: GeometricScene, options: {
  readonly frames?: readonly RoutingSurfaceFrame[]; readonly labelHost?: HTMLElement; readonly onSelect?: (id: string) => void;
} = {}): GeometricRoutingApparatus {
  assertGeometricScene(scene);
  const owner: Owner = { group: new THREE.Group(), geometry: new Set(), materials: new Set(), disposed: false };
  owner.group.name = 'W2 mounted geometric apparatus'; owner.group.userData.w2Apparatus = true;
  const components = new Map<string, THREE.Group>(), selection = new Map<string, THREE.Mesh>();
  const labels: { id: string; node: HTMLButtonElement; anchor: THREE.Vector3; bounds: { left: number; right: number; top: number; bottom: number } | null }[] = [];
  let selected = 'source', display: THREE.Group | null = null, labelReservation = 0, nodeCount = 0, labelsVisible = true;
  let boardFloorY = scene.source.origin_m[1] * 10 - .8;
  const box = ownedGeometry(owner, new THREE.BoxGeometry(1, 1, 1)), cylinder = ownedGeometry(owner, new THREE.CylinderGeometry(1, 1, 1, 20));
  const circle = ownedGeometry(owner, new THREE.CircleGeometry(1, 32));
  const plane = scene.elements.some(element => element.aperture.kind === 'rectangle') ? ownedGeometry(owner, new THREE.PlaneGeometry(1, 1)) : null;
  const ring = ownedGeometry(owner, new THREE.TorusGeometry(1, .055, 8, 32));
  const dark = standard(owner, '#263940', .55, .35), steel = standard(owner, '#7f959d', .8, .28), black = standard(owner, '#15252c', .15, .6);
  const silver = standard(owner, '#c8dfe6', .92, .18), receiver = standard(owner, '#214c58', .4, .35);
  const sourceBody = standard(owner, '#286d78', .65, .28), amber = standard(owner, '#d3a755', .5, .4);
  const splitter = material(owner, new THREE.MeshStandardMaterial({ color: '#6bc4ce', transparent: true, opacity: .48, roughness: .25, metalness: .12, side: THREE.DoubleSide, depthWrite: false }));
  const selectedMaterial = material(owner, new THREE.MeshBasicMaterial({ color: '#4cdbcc', transparent: true, opacity: .75, side: THREE.DoubleSide, depthWrite: false }));
  const frames = new Map(options.frames?.map(frame => [frame.element_id, frame]) ?? []);
  // The old renderer uses unlit surfaces. These lights are local to W2 and own
  // no shadow maps; they disappear with this group and cannot alter old modes.
  const fill = new THREE.HemisphereLight('#e3f1f4', '#20333d', 2.1), key = new THREE.DirectionalLight('#fff1d7', 2.6);
  key.position.copy(world(scene.source.origin_m)).add(new THREE.Vector3(-3, 6, 4)); key.target.position.copy(world(scene.source.origin_m));
  owner.group.add(fill, key, key.target);
  function label(id: string, title: string, anchor: THREE.Vector3): void {
    if (!options.labelHost) return;
    const node = document.createElement('button'); node.type = 'button'; node.className = 'w2-label'; node.dataset.w2ElementId = id;
    node.textContent = title; node.setAttribute('aria-label', `Select ${title}`); node.hidden = true;
    node.addEventListener('click', () => options.onSelect?.(id)); options.labelHost.append(node);
    labels.push({ id, node, anchor, bounds: null }); labelReservation += 512 + title.length * 2;
  }
  function stand(assembly: THREE.Group, size: number): void {
    const height = assembly.position.y - boardFloorY;
    const postHeight = Math.max(.1, height - .12);
    mesh(assembly, box, dark, [0, -height + .06, 0], [Math.max(.45, size + .25), .12, .45]);
    mesh(assembly, cylinder, steel, [0, -height + .12 + postHeight / 2, .11], [.045, postHeight, .045]);
    mesh(assembly, cylinder, dark, [0, -.12, .11], [.09, .16, .09]);
  }
  function assembly(id: string, at: RoutingVector): THREE.Group {
    const item = new THREE.Group(); item.position.copy(world(at)); item.userData.w2ElementId = id; item.userData.identity = id;
    components.set(id, item); owner.group.add(item); return item;
  }
  function mark(assembly: THREE.Group, size: number): void {
    const halo = mesh(assembly, ring, selectedMaterial, [0, 0, 0], [size + .09, size + .09, size + .09]); halo.visible = false;
    halo.userData.w2SelectionDecoration = true; selection.set(assembly.userData.w2ElementId, halo);
  }
  function cleanup(): void {
    if (owner.disposed) return; display?.removeFromParent(); display = null; labels.forEach(label => label.node.remove()); dispose(owner);
  }
  try {
    // A schematic mounting board only. Its surface/holes never enter optical
    // records or picking identity, and its dimensions are visibility aids.
    const centers = [scene.source.origin_m, ...scene.elements.map(element => element.pose.position_m)].map(world);
    const boardBounds = new THREE.Box3().setFromPoints(centers), middle = boardBounds.getCenter(new THREE.Vector3());
    const boardSize = boardBounds.getSize(new THREE.Vector3()), boardWidth = Math.max(4, boardSize.x + 1.4), boardDepth = Math.max(4.8, boardSize.z + 1.6);
    const floorY = Math.min(...centers.map(point => point.y)) - .8; boardFloorY = floorY;
    mesh(owner.group, box, dark, [middle.x, floorY - .055, middle.z], [boardWidth, .1, boardDepth]).userData.w2DecorativeBoard = true;
    const nx = Math.min(24, Math.max(3, Math.floor(boardWidth / .3))), nz = Math.min(24, Math.max(3, Math.floor(boardDepth / .3))), dots = new Float32Array(nx * nz * 3);
    let cursor = 0; for (let x = 0; x < nx; x++) for (let z = 0; z < nz; z++) {
      dots[cursor++] = middle.x + (x / (nx - 1) - .5) * (boardWidth - .35); dots[cursor++] = floorY + .004;
      dots[cursor++] = middle.z + (z / (nz - 1) - .5) * (boardDepth - .35);
    }
    const holeGeometry = ownedGeometry(owner, new THREE.BufferGeometry()); holeGeometry.setAttribute('position', new THREE.BufferAttribute(dots, 3));
    const holes = new THREE.Points(holeGeometry, material(owner, new THREE.PointsMaterial({ color: '#0c1c25', size: .035, sizeAttenuation: true })));
    holes.userData.w2DecorativeBoard = true; owner.group.add(holes);
    const source = assembly('source', scene.source.origin_m), orientation = new THREE.Group(); source.add(orientation);
    orientation.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), new THREE.Vector3(...scene.source.direction).normalize());
    const barrel = mesh(orientation, cylinder, sourceBody, [0, 0, -.26], [.14, .5, .14]); barrel.rotation.x = Math.PI / 2;
    const collar = mesh(orientation, cylinder, dark, [0, 0, -.035], [.17, .09, .17]); collar.rotation.x = Math.PI / 2;
    mesh(orientation, circle, amber, [0, 0, .012], [.085, .085, 1]);
    stand(source, .35); mark(source, .22); label('source', 'LASER / ONE RAY', source.position.clone().add(new THREE.Vector3(0, .42, 0)));
    for (const element of scene.elements) {
      const item = assembly(element.id, element.pose.position_m), optical = new THREE.Group(); item.add(optical);
      optical.quaternion.setFromRotationMatrix(routingDisplayMatrix(element.pose.rotation_xyz_rad, frames.get(element.id)));
      const radius = element.aperture.kind === 'disk' ? element.aperture.radius_m * 10 : Math.hypot(element.aperture.width_m, element.aperture.height_m) * 5;
      const width = element.aperture.kind === 'disk' ? radius * 2 : element.aperture.width_m * 10;
      const height = element.aperture.kind === 'disk' ? radius * 2 : element.aperture.height_m * 10;
      const faceMaterial = element.kind === 'mirror' ? silver : element.kind === 'ideal_splitter_50_50' ? splitter : element.kind === 'beam_stop' ? black : receiver;
      if (element.aperture.kind === 'disk') {
        mesh(optical, circle, faceMaterial, [0, 0, 0], [radius, radius, 1]);
        mesh(optical, ring, element.kind === 'ideal_splitter_50_50' ? steel : dark, [0, 0, 0], [radius + .04, radius + .04, radius + .04]);
      } else {
        mesh(optical, plane!, faceMaterial, [0, 0, 0], [width, height, 1]);
        for (const sign of [-1, 1]) { mesh(optical, box, dark, [sign * (width / 2 + .025), 0, 0], [.05, height + .1, .07]); mesh(optical, box, dark, [0, sign * (height / 2 + .025), 0], [width + .1, .05, .07]); }
      }
      if (element.kind === 'receiver') {
        mesh(optical, ring, amber, [0, 0, .007], [Math.min(width, height) * .24, Math.min(width, height) * .24, Math.min(width, height) * .24]);
        mesh(item, box, dark, [radius + .18, -.06, 0], [.15, .18, .13]);
      } else if (element.kind === 'beam_stop') {
        mesh(optical, box, black, [0, 0, -.055], [width * .82, height * .82, .1]);
      } else {
        for (const x of [-1, 1]) { const screw = mesh(optical, cylinder, steel, [x * (width / 2 + .08), -.1, -.04], [.035, .11, .035]); screw.rotation.x = Math.PI / 2; }
      }
      stand(item, width); mark(item, radius + .04);
      const title = `${element.id} / ${element.kind === 'ideal_splitter_50_50' ? 'IDEAL 50:50' : element.kind === 'beam_stop' ? 'STOP' : element.kind.toUpperCase()}`;
      label(element.id, title, item.position.clone().add(new THREE.Vector3(0, height / 2 + .35, 0)));
    }
    owner.group.traverse(object => {
      nodeCount++;
      for (let at: THREE.Object3D | null = object; at; at = at.parent) if (at.userData.w2ElementId) { object.userData.w2ElementId = at.userData.w2ElementId; object.userData.identity = at.userData.w2ElementId; break; }
    });
  } catch (error) { cleanup(); throw error; }
  const bytes = geometryBytes(owner.geometry), metadataReservation = nodeCount * 256 + owner.materials.size * 256;
  if (bytes + labelReservation + metadataReservation > W2_APPARATUS_CAP) { cleanup(); throw new Error('W2 apparatus exceeds its bounded ownership reservation.'); }
  function select(id: string): void {
    if (!components.has(id)) throw new Error('Unknown geometric component selection'); selected = id; selection.forEach((halo, key) => { halo.visible = key === id; });
    labels.forEach(label => { label.node.classList.toggle('selected', label.id === id); label.node.setAttribute('aria-pressed', String(label.id === id)); });
  }
  select('source');
  return {
    group: owner.group, get geometryBytes() { return owner.disposed ? 0 : bytes; }, get labelBytes() { return owner.disposed ? 0 : labelReservation; },
    get ownedBytes() { return owner.disposed ? 0 : bytes + labelReservation + metadataReservation; }, select,
    setLabelsVisible(visible) { labelsVisible = visible; if (!visible) labels.forEach(label => { label.node.hidden = true; }); },
    setDisplay(group) { if (owner.disposed) throw new Error('W2 apparatus disposed'); if (display === group) return; display?.removeFromParent(); display = group; if (group) owner.group.add(group); },
    framingBounds(id) {
      if (owner.disposed || id && !components.has(id)) throw new Error('W2 framing destination unavailable');
      owner.group.updateWorldMatrix(true, true); const bounds = new THREE.Box3();
      for (const component of id ? [components.get(id)!] : components.values()) bounds.expandByObject(component, true);
      if (!id && display) bounds.expandByObject(display, true); return bounds;
    },
    updateLabels(camera, width, height) {
      if (owner.disposed || !labelsVisible) return; owner.group.updateWorldMatrix(true, true); camera.updateMatrixWorld(true); const occupied: { left: number; right: number; top: number; bottom: number }[] = [];
      for (const label of [...labels].sort((a, b) => Number(b.id === selected) - Number(a.id === selected))) {
        const projected = label.anchor.clone().applyMatrix4(owner.group.matrixWorld).project(camera), depth = -label.anchor.clone().applyMatrix4(owner.group.matrixWorld).applyMatrix4(camera.matrixWorldInverse).z;
        label.bounds = null; label.node.hidden = depth <= camera.near || projected.z < -1 || projected.z > 1 || width < 80 || height < 60; if (label.node.hidden) continue;
        const w = Math.min(180, Math.max(100, label.node.textContent!.length * 6.4)), h = 24;
        const x = Math.max(8, Math.min(width - w - 8, (projected.x + 1) * width / 2 - w / 2)), initial = (1 - projected.y) * height / 2;
        let at: number | null = null;
        for (const offset of [0, -28, 28, -56, 56, -84, 84, -112, 112]) {
          const y = Math.max(8, Math.min(height - h - 8, initial + offset));
          if (!occupied.some(b => x < b.right + 3 && x + w + 3 > b.left && y < b.bottom + 3 && y + h + 3 > b.top)) { at = y; break; }
        }
        if (at === null) { label.node.hidden = true; continue; }
        label.node.style.left = `${x}px`; label.node.style.top = `${at}px`; label.node.style.width = `${w}px`;
        label.bounds = { left: x, right: x + w, top: at, bottom: at + h }; occupied.push(label.bounds);
      }
    },
    snapshot() { return { selected, disposed: owner.disposed, componentCount: components.size, geometryBytes: owner.disposed ? 0 : bytes,
      labelBytes: owner.disposed ? 0 : labelReservation, metadataReservationBytes: owner.disposed ? 0 : metadataReservation,
      ownedBytes: owner.disposed ? 0 : bytes + labelReservation + metadataReservation, displayAttached: !!display,
      worldMapping: '10 * SI metres, right-handed Y-up, isotropic', housings: 'decorative/nonblocking', opticalPicking: false,
      components: [...components].map(([id, group]) => ({ id, position_m: group.position.toArray().map(n => n / 10) })),
      labels: labels.map(label => ({ id: label.id, visible: !label.node.hidden, bounds: label.bounds })) }; }, dispose: cleanup,
  };
}

/** Draws exactly the returned endpoints. Thickness is a visibility aid, independent of weight. */
export function prepareGeometricRoutingDisplay(result: GeometricTraceResult): GeometricRoutingDisplay {
  const owner: Owner = { group: new THREE.Group(), geometry: new Set(), materials: new Set(), disposed: false };
  owner.group.name = 'W2 calculated ideal geometric paths'; owner.group.userData.w2CalculatedDisplay = true;
  const cylinder = ownedGeometry(owner, new THREE.CylinderGeometry(1, 1, 1, 10)), sphere = ownedGeometry(owner, new THREE.SphereGeometry(1, 10, 6));
  const routeMeshes: { branch: string; mesh: THREE.Mesh; base: THREE.Color; glow: boolean }[] = [], hitMeshes = new Map<string, THREE.Mesh>();
  let selectedBranch: string | null = null, selectedHit: string | null = null, nodeCount = 0;
  try {
    for (const segment of result.segments) {
      const start = world(segment.start_m), end = world(segment.end_m), delta = end.clone().sub(start), length = delta.length();
      if (!length) continue;
      const color = segment.branch_id.endsWith('.R') ? '#4fcac0' : '#eab35c';
      for (const glow of [false, true]) {
        const mat = material(owner, new THREE.MeshBasicMaterial({ color, transparent: glow, opacity: glow ? .12 : .95, depthWrite: !glow, toneMapped: false }));
        const item = new THREE.Mesh(cylinder, mat); item.position.copy(start).add(end).multiplyScalar(.5);
        item.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), delta.divideScalar(length)); item.scale.set(glow ? .026 : .009, length, glow ? .026 : .009);
        item.userData.w2BranchId = segment.branch_id; item.userData.w2SegmentId = segment.id; item.userData.visibilityAid = true;
        owner.group.add(item); routeMeshes.push({ branch: segment.branch_id, mesh: item, base: new THREE.Color(color), glow });
      }
    }
    for (const hit of result.hits) {
      const mat = material(owner, new THREE.MeshBasicMaterial({ color: '#ffdda0', toneMapped: false, depthTest: false }));
      const item = new THREE.Mesh(sphere, mat); item.position.copy(world(hit.position_m)); item.scale.setScalar(.034); item.renderOrder = 3;
      item.userData.w2HitId = hit.id; item.userData.w2ElementId = hit.element_id; item.userData.identity = hit.element_id; owner.group.add(item); hitMeshes.set(hit.id, item);
    }
    for (const terminal of result.terminals.filter(terminal => terminal.category === 'escaped' || terminal.category === 'resource_truncated')) {
      const mat = material(owner, new THREE.MeshBasicMaterial({ color: terminal.category === 'escaped' ? '#9dacb6' : '#ec8875', wireframe: true, toneMapped: false }));
      const item = new THREE.Mesh(sphere, mat); item.position.copy(world(terminal.position_m)); item.scale.setScalar(.05); item.userData.w2TerminalCategory = terminal.category;
      item.userData.w2BranchId = terminal.branch_id; owner.group.add(item);
    }
    owner.group.traverse(() => { nodeCount++; });
  } catch (error) { dispose(owner); throw error; }
  const bytes = geometryBytes(owner.geometry), metadata = nodeCount * 384 + owner.materials.size * 256;
  return { group: owner.group, result, get ownedBytes() { return owner.disposed ? 0 : bytes + metadata; }, get geometryBytes() { return owner.disposed ? 0 : bytes; },
    selectBranch(id) {
      if (id !== null && !result.branches.some(branch => branch.id === id)) throw new Error('Unknown calculated branch'); selectedBranch = id;
      routeMeshes.forEach(entry => { const mat = entry.mesh.material as THREE.MeshBasicMaterial; mat.color.copy(entry.base); if (id === entry.branch) mat.color.lerp(new THREE.Color('#ffffff'), .32);
        mat.opacity = entry.glow ? .12 : .95; });
    },
    selectHit(id) { if (id !== null && !hitMeshes.has(id)) throw new Error('Unknown calculated hit'); selectedHit = id; hitMeshes.forEach((mesh, key) => { mesh.scale.setScalar(key === id ? .055 : .034); }); },
    framingBounds() { owner.group.updateWorldMatrix(true, true); return new THREE.Box3().setFromObject(owner.group, true); },
    snapshot() { return { disposed: owner.disposed, selectedBranch, selectedHit, segmentCount: result.segments.length, hitCount: result.hits.length,
      ownedBytes: owner.disposed ? 0 : bytes + metadata, geometryBytes: owner.disposed ? 0 : bytes, metadataReservationBytes: owner.disposed ? 0 : metadata,
      requestId: result.request_id, sceneSha256: result.scene_sha256, endpoints: result.segments.map(segment => ({ id: segment.id, branch: segment.branch_id, start_m: segment.start_m, end_m: segment.end_m })),
      visibleBranchIds: [...new Set(result.segments.map(segment => segment.branch_id))], thickness: 'constant visibility aid; not physical width or relative weight' }; },
    dispose() { dispose(owner); },
  };
}
