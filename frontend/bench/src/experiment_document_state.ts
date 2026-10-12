/** Explicit, generation-bound settings operations, independent of scientific workers. */
import { assertDocumentCorrespondence, browserDocumentBytes, createDocumentFetchAPI, makeExperimentDocument,
  ownExperimentDocument, validateDocumentMetadata, MAX_DOCUMENT_BYTES, type BenchMode, type DocumentAPI,
  type DocumentMetadata, type ExperimentDocument, type ScientificExperiment, type ValidatedDocument } from './experiment_documents';
import { ExperimentDocumentFiles, type DocumentFiles, type PreparedDownload } from './experiment_document_files';
import { assertOwnedBudgets } from './polarization_display';
import { parseStrictJSON } from './contracts';

export interface DocumentContext { readonly mode: BenchMode; readonly token: string }
export interface ValidDraft { readonly mode: BenchMode; readonly experiment: ScientificExperiment;
  readonly revision: number; readonly attachmentEpoch: number }
export interface ImportPreview extends ValidatedDocument { readonly generation: number; readonly contextToken: string }
export interface DownloadState extends PreparedDownload { readonly document: ExperimentDocument; readonly revision: number;
  readonly requested: boolean }
export interface DocumentState {
  readonly metadata: Readonly<Record<BenchMode, DocumentMetadata>>;
  readonly metadataErrors: Readonly<Partial<Record<BenchMode, string>>>;
  readonly pending: boolean; readonly operation: 'import' | 'export' | null;
  readonly status: 'idle' | 'reading' | 'validating' | 'preview' | 'download_prepared' | 'download_requested' | 'restored' | 'error';
  readonly error: string | null; readonly preview: ImportPreview | null;
  readonly acknowledged: boolean; readonly preparedDownload: DownloadState | null;
  readonly restored: Readonly<{ mode: BenchMode; generation: number }> | null;
}
export interface DocumentControllerOptions {
  context(): DocumentContext;
  currentValidDraft(): ValidDraft | null;
  busy(): boolean;
  /** Preparation must not mutate; returned synchronous commit must not render or throw after assignment. */
  prepareApply(document: ValidatedDocument): () => void;
  api?: DocumentAPI; files?: DocumentFiles;
  /** Existing all-mode ownership excluding this controller. No resources are discarded to make room. */
  retainedBytes?(): number;
  /** Future allocations of an active scientific operation, above current actual retention. */
  reservedBytes?(): Readonly<{ persistent: number; transient: number }>;
}
type Intent = { kind: 'import'; file: File; generation: number; contextToken: string; resolve: (ok: boolean) => void }
  | { kind: 'export'; document: ExperimentDocument; revision: number; generation: number; resolve: (ok: boolean) => void };
