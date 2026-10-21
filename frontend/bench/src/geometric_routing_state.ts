/** Explicit W2 submission actor. Edits and viewing never trace or replay. */
import { ClientOperationGate } from './state';
import { W2_PRESETS, W2_RETAINED_RESERVATION, W2_TRANSIENT_RESERVATION, createGeometricRoutingFetchAPI,
  decodeGeometricTrace, freezeGeometricScene, freezeRoutingDraft, routingOwnedResults, routingResourceBreakdown, routingMetadataReservation, routingStructuralEqual,
  validateGeometricValidation, type GeometricRoutingAPI, type GeometricScene, type GeometricTraceRequest,
  type GeometricTraceResult, type GeometricValidationRequest, type RoutingKind, type RoutingSurfaceFrame } from './geometric_routing_contracts';

export interface GeometricRoutingPrepared { commit(): void; dispose(): void; finalize(): void }
interface Identity { readonly revision: number; readonly epoch: number; readonly digest: string; readonly scene: GeometricScene }
export interface GeometricRoutingState {
  readonly candidate: GeometricScene; readonly validatedDraft: GeometricScene | null; readonly surfaceFrames: readonly RoutingSurfaceFrame[] | null;
  readonly validatedDigest: string | null; readonly pendingValidation: boolean; readonly invalidEdits: Readonly<Record<string, string>>;
  readonly revision: number; readonly attachmentEpoch: number; readonly activeView: boolean; readonly selection: string;
  readonly active: Readonly<{ request: GeometricTraceRequest; revision: number; epoch: number }> | null;
  readonly status: 'idle' | 'validating' | 'ready' | 'tracing' | 'error'; readonly error: string | null; readonly renderError: string | null;
  readonly lastResult: GeometricTraceResult | null; readonly currentResult: GeometricTraceResult | null;
  readonly completedNumerical: GeometricTraceResult | null;
  readonly timings: Readonly<{ httpAndDecodeMs: number; decodeMs: number; attachmentMs: number }> | null;
}
export interface GeometricRoutingControllerOptions {
  readonly gate: ClientOperationGate; admit(persistent: number, transient: number): void;
  reserveOperation?(persistent: number, transient: number): void; readonly api?: GeometricRoutingAPI; readonly idFactory?: () => string;
}
const numeric = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
const message = (error: unknown): string => error instanceof Error ? error.message : String(error);

