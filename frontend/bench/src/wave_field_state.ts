/** Read-only observer of the existing Sequential draft; no second scientific editor. */
import { freezeExperiment, structuralEqual, type Experiment } from './contracts';
import { BenchController, type BenchState } from './state';
import { buildWaveFieldSampling, createWaveFieldFetchAPI, decodeWaveFieldResult, estimateWaveFieldOperation,
  waveFieldOwnedResults, type WaveFieldAPI, type WaveFieldRequest, type WaveFieldResult } from './wave_field_contracts';

export interface WaveFieldPrepared { commit(): void; dispose(): void; finalize(): void }
export interface WaveFieldState {
  readonly enabled: boolean; readonly activeView: boolean; readonly attachmentEpoch: number;
  readonly active: Readonly<{ request: WaveFieldRequest; revision: number; sourceEpoch: number; viewEpoch: number }> | null;
  readonly lastResult: WaveFieldResult | null; readonly currentResult: WaveFieldResult | null;
  readonly completedNumerical: WaveFieldResult | null; readonly error: string | null; readonly renderError: string | null;
  readonly timings: Readonly<{ httpAndDecodeMs: number; decodeMs: number; attachmentMs: number }> | null;
}
export interface WaveFieldControllerOptions {
  admit(persistent: number, transient: number): void;
  reserveOperation?(persistent: number, transient: number): void;
  api?: WaveFieldAPI; idFactory?: () => string;
}
const message = (error: unknown): string => error instanceof Error ? error.message : String(error);
export class WaveFieldController {
  private snapshot: WaveFieldState = Object.freeze({ enabled: false, activeView: true, attachmentEpoch: 0,
    active: null, lastResult: null, currentResult: null, completedNumerical: null, error: null, renderError: null, timings: null });
  private listeners = new Set<(state: WaveFieldState) => void>();
  private prepare: ((result: WaveFieldResult) => WaveFieldPrepared) | null = null;
  private readonly unsubscribe: () => void;
  private readonly api: WaveFieldAPI;
  private readonly id: () => string;
  private sourceRevision: number; private sourceEpoch: number;
  private disposed = false;
  private completedIdentity: { revision: number; sourceEpoch: number; viewEpoch: number; experiment: Experiment } | null = null;
  constructor(readonly bench: BenchController, private readonly options: WaveFieldControllerOptions) {
    this.api = options.api ?? createWaveFieldFetchAPI(); this.id = options.idFactory ?? (() => crypto.randomUUID());
    this.sourceRevision = bench.state.revision; this.sourceEpoch = bench.state.attachmentEpoch;
    this.unsubscribe = bench.subscribe(state => this.observe(state));
  }
  get state(): WaveFieldState { return this.snapshot; }
  get enabled(): boolean { return this.snapshot.enabled; }
  get gate() { return this.bench.gate; }
  get canRetryPresentation(): boolean { return !!this.snapshot.completedNumerical && !!this.completedIdentity && this.fresh(this.completedIdentity); }
  bindPresentation(prepare: ((result: WaveFieldResult) => WaveFieldPrepared) | null): void { this.prepare = prepare; }
  subscribe(listener: (state: WaveFieldState) => void): () => void { this.listeners.add(listener); this.notify(listener); return () => this.listeners.delete(listener); }
  private notify(listener: (state: WaveFieldState) => void): void {
    try { listener(this.snapshot); } catch (error) {
      const current = this.snapshot.currentResult;
      if (current) this.completedIdentity = { revision: this.bench.state.revision, sourceEpoch: this.bench.state.attachmentEpoch,
        viewEpoch: this.snapshot.attachmentEpoch, experiment: current.experiment };
      this.snapshot = Object.freeze({ ...this.snapshot,
        completedNumerical: current ?? this.snapshot.completedNumerical, currentResult: null, renderError: message(error) });
    }
  }
  private publish(change: Partial<WaveFieldState>): void { this.snapshot = Object.freeze({ ...this.snapshot, ...change }); for (const listener of this.listeners) this.notify(listener); }
  private observe(source: BenchState): void {
    const changed = this.sourceRevision !== source.revision || this.sourceEpoch !== source.attachmentEpoch;
    this.sourceRevision = source.revision; this.sourceEpoch = source.attachmentEpoch;
    if (changed || !source.validatedDraft || source.pendingValidation || Object.keys(source.invalidEdits).length) {
      this.completedIdentity = null;
      this.publish({ currentResult: null, completedNumerical: null, error: null,
        ...(changed ? { attachmentEpoch: this.snapshot.attachmentEpoch + 1 } : {}) });
    } else this.publish({});
  }
  /** Changing views invalidates attachment even when leaving and returning to the same draft. */
  setContext(enabled: boolean, activeSequential: boolean): void {
    if (enabled === this.snapshot.enabled && activeSequential === this.snapshot.activeView) return;
    this.completedIdentity = null;
    this.publish({ enabled, activeView: activeSequential, attachmentEpoch: this.snapshot.attachmentEpoch + 1,
      currentResult: null, completedNumerical: null, error: null, renderError: null });
  }
  private fresh(identity: { revision: number; sourceEpoch: number; viewEpoch: number; experiment: Experiment }): boolean {
    const source = this.bench.state;
    return this.snapshot.enabled && this.snapshot.activeView && this.snapshot.attachmentEpoch === identity.viewEpoch
      && source.revision === identity.revision && source.attachmentEpoch === identity.sourceEpoch
      && !source.pendingValidation && !Object.keys(source.invalidEdits).length && structuralEqual(source.validatedDraft, identity.experiment);
  }
  reportPresentationFailure(error: string | null): void {
    if (!error) { this.publish({ renderError: null }); return; }
    const result = this.snapshot.currentResult;
    if (result) {
      this.completedIdentity = { revision: this.bench.state.revision, sourceEpoch: this.bench.state.attachmentEpoch,
        viewEpoch: this.snapshot.attachmentEpoch, experiment: result.experiment };
    }
    this.publish({ currentResult: null, completedNumerical: result ?? this.snapshot.completedNumerical, renderError: error });
  }
  private attach(result: WaveFieldResult): boolean {
    let transaction: WaveFieldPrepared | null = null;
    const previousLast = this.snapshot.lastResult;
    const start = performance.now();
    try {
      if (!this.prepare) throw new Error('Computed Sections presentation is unavailable; numerical result retained without replay.');
      transaction = this.prepare(result); transaction.commit();
      this.publish({ lastResult: result, currentResult: result, completedNumerical: null, renderError: null,
        timings: this.snapshot.timings ? Object.freeze({ ...this.snapshot.timings, attachmentMs: performance.now() - start }) : null });
      if (this.snapshot.currentResult !== result || this.snapshot.renderError) throw new Error(this.snapshot.renderError ?? 'W1 presentation subscriber failed');
      transaction.finalize(); this.completedIdentity = null; return true;
    } catch (error) { transaction?.dispose(); this.publish({ lastResult: previousLast, currentResult: null, completedNumerical: result, renderError: message(error) }); return false; }
  }
  /** Exactly one explicit operation; no retry, queue, draft mutation or automatic replay. */
  async simulate(): Promise<boolean> {
    const source = this.bench.state;
    if (this.disposed || !this.enabled || !this.snapshot.activeView || this.gate.busy || this.snapshot.active || !source.validatedDraft
        || source.pendingValidation || Object.keys(source.invalidEdits).length) return false;
    let request: WaveFieldRequest;
    try {
      const experiment = freezeExperiment(source.validatedDraft), sampling = buildWaveFieldSampling(experiment);
      const estimate = estimateWaveFieldOperation(experiment);
      (this.options.reserveOperation ?? this.options.admit)(estimate.persistentBytes, estimate.transientBytes);
      request = Object.freeze({ request_id: this.id(), experiment, sampling });
    } catch (error) { this.publish({ error: message(error) }); return false; }
    if (!this.gate.acquire(request.request_id, 'sequential', 'single')) return false;
    const identity = { revision: source.revision, sourceEpoch: source.attachmentEpoch, viewEpoch: this.snapshot.attachmentEpoch, experiment: request.experiment };
    this.publish({ active: Object.freeze({ request, revision: identity.revision, sourceEpoch: identity.sourceEpoch, viewEpoch: identity.viewEpoch }), error: null, renderError: null });
    try {
      const start = performance.now(); let frame: ArrayBuffer | null = await this.api.simulate(request); const decodeStart = performance.now();
      const result = decodeWaveFieldResult(frame, request), complete = performance.now();
      // Decoder owns independent arrays. Release the joined frame before display preparation.
      frame = null;
      if (this.disposed) return false;
      this.publish({ timings: Object.freeze({ httpAndDecodeMs: complete - start, decodeMs: complete - decodeStart, attachmentMs: 0 }) });
      if (this.state.active?.request.request_id !== request.request_id) return false;
      if (!this.fresh(identity)) { this.publish({ active: null, lastResult: result, currentResult: null, completedNumerical: null }); return true; }
      this.completedIdentity = identity; this.publish({ active: null, completedNumerical: result }); this.attach(result); return true;
    } catch (error) {
      if (this.state.active?.request.request_id === request.request_id) this.publish({ active: null, error: message(error) });
      return false;
    } finally { this.gate.release(request.request_id); }
  }
  retryPresentation(): boolean {
    if (this.gate.busy || !this.canRetryPresentation) return false;
    return this.attach(this.snapshot.completedNumerical!);
  }
  numericalOwners(): (WaveFieldResult | null)[] { return [this.snapshot.currentResult, this.snapshot.lastResult, this.snapshot.completedNumerical]; }
  ownedNumericalBytes(): number { return waveFieldOwnedResults(this.numericalOwners()); }
  releaseResults(): boolean {
    if (this.gate.busy || this.snapshot.active) return false;
    this.completedIdentity = null; this.publish({ lastResult: null, currentResult: null, completedNumerical: null, error: null, renderError: null, timings: null }); return true;
  }
  dispose(): void { this.disposed = true; this.unsubscribe(); this.listeners.clear(); this.prepare = null;
    this.snapshot = Object.freeze({ ...this.snapshot, enabled: false, activeView: false, currentResult: null, lastResult: null, completedNumerical: null }); }
}
