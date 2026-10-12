import { describe, expect, it } from 'vitest';
import { ExperimentDocumentFiles } from '../src/experiment_document_files';
class Reader {
  result: ArrayBuffer | null = null; error: Error | null = null;
  onload: (() => void) | null = null; onerror: (() => void) | null = null; onabort: (() => void) | null = null;
  file: File | null = null; aborted = false;
  readAsArrayBuffer(file: File) { this.file = file; }
  abort() { this.aborted = true; this.onabort?.(); }
  finish(bytes: Uint8Array) { this.result = new Uint8Array(bytes).buffer; this.onload?.(); }
}
function setup() {
  const readers: Reader[] = [], urls = new Set<string>(), revoked: string[] = []; let next = 0;
  const files = new ExperimentDocumentFiles({ readerFactory: () => { const reader = new Reader(); readers.push(reader); return reader as unknown as FileReader; },
    urlAPI: { createObjectURL() { const url = `blob:test-${++next}`; urls.add(url); return url; }, revokeObjectURL(url) { urls.delete(url); revoked.push(url); } } });
  return { files, readers, urls, revoked };
}
describe('bounded document file and download ownership', () => {
  it('owns one abortable raw reader and drops every handler on completion or abort', async () => {
    const { files, readers } = setup(), abort = new AbortController(), file = new File(['{"x":1}'], 'same.json');
    const first = files.read(file, abort.signal);
    await expect(files.read(file, new AbortController().signal)).rejects.toThrow('already active');
    expect(files.ownershipSnapshot().activeReaders).toBe(1); abort.abort(); await expect(first).rejects.toThrow('superseded');
    expect(readers[0].onload).toBeNull(); expect(readers[0].onabort).toBeNull(); expect(readers[0].onerror).toBeNull();
    const second = files.read(file, new AbortController().signal); readers[1].finish(new TextEncoder().encode('{"x":1}'));
    expect(new TextDecoder().decode(await second)).toBe('{"x":1}'); expect(files.ownershipSnapshot().activeReaders).toBe(0);
  });
  it('checks claimed and actual byte caps without trusting extension or filename', async () => {
    const { files, readers } = setup(); await expect(files.read(new File(['x'.repeat(32769)], 'small.json'), new AbortController().signal)).rejects.toThrow('cap');
    const file = new File(['{}'], 'renamed.txt'), pending = files.read(file, new AbortController().signal);
    readers[0].finish(new Uint8Array(3)); await expect(pending).rejects.toThrow('actual');
  });
  it('keeps prepared URL usable until explicit dismissal and releases repeated downloads', async () => {
    const { files, urls, revoked } = setup(), bytes = new TextEncoder().encode('{"title":"中文"}\n');
    for (let i = 0; i < 5; i++) {
      const prepared = files.prepareDownload(bytes, 'polarization-settings.json');
      expect(urls.has(prepared.url), 'DOWNLOAD_LIFETIME_DETECTED').toBe(true);
      expect(new Uint8Array(await prepared.blob.arrayBuffer()), 'DOWNLOAD_LIFETIME_DETECTED').toEqual(bytes);
      expect(files.ownershipSnapshot().urls, 'DOWNLOAD_LIFETIME_DETECTED').toBe(1);
    }
    expect(revoked, 'DOWNLOAD_LIFETIME_DETECTED').toHaveLength(4); files.dismissDownload();
    expect(urls.size, 'DOWNLOAD_LIFETIME_DETECTED').toBe(0); expect(files.ownershipSnapshot().blobBytes).toBe(0);
    files.dispose(); expect(() => files.prepareDownload(bytes, 'sequential-settings.json')).toThrow('disposed');
  });
  it('page disposal aborts its own reader and releases only its prepared URL', async () => {
    const { files, readers, urls } = setup(); const reading = files.read(new File(['{}'], 'file.json'), new AbortController().signal);
    files.prepareDownload(new TextEncoder().encode('{}'), 'sequential-settings.json'); files.dispose();
    await expect(reading).rejects.toThrow('superseded'); expect(readers[0].onload).toBeNull(); expect(urls.size).toBe(0);
  });
});
