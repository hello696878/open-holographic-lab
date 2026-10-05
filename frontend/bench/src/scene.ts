/** Schematic viewing geometry only: no source, lens or propagation computation. */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { Experiment, DecodedResult } from './contracts';
import { structuralEqual } from './contracts';
import { detectorEdges, pixelFromUV, worldPosition } from './mapping';
import { createDetectorTexture, type ColorLimits } from './detector';

export interface SceneCallbacks {
  select: (ids: string[]) => void;
  pixel: (row: number, column: number) => void;
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
    if (!this.experiment || !structuralEqual(this.experiment, experiment)) {
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
      this.disposeGroup(this.bench);
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
    if (event.button !== 0 || this.lost || !this.experiment) return;
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
    const hits = this.raycaster.intersectObjects(this.bench.children, true);
    const ids = [...new Set(hits.map((hit) => hit.object.userData.identity as string | undefined).filter((id): id is string => !!id))];
    if (ids.length) this.callbacks.select(ids);
    const detectorHit = hits.find((hit) => hit.object.userData.detector && hit.uv);
    if (detectorHit?.uv && this.result && this.experiment) {
      const pixel = pixelFromUV(this.experiment.grid, detectorHit.uv.x, detectorHit.uv.y);
      if (pixel) this.callbacks.pixel(pixel.row, pixel.column);
    }
  }

  private cancelDrag(): void {
    this.drag = null;
    this.down = null;
    this.controls.enabled = true;
    this.updateRail();
  }

  resetCamera(): void {
    if (!this.experiment) return;
    // Consume residual public OrbitControls damping before assigning the reset view.
    // Otherwise a prior gesture continues moving the camera after a manual reset.
    const damping = this.controls.enableDamping;
    this.controls.enableDamping = false;
    this.controls.update();
    const edges = detectorEdges(this.experiment.grid);
    const end = this.experiment.observation.z_m * 100;
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
    const width = Math.max(1, this.host.clientWidth);
    const height = Math.max(1, this.host.clientHeight);
    const ratio = Math.min(window.devicePixelRatio || 1, 2, Math.sqrt(4_000_000 / (width * height)));
    this.renderer.setPixelRatio(ratio);
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }

  private animate = (): void => {
    if (this.disposed) return;
    this.frame = requestAnimationFrame(this.animate);
    if (!this.lost) {
      try { this.controls.update(); this.renderer.render(this.scene, this.camera); }
      catch (error) { this.lost = true; this.callbacks.presentationFailure(`3D 顯示失敗：${String(error)}`); }
    }
  };

  worldToClient(x: number, y: number, z: number): { x: number; y: number; visible: boolean } {
    const projected = new THREE.Vector3(x, y, z).project(this.camera);
    const rect = this.canvas.getBoundingClientRect();
    return { x: rect.left + (projected.x + 1) / 2 * rect.width,
      y: rect.top + (1 - projected.y) / 2 * rect.height, visible: projected.z >= -1 && projected.z <= 1 };
  }

  /** Read-only browser evidence, without simulation or state-mutation hooks. */
  snapshot(): object {
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
      owned: { geometries: this.geometries.size, materials: this.materials.size,
        textures: this.textures.size, controls: this.disposed ? 0 : 1, listeners: this.disposed ? 0 : 6,
        resizeObservers: this.disposed ? 0 : 1 },
      renderer: { geometries: this.renderer.info.memory.geometries, textures: this.renderer.info.memory.textures,
        programs: this.renderer.info.programs?.length ?? 0,
        vendor: extension ? gl.getParameter(extension.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR),
        renderer: extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
        version: gl.getParameter(gl.VERSION), toneMapping: this.renderer.toneMapping,
        outputColorSpace: this.renderer.outputColorSpace },
      camera: { position: this.camera.position.toArray(), target: this.controls.target.toArray(),
        aspect: this.camera.aspect },
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
    this.updateResult(null, { min: 0, max: 10 });
    this.disposeGroup(this.rail);
    this.disposeGroup(this.bench);
    this.renderer.dispose();
    this.canvas.remove();
  }
}
