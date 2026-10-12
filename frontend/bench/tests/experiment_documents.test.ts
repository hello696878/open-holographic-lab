import { describe, expect, it } from 'vitest';
import { assertDocumentCorrespondence, browserDocumentBytes, createDocumentFetchAPI, makeExperimentDocument,
  ownExperimentDocument, unicodeScalarCount, validateDocumentMetadata, type BenchMode } from '../src/experiment_documents';
import { presetExperiment } from '../src/presets';
import { twoPathPreset } from '../src/two_path_presets';
import { polarizationPreset } from '../src/polarization_presets';
const sources = { sequential: () => presetExperiment('aperture'), two_path: () => twoPathPreset('gaussian128'), polarization: () => polarizationPreset('analyzer') };
const metadata = { title: '中文 𝄞 e\u0301 <b>文字</b>', notes: '保留空白 \n\t文字' };
const doc = (mode: BenchMode = 'sequential') => makeExperimentDocument(mode, sources[mode](), metadata);
function bytes(value: unknown) { return new TextEncoder().encode(JSON.stringify(value, null, 2) + '\n'); }
function response(value: unknown, headers: Record<string, string> = {}) { return new Response(bytes(value), { headers: {
  'Content-Type': 'application/json', 'X-OHLab-Experiment-SHA256': 'a'.repeat(64), ...headers } }); }

