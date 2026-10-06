import { cloneExperiment, createFetchAPI, decodeResult, freezeExperiment, structuralEqual,
  validateValidationReply, type BenchAPI, type DecodedResult, type Experiment, type RequestEnvelope } from './contracts';
export type { BenchAPI } from './contracts';

/** One synchronous client operation slot, shared by both modes and sweep. */
export class ClientOperationGate {
  private operation: Readonly<{ requestId: string; mode: 'sequential' | 'two_path'; kind: 'single' | 'sweep' }> | null = null;
  private listeners = new Set<() => void>();
  get active() { return this.operation; }
  get busy(): boolean { return this.operation !== null; }
  subscribe(listener: () => void): () => void { this.listeners.add(listener); return () => this.listeners.delete(listener); }
  private notify(): void {
    for (const listener of this.listeners) { try { listener(); } catch { /* Viewing cannot strand a client operation. */ } }
  }
  acquire(requestId: string, mode: 'sequential' | 'two_path', kind: 'single' | 'sweep'): boolean {
    if (this.operation) return false;
    this.operation = Object.freeze({ requestId, mode, kind }); this.notify(); return true;
  }
  release(requestId: string): void {
    if (this.operation?.requestId !== requestId) return;
    this.operation = null; this.notify();
  }
}

export interface BenchState {
  readonly candidate: Experiment;
  readonly validatedDraft: Experiment | null;
  readonly pendingValidation: boolean;
  readonly invalidEdits: Readonly<Record<string, string>>;
  readonly revision: number;
  readonly attachmentEpoch: number;
  readonly status: 'idle' | 'validating' | 'ready' | 'simulating' | 'error';
  readonly error: string | null;
  readonly selection: string;
  readonly active: Readonly<{ requestId: string; experiment: Experiment; revision: number; attachmentEpoch: number }> | null;
  readonly lastResult: DecodedResult | null;
  readonly currentResult: DecodedResult | null;
  readonly renderError: string | null;
}
type Listener = (state: BenchState) => void;
const numericText = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
const messageOf = (error: unknown) => error instanceof Error ? error.message : 'Unknown V1 request failure';

