"""Entrega la aplicación Angular compilada en el mismo origen de la API."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import obtener_settings

RUTAS_BACKEND = frozenset({"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"})


def _cabeceras(nombre: str) -> dict[str, str]:
    """Usa caché larga solo para assets con hash de Angular."""
    tiene_hash = any(
        len(parte) >= 16 and all(caracter in "0123456789abcdef" for caracter in parte.lower())
        for parte in Path(nombre).stem.replace("-", ".").split(".")
    )
    return {
        "Cache-Control": "public, max-age=31536000, immutable" if tiene_hash else "no-cache"
    }


class MiddlewareFrontend(BaseHTTPMiddleware):
    """Resuelve rutas Angular sin interferir con el estado HTTP de las APIs."""

    def __init__(self, app, *, raiz: Path, prefijo_api: str) -> None:
        super().__init__(app)
        self.raiz = raiz
        self.indice = raiz / "index.html"
        self.prefijo_api = prefijo_api.rstrip("/")

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        ruta = request.url.path
        if (
            request.method != "GET"
            or ruta in RUTAS_BACKEND
            or ruta == "/api"
            or ruta.startswith("/api/")
            or ruta == self.prefijo_api
            or ruta.startswith(f"{self.prefijo_api}/")
        ):
            return await call_next(request)

        relativa = ruta.lstrip("/")
        candidato = (self.raiz / relativa).resolve()
        if relativa and self.raiz in candidato.parents and candidato.is_file():
            return FileResponse(candidato, headers=_cabeceras(candidato.name))
        return FileResponse(self.indice, headers={"Cache-Control": "no-cache"})


def registrar_frontend(app: FastAPI) -> None:
    """Registra fallback SPA solo si existe un build completo de Angular."""
    ajustes = obtener_settings()
    raiz = ajustes.frontend_dist.resolve()
    if raiz.is_dir() and (raiz / "index.html").is_file():
        app.add_middleware(
            MiddlewareFrontend, raiz=raiz, prefijo_api=ajustes.api_v1_prefix
        )
