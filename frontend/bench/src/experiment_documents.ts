/** V2e settings boundary. No optical calculations or persistent request identity. */
import { assertExperiment, freezeExperiment, parseStrictJSON, readBoundedResponse, type Experiment } from './contracts';
import { assertTwoPathExperiment, freezeTwoPathExperiment, type TwoPathExperiment } from './two_path_contracts';
import { assertPolarizationExperiment, freezePolarizationExperiment, type PolarizationExperiment } from './polarization_contracts';
import { assertPolarizedTwoPathExperiment, freezePolarizedTwoPathExperiment, type PolarizedTwoPathExperiment } from './polarized_two_path_contracts';

export const MAX_DOCUMENT_BYTES = 32768;
export const DOCUMENT_FORMAT = 'ohlab_virtual_experiment';
export const DOCUMENT_MODELS = Object.freeze({ sequential: 'v0_aligned_scalar_forward_v1',
  two_path: 'v2b_unfolded_scalar_two_path_v1', polarization: 'v2d_ideal_jones_same_plane_v1' } as const);
export type BenchMode = keyof typeof DOCUMENT_MODELS;
export type SupportedBenchMode = BenchMode | 'polarized_two_path';
export const POLARIZED_TWO_PATH_DOCUMENT_MODEL = 'v2g_ideal_polarized_two_path_v1';
export interface DocumentMetadata { readonly title: string; readonly notes: string }
type DocumentFor<M extends BenchMode, E> = Readonly<{ document_format: typeof DOCUMENT_FORMAT; document_version: 1;
  mode: M; model_contract: typeof DOCUMENT_MODELS[M]; experiment: E; metadata: DocumentMetadata }>;
export type ExperimentDocument = DocumentFor<'sequential', Experiment> | DocumentFor<'two_path', TwoPathExperiment>
  | DocumentFor<'polarization', PolarizationExperiment>;
export type PolarizedTwoPathDocument = Readonly<{ document_format: typeof DOCUMENT_FORMAT; document_version: 2;
  mode: 'polarized_two_path'; model_contract: typeof POLARIZED_TWO_PATH_DOCUMENT_MODEL; experiment: PolarizedTwoPathExperiment; metadata: DocumentMetadata }>;
export type SupportedExperimentDocument = ExperimentDocument | PolarizedTwoPathDocument;
export type DocumentByMode<M extends SupportedBenchMode> = Extract<SupportedExperimentDocument, { mode: M }>;
export type ScientificExperiment = Experiment | TwoPathExperiment | PolarizationExperiment | PolarizedTwoPathExperiment;
export interface ValidatedDocument<M extends SupportedBenchMode = BenchMode> { readonly document: DocumentByMode<M>; readonly bytes: Uint8Array;
  /** Existing mode-specific scientific digest; not file-byte identity or provenance. */
  readonly experimentSha256: string }
