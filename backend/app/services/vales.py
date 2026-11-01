"""Casos de uso del módulo Vales (VAL-01..08, VAL-12..15, QRY-01, plan 5.9).

La emisión se bloquea contra el presupuesto (RN-03, VAL-03): la fila de la
orden se toma con `FOR UPDATE`, se suma el compromiso vigente
(`valor_comprometido_soles` de vales no anulados) y se calcula todo bajo el
mismo bloqueo, de modo que dos emisiones simultáneas nunca exceden el
presupuesto. La operación es atómica (VAL-04): todos los vales y sus
movimientos de emisión, o ninguno.

Los vales de entidad (VAL-05, D-02) siempre se vinculan a una orden; el
número lo entrega la institución y su unicidad depende de la modalidad
(RN-15): `institucion:<id>:<numero>` con numeración general,
`orden:<id>:<numero>` con numeración por orden (P-11: descuentan del
presupuesto con el precio vigente al registrarlos).

El saldo es derivado (RN-08): cada variación deja su movimiento con el
saldo posterior, y las tablas de movimientos son inmutables (RN-11).
"""

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import dinero, tiempo
from app.errors import ErrorDominio
from app.services import auditoria, configuracion, numeracion, parametros, precios

CODIGO_UNICO_VIOLADO = "23505"
MAXIMA_POR_PAGINA = 100
CANDIDATOS_BUSQUEDA = 8

EMISOR_ESTACION = "estacion"
EMISOR_ENTIDAD = "entidad"


# ---------------------------------------------------------------------------
# Helpers de orden y presupuesto
# ---------------------------------------------------------------------------


async def _orden_bajo_bloqueo(sesion: AsyncSession, orden_id: int) -> dict:
    """La orden con FOR UPDATE y los datos que la emisión necesita.

    Emitir vale exige orden `vigente` (VAL-01: ni borrador, ni cerrada,
    ni anulada — RN-13). El bloqueo serializa emisiones simultáneas.
    """
    fila = (
        await sesion.execute(
            text(
                """
                SELECT o.id, o.institucion_id, o.anio, o.numero, o.estado,
                       o.presupuesto_soles, o.serie_desde, o.serie_hasta,
                       i.nombre AS razon_social,
                       i.modalidad_numeracion
                  FROM ordenes_compra o
                  JOIN instituciones i ON i.id = o.institucion_id
                 WHERE o.id = :id
                FOR UPDATE OF o
                """
            ),
            {"id": orden_id},
        )
    ).mappings().one_or_none()
    if fila is None:
        raise ErrorDominio(404, "ORDEN_NO_ENCONTRADA", "La orden de compra no existe.")
    orden = dict(fila)
    if orden["estado"] != "vigente":
        raise ErrorDominio(
            409,
            "ORDEN_NO_EMITIBLE",
            "Solo se emiten vales sobre una orden vigente.",
            detalles={"estado_actual": orden["estado"]},
        )
    return orden


async def _comprometido_soles(sesion: AsyncSession, orden_id: int) -> Decimal:
    """VAL-03/RN-03: presupuesto comprometido por vales no anulados."""
    return dinero.a_decimal(
        (
            await sesion.execute(
                text(
                    "SELECT coalesce(sum(valor_comprometido_soles), 0)"
                    " FROM vales WHERE orden_compra_id = :id AND estado <> 'anulado'"
                ),
                {"id": orden_id},
            )
        ).scalar_one()
    )


def _rechazar_exceso(
    presupuesto: Decimal,
    comprometido: Decimal,
    nuevo: Decimal,
    precio: Decimal,
) -> None:
    """409 PRESUPUESTO_EXCEDIDO con restante y máximo de galones (VAL-03)."""
    resta = presupuesto - comprometido
    restante = dinero.monto(resta)
    if nuevo > restante:
        maximo = restante / precio if dinero.es_positivo(precio) else Decimal("0")
        raise ErrorDominio(
            409,
            "PRESUPUESTO_EXCEDIDO",
            "La emisión excede el presupuesto de la orden.",
            detalles={
                "presupuesto_restante_soles": dinero.como_texto(restante),
                "maximo_galones": dinero.como_texto(maximo),
            },
        )


