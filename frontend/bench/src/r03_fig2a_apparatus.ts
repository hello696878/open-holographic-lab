/** Original mounted apparatus. All distances/routes are functional design, never computed rays. */
import * as THREE from 'three';
import { R03_APPARATUS_CAP } from './r03_fig2a_display';
export const R03_COMPONENT_LABELS: Readonly<Record<string, string>> = Object.freeze({ source: '光源 · Source', input_hwp: '輸入準備',
  router: '路由 · UNKNOWN', slm: '相位調制器 · SLM', qwp: '四分之一波片 · QWP', hwp: '半波片 · HWP', measurement: '統計讀值 · Readout' });
const SHORT_LABELS: Readonly<Record<string, string>> = Object.freeze({ source: 'D SOURCE', input_hwp: 'PREP', router: 'UNKNOWN',
  slm: 'SLM', qwp: 'QWP', hwp: 'HWP', measurement: 'READOUT' });
export interface R03Apparatus { readonly group: THREE.Group; readonly ownedBytes: number; readonly geometryBytes: number;
  readonly labelBytes: number; readonly geometryCount: number; select(id: string): void; setPhase(texture: THREE.DataTexture | null): void;
  setAngles(qwp: number, hwp: number): void; framingBounds(id?: string): THREE.Box3;
  updateLabels(camera: THREE.PerspectiveCamera, width: number, height: number): void; snapshot(): object; dispose(): void }
interface ApparatusLabel { id: string; canvas: HTMLCanvasElement; texture: THREE.CanvasTexture; sprite: THREE.Sprite;
  anchor: THREE.Vector3; rectangle: { left: number; right: number; top: number; bottom: number } | null }