describe('closed portable experiment document contract', () => {
  it.each(['sequential', 'two_path', 'polarization'] as BenchMode[])('owns %s settings without results or transport tokens', mode => {
    const original = doc(mode), owned = ownExperimentDocument(original);
    expect(owned, 'DOCUMENT_MODE_CONTRACT_DETECTED').toEqual(original);
    expect(Object.keys(owned)).toHaveLength(6); expect(Object.isFrozen(owned.experiment.grid)).toBe(true);
    const copy = structuredClone(original); (copy.metadata as { title: string }).title = 'changed';
    expect(owned.metadata.title).toBe(metadata.title);
  });
  it('rejects imported success fields and wrong mode model versions', () => {
    const original = doc();
    for (const value of [{ ...original, status: 'complete' }, { ...original, result: [] }, { ...original, request_id: 'fake' },
      { ...original, mode: 'future' }, { ...original, document_version: 2 }, { ...original, model_contract: 'future' },
      { ...original, mode: 'two_path' }, { ...original, metadata: { title: '' } }]) {
      expect(() => ownExperimentDocument(value), 'IMPORTED_SUCCESS_STATE_DETECTED').toThrow();
    }
  });
  it('retains nonzero binary64 bits order IDs readout and arbitrary coefficients', () => {
    const sequential = presetExperiment('aperture'); sequential.wavelength_m = 6.330000000000001e-7;
    sequential.observation.z_m = .020000000000000004;
    if (sequential.components[1].kind === 'thin_lens') sequential.components[1].focal_length_m = -.012345678901234568;
    const polarization = polarizationPreset('analyzer'); polarization.elements[0].axis_angle_rad = Math.PI / 2 + 2e-15;
    polarization.source.phase_rad = 31.123456789012344; polarization.coefficients = { x: { re: 2.3, im: -7.1 }, y: { re: Number.MIN_VALUE, im: .12345678901234568 } };
    polarization.readout = { row: 3, column: 5 }; polarization.grid = { ny: 5, nx: 8, dy: 3.0000000000000005e-6, dx: 2.0000000000000003e-6 };
    for (const original of [makeExperimentDocument('sequential', sequential, metadata), makeExperimentDocument('polarization', polarization, metadata)]) {
      const restored = JSON.parse(new TextDecoder().decode(browserDocumentBytes(original)));
      expect(() => assertDocumentCorrespondence(original, restored), 'DOCUMENT_NUMERIC_BITS_DETECTED').not.toThrow();
    }
    const changed = structuredClone(makeExperimentDocument('polarization', polarization, metadata));
    if (changed.mode === 'polarization') changed.experiment.coefficients.x.re = 1;
    expect(() => assertDocumentCorrespondence(makeExperimentDocument('polarization', polarization, metadata), changed), 'DOCUMENT_COEFFICIENT_BITS_DETECTED').toThrow();
    const reordered = structuredClone(doc('sequential')); if (reordered.mode === 'sequential') reordered.experiment.components.reverse();
    expect(() => assertDocumentCorrespondence(doc('sequential'), reordered), 'DOCUMENT_ORDER_IDS_DETECTED').toThrow();
  });
  it('allows zero representation only and rejects legal adjacent nonzero drift', () => {
    expect(() => assertDocumentCorrespondence({ value: -0 }, { value: 0 })).not.toThrow();
    expect(() => assertDocumentCorrespondence({ value: .020000000000000004 }, { value: .02 }), 'TWO_STAGE_NONZERO_DRIFT_DETECTED').toThrow('numeric drift');
    expect(() => assertDocumentCorrespondence({ value: Number.MIN_VALUE }, { value: 0 }), 'DOCUMENT_NUMERIC_BITS_DETECTED').toThrow();
  });
  it('follows current signed zero policies without snapping or wrapping nonzero phases', () => {
    const sequential = presetExperiment('free'); if (sequential.source.kind === 'gaussian') sequential.source.center_x_m = -0;
    const dual = twoPathPreset('uniform64'); dual.source.phase_rad = -0; dual.two_arm_spec.relative_phase_rad = -31.123456789012344;
    const polarization = polarizationPreset('analyzer'); polarization.coefficients.y.im = -0;
    for (const original of [makeExperimentDocument('sequential', sequential, metadata), makeExperimentDocument('two_path', dual, metadata), makeExperimentDocument('polarization', polarization, metadata)]) {
      const final = ownExperimentDocument(JSON.parse(new TextDecoder().decode(browserDocumentBytes(original))));
      expect(() => assertDocumentCorrespondence(original, final)).not.toThrow();
      expect(new TextDecoder().decode(browserDocumentBytes(final))).not.toContain('-0,');
    }
  });
  it('uses Unicode scalars while preserving Chinese supplementary combining and allowed whitespace', () => {
    expect(unicodeScalarCount('中😀e\u0301'), 'UNICODE_SCALAR_POLICY_DETECTED').toBe(4);
    expect(validateDocumentMetadata({ title: '😀'.repeat(120), notes: '中'.repeat(1998) + '\t\n' }).title, 'UNICODE_SCALAR_POLICY_DETECTED').toHaveLength(240);
    expect(validateDocumentMetadata(metadata)).toEqual(metadata);
    for (const value of [{ title: '😀'.repeat(121), notes: '' }, { title: '', notes: '😀'.repeat(2001) },
      { title: '\ud800', notes: '' }, { title: 'x\n', notes: '' }, { title: '', notes: '\r' }, { title: '', notes: '\u0085' }]) {
      expect(() => validateDocumentMetadata(value), 'UNICODE_SCALAR_POLICY_DETECTED').toThrow();
    }
  });
  it('sends untouched raw bytes and separates ephemeral scientific header from file identity', async () => {
    const raw = new TextEncoder().encode('{"mode":"sequential","mode":"polarization"}'); const calls: Uint8Array[] = [];
    const api = createDocumentFetchAPI(async (_url, init) => { calls.push(new Uint8Array(init!.body as ArrayBuffer)); return response(doc()); });
    const result = await api.validate(raw);
    expect(calls[0], 'RAW_DUPLICATE_KEYS_DETECTED').toEqual(raw);
    expect(result.experimentSha256, 'DOCUMENT_DIGEST_SEPARATION_DETECTED').toBe('a'.repeat(64));
    expect(new TextDecoder().decode(result.bytes), 'DOCUMENT_DIGEST_SEPARATION_DETECTED').not.toContain('experiment_sha256');
  });
  it('rejects malformed response bytes duplicate keys MIME and missing digest', async () => {
    for (const reply of [new Response('{"x":1,"x":2}', { headers: { 'Content-Type': 'application/json', 'X-OHLab-Experiment-SHA256': 'a'.repeat(64) } }),
      response(doc(), { 'X-OHLab-Experiment-SHA256': '' }), response(doc(), { 'Content-Type': 'text/html' }),
      new Response(new Uint8Array([0xff]), { headers: { 'Content-Type': 'application/json', 'X-OHLab-Experiment-SHA256': 'a'.repeat(64) } })]) {
      await expect(createDocumentFetchAPI(async () => reply).validate(bytes(doc()))).rejects.toThrow();
    }
  });
});
