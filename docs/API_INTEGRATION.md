# Contrato de integración frontend / backend

Revisión 1.2 — 18/11/2026. Inventario de `backend-station/app/routers`,
`schemas` y `core/permissions.py`, contrastado parcialmente con pruebas HTTP y PostgreSQL.
Ante un cambio, actualizar este documento junto con los esquemas y consumidores.

## Entorno y sesión

Angular usa `http://localhost:8000/api/v1` tanto en `environment.ts` (producción)
como en `environment.development.ts` (desarrollo). El backend debe permitir el
origen del frontend en `CORS_ORIGINS`. El proxy solo se utiliza si la URL se cambia
a una ruta relativa. En un despliegue remoto, cambiar `localhost` por la dirección
del backend accesible desde los navegadores. Configurar backend
y PostgreSQL siguiendo `backend-station/README.md`, sus scripts SQL y `.env.example`;
crear cuentas de desarrollo por los mecanismos del backend, sin guardar credenciales
reales en el repositorio. Comprobar `/api/v1/health/live` y `/health/ready` antes de integrar.

### Cuentas locales de prueba

Estas credenciales son exclusivamente para pruebas locales y no deben usarse en
producción. Juan y Pedro tienen asignada la sede San José.

| Rol | Correo | Contraseña |
|---|---|---|
| ADMIN | `admin@gmail.com` | `12345678` |
| OFFICE | `oficina@gmail.com` | `12345678` |
| ATTENDANT | `juan@gmail.com` | `12345678` |
| ATTENDANT | `pedro@gmail.com` | `12345678` |

Login recibe `{email,password}` y responde `access_token`, `token_type`, `expires_in`,
`user` y `permissions`. `GET /auth/me` devuelve usuario y permisos; logout devuelve
204. El frontend conserva token y permisos solo en memoria: al recargar se pierde la
sesión y se solicita login; no hay refresh ni persistencia. Al vencer o recibir 401
de la API, limpia la sesión y vuelve al login. 403 lleva a acceso denegado; un error
de logout cierra la sesión local e informa que no pudo confirmar la revocación.
Solo se adjunta el bearer a rutas bajo la URL base configurada. El servidor sigue
siendo la autoridad para revocación, permisos y alcance.

## Catálogo contrastado con código

Las rutas omiten `/api/v1`. Los permisos se leen de los routers y
`core/permissions.py`; los campos completos y sus validaciones están en los schemas.
La presencia de un router no acredita integración con datos reales.

| Operación | Permiso | Contrato principal |
|---|---|---|
| `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` | Público / autenticado | `schemas/auth.py`; logout 204. |
| `GET/POST /users`, `GET/PATCH /users/{id}`, `PATCH /users/{id}/role`, `PATCH /users/{id}/status` | `users.manage` | `schemas/user.py`, `schemas/common.py`; lista `page`, `page_size`. |
| `GET /branches`, `GET /fuel-types` | Autenticado | Listas `schemas/catalog.py`. |
| `GET/POST /purchase-orders`, `GET/PATCH/DELETE /purchase-orders/{id}` | `purchase_orders.read/create/update/delete` | `schemas/purchase_order.py`; lista acepta `search`, `branch_id`, `issue_date_from/to`, paginación, `sort_by` y `sort_order`. |
| `GET /vouchers`, `GET /vouchers/{id}` | `vouchers.read` | `schemas/voucher.py`, `schemas/attendance.py`; lista acepta paginación, `purchase_order_id`, `voucher_number`, `issuer_name`, `created_from/to`. |
| `GET /vouchers/attended` | `attendances.read_own` | Vales con al menos un despacho del usuario actual; admite paginación y `voucher_number`. |
| `PATCH /vouchers/{id}/descriptive-data`, `DELETE /vouchers/{id}` | `vouchers.correct_descriptive`, `vouchers.delete` | `schemas/voucher.py`; delete 204 sujeto a reglas de negocio. |
| `POST /purchase-orders/{id}/attendances`, `POST /vouchers/{id}/attendances` | `attendances.create` | `schemas/attendance.py`, cabecera UUID `Idempotency-Key`, 201; primera atención requiere emisor y número de vale. |
| `GET /reports/dashboard`, `/reports/purchase-orders`, `/reports/attendances` | `reports.read` | `schemas/report.py`; filtros específicos en `routers/reports.py`. |
| `GET /reports/purchase-orders/export`, `/reports/attendances/export` | `reports.export` | `format=pdf|xlsx`; los filtros de exportación son un subconjunto de los de consulta. |
| `POST /ocr/purchase-order-previews` | `ocr.purchase_orders.process` | Multipart `file` PDF; respuesta en `schemas/ocr.py`. |
| `GET /health/live`, `GET /health/ready` | Público | Estado de proceso y base de datos. |

Las listas de usuarios, órdenes y vales usan `items` y `pagination` con `page`,
`page_size`, `total` y `pages`; `page_size` máximo 100. Fechas y UUID siguen los
tipos de los schemas; importes y cantidades son decimales, sin convertirlos a
flotantes para cálculos oficiales. Errores de dominio y validación usan
`{success:false,error:{code,message,details}}`: 401 sesión/credenciales, 403
permisos, 404 recurso, 409 conflicto, 422 validación y 500 error inesperado;
consultar `core/exceptions.py` para códigos específicos.

## Brechas y responsables

| Brecha | Responsable propuesto | Bloque afectado / salida requerida |
|---|---|---|
| Las respuestas operativas de órdenes, vales y creación de atenciones excluyen los campos financieros para el grifero. El historial de un vale incluye solo sus propias atenciones para ese rol. | Backend + frontend | Las listas y detalles se contrastaron con API real; una prueba HTTP transaccional con PostgreSQL comprueba la creación y una prueba unitaria el filtrado de historial. Falta verificar el historial con varios usuarios mediante HTTP y autenticación real. |
| Los routers `GET /attendances` y `/balances/*` descritos en planes históricos no están implementados como endpoints dedicados. | Responsable funcional + backend | Consultar el listado de vales atendidos y los saldos derivados desde órdenes y vales. |

Estos responsables son propuestas de coordinación, no asignaciones confirmadas.

La pantalla de saldos consulta las líneas de órdenes, hasta 20 resultados por
búsqueda. Las respuestas operativas del grifero omiten precios e importes. El
listado y detalle de vales del grifero muestran registros de su sede; la página
de vales atendidos limita además el historial al usuario actual.

### Alcance actualmente implementado

Las consultas y detalles de órdenes y vales se limitan en el servidor a la sede del
grifero. La creación de atenciones comprueba que la orden o el vale pertenezcan a
esa misma sede; la página de vales atendidos limita además el resultado al usuario
actual. Oficina y Administración conservan su acceso global según sus permisos.

La primera atención ahora exige `voucher_items` con `purchase_order_item_id` y
`authorized_gallons`, además de `items` con las líneas y `attended_gallons` de la
entrega. Este cambio de contrato exige actualizar los clientes anteriores. Se
probó en PostgreSQL una autorización de dos combustibles con entrega parcial,
reintento de la misma clave y atención posterior. Los reintentos se comprueban por
contenido, usuario y orden o vale, y se serializan mediante un bloqueo transaccional
por clave. Las pruebas de concurrencia real, recuperación tras recarga y el flujo
de registro en el frontend siguen pendientes.
