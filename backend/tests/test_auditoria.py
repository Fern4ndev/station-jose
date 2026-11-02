"""Pruebas de Fase 8: bitácora e historial (AUD-03, AUD-04).

Cubre: acceso solo con permiso, filtros por usuario, acción, entidad y rango
de fechas, paginación descendente, historial de un vale (emisión y consumo),
de una orden, de una institución y de un usuario, y rechazo de una entidad
fuera del catálogo del plan.
"""

from datetime import timedelta

from app.core import tiempo
from tests.test_consumos import _vender
from tests.test_vales import _emitir, _escenario, _usuario_de_rol

_AYER = (tiempo.hoy() - timedelta(days=1)).isoformat()
_HOY = tiempo.hoy().isoformat()


async def _escenario_con_vale(cliente) -> dict:
    """Estación, combustible, institución, orden y un vale de 100 con consumo."""
    datos = await _escenario(cliente)
    emision = await _emitir(
        cliente, datos["orden"]["id"], datos["combustible"]["id"], cantidades=["100.00"]
    )
    assert emision.status_code == 201, emision.text
    vale = emision.json()[0]
    await _vender(cliente, vale["id"], "30.00")
    return {**datos, "vale": vale}


async def _bitacora(cliente, **parametros) -> dict:
    respuesta = await cliente.get("/api/v1/auditoria/bitacora", params=parametros)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


# ---------------------------------------------------------------------------
# Acceso (AUD-03/AUD-04)
# ---------------------------------------------------------------------------


async def test_bitacora_solo_administrador_y_historial_tambien_oficina(cliente):
    """AUD-03 es del administrador; AUD-04 lo comparten admin y oficina."""
    datos = await _escenario_con_vale(cliente)
    vale_id = datos["vale"]["id"]

    await _usuario_de_rol(cliente, "oficina.bitacora@pruebas.pe", "oficina")
    assert (await cliente.get("/api/v1/auditoria/bitacora")).status_code == 403
    assert (
        await cliente.get(f"/api/v1/auditoria/historial/vale/{vale_id}")
    ).status_code == 200

    await _usuario_de_rol(cliente, "despacho.bitacora@pruebas.pe", "despachador")
    assert (await cliente.get("/api/v1/auditoria/bitacora")).status_code == 403
    assert (
        await cliente.get(f"/api/v1/auditoria/historial/vale/{vale_id}")
    ).status_code == 403


# ---------------------------------------------------------------------------
# Filtros y paginación (AUD-03)
# ---------------------------------------------------------------------------


async def test_bitacora_filtra_por_accion_y_entidad(cliente):
    """AUD-03: la acción deja usuario, entidad y valores del cambio."""
    datos = await _escenario_con_vale(cliente)

    creadas = await _bitacora(cliente, accion="institucion_creada")
    assert creadas["total"] == 1
    fila = creadas["items"][0]
    assert fila["entidad"] == "instituciones"
    assert fila["entidad_id"] == str(datos["institucion"]["id"])
    assert fila["usuario"] == "Usuario de Prueba"
    assert fila["antes"] is None
    assert fila["despues"]["nombre"] == datos["institucion"]["nombre"]
    assert fila["ip"] in {"127.0.0.1", "::1"}  # inet serializada como texto

    vales = await _bitacora(cliente, entidad="vales")
    acciones = [item["accion"] for item in vales["items"]]
    assert "vale_emitido" in acciones
    assert "consumo_registrado" in acciones
    assert all(item["entidad"] == "vales" for item in vales["items"])


async def test_bitacora_filtra_por_usuario(cliente):
    """AUD-03: el filtro por usuario acota la huella a un operador."""
    datos = await _escenario_con_vale(cliente)
    yo = (await cliente.get("/api/v1/auth/yo")).json()
    usuario_id = int(yo["usuario"]["id"])

    propias = await _bitacora(cliente, usuario_id=usuario_id)
    assert propias["total"] > 0
    assert all(item["app_user_id"] == usuario_id for item in propias["items"])

    ajenas = await _bitacora(cliente, usuario_id=usuario_id + 500)
    assert ajenas["total"] == 0
    assert datos["vale"]["id"]


