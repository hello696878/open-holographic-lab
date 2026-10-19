/** Complete immutable V2g outcomes. Viewing and explicit release perform no optics. */
import { structuralEqual } from './contracts';
import { ClientOperationGate } from './state';
import { assertPolarizedTwoPathExperiment, createPolarizedTwoPathFetchAPI, decodePolarizedTwoPathResult,
  fixedPolarizedTwoPathExperiment, freezePolarizedTwoPathExperiment, SWEEP_PHASES_RAD, validatePolarizedTwoPathReply,
  validatePolarizedTwoPathSweep, validatePolarizedTwoPathSweepReply, type DecodedPolarizedTwoPathResult,
  type DecodedPolarizedTwoPathSweep, type PolarizedTwoPathAPI, type PolarizedTwoPathEnvelope,
  type PolarizedTwoPathExperiment, type PolarizedTwoPathSweepEnvelope } from './polarized_two_path_contracts';
export interface PreparedPolarizedTwoPathPresentation { commit(): void; dispose(): void; finalize?(): void }
export interface PolarizedTwoPathState {
  readonly candidate: PolarizedTwoPathExperiment; readonly validatedDraft: PolarizedTwoPathExperiment | null;
  readonly pendingValidation: boolean; readonly pendingSweepValidation: boolean; readonly invalidEdits: Readonly<Record<string, string>>;
  readonly revision: number; readonly attachmentEpoch: number; readonly selection: string; readonly viewSelection: 'raw' | 'analyzed';
  readonly status: 'idle' | 'validating' | 'ready' | 'simulating' | 'sweeping' | 'error'; readonly error: string | null; readonly renderError: string | null;
  readonly active: Readonly<{ requestId: string; kind: 'single' | 'sweep'; experiment: PolarizedTwoPathExperiment;
    revision: number; attachmentEpoch: number; resultGeneration: number }> | null;
  readonly lastResult: DecodedPolarizedTwoPathResult | null; readonly currentResult: DecodedPolarizedTwoPathResult | null;
  readonly completedNumerical: DecodedPolarizedTwoPathResult | null;
  readonly lastSweep: DecodedPolarizedTwoPathSweep | null; readonly currentSweep: DecodedPolarizedTwoPathSweep | null;
  readonly selectedSweepIndex: number | null;
}
const numericText = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
const messageOf = (error: unknown) => error instanceof Error ? error.message : 'Unknown polarized two-path failure';
export class PolarizedTwoPathController {
  private snapshot: PolarizedTwoPathState;
  private listeners = new Set<(state: PolarizedTwoPathState) => void>();
  private generation = 0; private resultsGeneration = 0; private validatedHash: string | null = null;
  private prepareResult: (result: DecodedPolarizedTwoPathResult) => PreparedPolarizedTwoPathPresentation = () => ({ commit() {}, dispose() {} });
  private beforeOperation: (kind: 'single' | 'sweep', experiment: PolarizedTwoPathExperiment) => void = () => {};
  constructor(initial: PolarizedTwoPathExperiment, private api: PolarizedTwoPathAPI = createPolarizedTwoPathFetchAPI(),
      private idFactory: () => string = () => crypto.randomUUID(), readonly gate = new ClientOperationGate()) {
    this.snapshot = Object.freeze({ candidate: freezePolarizedTwoPathExperiment(initial), validatedDraft: null,
      pendingValidation: false, pendingSweepValidation: false, invalidEdits: Object.freeze({}), revision: 0, attachmentEpoch: 0,
      selection: 'input', viewSelection: 'raw', status: 'idle', error: null, renderError: null, active: null,
      lastResult: null, currentResult: null, completedNumerical: null, lastSweep: null, currentSweep: null, selectedSweepIndex: null });
  }
  get state(): PolarizedTwoPathState { return this.snapshot; }
  get resultGeneration(): number { return this.resultsGeneration; }
  setResultPreparer(value: (result: DecodedPolarizedTwoPathResult) => PreparedPolarizedTwoPathPresentation): void { this.prepareResult = value; }
  setOperationAdmission(value: (kind: 'single' | 'sweep', experiment: PolarizedTwoPathExperiment) => void): void { this.beforeOperation = value; }
  subscribe(listener: (state: PolarizedTwoPathState) => void): () => void { this.listeners.add(listener); this.notify(listener); return () => this.listeners.delete(listener); }
  private notify(listener: (state: PolarizedTwoPathState) => void): void {
    try { listener(this.snapshot); } catch (error) { this.snapshot = Object.freeze({ ...this.snapshot, renderError: messageOf(error) }); }
  }
  private publish(change: Partial<PolarizedTwoPathState>): void {
    const next = { ...this.snapshot, ...change };
    next.status = next.active ? next.active.kind === 'sweep' ? 'sweeping' : 'simulating'
      : next.pendingValidation || next.pendingSweepValidation ? 'validating' : next.error || Object.keys(next.invalidEdits).length ? 'error' : next.validatedDraft ? 'ready' : 'idle';
    this.snapshot = Object.freeze(next); this.listeners.forEach(listener => this.notify(listener));
  }
  deactivate(): void { ++this.generation; this.validatedHash = null;
    this.publish({ attachmentEpoch: this.snapshot.attachmentEpoch + 1, validatedDraft: null, pendingValidation: false,
      pendingSweepValidation: false, currentResult: null, currentSweep: null }); }
  async activate(): Promise<void> { await this.validateInitial(); }
  async validateInitial(): Promise<void> {
    if (!this.snapshot.validatedDraft && !this.snapshot.pendingValidation && !Object.keys(this.snapshot.invalidEdits).length) await this.validateCandidate();
  }
  private envelope(digest: string | null, experiment = this.snapshot.candidate): PolarizedTwoPathEnvelope {
    return Object.freeze({ protocol_version: 1, message_type: 'polarized_two_path_submission', request_id: this.idFactory(),
      experiment_sha256: digest, experiment: freezePolarizedTwoPathExperiment(experiment) });
  }
  private async validateCandidate(): Promise<void> {
    const generation = ++this.generation; this.validatedHash = null; const envelope = this.envelope(null);
    this.publish({ pendingValidation: true, validatedDraft: null, error: null });
    try { const reply = validatePolarizedTwoPathReply(await this.api.validate(envelope), envelope);
      if (generation !== this.generation) return; this.validatedHash = reply.experiment_sha256;
      this.publish({ validatedDraft: reply.experiment, pendingValidation: false, error: null });
    } catch (error) { if (generation !== this.generation) return; this.publish({ validatedDraft: null, pendingValidation: false, error: messageOf(error) }); }
  }
  async replaceCandidate(experiment: PolarizedTwoPathExperiment): Promise<void> {
    ++this.generation; this.validatedHash = null;
    const selections = [...experiment.arm_0.actions, ...experiment.arm_1.actions].map(item => item.id);
    const reserved = ['input', 'splitter', 'combiner', 'arm_0', 'arm_1', 'port_0', 'port_1', 'analyzer'];
    this.publish({ candidate: freezePolarizedTwoPathExperiment(experiment), validatedDraft: null, pendingValidation: false,
      pendingSweepValidation: false, invalidEdits: Object.freeze({}), revision: this.snapshot.revision + 1,
      currentResult: null, currentSweep: null, error: null, renderError: null,
      selection: [...reserved, ...selections].includes(this.snapshot.selection) ? this.snapshot.selection : 'input' });
    await this.validateCandidate();
  }
  prepareValidatedSettings(experiment: PolarizedTwoPathExperiment, transientDigest: string): () => void {
    if (this.gate.busy || this.snapshot.active) throw new Error('Cannot restore settings during computation');
    assertPolarizedTwoPathExperiment(experiment); if (!/^[0-9a-f]{64}$/.test(transientDigest)) throw new Error('Invalid transient scientific digest');
    const previous = this.snapshot, generation = this.generation, canonical = freezePolarizedTwoPathExperiment(experiment);
    const next: PolarizedTwoPathState = Object.freeze({ ...previous, candidate: canonical, validatedDraft: canonical,
      pendingValidation: false, pendingSweepValidation: false, invalidEdits: Object.freeze({}), revision: previous.revision + 1,
      attachmentEpoch: previous.attachmentEpoch + 1, status: 'ready', error: null, renderError: null,
      currentResult: null, currentSweep: null, completedNumerical: null, selectedSweepIndex: null, selection: 'input', viewSelection: 'raw' });
    return () => { if (this.gate.busy || this.snapshot !== previous || this.generation !== generation) throw new Error('Settings destination changed before apply');
      ++this.generation; this.validatedHash = transientDigest; this.snapshot = next; this.listeners.forEach(listener => this.notify(listener)); };
  }
  restoreValidatedSettings(experiment: PolarizedTwoPathExperiment, transientDigest: string): void { this.prepareValidatedSettings(experiment, transientDigest)(); }
  async edit(path: string, text: string, scale = 1, integer = false): Promise<void> {
    if (!Number.isFinite(scale) || scale <= 0) throw new Error('Editor scale must be positive finite');
    ++this.generation; this.validatedHash = null; const invalid = { ...this.snapshot.invalidEdits }, input = text.trim();
    const raw = numericText.test(input) ? Number(input) : NaN, value = raw * scale;
    const erased = Number.isFinite(raw) && raw !== 0 && value === 0 || raw === 0 && /[1-9]/.test(input.split(/[eE]/, 1)[0]);
    if (!Number.isFinite(value) || erased || integer && !Number.isSafeInteger(value)) {
      invalid[path] = text; this.publish({ invalidEdits: Object.freeze(invalid), validatedDraft: null, pendingValidation: false, pendingSweepValidation: false,
        revision: this.snapshot.revision + 1, currentResult: null, currentSweep: null, error: 'Enter a complete, finite, representable number.', renderError: null }); return;
    }
    const experiment = structuredClone(this.snapshot.candidate), segments = path.split('.'); let owner: unknown = experiment;
    for (const segment of segments.slice(0, -1)) { if (!owner || typeof owner !== 'object' || !Object.hasOwn(owner, segment)) throw new Error(`Unknown numeric editor path ${path}`); owner = (owner as Record<string, unknown>)[segment]; }
    const key = segments.at(-1)!; if (!owner || typeof owner !== 'object' || typeof (owner as Record<string, unknown>)[key] !== 'number') throw new Error(`Unknown numeric editor path ${path}`);
    (owner as Record<string, unknown>)[key] = value; delete invalid[path];
    this.publish({ candidate: freezePolarizedTwoPathExperiment(experiment), invalidEdits: Object.freeze(invalid), validatedDraft: null,
      pendingValidation: false, pendingSweepValidation: false, revision: this.snapshot.revision + 1, currentResult: null, currentSweep: null, error: null, renderError: null });
    if (!Object.keys(invalid).length) await this.validateCandidate();
  }
  async setAnalyzerEnabled(enabled: boolean): Promise<void> { const experiment = structuredClone(this.snapshot.candidate); experiment.analyzer.enabled = enabled; await this.replaceCandidate(experiment); }
  select(id: string): void {
    if (!['input', 'splitter', 'combiner', 'arm_0', 'arm_1', 'port_0', 'port_1', 'analyzer', ...this.snapshot.candidate.arm_0.actions.map(a => a.id), ...this.snapshot.candidate.arm_1.actions.map(a => a.id)].includes(id)) throw new Error(`Unknown selection ${id}`);
    this.publish({ selection: id });
  }
  selectView(view: 'raw' | 'analyzed'): void {
    if (view !== 'raw' && view !== 'analyzed' || view === 'analyzed' && !this.snapshot.currentResult?.analyzedPorts) throw new Error('Analyzed view requires completed analyzed data');
    this.publish({ viewSelection: view });
  }
  reportRenderFailure(message: string | null): void { this.publish({ renderError: message }); }
  clearRenderFailure(): void { this.reportRenderFailure(null); }
  invalidatePresentation(message: string): void { this.publish({ currentResult: null, renderError: message }); }
  /** Small result-only transition; scientific drafts, validation identity and document context stay intact. */
  releaseResults(): boolean {
    if (this.gate.busy || this.snapshot.active) return false;
    const previous = this.snapshot;
    if (this.gate.busy || this.snapshot !== previous || this.snapshot.active) return false;
    ++this.resultsGeneration;
    this.publish({ lastResult: null, currentResult: null, completedNumerical: null, lastSweep: null, currentSweep: null,
      selectedSweepIndex: null, renderError: null, viewSelection: 'raw', pendingSweepValidation: false }); return true;
  }
  private available(): boolean { return !this.gate.busy && !this.snapshot.active && !this.snapshot.pendingValidation && !this.snapshot.pendingSweepValidation
    && !!this.snapshot.validatedDraft && !!this.validatedHash && !Object.keys(this.snapshot.invalidEdits).length; }
  private fresh(active: NonNullable<PolarizedTwoPathState['active']>): boolean { return this.snapshot.revision === active.revision
    && this.snapshot.attachmentEpoch === active.attachmentEpoch && this.resultsGeneration === active.resultGeneration
    && !this.snapshot.pendingValidation && !Object.keys(this.snapshot.invalidEdits).length && structuralEqual(this.snapshot.validatedDraft, active.experiment); }
  private present(result: DecodedPolarizedTwoPathResult, active?: NonNullable<PolarizedTwoPathState['active']>): boolean {
    const revision = this.snapshot.revision, epoch = this.snapshot.attachmentEpoch, generation = this.resultsGeneration;
    const eligible = () => generation === this.resultsGeneration && revision === this.snapshot.revision && epoch === this.snapshot.attachmentEpoch
      && structuralEqual(this.snapshot.validatedDraft, result.experiment) && (!active || this.snapshot.active?.requestId === active.requestId && this.fresh(active));
    let prepared: PreparedPolarizedTwoPathPresentation | null = null;
    try { prepared = this.prepareResult(result); if (!eligible()) { prepared.dispose(); return false; } prepared.commit();
      if (!eligible()) { prepared.dispose(); return false; }
    } catch (error) { let message = messageOf(error); try { prepared?.dispose(); } catch (cleanup) { message += `; cleanup: ${messageOf(cleanup)}`; }
      if (generation === this.resultsGeneration) this.publish({ active: null, completedNumerical: result, renderError: message }); return false;
    }
    this.publish({ active: null, lastResult: result, completedNumerical: result, currentResult: result, error: null, renderError: null,
      viewSelection: result.analyzedPorts ? this.snapshot.viewSelection : 'raw' });
    try { prepared.finalize?.(); } catch (error) { this.reportRenderFailure(messageOf(error)); } return true;
  }
  retryPresentation(): boolean { const result = this.snapshot.completedNumerical;
    if (!result || this.gate.busy || this.snapshot.active || !structuralEqual(result.experiment, this.snapshot.validatedDraft)) return false; return this.present(result); }
  async simulate(): Promise<boolean> {
    if (!this.available()) return false; const envelope = this.envelope(this.validatedHash, this.snapshot.validatedDraft!);
    const active = Object.freeze({ requestId: envelope.request_id, kind: 'single' as const, experiment: envelope.experiment,
      revision: this.snapshot.revision, attachmentEpoch: this.snapshot.attachmentEpoch, resultGeneration: this.resultsGeneration });
    try { this.beforeOperation('single', active.experiment); } catch (error) { this.publish({ error: messageOf(error) }); return false; }
    if (!this.available() || !this.gate.acquire(active.requestId, 'polarized_two_path', 'single')) return false;
    this.publish({ active, error: null, renderError: null });
    try { const result = decodePolarizedTwoPathResult(await this.api.simulate(envelope), envelope);
      if (this.snapshot.active?.requestId !== active.requestId) return false;
      if (!this.fresh(active)) { this.publish({ active: null, completedNumerical: result, currentResult: null }); return true; }
      this.present(result, active); if (this.snapshot.active?.requestId === active.requestId) this.publish({ active: null, completedNumerical: result }); return true;
    } catch (error) { if (this.snapshot.active?.requestId !== active.requestId) return false; this.publish({ active: null, error: messageOf(error) }); return false; }
    finally { this.gate.release(active.requestId); }
  }
  async runSweep(): Promise<boolean> {
    if (!this.available()) return false;
    const experiment = freezePolarizedTwoPathExperiment(this.snapshot.validatedDraft!), revision = this.snapshot.revision,
      epoch = this.snapshot.attachmentEpoch, generation = this.resultsGeneration, validationGeneration = this.generation;
    const initial: PolarizedTwoPathSweepEnvelope = Object.freeze({ protocol_version: 1, message_type: 'polarized_two_path_sweep_submission',
      request_id: this.idFactory(), fixed_experiment_sha256: null, fixed_experiment: fixedPolarizedTwoPathExperiment(experiment), phases_rad: SWEEP_PHASES_RAD });
    this.publish({ pendingSweepValidation: true, error: null });
    let validation;
    const eligible = () => revision === this.snapshot.revision && epoch === this.snapshot.attachmentEpoch && generation === this.resultsGeneration
      && validationGeneration === this.generation && !this.snapshot.pendingValidation && !Object.keys(this.snapshot.invalidEdits).length && structuralEqual(this.snapshot.validatedDraft, experiment);
    try { validation = validatePolarizedTwoPathSweepReply(await this.api.validateSweep(initial), initial); }
    catch (error) { if (eligible()) this.publish({ pendingSweepValidation: false, error: messageOf(error) }); return false; }
    if (!eligible()) return false;
    this.publish({ pendingSweepValidation: false });
    if (!this.available()) return false;
    const envelope: PolarizedTwoPathSweepEnvelope = Object.freeze({ ...initial, fixed_experiment_sha256: validation.fixed_experiment_sha256 });
    const active = Object.freeze({ requestId: envelope.request_id, kind: 'sweep' as const, experiment, revision, attachmentEpoch: epoch, resultGeneration: generation });
    try { this.beforeOperation('sweep', experiment); } catch (error) { this.publish({ error: messageOf(error) }); return false; }
    if (!eligible() || !this.available() || !this.gate.acquire(active.requestId, 'polarized_two_path', 'sweep')) return false;
    this.publish({ active, error: null });
    try { const response = await this.api.sweep(envelope), result = validatePolarizedTwoPathSweep(response.body, envelope, response.httpStatus, validation.sweep_sha256);
      if (this.snapshot.active?.requestId !== active.requestId) return false; const fresh = this.fresh(active);
      this.publish({ active: null, lastSweep: result, currentSweep: fresh ? result : null, selectedSweepIndex: null,
        error: fresh && result.status === 'failed' ? `FAILED / PARTIAL ${result.completedCount}/17 · HTTP ${result.httpStatus}: ${result.error!.message}` : null }); return result.status === 'complete';
    } catch (error) { if (this.snapshot.active?.requestId !== active.requestId) return false; this.publish({ active: null, error: messageOf(error) }); return false; }
    finally { this.gate.release(active.requestId); }
  }
  selectSweepPoint(index: number): void { if (!Number.isSafeInteger(index) || !this.snapshot.lastSweep?.rows.some(row => row.index === index)) throw new Error('No actual completed sweep row'); this.publish({ selectedSweepIndex: index }); }
  async applySelectedPhaseAndSimulate(): Promise<boolean> {
    if (this.gate.busy || this.snapshot.active || this.snapshot.selectedSweepIndex === null || !this.snapshot.lastSweep) return false;
    const sweep = this.snapshot.lastSweep, row = sweep.rows.find(item => item.index === this.snapshot.selectedSweepIndex); if (!row) return false;
    const intended = freezePolarizedTwoPathExperiment({ ...sweep.fixedExperiment, relative_phase_rad: row.phase_rad }), generation = this.resultsGeneration;
    const validating = this.replaceCandidate(intended), revision = this.snapshot.revision, epoch = this.snapshot.attachmentEpoch; await validating;
    if (generation !== this.resultsGeneration || revision !== this.snapshot.revision || epoch !== this.snapshot.attachmentEpoch || !structuralEqual(this.snapshot.validatedDraft, intended)) return false;
    return this.simulate();
  }
}
