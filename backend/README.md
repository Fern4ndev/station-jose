# Backend — Sistema de vales San José

API con **FastAPI**, **PostgreSQL 16+** y OCR con RapidOCR para la gestión de combustible de la estación San José, Abancay. Se desarrolla en Python 3.11 o superior.

> **Estado:** Fase 1 del plan cerrada (31/10/2026). Existe la API con `GET /api/v1/salud` y `GET /api/v1/catalogos/enums` (protegido), el ejecutor de migraciones SQL numeradas (`0001_base.sql`, `0002_sesiones.sql`), errores estandarizados, CLI, pruebas automatizadas y `scripts/smoke.py --hasta 2`.
**Fase 2 cerrada (31/10/2026):** autenticación y sesiones — `POST /auth/login`, `/auth/refresh` (rotación con CSRF), `/auth/logout`, `/auth/yo`, `/auth/recuperar`, `/auth/restablecer` y `/auth/cambiar-password`; contraseñas Argon2id, limpieza crítica de límite de intentos, reCAPTCHA v3, cierre de sesión y auditoría. No existe ruta de registro: las cuentas se crean con `python -m app.cli crear-admin`.
**Fase 3 cerrada (01/11/2026):** usuarios, roles y permisos — `GET/POST/PATCH /usuarios` y `POST /usuarios/{id}/restablecer-password` con permiso `usuarios.gestionar` (solo administrador), matriz rol → permisos en `app/core/permisos.py`, dependencia `requiere_permiso(...)` en `app/dependencies.py` y la protección del último administrador (`UL´TIMO_ADMINISTRADOR`). La prueba global de autorización recorre `app.routes` y hace fallar la suite si un endpoint nuevo sale sin sesión ni permiso. 14 pruebas nuevas en `tests/test_usuarios.py` (53 en total) y `scripts/smoke.py --hasta 3` listo; su ejecución sobre la base de desarrollo queda pendiente del ajuste de permisos de [db/permisos-dev-fix.sql](db/permisos-dev-fix.sql) (pgAdmin).

## Estructura

```text
backend/
├── .env.example                 # Plantilla de configuración local
├── .gitignore                   # Ignora entorno virtual, secretos y datos privados
├── pyproject.toml               # Dependencias cerradas, entrypoint, pytest y Ruff
├── README.md                    # Esta guía
├── app/
│   ├── __init__.py
│   ├── core/                    # Seguridad, permisos, dinero, tiempo y utilidades
│   ├── db/
│   │   └── migraciones/         # Migraciones SQL numeradas (Fase 1)
│   ├── models/                  # Modelos de persistencia por dominio
│   ├── routers/                 # Rutas HTTP de la API
│   ├── schemas/                 # Esquemas de entrada y salida
│   ├── services/
│   │   └── ocr/                 # Servicio de reconocimiento OCR
│   └── web/                     # Integración para servir el frontend compilado
├── almacenamiento/              # Archivos privados de la estación y de órdenes
├── datos/
│   ├── documentos/              # Documentos para OCR (ignorados por Git)
│   └── verdad_terreno/          # Etiquetas para evaluar el OCR
├── db/
│   ├── schema.sql               # Esquema inicial PostgreSQL
│   └── seed.sql                 # Catálogos de demostración (no producción)
├── informes/                    # Salida local de informes
├── scripts/
│   └── verificar_entorno.py     # Comprobación del entorno de desarrollo
└── tests/
    └── fixtures/                # Recursos de pruebas
```

El archivo `.env` y el entorno `.venv/` no se versionan: contienen configuración local y paquetes instalados. No subas secretos, documentos reales ni datos de clientes al repositorio.

## Requisitos

- Python 3.11 o superior (probado con 3.13).
- PostgreSQL 16 o superior (probado con 18), con `psql` y `pg_dump` en el `PATH`.
- pgAdmin 4 como herramienta de administración de la base.
- Git y Node.js (los exige el frontend Angular de la raíz).
- RapidOCR con `onnxruntime`, instalado por `pyproject.toml`.

## Preparación local

Desde esta carpeta (`backend/`):

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

En Linux/macOS la activación es `source .venv/bin/activate`.

La instalación editable permite ejecutar `python -m app.cli` desde cualquier subcarpeta y mantiene una única fuente de dependencias: `pyproject.toml`. El extra `dev` agrega `pytest`, `pytest-asyncio` y `ruff`.

Copia `.env.example` a `.env` y ajusta los valores. No uses las credenciales de ejemplo en un entorno compartido o productivo.

