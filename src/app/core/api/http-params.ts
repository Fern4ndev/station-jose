import { HttpParams } from '@angular/common/http';

/**
 * Convierte un objeto de query tipado en `HttpParams`, omitiendo los valores
 * vacíos (`undefined`, `null`, `''`) que FastAPI interpretaría como filtros.
 */
export const toHttpParams = (query: object): HttpParams => {
  let params = new HttpParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '') {
      continue;
    }
    params = params.set(key, String(value));
  }
  return params;
};
