import { describe, expect, it, vi } from 'vitest';
import { ExperimentDocumentController } from '../src/experiment_document_state';
import { makeExperimentDocument, ownExperimentDocument, type BenchMode, type DocumentAPI, type ExperimentDocument, type ValidatedDocument } from '../src/experiment_documents';
import { type DocumentFiles, type PreparedDownload } from '../src/experiment_document_files';
import { parseStrictJSON } from '../src/contracts';
import { presetExperiment } from '../src/presets';
import { twoPathPreset } from '../src/two_path_presets';
import { polarizationPreset } from '../src/polarization_presets';
import { BenchController, ClientOperationGate } from '../src/state';
import { TwoPathController } from '../src/two_path_state';
import { PolarizationController } from '../src/polarization_state';
function encoded(value: unknown) { return new TextEncoder().encode(JSON.stringify(value, null, 2) + '\n'); }
function definition(mode: BenchMode = 'sequential'): ExperimentDocument {
  const experiment = mode === 'sequential' ? presetExperiment('aperture') : mode === 'two_path' ? twoPathPreset('gaussian128') : polarizationPreset('analyzer');
  return makeExperimentDocument(mode, experiment, { title: `${mode} 中文😀`, notes: 'e\u0301\n\t保留' });
}
function validated(document: ExperimentDocument, digest = 'a'.repeat(64)): ValidatedDocument {
  return { document: ownExperimentDocument(document), bytes: encoded(document), experimentSha256: digest };
}
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (error: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { resolve, reject, promise }; }
async function until(check: () => boolean) { for (let i = 0; i < 100 && !check(); i++) await Promise.resolve(); expect(check()).toBe(true); }
class Files implements DocumentFiles {
  inputs = new Map<File, Uint8Array>(); prepared: PreparedDownload | null = null; reads = 0; releases = 0;
  async read(file: File, signal: AbortSignal) { this.reads++; if (signal.aborted) throw new Error('aborted'); return this.inputs.get(file)!; }
  prepareDownload(bytes: Uint8Array, filename: string) { this.dismissDownload(); return this.prepared = { bytes, filename, blob: new Blob([new Uint8Array(bytes).buffer]), url: `blob:owned-${this.releases}` }; }
  dismissDownload() { if (this.prepared) this.releases++; this.prepared = null; }
  ownershipSnapshot() { return { activeReaders: 0, readerReservedBytes: 0, urls: this.prepared ? 1 : 0, blobBytes: this.prepared?.blob.size ?? 0 }; }
  dispose() { this.dismissDownload(); }
  file(value: unknown, name = 'same.json') { const bytes = typeof value === 'string' ? new TextEncoder().encode(value) : encoded(value);
    const file = new File([new Uint8Array(bytes).buffer], name); this.inputs.set(file, bytes); return file; }
}
function setup(apiOverride?: DocumentAPI) {
  const files = new Files(), calls: Uint8Array[] = [], applied: ValidatedDocument[] = [];
  const state = { mode: 'sequential' as BenchMode, token: 's:0:0|t:0:0|p:0:0', busy: false, retained: 0,
    draft: { mode: 'sequential' as BenchMode, experiment: presetExperiment('aperture'), revision: 0, attachmentEpoch: 0 } };
  const api: DocumentAPI = apiOverride ?? { async validate(bytes) { calls.push(new Uint8Array(bytes));
    return validated(ownExperimentDocument(parseStrictJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes)))); } };
  const prepare = vi.fn((document: ValidatedDocument) => () => { applied.push(document); state.mode = document.document.mode; state.token += ':applied'; });
  const actor = new ExperimentDocumentController({ context: () => state, currentValidDraft: () => state.draft, busy: () => state.busy,
    prepareApply: prepare, api, files, retainedBytes: () => state.retained });
  return { actor, files, calls, applied, state, prepare };
}
describe('explicit frozen document operations', () => {
  it.each(['sequential', 'two_path', 'polarization'] as BenchMode[])('imports %s in two stages and applies only after explicit acknowledgment', async mode => {
    const { actor, files, calls, applied, state } = setup();
    expect(await actor.importFile(files.file(definition(mode)))).toBe(true);
    expect(calls, 'DOCUMENT_ZERO_COMPUTE_DETECTED').toHaveLength(2);
    expect(applied, 'TRANSACTIONAL_IMPORT_DETECTED').toHaveLength(0); expect(state.mode).toBe('sequential');
    expect(actor.applyImport()).toBe(false); actor.acknowledgeReplacement(true);
    expect(actor.applyImport(), 'TRANSACTIONAL_IMPORT_DETECTED').toBe(true);
    expect(applied[0].document.mode).toBe(mode); expect(actor.state.status).toBe('restored');
    expect(actor.state.metadata[mode]).toEqual(definition(mode).metadata); expect(actor.state.preview).toBeNull();
  });
  it('rejects raw duplicates before the second request while preserving every editor', async () => {
    const { actor, files, calls, applied, state } = setup(), before = structuredClone(state);
    const raw = '{"document_format":"ohlab_virtual_experiment","document_format":"wrong"}';
    expect(await actor.importFile(files.file(raw)), 'RAW_DUPLICATE_KEYS_DETECTED').toBe(false);
    expect(new TextDecoder().decode(calls[0]), 'RAW_DUPLICATE_KEYS_DETECTED').toBe(raw);
    expect(calls).toHaveLength(1); expect(applied, 'TRANSACTIONAL_IMPORT_DETECTED').toHaveLength(0); expect(state).toEqual(before);
  });
  it('detects legal nonzero drift in either authoritative stage', async () => {
    for (const failedStage of [1, 2]) {
      let count = 0; const api: DocumentAPI = { async validate(bytes) { count++; const doc = ownExperimentDocument(parseStrictJSON(new TextDecoder().decode(bytes)));
        const changed = structuredClone(doc); if (count === failedStage && changed.mode === 'sequential') changed.experiment.observation.z_m = .03;
        return validated(changed); } };
      const { actor, files, applied } = setup(api);
      expect(await actor.importFile(files.file(definition())), 'TWO_STAGE_NONZERO_DRIFT_DETECTED').toBe(false);
      expect(actor.state.preview, 'TWO_STAGE_NONZERO_DRIFT_DETECTED').toBeNull(); expect(applied, 'TRANSACTIONAL_IMPORT_DETECTED').toHaveLength(0);
    }
  });
  it('installs only the final digest and applies documented signed zero behavior', async () => {
    let count = 0; const api: DocumentAPI = { async validate(bytes) { return validated(ownExperimentDocument(parseStrictJSON(new TextDecoder().decode(bytes))), (++count === 1 ? '1' : '2').repeat(64)); } };
    const { actor, files, applied } = setup(api); const doc = structuredClone(definition('two_path'));
    if (doc.mode === 'two_path') { doc.experiment.source.phase_rad = -0; doc.experiment.two_arm_spec.arm_0_distance_m = -0; }
    const raw = JSON.stringify(doc).replace('"amplitude":1', '"amplitude":-0.0');
    expect(await actor.importFile(files.file(raw))).toBe(true); actor.acknowledgeReplacement(true); actor.applyImport();
    expect(applied[0].experimentSha256, 'DOCUMENT_DIGEST_SEPARATION_DETECTED').toBe('2'.repeat(64));
    expect(encoded(applied[0].document)).not.toContain('experiment_sha256');
    if (applied[0].document.mode === 'two_path') expect(Object.is(applied[0].document.experiment.source.amplitude, -0)).toBe(false);
  });
  it('freezes valid draft export at click instead of substituting an old result or later edit', async () => {
    const task = deferred<ValidatedDocument>(), requests: ExperimentDocument[] = [];
    const api: DocumentAPI = { async validate(bytes) { requests.push(ownExperimentDocument(parseStrictJSON(new TextDecoder().decode(bytes)))); return task.promise; } };
    const { actor, state } = setup(api); state.draft.experiment.observation.z_m = .020000000000000004;
    actor.setMetadata('sequential', { title: 'frozen', notes: '' }); const exporting = actor.exportCurrent(); await until(() => requests.length === 1);
    state.draft.experiment.observation.z_m = .04; state.draft.revision++; actor.setMetadata('sequential', { title: 'later', notes: '' });
    task.resolve(validated(requests[0])); expect(await exporting).toBe(true);
    const prepared = actor.state.preparedDownload!;
    expect(prepared.document.metadata.title, 'EXPORT_FROZEN_DRAFT_IDENTITY_DETECTED').toBe('frozen');
    if (prepared.document.mode === 'sequential') expect(prepared.document.experiment.observation.z_m, 'EXPORT_FROZEN_DRAFT_IDENTITY_DETECTED').toBe(.020000000000000004);
    actor.markDownloadRequested(); expect(actor.state.preparedDownload!.url).toBe(prepared.url); expect(actor.state.status).toBe('download_requested');
    actor.dismissDownload(); expect(actor.ownershipSnapshot().urls).toBe(0);
  });
  it('cancels preview and preserves state when destination changes or worker becomes busy', async () => {
    const { actor, files, state, applied } = setup(); await actor.importFile(files.file(definition('polarization'))); actor.acknowledgeReplacement(true);
    state.busy = true; expect(actor.applyImport(), 'TRANSACTIONAL_IMPORT_DETECTED').toBe(false); expect(applied).toHaveLength(0);
    state.busy = false; state.token += ':edit';
    expect(actor.applyImport(), 'STALE_IMPORT_GENERATION_DETECTED').toBe(false); actor.contextChanged(); expect(actor.state.preview).toBeNull();
    await actor.importFile(files.file(definition())); actor.cancelImport(); expect(applied).toHaveLength(0); expect(state.mode).toBe('sequential');
  });
  it.each([1, 2])('rejects a stale stage %i reply after editing or selecting a newer same-size file', async heldStage => {
    const held = deferred<ValidatedDocument>(); let count = 0; let pending!: ExperimentDocument;
    const api: DocumentAPI = { async validate(bytes) { const parsed = ownExperimentDocument(parseStrictJSON(new TextDecoder().decode(bytes))); if (++count === heldStage) { pending = parsed; return held.promise; } return validated(parsed); } };
    const { actor, files, state } = setup(api), first = actor.importFile(files.file(definition())); await until(() => count === heldStage);
    state.token += ':edited'; actor.contextChanged(); held.resolve(validated(pending));
    expect(await first, 'STALE_IMPORT_GENERATION_DETECTED').toBe(false); expect(actor.state.preview).toBeNull();
  });
  it('bounds overlapping same-name same-size file attempts and publishes only latest content', async () => {
    const held = deferred<ValidatedDocument>(); let first!: ExperimentDocument; let count = 0;
    const api: DocumentAPI = { async validate(bytes) { const parsed = ownExperimentDocument(parseStrictJSON(new TextDecoder().decode(bytes))); if (++count === 1) { first = parsed; return held.promise; } return validated(parsed); } };
    const { actor, files } = setup(api), a = structuredClone(definition()), b = structuredClone(definition());
    (a.metadata as { title: string }).title = 'A'; (b.metadata as { title: string }).title = 'B';
    const fa = files.file(a), fb = files.file(b); expect(fa.name).toBe(fb.name); expect(fa.size).toBe(fb.size);
    const older = actor.importFile(fa); await until(() => count === 1); const superseded = actor.importFile(fa), newer = actor.importFile(fb);
    expect(actor.ownershipSnapshot().pendingSelections).toBe(1); expect(files.reads).toBe(1); held.resolve(validated(first));
    expect(await older).toBe(false); expect(await superseded).toBe(false); expect(await newer, 'STALE_IMPORT_GENERATION_DETECTED').toBe(true);
    expect(actor.state.preview!.document.metadata.title).toBe('B'); expect(files.reads).toBe(2);
  });
  it.each([1, 2])('checks destination token at stage %i settlement even before a UI notification', async heldStage => {
    const held = deferred<ValidatedDocument>(); let count = 0; let pending!: ExperimentDocument;
    const api: DocumentAPI = { async validate(bytes) { const parsed = ownExperimentDocument(parseStrictJSON(new TextDecoder().decode(bytes)));
      if (++count === heldStage) { pending = parsed; return held.promise; } return validated(parsed); } };
    const { actor, files, state } = setup(api), importing = actor.importFile(files.file(definition())); await until(() => count === heldStage);
    // Deliberately omit contextChanged to test the authoritative settlement guard independently of abort.
    state.token += ':newer-destination'; held.resolve(validated(pending));
    expect(await importing, 'STALE_IMPORT_GENERATION_DETECTED').toBe(false); expect(actor.state.preview).toBeNull(); actor.contextChanged();
  });
  it('metadata is separate from optical state and prepare failures publish no replacement', async () => {
    const { actor, files, state, prepare, applied } = setup(); const before = structuredClone(state);
    actor.setMetadata('sequential', { title: '<img src=x onerror=alert(1)>', notes: '中文😀' });
    expect(state, 'DOCUMENT_ZERO_COMPUTE_DETECTED').toEqual(before);
    await actor.importFile(files.file(definition())); actor.acknowledgeReplacement(true); prepare.mockImplementation(() => { throw new Error('preparation failed'); });
    expect(actor.applyImport(), 'TRANSACTIONAL_IMPORT_DETECTED').toBe(false); expect(applied).toHaveLength(0); expect(state).toEqual(before);
    actor.setMetadata('sequential', { title: '😀'.repeat(121), notes: '' }); expect(await actor.exportCurrent()).toBe(false);
  });
  it('rechecks busy after preparation and clears restored marker after an external revision', async () => {
    const { actor, files, state, prepare, applied } = setup();
    await actor.importFile(files.file(definition())); actor.acknowledgeReplacement(true);
    prepare.mockImplementationOnce(() => { state.busy = true; return () => applied.push(validated(definition())); });
    expect(actor.applyImport(), 'TRANSACTIONAL_IMPORT_DETECTED').toBe(false); expect(applied).toHaveLength(0);
    state.busy = false; expect(actor.applyImport()).toBe(true); expect(actor.state.restored).not.toBeNull();
    state.token += ':later-edit'; actor.contextChanged(); expect(actor.state.restored).toBeNull(); expect(actor.state.status).toBe('idle');
  });
  it('rejects document allocation over unchanged global budgets without freeing science', async () => {
    const { actor, files, state } = setup(); state.retained = 16 * 1024 * 1024;
    expect(await actor.importFile(files.file(definition()))).toBe(false); expect(files.reads).toBe(0); expect(state.retained).toBe(16 * 1024 * 1024);
    actor.dispose(); expect(actor.ownershipSnapshot().urls).toBe(0);
  });
});

