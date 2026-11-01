"""Lectura de parámetros del sistema en cada uso (CFG-01).

La Fase 4 completa el servicio con tipos, rangos y validación; la Fase 2
necesita leer de PostgreSQL los valores que gobiernan la sesión, de modo
que un cambio por `PUT /configuracion/parametros` rija sin reiniciar.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Valores de respaldo si el catálogo de la base no tiene la clave (los
# mismos que inserta la migración 0001 con `ON CONFLICT DO NOTHING`).
DEFECTO_NUMERO: dict[str, int] = {
    "sesion_inactividad_min": 60,
    "login_intentos_max": 5,
    "login_bloqueo_min": 15,
    "refresh_token_dias": 30,
    "archivo_max_mb": 10,  # tope de documentos adjuntos a las órdenes (ORD-03)
}


async def numero(sesion: AsyncSession, clave: str) -> int:
    """Valor entero vigente del parámetro, leído de PostgreSQL en cada uso."""
    filas = await sesion.execute(
        text("SELECT valor FROM parametros WHERE clave = :clave"),
        {"clave": clave},
    )
    valor = filas.scalar_one_or_none()
    if valor is not None:
        try:
            numero_parseado = int(str(valor).strip())
        except ValueError:
            numero_parseado = DEFECTO_NUMERO.get(clave, 0)
    else:
        numero_parseado = DEFECTO_NUMERO.get(clave, 0)
    return max(numero_parseado, 0)
