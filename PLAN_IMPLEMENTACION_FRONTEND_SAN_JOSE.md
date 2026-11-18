# PLAN DE IMPLEMENTACIÓN - FRONTEND SAN JOSÉ (Angular 21 + PrimeNG 21 + Tailwind 4)

> Complemento de `PLAN_BACKEND_SAN_JOSE_V2.md` y guía operativa del plan detallado
> `PLAN_FRONTEND_SAN_JOSE_V2.md`. Organiza la conexión a datos reales en bloques
> navegables y verificables. Estado contrastado con el código del repositorio el
> 17/11/2026; las rutas presentes en Python no implican que su integración o sus
> reglas estén verificadas de extremo a extremo.
>
> Principio: interfaz profesional y técnica. SPA sin SSR, PWA ni gestores de
> estado externos; Angular standalone, signals y servicios; PrimeNG, Tailwind y
> Chart.js instalados. No agregar dependencias sin una necesidad justificada.

## 0. Estado actual del frontend (lo que YA existe y se reutiliza)

| Base existente | Estado observado |
|---|---|
| Angular, PrimeNG y Tailwind | Angular 21, PrimeNG 21 y Tailwind 4 instalados; tema Aura configurado en `src/app/app.config.ts`. |
| Autenticación | Login, `AuthApiService`, `AuthStore` en memoria, interceptores y guards. La restauración tras recarga y los flujos completos deben verificarse; no asumir refresh tokens. |
| Estructura | `AdminLayout`, layout de autenticación, header, sidebar filtrado por permisos, rutas lazy y páginas 403/404. |
| Pantallas | Existen estructuras para dashboard, usuarios, órdenes, vales, atenciones, espacio del grifero, verificación, saldos y reportes. Tener una página o formulario no significa que opere con la API. |
| Compartidos | Tablas, estados vacío/error/carga, paginación, encabezados y wrappers PrimeNG en `src/app/shared/components`; ver su README. |
| Integración de dominio | Fuera de autenticación, las pantallas contienen estructuras y estados pendientes de integración. Revisar cada flujo antes de marcarlo completo. |

El backend local contiene routers para autenticación, usuarios, catálogos, órdenes,
vales, creación de atenciones, verificación, reportes y OCR. La sección 5 señala
las diferencias con el catálogo propuesto del plan backend. Ningún bloque se marca
terminado hasta comprobar sus criterios y registrar evidencia.

## 1. Decisiones definitivas (respondidas por el usuario)

1. Usar Angular 21, PrimeNG 21, Tailwind 4 y Chart.js ya instalados; SPA, signals y servicios, sin SSR, PWA ni gestor externo.
2. Roles fijos `ADMIN`, `OFFICE` y `ATTENDANT`. Las acciones y datos se rigen por permisos efectivos del backend; la API es la autoridad final.
3. Conservar el mockup como referencia visual. Componentes grandes se dividen en subcomponentes; cada archivo comparte el nombre de su carpeta/componente, salvo convenciones explícitas como `data-table-cell.directive.ts`. Crear solo archivos necesarios y CSS local únicamente cuando haga falta.
4. Reutilizar los componentes compartidos y PrimeNG. Formularios reactivos tipados, componentes standalone con `OnPush`, entradas/salidas con signals y servicios por dominio; sin reglas de negocio ni llamadas HTTP en componentes visuales compartidos.
5. El despacho registrado es inmutable. La verificación es independiente del consumo; una observación requiere explicación y no cambia saldos. No ofrecer ajuste cuantitativo sin flujo aprobado.
6. Primera atención crea vale y despacho en una operación; las posteriores usan el vale existente. Validar límites en la interfaz para orientar, pero el servidor resuelve saldos, concurrencia e idempotencia.
7. El grifero no debe recibir precios ni importes financieros. La corrección debe aplicarse en las respuestas del servidor, no solo ocultarse en Angular.
8. OCR de órdenes forma parte del alcance: presenta candidatos editables y nunca guarda automáticamente. Las decisiones pendientes PD del plan backend permanecen pendientes hasta su aprobación.

## 2. Estructura de rutas objetivo

