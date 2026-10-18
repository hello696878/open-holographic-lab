import { afterEach, describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { cloneExperiment } from '../src/contracts';
import { intensityRGBA } from '../src/detector';
import { curtainBandPlan, formatWaveFieldNumber, prepareWaveFieldDisplay, sectionRGBA, sectionSample, waveFieldColor } from '../src/wave_field_display';
import { waveFieldPlan, waveFieldSection, W1_EXAMPLE, type WaveFieldResult } from '../src/wave_field_contracts';

function result(): WaveFieldResult {
  const experiment = cloneExperiment(W1_EXAMPLE); experiment.grid = { nx: 4, ny: 3, dx: .001, dy: .002 };
  const sampling = { interior_z_m: [.015, .045, .12] }, plan = waveFieldPlan(experiment, sampling);
  const intensities = Float64Array.from(plan.flatMap(plane => Array.from({ length: 12 }, (_, pixel) => (pixel + 1) / 10 * (plane.z_m >= .03 && !plane.stage.startsWith('before:aperture') ? .25 : 1))));
  const planes = plan.map((plane, index) => ({ ...plane, norm: index < 3 ? 12 : 3, previous_norm: index ? 12 : null,
    delta_norm: index ? index < 3 ? 0 : -9 : null, transmission_ratio: index ? index < 3 ? 1 : .25 : null,
    on_axis_intensity: intensities[index * 12 + 6], max_intensity: intensities[index * 12 + 11] }));
  return { requestId: 'display-only-unit-fixture', experimentSha256: 'a'.repeat(64), experiment, sampling, planes, stages: [], intensities,
    x: Float64Array.from([-.002, -.001, 0, .001]), y: Float64Array.from([-.002, 0, .002]) };
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
