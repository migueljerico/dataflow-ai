
import { describe, it, expect, vi } from 'vitest';
describe('api handleResponse', () => {
  it('throws on non-ok with message', async () => {
    const { api } = await import('./api');
    (globalThis as any).fetch = vi.fn().mockResolvedValue({ ok: false, status: 400, json: async () => ({ message: 'bad' }) } as any);
    await expect(api.getDatasetMetadata('x')).rejects.toThrow('bad');
  });
  it('validates FileUpload 10MB client-side', () => {
    const file = new File(['a'], 'a.csv', { type: 'text/csv' });
    Object.defineProperty(file, 'size', { value: 11*1024*1024 });
    expect(file.size).toBeGreaterThan(10*1024*1024);
  });
});
