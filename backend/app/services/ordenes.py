"""Casos de uso del módulo Órdenes de compra (ORD-01..10, plan sección 5.7).

Cada caso de uso es una función sobre la sesión; el router commitea.

El número de orden es único por institución y año (RN-12): la restricción
es de base (`ux_ordenes_institucion_anio_numero` de `0001`), el número se
proyecta con `max(numero) + 1` si el cliente no lo fija, y una colisión
de carrera se traduce al 409 `ORDEN_DUPLICADA`.

La advertencia de duplicado (ORD-08) contrasta la orden contra las demás
de la misma institución con el mismo presupuesto y la misma fecha; el
cliente reenvía la petición con `confirmar_duplicado = TRUE` si es real.

La validación de estados sigue la sección 3.4: borrador→vigente|anulada,
vigente→cerrada|anulada; cerrada y anulada son terminales. La anulación
requiere motivo (ORD-09) y no admite consumos (RN-17): el marcador
`tiene_consumos` queda para la Fase 7, y mientras tanto devuelve False.
"""

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import archivos, dinero, tiempo
from app.errors import ErrorDominio
from app.services import auditoria, parametros

MAXIMA_POR_PAGINA = 100

CODIGO_UNICO_VIOLADO = "23505"

TRANSICIONES_VALIDAS: dict[str, set[str]] = {
    "borrador": {"vigente", "anulada"},
    "vigente": {"cerrada", "anulada"},
    "cerrada": set(),
    "anulada": set(),
}


def tiene_consumos(_id_orden: int) -> bool:
    """ORD-09/RN-17: marcador de Fase 5. La Fase 7 lo convierte en la consulta
    real contra `movimientos_vale`; mientras tanto ninguna orden tiene consumos,
    así que la anulación solo depende del estado.
    """
    return False


async def _obtener_orden(sesion: AsyncSession, id_orden: int) -> dict:
    filas = await sesion.execute(
        text(
            """
            SELECT o.*, i.nombre AS razon_social, i.ruc AS institucion_ruc,
                   i.modalidad_numeracion, i.estado AS estado_institucion
              FROM ordenes_compra o
              JOIN instituciones i ON i.id = o.institucion_id
             WHERE o.id = :id
            """
        ),
        {"id": id_orden},
    )
    fila = filas.mappings().one_or_none()
    if fila is None:
        raise ErrorDominio(404, "ORDEN_NO_ENCONTRADA", "La orden de compra no existe.")
    return dict(fila)


async def listar(
    sesion: AsyncSession,
    *,
    institucion_id: int | None = None,
    estado: str | None = None,
    desde=None,
    hasta=None,
    texto: str | None = None,
    pagina: int,
    por_pagina: int,
) -> tuple[list[dict], int]:
    """ORD-05: listado paginado con filtros de institución, estado y rango de fechas."""
    por_pagina = min(max(por_pagina, 1), MAXIMA_POR_PAGINA)
    pagina = max(pagina, 1)
    condiciones: list[str] = []
    where_params: dict[str, object] = {}
    if institucion_id is not None:
        condiciones.append("o.institucion_id = :institucion")
        where_params["institucion"] = institucion_id
    if estado:
        condiciones.append("o.estado = :estado")
        where_params["estado"] = estado
    if desde:
        condiciones.append("o.fecha_emision >= :desde")
        where_params["desde"] = desde
    if hasta:
        condiciones.append("o.fecha_emision <= :hasta")
        where_params["hasta"] = hasta
    if texto:
        condiciones.append(
            "(o.numero ILIKE :patron OR i.nombre ILIKE :patron)"
        )
        where_params["patron"] = f"%{texto}%"
    where = f" WHERE {' AND '.join(condiciones)}" if condiciones else ""
    filas_total = await sesion.execute(
        text(
            "SELECT count(*) FROM ordenes_compra o"  # noqa: S608
            " JOIN instituciones i ON i.id = o.institucion_id"
            + where
        ),
        where_params,
    )
    total = int(filas_total.scalar_one())
    filas = await sesion.execute(
        text(
            "SELECT o.id, o.institucion_id, i.nombre AS razon_social, o.anio, o.numero,"  # noqa: S608
            " o.fecha_emision, o.presupuesto_soles, o.estado, o.combustible_id,"
            " o.creado_en"
            " FROM ordenes_compra o"
            " JOIN instituciones i ON i.id = o.institucion_id"
            + where
            + " ORDER BY o.fecha_emision DESC, o.anio DESC, o.numero DESC, o.id DESC"
            " LIMIT :limite OFFSET :desplazamiento"
        ),
        {**where_params, "limite": por_pagina, "desplazamiento": (pagina - 1) * por_pagina},
    )
    return [dict(fila) for fila in filas.mappings()], total


