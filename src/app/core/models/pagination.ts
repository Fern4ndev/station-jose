/** `Pagination` y `PaginationResponse` comparten la misma forma en el backend. */
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
