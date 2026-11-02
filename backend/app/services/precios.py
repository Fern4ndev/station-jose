"""Precio por galón: registro, vigencia y cálculo (CMB-02..04, D-01).

El histórico de `precios_combustible` es inmutable: registrar es INSERT,
nunca UPDATE ni DELETE (la base también lo rechaza desde la migración 0004).
El precio vigente a una fecha es el último con `vigente_desde` menor o igual;
la conversión de galones a soles vive en `calcular_valor` (CMB-04) y la usan
la emisión de vales y el control del presupuesto.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import dinero
from app.errors import ErrorDominio
from app.services import auditoria

PRECIO_INVALIDO_422 = 422


async def existe_combustible(sesion: AsyncSession, combustible_id: int) -> bool:
    """True si el combustible existe (activo o no)."""
    return (
        await sesion.execute(
            text("SELECT 1 FROM combustibles WHERE id = :id"),
            {"id": combustible_id},
        )
    ).first() is not None


def _a_precio(precio_galon: Decimal | int | str | float) -> Decimal:
    """CMB-02: mayor que cero y hasta 2 decimales."""
    precio = dinero.monto(precio_galon)
    if not dinero.es_positivo(precio):
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"precio_galon": ["El precio por galón debe ser mayor que cero."]},
        )
    return precio


def _a_fecha(vigente_desde: str) -> date:
    """Fecha de vigencia ISO `YYYY-MM-DD`; 422 si no lo es."""
    try:
        return date.fromisoformat(vigente_desde.strip())
    except ValueError as exc:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"vigente_desde": ["La fecha debe tener formato AAAA-MM-DD."]},
        ) from exc


async def registrar(
    sesion: AsyncSession,
    *,
    combustible_id: int,
    precio_galon: Decimal | int | str | float,
    vigente_desde: str,
    actor_id: int | None,
    ip: str | None,
    user_agent: str | None,
) -> dict:
    """CMB-02: registra un precio nuevo; la fecha no retrocede (el historial no se edita).

    Devuelve la fila registrada con el nombre de quién la registró.
    """
    if not await existe_combustible(sesion, combustible_id):
        raise ErrorDominio(
            404, "RECURSO_NO_ENCONTRADO", "El combustible no existe."
        )
    precio = _a_precio(precio_galon)
    desde = _a_fecha(vigente_desde)

    ultimo = (
        await sesion.execute(
            text(
                """
                SELECT max(vigente_desde) AS ultima_fecha
                FROM precios_combustible
                WHERE combustible_id = :combustible
                """
            ),
            {"combustible": combustible_id},
        )
    ).mappings().first()
    if ultimo is not None and ultimo["ultima_fecha"] is not None and desde < ultimo["ultima_fecha"]:
        raise ErrorDominio(
            409,
            "FECHA_PRECIO_ATRASADA",
            "La fecha de vigencia no puede ser anterior a la del último "
            "precio registrado; registre un precio nuevo, no retroactivo.",
            {"vigente_desde": [f"La última fecha registrada es {ultimo['ultima_fecha']}."]},
        )

    try:
        fila = (
            await sesion.execute(
                text(
                    """
                    INSERT INTO precios_combustible
                        (combustible_id, precio_galon, vigente_desde, app_user_id)
                    VALUES
                        (:combustible, :precio, :desde, :actor)
                    RETURNING id, combustible_id, precio_galon, vigente_desde,
                              app_user_id, creado_en
                    """
                ),
                {
                    "combustible": combustible_id,
                    "precio": str(precio),
                    "desde": desde,
                    "actor": actor_id,
                },
            )
        ).mappings().one()
    except IntegrityError as exc:
        if getattr(exc.orig, "pgcode", None) == "23505":  # UNIQUE (combustible, fecha)
            raise ErrorDominio(
            409,
            "FECHA_PRECIO_DUPLICADA",
            "Ya existe un precio para esa fecha de vigencia.",
            {"vigente_desde": ["Registre el precio con una fecha distinta."]},
        ) from exc
        raise
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="registrar_precio",
        entidad="combustible_precio",
        entidad_id=int(fila["id"]),
        despues={
            "combustible_id": combustible_id,
            "precio_galon": str(precio),
            "vigente_desde": desde.isoformat(),
        },
        ip=ip,
        user_agent=user_agent,
    )
    return dict(fila)


async def vigente_a(
    sesion: AsyncSession,
    combustible_id: int,
    *,
    fecha: date | None = None,
) -> dict:
    """CMB-03: el último precio con `vigente_desde <= fecha` (por defecto hoy)."""
    fila = (
        await sesion.execute(
            text(
                """
                SELECT precio_galon, vigente_desde
                FROM precios_combustible
                WHERE combustible_id = :combustible
                  AND vigente_desde <= COALESCE(:fecha, CURRENT_DATE)
                ORDER BY vigente_desde DESC
                LIMIT 1
                """
            ),
            {"combustible": combustible_id, "fecha": fecha},
        )
    ).mappings().first()
    if fila is None:
        raise ErrorDominio(
            404,
            "SIN_PRECIO_VIGENTE",
            "No hay precio vigente para ese combustible a esa fecha.",
        )
    return {
        "precio_galon": str(dinero.monto(fila["precio_galon"])),
        "vigente_desde": str(fila["vigente_desde"]),
    }


async def historico(
    sesion: AsyncSession,
    combustible_id: int,
) -> list[dict]:
    """CMB-03: todo el historial, del más reciente al más antiguo, con autor."""
    filas = (
        await sesion.execute(
            text(
                """
                SELECT p.id, p.precio_galon, p.vigente_desde, p.creado_en,
                       u.full_name AS registrado_por
                FROM precios_combustible p
                LEFT JOIN app_users u ON u.id = p.app_user_id
                WHERE p.combustible_id = :combustible
                ORDER BY p.vigente_desde DESC, p.id DESC
                """
            ),
            {"combustible": combustible_id},
        )
    )
    return [
        {
            "id": int(fila["id"]),
            "precio_galon": str(dinero.monto(fila["precio_galon"])),
            "vigente_desde": str(fila["vigente_desde"]),
            "creado_en": fila["creado_en"],
            "registrado_por": fila["registrado_por"],
        }
        for fila in filas.mappings()
    ]


def calcular_valor(
    cantidad_galones: Decimal | int | str | float,
    precio_galon: Decimal | int | str | float,
) -> Decimal:
    """CMB-04: galones por el precio, redondeado a 2 decimales mitad hacia arriba (D-01)."""
    valor = dinero.cantidad(cantidad_galones) * dinero.monto(precio_galon)
    return dinero.monto(valor)