async def _duplicado_exacto(
    sesion: AsyncSession,
    *,
    institucion_id: int,
    presupuesto_soles: Decimal,
    fecha_emision,
    id_excluir: int | None,
) -> dict | None:
    """ORD-08: primera orden distinta que calce en institución, presupuesto y fecha."""
    extra = ""
    params: dict[str, object] = {"institucion": institucion_id}
    if id_excluir is not None:
        extra = " AND o.id <> :id_excluir"
        params["id_excluir"] = id_excluir
    filas = await sesion.execute(
        text(
            "SELECT o.id, o.institucion_id, i.nombre AS razon_social, o.anio,"  # noqa: S608
            " o.numero, o.fecha_emision, o.presupuesto_soles, o.estado,"
            " o.combustible_id, o.creado_en"
            " FROM ordenes_compra o"
            " JOIN instituciones i ON i.id = o.institucion_id"
            " WHERE o.institucion_id = :institucion"
            " AND o.presupuesto_soles = :presupuesto AND o.fecha_emision = :fecha"
            + extra
            + " ORDER BY o.id"
        ),
        {
            **params,
            "presupuesto": presupuesto_soles,
            "fecha": fecha_emision,
        },
    )
    return next(iter([dict(f) for f in filas.mappings()]), None)


async def posible_duplicado(
    sesion: AsyncSession, *, institucion_id: int, presupuesto_soles: Decimal, fecha_emision
) -> dict | None:
    """ORD-08: consulta directa de la advertencia, para cruzar antes de guardar."""
    return await _duplicado_exacto(
        sesion,
        institucion_id=institucion_id,
        presupuesto_soles=presupuesto_soles,
        fecha_emision=fecha_emision,
        id_excluir=None,
    )


def _rechazar_duplicado(duplicado: dict | None, confirmado: bool) -> None:
    if duplicado is not None and not confirmado:
        raise ErrorDominio(
            409,
            "ORDEN_POSIBLE_DUPLICADA",
            "Parece duplicada: la misma institución ya registró esa fecha con ese monto.",
            detalles={
                "id": duplicado["id"],
                "numero": duplicado["numero"],
                "anio": duplicado["anio"],
                "estado": duplicado["estado"],
            },
        )


async def _institucion_activa(sesion: AsyncSession, id_institucion: int) -> dict:
    filas = await sesion.execute(
        text(
            "SELECT id, nombre, estado, modalidad_numeracion"
            " FROM instituciones WHERE id = :id"
        ),
        {"id": id_institucion},
    )
    fila = filas.mappings().one_or_none()
    if fila is None:
        raise ErrorDominio(
            422,
            "INSTITUCION_INEXISTENTE",
            "La institución indicada no existe.",
            detalles={"campo": "institucion_id"},
        )
    datos = dict(fila)
    if datos["estado"] != "activa":
        raise ErrorDominio(
            422,
            "INSTITUCION_INACTIVA",
            "No se registra una orden sobre una institución desactivada.",
            detalles={"campo": "institucion_id"},
        )
    return datos


async def _combustible_valido(sesion: AsyncSession, combustible_id: int | None) -> None:
    """ORD-01: combustible opcional; si se pasa, debe existir y estar activo."""
    if combustible_id is None:
        return
    filas = await sesion.execute(
        text("SELECT activo FROM combustibles WHERE id = :id"), {"id": combustible_id}
    )
    fila = filas.mappings().one_or_none()
    if fila is None:
        raise ErrorDominio(
            422,
            "COMBUSTIBLE_INEXISTENTE",
            "El combustible indicado no existe.",
            detalles={"campo": "combustible_id"},
        )
    if not fila["activo"]:
        raise ErrorDominio(
            422,
            "COMBUSTIBLE_INACTIVO",
            "Un combustible inactivo no puede elegirse en órdenes nuevas.",
            detalles={"campo": "combustible_id"},
        )


