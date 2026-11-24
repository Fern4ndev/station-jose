import { firstValueFrom, of } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';
import type { ListParams, Page } from '../../core/api/api-url';
import { fetchAllPages } from './fetch-all';

const page = <T>(items: T[], total: number, pageNumber: number, pageSize = 2): Page<T> => ({
  items,
  total,
  page: pageNumber,
  page_size: pageSize,
});

describe('fetchAllPages', () => {
  it('concatena todas las páginas hasta cubrir el total', async () => {
    const loader = vi.fn((params: ListParams) =>
      of(
        params.page === 1
          ? page(['a', 'b'], 3, 1, params.page_size)
          : page(['c'], 3, 2, params.page_size),
      ),
    );

    await expect(firstValueFrom(fetchAllPages(loader))).resolves.toEqual(['a', 'b', 'c']);
    expect(loader).toHaveBeenCalledTimes(2);
    expect(loader.mock.calls[1][0]).toMatchObject({ page: 2, page_size: 100 });
  });

  it('respeta el tamaño de página y el inicio indicados', async () => {
    const loader = vi.fn((params: ListParams) => of(page([1, 2], 4, params.page ?? 1, 2)));

    await expect(
      firstValueFrom(fetchAllPages(loader, { page_size: 2, q: 'diesel' })),
    ).resolves.toEqual([1, 2, 1, 2]);
    expect(loader.mock.calls[0][0]).toMatchObject({ page: 1, page_size: 2, q: 'diesel' });
  });

  it('se detiene con una página vacía o con maxPages', async () => {
    const empty = vi.fn(() => of(page<string>([], 10, 1)));
    await expect(firstValueFrom(fetchAllPages(empty))).resolves.toEqual([]);
    expect(empty).toHaveBeenCalledOnce();

    const endless = vi.fn((params: ListParams) => of(page(['x'], 10_000, params.page ?? 1)));
    const rows = await firstValueFrom(fetchAllPages(endless, { page_size: 1 }, 3));
    expect(rows).toHaveLength(3);
    expect(endless).toHaveBeenCalledTimes(3);
  });
});
