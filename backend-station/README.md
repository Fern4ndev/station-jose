# San José Fuel Control API

Backend FastAPI del sistema de control de combustible de la Estación de Servicio San José.

## Desarrollo local

1. Crear un entorno virtual e instalar las dependencias:

   ```bash
   python -m venv .venv
   ```

   En Windows:

   ```powershell
   .venv\\Scripts\\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements-dev.txt
   ```

2. Copiar `.env.example` a `.env` y configurar `DATABASE_URL` para tu instancia local de PostgreSQL.
3. Ejecutar las migraciones cuando existan migraciones de dominio:

   ```bash
   alembic upgrade head
   ```

4. Ejecutar la API:

   ```bash
   fastapi dev
   ```

La documentación queda disponible en `http://localhost:8000/docs`.

## Calidad

```bash
pytest
ruff check .
ruff format --check .
mypy app
```

`GET /api/v1/health/live` valida que el proceso esté activo. `GET /api/v1/health/ready` valida además la conexión a PostgreSQL.

Las entidades y migraciones de negocio se incorporarán en F2. Alembic es la única fuente versionada del esquema. Este proyecto no utiliza Docker; PostgreSQL debe estar instalado y ejecutándose localmente o en un servidor accesible.
