/** Intentos fallidos permitidos dentro de la ventana antes de bloquear. */
export const RATE_LIMIT_MAX = 5;

/** Ventana móvil en la que se cuentan los intentos fallidos. */
export const RATE_LIMIT_WINDOW_MS = 60_000;

/** Duración del bloqueo temporal una vez superado `RATE_LIMIT_MAX`. */
export const LOCKOUT_MS = 30_000;