def _serie_valida(
    modalidad_numeracion: str, serie_desde: int | None, serie_hasta: int | None
) -> None:
    """ORD-01: la serie aplica solo con numeración por orden y rango coherente."""
    hay_serie = serie_desde is not None or serie_hasta is not None
    if hay_serie and modalidad_numeracion != "por_orden":
        raise ErrorDominio(
            422,
            "SERIE_NO_APLICABLE",
            "La serie solo aplica a instituciones con numeración por orden.",
            detalles={"campo": "serie_desde"},
        )
    if (serie_desde is None) != (serie_hasta is None):
        raise ErrorDominio(
            422,
            "SERIE_INCOMPLETA",
            "serie_desde y serie_hasta van juntos.",
            detalles={"campo": "serie_hasta"},
        )
    if serie_desde is not None and serie_hasta is not None and serie_desde > serie_hasta:
        raise ErrorDominio(
            422,
            "SERIE_INVALIDA",
            "serie_desde debe ser menor o igual que serie_hasta.",
            detalles={"campo": "serie_desde"},
        )


async def crear(
    sesion: AsyncSession,
    *,
    institucion_id: int,
    numero: int | None,
    fecha_emision,
    presupuesto_soles: Decimal,
    observaciones: str | None,
    combustible_id: int | None,
    serie_desde: int | None,
    serie_hasta: int | None,
    estado_inicial: str,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
    confirmar_duplicado: bool,
) -> int:
    """ORD-01/02: alta con institución activa, presupuesto > 0 (lo fija el
    esquema) y control de duplicados. `estado_inicial` es `borrador` o
    `vigente`; el año sale de la fecha (RN-01/ORD-02).
    """
    if estado_inicial not in ("borrador", "vigente"):
        raise ErrorDominio(
            422, "ESTADO_INICIAL_INVALIDO", "El estado inicial debe ser borrador o vigente."
        )
    if fecha_emision > tiempo.hoy():
        raise ErrorDominio(
            422,
            "FECHA_FUTURA",
            "La fecha de emisión no puede ser posterior a hoy (Lima).",
            detalles={"campo": "fecha_emision"},
        )
    institucion = await _institucion_activa(sesion, institucion_id)
    await _combustible_valido(sesion, combustible_id)
    _serie_valida(institucion["modalidad_numeracion"], serie_desde, serie_hasta)
    _rechazar_duplicado(
        await _duplicado_exacto(
            sesion,
            institucion_id=institucion_id,
            presupuesto_soles=presupuesto_soles,
            fecha_emision=fecha_emision,
            id_excluir=None,
        ),
        confirmar_duplicado,
    )
    anio = fecha_emision.year
    if numero is None:
        filas = await sesion.execute(
            text(
                "SELECT coalesce(max(cast(numero AS bigint)), 0) + 1"
                " FROM ordenes_compra"
                " WHERE institucion_id = :institucion AND anio = :anio"
                " AND numero ~ '^[0-9]+$'"
            ),
            {"institucion": institucion_id, "anio": anio},
        )
        numero = str(int(filas.scalar_one()))
    else:
        numero = str(numero)
    # RF-ORD-02: el rechazo enlaza a la orden existente. Un cheque previo
    # entrega el id (el `IntegrityError` del índice único queda como
    # respaldo de carrera y conserva el propio código).
    fila_previa = await sesion.execute(
        text(
            "SELECT id FROM ordenes_compra"
            " WHERE institucion_id = :institucion AND anio = :anio AND numero = :numero"
        ),
        {"institucion": institucion_id, "anio": anio, "numero": numero},
    )
    id_previo = fila_previa.scalar_one_or_none()
    if id_previo is not None:
        raise ErrorDominio(
            409,
            "ORDEN_DUPLICADA",
            "Ya existe otra orden con ese número para la institución y el año.",
            detalles={"campo": "numero", "valor": numero, "orden_id": int(id_previo)},
        )
    try:
        filas = await sesion.execute(
            text(
                """
                INSERT INTO ordenes_compra (
                    institucion_id, anio, numero, fecha_emision, presupuesto_soles,
                    observaciones, estado, serie_desde, serie_hasta, combustible_id,
                    creado_por
                ) VALUES (
                    :institucion, :anio, :numero, :fecha, :presupuesto,
                    :observaciones, :estado, :serie_desde, :serie_hasta,
                    :combustible, :autor
                )
                RETURNING id
                """
            ),
            {
                "institucion": institucion_id,
                "anio": anio,
                "numero": numero,
                "fecha": fecha_emision,
                "presupuesto": presupuesto_soles,
                "observaciones": observaciones,
                "estado": estado_inicial,
                "serie_desde": serie_desde,
                "serie_hasta": serie_hasta,
                "combustible": combustible_id,
                "autor": actor_id,
            },
        )
        id_orden = int(filas.scalar_one())
    except IntegrityError as error:
        if getattr(error.orig, "pgcode", None) == CODIGO_UNICO_VIOLADO:
            raise ErrorDominio(
                409,
                "ORDEN_DUPLICADA",
                "Ya existe otra orden con ese número para la institución y el año.",
                detalles={"campo": "numero", "valor": numero},
            ) from error
        raise
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="orden_creada",
        entidad="ordenes_compra",
        entidad_id=id_orden,
        antes=None,
        despues={"numero": numero, "anio": anio, "estado": estado_inicial},
        ip=ip,
        user_agent=user_agent,
    )
    return id_orden


