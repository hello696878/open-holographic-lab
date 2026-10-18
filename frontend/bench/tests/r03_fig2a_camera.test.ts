import { afterEach, describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { BenchScene } from '../src/scene';
import { calculateResearchCameraFit, RESEARCH_TOP_TILT_RAD, RESEARCH_USABLE_NDC } from '../src/r03_fig2a_camera';

function camera(aspect: number, zoom = 1): THREE.PerspectiveCamera {
  const camera = new THREE.PerspectiveCamera(42, aspect, .001, 1000); camera.zoom = zoom; camera.updateProjectionMatrix(); return camera;
}
function apply(camera: THREE.PerspectiveCamera, fit: ReturnType<typeof calculateResearchCameraFit>): void {
  camera.position.copy(fit.position); camera.up.copy(fit.up); camera.near = fit.near; camera.far = fit.far;
  camera.lookAt(fit.target); camera.updateProjectionMatrix(); camera.updateMatrixWorld(true);
}
/** Independent corner enumeration/projection uses Three's actual camera matrix. */
function verifyCorners(bounds: THREE.Box3, camera: THREE.PerspectiveCamera): void {
  for (let mask = 0; mask < 8; mask++) {
    const point = new THREE.Vector3(mask & 1 ? bounds.max.x : bounds.min.x, mask & 2 ? bounds.max.y : bounds.min.y, mask & 4 ? bounds.max.z : bounds.min.z).project(camera);
    expect(Math.abs(point.x), 'horizontal projection fit').toBeLessThanOrEqual(RESEARCH_USABLE_NDC + 1e-12);
    expect(Math.abs(point.y), 'vertical projection fit').toBeLessThanOrEqual(RESEARCH_USABLE_NDC + 1e-12);
    expect(point.z, 'near clipping').toBeGreaterThan(-1); expect(point.z, 'far clipping').toBeLessThan(1);
  }
}
const apparatus = new THREE.Box3(new THREE.Vector3(-3.2, .05, -2.75), new THREE.Vector3(4.25, 1.75, .7));

/** Exercise the real public scene camera methods and actual OrbitControls,
 * without constructing a WebGL renderer or inventing scientific fixtures. */
function sceneFixture() {
  vi.stubGlobal('window', { devicePixelRatio: 1 });
  const c = camera(4/3); c.position.set(2, 3, 7); c.near = .003; c.far = 320;
  const eventDocument = { addEventListener: vi.fn(), removeEventListener: vi.fn() };
  const eventElement = { addEventListener: vi.fn(), removeEventListener: vi.fn(), ownerDocument: eventDocument,
    getRootNode: () => eventDocument, style: {}, clientWidth: 700, clientHeight: 560 };
  const controls = new OrbitControls(c, eventElement as unknown as HTMLElement); controls.enableDamping = true; controls.target.set(.2, .3, .4);
  controls.minDistance = .07; controls.maxDistance = 180; controls.update();
  const ordinaryHost = { clientWidth: 800, clientHeight: 600, append: vi.fn() };
  const researchHost = { clientWidth: 700, clientHeight: 560, append: vi.fn() };
  const scene = Object.create(BenchScene.prototype) as BenchScene;
  const state = scene as unknown as Record<string, any>;
  Object.assign(state, { camera: c, controls, host: ordinaryHost, canvas: {},
    scene: new THREE.Scene(), bench: new THREE.Group(), rail: new THREE.Group(),
    renderer: { setPixelRatio: vi.fn(), setSize: vi.fn() }, resizeObserver: { observe: vi.fn(), unobserve: vi.fn() },
    researchGroup: null, researchHost: null, oldCamera: null, researchCamera: null,
    researchOverviewBounds: null, researchFraming: null, researchFitCount: 0, researchLabelUpdater: null,
    lost: false, disposed: false, cancelDrag: () => { controls.enabled = true; },
  });
  return { scene, state, c, controls, researchHost, group: new THREE.Group() };
}
afterEach(() => vi.unstubAllGlobals());

describe('research-only projection-aware camera fit', () => {
  it.each([.55, .85, 1, 1.6, 2.3])('fits all apparatus corners at aspect %s in both explicit views', aspect => {
    for (const view of ['overview', 'top'] as const) {
      const c = camera(aspect), fit = calculateResearchCameraFit(apparatus, c, view); apply(c, fit); verifyCorners(apparatus, c);
      expect(fit.near).toBeGreaterThan(0); expect(fit.far).toBeGreaterThan(fit.maxDistance);
      expect(fit.minDistance).toBeLessThan(fit.distance); expect(fit.maxDistance).toBeGreaterThan(fit.distance);
    }
  });
  it('uses both viewport axes instead of a width-only or fixed-distance rule', () => {
    const wide = new THREE.Box3(new THREE.Vector3(-4, -.1, -.1), new THREE.Vector3(4, .1, .1));
    const tall = new THREE.Box3(new THREE.Vector3(-.1, -4, -.1), new THREE.Vector3(.1, 4, .1));
    expect(calculateResearchCameraFit(wide, camera(.55), 'overview').distance).toBeGreaterThan(calculateResearchCameraFit(wide, camera(2), 'overview').distance);
    const c = camera(2); apply(c, calculateResearchCameraFit(tall, c, 'overview')); verifyCorners(tall, c);
  });
  it.each([.4, 1, 2.5])('respects the current perspective zoom %s', zoom => {
    const c = camera(1.1, zoom); apply(c, calculateResearchCameraFit(apparatus, c, 'overview')); verifyCorners(apparatus, c);
  });
  it.each([.55, 1, 2.3])('keeps useful depth precision at aspect %s and all corners visible at maximum orbit distance', aspect => {
    const c = camera(aspect), fit = calculateResearchCameraFit(apparatus, c, 'overview'); apply(c, fit);
    const span = Math.max(...apparatus.getSize(new THREE.Vector3()).toArray());
    expect(fit.near).toBeGreaterThanOrEqual(span*.01); expect(fit.near).toBeLessThan(fit.minDistance);
    // Representative desktop projection cases, not a universal GPU precision
    // guarantee. The former span*1e-5 plane yielded a ratio above one million.
    expect(fit.far/fit.near).toBeLessThan(5000); verifyCorners(apparatus,c);
    const direction = c.position.clone().sub(fit.target).normalize();
    c.position.copy(fit.target).addScaledVector(direction,fit.maxDistance); c.lookAt(fit.target); c.updateMatrixWorld(true);
    verifyCorners(apparatus,c);
    const selected = new THREE.Box3(new THREE.Vector3(.8,.5,-.2),new THREE.Vector3(1.2,1.2,.3));
    const focus = calculateResearchCameraFit(selected,c,'focus',direction); apply(c,focus); verifyCorners(selected,c);
    expect(focus.near).toBeLessThan(focus.minDistance); expect(focus.far/focus.near).toBeLessThan(5000);
    c.position.copy(focus.target).addScaledVector(direction,focus.maxDistance); c.lookAt(focus.target); c.updateMatrixWorld(true); verifyCorners(selected,c);
  });
  it('top screen-up is north (-Z) without replacing OrbitControls cached world-up', () => {
    const c = camera(1.2), fit = calculateResearchCameraFit(apparatus, c, 'top'); apply(c, fit);
    expect(c.up.toArray()).toEqual([0, 1, 0]); expect(fit.topTiltRad).toBe(RESEARCH_TOP_TILT_RAD);
    expect(THREE.MathUtils.radToDeg(fit.topTiltRad)).toBeCloseTo(.00572957793, 10);
    const screenUp = new THREE.Vector3(0, 1, 0).applyQuaternion(c.quaternion);
    expect(screenUp.dot(new THREE.Vector3(0, 0, -1))).toBeGreaterThan(.99999999);
    expect(fit.position.clone().sub(fit.target).normalize().y).toBeGreaterThan(.99999999);
  });
  it('explicit focus keeps the selected viewing direction and handles small/point bounds', () => {
    const direction = new THREE.Vector3(-.5, .7, 1.2).normalize();
    for (const box of [new THREE.Box3(new THREE.Vector3(.1, .8, .1), new THREE.Vector3(.3, 1, .3)), new THREE.Box3(new THREE.Vector3(1, 2, 3), new THREE.Vector3(1, 2, 3))]) {
      const c = camera(.8), fit = calculateResearchCameraFit(box, c, 'focus', direction); apply(c, fit); verifyCorners(box, c);
      expect(fit.position.clone().sub(fit.target).normalize().distanceTo(direction)).toBeLessThan(1e-12);
      expect(fit.distance).toBeGreaterThan(0); expect(fit.near).toBeGreaterThan(0);
    }
  });
  it('does not mutate input bounds/camera or fit implicitly after projection changes', () => {
    const c = camera(1), before = c.toJSON(), bounds = apparatus.clone();
    const fit = calculateResearchCameraFit(apparatus, c, 'overview'); expect(c.toJSON()).toEqual(before); expect(apparatus.equals(bounds)).toBe(true);
    apply(c, fit); const position = c.position.clone(); c.aspect = .7; c.updateProjectionMatrix();
    expect(c.position.equals(position)).toBe(true); expect(fit.aspect).toBe(1);
  });
  it.each([new THREE.Box3(), new THREE.Box3(new THREE.Vector3(NaN, 0, 0), new THREE.Vector3(1, 1, 1)), new THREE.Box3(new THREE.Vector3(0, 0, 0), new THREE.Vector3(Infinity, 1, 1))])('rejects invalid bounds without inventing a fit', bounds => {
    expect(() => calculateResearchCameraFit(bounds, camera(1), 'overview')).toThrow();
  });
  it.each([0, -1, Infinity, NaN])('rejects invalid projection aspect %s', aspect => {
    expect(() => calculateResearchCameraFit(apparatus, camera(aspect), 'overview')).toThrow();
  });
  it('rejects an offset projection rather than silently applying a symmetric approximation', () => {
    const c = camera(1); c.filmOffset = 1; expect(() => calculateResearchCameraFit(apparatus, c, 'overview')).toThrow('offset');
  });
  it('fits through the one actual OrbitControls instance, including stable top direction', () => {
    const { scene, c, controls, researchHost, group } = sceneFixture();
    scene.showResearchApparatus(researchHost as unknown as HTMLElement, group);
    for (const view of ['overview', 'top', 'focus'] as const) {
      scene.fitResearchApparatus(apparatus, view); verifyCorners(apparatus, c);
      const position = c.position.clone(); for (let i = 0; i < 20; i++) controls.update(); c.updateMatrixWorld(true);
      expect(c.position.distanceTo(position)).toBeLessThan(1e-10); expect(c.up.toArray()).toEqual([0, 1, 0]); verifyCorners(apparatus, c);
    }
    controls.dispose();
  });
  it('restores ordinary camera isolation and preserves A view on reentry without another fit', () => {
    const { scene, state, c, controls, researchHost, group } = sceneFixture();
    const old = { position: c.position.clone(), target: controls.target.clone(), up: c.up.clone(), near: c.near, far: c.far,
      min: controls.minDistance, max: controls.maxDistance };
    scene.showResearchApparatus(researchHost as unknown as HTMLElement, group); scene.fitResearchApparatus(apparatus, 'top');
    scene.setResearchLabelUpdater(() => {}); const research = { position: c.position.clone(), target: controls.target.clone(), near: c.near, far: c.far };
    scene.hideResearchApparatus();
    expect(state.researchLabelUpdater).toBeNull(); expect(c.position.distanceTo(old.position)).toBeLessThan(1e-12);
    expect(controls.target.equals(old.target)).toBe(true); expect(c.up.equals(old.up)).toBe(true);
    expect([c.near,c.far,controls.minDistance,controls.maxDistance]).toEqual([old.near,old.far,old.min,old.max]);
    scene.showResearchApparatus(researchHost as unknown as HTMLElement, group);
    expect(c.position.distanceTo(research.position)).toBeLessThan(1e-10); expect(controls.target.equals(research.target)).toBe(true);
    expect([c.near,c.far]).toEqual([research.near,research.far]); expect(state.researchFitCount).toBe(1); controls.dispose();
  });
  it('resize changes projection only, while explicit reset restores full apparatus bounds', () => {
    const { scene, state, c, controls, researchHost, group } = sceneFixture();
    scene.showResearchApparatus(researchHost as unknown as HTMLElement, group); scene.fitResearchApparatus(apparatus, 'overview');
    const selected = new THREE.Box3(new THREE.Vector3(.8,.5,-.2),new THREE.Vector3(1.2,1.2,.3)); scene.fitResearchApparatus(selected, 'focus');
    const position = c.position.clone(), target = controls.target.clone(); researchHost.clientWidth = 410; state.resize();
    expect(state.researchFitCount).toBe(2); expect(c.position.equals(position)).toBe(true); expect(controls.target.equals(target)).toBe(true);
    scene.resetCamera(); expect(state.researchFitCount).toBe(3); expect(state.researchFraming.view).toBe('overview');
    expect(state.researchFraming.bounds.equals(apparatus)).toBe(true); verifyCorners(apparatus, c); controls.dispose();
  });
});
