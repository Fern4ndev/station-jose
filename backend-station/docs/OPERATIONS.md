# Guía operativa de producción

## Alcance

El backend se ejecuta nativamente en Windows con Python, `venv`, FastAPI y PostgreSQL. No se utiliza Docker ni Alembic.

## Instalación reproducible

Desde `backend-station`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Configura en `.env`:

- `APP_ENV=production`
- `DEBUG=false`
- `DATABASE_URL` apuntando a PostgreSQL
- `JWT_SECRET_KEY` con al menos 32 caracteres aleatorios
- `CORS_ORIGINS` con orígenes explícitos, sin `*`
- `OCR_TEMP_DIR` en una carpeta temporal con permisos restringidos

## Base de datos

Para una base nueva, aplica en este orden:

```powershell
psql -U postgres -d sanjose -v ON_ERROR_STOP=1 -f db/001_schema.sql
```

`db/002_seed.sql` contiene datos y cuentas de demostración: úsalo exclusivamente en desarrollo o pruebas, nunca en producción. Prepara los catálogos y la cuenta inicial de producción mediante un procedimiento autorizado.

Para una base existente aplica únicamente los ALTER pendientes, en orden numérico. Cada ALTER debe probarse dos veces antes de producción. Verifica que el esquema consolidado coincida con una instalación nueva desde `001`.

## Arranque

Desarrollo:

```powershell
fastapi dev
```

Producción detrás de un proxy HTTPS:

```powershell
fastapi run
```

El TLS/HTTPS debe terminar en el proxy o balanceador. La API no debe exponerse directamente a Internet sin HTTPS, firewall y control de acceso de red.

## Verificaciones previas al despliegue

1. Ejecutar `pytest`.
2. Ejecutar `ruff check .` y `ruff format --check .`.
3. Ejecutar `mypy app`.
4. Consultar `/api/v1/health/live`.
5. Consultar `/api/v1/health/ready` con PostgreSQL disponible.
6. Revisar `/docs` y `/openapi.json` en el entorno de pruebas.
7. Ejecutar los escenarios de atención parcial y concurrencia contra PostgreSQL real.
8. Confirmar que `CORS_ORIGINS` solo contiene los frontends autorizados.
9. Confirmar que el usuario de PostgreSQL no tiene permisos administrativos innecesarios.
10. Confirmar que los logs no contienen tokens, contraseñas ni payloads sensibles.

## Backup

Usa `scripts/backup_db.ps1` con una cuenta que pueda ejecutar `pg_dump`. El script utiliza el mecanismo de autenticación de PostgreSQL configurado en el equipo; no guardes contraseñas en el script ni en el repositorio.

```powershell
.\scripts\backup_db.ps1 -Database sanjose -OutputFile .\backups\sanjose-2026-01-01.dump
```

Conserva los backups fuera del equipo de la aplicación y define una política de retención antes de producción.

## Restauración

La restauración debe probarse primero en una base aislada:

```powershell
.\scripts\restore_db.ps1 -Database sanjose_restore -InputFile .\backups\sanjose-2026-01-01.dump
```

Después ejecuta los health checks, valida conteos y revisa los casos críticos de órdenes, vales y atenciones. No restaures sobre producción sin una ventana aprobada y un backup previo.

## Seguridad operacional

- No usar el secreto JWT de desarrollo en producción.
- No usar `CORS_ORIGINS=*` en producción.
- Mantener HTTPS obligatorio en el proxy.
- Restringir PostgreSQL a la red de la aplicación.
- Mantener `OCR_MAX_UPLOAD_BYTES`, `OCR_MAX_PDF_PAGES`, `OCR_TIMEOUT_SECONDS` y `REPORT_MAX_EXPORT_ROWS` con valores aprobados.
- Los despachos confirmados son inmutables; las correcciones cuantitativas requieren un procedimiento aprobado.
- Los reportes y exportaciones no están disponibles para `ATTENDANT`.