def _verificar_vencimiento(fecha_emision, fecha_vencimiento) -> None:
    """P-02: la fecha de vencimiento es opcional, pero si viene no es anterior."""
    if fecha_vencimiento is None:
        return
    if fecha_vencimiento < fecha_emision:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"fecha_vencimiento": ["El vencimiento no puede ser anterior a hoy."]},
        )


def _a_cantidad(valor: str) -> Decimal:
    """Cantidad en galones con 2 decimales y mayor que cero (VAL-01)."""
    try:
        cantidad = dinero.cantidad(valor)
    except dinero.ErrorNumero as exc:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"cantidades": ["Cada cantidad debe ser un número con hasta 2 decimales."]},
        ) from exc
    if not dinero.es_positivo(cantidad):
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"cantidades": ["Cada cantidad debe ser mayor que cero."]},
        )
    return cantidad


# ---------------------------------------------------------------------------
# Simulación (vista previa) y emisión de vales de estación
# ---------------------------------------------------------------------------


async def simulacion(
    sesion: AsyncSession,
    orden_id: int,
    *,
    combustible_id: int,
    cantidades: list[str],
) -> dict:
    """VAL-01/VAL-03/CMB-04: vista previa sin guardar nada."""
    orden = await _orden_bajo_bloqueo(sesion, orden_id)
    precio = dinero.a_decimal(
        (await precios.vigente_a(sesion, combustible_id))["precio_galon"]
    )
    cantidades_dec = [_a_cantidad(c) for c in cantidades]
    total_nuevo = sum(
        (precios.calcular_valor(c, precio) for c in cantidades_dec), Decimal("0.00")
    )
    presupuestado = dinero.a_decimal(orden["presupuesto_soles"])
    comprometido = await _comprometido_soles(sesion, orden_id)
    restante = dinero.monto(presupuestado - comprometido)
    maximo = restante / precio if dinero.es_positivo(precio) else Decimal("0.00")
    _rechazar_exceso(dinero.monto(presupuestado), comprometido, total_nuevo, precio)
    return {
        "orden_compra_id": orden["id"],
        "precio_galon": dinero.como_texto(precio),
        "presupuesto_restante_soles": dinero.como_texto(restante),
        "maximo_galones": dinero.como_texto(maximo),
        "vales": [
            {
                "cantidad_galones": dinero.como_texto(cantidad),
                "valor_soles": dinero.como_texto(
                    precios.calcular_valor(cantidad, precio)
                ),
            }
            for cantidad in cantidades_dec
        ],
        "total_soles": dinero.como_texto(total_nuevo),
    }


async def emitir_estacion(
    sesion: AsyncSession,
    orden_id: int,
    *,
    combustible_id: int,
    cantidades: list[str],
    fecha_vencimiento,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> list[dict]:
    """VAL-01..04: emisión atómica de vales de estación sobre orden vigente.

    Toma el precio vigente del combustible (404 SIN_PRECIO_VIGENTE si no
    hay), crea todos los vales con su movimiento de emisión o ninguno, y
    controla el presupuesto total de la operación bajo el bloqueo de la
    orden.
    """
    if not cantidades:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"cantidades": ["Indica al menos un vale con su cantidad."]},
        )
    orden = await _orden_bajo_bloqueo(sesion, orden_id)
    precio = dinero.a_decimal(
        (await precios.vigente_a(sesion, combustible_id))["precio_galon"]
    )
    cantidades_dec = [_a_cantidad(c) for c in cantidades]
    total_nuevo = sum(
        (precios.calcular_valor(c, precio) for c in cantidades_dec), Decimal("0.00")
    )
    presupuestado = dinero.a_decimal(orden["presupuesto_soles"])
    comprometido = await _comprometido_soles(sesion, orden_id)
    _rechazar_exceso(dinero.monto(presupuestado), comprometido, total_nuevo, precio)
    fecha_emision = tiempo.hoy()
    _verificar_vencimiento(fecha_emision, fecha_vencimiento)
    id_estacion = await _id_estacion(sesion)
    emitidos: list[dict] = []
    for cantidad in cantidades_dec:
        valor = precios.calcular_valor(cantidad, precio)
        numero = await numeracion.asignar_numero_estacion(sesion, fecha_emision)
        fila = (
            await sesion.execute(
                text(
                    """
                    INSERT INTO vales (
                        numero_estacion, orden_compra_id, emisor, combustible_id,
                        cantidad_inicial, precio_galon_aplicado, valor_soles,
                        valor_comprometido_soles, saldo, estado, fecha_emision,
                        fecha_vencimiento, creado_por
                    ) VALUES (
                        :numero, :orden, :emisor, :combustible,
                        :cantidad, :precio, :valor, :compromiso, :saldo,
                        :estado, :fecha_emision, :fecha_venc, :autor
                    )
                    RETURNING id
                    """
                ),
                {
                    "numero": numero,
                    "orden": orden["id"],
                    "emisor": EMISOR_ESTACION,
                    "combustible": combustible_id,
                    "cantidad": cantidad,
                    "precio": precio,
                    "valor": valor,
                    "compromiso": valor,
                    "saldo": cantidad,
                    "estado": "activo",
                    "fecha_emision": fecha_emision,
                    "fecha_venc": fecha_vencimiento,
                    "autor": actor_id,
                },
            )
        ).mappings().one()
        await _movimiento_emision(
            sesion,
            vale_id=int(fila["id"]),
            cantidad=cantidad,
            valor=valor,
            precio=precio,
            actor_id=actor_id,
            estacion_id=id_estacion,
        )
        emitidos.append(
            {
                "id": int(fila["id"]),
                "numero_estacion": numero,
                "cantidad_inicial": dinero.como_texto(cantidad),
                "saldo": dinero.como_texto(cantidad),
                "valor_soles": dinero.como_texto(valor),
                "precio_galon_aplicado": dinero.como_texto(precio),
                "emisor": EMISOR_ESTACION,
                "estado": "activo",
            }
        )
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="vales_emitidos",
        entidad="ordenes_compra",
        entidad_id=orden_id,
        despues={
            "combustible_id": combustible_id,
            "vales": len(emitidos),
            "total_soles": dinero.como_texto(total_nuevo),
        },
        ip=ip,
        user_agent=user_agent,
    )
    return emitidos


