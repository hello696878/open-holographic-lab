/** Quantitative arrays remain untouched; amber sheets/curtains are labelled presentation. */
import * as THREE from 'three';
import { createArrayDetectorTexture, intensityRGBA, validateColorLimits, type ColorLimits } from './detector';
import { detectorEdges, pixelCoordinates } from './mapping';
import { waveFieldSection, type WaveFieldResult } from './wave_field_contracts';

export const W1_INITIAL_RANGE: Readonly<ColorLimits> = Object.freeze({ min: 0, max: 3 });
export interface CurtainBand { readonly sectionId: string; readonly sectionIndex: number; readonly segment: number;
  readonly start_m: number; readonly end_m: number; readonly z_m: number }
/** Each gap owns its two event sides. Never bridge a thin element or tie-break by nearest z. */
export function curtainBandPlan(result: WaveFieldResult): readonly CurtainBand[] {
  const [aperture, lens] = result.experiment.components;
  const groups = [ ['source', `before:${aperture.id}`], [`after:${aperture.id}`, `before:${lens.id}`], [`after:${lens.id}`, 'observation'] ];
  const output: CurtainBand[] = [];
  groups.forEach(([first, last], segment) => {
    const start = result.planes.findIndex(plane => plane.stage === first), end = result.planes.findIndex(plane => plane.stage === last);
    if (start < 0 || end < start) throw new Error('Missing actual event sides for sampled curtain');
    const planes = result.planes.slice(start, end + 1);
    planes.forEach((plane, index) => {
      const left = index ? (planes[index - 1].z_m + plane.z_m) / 2 : plane.z_m;
      const right = index + 1 < planes.length ? (plane.z_m + planes[index + 1].z_m) / 2 : plane.z_m;
      if (right > left) output.push(Object.freeze({ sectionId: plane.id, sectionIndex: start + index, segment, start_m: left, end_m: right, z_m: plane.z_m }));
    });
  }); return Object.freeze(output);
}
/** Shared linear scale. The opacity is decorative, never a power or scattering measurement. */
export function waveFieldColor(value: number, limits: ColorLimits, glow = true): readonly [number, number, number, number] {
  validateColorLimits(limits); if (!Number.isFinite(value) || value < 0) throw new Error('Invalid raw intensity for W1 display');
  const t = Math.max(0, Math.min(1, (value - limits.min) / (limits.max - limits.min)));
  return [255, Math.round(125 + t * 103), Math.round(37 + t * 133), Math.round(255 * t * (glow ? .88 : .58))];
}
export function sectionRGBA(result: WaveFieldResult, index: number, limits: ColorLimits, glow = true): Uint8Array {
  const values = waveFieldSection(result, index), { nx, ny } = result.experiment.grid, bytes = new Uint8Array(values.length * 4);
  for (let row = 0; row < ny; row++) for (let column = 0; column < nx; column++) {
    bytes.set(waveFieldColor(values[row * nx + column], limits, glow), 4 * ((ny - 1 - row) * nx + column));
  } return bytes;
}
export function sectionSample(result: WaveFieldResult, section: number, row: number, column: number) {
  const coordinates = pixelCoordinates(result.experiment.grid, row, column), plane = result.planes[section];
  if (!plane) throw new Error('Unknown calculated section');
  return Object.freeze({ sectionId: plane.id, stage: plane.stage, z_m: plane.z_m, row, column, ...coordinates,
    intensity: waveFieldSection(result, section)[row * result.experiment.grid.nx + column] });
}
export function formatWaveFieldNumber(value: number | null, full = false): string {
  if (value === null) return 'undefined (null)'; if (Object.is(value, -0)) return '−0'; return full ? value.toPrecision(17) : value.toPrecision(6);
}
export interface WaveFieldDisplay {
  readonly result: WaveFieldResult; readonly group: THREE.Group; readonly canvas: HTMLCanvasElement;
  readonly detectorTexture: THREE.DataTexture; readonly limits: Readonly<ColorLimits>; readonly bands: readonly CurtainBand[];
  readonly ownedBytes: number; readonly textureSourceBytes: number; readonly geometryBytes: number;
  select(index: number): void; snapshot(): object; dispose(): void;
}
export interface WaveFieldDisplayFactories { canvas?: () => HTMLCanvasElement; texture?: (bytes: Uint8Array, width: number, height: number) => THREE.DataTexture }
export function prepareWaveFieldDisplay(result: WaveFieldResult, limits: ColorLimits, glow = true,
    factories: WaveFieldDisplayFactories = {}): WaveFieldDisplay {
  validateColorLimits(limits);
  const { nx, ny } = result.experiment.grid, edges = detectorEdges(result.experiment.grid), group = new THREE.Group();
  group.name = 'w1-calculated-fields';
  const geometries = new Set<THREE.BufferGeometry>(), materials = new Set<THREE.Material>(), textures = new Set<THREE.DataTexture>();
  const sourceBuffers = new Set<ArrayBufferLike>();
  const canvas = factories.canvas?.() ?? document.createElement('canvas');
  let disposed = false, selected = result.planes.length - 1, scratchBytes = 0;
  const bands = curtainBandPlan(result), sheetMeshes: THREE.Mesh[] = [], curtainMeshes: THREE.Mesh[] = [];
  const texture = (bytes: Uint8Array, width: number, height: number) => {
    const value = factories.texture?.(bytes, width, height) ?? new THREE.DataTexture(bytes, width, height, THREE.RGBAFormat, THREE.UnsignedByteType);
    value.flipY = false; value.minFilter = value.magFilter = THREE.NearestFilter; value.generateMipmaps = false;
    value.colorSpace = THREE.SRGBColorSpace; value.needsUpdate = true; textures.add(value); sourceBuffers.add(bytes.buffer); return value;
  };
  const geometry = <T extends THREE.BufferGeometry>(value: T): T => { geometries.add(value); return value; };
  const material = <T extends THREE.Material>(value: T): T => { materials.add(value); return value; };
  const dispose = () => { if (disposed) return; disposed = true; group.removeFromParent(); group.clear();
    geometries.forEach(value => value.dispose()); materials.forEach(value => value.dispose()); textures.forEach(value => value.dispose());
    geometries.clear(); materials.clear(); textures.clear(); sourceBuffers.clear(); canvas.width = canvas.height = 0; };
  let detectorTexture: THREE.DataTexture;
  try {
    const planeGeometry = geometry(new THREE.PlaneGeometry(edges.width * 1000, edges.height * 1000));
    const terminal = waveFieldSection(result, result.planes.length - 1);
    detectorTexture = createArrayDetectorTexture(terminal, result.experiment.grid, limits); textures.add(detectorTexture);
    sourceBuffers.add((detectorTexture.image.data as Uint8Array).buffer);
    result.planes.forEach((plane, index) => {
      const appearance = material(new THREE.MeshBasicMaterial({ map: texture(sectionRGBA(result, index, limits, glow), nx, ny),
        side: THREE.DoubleSide, transparent: true, depthWrite: false, toneMapped: false, opacity: .76 }));
      const mesh = new THREE.Mesh(planeGeometry, appearance); mesh.position.set(edges.centerX * 1000, 1 - edges.centerY * 1000, plane.z_m * 100);
      mesh.userData.waveFieldSection = plane.id; mesh.userData.waveFieldIndex = index; mesh.userData.waveFieldGrid = result.experiment.grid;
      sheetMeshes.push(mesh); group.add(mesh);
    });
    for (const band of bands) for (const axis of ['x', 'y'] as const) {
      const values = waveFieldSection(result, band.sectionIndex), length = axis === 'x' ? nx : ny, bytes = new Uint8Array(length * 4);
      for (let sample = 0; sample < length; sample++) {
        const value = axis === 'x' ? values[Math.floor(ny / 2) * nx + sample] : values[sample * nx + Math.floor(nx / 2)];
        bytes.set(waveFieldColor(value, limits, glow), sample * 4);
      }
      const map = texture(bytes, length, 1), span = (band.end_m - band.start_m) * 100;
      const a = axis === 'x' ? edges.xMin * 1000 : 1 - edges.yMin * 1000;
      const b = axis === 'x' ? edges.xMax * 1000 : 1 - edges.yMax * 1000;
      const start = band.start_m * 100, end = band.end_m * 100;
      const vertices = axis === 'x' ? [a, 1, start, b, 1, start, a, 1, end, b, 1, end]
        : [0, a, start, 0, b, start, 0, a, end, 0, b, end];
      const shape = geometry(new THREE.BufferGeometry());
      shape.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
      shape.setAttribute('uv', new THREE.Float32BufferAttribute([0, 0, 1, 0, 0, 1, 1, 1], 2)); shape.setIndex([0, 1, 2, 2, 1, 3]);
      const appearance = material(new THREE.MeshBasicMaterial({ map, side: THREE.DoubleSide, transparent: true, depthWrite: false, toneMapped: false, opacity: .72 }));
      const mesh = new THREE.Mesh(shape, appearance);
      // Explicit per-band provenance; it is nearest-sample presentation, not another calculated plane.
      mesh.userData.waveFieldCurtain = { ...band, axis, interpolation: 'nearest-sample band; split at events' };
      curtainMeshes.push(mesh); group.add(mesh);
    }
    const cursorShape = geometry(new THREE.EdgesGeometry(planeGeometry));
    const cursor = new THREE.LineSegments(cursorShape, material(new THREE.LineBasicMaterial({ color: '#f5e4ad', transparent: true, opacity: .95 })));
    cursor.name = 'w1-inspection-cursor'; group.add(cursor);
    canvas.width = nx; canvas.height = ny; canvas.dataset.testid = 'w1-cross-section'; canvas.tabIndex = 0;
    canvas.setAttribute('aria-label', '已計算截面的原始強度灰階，row 0 在上，column 0 在左');
    const context = canvas.getContext('2d'); if (!context) throw new Error('W1 cross-section canvas preparation failed');
    const select = (index: number) => {
      if (disposed || !Number.isInteger(index) || index < 0 || index >= result.planes.length) throw new Error('Unknown actual calculated section');
      selected = index;
      // Sparse physical sections plus the selected event side. One representative at a shared z;
      // the selected side always wins without inventing a physical displacement.
      const sparse = new Map<number, number>();
      for (let n = 0; n < 7; n++) { const at = Math.round(n * (result.planes.length - 1) / 6); sparse.set(result.planes[at].z_m, at); }
      sparse.set(result.planes[index].z_m, index);
      sheetMeshes.forEach((mesh, at) => { mesh.visible = sparse.get(result.planes[at].z_m) === at;
        (mesh.material as THREE.MeshBasicMaterial).opacity = at === index ? 1 : .58; });
      cursor.position.copy(sheetMeshes[index].position);
      const raw = intensityRGBA(waveFieldSection(result, index), ny, nx, limits);
      const data = new Uint8ClampedArray(raw); scratchBytes = raw.byteLength + data.byteLength;
      context.putImageData(new ImageData(data, nx, ny), 0, 0); scratchBytes = 0;
      canvas.dataset.requestId = result.requestId; canvas.dataset.sectionId = result.planes[index].id;
    };
    select(selected);
    const geometryBuffers = new Set<ArrayBufferLike>();
    geometries.forEach(shape => { if (shape.index) geometryBuffers.add(shape.index.array.buffer); Object.values(shape.attributes).forEach(value => geometryBuffers.add(value.array.buffer)); });
    const geometryBytes = [...geometryBuffers].reduce((n, buffer) => n + buffer.byteLength, 0);
    const textureSourceBytes = [...sourceBuffers].reduce((n, buffer) => n + buffer.byteLength, 0);
    const ownedBytes = geometryBytes + textureSourceBytes + nx * ny * 4 + bands.length * 128 + result.planes.length * 3 * 8;
    return { result, group, canvas, detectorTexture, limits: Object.freeze({ ...limits }), bands,
      get ownedBytes() { return disposed ? 0 : ownedBytes; }, get textureSourceBytes() { return disposed ? 0 : textureSourceBytes; },
      get geometryBytes() { return disposed ? 0 : geometryBytes; }, select,
      snapshot() { return { disposed, ownedBytes: disposed ? 0 : ownedBytes, textureSourceBytes: disposed ? 0 : textureSourceBytes,
        geometryBytes: disposed ? 0 : geometryBytes, canvasBytes: disposed ? 0 : nx * ny * 4, scratchBytes,
        selectedIndex: selected, selectedId: result.planes[selected].id, limits: { ...limits }, glow,
        visibleSheets: sheetMeshes.filter(mesh => !disposed && mesh.visible).map(mesh => ({ id: mesh.userData.waveFieldSection, z_m: mesh.position.z / 100 })),
        curtainBands: bands.map(band => ({ ...band })), presentationInterpolation: 'event-split nearest-sample meridional bands',
        computedVolumetricField: false, gaussianEnvelopeFit: false, textureCount: textures.size, geometryCount: geometries.size }; }, dispose };
  } catch (error) { dispose(); throw error; }
}
