/** Explicit V2d submissions and immutable identities. Viewing never invokes optics. */
import { structuralEqual } from './contracts';
import { ClientOperationGate } from './state';
import { assertPolarizationExperiment, createPolarizationFetchAPI, decodePolarizationResult, freezePolarizationExperiment, SWEEP_ANGLES_RAD,
  validatePolarizationReply, validatePolarizationSweep, type DecodedPolarizationResult, type DecodedPolarizationSweep,
  type PolarizationAPI, type PolarizationEnvelope, type PolarizationExperiment, type PolarizationSweepEnvelope } from './polarization_contracts';
export interface PreparedPolarizationPresentation { commit(): void; dispose(): void; finalize?(): void }
export interface PolarizationState {
  readonly candidate: PolarizationExperiment; readonly validatedDraft: PolarizationExperiment | null;
  readonly pendingValidation: boolean; readonly invalidEdits: Readonly<Record<string, string>>;
  readonly revision: number; readonly attachmentEpoch: number; readonly selection: string; readonly selectedStage: string;
  readonly status: 'idle' | 'validating' | 'ready' | 'simulating' | 'sweeping' | 'error';
  readonly error: string | null; readonly renderError: string | null;
  readonly active: Readonly<{ requestId: string; kind: 'single' | 'sweep'; experiment: PolarizationExperiment; revision: number; attachmentEpoch: number }> | null;
  readonly lastResult: DecodedPolarizationResult | null; readonly currentResult: DecodedPolarizationResult | null;
  readonly completedNumerical: DecodedPolarizationResult | null;
  readonly lastSweep: DecodedPolarizationSweep | null; readonly currentSweep: DecodedPolarizationSweep | null; readonly selectedSweepIndex: number | null;
}
const numericText = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
const messageOf = (error: unknown): string => error instanceof Error ? error.message : 'Unknown V2d failure';
export class PolarizationController {
  private snapshot: PolarizationState;
  private listeners = new Set<(state: PolarizationState) => void>();
  private generation = 0;
  private validatedHash: string | null = null;
  private resultsGeneration = 0;
  private prepareResult: (result: DecodedPolarizationResult) => PreparedPolarizationPresentation = () => ({ commit() {}, dispose() {} });
  private beforeOperation: (kind: 'single' | 'sweep', experiment: PolarizationExperiment) => void = () => {};
  constructor(initial: PolarizationExperiment, private api: PolarizationAPI = createPolarizationFetchAPI(),
      private idFactory: () => string = () => crypto.randomUUID(), readonly gate = new ClientOperationGate()) {
    this.snapshot = Object.freeze({ candidate: freezePolarizationExperiment(initial), validatedDraft: null, pendingValidation: false,
      invalidEdits: Object.freeze({}), revision: 0, attachmentEpoch: 0, selection: 'source', selectedStage: 'input', status: 'idle',
      error: null, renderError: null, active: null, lastResult: null, currentResult: null, completedNumerical: null,
      lastSweep: null, currentSweep: null, selectedSweepIndex: null });
  }
  get state(): PolarizationState { return this.snapshot; }
  get resultGeneration(): number { return this.resultsGeneration; }
  /** Release numerical outputs and retry handles, retaining every scientific edit. */
  releaseResults(): boolean {
    if (this.gate.busy || this.snapshot.active) return false;
    const previous = this.snapshot;
    if (this.gate.busy || this.snapshot !== previous || this.snapshot.active) return false;
    ++this.resultsGeneration;
    this.publish({ lastResult: null, currentResult: null, completedNumerical: null,
      lastSweep: null, currentSweep: null, selectedSweepIndex: null, renderError: null }); return true;
  }
  setResultPreparer(value: (result: DecodedPolarizationResult) => PreparedPolarizationPresentation): void { this.prepareResult = value; }
  setOperationAdmission(value: (kind: 'single' | 'sweep', experiment: PolarizationExperiment) => void): void { this.beforeOperation = value; }
  subscribe(listener: (state: PolarizationState) => void): () => void {
    this.listeners.add(listener); this.notify(listener); return () => this.listeners.delete(listener);
  }
  private notify(listener: (state: PolarizationState) => void): void {
    try { listener(this.snapshot); } catch (error) { this.snapshot = Object.freeze({ ...this.snapshot, renderError: messageOf(error) }); }
  }
  private publish(change: Partial<PolarizationState>): void {
    const next = { ...this.snapshot, ...change };
    next.status = next.active ? next.active.kind === 'sweep' ? 'sweeping' : 'simulating' : next.pendingValidation ? 'validating'
      : next.error || Object.keys(next.invalidEdits).length ? 'error' : next.validatedDraft ? 'ready' : 'idle';
    this.snapshot = Object.freeze(next); this.listeners.forEach(listener => this.notify(listener));
  }
  deactivate(): void {
    ++this.generation; this.validatedHash = null;
    this.publish({ attachmentEpoch: this.snapshot.attachmentEpoch + 1, validatedDraft: null, pendingValidation: false, currentResult: null, currentSweep: null });
  }
  async activate(): Promise<void> { await this.validateInitial(); }
  async validateInitial(): Promise<void> {
    if (!this.snapshot.validatedDraft && !this.snapshot.pendingValidation && !Object.keys(this.snapshot.invalidEdits).length) await this.validateCandidate();
  }
  private envelope(message_type: 'polarization_submission', digest: string | null, experiment = this.snapshot.candidate): PolarizationEnvelope {
    return Object.freeze({ protocol_version: 1, message_type, request_id: this.idFactory(),
      experiment: freezePolarizationExperiment(experiment), experiment_sha256: digest });
  }
  private async validateCandidate(): Promise<void> {
    const generation = ++this.generation; this.validatedHash = null;
    const envelope = this.envelope('polarization_submission', null); this.publish({ pendingValidation: true, validatedDraft: null, error: null });
    try {
      const reply = validatePolarizationReply(await this.api.validate(envelope), envelope);
      if (generation !== this.generation) return;
      this.validatedHash = reply.experiment_sha256; this.publish({ validatedDraft: reply.experiment, pendingValidation: false, error: null });
    } catch (error) {
      if (generation !== this.generation) return;
      this.publish({ validatedDraft: null, pendingValidation: false, error: messageOf(error) });
    }
  }
  async replaceCandidate(experiment: PolarizationExperiment): Promise<void> {
    ++this.generation; this.validatedHash = null;
    this.publish({ candidate: freezePolarizationExperiment(experiment), validatedDraft: null, pendingValidation: false,
      invalidEdits: Object.freeze({}), revision: this.snapshot.revision + 1, currentResult: null, currentSweep: null,
      selection: experiment.elements.some(item => item.id === this.snapshot.selection) ? this.snapshot.selection : 'source', error: null, renderError: null });
    await this.validateCandidate();
  }
  /** Prepare a coherent restored editor and invalidate even identical old attachment eligibility. */
  prepareValidatedSettings(experiment: PolarizationExperiment, transientDigest: string): () => void {
    if (this.gate.busy || this.snapshot.active) throw new Error('Cannot restore settings during computation');
    assertPolarizationExperiment(experiment);
    if (!/^[0-9a-f]{64}$/.test(transientDigest)) throw new Error('Invalid transient scientific digest');
    const previous = this.snapshot, generation = this.generation, canonical = freezePolarizationExperiment(experiment);
    const next: PolarizationState = Object.freeze({ ...previous, candidate: canonical, validatedDraft: canonical,
      pendingValidation: false, invalidEdits: Object.freeze({}), revision: previous.revision + 1,
      attachmentEpoch: previous.attachmentEpoch + 1, status: 'ready', error: null, renderError: null,
      currentResult: null, currentSweep: null, completedNumerical: null, selectedSweepIndex: null, selection: 'source', selectedStage: 'input' });
    return () => {
      if (this.gate.busy || this.snapshot !== previous || this.generation !== generation) throw new Error('Settings destination changed before apply');
      ++this.generation; this.validatedHash = transientDigest; this.snapshot = next;
      this.listeners.forEach(listener => this.notify(listener));
    };
  }
  restoreValidatedSettings(experiment: PolarizationExperiment, transientDigest: string): void { this.prepareValidatedSettings(experiment, transientDigest)(); }
  async edit(path: string, text: string, integer = false): Promise<void> {
    ++this.generation; this.validatedHash = null;
    const invalid = { ...this.snapshot.invalidEdits }, trimmed = text.trim(), value = numericText.test(trimmed) ? Number(trimmed) : NaN;
    if (!Number.isFinite(value) || integer && !Number.isSafeInteger(value)) {
      invalid[path] = text;
      this.publish({ invalidEdits: Object.freeze(invalid), validatedDraft: null, pendingValidation: false,
        revision: this.snapshot.revision + 1, currentResult: null, currentSweep: null, error: '請輸入完整有限數值（Finite number）', renderError: null }); return;
    }
    const experiment = structuredClone(this.snapshot.candidate), segments = path.split('.'); let owner: unknown = experiment;
    for (const segment of segments.slice(0, -1)) {
      if (!owner || typeof owner !== 'object' || !Object.hasOwn(owner, segment)) throw new Error(`Unknown numeric editor path ${path}`);
      owner = (owner as Record<string, unknown>)[segment];
    }
    const key = segments.at(-1)!;
    if (!owner || typeof owner !== 'object' || typeof (owner as Record<string, unknown>)[key] !== 'number') throw new Error(`Unknown numeric editor path ${path}`);
    (owner as Record<string, unknown>)[key] = value; delete invalid[path];
    this.publish({ candidate: freezePolarizationExperiment(experiment), invalidEdits: Object.freeze(invalid), validatedDraft: null,
      pendingValidation: false, revision: this.snapshot.revision + 1, currentResult: null, currentSweep: null, error: null, renderError: null });
    if (!Object.keys(invalid).length) await this.validateCandidate();
  }
  select(id: string): void {
    if (id !== 'source' && !this.snapshot.candidate.elements.some(item => item.id === id)) throw new Error(`Unknown element ID ${id}`);
    this.publish({ selection: id });
  }
  selectStage(id: string): void {
    if (!this.snapshot.lastResult?.orderedStageIds.includes(id)) throw new Error(`Unknown completed stage ${id}`);
    this.publish({ selectedStage: id });
  }
  reportRenderFailure(message: string | null): void { this.publish({ renderError: message }); }
  invalidatePresentation(message: string): void { this.publish({ currentResult: null, renderError: message }); }
  private available(): boolean { return !this.gate.busy && !this.snapshot.active && !this.snapshot.pendingValidation
    && !!this.snapshot.validatedDraft && !!this.validatedHash && !Object.keys(this.snapshot.invalidEdits).length; }
  private fresh(active: NonNullable<PolarizationState['active']>): boolean {
    return this.snapshot.revision === active.revision && this.snapshot.attachmentEpoch === active.attachmentEpoch
      && !this.snapshot.pendingValidation && !Object.keys(this.snapshot.invalidEdits).length && structuralEqual(this.snapshot.validatedDraft, active.experiment);
  }
  private present(result: DecodedPolarizationResult): boolean {
    const resultsGeneration = this.resultsGeneration;
    let prepared: PreparedPolarizationPresentation | null = null;
    try { prepared = this.prepareResult(result);
      if (resultsGeneration !== this.resultsGeneration) { prepared.dispose(); return false; }
      prepared.commit();
      if (resultsGeneration !== this.resultsGeneration) { prepared.dispose(); return false; }
    }
    catch (error) {
      let message = messageOf(error); try { prepared?.dispose(); } catch (cleanup) { message += `; cleanup: ${messageOf(cleanup)}`; }
      if (resultsGeneration !== this.resultsGeneration) return false;
      const previous = this.snapshot.currentResult;
      this.publish({ active: null, completedNumerical: result,
        currentResult: previous && structuralEqual(previous.experiment, result.experiment) ? previous : null, renderError: message }); return false;
    }
    this.publish({ active: null, lastResult: result, completedNumerical: result, currentResult: result, error: null, renderError: null,
      selectedStage: result.orderedStageIds.includes(this.snapshot.selectedStage) ? this.snapshot.selectedStage : 'input' });
    try { prepared.finalize?.(); } catch (error) { this.reportRenderFailure(messageOf(error)); } return true;
  }
  /** Explicit presentation retry reuses numerics; never sends a scientific request. */
  retryPresentation(): boolean {
    const result = this.snapshot.completedNumerical;
    if (!result || this.snapshot.active || !structuralEqual(result.experiment, this.snapshot.validatedDraft)) return false;
    return this.present(result);
  }
  async simulate(): Promise<boolean> {
    if (!this.available()) return false;
    const envelope = this.envelope('polarization_submission', this.validatedHash, this.snapshot.validatedDraft!);
    const active = Object.freeze({ requestId: envelope.request_id, kind: 'single' as const, experiment: envelope.experiment,
      revision: this.snapshot.revision, attachmentEpoch: this.snapshot.attachmentEpoch });
    try { this.beforeOperation('single', active.experiment); } catch (error) { this.publish({ error: messageOf(error) }); return false; }
    if (!this.gate.acquire(active.requestId, 'polarization', 'single')) return false;
    this.publish({ active, error: null, renderError: null });
    try {
      const result = decodePolarizationResult(await this.api.simulate(envelope), envelope);
      if (this.snapshot.active?.requestId !== active.requestId) return false;
      if (!this.fresh(active)) { this.publish({ active: null, lastResult: result, completedNumerical: result, currentResult: null }); return true; }
      this.present(result); return true; // Numerical success is independent of presentation success.
    } catch (error) {
      if (this.snapshot.active?.requestId !== active.requestId) return false;
      this.publish({ active: null, error: messageOf(error) }); return false;
    } finally { this.gate.release(active.requestId); }
  }
  async runSweep(): Promise<boolean> {
    if (!this.available()) return false;
    const selected = this.snapshot.validatedDraft!.elements.find(item => item.id === this.snapshot.selection && item.kind === 'linear_polarizer');
    if (!selected) { this.publish({ error: '請選取列表中的線偏振片（linear polarizer）；未送出掃描。' }); return false; }
    const base = this.envelope('polarization_submission', this.validatedHash, this.snapshot.validatedDraft!);
    const envelope: PolarizationSweepEnvelope = Object.freeze({ ...base, message_type: 'polarization_sweep_submission',
      selected_element_id: selected.id, angles_rad: SWEEP_ANGLES_RAD });
    const active = Object.freeze({ requestId: envelope.request_id, kind: 'sweep' as const, experiment: envelope.experiment,
      revision: this.snapshot.revision, attachmentEpoch: this.snapshot.attachmentEpoch });
    try { this.beforeOperation('sweep', active.experiment); } catch (error) { this.publish({ error: messageOf(error) }); return false; }
    if (!this.gate.acquire(active.requestId, 'polarization', 'sweep')) return false;
    this.publish({ active, error: null });
    try {
      const response = await this.api.sweep(envelope), result = validatePolarizationSweep(response.body, envelope, response.httpStatus);
      if (this.snapshot.active?.requestId !== active.requestId) return false;
      const fresh = this.fresh(active);
      this.publish({ active: null, lastSweep: result, currentSweep: fresh ? result : null, selectedSweepIndex: null,
        error: fresh && result.status === 'failed' ? `FAILED / PARTIAL ${result.completedCount}/13 · HTTP ${result.httpStatus}: ${result.error!.message}` : null });
      return result.status === 'complete';
    } catch (error) {
      if (this.snapshot.active?.requestId !== active.requestId) return false;
      this.publish({ active: null, error: messageOf(error) }); return false;
    } finally { this.gate.release(active.requestId); }
  }
  selectSweepPoint(index: number): void {
    if (!Number.isSafeInteger(index) || !this.snapshot.lastSweep?.rows.some(row => row.index === index)) throw new Error('No actual completed sweep point');
    this.publish({ selectedSweepIndex: index });
  }
  async applySelectedAngleAndSimulate(): Promise<boolean> {
    if (this.gate.busy || this.snapshot.active || this.snapshot.selectedSweepIndex === null || !this.snapshot.lastSweep) return false;
    const sweep = this.snapshot.lastSweep, resultsGeneration = this.resultsGeneration, row = sweep.rows.find(item => item.index === this.snapshot.selectedSweepIndex);
    if (!row) return false;
    const intended = structuredClone(sweep.experiment), element = intended.elements.find(item => item.id === sweep.selectedElementId)!;
    element.axis_angle_rad = row.axis_angle_rad;
    const validating = this.replaceCandidate(intended), revision = this.snapshot.revision, epoch = this.snapshot.attachmentEpoch;
    await validating;
    if (this.resultsGeneration !== resultsGeneration || this.snapshot.revision !== revision || this.snapshot.attachmentEpoch !== epoch || !structuralEqual(this.snapshot.validatedDraft, intended)) return false;
    return this.simulate();
  }
}
