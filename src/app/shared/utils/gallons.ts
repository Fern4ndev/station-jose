/**
 * Galones con precisión de 3 decimales.
 *
 * Los saldos se comparan en milésimas enteras para no arrastrar los residuos
 * binarios de `autorizado - atendido` (p. ej. 99.7 frente a 99.69999999999999),
 * que hacían rechazar atenciones válidas con decimales. El backend usa
 * `NUMERIC(14,3)`, por lo que 11 dígitos enteros y 3 decimales caben en un
 * entero seguro de JavaScript.
 */

export const GALLON_DECIMALS = 3;

const GALLON_FACTOR = 1000;
const GALLON_INPUT = /^\d{1,11}(?:[.,]\d{1,3})?$/;

export interface ParsedGallons {
  /** Cantidad exacta en milésimas. */
  readonly milli: number;
  /** Valor canónico para el payload: punto decimal y 3 decimales. */
  readonly normalized: string;
}

/**
 * Milésimas exactas de una cantidad ya validada por el servidor. Tolera
 * strings decimales, números y los residuos flotantes que produce JavaScript.
 */
export function gallonsToMilli(value: string | number | null | undefined): number {
  if (value === null || value === undefined) return 0;
  const numeric = typeof value === 'number' ? value : Number(value.replace(',', '.'));
  return Number.isFinite(numeric) ? Math.round(numeric * GALLON_FACTOR) : 0;
}

/** Saldo disponible en milésimas, sin valores negativos. */
export function gallonsBalanceMilli(
  authorized: string | number | null | undefined,
  attended: string | number | null | undefined,
): number {
  return Math.max(0, gallonsToMilli(authorized) - gallonsToMilli(attended));
}

/**
 * Interpreta lo escrito por el usuario: acepta coma o punto y exige un máximo
 * de 3 decimales. Devuelve `null` si el formato no es válido o excede la
 * precisión soportada por el servidor.
 */
export function parseGallonsInput(value: string): ParsedGallons | null {
  const text = value.trim();
  if (!GALLON_INPUT.test(text)) return null;
  const milli = Math.round(Number(text.replace(',', '.')) * GALLON_FACTOR);
  if (!Number.isSafeInteger(milli)) return null;
  return { milli, normalized: (milli / GALLON_FACTOR).toFixed(GALLON_DECIMALS) };
}
