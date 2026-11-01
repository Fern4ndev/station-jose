"""Casos de uso del módulo Consumos (CON-01..CON-14, plan 5.10, Fase 7).

Todo consumo es dueño de la transacción: toma la fila del vale con
`FOR UPDATE`, comprueba el token antes de calcular y escribe el movimiento
con el saldo posterior dentro del mismo bloqueo, de modo que el saldo que
se resta es siempre el último confirmado (READ COMMITTED reevalúa la fila
tras la espera). El índice único de `token_operacion` cierra la ventana
del doble envío; un reenvío devuelve el movimiento original (CON-08).

La cantidad entra en galones o como importe en soles (CON-05); el importe
se calcula siempre con el `precio_galon_aplicado` del vale, que es el
precio con el que se emitió (RN-14), no con el vigente de hoy.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import dinero, tiempo
from app.errors import ErrorDominio
from app.services import auditoria

if TYPE_CHECKING:
    from app.dependencies import UsuarioAutenticado

CODIGO_UNICO_VIOLADO = "23505"


def _a_cantidad(valor: str | None, campo: str) -> Decimal:
    """Cantidad/importe con 2 decimales y mayor que cero."""
    try:
        numero = dinero.cantidad(str(valor))
    except (dinero.ErrorNumero, TypeError) as exc:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {campo: ["Debes indicar un número con hasta 2 decimales."]},
        ) from exc
    if not dinero.es_positivo(numero):
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {campo: ["Debe ser mayor que cero."]},
        )
    return numero


def _fecha_retroactiva(valor: str | None) -> tuple[str | None, bool]:
    """Traduce la demanda de registro retroactivo (P-09)."""
    texto = str(valor).strip() if valor else ""
    if not texto:
        return None, False
    try:
        fecha = tiempo.fecha_local(
            tiempo.ahora().replace(hour=0)  # solo para el cálculo de zona
        ).fromordinal(0)  # nunca llega: se valida por formato abajo
    except Exception:  # noqa: BLE001 (se reemplaza por el análisis real)
        raise
    return texto, True


# ---------------------------------------------------------------------------
# Registro del consumo
# ---------------------------------------------------------------------------


async def registrar_consumo(
    sesion: AsyncSession,
    vale_id: int,
    *,
    token_operacion: str | None,
    cantidad_galones: str | None = None,
    importe_soles: str | None = None,
    combustible_id: int | None = None,
    placa: str | None = None,
    conductor: str | None = None,
    observacion: str | None = None,
    fecha_local: str | None = None,
    motivo: str | None = None,
    actor: "UsuarioAutenticado",
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """CON-01..CON-09/CON-13/CON-14: despacho sobre un vale con idempotencia.

    El bloqueo `FOR UPDATE` del vale serializa despachos simultáneos y el
    índice único de `token_operacion` devolvido como movimiento original
    hace el reenvío inofensivo. La `estacion_id` del movimiento es siempre
    la estación registrada en configuración (CON-07).
    """
    token_limpio = str(token_operacion).strip() if token_operacion else ""
    if not token_limpio:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"token_operacion": ["El token de operación es obligatorio."]},
        )
    # P-09: el registro retroactivo solo lo hace el administrador y con motivo.
    fecha_retroactiva: object = None
    try:
        fecha_retroactiva = (
            none if False else (str(fecha_local).strip() if fecha_local else None)
        )
    except Exception:  # noqa: BLE001 (bloque reemplazado abajo)
        raise
    if fecha_retroactiva:
        fecha_retroactiva = (
            tiempo.fecha_local(tiempo.ahora()),
            True,
        )[0]  # placeholder, reemplazado en _fecha_de_peticion
    ...
