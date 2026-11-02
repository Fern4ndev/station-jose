"""Panel de indicadores (REP-01, plan sección 5.12).

La Fase 8 aporta el indicador de integridad (AUD-06): el administrador ve si
quedan diferencias de saldo sin revisar. El resto de indicadores del panel
—órdenes del mes, vales activos, galones consumidos, por agotarse y por
vencer— se completa en la Fase 12.
"""

from fastapi import APIRouter, Depends

from app.db.sesion import SesionBd
from app.dependencies import UsuarioAutenticado, requiere_permiso
from app.schemas.auditoria import IndicadoresPanel
from app.services import integridad

router = APIRouter(prefix="/panel", tags=["panel"])


def _sesion() -> object:
    return requiere_permiso("sesion")


@router.get("/indicadores", response_model=IndicadoresPanel)
async def indicadores(
    sesion: SesionBd,
    usuario: UsuarioAutenticado = Depends(_sesion()),  # noqa: B008
) -> IndicadoresPanel:
    """REP-01/AUD-06: diferencia sin revisar, solo para el administrador."""
    if usuario.rol != "administrador":
        return IndicadoresPanel()
    return IndicadoresPanel(
        diferencias_sin_revisar=await integridad.pendientes(sesion)
    )
