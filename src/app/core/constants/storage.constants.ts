/** Prefijo único para no colisionar con otras claves del navegador. */
export const STORAGE_PREFIX = 'sanjose';

export const STORAGE_KEYS = {
  accessToken: `${STORAGE_PREFIX}.auth.access-token`,
  user: `${STORAGE_PREFIX}.auth.user`,
  permissions: `${STORAGE_PREFIX}.auth.permissions`,
  expiresAt: `${STORAGE_PREFIX}.auth.expires-at`,
  persistence: `${STORAGE_PREFIX}.auth.persistence`,
} as const;

/** El checkbox "Mantener la sesión en este equipo" decide el almacenamiento. */
export type StoragePersistence = 'local' | 'session';
