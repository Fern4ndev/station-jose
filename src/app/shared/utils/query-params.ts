export type QueryParams = Readonly<Record<string, unknown>>;

/**
 * Elimina `null`, `undefined`, `NaN`, cadenas vacías (o solo espacios) y
 * arreglos vacíos de un objeto de consulta. Devuelve un objeto nuevo: el
 * original no se muta, así que sirve tanto para `HttpParams` como para
 * construir URLs o filtros de estado.
 */
export function cleanParams<T extends QueryParams>(params?: T | null): Partial<T> {
  const result: Record<string, unknown> = {};
  if (!params) {
    return result as Partial<T>;
  }

  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined) {
      continue;
    }

    if (typeof value === 'number') {
      if (!Number.isNaN(value)) {
        result[key] = value;
      }
      continue;
    }

    if (typeof value === 'string') {
      const trimmed = value.trim();
      if (trimmed !== '') {
        result[key] = trimmed;
      }
      continue;
    }

    if (Array.isArray(value)) {
      const items = value.filter(
        (item) => item !== null && item !== undefined && item !== '',
      );
      if (items.length > 0) {
        result[key] = items;
      }
      continue;
    }

    result[key] = value;
  }

  return result as Partial<T>;
}
