# Sistema de vales de combustible — Estación San José

Sistema web con lectura OCR para la gestión de combustible institucional de la estación de servicio San José (Abancay). Repositorio único con dos aplicaciones: el frontend Angular vive en la **raíz** y la API FastAPI en `backend/`.

## Composición del repositorio

```text
station-jose/
├── angular.json  package.json  tsconfig*.json   # proyecto Angular (raíz)
├── src/  public/                                # código y estáticos del frontend
├── backend/                                     # FastAPI, PostgreSQL y OCR
├── requerimientos-funcionales-sistema.md
├── plan-implementacion-backend-fastapi.md
└── plan-implementacion-frontend-angular.md
```

| Parte | Tecnología | Entrada |
| --- | --- | --- |
| Frontend | Angular 21 (SPA, standalone, zoneless), PrimeNG 21, Tailwind 4, `iconify-icon` | `src/main.ts` |
| Backend | FastAPI, SQLAlchemy/SQLModel async, PostgreSQL 16, RapidOCR | `backend/app/main.py` |
| Base de datos | SQL versionado a mano en `backend/db/` | `backend/db/schema.sql` |

## Estado

Etapa inicial. La documentación de diseño está completa (requerimientos + planes de backend y frontend, cada uno con 15 fases/bloques); la implementación recién comienza.

## Frontend — desarrollo

Requiere Node.js en la versión que exija Angular 21 (`ng version` la muestra).

```bash
npm install
npm start
```

La aplicación queda en `http://localhost:4200/`. En desarrollo, `proxy.conf.json` dirige `/api` hacia `http://127.0.0.1:8000`.

```bash
npm run build     # compila a dist/frontend/browser
npm test          # Vitest
```

## Backend — desarrollo

Requisitos y preparación detallada en [`backend/README.md`](backend/README.md). Resumen:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

La API aún no tiene entrypoint (`backend/app/main.py` no existe). Cuando se implemente:

```powershell
fastapi dev app/main.py
```

Documentación interactiva en `http://127.0.0.1:8000/docs`.

## Despliegue

Un solo origen: el backend sirve los archivos estáticos de Angular desde `../dist/frontend/browser` (variable `FRONTEND_DIST`) y la API responde bajo `/api/v1`. No hay CORS en producción.

## Documentación

- [`requerimientos-funcionales-sistema.md`](requerimientos-funcionales-sistema.md) — especificación funcional v3.0.
- [`plan-implementacion-backend-fastapi.md`](plan-implementacion-backend-fastapi.md) — 15 fases, catálogo de 93 endpoints.
- [`plan-implementacion-frontend-angular.md`](plan-implementacion-frontend-angular.md) — 15 bloques, rutas y contrato de la API.
- [`AGENTS.md`](AGENTS.md) — convenciones de código Angular del proyecto.
