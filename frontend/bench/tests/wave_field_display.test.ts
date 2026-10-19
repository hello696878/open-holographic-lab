import { afterEach, describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { cloneExperiment } from '../src/contracts';
import { intensityRGBA } from '../src/detector';
import { detectorEdges, pixelCenterUV, pixelCoordinates, pixelFromUV } from '../src/mapping';
import { curtainBandPlan, formatWaveFieldNumber, prepareWaveFieldDisplay, sectionRGBA, sectionSample, waveFieldColor, W1_DEFAULT_PRESENTATION } from '../src/wave_field_display';
import { buildWaveFieldSampling, waveFieldPlan, waveFieldSection, W1_EXAMPLE, type WaveFieldResult } from '../src/wave_field_contracts';

function result(nx = 4, ny = 3, full = false): WaveFieldResult {
  const experiment = cloneExperiment(W1_EXAMPLE); experiment.grid = { nx, ny, dx: .001, dy: .002 };
  const sampling = full ? buildWaveFieldSampling(experiment) : { interior_z_m: [.015, .045, .12] }, plan = waveFieldPlan(experiment, sampling);
  const count = nx * ny, axis = Math.floor(ny / 2) * nx + Math.floor(nx / 2);
  const intensities = Float64Array.from(plan.flatMap(plane => Array.from({ length: count }, (_, pixel) => (pixel + 1) / 10 * (plane.z_m >= .03 && !plane.stage.startsWith('before:aperture') ? .25 : 1))));
  const planes = plan.map((plane, index) => ({ ...plane, norm: index < 3 ? 12 : 3, previous_norm: index ? 12 : null,
    delta_norm: index ? index < 3 ? 0 : -9 : null, transmission_ratio: index ? index < 3 ? 1 : .25 : null,
    on_axis_intensity: intensities[index * count + axis], max_intensity: intensities[index * count + count - 1] }));
  return { requestId: 'display-only-unit-fixture', experimentSha256: 'a'.repeat(64), experiment, sampling, planes, stages: [], intensities,
    x: Float64Array.from({ length: nx }, (_, column) => pixelCoordinates(experiment.grid, 0, column).x_m),
    y: Float64Array.from({ length: ny }, (_, row) => pixelCoordinates(experiment.grid, row, 0).y_m) };
}
function install(failed = false) {
  const paints: Uint8ClampedArray[] = []; const canvas = { width: 0, height: 0, dataset: {}, setAttribute() {}, getContext() { return failed ? null : { putImageData(image: { data: Uint8ClampedArray }) { paints.push(image.data.slice()); } }; } } as unknown as HTMLCanvasElement;
  vi.stubGlobal('ImageData', class { constructor(readonly data: Uint8ClampedArray) {} }); return { canvas, paints };
}
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });
describe('actual sampled W1 sections and presentation ownership', () => {
  it('preserves all raw asymmetric values and exact physical sample coordinates including signed zero/null readouts', () => {
    const raw = result(), copy = raw.intensities.slice(); expect(sectionSample(raw, 0, 0, 3)).toMatchObject({ row: 0, column: 3, x_m: .001, y_m: -.002, intensity: .4 });
    expect(formatWaveFieldNumber(null, true)).toBe('undefined (null)'); expect(formatWaveFieldNumber(-0, true)).toBe('−0');
    expect(formatWaveFieldNumber(1 + Number.EPSILON, true)).toBe('1.0000000000000002'); expect(formatWaveFieldNumber(1e-13, true)).toBe('1.0000000000000000e-13');
    expect(raw.intensities).toEqual(copy); expect(() => sectionSample(raw, 0, 3, 0)).toThrow('outside');
  });
  it('uses one stable global range, visibly retains aperture loss and detects independent per-plane normalization', () => {
    const raw = result(), range = { min: 0, max: 3 }, before = sectionRGBA(raw, 2, range), after = sectionRGBA(raw, 3, range);
    expect(after[3], 'W1_SHARED_RANGE_APERTURE_LOSS').toBeLessThan(before[3]); expect(waveFieldColor(.3, range)[3]).toBeLessThan(waveFieldColor(1.2, range)[3]);
    const wrongAfter = sectionRGBA(raw, 3, { min: 0, max: raw.planes[3].max_intensity });
    expect(() => expect(wrongAfter, 'W1_DETECT_HIDDEN_INDEPENDENT_NORMALIZATION').toEqual(after)).toThrow();
    expect(raw.planes[2].norm).toBe(12); expect(raw.planes[3].norm).toBe(3); expect(() => waveFieldColor(NaN, range)).toThrow();
  });
  it('maps row 0 to top in the inspector and reverses only Three sheet UV rows, detecting transpose and row reversal', () => {
    const raw = result(), range = { min: 0, max: 3 }, rgba = sectionRGBA(raw, 0, range), values = waveFieldSection(raw, 0);
    expect(Array.from(rgba.slice(4 * 8, 4 * 8 + 4)), 'W1_RAW_ROW_ORIENTATION').toEqual(waveFieldColor(values[0], range));
    expect(Array.from(rgba.slice(0, 4))).toEqual(waveFieldColor(values[8], range));
    const wrong = new Uint8Array(rgba); wrong.set(rgba.subarray(0, 16), 32);
    expect(() => expect(wrong, 'W1_DETECT_REVERSED_TEXTURE_ORIENTATION').toEqual(rgba)).toThrow();
    const sample = sectionSample(raw, 0, 0, 3), transpose = values[3 * 3 + 0];
    expect(() => expect(transpose, 'W1_DETECT_X_Y_TRANSPOSE').toBe(sample.intensity)).toThrow();
  });
  it('splits nearest-sample meridional bands at event sides and rejects collapsed or fabricated between-plane data', () => {
    const raw = result(), bands = curtainBandPlan(raw);
    for (const segment of [0, 1, 2]) { const group = bands.filter(band => band.segment === segment);
      expect(group).toHaveLength(3); expect(group[0].start_m).toBe([0, .03, .06][segment]); expect(group.at(-1)!.end_m).toBe([.03, .06, .22][segment]); }
    expect(bands.filter(band => band.end_m === .03).map(band => band.sectionId)).toEqual(['section:before:aperture']);
    expect(bands.filter(band => band.start_m === .03).map(band => band.sectionId), 'W1_EVENT_SIDE_CURTAIN_IDENTITY').toEqual(['section:after:aperture']);
    const collapsed = { ...raw, planes: raw.planes.filter(plane => plane.stage !== 'after:aperture') };
    expect(() => curtainBandPlan(collapsed)).toThrow('event sides');
    const interpolated = new Float64Array(raw.intensities.length).fill(.5), rgba = sectionRGBA(raw, 1, { min: 0, max: 3 });
    expect(() => expect(sectionRGBA({ ...raw, intensities: interpolated }, 1, { min: 0, max: 3 }), 'W1_DETECT_FABRICATED_INTERPOLATION').toEqual(rgba)).toThrow();
  });
  it('builds genuine sparse plane textures and correctly oriented x/y curtains from exact selected samples', () => {
    const raw = result(), copy = raw.intensities.slice(), { canvas, paints } = install(), display = prepareWaveFieldDisplay(raw, { min: 0, max: 3 }, true, { canvas: () => canvas });
    display.select(0); expect(paints.at(-1)).toEqual(new Uint8ClampedArray(intensityRGBA(waveFieldSection(raw, 0), 3, 4, { min: 0, max: 3 })));
    const sheets: THREE.Mesh[] = [], curtains: THREE.Mesh[] = [];
    display.group.traverse(object => { if (object.userData.waveFieldSection) sheets.push(object as THREE.Mesh); if (object.userData.waveFieldCurtain) curtains.push(object as THREE.Mesh); });
    expect(sheets).toHaveLength(raw.planes.length); expect(sheets[2].position.z).toBe(sheets[3].position.z); display.select(3);
    expect(sheets[3].visible).toBe(true); expect(sheets[2].visible).toBe(false);
    expect(sheets.every((sheet, index) => sheet.position.z === raw.planes[index].z_m * 100), 'W1_ACTUAL_PLANE_POSITIONS').toBe(true);
    for (const mesh of curtains) {
      const band = mesh.userData.waveFieldCurtain, positions = mesh.geometry.getAttribute('position'), uv = mesh.geometry.getAttribute('uv');
      expect(positions.getZ(0)).toBeCloseTo(band.start_m * 100, 6); expect(positions.getZ(3)).toBeCloseTo(band.end_m * 100, 6);
      if (band.axis === 'x') { expect(positions.getY(0)).toBe(1); expect(positions.getY(3)).toBe(1); expect(positions.getX(0)).toBeCloseTo(-2.5, 6); }
      else { expect(positions.getX(0)).toBe(0); expect(positions.getX(3)).toBe(0); expect(positions.getY(0)).toBeCloseTo(4, 6); expect(positions.getY(1)).toBeCloseTo(-2, 6); }
      expect(uv.getX(0)).toBe(0); expect(uv.getX(1)).toBe(1);
      const map = (mesh.material as THREE.MeshBasicMaterial).map as THREE.DataTexture, array = waveFieldSection(raw, band.sectionIndex);
      const first = band.axis === 'x' ? array[4] : array[2]; expect(Array.from((map.image.data as Uint8Array).slice(0, 4))).toEqual(waveFieldColor(first, { min: 0, max: 3 }));
    }
    expect(raw.intensities).toEqual(copy); expect((display.snapshot() as any).visibleSheets.length).toBeLessThanOrEqual(8); display.dispose();
  });
  it('leaves the authoritative detector grayscale unchanged by decorative glow and retains shared range across selection', () => {
    const raw = result(), { canvas } = install(), a = prepareWaveFieldDisplay(raw, { min: 0, max: 3 }, false, { canvas: () => canvas });
    const bytes = (a.detectorTexture.image.data as Uint8Array).slice(); a.select(2); a.select(3);
    expect(a.limits).toEqual({ min: 0, max: 3 }); expect(a.detectorTexture.image.data).toEqual(bytes); a.dispose();
    const b = prepareWaveFieldDisplay(raw, { min: 0, max: 3 }, true, { canvas: () => install().canvas }); expect(b.detectorTexture.image.data).toEqual(bytes); b.dispose();
  });
  it('enhances only 3D opacity from the shared fixed range while preserving zero, aperture loss and linear RGB', () => {
    const range = { min: 0, max: 3 };
    for (const value of [0, 1e-12, .075, .3, 1, 3, 12]) {
      const enhanced = waveFieldColor(value, range, true), linear = waveFieldColor(value, range, false), t = Math.min(value / 3, 1);
      expect(enhanced.slice(0, 3), 'W11_RGB_STAYS_SHARED_LINEAR').toEqual(linear.slice(0, 3));
      expect(enhanced[3], 'W11_EXPLICIT_SHARED_SQRT_OPACITY').toBe(Math.round(255 * Math.sqrt(t) * .88));
      expect(linear[3]).toBe(Math.round(255 * t * .58));
    }
    expect(waveFieldColor(0, range)[3]).toBe(0);
    expect(waveFieldColor(.3, range)[3], 'W11_APERTURE_LOSS_NOT_NORMALIZED').toBeLessThan(waveFieldColor(1.2, range)[3]);
  });
  it('independently toggles selected, sparse, curtains and labelled schematic guides without moving co-located event sides', () => {
    const raw = result(), { canvas } = install(), display = prepareWaveFieldDisplay(raw, { min: 0, max: 3 }, true, { canvas: () => canvas });
    const sheets: THREE.Mesh[] = [], curtains: THREE.Mesh[] = [], sparseOutlines: THREE.LineSegments[] = [];
    display.group.traverse(object => { if (object.userData.waveFieldSection) sheets.push(object as THREE.Mesh);
      if (object.userData.waveFieldCurtain) curtains.push(object as THREE.Mesh);
      if (object.userData.waveFieldOutline?.category === 'sparse calculated section') sparseOutlines.push(object as THREE.LineSegments); });
    const cursor = display.group.getObjectByName('w1-inspection-cursor')!, guides = display.group.getObjectByName('w1-schematic-guides')!;
    expect((display.snapshot() as any).presentation).toEqual(W1_DEFAULT_PRESENTATION); display.select(3);
    display.setPresentation({ selected: true, sparse: false, curtains: false, guides: false, magnification: 4 });
    expect(sheets.filter(sheet => sheet.visible)).toEqual([sheets[3]]); expect(cursor.visible).toBe(true);
    expect((cursor as THREE.LineSegments).material).toMatchObject({ color: new THREE.Color('#79f3f5'), opacity: 1, depthTest: false });
    expect(cursor.userData.waveFieldOutline.sectionId, 'W11_SELECTED_EVENT_SIDE_IDENTITY').toBe(raw.planes[3].id);
    expect(curtains.every(mesh => !mesh.visible)).toBe(true); expect(guides.visible).toBe(false); expect(sparseOutlines.every(line => !line.visible)).toBe(true);
    display.setPresentation({ selected: false, sparse: true, curtains: false, guides: false, magnification: 4 });
    expect(cursor.visible).toBe(false); expect(sheets.filter(sheet => sheet.visible).length).toBeGreaterThan(1);
    expect(sparseOutlines.filter(line => line.visible)).toHaveLength(sheets.filter(sheet => sheet.visible).length);
    display.setPresentation({ selected: false, sparse: false, curtains: true, guides: false, magnification: 4 });
    expect(sheets.every(sheet => !sheet.visible)).toBe(true); expect(curtains.every(mesh => mesh.visible)).toBe(true);
    display.setPresentation({ selected: false, sparse: false, curtains: false, guides: true, magnification: 4 });
    expect(curtains.every(mesh => !mesh.visible)).toBe(true); expect(guides.visible).toBe(true);
    expect(guides.children.every(child => typeof child.userData.waveFieldGuide === 'string' && child.userData.waveFieldGuide.includes('schematic'))).toBe(true);
    expect(guides.children.some(child => (child as THREE.Line).material instanceof THREE.LineDashedMaterial)).toBe(true);
    expect(sheets[2].getWorldPosition(new THREE.Vector3()).z).toBe(sheets[3].getWorldPosition(new THREE.Vector3()).z);
    expect(sheets.every((sheet, at) => sheet.getWorldPosition(new THREE.Vector3()).z === raw.planes[at].z_m * 100), 'W11_NO_INVENTED_LONGITUDINAL_OFFSET').toBe(true);
    display.dispose();
  });
  it('uses an explicit selected inspection overlay while preserving ordinary depth for sparse sheets and curtains', () => {
    const raw = result(), original = raw.intensities.slice(), x = raw.x.slice(), y = raw.y.slice(), { canvas, paints } = install();
    const display = prepareWaveFieldDisplay(raw, { min: 0, max: 3 }, true, { canvas: () => canvas }), sheets: THREE.Mesh[] = [], curtains: THREE.Mesh[] = [];
    display.group.traverse(object => { if (object.userData.waveFieldSection) sheets.push(object as THREE.Mesh); if (object.userData.waveFieldCurtain) curtains.push(object as THREE.Mesh); });
    display.select(3); display.setPresentation({ selected: true, sparse: true, curtains: true, guides: false, magnification: 4 });
    const bounds = display.framingBounds('section'), detector = (display.detectorTexture.image.data as Uint8Array).slice(), paint = paints.at(-1)!.slice();
    const textures = sheets.concat(curtains).map(mesh => (mesh.material as THREE.MeshBasicMaterial).map);
    const bytes = textures.map(texture => ((texture as THREE.DataTexture).image.data as Uint8Array).slice());
    const ledger = display.snapshot() as any;
    for (const selected of [3, raw.planes.length - 1, 3]) {
      display.select(selected);
      sheets.forEach((mesh, index) => {
        expect((mesh.material as THREE.MeshBasicMaterial).depthTest, index === selected ? 'W11_SELECTED_INSPECTION_OVERLAY' : 'W11_SPARSE_DEPTH_TEST_RESTORED').toBe(index !== selected);
        expect(mesh.renderOrder, 'W11_SELECTED_INSPECTION_DRAW_ORDER').toBe(index === selected ? 10 : 0);
        expect(mesh.getWorldPosition(new THREE.Vector3()).z).toBe(raw.planes[index].z_m * 100);
      });
      expect(curtains.every(mesh => (mesh.material as THREE.MeshBasicMaterial).depthTest && mesh.renderOrder === 0), 'W11_CURTAINS_RETAIN_ORDINARY_DEPTH').toBe(true);
    }
    expect(display.framingBounds('section')).toEqual(bounds); expect(paints.at(-1)).toEqual(paint);
    display.setPresentation({ selected: false, sparse: true, curtains: true, guides: false, magnification: 4 });
    expect(sheets.every(mesh => (mesh.material as THREE.MeshBasicMaterial).depthTest && mesh.renderOrder === 0), 'W11_OVERLAY_DISABLE_RESTORES_ORDINARY_DEPTH').toBe(true);
    display.setPresentation({ selected: true, sparse: true, curtains: true, guides: false, magnification: 4 });
    expect(sheets.concat(curtains).map(mesh => (mesh.material as THREE.MeshBasicMaterial).map)).toEqual(textures);
    textures.forEach((texture, index) => expect((texture as THREE.DataTexture).image.data, 'W11_OVERLAY_NEVER_REWRITES_TEXTURES').toEqual(bytes[index]));
    expect(display.detectorTexture.image.data).toEqual(detector); expect(raw.intensities).toEqual(original); expect(raw.x).toEqual(x); expect(raw.y).toEqual(y);
    const after = display.snapshot() as any;
    for (const key of ['ownedBytes', 'textureSourceBytes', 'geometryBytes', 'canvasBytes', 'textureCount', 'geometryCount']) expect(after[key], 'W11_OVERLAY_NO_ALLOCATION').toBe(ledger[key]);
    expect(display.framingBounds('section')).toEqual(bounds); display.dispose();
  });
  it.each([[4, 3], [5, 4]])('magnifies only transverse display coordinates and preserves exact UV/raw sample identity on a %ix%i grid', (nx, ny) => {
    const raw = result(nx, ny), original = raw.intensities.slice(), x = raw.x.slice(), y = raw.y.slice(), { canvas, paints } = install();
    const display = prepareWaveFieldDisplay(raw, { min: 0, max: 3 }, true, { canvas: () => canvas }), sheets: THREE.Mesh[] = [];
    display.group.traverse(object => { if (object.userData.waveFieldSection) sheets.push(object as THREE.Mesh); });
    display.select(3); const detector = (display.detectorTexture.image.data as Uint8Array).slice(), paint = paints.at(-1)!.slice();
    const row = 0, column = nx - 1, coordinate = pixelCoordinates(raw.experiment.grid, row, column), uv = pixelCenterUV(raw.experiment.grid, row, column);
    const edges = detectorEdges(raw.experiment.grid), mesh = sheets[3];
    for (const magnification of [1, 2, 4, 1] as const) {
      display.setPresentation({ selected: true, sparse: false, curtains: false, guides: false, magnification });
      const local = new THREE.Vector3((uv.u - .5) * edges.width * 1000, (uv.v - .5) * edges.height * 1000, 0), world = mesh.localToWorld(local);
      expect(world.x, 'W11_TRANSVERSE_X_MAPPING').toBeCloseTo(coordinate.x_m * 1000 * magnification, 11);
      expect(world.y, 'W11_TRANSVERSE_AXIS_PIVOT').toBeCloseTo(1 - coordinate.y_m * 1000 * magnification, 11);
      expect(world.z, 'W11_PHYSICAL_Z_UNCHANGED').toBe(raw.planes[3].z_m * 100);
      const hit = new THREE.Raycaster(world.clone().add(new THREE.Vector3(0, 0, 5)), new THREE.Vector3(0, 0, -1)).intersectObject(mesh, false)[0];
      expect(hit).toBeDefined(); expect(pixelFromUV(raw.experiment.grid, hit.uv!.x, hit.uv!.y), 'W11_MAGNIFIED_RAY_PICK_RAW_IDENTITY').toEqual({ row, column });
      expect(sectionSample(raw, 3, row, column).intensity).toBe(original[3 * nx * ny + row * nx + column]);
      const bounds = display.framingBounds('section');
      expect(bounds.min.x).toBeCloseTo(edges.xMin * 1000 * magnification, 5); expect(bounds.max.x).toBeCloseTo(edges.xMax * 1000 * magnification, 5);
      expect(bounds.min.y).toBeCloseTo(1 - edges.yMax * 1000 * magnification, 5); expect(bounds.max.y).toBeCloseTo(1 - edges.yMin * 1000 * magnification, 5);
      expect(bounds.min.z).toBe(bounds.max.z); expect(bounds.min.z).toBe(raw.planes[3].z_m * 100);
      const snapshot = display.snapshot() as any;
      expect(snapshot.selectedPlane).toMatchObject({ id: raw.planes[3].id, stage: 'after:aperture', z_m: .03,
        physicalX_m: [edges.xMin, edges.xMax], physicalY_m: [edges.yMin, edges.yMax] });
      expect(snapshot.presentation.magnification).toBe(magnification);
      expect(display.detectorTexture.image.data, 'W11_DETECTOR_UNMAGNIFIED_UNRECOLORED').toEqual(detector); expect(paints.at(-1)).toEqual(paint);
    }
    expect(raw.intensities).toEqual(original); expect(raw.x).toEqual(x); expect(raw.y).toEqual(y); display.dispose();
  });
  it('frames the transformed visible calculated layers, excludes guides, and retains selected-plane access when every layer is hidden', () => {
    const raw = result(), { canvas } = install(), display = prepareWaveFieldDisplay(raw, { min: 0, max: 3 }, true, { canvas: () => canvas });
    display.select(3); display.setPresentation({ selected: true, sparse: false, curtains: false, guides: true, magnification: 4 });
    expect(display.framingBounds('beam')).toEqual(display.framingBounds('section'));
    display.setPresentation({ selected: false, sparse: false, curtains: true, guides: false, magnification: 4 });
    const beam = display.framingBounds('beam'); expect(beam.min.z).toBe(0); expect(beam.max.z).toBeCloseTo(22, 5);
    const section = display.framingBounds('section'); expect(section.min.z).toBe(3); expect(section.max.z).toBe(3);
    expect(beam.containsBox(section)).toBe(true);
    display.setPresentation({ selected: false, sparse: false, curtains: false, guides: false, magnification: 4 });
    expect(display.framingBounds('beam')).toEqual(section);
    const copy = display.framingBounds('section'); copy.makeEmpty(); expect(display.framingBounds('section').isEmpty()).toBe(false); display.dispose();
  });
  it('reuses every owned texture and geometry through viewing actions and stays within the existing maximum-grid reservation', () => {
    const raw = result(128, 128, true), { canvas } = install(), textureFactory = vi.fn((bytes: Uint8Array, width: number, height: number) => new THREE.DataTexture(bytes, width, height));
    const display = prepareWaveFieldDisplay(raw, { min: 0, max: 3 }, true, { canvas: () => canvas, texture: textureFactory });
    expect(raw.planes).toHaveLength(25);
    const textures = new Set<THREE.Texture>([display.detectorTexture]), geometries = new Set<THREE.BufferGeometry>(), buffers = new Set<ArrayBufferLike>(), textureBuffers = new Set<ArrayBufferLike>();
    display.group.traverse(object => { const mesh = object as THREE.Mesh;
      if (mesh.geometry) { geometries.add(mesh.geometry); if (mesh.geometry.index) buffers.add(mesh.geometry.index.array.buffer); Object.values(mesh.geometry.attributes).forEach(attribute => buffers.add(attribute.array.buffer)); }
      if (mesh.material) for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) { const map = (material as THREE.MeshBasicMaterial).map; if (map) textures.add(map); }
    });
    textures.forEach(texture => textureBuffers.add((texture.image as { data: Uint8Array }).data.buffer));
    expect(display.geometryBytes, 'W11_GUIDE_AND_OUTLINE_BUFFERS_ACCOUNTED').toBe([...buffers].reduce((bytes, buffer) => bytes + buffer.byteLength, 0));
    expect(display.textureSourceBytes).toBe([...textureBuffers].reduce((bytes, buffer) => bytes + buffer.byteLength, 0));
    const reserve = 25 * 128 * 128 * 4 + 128 * 128 * 8 + 25 * (128 + 128) * 8 + 128 * 1024;
    expect(display.ownedBytes, 'W11_EXISTING_DISPLAY_RESERVATION').toBeLessThanOrEqual(reserve);
    const before = display.snapshot() as any, allocations = textureFactory.mock.calls.length;
    for (let index = 0; index < 60; index++) {
      display.setPresentation({ selected: index % 2 === 0, sparse: index % 3 === 0, curtains: index % 4 === 0, guides: index % 5 === 0, magnification: ([1, 2, 4] as const)[index % 3] });
      display.select(index % raw.planes.length); display.framingBounds(index % 2 ? 'beam' : 'section');
    }
    expect(textureFactory).toHaveBeenCalledTimes(allocations); const after = display.snapshot() as any;
    for (const key of ['ownedBytes', 'geometryBytes', 'textureSourceBytes', 'textureCount', 'geometryCount']) expect(after[key], 'W11_VIEW_ACTIONS_NO_RESOURCE_GROWTH').toBe(before[key]);
    const afterGeometries = new Set<THREE.BufferGeometry>(), afterTextures = new Set<THREE.Texture>([display.detectorTexture]);
    display.group.traverse(object => { const mesh = object as THREE.Mesh; if (mesh.geometry) afterGeometries.add(mesh.geometry);
      if (mesh.material) for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) { const map = (material as THREE.MeshBasicMaterial).map; if (map) afterTextures.add(map); } });
    expect(afterGeometries, 'W11_VIEW_ACTIONS_REUSE_GEOMETRIES').toEqual(geometries); expect(afterTextures, 'W11_VIEW_ACTIONS_REUSE_TEXTURES').toEqual(textures); display.dispose();
  });
  it('rejects invalid display options atomically and prevents selecting or framing disposed resources', () => {
    const raw = result(), { canvas } = install(), display = prepareWaveFieldDisplay(raw, { min: 0, max: 3 }, true, { canvas: () => canvas });
    display.setPresentation({ ...W1_DEFAULT_PRESENTATION, magnification: 2 }); const before = display.snapshot();
    for (const options of [null, [], { ...W1_DEFAULT_PRESENTATION, magnification: 3 }, { ...W1_DEFAULT_PRESENTATION, guides: 1 }, { ...W1_DEFAULT_PRESENTATION, extra: true }]) {
      expect(() => display.setPresentation(options as any)).toThrow('Expected bounded W1'); expect(display.snapshot()).toEqual(before);
    }
    expect(() => display.framingBounds('unknown' as any)).toThrow(); display.dispose();
    expect(() => display.setPresentation(W1_DEFAULT_PRESENTATION)).toThrow('disposed'); expect(() => display.framingBounds('section')).toThrow(); expect(() => display.select(0)).toThrow();
  });
  it('disposes every owned texture/geometry/material exactly once across replacement and cleans partial preparation', () => {
    const raw = result(), { canvas } = install(), display = prepareWaveFieldDisplay(raw, { min: 0, max: 3 }, true, { canvas: () => canvas });
    const owned = new Set<THREE.BufferGeometry | THREE.Material | THREE.Texture>([display.detectorTexture]);
    display.group.traverse(object => { const mesh = object as THREE.Mesh; if (mesh.geometry) owned.add(mesh.geometry);
      if (mesh.material) for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) { owned.add(material); const map = (material as THREE.MeshBasicMaterial).map; if (map) owned.add(map); } });
    const spies = [...owned].map(object => { const spy = vi.fn(); object.addEventListener('dispose' as never, spy); return spy; });
    expect(display.ownedBytes).toBeGreaterThan(display.textureSourceBytes); display.dispose(); display.dispose(); spies.forEach(spy => expect(spy, 'W1_DETECT_RESOURCE_LEAK').toHaveBeenCalledOnce());
    expect(display.ownedBytes).toBe(0); expect(canvas.width).toBe(0); expect(display.group.children).toHaveLength(0);
    const failed = install(true), disposed: ReturnType<typeof vi.fn>[] = [];
    expect(() => prepareWaveFieldDisplay(raw, { min: 0, max: 3 }, true, { canvas: () => failed.canvas, texture(bytes, width, height) {
      const texture = new THREE.DataTexture(bytes, width, height); const spy = vi.fn(); texture.addEventListener('dispose', spy); disposed.push(spy); return texture; } })).toThrow('preparation');
    expect(disposed.length).toBeGreaterThan(5); disposed.forEach(spy => expect(spy).toHaveBeenCalledOnce()); expect(failed.canvas.width).toBe(0);
  });
});

// Constructor DOM bindings route both the real cursor's input and section select's
// change to this production method. Stub only its owned DOM/resource collaborators.
import { WaveFieldWorkspace } from '../src/wave_field_workspace';
it('the actual longitudinal cursor handler selects cached raw data without invoking numerical propagation', () => {
  const raw = result(), original = raw.intensities.slice(), simulate = vi.fn(), select = vi.fn(), updateReadout = vi.fn();
  const workspace = Object.create(WaveFieldWorkspace.prototype) as any;
  workspace.controller = { state: { currentResult: raw }, simulate };
  workspace.resource = { result: raw, select }; workspace.updateReadout = updateReadout; workspace.section = 0;
  workspace.select(3);
  expect(workspace.section, 'W1_CURSOR_SELECTS_ACTUAL_RETURNED_SECTION').toBe(3);
  expect(select).toHaveBeenCalledExactlyOnceWith(3); expect(updateReadout).toHaveBeenCalledOnce();
  expect(raw.planes[3].id).toBe('section:after:aperture'); expect(raw.intensities).toEqual(original);
  expect(simulate, 'W1_CURSOR_NO_PROPAGATION').not.toHaveBeenCalled();
});