async def obtener(sesion: AsyncSession, id_orden: int) -> dict:
    """ORD-06/ORD-09: ficha con totales derivados de sus vales (RN-03).

    Los vales anulados no cuentan para el presupuesto comprometido la Fase 7
    los ajusta contra el saldo no consumido (RN-18); el consumo acumulado
    queda visible con `cantidad_inicial - saldo` de cada vale vivo.
    """
    orden = await _obtener_orden(sesion, id_orden)
    filas_agregado = await sesion.execute(
        text(
            """
            SELECT coalesce(sum(valor_soles), 0)::numeric AS emitido_soles,
                   coalesce(sum(cantidad_inicial), 0)::numeric AS emitido_galones,
                   count(*)::int AS vales
              FROM vales
             WHERE orden_compra_id = :id AND estado <> 'anulado'
            """
        ),
        {"id": id_orden},
    )
    agregado = filas_agregado.mappings().one()
    filas_total_orden = await sesion.execute(
        text(
            """
            SELECT count(*)::int
              FROM vales
             WHERE orden_compra_id = :id
            """
        ),
        {"id": id_orden},
    )
    total_vales = int(filas_total_orden.scalar_one())
    filas_consumo = await sesion.execute(
        text(
            """
            SELECT coalesce(sum(cantidad_inicial - saldo), 0)::numeric
              FROM vales
             WHERE orden_compra_id = :id AND estado <> 'anulado'
            """
        ),
        {"id": id_orden},
    )
    filas_vales = await sesion.execute(
        text(
            """
            SELECT id, emisor, numero_estacion, numero_entidad, estado, saldo,
                   valor_soles, fecha_emision
              FROM vales
             WHERE orden_compra_id = :id
          ORDER BY id
            """
        ),
        {"id": id_orden},
    )
    emitido_soles = dinero.a_decimal(agregado["emitido_soles"] or 0)
    presupuesto = dinero.a_decimal(orden["presupuesto_soles"])
    return {
        **orden,
        "total_emitido_soles": dinero.como_texto(emitido_soles),
        "total_emitido_galones": dinero.como_texto(
            dinero.a_decimal(agregado["emitido_galones"] or 0)
        ),
        "presupuesto_restante_soles": dinero.como_texto(presupuesto - emitido_soles),
        "total_consumido_soles": dinero.como_texto(
            dinero.a_decimal(filas_consumo.scalar_one() or 0)
        ),
        "cantidad_vales": total_vales,
        "vales": [dict(f) for f in filas_vales.mappings()],
    }


