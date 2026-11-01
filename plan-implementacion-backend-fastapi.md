# Plan de implementación del backend (FastAPI, PostgreSQL y OCR con RapidOCR)

**Proyecto:** Sistema web con OCR para la gestión de combustible institucional, estación de servicio San José, Abancay
**Documento complementario de:** `requerimientos-funcionales-sistema.md` (v3.0) y del frontend en Angular 21
**Versión del plan:** 4.0 (alineado a requerimientos v3.0; FastAPI, Angular 21.2.0, RapidOCR, JWT y tres roles)
**Fecha de corte del estado:** 30 de octubre de 2026

**Cómo usar este archivo:** cada tarea es una casilla. Al terminarla, cambia `- [ ]` por `- [x]`. Una fase se cierra solo cuando pasa su **Verificación**. Cada fase termina en algo **navegable** (la documentación interactiva de la API en `/docs`, y luego las pantallas de Angular) y **verificable** (pruebas automáticas y un recorrido ejecutable con datos reales).

<a id="indice"></a>

## Índice

1. [Decisiones técnicas y restricciones](#s1)
2. [Estado actual y tablero de avance](#s2)
3. [Estructura de carpetas](#s3)
4. [Convenciones de la API](#s4)
5. [Catálogo de endpoints](#s5)
6. [Fases de implementación](#s6)
   - [Fase 0. Entorno y repositorio](#f0)
   - [Fase 1. Esqueleto FastAPI, PostgreSQL y migraciones propias](#f1)
   - [Fase 2. Autenticación, sesiones y auditoría base](#f2)
   - [Fase 3. Usuarios, roles y permisos](#f3)
   - [Fase 4. Configuración, combustibles y precios](#f4)
   - [Fase 5. Instituciones y órdenes de compra](#f5)
   - [Fase 6. Vales: emisión y vales de entidad](#f6)
   - [Fase 7. Consumos y correcciones](#f7)
   - [Fase 8. Auditoría e integridad de saldos](#f8)
   - [Fase 9. Motor OCR con RapidOCR](#f9)
   - [Fase 10. Dataset y evaluación del OCR](#f10)
   - [Fase 11. API de lectura OCR](#f11)
   - [Fase 12. Consultas, reportes y exportación](#f12)
   - [Fase 13. Integración con Angular y pruebas integrales](#f13)
   - [Fase 14. Despliegue sin Docker y respaldo](#f14)
7. [Decisiones pendientes y supuestos por defecto](#s7)
8. [Cobertura de requerimientos](#s8)

---

<a id="s1"></a>

## 1. Decisiones técnicas y restricciones

**Autenticación requerida:** reCAPTCHA v3 validado desde el backend (token, acción, hostname y umbral configurable); JWT de acceso de vida corta; refresh tokens aleatorios, almacenados como hash, rotatorios y revocables. La configuración, secretos y endpoints quedan fuera del control del cliente. JWT, hashing compatible, configuración y RapidOCR figuran como dependencias explícitas en `backend/pyproject.toml`, con versiones fijadas.

**Roles:** Administrador (todos los permisos), Oficina (operación, OCR, vales y reportes) y Despachador (consulta operativa mínima y registro de consumos). Toda ruta protegida declara permiso; ocultar módulos en Angular nunca sustituye autorización en API.

**Varias estaciones:** todas apuntan a la misma base de datos/API central. Consumo es transaccional, bloquea el saldo del vale, usa idempotency key e identifica `estacion_id`; una consulta posterior desde cualquier sede ve el saldo confirmado. Para actualización proactiva se contempla SSE/WebSocket; el primer alcance puede refrescar al consultar y sondear cada pocos segundos.

**Arquitectura.** Aplicación monolítica en un solo repositorio y un solo proceso en producción:
- **Backend:** FastAPI (Python 3.11 o superior) con PostgreSQL 16 o superior. Contiene la API, las reglas de negocio y el motor de OCR (RapidOCR).
- **Base de datos:** PostgreSQL con `pgAdmin 4` como herramienta de administración (crear bases y roles, ejecutar consultas, revisar tablas y respaldar). `pgAdmin` es un cliente: el servidor PostgreSQL debe estar instalado y corriendo como servicio.
- **Frontend:** Angular 21.2.0 (aplicación de una sola página). En producción se compila a archivos estáticos y los sirve el propio FastAPI, de modo que hay **un solo origen** (sin problemas de CORS y con cookies simples). En desarrollo, `ng serve` hace de proxy hacia FastAPI.

**Restricciones acordadas y cómo se cumplen:**
- **Sin SSR:** Angular se compila como aplicación de navegador; no hay renderizado en servidor ni hidratación.
- **Sin PWA:** no hay service worker ni manifiesto; el servidor controla la caché con cabeceras HTTP.
- **Sin state manager externo:** el estado de la interfaz usa las señales (`signal`) de Angular y la URL; la fuente de verdad es la API.
- **Sin librerías nuevas no autorizadas:** en Angular, además de los paquetes de un proyecto nuevo (núcleo, router, formularios, `HttpClient`, RxJS, compilación y pruebas), solo se autorizan PrimeNG 21 con `@primeuix/themes` y `primeicons`, `iconify-icon`, `chart.js` y Tailwind 4; no se agregan Angular Material, NgRx ni librerías de PDF. En el backend, la lista de dependencias es **cerrada** (ver abajo).
- **Sin Docker:** instalación nativa de Python, PostgreSQL, pgAdmin 4, RapidOCR y Node. Los procesos se lanzan con comandos de la propia herramienta.
- **Sin Redis:** refresh tokens revocables, límites de intentos, secuencias y notificaciones entre instancias (`LISTEN/NOTIFY`) viven en PostgreSQL.
- **Sin Celery ni workers externos:** no hay colas ni procesos auxiliares. La lectura OCR se ejecuta dentro de la petición (en el pool de hilos de FastAPI), con límite de concurrencia y de tiempo. Las tareas periódicas son comandos (`python -m app.cli ...`) que también se pueden ejecutar desde un endpoint a demanda; programarlas con `APScheduler` en la aplicación; se evita iniciar más de una instancia del scheduler por despliegue.
- **Sin Alembic:** la estructura de PostgreSQL se versiona con archivos SQL numerados y un ejecutor propio (Fase 1). SQLAlchemy se usa solo para consultar, nunca para crear tablas.
- **Sin extensiones de PostgreSQL:** no se instalan `pgvector`, `citext`, `unaccent` ni similares; el sistema no usa búsqueda vectorial y todo se resuelve con tipos y funciones estándar.

**Dependencias del backend (lista cerrada).** Cualquier otra requiere una decisión explícita.
- **API y validación:** `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `python-multipart`, `websockets`, `httpx`.
- **Persistencia:** `sqlmodel`, `sqlalchemy[asyncio]` y `asyncpg` para PostgreSQL asíncrono; URL `postgresql+asyncpg://`.
- **Autenticación y correo:** `pwdlib[argon2]`, `pyjwt`, `email-validator`, `aiosmtplib`; `httpx` valida reCAPTCHA v3 desde el servidor.
- **Procesamiento y tareas:** `rapidocr==3.10.0` con `onnxruntime`, `numpy`, `opencv-python-headless`, `pdfplumber` y `pypdfium2`; `apscheduler` para tareas programadas; `sse-starlette` para avisos SSE entre sedes.
- **Archivos y reportes:** `openpyxl` para Excel, `reportlab` para PDF y `boto3` para almacenamiento compatible con S3.
- **Desarrollo y verificación:** `pytest`, `pytest-asyncio` y `ruff`.
- Las versiones exactas instalables están declaradas en `backend/pyproject.toml` (`[project] dependencies` y el extra `dev`) y se instalan con `pip install -e ".[dev]"`. Se usa la compilación headless de OpenCV en servidor; no se instala también `opencv-python`, pues ambos distribuyen el mismo módulo `cv2`.

**Lo que se resuelve sin librería (y por qué):**
- **Contraseñas:** `pwdlib[argon2]`.
- **JWT y refresh tokens:** usar biblioteca mantenida (por ejemplo `pyjwt`) para firmar/verificar access JWT. Refresh tokens opacos aleatorios se guardan como hash en PostgreSQL, rotan y se revocan por sesión/familia. Las cuentas desactivadas y los cambios de contraseña invalidan refresh tokens; los access JWT vencen en pocos minutos.
- **Protección CSRF:** obligatoria si refresh/access se transportan en cookies; con access token en cabecera Authorization, aplicar CORS estricto, HTTPS y políticas de origen.
- **Correo de recuperación (P-08):** `aiosmtplib`.
- **Excel (.xlsx):** `openpyxl` (RF-REP-07).
- **PDF (vales, comprobantes y reportes):** `reportlab` para generar PDF en el backend.
- **Numeración de vales:** no se usa código de barras ni QR. Los vales de la estación conservan la numeración propia de San José; los vales de entidad conservan la numeración que les asigna cada institución. Para entidades con reinicio por orden, el número puede repetirse en órdenes distintas; para numeración general, es único por institución.
- **Migraciones, CLI y configuración:** ejecutor propio, `argparse` y variables de entorno.

**Decisiones de diseño con impacto en la exactitud de saldos:**
- **Saldo derivado de movimientos.** Cada movimiento guarda su variación con signo (positiva en emisión y reversión; negativa en consumo y anulación; con signo en ajuste). El saldo de un vale es la suma de sus variaciones y se verifica a diario (RN-05, RN-08).
- **Bloqueo de fila y aislamiento `READ COMMITTED`.** Todo cambio de saldo bloquea el vale con `SELECT ... FOR UPDATE` dentro de una transacción. El motor usa `READ COMMITTED` para que lecturas posteriores al bloqueo vean siempre lo último confirmado.
- **Idempotencia.** Cada consumo lleva un `token_operacion` (UUID generado por Angular) con índice único: un reenvío devuelve el movimiento original (RF-CON-09).
- **Dinero con `Decimal`.** Nunca `float`. Redondeo a 2 decimales, mitad hacia arriba. Los montos viajan como cadena en el JSON.
- **Zona horaria de Lima.** Lima no tiene horario de verano; se usa un desfase fijo de UTC-5 (sin depender de bases de zonas horarias). Los movimientos guardan además `fecha_local` (DATE) para agrupar por día, semana y mes.
- **Movimientos y bitácora inalterables.** Control principal por permisos de PostgreSQL: el rol de la aplicación solo tiene `SELECT` e `INSERT` sobre esas tablas (sin `UPDATE`, `DELETE` ni `TRUNCATE`). Como defensa adicional, disparadores `BEFORE UPDATE OR DELETE` y `BEFORE TRUNCATE` que rechazan el cambio incluso para el rol dueño.
- **Dos roles de PostgreSQL.** `vales_migrador` (dueño de la estructura y los disparadores) para el ejecutor de migraciones y `vales_app` (permisos mínimos) para la aplicación. Las bases y los roles se pueden crear desde `pgAdmin`; las migraciones siempre se aplican con el comando del proyecto, para que la estructura quede versionada. Cada migración concede a `vales_app` los permisos de tabla que correspondan y `USAGE` sobre las secuencias de identidad (`bigint GENERATED ... AS IDENTITY`).

**Fuera de este plan:** los instrumentos de la tesis (encuestas, mediciones para el estudio y selección de la muestra), igual que en la especificación de requerimientos.

---

<a id="s2"></a>

## 2. Estado actual y tablero de avance

### 2.1 Estado actual del proyecto

Documentación y diseño:
- [x] Ficha metodológica de la tesis
- [x] Especificación de requerimientos funcionales v3.0 (roles Oficina/Despachador y autenticación con reCAPTCHA/JWT)
- [x] Decisiones D-01 (soles y galones con precio vigente) y D-02 (vales de entidad vinculados a una orden)
- [x] Stack definido: Angular 21, FastAPI, PostgreSQL y OCR con RapidOCR
- [x] Restricciones definidas (sin SSR, PWA, state manager, librerías nuevas, Redis, Celery, workers, Alembic, extensiones de PostgreSQL ni Docker)
- [x] Planes anteriores basados en Laravel y Livewire (reemplazados por este plan)
- [ ] Plan de frontend en Angular 21 (complemento de este plan)
- [ ] Puntos por confirmar con la estación (sección 7)
- [ ] Órdenes de compra reales de ejemplo (30 a 50, anonimizadas) para el OCR

Implementación:
- [x] Repositorio creado
- [x] Base de datos PostgreSQL creada y visible en pgAdmin 4
- [x] Esquema inicial `backend/db/schema.sql` y seed de desarrollo `backend/db/seed.sql` con tablas, tipos enum y numeración de vales diferenciada
- [x] Entry point FastAPI, configuración, sesión asíncrona y endpoint básico de salud (`/api/v1/salud`)
- [x] Servicio FastAPI levantado y verificado (Fase 1)
- [x] RapidOCR instalado

### 2.2 Tablero de fases

Avance global: **2 de 15 fases cerradas**. La Fase 1 cerró el 31/10/2026: ejecutor de migraciones con checksum y línea base, migración `0001_base.sql`, manejo de errores estándar, `core/dinero.py`, `core/tiempo.py`, `GET /catalogos/enums`, `cli.py`, `tests/conftest.py`, pruebas de sistema/dinero/tiempo y `scripts/smoke.py --hasta 1` en verde.

La Fase 3 (01/11/2026) agregó `core/permisos.py` (matriz rol → permisos), `requiere_permiso`, el módulo completo `GET/POST/PATCH /usuarios`, `POST /usuarios/{id}/restablecer-password`, la protección del último administrador y la prueba global de autorización que recorre `app.routes`; 53 pruebas en verde (14 nuevas en `tests/test_usuarios.py`) y Ruff limpio.

- [x] **Fase 0** Entorno y repositorio (inicio: 31/10/2026 / fin: 31/10/2026)
- [x] **Fase 1** Esqueleto FastAPI, PostgreSQL y migraciones propias (inicio: 31/10/2026 / fin: 31/10/2026) - [x] **Fase 2** Autenticación, sesiones y auditoría base (inicio: ____ / fin: 31/10/2026)
- [x] **Fase 3** Usuarios, roles y permisos (inicio: 31/10/2026 / fin: 01/11/2026; smoke `--hasta 3` pendiente solo del ajuste de permisos de la base de desarrollo, ver `backend/db/permisos-dev-fix.sql`)
- [ ] **Fase 4** Configuración, combustibles y precios (inicio: ____ / fin: ____)
- [ ] **Fase 5** Instituciones y órdenes de compra (inicio: ____ / fin: ____)
- [ ] **Fase 6** Vales: emisión y vales de entidad (inicio: ____ / fin: ____)
- [ ] **Fase 7** Consumos y correcciones (inicio: ____ / fin: ____)
- [ ] **Fase 8** Auditoría e integridad de saldos (inicio: ____ / fin: ____)
- [ ] **Fase 9** Motor OCR con RapidOCR (inicio: ____ / fin: ____)
- [ ] **Fase 10** Dataset y evaluación del OCR (inicio: ____ / fin: ____)
- [ ] **Fase 11** API de lectura OCR (inicio: ____ / fin: ____)
- [ ] **Fase 12** Consultas, reportes y exportación (inicio: ____ / fin: ____)
- [ ] **Fase 13** Integración con Angular y pruebas integrales (inicio: ____ / fin: ____)
- [ ] **Fase 14** Despliegue sin Docker y respaldo (inicio: ____ / fin: ____)

### 2.3 Orden y dependencias

1. Fases 0 a 4 son la base: entorno, esqueleto, acceso, usuarios y catálogos.
2. Fases 5 a 8 forman el núcleo y ya reemplazan al Excel (sin OCR): órdenes, vales, consumos e integridad.
3. Fases 9 y 10 (motor y evaluación del OCR) no dependen de la base de datos: se pueden hacer en paralelo con las fases 2 a 8.
4. La Fase 11 necesita la Fase 5 (órdenes) y la Fase 9 (motor).
5. La Fase 12 necesita la Fase 7 (consumos).
6. Las fases 13 y 14 cierran.

**Cómo se complementa con Angular.** Cada fase indica qué pantallas de Angular habilita. Angular puede avanzar una fase detrás del backend, siempre sobre datos reales y nunca sobre datos simulados.

---

<a id="s3"></a>

## 3. Estructura de carpetas

### 3.1 Raíz del repositorio

```
station-jose/                        # raíz del repositorio
├── README.md
├── .gitignore
├── angular.json  package.json  tsconfig*.json   # proyecto Angular en la raíz
├── src/  public/                                # Angular 21 (detalle en el plan de frontend)
└── backend/                         # FastAPI, PostgreSQL y OCR
```

### 3.2 Backend (FastAPI) dentro de `backend/`

Sigue las prácticas oficiales de FastAPI: CLI `fastapi dev` y `fastapi run`, entrypoint declarado en `pyproject.toml`, parámetros y dependencias con `Annotated`, y organización por capas (routers delgados, esquemas Pydantic, servicios con la lógica) según la guía "Bigger Applications".

```
backend/
├── pyproject.toml                    # dependencias, [tool.fastapi] entrypoint, pytest y ruff
├── .env.example                      # variables de entorno (sin secretos reales)
├── .gitignore                        # .venv/, .env, almacenamiento/, datos/documentos/
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py                       # instancia FastAPI, routers, errores y servicio del frontend
│   ├── config.py                     # Settings desde variables de entorno
│   ├── dependencies.py               # SesionBd, UsuarioActual, requiere_permiso, ProteccionCsrf
│   ├── errors.py                     # ErrorDominio, catálogo de códigos, manejadores
│   ├── cli.py                        # comandos: migrar, crear-admin, sembrar-demo, vencimientos, ...
│   ├── core/
│   │   ├── seguridad.py              # Argon2, JWT, refresh tokens, CSRF
│   │   ├── permisos.py               # roles y permisos (matriz de la sección 4.2 de los requerimientos)
│   │   ├── dinero.py                 # Decimal, redondeo, comparaciones
│   │   ├── tiempo.py                 # ahora en Lima, fecha local, rangos (hoy, semana, mes)
│   │   ├── archivos.py               # validación por contenido, almacenamiento privado
│   │   └── correo.py                 # aiosmtplib
│   ├── db/
│   │   ├── sesion.py                 # async_engine (READ COMMITTED), AsyncSessionLocal, get_db
│   │   ├── migrar.py                 # ejecutor de migraciones SQL
│   │   └── migraciones/              # 0001_base.sql, 0002_..., (solo hacia adelante)
│   ├── models/                       # SQLAlchemy, un archivo por dominio
│   │   ├── usuarios.py  instituciones.py  combustibles.py  ordenes.py
│   │   ├── vales.py     ocr.py            auditoria.py     configuracion.py
│   ├── schemas/                      # Pydantic de entrada y salida, por dominio
│   ├── routers/                      # un archivo por módulo
│   │   ├── sistema.py  auth.py  usuarios.py  configuracion.py  combustibles.py
│   │   ├── instituciones.py  ordenes.py  ocr.py  vales.py  consumos.py
│   │   ├── consultas.py  reportes.py  auditoria.py
│   ├── services/                     # reglas de negocio (una función por caso de uso)
│   │   ├── auth.py  usuarios.py  parametros.py  precios.py  instituciones.py
│   │   ├── ordenes.py  vales.py  consumos.py  numeracion.py  integridad.py
│   │   ├── consultas.py  reportes.py  auditoria.py  xlsx.py
│   │   └── ocr/
│   │       ├── lector.py             # tipo de archivo, texto digital, páginas a imagen
│   │       ├── preprocesado.py       # OpenCV: gris, ruido, inclinación, binarización
│   │       ├── rapidocr.py          # invocación por subprocess y lectura de TSV
│   │       ├── extractor.py          # reglas y anclas por etiqueta
│   │       ├── normalizador.py       # fechas, montos, RUC, combustible
│   │       └── pipeline.py           # orquestación y confianza por campo
│   └── web/
│       └── frontend.py               # servicio de archivos estáticos de Angular y respaldo a index.html
├── almacenamiento/                   # archivos privados (fuera del alcance web)
│   ├── ordenes/
│   └── estacion/
├── datos/                            # dataset del OCR (fuera de git si es sensible)
│   ├── documentos/
│   ├── verdad_terreno/
│   └── division.json
├── db/                               # esquema y datos iniciales, previos a las migraciones
│   ├── schema.sql                    # esquema completo en un solo archivo (idempotente)
│   └── seed.sql                      # catálogos de demostración (no producción)
├── informes/                         # resultados de evaluación del OCR
├── scripts/
│   ├── verificar_entorno.py
│   ├── smoke.py                      # recorrido de verificación por fase (--hasta N)
│   ├── probar_concurrencia.py
│   ├── evaluar_ocr.py
│   └── benchmark.py
└── tests/
    ├── conftest.py                   # base de pruebas PostgreSQL y cliente de pruebas
    ├── test_sistema.py  test_auth.py  test_usuarios.py  test_configuracion.py
    ├── test_combustibles.py  test_instituciones.py  test_ordenes.py
    ├── test_vales.py  test_consumos.py  test_integridad.py  test_auditoria.py
    ├── test_ocr_unidad.py  test_ocr_api.py  test_consultas.py  test_reportes.py
    └── fixtures/                     # documentos mínimos sin datos reales
```

**Implementado hasta ahora (cierre de Fase 1):** `pyproject.toml`, `.env.example`, `app/config.py`, `app/errors.py`, `app/cli.py`, `app/main.py`, `app/core/dinero.py`, `app/core/tiempo.py`, `app/core/permisos.py`, `app/core/dominio.py`, `app/db/sesion.py`, `app/db/migrar.py`, `app/db/migraciones/0001_base.sql`, `app/routers/sistema.py`, `app/routers/catalogos.py`, `app/schemas/sistema.py`, `db/schema.sql`, `db/seed.sql`, `scripts/crear_admin.py`, `scripts/verificar_entorno.py`, `scripts/smoke.py`, `tests/conftest.py`, `tests/test_sistema.py`, `tests/test_dinero.py` y `tests/test_tiempo.py`. Los demás módulos del árbol representan trabajo pendiente, no funcionalidades terminadas.

Nota sobre bases con esquema legacy (`usuarios`, `usuario_id`, `vales.codigo_interno`): el plan no convierte esquemas heredados automáticamente. Para esas bases, respaldar los datos necesarios, eliminar los objetos payload y aplicar las migraciones desde una base vacía; la base de pruebas se reconstruyó así al cerrar la Fase 1.

**Esquema inicial vigente:** las cuentas viven en `app_users` con los roles `administrador`, `oficina` y `despachador` (`user_role`). No hay columna `active` ni flujo para activar/desactivar cuentas. `must_change_password` admite `NULL`: solo `TRUE` obliga a cambiar la contraseña antes de usar los demás módulos; `FALSE` y `NULL` permiten el acceso normal. El seed asigna `NULL` a las tres cuentas de demo. `code` es un identificador opcional de la cuenta, por ejemplo un código interno de personal; no reemplaza el DNI ni el correo. No se almacena WhatsApp.

Los vales se identifican solo por números, sin código de barras ni QR: `numero_estacion` guarda la numeración propia de la estación; `numero_entidad` guarda la numeración asignada por una institución. `clave_numeracion` garantiza unicidad general por institución o reinicio de numeración por orden de compra. El `id` de PostgreSQL se usa como identificador relacional interno y no se imprime como numeración del vale.

`schema.sql` y `seed.sql` son scripts SQL directos, ejecutables desde pgAdmin o `psql`. `schema.sql` también ajusta una instalación previa de `app_users` quitando `active` y haciendo nullable `must_change_password`; no convierte otros esquemas heredados automáticamente. El seed incluye tres cuentas de demostración, una por rol, y datos vinculados a la cuenta de administrador. Antes de ejecutar, se deben reemplazar sus hashes Argon2id de ejemplo por hashes correspondientes a contraseñas conocidas.

---

<a id="s4"></a>

## 4. Convenciones de la API

- **Prefijo y formato.** Todo bajo `/api/v1`, en JSON. Excepciones: descargas de archivos y `.xlsx`.
- **Nombres.** Rutas en español y en plural (`/ordenes`, `/vales`). Acciones que no son un simple alta o cambio, como verbos en la ruta (`/ordenes/{id}/cerrar`).
- **Paginación.** `?pagina=1&por_pagina=15` (máximo 100). Respuesta: `{ "items": [...], "total": 120, "pagina": 1, "por_pagina": 15 }`.
- **Filtros y orden.** Parámetros de consulta con nombre explícito (`estado`, `desde`, `hasta`, `q`). Orden por defecto documentado en cada listado.
- **Dinero y cantidades.** Cadenas decimales (`"1500.00"`). Fechas en ISO 8601 (`2027-03-15`); instantes con desfase (`2027-03-15T10:30:00-05:00`).
- **Errores.** Siempre `{ "codigo": "SALDO_INSUFICIENTE", "mensaje": "...", "detalles": {...} }` con el estado HTTP adecuado: 400 petición inválida, 401 sin sesión, 403 sin permiso, 404 no existe, 409 conflicto de reglas o de estado, 413 archivo grande, 415 tipo no permitido, 422 validación de campos, 503 servicio ocupado o no disponible. El campo `detalles` de un 422 lista cada campo con su mensaje, para mostrarlo junto al campo.
- **Códigos de error del dominio:** `CREDENCIALES_INVALIDAS`, `CUENTA_BLOQUEADA`, `CAMBIO_PASSWORD_OBLIGATORIO`, `SESION_EXPIRADA`, `SIN_PERMISO`, `ULTIMO_ADMINISTRADOR`, `RUC_DUPLICADO`, `ORDEN_DUPLICADA`, `ORDEN_POSIBLE_DUPLICADA`, `ESTADO_INVALIDO`, `ORDEN_CON_CONSUMOS`, `SIN_PRECIO_VIGENTE`, `PRESUPUESTO_EXCEDIDO`, `NUMERO_ENTIDAD_DUPLICADO`, `NUMERO_FUERA_DE_SERIE`, `SERIE_AGOTADA`, `VALE_NO_CONSUMIBLE`, `SALDO_INSUFICIENTE`, `COMBUSTIBLE_DISTINTO`, `CONSUMO_YA_REVERTIDO`, `AJUSTE_NEGATIVO`, `ARCHIVO_NO_PERMITIDO`, `ARCHIVO_DEMASIADO_GRANDE`, `OCR_NO_DISPONIBLE`, `OCR_OCUPADO`, `DOCUMENTO_ILEGIBLE`, `EXTRACCION_NO_CONFIRMABLE`.
- **Autenticación.** Access JWT enviado como Bearer y guardado solo en memoria en Angular. Refresh token rotatorio en cookie HttpOnly, Secure y SameSite; proteger `/auth/refresh` y `/auth/logout` contra CSRF. Nunca almacenar tokens en localStorage ni exponer secretos reCAPTCHA al cliente.
- **Autorización.** Cada endpoint declara su permiso con `Depends(requiere_permiso("..."))`. Se valida en el servidor en cada petición.
- **Documentación.** `/docs` (Swagger) y `/openapi.json` solo en desarrollo.
- **Servicio del frontend.** Cualquier ruta que no empiece por `/api` devuelve el archivo de Angular si existe o `index.html` si no (rutas internas de la aplicación).

### 4.1 Permisos

Cadena de permiso, roles que lo tienen y requerimientos que lo originan (sección 4.2 de la especificación):

- `sesion`: cualquier usuario autenticado.
- `usuarios.gestionar`: Administrador.
- `instituciones.ver`, `ordenes.ver`, `vales.ver`, `consultas.ver`, `reportes.ver`, `catalogo.ver`, `estacion.ver`: Administrador y Oficina.
- `consumos.buscar`, `consumos.registrar`: Administrador, Oficina y Despachador; Despachador solo accede a datos mínimos del vale y al movimiento que registra.
- `instituciones.editar`, `ordenes.editar`, `ocr.usar`, `vales.emitir`, `historial.ver`: Administrador y Oficina.
- `instituciones.desactivar`, `catalogo.gestionar`, `ordenes.anular`, `vales.anular`, `vales.ajustar`, `consumos.revertir`, `auditoria.ver`, `ocr.historial`, `config.gestionar`: Administrador.

[↑ Volver al índice](#indice)

---

<a id="s5"></a>

## 5. Catálogo de endpoints

Todas las rutas van bajo `/api/v1`. Formato de cada línea: **método y ruta** · permiso · requerimientos que cubre · qué recibe y qué devuelve. "Recibe" lista lo principal; los esquemas completos salen de `/openapi.json`. Las pantallas de Angular se construyen solo contra estos endpoints.

### 5.1 Sistema

- `GET /eventos/vales/{vale_id}` · `consumos.buscar` · CON-14 · flujo SSE autenticado; emite un evento cuando cambia el saldo del vale. El cliente vuelve a consultar el saldo por REST y solo recibe notificaciones de vales autorizados. Los procesos publican eventos mediante PostgreSQL `LISTEN/NOTIFY` para que todas las instancias de la API distribuyan el cambio.
- `GET /salud` · público · estado de PostgreSQL y de RapidOCR, sin datos sensibles.
- `GET /catalogos/enums` · `sesion` · estados de orden, vale y extracción, tipos de movimiento, emisores, modalidades de numeración, tipos de institución, roles y permisos. Evita repetir esas listas en Angular.

### 5.2 Autenticación y sesión (M01)

- `POST /auth/login` · público · AUT-01, AUT-04 · recibe correo, contraseña y token reCAPTCHA v3; el backend verifica el token con Google, comprueba acción, hostname y score. Emite access JWT corto y refresh token opaco rotatorio.
- `POST /auth/refresh` · refresh válido · AUT-10 · invalida el token usado y devuelve access JWT y refresh nuevo; reutilización revoca la familia.
- `POST /auth/logout` · sesión autenticada · AUT-02 · revoca la familia de refresh tokens.
- `GET /auth/yo` · access JWT válido · AUT-07, AUT-08, AUT-09 · devuelve usuario, rol, permisos e indicador de cambio obligatorio (normaliza `must_change_password IS TRUE` como `true`; `NULL` y `false` como `false`).
- `POST /auth/recuperar` · público · AUT-05 · recibe `correo`; siempre responde con el mismo mensaje, exista o no el correo.
- `POST /auth/restablecer` · público · AUT-05, AUT-06 · recibe `token` y `password_nueva`; el token es de un solo uso y vence.
- `POST /auth/cambiar-password` · `sesion` (permitido aun con cambio obligatorio) · AUT-06, AUT-07 · recibe `password_actual` y `password_nueva` (mínimo 8 caracteres, distinta de la actual).
- No existe ninguna ruta de registro (AUT-03); una prueba automática lo verifica.

### 5.3 Usuarios (M02)

- `GET /usuarios` · `usuarios.gestionar` · USR-02 · filtros `q`, `rol`, paginación.
- `POST /usuarios` · `usuarios.gestionar` · USR-01 · recibe `nombre`, `correo`, `rol`; devuelve la contraseña temporal una sola vez.
- `GET /usuarios/{id}` · `usuarios.gestionar` · USR-02 · detalle.
- `PATCH /usuarios/{id}` · `usuarios.gestionar` · USR-03, USR-04 · cambia `nombre`, `correo` o `rol`; protege al último administrador.
- `POST /usuarios/{id}/restablecer-password` · `usuarios.gestionar` · USR-06 · devuelve una contraseña temporal una sola vez y establece `must_change_password = TRUE`.

### 5.4 Configuración (M12)

- `GET /configuracion/parametros` · `config.gestionar` · CFG-01 · cada parámetro con su valor, valor por defecto, tipo, rango y descripción.
- `PUT /configuracion/parametros` · `config.gestionar` · CFG-01 · recibe un conjunto de parámetros; valida tipo y rango; rige de inmediato; queda auditado.
- `GET /configuracion/estacion` · `estacion.ver` · CFG-02 · nombre, RUC, dirección; se usa en las vistas de impresión.
- `PUT /configuracion/estacion` · `config.gestionar` · CFG-02.
- `POST /configuracion/estacion/logo` · `config.gestionar` · CFG-02 · archivo PNG o JPG de hasta 1 MB, validado por contenido.
- `GET /configuracion/estacion/logo` · `estacion.ver` · CFG-02.

### 5.5 Combustibles y precios (M04)

- `GET /combustibles` · `catalogo.ver` · CMB-01, CMB-03 · filtro `activo`; incluye el precio vigente de cada uno.
- `POST /combustibles` · `catalogo.gestionar` · CMB-01 · recibe `nombre`.
- `PATCH /combustibles/{id}` · `catalogo.gestionar` · CMB-01 · cambia `nombre` o `activo`; un tipo en uso no se elimina.
- `GET /combustibles/{id}/precios` · `catalogo.ver` · CMB-03 · histórico del más reciente al más antiguo, con quién lo registró.
- `POST /combustibles/{id}/precios` · `catalogo.gestionar` · CMB-02 · recibe `precio_galon` y `vigente_desde`; no hay edición ni borrado de precios.
- `GET /combustibles/{id}/precio-vigente` · `catalogo.ver` · CMB-03 · parámetro `fecha` (por defecto hoy); `404` con `SIN_PRECIO_VIGENTE` si no hay.

### 5.6 Instituciones (M03)

- `GET /instituciones` · `instituciones.ver` · INS-03, OCR-08 · filtros `q`, `ruc` (exacto), `estado`, `tipo`, paginación.
- `GET /instituciones/ruc/{ruc}` · `instituciones.ver` · INS-01, OCR-08 · devuelve si el RUC es válido (11 dígitos y dígito verificador) y la institución existente si la hay, para la validación en vivo y el enlace a la existente.
- `POST /instituciones` · `instituciones.editar` · INS-01 · recibe nombre, RUC, tipo, teléfono, correo, dirección, representante y `modalidad_numeracion` (general, por_orden o no_aplica).
- `GET /instituciones/{id}` · `instituciones.ver` · INS-04 · datos y resumen (órdenes, saldo vigente y consumo del mes).
- `PATCH /instituciones/{id}` · `instituciones.editar` · INS-02 · el RUC solo cambia si no hay órdenes, o si lo hace el administrador.
- `POST /instituciones/{id}/desactivar` · `instituciones.desactivar` · INS-05.
- `POST /instituciones/{id}/reactivar` · `instituciones.desactivar` · INS-05.

### 5.7 Órdenes de compra (M05)

- `GET /ordenes` · `ordenes.ver` · ORD-05 · filtros `institucion_id`, `estado`, `desde`, `hasta`, `numero`, paginación; orden por fecha descendente.
- `GET /ordenes/posible-duplicado` · `ordenes.ver` · ORD-11 · parámetros `institucion_id`, `presupuesto_soles`, `fecha_emision`; devuelve la orden coincidente si existe.
- `POST /ordenes` · `ordenes.editar` · ORD-01, ORD-02, ORD-11, VAL-15 · recibe institución, número, fecha, presupuesto en soles, combustible opcional, serie opcional (`serie_desde` y `serie_hasta`), observaciones, `estado` (`borrador` o `vigente`) y `confirmar_duplicado`. Si hay una orden coincidente y no se confirmó, responde `409` con `ORDEN_POSIBLE_DUPLICADA` y el enlace a esa orden.
- `GET /ordenes/{id}` · `ordenes.ver` · ORD-06 · presupuesto, total emitido en soles y galones, presupuesto restante, consumo acumulado, vales con estado y saldo, estado y usuario.
- `PATCH /ordenes/{id}` · `ordenes.editar` · ORD-07 · sin vales se editan todos los campos; con vales, solo observaciones.
- `POST /ordenes/{id}/archivo` · `ordenes.editar` · ORD-03 · carga multipart; se valida por contenido (PDF, JPG o PNG) y por tamaño.
- `GET /ordenes/{id}/archivo` · `ordenes.ver` · ORD-04 · devuelve el documento en línea, solo a usuarios autorizados.
- `POST /ordenes/{id}/marcar-vigente` · `ordenes.editar` · ORD-08 · pasa de borrador a vigente.
- `POST /ordenes/{id}/cerrar` · `ordenes.editar` · ORD-10, ORD-08.
- `POST /ordenes/{id}/anular` · `ordenes.anular` · ORD-09 · recibe `motivo`; `409` con `ORDEN_CON_CONSUMOS` si tiene consumos.
- `GET /ordenes/{id}/serie` · `ordenes.ver` · VAL-15 · rango autorizado, números usados y números disponibles.

### 5.8 Lectura OCR (M06)

- `POST /ocr/extracciones` · `ocr.usar` · OCR-01, OCR-02, OCR-03, OCR-04, OCR-09 · recibe el archivo (multipart); lo lee dentro de la misma petición y devuelve la extracción con estado `lista` o `fallida`: cada campo con `valor`, `confianza` y `requiere_revision`, la institución sugerida por RUC, advertencias y el método de lectura (texto digital u OCR). Si el motor falla, devuelve la extracción `fallida` con el motivo y el archivo queda guardado.
- `GET /ocr/extracciones/{id}` · `ocr.usar` · OCR-02 · estado y resultado.
- `GET /ocr/extracciones/{id}/archivo` · `ocr.usar` · OCR-05 · documento original para el visor.
- `POST /ocr/extracciones/{id}/reintentar` · `ocr.usar` · OCR-10 · vuelve a leer sin subir el archivo.
- `POST /ocr/extracciones/{id}/confirmar` · `ocr.usar` · OCR-06, OCR-07, OCR-11 · recibe los valores finales y `datos_revisados: true`; valida igual que `POST /ordenes`, crea la orden marcada como registrada con OCR y guarda por campo lo extraído, lo final y si se corrigió. Sin `datos_revisados` responde `409` con `EXTRACCION_NO_CONFIRMABLE`.
- `POST /ocr/extracciones/{id}/descartar` · `ocr.usar` · OCR-12.
- `GET /ocr/extracciones` · `ocr.historial` · OCR-13 · filtros `estado`, `desde`, `hasta`; fecha, usuario, estado, método, tiempo y confianza promedio.
- `GET /ocr/precision` · `ocr.historial` · OCR-11 · exactitud por campo calculada con las correcciones de los usuarios, en un rango de fechas.

### 5.9 Vales (M07)

- `POST /ordenes/{orden_id}/vales/simulacion` · `vales.emitir` · VAL-01, VAL-03, CMB-04 · recibe `combustible_id` y las cantidades; devuelve el precio vigente, el valor en soles, el presupuesto restante y el máximo de galones emisibles. No guarda nada.
- `POST /ordenes/{orden_id}/vales` · `vales.emitir` · VAL-01, VAL-02, VAL-03, VAL-04 · recibe `combustible_id`, `fecha_vencimiento` opcional y la lista de vales (cantidad de cada uno); emite todos o ninguno.
- `POST /ordenes/{orden_id}/vales-entidad` · `vales.emitir` · VAL-05, VAL-15 · recibe `numero_entidad`, `combustible_id`, `cantidad` y `fecha_vencimiento` opcional; valida la unicidad según la modalidad de la institución y el rango de la serie.
- `GET /vales` · `vales.ver` · VAL-06 · filtros `q` (número de estación o número de entidad), `institucion_id`, `orden_id`, `estado`, `combustible_id`, `emisor`, paginación.
- `GET /vales/buscar` · `vales.ver` · QRY-01, CON-01, VAL-06 · parámetro `q`; devuelve hasta 8 candidatos con institución, orden, combustible, saldo y estado. Si el número coincide con varios vales, devuelve todos.
- `GET /vales/alertas` · `vales.ver` · VAL-13 · vales con saldo bajo y próximos a vencer, según los parámetros.
- `GET /vales/{id}` · `vales.ver` · VAL-07, VAL-08 · numeración de estación o de entidad, orden, cantidad inicial, consumido, saldo, precio aplicado, valor en soles y estado (un vale vencido se reconoce como tal aunque el proceso diario no lo haya marcado).
- `GET /vales/{id}/movimientos` · `vales.ver` · CON-12 · línea de tiempo con cantidad, saldo posterior, usuario, fecha y motivo.
- `POST /vales/{id}/impresion` · `vales.emitir` · VAL-12 · registra la impresión y devuelve los datos y números del vale; desde la segunda vez marca el vale como duplicado.
- `POST /vales/{id}/anular` · `vales.anular` · VAL-10 · recibe `motivo`.
- `POST /vales/{id}/ajustes` · `vales.ajustar` · VAL-11 · recibe `variacion` (con signo) y `motivo`; `409` con `AJUSTE_NEGATIVO` si el saldo quedaría negativo.
- `POST /vales/vencimientos/procesar` · `config.gestionar` · VAL-09 · marca como vencidos los vales cuya fecha ya pasó, a demanda.

### 5.10 Consumos (M08)

- `POST /vales/{id}/consumos` · `consumos.registrar` · CON-01 a CON-09, CON-13, CON-14 · recibe `cantidad` en galones o `importe_soles`, `token_operacion` (UUID), `combustible_id` opcional, `placa`, `conductor`, `observacion` y, solo para el administrador, `fecha_local` con motivo (registro retroactivo). Todo movimiento registra `estacion_id`; el saldo leído por cualquier sede se obtiene de la fuente central y refleja el movimiento confirmado. Devuelve el movimiento y el saldo actualizado. Un reenvío con el mismo `token_operacion` devuelve el movimiento original.
- `GET /vales/{id}/consumos` · `vales.ver` · QRY-05 · filtros `desde` y `hasta`.
- `POST /consumos/{movimiento_id}/revertir` · `consumos.revertir` · CON-11 · recibe `motivo`; `409` con `CONSUMO_YA_REVERTIDO` si ya se revirtió.
- `GET /consumos/{movimiento_id}/comprobante` · `consumos.registrar` · CON-10 · datos para el comprobante imprimible.

### 5.11 Consultas (M09)

- `GET /consultas/saldo/ordenes/{id}` · `consultas.ver` · QRY-02 · presupuesto, emitido, consumido, saldo de cada vale, saldo total y presupuesto restante.
- `GET /consultas/saldo/instituciones/{id}` · `consultas.ver` · QRY-03 · saldo vigente con desglose por orden y vale; los vales anulados y vencidos aparecen aparte.
- `GET /consultas/consumo` · `consultas.ver` · QRY-04, QRY-05, QRY-06 · filtros `institucion_id`, `orden_id`, `vale_id`, `desde`, `hasta`, `agrupacion` (dia, semana o mes), `combustible_id`, `estado`, `emisor`; las reversiones se descuentan.
- `GET /consultas/estado-cuenta/{institucion_id}` · `consultas.ver` · QRY-07 · parámetros `desde` y `hasta`; saldo inicial, movimientos y saldo final.
- QRY-01 se resuelve con `GET /vales/buscar`; QRY-08 se cumple por diseño (no hay caché de saldos) y se verifica con una prueba.

### 5.12 Reportes y panel (M10)

- `GET /panel/indicadores` · `sesion` · REP-01, VAL-13, AUD-06 · órdenes del mes, vales activos, galones consumidos y vales por agotarse o vencer; para el administrador incluye si hay diferencias de saldo sin revisar.
- `GET /reportes/rangos` · `reportes.ver` · REP-06 · devuelve los rangos de hoy, esta semana, este mes y mes anterior calculados en la zona horaria de Lima.
- `GET /reportes/consumo/periodo` · `reportes.ver` · REP-02 · serie agrupada por día, semana o mes.
- `GET /reportes/consumo/instituciones` · `reportes.ver` · REP-03 · ranking.
- `GET /reportes/consumo/combustibles` · `reportes.ver` · REP-04 · distribución.
- `GET /reportes/ordenes` · `reportes.ver` · REP-05 · cantidad de órdenes y presupuesto total del periodo, con detalle por institución.
- `GET /reportes/exportar/{reporte}.xlsx` · `reportes.ver` · REP-07 · `reporte` es `consumo-periodo`, `consumo-instituciones`, `consumo-combustibles`, `ordenes`, `consumo` o `estado-cuenta`; recibe los mismos filtros que la consulta y devuelve un archivo Excel con los mismos datos.
- REP-08 (PDF): Angular muestra los mismos datos en una vista preparada para impresión, con `GET /configuracion/estacion` para el encabezado; no requiere un endpoint adicional.

### 5.13 Auditoría e integridad (M11)

- `GET /auditoria/bitacora` · `auditoria.ver` · AUD-03 · filtros `usuario_id`, `accion`, `entidad`, `desde`, `hasta`; valores anteriores y nuevos.
- `GET /auditoria/historial/{entidad}/{id}` · `historial.ver` · AUD-04 · `entidad` es `orden`, `vale`, `institucion`, `usuario` o `combustible`.
- `GET /auditoria/integridad/ultima` · `auditoria.ver` · AUD-05 · resultado de la última verificación.
- `GET /auditoria/integridad/verificaciones` · `auditoria.ver` · AUD-05 · historial de verificaciones.
- `POST /auditoria/integridad/verificar` · `auditoria.ver` · AUD-05 · ejecuta la verificación a demanda y devuelve el resultado.
- `GET /auditoria/integridad/diferencias` · `auditoria.ver` · AUD-06 · filtro `revisada`.
- `POST /auditoria/integridad/diferencias/{id}/revisar` · `auditoria.ver` · AUD-06 · recibe `comentario`.
- AUD-01 (registro de acciones) lo hace el sistema en cada servicio; AUD-02 (inalterabilidad) lo garantizan los permisos de PostgreSQL y los disparadores.

[↑ Volver al índice](#indice)

---

<a id="s6"></a>

## 6. Fases de implementación

**Estructura de cada fase:** objetivo, requerimientos, tareas, entregable **navegable**, **verificación** y qué habilita en Angular.

**Definición de terminado de una fase:**
- [ ] Todas las tareas de la fase marcadas
- [ ] Pruebas de la fase en verde (`pytest`) y `ruff check .` sin errores
- [ ] Verificación de la fase ejecutada con el resultado esperado
- [ ] `python scripts/smoke.py --hasta N` termina en verde (es acumulativo: cada fase agrega sus comprobaciones y repite las anteriores)
- [ ] Commit y etiqueta de git (`fase-NN-cerrada`)

**Reglas permanentes:**
- Los routers no contienen reglas de negocio: validan la entrada, llaman a un servicio y devuelven el resultado.
- El servicio es dueño de la transacción: hace `commit` al terminar o `rollback` ante un error.
- Ninguna dependencia fuera de la lista cerrada de la sección 1.
- Cada endpoint nuevo declara su permiso y queda cubierto por una prueba de autorización.

---

<a id="f0"></a>

### Fase 0. Entorno y repositorio

**Objetivo:** todo instalado y comprobable con un solo comando.
**Requerimientos:** ninguno directo (base).

Tareas:
- [x] Instalar Python 3.11 o superior, PostgreSQL 16 o superior, pgAdmin 4, RapidOCR (`rapidocr==3.10.0`), Git y la versión de Node.js que exige Angular 21 (comprobar con `ng version` cuando se cree el frontend). En Windows, asegurarse de que `psql`, `pg_dump` y `pg_restore` queden en el `PATH` (o anotar su ruta en `C:\Program Files\PostgreSQL\<versión>\bin`).
- [x] Crear el repositorio con `backend/` y el proyecto Angular en la raíz, y el `.gitignore` (`.venv/`, `.env`, `almacenamiento/`, `datos/documentos/`, `node_modules/`, `dist/`, `.angular/`).
- [x] Crear el entorno virtual en `backend/` y el `pyproject.toml` con la lista cerrada de dependencias, el entrypoint (`[tool.fastapi] entrypoint = "app.main:app"`) y la configuración de `pytest` y `ruff`. Instalar con `pip install -e ".[dev]"`.
- [x] Crear en PostgreSQL las bases `vales_san_jose` y `vales_san_jose_test` con codificación `UTF8` (por ejemplo `CREATE DATABASE vales_san_jose WITH ENCODING 'UTF8' TEMPLATE template0;`) y los dos roles con `LOGIN`: `vales_migrador` (dueño de la estructura y los disparadores) y `vales_app` (sin privilegios por defecto; cada migración concede lo mínimo). Otorgar `CONNECT` sobre ambas bases, `CREATE` sobre el esquema `public` a `vales_migrador` y `USAGE` sobre `public` a `vales_app`; PostgreSQL 15 o superior ya no da `CREATE` en `public` a todos los usuarios. Se pueden crear desde pgAdmin (clic derecho en *Databases* → *Create* y en *Login/Group Roles* → *Create*), anotando la configuración en `.env.example`.

  Con `psql` como superusuario (en pgAdmin, ejecutar cada bloque conectado a la base que corresponda):

  ```sql
  CREATE ROLE vales_migrador LOGIN PASSWORD 'cambiar_esta_clave';
  CREATE ROLE vales_app      LOGIN PASSWORD 'cambiar_esta_clave';

  CREATE DATABASE vales_san_jose      WITH ENCODING 'UTF8' TEMPLATE template0;
  CREATE DATABASE vales_san_jose_test WITH ENCODING 'UTF8' TEMPLATE template0;

  GRANT CONNECT ON DATABASE vales_san_jose      TO vales_migrador, vales_app;
  GRANT CONNECT ON DATABASE vales_san_jose_test TO vales_migrador, vales_app;

  \c vales_san_jose
  GRANT CREATE, USAGE ON SCHEMA public TO vales_migrador;
  GRANT USAGE        ON SCHEMA public TO vales_app;

  \c vales_san_jose_test
  GRANT CREATE, USAGE ON SCHEMA public TO vales_migrador;
  GRANT USAGE        ON SCHEMA public TO vales_app;
  ```

  La contraseña real no se escribe en el repositorio: va en `.env` (fuera de git) y en `.env.example` solo como marcador.

- [x] Comprobar la conexión desde pgAdmin 4: registrar el servidor con host `127.0.0.1`, puerto `5432` y el rol `postgres`, y ver las dos bases en el árbol. pgAdmin es solo la herramienta de administración; las migraciones se aplican con `python -m app.cli migrar aplicar`.
- [x] Escribir `scripts/verificar_entorno.py`: comprueba las versiones de Python, PostgreSQL (`SELECT version()`), RapidOCR mediante import y carga del modelo, Git, Node y `pg_dump`, y la conexión a las dos bases con los dos roles.

**Entregable navegable:** resultado del script en consola, con una línea por comprobación.

**Verificación:**
- `python scripts/verificar_entorno.py` termina con código 0 y lista cada herramienta con su versión.
- `pip list` muestra únicamente las dependencias de la lista cerrada y sus dependencias transitivas.
- pgAdmin 4 conecta al servidor local y muestra `vales_san_jose` y `vales_san_jose_test`; `vales_app` puede conectarse pero no crear tablas ni borrar filas de las tablas que solo permiten `SELECT` e `INSERT`.

**Habilita en Angular:** crear el proyecto Angular 21 (sin SSR) en la raíz del repositorio, con la configuración de proxy `/api` hacia `http://127.0.0.1:8000`.

---

<a id="f1"></a>

### Fase 1. Esqueleto FastAPI, PostgreSQL y migraciones propias

**Objetivo:** aplicación que arranca, conecta a PostgreSQL, versiona la estructura sin Alembic y responde con las convenciones de la API.
**Requerimientos:** ninguno directo (base de todos).

Tareas:
- [x] Crear la estructura base de carpetas de la sección 3.2; los módulos de dominio se completan en sus respectivas fases.
- [x] `config.py`: configuración de entorno con Pydantic Settings, archivo `.env` local y secretos fuera del repositorio. Las URL usan `postgresql+asyncpg://`.
- [x] `db/sesion.py`: motor de SQLAlchemy con `isolation_level="READ COMMITTED"`, `pool_pre_ping` y dependencia `SesionBd` con `Annotated`.
- [x] Ejecutor de migraciones (`db/migrar.py`):
  - tabla `schema_migrations` (versión, nombre, checksum, fecha);
  - archivos `NNNN_descripcion.sql` en orden; sentencias separadas por una línea `-- ---` (así los cuerpos de funciones y disparadores en PL/pgSQL, delimitados con `$$ ... $$`, pueden contener `;` sin romper el archivo);
  - cada archivo se aplica dentro de una transacción: PostgreSQL permite DDL transaccional, de modo que una migración fallida no deja cambios a medias (si alguna necesita `CREATE INDEX CONCURRENTLY`, se marca como no transaccional);
  - se rechaza aplicar si un archivo ya aplicado cambió (checksum distinto);
  - usa `MIGRADOR_URL`; solo hacia adelante (la reversión se hace con respaldo);
  - comandos `python -m app.cli migrar estado`, `aplicar` y `nueva <nombre>`.
- [x] Crear el bootstrap inicial `db/schema.sql` ejecutable desde pgAdmin/psql: tipos enum (`user_role`, tipos de institución, estados de orden/OCR/vale y movimientos), tablas y restricciones. `db/seed.sql` carga datos de demostración; todavía no sustituye al futuro ejecutor de migraciones numeradas.
- [x] Implementar el ejecutor propio de migraciones SQL numeradas y establecer cómo convertir el esquema inicial en la primera migración versionada sin duplicar el estado de una base.

  Resolución acordada: el ejecutor detecta una base ya poblada con `schema.sql` (existe `estaciones` y no hay filas en `schema_migrations`), registra `0001` como aplicada con su checksum real y no vuelve a ejecutarla. Sobre una base vacía ejecuta el archivo completo dentro de una transacción. La tabla de control `schema_migrations` la maneja el ejecutor y no forma parte de los archivos numerados.
- [x] Completar `parametros` y `secuencias` en el flujo versionado, con claves y marcas de tiempo definidas en este plan. La migración `0001_base.sql` inserta los diez parámetros por defecto (`ocr_umbral_confianza`, `archivo_max_mb`, `vale_formato_numeracion_estacion`, `vale_vigencia_dias`, `vale_umbral_saldo_bajo_pct`, `vale_dias_aviso_vencimiento`, `sesion_inactividad_min`, `login_intentos_max`, `login_bloqueo_min`, `refresh_token_dias`) con `ON CONFLICT DO NOTHING`.
- [x] `errors.py`: `ErrorDominio(status, codigo, mensaje, detalles)`, manejador de errores de validación (422 con detalle por campo), manejador de 404/405 con el formato estándar y manejador general que nunca expone trazas.
- [x] `core/dinero.py` (Decimal, redondeo a 2 decimales con mitad hacia arriba) y `core/tiempo.py` (ahora en Lima con UTC-5 fijo, fecha local, rangos de hoy, semana, mes y mes anterior), con pruebas (`tests/test_dinero.py`, `tests/test_tiempo.py`).
- [x] Crear enums PostgreSQL del dominio y router `sistema.py` con `GET /salud` (consulta `SELECT 1` y versión del servidor).
- [x] Agregar `GET /catalogos/enums` y pruebas para el endpoint de salud.
- [x] `tests/conftest.py`: aplica las migraciones sobre `vales_san_jose_test` con `MIGRADOR_URL`; para limpiar entre pruebas, desactiva temporalmente los disparadores de inalterabilidad con `ALTER TABLE ... DISABLE TRIGGER USER`, ejecuta `TRUNCATE ... RESTART IDENTITY CASCADE` y los vuelve a habilitar; ofrece el cliente de pruebas conectado como `vales_app` cuando la prueba necesite comprobar permisos.
- [x] `scripts/smoke.py`: cliente HTTP que ejecuta comprobaciones numeradas hasta la fase indicada (`--hasta N`), con salida `OK` o `FALLA` y código de salida. La obtención de JWT y la rotación de refresh token se agregan como comprobaciones desde la Fase 2.
- [x] `cli.py` con `argparse` y el comando `migrar` (`estado`, `aplicar`, `nueva <nombre>`, con `--test` para la base de pruebas).

**Entregable navegable:** `fastapi dev` y la documentación interactiva en `http://127.0.0.1:8000/docs`.

**Verificación:**
- `python -m app.cli migrar aplicar` aplica `0001`; `migrar estado` la muestra como aplicada.
- Alterar un archivo ya aplicado y ejecutar `migrar aplicar` falla por checksum.
- `GET /api/v1/salud` responde `{"estado": "ok", ...}` con PostgreSQL y RapidOCR en `ok`.
- `GET /api/v1/catalogos/enums` devuelve las listas.
- En pgAdmin, la base `vales_san_jose` muestra la tabla `schema_migrations` con la versión `0001`.
- `pytest tests/test_sistema.py` y `ruff check .` en verde; `python scripts/smoke.py --hasta 1`.

**Habilita en Angular:** servicio base de acceso a la API, manejo uniforme de errores y pantalla de arranque que consulta `GET /salud`.

---

<a id="f2"></a>

### Fase 2. Autenticación, sesiones y auditoría base

**Objetivo:** inicio y cierre de sesión seguros, con cambio obligatorio de contraseña y huella de acciones.
**Requerimientos:** AUT-01 a AUT-10 (AUT-09 se completa en la Fase 3), AUD-01.
**Endpoints:** sección 5.2.

Tareas:
- [x] Migración versionada de acceso: integrar la tabla ya definida en el bootstrap como `app_users` (`full_name`, `email`, `dni`, `code` opcional, `password_hash`, `role user_role`, `station_id`, `must_change_password boolean NULL` y timestamps). No agregar `active`; además integrar `estaciones`, `refresh_tokens`, `intentos_login` y `tokens_recuperacion`. No duplicar tablas ni mantener el nombre anterior `usuarios`.
- [x] `core/seguridad.py`: contraseñas con `pwdlib[argon2]` y comparación segura; access JWT firmado con PyJWT; refresh aleatorio con `secrets` y almacenado solo como hash, junto al identificador de familia y auditoría de rotación.
- [x] Access JWT con expiración de pocos minutos y claims mínimos; refresh token rotatorio con expiración configurable, revocación por logout/cambio de contraseña/desactivación y detección de reutilización.
- [x] Refresh token viaja en cookie HttpOnly, Secure, SameSite; aplicar validación CSRF/origen a refresh/logout.
- [x] Dependencias en `dependencies.py`:
  - `UsuarioActual`: rechaza JWT inválido o expirado (`401`, `TOKEN_INVALIDO`); si `must_change_password IS TRUE`, permite solo `/auth/yo`, `/auth/cambiar-password` y `/auth/logout` (`403`, `CAMBIO_PASSWORD_OBLIGATORIO`). Con `NULL` o `false`, el acceso es normal.
  - `ProteccionCsrf`: valida origen y token CSRF en endpoints que usan refresh en cookie; se omite para API Bearer sin cookies.
- [x] Límite de intentos con `intentos_login` en PostgreSQL (parámetros `login_intentos_max` y `login_bloqueo_min`); mensaje con el tiempo de espera.
- [x] Recuperación de contraseña: token de un solo uso con vencimiento; correo asíncrono con `aiosmtplib`; en desarrollo, el enlace se imprime en la consola (P-08).
- [x] `services/auditoria.py` con `registrar(db, usuario, accion, entidad, entidad_id, antes, despues)`, que usarán todos los servicios. Registrar inicios de sesión e intentos fallidos.
- [x] Comando `python -m app.cli crear-admin --nombre ... --correo ...`: genera una contraseña temporal, la muestra una vez y marca el cambio obligatorio.
- [x] Pruebas: inicio correcto, mensaje idéntico para correo inexistente y contraseña errónea, bloqueo tras 5 intentos, expiración por inactividad (alterando `ultimo_uso`), reCAPTCHA inválido o score bajo, refresh válido/expirado/reutilizado, revocación al cerrar sesión, `must_change_password` en `TRUE` y `NULL`, recuperación (token de un solo uso y vencido), inexistencia de rutas de registro, filas de auditoría.

**Entregable navegable:** en `/docs`, pulsar "Authorize", iniciar sesión con el administrador creado y llamar a `GET /auth/yo`.

**Verificación:**
- `python -m app.cli crear-admin --nombre Admin --correo admin@ejemplo.pe` muestra la contraseña temporal.
- En `/docs`: probar una cuenta con `must_change_password = TRUE` (los endpoints quedan restringidos hasta el cambio) y otra con `NULL` (acceso normal).
- `pytest tests/test_auth.py` en verde; `python scripts/smoke.py --hasta 2`.

**Habilita en Angular:** pantallas de inicio de sesión, recuperación y cambio de contraseña; guarda de rutas; interceptor que lleva a la pantalla de ingreso ante un `401`; un interceptor de Authorization y renovación del access token mediante refresh.

---

<a id="f3"></a>

### Fase 3. Usuarios, roles y permisos

**Objetivo:** administración de cuentas y control de acceso por rol en cada endpoint.
**Requerimientos:** USR-01 a USR-07, AUT-09.
**Endpoints:** sección 5.3.

Tareas:
- [x] `core/permisos.py` con la matriz de la sección 4.1 y `requiere_permiso("...")` como dependencia.
- [x] Servicio de usuarios: crear, editar, asignar rol y restablecer contraseña; proteger al último administrador de cambios de rol que lo dejen sin administrador. No implementar activación/desactivación de cuentas.
- [x] Router `usuarios.py` con filtros y paginación.
- [x] Prueba global de autorización: recorre `app.routes` y falla si algún endpoint, salvo los públicos declarados, no tiene un permiso.
- [x] Pruebas: permisos por rol, correo duplicado, último administrador, restablecimiento que establece `must_change_password = TRUE`.

**Entregable navegable:** gestión completa de usuarios desde `/docs` con tres usuarios (uno por rol).

**Verificación:**
- Con `smoke.py --hasta 3`: crea un operador, inicia sesión con él y obtiene `403` en `/usuarios`; valida permisos y protección del último administrador al cambiar roles.
- `pytest tests/test_usuarios.py` en verde, incluida la prueba global de autorización.

**Habilita en Angular:** menú según permisos, pantalla de gestión de usuarios y pantalla de acceso denegado.

---

<a id="f4"></a>

### Fase 4. Configuración, combustibles y precios

**Objetivo:** parámetros del sistema, datos de la estación, catálogo de combustibles y precio por galón con histórico (D-01).
**Requerimientos:** CFG-01, CFG-02, CMB-01, CMB-02, CMB-03, CMB-04.
**Endpoints:** secciones 5.4 y 5.5.

Tareas:
- [ ] Migración `0004_catalogos.sql`: `estacion` (una fila), `combustibles`, `precios_combustible` (combustible, `precio_galon numeric(8,2)`, `vigente_desde`, usuario). `vales_app` sin `UPDATE`, `DELETE` ni `TRUNCATE` sobre `precios_combustible`.
- [ ] `services/parametros.py`: definición en código de cada parámetro (tipo, valor por defecto, mínimo, máximo, descripción) y lectura directa de PostgreSQL en cada uso, para que el cambio rija sin reiniciar. Parámetros: `ocr_umbral_confianza` (0.80), `archivo_max_mb` (10), `vale_formato_numeracion_estacion` (formato configurable para numeración propia de San José), `vale_vigencia_dias` (vacío), `vale_umbral_saldo_bajo_pct` (10), `vale_dias_aviso_vencimiento` (7), `sesion_inactividad_min` (60), `login_intentos_max` (5), `login_bloqueo_min` (15).
- [ ] Servicio de precios: registrar (la fecha no puede ser anterior a la del último precio del combustible), precio vigente a una fecha (el último con vigencia menor o igual) y la función `calcular_valor(cantidad, precio)` de CMB-04.
- [ ] Logo de la estación: validación por contenido (PNG o JPG), máximo 1 MB, almacenado en `almacenamiento/estacion/`.
- [ ] Combustibles: crear, editar nombre, activar o desactivar; uno en uso no se elimina.
- [ ] Comando `python -m app.cli sembrar-demo --catalogos`: combustibles (Diésel B5, Gasohol 90, Gasohol 95, GLP) y precios de ejemplo.
- [ ] Pruebas: precio vigente con dos cambios, fecha anterior a la primera, ausencia de edición y borrado de precios, validación de rango de parámetros, cambio de parámetro sin reinicio, subida de logo inválida.

**Entregable navegable:** catálogo, precios y parámetros gestionables desde `/docs`.

**Verificación:**
- `python -m app.cli sembrar-demo --catalogos` termina sin error.
- `GET /combustibles` muestra cada combustible con su precio vigente; registrar un precio nuevo con la fecha de hoy y ver que el histórico lo muestra primero.
- `PUT /configuracion/parametros` con `login_intentos_max` en 3 cambia el comportamiento del bloqueo sin reiniciar.
- `pytest tests/test_combustibles.py tests/test_configuracion.py` en verde; `python scripts/smoke.py --hasta 4`.

**Habilita en Angular:** pantallas de catálogo, precios, parámetros y datos de la estación; cabecera para las vistas de impresión.

---

<a id="f5"></a>

### Fase 5. Instituciones y órdenes de compra

**Objetivo:** registrar instituciones y órdenes con presupuesto en soles, documento original y estados.
**Requerimientos:** INS-01 a INS-05, ORD-01 a ORD-11.
**Endpoints:** secciones 5.6 y 5.7.

Tareas:
- [ ] Migración `0005_ordenes.sql`: `instituciones` (RUC único con `CHECK (ruc ~ '^[0-9]{11}$')`, `modalidad_numeracion`, estado, etc.) y `ordenes_compra` (`institucion_id`, `numero`, `anio`, `fecha_emision`, `presupuesto_soles numeric(12,2)`, `combustible_id`, `estado`, `serie_desde`, `serie_hasta`, `creada_con_ocr`, `observaciones`, `motivo_anulacion`, metadatos del archivo: ruta relativa, tipo, tamaño y hash). Índice único `(institucion_id, anio, numero)`.
- [ ] Validación de RUC: 11 dígitos y dígito verificador (pesos 5, 4, 3, 2, 7, 6, 5, 4, 3, 2 sobre los 10 primeros dígitos; resto de la suma entre 11; dígito igual a 11 menos el resto, con 10 como 0 y 11 como 1). Endpoint `GET /instituciones/ruc/{ruc}`.
- [ ] Servicio de instituciones: alta, edición con la restricción del RUC, desactivación y reactivación, y ficha con resumen (los saldos y consumos se completan en las Fases 6 y 7).
- [ ] Servicio de órdenes: registro con `borrador` o `vigente`, número único por institución y año, advertencia de posible duplicado (`409` con `ORDEN_POSIBLE_DUPLICADA` y confirmación explícita), edición controlada, transiciones válidas en un diccionario de estados, cierre y anulación con motivo.
- [ ] `core/archivos.py`: validación por contenido (firmas de PDF, JPG y PNG), tamaño máximo desde el parámetro, almacenamiento en `almacenamiento/ordenes/{año}/{uuid}.{ext}`, lectura en bloques con tope; respuesta con `Content-Disposition: inline` y `X-Content-Type-Options: nosniff`.
- [ ] Función `tiene_consumos(orden_id)` que por ahora devuelve falso; la Fase 7 la completa y actualiza su prueba.
- [ ] Pruebas: RUC válido e inválido, RUC duplicado, número duplicado por año, advertencia de duplicado, edición restringida, transiciones inválidas, archivo con extensión falsa, descarga solo autorizada.

**Entregable navegable:** registro de instituciones y órdenes con documento adjunto, desde `/docs`.

**Verificación:**
- Con `smoke.py --hasta 5`: crear una institución, probar un RUC inválido (`422`), crear una orden, repetir el número (`409`), subir un PDF, descargarlo, marcarla vigente y cerrarla.
- `pytest tests/test_instituciones.py tests/test_ordenes.py` en verde.

**Habilita en Angular:** pantallas de instituciones (con validación de RUC en vivo) y de órdenes (listado, formulario, detalle con visor del documento).

---

<a id="f6"></a>

### Fase 6. Vales: emisión y vales de entidad

**Objetivo:** emitir vales con conversión de galones a soles (D-01) y registrar vales de entidad con su numeración (D-02).
**Requerimientos:** VAL-01 a VAL-07, VAL-12 a VAL-15, QRY-01.
**Endpoints:** sección 5.9 (excepto anulación, ajuste y vencimientos, que son de la Fase 7).

Tareas:
- [ ] Migración `0006_vales.sql`:
  - `vales`: `numero_estacion` único para vales de San José, `numero_entidad` para vales emitidos por instituciones, `clave_numeracion` única según la modalidad institucional, `orden_compra_id`, `emisor`, `combustible_id`, `cantidad_inicial`, `precio_galon_aplicado`, `valor_soles`, `valor_comprometido_soles`, `saldo` como `numeric(12,2)` con `CHECK (saldo >= 0)`, `estado`, `fecha_emision`, `fecha_vencimiento`, `veces_impreso`; no existe un código interno impreso ni código de barras/QR.
  - `movimientos_vale`: vale, tipo, `variacion numeric(12,2)` con signo, `saldo_posterior numeric(12,2)`, usuario, motivo, placa, conductor, `token_operacion uuid` único, `movimiento_origen_id` único (para reversiones), `fecha_local date`, instante de creación `timestamptz`; `vales_app` con `GRANT SELECT, INSERT` únicamente.
- [ ] Migración `0007_disparadores.sql` (ejecutada con `vales_migrador`): función en PL/pgSQL y disparadores `BEFORE UPDATE OR DELETE` (por fila) y `BEFORE TRUNCATE` (por sentencia) sobre `movimientos_vale` y `auditoria`, que rechazan el cambio incluso para el rol dueño. Modelo:

```sql
CREATE OR REPLACE FUNCTION rechazar_cambio() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'La tabla % es inalterable', TG_TABLE_NAME
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER movimientos_vale_inalterable
    BEFORE UPDATE OR DELETE ON movimientos_vale
    FOR EACH ROW EXECUTE FUNCTION rechazar_cambio();

CREATE TRIGGER movimientos_vale_sin_truncate
    BEFORE TRUNCATE ON movimientos_vale
    FOR EACH STATEMENT EXECUTE FUNCTION rechazar_cambio();
```

En PostgreSQL los disparadores se ejecutan también para el rol dueño, así que el control no depende del registro binario. El dueño de la tabla puede desactivarlos con `ALTER TABLE ... DISABLE TRIGGER` (por eso las pruebas de limpieza lo hacen de forma explícita) y un superusuario puede hacerlo con `session_replication_role`; ninguno de esos privilegios los tiene `vales_app`, que sigue limitado por los `GRANT`.

- [ ] `services/numeracion.py`: genera/asigna la numeración propia de la estación con el formato configurable, incrementando `secuencias` bajo `SELECT ... FOR UPDATE`. La numeración de entidad se conserva como la entrega cada institución.
- [ ] Emisión: bajo bloqueo de la orden, toma el precio vigente, calcula `valor_soles`, comprueba que la suma de `valor_comprometido_soles` más lo nuevo no exceda el presupuesto y crea todos los vales y sus movimientos de emisión, o ninguno. Errores con el presupuesto restante y el máximo de galones. Simulación sin guardar.
- [ ] Vales de entidad: arma `clave_numeracion` (`institucion:{institucion_id}:{numero}` o `orden:{orden_id}:{numero}` según la modalidad), valida el rango de la serie de la orden, aplica las mismas reglas de saldo y presupuesto y conserva el número de entidad. El tratamiento del presupuesto sigue el supuesto de P-11.
- [ ] Búsqueda (`GET /vales/buscar`) por número de estación o número de entidad, con todos los candidatos cuando hay coincidencias múltiples, y listado con filtros.
- [ ] Alertas de saldo bajo y por vencer; datos de impresión con registro de la impresión y marca de duplicado.
- [ ] Pruebas: presupuesto excedido, cambio de precio entre dos emisiones (cada vale conserva su precio), atomicidad (tres vales y el tercero falla: no queda ninguno), orden en borrador, cerrada o anulada, combustible sin precio, número de entidad repetido en la misma serie (rechazado) y en otra orden con numeración por orden (aceptado), número fuera de rango, serie agotada, búsqueda con varias coincidencias, y emisión simultánea de dos usuarios sobre la misma orden (el total nunca excede el presupuesto).

**Entregable navegable:** emisión de vales y registro de vales de entidad desde `/docs`.

**Verificación:**
- Con `smoke.py --hasta 6`: simular una emisión, emitir 2 vales, intentar uno que excede el presupuesto (`409` con el máximo de galones), registrar un vale de entidad repetido en una institución con numeración general (`409`) y buscar por número de entidad.
- `pytest tests/test_vales.py` en verde, incluida la prueba de emisión simultánea.

**Habilita en Angular:** emisión con vista previa, registro de vales de entidad, listado, detalle, vista de impresión numerada, buscador global y alertas.

---

<a id="f7"></a>

### Fase 7. Consumos y correcciones

**Objetivo:** consumos parciales exactos, sin doble envío, con concurrencia controlada y correcciones trazables.
**Requerimientos:** CON-01 a CON-14, VAL-08 a VAL-11.
**Endpoints:** secciones 5.9 (anulación, ajustes y vencimientos) y 5.10.

Tareas:
- [ ] Servicio de consumo, dueño de la transacción:

```python
async def registrar_consumo(db: AsyncSession, vale_id: int, datos: ConsumoIn, usuario: Usuario) -> Movimiento:
    try:
        vale = (await db.execute(
            select(Vale).where(Vale.id == vale_id).with_for_update()
        )).scalar_one_or_none()
        if vale is None:
            raise ErrorDominio(404, "VALE_NO_ENCONTRADO", "El vale no existe")

        previo = (await db.execute(
            select(Movimiento).where(Movimiento.token_operacion == datos.token_operacion)
        )).scalar_one_or_none()
        if previo is not None:
            return previo                                    # reenvío: no duplica

        vale.asegurar_consumible(hoy_lima(), datos.combustible_id)  # estado, vencimiento, orden, combustible
        if datos.importe_soles is not None:
            importe = dinero.monto(datos.importe_soles)
            cantidad = dinero.galones(importe / vale.precio_galon)
        else:
            cantidad = dinero.cantidad(datos.cantidad_galones)
            importe = dinero.monto(cantidad * vale.precio_galon)
        if cantidad > vale.saldo:
            raise ErrorDominio(409, "SALDO_INSUFICIENTE", "La cantidad excede el saldo",
                               {"saldo": str(vale.saldo)})
        nuevo = vale.saldo - cantidad
        mov = Movimiento(vale_id=vale.id, tipo="consumo", variacion=-cantidad,
                         saldo_posterior=nuevo, importe_soles=importe, precio_galon=vale.precio_galon,
                         token_operacion=datos.token_operacion, estacion_id=usuario.estacion_id,
                         usuario_id=usuario.id, fecha_local=hoy_lima(), ...)
        db.add(mov)
        vale.saldo = nuevo
        vale.estado = "agotado" if nuevo == 0 else "activo"
        await auditoria.registrar(db, usuario, "consumo", "vale", vale.id, None, {"cantidad": str(cantidad)})
        await db.commit()
        return mov
    except Exception:
        await db.rollback()
        raise
```

En PostgreSQL, `SELECT ... FOR UPDATE` dentro de `READ COMMITTED` espera al bloqueo y vuelve a evaluar la fila con el valor ya confirmado, así que el saldo que se resta es siempre el último. El índice único de `token_operacion` cierra la ventana del doble envío; no hace falta subir a `SERIALIZABLE`.

- [ ] `Vale.asegurar_consumible`: rechaza vale agotado, anulado o vencido (se reconoce por fecha aunque no esté marcado), orden anulada y combustible distinto del del vale (P-03), con el código de error específico.
- [ ] Validación de la cantidad (mayor que cero, hasta 2 decimales), datos complementarios opcionales (P-06) y fecha local siempre del servidor; el registro retroactivo solo para el administrador y con motivo (P-09).
- [ ] Reversión: movimiento inverso enlazado con `movimiento_origen_id` (único: no se revierte dos veces); no se revierte un consumo de un vale anulado.
- [ ] Anulación de vale: movimiento de anulación por el saldo restante, saldo en cero y `valor_comprometido_soles` igual al valor ya consumido (P-13). Ajuste de saldo con signo y motivo, sin dejar saldo negativo.
- [ ] Vencimiento: reconocimiento por fecha en cada consulta y consumo, más `procesar_vencimientos` (comando `python -m app.cli vencimientos` y endpoint a demanda).
- [ ] Completar `tiene_consumos` de la Fase 5 y actualizar su prueba; el comprobante de consumo devuelve los datos para imprimir.
- [ ] `scripts/probar_concurrencia.py`: inicia sesión con varios clientes y lanza consumos simultáneos sobre un mismo vale con hilos.
- [ ] Pruebas: consumo parcial (100 menos 30 es 70), saldo insuficiente, vale agotado, anulado, vencido, combustible distinto, token repetido (devuelve el original), reversión y doble reversión, ajuste que dejaría saldo negativo, historial ordenado, anulación de orden con y sin consumos, y concurrencia.

**Entregable navegable:** despacho completo desde `/docs`.

**Verificación:**
- `pytest tests/test_consumos.py` en verde.
- `python scripts/probar_concurrencia.py --numero-estacion 2027-000001 --procesos 10 --cantidad 15` sobre un vale de 100 galones imprime: aceptados 6, rechazados 4, saldo final 10.00.
- Con `smoke.py --hasta 7`: consumir 30 de 100 (saldo 70), consumir 80 (`409`), reenviar el mismo `token_operacion` (un solo movimiento), revertir como administrador y anular un vale.

**Habilita en Angular:** pantalla de despacho (con el `token_operacion` generado por pantalla), historial de movimientos y acciones del administrador (anular, ajustar, revertir).

---

<a id="f8"></a>

### Fase 8. Auditoría e integridad de saldos

**Objetivo:** que cualquier saldo incorrecto o cambio indebido se detecte solo.
**Requerimientos:** AUD-02 a AUD-06.
**Endpoints:** sección 5.13.

Tareas:
- [ ] Migración `0008_integridad.sql`: `verificaciones_integridad` (fecha, vales revisados, diferencias) y `diferencias_saldo` (verificación, vale, saldo almacenado, saldo recalculado, `revisada`, comentario).
- [ ] `services/integridad.py`: una sola consulta que compara `vales.saldo` con la suma de `variacion` por vale, guarda el resultado y las diferencias nuevas; no repite avisos de diferencias ya revisadas salvo que reaparezcan.
- [ ] Comando `python -m app.cli verificar-saldos` (código de salida 1 si hay diferencias) y endpoint a demanda.
- [ ] Bitácora con filtros y paginación; historial por registro (`orden`, `vale`, `institucion`, `usuario`, `combustible`).
- [ ] Indicador de diferencias sin revisar en `GET /panel/indicadores` (se completa en la Fase 12).
- [ ] Pruebas: sin diferencias con datos coherentes; diferencia provocada y detectada; marcar como revisada; la aplicación (con `vales_app`) no puede modificar ni borrar `movimientos_vale` ni `auditoria` (error de permisos), y los disparadores lo impiden también para `vales_migrador`; `TRUNCATE` sobre esas tablas también se rechaza.

**Entregable navegable:** bitácora, historial e integridad desde `/docs`.

**Verificación:**
- `python -m app.cli verificar-saldos` imprime "0 diferencias" con código 0.
- Con `vales_migrador`: `UPDATE vales SET saldo = saldo + 1 WHERE id = 1`; el comando informa 1 diferencia y termina con código 1; `GET /auditoria/integridad/diferencias` la lista y `POST .../revisar` la marca con un comentario.
- `UPDATE movimientos_vale SET variacion = 0` con `vales_app` falla por permisos.
- `TRUNCATE movimientos_vale` con `vales_migrador` falla por el disparador `BEFORE TRUNCATE`.
- En pgAdmin, la tabla `vales` del vale alterado muestra el saldo inflado y `diferencias_saldo` la fila pendiente de revisión.
- `pytest tests/test_integridad.py tests/test_auditoria.py` en verde; `python scripts/smoke.py --hasta 8`.

**Habilita en Angular:** pantallas de bitácora, historial dentro de los detalles de orden y vale, e integridad de saldos.

---

<a id="f9"></a>

### Fase 9. Motor OCR con RapidOCR

**Objetivo:** leer documentos y extraer los campos con su confianza, sin depender de la base de datos.
**Requerimientos:** OCR-03, OCR-04.

Tareas:
- [ ] `services/ocr/lector.py`: valida el tipo real (firmas de PDF, JPG y PNG). En PDF, `pdfplumber` extrae texto y coordenadas del PDF; si hay texto suficiente se usa como texto digital con confianza fija, y si no se renderiza cada página con `pypdfium2` a imagen a 300 dpi. En imágenes se corrige la orientación EXIF con OpenCV. Límites de páginas, de tamaño y de megapíxeles.
- [ ] Estructura común `Palabra` (texto, posición, tamaño, confianza, línea) para texto digital y OCR, de modo que el extractor sea el mismo.
- [ ] `services/ocr/preprocesado.py` con OpenCV: escala de grises, reducción de ruido, corrección de inclinación, binarización adaptativa y escalado; cada paso activable por configuración para medir su efecto en la Fase 10.
- [ ] `services/ocr/rapidocr.py`: integrar `rapidocr==3.10.0` directamente. Inicializar `RapidOCR()` una vez por proceso, convertir la imagen preprocesada a matriz NumPy y mapear cajas/texto/confianza devueltos a `Palabra`; manejar excepción de carga y timeout sin subprocess ni binario externo.

- [ ] Límite de concurrencia con un semáforo (`OCR_CONCURRENCIA`, por defecto 2): si no se obtiene turno en pocos segundos, `503` con `OCR_OCUPADO`.
- [ ] `normalizador.py`: fechas a ISO (acepta `15/03/2027` y `15 de marzo de 2027`), montos a decimal (`S/ 1,500.00` y `1.500,00`), RUC con dígito verificador, combustible contra el catálogo con coincidencia aproximada y correcciones de confusiones en campos numéricos (O por 0, l por 1, S por 5).
- [ ] `extractor.py`: expresiones regulares para patrones fijos y anclas por etiqueta (valor a la derecha o debajo de "Orden de compra N°", "Fecha", "Monto", "Señores"); campo no hallado con valor vacío y confianza 0, nunca inventado. Los campos exactos se ajustan con los documentos reales (P-05).
- [ ] `pipeline.py`: orquesta todo y calcula la confianza por campo (fija y alta para texto digital que valida el formato; en OCR, el promedio de las palabras del valor, penalizado si el formato no valida) y las advertencias según `ocr_umbral_confianza`.
- [ ] Comando `python -m app.cli ocr-probar <archivo>`: procesa un archivo e imprime el JSON.
- [ ] Pruebas: normalizadores con casos reales y límite, extractor con listas de palabras de ejemplo, pipeline con un PDF digital y con una imagen (documentos de prueba sin datos reales), RapidOCR no disponible por error de carga del modelo y tiempo agotado.

**Entregable navegable:** salida JSON en consola con los campos, la confianza y el método de lectura.

**Verificación:**
- `python -m app.cli ocr-probar tests/fixtures/oc_digital.pdf` imprime los campos con método `texto_digital`.
- `python -m app.cli ocr-probar tests/fixtures/oc_foto.jpg` imprime los campos con método `ocr`.
- Una prueba con fallo simulado al cargar el modelo devuelve `OCR_NO_DISPONIBLE`, sin traza interna.
- `pytest tests/test_ocr_unidad.py` en verde.

**Habilita en Angular:** nada todavía (los endpoints llegan en la Fase 11).

---

<a id="f10"></a>

### Fase 10. Dataset y evaluación del OCR

**Objetivo:** medir con documentos reales qué tan bien lee el motor y congelar su versión.
**Requerimientos:** OCR-03, OCR-04 (calidad de la lectura).

Tareas:
- [ ] Reunir de 30 a 50 órdenes reales, anonimizadas o con autorización, en formatos variados (PDF digital, escaneo, foto), en `datos/documentos/`, fuera de git si son sensibles.
- [ ] Crear un JSON de verdad terreno por documento en `datos/verdad_terreno/` y hacerlo revisar por una segunda persona o en una segunda pasada.
- [ ] `datos/division.json` con el grupo de desarrollo (aprox. 70 %) y el de prueba (aprox. 30 %), que no se usa hasta la evaluación final.
- [ ] `scripts/evaluar_ocr.py --grupo desarrollo|prueba`: exactitud por campo, tasa de campos no encontrados, tasa de campos incorrectos con confianza alta, porcentaje de documentos completamente correctos y tiempo medio, desglosados por categoría (digital, escaneo, foto). Guarda un informe fechado en `informes/`.
- [ ] Definir antes de medir una meta de exactitud por campo clave, ajustada a la realidad de los documentos.
- [ ] Calibrar `ocr_umbral_confianza` con el grupo de desarrollo para separar campos correctos de incorrectos.
- [ ] Ajustar preprocesado y modo de segmentación (`--psm`) midiendo un cambio a la vez.
- [ ] Evaluación final sobre el grupo de prueba, una sola vez, con la versión del pipeline registrada; congelar `VERSION_PIPELINE` con una etiqueta de git.

**Entregable navegable:** informe de evaluación en `informes/`.

**Verificación:**
- `python scripts/evaluar_ocr.py --grupo desarrollo` genera el informe con la exactitud por campo y por categoría.
- `python scripts/evaluar_ocr.py --grupo prueba` genera el informe final sin modificar el pipeline.

**Habilita en Angular:** nada (informa el umbral que se configura en la Fase 4).

---

<a id="f11"></a>

### Fase 11. API de lectura OCR

**Objetivo:** subir una orden, revisar lo leído y confirmarla, con una falla del OCR que nunca bloquee el registro.
**Requerimientos:** OCR-01, OCR-02, OCR-05 a OCR-13.
**Endpoints:** sección 5.8.

Tareas:
- [ ] Migración `0009_ocr.sql`: `ocr_extracciones` (usuario, archivo, estado, método, `resultado jsonb`, `campos_finales jsonb`, `correcciones jsonb`, confianza promedio, tiempo, versión del pipeline, error, orden creada).
- [ ] `POST /ocr/extracciones`: valida el archivo, lo guarda, crea la extracción en `pendiente`, la pasa a `procesando`, ejecuta el pipeline dentro de la misma petición (procesamiento de OCR fuera del event loop, usando función síncrona en el pool de hilos de FastAPI) y la deja `lista` o `fallida` con el motivo. El archivo se conserva siempre.
- [ ] Institución sugerida por el RUC extraído.
- [ ] `confirmar`: exige `datos_revisados`, valida con el mismo esquema que `POST /ordenes`, crea la orden marcada como registrada con OCR (con el archivo ya guardado), guarda por campo lo extraído, lo final y si se corrigió, y pasa la extracción a `confirmada`.
- [ ] `reintentar` sin volver a subir el archivo y conservando el intento anterior; `descartar`; historial con filtros; `GET /ocr/precision`.
- [ ] Pruebas: lectura correcta con los documentos de prueba, falla del OCR (`fallida` con `OCR_NO_DISPONIBLE` y registro manual posible), `OCR_OCUPADO` con concurrencia saturada, confirmación sin `datos_revisados` (`409`), confirmación con campos inválidos (`422`), correcciones guardadas, precisión calculada.

**Entregable navegable:** el flujo completo de lectura y confirmación desde `/docs`.

**Verificación:**
- Con `smoke.py --hasta 11`: subir el documento de prueba y obtener una extracción `lista`, confirmarla y comprobar que la orden aparece con `creada_con_ocr` activo y sus correcciones registradas.
- Con dispositivo OCR no disponible: la subida devuelve la extracción `fallida` y el registro manual de la misma orden funciona.
- `pytest tests/test_ocr_api.py` en verde.

**Habilita en Angular:** carga con vista previa y temporizador de espera, pantalla de revisión (documento junto a los campos, confianza con color y texto), historial y precisión.

---

<a id="f12"></a>

### Fase 12. Consultas, reportes y exportación

**Objetivo:** responder saldo y consumo con rapidez y generar los reportes.
**Requerimientos:** QRY-02 a QRY-08, REP-01 a REP-08.
**Endpoints:** secciones 5.11 y 5.12.

Tareas:
- [ ] Migración `0010_indices.sql` con los índices que revele `EXPLAIN (ANALYZE, BUFFERS)`: `movimientos_vale (vale_id, fecha_local)`, `movimientos_vale (fecha_local, tipo)`, `vales (orden_compra_id)`, `vales (numero_entidad)`, `ordenes_compra (institucion_id, fecha_emision)`.
- [ ] `services/consultas.py`: saldo por orden y por institución; consumo con agrupación por día (`fecha_local`), semana (`date_trunc('week', fecha_local)`, que en PostgreSQL empieza el lunes, o `EXTRACT(WEEK ...)` con la fecha del lunes como etiqueta) y mes (`date_trunc('month', fecha_local)`), filtros combinables; consumo neto igual a menos la suma de `variacion` de los tipos consumo y reversión; estado de cuenta (saldo inicial más movimientos igual al saldo final).
- [ ] `services/reportes.py`: series por periodo, institución y combustible, reporte de órdenes, rangos predefinidos en Lima e indicadores del panel (incluido el aviso de diferencias sin revisar).
- [ ] `services/xlsx.py`: escritor mínimo de `.xlsx` con `zipfile` y XML (tipos de contenido, relaciones, libro, hoja con cadenas en línea y números, y estilos mínimos para el encabezado en negrita). `GET /reportes/exportar/{reporte}.xlsx` reutiliza las mismas funciones y filtros que la pantalla.
- [ ] Sin caché de saldos ni de reportes: toda consulta lee el último movimiento.
- [ ] Comando `python -m app.cli cargar-volumen --movimientos 50000` y `scripts/benchmark.py` con los tiempos de las consultas principales (meta propuesta: menos de 1 segundo con 50 000 movimientos).
- [ ] Pruebas: totales, descuento de reversiones, agrupación por semana y mes, igualdad de saldo inicial más movimientos con saldo final, saldo actualizado justo después de un consumo, y archivo `.xlsx` íntegro (se descomprime, se lee el XML y se comparan sus datos con los de la consulta).

**Entregable navegable:** consultas, gráficos de datos y exportación a Excel desde `/docs`.

**Verificación:**
- `python -m app.cli cargar-volumen --movimientos 50000` y `python scripts/benchmark.py` muestran cada consulta dentro de la meta.
- Descargar `GET /reportes/exportar/consumo-periodo.xlsx` y abrirlo en Excel o LibreOffice: los datos coinciden con `GET /reportes/consumo/periodo` con los mismos filtros.
- `pytest tests/test_consultas.py tests/test_reportes.py` en verde; `python scripts/smoke.py --hasta 12`.

**Habilita en Angular:** consultas de saldo y consumo, panel de inicio, gráficos de barras y líneas con `p-chart` sobre `chart.js` (siempre con tabla equivalente accesible), exportación a Excel y vistas de impresión para PDF.

---

<a id="f13"></a>

### Fase 13. Integración con Angular y pruebas integrales

**Objetivo:** un solo origen sirviendo la aplicación Angular y la API, con todo el sistema probado de punta a punta.
**Requerimientos:** AUT-09 (verificación global) y todos los anteriores (prueba integral).

Tareas:
- [ ] `web/frontend.py`: servir los archivos compilados de Angular (`FRONTEND_DIST`) y devolver `index.html` para las rutas internas de la aplicación. Se registra al final, después de los routers de la API:

```python
def registrar_frontend(app: FastAPI) -> None:
    raiz = Path(settings.frontend_dist).resolve()
    if not raiz.is_dir():
        return
    indice = raiz / "index.html"

    @app.get("/{ruta:path}", include_in_schema=False)
    def servir(ruta: str):
        if ruta == "api" or ruta.startswith("api/"):
            raise ErrorDominio(404, "NO_ENCONTRADO", "La ruta no existe")
        candidato = (raiz / ruta).resolve()
        if ruta and candidato.is_file() and raiz in candidato.parents:
            return FileResponse(candidato, headers=_cabeceras_estaticas(candidato.name))
        return FileResponse(indice, headers={"Cache-Control": "no-cache"})
```

- [ ] Cabeceras de caché: archivos con hash en el nombre con `Cache-Control: public, max-age=31536000, immutable`; `index.html` con `no-cache`. Sin service worker ni manifiesto (sin PWA).
- [ ] Cabeceras de seguridad: `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options` y una política `Content-Security-Policy` con `default-src 'self'`, ajustada a lo que emita la compilación de Angular.
- [ ] Configuración de proxy para el desarrollo de Angular (`/api` hacia `http://127.0.0.1:8000`) documentada en el README.
- [ ] Guardar `openapi.json` versionado como contrato con Angular y revisarlo cuando cambie un endpoint.
- [ ] Prueba integral de punta a punta con la API: iniciar sesión como administrador, registrar combustible y precio, crear una institución, leer una orden con OCR, confirmarla, emitir vales, registrar vales de entidad, consumir, consultar, revertir y verificar integridad; con Oficina y Despachador, comprobar sus límites.
- [ ] Prueba de carga ligera: 10 clientes simultáneos consumiendo y consultando.
- [ ] Revisión de seguridad:
  - [ ] Refresh token en cookie HttpOnly, SameSite y `Secure` en producción; access JWT solo viaja en Authorization
  - [ ] CSRF exigido en toda petición que modifica datos
  - [ ] Cada endpoint con permiso declarado y probado
  - [ ] Archivos solo por rutas autorizadas, validados por contenido y con tope de tamaño
  - [ ] Rol `vales_app` con permisos mínimos
  - [ ] `/docs` y `/openapi.json` desactivados fuera de desarrollo
  - [ ] Registros (logs) sin contraseñas, tokens ni contenido de las órdenes
- [ ] `python scripts/smoke.py --hasta 13` completo.

**Entregable navegable:** la aplicación Angular completa en `http://127.0.0.1:8000`, con la API en el mismo origen.

**Verificación:**
- `ng build` en la raíz del repositorio, luego `fastapi run` en `backend/`: abrir `http://127.0.0.1:8000`, iniciar sesión, recargar una ruta interna (por ejemplo `/ordenes`) y comprobar que carga la aplicación; `GET /api/v1/ruta-inexistente` devuelve JSON `404`, no la aplicación.
- `pytest -q` completo y `ruff check .` en verde.
- La prueba de carga termina sin errores y con `verificar-saldos` en 0 diferencias.

**Habilita en Angular:** compilación de producción servida por el backend y verificación de los flujos completos.

---

<a id="f14"></a>

### Fase 14. Despliegue sin Docker y respaldo

**Objetivo:** sistema en producción, con respaldo probado y versión congelada.

Tareas:
- [ ] Servidor Linux (por ejemplo Ubuntu) o Windows, con Python 3.11 o superior, PostgreSQL 16 o superior y RapidOCR (`rapidocr==3.10.0`). PostgreSQL se instala como servicio y arranca con el sistema; pgAdmin no es necesario en producción.
- [ ] Copiar el backend, crear el entorno virtual, instalar las dependencias y colocar la compilación de Angular en `FRONTEND_DIST`.
- [ ] `.env` de producción con permisos restringidos (`ENTORNO=produccion`, contraseñas de PostgreSQL, SMTP, claves privadas JWT, secretos reCAPTCHA y flags Secure/SameSite).
- [ ] Aplicar las migraciones con `vales_migrador`; crear la cuenta inicial segura y no reutilizar usuarios ni hashes del seed de demostración.
- [ ] Ejecutar `fastapi run --host 127.0.0.1 --port 8000` como servicio del sistema (systemd, o un servicio de Windows) con reinicio automático y un solo proceso (el límite de concurrencia del OCR es por proceso).
- [ ] Proxy inverso (Nginx o IIS) con HTTPS (Let's Encrypt) hacia el puerto local; el tiempo de espera del proxy mayor que el máximo de lectura OCR.
- [ ] Respaldos diarios: `pg_dump --format=custom --no-owner --file=...` (más `pg_dumpall --globals-only` para los roles) y copia de `almacenamiento/` (cifrando datos en tránsito y protegiendo el almacenamiento de documentos con permisos restringidos), con retención definida y script documentado. El mismo respaldo se puede lanzar desde pgAdmin (*Backup*), pero el script de `pg_dump` es el que queda versionado y programado.
- [ ] Prueba de restauración: `createdb vales_san_jose_restauracion`, `pg_restore --no-owner -d vales_san_jose_restauracion ...` y ejecutar `verificar-saldos` contra esa base.
- [ ] Tareas periódicas (opcional): programar `python -m app.cli vencimientos` y `python -m app.cli verificar-saldos` en el Programador de tareas o cron; sin ellas, los mismos procesos están disponibles a demanda desde la aplicación.
- [ ] Rotación de registros y manual de operación breve: reiniciar el servicio, restaurar, aplicar migraciones y actualizar.
- [ ] Congelar la versión durante el estudio: etiqueta `estudio-v1.0`, versión del pipeline OCR registrada y registro con fecha de cualquier corrección crítica.

**Entregable navegable:** sistema accesible por HTTPS con la aplicación y la API.

**Verificación:**
- `curl -I https://<dominio>/api/v1/salud` devuelve 200 y la aplicación abre en el navegador.
- El puerto del servicio no responde desde fuera del servidor; solo lo hace el proxy.
- Reiniciar el servidor y comprobar que el servicio vuelve solo.
- Restaurar el respaldo en una base temporal y ejecutar `python -m app.cli verificar-saldos` con 0 diferencias.

[↑ Volver al índice](#indice)

---

<a id="s7"></a>

## 7. Decisiones pendientes y supuestos por defecto

- **P-14. Campos OCR:** tipo de combustible, precio y galones, nombre de la entidad, número/fecha de orden, monto y RUC son candidatos; Oficina confirma el conjunto final al revisar formatos reales.
- **P-15. Actualización entre sedes:** decisión técnica definida: SSE autenticado emite aviso de actualización cuando se confirma un movimiento; Angular vuelve a consultar el saldo autoritativo. La consulta inicial también refresca al volver a la pantalla.
- **P-16. Ubicación de estaciones:** se define catálogo de estaciones y asociación de usuario/consumo; confirmar si cada cuenta pertenece a una sede fija o puede operar en varias.
- **P-17. Precio y unidad de despacho:** confirmar si el despacho se captura en galones o soles; el saldo autoritativo del vale se conserva en galones y el importe se calcula con precio fijado al emitir.

Para no frenar el desarrollo, cada punto abierto tiene un supuesto por defecto. Los de negocio conservan la numeración de la especificación de requerimientos (sección 8.2).

Las decisiones confirmadas en este plan prevalecen sobre supuestos anteriores de los documentos de requerimientos: los vales se buscan e imprimen por numeración, sin código interno visible, código de barras ni QR.

### 7.1 De negocio

- [x] **P-01. Identificación impresa de vales.** Decisión confirmada: no llevan código de barras ni QR; se imprimen con su numeración (propia de San José o asignada por la entidad). *Afecta:* Fase 6.
- [ ] **P-02. Vencimiento de vales.** Supuesto: la fecha de vencimiento es opcional. *Afecta:* Fases 6 y 7.
- [ ] **P-03. Combustible del consumo.** Supuesto: debe coincidir con el del vale. *Afecta:* Fase 7.
- [ ] **P-04. Anulación de órdenes con consumos.** Supuesto: no se permite; solo se cierran. *Afecta:* Fases 5 y 7.
- [ ] **P-05. Campos reales de las órdenes.** Se define con los documentos reales. *Afecta:* Fases 9 y 10.
- [ ] **P-06. Datos del consumo.** Supuesto: placa y conductor opcionales. *Afecta:* Fase 7.
- [ ] **P-08. Correo saliente.** Sin cuenta de correo, el enlace de recuperación solo se imprime en consola. *Afecta:* Fase 2.
- [ ] **P-09. Registro retroactivo.** Supuesto: solo el administrador, con motivo. *Afecta:* Fase 7.
- [ ] **P-10. Precio fijo al emitir.** Supuesto: el precio por galón queda guardado en el vale y no cambia. *Afecta:* Fases 4 y 6.
- [ ] **P-11. Vales de entidad y presupuesto.** Supuesto: descuentan del presupuesto de la orden con el precio vigente al registrarlos. *Afecta:* Fase 6.
- [ ] **P-12. Rango de numeración.** Supuesto: la serie de la orden es opcional y, si existe, se controla. *Afecta:* Fases 5 y 6.
- [ ] **P-13. Liberación de presupuesto al anular vales.** Supuesto: se libera solo la parte no consumida. *Afecta:* Fase 7.

### 7.2 Técnicas

- [ ] **T-01. Excel.** Supuesto: escritor propio de `.xlsx` con la biblioteca estándar. Si se permite `openpyxl`, se reemplaza detrás de la misma interfaz. *Afecta:* Fase 12.
- [ ] **T-02. PDF.** Supuesto: el navegador imprime o guarda como PDF las vistas de Angular. Si se exige generarlo en el servidor, hay que sumar una librería. *Afecta:* Fases 6, 7 y 12.
- [x] **T-03. Código de barras/QR.** No se implementan; la búsqueda e impresión usan numeración de vales.
- [ ] **T-04. Disparadores de PostgreSQL.** Se crean con PL/pgSQL y se ejecutan también para el rol dueño de la tabla; no dependen del registro binario. Si por alguna razón no se pudieran crear, el control de inalterabilidad se mantiene con los permisos de `vales_app` (sin `UPDATE`, `DELETE` ni `TRUNCATE`). *Afecta:* Fases 6 y 8.
- [ ] **T-05. Versión de Node.js.** Se confirma con la que exija Angular 21 en el momento de crear el proyecto. *Afecta:* Fase 0.

[↑ Volver al índice](#indice)

---

<a id="s8"></a>

## 8. Cobertura de requerimientos

La matriz de trazabilidad de requerimientos y cobertura de endpoints se recalculará al cerrar el diseño de los campos OCR y sincronización entre estaciones; las cifras heredadas de versiones anteriores ya no aplican.

Requerimientos que no tienen un endpoint propio porque se cumplen con reglas internas, con procesos automáticos o en Angular:
- **VAL-14** (Fase 6)

[↑ Volver al índice](#indice)
