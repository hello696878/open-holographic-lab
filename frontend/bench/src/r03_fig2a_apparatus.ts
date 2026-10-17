/** Original mounted apparatus. All distances/routes are functional design, never computed rays. */
import * as THREE from 'three';
import { R03_APPARATUS_CAP } from './r03_fig2a_display';
export const R03_COMPONENT_LABELS: Readonly<Record<string, string>> = Object.freeze({ source: '01 · D source', input_hwp: '02 · Input preparation',
  router: '03 · Routing / UNKNOWN', slm: '04 · Phase-only SLM', qwp: '05 · Ideal QWP', hwp: '06 · Ideal HWP', measurement: '07 · Ensemble readout' });
export interface R03Apparatus { readonly group: THREE.Group; readonly ownedBytes: number; readonly geometryBytes: number;
  readonly labelBytes: number; readonly geometryCount: number; select(id: string): void; setPhase(texture: THREE.DataTexture | null): void;
  setAngles(qwp: number, hwp: number): void; snapshot(): object; dispose(): void }
export function createR03Apparatus(): R03Apparatus {
  const group = new THREE.Group(), geometries = new Set<THREE.BufferGeometry>(), materials = new Set<THREE.Material>();
  const textures = new Set<THREE.CanvasTexture>(), labels: HTMLCanvasElement[] = [], instances: THREE.InstancedMesh[] = [];
  const selectable = new Map<string, THREE.Group>(), markers = new Map<string, THREE.Group>(); let selected = 'slm', disposed = false;
  const geometry = <T extends THREE.BufferGeometry>(g: T): T => { geometries.add(g); return g; };
  const material = <T extends THREE.Material>(m: T): T => { materials.add(m); return m; };
  const metal = material(new THREE.MeshStandardMaterial({ color: '#a3b6c1', metalness: .7, roughness: .33 }));
  const dark = material(new THREE.MeshStandardMaterial({ color: '#284655', metalness: .62, roughness: .39 }));
  const teal = material(new THREE.MeshStandardMaterial({ color: '#4eaca8', metalness: .2, roughness: .3, transparent: true, opacity: .62 }));
  const black = material(new THREE.MeshStandardMaterial({ color: '#102b38', roughness: .6 }));
  const unitBox = geometry(new THREE.BoxGeometry(1, 1, 1)), postGeometry = geometry(new THREE.CylinderGeometry(.055, .064, 1, 14));
  const baseGeometry = geometry(new THREE.BoxGeometry(.64, .08, .48));
  const torusGeometry = geometry(new THREE.TorusGeometry(.29, .055, 7, 36)), glassGeometry = geometry(new THREE.CircleGeometry(.25, 40));
  function mesh(parent: THREE.Object3D, shape: THREE.BufferGeometry, appearance: THREE.Material, position: number[], scale = [1, 1, 1]): THREE.Mesh {
    const value = new THREE.Mesh(shape, appearance); value.position.set(position[0], position[1], position[2]); value.scale.set(...scale as [number, number, number]); parent.add(value); return value;
  }
  function component(id: string, x: number, z: number): THREE.Group { const item = new THREE.Group(); item.position.set(x, 0, z); group.add(item); selectable.set(id, item); return item; }
  function mount(parent: THREE.Object3D): void { mesh(parent, baseGeometry, dark, [0, .1, 0]); mesh(parent, postGeometry, metal, [0, .43, 0], [1, .6, 1]); }
  function label(parent: THREE.Group, id: string, y = .12, z = .48): void {
    const canvas = document.createElement('canvas'); canvas.width = 192; canvas.height = 40; labels.push(canvas);
    const ctx = canvas.getContext('2d'); if (!ctx) throw new Error('Mounted apparatus label canvas unavailable');
    ctx.fillStyle = '#153543'; ctx.fillRect(0, 0, 192, 40); ctx.font = '600 13px system-ui'; ctx.textAlign = 'center';
    ctx.fillStyle = '#d6e6eb'; ctx.fillText(R03_COMPONENT_LABELS[id], 96, 24, 184);
    const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace; textures.add(texture);
    const sprite = new THREE.Sprite(material(new THREE.SpriteMaterial({ map: texture, depthTest: false, transparent: true })));
    sprite.position.set(0, y, z); sprite.scale.set(1.25, .26, 1); parent.add(sprite);
  }
  let phaseFace: THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial>;
  try {
    group.add(new THREE.HemisphereLight('#d5f3ff', '#284333', 2.6));
    const light = new THREE.DirectionalLight('#ffffff', 3.3); light.position.set(-3, 8, 5); group.add(light);
    const rim = new THREE.DirectionalLight('#80cbbf', 1.5); rim.position.set(4, 3, -5); group.add(rim);
    mesh(group, unitBox, material(new THREE.MeshStandardMaterial({ color: '#173746', metalness: .48, roughness: .58 })), [.5, -.055, -.12], [9.9, .12, 5.7]);
    mesh(group, unitBox, dark, [.5, -.15, -.12], [10, .12, 5.8]);
    const hole = geometry(new THREE.CylinderGeometry(.027, .027, .014, 9));
    const holes = new THREE.InstancedMesh(hole, black, 24 * 13), matrix = new THREE.Matrix4(); let n = 0;
    for (let x = 0; x < 24; x++) for (let z = 0; z < 13; z++) { matrix.makeTranslation(-4.1 + x * .4, .013, -2.5 + z * .4); holes.setMatrixAt(n++, matrix); }
    group.add(holes); instances.push(holes);
    const source = component('source', -.7, -2); mount(source);
    mesh(source, unitBox, metal, [0, .83, -.1], [.64, .52, 1.05]); mesh(source, unitBox, dark, [0, .84, -.12], [.52, .4, .86]);
    for (let i = 0; i < 6; i++) mesh(source, unitBox, metal, [0, 1.07, -.48 + i * .14], [.46, .016, .027]);
    const sourceAperture = mesh(source, glassGeometry, teal, [0, .83, .445]); sourceAperture.scale.setScalar(.65); label(source, 'source', .17, -.85);
    const input = component('input_hwp', -.7, -.83); mount(input);
    const inRing = mesh(input, torusGeometry, metal, [0, .83, 0]); mesh(input, glassGeometry, teal, [0, .83, .006]);
    const inAxis = mesh(input, unitBox, metal, [0, .83, .025], [.025, .4, .018]); inAxis.rotation.z = -Math.PI / 4; label(input, 'input_hwp', .1, -.3);
    const router = component('router', -.7, .15); mount(router);
    const cube = mesh(router, unitBox, material(new THREE.MeshStandardMaterial({ color: '#85bfc1', transparent: true, opacity: .3, metalness: .1, roughness: .15 })), [0, .83, 0], [.48, .48, .48]);
    const edges = new THREE.LineSegments(geometry(new THREE.EdgesGeometry(unitBox)), material(new THREE.LineBasicMaterial({ color: '#a1d3d3' })));
    edges.scale.copy(cube.scale); edges.position.copy(cube.position); router.add(edges); label(router, 'router', .12, .55);
    const slm = component('slm', -3, .15); mount(slm);
    mesh(slm, unitBox, metal, [0, 1.02, 0], [.25, 1.35, 1.47]); mesh(slm, unitBox, black, [.14, 1.02, 0], [.04, 1.16, 1.28]);
    phaseFace = new THREE.Mesh(geometry(new THREE.PlaneGeometry(1.04, 1.04)), material(new THREE.MeshBasicMaterial({ color: '#345c65', side: THREE.DoubleSide, toneMapped: false })));
    phaseFace.rotation.y = Math.PI / 2; phaseFace.position.set(.17, 1.02, 0); slm.add(phaseFace); label(slm, 'slm', .16, .98);
    const cable = new THREE.Line(geometry(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-3, .9, -.55), new THREE.Vector3(-3.38, .45, -.8), new THREE.Vector3(-3.5, .08, -1.15)])), material(new THREE.LineBasicMaterial({ color: '#527783', linewidth: 2 }))); group.add(cable);
    function waveplate(id: 'qwp' | 'hwp', x: number): void {
      const plate = component(id, x, .15); mount(plate); const ring = mesh(plate, torusGeometry, metal, [0, .83, 0]); ring.rotation.y = Math.PI / 2;
      const glass = mesh(plate, glassGeometry, teal, [.006, .83, 0]); glass.rotation.y = Math.PI / 2;
      const axis = new THREE.Group(); axis.position.set(.028, .83, 0); plate.add(axis);
      mesh(axis, unitBox, material(new THREE.MeshBasicMaterial({ color: '#e5b66c' })), [0, 0, 0], [.02, .43, .018]); markers.set(id, axis);
      mesh(plate, unitBox, dark, [.04, .85, .34], [.16, .13, .13]); label(plate, id, .12, .6);
    }
    waveplate('qwp', 1); waveplate('hwp', 2.3);
    const measurement = component('measurement', 3.8, .15); mount(measurement);
    mesh(measurement, unitBox, metal, [0, .96, 0], [.9, .8, .95]); mesh(measurement, unitBox, black, [.02, 1, .49], [.72, .57, .025]);
    mesh(measurement, unitBox, teal, [.02, 1.08, .51], [.55, .16, .015]);
    for (let i = 0; i < 3; i++) mesh(measurement, glassGeometry, teal, [-.18 + i * .18, .85, .52], [.14, .14, .14]);
    const aperture = mesh(measurement, torusGeometry, dark, [-.47, .94, 0]); aperture.rotation.y = Math.PI / 2; aperture.scale.setScalar(.75); label(measurement, 'measurement', .1, .83);
    const guideMaterial = material(new THREE.LineDashedMaterial({ color: '#dcae68', dashSize: .13, gapSize: .085, transparent: true, opacity: .95 }));
    for (const points of [[[-.7, .83, -1.55], [-.7, .83, .08], [-2.81, .83, .08]], [[-2.81, .89, .26], [-.7, .89, .26], [3.3, .89, .26]]]) {
      const line = new THREE.Line(geometry(new THREE.BufferGeometry().setFromPoints(points.map(p => new THREE.Vector3(...p as [number, number, number])))), guideMaterial); line.computeLineDistances(); group.add(line);
    }
    const referenceMaterial = material(new THREE.MeshBasicMaterial({ color: '#6dbdc9', transparent: true, opacity: .15, side: THREE.DoubleSide, depthWrite: false }));
    const referenceGeometry = geometry(new THREE.PlaneGeometry(.85, .9));
    for (const x of [-2.05, .25, 3.05]) { const plane = mesh(group, referenceGeometry, referenceMaterial, [x, .85, .15]); plane.rotation.y = Math.PI / 2; }
    const selectionRing = geometry(new THREE.TorusGeometry(.45, .014, 5, 42)), selectionMaterial = material(new THREE.MeshBasicMaterial({ color: '#e9b668' }));
    for (const [id, item] of selectable) { const halo = mesh(item, selectionRing, selectionMaterial, [0, .03, 0]); halo.rotation.x = Math.PI / 2; halo.name = 'selection-halo'; halo.visible = id === selected;
      item.traverse(object => { object.userData.identity = id; }); }
  } catch (error) { geometries.forEach(g => g.dispose()); materials.forEach(m => m.dispose()); textures.forEach(t => t.dispose()); labels.forEach(c => c.width = c.height = 0); throw error; }
  const buffers = new Set<ArrayBufferLike>();
  for (const shape of geometries) { if (shape.index) buffers.add(shape.index.array.buffer); Object.values(shape.attributes).forEach(a => buffers.add(a.array.buffer)); }
  instances.forEach(instance => buffers.add(instance.instanceMatrix.array.buffer));
  const geometryBytes = [...buffers].reduce((n, b) => n + b.byteLength, 0), labelBytes = labels.reduce((n, c) => n + c.width * c.height * 4, 0), ownedBytes = geometryBytes + labelBytes;
  if (ownedBytes > R03_APPARATUS_CAP) { geometries.forEach(g => g.dispose()); materials.forEach(m => m.dispose()); textures.forEach(t => t.dispose()); labels.forEach(c => c.width = c.height = 0); throw new Error('Ideal apparatus exceeds 512 KiB app-owned reservation'); }
  return { group, ownedBytes, geometryBytes, labelBytes, geometryCount: geometries.size,
    select(id) { selected = id; selectable.forEach((item, key) => { const halo = item.getObjectByName('selection-halo'); if (halo) halo.visible = key === id; }); },
    setPhase(texture) { phaseFace.material.map = texture; phaseFace.material.color.set(texture ? '#ffffff' : '#345c65'); phaseFace.material.needsUpdate = true; },
    setAngles(qwp, hwp) { markers.get('qwp')!.rotation.x = qwp; markers.get('hwp')!.rotation.x = hwp; },
    snapshot() { return { selected, geometryBytes, labelBytes, ownedBytes, geometryCount: geometries.size, componentCount: selectable.size,
      phaseVisible: phaseFace.material.map !== null, functionalGuides: true, computedRays: false, propagatedFieldSections: false,
      components: [...selectable.entries()].map(([id, item]) => ({ id, world: item.position.toArray() })) }; },
    dispose() { if (disposed) return; disposed = true; group.removeFromParent(); group.clear(); geometries.forEach(g => g.dispose()); materials.forEach(m => m.dispose()); textures.forEach(t => t.dispose()); labels.forEach(c => c.width = c.height = 0); },
  };
}