async def editar(
    sesion: AsyncSession,
    id_orden: int,
    *,
    datos: dict,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> dict:
    """ORD-03: edición parcial. Solo borrador/vigente; con vales ya emitidos
    únicamente `observaciones`. El presupuesto entra por `presupuesto_soles`
    pero se contrasta contra el resto de la institución antes de persistir.
    """
    anterior = await _obtener_orden(sesion, id_orden)
    if anterior["estado"] in ("cerrada", "anulada"):
        raise ErrorDominio(
            409, "ESTADO_INVALIDO", "Solo puede editarse una orden en borrador o vigente."
        )
    filas_conteo = await sesion.execute(
        text("SELECT count(*) FROM vales WHERE orden_compra_id = :id"), {"id": id_orden}
    )
    con_vales = int(filas_conteo.scalar_one()) > 0
    campos_solicitados = {k: v for k, v in datos.items() if v is not None}
    if con_vales and set(campos_solicitados) - {"observaciones"}:
        raise ErrorDominio(
            409,
            "ORDEN_CON_VALES",
            "Una orden con vales emitidos solo acepta el campo observaciones.",
        )
    duplicado = None
    if "presupuesto_soles" in datos and datos["presupuesto_soles"] is not None:
        duplicado = await _duplicado_exacto(
            sesion,
            institucion_id=anterior["institucion_id"],
            presupuesto_soles=datos["presupuesto_soles"],
            fecha_emision=anterior["fecha_emision"],
            id_excluir=id_orden,
        )
    _rechazar_duplicado(duplicado, bool(datos.get("confirmar_duplicado")))
    if "serie_desde" in datos or "serie_hasta" in datos:
        serie_desde = datos.get("serie_desde", anterior["serie_desde"])
        serie_hasta = datos.get("serie_hasta", anterior["serie_hasta"])
        _serie_valida(anterior["modalidad_numeracion"], serie_desde, serie_hasta)
    conjuntos: list[str] = []
    params: dict[str, object] = {"id": id_orden}
    for campo in (
        "presupuesto_soles", "observaciones", "serie_desde", "serie_hasta", "combustible_id"
    ):
        if campo in datos and datos[campo] is not None:
            conjuntos.append(f"{campo} = :{campo}")
            params[campo] = datos[campo]
    if not conjuntos:
        return anterior
    conjuntos.append("actualizado_en = now()")
    filas = await sesion.execute(
        text(
            f"UPDATE ordenes_compra SET {', '.join(conjuntos)}"  # noqa: S608
            " WHERE id = :id RETURNING *"
        ),
        params,
    )
    fila = dict(filas.mappings().one())
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="orden_editada",
        entidad="ordenes_compra",
        entidad_id=id_orden,
        antes=anterior,
        despues=fila,
        ip=ip,
        user_agent=user_agent,
    )
    return fila


async def adjuntar_archivo(
    sesion: AsyncSession,
    id_orden: int,
    *,
    datos_archivo: bytes,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> dict:
    """ORD-04: documento adjunto validado por firma; se reemplaza si ya había uno."""
    orden = await _obtener_orden(sesion, id_orden)
    if orden["estado"] == "anulada":
        raise ErrorDominio(
            409,
            "ESTADO_INVALIDO",
            "No puede adjuntarse un documento a una orden anulada.",
        )
    tope_mb = await parametros.numero(sesion, "archivo_max_mb")
    archivo = archivos.validar(
        datos_archivo,
        uso="documento",
        formatos=("pdf", "jpg", "png"),
        maximo_bytes=tope_mb * 1024 * 1024,
    )
    exportado = await archivos.guardar_documento_orden(
        archivo.contenido, archivo.extension, orden["fecha_emision"].year
    )
    path_anterior = orden["archivo_path"]
    await sesion.execute(
        text(
            """
            UPDATE ordenes_compra
               SET archivo_path = :path, archivo_tipo = :tipo,
                   archivo_tamano = :tamano, archivo_hash = :hash,
                   actualizado_en = now()
             WHERE id = :id
            """
        ),
        {
            "path": exportado.path_relativo,
            "tipo": exportado.media_type,
            "tamano": exportado.tamano,
            "hash": exportado.hash_sha256,
            "id": id_orden,
        },
    )
    # El archivo reemplazado deja de estar referenciado; se retira del almacén.
    if path_anterior:
        await archivos.eliminar_documento(path_anterior)
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="orden_archivo_adjuntado",
        entidad="ordenes_compra",
        entidad_id=id_orden,
        antes={"archivo_path": path_anterior},
        despues={
            "archivo_path": exportado.path_relativo,
            "archivo_tipo": exportado.media_type,
        },
        ip=ip,
        user_agent=user_agent,
    )
    return {"media_type": exportado.media_type, "archivo_path": exportado.path_relativo}


async def leer_archivo(sesion: AsyncSession, id_orden: int) -> tuple[str, str, int, str]:
    """ORD-04: descarga del documento privado; devuelve `(media_type, path, tamano, hash)`.

    El router sirve los bytes con `archivos.leer_bloques`, que verifica el
    hash registrado (Dani: ningún archivo en disco ajeno sale de la API).
    """
    orden = await _obtener_orden(sesion, id_orden)
    if not orden["archivo_path"]:
        raise ErrorDominio(
            404, "ARCHIVO_NO_ADJUNTO", "La orden no tiene documento adjunto."
        )
    return (
        orden["archivo_tipo"] or "application/pdf",
        orden["archivo_path"],
        int(orden["archivo_tamano"] or 0),
        orden["archivo_hash"] or "",
    )