Se mantienen las rutas existentes bajo `/app`; son rutas de interfaz, no prueba de integración. Cada ruta protegida usa autenticación y el permiso efectivo correspondiente.

```text
/auth/login                         Login
/access-denied  /not-found          Errores
/app                                Redirección según permisos
  /dashboard                        Resumen y gráficos
  /users                            Lista; /new, /:userId, /:userId/attendances
  /purchase-orders                  Lista; /new, /:orderId, /:orderId/edit
  /purchase-orders/:orderId/attendances/new   Primera atención
  /vouchers                         Lista; /:voucherId
  /vouchers/:voucherId/attendances/new        Atención posterior
  /attendant/workspace              Búsqueda y despacho
  /attendant/attendances            Historial propio
  /attendances                      Historial general
  /attendances/pending-verification Bandeja
  /attendances/:attendanceId        Detalle y revisión
  /balances                         Consulta de saldos
  /reports                          Catálogo; /purchase-orders, /attendances
```

Revisar el guard de `/attendances/:attendanceId`: actualmente exige `vouchers.verify`, por lo que no cubre el detalle de lectura general o propia. Definir autorización por acción y alcance antes de reutilizarlo. La ruta específica `pending-verification` debe preceder a la ruta con parámetro. El destino inicial será dashboard si tiene `reports.read` y espacio operativo para quien solo tenga `attendances.create`.

## 3. Menú del sidebar (agrupado, con roles)

Propuesta de una configuración compartida con etiqueta, ruta, icono, permiso y grupo; el sidebar la filtra mediante permisos devueltos por la sesión. Las rutas y acciones mantienen guards y comprobaciones propias. Los grupos pueden plegarse y deben funcionar en móvil y con teclado.

| Grupo | Entrada | Ruta | Permiso | Roles según política actual |
|---|---|---|---|---|
| Inicio | Panel principal | `/app/dashboard` | `reports.read` | ADMIN, OFFICE |
| Operaciones | Órdenes de compra | `/app/purchase-orders` | `purchase_orders.read` | ADMIN, OFFICE, ATTENDANT* |
| Operaciones | Vales | `/app/vouchers` | `vouchers.read` | ADMIN, OFFICE, ATTENDANT* |
| Operaciones | Espacio de atención | `/app/attendant/workspace` | `attendances.create` | ADMIN, ATTENDANT |
| Operaciones | Mis atenciones | `/app/attendant/attendances` | `attendances.read_own` | ADMIN, ATTENDANT |
| Operaciones | Atenciones | `/app/attendances` | `attendances.read_all` | ADMIN, OFFICE |
| Operaciones | Saldos | `/app/balances` | `balances.read` | ADMIN, OFFICE, ATTENDANT* |
| Oficina | Verificación | `/app/attendances/pending-verification` | `vouchers.verify` | ADMIN, OFFICE |
| Herramientas | Reportes | `/app/reports` | `reports.read` | ADMIN, OFFICE |
| Administración | Usuarios | `/app/users` | `users.manage` | ADMIN |

\* La presentación y consulta del grifero requieren DTOs y alcance operativo sin información financiera. El sidebar actual es plano: la agrupación es trabajo pendiente. El menú actual vincula «Atenciones» a `attendances.create` aunque la ruta requiere `attendances.read_all`; corregir esa diferencia en F1.

## 4. Bloques de implementación (cada uno termina verificable)

### F0 — Contrato y preparación

**Comprobación 17/11/2026:** `/api/v1/health/ready` respondió HTTP 200 con base disponible; CORS permitió `http://localhost:4200`, `/auth/me` sin sesión respondió 401 y las cuatro cuentas de desarrollo completaron login y logout. La consulta por rol devolvió 403 al grifero para usuarios, reportes y verificación, y a oficina para usuarios. El grifero recibió órdenes y vales sin campos financieros; su historial de vales quedó limitado a sus propias atenciones. Se corrigieron correos ficticios inválidos del seed que causaban HTTP 500 en usuarios.

**Calidad:** suite frontend 17 pruebas aprobadas, suite backend 32 pruebas aprobadas y Ruff sin errores; build Angular exitoso con aviso de presupuesto inicial de 207 bytes. La creación de atenciones, los saldos y el alcance por sede aún requieren los contratos y pruebas indicados abajo.

