/**
 * Llaves de almacenamiento de la sesión (única fuente de verdad).
 *
 * `POST /auth/login` devuelve `access_token`, `token_type`, `expires_in`, `user`
 * y `permissions`: no hay `refresh_token`, así que no se persiste ninguno.
 * El vencimiento se guarda como instante absoluto para poder validarlo sin
 * volver a leer `expires_in`.
 */
export const AUTH_STORAGE_PREFIX = 'sanjose';

export const ACCESS_TOKEN_KEY = `${AUTH_STORAGE_PREFIX}.auth.access-token`;
export const ACCESS_TOKEN_EXPIRES_AT_KEY = `${AUTH_STORAGE_PREFIX}.auth.expires-at`;

/** Sesión serializada: incluye `user` y `permissions`. */
export const SESSION_KEY = `${AUTH_STORAGE_PREFIX}.auth.session`;

/** `'local' | 'session'`: dónde quedó guardada la sesión vigente. */
export const SESSION_PERSISTENCE_KEY = `${AUTH_STORAGE_PREFIX}.auth.persistence`;

export const AUTH_STORAGE_KEYS = {
  accessToken: ACCESS_TOKEN_KEY,
  expiresAt: ACCESS_TOKEN_EXPIRES_AT_KEY,
  session: SESSION_KEY,
  persistence: SESSION_PERSISTENCE_KEY,
} as const;

/** El checkbox "Mantener la sesión en este equipo" decide el almacenamiento. */
export type StoragePersistence = 'local' | 'session';