/** Explicit submission actor. Viewing state never enters this controller. */
export class BenchController {
  private snapshot: BenchState;
  private listeners = new Set<Listener>();
  private validationGeneration = 0;
  private validatedHash: string | null = null;
  constructor(initial: Experiment, private api: BenchAPI = createFetchAPI(),
      private idFactory: () => string = () => crypto.randomUUID(), readonly gate = new ClientOperationGate()) {
    this.snapshot = Object.freeze({ candidate: freezeExperiment(initial), validatedDraft: null,
      pendingValidation: false, invalidEdits: Object.freeze({}), revision: 0, attachmentEpoch: 0, status: 'idle', error: null,
      selection: 'source', active: null, lastResult: null, currentResult: null, renderError: null });
  }
  get state(): BenchState { return this.snapshot; }
  /** Mode switches invalidate attachment even when switching away and back. */
  deactivate(): void {
    ++this.validationGeneration; this.validatedHash = null;
    this.publish({ attachmentEpoch: this.snapshot.attachmentEpoch + 1, validatedDraft: null,
      pendingValidation: false, currentResult: null });
  }
  async activate(): Promise<void> {
    if (!Object.keys(this.snapshot.invalidEdits).length) await this.validateInitial();
  }
  subscribe(listener: Listener): () => void {
    this.listeners.add(listener); this.notify(listener);
    return () => { this.listeners.delete(listener); };
  }
  private notify(listener: Listener): void {
    try { listener(this.snapshot); }
    catch (error) {
      // A view failure cannot turn a completed numerical submission into a transport failure.
      this.snapshot = Object.freeze({ ...this.snapshot, renderError: messageOf(error) });
    }
  }
  private publish(change: Partial<BenchState>): void {
    const next = { ...this.snapshot, ...change };
    next.status = next.active ? 'simulating' : next.pendingValidation ? 'validating'
      : next.error || Object.keys(next.invalidEdits).length ? 'error' : next.validatedDraft ? 'ready' : 'idle';
    this.snapshot = Object.freeze(next);
    for (const listener of this.listeners) this.notify(listener);
  }
  /** Initial server validation is passive: no solver or replay call. */
  async validateInitial(): Promise<void> {
    if (this.snapshot.pendingValidation || this.snapshot.validatedDraft) return;
    await this.validateCandidate();
  }
  private async validateCandidate(): Promise<void> {
    const generation = ++this.validationGeneration;
    this.validatedHash = null;
    const envelope: RequestEnvelope = Object.freeze({ request_id: this.idFactory(), experiment: freezeExperiment(this.snapshot.candidate) });
    this.publish({ pendingValidation: true, validatedDraft: null, error: null });
    try {
      const reply = validateValidationReply(await this.api.validate(envelope), envelope);
      if (generation !== this.validationGeneration) return;
      this.validatedHash = reply.experiment_sha256;
      this.publish({ validatedDraft: reply.experiment, pendingValidation: false, error: null });
    } catch (error) {
      if (generation !== this.validationGeneration) return;
      this.publish({ pendingValidation: false, validatedDraft: null, error: messageOf(error) });
    }
  }
  async replaceCandidate(experiment: Experiment): Promise<void> {
    ++this.validationGeneration;
    this.validatedHash = null;
    const selection = this.snapshot.selection;
    const exists = selection === 'source' || selection === experiment.observation.id || experiment.components.some(c => c.id === selection);
    this.publish({ candidate: freezeExperiment(experiment), validatedDraft: null, pendingValidation: false,
      invalidEdits: Object.freeze({}), revision: this.snapshot.revision + 1, currentResult: null,
      selection: exists ? selection : 'source', error: null, renderError: null });
    await this.validateCandidate();
  }
  /** Dot paths name schema fields. Text remains separate until it is finite numeric input. */
  async edit(path: string, text: string, scale = 1, integer = false): Promise<void> {
    if (!Number.isFinite(scale) || scale <= 0) throw new Error('Editor scale must be positive finite');
    ++this.validationGeneration;
    this.validatedHash = null;
    const invalid = { ...this.snapshot.invalidEdits };
    const input = text.trim(); const value = numericText.test(input) ? Number(input) * scale : NaN;
    if (!Number.isFinite(value) || (integer && !Number.isSafeInteger(value))) {
      invalid[path] = text;
      this.publish({ invalidEdits: Object.freeze(invalid), validatedDraft: null, pendingValidation: false,
        revision: this.snapshot.revision + 1, currentResult: null, error: '請輸入完整有限數值（Finite number）', renderError: null });
      return;
    }
    const candidate = cloneExperiment(this.snapshot.candidate);
    const segments = path.split('.'); let owner: unknown = candidate;
    for (const segment of segments.slice(0, -1)) {
      if (owner === null || typeof owner !== 'object' || !Object.hasOwn(owner, segment)) throw new Error(`Unknown editor path: ${path}`);
      owner = (owner as Record<string, unknown>)[segment];
    }
    const key = segments.at(-1)!;
    if (owner === null || typeof owner !== 'object' || !Object.hasOwn(owner, key)
        || typeof (owner as Record<string, unknown>)[key] !== 'number') throw new Error(`Unknown numeric editor path: ${path}`);
    (owner as Record<string, unknown>)[key] = value;
    delete invalid[path];
    this.publish({ candidate: freezeExperiment(candidate), invalidEdits: Object.freeze(invalid),
      validatedDraft: null, pendingValidation: false, revision: this.snapshot.revision + 1,
      currentResult: null, error: null, renderError: null });
    if (Object.keys(invalid).length === 0) await this.validateCandidate();
  }
  select(id: string): void {
    if (id !== 'source' && id !== this.snapshot.candidate.observation.id && !this.snapshot.candidate.components.some(c => c.id === id)) {
      throw new Error(`Unknown selection: ${id}`);
    }
    this.publish({ selection: id });
  }
  reportRenderFailure(message: string | null): void { this.publish({ renderError: message }); }
  clearRenderFailure(): void { this.reportRenderFailure(null); }
  /** Busy is acquired synchronously before the first await and never retries itself. */
  async simulate(): Promise<boolean> {
    if (this.gate.busy || this.snapshot.active || this.snapshot.pendingValidation || !this.snapshot.validatedDraft || !this.validatedHash
        || Object.keys(this.snapshot.invalidEdits).length) return false;
    const active = Object.freeze({ requestId: this.idFactory(), experiment: freezeExperiment(this.snapshot.validatedDraft),
      revision: this.snapshot.revision, attachmentEpoch: this.snapshot.attachmentEpoch });
    const envelope = Object.freeze({ request_id: active.requestId, experiment: active.experiment });
    const submittedHash = this.validatedHash;
    if (!this.gate.acquire(active.requestId, 'sequential', 'single')) return false;
    this.publish({ active, error: null, renderError: null });
    try {
      const frame = await this.api.simulate(envelope);
      const result = decodeResult(frame, envelope);
      if (result.experimentSha256 !== submittedHash) throw new Error('V1 protocol: experiment hash differs from validated snapshot');
      if (this.state.active?.requestId !== active.requestId) return false;
      const fresh = this.snapshot.revision === active.revision && this.snapshot.attachmentEpoch === active.attachmentEpoch && !this.snapshot.pendingValidation
        && Object.keys(this.snapshot.invalidEdits).length === 0
        && structuralEqual(this.snapshot.validatedDraft, active.experiment);
      this.publish({ active: null, lastResult: result, currentResult: fresh ? result : null,
        error: fresh ? null : this.snapshot.error });
      return true;
    } catch (error) {
      if (this.state.active?.requestId !== active.requestId) return false;
      this.publish({ active: null, error: messageOf(error) });
      return false;
    } finally {
      this.gate.release(active.requestId);
    }
  }
}