# ---------------------------------------------------------------------------
# Movimientos
# ---------------------------------------------------------------------------


async def _id_estacion(sesion: AsyncSession) -> int:
    """CFG-02: la estación única activa; los movimientos la registran."""
    id_estacion = await configuracion.id_estacion_activa(sesion)
    if id_estacion is None:
        raise ErrorDominio(
            409,
            "ESTACION_NO_REGISTRADA",
            "Registra la ficha de la estación en configuración antes de operar vales.",
        )
    return id_estacion


async def _movimiento_emision(
    sesion: AsyncSession,
    *,
    vale_id: int,
    cantidad: Decimal,
    valor: Decimal,
    precio: Decimal,
    actor_id: int,
    estacion_id: int,
) -> None:
    await sesion.execute(
        text(
            """
            INSERT INTO movimientos_vale (
                vale_id, tipo, variacion, saldo_posterior,
                cantidad_galones, precio_galon, importe_soles,
                app_user_id, estacion_id
            ) VALUES (
                :vale, 'emision', :variacion, :saldo_posterior,
                :cantidad, :precio, :importe, :usuario, :estacion
            )
            """
        ),
        {
            "vale": vale_id,
            "variacion": cantidad,
            "saldo_posterior": cantidad,
            "cantidad": cantidad,
            "precio": precio,
            "importe": valor,
            "usuario": actor_id,
            "estacion": estacion_id,
        },
    )


# ---------------------------------------------------------------------------
# Vales de entidad
# ---------------------------------------------------------------------------


def _clave_numeracion(
    modalidad: str, orden_id: int, institucion_id: int, numero: str
) -> str:
    """D-02/RN-15: clave de unicidad según la modalidad de la institución."""
    if modalidad == "general":
        return f"institucion:{institucion_id}:{numero}"
    if modalidad == "por_orden":
        return f"orden:{orden_id}:{numero}"
    raise ErrorDominio(
        409,
        "VALE_ENTIDAD_NO_APLICABLE",
        "La institución no usa numeración propia de vales.",
    )




