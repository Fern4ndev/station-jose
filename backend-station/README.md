# San José Fuel Control API

API backend del sistema de control de combustible de la Estación de Servicio San José. Proporciona autenticación, administración de usuarios y verificaciones de salud; utiliza PostgreSQL para persistir usuarios y datos operativos.

## Tabla de contenidos

- [1. Descripción](#1-descripción-del-proyecto)
- [2. Características](#2-características-principales)
- [3. Tecnologías](#3-tecnologías-utilizadas)
- [4. Arquitectura](#4-arquitectura-del-proyecto)
- [5. Estructura](#5-estructura-de-directorios)
- [6. Requisitos](#6-requisitos-previos)
- [7. Instalación](#7-instalación)
- [8. Configuración](#8-configuración-del-entorno)
- [9. Base de datos](#9-base-de-datos)
- [10. Ejecución](#10-ejecución-del-proyecto)
- [11. Uso de la API](#11-uso-del-sistema)
- [12. Pruebas y calidad](#12-pruebas)
- [13. Convenciones](#13-convenciones-y-buenas-prácticas)
- [14. Despliegue](#14-despliegue)
- [15. Solución de problemas](#15-solución-de-problemas)
- [16. Contribución](#16-contribución)
- [17. Licencia](#17-licencia)
- [18. Autoría y contacto](#18-autoría-y-contacto)

## 1. Descripción del proyecto

Este servicio implementa la API del sistema de control de combustible de la estación. Su objetivo es proporcionar las operaciones backend necesarias para gestionar el acceso y las cuentas de usuario, y servir como base para los datos operativos de la estación.

El repositorio contiene modelos para sucursales, usuarios, tipos de combustible, órdenes de compra, vales y atenciones. No todos esos modelos tienen actualmente rutas API: las rutas implementadas se detallan en [Uso del sistema](#11-uso-del-sistema).

## 2. Características principales

- Autenticación mediante tokens JWT y cierre de sesión.
- Consulta de la identidad y permisos del usuario autenticado.
- Administración de usuarios: listado paginado, creación, consulta y actualización de datos, rol y estado.
- Control de acceso a la administración de usuarios mediante permisos.
- Comprobaciones de disponibilidad del proceso y de conexión a la base de datos.
- Migraciones de esquema con Alembic y scripts para verificar la base de datos, crear un administrador y cargar catálogos iniciales.
- Configuración de CORS y parámetros operativos mediante variables de entorno.

## 3. Tecnologías utilizadas

| Categoría | Tecnologías |
| --- | --- |
| Lenguaje | Python 3.12 o superior |
| API | FastAPI, Pydantic y pydantic-settings |
| Persistencia | PostgreSQL, SQLAlchemy 2 y Psycopg 3 |
| Migraciones | Alembic |
| Autenticación y seguridad | PyJWT y pwdlib con Argon2 |
| Pruebas y calidad | pytest, Ruff y mypy |

## 4. Arquitectura del proyecto

La aplicación es una API HTTP versionada construida con FastAPI. Las rutas reciben solicitudes y delegan operaciones de negocio a servicios; los repositorios encapsulan el acceso a datos y SQLAlchemy mapea las entidades persistidas en PostgreSQL. Los esquemas Pydantic definen la validación y las respuestas de la API.

```mermaid
flowchart LR
    Cliente --> API["FastAPI /api/v1"]
    API --> Routers["Rutas"]
    Routers --> Services["Servicios"]
    Services --> Repositories["Repositorios"]
    Repositories --> ORM["SQLAlchemy"]
    ORM --> PostgreSQL
    API --> Core["Configuración, seguridad y errores"]
    Alembic --> ORM
```

## 5. Estructura de directorios

```text
backend-station/
├── app/
│   ├── ai/                 # Espacio reservado; no contiene implementación actualmente
│   ├── core/               # Configuración, seguridad, permisos, dependencias y errores
│   ├── repositories/       # Acceso a datos
│   ├── routers/            # Rutas de salud, autenticación y usuarios
│   ├── schemas/            # Modelos de entrada y salida de la API
│   ├── services/           # Lógica de autenticación y usuarios
│   ├── database.py         # Motor, sesiones y base ORM
│   ├── main.py             # Aplicación FastAPI
│   └── tables.py           # Entidades y relaciones SQLAlchemy
├── alembic/
│   └── versions/           # Migraciones versionadas del esquema
├── db/
│   ├── schema.sql          # Definición SQL del esquema
│   └── seed.sql            # Datos de demostración
├── scripts/                # Utilidades de base de datos y administración
├── storage/ocr_tmp/        # Directorio de almacenamiento temporal de OCR
├── tests/
│   ├── api/                # Pruebas de contrato y salud de la API
│   ├── concurrency/        # Espacio para pruebas de concurrencia
│   ├── integration/        # Espacio para pruebas de integración
│   └── unit/               # Pruebas unitarias
├── .env.example            # Ejemplo de configuración local
├── alembic.ini             # Configuración de Alembic
├── pyproject.toml          # Metadatos, dependencias de desarrollo y herramientas
├── requirements.txt        # Dependencias de ejecución
└── requirements-dev.txt    # Dependencias de desarrollo y pruebas
```

## 6. Requisitos previos

- Python 3.12 o superior.
- PostgreSQL accesible desde el entorno donde se ejecuta la API.
- `pip` y `venv`, incluidos en las distribuciones habituales de Python.

Docker y archivos de configuración de contenedores no están incluidos en este backend.

## 7. Instalación

Desde el directorio `backend-station`, crea y activa un entorno virtual e instala las dependencias de desarrollo:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

En Linux o macOS, activa el entorno con:

```bash
source .venv/bin/activate
```

Después, configura el entorno según la sección siguiente y prepara PostgreSQL antes de aplicar la migración.

## 8. Configuración del entorno

La configuración se lee de variables de entorno o de un archivo `.env` en el directorio de trabajo. Para desarrollo, parte del archivo de ejemplo:

```powershell
Copy-Item .env.example .env
```

Edita `.env` con los datos de tu entorno. Los siguientes ejemplos son ilustrativos; reemplaza los valores de conexión y secretos. En producción, define un `JWT_SECRET_KEY` aleatorio de al menos 32 caracteres.

| Variable | Descripción | Ejemplo |
| --- | --- | --- |
| `APP_NAME` | Nombre de la aplicación | `San Jose Fuel Control API` |
| `APP_ENV` | Entorno: `development`, `testing` o `production` | `development` |
| `DEBUG` | Activa el modo de depuración | `false` |
| `API_V1_PREFIX` | Prefijo de las rutas versionadas | `/api/v1` |
| `TIMEZONE` | Zona horaria configurada | `America/Lima` |
| `DATABASE_URL` | URL de conexión SQLAlchemy a PostgreSQL | `postgresql+psycopg://usuario:clave-local@localhost:5432/sanjosedb` |
| `JWT_SECRET_KEY` | Secreto de firma JWT | `reemplazar-por-un-secreto-aleatorio-de-32-caracteres` |
| `JWT_ALGORITHM` | Algoritmo JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración del token de acceso, entre 1 y 1440 minutos | `30` |
| `JWT_ISSUER` | Emisor declarado en el token | `san-jose-api` |
| `CORS_ORIGINS` | Orígenes permitidos, separados por comas | `http://localhost:4200` |
| `LOG_LEVEL` | Nivel de registro: `DEBUG`, `INFO`, `WARNING`, `ERROR` o `CRITICAL` | `INFO` |
| `OCR_ENABLED` | Indicador de configuración de OCR | `true` |
| `OCR_MAX_UPLOAD_BYTES` | Límite configurado de carga en bytes | `10485760` |
| `OCR_MAX_PDF_PAGES` | Máximo configurado de páginas PDF | `20` |
| `OCR_TIMEOUT_SECONDS` | Tiempo límite configurado para OCR | `60` |
| `OCR_TEMP_DIR` | Directorio temporal configurado para OCR | `/tmp/san-jose-ocr` |

Los parámetros OCR están disponibles en la configuración, pero actualmente no hay rutas de OCR expuestas por la API.

## 9. Base de datos

PostgreSQL es el motor de persistencia. `DATABASE_URL` debe usar el controlador `postgresql+psycopg` y apuntar a una base de datos ya creada. Por ejemplo, con `psql`:

```sql
CREATE DATABASE sanjosedb;
```

Aplica la migración inicial y cualquier migración posterior con Alembic:

```powershell
alembic upgrade head
```

La migración `0001_initial_schema` crea las tablas declaradas por los modelos SQLAlchemy. Para comprobar la conexión:

```powershell
python scripts/check_db.py
```

Para cargar las sucursales y tipos de combustible definidos por el script:

```powershell
python scripts/seed_catalogs.py
```

El archivo `db/seed.sql` contiene datos de demostración; úsalo únicamente en desarrollo. Para crear el primer usuario administrador, el script requiere los datos por argumentos:

```powershell
python scripts/create_admin.py --first-name "Nombre" --last-name "Apellido" --dni "DNI-DE-PRUEBA" --email "admin@example.test" --password "CAMBIAR-POR-UNA-CLAVE-SEGURA"
```

No uses credenciales reales en comandos visibles o guardados en el historial del shell. El script no crea otro administrador si ya existe uno.

## 10. Ejecución del proyecto

Con el entorno virtual activo, PostgreSQL preparado y `.env` configurado, inicia el servidor de desarrollo:

```powershell
fastapi dev
```

La aplicación se configura en `app.main:app`. La documentación interactiva de FastAPI queda disponible por defecto en `http://localhost:8000/docs`; el esquema OpenAPI está en `http://localhost:8000/openapi.json`.

## 11. Uso del sistema

Las rutas de la API tienen el prefijo `API_V1_PREFIX` (por defecto `/api/v1`).

| Método | Ruta | Descripción | Acceso |
| --- | --- | --- | --- |
| `GET` | `/api/v1/health/live` | Comprueba que el proceso responde | Público |
| `GET` | `/api/v1/health/ready` | Comprueba la conexión con PostgreSQL | Público |
| `POST` | `/api/v1/auth/login` | Inicia sesión y devuelve un token | Público |
| `POST` | `/api/v1/auth/logout` | Cierra la sesión del token actual | Autenticado |
| `GET` | `/api/v1/auth/me` | Devuelve el usuario actual y sus permisos | Autenticado |
| `GET` | `/api/v1/users` | Lista usuarios con paginación | Requiere `users.manage` |
| `POST` | `/api/v1/users` | Crea un usuario | Requiere `users.manage` |
| `GET` | `/api/v1/users/{user_id}` | Consulta un usuario por UUID | Requiere `users.manage` |
| `PATCH` | `/api/v1/users/{user_id}` | Actualiza datos del usuario | Requiere `users.manage` |
| `PATCH` | `/api/v1/users/{user_id}/role` | Cambia el rol del usuario | Requiere `users.manage` |
| `PATCH` | `/api/v1/users/{user_id}/status` | Cambia el estado del usuario | Requiere `users.manage` |

Las rutas protegidas utilizan el encabezado `Authorization: Bearer <token>`. El listado acepta `page` (mínimo 1) y `page_size` (entre 1 y 100; por defecto 20). Los esquemas de solicitud y respuesta están disponibles en `/docs`.

Ejemplo de comprobación de salud:

```bash
curl http://localhost:8000/api/v1/health/live
```

Las rutas de órdenes, vales y atenciones no están implementadas en los routers actuales, aunque existen modelos de datos relacionados.

## 12. Pruebas

Las pruebas automatizadas usan pytest. Desde `backend-station`:

```powershell
pytest
```

Para ejecutar una prueba o grupo específico:

```powershell
pytest tests\api\test_health.py
pytest tests\unit
```

Las herramientas configuradas para estilo, formato y tipado son Ruff y mypy:

```powershell
ruff check .
ruff format --check .
mypy app
```

## 13. Convenciones y buenas prácticas

- Mantén las rutas HTTP en `app/routers`, la lógica de negocio en `app/services` y el acceso a datos en `app/repositories`.
- Usa esquemas Pydantic para validar entradas y definir respuestas, y modelos SQLAlchemy para persistencia.
- Gestiona cambios de esquema mediante migraciones de Alembic.
- Ruff aplica reglas `E`, `F`, `I`, `B` y `UP`, con longitud de línea de 100 caracteres y objetivo Python 3.12.
- mypy está configurado en modo estricto.
- No se encontró una convención de formato de commits definida en la configuración del proyecto.

## 14. Despliegue

El repositorio no incluye Docker ni una configuración de despliegue. Para ejecutar la aplicación en producción, configura un PostgreSQL accesible y las variables de entorno necesarias, usa un `APP_ENV=production` y establece un secreto JWT de al menos 32 caracteres. No expongas el archivo `.env` ni las credenciales.

La configuración de ejecución en producción y su infraestructura quedan pendientes de documentar cuando se definan.

## 15. Solución de problemas

- **La comprobación `/health/ready` falla:** verifica que PostgreSQL esté disponible y que `DATABASE_URL` apunte al host, puerto y base correctos. Puedes probar la conexión con `python scripts/check_db.py`.
- **La aplicación rechaza la configuración en producción:** comprueba que `APP_ENV` sea un valor admitido y que `JWT_SECRET_KEY` tenga al menos 32 caracteres.
- **Un origen del frontend no puede acceder a la API:** verifica que su URL esté incluida en `CORS_ORIGINS`; pueden indicarse varios orígenes separados por comas.

## 16. Contribución

1. Crea una rama a partir de la rama de trabajo del repositorio.
2. Realiza cambios acotados, siguiendo la organización y las convenciones descritas.
3. Ejecuta `pytest`, `ruff check .`, `ruff format --check .` y `mypy app`.
4. Envía los cambios mediante un Pull Request con una descripción del cambio y de las verificaciones realizadas.

No se encontró una guía de contribución ni una convención de nombres de ramas específica.

## 17. Licencia

La licencia del proyecto está pendiente de definir.

## 18. Autoría y contacto

La información de autoría y contacto está pendiente de definir.