**Revisión adicional 17/11/2026:** suite backend 46 pruebas aprobadas con PostgreSQL. Una prueba HTTP transaccional comprueba creación parcial para grifero, respuesta operativa, saldos, reintento idempotente y atención posterior; usa una identidad autenticada simulada. El router no restringe automáticamente las consultas por sede y la creación registra la sede del actor sin exigir que coincida con la orden. Falta decidir y verificar la política de sede, además del historial multiusuario por HTTP y los contratos faltantes descritos en `docs/API_INTEGRATION.md`. F0 permanece abierta.

- [x] Contrastar estáticamente routers, esquemas, permisos y errores; documentar contrato en `docs/API_INTEGRATION.md`.
- [ ] Resolver con backend DTOs operativos sin precios, consultas e historial de atenciones, saldos y demás diferencias de §5. Comprobar permisos y alcance por sede/usuario con respuestas reales.
- [x] Preparar y verificar PostgreSQL, API, datos de desarrollo y cuentas de los tres roles sin registrar credenciales reales en el repositorio. Los pasos de preparación están documentados en `docs/API_INTEGRATION.md` y `backend-station/README.md`.
- **Entregable:** matriz de contrato con diferencias y responsables; cada bloqueo asignado al flujo afectado.
- **Verificación:** contrastar catálogo contra routers y respuestas reales con API y base disponibles.

### F1 — Sesión, navegación y componentes base

**Comprobación 17/11/2026:** pruebas HTTP simuladas cubren login y logout, y la suite verifica permisos del menú. Las constantes de almacenamiento y rate limit añadidas están reservadas y no activan persistencia, refresh ni protección del servidor.

**Avance adicional:** pruebas automatizadas de guards verifican redirección sin sesión y acceso por permisos para ADMIN, OFFICE y ATTENDANT. Las cuatro cuentas de desarrollo completaron login, `/auth/me`, logout y revocación HTTP real. Quedan pendientes los recorridos visuales en navegador, validación de componentes con datos reales y las brechas de contrato de F0; estas pruebas no constituyen una verificación completa de interfaz.

**Pruebas adicionales 17/11/2026:** la suite Angular pasó con 20 pruebas, incluyendo reintento y carga de la tabla y sincronización del input con formularios; la suite backend pasó con 32 pruebas. La navegación visual, la expiración observada en navegador y la validación de los demás componentes con consumidores reales siguen pendientes.

- [x] Implementar manejo de expiración, 401/403, logout y redirección por permiso; documentar sesión en memoria y recarga. Pendiente verificación con API real.
- [x] Corregir permiso del menú de atenciones, agrupar navegación y proteger el menú móvil cerrado frente al foco. Pendiente recorrido manual de accesibilidad, responsive y rutas directas por rol.
- [ ] Validar `data-table`, `page-header`, alertas, botones, formularios, modal y carga de archivos con consumidores reales; verificar carga, vacío, error, reintento y paginación. Se ajustó el mensaje vacío genérico de la tabla.
- **Entregable:** cada rol inicia sesión y navega solo a sus opciones autorizadas.
- **Verificación:** login inválido/válido, expiración, cierre, recarga, URL directa y menú de los tres roles.

### F2 — Usuarios y catálogos

**Avance 17/11/2026:** lista, detalle, alta, edición de nombre, cambio de rol y estado conectados; formularios muestran errores y sedes activas. Dos pruebas HTTP contra PostgreSQL, ejecutadas en transacción revertida, verificaron alta, duplicados, detalle, edición, rol, deshabilitación, reactivación y 403 a oficina. Dos pruebas unitarias comprueban la protección del último administrador. Suite Angular: 20 pruebas aprobadas. Falta el recorrido visual completo por rol, probar catálogos vacíos con consumidores y el historial del grifero cuando exista su contrato.