async def registrar_entidad(
    sesion: AsyncSession,
    orden_id: int,
    *,
    numero_entidad: str,
    combustible_id: int,
    cantidad: str,
    fecha_vencimiento,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> dict:
    """VAL-05/VAL-15: registro del vale que emitió la propia institución.

    Valida la unicidad según la modalidad (409 NUMERO_ENTIDAD_DUPLICADO),
    el rango autorizado de la orden (422 NUMERO_FUERA_DE_SERIE; 409
    SERIE_AGOTADA si todos los números del rango fueron usados) y las
    mismas reglas de presupuesto que los vales de estación (P-11).
    """
    numero_limpio = str(numero_entidad).strip()
    if not numero_limpio:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"numero_entidad": ["El número del vale de entidad es obligatorio."]},
        )
    orden = await _orden_bajo_bloqueo(sesion, orden_id)
    modalidad = orden["modalidad_numeracion"]
    if modalidad not in ("general", "por_orden"):
        raise ErrorDominio(
            409,
            "VALE_ENTIDAD_NO_APLICABLE",
            "La institución no usa numeración propia de vales.",
        )
    if orden["serie_desde"] is not None and str(numero_limpio).isdigit():
        usados = (
            await sesion.execute(
                text(
                    "SELECT numero_entidad FROM vales WHERE orden_compra_id = :orden"
                    " AND emisor = 'entidad'"
                ),
                {"orden": orden["id"]},
            )
        ).scalars()
        usados_rango = {int(u) for u in usados if u is not None and str(u).isdigit()}
        total_rango = orden["serie_hasta"] - orden["serie_desde"] + 1
        numero_int = int(numero_limpio)
        if numero_int not in usados_rango and len(usados_rango) >= total_rango:
            raise ErrorDominio(
                409,
                "SERIE_AGOTADA",
                "El rango de la serie está agotado: no quedan números disponibles.",
            )
        if not (
            orden["serie_desde"] <= numero_int <= orden["serie_hasta"]
        ):
            raise ErrorDominio(
                422,
                "NUMERO_FUERA_DE_SERIE",
                "El número del vale está fuera del rango autorizado de la orden.",
                detalles={
                    "serie_desde": orden["serie_desde"],
                    "serie_hasta": orden["serie_hasta"],
                },
            )
    elif orden["serie_desde"] is not None:
        raise ErrorDominio(
            422,
            "NUMERO_FUERA_DE_SERIE",
            "El número del vale está fuera del rango autorizado de la orden.",
            detalles={
                "serie_desde": orden["serie_desde"],
                "serie_hasta": orden["serie_hasta"],
            },
        )
    clave = _clave_numeracion(
        modalidad, orden["id"], orden["institucion_id"], numero_limpio
    )
    precio = dinero.a_decimal(
        (await precios.vigente_a(sesion, combustible_id))["precio_galon"]
    )
    cantidad_dec = _a_cantidad(cantidad)
    valor = precios.calcular_valor(cantidad_dec, precio)
    presupuestado = dinero.a_decimal(orden["presupuesto_soles"])
    comprometido = await _comprometido_soles(sesion, orden_id)
    _rechazar_exceso(dinero.monto(presupuestado), comprometido, valor, precio)
    fecha_emision = tiempo.hoy()
    _verificar_vencimiento(fecha_emision, fecha_vencimiento)
    id_estacion = await _id_estacion(sesion)
    try:
        id_vale = int(
            (
                await sesion.execute(
                    text(
                        """
                        INSERT INTO vales (
                            numero_entidad, clave_numeracion, orden_compra_id, emisor,
                            combustible_id, cantidad_inicial, precio_galon_aplicado,
                            valor_soles, valor_comprometido_soles, saldo, estado,
                            fecha_emision, fecha_vencimiento, creado_por
                        ) VALUES (
                            :numero, :clave, :orden, :emisor, :combustible,
                            :cantidad, :precio, :valor, :compromiso, :saldo,
                            :estado, :fecha_emision, :fecha_venc, :autor
                        )
                        RETURNING id
                        """
                    ),
                    {
                        "numero": numero_limpio,
                        "clave": clave,
                        "orden": orden["id"],
                        "emisor": EMISOR_ENTIDAD,
                        "combustible": combustible_id,
                        "cantidad": cantidad_dec,
                        "precio": precio,
                        "valor": valor,
                        "compromiso": valor,
                        "saldo": cantidad_dec,
                        "estado": "activo",
                        "fecha_emision": fecha_emision,
                        "fecha_venc": fecha_vencimiento,
                        "autor": actor_id,
                    },
                )
            ).scalar_one()
        )
    except IntegrityError as error:
        if getattr(error.orig, "pgcode", None) == CODIGO_UNICO_VIOLADO:
            raise ErrorDominio(
                409,
                "NUMERO_ENTIDAD_DUPLICADO",
                "Ese número de vale de entidad está duplicado.",
                detalles={"campo": "numero_entidad", "valor": numero_limpio},
            ) from error
        raise
    await _movimiento_emision(
        sesion,
        vale_id=id_vale,
        cantidad=cantidad_dec,
        valor=valor,
        precio=precio,
        actor_id=actor_id,
        estacion_id=id_estacion,
    )
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="vale_entidad_registrado",
        entidad="ordenes_compra",
        entidad_id=orden["id"],
        despues={
            "numero_entidad": numero_limpio,
            "valor_soles": dinero.como_texto(valor),
        },
        ip=ip,
        user_agent=user_agent,
    )
    return {
        "id": id_vale,
        "numero_entidad": numero_limpio,
        "cantidad_inicial": dinero.como_texto(cantidad_dec),
        "saldo": dinero.como_texto(cantidad_dec),
        "valor_soles": dinero.como_texto(valor),
        "precio_galon_aplicado": dinero.como_texto(precio),
        "emisor": EMISOR_ENTIDAD,
        "estado": "activo",
    }