export type SupportedValidatedDocument = ValidatedDocument<SupportedBenchMode>;
export interface DocumentAPI<M extends SupportedBenchMode = BenchMode> { validate(bytes: Uint8Array, signal?: AbortSignal): Promise<ValidatedDocument<M>> }
export type SupportedDocumentAPI = DocumentAPI<SupportedBenchMode>;
function fail(message: string): never { throw new Error(`V2e document: ${message}`); }
function record(value: unknown, name: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(`${name}: expected object`);
  return value as Record<string, unknown>;
}
function exactKeys(value: Record<string, unknown>, expected: readonly string[], name: string): void {
  if (Object.keys(value).length !== expected.length || Object.keys(value).some(key => !expected.includes(key))) fail(`${name}: incorrect keys`);
}
/** Count Unicode scalars, rejecting lone UTF-16 surrogates before counting. */
export function unicodeScalarCount(text: string): number {
  let count = 0;
  for (const character of text) {
    const code = character.codePointAt(0)!;
    if (code >= 0xd800 && code <= 0xdfff) fail('lone Unicode surrogate');
    count += 1;
  }
  return count;
}
export function validateDocumentMetadata(value: unknown): DocumentMetadata {
  const metadata = record(value, 'metadata'); exactKeys(metadata, ['title', 'notes'], 'metadata');
  for (const [key, maximum] of [['title', 120], ['notes', 2000]] as const) {
    const text = metadata[key];
    if (typeof text !== 'string' || unicodeScalarCount(text) > maximum) fail(`${key}: Unicode scalar limit ${maximum}`);
    for (const character of text) {
      const code = character.codePointAt(0)!;
      if ((code <= 0x1f || code >= 0x7f && code <= 0x9f) && !(key === 'notes' && [9, 10].includes(code))) fail(`${key}: forbidden control character`);
    }
  }
  return Object.freeze({ title: metadata.title as string, notes: metadata.notes as string });
}
function structuralLimits(value: unknown): void {
  let nodes = 0; const pending: { value: unknown; depth: number }[] = [{ value, depth: 0 }];
  while (pending.length) {
    const item = pending.pop()!; if (++nodes > 2048) fail('value node limit');
    if (typeof item.value === 'string' && unicodeScalarCount(item.value) > 8192) fail('string token limit');
    if (typeof item.value === 'number' && !Number.isFinite(item.value)) fail('nonfinite number');
    if (item.value && typeof item.value === 'object') {
      if (item.depth > 12) fail('container depth limit');
      for (const [key, child] of Object.entries(item.value)) {
        if (unicodeScalarCount(key) > 8192) fail('key token limit');
        pending.push({ value: child, depth: item.depth + 1 });
      }
    }
  }
}
function freezeOwned<T>(value: T): T {
  if (value && typeof value === 'object') { Object.values(value).forEach(freezeOwned); Object.freeze(value); }
  return value;
}
/** Build owned closed records, preserving first-reply numbers before browser preparation. */
export function ownExperimentDocument(value: unknown): ExperimentDocument {
  const owned = ownSupportedExperimentDocument(value);
  if (owned.document_version !== 1) fail('unsupported document format/version'); return owned;
}
/** Explicit v2 branch; the legacy mode map and v1 helper stay closed. */
export function ownSupportedExperimentDocument(value: unknown): SupportedExperimentDocument {
  structuralLimits(value); const data = record(value, 'document');
  exactKeys(data, ['document_format', 'document_version', 'mode', 'model_contract', 'experiment', 'metadata'], 'document');
  if (data.document_format !== DOCUMENT_FORMAT) fail('unsupported document format/version');
  if (data.document_version === 2) {
    if (data.mode !== 'polarized_two_path') fail('unsupported document format/version for mode');
    if (data.model_contract !== POLARIZED_TWO_PATH_DOCUMENT_MODEL) fail('unsupported model contract');
    assertPolarizedTwoPathExperiment(data.experiment); const metadata = validateDocumentMetadata(data.metadata);
    return freezeOwned({ document_format: DOCUMENT_FORMAT, document_version: 2, mode: 'polarized_two_path',
      model_contract: POLARIZED_TWO_PATH_DOCUMENT_MODEL, experiment: structuredClone(data.experiment), metadata });
  }
  if (data.document_version !== 1) fail('unsupported document format/version');
  if (typeof data.mode !== 'string' || !Object.hasOwn(DOCUMENT_MODELS, data.mode)) fail('unsupported document mode');
  const mode = data.mode as BenchMode;
  if (data.model_contract !== DOCUMENT_MODELS[mode]) fail('unsupported model contract');
  if (mode === 'sequential') assertExperiment(data.experiment);
  else if (mode === 'two_path') assertTwoPathExperiment(data.experiment);
  else assertPolarizationExperiment(data.experiment);
  const metadata = validateDocumentMetadata(data.metadata);
  return freezeOwned({ document_format: DOCUMENT_FORMAT, document_version: 1, mode,
    model_contract: DOCUMENT_MODELS[mode], experiment: structuredClone(data.experiment), metadata }) as ExperimentDocument;
}
export function makeExperimentDocument<M extends SupportedBenchMode>(mode: M, experiment: ScientificExperiment, metadata: DocumentMetadata): DocumentByMode<M> {
  return ownSupportedExperimentDocument({ document_format: DOCUMENT_FORMAT, document_version: mode === 'polarized_two_path' ? 2 : 1, mode,
    model_contract: mode === 'polarized_two_path' ? POLARIZED_TWO_PATH_DOCUMENT_MODEL : DOCUMENT_MODELS[mode as BenchMode], experiment, metadata }) as DocumentByMode<M>;
}
/** Exact finite-number correspondence; only the existing zero representation may differ. */
export function assertDocumentCorrespondence(expected: unknown, actual: unknown, path = 'document'): void {
  if (typeof expected === 'number' || typeof actual === 'number') {
    if (typeof expected !== 'number' || typeof actual !== 'number' || !Number.isFinite(expected) || !Number.isFinite(actual)
      || !(Object.is(expected, actual) || expected === 0 && actual === 0)) fail(`${path}: scientific numeric drift`);
    return;
  }
  if (expected === null || actual === null || typeof expected !== 'object' || typeof actual !== 'object') {
    if (expected !== actual) fail(`${path}: value drift`); return;
  }
  if (Array.isArray(expected) || Array.isArray(actual)) {
    if (!Array.isArray(expected) || !Array.isArray(actual) || expected.length !== actual.length) fail(`${path}: ordered array drift`);
    expected.forEach((value, index) => assertDocumentCorrespondence(value, actual[index], `${path}[${index}]`)); return;
  }
  const left = expected as Record<string, unknown>, right = actual as Record<string, unknown>;
  exactKeys(right, Object.keys(left), path);
  for (const key of Object.keys(left)) assertDocumentCorrespondence(left[key], right[key], `${path}.${key}`);
}
/** Ordinary mode freezer and JSON semantics; never shorten or unit-convert values. */
export function browserDocumentBytes(document: ExperimentDocument): Uint8Array {
  return browserSupportedDocumentBytes(document);
}
export function browserSupportedDocumentBytes(document: SupportedExperimentDocument): Uint8Array {
  const experiment = document.mode === 'sequential' ? freezeExperiment(document.experiment)
    : document.mode === 'two_path' ? freezeTwoPathExperiment(document.experiment)
    : document.mode === 'polarization' ? freezePolarizationExperiment(document.experiment) : freezePolarizedTwoPathExperiment(document.experiment);
  const owned = makeExperimentDocument(document.mode, experiment, document.metadata);
  const bytes = new TextEncoder().encode(JSON.stringify(owned));
  if (bytes.byteLength > MAX_DOCUMENT_BYTES) fail('request byte cap');
  const serialized = ownSupportedExperimentDocument(parseStrictJSON(new TextDecoder('utf-8', { fatal: true }).decode(bytes)));
  assertDocumentCorrespondence(document, serialized);
  return bytes;
}
export function createDocumentFetchAPI(fetchImpl: typeof fetch = globalThis.fetch.bind(globalThis)): DocumentAPI {
  const supported = createSupportedDocumentFetchAPI(fetchImpl);
  return { async validate(bytes, signal) { const result = await supported.validate(bytes, signal); if (result.document.document_version !== 1) fail('unsupported document format/version');
    return { ...result, document: result.document }; } };
}
export function createSupportedDocumentFetchAPI(fetchImpl: typeof fetch = globalThis.fetch.bind(globalThis)): SupportedDocumentAPI {
  return { async validate(bytes, signal) {
    if (!(bytes instanceof Uint8Array) || bytes.byteLength < 2 || bytes.byteLength > MAX_DOCUMENT_BYTES) fail('request byte cap');
    const response = await fetchImpl('/api/v2e/documents/validate', { method: 'POST', credentials: 'same-origin', redirect: 'error',
      cache: 'no-store', signal, headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: new Uint8Array(bytes).buffer });
    const type = response.headers.get('content-type')?.split(';', 1)[0].trim();
    if (!response.ok) {
      const raw = await readBoundedResponse(response, MAX_DOCUMENT_BYTES); let message = `HTTP ${response.status}`;
      if (type === 'application/json') { try { const parsed = record(parseStrictJSON(new TextDecoder('utf-8', { fatal: true }).decode(raw)), 'error');
        const error = record(parsed.error, 'error detail'); if (typeof error.message === 'string') message += `: ${error.message.slice(0, 300)}`;
      } catch { /* Preserve actual HTTP status for malformed error replies. */ } }
      throw new Error(message);
    }
    if (type !== 'application/json') { await response.body?.cancel('V2e MIME'); fail('response content-type'); }
    const digest = response.headers.get('X-OHLab-Experiment-SHA256');
    if (!digest || !/^[0-9a-f]{64}$/.test(digest)) { await response.body?.cancel('V2e digest'); fail('scientific digest header'); }
    const raw = new Uint8Array(await readBoundedResponse(response, MAX_DOCUMENT_BYTES));
    const text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(raw);
    const document = ownSupportedExperimentDocument(parseStrictJSON(text));
    return Object.freeze({ document, bytes: raw, experimentSha256: digest });
  } };
}
