# Integración manual con la API

Este catálogo se mantiene manualmente junto con el backend. Antes de cambiar una ruta o un DTO, revisar el router, el schema Pydantic, los permisos y los errores que produce el servicio correspondiente.

## Configuración de conexión

- Prefijo actual: `/api/v1`.
- Desarrollo local: Angular envía a `/api/v1`; `proxy.conf.json` reenvía `/api` a `http://127.0.0.1:8000`.
- Producción: el host web debe reenviar `/api` al backend. La URL base se lee desde `src/environments/` mediante `API_BASE_URL`.
- Las llamadas autenticadas usan `Authorization: Bearer <access_token>`.

## Formato de error común

```ts
interface ApiErrorEnvelope {
  success: false;
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
}
```

El frontend muestra mensajes de recuperación entendibles y no presenta `details` internos directamente al usuario.

## Autenticación

### `POST /api/v1/auth/login`

- Público.
- Request: `{ email: string, password: string }`.
- Email validado como dirección de correo; contraseña entre 8 y 128 caracteres.
- Response `200`: `access_token`, `token_type` (`bearer`), `expires_in` (segundos), `user` y `permissions`.
- `user`: `id`, `first_name`, `last_name`, `dni`, `email`, `role`, `branch` (`id`, `code`, `name` o `null`) e `is_active`.
- Roles conocidos: `ADMIN`, `OFFICE`, `ATTENDANT`.
- Errores `401`: `INVALID_CREDENTIALS` y `INACTIVE_USER`.

El DTO de transporte se mapea a un modelo de sesión camelCase en `AuthApiService`; los componentes no consumen directamente los nombres snake_case de la respuesta.

### `GET /api/v1/auth/me`

- Requiere Bearer token.
- Response `200`: los campos de `user` más `permissions`.
- Errores de autenticación: `401`; el backend comprueba cuenta habilitada, expiración y sesión activa.

### `POST /api/v1/auth/logout`

- Requiere Bearer token.
- Sin body.
- Response `204`; revoca la sesión identificada por el token.
- Ante un fallo de red, el frontend limpia igualmente la sesión local e informa que no pudo confirmar la revocación remota.

## Sesión frontend

- El token permanece solo en memoria; se toma la duración de `expires_in` y no se crean renovaciones que la API no soporta.
- Al recargar la página se solicita iniciar sesión nuevamente.
- Los permisos recibidos controlan navegación y acceso en frontend; cada endpoint mantiene la autorización definitiva en backend.
- `AuthStore` conserva token, usuario, sede, permisos y vencimiento; nunca se guardan credenciales ni tokens en Web Storage.

## Cambios de contrato

1. Revisar la implementación y acordar el cambio con backend.
2. Actualizar esta ficha, los DTOs de transporte, el mapper y el servicio Angular en el mismo cambio.
3. Actualizar guards o presentación solo si cambian permisos o errores.
4. Mantener tipos específicos por rol cuando los campos disponibles sean distintos.
