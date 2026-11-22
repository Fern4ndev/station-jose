/** `Pagination` y `PaginationResponse` del backend comparten la misma forma. */
export interface Pagination {
  readonly page: number;
  readonly page_size: number;
  readonly total: number;
  readonly pages: number;
}

export type PaginationResponse = Pagination;

export interface PaginatedResponse<T> {
  readonly items: readonly T[];
  readonly pagination: Pagination;
}

/** Parámetros de paginación comunes (page: 1, page_size: 20 en FastAPI). */
export interface PageQuery {
  readonly page?: number;
  readonly page_size?: number;
}

export const DEFAULT_PAGE = 1;
export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 100;

export const firstPageQuery: PageQuery = {
  page: DEFAULT_PAGE,
  page_size: DEFAULT_PAGE_SIZE,
};