const textOf = (error: unknown) => error instanceof Error ? error.message : 'Document operation failed';
export class ExperimentDocumentController {
  private snapshot: DocumentState;
  private api: DocumentAPI;
  private files: DocumentFiles;
  private listeners = new Set<(state: DocumentState) => void>();
  private generation = 0;
  private metadataGeneration = 0;
  private lastContext: string;
  private pendingIntent: Intent | null = null;
  private activeIntent: Intent | null = null;
  private abort: AbortController | null = null;
  private pumping = false;
  private applying = false;
  private disposed = false;
  private operationBuffers = new Set<ArrayBufferLike>();
  private operationStrings: string[] = [];
  private transientReserved = 0;
  constructor(private options: DocumentControllerOptions) {
    this.api = options.api ?? createDocumentFetchAPI(); this.files = options.files ?? new ExperimentDocumentFiles();
    const empty = Object.freeze({ title: '', notes: '' });
    this.snapshot = Object.freeze({ metadata: Object.freeze({ sequential: empty, two_path: empty, polarization: empty }),
      metadataErrors: Object.freeze({}), pending: false, operation: null, status: 'idle', error: null,
      preview: null, acknowledged: false, preparedDownload: null, restored: null });
    this.lastContext = this.contextToken();
  }
  get state(): DocumentState { return this.snapshot; }
  get isApplying(): boolean { return this.applying; }
  private contextToken(): string { const context = this.options.context(); return `${context.mode}|${context.token}|metadata:${this.metadataGeneration}`; }
  subscribe(listener: (state: DocumentState) => void): () => void {
    this.listeners.add(listener); listener(this.snapshot); return () => this.listeners.delete(listener);
  }
  private publish(change: Partial<DocumentState>): void {
    this.snapshot = Object.freeze({ ...this.snapshot, ...change });
    for (const listener of this.listeners) { try { listener(this.snapshot); } catch { /* Presentation cannot turn settings into a failed scientific request. */ } }
  }
  setMetadata(mode: BenchMode, value: DocumentMetadata): void {
    const errors = { ...this.snapshot.metadataErrors }; let copied: DocumentMetadata;
    try {
      copied = validateDocumentMetadata(value);
      this.admit(2 * (copied.title.length + copied.notes.length)); delete errors[mode];
    } catch (error) {
      ++this.metadataGeneration;
      this.publish({ metadataErrors: Object.freeze({ ...errors, [mode]: textOf(error) }) }); this.contextChanged(); return;
    }
    ++this.metadataGeneration;
    this.publish({ metadata: Object.freeze({ ...this.snapshot.metadata, [mode]: copied }), metadataErrors: Object.freeze(errors) });
    this.contextChanged();
  }
  /** Main calls after scientific subscriptions or mode changes; viewing selection keeps its token unchanged. */
  contextChanged(): void {
    if (this.disposed || this.applying) return;
    const next = this.contextToken(); if (next === this.lastContext) return;
    this.lastContext = next; this.cancelImport();
    if (this.snapshot.restored) this.publish({ restored: null, ...(this.snapshot.status === 'restored' ? { status: 'idle' as const } : {}) });
  }
  acknowledgeReplacement(value: boolean): void { this.publish({ acknowledged: !!this.snapshot.preview && value }); }
  private current(intent: Intent): boolean {
    return !this.disposed && intent.generation === this.generation
      && (intent.kind !== 'import' || intent.contextToken === this.contextToken());
  }
  private admit(extraPersistent = 0, extraTransient = 0): void {
    const own = this.ownershipSnapshot(), external = this.options.retainedBytes?.() ?? 0;
    const reserved = this.options.reservedBytes?.() ?? { persistent: 0, transient: 0 };
    assertOwnedBudgets(external + own.retainedBytes + reserved.persistent + Math.max(extraPersistent, own.projectedPersistentBytes),
      external + own.retainedBytes + reserved.transient + Math.max(own.transientReservedBytes, extraTransient));
  }
  private schedule(intent: Omit<Extract<Intent, { kind: 'import' }>, 'resolve'> | Omit<Extract<Intent, { kind: 'export' }>, 'resolve'>): Promise<boolean> {
    if (this.disposed) return Promise.resolve(false);
    this.pendingIntent?.resolve(false);
    this.abort?.abort();
    return new Promise(resolve => {
      this.pendingIntent = { ...intent, resolve } as Intent;
      this.publish({ pending: true, operation: intent.kind, status: intent.kind === 'import' ? 'reading' : 'validating', error: null, preview: null, acknowledged: false });
      if (!this.pumping) void this.pump();
    });
  }
  exportCurrent(): Promise<boolean> {
    const draft = this.options.currentValidDraft();
    if (!draft || this.snapshot.metadataErrors[draft.mode]) { this.publish({ error: '目前草稿尚未通過驗證，無法匯出。' }); return Promise.resolve(false); }
    let document: ExperimentDocument;
    try { document = makeExperimentDocument(draft.mode, draft.experiment, this.snapshot.metadata[draft.mode]); }
    catch (error) { this.publish({ error: textOf(error) }); return Promise.resolve(false); }
    const generation = ++this.generation;
    return this.schedule({ kind: 'export', document, revision: draft.revision, generation });
  }
  importFile(file: File): Promise<boolean> {
    const generation = ++this.generation, contextToken = this.contextToken(); this.lastContext = contextToken;
    return this.schedule({ kind: 'import', file, generation, contextToken });
  }
  cancelImport(): void {
    if (this.activeIntent?.kind === 'import' || this.pendingIntent?.kind === 'import' || this.snapshot.preview) {
      ++this.generation;
      if (this.activeIntent?.kind === 'import') this.abort?.abort();
      if (this.pendingIntent?.kind === 'import') { this.pendingIntent.resolve(false); this.pendingIntent = null; }
      this.publish({ preview: null, acknowledged: false, pending: false, operation: null, status: 'idle', error: null });
    }
  }
  private async validate(bytes: Uint8Array, intent: Intent, signal: AbortSignal): Promise<ValidatedDocument | null> {
    if (!this.current(intent)) return null;
    this.operationBuffers.add(bytes.buffer); this.transientReserved = 16 * MAX_DOCUMENT_BYTES; this.admit();
    const result = await this.api.validate(bytes, signal);
    if (!this.current(intent) || signal.aborted) return null;
    if (!(result.bytes instanceof Uint8Array) || result.bytes.byteLength > MAX_DOCUMENT_BYTES || !/^[0-9a-f]{64}$/.test(result.experimentSha256)) throw new Error('Invalid authoritative document reply');
    this.operationBuffers.add(result.bytes.buffer);
    const owned = ownExperimentDocument(result.document);
    this.operationStrings.push(JSON.stringify(owned)); this.admit();
    return Object.freeze({ document: owned, bytes: result.bytes, experimentSha256: result.experimentSha256 });
  }
  private async execute(intent: Intent, signal: AbortSignal): Promise<boolean> {
    this.transientReserved = 16 * MAX_DOCUMENT_BYTES;
    // Reserve the incoming owned file before its FileReader can allocate it.
    this.admit(intent.kind === 'import' ? intent.file.size : MAX_DOCUMENT_BYTES);
    if (intent.kind === 'export') {
      const body = browserDocumentBytes(intent.document);
      const validated = await this.validate(body, intent, signal); if (!validated) return false;
      assertDocumentCorrespondence(intent.document, validated.document);
      this.admit(validated.bytes.byteLength + 2 * JSON.stringify(validated.document).length);
      const download = this.files.prepareDownload(validated.bytes, `${validated.document.mode}-settings.json`);
      if (!this.current(intent)) { this.files.dismissDownload(); return false; }
      this.publish({ preparedDownload: Object.freeze({ ...download, document: validated.document, revision: intent.revision, requested: false }),
        status: 'download_prepared', error: null });
      return true;
    }
    if (!this.current(intent)) return false;
    const raw = await this.files.read(intent.file, signal);
    if (!this.current(intent) || signal.aborted) return false;
    // Raw uploaded bytes must reach the authoritative parser before any browser parse.
    const first = await this.validate(raw, intent, signal); if (!first) return false;
    const rawDefinition = ownExperimentDocument(parseStrictJSON(new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(raw)));
    assertDocumentCorrespondence(rawDefinition, first.document);
    this.publish({ status: 'validating' });
    const body = browserDocumentBytes(first.document);
    const second = await this.validate(body, intent, signal); if (!second) return false;
    assertDocumentCorrespondence(first.document, second.document);
    this.admit(2 * JSON.stringify(second.document).length);
    if (!this.current(intent)) return false;
    this.publish({ preview: Object.freeze({ ...second, generation: intent.generation, contextToken: intent.contextToken }),
      status: 'preview', acknowledged: false, error: null });
    return true;
  }
  private async pump(): Promise<void> {
    this.pumping = true;
    try {
      while (this.pendingIntent) {
        const intent = this.pendingIntent; this.pendingIntent = null;
        if (!this.current(intent)) { intent.resolve(false); continue; }
        this.activeIntent = intent; const abort = new AbortController(); this.abort = abort;
        let ok = false;
        try { ok = await this.execute(intent, abort.signal); }
        catch (error) {
          if (this.current(intent) && !abort.signal.aborted) this.publish({ status: 'error', error: textOf(error), preview: null, acknowledged: false });
        } finally {
          this.operationBuffers.clear(); this.operationStrings = []; this.transientReserved = 0;
          if (this.abort === abort) this.abort = null;
          if (this.activeIntent === intent) this.activeIntent = null;
          if (this.current(intent)) this.publish({ pending: false, operation: null });
          intent.resolve(ok);
        }
      }
    } finally { this.pumping = false; }
  }
  /** All throwing preparation precedes the synchronous settings commit. */
  applyImport(): boolean {
    const preview = this.snapshot.preview;
    if (!preview || !this.snapshot.acknowledged || this.snapshot.pending || this.options.busy()
      || preview.generation !== this.generation || preview.contextToken !== this.contextToken()) return false;
    let commit: () => void;
    try { commit = this.options.prepareApply(preview); }
    catch (error) { this.publish({ error: textOf(error) }); return false; }
    if (this.options.busy() || this.snapshot.preview !== preview || preview.generation !== this.generation
      || preview.contextToken !== this.contextToken()) return false;
    this.applying = true;
    try {
      commit();
      ++this.metadataGeneration;
      const errors = { ...this.snapshot.metadataErrors }; delete errors[preview.document.mode];
      this.publish({ metadata: Object.freeze({ ...this.snapshot.metadata, [preview.document.mode]: preview.document.metadata }),
        metadataErrors: Object.freeze(errors), preview: null, acknowledged: false, status: 'restored', error: null,
        restored: Object.freeze({ mode: preview.document.mode, generation: preview.generation }) });
      this.lastContext = this.contextToken(); return true;
    } catch (error) { this.publish({ error: textOf(error) }); return false; }
    finally { this.applying = false; }
  }
  markDownloadRequested(): void {
    if (this.snapshot.preparedDownload) this.publish({ preparedDownload: Object.freeze({ ...this.snapshot.preparedDownload, requested: true }), status: 'download_requested' });
  }
  dismissDownload(): void { this.files.dismissDownload(); this.publish({ preparedDownload: null, status: this.snapshot.preview ? 'preview' : 'idle' }); }
  ownershipSnapshot(): Readonly<{ retainedBytes: number; bufferBytes: number; blobBytes: number; logicalStringBytes: number;
    transientReservedBytes: number; projectedPersistentBytes: number; activeReaders: number; activeFetches: number; pendingSelections: number; urls: number }> {
    const buffers = new Set(this.operationBuffers), documents = new Set<object>();
    if (this.snapshot.preview) { buffers.add(this.snapshot.preview.bytes.buffer); documents.add(this.snapshot.preview.document); }
    if (this.snapshot.preparedDownload) { buffers.add(this.snapshot.preparedDownload.bytes.buffer); documents.add(this.snapshot.preparedDownload.document); }
    const bufferBytes = [...buffers].reduce((total, buffer) => total + buffer.byteLength, 0), files = this.files.ownershipSnapshot();
    const logicalStringBytes = [...documents].reduce((total, document) => total + 2 * JSON.stringify(document).length, 0)
      + this.operationStrings.reduce((total, string) => total + 2 * string.length, 0)
      + Object.values(this.snapshot.metadata).reduce((total, metadata) => total + 2 * (metadata.title.length + metadata.notes.length), 0);
    return Object.freeze({ retainedBytes: bufferBytes + files.blobBytes + logicalStringBytes + files.readerReservedBytes,
      bufferBytes, blobBytes: files.blobBytes, logicalStringBytes, transientReservedBytes: this.transientReserved,
      projectedPersistentBytes: this.snapshot.pending ? 4 * MAX_DOCUMENT_BYTES : 0,
      activeReaders: files.activeReaders, activeFetches: this.abort && this.activeIntent && files.activeReaders === 0 ? 1 : 0,
      pendingSelections: this.pendingIntent ? 1 : 0, urls: files.urls });
  }
  dispose(): void {
    this.disposed = true; ++this.generation; this.abort?.abort();
    this.pendingIntent?.resolve(false); this.pendingIntent = null; this.files.dispose();
    this.snapshot = Object.freeze({ ...this.snapshot, pending: false, operation: null, preview: null, preparedDownload: null, acknowledged: false });
    this.listeners.clear();
  }
}