- [x] Integrar lista paginada, alta, detalle, edición permitida, cambio de rol y estado con `/users`; manejar errores de duplicidad y reglas del último administrador.
- [ ] Cargar sedes y combustibles desde `/branches` y `/fuel-types`; aplicar validaciones de formulario y permisos reales.
- [ ] Enlace a historial de un grifero solo cuando exista contrato de lectura de atenciones.
- **Entregable:** ADMIN administra cuentas y puede seleccionar catálogos reales en formularios.
- **Verificación:** alta, edición, deshabilitación, duplicados, acceso denegado y catálogos vacíos.

### F3 — Órdenes y OCR

**Avance 17/11/2026:** lista con búsqueda, sede, fechas, ordenación y paginación; detalle, alta, edición, baja y previsualización OCR conectados. Pruebas HTTP con PostgreSQL en transacción revertida verificaron alta con dos combustibles, filtros, edición, baja y conflicto de orden con vale. Se corrigió la verificación de baja para comprobar la existencia del vale. Un PDF generado con texto verificó extracción y revisión manual; se probó el límite de tamaño. Los contratos operativos omiten datos financieros para el grifero. OCR de PDF escaneados sigue pendiente: el entorno Python 3.13 no pudo instalar `rapidocr_onnxruntime==1.4.4`; se requiere resolver la dependencia compatible y probar documentos escaneados reales. Falta recorrido integral de interfaz y alcance por sede/usuario.

**Pruebas adicionales:** la validación de líneas duplicadas detectó un error de serialización en la respuesta 422; fue corregido y comprobado. Suite Angular: 22 pruebas aprobadas; suite backend con pruebas reversibles: 40 aprobadas; Ruff sin errores. Build correcto con advertencia de presupuesto inicial de 429 bytes.

- [ ] Conectar listado, búsqueda, filtros y paginación soportados, detalle, alta, modificación y baja permitida de órdenes; editar líneas por combustible y reflejar conflictos del backend.
- [ ] Procesar PDF mediante OCR, mostrar candidatos y permitir corrección antes de enviar el formulario normal; mostrar error y límites proporcionados por contrato.
- [ ] Aplicar permisos por acción y bloquear eliminación cuando el servidor informe vales asociados. Separar respuesta operativa de la financiera.
- **Entregable:** ADMIN/OFFICE registran y consultan una orden real, manualmente o con prellenado OCR.
- **Verificación:** varias líneas, duplicados, límites de PDF, corrección OCR, fallo de API y conflicto de eliminación.

### F4 — Despacho y saldos

**Avance:** búsqueda de órdenes y vales conectada al espacio operativo. El contrato de primera atención separa `voucher_items` autorizados de `items` despachados; una prueba PostgreSQL con rollback verificó entrega parcial, reintento, entrega posterior y exceso. El servidor serializa los reintentos por clave. Faltan el formulario conectado y recuperación tras recarga, pruebas concurrentes reales, historial y resolución del alcance por sede; F4 permanece abierta.

- [ ] Integrar búsqueda operativa de orden/vale y saldos seguros; capturar vale y primer despacho, o registrar despacho posterior sobre el vale existente.
- [ ] Mantener un `Idempotency-Key` UUID por intento lógico de envío y reutilizarlo al reintentar el mismo contenido; evitar dobles envíos y mostrar el resultado confirmado por servidor.
- [ ] Refrescar saldos tras éxito y manejar 409, 422, red y concurrencia. No calcular saldos oficiales con decimales de JavaScript; conservar precisión según DTO.
- [ ] Implementar historial propio/general y detalle cuando sus endpoints y alcance estén disponibles. Los recursos `/balances` propuestos requieren confirmación o implementación backend.
- **Entregable:** ADMIN/ATTENDANT registran una primera atención y una posterior con saldos reales y trazabilidad.
- **Verificación:** parcial, completo, exceso, doble clic, reintento, conflicto concurrente, ámbito de usuario y ausencia de precios en respuesta del grifero.

### F5 — Vales y verificación administrativa

**Avance 17/11/2026:** lista por número y paginación, detalle, corrección descriptiva, conflicto de eliminación y bandeja conectados. El historial de revisiones se presenta desde las atenciones incluidas en `GET /vouchers/{id}`. Una prueba HTTP contra PostgreSQL con rollback verificó permisos de oficina, observación obligatoria, observado, verificado, conflicto por revisión repetida y por eliminación, corrección por administrador e invariabilidad del saldo. Pendiente recorrido completo en navegador y pruebas adicionales de duplicidad y concurrencia de verificaciones; F5 permanece abierta.

