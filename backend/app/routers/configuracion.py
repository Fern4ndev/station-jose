"""Configuración del sistema: parámetros, ficha de la estación y logo.

`GET /configuracion/parametros` y la estación de `config.gestionar`; los
datos y el logo de la estación se leen con `estacion.ver` (plan sección 5.4).
"""

from collections.abc import Callable

from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import Response

from app.db.sesion import SesionBd
from app.dependencies import (
    UsuarioAutenticado,
    ip_de_peticion,
    requiere_permiso,
    user_agent_de_peticion,
)
from app.errors import ErrorDominio
from app.schemas.configuracion import (
    EstacionDatos,
    EstacionSalida,
    LogoSubido,
    ParametroDetalle,
    ParametrosEntrada,
    ParametrosGuardados,
    ParametrosLista,
)
from app.services import configuracion as servicio

router = APIRouter(prefix="/configuracion", tags=["configuracion"])


def _gestionar() -> Callable:
    return requiere_permiso("config.gestionar")


def _ver_estacion() -> Callable:
    return requiere_permiso("estacion.ver")


@router.get("/parametros", response_model=ParametrosLista)
async def listar_parametros(
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_gestionar()),  # noqa: B008
) -> ParametrosLista:
    """CFG-01: cada parámetro con valor vigente, tipo, rango y descripción."""
    items = await servicio.parametros_actuales(sesion)
    return ParametrosLista(items=[ParametroDetalle(**item) for item in items])


@router.put("/parametros", response_model=ParametrosGuardados)
async def guardar_parametros(
    peticion: ParametrosEntrada,
    request: Request,
    sesion: SesionBd,
    gestionador: UsuarioAutenticado = Depends(_gestionar()),  # noqa: B008
) -> ParametrosGuardados:
    """CFG-01: valida tipo y rango, guarda y rige de inmediato; queda auditado."""
    valores = await servicio.guardar_parametros(
        sesion,
        peticion.valores,
        actor_id=gestionador.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return ParametrosGuardados(valores=valores)


@router.get("/estacion", response_model=EstacionSalida)
async def obtener_estacion(
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_ver_estacion()),  # noqa: B008
) -> EstacionSalida:
    """CFG-02: datos que usan comprobantes y vistas de impresión; 404 si falta la ficha."""
    fila = await servicio.obtener_estacion(sesion)
    if fila is None:
        raise ErrorDominio(
            404, "RECURSO_NO_ENCONTRADO", "Aún no se registran los datos de la estación."
        )
    return EstacionSalida(**fila)


@router.put("/estacion", response_model=EstacionSalida)
async def guardar_estacion(
    peticion: EstacionDatos,
    request: Request,
    sesion: SesionBd,
    gestionador: UsuarioAutenticado = Depends(_gestionar()),  # noqa: B008
) -> EstacionSalida:
    """CFG-02: crea o actualiza la ficha única de la estación."""
    fila = await servicio.guardar_estacion(
        sesion,
        nombre=peticion.nombre,
        ruc=peticion.ruc,
        direccion=peticion.direccion,
        telefono=peticion.telefono,
        correo=peticion.correo,
        actor_id=gestionador.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return EstacionSalida(**fila)


@router.post("/estacion/logo", response_model=LogoSubido, status_code=201)
async def subir_logo(
    archivo: UploadFile,
    request: Request,
    sesion: SesionBd,
    gestionador: UsuarioAutenticado = Depends(_gestionar()),  # noqa: B008
) -> LogoSubido:
    """CFG-02: PNG o JPG validados por contenido, hasta 1 MB."""
    # Un byte de reserva delimita la lectura: nunca carga un archivo mayor
    # que el máximo en memoria para luego rechazarlo por grande.
    datos = await archivo.read(servicio.LOGO_MAX_BYTES + 1)
    resultado = await servicio.subir_logo(
        sesion,
        datos,
        actor_id=gestionador.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return LogoSubido(**resultado)


@router.get("/estacion/logo")
async def descargar_logo(
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_ver_estacion()),  # noqa: B008
) -> Response:
    """CFG-02: bytes del logo con su tipo real; 404 si nunca se subió."""
    contenido = await servicio.leer_logo(sesion)
    if contenido is None:
        raise ErrorDominio(
            404, "RECURSO_NO_ENCONTRADO", "La estación no tiene logo registrado."
        )
    datos, media = contenido
    return Response(
        content=datos,
        media_type=media,
        headers={
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
        },
    )
