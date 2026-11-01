"""Pruebas de Fase 6: vales de estación y de entidad (VAL-01..07, VAL-12..15, QRY-01).

Cubre: permisos por rol, simulación sin guardar, numeración consecutiva con
el formato por defecto y configurable, precio vigente congelado por vale,
presupuesto excedido con techo de galones (VAL-03), emisión atómica
«todos o ninguno» (VAL-04), orden no emitible (borrador/cerrada/anulada),
combustible sin precio, unicidad de vales de entidad según modalidad
(RN-15), rango de serie y serie agotada, búsqueda con varias coincidencias
(QRY-01), listado con filtros y paginación, vencido reconocido al consultar
(RN-07), alertas (VAL-13), impresión con marca de duplicado (VAL-12) y
emisión simultánea de dos usuarios que nunca excede el presupuesto (RN-03).
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import date

import asyncpg
from httpx import AsyncClient

from app.config import obtener_settings
from app.db.migrar import a_dsn

_RUC_SEC = 0


def _ruc_unico() -> str:
    """RUC válido distinto por institución: 10 dígitos base + dígito verificador
    calculado con los pesos de SUNAT (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)."""
    global _RUC_SEC
    _RUC_SEC += 1
    pesos = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    base = f"20{_RUC_SEC:08d}"  # 10 dígitos, distintos entre sí de base
    suma = sum(int(d) * p for d, p in zip(base, pesos, strict=True))
    verificador = 11 - (suma % 11)
    verificador = {10: 0, 11: 1}.get(verificador, verificador)
    return base + str(verificador)


async def _admin(cliente: AsyncClient, correo: str = "valadmin@pruebas.pe") -> dict:
    from tests.test_usuarios import _crear_usuario, _iniciar_sesion

    await _crear_usuario(correo, rol="administrador")
    sesion = await _iniciar_sesion(cliente, correo)
    cliente.headers["Authorization"] = f"Bearer {sesion['access_token']}"
    return sesion


async def _usuario_de_rol(cliente: AsyncClient, correo: str, rol: str) -> None:
    from tests.test_usuarios import _crear_usuario, _iniciar_sesion

    await _crear_usuario(correo, rol=rol)
    sesion = await _iniciar_sesion(cliente, correo)
    cliente.headers["Authorization"] = f"Bearer {sesion['access_token']}"


@asynccontextmanager
async def _cliente_con_rol(cliente: AsyncClient, correo: str, rol: str):
    """Cliente HTTP independiente con sesión propia, para peticiones paralelas."""
    from httpx import ASGITransport

    from app.main import app as aplicacion
    from tests.test_usuarios import _crear_usuario, _iniciar_sesion

    await _crear_usuario(correo, rol=rol)
    sesion = await _iniciar_sesion(cliente, correo)
    paralelo = AsyncClient(
        transport=ASGITransport(app=aplicacion), base_url="http://pruebas.local"
    )
    paralelo.headers["Authorization"] = f"Bearer {sesion['access_token']}"
    try:
        yield paralelo
    finally:
        await paralelo.aclose()


async def _estacion(cliente: AsyncClient) -> None:
    """CFG-02: ficha única de la estación, obligatoria para operar vales."""
    ficha = await cliente.put(
        "/api/v1/configuracion/estacion",
        json={"nombre": "Estación San José", "ruc": "20100047218"},
    )
    assert ficha.status_code in (200, 201), ficha.text


async def _combustible(
    cliente: AsyncClient, nombre: str = "Gasohol 90", precio: str = "15.50"
) -> dict:
    creado = await cliente.post("/api/v1/combustibles", json={"nombre": nombre})
    assert creado.status_code == 201, creado.text
    tipo = creado.json()
    if precio is not None:
        precio_registrado = await cliente.post(
            f"/api/v1/combustibles/{tipo['id']}/precios",
            json={"precio_galon": precio, "vigente_desde": "2026-01-01"},
        )
        assert precio_registrado.status_code == 201, precio_registrado.text
    return tipo


async def _institucion(cliente: AsyncClient, **ajustes) -> dict:
    carga = {
        "nombre": "Municipalidad Distrital San Juan",
        "ruc": _ruc_unico(),
        "tipo": "publica",
        "modalidad_numeracion": "por_orden",
    }
    carga.update(ajustes)
    respuesta = await cliente.post("/api/v1/instituciones", json=carga)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


_DIA_ORDEN = 0


async def _orden(cliente: AsyncClient, institucion: dict, **ajustes) -> dict:
    """Órdenes de prueba: cada una lleva una fecha distinta (hoy - N días),
    de modo que la advertencia de duplicado de ORD-08 no detenga los altas ni
    aparezca una fecha futura."""
    from datetime import timedelta

    from app.core import tiempo

    global _DIA_ORDEN
    _DIA_ORDEN += 1
    fecha = tiempo.hoy() - timedelta(days=_DIA_ORDEN)
    carga = {
        "institucion_id": institucion["id"],
        "fecha_emision": ajustes.pop("fecha_emision", fecha.isoformat()),
        "presupuesto_soles": "5000.00",
        "estado": "borrador",
        "confirmar_duplicado": True,
    }
    carga.update(ajustes)
    respuesta = await cliente.post("/api/v1/ordenes", json=carga)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


async def _escenario(cliente: AsyncClient, **ajustes) -> dict:
    """Estación + combustible + institución + orden vigente, lista para emitir."""
    await _admin(cliente, correo=f"{ajustes.pop('correo', 'valadmin')}@pruebas.pe")
    await _estacion(cliente)
    precio = ajustes.pop("precio", "15.50")
    modalidad = ajustes.pop("modalidad", "por_orden")
    presupuesto = ajustes.pop("presupuesto", "5000.00")
    nombre = ajustes.pop("combustible_nombre", "Gasohol 90")
    datos = {
        "combustible": await _combustible(cliente, nombre=nombre, precio=precio),
        "institucion": await _institucion(cliente, modalidad_numeracion=modalidad),
    }
    datos["orden"] = await _orden(
        cliente, datos["institucion"], estado="vigente", presupuesto_soles=presupuesto, **ajustes
    )
    return datos


async def _emitir(cliente: AsyncClient, orden_id: int, combustible_id: int, **ajustes) -> dict:
    carga = {"combustible_id": combustible_id, "cantidades": ["10.00"]}
    carga.update(ajustes)
    return await cliente.post(f"/api/v1/ordenes/{orden_id}/vales", json=carga)


async def _registrar_entidad(
    cliente: AsyncClient, orden_id: int, combustible_id: int, numero: str
) -> dict:
    return await cliente.post(
        f"/api/v1/ordenes/{orden_id}/vales-entidad",
        json={
            "numero_entidad": numero,
            "combustible_id": combustible_id,
            "cantidad": "20.00",
        },
    )


def _valor_para_bd(columna: str, valor: object) -> object:
    """asyncpg exige `date` en las columnas de fecha, no cadenas ISO."""
    if columna.startswith("fecha_") and isinstance(valor, str):
        return date.fromisoformat(valor)
    return valor


async def _parchear_vale(vale_id: int, cambios: dict) -> None:
    """Actualiza una fila de `vales` directamente en la base de pruebas.

    Los disparadores de inalterabilidad solo cubren movimientos y auditoría,
    no `vales`, de modo que la prueba puede arrancar estados que todavía no
    salen de la API (saldo parcial, vencimientos pasados).
    """
    from app.config import obtener_settings as ajustes

    async def ejecutar() -> None:
        conexion = await asyncpg.connect(a_dsn(ajustes().database_url))
        try:
            columnas = ", ".join(f"{k} = ${i + 2}" for i, k in enumerate(cambios))
            await conexion.execute(
                f"UPDATE vales SET {columnas} WHERE id = $1",  # noqa: S608
                vale_id,
                *(_valor_para_bd(k, v) for k, v in cambios.items()),
            )
        finally:
            await conexion.close()

    await ejecutar()


# ---------------------------------------------------------------------------
# Permisos (sección 4.1)
# ---------------------------------------------------------------------------


async def test_permisos_por_rol(cliente):
    escenario = await _escenario(cliente)
    orden = escenario["orden"]
    combustible = escenario["combustible"]

    await _usuario_de_rol(cliente, "valofi@pruebas.pe", "oficina")
    listo = await cliente.get("/api/v1/vales")
    assert listo.status_code == 200
    emision = await _emitir(cliente, orden["id"], combustible["id"])
    assert emision.status_code == 201, emision.text

    cliente.headers.pop("Authorization")
    await _usuario_de_rol(cliente, "valdesp@pruebas.pe", "despachador")
    lectura = await cliente.get("/api/v1/vales")
    assert lectura.status_code == 403
    assert lectura.json()["codigo"] == "SIN_PERMISO"
    anulado = await cliente.post(
        f"/api/v1/vales/{emision.json()[0]['id']}/impresion"
    )
    assert anulado.status_code == 403


# ---------------------------------------------------------------------------
# Simulación (VAL-01/VAL-03) y numeración (VAL-02)
# ---------------------------------------------------------------------------


async def test_simulacion_no_guarda_nada(cliente):
    escenario = await _escenario(cliente)
    orden = escenario["orden"]
    combustible = escenario["combustible"]

    previo = await cliente.post(
        f"/api/v1/ordenes/{orden['id']}/vales/simulacion",
        json={"combustible_id": combustible["id"], "cantidades": ["100.00", "50.00"]},
    )
    assert previo.status_code == 200, previo.text
    datos = previo.json()
    assert datos["precio_galon"] == "15.50"
    assert datos["maximo_galones"] == "322.58"  # 5000.00 / 15.50 = 322.58…
    assert datos["total_soles"] == "2325.00"  # 150 x 15.50
    assert datos["presupuesto_restante_soles"] == "5000.00"
    lista = datos["vales"]
    assert [v["valor_soles"] for v in lista] == ["1550.00", "775.00"]

    # Nada se guardó.
    listado = (await cliente.get("/api/v1/vales")).json()
    assert listado["total"] == 0


async def test_numeracion_consecutiva_y_formato_configurable(cliente):
    escenario = await _escenario(cliente)
    orden = escenario["orden"]
    combustible = escenario["combustible"]

    # La tabla `parametros` no se trunc entre pruebas: restaura el formato
    # por defecto y después prueba uno configurable.
    restaurado = await cliente.put(
        "/api/v1/configuracion/parametros",
        json={"valores": {"vale_formato_numeracion_estacion": "{anio}-{secuencia:06d}"}},
    )
    assert restaurado.status_code == 200, restaurado.text

    primera = await _emitir(
        cliente, orden["id"], combustible["id"], cantidades=["20.00", "30.00"]
    )
    assert primera.status_code == 201, primera.text
    emitidos = primera.json()
    assert [v["numero_estacion"] for v in emitidos] == ["2026-000001", "2026-000002"]
    assert [int(v["id"]) for v in emitidos] == sorted(
        int(v["id"]) for v in emitidos
    )

    formato = await cliente.put(
        "/api/v1/configuracion/parametros",
        json={
            "valores": {
                "vale_formato_numeracion_estacion": "VA-{anio}-{secuencia:05d}"
            }
        },
    )
    assert formato.status_code == 200, formato.text
    segunda = await _emitir(cliente, orden["id"], combustible["id"])
    assert segunda.status_code == 201, segunda.text
    assert segunda.json()[0]["numero_estacion"] == "VA-2026-00003"


async def test_precio_vigente_congelado_por_vale(cliente):
    """Cada emisión escribe el precio vigente de ese momento y no lo cambia."""
    escenario = await _escenario(cliente, precio="15.50")
    orden = escenario["orden"]
    combustible = escenario["combustible"]

    primero = await _emitir(cliente, orden["id"], combustible["id"], cantidades=["10.00"])
    assert primero.status_code == 201
    assert primero.json()[0]["precio_galon_aplicado"] == "15.50"

    cambio = await cliente.post(
        f"/api/v1/combustibles/{combustible['id']}/precios",
        json={"precio_galon": "16.30", "vigente_desde": "2026-11-01"},
    )
    assert cambio.status_code == 201, cambio.text
    segundo = await _emitir(cliente, orden["id"], combustible["id"], cantidades=["10.00"])
    assert segundo.status_code == 201
    assert segundo.json()[0]["precio_galon_aplicado"] == "16.30"
    assert segundo.json()[0]["valor_soles"] == "163.00"

    # El primer vale conserva su precio y su valor original.
    detalle = (await cliente.get(f"/api/v1/vales/{primero.json()[0]['id']}")).json()
    assert detalle["precio_galon_aplicado"] == "15.50"
    assert detalle["valor_soles"] == "155.00"


# ---------------------------------------------------------------------------
# Presupuesto y atomicidad (VAL-03/VAL-04)
# ---------------------------------------------------------------------------


async def test_presupuesto_excedido_con_techo_de_galones(cliente):
    escenario = await _escenario(cliente, presupuesto="1000.00")
    orden = escenario["orden"]
    combustible = escenario["combustible"]

    excedido = await _emitir(
        cliente, orden["id"], combustible["id"], cantidades=["70.00"]
    )  # 70 x 15.50 = 1085.00 > 1000.00
    assert excedido.status_code == 409
    cuerpo = excedido.json()
    assert cuerpo["codigo"] == "PRESUPUESTO_EXCEDIDO"
    assert cuerpo["detalles"]["presupuesto_restante_soles"] == "1000.00"
    # Techo de galones a ese precio: 1000.00 / 15.50 = 65.3866… → 65.38.
    assert cuerpo["detalles"]["maximo_galones"] == "64.52"
    # Hasta el máximo de galones calculado excede por valor (64.52 x 15.50 =
    # 1000.06 > 1000.00): el límite real es el valor comprometido.
    en_techo = await _emitir(
        cliente, orden["id"], combustible["id"], cantidades=["64.52"]
    )
    assert en_techo.status_code == 409

    dentro = await _emitir(
        cliente, orden["id"], combustible["id"], cantidades=["64.00"]
    )  # 64 x 15.50 = 992.00 ≤ 1000.00
    assert dentro.status_code == 201, dentro.text

    # Con parte del presupuesto comprometido, el error devuelve el restante:
    # 1000.00 - 992.00 = 8.00, y 1.00 galón ya excede (15.50 > 8.00).
    casi = await _emitir(cliente, orden["id"], combustible["id"], cantidades=["1.00"])
    assert casi.status_code == 409
    assert casi.json()["detalles"]["presupuesto_restante_soles"] == "8.00"
    # Justo dentro del restante sí entra: 0.50 x 15.50 = 7.75 ≤ 8.00.
    final = await _emitir(
        cliente, orden["id"], combustible["id"], cantidades=["0.50"]
    )
    assert final.status_code == 201, final.text


async def test_emision_atomica_todos_o_ninguno(cliente):
    """Tres vales, el tercero rompe la petición; no queda ninguno (VAL-04)."""
    escenario = await _escenario(cliente)
    orden = escenario["orden"]
    combustible = escenario["combustible"]

    fallida = await _emitir(
        cliente, orden["id"], combustible["id"], cantidades=["100.00", "100.00", "-5.00"]
    )
    assert fallida.status_code == 422
    listado = (await cliente.get("/api/v1/vales")).json()
    assert listado["total"] == 0

    # También con presupuesto: la comprobación ocurre antes de escribir.
    escenario2 = await _escenario(
        cliente,
        correo="valadmin2",
        presupuesto="2000.00",
        combustible_nombre="Gasohol 95",
    )
    parcial = await _emitir(
        cliente,
        escenario2["orden"]["id"],
        escenario2["combustible"]["id"],
        cantidades=["80.00", "80.00", "20.00"],
    )  # 180 x 15.50 = 2790.00 > 2000.00
    assert parcial.status_code == 409
    listado = (await cliente.get("/api/v1/vales")).json()
    assert listado["total"] == 0


async def test_orden_no_emitible(cliente):
    """VAL-01/RN-13: solo la orden `vigente` emite vales."""
    escenario = await _escenario(cliente)
    combustible = escenario["combustible"]
    institucion = escenario["institucion"]

    borrador = await _orden(cliente, institucion)
    rechazo = await _emitir(cliente, borrador["id"], combustible["id"])
    assert rechazo.status_code == 409
    assert rechazo.json()["codigo"] == "ORDEN_NO_EMITIBLE"
    assert rechazo.json()["detalles"]["estado_actual"] == "borrador"

    cerrada = await _orden(cliente, institucion, estado="vigente")
    cierre = await cliente.post(f"/api/v1/ordenes/{cerrada['id']}/cerrar")
    assert cierre.status_code == 200
    post_cierre = await _emitir(cliente, cerrada["id"], combustible["id"])
    assert post_cierre.status_code == 409
    assert post_cierre.json()["detalles"]["estado_actual"] == "cerrada"

    anulable = await _orden(cliente, institucion, estado="vigente")
    anulacion = await cliente.post(
        f"/api/v1/ordenes/{anulable['id']}/anular", json={"motivo": "prueba de la fase 6"}
    )
    assert anulacion.status_code == 200, anulacion.text
    post_anulacion = await _emitir(cliente, anulable["id"], combustible["id"])
    assert post_anulacion.status_code == 409
    assert post_anulacion.json()["detalles"]["estado_actual"] == "anulada"


async def test_combustible_sin_precio_vigente_404(cliente):
    escenario = await _escenario(cliente)
    vacio = await _combustible(cliente, nombre="GLP", precio=None)

    intento = await _emitir(cliente, escenario["orden"]["id"], vacio["id"])
    assert intento.status_code == 404
    assert intento.json()["codigo"] == "SIN_PRECIO_VIGENTE"


# ---------------------------------------------------------------------------
# Vales de entidad (VAL-05, VAL-15, D-02, P-11)
# ---------------------------------------------------------------------------


async def test_vale_entidad_repetido_en_la_misma_serie_rechazado(cliente):
    escenario = await _escenario(cliente)
    orden = escenario["orden"]
    combustible = escenario["combustible"]

    primero = await _registrar_entidad(
        cliente, orden["id"], combustible["id"], "PO-0007"
    )
    assert primero.status_code == 201, primero.text
    assert primero.json()["numero_entidad"] == "PO-0007"
    assert primero.json()["numero_estacion"] is None

    repetido = await _registrar_entidad(
        cliente, orden["id"], combustible["id"], "PO-0007"
    )
    assert repetido.status_code == 409
    assert repetido.json()["codigo"] == "NUMERO_ENTIDAD_DUPLICADO"

    # Perfil de presupuesto: 20 x 15.50 = 310.00 comprometidos (P-11).
    filas = (await cliente.get("/api/v1/vales", params={"emisor": "entidad"})).json()
    assert filas["total"] == 1
    assert filas["items"][0]["valor_soles"] == "310.00"


async def test_vale_entidad_mismo_numero_en_otra_orden_aceptado(cliente):
    """D-02: numeración por orden puede repetirse en órdenes distintas."""
    escenario = await _escenario(cliente)
    orden = escenario["orden"]
    combustible = escenario["combustible"]

    primera = await _registrar_entidad(
        cliente, orden["id"], combustible["id"], "PO-0007"
    )
    assert primera.status_code == 201

    otra = await _orden(cliente, escenario["institucion"], estado="vigente")
    segunda = await _registrar_entidad(cliente, otra["id"], combustible["id"], "PO-0007")
    assert segunda.status_code == 201, segunda.text


async def test_vale_entidad_general_unico_por_institucion(cliente):
    """RN-15: con numeración general, el número es único por institución."""
    escenario = await _escenario(cliente, modalidad="general")
    orden = escenario["orden"]
    combustible = escenario["combustible"]

    primera = await _registrar_entidad(
        cliente, orden["id"], combustible["id"], "GEN-1"
    )
    assert primera.status_code == 201

    # El mismo número en otra orden de la misma institución choca (clave general).
    otra = await _orden(cliente, escenario["institucion"], estado="vigente")
    repetido = await _registrar_entidad(cliente, otra["id"], combustible["id"], "GEN-1")
    assert repetido.status_code == 409
    assert repetido.json()["codigo"] == "NUMERO_ENTIDAD_DUPLICADO"

    # En otra institución, el mismo número es válido.
    otra_municipalidad = await _institucion(cliente, modalidad_numeracion="general",
                                            nombre="Gobierno Regional Ica")
    orden3 = await _orden(cliente, otra_municipalidad, estado="vigente")
    cruzado = await _registrar_entidad(
        cliente, orden3["id"], combustible["id"], "GEN-1"
    )
    assert cruzado.status_code == 201


async def test_vale_entidad_no_aplicable(cliente):
    """Modalidad no_aplica: la institución no genera vales propios."""
    escenario = await _escenario(cliente, modalidad="no_aplica")
    intento = await _registrar_entidad(
        cliente, escenario["orden"]["id"], escenario["combustible"]["id"], "X-1"
    )
    assert intento.status_code == 409
    assert intento.json()["codigo"] == "VALE_ENTIDAD_NO_APLICABLE"


async def test_vale_entidad_fuera_de_rango_y_serie_agotada(cliente):
    escenario = await _escenario(
        cliente, serie_desde=1, serie_hasta=2, presupuesto="2000.00"
    )
    orden = escenario["orden"]
    combustible = escenario["combustible"]

    # Serie vacía: cualquier número fuera del rango se rechaza.
    fuera = await _registrar_entidad(cliente, orden["id"], combustible["id"], "3")
    assert fuera.status_code == 422
    cuerpo = fuera.json()
    assert cuerpo["codigo"] == "NUMERO_FUERA_DE_SERIE"
    assert cuerpo["detalles"]["serie_desde"] == 1
    assert cuerpo["detalles"]["serie_hasta"] == 2

    # Se agotan los dos números del rango.
    primero = await _registrar_entidad(cliente, orden["id"], combustible["id"], "1")
    assert primero.status_code == 201, primero.text
    segundo = await _registrar_entidad(cliente, orden["id"], combustible["id"], "2")
    assert segundo.status_code == 201, segundo.text
    # Ya no queda ningún número del rango (SERIE_AGOTADA antes del chequeo del
    # rango: el plan lo pide con este código y con estado HTTP 409).
    agotado = await _registrar_entidad(cliente, orden["id"], combustible["id"], "3")
    assert agotado.status_code == 409
    assert agotado.json()["codigo"] == "SERIE_AGOTADA"
    duplicado = await _registrar_entidad(cliente, orden["id"], combustible["id"], "2")
    assert duplicado.status_code == 409
    assert duplicado.json()["codigo"] == "NUMERO_ENTIDAD_DUPLICADO"


# ---------------------------------------------------------------------------
# Consultas: buscar (QRY-01), listado (VAL-06), detalle (VAL-07/VAL-08)
# ---------------------------------------------------------------------------


async def test_busqueda_con_varias_coincidencias(cliente):
    escenario = await _escenario(cliente)
    orden = escenario["orden"]
    combustible = escenario["combustible"]
    await _registrar_entidad(cliente, orden["id"], combustible["id"], "PO-9")
    otra = await _orden(cliente, escenario["institucion"], estado="vigente")
    await _registrar_entidad(cliente, otra["id"], combustible["id"], "PO-9")

    candidatos = (await cliente.get("/api/v1/vales/buscar", params={"q": "PO-9"})).json()
    assert len(candidatos) == 2
    assert {c["orden_id"] for c in candidatos} == {orden["id"], otra["id"]}
    for candidato in candidatos:
        assert candidato["razon_social"] == escenario["institucion"]["nombre"]
        assert candidato["estado"] == "activo"
        assert candidato["saldo"] == "20.00"
        assert candidato["combustible_nombre"] == "Gasohol 90"

    # El código interno de la estación también se busca.
    emitido = await _emitir(cliente, orden["id"], combustible["id"], cantidades=["10.00"])
    codigo = emitido.json()[0]["numero_estacion"]
    solos = (await cliente.get("/api/v1/vales/buscar", params={"q": codigo})).json()
    assert len(solos) == 1
    assert solos[0]["numero_estacion"] == codigo
    assert solos[0]["numero_entidad"] is None

    sin_nada = await cliente.get("/api/v1/vales/buscar", params={"q": "INEXISTENTE"})
    assert sin_nada.json() == []


async def test_listado_filtros_y_paginacion(cliente):
    escenario = await _escenario(cliente)
    orden = escenario["orden"]
    combustible = escenario["combustible"]
    await _emitir(cliente, orden["id"], combustible["id"], cantidades=["10.00", "10.00"])
    await _registrar_entidad(cliente, orden["id"], combustible["id"], "PO-1")

    bruto = (await cliente.get("/api/v1/vales")).json()
    assert bruto["total"] == 3
    assert [v["consumido"] for v in bruto["items"]] == ["0.00", "0.00", "0.00"]

    por_emisor = (
        await cliente.get("/api/v1/vales", params={"emisor": "entidad"})
    ).json()
    assert por_emisor["total"] == 1
    assert por_emisor["items"][0]["numero_entidad"] == "PO-1"

    por_orden = (
        await cliente.get("/api/v1/vales", params={"orden_id": orden["id"]})
    ).json()
    assert por_orden["total"] == 3

    paginados = (
        await cliente.get("/api/v1/vales", params={"pagina": 2, "por_pagina": 2})
    ).json()
    assert paginados["pagina"] == 2 and paginados["por_pagina"] == 2
    assert len(paginados["items"]) == 1


async def test_detalle_vencido_se_reconoce_al_consultar(cliente):
    """VAL-08/RN-07: el vencimiento leído manda aunque el proceso no corra."""
    escenario = await _escenario(cliente)
    orden = escenario["orden"]
    combustible = escenario["combustible"]
    emitidos = await _emitir(cliente, orden["id"], combustible["id"])
    id_vale = int(emitidos.json()[0]["id"])

    ajustes = obtener_settings()
    conexion = await asyncpg.connect(a_dsn(ajustes.database_url))
    try:
        await conexion.execute(
            # El CHECK exige vencimiento >= emision: muevo ambas fechas.
            "UPDATE vales SET fecha_emision = CURRENT_DATE - 2,"
            " fecha_vencimiento = CURRENT_DATE - 1 WHERE id = $1",
            id_vale,
        )
    finally:
        await conexion.close()

    ficha = (await cliente.get(f"/api/v1/vales/{id_vale}")).json()
    assert ficha["estado"] == "vencido"
    assert ficha["consumido"] == "0.00"
    assert ficha["saldo"] == "10.00"
    assert ficha["institucion"] == escenario["institucion"]["nombre"]

    # El listado con el filtro de estado también lo refleja.
    listado = (await cliente.get("/api/v1/vales", params={"estado": "vencido"})).json()
    assert listado["total"] == 1
    extraido = (await cliente.get(f"/api/v1/vales/{id_vale + 99}"))
    assert extraido.status_code == 404
    assert extraido.json()["codigo"] == "VALE_NO_ENCONTRADO"


async def test_movimientos_de_la_emision(cliente):
    """CON-12: la emisión queda en la línea de tiempo con el saldo posterior."""
    escenario = await _escenario(cliente)
    orden = escenario["orden"]
    combustible = escenario["combustible"]
    emitidos = await _emitir(cliente, orden["id"], combustible["id"])
    id_vale = int(emitidos.json()[0]["id"])

    historia = (await cliente.get(f"/api/v1/vales/{id_vale}/movimientos")).json()
    assert len(historia) == 1
    movimiento = historia[0]
    assert movimiento["tipo"] == "emision"
    assert movimiento["variacion"] == "10.00"
    assert movimiento["saldo_posterior"] == "10.00"
    assert movimiento["importe_soles"] == "155.00"
    assert movimiento["usuario"] is not None
    assert movimiento["fecha_local"] is not None


# ---------------------------------------------------------------------------
# Alertas (VAL-13): umbral 10% y 7 días por defecto (migración 0001)
# ---------------------------------------------------------------------------


async def test_alertas_saldo_bajo_y_por_vencer(cliente):
    escenario = await _escenario(cliente)
    orden = escenario["orden"]
    combustible = escenario["combustible"]
    emitidos = await _emitir(
        cliente, orden["id"], combustible["id"], cantidades=["100.00"]
    )
    id_vale = int(emitidos.json()[0]["id"])

    ajustes = obtener_settings()
    conexion = await asyncpg.connect(a_dsn(ajustes.database_url))
    try:
        await conexion.execute(
            "UPDATE vales SET saldo = 5.00, fecha_vencimiento = CURRENT_DATE + 2"
            " WHERE id = $1",
            id_vale,
        )
    finally:
        await conexion.close()

    franja = (await cliente.get("/api/v1/vales/alertas")).json()
    assert [int(v["id"]) for v in franja["saldo_bajo"]] == [id_vale]  # 5% ≤ 10%
    assert [int(v["id"]) for v in franja["por_vencer"]] == [id_vale]
    assert franja["por_vencer"][0]["dias_para_vencer"] == 2


# ---------------------------------------------------------------------------
# Impresión (VAL-12)
# ---------------------------------------------------------------------------


async def test_impresion_registra_y_marca_duplicado(cliente):
    escenario = await _escenario(cliente)
    orden = escenario["orden"]
    combustible = escenario["combustible"]
    emitidos = await _emitir(cliente, orden["id"], combustible["id"])
    id_vale = int(emitidos.json()[0]["id"])
    numero = emitidos.json()[0]["numero_estacion"]

    primera = await cliente.post(f"/api/v1/vales/{id_vale}/impresion")
    assert primera.status_code in (200, 201), primera.text
    assert primera.json()["es_duplicado"] is False
    assert primera.json()["numero_estacion"] == numero

    segunda = await cliente.post(f"/api/v1/vales/{id_vale}/impresion")
    assert segunda.status_code in (200, 201), segunda.text
    cuerpo = segunda.json()
    assert cuerpo["es_duplicado"] is True
    assert cuerpo["veces_impreso"] == 2

    ficha = (await cliente.get(f"/api/v1/vales/{id_vale}")).json()
    assert ficha["veces_impreso"] == 2


# ---------------------------------------------------------------------------
# Emisión simultánea de dos usuarios sobre la misma orden (VAL-04, RN-03)
# ---------------------------------------------------------------------------


async def test_emision_simultanea_no_excede_presupuesto(cliente):
    escenario = await _escenario(cliente, presupuesto="1000.00")
    orden = escenario["orden"]
    combustible = escenario["combustible"]

    cuerpo = {"combustible_id": combustible["id"], "cantidades": ["40.00"]}
    # 40 x 15.50 = 620.00 por emisión: 1240.00 > 1000.00, así que solo una
    # puede pasar bajo el bloqueo de la orden (RN-03).
    async with _cliente_con_rol(cliente, "valpar@pruebas.pe", "oficina") as paralelo:
        resultado = await asyncio.gather(
            cliente.post(f"/api/v1/ordenes/{orden['id']}/vales", json=cuerpo),
            paralelo.post(f"/api/v1/ordenes/{orden['id']}/vales", json=cuerpo),
        )

    estados = {r.status_code for r in resultado}
    assert 201 in estados and 409 in estados, [
        (r.status_code, r.text[:200]) for r in resultado
    ]
    # En la base solo queda la emisión aceptada; su valor no excede el techo.
    listado = (await cliente.get("/api/v1/vales")).json()
    total_soles = sum(float(v["valor_soles"]) for v in listado["items"])
    assert total_soles <= 1000.00
    assert listado["total"] == 1
    # Y la simulación siguiente ve exactamente ese compromiso (restante).
    restante = await cliente.post(
        f"/api/v1/ordenes/{orden['id']}/vales/simulacion",
        json={"combustible_id": combustible["id"], "cantidades": ["40.00"]},
    )
    assert restante.status_code == 409  # 620 + 620 > 1000: ya no cabe otro.
    assert (
        restante.json()["detalles"]["presupuesto_restante_soles"]
        == formato_restante(1000.00 - total_soles)
    )


def formato_restante(valor: float) -> str:
    return f"{valor:.2f}"
