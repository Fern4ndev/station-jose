import { afterEach, describe, expect, it, vi } from 'vitest';
import { downloadBlob } from './download';

describe('downloadBlob', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('crea el enlace, dispara la descarga y libera la URL', () => {
    const createObjectURL = vi.fn(() => 'blob:reporte');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL });
    vi.useFakeTimers();
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);

    downloadBlob(new Blob(['a,b'], { type: 'text/csv' }), 'reporte.csv');

    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectURL).not.toHaveBeenCalled();
    expect(document.querySelector('a')).toBeNull();

    vi.runAllTimers();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:reporte');

    vi.useRealTimers();
    vi.unstubAllGlobals();
  });
});