# ---------------------------------------------------------------------------
# Consultas: listado, búsqueda, detalle y movimientos
# ---------------------------------------------------------------------------


def _vale_basico(fila: dict) -> dict:
    """Proyección común de listado/búsqueda con el consumo derivado (CON-12)."""
    inicial = dinero.a_decimal(fila["cantidad_inicial"])
    saldo = dinero.a_decimal(fila["saldo"])
    fila["consumido"] = dinero.como_texto(dinero.monto(inicial - saldo))
    fila["cantidad_inicial"] = dinero.como_texto(fila["cantidad_inicial"])
    fila["saldo"] = dinero.como_texto(fila["saldo"])
    fila["valor_soles"] = dinero.como_texto(fila["valor_soles"])
    return fila


def _fila_con_estado(fila: dict) -> dict:
    """VAL-08/RN-07: el vale vencido se reconoce al consultar."""
    if (
        fila.get("estado") == "activo"
        and fila.get("fecha_vencimiento") is not None
        and fila["fecha_vencimiento"] < tiempo.hoy()
    ):
        fila["estado"] = "vencido"
    return fila


async def listar(
    sesion: AsyncSession,
    *,
    q: str | None = None,
    institucion_id: int | None = None,
    orden_id: int | None = None,
    estado: str | None = None,
    combustible_id: int | None = None,
    emisor: str | None = None,
    pagina: int = 1,
    por_pagina: int = 20,
) -> tuple[list[dict], int]:
    """VAL-06: listado paginado con búsqueda por número y filtros."""
    por_pagina = min(max(por_pagina, 1), MAXIMA_POR_PAGINA)
    pagina = max(pagina, 1)
    condiciones: list[str] = []
    where_params: dict[str, object] = {}
    if q:
        condiciones.append("(v.numero_estacion::text = :q OR v.numero_entidad = :q)")
        where_params["q"] = q
    if institucion_id is not None:
        condiciones.append("o.institucion_id = :institucion")
        where_params["institucion"] = institucion_id
    if orden_id is not None:
        condiciones.append("v.orden_compra_id = :orden")
        where_params["orden"] = orden_id
    if estado:
        # RN-07: el vencimiento se reconoce al consultar; el filtro de estado
        # también usa el estado derivado (activo con fecha pasada → vencido).
        condiciones.append(
            "(CASE WHEN v.estado = 'activo' AND v.fecha_vencimiento < CURRENT_DATE"
            " THEN 'vencido' ELSE v.estado::text END) = :estado"
        )
        where_params["estado"] = estado
    if combustible_id is not None:
        condiciones.append("v.combustible_id = :combustible")
        where_params["combustible"] = combustible_id
    if emisor:
        condiciones.append("v.emisor = :emisor")
        where_params["emisor"] = emisor
    where = f" WHERE {' AND '.join(condiciones)}" if condiciones else ""
    total = int(
        (
            await sesion.execute(
                text(
                    "SELECT count(*) FROM vales v"  # noqa: S608 (where es interno)
                    " JOIN ordenes_compra o ON o.id = v.orden_compra_id"
                    + where
                ),
                where_params,
            )
        ).scalar_one()
    )
    filas = await sesion.execute(
        text(
            "SELECT v.id, v.emisor, v.numero_estacion, v.numero_entidad,"  # noqa: S608 (where es interno)
            " o.institucion_id, i.nombre AS razon_social, o.id AS orden_id,"
            " o.numero AS orden_numero, o.anio AS orden_anio,"
            " v.combustible_id, c.nombre AS combustible_nombre,"
            " v.cantidad_inicial, v.saldo, v.estado, v.fecha_emision,"
            " v.fecha_vencimiento, v.valor_soles, v.creado_en"
            " FROM vales v"
            " JOIN ordenes_compra o ON o.id = v.orden_compra_id"
            " JOIN instituciones i ON i.id = o.institucion_id"
            " JOIN combustibles c ON c.id = v.combustible_id"
            + where
            + " ORDER BY v.creado_en DESC, v.id DESC"
            " LIMIT :limite OFFSET :desplazamiento"
        ),
        {
            **where_params,
            "limite": por_pagina,
            "desplazamiento": (pagina - 1) * por_pagina,
        },
    )
    resultados = [
        _fila_con_estado(_vale_basico(dict(fila))) for fila in filas.mappings()
    ]
    return resultados, total


