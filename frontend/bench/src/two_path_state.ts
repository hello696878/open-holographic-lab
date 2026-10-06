/** Explicit V2b submission; no optical calculation or implicit retries. */
import { structuralEqual } from './contracts';
import { ClientOperationGate } from './state';
import { cloneTwoPathExperiment, createTwoPathFetchAPI, decodeTwoPathResult, fixedTwoPathExperiment,
  freezeTwoPathExperiment, SWEEP_PHASES_RAD, validateTwoPathReply, validateTwoPathSweep,
  type DecodedTwoPathResult, type DecodedTwoPathSweep, type TwoPathAPI, type TwoPathEnvelope,
  type TwoPathExperiment, type TwoPathSweepEnvelope } from './two_path_contracts';

export interface PreparedDualPresentation {
  /** Synchronous pair swap. No old-resource disposal until finalized. */
  commit(): void;
  /** Dispose newly prepared resources if publication did not complete. */
  dispose(): void;
  /** Dispose obsolete resources only after immutable state publication. */
  finalize?(): void;
}
export type PrepareDualResult = (result: DecodedTwoPathResult) => PreparedDualPresentation;
export interface TwoPathState {
  readonly candidate: TwoPathExperiment; readonly validatedDraft: TwoPathExperiment | null;
  readonly pendingValidation: boolean; readonly invalidEdits: Readonly<Record<string, string>>;
  readonly revision: number; readonly attachmentEpoch: number;
  readonly status: 'idle' | 'validating' | 'ready' | 'simulating' | 'sweeping' | 'error';
  readonly error: string | null; readonly renderError: string | null; readonly selection: string;
  readonly active: Readonly<{ requestId: string; kind: 'single' | 'sweep'; experiment: TwoPathExperiment;
    revision: number; attachmentEpoch: number }> | null;
  readonly lastResult: DecodedTwoPathResult | null; readonly currentResult: DecodedTwoPathResult | null;
  /** Successful numerics remain recoverable when presentation preparation failed. */
  readonly completedNumerical: DecodedTwoPathResult | null;
  readonly lastSweep: DecodedTwoPathSweep | null; readonly currentSweep: DecodedTwoPathSweep | null;
  readonly selectedSweepIndex: number | null;
}
const numericText = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
const messageOf = (error: unknown) => error instanceof Error ? error.message : 'Unknown V2b failure';
const selections = ['source', 'B', 'arm_0', 'arm_1', 'phase', 'B_dagger', 'port_0', 'port_1'];

