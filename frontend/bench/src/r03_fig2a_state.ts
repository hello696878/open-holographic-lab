/** One immutable submitted ensemble; view recovery is independent of computation. */
import { ClientOperationGate } from './state';
import { structuralEqual } from './contracts';
import { R03_DEFAULT, freezeR03Experiment, validateR03Reply, decodeR03Result, createR03FetchAPI,
  type R03Experiment, type R03Envelope, type R03Result, type R03API } from './r03_fig2a_contracts';

export interface R03Prepared { commit(): void; dispose(): void; finalize?(): void }
export interface R03State { readonly candidate: R03Experiment; readonly validatedDraft: R03Experiment | null;
  readonly pendingValidation: boolean; readonly invalidEdits: Readonly<Record<string, string>>; readonly revision: number;
  readonly attachmentEpoch: number; readonly selection: string; readonly error: string | null; readonly renderError: string | null;
  readonly active: Readonly<{ requestId: string; experiment: R03Experiment; revision: number; epoch: number; generation: number }> | null;
  readonly currentResult: R03Result | null; readonly lastResult: R03Result | null; readonly completedNumerical: R03Result | null }
const numeric = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
const message = (error: unknown) => error instanceof Error ? error.message : String(error);
export const R03_COMPONENTS = Object.freeze(['source', 'input_hwp', 'router', 'slm', 'qwp', 'hwp', 'measurement']);
export class R03Controller {
  private snapshot: R03State; private listeners = new Set<(state: R03State) => void>();
  private validationGeneration = 0; private resultsGeneration = 0; private validatedHash: string | null = null;
  private completionToken: { result: R03Result; revision: number; epoch: number; generation: number } | null = null;
  private prepare: (result: R03Result) => R03Prepared = () => ({ commit() {}, dispose() {} });
  private admission: () => void = () => {};
  constructor(initial: R03Experiment = { ...R03_DEFAULT }, private api: R03API = createR03FetchAPI(),
      private idFactory: () => string = () => crypto.randomUUID(), readonly gate = new ClientOperationGate()) {
    this.snapshot = Object.freeze({ candidate: freezeR03Experiment(initial), validatedDraft: null, pendingValidation: false,
      invalidEdits: Object.freeze({}), revision: 0, attachmentEpoch: 0, selection: 'slm', error: null, renderError: null,
      active: null, currentResult: null, lastResult: null, completedNumerical: null });
  }
  get state(): R03State { return this.snapshot; }
  get canRetryPresentation(): boolean { const token = this.completionToken;
    return !!token && token.result === this.snapshot.completedNumerical && token.revision === this.snapshot.revision
      && token.epoch === this.snapshot.attachmentEpoch && token.generation === this.resultsGeneration
      && !this.gate.busy && !this.snapshot.active && !this.snapshot.pendingValidation && !Object.keys(this.snapshot.invalidEdits).length
      && structuralEqual(this.snapshot.validatedDraft, token.result.experiment); }
  setResultPreparer(value: (result: R03Result) => R03Prepared): void { this.prepare = value; }
  setOperationAdmission(value: () => void): void { this.admission = value; }
  subscribe(listener: (state: R03State) => void): () => void { this.listeners.add(listener); this.notify(listener); return () => this.listeners.delete(listener); }
  private notify(listener: (state: R03State) => void): void { try { listener(this.snapshot); } catch (error) {
    this.snapshot = Object.freeze({ ...this.snapshot, renderError: message(error) }); } }
  private publish(change: Partial<R03State>): void { this.snapshot = Object.freeze({ ...this.snapshot, ...change }); this.listeners.forEach(l => this.notify(l)); }
  private envelope(sha: string | null, experiment = this.snapshot.candidate): R03Envelope { return Object.freeze({ protocol_version: 1,
    message_type: 'r03_ideal_submission', request_id: this.idFactory(), experiment: freezeR03Experiment(experiment), experiment_sha256: sha }); }
  async activate(): Promise<void> { if (!this.snapshot.validatedDraft && !this.snapshot.pendingValidation && !Object.keys(this.snapshot.invalidEdits).length) await this.validate(); }
  deactivate(): void { ++this.validationGeneration; this.validatedHash = null; this.publish({ attachmentEpoch: this.snapshot.attachmentEpoch + 1,
    validatedDraft: null, pendingValidation: false, currentResult: null }); }
  private async validate(): Promise<void> { const generation = ++this.validationGeneration, sent = this.envelope(null); this.validatedHash = null;
    this.publish({ pendingValidation: true, validatedDraft: null, error: null });
    try { const reply = validateR03Reply(await this.api.validate(sent), sent); if (generation !== this.validationGeneration) return;
      this.validatedHash = reply.experiment_sha256; this.publish({ validatedDraft: reply.experiment, pendingValidation: false, error: null });
    } catch (error) { if (generation === this.validationGeneration) this.publish({ pendingValidation: false, validatedDraft: null, error: message(error) }); }
  }
  async edit(key: string, value: string): Promise<void> {
    if (!['source_amplitude', 'mean_phase_rad', 'phase_std_rad', 'qwp_angle_rad', 'hwp_angle_rad', 'seed'].includes(key)) throw new Error('Unknown ideal-model editor');
    ++this.validationGeneration; this.validatedHash = null; const invalid = { ...this.snapshot.invalidEdits }, input = value.trim();
    const number = numeric.test(input) ? Number(input) : NaN;
    const erased = number === 0 && /[1-9]/.test(input.split(/[eE]/, 1)[0]);
    if (!Number.isFinite(number) || erased || key === 'seed' && !Number.isSafeInteger(number)) {
      invalid[key] = value; this.publish({ invalidEdits: Object.freeze(invalid), revision: this.snapshot.revision + 1, validatedDraft: null,
        pendingValidation: false, currentResult: null, error: '請輸入完整、有限且可表示的數值；seed 必須是整數。', renderError: null }); return;
    }
    const candidate = freezeR03Experiment({ ...this.snapshot.candidate, [key]: number }); delete invalid[key];
    this.publish({ candidate, invalidEdits: Object.freeze(invalid), revision: this.snapshot.revision + 1, validatedDraft: null,
      pendingValidation: false, currentResult: null, error: null, renderError: null });
    if (!Object.keys(invalid).length) await this.validate();
  }
  select(id: string): void { if (!R03_COMPONENTS.includes(id)) throw new Error('Unknown apparatus selection'); this.publish({ selection: id }); }
  reportRenderFailure(value: string | null): void { this.publish({ renderError: value }); }
  invalidatePresentation(value: string): void { this.publish({ currentResult: null, renderError: value }); }
  releaseResults(): boolean { if (this.gate.busy || this.snapshot.active) return false; ++this.resultsGeneration; this.completionToken = null;
    this.publish({ currentResult: null, lastResult: null, completedNumerical: null, renderError: null }); return true; }
  private fresh(active: NonNullable<R03State['active']>): boolean { return this.snapshot.revision === active.revision
    && this.snapshot.attachmentEpoch === active.epoch && this.resultsGeneration === active.generation && !this.snapshot.pendingValidation
    && !Object.keys(this.snapshot.invalidEdits).length && structuralEqual(this.snapshot.validatedDraft, active.experiment); }
  private present(result: R03Result, active?: NonNullable<R03State['active']>): boolean {
    const revision = this.snapshot.revision, epoch = this.snapshot.attachmentEpoch, generation = this.resultsGeneration;
    const eligible = () => generation === this.resultsGeneration && revision === this.snapshot.revision && epoch === this.snapshot.attachmentEpoch
      && structuralEqual(this.snapshot.validatedDraft, result.experiment) && (!active || this.snapshot.active?.requestId === active.requestId && this.fresh(active));
    let prepared: R03Prepared | null = null;
    try { prepared = this.prepare(result); if (!eligible()) { prepared.dispose(); return false; } prepared.commit();
      if (!eligible()) { prepared.dispose(); return false; }
    } catch (error) { try { prepared?.dispose(); } catch { /* preserve original display error */ }
      if (generation === this.resultsGeneration) this.publish({ active: null, completedNumerical: result, renderError: message(error) }); return false; }
    this.publish({ active: null, lastResult: result, completedNumerical: result, currentResult: result, error: null, renderError: null });
    try { prepared.finalize?.(); } catch (error) { this.reportRenderFailure(message(error)); } return true;
  }
  retryPresentation(): boolean { const result = this.snapshot.completedNumerical; if (!result || !this.canRetryPresentation) return false; return this.present(result); }
  async simulate(): Promise<boolean> {
    const available = () => !this.gate.busy && !this.snapshot.active && !this.snapshot.pendingValidation
      && !!this.snapshot.validatedDraft && !!this.validatedHash && !Object.keys(this.snapshot.invalidEdits).length;
    if (!available()) return false; const sent = this.envelope(this.validatedHash, this.snapshot.validatedDraft!);
    const active = Object.freeze({ requestId: sent.request_id, experiment: sent.experiment, revision: this.snapshot.revision,
      epoch: this.snapshot.attachmentEpoch, generation: this.resultsGeneration });
    try { this.admission(); } catch (error) { this.publish({ error: message(error) }); return false; }
    if (!available() || !this.gate.acquire(active.requestId, 'r03_ideal', 'single')) return false;
    this.publish({ active, error: null, renderError: null });
    try { const result = decodeR03Result(await this.api.simulate(sent), sent); if (this.snapshot.active?.requestId !== active.requestId) return false;
      this.completionToken = { result, revision: active.revision, epoch: active.epoch, generation: active.generation };
      if (!this.fresh(active)) { this.publish({ active: null, completedNumerical: result, currentResult: null }); return true; }
      this.present(result, active);
      // Preparation/commit may synchronously change attachment eligibility. Settlement still ends this intent.
      if (this.snapshot.active?.requestId === active.requestId) this.publish({ active: null, completedNumerical: result });
      return true;
    } catch (error) { if (this.snapshot.active?.requestId === active.requestId) this.publish({ active: null, error: message(error) }); return false;
    } finally { this.gate.release(active.requestId); }
  }
}
