/**
 * Entorno de producción.
 * La API se publica detrás del mismo origen (reverse proxy), por eso el prefijo
 * es relativo y no requiere CORS.
 */
export const environment = {
  production: true,
  appName: 'San José · Control de combustible',
  apiUrl: '/api/v1',
} as const;
