"""Estado del sistema: backend, PostgreSQL y RapidOCR."""

import importlib
import importlib.metadata

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.sesion import SesionBd

router = APIRouter(tags=["sistema"])

ESTADO_OK = "ok"
ESTADO_DEGRADADO = "degradado"
ESTADO_ERROR = "error"


def _version_ocr() -> str:
    """Devuelve la versión de RapidOCR o `error` si no se puede importar."""
    try:
        importlib.import_module("rapidocr")
        return importlib.metadata.version("rapidocr")
    except (ImportError, importlib.metadata.PackageNotFoundError):
        return ESTADO_ERROR


@router.get("/salud")
async def salud(sesion: SesionBd) -> dict[str, str]:
    """Informa el estado de la API sin exponer datos sensibles."""
    try:
        await sesion.execute(text("SELECT 1"))
        version_base = str((await sesion.execute(text("SHOW server_version"))).scalar_one())
        base = ESTADO_OK
    except SQLAlchemyError:
        version_base = ""
        base = ESTADO_ERROR

    ocr = _version_ocr()
    todo_ok = base == ESTADO_OK and ocr != ESTADO_ERROR

    respuesta = {
        "estado": ESTADO_OK if todo_ok else ESTADO_DEGRADADO,
        "base": base,
        "ocr": ocr,
        "version": f"PostgreSQL {version_base}" if version_base else "",
    }
    return {clave: valor for clave, valor in respuesta.items() if valor}
