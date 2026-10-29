/** Explicit W4 submission actor. Edits and viewing never trace or replay. */
import { ClientOperationGate } from './state';
import { routingMetadataReservation, routingStructuralEqual, type RoutingKind } from './geometric_routing_contracts';
import { W4_PRESETS, W4_RETAINED_RESERVATION, W4_TRANSIENT_RESERVATION, createFresnelRoutingFetchAPI,
  decodeFresnelTrace, freezeFresnelScene, freezeFresnelDraft, fresnelOwnedResults, fresnelResourceBreakdown,
  validateFresnelValidation, type FresnelRoutingAPI, type FresnelScene, type FresnelTraceRequest,
  type FresnelTraceResult, type FresnelValidationRequest, type FresnelValidationReply } from './fresnel_routing_contracts';

export interface FresnelRoutingPrepared { commit(): void; dispose(): void; finalize(): void }
interface Identity { readonly revision: number; readonly epoch: number; readonly digest: string; readonly scene: FresnelScene }
export interface FresnelRoutingState {
  readonly candidate: FresnelScene; readonly validatedDraft: FresnelScene | null; readonly validation: FresnelValidationReply | null;
  readonly validatedDigest: string | null; readonly pendingValidation: boolean; readonly invalidEdits: Readonly<Record<string, string>>;
  readonly revision: number; readonly attachmentEpoch: number; readonly activeView: boolean; readonly selection: string;
  readonly active: Readonly<{ request: FresnelTraceRequest; revision: number; epoch: number }> | null;
  readonly status: 'idle' | 'validating' | 'ready' | 'tracing' | 'error'; readonly error: string | null; readonly renderError: string | null;
  readonly lastResult: FresnelTraceResult | null; readonly currentResult: FresnelTraceResult | null;
  readonly completedNumerical: FresnelTraceResult | null;
  readonly timings: Readonly<{ httpAndDecodeMs: number; decodeMs: number; attachmentMs: number }> | null;
}
export interface FresnelRoutingControllerOptions {
  readonly gate: ClientOperationGate; admit(persistent: number, transient: number): void;
  reserveOperation?(persistent: number, transient: number): void; readonly api?: FresnelRoutingAPI; readonly idFactory?: () => string;
}
const numeric = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
const message = (error: unknown): string => error instanceof Error ? error.message : String(error);