export class TwoPathController {
  private snapshot: TwoPathState;
  private listeners = new Set<(state: TwoPathState) => void>();
  private generation = 0;
  private validatedHash: string | null = null;
  constructor(initial: TwoPathExperiment, private api: TwoPathAPI = createTwoPathFetchAPI(),
      private idFactory: () => string = () => crypto.randomUUID(), readonly gate = new ClientOperationGate(),
      private prepareResult: PrepareDualResult = () => ({ commit() {}, dispose() {} })) {
    this.snapshot = Object.freeze({ candidate: freezeTwoPathExperiment(initial), validatedDraft: null,
      pendingValidation: false, invalidEdits: Object.freeze({}), revision: 0, attachmentEpoch: 0,
      status: 'idle', error: null, renderError: null, selection: 'source', active: null,
      lastResult: null, currentResult: null, completedNumerical: null, lastSweep: null, currentSweep: null, selectedSweepIndex: null });
  }
  get state(): TwoPathState { return this.snapshot; }
  setResultPreparer(preparer: PrepareDualResult): void { this.prepareResult = preparer; }
  subscribe(listener: (state: TwoPathState) => void): () => void {
    this.listeners.add(listener); this.notify(listener); return () => this.listeners.delete(listener);
  }
  private notify(listener: (state: TwoPathState) => void): void {
    try { listener(this.snapshot); }
    catch (error) { this.snapshot = Object.freeze({ ...this.snapshot, renderError: messageOf(error) }); }
  }
  private publish(change: Partial<TwoPathState>): void {
    const next = { ...this.snapshot, ...change };
    next.status = next.active ? next.active.kind === 'sweep' ? 'sweeping' : 'simulating'
      : next.pendingValidation ? 'validating' : next.error || Object.keys(next.invalidEdits).length ? 'error'
        : next.validatedDraft ? 'ready' : 'idle';
    this.snapshot = Object.freeze(next); this.listeners.forEach(listener => this.notify(listener));
  }
  deactivate(): void {
    ++this.generation; this.validatedHash = null;
    this.publish({ attachmentEpoch: this.snapshot.attachmentEpoch + 1, validatedDraft: null,
      pendingValidation: false, currentResult: null, currentSweep: null });
  }
  async activate(): Promise<void> { await this.validateInitial(); }
  async validateInitial(): Promise<void> {
    if (!this.snapshot.validatedDraft && !this.snapshot.pendingValidation && !Object.keys(this.snapshot.invalidEdits).length) await this.validateCandidate();
  }
  private async validateCandidate(): Promise<void> {
    const generation = ++this.generation; this.validatedHash = null;
    const envelope: TwoPathEnvelope = Object.freeze({ protocol_version: 1, message_type: 'two_path_submission',
      request_id: this.idFactory(), experiment: freezeTwoPathExperiment(this.snapshot.candidate) });
    this.publish({ pendingValidation: true, validatedDraft: null, error: null });
    try {
      const reply = validateTwoPathReply(await this.api.validate(envelope), envelope);
      if (generation !== this.generation) return;
      this.validatedHash = reply.experiment_sha256;
      this.publish({ pendingValidation: false, validatedDraft: reply.experiment, error: null });
    } catch (error) {
      if (generation !== this.generation) return;
      this.publish({ pendingValidation: false, validatedDraft: null, error: messageOf(error) });
    }
  }
  async replaceCandidate(experiment: TwoPathExperiment): Promise<void> {
    ++this.generation; this.validatedHash = null;
    this.publish({ candidate: freezeTwoPathExperiment(experiment), validatedDraft: null, pendingValidation: false,
      invalidEdits: Object.freeze({}), revision: this.snapshot.revision + 1, currentResult: null, currentSweep: null,
      error: null, renderError: null });
    await this.validateCandidate();
  }
  async edit(path: string, text: string, scale = 1, integer = false): Promise<void> {
    if (!Number.isFinite(scale) || scale <= 0) throw new Error('Editor scale must be positive finite');
    ++this.generation; this.validatedHash = null;
    const invalid = { ...this.snapshot.invalidEdits }; const input = text.trim();
    const value = numericText.test(input) ? Number(input) * scale : NaN;
    if (!Number.isFinite(value) || integer && !Number.isSafeInteger(value)) {
      invalid[path] = text;
      this.publish({ invalidEdits: Object.freeze(invalid), validatedDraft: null, pendingValidation: false,
        revision: this.snapshot.revision + 1, currentResult: null, currentSweep: null, error: '請輸入完整有限數值（Finite number）', renderError: null });
      return;
    }
    const candidate = cloneTwoPathExperiment(this.snapshot.candidate); const segments = path.split('.'); let owner: unknown = candidate;
    for (const segment of segments.slice(0, -1)) {
      if (!owner || typeof owner !== 'object' || !Object.hasOwn(owner, segment)) throw new Error(`Unknown editor path: ${path}`);
      owner = (owner as Record<string, unknown>)[segment];
    }
    const key = segments.at(-1)!;
    if (!owner || typeof owner !== 'object' || typeof (owner as Record<string, unknown>)[key] !== 'number') throw new Error(`Unknown numeric editor path: ${path}`);
    (owner as Record<string, unknown>)[key] = value; delete invalid[path];
    this.publish({ candidate: freezeTwoPathExperiment(candidate), invalidEdits: Object.freeze(invalid), validatedDraft: null,
      pendingValidation: false, revision: this.snapshot.revision + 1, currentResult: null, currentSweep: null, error: null, renderError: null });
    if (!Object.keys(invalid).length) await this.validateCandidate();
  }
  select(id: string): void { if (!selections.includes(id)) throw new Error(`Unknown two-path selection: ${id}`); this.publish({ selection: id }); }
  reportRenderFailure(message: string | null): void { this.publish({ renderError: message }); }
  clearRenderFailure(): void { this.reportRenderFailure(null); }
  private available(): boolean {
    return !this.gate.busy && !this.snapshot.active && !this.snapshot.pendingValidation
      && !!this.snapshot.validatedDraft && !!this.validatedHash && !Object.keys(this.snapshot.invalidEdits).length;
  }
  private fresh(active: NonNullable<TwoPathState['active']>): boolean {
    return this.snapshot.revision === active.revision && this.snapshot.attachmentEpoch === active.attachmentEpoch
      && !this.snapshot.pendingValidation && !Object.keys(this.snapshot.invalidEdits).length
      && structuralEqual(this.snapshot.validatedDraft, active.experiment);
  }
  async simulate(): Promise<boolean> {
    if (!this.available()) return false;
    const active = Object.freeze({ requestId: this.idFactory(), kind: 'single' as const,
      experiment: freezeTwoPathExperiment(this.snapshot.validatedDraft!), revision: this.snapshot.revision,
      attachmentEpoch: this.snapshot.attachmentEpoch });
    const submittedHash = this.validatedHash;
    const envelope: TwoPathEnvelope = Object.freeze({ protocol_version: 1, message_type: 'two_path_submission', request_id: active.requestId, experiment: active.experiment });
    if (!this.gate.acquire(active.requestId, 'two_path', 'single')) return false;
    this.publish({ active, error: null, renderError: null });
    try {
      const result = decodeTwoPathResult(await this.api.simulate(envelope), envelope);
      if (result.experimentSha256 !== submittedHash) throw new Error('V2b protocol: result hash differs from validated snapshot');
      if (this.snapshot.active?.requestId !== active.requestId) return false;
      if (!this.fresh(active)) {
        this.publish({ active: null, lastResult: result, completedNumerical: result, currentResult: null }); return true;
      }
      let prepared: PreparedDualPresentation | null = null;
      try {
        prepared = this.prepareResult(result);
        prepared.commit();
      } catch (error) {
        let message = messageOf(error);
        try { prepared?.dispose(); } catch (cleanup) { message += `; presentation cleanup: ${messageOf(cleanup)}`; }
        this.publish({ active: null, completedNumerical: result, currentResult: null, renderError: message });
        return true; // Numerical completion remains distinct from presentation preparation failure.
      }
      this.publish({ active: null, lastResult: result, currentResult: result, completedNumerical: result, error: null });
      try { prepared.finalize?.(); } catch (error) { this.reportRenderFailure(messageOf(error)); }
      return true;
    } catch (error) {
      if (this.snapshot.active?.requestId !== active.requestId) return false;
      this.publish({ active: null, error: messageOf(error) }); return false;
    } finally { this.gate.release(active.requestId); }
  }
  async runSweep(): Promise<boolean> {
    if (!this.available()) return false;
    if (this.snapshot.validatedDraft!.grid.nx > 128 || this.snapshot.validatedDraft!.grid.ny > 128) {
      this.publish({ error: 'Phase sweep grid must be at most 128 per axis; no request was sent.' }); return false;
    }
    const active = Object.freeze({ requestId: this.idFactory(), kind: 'sweep' as const,
      experiment: freezeTwoPathExperiment(this.snapshot.validatedDraft!), revision: this.snapshot.revision,
      attachmentEpoch: this.snapshot.attachmentEpoch });
    const envelope: TwoPathSweepEnvelope = Object.freeze({ protocol_version: 1, message_type: 'two_path_sweep_submission',
      request_id: active.requestId, fixed_experiment: fixedTwoPathExperiment(active.experiment), phases_rad: SWEEP_PHASES_RAD });
    if (!this.gate.acquire(active.requestId, 'two_path', 'sweep')) return false;
    this.publish({ active, error: null });
    try {
      const response = await this.api.sweep(envelope); const sweep = validateTwoPathSweep(response.body, envelope, response.httpStatus);
      if (this.snapshot.active?.requestId !== active.requestId) return false;
      const fresh = this.fresh(active);
      this.publish({ active: null, lastSweep: sweep, currentSweep: fresh ? sweep : null, selectedSweepIndex: null,
        error: fresh ? sweep.status === 'failed' ? `Phase sweep failed after ${sweep.completedCount}/17 actual points: ${sweep.error!.message}` : null : this.snapshot.error });
      return sweep.status === 'complete';
    } catch (error) {
      if (this.snapshot.active?.requestId !== active.requestId) return false;
      this.publish({ active: null, error: messageOf(error) }); return false;
    } finally { this.gate.release(active.requestId); }
  }
  selectSweepPoint(index: number): void {
    if (!Number.isSafeInteger(index) || !this.snapshot.lastSweep?.rows.some(row => row.index === index)) throw new Error('No calculated sweep row at this index');
    this.publish({ selectedSweepIndex: index });
  }
  async simulateSelectedPhase(): Promise<boolean> {
    if (this.gate.busy || this.snapshot.active || this.snapshot.selectedSweepIndex === null || !this.snapshot.lastSweep) return false;
    const sweep = this.snapshot.lastSweep; const row = sweep.rows.find(item => item.index === this.snapshot.selectedSweepIndex);
    if (!row) return false;
    const fixed = sweep.fixedExperiment;
    const intended = freezeTwoPathExperiment({ wavelength_m: fixed.wavelength_m, grid: fixed.grid, source: fixed.source,
      two_arm_spec: { arm_0_distance_m: fixed.arm_0_distance_m, arm_1_distance_m: fixed.arm_1_distance_m, relative_phase_rad: row.phase_rad } });
    const validating = this.replaceCandidate(intended);
    const revision = this.snapshot.revision, attachmentEpoch = this.snapshot.attachmentEpoch;
    await validating;
    // The explicit action belongs only to its captured draft and mode lifetime.
    // A later edit/away-and-back switch cannot turn it into a run of a different draft.
    if (this.snapshot.revision !== revision || this.snapshot.attachmentEpoch !== attachmentEpoch
        || !structuralEqual(this.snapshot.candidate, intended) || !structuralEqual(this.snapshot.validatedDraft, intended)) return false;
    return this.simulate();
  }
}
