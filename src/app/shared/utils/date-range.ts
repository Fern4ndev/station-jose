const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})/;

const pad = (value: number): string => String(value).padStart(2, '0');

export interface IsoRange {
  readonly date_from: string | null;
  readonly date_to: string | null;
}

/**
 * Fecha local en `YYYY-MM-DD` (el formato que esperan los filtros de FastAPI).
 * Acepta `Date`, ISO completo (`2026-11-23T15:04:05Z`) o texto ya recortado.
 * Devuelve `null` cuando el valor no es una fecha válida.
 */
export function toIsoDate(value: Date | string | null | undefined): string | null {
  if (value === null || value === undefined) {
    return null;
  }

  if (value instanceof Date) {
    return Number.isNaN(value.getTime())
      ? null
      : `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`;
  }

  const trimmed = value.trim();
  if (trimmed === '') {
    return null;
  }

  const match = ISO_DATE.exec(trimmed);
  if (match) {
    return `${match[1]}-${match[2]}-${match[3]}`;
  }

  const parsed = new Date(trimmed);
  return toIsoDate(parsed);
}

/** Hoy en `YYYY-MM-DD`, con `now` inyectable para pruebas. */
export function todayIso(now: Date = new Date()): string {
  return toIsoDate(now) ?? '';
}

/** Par de filtros `date_from`/`date_to`, descartando valores inválidos. */
export function toIsoRange(
  from: Date | string | null | undefined,
  to: Date | string | null | undefined,
): IsoRange {
  return { date_from: toIsoDate(from), date_to: toIsoDate(to) };
}

/** `true` cuando `from` es posterior a `to` (ambos válidos). */
export function isReversedRange(
  from: Date | string | null | undefined,
  to: Date | string | null | undefined,
): boolean {
  const start = toIsoDate(from);
  const end = toIsoDate(to);
  return start !== null && end !== null && start > end;
}