export class FresnelRoutingController {
  private snapshot: FresnelRoutingState;
  private readonly api: FresnelRoutingAPI; private readonly id: () => string;
  private readonly listeners = new Set<(state: FresnelRoutingState) => void>();
  private validationGeneration = 0; private disposed = false;
  private presentation: ((result: FresnelTraceResult) => FresnelRoutingPrepared) | null = null;
  private completedIdentity: Identity | null = null;
  private readonly validationRequests = new Set<FresnelValidationRequest>();
  private readBusy = false; private queuedValidation = false; private validationFlight: Promise<void> | null = null;
  get hasPendingRead(): boolean { return this.readBusy; }
  ownedPendingReadBytes(): number { return this.readBusy ? W4_TRANSIENT_RESERVATION : 0; }
  constructor(initial: FresnelScene = W4_PRESETS.A, private readonly options: FresnelRoutingControllerOptions) {
    this.api = options.api ?? createFresnelRoutingFetchAPI(); this.id = options.idFactory ?? (() => crypto.randomUUID());
    this.snapshot = Object.freeze({ candidate: freezeFresnelScene(initial), validatedDraft: null, validation: null,
      validatedDigest: null, pendingValidation: false, invalidEdits: Object.freeze({}), revision: 0, attachmentEpoch: 0,
      activeView: false, selection: 'source', active: null, status: 'idle', error: null, renderError: null,
      lastResult: null, currentResult: null, completedNumerical: null, timings: null });
  }
  get state(): FresnelRoutingState { return this.snapshot; }
  get gate(): ClientOperationGate { return this.options.gate; }
  get canRetryPresentation(): boolean { return !!this.snapshot.completedNumerical && !!this.completedIdentity && this.fresh(this.completedIdentity); }
  subscribe(listener: (state: FresnelRoutingState) => void): () => void { this.listeners.add(listener); this.notify(listener); return () => this.listeners.delete(listener); }
  private notify(listener: (state: FresnelRoutingState) => void): void {
    try { listener(this.snapshot); } catch (error) {
      const result = this.snapshot.completedNumerical ?? this.snapshot.currentResult;
      if (result && this.snapshot.validatedDigest) this.completedIdentity = this.identity(result.scene, this.snapshot.validatedDigest);
      this.snapshot = Object.freeze({ ...this.snapshot, currentResult: null, completedNumerical: result ?? this.snapshot.completedNumerical, renderError: message(error) });
    }
  }
  private publish(change: Partial<FresnelRoutingState>): void {
    const next = { ...this.snapshot, ...change };
    next.status = next.active ? 'tracing' : next.pendingValidation ? 'validating' : next.error || Object.keys(next.invalidEdits).length ? 'error' : next.validatedDraft ? 'ready' : 'idle';
    this.snapshot = Object.freeze(next); for (const listener of this.listeners) this.notify(listener);
  }
  bindPresentation(prepare: ((result: FresnelTraceResult) => FresnelRoutingPrepared) | null): void { this.presentation = prepare; }
  async activate(): Promise<void> {
    if (this.disposed) return;
    if (!this.snapshot.activeView) this.publish({ activeView: true, attachmentEpoch: this.snapshot.attachmentEpoch + 1 });
    await this.validateInitial();
  }
  deactivate(): void {
    if (!this.snapshot.activeView) return;
    ++this.validationGeneration; this.completedIdentity = null;
    this.publish({ activeView: false, attachmentEpoch: this.snapshot.attachmentEpoch + 1, currentResult: null,
      lastResult: this.snapshot.completedNumerical ?? this.snapshot.lastResult,
      completedNumerical: null, pendingValidation: this.readBusy, validatedDraft: null, validatedDigest: null, validation: null });
  }
  async validateInitial(): Promise<void> {
    if (this.disposed || this.snapshot.validatedDraft || Object.keys(this.snapshot.invalidEdits).length) return;
    await this.validateCandidate();
  }
  private validateCandidate(): Promise<void> {
    this.queuedValidation = true;
    if (this.validationFlight) return this.validationFlight;
    if (this.readBusy) { this.publish({ pendingValidation: true }); return Promise.resolve(); }
    const flight = this.drainValidation(); this.validationFlight = flight;
    return flight.finally(() => { if (this.validationFlight === flight) this.validationFlight = null; });
  }
  private async drainValidation(): Promise<void> {
    while (this.queuedValidation && !this.disposed && this.snapshot.activeView && !Object.keys(this.snapshot.invalidEdits).length) {
      this.queuedValidation = false;
      const generation = ++this.validationGeneration, request = Object.freeze({ request_id: this.id(), scene: freezeFresnelDraft(this.snapshot.candidate) });
      try { this.options.admit(W4_RETAINED_RESERVATION, W4_TRANSIENT_RESERVATION); }
      catch (error) { this.publish({ pendingValidation: false, error: message(error) }); return; }
      this.readBusy = true; this.validationRequests.add(request);
      this.publish({ pendingValidation: true, validatedDraft: null, validatedDigest: null, validation: null, error: null });
      try {
        const reply = validateFresnelValidation(await this.api.validate(request), request);
        if (this.disposed || generation !== this.validationGeneration || !this.snapshot.activeView) continue;
        const actual = routingMetadataReservation([this.snapshot, reply, W4_PRESETS, this.completedIdentity, [...this.validationRequests]], this.numericalOwners());
        if (actual + this.ownedNumericalBytes() > W4_RETAINED_RESERVATION) throw new Error('W4 validation metadata exceeds its 4 MiB ownership reservation.');
        this.options.admit(Math.max(0, actual-this.ownedStateBytes()), 0);
        this.publish({ validatedDraft: reply.scene, validatedDigest: reply.scene_sha256, validation: reply, error: null });
      } catch (error) { if (!this.disposed && generation === this.validationGeneration) this.publish({ validatedDraft: null, validatedDigest: null, validation: null, error: message(error) }); }
      finally { this.readBusy = false; this.validationRequests.delete(request); if (!this.disposed) this.publish({ pendingValidation: this.queuedValidation }); }
    }
    if (!this.disposed) this.publish({ pendingValidation: false });
  }
  private detach(change: Partial<FresnelRoutingState>): void {
    ++this.validationGeneration; this.completedIdentity = null;
    this.publish({ ...change, revision: this.snapshot.revision + 1, currentResult: null, completedNumerical: null,
      validatedDraft: null, validatedDigest: null, validation: null, pendingValidation: this.readBusy, error: null, renderError: null });
  }
  async replaceCandidate(scene: FresnelScene): Promise<void> {
    const owned = freezeFresnelScene(scene), exists = this.snapshot.selection === 'source' || owned.elements.some(element => element.id === this.snapshot.selection) || owned.bodies.some(body => body.id === this.snapshot.selection);
    this.detach({ candidate: owned, invalidEdits: Object.freeze({}), selection: exists ? this.snapshot.selection : 'source' });
    if (this.snapshot.activeView) await this.validateCandidate();
  }
  async setPolarization(polarization: FresnelScene['source']['polarization']): Promise<void> {
    if (!['unpolarized','linear_e1','linear_e2','linear_45'].includes(polarization)) throw new Error('Unknown source polarization');
    this.detach({ candidate: freezeFresnelDraft({ ...this.snapshot.candidate, source: { ...this.snapshot.candidate.source, polarization } }) });
    if (!Object.keys(this.snapshot.invalidEdits).length && this.snapshot.activeView) await this.validateCandidate();
  }
  async setPreset(preset: keyof typeof W4_PRESETS): Promise<void> { await this.replaceCandidate(W4_PRESETS[preset]); }
  /** Only the named changed field is written. Untouched inspector components retain their binary64 value. */
  async edit(path: string, text: string, scale = 1): Promise<void> {
    if (!Number.isFinite(scale) || scale <= 0) throw new Error('Editor unit scale must be positive finite');
    if (path.startsWith('source.')) throw new Error('W4 source geometry and frame are preset-only.');
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
    this.detach({ candidate: freezeFresnelDraft(clone), invalidEdits: Object.freeze(invalid) });
    if (!Object.keys(invalid).length && this.snapshot.activeView) await this.validateCandidate();
  }
  async changeAperture(kind: 'disk' | 'rectangle'): Promise<void> {
    const index = this.snapshot.candidate.elements.findIndex(element => element.id === this.snapshot.selection); if (index < 0) return;
    const clone = structuredClone(this.snapshot.candidate) as unknown as { elements: { aperture: unknown }[] };
    clone.elements[index].aperture = kind === 'disk' ? { kind, radius_m: .025 } : { kind, width_m: .05, height_m: .05 };
    const invalid = Object.fromEntries(Object.entries(this.snapshot.invalidEdits).filter(([path]) => !path.startsWith(`elements.${index}.aperture.`)));
    this.detach({ candidate: freezeFresnelDraft(clone as unknown as FresnelScene), invalidEdits: Object.freeze(invalid) });
    if (!Object.keys(invalid).length && this.snapshot.activeView) await this.validateCandidate();
  }
  async add(kind: RoutingKind): Promise<void> {
    if (this.snapshot.candidate.elements.length >= 4) { this.publish({ error: 'W4 supports at most four finite receiver or beam-stop elements.' }); return; }
    if (!['beam_stop', 'receiver'].includes(kind)) throw new Error('Unsupported routing element');
    const prefix = { mirror: 'M', ideal_splitter_50_50: 'S', beam_stop: 'STOP', receiver: 'D' }[kind];
    let ordinal = 1; while (this.snapshot.candidate.elements.some(element => element.id === `${prefix}${ordinal}`)) ++ordinal;
    const id = `${prefix}${ordinal}`, count = this.snapshot.candidate.elements.length, source = this.snapshot.candidate.source.origin_m;
    const item = { id, kind, pose: { position_m: [source[0] + .08 * (count % 4), source[1], source[2] + .15 + .1 * Math.floor(count / 4)], rotation_xyz_rad: [0, kind === 'mirror' || kind === 'ideal_splitter_50_50' ? -Math.PI / 4 : 0, 0] }, aperture: { kind: 'disk', radius_m: .025 } };
    const scene = { ...structuredClone(this.snapshot.candidate), elements: [...this.snapshot.candidate.elements, item] } as unknown as FresnelScene;
    this.detach({ candidate: freezeFresnelDraft(scene), selection: id }); if (!Object.keys(this.snapshot.invalidEdits).length && this.snapshot.activeView) await this.validateCandidate();
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
    this.detach({ candidate: freezeFresnelDraft(scene), selection: 'source', invalidEdits: Object.freeze(invalid) }); if (!Object.keys(invalid).length && this.snapshot.activeView) await this.validateCandidate();
  }
  async changeBodyKind(kind: 'rectangular_block' | 'right_triangular_prism'): Promise<void> {
    if (!this.snapshot.candidate.bodies.length) return;
    const scene = structuredClone(this.snapshot.candidate) as unknown as { bodies: { kind: string; shape: unknown }[] };
    scene.bodies[0].kind = kind;
    scene.bodies[0].shape = kind === 'rectangular_block' ? { width_x_m: .12, height_y_m: .08, depth_z_m: .03 } : { leg_x_m: .08, leg_z_m: .08, height_y_m: .04 };
    const invalid = Object.freeze(Object.fromEntries(Object.entries(this.snapshot.invalidEdits).filter(([path]) => !path.startsWith('bodies.0.shape.'))));
    this.detach({ candidate: freezeFresnelDraft(scene as unknown as FresnelScene), invalidEdits: invalid });
    if (this.snapshot.activeView && !Object.keys(invalid).length) await this.validateCandidate();
  }
  async removeBody(): Promise<void> {
    const invalid = Object.freeze(Object.fromEntries(Object.entries(this.snapshot.invalidEdits).filter(([path]) => !path.startsWith('bodies.'))));
    this.detach({ candidate: freezeFresnelDraft({ ...this.snapshot.candidate, bodies: [] }), selection: 'source', invalidEdits: invalid });
    if (this.snapshot.activeView && !Object.keys(invalid).length) await this.validateCandidate();
  }
  select(id: string): void {
    if (id !== 'source' && !this.snapshot.candidate.elements.some(element => element.id === id) && !this.snapshot.candidate.bodies.some(body => body.id === id)) throw new Error('Unknown routing selection');
    if (id !== this.snapshot.selection) this.publish({ selection: id });
  }
  private identity(scene: FresnelScene, digest: string): Identity { return Object.freeze({ revision: this.snapshot.revision, epoch: this.snapshot.attachmentEpoch, scene, digest }); }
  private fresh(identity: Identity): boolean {
    return !this.disposed && this.snapshot.activeView && identity.revision === this.snapshot.revision && identity.epoch === this.snapshot.attachmentEpoch
      && identity.digest === this.snapshot.validatedDigest && !this.snapshot.pendingValidation && !Object.keys(this.snapshot.invalidEdits).length && routingStructuralEqual(identity.scene, this.snapshot.validatedDraft);
  }
  private attach(result: FresnelTraceResult): boolean {
    let transaction: FresnelRoutingPrepared | null = null; const previous = this.snapshot.lastResult, start = performance.now();
    try {
      if (!this.presentation) throw new Error('Geometric Routing display is unavailable. Numerical data retained; no automatic recalculation.');
      transaction = this.presentation(result); transaction.commit();
      this.publish({ lastResult: result, currentResult: result, completedNumerical: null, renderError: null,
        timings: this.snapshot.timings ? Object.freeze({ ...this.snapshot.timings, attachmentMs: performance.now() - start }) : null });
      if (this.snapshot.currentResult !== result || this.snapshot.renderError) throw new Error(this.snapshot.renderError ?? 'Routing display subscriber failed');
      transaction.finalize();
      if (this.snapshot.currentResult !== result || this.snapshot.renderError) throw new Error(this.snapshot.renderError ?? 'Routing display finalizer failed');
      this.completedIdentity = null; return true;
    } catch (error) {
      transaction?.dispose(); this.publish({ lastResult: previous, currentResult: null, completedNumerical: result, renderError: message(error) }); return false;
    }
  }
  async trace(): Promise<boolean> {
    const state = this.snapshot;
    if (this.disposed || !state.activeView || this.gate.busy || state.active || state.pendingValidation || this.readBusy || !state.validatedDraft || !state.validatedDigest || Object.keys(state.invalidEdits).length) return false;
    const request = Object.freeze({ request_id: this.id(), scene_sha256: state.validatedDigest, scene: freezeFresnelScene(state.validatedDraft) });
    try { (this.options.reserveOperation ?? this.options.admit)(W4_RETAINED_RESERVATION, W4_TRANSIENT_RESERVATION); }
    catch (error) { this.publish({ error: message(error) }); return false; }
    if (!this.gate.acquire(request.request_id, 'fresnel_routing', 'trace')) return false;
    this.readBusy = true;
    const identity = this.identity(request.scene, request.scene_sha256), frames = state.validation;
    this.publish({ active: Object.freeze({ request, revision: identity.revision, epoch: identity.epoch }), error: null, renderError: null });
    try {
      const started = performance.now(); let raw: ArrayBuffer | null = await this.api.trace(request); const beforeDecode = performance.now();
      const result = decodeFresnelTrace(raw, request, frames ?? undefined), finished = performance.now(); raw = null;
      if (this.disposed) return false;
      if (fresnelResourceBreakdown(result).retainedBytes > W4_RETAINED_RESERVATION) throw new Error('Routing result exceeds the approved 4 MiB ownership reservation.');
      const before = this.ownedNumericalBytes(), after = fresnelOwnedResults([...this.numericalOwners(), result]);
      this.options.admit(after - before, after - before);
      this.publish({ timings: Object.freeze({ httpAndDecodeMs: finished - started, decodeMs: finished - beforeDecode, attachmentMs: 0 }) });
      if (this.snapshot.active?.request.request_id !== request.request_id) return false;
      if (!this.fresh(identity)) { this.publish({ active: null, lastResult: result, currentResult: null, completedNumerical: null }); return true; }
      this.completedIdentity = identity; this.publish({ active: null, completedNumerical: result });
      if (!this.snapshot.renderError) this.attach(result);
      return true;
    } catch (error) { if (!this.disposed && this.snapshot.active?.request.request_id === request.request_id) this.publish({ active: null, error: message(error) }); return false; }
    finally { this.readBusy = false; this.gate.release(request.request_id); if (this.queuedValidation && !this.disposed) void this.validateCandidate(); }
  }
  reportPresentationFailure(error: string | null): void {
    const current = this.snapshot.currentResult;
    if (error && current && this.snapshot.validatedDigest) this.completedIdentity = this.identity(current.scene, this.snapshot.validatedDigest);
    this.publish(error ? { currentResult: null, completedNumerical: current ?? this.snapshot.completedNumerical, renderError: error } : { renderError: null });
  }
  invalidatePresentation(error: string): void { this.reportPresentationFailure(error); }
  retryPresentation(): boolean { return !this.gate.busy && this.canRetryPresentation ? this.attach(this.snapshot.completedNumerical!) : false; }
  numericalOwners(): readonly (FresnelTraceResult | null)[] { return [this.snapshot.currentResult, this.snapshot.lastResult, this.snapshot.completedNumerical]; }
  ownedNumericalBytes(): number { return fresnelOwnedResults(this.numericalOwners()); }
  ownedStateBytes(): number {
    return routingMetadataReservation([this.snapshot, W4_PRESETS, this.completedIdentity, [...this.validationRequests]], this.numericalOwners());
  }
  releaseResults(): boolean {
    if (this.gate.busy || this.snapshot.active) return false; this.completedIdentity = null;
    this.publish({ lastResult: null, currentResult: null, completedNumerical: null, error: this.snapshot.validatedDraft ? null : this.snapshot.error, renderError: null, timings: null }); return true;
  }
  dispose(): void { this.disposed = true; ++this.validationGeneration; this.queuedValidation = false; this.presentation = null; this.completedIdentity = null; this.listeners.clear();
    this.snapshot = Object.freeze({ ...this.snapshot, activeView: false, currentResult: null, lastResult: null, completedNumerical: null }); }
}
