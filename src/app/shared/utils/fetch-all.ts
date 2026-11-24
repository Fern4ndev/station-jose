import { EMPTY, type Observable, expand, reduce } from 'rxjs';
import type { ListParams, Page } from '../../core/api/api-url';

export const FETCH_ALL_PAGE_SIZE = 100;
export const FETCH_ALL_MAX_PAGES = 50;

/**
 * Recorre un endpoint paginado (`Page<T>`) hasta agotar `total` y devuelve
 * todas las filas juntas: útil para llenar selects de catálogo.
 *
 * `expand` encadena las páginas y `reduce` acumula los `items`. Se corta si la
 * página viene vacía, si ya se cubrió `total` o al alcanzar `maxPages`
 * (protege ante un backend que ignore `page`).
 */
export function fetchAllPages<T>(
  loader: (params: ListParams) => Observable<Page<T>>,
  params: ListParams = {},
  maxPages: number = FETCH_ALL_MAX_PAGES,
): Observable<T[]> {
  const pageSize = params.page_size ?? FETCH_ALL_PAGE_SIZE;
  const firstPage = params.page ?? 1;
  const lastPage = firstPage + Math.max(1, maxPages) - 1;

  return loader({ ...params, page: firstPage, page_size: pageSize }).pipe(
    expand((page) => {
      const loaded = (page.page - 1) * page.page_size + page.items.length;
      const hasMore = page.items.length > 0 && loaded < page.total && page.page < lastPage;
      return hasMore
        ? loader({ ...params, page: page.page + 1, page_size: page.page_size })
        : EMPTY;
    }),
    reduce((rows: T[], page) => rows.concat(page.items), []),
  );
}
