"""Casos de uso del módulo Consumos (CON-01..CON-14, plan 5.10, Fase 7).

Todo consumo es dueño de la transacción: toma la fila del vale con
`FOR UPDATE`, comprueba el token antes de calcular y escribe el movimiento
con el saldo posterior dentro del mismo bloqueo, de modo que el saldo que
se resta es siempre el último confirmado: en `READ COMMITTED` la consulta
bloqueante espera y reevalúa la fila con el valor ya confirmado (RN-05,
CON-09). El índice único de `movimientos_vale.token_operacion` cierra la
ventana del doble envío; un reenvío con el mismo token devuelve el
movimiento original (CON-08), así que no hace falta subir a SERIALIZABLE.

La cantidad entra en galones o como importe en soles, nunca ambos (CON-05);
el importe se calcula siempre con el `precio_galon_aplicado` del vale, que
es el precio con el que se emitió (RN-14), no con el vigente de hoy.
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import dinero, tiempo
from app.errors import ErrorDominio
from app.services import auditoria, vales

if TYPE_CHECKING:
    from app.dependencies import UsuarioAutenticado

CODIGO_UNICO_VIOLADO = "23505"


# ---------------------------------------------------------------------------
# Validaciones previas
# ---------------------------------------------------------------------------


def _a_positivo(valor: str | None, campo: str) -> Decimal:
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


def _fecha_de_peticion(
    fecha_local: str | None,
    motivo: str | None,
    rol: str,
) -> date | None:
    """Resuelve la `fecha_local` retroactiva del administrador (P-09).

    Sin fecha, el servidor la imprime hoy en Lima (CON-06). Con fecha se
    exige rol `administrador` y motivo registrado; además la fecha no es
    futura: el registro retroactivo documenta hechos pasados, no inventados.
    """
    texto = str(fecha_local).strip() if fecha_local else ""
    if not texto:
        return None
    if rol != "administrador":
        raise ErrorDominio(
            403,
            "SIN_PERMISO",
            "Solo el administrador puede registrar consumos retroactivos.",
        )
    if not str(motivo or "").strip():
        raise ErrorDominio(
            422,
            "MOTIVO_OBLIGATORIO",
            "Un consumo retroactivo exige motivo.",
            {"motivo": ["Indica el motivo del registro retroactivo."]},
        )
    try:
        fecha = date.fromisoformat(texto)
    except ValueError as exc:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"fecha_local": ["La fecha debe tener formato AAAA-MM-DD."]},
        ) from exc
    if fecha.isoformat() != texto:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"fecha_local": ["La fecha debe tener formato AAAA-MM-DD."]},
        )
    if fecha > tiempo.hoy():
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"fecha_local": ["La fecha retroactiva no puede ser futura."]},
        )
    return fecha


def _asegurar_consumible(vale: dict, combustible_id: int | None) -> None:
    """CON-04/P-03: el vale admite despacho o levanta su error específico.

    Rechaza vale anulado, agotado o vencido (el vencido se reconoce por
    fecha aunque el proceso diario no lo haya marcado), vale de una orden
    anulada y combustible distinto del que declara el vale.
    """
    estado = str(vale["estado"])
    if estado == "anulado":
        raise ErrorDominio(409, "VALE_ANULADO", "El vale está anulado.")
    if estado == "agotado" or not dinero.es_positivo(vale["saldo"]):
        raise ErrorDominio(
            409, "VALE_AGOTADO", "El vale no tiene saldo disponible."
        )
    if estado == "vencido" or (
        vale["fecha_vencimiento"] is not None
        and vale["fecha_vencimiento"] < tiempo.hoy()
    ):
        raise ErrorDominio(
            409,
            "VALE_VENCIDO",
            "El vale ya está vencido: su fecha de vencimiento pasó.",
        )
    if vale["orden_estado"] == "anulada":
        raise ErrorDominio(
            409,
            "ORDEN_ANULADA",
            "El vale pertenece a una orden de compra anulada.",
        )
    if combustible_id is not None and int(combustible_id) != int(
        vale["combustible_id"]
    ):
        raise ErrorDominio(
            409,
            "CONSUMO_COMBUSTIBLE_DISTINTO",
            "El combustible del despacho no es el del vale.",
        )


# ---------------------------------------------------------------------------
# Registro, listado y reversiones
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
) -> tuple[dict, dict]:
    """CON-01..CON-09/CON-13/CON-14: despacho sobre un vale, idempotente.

    Devuelve `(movimiento, vale_actualizado)`: el reenvío con el mismo
    `token_operacion` trae el movimiento original (CON-08) y el saldo que
    estaba vigente al confirmarse el primero.
    """
    token_limpio = str(token_operacion).strip() if token_operacion else ""
    if not token_limpio:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"token_operacion": ["El token de operación es obligatorio."]},
        )
    if (cantidad_galones is None or not str(cantidad_galones).strip()) and (
        importe_soles is None or not str(importe_soles).strip()
    ):
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {
                "cantidad_galones": [
                    "Indica cantidad_galones o importe_soles."
                ]
            },
        )
    if cantidad_galones and importe_soles:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {
                "importe_soles": [
                    "Envié cantidad_galones o importe_soles, no ambos."
                ]
            },
        )
    fecha_retroactiva = _fecha_de_peticion(
        fecha_local, motivo, actor.rol if actor else "oficina"
    )

    # ¿Ya operó este token? Reenvío: devuelve el movimiento original (CON-08).
    previo = await _movimiento_por_token(sesion, token_limpio)
    if previo is not None:
        return previo, {}

    vale = (
        await sesion.execute(
            text(
                """
                SELECT v.*, o.estado AS orden_estado
                  FROM vales v
                  JOIN ordenes_compra o ON o.id = v.orden_compra_id
                 WHERE v.id = :id
                FOR UPDATE OF v
                """
            ),
            {"id": vale_id},
        )
    ).mappings().one_or_none()
    if vale is None:
        raise ErrorDominio(404, "VALE_NO_ENCONTRADO", "El vale no existe.")
    datos = dict(vale)
    _asegurar_consumible(datos, combustible_id)

    precio = dinero.a_decimal(datos["precio_galon_aplicado"])
    if importe_soles:
        importe = _a_positivo(importe_soles, "importe_soles")
        cantidad = dinero.cantidad(importe / precio)
        if not dinero.es_positivo(cantidad):
            # El importe es tan pequeño que redondeó a cero galones.
            raise ErrorDominio(
                422,
                "VALIDACION_INVALIDA",
                "Revise los campos marcados.",
                {
                    "importe_soles": [
                        "El importe es menor que el precio de un galón."
                    ]
                },
            )
        importe = dinero.monto(cantidad * precio)  # cuadre importe/cantidad
    else:
        cantidad = _a_positivo(cantidad_galones, "cantidad_galones")
        importe = dinero.monto(cantidad * precio)

    saldo_actual = dinero.a_decimal(datos["saldo"])
    if cantidad > saldo_actual:
        raise ErrorDominio(
            409,
            "SALDO_INSUFICIENTE",
            "La cantidad excede el saldo del vale.",
            detalles={"saldo": dinero.como_texto(saldo_actual)},
        )
    nuevo = dinero.monto(saldo_actual - cantidad)
    estado_nuevo = "agotado" if nuevo == 0 else "activo"
    fecha_movimiento = fecha_retroactiva or tiempo.hoy()

    id_estacion = await vales._id_estacion(sesion)
    # P-06: placa, conductor y observación son opcionales; la observación
    # viaja en el `motivo` del movimiento (la tabla no tiene columna propia).
    datos_movimiento = {"motivo": (observacion or "").strip() or (motivo or "").strip() or None}
    try:
        fila = (
            await sesion.execute(
                text(
                    """
                    INSERT INTO movimientos_vale (
                        vale_id, tipo, variacion, saldo_posterior,
                        cantidad_galones, precio_galon, importe_soles,
                        app_user_id, estacion_id, motivo, placa, conductor,
                        token_operacion, fecha_local
                    ) VALUES (
                        :vale, 'consumo', :variacion, :saldo_posterior,
                        :cantidad, :precio, :importe,
                        :usuario, :estacion, :motivo, :placa, :conductor,
                        CAST(:token AS uuid), :fecha_local
                    )
                    RETURNING id, creado_en
                    """
                ),
                {
                    "vale": vale_id,
                    "variacion": -cantidad,
                    "saldo_posterior": nuevo,
                    "cantidad": cantidad,
                    "precio": precio,
                    "importe": importe,
                    "usuario": actor.id,
                    "estacion": id_estacion,
                    "motivo": datos_movimiento["motivo"],
                    "placa": placa,
                    "conductor": conductor,
                    "token": token_limpio,
                    "fecha_local": fecha_movimiento,
                },
            )
        ).mappings().one()
    except IntegrityError as error:
        sesion.rollback()
        if getattr(error.orig, "pgcode", None) == CODIGO_UNICO_VIOLADO:
            # El token del doble envío confirmó primero: devolvemos el
            # movimiento original (CON-08) releyendo en una transacción limpia.
            previo = await _movimiento_por_token(sesion, token_limpio)
            if previo is not None:
                return previo, {}
            raise ErrorDominio(
                409,
                "CONFLICTO_CONCURRENTE",
                "El token de operación chocó con otro movimiento.",
            ) from error
        raise

    await sesion.execute(
        text(
            "UPDATE vales SET saldo = :saldo, estado = :estado,"
            " actualizado_en = now() WHERE id = :id"
        ),
        {
            "saldo": nuevo,
            "estado": estado_nuevo,
            "id": vale_id,
        },
    )
    movimiento = {
        "id": int(fila["id"]),
        "vale_id": vale_id,
        "tipo": "consumo",
        "variacion": dinero.como_texto(-cantidad),
        "saldo_posterior": dinero.como_texto(nuevo),
        "cantidad_galones": dinero.como_texto(cantidad),
        "precio_galon": dinero.como_texto(precio),
        "importe_soles": dinero.como_texto(importe),
        "motivo": datos_movimiento["motivo"],
        "placa": placa,
        "conductor": conductor,
        "token_operacion": token_limpio,
        "fecha_local": str(fecha_movimiento),
        "creado_en": fila["creado_en"],
        "usuario": actor.nombre,
    }
    await auditoria.registrar(
        sesion,
        usuario_id=actor.id,
        accion="consumo_registrado",
        entidad="vales",
        entidad_id=str(vale_id),
        despues={
            "cantidad_galones": dinero.como_texto(cantidad),
            "importe_soles": dinero.como_texto(importe),
            "token_operacion": token_limpio,
        },
        ip=ip,
        user_agent=user_agent,
    )
    return movimiento, {"saldo": dinero.como_texto(nuevo), "estado": estado_nuevo}


_PROYECCION_CONSUMOS = (
    "SELECT m.id, m.vale_id, m.tipo, m.variacion, m.saldo_posterior,"
    " m.cantidad_galones, m.precio_galon, m.importe_soles, m.motivo,"
    " m.placa, m.conductor, m.token_operacion::text AS token_operacion,"
    " m.estacion_id, m.fecha_local, m.creado_en, u.full_name AS usuario"
    " FROM movimientos_vale m"
    " JOIN app_users u ON u.id = m.app_user_id"
)


def _proyeccion_consumos(where: str) -> str:
    """Consulta base del listado de consumos por vale (QRY-05).

    El fragmento `where` lo arma `listar_consumos` con condiciones literales
    de una lista blanca y todos los valores viajan como parámetros; nunca
    llega texto de la petición a la cadena SQL.
    """
    return _PROYECCION_CONSUMOS + where


async def listar_consumos(
    sesion: AsyncSession,
    vale_id: int,
    *,
    desde: str | None = None,
    hasta: str | None = None,
) -> list[dict]:
    """QRY-05: consumos del vale en el rango pedido, con su reversión."""
    condiciones = ["m.vale_id = :id", "m.tipo IN ('consumo', 'reversion')"]
    parametros: dict[str, object] = {"id": vale_id}
    if desde:
        condiciones.append("m.fecha_local >= :desde")
        parametros["desde"] = desde
    if hasta:
        condiciones.append("m.fecha_local <= :hasta")
        parametros["hasta"] = hasta
    consulta = _proyeccion_consumos(
        " WHERE " + " AND ".join(condiciones) + " ORDER BY m.id"
    )
    filas = await sesion.execute(text(consulta), parametros)
    return [_movimiento_de_fila(fila) for fila in filas.mappings()]


def _movimiento_de_fila(fila) -> dict:
    datos = dict(fila)
    for campo in (
        "variacion",
        "saldo_posterior",
        "cantidad_galones",
        "precio_galon",
        "importe_soles",
    ):
        if datos.get(campo) is not None:
            datos[campo] = dinero.como_texto(datos[campo])
    datos["token_operacion"] = datos.get("token_operacion")
    datos["fecha_local"] = (
        str(datos["fecha_local"]) if datos.get("fecha_local") is not None else None
    )
    return datos


async def _movimiento_por_token(sesion: AsyncSession, token: str) -> dict | None:
    """El movimiento ya registrado con este `token_operacion` (CON-08).

    Normaliza cifras, fechas y UUID a sus formas de texto para que el
    reenvío devuelva exactamente lo mismo que la primera respuesta.
    """
    fila = (
        await sesion.execute(
            text(
                """
                    SELECT m.id, m.vale_id, m.tipo, m.variacion, m.saldo_posterior,
                           m.cantidad_galones, m.precio_galon, m.importe_soles,
                           m.motivo, m.placa, m.conductor, m.token_operacion::text,
                           m.fecha_local, m.creado_en, u.full_name AS usuario,
                           v.saldo AS saldo_vale
                      FROM movimientos_vale m
                      JOIN app_users u ON u.id = m.app_user_id
                      JOIN vales v ON v.id = m.vale_id
                     WHERE m.token_operacion = CAST(:token AS uuid)
                    """
            ),
            {"token": token},
        )
    ).mappings().one_or_none()
    if fila is None:
        return None
    datos = _movimiento_de_fila(fila)
    datos["token_operacion"] = token
    datos["saldo_vale"] = (
        dinero.como_texto(datos["saldo_vale"])
        if datos.get("saldo_vale") is not None
        else None
    )
    return datos


async def _movimiento_por_id(sesion: AsyncSession, movimiento_id: int) -> dict:
    fila = (
        await sesion.execute(
            text(
                _proyeccion_consumos(" WHERE m.id = :id")
            ),
            {"id": movimiento_id},
        )
    ).mappings().one_or_none()
    if fila is None:
        raise ErrorDominio(
            404, "MOVIMIENTO_NO_ENCONTRADO", "El movimiento no existe."
        )
    # Mismas formas de texto que el listado: el router arma el esquema Pydantic
    # con cadenas exactas y el comprobante no debe reintroducir Decimal ni date.
    return _movimiento_de_fila(fila)


async def comprobante(sesion: AsyncSession, movimiento_id: int) -> dict:
    """CON-10: los datos completos para el comprobante imprimible."""
    movimiento = await _movimiento_por_id(sesion, movimiento_id)
    fila = (
        await sesion.execute(
            text(
                """
                SELECT v.emisor, v.numero_estacion, v.numero_entidad,
                       v.saldo AS saldo_vale, i.nombre AS institucion,
                       o.numero AS orden_numero, o.anio AS orden_anio,
                       c.nombre AS combustible, e.nombre AS estacion
                  FROM vales v
                  JOIN ordenes_compra o ON o.id = v.orden_compra_id
                  JOIN instituciones i ON i.id = o.institucion_id
                  JOIN combustibles c ON c.id = v.combustible_id
                  JOIN estaciones e ON e.id = :estacion
                 WHERE v.id = :vale
                """
            ),
            {"vale": movimiento["vale_id"], "estacion": movimiento.get("estacion_id")},
        )
    ).mappings().one_or_none()
    datos = dict(fila) if fila is not None else {}
    salida = {
        "movimiento_id": movimiento["id"],
        "tipo": movimiento["tipo"],
        "fecha_local": movimiento["fecha_local"],
        "creado_en": movimiento["creado_en"],
        "vale_id": movimiento["vale_id"],
        "numero_estacion": datos.get("numero_estacion"),
        "numero_entidad": datos.get("numero_entidad"),
        "emisor": datos.get("emisor"),
        "institucion": datos.get("institucion"),
        "orden_numero": datos.get("orden_numero"),
        "orden_anio": datos.get("orden_anio"),
        "combustible": datos.get("combustible"),
        "cantidad_galones": movimiento.get("cantidad_galones"),
        "precio_galon": movimiento.get("precio_galon"),
        "importe_soles": movimiento.get("importe_soles"),
        "saldo_posterior": movimiento["saldo_posterior"],
        "saldo_vale": dinero.como_texto(datos["saldo_vale"])
        if datos.get("saldo_vale") is not None
        else None,
        "placa": movimiento.get("placa"),
        "conductor": movimiento.get("conductor"),
        "usuario": movimiento["usuario"],
        "estacion": datos.get("estacion"),
    }
    return salida


async def revertir(
    sesion: AsyncSession,
    movimiento_id: int,
    *,
    motivo: str,
    actor: "UsuarioAutenticado",
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """CON-11: reversión del consumo con movimiento inverso enlazado.

    El `movimiento_origen_id` es único: la doble reversión choca con el
    índice (409 `CONSUMO_YA_REVERTIDO`, comprobado antes por consulta).
    No se revierte un consumo de un vale anulado: su saldo quedó en cero
    por la anulación y reactivarlo rompería la trazabilidad (P-13).
    """
    if not str(motivo).strip():
        raise ErrorDominio(
            422,
            "MOTIVO_OBLIGATORIO",
            "El motivo es obligatorio para revertir un consumo.",
            {"motivo": ["Indica por qué se revierte el consumo."]},
        )
    origen = await _movimiento_por_id(sesion, movimiento_id)
    if origen["tipo"] != "consumo":
        raise ErrorDominio(
            409,
            "CONSUMO_NO_REVERTIBLE",
            "Solo se reversan movimientos de consumo.",
        )
    anterior = (
        await sesion.execute(
            text(
                "SELECT id FROM movimientos_vale"
                " WHERE movimiento_origen_id = :id AND tipo = 'reversion'"
            ),
            {"id": movimiento_id},
        )
    ).scalar_one_or_none()
    if anterior is not None:
        raise ErrorDominio(
            409,
            "CONSUMO_YA_REVERTIDO",
            "Ese consumo ya tiene su reversión registrada.",
        )

    vale = (
        await sesion.execute(
            text(
                """
                SELECT v.*, o.estado AS orden_estado
                  FROM vales v
                  JOIN ordenes_compra o ON o.id = v.orden_compra_id
                 WHERE v.id = :id
                FOR UPDATE OF v
                """
            ),
            {"id": origen["vale_id"]},
        )
    ).mappings().one()
    datos = dict(vale)
    if datos["estado"] == "anulado":
        raise ErrorDominio(
            409,
            "CONSUMO_VALE_ANULADO",
            "Consumos de un vale anulado no se reversan.",
        )
    cantidad = dinero.a_decimal(origen["cantidad_galones"])
    saldo_actual = dinero.a_decimal(datos["saldo"])
    inicial = dinero.a_decimal(datos["cantidad_inicial"])
    nuevo_saldo = saldo_actual + cantidad
    if nuevo_saldo > inicial:
        raise ErrorDominio(
            409,
            "REVERSION_INCOMPATIBLE",
            "La reversión dejaría el saldo sobre el vale de origen,"
            " probablemente por un ajuste posterior.",
            detalles={
                "saldo": dinero.como_texto(saldo_actual),
                "cantidad_inicial": dinero.como_texto(inicial),
            },
        )
    nuevo_saldo = dinero.monto(nuevo_saldo)
    id_estacion = await vales._id_estacion(sesion)
    try:
        fila = (
            await sesion.execute(
                text(
                    """
                    INSERT INTO movimientos_vale (
                        vale_id, tipo, variacion, saldo_posterior,
                        cantidad_galones, precio_galon, importe_soles,
                        app_user_id, estacion_id, motivo,
                        movimiento_origen_id, fecha_local
                    ) VALUES (
                        :vale, 'reversion', :variacion, :saldo_posterior,
                        :cantidad, :precio, :importe,
                        :usuario, :estacion, :motivo, :origen, :fecha_local
                    )
                    RETURNING id
                    """
                ),
                {
                    "vale": origen["vale_id"],
                    "variacion": +cantidad,
                    "saldo_posterior": nuevo_saldo,
                    "cantidad": cantidad,
                    "precio": dinero.a_decimal(origen["precio_galon"]),
                    "importe": dinero.a_decimal(origen["importe_soles"]),
                    "usuario": actor.id,
                    "estacion": id_estacion,
                    "motivo": motivo.strip(),
                    "origen": movimiento_id,
                    "fecha_local": tiempo.hoy(),
                },
            )
        ).mappings().one()
    except IntegrityError as error:
        if getattr(error.orig, "pgcode", None) == CODIGO_UNICO_VIOLADO:
            raise ErrorDominio(
                409,
                "CONSUMO_YA_REVERTIDO",
                "Ese consumo ya tiene su reversión registrada.",
            ) from error
        raise
    await sesion.execute(
        text(
            "UPDATE vales SET saldo = :saldo, estado = :estado,"
            " actualizado_en = now() WHERE id = :id"
        ),
        {
            "saldo": nuevo_saldo,
            "estado": "activo" if nuevo_saldo > 0 else "agotado",
            "id": origen["vale_id"],
        },
    )
    await auditoria.registrar(
        sesion,
        usuario_id=actor.id,
        accion="consumo_revertido",
        entidad="movimientos_vale",
        entidad_id=str(movimiento_id),
        despues={
            "cantidad_galones": dinero.como_texto(cantidad),
            "motivo": motivo.strip(),
        },
        ip=ip,
        user_agent=user_agent,
    )
    return {
        "id": int(fila["id"]),
        "vale_id": origen["vale_id"],
        "tipo": "reversion",
        "variacion": dinero.como_texto(+cantidad),
        "saldo_posterior": dinero.como_texto(nuevo_saldo),
        "cantidad_galones": dinero.como_texto(cantidad),
        "precio_galon": dinero.como_texto(dinero.a_decimal(origen["precio_galon"])),
        "importe_soles": dinero.como_texto(dinero.a_decimal(origen["importe_soles"])),
        "motivo": motivo.strip(),
        "movimiento_origen_id": movimiento_id,
        "usuario": actor.nombre,
        "saldo_vale": dinero.como_texto(nuevo_saldo),
    }
