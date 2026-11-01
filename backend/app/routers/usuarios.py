"""Gestión de usuarios y roles (M02, plan sección 5.3).

Todo el módulo exige el permiso `usuarios.gestionar` (solo el administrador).
`GET /usuarios` acepta `q`, `rol` y paginación; `POST` devuelve la contraseña
temporal una sola vez; `PATCH` protege al último administrador (USR-07).
"""

from collections.abc import Callable

from fastapi import APIRouter, Depends, Request

from app.core.dominio import ROLES
from app.db.sesion import SesionBd
from app.dependencies import (
    UsuarioAutenticado,
    ip_de_peticion,
    requiere_permiso,
    user_agent_de_peticion,
)
from app.errors import ErrorDominio
from app.schemas.usuarios import (
    UsuarioConClaveTemporal,
    UsuarioCrear,
    UsuarioEditar,
    UsuarioLista,
    UsuarioSalida,
)
from app.services import usuarios as servicio

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


def _gestion() -> Callable:
    """El permiso común del módulo, para colocarse en cada endpoint."""
    return requiere_permiso("usuarios.gestionar")


def _salida(fila: dict) -> UsuarioSalida:
    """Traduce la fila de `app_users` a los nombres del esquema."""
    return UsuarioSalida(
        id=int(fila["id"]),
        nombre=str(fila["full_name"]),
        correo=str(fila["email"]),
        rol=str(fila["role"]),
        debe_cambiar_password=fila["must_change_password"] is True,
        creado_en=fila["creado_en"],
    )


def _rol_validado(rol: str) -> str:
    """El rol siempre pertenece al catálogo cerrado del dominio."""
    if rol not in ROLES:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"rol": [f"El rol debe ser uno de: {', '.join(ROLES)}."]},
        )
    return rol


@router.get("", response_model=UsuarioLista)
async def listar(
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_gestion()),  # noqa: B008
    q: str = "",
    rol: str | None = None,
    pagina: int = 1,
    por_pagina: int = 20,
) -> UsuarioLista:
    """USR-02: búsqueda por nombre o correo, filtro por rol y paginación."""
    if rol is not None and rol not in ROLES:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"rol": [f"El rol debe ser uno de: {', '.join(ROLES)}."]},
        )
    if pagina < 1 or por_pagina < 1:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"pagina": ["La paginación debe empezar en 1."]},
        )
    filas, total = await servicio.listar(
        sesion,
        busqueda=q,
        rol=rol,
        pagina=pagina,
        por_pagina=por_pagina,
    )
    return UsuarioLista(
        items=[_salida(fila) for fila in filas],
        total=total,
        pagina=pagina,
        por_pagina=min(por_pagina, servicio.MAXIMA_POR_PAGINA),
    )


@router.post("", response_model=UsuarioConClaveTemporal, status_code=201)
async def crear(
    peticion: UsuarioCrear,
    request: Request,
    sesion: SesionBd,
    admin: UsuarioAutenticado = Depends(_gestion()),  # noqa: B008
) -> UsuarioConClaveTemporal:
    """USR-01: crea la cuenta; la contraseña temporal solo se muestra aquí."""
    _rol_validado(peticion.rol)
    usuario_id, clave_temporal = await servicio.crear(
        sesion,
        nombre=peticion.nombre,
        correo=peticion.correo,
        rol=peticion.rol,
        actor_id=admin.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    fila = await servicio.obtener(sesion, usuario_id)
    return UsuarioConClaveTemporal(
        id=int(fila["id"]),
        nombre=str(fila["full_name"]),
        correo=str(fila["email"]),
        rol=str(fila["role"]),
        password_temporal=clave_temporal,
    )


@router.get("/{usuario_id}", response_model=UsuarioSalida)
async def obtener(
    usuario_id: int,
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_gestion()),  # noqa: B008
) -> UsuarioSalida:
    """USR-02: detalle del usuario."""
    return _salida(await servicio.obtener(sesion, usuario_id))


@router.patch("/{usuario_id}", response_model=UsuarioSalida)
async def editar(
    usuario_id: int,
    peticion: UsuarioEditar,
    request: Request,
    sesion: SesionBd,
    admin: UsuarioAutenticado = Depends(_gestion()),  # noqa: B008
) -> UsuarioSalida:
    """USR-03/04: cambia nombre, correo o rol; protege al último administrador."""
    if peticion.rol is not None:
        _rol_validado(peticion.rol)
    actualizado = await servicio.editar(
        sesion,
        usuario_id,
        nombre=peticion.nombre,
        correo=peticion.correo,
        rol=peticion.rol,
        actor_id=admin.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return _salida(actualizado)


@router.post("/{usuario_id}/restablecer-password", response_model=UsuarioConClaveTemporal)
async def restablecer_password(
    usuario_id: int,
    request: Request,
    sesion: SesionBd,
    admin: UsuarioAutenticado = Depends(_gestion()),  # noqa: B008
) -> UsuarioConClaveTemporal:
    """USR-06: nueva contraseña temporal; el usuario debe cambiarla al entrar."""
    clave_temporal = await servicio.restablecer_password(
        sesion,
        usuario_id,
        admin_id=admin.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    fila = await servicio.obtener(sesion, usuario_id)
    return UsuarioConClaveTemporal(
        id=int(fila["id"]),
        nombre=str(fila["full_name"]),
        correo=str(fila["email"]),
        rol=str(fila["role"]),
        password_temporal=clave_temporal,
    )
