import { describe, expect, it, vi } from 'vitest';
import { assertDocumentCorrespondence, browserDocumentBytes, browserSupportedDocumentBytes, DOCUMENT_MODELS,
  makeExperimentDocument, ownExperimentDocument, ownSupportedExperimentDocument,
  type SupportedBenchMode, type SupportedDocumentAPI, type SupportedExperimentDocument, type SupportedValidatedDocument } from '../src/experiment_documents';
import { ExperimentDocumentController } from '../src/experiment_document_state';
import { ExperimentDocumentFiles, type DocumentFiles, type PreparedDownload } from '../src/experiment_document_files';
import { PolarizedTwoPathController } from '../src/polarized_two_path_state';
import { polarizedTwoPathPreset } from '../src/polarized_two_path_presets';
import { parseStrictJSON } from '../src/contracts';
const metadata = { title: '中文 😀 e\u0301', notes: '  literal\n\tsettings  ' }, digest = 'a'.repeat(64);
function definition(enabled = false): SupportedExperimentDocument {
  const experiment = polarizedTwoPathPreset('orthogonal_analyzed'); experiment.source = { kind: 'gaussian', amplitude: 2.3, phase_rad: -31.123456789012344,
    waist_radius_m: 40e-6, waist_z_m: -.0012345678901234567, center_x_m: 12e-6, center_y_m: -8e-6 };
  experiment.coefficients = { x: { re: 2.3, im: -7.1 }, y: { re: Number.MIN_VALUE, im: .12345678901234568 } };
  experiment.arm_0.actions = [{ id: 'loss1', kind: 'linear_polarizer', axis_angle_rad: -.12345678901234568 },
    { id: 'wave0', kind: 'linear_retarder', axis_angle_rad: 17.123456789012345, retardance_rad: -Math.PI / 2 }];
  experiment.arm_1.actions[0].id = 'other_wave'; experiment.relative_phase_rad = -23.123456789012344;
  experiment.analyzer = { enabled, axis_angle_rad: -.9876543210987654 };
  return makeExperimentDocument('polarized_two_path', experiment, metadata);
}
const encode = (value: unknown) => new TextEncoder().encode(JSON.stringify(value, null, 2) + '\n');
class Files implements DocumentFiles {
  inputs = new Map<File, Uint8Array>(); prepared: PreparedDownload | null = null; releases = 0;
  async read(file: File, signal: AbortSignal) { if (signal.aborted) throw new Error('aborted'); return this.inputs.get(file)!; }
  prepareDownload(bytes: Uint8Array, filename: string) { this.dismissDownload(); return this.prepared = { bytes, filename, blob: new Blob([new Uint8Array(bytes).buffer]), url: `blob:prepared-${this.releases}` }; }
  dismissDownload() { if (this.prepared) this.releases++; this.prepared = null; }
  ownershipSnapshot() { return { activeReaders: 0, readerReservedBytes: 0, urls: this.prepared ? 1 : 0, blobBytes: this.prepared?.blob.size ?? 0 }; }
  dispose() { this.dismissDownload(); }
  file(value: unknown, name = 'settings.json') { const bytes = encode(value), file = new File([new Uint8Array(bytes).buffer], name); this.inputs.set(file, bytes); return file; }
}
function setup() {
  const document = definition(), science = new PolarizedTwoPathController(document.mode === 'polarized_two_path' ? document.experiment : polarizedTwoPathPreset('identical'));
  science.restoreValidatedSettings(science.state.candidate, digest); const files = new Files(), calls: Uint8Array[] = [], applies: SupportedValidatedDocument[] = [];
  const api: SupportedDocumentAPI = { async validate(bytes) { calls.push(bytes.slice()); const document = ownSupportedExperimentDocument(parseStrictJSON(new TextDecoder().decode(bytes)));
    return { document, bytes: encode(document), experimentSha256: digest }; } };
  const actor = new ExperimentDocumentController<SupportedBenchMode>({ context: () => ({ mode: 'polarized_two_path', token: `${science.state.revision}:${science.state.attachmentEpoch}` }),
    currentValidDraft: () => science.state.validatedDraft ? { mode: 'polarized_two_path', experiment: science.state.validatedDraft, revision: science.state.revision, attachmentEpoch: science.state.attachmentEpoch } : null,
    busy: () => science.gate.busy, prepareApply(value) { if (value.document.mode !== 'polarized_two_path') throw new Error('test destination');
      const commit = science.prepareValidatedSettings(value.document.experiment, value.experimentSha256); return () => { commit(); applies.push(value); }; }, api, files });
  science.subscribe(() => actor.contextChanged()); actor.setMetadata('polarized_two_path', metadata); return { actor, science, files, calls, applies };
}
describe('explicit version-2 portable settings with unchanged closed version 1', () => {
  it('real download ownership accepts the new filename and all three legacy names with exact Blob bytes and URL lifetimes', async () => {
    const active = new Map<string, Blob>(), revoked: string[] = [], blobs: Blob[] = []; let next = 0;
    const files = new ExperimentDocumentFiles({
      urlAPI: { createObjectURL(blob) { if (!(blob instanceof Blob)) throw new Error('Expected owned document Blob'); const url = `blob:real-files-${++next}`; active.set(url, blob); return url; },
        revokeObjectURL(url) { revoked.push(url); active.delete(url); } },
      blobFactory(bytes) { const blob = new Blob([new Uint8Array(bytes).buffer], { type: 'application/json;charset=utf-8' }); blobs.push(blob); return blob; },
    });
    const bytes = browserSupportedDocumentBytes(definition(false)); let previous: PreparedDownload | null = null;
    for (const mode of ['polarized_two_path', 'sequential', 'two_path', 'polarization']) {
      let prepared!: PreparedDownload;
      expect(() => { prepared = files.prepareDownload(bytes, `${mode}-settings.json`); }, 'PT_REAL_DOWNLOAD_FILENAME').not.toThrow();
      expect(prepared.filename).toBe(`${mode}-settings.json`); expect(prepared.bytes).toBe(bytes);
      expect(new Uint8Array(await prepared.blob.arrayBuffer()), 'PT_REAL_DOWNLOAD_BYTES').toEqual(bytes);
      expect(prepared.blob.type).toBe('application/json;charset=utf-8'); expect(active.get(prepared.url)).toBe(prepared.blob);
      expect(files.ownershipSnapshot(), 'PT_REAL_DOWNLOAD_LIFETIME').toEqual({ activeReaders: 0, readerReservedBytes: 0, urls: 1, blobBytes: bytes.byteLength });
      if (previous) { expect(active.has(previous.url)).toBe(false); expect(revoked.filter(url => url === previous!.url)).toHaveLength(1); }
      previous = prepared;
    }
    expect(blobs).toHaveLength(4); expect(revoked).toHaveLength(3); files.dismissDownload(); files.dismissDownload();
    expect(active.size, 'PT_REAL_DOWNLOAD_LIFETIME').toBe(0); expect(revoked).toHaveLength(4); expect(files.ownershipSnapshot().blobBytes).toBe(0);
    files.dispose(); expect(() => files.prepareDownload(bytes, 'polarized_two_path-settings.json')).toThrow('disposed');
  });
  it('real download guard rejects unknown or unsafe names before allocation and preserves its useful existing URL', () => {
    const create = vi.fn(() => 'blob:preserved-document'), revoke = vi.fn(), blob = vi.fn((bytes: Uint8Array) => new Blob([new Uint8Array(bytes).buffer]));
    const files = new ExperimentDocumentFiles({ urlAPI: { createObjectURL: create, revokeObjectURL: revoke }, blobFactory: blob });
    const bytes = browserSupportedDocumentBytes(definition()), prepared = files.prepareDownload(bytes, 'polarized_two_path-settings.json');
    for (const filename of ['', 'future-settings.json', '../polarized_two_path-settings.json', 'C:\\polarized_two_path-settings.json',
      'polarized_two_path-settings.json.exe', 'polarized_two_path-settings.JSON', 'polarized_two_path-settings.json\n', 'polarized_two_path/settings.json']) {
      expect(() => files.prepareDownload(bytes, filename), 'PT_REAL_DOWNLOAD_NAME_GUARD').toThrow('filename');
    }
    for (const invalid of [new Uint8Array(1), new Uint8Array(32769)]) expect(() => files.prepareDownload(invalid, 'polarized_two_path-settings.json')).toThrow('cap');
    expect(create, 'PT_REAL_DOWNLOAD_NAME_GUARD').toHaveBeenCalledOnce(); expect(blob).toHaveBeenCalledOnce(); expect(revoke).not.toHaveBeenCalled();
    expect(files.ownershipSnapshot().urls).toBe(1); expect(prepared.url).toBe('blob:preserved-document'); files.dispose(); expect(revoke).toHaveBeenCalledExactlyOnceWith(prepared.url);
  });
  it.each([false, true])('retains every exact setting with analyzer enabled=%s', enabled => {
    const original = definition(enabled), restored = ownSupportedExperimentDocument(parseStrictJSON(new TextDecoder().decode(browserSupportedDocumentBytes(original))));
    expect(restored.document_version).toBe(2); expect(Object.keys(restored)).toHaveLength(6);
    expect(() => assertDocumentCorrespondence(original, restored), 'PT_DOCUMENT_COMPLETE_SETTINGS').not.toThrow();
    if (restored.mode !== 'polarized_two_path') throw new Error('mode');
    expect(restored.experiment.analyzer.axis_angle_rad, 'PT_DISABLED_DOCUMENT_ANGLE').toBe(-.9876543210987654);
    expect(restored.experiment.coefficients.y.re).toBe(Number.MIN_VALUE); expect(restored.experiment.arm_0.actions.map(a => a.id)).toEqual(['loss1', 'wave0']);
    expect(browserSupportedDocumentBytes(restored)).toEqual(browserSupportedDocumentBytes(original));
    expect(() => ownExperimentDocument(original)).toThrow('version'); expect(Object.keys(DOCUMENT_MODELS)).toEqual(['sequential', 'two_path', 'polarization']);
  });
  it('rejects every unsupported version/mode/model/schema combination instead of migrating', () => {
    const original = definition();
    for (const mode of ['sequential', 'two_path', 'polarization']) expect(() => ownSupportedExperimentDocument({ ...original, mode }), 'PT_DOCUMENT_VERSION_MATRIX').toThrow();
    for (const change of [{ document_version: 1 }, { document_version: 3 }, { document_version: true }, { document_version: 2.1 },
      { model_contract: 'v2d_ideal_jones_same_plane_v1' }, { mode: 'future' }, { result: [] }, { request_id: 'saved' }]) expect(() => ownSupportedExperimentDocument({ ...original, ...change }), 'PT_DOCUMENT_VERSION_MATRIX').toThrow();
    const broken = structuredClone(original); if (broken.mode === 'polarized_two_path') (broken.experiment as any).schema_version = 2;
    expect(() => ownSupportedExperimentDocument(broken)).toThrow();
  });
  it('preserves a literal preexisting-style v1 browser byte fixture without extending its mode map', () => {
    const bytes = '{"document_format":"ohlab_virtual_experiment","document_version":1,"mode":"sequential","model_contract":"v0_aligned_scalar_forward_v1","experiment":{"schema_version":1,"model_contract":"v0_aligned_scalar_forward_v1","wavelength_m":6.33e-7,"grid":{"ny":1,"nx":1,"dy":0.000004,"dx":0.000004},"source":{"kind":"uniform","amplitude":1,"phase_rad":0},"components":[],"observation":{"id":"detector","z_m":0}},"metadata":{"title":"legacy","notes":"stay"}}';
    const old = ownExperimentDocument(parseStrictJSON(bytes)); expect(new TextDecoder().decode(browserDocumentBytes(old)), 'PT_LEGACY_V1_BYTES').toBe(bytes);
    expect(() => ownSupportedExperimentDocument({ ...old, document_version: 2 }), 'PT_LEGACY_V1_BYTES').toThrow();
  });
  it('detects dropped inactive analyzer settings and reordered IDs or adjacent nonzero drift', () => {
    const original = definition(), changed = structuredClone(original); if (changed.mode !== 'polarized_two_path') throw new Error('mode');
    changed.experiment.analyzer.axis_angle_rad = Math.PI / 4;
    expect(() => assertDocumentCorrespondence(original, changed), 'PT_DISABLED_DOCUMENT_ANGLE').toThrow('drift');
    const reordered = structuredClone(original); if (reordered.mode === 'polarized_two_path') reordered.experiment.arm_0.actions.reverse(); expect(() => assertDocumentCorrespondence(original, reordered)).toThrow('actions[0]');
    const erased = structuredClone(original); if (erased.mode === 'polarized_two_path') erased.experiment.coefficients.y.re = 0; expect(() => assertDocumentCorrespondence(original, erased)).toThrow('numeric drift');
  });
  it('imports via two authoritative stages, applies transactionally and leaves optics unsimulated', async () => {
    const { actor, science, files, calls, applies } = setup();
    expect(await actor.importFile(files.file(definition()))).toBe(true); expect(calls).toHaveLength(2); expect(actor.state.preview?.document.document_version).toBe(2);
    expect(actor.applyImport()).toBe(false); actor.acknowledgeReplacement(true); expect(actor.applyImport()).toBe(true);
    expect(applies).toHaveLength(1); expect(actor.state.status).toBe('restored'); expect(science.state.currentResult).toBeNull(); expect(science.state.active).toBeNull();
    expect(science.state.candidate.analyzer, 'PT_DISABLED_DOCUMENT_ANGLE').toEqual({ enabled: false, axis_angle_rad: -.9876543210987654 });
    const validate = vi.fn(async (sent: any) => ({ protocol_version: 1, message_type: 'polarized_two_path_validation', request_id: sent.request_id, experiment_sha256: digest, experiment: sent.experiment }));
    (science as any).api.validate = validate; await science.setAnalyzerEnabled(true);
    expect(science.state.candidate.analyzer.axis_angle_rad, 'PT_DISABLED_DOCUMENT_ANGLE').toBe(-.9876543210987654); expect(validate).toHaveBeenCalledOnce();
  });
  it('release preserves document preview, metadata, useful Blob URL and later download/import without revalidation', async () => {
    const { actor, science, files, calls } = setup(); expect(await actor.exportCurrent()).toBe(true);
    const download = actor.state.preparedDownload; expect(download).not.toBeNull(); expect(await actor.importFile(files.file(definition()))).toBe(true);
    const preview = actor.state.preview, metadataBefore = actor.state.metadata, count = calls.length, owned = actor.ownershipSnapshot();
    expect(science.releaseResults()).toBe(true); actor.contextChanged();
    expect(actor.state.preview, 'PT_RELEASE_DOCUMENT_PRESERVATION').toBe(preview); expect(actor.state.preparedDownload, 'PT_RELEASE_DOCUMENT_PRESERVATION').toBe(download);
    expect(actor.state.metadata).toBe(metadataBefore); expect(files.prepared?.url, 'PT_RELEASE_DOCUMENT_PRESERVATION').toBe(download!.url);
    expect(calls, 'PT_RELEASE_DOCUMENT_ZERO_REVALIDATION').toHaveLength(count); expect(actor.ownershipSnapshot()).toEqual(owned);
    actor.markDownloadRequested(); expect(actor.state.preparedDownload?.requested).toBe(true); expect(files.releases).toBe(0);
    const moved = new File([new Uint8Array(download!.bytes).buffer], 'moved-renamed-v2.json'); files.inputs.set(moved, download!.bytes);
    expect(await actor.importFile(moved)).toBe(true); expect(calls).toHaveLength(count + 2); expect(() => assertDocumentCorrespondence(download!.document, actor.state.preview!.document)).not.toThrow();
  });
  it('rechecks numerical busy state at Apply without releasing or acquiring its gate', async () => {
    const { actor, science, files, applies } = setup(); await actor.importFile(files.file(definition())); actor.acknowledgeReplacement(true);
    science.gate.acquire('held', 'sequential', 'single'); expect(actor.applyImport()).toBe(false); expect(applies).toHaveLength(0); expect(science.gate.busy).toBe(true);
    science.gate.release('held'); expect(actor.applyImport()).toBe(true); expect(science.gate.busy).toBe(false);
  });
});