describe('atomic restored scientific controllers', () => {
  it('prepares all three modes without validation or science, advances eligibility and rejects busy commit', () => {
    const forbidden = vi.fn(() => { throw new Error('unexpected optical API'); }), gate = new ClientOperationGate();
    const sequential = new BenchController(presetExperiment('free'), { validate: forbidden, simulate: forbidden }, undefined, gate);
    const dual = new TwoPathController(twoPathPreset('uniform64'), { validate: forbidden, simulate: forbidden, sweep: forbidden }, undefined, gate);
    const polarization = new PolarizationController(polarizationPreset('analyzer'), { validate: forbidden, simulate: forbidden, sweep: forbidden }, undefined, gate);
    const commits = [sequential.prepareValidatedSettings(presetExperiment('aperture'), 'a'.repeat(64)),
      dual.prepareValidatedSettings(twoPathPreset('gaussian128'), 'b'.repeat(64)), polarization.prepareValidatedSettings(polarizationPreset('analyzer'), 'c'.repeat(64))];
    expect(sequential.state.revision).toBe(0); commits.forEach(commit => commit());
    for (const actor of [sequential, dual, polarization]) { expect(actor.state.revision).toBe(1); expect(actor.state.attachmentEpoch).toBe(1); expect(actor.state.currentResult).toBeNull(); }
    expect(forbidden, 'DOCUMENT_ZERO_COMPUTE_DETECTED').not.toHaveBeenCalled(); expect(polarization.retryPresentation()).toBe(false);
    const pending = sequential.prepareValidatedSettings(presetExperiment('free'), 'd'.repeat(64)); gate.acquire('other', 'two_path', 'single');
    expect(pending, 'TRANSACTIONAL_IMPORT_DETECTED').toThrow('changed'); expect(sequential.state.revision).toBe(1); expect(gate.busy).toBe(true); gate.release('other');
  });
  it('obsolete ordinary validation cannot overwrite restored canonical settings', async () => {
    const held = deferred<any>(); let submitted: any;
    const actor = new BenchController(presetExperiment('free'), { validate(envelope) { submitted = envelope; return held.promise; }, async simulate() { throw new Error('no solve'); } });
    const pending = actor.validateInitial(), restored = presetExperiment('lens'); restored.observation.z_m = .020000000000000007;
    actor.restoreValidatedSettings(restored, 'b'.repeat(64)); held.resolve({ protocol_version: 1, request_id: submitted.request_id, experiment_sha256: 'a'.repeat(64), experiment: submitted.experiment }); await pending;
    expect(actor.state.validatedDraft!.observation.z_m, 'STALE_IMPORT_GENERATION_DETECTED').toBe(.020000000000000007); expect(actor.state.revision).toBe(1);
  });
  it('failed preparation preserves exact state and old retry slots are invalidated by identical restore', () => {
    const forbidden = vi.fn(() => { throw new Error('unexpected optical API'); }), gate = new ClientOperationGate();
    const sequential = new BenchController(presetExperiment('free'), { validate: forbidden, simulate: forbidden }, undefined, gate);
    const dual = new TwoPathController(twoPathPreset('uniform64'), { validate: forbidden, simulate: forbidden, sweep: forbidden }, undefined, gate);
    const polarization = new PolarizationController(polarizationPreset('analyzer'), { validate: forbidden, simulate: forbidden, sweep: forbidden }, undefined, gate);
    const before = sequential.state;
    expect(() => sequential.prepareValidatedSettings(presetExperiment('lens'), 'bad'), 'TRANSACTIONAL_IMPORT_DETECTED').toThrow();
    expect(sequential.state, 'TRANSACTIONAL_IMPORT_DETECTED').toBe(before);
    // Identity-only fixture for retained numerical slots; this is not a computed optical result.
    for (const actor of [dual, polarization]) {
      const old = { experiment: actor.state.candidate, requestId: 'original-only' };
      (actor as unknown as { snapshot: unknown }).snapshot = Object.freeze({ ...actor.state, completedNumerical: old, lastResult: old, currentResult: old });
    }
    dual.restoreValidatedSettings(dual.state.candidate, 'b'.repeat(64)); polarization.restoreValidatedSettings(polarization.state.candidate, 'c'.repeat(64));
    expect(dual.state.completedNumerical).toBeNull(); expect(polarization.state.completedNumerical).toBeNull();
    expect(polarization.retryPresentation()).toBe(false); expect(dual.state.lastResult!.requestId).toBe('original-only'); expect(polarization.state.lastResult!.requestId).toBe('original-only');
    expect(forbidden, 'DOCUMENT_ZERO_COMPUTE_DETECTED').not.toHaveBeenCalled();
  });
});
