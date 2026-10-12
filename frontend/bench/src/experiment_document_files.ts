/** Owned browser file/download lifetimes. Filenames never reach a server path. */
import { MAX_DOCUMENT_BYTES } from './experiment_documents';

export interface PreparedDownload {
  readonly url: string; readonly filename: string; readonly bytes: Uint8Array; readonly blob: Blob;
}
export interface DocumentFiles {
  read(file: File, signal: AbortSignal): Promise<Uint8Array>;
  prepareDownload(bytes: Uint8Array, filename: string): PreparedDownload;
  dismissDownload(): void; dispose(): void;
  ownershipSnapshot(): Readonly<{ activeReaders: number; readerReservedBytes: number; urls: number; blobBytes: number }>;
}
interface FileOptions { readerFactory?: () => FileReader; urlAPI?: Pick<typeof URL, 'createObjectURL' | 'revokeObjectURL'>;
  blobFactory?: (bytes: Uint8Array) => Blob }
const aborted = () => new DOMException('Document operation superseded', 'AbortError');
export class ExperimentDocumentFiles implements DocumentFiles {
  private reader: FileReader | null = null;
  private readerReservedBytes = 0;
  private download: PreparedDownload | null = null;
  private disposed = false;
  constructor(private options: FileOptions = {}) {}
  read(file: File, signal: AbortSignal): Promise<Uint8Array> {
    if (this.disposed) return Promise.reject(new Error('Document files disposed'));
    if (signal.aborted) return Promise.reject(aborted());
    if (!Number.isSafeInteger(file.size) || file.size < 2 || file.size > MAX_DOCUMENT_BYTES) return Promise.reject(new Error('Document file byte cap'));
    if (this.reader) return Promise.reject(new Error('One owned document reader is already active'));
    const reader = (this.options.readerFactory ?? (() => new FileReader()))();
    this.reader = reader; this.readerReservedBytes = file.size;
    return new Promise((resolve, reject) => {
      let finished = false;
      const cleanup = () => {
        reader.onload = null; reader.onerror = null; reader.onabort = null;
        signal.removeEventListener('abort', onAbort);
        if (this.reader === reader) { this.reader = null; this.readerReservedBytes = 0; }
      };
      const finish = (bytes: Uint8Array | null, error?: unknown) => {
        if (finished) return; finished = true; cleanup();
        if (bytes) resolve(bytes); else reject(error ?? new Error('Document file read failed'));
      };
      const onAbort = () => { try { reader.abort(); } finally { finish(null, aborted()); } };
      reader.onload = () => {
        if (signal.aborted) { finish(null, aborted()); return; }
        if (!(reader.result instanceof ArrayBuffer) || reader.result.byteLength !== file.size
          || reader.result.byteLength > MAX_DOCUMENT_BYTES) { finish(null, new Error('Document actual file length/cap')); return; }
        finish(new Uint8Array(reader.result));
      };
      reader.onerror = () => finish(null, reader.error ?? new Error('Document file read failed'));
      reader.onabort = () => finish(null, aborted());
      signal.addEventListener('abort', onAbort, { once: true });
      try { reader.readAsArrayBuffer(file); } catch (error) { finish(null, error); }
    });
  }
  prepareDownload(bytes: Uint8Array, filename: string): PreparedDownload {
    if (this.disposed) throw new Error('Document files disposed');
    if (!(bytes instanceof Uint8Array) || bytes.byteLength < 2 || bytes.byteLength > MAX_DOCUMENT_BYTES) throw new Error('Document download byte cap');
    if (!/^(sequential|two_path|polarization)-settings\.json$/.test(filename)) throw new Error('Document download filename');
    const blob = (this.options.blobFactory ?? (data => new Blob([new Uint8Array(data).buffer], { type: 'application/json;charset=utf-8' })))(bytes);
    const urlAPI = this.options.urlAPI ?? URL;
    const url = urlAPI.createObjectURL(blob);
    const prepared = Object.freeze({ url, filename, bytes, blob });
    // Preparation is a deliberate later action; the old link's useful lifetime ends here.
    this.dismissDownload(); this.download = prepared; return prepared;
  }
  dismissDownload(): void {
    if (this.download) { (this.options.urlAPI ?? URL).revokeObjectURL(this.download.url); this.download = null; }
  }
  ownershipSnapshot() {
    return Object.freeze({ activeReaders: this.reader ? 1 : 0, readerReservedBytes: this.readerReservedBytes,
      urls: this.download ? 1 : 0, blobBytes: this.download?.blob.size ?? 0 });
  }
  dispose(): void {
    this.disposed = true; this.reader?.abort(); this.dismissDownload();
  }
}