async def buscar(sesion: AsyncSession, q: str) -> list[dict]:
    """QRY-01: candidatos por código interno o número de entidad (hasta 8)."""
    texto = str(q).strip()
    if not texto:
        return []
    filas = await sesion.execute(
        text(
            "SELECT v.id, v.emisor, v.numero_estacion, v.numero_entidad,"
            " o.institucion_id, i.nombre AS razon_social, o.id AS orden_id,"
            " o.numero AS orden_numero, v.combustible_id,"
            " c.nombre AS combustible_nombre,"
            " v.cantidad_inicial, v.saldo, v.estado, v.valor_soles,"
            " v.fecha_vencimiento"
            " FROM vales v"
            " JOIN ordenes_compra o ON o.id = v.orden_compra_id"
            " JOIN instituciones i ON i.id = o.institucion_id"
            " JOIN combustibles c ON c.id = v.combustible_id"
            " WHERE v.numero_estacion::text = :q OR v.numero_entidad = :q"
            " ORDER BY v.id"
            " LIMIT :limite"
        ),
        {"q": texto, "limite": CANDIDATOS_BUSQUEDA},
    )
    return [_fila_con_estado(_vale_basico(dict(fila))) for fila in filas.mappings()]


async def detalle(sesion: AsyncSession, id_vale: int) -> dict:
    """VAL-07/VAL-08: ficha completa con orden, institución y derivados."""
    fila = (
        await sesion.execute(
            text(
                """
                SELECT v.*, i.id AS institucion_id, i.nombre AS institucion,
                       i.ruc AS institucion_ruc, o.numero AS orden_numero,
                       o.anio AS orden_anio, c.nombre AS combustible_nombre
                  FROM vales v
                  JOIN ordenes_compra o ON o.id = v.orden_compra_id
                  JOIN instituciones i ON i.id = o.institucion_id
                  JOIN combustibles c ON c.id = v.combustible_id
                 WHERE v.id = :id
                """
            ),
            {"id": id_vale},
        )
    ).mappings().one_or_none()
    if fila is None:
        raise ErrorDominio(404, "VALE_NO_ENCONTRADO", "El vale no existe.")
    ficha = _vale_basico(dict(fila))
    ficha["estado"] = _fila_con_estado(
        {"estado": ficha["estado"], "fecha_vencimiento": ficha.get("fecha_vencimiento")}
    )["estado"]
    ficha["precio_galon_aplicado"] = dinero.como_texto(ficha["precio_galon_aplicado"])
    ficha["valor_comprometido_soles"] = dinero.como_texto(
        ficha["valor_comprometido_soles"]
    )
    ficha.pop("clave_numeracion", None)
    return ficha