async def test_bitacora_pagina_en_descendente(cliente):
    """AUD-03: páginas sin solapes y de la acción más reciente a la más vieja."""
    await _escenario_con_vale(cliente)

    primera = await _bitacora(cliente, pagina=1, por_pagina=2)
    segunda = await _bitacora(cliente, pagina=2, por_pagina=2)
    assert primera["total"] == segunda["total"] >= 6
    assert len(primera["items"]) == 2
    assert len(segunda["items"]) == 2

    ids = [item["id"] for item in primera["items"] + segunda["items"]]
    assert ids == sorted(ids, reverse=True)
    assert len(set(ids)) == 4


async def test_bitacora_rango_de_fechas(cliente):
    """AUD-03: `desde`/`hasta` acotan por día y el rango invertido es 422."""
    await _escenario_con_vale(cliente)

    total = (await _bitacora(cliente))["total"]
    de_hoy = await _bitacora(cliente, desde=_HOY, hasta=_HOY)
    assert de_hoy["total"] == total  # todo se registró hoy

    de_ayer = await _bitacora(cliente, hasta=_AYER)
    assert de_ayer["total"] == 0

    invertido = await cliente.get(
        "/api/v1/auditoria/bitacora", params={"desde": _HOY, "hasta": _AYER}
    )
    assert invertido.status_code == 422
    assert invertido.json()["codigo"] == "VALIDACION_INVALIDA"


# ---------------------------------------------------------------------------
# Historial por registro (AUD-04)
# ---------------------------------------------------------------------------


async def test_historial_del_vale_trae_emision_y_consumo(cliente):
    """AUD-04: el vale arranca su historial en la emisión."""
    datos = await _escenario_con_vale(cliente)
    vale_id = datos["vale"]["id"]

    respuesta = await cliente.get(f"/api/v1/auditoria/historial/vale/{vale_id}")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["entidad"] == "vale"
    assert cuerpo["entidad_id"] == vale_id

    acciones = [item["accion"] for item in cuerpo["items"]]
    assert acciones[0] == "consumo_registrado"  # lo más reciente primero
    assert "vale_emitido" in acciones
    emision = next(item for item in cuerpo["items"] if item["accion"] == "vale_emitido")
    assert emision["despues"]["numero_estacion"] == datos["vale"]["numero_estacion"]
    assert emision["despues"]["cantidad_inicial"] == "100.00"


async def test_historial_de_orden_institucion_y_usuario(cliente):
    """AUD-04: órdenes, instituciones y usuarios también tienen su línea."""
    datos = await _escenario_con_vale(cliente)

    orden = (
        await cliente.get(
            f"/api/v1/auditoria/historial/orden/{datos['orden']['id']}"
        )
    ).json()
    assert [item["accion"] for item in orden["items"]][-1] == "orden_creada"

    institucion = (
        await cliente.get(
            f"/api/v1/auditoria/historial/institucion/{datos['institucion']['id']}"
        )
    ).json()
    assert "institucion_creada" in [item["accion"] for item in institucion["items"]]

    yo = (await cliente.get("/api/v1/auth/yo")).json()
    usuario = (
        await cliente.get(
            f"/api/v1/auditoria/historial/usuario/{yo['usuario']['id']}"
        )
    ).json()
    assert "iniciar_sesion" in [item["accion"] for item in usuario["items"]]


async def test_historial_rechaza_entidad_fuera_del_catalogo(cliente):
    """AUD-04: solo las cinco entidades del plan tienen historial."""
    await _escenario(cliente)
    respuesta = await cliente.get("/api/v1/auditoria/historial/factura/1")
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "VALIDACION_INVALIDA"