export class GeometricRoutingController {
  private snapshot: GeometricRoutingState;
  private readonly api: GeometricRoutingAPI; private readonly id: () => string;
  private readonly listeners = new Set<(state: GeometricRoutingState) => void>();
  private validationGeneration = 0; private disposed = false;
  private presentation: ((result: GeometricTraceResult) => GeometricRoutingPrepared) | null = null;
  private completedIdentity: Identity | null = null;
  private readonly validationRequests = new Set<GeometricValidationRequest>();
  constructor(initial: GeometricScene = W2_PRESETS.A, private readonly options: GeometricRoutingControllerOptions) {
    this.api = options.api ?? createGeometricRoutingFetchAPI(); this.id = options.idFactory ?? (() => crypto.randomUUID());
    this.snapshot = Object.freeze({ candidate: freezeGeometricScene(initial), validatedDraft: null, surfaceFrames: null,
      validatedDigest: null, pendingValidation: false, invalidEdits: Object.freeze({}), revision: 0, attachmentEpoch: 0,
      activeView: false, selection: 'source', active: null, status: 'idle', error: null, renderError: null,
      lastResult: null, currentResult: null, completedNumerical: null, timings: null });
  }
  get state(): GeometricRoutingState { return this.snapshot; }
  get gate(): ClientOperationGate { return this.options.gate; }
  get canRetryPresentation(): boolean { return !!this.snapshot.completedNumerical && !!this.completedIdentity && this.fresh(this.completedIdentity); }
  subscribe(listener: (state: GeometricRoutingState) => void): () => void { this.listeners.add(listener); this.notify(listener); return () => this.listeners.delete(listener); }
  private notify(listener: (state: GeometricRoutingState) => void): void {
    try { listener(this.snapshot); } catch (error) {
      const result = this.snapshot.completedNumerical ?? this.snapshot.currentResult;
      if (result && this.snapshot.validatedDigest) this.completedIdentity = this.identity(result.scene, this.snapshot.validatedDigest);
      this.snapshot = Object.freeze({ ...this.snapshot, currentResult: null, completedNumerical: result ?? this.snapshot.completedNumerical, renderError: message(error) });
    }
  }
  private publish(change: Partial<GeometricRoutingState>): void {
    const next = { ...this.snapshot, ...change };
    next.status = next.active ? 'tracing' : next.pendingValidation ? 'validating' : next.error || Object.keys(next.invalidEdits).length ? 'error' : next.validatedDraft ? 'ready' : 'idle';
    this.snapshot = Object.freeze(next); for (const listener of this.listeners) this.notify(listener);
  }
  bindPresentation(prepare: ((result: GeometricTraceResult) => GeometricRoutingPrepared) | null): void { this.presentation = prepare; }
  async activate(): Promise<void> {
    if (this.disposed) return;
    if (!this.snapshot.activeView) this.publish({ activeView: true, attachmentEpoch: this.snapshot.attachmentEpoch + 1 });
    await this.validateInitial();
  }
  deactivate(): void {
    if (!this.snapshot.activeView) return;
    ++this.validationGeneration; this.completedIdentity = null;
    this.publish({ activeView: false, attachmentEpoch: this.snapshot.attachmentEpoch + 1, currentResult: null,
      completedNumerical: null, pendingValidation: false, validatedDraft: null, validatedDigest: null, surfaceFrames: null });
  }
  async validateInitial(): Promise<void> {
    if (this.disposed || this.snapshot.pendingValidation || this.snapshot.validatedDraft || Object.keys(this.snapshot.invalidEdits).length) return;
    await this.validateCandidate();
  }
  private async validateCandidate(): Promise<void> {
    const generation = ++this.validationGeneration, request = Object.freeze({ request_id: this.id(), scene: freezeRoutingDraft(this.snapshot.candidate) });
    try { const bytes = routingMetadataReservation(request); this.options.admit(bytes, bytes + 2 * 32 * 1024); }
    catch (error) { this.publish({ pendingValidation: false, validatedDraft: null, validatedDigest: null, surfaceFrames: null, error: message(error) }); return; }
    this.validationRequests.add(request);
    this.publish({ pendingValidation: true, validatedDraft: null, validatedDigest: null, surfaceFrames: null, error: null });
    try {
      const reply = validateGeometricValidation(await this.api.validate(request), request);
      if (this.disposed || generation !== this.validationGeneration) return;
      this.publish({ validatedDraft: reply.scene, validatedDigest: reply.scene_sha256, surfaceFrames: reply.surface_frames, pendingValidation: false, error: null });
    } catch (error) {
      if (this.disposed || generation !== this.validationGeneration) return;
      this.publish({ pendingValidation: false, validatedDraft: null, validatedDigest: null, surfaceFrames: null, error: message(error) });
    } finally { this.validationRequests.delete(request); }
  }
  private detach(change: Partial<GeometricRoutingState>): void {
    ++this.validationGeneration; this.completedIdentity = null;
    this.publish({ ...change, revision: this.snapshot.revision + 1, currentResult: null, completedNumerical: null,
      validatedDraft: null, validatedDigest: null, surfaceFrames: null, pendingValidation: false, error: null, renderError: null });
  }
  async replaceCandidate(scene: GeometricScene): Promise<void> {
    const owned = freezeGeometricScene(scene), exists = this.snapshot.selection === 'source' || owned.elements.some(element => element.id === this.snapshot.selection);
    this.detach({ candidate: owned, invalidEdits: Object.freeze({}), selection: exists ? this.snapshot.selection : 'source' });
    if (this.snapshot.activeView) await this.validateCandidate();
  }
  async setPreset(preset: keyof typeof W2_PRESETS): Promise<void> { await this.replaceCandidate(W2_PRESETS[preset]); }
  /** Only the named changed field is written. Untouched inspector components retain their binary64 value. */
  async edit(path: string, text: string, scale = 1): Promise<void> {
    if (!Number.isFinite(scale) || scale <= 0) throw new Error('Editor unit scale must be positive finite');
    const invalid = { ...this.snapshot.invalidEdits }, token = text.trim(), value = numeric.test(token) ? Number(token) * scale : NaN;
    if (!Number.isFinite(value) || value === 0 && /[1-9]/.test(token.split(/[eE]/, 1)[0])) {
      invalid[path] = text; this.detach({ invalidEdits: Object.freeze(invalid) }); return;
    }
    const clone = structuredClone(this.snapshot.candidate), parts = path.split('.'); let owner: unknown = clone;
    for (const part of parts.slice(0, -1)) {
      if (!owner || typeof owner !== 'object' || !Object.hasOwn(owner, part)) throw new Error(`Unknown routing editor path: ${path}`);
      owner = (owner as Record<string, unknown>)[part];
    }
    const key = parts.at(-1)!;
    if (!owner || typeof owner !== 'object' || !Object.hasOwn(owner, key) || typeof (owner as Record<string, unknown>)[key] !== 'number') throw new Error(`Unknown routing numeric field: ${path}`);
    if (Object.is((owner as Record<string, unknown>)[key], value) && !Object.hasOwn(invalid, path)) return;
    (owner as Record<string, unknown>)[key] = value; delete invalid[path];
    this.detach({ candidate: freezeRoutingDraft(clone), invalidEdits: Object.freeze(invalid) });
    if (!Object.keys(invalid).length && this.snapshot.activeView) await this.validateCandidate();
  }
  async changeAperture(kind: 'disk' | 'rectangle'): Promise<void> {
    const index = this.snapshot.candidate.elements.findIndex(element => element.id === this.snapshot.selection); if (index < 0) return;
    const clone = structuredClone(this.snapshot.candidate) as unknown as { elements: { aperture: unknown }[] };
    clone.elements[index].aperture = kind === 'disk' ? { kind, radius_m: .025 } : { kind, width_m: .05, height_m: .05 };
    const invalid = Object.fromEntries(Object.entries(this.snapshot.invalidEdits).filter(([path]) => !path.startsWith(`elements.${index}.aperture.`)));
    this.detach({ candidate: freezeRoutingDraft(clone as unknown as GeometricScene), invalidEdits: Object.freeze(invalid) });
    if (!Object.keys(invalid).length && this.snapshot.activeView) await this.validateCandidate();
  }
  async add(kind: RoutingKind): Promise<void> {
    if (this.snapshot.candidate.elements.length >= 16) { this.publish({ error: 'The scene supports at most 16 finite optical elements.' }); return; }
    if (!['mirror', 'ideal_splitter_50_50', 'beam_stop', 'receiver'].includes(kind)) throw new Error('Unsupported routing element');
    const prefix = { mirror: 'M', ideal_splitter_50_50: 'S', beam_stop: 'STOP', receiver: 'D' }[kind];
    let ordinal = 1; while (this.snapshot.candidate.elements.some(element => element.id === `${prefix}${ordinal}`)) ++ordinal;
    const id = `${prefix}${ordinal}`, count = this.snapshot.candidate.elements.length, source = this.snapshot.candidate.source.origin_m;
    const item = { id, kind, pose: { position_m: [source[0] + .08 * (count % 4), source[1], source[2] + .15 + .1 * Math.floor(count / 4)], rotation_xyz_rad: [0, kind === 'mirror' || kind === 'ideal_splitter_50_50' ? -Math.PI / 4 : 0, 0] }, aperture: { kind: 'disk', radius_m: .025 } };
    const scene = { ...structuredClone(this.snapshot.candidate), elements: [...this.snapshot.candidate.elements, item] } as unknown as GeometricScene;
    this.detach({ candidate: freezeRoutingDraft(scene), selection: id }); if (!Object.keys(this.snapshot.invalidEdits).length && this.snapshot.activeView) await this.validateCandidate();
  }
  async remove(id = this.snapshot.selection): Promise<void> {
    if (id === 'source') return; if (!this.snapshot.candidate.elements.some(element => element.id === id)) throw new Error('Unknown routing element');
    const removedIndex = this.snapshot.candidate.elements.findIndex(element => element.id === id);
    const scene = { ...this.snapshot.candidate, elements: this.snapshot.candidate.elements.filter(element => element.id !== id) }, invalid: Record<string, string> = {};
    for (const [path, text] of Object.entries(this.snapshot.invalidEdits)) {
      const match = /^elements\.(\d+)\.(.+)$/.exec(path);
      if (!match) invalid[path] = text;
      else if (Number(match[1]) !== removedIndex) invalid[`elements.${Number(match[1]) > removedIndex ? Number(match[1]) - 1 : Number(match[1])}.${match[2]}`] = text;
    }
    this.detach({ candidate: freezeRoutingDraft(scene), selection: 'source', invalidEdits: Object.freeze(invalid) }); if (!Object.keys(invalid).length && this.snapshot.activeView) await this.validateCandidate();
  }
  select(id: string): void {
    if (id !== 'source' && !this.snapshot.candidate.elements.some(element => element.id === id)) throw new Error('Unknown routing selection');
    if (id !== this.snapshot.selection) this.publish({ selection: id });
  }
  private identity(scene: GeometricScene, digest: string): Identity { return Object.freeze({ revision: this.snapshot.revision, epoch: this.snapshot.attachmentEpoch, scene, digest }); }
  private fresh(identity: Identity): boolean {
    return !this.disposed && this.snapshot.activeView && identity.revision === this.snapshot.revision && identity.epoch === this.snapshot.attachmentEpoch
      && identity.digest === this.snapshot.validatedDigest && !this.snapshot.pendingValidation && !Object.keys(this.snapshot.invalidEdits).length && routingStructuralEqual(identity.scene, this.snapshot.validatedDraft);
  }
  private attach(result: GeometricTraceResult): boolean {
    let transaction: GeometricRoutingPrepared | null = null; const previous = this.snapshot.lastResult, start = performance.now();
    try {
      if (!this.presentation) throw new Error('Geometric Routing display is unavailable. Numerical data retained; no automatic recalculation.');
      transaction = this.presentation(result); transaction.commit();
      this.publish({ lastResult: result, currentResult: result, completedNumerical: null, renderError: null,
        timings: this.snapshot.timings ? Object.freeze({ ...this.snapshot.timings, attachmentMs: performance.now() - start }) : null });
      if (this.snapshot.currentResult !== result || this.snapshot.renderError) throw new Error(this.snapshot.renderError ?? 'Routing display subscriber failed');
      transaction.finalize(); this.completedIdentity = null; return true;
    } catch (error) {
      transaction?.dispose(); this.publish({ lastResult: previous, currentResult: null, completedNumerical: result, renderError: message(error) }); return false;
    }
  }
  async trace(): Promise<boolean> {
    const state = this.snapshot;
    if (this.disposed || !state.activeView || this.gate.busy || state.active || state.pendingValidation || !state.validatedDraft || !state.validatedDigest || Object.keys(state.invalidEdits).length) return false;
    const request = Object.freeze({ request_id: this.id(), scene_sha256: state.validatedDigest, scene: freezeGeometricScene(state.validatedDraft) });
    try { (this.options.reserveOperation ?? this.options.admit)(W2_RETAINED_RESERVATION, W2_TRANSIENT_RESERVATION); }
    catch (error) { this.publish({ error: message(error) }); return false; }
    if (!this.gate.acquire(request.request_id, 'geometric_routing', 'trace')) return false;
    const identity = this.identity(request.scene, request.scene_sha256), frames = state.surfaceFrames;
    this.publish({ active: Object.freeze({ request, revision: identity.revision, epoch: identity.epoch }), error: null, renderError: null });
    try {
      const started = performance.now(); let raw: ArrayBuffer | null = await this.api.trace(request); const beforeDecode = performance.now();
      const result = decodeGeometricTrace(raw, request, frames ?? undefined), finished = performance.now(); raw = null;
      if (this.disposed) return false;
      if (routingResourceBreakdown(result).retainedBytes > W2_RETAINED_RESERVATION) throw new Error('Routing result exceeds the approved 2 MiB ownership reservation.');
      const before = this.ownedNumericalBytes(), after = routingOwnedResults([...this.numericalOwners(), result]);
      this.options.admit(after - before, after - before);
      this.publish({ timings: Object.freeze({ httpAndDecodeMs: finished - started, decodeMs: finished - beforeDecode, attachmentMs: 0 }) });
      if (this.snapshot.active?.request.request_id !== request.request_id) return false;
      if (!this.fresh(identity)) { this.publish({ active: null, lastResult: result, currentResult: null, completedNumerical: null }); return true; }
      this.completedIdentity = identity; this.publish({ active: null, completedNumerical: result });
      if (!this.snapshot.renderError) this.attach(result);
      return true;
    } catch (error) { if (!this.disposed && this.snapshot.active?.request.request_id === request.request_id) this.publish({ active: null, error: message(error) }); return false; }
    finally { this.gate.release(request.request_id); }
  }
  reportPresentationFailure(error: string | null): void {
    const current = this.snapshot.currentResult;
    if (error && current && this.snapshot.validatedDigest) this.completedIdentity = this.identity(current.scene, this.snapshot.validatedDigest);
    this.publish(error ? { currentResult: null, completedNumerical: current ?? this.snapshot.completedNumerical, renderError: error } : { renderError: null });
  }
  invalidatePresentation(error: string): void { this.reportPresentationFailure(error); }
  retryPresentation(): boolean { return !this.gate.busy && this.canRetryPresentation ? this.attach(this.snapshot.completedNumerical!) : false; }
  numericalOwners(): readonly (GeometricTraceResult | null)[] { return [this.snapshot.currentResult, this.snapshot.lastResult, this.snapshot.completedNumerical]; }
  ownedNumericalBytes(): number { return routingOwnedResults(this.numericalOwners()); }
  ownedStateBytes(): number {
    return routingMetadataReservation([this.snapshot, W2_PRESETS, this.completedIdentity, [...this.validationRequests]], this.numericalOwners());
  }
  releaseResults(): boolean {
    if (this.gate.busy || this.snapshot.active) return false; this.completedIdentity = null;
    this.publish({ lastResult: null, currentResult: null, completedNumerical: null, error: this.snapshot.validatedDraft ? null : this.snapshot.error, renderError: null, timings: null }); return true;
  }
  dispose(): void { this.disposed = true; ++this.validationGeneration; this.presentation = null; this.completedIdentity = null; this.listeners.clear();
    this.snapshot = Object.freeze({ ...this.snapshot, activeView: false, currentResult: null, lastResult: null, completedNumerical: null }); }
}