async def movimientos(sesion: AsyncSession, id_vale: int) -> list[dict]:
    """CON-12: línea de tiempo con cantidad, saldo posterior y motivo."""
    filas = await sesion.execute(
        text(
            "SELECT m.id, m.tipo, m.variacion, m.saldo_posterior,"
            " m.cantidad_galones, m.importe_soles, m.motivo, m.placa,"
            " m.conductor, m.fecha_local, m.creado_en, u.full_name AS usuario"
            " FROM movimientos_vale m"
            " JOIN app_users u ON u.id = m.app_user_id"
            " WHERE m.vale_id = :id"
            " ORDER BY m.id"
        ),
        {"id": id_vale},
    )
    return [
        {
            "id": int(fila["id"]),
            "tipo": str(fila["tipo"]),
            "variacion": dinero.como_texto(fila["variacion"]),
            "saldo_posterior": dinero.como_texto(fila["saldo_posterior"]),
            "cantidad_galones": dinero.como_texto(fila["cantidad_galones"])
            if fila["cantidad_galones"] is not None
            else None,
            "importe_soles": dinero.como_texto(fila["importe_soles"])
            if fila["importe_soles"] is not None
            else None,
            "motivo": fila["motivo"],
            "placa": fila["placa"],
            "conductor": fila["conductor"],
            "fecha_local": str(fila["fecha_local"])
            if fila["fecha_local"] is not None
            else None,
            "creado_en": fila["creado_en"],
            "usuario": fila["usuario"],
        }
        for fila in filas.mappings()
    ]


# ---------------------------------------------------------------------------
# Alertas e impresión
# ---------------------------------------------------------------------------


async def alertas(sesion: AsyncSession) -> dict:
    """VAL-13: saldo bajo y por vencer, según los parámetros de CFG-01."""
    umbral = await parametros.numero(sesion, "vale_umbral_saldo_bajo_pct")
    dias = await parametros.numero(sesion, "vale_dias_aviso_vencimiento")
    filas = await sesion.execute(
        text(
            "SELECT v.id, v.emisor, v.numero_estacion, v.numero_entidad,"
            " o.institucion_id, i.nombre AS razon_social, v.combustible_id,"
            " c.nombre AS combustible_nombre, v.cantidad_inicial, v.saldo,"
            " v.estado, v.fecha_vencimiento, v.valor_soles"
            " FROM vales v"
            " JOIN ordenes_compra o ON o.id = v.orden_compra_id"
            " JOIN instituciones i ON i.id = o.institucion_id"
            " JOIN combustibles c ON c.id = v.combustible_id"
            " WHERE v.estado = 'activo'"
            " ORDER BY v.id"
        )
    )
    hoy = tiempo.hoy()
    saldo_bajo: list[dict] = []
    por_vencer: list[dict] = []
    for fila in filas.mappings():
        datos = dict(fila)
        inicial = dinero.a_decimal(datos["cantidad_inicial"])
        saldo = dinero.a_decimal(datos["saldo"])
        if inicial > 0 and (saldo / inicial) * Decimal("100") <= umbral:
            datos["saldo_pct"] = dinero.como_texto(
                dinero.monto((saldo / inicial) * Decimal("100"))
            )
            saldo_bajo.append(_fila_con_estado(_vale_basico(datos)))
        if datos["fecha_vencimiento"] is not None:
            dias_restantes = (datos["fecha_vencimiento"] - hoy).days
            if dias_restantes <= dias:
                datos["dias_para_vencer"] = dias_restantes
                por_vencer.append(_fila_con_estado(_vale_basico(datos)))
    return {"saldo_bajo": saldo_bajo, "por_vencer": por_vencer}


async def registrar_impresion(
    sesion: AsyncSession,
    id_vale: int,
    *,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> dict:
    """VAL-12: registra la impresión; desde la segunda es duplicado."""
    ficha = await detalle(sesion, id_vale)
    conteo = int(
        (
            await sesion.execute(
                text("SELECT count(*) FROM impresiones_vale WHERE vale_id = :id"),
                {"id": id_vale},
            )
        ).scalar_one()
    )
    es_duplicado = conteo > 0
    await sesion.execute(
        text(
            "INSERT INTO impresiones_vale (vale_id, app_user_id, es_duplicado)"
            " VALUES (:vale, :usuario, :duplicado)"
        ),
        {"vale": id_vale, "usuario": actor_id, "duplicado": es_duplicado},
    )
    await sesion.execute(
        text("UPDATE vales SET veces_impreso = veces_impreso + 1 WHERE id = :id"),
        {"id": id_vale},
    )
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="vale_impreso",
        entidad="vales",
        entidad_id=id_vale,
        despues={"es_duplicado": es_duplicado},
        ip=ip,
        user_agent=user_agent,
    )
    return {**ficha, "es_duplicado": es_duplicado, "veces_impreso": conteo + 1}