interface FunctionalSegment { id: string; owners: readonly string[]; from: THREE.Vector3; to: THREE.Vector3; meshes: THREE.Mesh[] }
export function createR03Apparatus(): R03Apparatus {
  const group = new THREE.Group(), geometries = new Set<THREE.BufferGeometry>(), materials = new Set<THREE.Material>();
  // Sprite's quad is shared by Three itself. Count its retained source once, but never dispose that borrowed global geometry.
  const borrowedGeometries = new Set<THREE.BufferGeometry>();
  const textures = new Set<THREE.CanvasTexture>(), labels: HTMLCanvasElement[] = [], instances: THREE.InstancedMesh[] = [];
  const labelRecords = new Map<string, ApparatusLabel>(), segments: FunctionalSegment[] = [];
  const selectable = new Map<string, THREE.Group>(), markers = new Map<string, THREE.Group>(); let selected = 'slm', disposed = false;
  const geometry = <T extends THREE.BufferGeometry>(g: T): T => { geometries.add(g); return g; };
  const material = <T extends THREE.Material>(m: T): T => { materials.add(m); return m; };
  const metal = material(new THREE.MeshStandardMaterial({ color: '#c5d0d8', metalness: .74, roughness: .29 }));
  const dark = material(new THREE.MeshStandardMaterial({ color: '#2d3944', metalness: .42, roughness: .44 }));
  const teal = material(new THREE.MeshStandardMaterial({ color: '#70bdb9', metalness: .12, roughness: .26, transparent: true, opacity: .52 }));
  const black = material(new THREE.MeshStandardMaterial({ color: '#13212b', roughness: .7 }));
  const guideMaterial = material(new THREE.MeshBasicMaterial({ color: '#c59b58', transparent: true, opacity: .85, toneMapped: false }));
  const selectedGuideMaterial = material(new THREE.MeshBasicMaterial({ color: '#ffe0a0', toneMapped: false }));
  const unitBox = geometry(new THREE.BoxGeometry(1, 1, 1)), postGeometry = geometry(new THREE.CylinderGeometry(.055, .064, 1, 14));
  const baseGeometry = geometry(new THREE.BoxGeometry(.64, .08, .48));
  const torusGeometry = geometry(new THREE.TorusGeometry(.29, .055, 7, 36)), glassGeometry = geometry(new THREE.CircleGeometry(.25, 40));
  function mesh(parent: THREE.Object3D, shape: THREE.BufferGeometry, appearance: THREE.Material, position: number[], scale = [1, 1, 1]): THREE.Mesh {
    const value = new THREE.Mesh(shape, appearance); value.position.set(position[0], position[1], position[2]); value.scale.set(...scale as [number, number, number]); parent.add(value);
    let ancestor: THREE.Object3D | null = parent;
    while (ancestor && ancestor !== group) { if (ancestor.userData.r03Component) { value.userData.r03Assembly = true; break; } ancestor = ancestor.parent; }
    return value;
  }
  function component(id: string, x: number, z: number): THREE.Group { const item = new THREE.Group(); item.position.set(x, 0, z); item.userData.r03Component = id; group.add(item); selectable.set(id, item); return item; }
  function mount(parent: THREE.Object3D, footprint = 1): void { mesh(parent, baseGeometry, dark, [0, .1, 0], [footprint, 1, footprint]); mesh(parent, postGeometry, metal, [0, .43, 0], [1, .6, 1]); }
  function drawLabel(record: ApparatusLabel): void {
    const ctx = record.canvas.getContext('2d'); if (!ctx) throw new Error('Mounted apparatus label canvas unavailable');
    ctx.fillStyle = record.id === selected ? '#e6bf79' : '#6b8391'; ctx.fillRect(0, 0, 128, 48);
    ctx.fillStyle = '#142632'; ctx.fillRect(2, 2, 124, 44); ctx.font = '600 28px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = record.id === selected ? '#ffe0a0' : '#eef4f7'; ctx.fillText(SHORT_LABELS[record.id], 64, 25, 120); record.texture.needsUpdate = true;
  }
  function label(parent: THREE.Group, id: string, y = 1.4, z = 0): void {
    const canvas = document.createElement('canvas'); canvas.width = 128; canvas.height = 48; labels.push(canvas);
    const ctx = canvas.getContext('2d'); if (!ctx) throw new Error('Mounted apparatus label canvas unavailable');
    const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace; textures.add(texture);
    const sprite = new THREE.Sprite(material(new THREE.SpriteMaterial({ map: texture, depthTest: id !== selected, transparent: true, depthWrite: false })));
    borrowedGeometries.add(sprite.geometry);
    sprite.position.set(0, y, z); sprite.scale.set(.8, .3, 1); sprite.userData.r03Label = id; parent.add(sprite);
    const record = { id, canvas, texture, sprite, anchor: new THREE.Vector3(0, y, z), rectangle: null }; labelRecords.set(id, record); drawLabel(record);
  }
  let phaseFace: THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial>;
  try {
    group.add(new THREE.HemisphereLight('#d5f3ff', '#284333', 2.6));
    const light = new THREE.DirectionalLight('#ffffff', 3.3); light.position.set(-3, 8, 5); group.add(light);
    const rim = new THREE.DirectionalLight('#80cbbf', 1.5); rim.position.set(4, 3, -5); group.add(rim);
    const table = mesh(group, unitBox, material(new THREE.MeshStandardMaterial({ color: '#102631', metalness: .2, roughness: .77 })), [.5, -.055, -.12], [9.9, .12, 5.7]); table.userData.r03Decoration = 'table';
    const tableEdge = mesh(group, unitBox, black, [.5, -.15, -.12], [10, .12, 5.8]); tableEdge.userData.r03Decoration = 'table';
    const hole = geometry(new THREE.CylinderGeometry(.027, .027, .014, 9));
    const holes = new THREE.InstancedMesh(hole, black, 24 * 13), matrix = new THREE.Matrix4(); let n = 0;
    for (let x = 0; x < 24; x++) for (let z = 0; z < 13; z++) { matrix.makeTranslation(-4.1 + x * .4, .013, -2.5 + z * .4); holes.setMatrixAt(n++, matrix); }
    holes.userData.r03Decoration = 'breadboard-holes'; group.add(holes); instances.push(holes);
    const source = component('source', -.7, -2); mount(source);
    mesh(source, unitBox, dark, [0, .83, -.1], [.64, .52, 1.05]); mesh(source, unitBox, metal, [0, 1.08, -.12], [.58, .045, .94]);
    for (let i = 0; i < 6; i++) mesh(source, unitBox, metal, [0, 1.07, -.48 + i * .14], [.46, .016, .027]);
    const sourceBarrel = mesh(source, geometry(new THREE.CylinderGeometry(.18, .18, .18, 24)), metal, [0, .83, .48]); sourceBarrel.rotation.x = Math.PI / 2;
    const sourceAperture = mesh(source, glassGeometry, teal, [0, .83, .58]); sourceAperture.scale.setScalar(.62);
    mesh(source, geometry(new THREE.TorusGeometry(.143, .018, 6, 28)), black, [0, .83, .588]); label(source, 'source', 1.42, -.25);
    const input = component('input_hwp', -.7, -.83); mount(input);
    mesh(input, torusGeometry, metal, [0, .83, 0]); mesh(input, glassGeometry, teal, [0, .83, .006]);
    // Input preparation is explanatory: no historical HWP angle is implied by a moving axis mark.
    label(input, 'input_hwp', 1.36, -.15);
    const router = component('router', -.7, .15); mount(router);
    const connector = mesh(router, unitBox, dark, [0, .83, 0], [.46, .4, .46]); connector.userData.r03UnknownConnector = true;
    mesh(router, unitBox, metal, [0, 1.04, 0], [.42, .035, .42]); label(router, 'router', 1.34, .14);
    const slm = component('slm', -3, .15); mount(slm, 1.65);
    mesh(slm, unitBox, dark, [0, 1.02, 0], [.25, 1.35, 1.47]); mesh(slm, unitBox, metal, [.135, 1.02, 0], [.035, 1.23, 1.35]);
    mesh(slm, unitBox, black, [.158, 1.02, 0], [.025, 1.13, 1.22]);
    phaseFace = new THREE.Mesh(geometry(new THREE.PlaneGeometry(1.04, 1.04)), material(new THREE.MeshBasicMaterial({ color: '#345c65', side: THREE.DoubleSide, toneMapped: false })));
    phaseFace.rotation.y = Math.PI / 2; phaseFace.position.set(.177, 1.02, 0); phaseFace.userData.r03Assembly = true; phaseFace.userData.r03PhaseFace = true; slm.add(phaseFace);
    const screwGeometry = geometry(new THREE.CylinderGeometry(.027, .027, .018, 9));
    for (const y of [.48, 1.56]) for (const z of [-.6, .6]) { const screw = mesh(slm, screwGeometry, black, [.16, y, z]); screw.rotation.z = Math.PI / 2; }
    label(slm, 'slm', 1.97, 0);
    const cable = new THREE.Line(geometry(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-3, .9, -.55), new THREE.Vector3(-3.38, .45, -.8), new THREE.Vector3(-3.5, .08, -1.15)])), material(new THREE.LineBasicMaterial({ color: '#527783', linewidth: 2 }))); group.add(cable);
    function waveplate(id: 'qwp' | 'hwp', x: number): void {
      const plate = component(id, x, .15); mount(plate); const ring = mesh(plate, torusGeometry, dark, [0, .83, 0]); ring.rotation.y = Math.PI / 2;
      const rim = mesh(plate, torusGeometry, metal, [.018, .83, 0]); rim.rotation.y = Math.PI / 2; rim.scale.setScalar(.84);
      const glass = mesh(plate, glassGeometry, teal, [.006, .83, 0]); glass.rotation.y = Math.PI / 2;
      const axis = new THREE.Group(); axis.position.set(.028, .83, 0); plate.add(axis);
      // Algebraic (+x,+y) maps to schematic (+z,-y), matching the declared +y-down view.
      // This is a display basis, not a reflected physical-frame transformation.
      mesh(axis, unitBox, material(new THREE.MeshBasicMaterial({ color: '#e5b66c', toneMapped: false })), [0, 0, 0], [.024, .032, .47]); markers.set(id, axis);
      mesh(plate, unitBox, dark, [.04, .85, .34], [.16, .13, .13]); label(plate, id, 1.4, 0);
    }
    waveplate('qwp', 1); waveplate('hwp', 2.3);
    const measurement = component('measurement', 3.8, .15); mount(measurement, 1.25);
    mesh(measurement, unitBox, dark, [0, .96, 0], [.9, .8, .95]); mesh(measurement, unitBox, metal, [.02, 1.36, 0], [.84, .04, .91]);
    mesh(measurement, unitBox, black, [.02, 1, .49], [.72, .57, .025]);
    mesh(measurement, unitBox, teal, [.02, 1.08, .51], [.55, .16, .015]);
    for (let i = 0; i < 3; i++) mesh(measurement, glassGeometry, teal, [-.18 + i * .18, .85, .52], [.14, .14, .14]);
    const aperture = mesh(measurement, torusGeometry, metal, [-.47, .94, 0]); aperture.rotation.y = Math.PI / 2; aperture.scale.setScalar(.75); label(measurement, 'measurement', 1.67, 0);
    const guideGeometry = geometry(new THREE.CylinderGeometry(.018, .018, 1, 8)), arrowGeometry = geometry(new THREE.ConeGeometry(.077, .19, 12));
    const guideUp = new THREE.Vector3(0, 1, 0);
    function segment(id: string, owners: readonly string[], a: number[], b: number[]): void {
      const from = new THREE.Vector3(...a as [number, number, number]), to = new THREE.Vector3(...b as [number, number, number]);
      const direction = to.clone().sub(from), length = direction.length(); direction.normalize();
      const tube = mesh(group, guideGeometry, guideMaterial, from.clone().add(to).multiplyScalar(.5).toArray(), [1, length, 1]);
      tube.quaternion.setFromUnitVectors(guideUp, direction); tube.userData.r03Decoration = 'functional-guide';
      const arrow = mesh(group, arrowGeometry, guideMaterial, from.clone().lerp(to, .64).toArray()); arrow.quaternion.copy(tube.quaternion); arrow.userData.r03Decoration = 'static-direction';
      segments.push({ id, owners, from, to, meshes: [tube, arrow] });
    }
    segment('source-preparation', ['source', 'input_hwp'], [-.7, .83, -1.38], [-.7, .83, -.94]);
    segment('preparation-routing', ['input_hwp', 'router'], [-.7, .83, -.62], [-.7, .83, .08]);
    segment('routing-modulator', ['router', 'slm'], [-.7, .83, .08], [-2.81, .83, .08]);
    segment('modulator-routing', ['slm', 'router'], [-2.81, .89, .26], [-.7, .89, .26]);
    segment('routing-qwp', ['router', 'qwp'], [-.7, .89, .26], [.92, .89, .26]);
    segment('qwp-hwp', ['qwp', 'hwp'], [1.08, .89, .26], [2.22, .89, .26]);
    segment('hwp-readout', ['hwp', 'measurement'], [2.38, .89, .26], [3.3, .89, .26]);
    const selectionRing = geometry(new THREE.TorusGeometry(.47, .022, 6, 48)), selectionMaterial = material(new THREE.MeshBasicMaterial({ color: '#f1c878', toneMapped: false }));
    for (const [id, item] of selectable) { const halo = mesh(item, selectionRing, selectionMaterial, [0, .035, 0]); halo.rotation.x = Math.PI / 2; halo.name = 'selection-halo'; halo.visible = id === selected;
      halo.userData.r03FramingExcluded = true; if (id === 'slm') halo.scale.set(1.25, 1.85, 1); else if (id === 'measurement') halo.scale.setScalar(1.25);
      item.traverse(object => { object.userData.identity = id; }); }
  } catch (error) { geometries.forEach(g => g.dispose()); materials.forEach(m => m.dispose()); textures.forEach(t => t.dispose()); labels.forEach(c => c.width = c.height = 0); throw error; }
  function framingBounds(id?: string): THREE.Box3 {
    if (disposed) throw new Error('Mounted apparatus has been disposed');
    if (id !== undefined && !selectable.has(id)) throw new Error(`Unknown apparatus component: ${id}`);
    group.updateWorldMatrix(true, true); const bounds = new THREE.Box3(), part = new THREE.Box3();
    for (const assembly of id === undefined ? selectable.values() : [selectable.get(id)!]) assembly.traverse(object => {
      if (!(object instanceof THREE.Mesh) || !object.userData.r03Assembly || object.userData.r03FramingExcluded) return;
      if (!object.geometry.boundingBox) object.geometry.computeBoundingBox();
      if (object.geometry.boundingBox) { part.copy(object.geometry.boundingBox).applyMatrix4(object.matrixWorld); bounds.union(part); }
    });
    if (bounds.isEmpty()) throw new Error('No mounted component assembly is available for framing'); return bounds;
  }
  function select(id: string): void {
    if (!selectable.has(id)) throw new Error(`Unknown apparatus component: ${id}`);
    const previous = selected; selected = id;
    selectable.forEach((item, key) => { const halo = item.getObjectByName('selection-halo'); if (halo) halo.visible = key === id; });
    segments.forEach(segment => segment.meshes.forEach(mesh => { mesh.material = segment.owners.includes(id) ? selectedGuideMaterial : guideMaterial; }));
    for (const label of labelRecords.values()) {
      const depthTest = label.id !== selected; if ((label.sprite.material as THREE.SpriteMaterial).depthTest !== depthTest) {
        label.sprite.material.depthTest = depthTest; label.sprite.material.needsUpdate = true; }
      if (previous !== selected && (label.id === selected || label.id === previous)) drawLabel(label);
    }
  }
  select(selected);
  const world = new THREE.Vector3(), view = new THREE.Vector3(), projected = new THREE.Vector3();
  let labelUpdateCount = 0;
  function updateLabels(camera: THREE.PerspectiveCamera, width: number, height: number): void {
    if (disposed || !Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) return;
    camera.updateMatrixWorld(); group.updateWorldMatrix(true, true); ++labelUpdateCount;
    const occupied: { left: number; right: number; top: number; bottom: number }[] = [];
    const order = [selected, 'slm', 'source', 'measurement', 'qwp', 'hwp', 'input_hwp', 'router'];
    for (const id of [...new Set(order)]) { const label = labelRecords.get(id)!; label.rectangle = null;
      world.copy(label.anchor); label.sprite.parent!.localToWorld(world); view.copy(world).applyMatrix4(camera.matrixWorldInverse);
      projected.copy(world).project(camera); const depth = -view.z;
      const visible = depth > camera.near && projected.z >= -1 && projected.z <= 1 && Math.abs(projected.x) < 1.4 && Math.abs(projected.y) < 1.5;
      if (!visible || width < 80 || height < 40) { label.sprite.visible = false; label.sprite.layers.set(31); continue; }
      const pixelHeight = 26, pixelWidth = pixelHeight * (128 / 48), half = pixelWidth / 2;
      const x = Math.max(half + 5, Math.min(width - half - 5, (projected.x + 1) * width / 2));
      const y = Math.max(pixelHeight / 2 + 5, Math.min(height - pixelHeight / 2 - 5, (1 - projected.y) * height / 2));
      const rectangle = { left: x - half - 3, right: x + half + 3, top: y - pixelHeight / 2 - 3, bottom: y + pixelHeight / 2 + 3 };
      const overlaps = occupied.some(other => rectangle.left < other.right && rectangle.right > other.left && rectangle.top < other.bottom && rectangle.bottom > other.top);
      if (overlaps) { label.sprite.visible = false; label.sprite.layers.set(31); continue; }
      // Keep screen-readable labels in the view; this moves only decorative labels, never geometry/camera.
      projected.x = 2 * x / width - 1; projected.y = 1 - 2 * y / height; projected.unproject(camera);
      label.sprite.position.copy(label.sprite.parent!.worldToLocal(projected));
      const worldHeight = 2 * depth * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) * pixelHeight / height;
      label.sprite.scale.set(worldHeight * 128 / 48, worldHeight, 1); label.sprite.visible = true; label.sprite.layers.set(0);
      label.rectangle = rectangle; occupied.push(rectangle);
    }
  }
  const buffers = new Set<ArrayBufferLike>();
  for (const shape of [...geometries, ...borrowedGeometries]) { if (shape.index) buffers.add(shape.index.array.buffer); Object.values(shape.attributes).forEach(a => buffers.add(a.array.buffer)); }
  instances.forEach(instance => buffers.add(instance.instanceMatrix.array.buffer));
  const geometryBytes = [...buffers].reduce((n, b) => n + b.byteLength, 0), labelBytes = labels.reduce((n, c) => n + c.width * c.height * 4, 0), ownedBytes = geometryBytes + labelBytes;
  if (ownedBytes > R03_APPARATUS_CAP) { geometries.forEach(g => g.dispose()); materials.forEach(m => m.dispose()); textures.forEach(t => t.dispose()); labels.forEach(c => c.width = c.height = 0); throw new Error('Ideal apparatus exceeds 512 KiB app-owned reservation'); }
  return { group, get ownedBytes() { return disposed ? 0 : ownedBytes; }, get geometryBytes() { return disposed ? 0 : geometryBytes; },
    get labelBytes() { return disposed ? 0 : labelBytes; }, get geometryCount() { return geometries.size; },
    select, framingBounds, updateLabels,
    setPhase(texture) { phaseFace.material.map = texture; phaseFace.material.color.set(texture ? '#ffffff' : '#345c65'); phaseFace.material.needsUpdate = true; },
    setAngles(qwp, hwp) { if (![qwp, hwp].every(angle => Number.isFinite(angle) && Math.abs(angle) <= 2 * Math.PI)) throw new Error('Validated display angles must be finite radians in [-2π,2π]');
      markers.get('qwp')!.rotation.x = qwp; markers.get('hwp')!.rotation.x = hwp; },
    snapshot() { return { selected, geometryBytes: disposed ? 0 : geometryBytes, labelBytes: disposed ? 0 : labelBytes, ownedBytes: disposed ? 0 : ownedBytes, geometryCount: geometries.size, componentCount: selectable.size,
      phaseVisible: phaseFace.material.map !== null, functionalGuides: true, computedRays: false, propagatedFieldSections: false,
      staticDirections: true, axisDisplayBasis: { x: '+z', y: '-y' }, axisDirections: Object.fromEntries([...markers].map(([id, marker]) => [id, new THREE.Vector3(0, 0, 1).applyQuaternion(marker.quaternion).toArray()])),
      functionalSegments: segments.map(segment => ({ id: segment.id, highlighted: segment.owners.includes(selected), from: segment.from.toArray(), to: segment.to.toArray() })),
      labels: [...labelRecords.values()].map(label => ({ id: label.id, text: SHORT_LABELS[label.id], visible: label.sprite.visible, pixelBounds: label.rectangle })), labelUpdateCount,
      borrowedGeometryCount: borrowedGeometries.size,
      components: [...selectable.entries()].map(([id, item]) => ({ id, world: item.position.toArray() })) }; },
    dispose() { if (disposed) return; disposed = true; phaseFace.material.map = null; group.removeFromParent(); group.clear();
      geometries.forEach(g => g.dispose()); materials.forEach(m => m.dispose()); textures.forEach(t => t.dispose()); labels.forEach(c => c.width = c.height = 0);
      geometries.clear(); borrowedGeometries.clear(); materials.clear(); textures.clear(); labels.length = 0; selectable.clear(); markers.clear(); labelRecords.clear(); segments.length = 0; },
  };
}