- [x] Integrar búsqueda y detalle de vales con sus datos disponibles, corrección descriptiva autorizada y conflicto de eliminación; no permitir cambios de cantidades despachadas.
- [x] Conectar bandeja real `/verifications/pending` y decisión por atención; exigir observación cuando corresponda y recargar el estado confirmado.
- [x] Integrar historial de verificaciones desde las atenciones del detalle del vale.
- **Entregable:** ADMIN/OFFICE revisan una atención y ADMIN corrige los campos descriptivos permitidos.
- **Verificación:** verificado, observado sin/con motivo, permisos, historial y saldos sin cambios por revisión.

### F6 — Dashboard, reportes y exportación

**Avance 17/11/2026:** dashboard con fechas, sede y agrupación; reportes de órdenes y atenciones con fechas y sede, carga, error, vacío y exportación PDF/XLSX usando la última consulta. La API no admite estado en los endpoints de exportación, por lo que la interfaz usa los filtros comunes. Una prueba PostgreSQL con rollback verificó filtros, intervalo inválido, firmas PDF/XLSX y 403 para ATTENDANT. Suite Angular: 24 pruebas. Falta verificar los archivos descargados y el recorrido en navegador con datos reales; F6 permanece abierta.

- [x] Consumir `/reports/dashboard` y reportes reales, con filtros compatibles y gráficos Chart.js basados en los datos devueltos.
- [x] Descargar PDF/XLSX con parámetros admitidos por cada exportación; conservar filtros comunes y comunicar aquellos que el endpoint no soporte.
- **Entregable:** ADMIN/OFFICE consultan indicadores y descargan ambos reportes.
- **Verificación:** rango inválido, sin resultados, filtros, archivos descargados y 403 para ATTENDANT.

### F7 — Integración integral y entrega

- [ ] Revisar estados de carga/error, foco, navegación con teclado, vista móvil y autorización directa por ruta y acción.
- [ ] Ejecutar build, pruebas de servicios/formularios y recorridos integrales de los tres roles contra backend y datos controlados; registrar evidencias y defectos.
- [ ] Documentar configuración de API, despliegue SPA y fallback de rutas conforme a la infraestructura acordada; no colocar secretos en Angular.
- **Entregable:** recorrido completo de orden → despacho → verificación → reporte, con criterios de seguridad y contrato cumplidos.
- **Verificación:** build de producción, pruebas pertinentes y aprobación funcional con evidencia.

**Avance de verificación, 17/11/2026:** `npm test -- --watch=false`: 24 pruebas aprobadas; `npm run build`: compilación correcta con advertencia de presupuesto inicial (500,43 kB frente a 500 kB). Backend: 46 pruebas aprobadas con `SANJOSE_RUN_DB_TESTS=1` y `ruff check app tests` correcto. En navegador local se comprobó inicio y cierre de sesión para administrador, oficina y grifero, sus menús y el panel con datos reales para los dos primeros. La configuración y el fallback SPA están documentados en `docs/FRONTEND_OPERATIONS.md`.

**Pendiente para cerrar F7:** implementar el registro de atenciones de F4 y verificar el recorrido orden → despacho → verificación → reporte; completar pruebas de autorización por ruta y acción, teclado, foco, móvil y estados de error, así como obtener aprobación funcional. Los accesos probados no sustituyen estas verificaciones.

## 5. Referencia rápida API ↔ frontend ↔ rol

Prefijo común `/api/v1`. «Código» indica router presente en el repositorio, no que el flujo haya sido validado. `A` = ADMIN, `O` = OFFICE, `T` = ATTENDANT.

