"""Numeración propia de la estación (VAL-02, CFG-01).

El código interno del vale de estación sale del parámetro
`vale_formato_numeracion_estacion` (por defecto `{anio}-{secuencia:06d}`)
con un contador por año en `secuencias`. La fila del contador se toma con
`SELECT ... FOR UPDATE` dentro de la transacción de la emisión, así que dos
emisiones simultáneas reciben códigos distintos por construcción (RN-04).
La numeración de los vales de entidad no se genera: se conserva como la
entrega cada institución (D-02).
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import configuracion

NOMBRE_SECUENCIA = "vale_estacion"
FORMATO_DEFECTO = "{anio}-{secuencia:06d}"


async def _formato(sesion: AsyncSession) -> str:
    """Formato configurable del código interno; el defecto si nunca se fijó."""
    valor = await configuracion.valor_texto(
        sesion, "vale_formato_numeracion_estacion"
    )
    return valor if valor and valor.strip() else FORMATO_DEFECTO


async def asignar_numero_estacion(sesion: AsyncSession, fecha_emision) -> str:
    """Devuelve el siguiente código interno a partir del año de la emisión.

    Toma la fila de `secuencias` con FOR UPDATE, la incrementa y formatea
    con el parámetro de configuración; la llamada es segura bajo
    emisiones simultáneas porque el bloqueo pertenece a la transacción.
    """
    anio = fecha_emision.year
    formato = await _formato(sesion)
    fila = (
        await sesion.execute(
            text(
                "SELECT ultimo FROM secuencias"
                " WHERE nombre = :nombre AND anio = :anio FOR UPDATE"
            ),
            {"nombre": NOMBRE_SECUENCIA, "anio": anio},
        )
    ).first()
    if fila is None:
        insertado = await sesion.execute(
            text(
                "INSERT INTO secuencias (nombre, anio, ultimo)"
                " VALUES (:nombre, :anio, 1)"
                " ON CONFLICT (nombre, anio) DO UPDATE SET ultimo = secuencias.ultimo + 1"
                " RETURNING ultimo"
            ),
            {"nombre": NOMBRE_SECUENCIA, "anio": anio},
        )
        ultimo = int(insertado.scalar_one())
    else:
        actualizado = await sesion.execute(
            text(
                "UPDATE secuencias SET ultimo = ultimo + 1"
                " WHERE nombre = :nombre AND anio = :anio RETURNING ultimo"
            ),
            {"nombre": NOMBRE_SECUENCIA, "anio": anio},
        )
        ultimo = int(actualizado.scalar_one())
    return formato.format(anio=anio, secuencia=ultimo)
