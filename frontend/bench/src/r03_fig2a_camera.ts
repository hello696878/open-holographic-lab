/** Presentation-only perspective framing. No optical geometry or propagation. */
import * as THREE from 'three';

export type ResearchCameraView = 'overview' | 'top' | 'focus';
export interface ResearchCameraFit {
  readonly view: ResearchCameraView;
  readonly position: THREE.Vector3;
  readonly target: THREE.Vector3;
  readonly up: THREE.Vector3;
  readonly near: number;
  readonly far: number;
  readonly minDistance: number;
  readonly maxDistance: number;
  readonly distance: number;
  readonly aspect: number;
  readonly usableNDC: number;
  readonly topTiltRad: number;
}

/** Keep the existing OrbitControls world-up basis; top's screen-up is -Z.
 *
 * OrbitControls caches its world-up transform at construction. A direction
 * 0.0001 rad (atan(0.0001), about 0.00573 degrees) off the +Y pole avoids
 * its singularity without changing camera.up, private controls, or renderer.
 * This is a display choice, not an apparatus angle or optical parameter.
 */
export const RESEARCH_TOP_TILT_RAD = Math.atan(1e-4);
export const RESEARCH_USABLE_NDC = 0.88;
const WORLD_UP = new THREE.Vector3(0, 1, 0);
const OVERVIEW_DIRECTION = new THREE.Vector3(0.8, 0.85, 1.15).normalize();

export function researchBoundsCorners(bounds: THREE.Box3): THREE.Vector3[] {
  if (!(bounds instanceof THREE.Box3) || bounds.isEmpty()
      || [...bounds.min.toArray(), ...bounds.max.toArray()].some(v => !Number.isFinite(v))) {
    throw new Error('Research framing requires finite nonempty optical-component bounds');
  }
  const corners: THREE.Vector3[] = [];
  for (const x of [bounds.min.x, bounds.max.x]) for (const y of [bounds.min.y, bounds.max.y]) {
    for (const z of [bounds.min.z, bounds.max.z]) corners.push(new THREE.Vector3(x, y, z));
  }
  return corners;
}

/** Fit all eight corners using horizontal AND vertical perspective constraints.
 *
 * The bounds are supplied by optical component assemblies, excluding the
 * oversized table, labels, lights and selection decorations. Neither bounds
 * nor camera is changed. For camera-back direction d and corner offset v,
 * depth = distance - dot(v,d). Requiring abs(x)/depth <= usableNDC*tan(hFov/2)
 * and the analogous vertical inequality gives a direct distance lower bound
 * for each corner, including its depth. No iterative fit or hand framing.
 * Focus preserves the caller's viewing direction; overview/top are explicit.
 */
export function calculateResearchCameraFit(
  bounds: THREE.Box3, camera: THREE.PerspectiveCamera, view: ResearchCameraView,
  focusDirection?: THREE.Vector3,
): ResearchCameraFit {
  const corners = researchBoundsCorners(bounds);
  if (!(camera instanceof THREE.PerspectiveCamera) || !Number.isFinite(camera.fov) || camera.fov <= 0 || camera.fov >= 179
      || !Number.isFinite(camera.aspect) || camera.aspect <= 0 || !Number.isFinite(camera.zoom) || camera.zoom <= 0) {
    throw new Error('Research framing requires a usable perspective field of view, aspect and zoom');
  }
  if (!['overview', 'top', 'focus'].includes(view)) throw new Error('Unknown research camera view');
  if (camera.filmOffset !== 0 || camera.view?.enabled) throw new Error('Research framing does not support an offset projection');
  const center = bounds.getCenter(new THREE.Vector3()), size = bounds.getSize(new THREE.Vector3());
  if ([...center.toArray(), ...size.toArray()].some(v => !Number.isFinite(v))) throw new Error('Research bounds exceed usable display arithmetic');
  // A minimum visual span makes a point/thin selected part navigable. It never
  // changes a component, model dimension or the supplied authoritative bounds.
  const span = Math.max(size.x, size.y, size.z, 0.25);
  let direction = view === 'top' ? new THREE.Vector3(0, 1, 1e-4).normalize()
    : view === 'focus' && focusDirection ? focusDirection.clone() : OVERVIEW_DIRECTION.clone();
  if (direction.toArray().some(v => !Number.isFinite(v)) || direction.lengthSq() === 0) throw new Error('Research focus requires a finite nonzero view direction');
  direction.normalize();
  // Explicitly avoid a focus exactly parallel to world-up as well. This is
  // the same near-pole display convention, never a new controls instance.
  if (Math.abs(direction.dot(WORLD_UP)) > 1 - 1e-10) direction = new THREE.Vector3(0, Math.sign(direction.y), 1e-4).normalize();
  const right = new THREE.Vector3().crossVectors(WORLD_UP, direction).normalize();
  const screenUp = new THREE.Vector3().crossVectors(direction, right).normalize();
  const tanVertical = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) / camera.zoom;
  const tanHorizontal = tanVertical * camera.aspect;
  if (![tanVertical, tanHorizontal].every(v => Number.isFinite(v) && v > 0)) throw new Error('Research projection slopes are unusable');
  let distance = span * 0.5;
  for (const point of corners) {
    const offset = point.clone().sub(center), z = offset.dot(direction);
    distance = Math.max(distance,
      z + Math.abs(offset.dot(right)) / (tanHorizontal * RESEARCH_USABLE_NDC),
      z + Math.abs(offset.dot(screenUp)) / (tanVertical * RESEARCH_USABLE_NDC),
      z + span * 0.1);
  }
  // A small explicit margin absorbs projection/OrbitControls arithmetic; the
  // actual usable screen fraction remains bounded by the declared 0.88.
  distance *= 1 + 1e-6;
  const minDistance = Math.max(span * 0.02, 0.005);
  const maxDistance = Math.max(distance * 8, span * 10, 2);
  // Near must not be needlessly close to zero: perspective depth precision
  // then collapses at apparatus distance and distinct housing/phase surfaces
  // fight. This lies below minDistance and below the fitted nearest-corner
  // clearance, while keeping a useful depth ratio at the tested viewports.
  const near = Math.max(span * 0.01, 0.001);
  const far = maxDistance + span * 2;
  const position = center.clone().addScaledVector(direction, distance);
  if ([...position.toArray(), distance, near, far, minDistance, maxDistance].some(v => !Number.isFinite(v)) || near >= far) {
    throw new Error('Research framing produced unusable camera limits');
  }
  return { view, position, target: center, up: WORLD_UP.clone(), near, far, minDistance, maxDistance,
    distance, aspect: camera.aspect, usableNDC: RESEARCH_USABLE_NDC, topTiltRad: view === 'top' ? RESEARCH_TOP_TILT_RAD : 0 };
}
