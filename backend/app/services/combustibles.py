"""Catálogo de combustibles (CMB-01, CMB-03).

Cada tipo admite crear, editar nombre y activar/desactivar; no hay borrado
físico (los precios y las órdenes lo referencian). El listado incluye el
precio vigente de cada uno para que el frontend no haga N consultas.
"""

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ErrorDominio
from app.services import auditoria, precios

CODIGO_UNICO_VIOLADO = "23505"


async def listar(
    sesion: AsyncSession,
    *,
    activo: bool | None = None,
) -> list[dict]:
    """CMB-01/03: catálogo con el precio vigente de hoy de cada tipo."""
    condicion = "WHERE activo = TRUE" if activo else ""
    filas = await sesion.execute(
        text(
            "SELECT id, nombre, activo, creado_en"  # noqa: S608
            " FROM combustibles "
            + condicion
            + " ORDER BY activo DESC, nombre"
        ),
        {},
    )
    catalogo: list[dict] = []
    for fila in filas.mappings():
        item = dict(fila)
        try:
            item["precio_vigente"] = await precios.vigente_a(sesion, int(fila["id"]))
        except ErrorDominio:
            item["precio_vigente"] = None
        catalogo.append(item)
    return catalogo


async def obtener(sesion: AsyncSession, combustible_id: int) -> dict:
    """Detalle del tipo; 404 si no existe."""
    fila = (
        await sesion.execute(
            text(
                """
                SELECT id, nombre, activo, creado_en
                FROM combustibles
                WHERE id = :id
                """
            ),
            {"id": combustible_id},
        )
    ).mappings().first()
    if fila is None:
        raise ErrorDominio(404, "RECURSO_NO_ENCONTRADO", "El combustible no existe.")
    return dict(fila)


async def crear(
    sesion: AsyncSession,
    *,
    nombre: str,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> dict:
    """CMB-01: alta del tipo; el nombre no se repite (índice único en lower)."""
    try:
        fila = (
            await sesion.execute(
                text(
                    """
                    INSERT INTO combustibles (nombre)
                    VALUES (:nombre)
                    RETURNING id, nombre, activo, creado_en
                    """
                ),
                {"nombre": nombre.strip()},
            )
        ).mappings().one()
    except IntegrityError as exc:
        if getattr(exc.orig, "pgcode", None) == CODIGO_UNICO_VIOLADO:
            raise ErrorDominio(
                409,
                "NOMBRE_DUPLICADO",
                "Ya existe un combustible con ese nombre.",
            ) from exc
        raise
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="crear_combustible",
        entidad="combustible",
        entidad_id=int(fila["id"]),
        despues={"nombre": str(fila["nombre"])},
        ip=ip,
        user_agent=user_agent,
    )
    return dict(fila)


async def editar(
    sesion: AsyncSession,
    combustible_id: int,
    *,
    nombre: str | None,
    activo: bool | None,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> dict:
    """CMB-01: cambia nombre o estado.

    Desactivar está permitido incluso si hay órdenes que lo referencian: el
    efecto del plan es que un tipo inactivo no se puede elegir en órdenes ni
    vales nuevos (CMB-01). No existe DELETE: el historial de precios y las
    órdenes lo referencian.
    """
    actual = await obtener(sesion, combustible_id)
    nombre_nuevo = nombre.strip() if nombre is not None else None
    campos: list[str] = []
    parametros: dict[str, object] = {"id": combustible_id}
    if nombre_nuevo is not None:
        campos.append("nombre = :nombre")
        parametros["nombre"] = nombre_nuevo
    if activo is not None:
        campos.append("activo = :activo")
        parametros["activo"] = activo
    if not campos:
        return actual
    try:
        fila = (
            await sesion.execute(
                text(
                    "UPDATE combustibles SET "  # noqa: S608
                    + ", ".join(campos)
                    + " WHERE id = :id"
                      " RETURNING id, nombre, activo, creado_en"
                ),
                parametros,
            )
        ).mappings().one()
    except IntegrityError as exc:
        if getattr(exc.orig, "pgcode", None) == CODIGO_UNICO_VIOLADO:
            raise ErrorDominio(
                409,
                "NOMBRE_DUPLICADO",
                "Ya existe un combustible con ese nombre.",
            ) from exc
        raise
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="editar_combustible",
        entidad="combustible",
        entidad_id=combustible_id,
        antes={"nombre": actual["nombre"], "activo": actual["activo"]},
        despues={"nombre": str(fila["nombre"]), "activo": fila["activo"]},
        ip=ip,
        user_agent=user_agent,
    )
    return dict(fila)
