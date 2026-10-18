/** Schematic viewing geometry only: no source, lens or propagation computation. */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { Experiment, DecodedResult } from './contracts';
import { structuralEqual } from './contracts';
import { detectorEdges, pixelFromUV, worldPosition } from './mapping';
import { createDetectorTexture, prepareDualTextures, type ColorLimits } from './detector';
import type { DecodedTwoPathResult, TwoPathExperiment } from './two_path_contracts';
import type { DecodedPolarizationResult, PolarizationExperiment } from './polarization_contracts';
import type { DecodedPolarizedTwoPathResult, PolarizedTwoPathExperiment } from './polarized_two_path_contracts';
import { calculateResearchCameraFit, researchBoundsCorners, type ResearchCameraView } from './r03_fig2a_camera';

export interface SceneCallbacks {
  select: (ids: string[]) => void;
  pixel: (row: number, column: number) => void;
  dualPixel?: (port: 0 | 1, row: number, column: number) => void;
  polarizationPixel?: (view: 0 | 1, row: number, column: number) => void;
  polarizedTwoPathPixel?: (view: 'raw' | 'analyzed', port: 0 | 1, row: number, column: number) => void;
  commitZ: (id: string, z_m: number) => void;
  notice: (message: string) => void;
  presentationFailure: (message: string | null) => void;
}

type DetectorMesh = THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial>;

export class BenchScene {
  readonly canvas: HTMLCanvasElement;
  private readonly renderer: THREE.WebGLRenderer;
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(42, 1, 0.001, 1000);
  private readonly controls: OrbitControls;
  private readonly bench = new THREE.Group();
  private readonly rail = new THREE.Group();
  private readonly geometries = new Set<THREE.BufferGeometry>();
  private readonly materials = new Set<THREE.Material>();
  private readonly textures = new Set<THREE.Texture>();
  private readonly callbacks: SceneCallbacks;
  private readonly resizeObserver: ResizeObserver;
  private readonly raycaster = new THREE.Raycaster();
  private readonly pointer = new THREE.Vector2();
  private experiment: Experiment | null = null;
  private mode: 'sequential' | 'two_path' | 'polarization' | 'polarized_two_path' = 'sequential';
  private polarizedTwoPathExperiment: PolarizedTwoPathExperiment | null = null;
  private polarizedTwoPathDetectors: readonly [DetectorMesh, DetectorMesh] | null = null;
  private polarizedTwoPathTextures: readonly THREE.DataTexture[] | null = null;
  private polarizedTwoPathResult: DecodedPolarizedTwoPathResult | null = null;
  private polarizedTwoPathView: 'raw' | 'analyzed' = 'raw';
  private resultGeneration = 0;
  private polarizationExperiment: PolarizationExperiment | null = null;
  private polarizationDetectors: readonly [DetectorMesh, DetectorMesh] | null = null;
  private polarizationTextures: readonly [THREE.DataTexture, THREE.DataTexture] | null = null;
  private polarizationResult: DecodedPolarizationResult | null = null;
  private frameCallback: ((time: number) => void) | null = null;
  private twoPathExperiment: TwoPathExperiment | null = null;
  private dualDetectors: readonly [DetectorMesh, DetectorMesh] | null = null;
  private dualTextures: readonly [THREE.DataTexture, THREE.DataTexture] | null = null;
  private dualResult: DecodedTwoPathResult | null = null;
  private dualColorKey = '';
  private selection = 'source';
  private detector: DetectorMesh | null = null;
  private texture: THREE.DataTexture | null = null;
  private result: DecodedResult | null = null;
  private colorKey = '';
  private handle: THREE.Mesh | null = null;
  private railX = 0;
  private drag: { id: string; z_m: number; valid: boolean } | null = null;
  private down: { x: number; y: number } | null = null;
  private frame = 0;
  private lost = false;
  private disposed = false;
  private researchGroup: THREE.Group | null = null;
  private researchHost: HTMLElement | null = null;
  private oldCamera: { position: THREE.Vector3; target: THREE.Vector3; up: THREE.Vector3; near: number; far: number; minDistance: number; maxDistance: number } | null = null;
  private researchCamera: { position: THREE.Vector3; target: THREE.Vector3; up: THREE.Vector3; near: number; far: number; minDistance: number; maxDistance: number } | null = null;
  private researchOverviewBounds: THREE.Box3 | null = null;
  private researchFraming: { view: ResearchCameraView; bounds: THREE.Box3; aspect: number; topTiltRad: number } | null = null;
  private researchFitCount = 0;
  private researchLabelUpdater: ((camera: THREE.PerspectiveCamera, width: number, height: number) => void) | null = null;
  private initializedCamera = false;
  private draftValidated = false;
  private readonly onPointerDown: (event: PointerEvent) => void;
  private readonly onPointerMove: (event: PointerEvent) => void;
  private readonly onPointerUp: (event: PointerEvent) => void;
  private readonly onPointerCancel: (event: PointerEvent) => void;
  private readonly onContextLost: (event: Event) => void;
  private readonly onContextRestored: () => void;

