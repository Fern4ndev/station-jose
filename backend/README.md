# Backend — Sistema de vales San José

API con **FastAPI**, **PostgreSQL 16+** y OCR con RapidOCR para la gestión de combustible de la estación San José, Abancay. Se desarrolla en Python 3.11 o superior.

> **Estado:** Fase 0 del plan completada (entorno, repositorio, dependencias y base de datos). Los módulos `app/` todavía no contienen la API: `app.main:app` se crea en la Fase 1, igual que el ejecutor de migraciones.

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
| `MIGRADOR_URL` | Conexión como `vales_migrador`, para aplicar migraciones |
| `MIGRADOR_URL_TEST` | La misma conexión sobre `vales_san_jose_test` |
| `OCR_DEVICE` | Dispositivo de `onnxruntime` (`cpu` en desarrollo) |
| `ALMACENAMIENTO_DIR` | Directorio de archivos privados |
| `FRONTEND_DIST` | Carpeta compilada del frontend (`../dist/frontend/browser`, relativa a `backend/`) |
| `JWT_SECRET_KEY` | Clave de firma JWT, larga y aleatoria |
| `RECAPTCHA_SECRET_KEY` | Clave secreta de reCAPTCHA v3 |
| `RECAPTCHA_SITE_KEY` | Clave pública de reCAPTCHA que usa el frontend |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Correo saliente |

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

La estructura y los datos iniciales se aplican con `psql` y el rol `vales_migrador`, desde la raíz del repositorio:

```powershell
psql "postgresql://vales_migrador:CLAVE@127.0.0.1:5432/vales_san_jose" -v ON_ERROR_STOP=1 -f backend/db/schema.sql
```

`db/schema.sql` crea los enums de dominio y la tabla `app_users`. `db/seed.sql` es solo para desarrollo y no necesita un usuario creado previamente: inserta un administrador inicial con un hash Argon2id. Antes de ejecutarlo, reemplaza el hash de ejemplo por uno generado para la contraseña deseada. Puedes ejecutar el archivo completo en pgAdmin o con `psql`:

```powershell
psql "postgresql://vales_migrador:CLAVE@127.0.0.1:5432/vales_san_jose" -v ON_ERROR_STOP=1 -f backend/db/seed.sql
```

Los vales se identifican por numeración: `numero_estacion` para los emitidos por San José y `numero_entidad` para los emitidos por una institución. En las entidades, `clave_numeracion` aplica unicidad por institución (numeración general) o por orden de compra (numeración que se reinicia en cada orden).

El SQL de `schema.sql` define el esquema inicial; no convierte automáticamente una base creada con la estructura anterior. Para una base existente hace falta una migración de datos antes de usar esta versión.

Además, la Fase 1 del plan agrega el ejecutor de migraciones numeradas (`app/db/migraciones/`), que se usa con `python -m app.cli migrar aplicar` y `python -m app.cli migrar estado`.

## Verificar el entorno

```powershell
python scripts/verificar_entorno.py
```

Imprime una línea por comprobación (Python, entorno virtual, dependencias, Git, Node, `psql`, `pg_dump`, pgAdmin 4, RapidOCR, servidor PostgreSQL y las cuatro conexiones) y termina con código 0 solo si todas pasan.

## Ejecutar la API

El entrypoint `app.main:app` se crea en la Fase 1. Cuando exista:

```powershell
fastapi dev app/main.py
```

La documentación interactiva quedará en `/docs` y el esquema OpenAPI en `/openapi.json`. En producción, el plan contempla `fastapi run` detrás de un proxy con HTTPS.

## Pruebas y calidad

```powershell
python -m pytest
ruff check .
```

Ambos comandos están configurados en `pyproject.toml` y todavía no tienen casos: las primeras pruebas llegan con la Fase 1.

## Notas de diseño

- La API y el acceso a PostgreSQL son asíncronos (`asyncpg`/SQLAlchemy).
- Routers delgados, validación con Pydantic y reglas de negocio en servicios.
- Autenticación con JWT de acceso, refresh tokens revocables y contraseñas con Argon2.
- OCR, documentos y reportes se procesan en el backend; `almacenamiento/` permanece privado.
- La estructura PostgreSQL se versiona con SQL propio; el plan no contempla Alembic ni Docker.
- La especificación de implementación está en [`../plan-implementacion-backend-fastapi.md`](../plan-implementacion-backend-fastapi.md).