async def marcar_vigente(
    sesion: AsyncSession,
    id_orden: int,
    *,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> dict:
    """ORD-07: borrador → vigente. Única salida del borrador aparte de anular."""
    return await _transicionar(
        sesion, id_orden, "vigente", actor_id=actor_id, ip=ip, user_agent=user_agent
    )


async def cerrar(
    sesion: AsyncSession,
    id_orden: int,
    *,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> dict:
    """ORD-10: vigente → cerrada. Cierra la orden con sus vales terminados."""
    return await _transicionar(
        sesion, id_orden, "cerrada", actor_id=actor_id, ip=ip, user_agent=user_agent
    )


async def anular(
    sesion: AsyncSession,
    id_orden: int,
    *,
    motivo: str,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> dict:
    """ORD-09/RN-17: invalidación con motivo obligatorio y sin consumos."""
    if not str(motivo).strip():
        raise ErrorDominio(
            422,
            "MOTIVO_OBLIGATORIO",
            "El motivo es obligatorio para anular una orden.",
            detalles={"campo": "motivo"},
        )
    if tiene_consumos(id_orden):
        raise ErrorDominio(
            409,
            "ORDEN_CON_CONSUMOS",
            "Una orden con consumos registrados no puede anularse; solo puede cerrarse.",
        )
    return await _transicionar(
        sesion,
        id_orden,
        "anulada",
        motivo=motivo,
        actor_id=actor_id,
        ip=ip,
        user_agent=user_agent,
    )


async def _transicionar(
    sesion: AsyncSession,
    id_orden: int,
    estado_nuevo: str,
    *,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
    motivo: str | None = None,
) -> dict:
    """Sección 3.4: única transición posible según el estado actual."""
    orden = await _obtener_orden(sesion, id_orden)
    estado_actual = orden["estado"]
    if estado_nuevo not in TRANSICIONES_VALIDAS.get(estado_actual, set()):
        raise ErrorDominio(
            409,
            "TRANSICION_INVALIDA",
            f"Una orden en estado {estado_actual} no puede pasar a {estado_nuevo}.",
            detalles={"estado_actual": estado_actual, "estado_nuevo": estado_nuevo},
        )
    if estado_nuevo == "anulada":
        filas = await sesion.execute(
            text(
                """
                UPDATE ordenes_compra
                   SET estado = 'anulada', motivo_anulacion = :motivo,
                       actualizado_en = now()
                 WHERE id = :id
                RETURNING *
                """
            ),
            {"motivo": motivo, "id": id_orden},
        )
    else:
        filas = await sesion.execute(
            text(
                "UPDATE ordenes_compra SET estado = :nuevo, actualizado_en = now()"
                " WHERE id = :id RETURNING *"
            ),
            {"nuevo": estado_nuevo, "id": id_orden},
        )
    fila = dict(filas.mappings().one())
    accion = {
        "vigente": "orden_marcada_vigente",
        "cerrada": "orden_cerrada",
        "anulada": "orden_anulada",
    }[estado_nuevo]
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion=accion,
        entidad="ordenes_compra",
        entidad_id=id_orden,
        antes={"estado": estado_actual},
        despues={"estado": estado_nuevo, "motivo_anulacion": motivo},
        ip=ip,
        user_agent=user_agent,
    )
    return fila


async def serie(
    sesion: AsyncSession, id_orden: int
) -> dict:
    """ORD-02b/VAL-15: stock de la serie de una orden con numeración por orden."""
    orden = await _obtener_orden(sesion, id_orden)
    if orden["serie_desde"] is None or orden["serie_hasta"] is None:
        raise ErrorDominio(409, "SIN_SERIE", "La orden no tiene rango de serie definido.")
    filas = await sesion.execute(
        text(
            "SELECT numero_entidad FROM vales"
            " WHERE orden_compra_id = :id AND emisor = 'entidad'"
        ),
        {"id": id_orden},
    )
    usados: set[int] = set()
    for fila in filas.mappings():
        valor = fila["numero_entidad"]
        if valor is not None and valor.isdigit():
            usados.add(int(valor))
    disponibles = [
        numero
        for numero in range(orden["serie_desde"], orden["serie_hasta"] + 1)
        if numero not in usados
    ]
    total_rango = orden["serie_hasta"] - orden["serie_desde"] + 1
    return {
        "serie_desde": orden["serie_desde"],
        "serie_hasta": orden["serie_hasta"],
        "total_rango": total_rango,
        "usados": sorted(usados),
        "disponibles": disponibles,
    }