| API | Pantalla / bloque | Roles según permisos actuales | Estado / dependencia |
|---|---|---|---|
| `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` | Login y sesión F1 | A/O/T | Código; servicio Angular existente. |
| `GET/POST /users`, `GET/PATCH /users/{id}`, `PATCH /users/{id}/role`, `PATCH /users/{id}/status` | Usuarios F2 | A | Código; integrar y validar. |
| `GET /branches`, `GET /fuel-types` | Formularios F2–F4 | A/O/T autenticados | Código; validar alcance real. |
| `GET/POST /purchase-orders`, `GET/PATCH/DELETE /purchase-orders/{id}` | Órdenes F3 | A/O; T lectura operativa | Código; DTO financiero del grifero es bloqueo. |
| `GET /vouchers`, `GET /vouchers/{id}`, `PATCH /vouchers/{id}/descriptive-data`, `DELETE /vouchers/{id}` | Vales F5 | Lectura A/O/T; corrección A; eliminación A/O según permiso | Código; confirmar límites de seguridad y reglas de negocio. |
| `POST /purchase-orders/{id}/attendances`, `POST /vouchers/{id}/attendances` | Despacho F4 | A/T | Código; requiere cabecera `Idempotency-Key` UUID. |
| `GET /verifications/pending`, `POST /attendances/{id}/verifications` | Verificación F5 | A/O | Código; difiere de la bandeja propuesta en plan backend. |
| `GET /reports/dashboard`, `GET /reports/purchase-orders`, `GET /reports/attendances` | Dashboard y reportes F6 | A/O | Código; dashboard difiere de `/dashboard` propuesto. |
| `GET /reports/purchase-orders/export`, `GET /reports/attendances/export` | Descarga F6 | A/O | Código; `format=pdf` o `xlsx`; revisar filtros por endpoint. |
| `POST /ocr/purchase-order-previews` | Formulario de orden F3 | A/O | Código; multipart PDF, validar configuración. |
| `GET /attendances`, `GET /attendances/{id}`, historial de usuario, `GET /attendances/{id}/verifications`, `/balances/*` | Historial, detalle, saldos F4–F5 | Según contrato pendiente | Propuestos en plan backend; no aparecen como rutas dedicadas en los routers examinados. Confirmar alternativas o implementar en backend. |

## 6. Control de acceso por rol

| Capacidad | ADMIN | OFFICE | ATTENDANT |
|---|---|---|---|
| Usuarios y roles | Administrar | — | — |
| Órdenes | Consultar y gestionar | Consultar y gestionar | Lectura operativa sin datos financieros |
| Vales | Consultar, corrección descriptiva | Consultar | Consulta necesaria para atención |
| Atención | Registrar y consultar según permisos | Consultar todas | Registrar y consultar propias |
| Verificación | Sí | Sí | — |
| Saldos | Sí | Sí | Solo operativos, sujetos al contrato seguro |
| Reportes, dashboard, exportación y OCR | Sí | Sí | — |

`AuthStore` expone permisos de sesión y los guards protegen rutas; completar la protección de cada acción y sus estados de error. El backend debe volver a validar rol, propiedad, sede y datos devueltos en cada solicitud. La política actual incluye `vouchers.delete` para ADMIN/OFFICE; el servicio determina si la operación está permitida por las reglas del vale. Resolver las diferencias de nomenclatura entre los planes y `backend-station/app/core/permissions.py` usando los permisos efectivamente devueltos por la API.

## 7. Estructura de menús por rol

### 7.1 Administrador

Panel principal; Operaciones: órdenes, vales, espacio de atención, mis atenciones, atenciones y saldos; Oficina: verificación; Herramientas: reportes; Administración: usuarios. Sus acciones de despacho quedan registradas a su nombre.

### 7.2 Oficina

Panel principal; Operaciones: órdenes, vales, atenciones y saldos; Oficina: verificación; Herramientas: reportes. No se muestra creación de atenciones ni administración de usuarios.

### 7.3 Grifero

Operaciones: espacio de atención, mis atenciones y consultas de órdenes, vales y saldos necesarias para el despacho. Esas consultas se habilitan solo con respuestas y alcance seguros. No incluir precios, importes, verificación, reportes ni administración.

### 7.4 Criterio de cierre

Cada entrada debe llevar a una pantalla funcional o indicar claramente que está pendiente durante el desarrollo. Antes de liberar, comprobar menú, acceso directo, acciones y respuestas de red por cada rol, y registrar evidencia de los bloques F0–F7.