  constructor(private readonly host: HTMLElement, callbacks: SceneCallbacks) {
    this.callbacks = callbacks;
    this.canvas = document.createElement('canvas');
    this.canvas.dataset.testid = 'bench-canvas';
    this.canvas.setAttribute('aria-label', '互動式 3D 光學實驗台');
    const context = this.canvas.getContext('webgl2', {
      antialias: true, alpha: false, preserveDrawingBuffer: true,
    });
    if (!context) throw new Error('此瀏覽器無法建立 WebGL2；3D 實驗台不可用。沒有產生替代模擬。');
    this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, context, antialias: true });
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.NoToneMapping;
    this.raycaster.params.Line.threshold = 0.015;
    this.scene.background = new THREE.Color('#f1f6fa');
    this.scene.add(this.bench, this.rail);
    this.controls = new OrbitControls(this.camera, this.canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.12;
    this.controls.minDistance = 0.05;
    this.controls.maxDistance = 200;
    this.host.append(this.canvas);

    this.onPointerDown = (event) => this.pointerDown(event);
    this.onPointerMove = (event) => this.pointerMove(event);
    this.onPointerUp = (event) => this.pointerUp(event);
    this.onPointerCancel = () => this.cancelDrag();
    this.onContextLost = (event) => {
      event.preventDefault();
      this.lost = true;
      this.cancelDrag();
      this.frameCallback = null;
      this.detachPolarizationResult();
      this.detachPolarizedTwoPathResult();
      this.callbacks.presentationFailure('WebGL2 顯示內容已遺失；數值結果保留，不會自動重算。');
    };
    this.onContextRestored = () => {
      this.lost = false;
      this.callbacks.presentationFailure(null);
    };
    // Capture intercepts only the dedicated rail handle, leaving ordinary orbit intact.
    this.canvas.addEventListener('pointerdown', this.onPointerDown, true);
    this.canvas.addEventListener('pointermove', this.onPointerMove, true);
    this.canvas.addEventListener('pointerup', this.onPointerUp, true);
    this.canvas.addEventListener('pointercancel', this.onPointerCancel, true);
    this.canvas.addEventListener('webglcontextlost', this.onContextLost);
    this.canvas.addEventListener('webglcontextrestored', this.onContextRestored);
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(host);
    this.resize();
    this.animate();
  }

  private geometry<T extends THREE.BufferGeometry>(geometry: T): T {
    this.geometries.add(geometry);
    return geometry;
  }

  private material<T extends THREE.Material>(material: T): T {
    this.materials.add(material);
    return material;
  }

  private settleResearchCameraMotion(): void {
    const damping = this.controls.enableDamping;
    this.controls.enableDamping = false;
    try { this.controls.update(); } finally { this.controls.enableDamping = damping; }
  }

  /** Reuse the one renderer; research geometry/resources remain owned by its workspace. */
  showResearchApparatus(host: HTMLElement, group: THREE.Group): void {
    if (this.disposed || this.lost) throw new Error('Shared WebGL2 renderer unavailable');
    if (!this.researchGroup) {
      this.cancelDrag(); this.frameCallback = null; this.settleResearchCameraMotion();
      this.oldCamera = { position: this.camera.position.clone(), target: this.controls.target.clone(), up: this.camera.up.clone(), near: this.camera.near,
        far: this.camera.far, minDistance: this.controls.minDistance, maxDistance: this.controls.maxDistance };
      this.researchGroup = group; this.scene.add(group); this.bench.visible = this.rail.visible = false;
      this.scene.background = new THREE.Color('#122c3b'); this.camera.near = .01; this.camera.far = 100; this.controls.maxDistance = 40;
      this.camera.position.copy(this.researchCamera?.position ?? new THREE.Vector3(5.3, 5.8, 7.4));
      this.controls.target.copy(this.researchCamera?.target ?? new THREE.Vector3(.2, .5, -.15));
      this.camera.up.copy(this.researchCamera?.up ?? new THREE.Vector3(0, 1, 0));
      if (this.researchCamera) { this.camera.near = this.researchCamera.near; this.camera.far = this.researchCamera.far;
        this.controls.minDistance = this.researchCamera.minDistance; this.controls.maxDistance = this.researchCamera.maxDistance; }
      const damping = this.controls.enableDamping; this.controls.enableDamping = false; this.controls.update(); this.controls.enableDamping = damping;
    } else if (this.researchGroup !== group) throw new Error('Another research apparatus is already attached');
    this.researchHost = host; host.append(this.canvas); this.resizeObserver.observe(host); this.resize();
  }

  hideResearchApparatus(): void {
    if (!this.researchGroup) return;
    this.settleResearchCameraMotion();
    this.researchCamera = { position: this.camera.position.clone(), target: this.controls.target.clone(), up: this.camera.up.clone(),
      near: this.camera.near, far: this.camera.far, minDistance: this.controls.minDistance, maxDistance: this.controls.maxDistance };
    this.researchLabelUpdater = null;
    this.researchGroup.removeFromParent(); this.researchGroup = null;
    if (this.researchHost) this.resizeObserver.unobserve(this.researchHost); this.researchHost = null;
    this.host.append(this.canvas); this.bench.visible = this.rail.visible = true; this.scene.background = new THREE.Color('#f1f6fa');
    if (this.oldCamera) { this.camera.position.copy(this.oldCamera.position); this.controls.target.copy(this.oldCamera.target);
      this.camera.up.copy(this.oldCamera.up); this.camera.near = this.oldCamera.near; this.camera.far = this.oldCamera.far;
      this.controls.minDistance = this.oldCamera.minDistance; this.controls.maxDistance = this.oldCamera.maxDistance;
      const damping = this.controls.enableDamping; this.controls.enableDamping = false; this.controls.update(); this.controls.enableDamping = damping; }
    this.oldCamera = null; this.resize();
  }

  assertResearchReady(): void { if (!this.researchGroup || this.lost || this.disposed) throw new Error('Shared research renderer is unavailable; numerical data retained'); }

  /** Called only on initial research entry or an explicit view command. */
  fitResearchApparatus(bounds: THREE.Box3, view: ResearchCameraView): void {
    this.assertResearchReady();
    const fit = calculateResearchCameraFit(bounds, this.camera, view,
      view === 'focus' ? this.camera.position.clone().sub(this.controls.target) : undefined);
    if (view !== 'focus') this.researchOverviewBounds = bounds.clone();
    const damping = this.controls.enableDamping;
    // Public update with damping disabled consumes outstanding gesture deltas
    // before assigning this explicit view; no private controls manipulation.
    this.controls.enableDamping = false;
    try {
      this.controls.update();
      this.camera.position.copy(fit.position); this.camera.up.copy(fit.up); this.controls.target.copy(fit.target);
      this.camera.near = fit.near; this.camera.far = fit.far;
      this.controls.minDistance = fit.minDistance; this.controls.maxDistance = fit.maxDistance;
      this.camera.updateProjectionMatrix(); this.controls.update(); this.camera.updateMatrixWorld(true);
    } finally { this.controls.enableDamping = damping; }
    this.researchFraming = { view, bounds: bounds.clone(), aspect: fit.aspect, topTiltRad: fit.topTiltRad };
    ++this.researchFitCount;
  }

  /** Shares the existing frame loop; cleared automatically on research leave. */
  setResearchLabelUpdater(callback: ((camera: THREE.PerspectiveCamera, width: number, height: number) => void) | null): void {
    this.researchLabelUpdater = callback;
  }

  private disposeGroup(group: THREE.Group): void {
    const geometries = new Set<THREE.BufferGeometry>();
    const materials = new Set<THREE.Material>();
    group.traverse((object) => {
      const drawable = object as THREE.Mesh;
      if (drawable.geometry) geometries.add(drawable.geometry);
      if (drawable.material) {
        for (const material of Array.isArray(drawable.material) ? drawable.material : [drawable.material]) {
          materials.add(material);
        }
      }
    });
    group.clear();
    for (const geometry of geometries) { geometry.dispose(); this.geometries.delete(geometry); }
    for (const material of materials) { material.dispose(); this.materials.delete(material); }
  }

  private ensureDisplayFinite(values: number[]): void {
    if (values.some((value) => !Number.isFinite(value) || !Number.isFinite(Math.fround(value))
      || (value !== 0 && Math.fround(value) === 0))) {
      throw new Error('此 SI 幾何超出 3D 顯示可用範圍；未修改或縮減實驗參數。');
    }
  }

  /** Accept only the validated draft. Camera position is preserved on edits. */
  updateExperiment(experiment: Experiment, selection: string): void {
    if (this.mode !== 'sequential' || !this.experiment || !structuralEqual(this.experiment, experiment)) {
      const edges = detectorEdges(experiment.grid);
      this.ensureDisplayFinite([
        edges.width * 1000, edges.height * 1000, edges.centerX * 1000,
        edges.centerY * 1000, experiment.observation.z_m * 100,
        ...experiment.components.map((component) => component.z_m * 100),
      ]);
      // Validate every presentation-derived size before replacing the active scene.
      const prospectiveSpan = Math.max(edges.width * 1000, edges.height * 1000,
        experiment.observation.z_m * 100, 1);
      this.ensureDisplayFinite([prospectiveSpan * 1.5,
        experiment.observation.z_m * 50 + prospectiveSpan * 1.1]);
      for (const component of experiment.components) {
        if (component.kind === 'circular_aperture') this.ensureDisplayFinite([
          component.radius_m * 1000, component.radius_m * 1120,
        ]);
        if (component.kind === 'rectangular_aperture') this.ensureDisplayFinite([
          component.width_m * 1000, component.height_m * 1000,
          component.width_m * 1150, component.height_m * 1150,
        ]);
      }
      this.updateResult(null, { min: 0, max: 10 });
      this.detachDualResult();
      this.detachPolarizationResult(); this.polarizationExperiment = null; this.polarizationDetectors = null;
      this.detachPolarizedTwoPathResult(); this.polarizedTwoPathExperiment = null; this.polarizedTwoPathDetectors = null;
      this.disposeGroup(this.bench);
      this.mode = 'sequential';
      this.twoPathExperiment = null;
      this.dualDetectors = null;
      this.experiment = experiment;
      this.detector = null;
      const width = edges.width * 1000;
      const height = edges.height * 1000;
      const zEnd = experiment.observation.z_m * 100;
      const span = Math.max(width, height, zEnd, 1);
      this.ensureDisplayFinite([span * 1.5, zEnd / 2 + span * 1.1]);
      const guide = new THREE.Line(
        this.geometry(new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, zEnd),
        ])), this.material(new THREE.LineDashedMaterial({ color: '#779ba9', dashSize: 0.06, gapSize: 0.04 })),
      );
      guide.computeLineDistances();
      this.bench.add(guide);
      const grid = new THREE.GridHelper(span * 1.5, 16, '#bdced8', '#dce5eb');
      this.geometries.add(grid.geometry);
      for (const material of Array.isArray(grid.material) ? grid.material : [grid.material]) this.materials.add(material);
      grid.position.set(0, -height / 2 - span * 0.08, zEnd / 2);
      this.bench.add(grid);
      this.addCircle('source', 0, Math.max(width, height) * 0.075, '#ce922e', true);

      for (const component of experiment.components) {
        const z = component.z_m * 100;
        if (component.kind === 'thin_lens') {
          // Cosmetic lens housing has no physical clear aperture.
          this.addCircle(component.id, z, Math.max(width, height) * 0.22, '#50a3c0', true);
        } else if (component.kind === 'circular_aperture') {
          const radius = component.radius_m * 1000;
          const outer = Math.max(radius * 1.12, Math.max(width, height) * 0.29);
          this.ensureDisplayFinite([radius, outer]);
          this.addShape(component.id, z, this.geometry(new THREE.RingGeometry(radius, outer, 64)), '#3d5b6b');
        } else {
          const apertureWidth = component.width_m * 1000;
          const apertureHeight = component.height_m * 1000;
          this.ensureDisplayFinite([apertureWidth, apertureHeight]);
          const outerWidth = Math.max(apertureWidth * 1.15, width * 0.6);
          const outerHeight = Math.max(apertureHeight * 1.15, height * 0.6);
          this.ensureDisplayFinite([outerWidth, outerHeight]);
          const shape = new THREE.Shape();
          shape.moveTo(-outerWidth / 2, -outerHeight / 2);
          shape.lineTo(outerWidth / 2, -outerHeight / 2);
          shape.lineTo(outerWidth / 2, outerHeight / 2);
          shape.lineTo(-outerWidth / 2, outerHeight / 2);
          shape.closePath();
          const hole = new THREE.Path();
          hole.moveTo(-apertureWidth / 2, -apertureHeight / 2);
          hole.lineTo(-apertureWidth / 2, apertureHeight / 2);
          hole.lineTo(apertureWidth / 2, apertureHeight / 2);
          hole.lineTo(apertureWidth / 2, -apertureHeight / 2);
          hole.closePath();
          shape.holes.push(hole);
          this.addShape(component.id, z, this.geometry(new THREE.ShapeGeometry(shape)), '#3d5b6b');
        }
      }
      const detectorMaterial = this.material(new THREE.MeshBasicMaterial({
        color: '#d4e6ed', side: THREE.DoubleSide, toneMapped: false,
      }));
      this.detector = new THREE.Mesh(this.geometry(new THREE.PlaneGeometry(width, height)), detectorMaterial);
      const world = worldPosition(edges.centerX, edges.centerY, experiment.observation.z_m);
      this.detector.position.set(world.x, world.y, world.z);
      this.detector.userData.identity = experiment.observation.id;
      this.detector.userData.detector = true;
      this.bench.add(this.detector);
      const border = new THREE.LineSegments(
        this.geometry(new THREE.EdgesGeometry(this.detector.geometry)),
        this.material(new THREE.LineBasicMaterial({ color: '#178894' })),
      );
      border.position.copy(this.detector.position);
      border.userData.identity = experiment.observation.id;
      this.bench.add(border);
      if (!this.initializedCamera) { this.resetCamera(); this.initializedCamera = true; }
    }
    this.selection = selection;
    this.updateRail();
  }

  /** Fixed unfolded topology. Mesh spacing does not represent propagation. */
  updateTwoPathExperiment(experiment: TwoPathExperiment, selection: string): void {
    if (this.mode !== 'two_path' || !structuralEqual(this.twoPathExperiment, experiment)) {
      const edges = detectorEdges(experiment.grid);
      const width = edges.width * 1000, height = edges.height * 1000;
      const lane = Math.max(width * 0.8, 0.26);
      const end = Math.max(width * 3, height * 2, 1.4);
      const radius = Math.max(width * 0.13, 0.045);
      // Preflight derived schematic geometry before disposing the prior scene.
      this.ensureDisplayFinite([width, height, radius, lane, end, end * 1.6, end * 100,
        edges.centerX * 1000 - lane, edges.centerX * 1000 + lane,
        edges.centerY * 1000, lane * 2]);
      const changedMode = this.mode !== 'two_path';
      this.updateResult(null, { min: 0, max: 10 });
      this.detachDualResult();
      this.detachPolarizationResult(); this.polarizationExperiment = null; this.polarizationDetectors = null;
      this.detachPolarizedTwoPathResult(); this.polarizedTwoPathExperiment = null; this.polarizedTwoPathDetectors = null;
      this.disposeGroup(this.bench); this.disposeGroup(this.rail);
      this.handle = null; this.experiment = null; this.detector = null;
      this.mode = 'two_path'; this.twoPathExperiment = experiment;
      const positions: [string, number, number, string][] = [
        ['source', 0, 0, '#ce922e'], ['B', 0, end * 0.22, '#50a3c0'],
        ['arm_0', -lane, end * 0.47, '#087f89'], ['arm_1', lane, end * 0.47, '#9665a8'],
        ['phase', lane, end * 0.64, '#c08028'], ['B_dagger', 0, end * 0.78, '#50a3c0'],
      ];
      for (const [id, x, z, color] of positions) {
        const mesh = new THREE.Mesh(this.geometry(new THREE.CircleGeometry(radius, 32)),
          this.material(new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide, toneMapped: false })));
        mesh.position.set(x, 0, z); mesh.userData.identity = id; this.bench.add(mesh);
      }
      const guide = (points: number[][]) => {
        const line = new THREE.Line(this.geometry(new THREE.BufferGeometry().setFromPoints(
          points.map(([x, z]) => new THREE.Vector3(x, 0, z)))),
        this.material(new THREE.LineDashedMaterial({ color: '#779ba9', dashSize: 0.05, gapSize: 0.03 })));
        line.computeLineDistances(); this.bench.add(line);
      };
      guide([[0, 0], [0, end * 0.22]]);
      for (const sign of [-1, 1]) {
        guide([[0, end * 0.22], [sign * lane, end * 0.38], [sign * lane, end * 0.68], [0, end * 0.78]]);
        guide([[0, end * 0.78], [sign * lane, end]]);
      }
      const detectors = ([0, 1] as const).map((port) => {
        const material = this.material(new THREE.MeshBasicMaterial({ color: '#d4e6ed', side: THREE.DoubleSide, toneMapped: false }));
        const mesh = new THREE.Mesh(this.geometry(new THREE.PlaneGeometry(width, height)), material);
        mesh.position.set((port === 0 ? -lane : lane) + edges.centerX * 1000, -edges.centerY * 1000, end);
        mesh.userData.identity = `port_${port}`; mesh.userData.detector = true; mesh.userData.portId = port;
        this.bench.add(mesh);
        const border = new THREE.LineSegments(this.geometry(new THREE.EdgesGeometry(mesh.geometry)),
          this.material(new THREE.LineBasicMaterial({ color: port === 0 ? '#087f89' : '#9665a8' })));
        border.position.copy(mesh.position); border.userData.identity = `port_${port}`; this.bench.add(border);
        return mesh;
      });
      this.dualDetectors = detectors as [DetectorMesh, DetectorMesh];
      if (changedMode || !this.initializedCamera) { this.resetCamera(); this.initializedCamera = true; }
    }
    this.selection = selection;
  }

  /** Prepare both new textures; commit synchronously, dispose old only in finalize. */
  prepareTwoPathResult(result: DecodedTwoPathResult, limits: ColorLimits): {
    commit: () => void; dispose: () => void; finalize: () => void;
  } {
    if (this.mode !== 'two_path' || !this.twoPathExperiment || !this.dualDetectors
        || !structuralEqual(result.experiment, this.twoPathExperiment)) {
      throw new Error('兩埠結果不屬於目前草稿；未附加任何輸出。');
    }
    const prepared = prepareDualTextures(result, limits);
    const meshes = this.dualDetectors, oldTextures = this.dualTextures, oldResult = this.dualResult;
    const oldKey = this.dualColorKey;
    let committed = false, closed = false;
    return {
      commit: () => {
        if (closed || committed || this.dualDetectors !== meshes) throw new Error('兩埠顯示交易已失效。');
        for (const port of [0, 1] as const) {
          meshes[port].material.map = prepared.textures[port];
          meshes[port].material.color.set('#ffffff'); meshes[port].material.needsUpdate = true;
          this.textures.add(prepared.textures[port]);
        }
        this.dualTextures = prepared.textures; this.dualResult = result;
        this.dualColorKey = `${limits.min}:${limits.max}`; committed = true;
      },
      finalize: () => {
        if (closed || !committed) return;
        closed = true;
        for (const texture of oldTextures ?? []) { texture.dispose(); this.textures.delete(texture); }
      },
      dispose: () => {
        if (closed) return;
        closed = true;
        if (committed && this.dualTextures === prepared.textures) {
          for (const port of [0, 1] as const) {
            meshes[port].material.map = oldTextures?.[port] ?? null;
            meshes[port].material.color.set(oldTextures ? '#ffffff' : '#d4e6ed');
            meshes[port].material.needsUpdate = true;
          }
          this.dualTextures = oldTextures; this.dualResult = oldResult; this.dualColorKey = oldKey;
        }
        for (const texture of prepared.textures) this.textures.delete(texture);
        prepared.dispose();
      },
    };
  }

  detachDualResult(): void {
    for (const texture of this.dualTextures ?? []) { texture.dispose(); this.textures.delete(texture); }
    this.dualTextures = null; this.dualResult = null; this.dualColorKey = '';
    for (const mesh of this.dualDetectors ?? []) {
      mesh.material.map = null; mesh.material.color.set('#d4e6ed'); mesh.material.needsUpdate = true;
    }
  }

  updateTwoPathResult(result: DecodedTwoPathResult | null, limits: ColorLimits): void {
    if (!result) { this.detachDualResult(); return; }
    if (result === this.dualResult && this.dualColorKey === `${limits.min}:${limits.max}`) return;
    const prepared = this.prepareTwoPathResult(result, limits);
    try { prepared.commit(); prepared.finalize(); } catch (error) { prepared.dispose(); throw error; }
  }

  /** Ordered common-plane actions; these z slots are cosmetic and have no scientific fields. */
  updatePolarizationExperiment(experiment: PolarizationExperiment, selection: string): void {
    if (this.mode !== 'polarization' || !structuralEqual(this.polarizationExperiment, experiment)) {
      const edges = detectorEdges(experiment.grid), width = edges.width * 1000, height = edges.height * 1000;
      const lane = Math.max(width * 0.8, 0.26), end = Math.max(width * 3, height * 2, 1.4), radius = Math.max(width * 0.2, 0.06);
      this.ensureDisplayFinite([width, height, lane, end, radius, edges.centerX * 1000, edges.centerY * 1000]);
      const changedMode = this.mode !== 'polarization';
      this.updateResult(null, { min: 0, max: 10 }); this.detachDualResult(); this.detachPolarizationResult();
      this.detachPolarizedTwoPathResult(); this.polarizedTwoPathExperiment = null; this.polarizedTwoPathDetectors = null;
      this.disposeGroup(this.bench); this.disposeGroup(this.rail); this.handle = null;
      this.experiment = null; this.twoPathExperiment = null; this.dualDetectors = null; this.detector = null;
      this.mode = 'polarization'; this.polarizationExperiment = experiment;
      this.addCircle('source', 0, radius * 0.55, '#ce922e', true);
      for (const [index, item] of experiment.elements.entries()) {
        const z = end * (index + 1) / (experiment.elements.length + 2);
        this.addCircle(item.id, z, radius, item.kind === 'linear_polarizer' ? '#087f89' : '#9665a8', true);
        const c = Math.cos(item.axis_angle_rad), s = Math.sin(item.axis_angle_rad);
        const marker = new THREE.Line(this.geometry(new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(-radius * c, radius * s, z), new THREE.Vector3(radius * c, -radius * s, z),
        ])), this.material(new THREE.LineBasicMaterial({ color: '#163f50' })));
        marker.userData.identity = item.id; this.bench.add(marker);
      }
      const line = new THREE.Line(this.geometry(new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, end),
      ])), this.material(new THREE.LineDashedMaterial({ color: '#779ba9', dashSize: 0.05, gapSize: 0.03 })));
      line.computeLineDistances(); this.bench.add(line);
      this.polarizationDetectors = ([0, 1] as const).map(view => {
        const mesh = new THREE.Mesh(this.geometry(new THREE.PlaneGeometry(width, height)),
          this.material(new THREE.MeshBasicMaterial({ color: '#d4e6ed', side: THREE.DoubleSide, toneMapped: false })));
        mesh.position.set((view === 0 ? -lane : lane) + edges.centerX * 1000, -edges.centerY * 1000, end);
        mesh.userData.detector = true; mesh.userData.polarizationView = view;
        this.bench.add(mesh); return mesh;
      }) as [DetectorMesh, DetectorMesh];
      if (changedMode || !this.initializedCamera) { this.resetCamera(); this.initializedCamera = true; }
    }
    this.selection = selection;
  }

  /** Receives already prepared paired resources; all later preparation precedes this commit. */
  preparePolarizationResult(result: DecodedPolarizationResult, textures: readonly [THREE.DataTexture, THREE.DataTexture]): {
    commit(): void; dispose(): void; finalize(): void;
  } {
    if (this.lost || this.mode !== 'polarization' || !this.polarizationDetectors
        || !structuralEqual(result.experiment, this.polarizationExperiment)) throw new Error('Polarization result is detached from the active scene.');
    const meshes = this.polarizationDetectors, oldTextures = this.polarizationTextures, oldResult = this.polarizationResult;
    let committed = false, closed = false;
    return {
      commit: () => {
        if (closed || committed || this.polarizationDetectors !== meshes) throw new Error('Polarization presentation transaction expired');
        textures.forEach((texture, index) => { meshes[index].material.map = texture; meshes[index].material.color.set('#ffffff');
          meshes[index].material.needsUpdate = true; this.textures.add(texture); });
        this.polarizationTextures = textures; this.polarizationResult = result; committed = true;
      },
      dispose: () => {
        if (closed) return; closed = true;
        if (committed && this.polarizationTextures === textures) {
          meshes.forEach((mesh, index) => { mesh.material.map = oldTextures?.[index] ?? null;
            mesh.material.color.set(oldTextures ? '#ffffff' : '#d4e6ed'); mesh.material.needsUpdate = true; });
          this.polarizationTextures = oldTextures; this.polarizationResult = oldResult;
        }
        textures.forEach(texture => this.textures.delete(texture));
      },
      finalize: () => {
        if (closed || !committed) return; closed = true;
        for (const texture of oldTextures ?? []) { texture.dispose(); this.textures.delete(texture); }
      },
    };
  }

  detachPolarizationResult(): void {
    for (const texture of this.polarizationTextures ?? []) { texture.dispose(); this.textures.delete(texture); }
    this.polarizationTextures = null; this.polarizationResult = null;
    for (const mesh of this.polarizationDetectors ?? []) { mesh.material.map = null; mesh.material.color.set('#d4e6ed'); mesh.material.needsUpdate = true; }
  }

  /** Ideal unfolded lanes; actions occupy cosmetic terminal slots, never extra propagation. */
  updatePolarizedTwoPathExperiment(experiment: PolarizedTwoPathExperiment, selection: string): void {
    if (this.mode !== 'polarized_two_path' || !structuralEqual(this.polarizedTwoPathExperiment, experiment)) {
      const edges = detectorEdges(experiment.grid), width = edges.width * 1000, height = edges.height * 1000;
      const lane = Math.max(width * 0.8, 0.26), end = Math.max(width * 3, height * 2, 1.4), radius = Math.max(width * 0.12, 0.04);
      this.ensureDisplayFinite([width, height, lane, end, radius, end * 100,
        edges.centerX * 1000 - lane, edges.centerX * 1000 + lane, edges.centerY * 1000]);
      const changedMode = this.mode !== 'polarized_two_path';
      const next = new THREE.Group(), geometries = new Set<THREE.BufferGeometry>(), materials = new Set<THREE.Material>();
      const geometry = <T extends THREE.BufferGeometry>(value: T): T => { geometries.add(value); return value; };
      const material = <T extends THREE.Material>(value: T): T => { materials.add(value); return value; };
      let detectors: readonly [DetectorMesh, DetectorMesh];
      try {
      const token = (id: string, x: number, z: number, color: string, angle?: number) => {
        const mesh = new THREE.Mesh(geometry(new THREE.CircleGeometry(radius, 32)),
          material(new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide, toneMapped: false })));
        mesh.position.set(x, 0, z); mesh.userData.identity = id; next.add(mesh);
        if (angle !== undefined) {
          const c = Math.cos(angle), s = Math.sin(angle);
          const marker = new THREE.Line(geometry(new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(x - radius * c, radius * s, z), new THREE.Vector3(x + radius * c, -radius * s, z),
          ])), material(new THREE.LineBasicMaterial({ color: '#183b4c' })));
          marker.userData.identity = id; next.add(marker);
        }
      };
      token('input', 0, 0, '#ce922e'); token('splitter', 0, end * 0.2, '#50a3c0'); token('combiner', 0, end * 0.8, '#50a3c0');
      for (const port of [0, 1] as const) {
        const arm = port === 0 ? experiment.arm_0 : experiment.arm_1, x = port === 0 ? -lane : lane;
        token(`arm_${port}`, x, end * 0.38, port === 0 ? '#087f89' : '#9665a8');
        arm.actions.forEach((action, index) => token(action.id, x, end * (0.5 + index * 0.13),
          action.kind === 'linear_polarizer' ? '#087f89' : '#a880b4', action.axis_angle_rad));
        const guide = new THREE.Line(geometry(new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, end * 0.2), new THREE.Vector3(x, 0, end * 0.36),
          new THREE.Vector3(x, 0, end * 0.68), new THREE.Vector3(0, 0, end * 0.8), new THREE.Vector3(x, 0, end),
        ])), material(new THREE.LineDashedMaterial({ color: '#779ba9', dashSize: 0.05, gapSize: 0.03 })));
        guide.computeLineDistances(); next.add(guide);
      }
      if (experiment.analyzer.enabled) token('analyzer', 0, end * 0.9, '#c08028', experiment.analyzer.axis_angle_rad);
      detectors = ([0, 1] as const).map(port => {
        const mesh = new THREE.Mesh(geometry(new THREE.PlaneGeometry(width, height)),
          material(new THREE.MeshBasicMaterial({ color: '#d4e6ed', side: THREE.DoubleSide, toneMapped: false })));
        mesh.position.set((port === 0 ? -lane : lane) + edges.centerX * 1000, -edges.centerY * 1000, end);
        mesh.userData.identity = `port_${port}`; mesh.userData.detector = true; mesh.userData.polarizedTwoPathPort = port;
        next.add(mesh); return mesh;
      }) as [DetectorMesh, DetectorMesh];
      const buffers = new Set<ArrayBufferLike>();
      for (const item of geometries) {
        if (item.index) buffers.add(item.index.array.buffer);
        for (const attribute of [...Object.values(item.attributes), ...Object.values(item.morphAttributes).flat()])
          buffers.add(attribute instanceof THREE.InterleavedBufferAttribute ? attribute.data.array.buffer : attribute.array.buffer);
      }
      if ([...buffers].reduce((sum, buffer) => sum + buffer.byteLength, 0) > 131072)
        throw new Error('Prepared polarized two-path geometry exceeds its 131072-byte reservation; previous scene preserved.');
      } catch (error) {
        next.clear(); geometries.forEach(item => item.dispose()); materials.forEach(item => item.dispose()); throw error;
      }
      this.releaseRetainedResults(); this.disposeGroup(this.bench); this.disposeGroup(this.rail); this.handle = null;
      this.experiment = null; this.twoPathExperiment = null; this.polarizationExperiment = null;
      this.detector = null; this.dualDetectors = null; this.polarizationDetectors = null;
      this.mode = 'polarized_two_path'; this.polarizedTwoPathExperiment = experiment; this.polarizedTwoPathDetectors = detectors;
      geometries.forEach(item => this.geometries.add(item)); materials.forEach(item => this.materials.add(item));
      this.bench.add(...[...next.children]);
      if (changedMode || !this.initializedCamera) { this.resetCamera(); this.initializedCamera = true; }
    }
    this.selection = selection;
  }

  /** Entire result is retained as one owner; selecting a prepared pair allocates no scientific data. */
  preparePolarizedTwoPathResult(result: DecodedPolarizedTwoPathResult, textures: readonly THREE.DataTexture[], view: 'raw' | 'analyzed'): {
    commit(): void; dispose(): void; finalize(): void;
  } {
    if (this.lost || this.mode !== 'polarized_two_path' || !this.polarizedTwoPathDetectors
        || !structuralEqual(result.experiment, this.polarizedTwoPathExperiment)
        || textures.length !== (result.analyzedPorts ? 4 : 2) || view === 'analyzed' && !result.analyzedPorts) {
      throw new Error('Polarized two-path presentation does not match the complete active result.');
    }
    const meshes = this.polarizedTwoPathDetectors, oldTextures = this.polarizedTwoPathTextures,
      oldResult = this.polarizedTwoPathResult, oldView = this.polarizedTwoPathView, generation = this.resultGeneration;
    let committed = false, closed = false;
    return {
      commit: () => {
        if (closed || committed || generation !== this.resultGeneration || meshes !== this.polarizedTwoPathDetectors) throw new Error('Polarized two-path presentation expired');
        committed = true;
        this.polarizedTwoPathTextures = textures; this.polarizedTwoPathResult = result;
        textures.forEach(texture => this.textures.add(texture)); this.selectPolarizedTwoPathView(view);
      },
      dispose: () => {
        if (closed) return; closed = true;
        if (committed && generation === this.resultGeneration && this.polarizedTwoPathTextures === textures) {
          this.polarizedTwoPathTextures = oldTextures; this.polarizedTwoPathResult = oldResult;
          this.selectPolarizedTwoPathView(oldView);
        }
        textures.forEach(texture => this.textures.delete(texture));
      },
      finalize: () => {
        if (closed || !committed) return; closed = true;
        for (const texture of oldTextures ?? []) { texture.dispose(); this.textures.delete(texture); }
      },
    };
  }

  selectPolarizedTwoPathView(view: 'raw' | 'analyzed'): void {
    if (view === 'analyzed' && !this.polarizedTwoPathResult?.analyzedPorts) throw new Error('No analyzed output is available');
    const offset = view === 'raw' ? 0 : 2;
    for (const [port, mesh] of (this.polarizedTwoPathDetectors ?? []).entries()) {
      mesh.material.map = this.polarizedTwoPathTextures?.[offset + port] ?? null;
      mesh.material.color.set(mesh.material.map ? '#ffffff' : '#d4e6ed'); mesh.material.needsUpdate = true;
    }
    this.polarizedTwoPathView = view;
  }
  detachPolarizedTwoPathResult(): void {
    ++this.resultGeneration;
    for (const texture of this.polarizedTwoPathTextures ?? []) { texture.dispose(); this.textures.delete(texture); }
    this.polarizedTwoPathTextures = null; this.polarizedTwoPathResult = null; this.polarizedTwoPathView = 'raw';
    for (const mesh of this.polarizedTwoPathDetectors ?? []) { mesh.material.map = null; mesh.material.color.set('#d4e6ed'); mesh.material.needsUpdate = true; }
  }
  /** Result-only cleanup leaves current schematic, renderer, camera and controls usable. */
  releaseRetainedResults(): void {
    this.frameCallback = null; this.updateResult(null, { min: 0, max: 10 }); this.detachDualResult();
    this.detachPolarizationResult(); this.detachPolarizedTwoPathResult();
  }

  /** One replaceable callback inside the shared renderer; no additional RAF chain. */
  setFrameCallback(callback: ((time: number) => void) | null): void { this.frameCallback = callback; }

  /** Internal ownership inventory uses actual references, never cloned evidence summaries. */
  ownedNumericalResults(): Readonly<{ sequential: DecodedResult | null; dual: DecodedTwoPathResult | null;
    polarization: DecodedPolarizationResult | null; polarizedTwoPath: DecodedPolarizedTwoPathResult | null }> {
    return { sequential: this.result, dual: this.dualResult, polarization: this.polarizationResult, polarizedTwoPath: this.polarizedTwoPathResult };
  }

  /** Exact CPU texture-source backing stores; GPU disposal does not erase them. */
  ownedTextureBuffers(): readonly ArrayBufferLike[] {
    return [...new Set([...this.textures].map(texture => ((texture as THREE.DataTexture).image?.data as Uint8Array | undefined)?.buffer)
      .filter((buffer): buffer is ArrayBufferLike => buffer !== undefined))];
  }

  /** CPU geometry sources are app-owned too; deduplicate interleaved/index aliases. */
  ownedGeometryBuffers(): readonly ArrayBufferLike[] {
    const buffers = new Set<ArrayBufferLike>();
    for (const geometry of this.geometries) {
      if (geometry.index) buffers.add(geometry.index.array.buffer);
      for (const attribute of [...Object.values(geometry.attributes), ...Object.values(geometry.morphAttributes).flat()]) {
        buffers.add(attribute instanceof THREE.InterleavedBufferAttribute ? attribute.data.array.buffer : attribute.array.buffer);
      }
    }
    return [...buffers];
  }

  private addCircle(id: string, z: number, radius: number, color: string, translucent: boolean): void {
    this.addShape(id, z, this.geometry(new THREE.CircleGeometry(radius, 64)), color, translucent);
    const edge = new THREE.LineLoop(
      this.geometry(new THREE.BufferGeometry().setFromPoints(Array.from({ length: 64 }, (_, index) => {
        const angle = index / 64 * 2 * Math.PI;
        return new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, z);
      }))), this.material(new THREE.LineBasicMaterial({ color })),
    );
    edge.userData.identity = id;
    this.bench.add(edge);
  }

  private addShape(id: string, z: number, geometry: THREE.BufferGeometry, color: string, translucent = false): void {
    const mesh = new THREE.Mesh(geometry, this.material(new THREE.MeshBasicMaterial({
      color, side: THREE.DoubleSide, transparent: translucent,
      opacity: translucent ? 0.35 : 1, depthWrite: !translucent, toneMapped: false,
      // Coplanar cosmetic faces receive depth-buffer bias only; SI/world z is unchanged.
      polygonOffset: translucent, polygonOffsetFactor: translucent ? -1 : 0,
      polygonOffsetUnits: translucent ? -1 : 0,
    })));
    mesh.position.z = z;
    mesh.userData.identity = id;
    this.bench.add(mesh);
  }

  updateResult(result: DecodedResult | null, limits: ColorLimits): void {
    const key = `${limits.min}:${limits.max}`;
    if (result === this.result && key === this.colorKey) return;
    if (result && (!this.experiment || !structuralEqual(result.experiment, this.experiment))) {
      throw new Error('結果不屬於目前通過驗證的草稿；未貼上強度圖。');
    }
    if (result && !this.detector) throw new Error('3D 觀察面未建立；數值結果未貼到任何替代幾何。');
    const nextTexture = result ? createDetectorTexture(result, limits) : null;
    if (this.texture) { this.texture.dispose(); this.textures.delete(this.texture); }
    this.texture = nextTexture;
    if (nextTexture) this.textures.add(nextTexture);
    if (this.detector) {
      this.detector.material.map = nextTexture;
      this.detector.material.color.set(nextTexture ? '#ffffff' : '#d4e6ed');
      this.detector.material.needsUpdate = true;
    }
    this.result = result;
    this.colorKey = key;
  }

  private updateRail(): void {
    if (this.drag) return;
    this.disposeGroup(this.rail);
    this.handle = null;
    if (!this.experiment || this.selection === 'source') return;
    const component = this.experiment.components.find((item) => item.id === this.selection);
    const record = component ?? (this.experiment.observation.id === this.selection ? this.experiment.observation : null);
    if (!record) return;
    const edges = detectorEdges(this.experiment.grid);
    this.railX = edges.xMax * 1000 + Math.max(edges.width * 1000 * 0.12, 0.12);
    const end = Math.max(this.experiment.observation.z_m * 100 * 1.3, 1);
    const line = new THREE.Line(
      this.geometry(new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(this.railX, 0, 0), new THREE.Vector3(this.railX, 0, end),
      ])), this.material(new THREE.LineBasicMaterial({ color: '#bb7820' })),
    );
    this.rail.add(line);
    this.handle = new THREE.Mesh(this.geometry(new THREE.SphereGeometry(0.055, 16, 12)),
      this.material(new THREE.MeshBasicMaterial({ color: '#d99b34' })));
    this.handle.position.set(this.railX, 0, record.z_m * 100);
    this.handle.userData.identity = record.id;
    this.rail.add(this.handle);
  }

  private setRay(event: PointerEvent): void {
    const rect = this.canvas.getBoundingClientRect();
    this.pointer.set((event.clientX - rect.left) / rect.width * 2 - 1,
      -(event.clientY - rect.top) / rect.height * 2 + 1);
    this.raycaster.setFromCamera(this.pointer, this.camera);
  }

  private railZ(): number | null {
    const { origin, direction } = this.raycaster.ray;
    const denominator = 1 - direction.z ** 2;
    if (denominator < 1e-4) return null;
    const dot = direction.x * (origin.x - this.railX) + direction.y * origin.y + direction.z * origin.z;
    return (origin.z - direction.z * dot) / denominator / 100;
  }

  private validZ(id: string, z_m: number): boolean {
    if (!this.experiment || !Number.isFinite(z_m) || z_m < 0) return false;
    const index = this.experiment.components.findIndex((component) => component.id === id);
    if (index >= 0) {
      const minimum = index === 0 ? 0 : this.experiment.components[index - 1].z_m;
      const maximum = index + 1 < this.experiment.components.length
        ? this.experiment.components[index + 1].z_m : this.experiment.observation.z_m;
      return z_m >= minimum && z_m <= maximum;
    }
    return id === this.experiment.observation.id
      && z_m >= (this.experiment.components.at(-1)?.z_m ?? 0);
  }

  private pointerDown(event: PointerEvent): void {
    if (this.researchGroup) { this.down = { x: event.clientX, y: event.clientY }; return; }
    if (event.button !== 0 || this.lost || (!this.experiment && !this.twoPathExperiment && !this.polarizationExperiment && !this.polarizedTwoPathExperiment)) return;
    this.setRay(event);
    if (this.handle && this.raycaster.intersectObject(this.handle).length) {
      if (!this.draftValidated) {
        this.callbacks.notice('草稿尚未通過驗證，z 拖曳暫停；請先修正輸入。');
        return;
      }
      if (this.railZ() === null) {
        this.callbacks.notice('目前視角接近 z 軸，拖曳不可用；請轉動相機或輸入數值。');
        return;
      }
      this.drag = { id: this.selection, z_m: this.handle.position.z / 100, valid: true };
      this.controls.enabled = false;
      event.stopImmediatePropagation();
      event.preventDefault();
      this.canvas.setPointerCapture(event.pointerId);
      return;
    }
    this.down = { x: event.clientX, y: event.clientY };
  }

  private pointerMove(event: PointerEvent): void {
    if (!this.drag || !this.handle) return;
    event.stopImmediatePropagation();
    this.setRay(event);
    const z_m = this.railZ();
    if (z_m === null) return;
    this.drag.z_m = z_m;
    this.drag.valid = this.validZ(this.drag.id, z_m);
    this.handle.position.z = z_m * 100;
    (this.handle.material as THREE.MeshBasicMaterial).color.set(this.drag.valid ? '#d99b34' : '#d8453a');
    this.callbacks.notice(`z 拖曳預覽：${(z_m * 1000).toFixed(4)} mm${this.drag.valid ? '；放開提交' : '；位置無效，放開將拒絕'}`);
  }

  private pointerUp(event: PointerEvent): void {
    if (this.drag) {
      event.stopImmediatePropagation();
      const completed = this.drag;
      this.drag = null;
      this.controls.enabled = true;
      if (this.canvas.hasPointerCapture(event.pointerId)) this.canvas.releasePointerCapture(event.pointerId);
      this.updateRail();
      if (completed.valid) {
        this.callbacks.commitZ(completed.id, completed.z_m);
        this.callbacks.notice('已提交 z 位置以進行驗證；尚未重新模擬。');
      } else this.callbacks.notice('已拒絕拖曳：位置必須非負並保留現有光路順序。草稿未改動。');
      return;
    }
    if (!this.down || Math.hypot(event.clientX - this.down.x, event.clientY - this.down.y) > 4) {
      this.down = null;
      return;
    }
    this.down = null;
    this.setRay(event);
    const hits = this.raycaster.intersectObjects(this.researchGroup?.children ?? this.bench.children, true);
    const ids = [...new Set(hits.map((hit) => hit.object.userData.identity as string | undefined).filter((id): id is string => !!id))];
    if (ids.length) this.callbacks.select(ids);
    const detectorHit = hits.find((hit) => hit.object.userData.detector && hit.uv);
    if (detectorHit?.uv && this.result && this.experiment) {
      const pixel = pixelFromUV(this.experiment.grid, detectorHit.uv.x, detectorHit.uv.y);
      if (pixel) this.callbacks.pixel(pixel.row, pixel.column);
    }
    if (detectorHit?.uv && this.dualResult && this.twoPathExperiment) {
      const port = detectorHit.object.userData.portId as 0 | 1;
      const pixel = pixelFromUV(this.twoPathExperiment.grid, detectorHit.uv.x, detectorHit.uv.y);
      if (pixel && (port === 0 || port === 1)) this.callbacks.dualPixel?.(port, pixel.row, pixel.column);
    }
    if (detectorHit?.uv && this.polarizationResult && this.polarizationExperiment) {
      const view = detectorHit.object.userData.polarizationView as 0 | 1;
      const pixel = pixelFromUV(this.polarizationExperiment.grid, detectorHit.uv.x, detectorHit.uv.y);
      if (pixel && (view === 0 || view === 1)) this.callbacks.polarizationPixel?.(view, pixel.row, pixel.column);
    }
    if (detectorHit?.uv && this.polarizedTwoPathResult && this.polarizedTwoPathExperiment) {
      const port = detectorHit.object.userData.polarizedTwoPathPort;
      const pixel = pixelFromUV(this.polarizedTwoPathExperiment.grid, detectorHit.uv.x, detectorHit.uv.y);
      if (pixel && (port === 0 || port === 1)) this.callbacks.polarizedTwoPathPixel?.(this.polarizedTwoPathView, port, pixel.row, pixel.column);
    }
  }

  private cancelDrag(): void {
    this.drag = null;
    this.down = null;
    this.controls.enabled = true;
    this.updateRail();
  }

  resetCamera(): void {
    if (this.researchGroup) {
      if (this.researchOverviewBounds) this.fitResearchApparatus(this.researchOverviewBounds, 'overview');
      return;
    }
    if (!this.experiment && !this.twoPathExperiment && !this.polarizationExperiment && !this.polarizedTwoPathExperiment) return;
    // Consume residual public OrbitControls damping before assigning the reset view.
    // Otherwise a prior gesture continues moving the camera after a manual reset.
    const damping = this.controls.enableDamping;
    this.controls.enableDamping = false;
    this.controls.update();
    const edges = detectorEdges((this.experiment ?? this.twoPathExperiment ?? this.polarizationExperiment ?? this.polarizedTwoPathExperiment!).grid);
    const end = this.experiment ? this.experiment.observation.z_m * 100
      : Math.max(edges.width * 3000, edges.height * 2000, 1.4);
    const span = Math.max(edges.width * 1000, edges.height * 1000, end, 1);
    this.camera.near = Math.max(span / 10000, 0.00001);
    this.camera.far = Math.max(span * 100, 10);
    this.controls.maxDistance = span * 30;
    this.camera.position.set(span * 0.95, span * 0.7, end / 2 + span * 1.1);
    this.controls.target.set(0, 0, end / 2);
    this.camera.updateProjectionMatrix();
    this.controls.update();
    this.controls.enableDamping = damping;
  }

  setDraftValidated(validated: boolean): void {
    this.draftValidated = validated;
    if (!validated && this.drag) this.cancelDrag();
  }

  pan(horizontal: number, vertical: number): void {
    const distance = this.camera.position.distanceTo(this.controls.target);
    const right = new THREE.Vector3().setFromMatrixColumn(this.camera.matrix, 0);
    const up = new THREE.Vector3().setFromMatrixColumn(this.camera.matrix, 1);
    const shift = right.multiplyScalar(horizontal * distance * 0.05).add(up.multiplyScalar(vertical * distance * 0.05));
    this.camera.position.add(shift);
    this.controls.target.add(shift);
    this.controls.update();
  }

  zoom(factor: number): void {
    const offset = this.camera.position.clone().sub(this.controls.target).multiplyScalar(factor);
    this.camera.position.copy(this.controls.target).add(offset);
    this.controls.update();
  }

  private resize(): void {
    const width = Math.max(1, (this.researchHost ?? this.host).clientWidth);
    const height = Math.max(1, (this.researchHost ?? this.host).clientHeight);
    const ratio = Math.min(window.devicePixelRatio || 1, 2, Math.sqrt(4_000_000 / (width * height)));
    this.renderer.setPixelRatio(ratio);
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }

  private animate = (time = 0): void => {
    if (this.disposed) return;
    this.frame = requestAnimationFrame(this.animate);
    if (!this.lost) {
      try { this.frameCallback?.(time); this.controls.update();
        if (this.researchGroup && this.researchHost) {
          this.camera.updateMatrixWorld(true);
          this.researchLabelUpdater?.(this.camera, Math.max(1, this.researchHost.clientWidth), Math.max(1, this.researchHost.clientHeight));
        }
        this.renderer.render(this.scene, this.camera); }
      catch (error) { this.lost = true; this.callbacks.presentationFailure(`3D 顯示失敗：${String(error)}`); }
    }
  };

  worldToClient(x: number, y: number, z: number): { x: number; y: number; visible: boolean } {
    const projected = new THREE.Vector3(x, y, z).project(this.camera);
    const rect = this.canvas.getBoundingClientRect();
    return { x: rect.left + (projected.x + 1) / 2 * rect.width,
      y: rect.top + (1 - projected.y) / 2 * rect.height, visible: projected.z >= -1 && projected.z <= 1 };
  }

  dualPixelWorld(port: 0 | 1, row: number, column: number): { x: number; y: number; z: number } | null {
    const grid = this.twoPathExperiment?.grid, mesh = this.dualDetectors?.[port];
    if (!grid || !mesh || row < 0 || row >= grid.ny || column < 0 || column >= grid.nx
        || !Number.isInteger(row) || !Number.isInteger(column)) return null;
    const edges = detectorEdges(grid);
    return { x: mesh.position.x + ((column - Math.floor(grid.nx / 2)) * grid.dx - edges.centerX) * 1000,
      y: mesh.position.y - ((row - Math.floor(grid.ny / 2)) * grid.dy - edges.centerY) * 1000, z: mesh.position.z };
  }

  polarizedTwoPathPixelWorld(port: 0 | 1, row: number, column: number): { x: number; y: number; z: number } | null {
    const grid = this.polarizedTwoPathExperiment?.grid, mesh = this.polarizedTwoPathDetectors?.[port];
    if (!grid || !mesh || !Number.isInteger(row) || !Number.isInteger(column) || row < 0 || row >= grid.ny || column < 0 || column >= grid.nx) return null;
    const edges = detectorEdges(grid);
    return { x: mesh.position.x + ((column - Math.floor(grid.nx / 2)) * grid.dx - edges.centerX) * 1000,
      y: mesh.position.y - ((row - Math.floor(grid.ny / 2)) * grid.dy - edges.centerY) * 1000, z: mesh.position.z };
  }

  /** Read-only browser evidence, without simulation or state-mutation hooks. */
  snapshot(): object {
    if (this.researchGroup) this.camera.updateMatrixWorld(true);
    const gl = this.renderer.getContext();
    const extension = gl.getExtension('WEBGL_debug_renderer_info');
    const identities: { id: string; position: number[] }[] = [];
    this.bench.traverse((object) => {
      if (object.userData.identity && object instanceof THREE.Mesh) identities.push({
        id: object.userData.identity, position: object.position.toArray(),
      });
    });
    return {
      available: true, contextLost: this.lost, textureRequestId: this.result?.requestId ?? null,
      researchActive: this.researchGroup !== null,
      researchLabelCallbacks: this.researchLabelUpdater ? 1 : 0,
      researchFraming: this.researchGroup && this.researchFraming ? {
        view: this.researchFraming.view, bounds: { min: this.researchFraming.bounds.min.toArray(), max: this.researchFraming.bounds.max.toArray() },
        projectedCorners: researchBoundsCorners(this.researchFraming.bounds).map(point => point.project(this.camera).toArray()),
        fitAspect: this.researchFraming.aspect, currentAspect: this.camera.aspect, fitCount: this.researchFitCount,
        topTiltRad: this.researchFraming.topTiltRad,
      } : null,
      mode: this.mode,
      polarizedTwoPath: { view: this.polarizedTwoPathView,
        textureRequestIds: this.polarizedTwoPathTextures ? [this.polarizedTwoPathResult?.requestId, this.polarizedTwoPathResult?.requestId] : [null, null],
        retainedRoles: this.polarizedTwoPathTextures?.length ?? 0,
        detectors: this.polarizedTwoPathDetectors?.map((mesh, port) => ({ port, position: mesh.position.toArray() })) ?? [], resultGeneration: this.resultGeneration },
      polarization: { textureRequestIds: this.polarizationTextures ? [this.polarizationResult?.requestId, this.polarizationResult?.requestId] : [null, null],
        detectors: this.polarizationDetectors?.map((mesh, view) => ({ view, position: mesh.position.toArray() })) ?? [], frameCallbacks: this.frameCallback ? 1 : 0 },
      dualTextureRequestIds: this.dualTextures ? [this.dualResult?.requestId, this.dualResult?.requestId] : [null, null],
      dualDetectors: this.dualDetectors?.map((mesh, port) => ({ port, position: mesh.position.toArray(),
        width: mesh.geometry.parameters.width, height: mesh.geometry.parameters.height,
        texture: this.dualTextures ? { flipY: this.dualTextures[port].flipY,
          minFilter: this.dualTextures[port].minFilter, magFilter: this.dualTextures[port].magFilter,
          generateMipmaps: this.dualTextures[port].generateMipmaps, colorSpace: this.dualTextures[port].colorSpace } : null })) ?? [],
      owned: { geometries: this.geometries.size, materials: this.materials.size,
        textures: this.textures.size, controls: this.disposed ? 0 : 1, listeners: this.disposed ? 0 : 6,
        resizeObservers: this.disposed ? 0 : 1, geometrySourceBytes: this.ownedGeometryBuffers().reduce((n, buffer) => n + buffer.byteLength, 0),
        textureSourceBytes: [...this.textures].reduce((n, texture) => n +
          (((texture as THREE.DataTexture).image?.data as Uint8Array | undefined)?.byteLength ?? 0), 0) },
      renderer: { geometries: this.renderer.info.memory.geometries, textures: this.renderer.info.memory.textures,
        programs: this.renderer.info.programs?.length ?? 0,
        vendor: extension ? gl.getParameter(extension.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR),
        renderer: extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
        version: gl.getParameter(gl.VERSION), toneMapping: this.renderer.toneMapping,
        outputColorSpace: this.renderer.outputColorSpace },
      camera: { position: this.camera.position.toArray(), target: this.controls.target.toArray(),
        aspect: this.camera.aspect, up: this.camera.up.toArray(), near: this.camera.near, far: this.camera.far,
        minDistance: this.controls.minDistance, maxDistance: this.controls.maxDistance },
      drawingBuffer: { width: this.canvas.width, height: this.canvas.height, dpr: this.renderer.getPixelRatio() },
      identities,
      rail: this.handle ? { id: this.selection, position: this.handle.position.toArray(),
        z_m: this.handle.position.z / 100, dragging: this.drag !== null,
        enabled: this.draftValidated } : null,
      detector: this.detector ? { position: this.detector.position.toArray(),
        width: this.detector.geometry.parameters.width, height: this.detector.geometry.parameters.height,
        texture: this.texture ? { flipY: this.texture.flipY, minFilter: this.texture.minFilter,
          magFilter: this.texture.magFilter, generateMipmaps: this.texture.generateMipmaps,
          colorSpace: this.texture.colorSpace } : null } : null,
    };
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    cancelAnimationFrame(this.frame);
    this.resizeObserver.disconnect();
    this.canvas.removeEventListener('pointerdown', this.onPointerDown, true);
    this.canvas.removeEventListener('pointermove', this.onPointerMove, true);
    this.canvas.removeEventListener('pointerup', this.onPointerUp, true);
    this.canvas.removeEventListener('pointercancel', this.onPointerCancel, true);
    this.canvas.removeEventListener('webglcontextlost', this.onContextLost);
    this.canvas.removeEventListener('webglcontextrestored', this.onContextRestored);
    this.controls.dispose();
    this.researchLabelUpdater = null;
    this.frameCallback = null;
    this.updateResult(null, { min: 0, max: 10 });
    this.detachDualResult();
    this.detachPolarizationResult();
    this.detachPolarizedTwoPathResult();
    this.disposeGroup(this.rail);
    this.disposeGroup(this.bench);
    this.renderer.dispose();
    this.canvas.remove();
  }
}
