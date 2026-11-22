/**
 * Entorno de desarrollo.
 * FastAPI escucha en el puerto 8000 y su CORS permite http://localhost:4200.
 * Si se prefiere pasar por el proxy de `ng serve` (`proxy.conf.json`), usar
 * `apiUrl: '/api/v1'`.
 */
export const environment = {
  production: false,
  appName: 'San José · Control de combustible',
  apiUrl: 'http://localhost:8000/api/v1',
} as const;