| Variable | Uso |
| --- | --- |
| `ENTORNO` | Entorno de ejecución (`desarrollo`, `pruebas`, `produccion`) |
| `DATABASE_URL` | Conexión de la aplicación como `vales_app` (`postgresql+asyncpg://`) |
| `DATABASE_URL_TEST` | La misma conexión sobre `vales_san_jose_test` |
| `MIGRADOR_URL` | Conexión como `vales_migrador`, para aplicar migraciones y `crear-admin` |
| `MIGRADOR_URL_TEST` | La misma conexión sobre `vales_san_jose_test` |
| `OCR_DEVICE` | Dispositivo de `onnxruntime` (`cpu` en desarrollo) |
| `ALMACENAMIENTO_DIR` | Directorio de archivos privados |
| `FRONTEND_DIST` | Carpeta compilada del frontend (`../dist/frontend/browser`, relativa a `backend/`) |
| `JWT_SECRET_KEY` | Clave de firma JWT, larga y aleatoria (obligatoria fuera de desarrollo) |
| `ACCESS_TOKEN_MINUTOS` | Vida del access JWT (10) |
| `RECUPERACION_TOKEN_MINUTOS` | Vida del token de un solo uso del correo (15) |
| `FRONTEND_URL` | Base del frontend para el enlace de recuperación (vacío: solo se imprime el enlace) |
| `RECAPTCHA_SECRET_KEY` | Clave secreta de reCAPTCHA v3 (vacío: verificación local en desarrollo) |
| `RECAPTCHA_SITE_KEY` | Clave pública de reCAPTCHA que usa el frontend |
| `RECAPTCHA_UMBRAL_MINIMO` | Score mínimo aceptado (0.5) |
| `RECAPTCHA_HOSTNAME` | `hostname` esperado si difiere del host de la petición |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Correo saliente (sin `SMTP_HOST` el enlace se imprime en consola) |

## Base de datos

Dos roles de PostgreSQL: `vales_migrador` es dueño de la estructura y los disparadores; `vales_app` trabaja con permisos mínimos. Hay dos bases: `vales_san_jose` y `vales_san_jose_test` (esta última solo para pruebas).

Con `psql` como superusuario:

```sql
CREATE ROLE vales_migrador LOGIN PASSWORD 'cambiar_esta_clave';
CREATE ROLE vales_app      LOGIN PASSWORD 'cambiar_esta_clave';

CREATE DATABASE vales_san_jose      WITH ENCODING 'UTF8' TEMPLATE template0;
CREATE DATABASE vales_san_jose_test WITH ENCODING 'UTF8' TEMPLATE template0;

GRANT CONNECT ON DATABASE vales_san_jose      TO vales_migrador, vales_app;
GRANT CONNECT ON DATABASE vales_san_jose_test TO vales_migrador, vales_app;

\c vales_san_jose
GRANT CREATE, USAGE ON SCHEMA public TO vales_migrador;
GRANT USAGE         ON SCHEMA public TO vales_app;
REVOKE CREATE       ON SCHEMA public FROM PUBLIC;

\c vales_san_jose_test
GRANT CREATE, USAGE ON SCHEMA public TO vales_migrador;
GRANT USAGE         ON SCHEMA public TO vales_app;
REVOKE CREATE       ON SCHEMA public FROM PUBLIC;
```

### Migraciones versionadas (camino canónico)

La estructura vive en archivos SQL numerados en `app/db/migraciones/` y se aplica con el CLI del proyecto, que conecta con `MIGRADOR_URL`:

```powershell
python -m app.cli migrar aplicar                 # base de desarrollo
python -m app.cli migrar estado                  # qué está aplicada y qué falta
python -m app.cli migrar aplicar --test          # sobre la base de pruebas
python -m app.cli migrar nueva <nombre>          # genera el siguiente NNNN_<nombre>.sql
```

Reglas del ejecutor (`app/db/migrar.py`):

- Cada archivo se aplica dentro de una transacción (PostgreSQL permite DDL transaccional). Un archivo no transaccional se marca con `-- NO-TRANSACCIONAL` en la primera línea.
- Un archivo ya aplicado que cambie el checksum hace fallar `aplicar`: los cambios se hacen en una migración nueva.
- Bases ya pobladas con `backend/db/schema.sql` y sin registro: el ejecutor detecta `estaciones`, registra `0001` como aplicada y no la re-ejecuta.
- Esquemas legacy más antiguos (`usuarios`, `usuario_id`, `vales.codigo_interno`) no se convierten automáticamente: respalda los datos, borra los objetos y aplica las migraciones desde una base vacía.

`backend/db/schema.sql` y `backend/db/seed.sql` quedan como bootstrap manual desde pgAdmin/psql para desarrollo y para sembrar datos de demostración; la fuente de la estructura, en adelante, son las migraciones versionadas en `app/db/migraciones/`.

La estructura y los datos iniciales se aplican con `psql` y el rol `vales_migrador`, desde la raíz del repositorio:

```powershell
psql "postgresql://vales_migrador:CLAVE@127.0.0.1:5432/vales_san_jose" -v ON_ERROR_STOP=1 -f backend/db/schema.sql
```

`db/schema.sql` crea los enums de dominio y la tabla `app_users`. `db/seed.sql` es solo para desarrollo y no necesita usuarios creados previamente: inserta un administrador, un usuario de oficina y un despachador. Antes de ejecutarlo, reemplaza los hashes Argon2id de ejemplo por hashes de contraseñas conocidas. Las tres cuentas están marcadas para cambiar la contraseña en el primer inicio de sesión. Puedes ejecutar el archivo completo en pgAdmin o con `psql`:

```powershell
psql "postgresql://vales_migrador:CLAVE@127.0.0.1:5432/vales_san_jose" -v ON_ERROR_STOP=1 -f backend/db/seed.sql
```

Los vales se identifican por numeración: `numero_estacion` para los emitidos por San José y `numero_entidad` para los emitidos por una institución. En las entidades, `clave_numeracion` aplica unicidad por institución (numeración general) o por orden de compra (numeración que se reinicia en cada orden).

En `app_users`, no hay columna `active`. `must_change_password` admite `NULL`: solo `TRUE` obliga a cambiar una contraseña al ingresar; `FALSE` o `NULL` no fuerzan el cambio. Las cuentas del seed reciben `NULL`. `code` es un identificador opcional de la cuenta (por ejemplo, un código interno de personal), distinto del DNI y del correo; el seed usa códigos de demostración únicos.

El SQL de `schema.sql` define el esquema inicial y actualiza una instalación previa de `app_users` quitando `active` y permitiendo `NULL` en `must_change_password`. No convierte otros esquemas heredados automáticamente; para esos casos hace falta una migración de datos.

Además, la Fase 1 del plan agrega el ejecutor de migraciones numeradas (`app/db/migraciones/`), que se usa con `python -m app.cli migrar aplicar` y `python -m app.cli migrar estado`.

## Crear el administrador (Fase 2)

No existe ruta de registro: las cuentas nacen por CLI. `crear-admin` genera una contraseña temporal aleatoria, la imprime **una sola vez** y marca `must_change_password = TRUE`, de modo que en el primer inicio el sistema exige el cambio y restringe la API hasta completarlo (AUT-06):

```powershell
python -m app.cli crear-admin --nombre Admin --correo admin@ejemplo.pe
python -m app.cli crear-admin --nombre Admin --correo admin@ejemplo.pe --test   # base de pruebas
```

El flujo restante se hace desde `/docs`: `POST /auth/login` con la contraseña temporal → `POST /auth/cambiar-password`. Los *refresh tokens* viajan en una cookie HttpOnly bajo `/api/v1/auth` y `refresh`/`logout` validan el token CSRF de la cookie pública `csrf_token` (doble envío).

## Verificar el entorno

```powershell
python scripts/verificar_entorno.py
```

Imprime una línea por comprobación (Python, entorno virtual, dependencias, Git, Node, `psql`, `pg_dump`, pgAdmin 4, RapidOCR, servidor PostgreSQL y las cuatro conexiones) y termina con código 0 solo si todas pasan.

## Ejecutar la API

```powershell
fastapi dev app/main.py
```

La documentación interactiva quedará en `/docs` y el esquema OpenAPI en `/openapi.json`. En producción, el plan contempla `fastapi run` detrás de un proxy con HTTPS.

## Pruebas y calidad

```powershell
python -m pytest
ruff check .
```

La suite cubre el módulo de sistema (`/salud`, formato de errores y el bloqueo de `/catalogos/enums` sin sesión), `core/dinero.py`, `core/tiempo.py` y toda la Fase 2 de autenticación (`tests/test_auth.py`: límite de intentos, cambio obligatorio, rotación y reutilización de refresh, CSRF, recuperación de un solo uso, inactividad y auditoría). En la batería, reCAPTCHA queda en modo local y el correo se imprime en consola, para no depender de servicios externos. `tests/conftest.py` apunta la aplicación a la base de pruebas, aplica las migraciones con `MIGRADOR_URL_TEST` y vacía las tablas entre pruebas (desactiva los disparadores inmutables, `TRUNCATE ... RESTART IDENTITY CASCADE` y los reactiva).

El recorrido acumulado por fase, con la API corriendo:

```powershell
python scripts/smoke.py --hasta 1
python scripts/smoke.py --hasta 2      # requiere SMOKE_CORREO y SMOKE_PASSWORD de un admin ya cambiado
```

La Fase 2 del smoke verifica el bloqueo sin sesión, login correcto y erróneo, `/auth/yo` con permisos, `/catalogos/enums` con sesión, rotación del refresh con CSRF y el cierre que revoca la familia.

## Notas de diseño

- La API y el acceso a PostgreSQL son asíncronos (`asyncpg`/SQLAlchemy).
- Routers delgados, validación con Pydantic y reglas de negocio en servicios.
- Autenticación con JWT de acceso, refresh tokens revocables y contraseñas con Argon2.
- OCR, documentos y reportes se procesan en el backend; `almacenamiento/` permanece privado.
- La estructura PostgreSQL se versiona con SQL propio; el plan no contempla Alembic ni Docker.
- La especificación de implementación está en [`../plan-implementacion-backend-fastapi.md`](../plan-implementacion-backend-fastapi.md).
