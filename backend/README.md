# Backend — Sistema de vales San José

API prevista con **FastAPI**, **PostgreSQL 16+** y procesamiento OCR con RapidOCR para el sistema de gestión de combustible de la estación San José, Abancay. El backend se desarrolla en Python 3.11 o superior.

> **Estado:** la estructura está en etapa inicial. Actualmente hay archivos SQL para el esquema y datos de demostración, dependencias declaradas y paquetes Python preparados. Los módulos de aplicación aún no contienen la API, lógica de negocio ni comandos funcionales; por tanto, los comandos de arranque de FastAPI indicados más abajo quedarán disponibles cuando se implemente `app.main:app`.

## Estructura actual

```text
backend/
├── .env.example                 # Plantilla de configuración local
├── .gitignore                   # Ignora entorno virtual, secretos y datos privados
├── README.md                    # Esta guía
├── requirements.txt             # Dependencias fijadas del proyecto
├── requirements-dev.txt         # Dependencias de desarrollo (incluye requirements.txt)
├── app/
│   ├── __init__.py
│   ├── core/
│   │   └── __init__.py          # Seguridad, permisos, dinero, tiempo y utilidades
│   ├── db/
│   │   ├── __init__.py
│   │   └── migraciones/
│   │       └── .gitkeep          # Reservado para migraciones SQL versionadas
│   ├── models/
│   │   └── __init__.py          # Modelos de persistencia por dominio
│   ├── routers/
│   │   └── __init__.py          # Rutas HTTP de la API
│   ├── schemas/
│   │   └── __init__.py          # Esquemas de entrada y salida
│   ├── services/
│   │   ├── __init__.py
│   │   └── ocr/
│   │       └── __init__.py      # Servicio de reconocimiento OCR
│   └── web/
│       └── __init__.py          # Integración futura para servir el frontend
├── almacenamiento/
│   ├── estacion/
│   │   └── .gitkeep              # Archivos privados de la estación
│   └── ordenes/
│       └── .gitkeep              # Documentos de órdenes de compra
├── datos/
│   ├── documentos/
│   │   └── .gitkeep              # Documentos para OCR (ignorados por Git)
│   └── verdad_terreno/
│       └── .gitkeep              # Etiquetas/datos de evaluación OCR
├── db/
│   ├── schema.sql                # Esquema inicial PostgreSQL
│   └── seed.sql                  # Catálogos/datos de demostración; no producción
├── informes/
│   └── .gitkeep                  # Salida local de informes
├── scripts/
│   └── .gitkeep                  # Scripts auxiliares futuros
└── tests/
    ├── __init__.py
    └── fixtures/
        └── .gitkeep              # Recursos de pruebas futuros
```

El archivo local `.env` y el entorno `.venv/` no se incluyen en el árbol porque contienen configuración local y paquetes instalados. No subas secretos, documentos reales ni datos de clientes al repositorio.

## Requisitos

- Python 3.11 o superior.
- PostgreSQL 16 o superior.
- `pip` actualizado.
- Para OCR se instalarán RapidOCR y sus dependencias declaradas en `requirements.txt`.

## Preparación local

Desde esta carpeta (`backend/`), crea y activa un entorno virtual:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

En Linux/macOS, activa con `source .venv/bin/activate`.

Copia `.env.example` a `.env` y ajusta los valores a tu entorno. Como mínimo, configura `DATABASE_URL`, `MIGRADOR_URL` y `JWT_SECRET_KEY`. No uses las credenciales de ejemplo en un entorno compartido o productivo. La plantilla contiene `ENVIROMENT` (con esa grafía); conserva el nombre que espera la configuración hasta que se implemente y confirme `Settings`.

Variables de la plantilla:

| Variable | Uso |
| --- | --- |
| `APP_NAME` | Nombre visible de la API |
| `ENVIROMENT` | Entorno de ejecución (development/production) |
| `API_V1_PREFIX` | Prefijo de las rutas versionadas |
| `CORS_ORIGINS` | Orígenes de frontend permitidos, separados por coma |
| `DATABASE_URL` | Conexión asíncrona de la aplicación (`postgresql+asyncpg://`) |
| `MIGRADOR_URL` | Conexión con permisos para aplicar el esquema |
| `ALMACENAMIENTO_DIR` | Directorio de archivos privados |
| `FRONTEND_DIST` | Carpeta compilada del frontend para producción (`../dist/frontend/browser`, relativa a `backend/`) |
| `JWT_SECRET_KEY` | Clave de firma JWT, larga y aleatoria |
| `RECAPTCHA_SECRET_KEY` | Clave secreta de reCAPTCHA |
| `RECAPTCHA_SITE_KEY` | Clave pública de reCAPTCHA asociada al frontend |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Parámetros de correo saliente |

## Base de datos

La aplicación está diseñada para usar dos roles PostgreSQL: `vales_migrador`, propietario del esquema y encargado de cambios estructurales, y `vales_app`, con permisos de ejecución limitados. Crea la base y ambos roles en PostgreSQL antes de configurar sus URL. El esquema requiere PostgreSQL 16+.

Desde la raíz del repositorio, ejecuta el esquema con un cliente PostgreSQL y el usuario migrador:

```powershell
psql "postgresql://vales_migrador:CONTRASENA@127.0.0.1:5432/san_jose" -v ON_ERROR_STOP=1 -f backend/db/schema.sql
```

El SQL inicial otorga permisos al rol de aplicación, que debe existir previamente. Para cargar datos demostrativos, crea primero un administrador válido desde la aplicación cuando ese comando esté implementado; luego:

```powershell
psql "postgresql://vales_migrador:CONTRASENA@127.0.0.1:5432/san_jose" -v ON_ERROR_STOP=1 -f backend/db/seed.sql
```

`seed.sql` es solo para desarrollo/demo y requiere que exista un administrador activo. No lo ejecutes en producción. El esquema actual documenta idempotencia para uso de desarrollo; revisa los SQL antes de volver a aplicarlos sobre una base con datos.

## Ejecutar la API

El entrypoint `app.main:app` todavía no existe. Cuando se implemente, el modo de desarrollo previsto será:

```powershell
fastapi dev app/main.py
```

La documentación interactiva estará en `/docs` y el esquema OpenAPI en `/openapi.json`, una vez levantada la aplicación. Para producción, el plan contempla `fastapi run app/main.py` detrás de un servidor/proxy configurado para HTTPS.

## Pruebas y calidad

Las dependencias de pytest, pytest-asyncio y Ruff ya están fijadas. Aún no hay pruebas funcionales implementadas. Cuando se agreguen:

```powershell
python -m pytest
ruff check .
```

## Notas de diseño

- La API y acceso a PostgreSQL serán asíncronos (`asyncpg`/SQLAlchemy).
- Se planea mantener routers delgados, validación con Pydantic y reglas de negocio en servicios.
- La autenticación prevista combina JWT de acceso, refresh tokens revocables y contraseñas con Argon2.
- OCR, documentos y reportes se procesarán en el backend; `almacenamiento/` debe permanecer privado.
- La estructura PostgreSQL se versionará con SQL; el plan del proyecto no contempla Alembic ni Docker.
- La especificación de implementación está en [`../plan-implementacion-backend-fastapi.md`](../plan-implementacion-backend-fastapi.md).
