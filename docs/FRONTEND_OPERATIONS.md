# Operación y despliegue del frontend

## Desarrollo local

Desde la raíz del proyecto ejecuta `npm ci` y después `npm start`. Abre `http://localhost:4200`. El backend debe estar disponible y su configuración CORS debe autorizar ese origen. La guía del backend está en `backend-station/docs/OPERATIONS.md`.

Los archivos `src/environments/environment.ts` y `src/environments/environment.development.ts` apuntan actualmente a `http://localhost:8000/api/v1`. Angular sustituye el primero por el segundo en la configuración de desarrollo. `localhost` identifica el equipo del navegador: esta dirección solo sirve si la API es accesible en ese mismo equipo.

## Compilación y publicación

Ejecuta `npm test -- --watch=false` y `npm run build`. Publica los archivos estáticos generados en `dist/station/browser` en el servidor web acordado. Antes de compilar para producción, configura `apiUrl` en `environment.ts` con la dirección HTTPS accesible para los usuarios o con `/api/v1` si el servidor web envía ese prefijo a la API mediante un proxy inverso. Ajusta CORS en el backend cuando frontend y API tengan orígenes distintos. No incluyas contraseñas ni secretos en los archivos de Angular: su contenido se publica en el navegador.

El servidor debe devolver `index.html` para las rutas de la aplicación que no correspondan a archivos estáticos, de modo que una recarga de `/app/...` funcione. Si se usa el proxy `/api/v1`, sus solicitudes deben dirigirse al backend antes de aplicar el fallback de la SPA; no deben recibir `index.html`. Configura HTTPS y comprueba recarga de rutas, acceso a la API y respuestas de error en el entorno de destino. La configuración concreta depende del servidor elegido y debe verificarse allí.

## Estado de entrega

El registro de atenciones desde el espacio del grifero y el recorrido integral siguen pendientes; una compilación correcta no implica que el sistema esté listo para producción. No cargues los datos ni las cuentas de demostración en una base de producción.
