"""Pruebas de Fase 7: consumos y correcciones (CON-01..14, VAL-08..11, P-03/06/09/13).

Cubre: consumo parcial exacto, saldo insuficiente, vale agotado, anulado y
vencido (reconocido por fecha), combustible distinto (P-03), importe en
soles con su cuadre de galones, datos complementarios opcionales (P-06),
registro retroactivo solo para el administrador con motivo (P-09), reenvío
con el mismo `token_operacion` que no duplica (CON-08), reversión y doble
reversión (CON-11), no revertir consumos de un vale anulado (P-13),
ajustes que no dejan saldo negativo ni sobre la cantidad inicial (VAL-11),
anulación del vale con compromiso igual a lo consumido (VAL-10/P-13),
anulación de orden con y sin consumos (ORD-09/RN-17), historial ordenado
(CON-12), comprobante (CON-10), permisos por rol y consumos simultáneos
que nunca exceden el saldo (RN-05).
"""

import asyncio
import uuid
from datetime import timedelta

from httpx import AsyncClient

from app.core import tiempo
from tests.test_vales import (
    _cliente_con_rol,
    _combustible,
    _emitir,
    _escenario,
    _orden,
    _parchear_vale,
)

_AYER = (tiempo.hoy() - timedelta(days=1)).isoformat()
_MAÑANA = (tiempo.hoy() + timedelta(days=1)).isoformat()


def _token() -> str:
    return str(uuid.uuid4())


async def _vale_de_100(cliente: AsyncClient, **ajustes) -> dict:
    """Escenario con un vale de estación de 100 galones, listo para despachar."""
    escenario = await _escenario(cliente, **ajustes)
    orden = escenario["orden"]
    combustible = escenario["combustible"]
    emision = await _emitir(
        cliente, orden["id"], combustible["id"], cantidades=["100.00"]
    )
    assert emision.status_code == 201, emision.text
    return {**escenario, "vale": emision.json()[0]}


async def _vender(cliente: AsyncClient, vale_id: int, cantidad: str = "30.00") -> dict:
    """Despacha `cantidad` de galones y devuelve el movimiento 201."""
    respuesta = await cliente.post(
        f"/api/v1/vales/{vale_id}/consumos",
        json={"token_operacion": _token(), "cantidad_galones": cantidad},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# ---------------------------------------------------------------------------
# Despacho nominal (CON-01, CON-05, CON-06)
# ---------------------------------------------------------------------------


async def test_consumo_parcial_deja_saldo_exacto(cliente):
    """CON-01: 100 menos 30 es 70 y el importe cuadra con el precio del vale."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]

    respuesta = await cliente.post(
        f"/api/v1/vales/{vale['id']}/consumos",
        json={"token_operacion": _token(), "cantidad_galones": "30.00"},
    )
    assert respuesta.status_code == 201, respuesta.text
    movimiento = respuesta.json()
    assert movimiento["tipo"] == "consumo"
    assert movimiento["variacion"] == "-30.00"
    assert movimiento["saldo_posterior"] == "70.00"
    assert movimiento["importe_soles"] == "465.00"  # 30 x 15.50
    assert movimiento["fecha_local"] == tiempo.hoy().isoformat()

    detalle = (await cliente.get(f"/api/v1/vales/{vale['id']}")).json()
    assert detalle["saldo"] == "70.00"
    assert detalle["consumido"] == "30.00"
    assert detalle["estado"] == "activo"
    assert detalle["valor_soles"] == "1550.00"  # el precio del vale no cambia


async def test_ambas_cantidades_rechazadas(cliente):
    """CON-05: galones e importe a la vez no pasa la validación."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]

    respuesta = await cliente.post(
        f"/api/v1/vales/{vale['id']}/consumos",
        json={
            "token_operacion": _token(),
            "cantidad_galones": "10.00",
            "importe_soles": "155.00",
        },
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "VALIDACION_INVALIDA"


async def test_importe_soles_deriva_galones(cliente):
    """CON-05: el importe manda y los galones se derivan con el precio del vale."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]

    respuesta = await cliente.post(
        f"/api/v1/vales/{vale['id']}/consumos",
        json={"token_operacion": _token(), "importe_soles": "465.00"},
    )
    assert respuesta.status_code == 201, respuesta.text
    movimiento = respuesta.json()
    assert movimiento["cantidad_galones"] == "30.00"
    assert movimiento["importe_soles"] == "465.00"
    assert movimiento["saldo_posterior"] == "70.00"


async def test_importe_menor_que_un_galon_rechazado(cliente):
    """Un importe que redondeó a cero galones no despacha nada."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]

    respuesta = await cliente.post(
        f"/api/v1/vales/{vale['id']}/consumos",
        json={"token_operacion": _token(), "importe_soles": "0.05"},
    )
    assert respuesta.status_code == 422, respuesta.text
    assert "importe_soles" in respuesta.json()["detalles"]


# ---------------------------------------------------------------------------
# Estados que impiden el despacho (CON-04, P-03)
# ---------------------------------------------------------------------------


async def test_saldo_insuficiente_rechazado_con_saldo(cliente):
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]

    await _vender(cliente, vale["id"])
    respuesta = await cliente.post(
        f"/api/v1/vales/{vale['id']}/consumos",
        json={"token_operacion": _token(), "cantidad_galones": "80.00"},
    )
    assert respuesta.status_code == 409, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "SALDO_INSUFICIENTE"
    assert cuerpo["detalles"]["saldo"] == "70.00"

    detalle = (await cliente.get(f"/api/v1/vales/{vale['id']}")).json()
    assert detalle["saldo"] == "70.00"  # el rechazo no movió el saldo


async def test_vale_agotado_rechazado(cliente):
    datos = await _vale_de_100(cliente, combustible_nombre="Diésel B5")
    vale = datos["vale"]

    await _vender(cliente, vale["id"], cantidad="100.00")
    detalle = (await cliente.get(f"/api/v1/vales/{vale['id']}")).json()
    assert detalle["estado"] == "agotado"

    respuesta = await cliente.post(
        f"/api/v1/vales/{vale['id']}/consumos",
        json={"token_operacion": _token(), "cantidad_galones": "1.00"},
    )
    assert respuesta.status_code == 409, respuesta.text
    assert respuesta.json()["codigo"] == "VALE_AGOTADO"


async def test_vale_anulado_rechazado(cliente):
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]

    anulacion = await cliente.post(
        f"/api/v1/vales/{vale['id']}/anular", json={"motivo": "Vale mal emitido"}
    )
    assert anulacion.status_code == 200, anulacion.text

    respuesta = await cliente.post(
        f"/api/v1/vales/{vale['id']}/consumos",
        json={"token_operacion": _token(), "cantidad_galones": "10.00"},
    )
    assert respuesta.status_code == 409, respuesta.text
    assert respuesta.json()["codigo"] == "VALE_ANULADO"


async def test_vale_vencido_por_fecha_y_proceso_de_vencimientos(cliente):
    """VAL-08/VAL-09: la fecha vence el vale aunque el proceso diario no pase."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]

    # La fecha de hoy es límite (cualquier lectura/en uso deja pasarlo).
    await _parchear_vale(vale["id"], {"fecha_vencimiento": tiempo.hoy().isoformat()})
    aceptado = await cliente.post(
        f"/api/v1/vales/{vale['id']}/consumos",
        json={"token_operacion": _token(), "cantidad_galones": "10.00"},
    )
    assert aceptado.status_code == 201, aceptado.text

    # El CHECK exige vencimiento >= emision: muevo ambas fechas al pasado.
    await _parchear_vale(
        vale["id"], {"fecha_emision": _AYER, "fecha_vencimiento": _AYER}
    )
    tarde = await cliente.post(
        f"/api/v1/vales/{vale['id']}/consumos",
        json={"token_operacion": _token(), "cantidad_galones": "10.00"},
    )
    assert tarde.status_code == 409, tarde.text
    assert tarde.json()["codigo"] == "VALE_VENCIDO"

    proceso = await cliente.post("/api/v1/vales/vencimientos/procesar")
    assert proceso.status_code == 200, proceso.text
    assert proceso.json()["vencidos"] == 1
    detalle = (await cliente.get(f"/api/v1/vales/{vale['id']}")).json()
    assert detalle["estado"] == "vencido"


async def test_combustible_distinto_rechazado(cliente):
    """P-03: el combustible del despacho debe ser el del vale."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]
    otro = await _combustible(cliente, nombre="Gasohol 95", precio=None)

    respuesta = await cliente.post(
        f"/api/v1/vales/{vale['id']}/consumos",
        json={
            "token_operacion": _token(),
            "cantidad_galones": "10.00",
            "combustible_id": otro["id"],
        },
    )
    assert respuesta.status_code == 409, respuesta.text
    assert respuesta.json()["codigo"] == "CONSUMO_COMBUSTIBLE_DISTINTO"


# ---------------------------------------------------------------------------
# Token de operación y reenvío (CON-08)
# ---------------------------------------------------------------------------


async def test_token_repetido_devuelve_el_movimiento_original(cliente):
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]
    token = _token()

    primera = await cliente.post(
        f"/api/v1/vales/{vale['id']}/consumos",
        json={"token_operacion": token, "cantidad_galones": "10.00"},
    )
    assert primera.status_code == 201, primera.text
    original = primera.json()

    reenvio = await cliente.post(
        f"/api/v1/vales/{vale['id']}/consumos",
        json={"token_operacion": token, "cantidad_galones": "25.00"},
    )
    assert reenvio.status_code == 201, reenvio.text
    repetido = reenvio.json()
    assert repetido["id"] == original["id"]
    assert repetido["saldo_posterior"] == original["saldo_posterior"] == "90.00"
    assert repetido["cantidad_galones"] == "10.00"  # ni 25 ni doble

    historia = (await cliente.get(f"/api/v1/vales/{vale['id']}/movimientos")).json()
    assert [m["tipo"] for m in historia] == ["emision", "consumo"]
    detalle = (await cliente.get(f"/api/v1/vales/{vale['id']}")).json()
    assert detalle["saldo"] == "90.00"


# ---------------------------------------------------------------------------
# Datos complementarios y registro retroactivo (P-06, P-09)
# ---------------------------------------------------------------------------


async def test_datos_complementarios_opcionales_se_registran(cliente):
    """P-06: placa, conductor y observación viajan al movimiento."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]

    respuesta = await cliente.post(
        f"/api/v1/vales/{vale['id']}/consumos",
        json={
            "token_operacion": _token(),
            "cantidad_galones": "10.00",
            "placa": "ABC-123",
            "conductor": "Julio Prado",
            "observacion": "Carga del camión n° 2",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    movimiento = respuesta.json()
    assert movimiento["placa"] == "ABC-123"
    assert movimiento["conductor"] == "Julio Prado"
    assert movimiento["motivo"] == "Carga del camión n° 2"

    listado = (await cliente.get(f"/api/v1/vales/{vale['id']}/consumos")).json()
    assert len(listado) == 1
    assert listado[0]["placa"] == "ABC-123"
    assert listado[0]["conductor"] == "Julio Prado"


async def test_retroactivo_solo_administrador_y_con_motivo(cliente):
    """P-09: oficina y despachador no retroactúan; para el admin es con motivo."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]
    cuerpo_retro = {"token_operacion": _token(), "cantidad_galones": "5.00", "fecha_local": _AYER}

    async with _cliente_con_rol(cliente, "conofi@pruebas.pe", "oficina") as paralelo:
        rechazado = await paralelo.post(
            f"/api/v1/vales/{vale['id']}/consumos", json=cuerpo_retro
        )
    assert rechazado.status_code == 403, rechazado.text
    assert rechazado.json()["codigo"] == "SIN_PERMISO"

    async with _cliente_con_rol(cliente, "condes@pruebas.pe", "despachador") as paralelo:
        rechazado = await paralelo.post(
            f"/api/v1/vales/{vale['id']}/consumos", json=cuerpo_retro
        )
    assert rechazado.status_code == 403, rechazado.text

    # El administrador exige motivo cuando manda fecha retroactiva.
    faltante = await cliente.post(
        f"/api/v1/vales/{vale['id']}/consumos",
        json={"token_operacion": _token(), "cantidad_galones": "5.00", "fecha_local": _AYER},
    )
    assert faltante.status_code == 422, faltante.text
    assert "motivo" in faltante.json()["detalles"]

    # La fecha futura no inventa hechos.
    futuro = await cliente.post(
        f"/api/v1/vales/{vale['id']}/consumos",
        json={
            "token_operacion": _token(),
            "cantidad_galones": "5.00",
            "fecha_local": _MAÑANA,
            "motivo": "No operativo",
        },
    )
    assert futuro.status_code == 422, futuro.text
    assert "fecha_local" in futuro.json()["detalles"]

    aceptado = await cliente.post(
        f"/api/v1/vales/{vale['id']}/consumos",
        json={
            "token_operacion": _token(),
            "cantidad_galones": "5.00",
            "fecha_local": _AYER,
            "motivo": "Registro tardío del camión n° 1",
        },
    )
    assert aceptado.status_code == 201, aceptado.text
    assert aceptado.json()["fecha_local"] == _AYER


# ---------------------------------------------------------------------------
# Reversión (CON-11)
# ---------------------------------------------------------------------------


async def test_reversion_una_sola_vez(cliente):
    """CON-11: reversión con motivo; la doble reversión es 409."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]
    consumo = await _vender(cliente, vale["id"])

    reversion = await cliente.post(
        f"/api/v1/consumos/{consumo['id']}/revertir",
        json={"motivo": "Despacho grabado dos veces por error de caja"},
    )
    assert reversion.status_code == 200, reversion.text
    datos_reversion = reversion.json()
    assert datos_reversion["tipo"] == "reversion"
    assert datos_reversion["variacion"] == "30.00"
    assert datos_reversion["saldo_posterior"] == "100.00"
    assert datos_reversion["movimiento_origen_id"] == consumo["id"]

    detalle = (await cliente.get(f"/api/v1/vales/{vale['id']}")).json()
    assert detalle["saldo"] == "100.00"
    assert detalle["estado"] == "activo"

    doble = await cliente.post(
        f"/api/v1/consumos/{consumo['id']}/revertir",
        json={"motivo": "Intento duplicado"},
    )
    assert doble.status_code == 409, doble.text
    assert doble.json()["codigo"] == "CONSUMO_YA_REVERTIDO"

    reversar_reversion = await cliente.post(
        f"/api/v1/consumos/{datos_reversion['id']}/revertir",
        json={"motivo": "No se revierte una reversión"},
    )
    assert reversar_reversion.status_code == 409, reversar_reversion.text
    assert reversar_reversion.json()["codigo"] == "CONSUMO_NO_REVERTIBLE"

    vacio = await cliente.post(
        f"/api/v1/consumos/{consumo['id']}/revertir", json={"motivo": "  "}
    )
    assert vacio.status_code == 422, vacio.text


async def test_reversion_de_vale_anulado_bloqueada(cliente):
    """P-13: lo consumido de un vale anulado queda fijo."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]
    consumo = await _vender(cliente, vale["id"])

    anulacion = await cliente.post(
        f"/api/v1/vales/{vale['id']}/anular", json={"motivo": "Orden corregida"}
    )
    assert anulacion.status_code == 200, anulacion.text

    reversion = await cliente.post(
        f"/api/v1/consumos/{consumo['id']}/revertir",
        json={"motivo": "Apareció la carga real"},
    )
    assert reversion.status_code == 409, reversion.text
    assert reversion.json()["codigo"] == "CONSUMO_VALE_ANULADO"


async def test_reversion_no_reactiva_sobre_la_cantidad_inicial(cliente):
    """El saldo nunca pasa de la cantidad inicial del vale."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]
    consumo = await _vender(cliente, vale["id"], cantidad="60.00")

    ajuste = await cliente.post(
        f"/api/v1/vales/{vale['id']}/ajustes",
        json={"variacion": "40.00", "motivo": "Reconciliación de tanque"},
    )
    assert ajuste.status_code == 200, ajuste.text
    assert ajuste.json()["saldo"] == "80.00"

    reversion = await cliente.post(
        f"/api/v1/consumos/{consumo['id']}/revertir",
        json={"motivo": "Carga no ocurrió"},
    )
    assert reversion.status_code == 409, reversion.text
    assert reversion.json()["codigo"] == "REVERSION_INCOMPATIBLE"


# ---------------------------------------------------------------------------
# Permisos (sección 4.1)
# ---------------------------------------------------------------------------


async def test_despachador_registra_pero_no_lee_ni_revierte(cliente):
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]

    async with _cliente_con_rol(
        cliente, "condes2@pruebas.pe", "despachador"
    ) as paralelo:
        despacho = await paralelo.post(
            f"/api/v1/vales/{vale['id']}/consumos",
            json={"token_operacion": _token(), "cantidad_galones": "10.00"},
        )
        assert despacho.status_code == 201, despacho.text
        movimiento_id = despacho.json()["id"]

        lectura = await paralelo.get(f"/api/v1/vales/{vale['id']}/movimientos")
        assert lectura.status_code == 403
        assert lectura.json()["codigo"] == "SIN_PERMISO"
        ficha = await paralelo.get(f"/api/v1/vales/{vale['id']}")
        assert ficha.status_code == 403

        reversion = await paralelo.post(
            f"/api/v1/consumos/{movimiento_id}/revertir",
            json={"motivo": "Ni despachador ni oficina revisan"},
        )
        assert reversion.status_code == 403, reversion.text

    async with _cliente_con_rol(cliente, "conofi2@pruebas.pe", "oficina") as paralelo:
        reversion_oficina = await paralelo.post(
            f"/api/v1/consumos/{movimiento_id}/revertir",
            json={"motivo": "Oficina tampoco revierte"},
        )
        assert reversion_oficina.status_code == 403, reversion_oficina.text

    # El administrador sí revierte.
    autorizada = await cliente.post(
        f"/api/v1/consumos/{movimiento_id}/revertir",
        json={"motivo": "Revisado por taller"},
    )
    assert autorizada.status_code == 200, autorizada.text


async def test_comprobante_con_datos_del_vale(cliente):
    """CON-10: el comprobante reúne vale, orden, institución y estación."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]
    consumo = await _vender(cliente, vale["id"])

    respuesta = await cliente.get(f"/api/v1/consumos/{consumo['id']}/comprobante")
    assert respuesta.status_code == 200, respuesta.text
    ficha = respuesta.json()
    assert ficha["movimiento_id"] == consumo["id"]
    assert ficha["numero_estacion"] == vale["numero_estacion"]
    assert ficha["combustible"] == datos["combustible"]["nombre"]
    assert ficha["institucion"] == datos["institucion"]["nombre"]
    assert ficha["cantidad_galones"] == "30.00"
    assert ficha["importe_soles"] == "465.00"
    assert ficha["saldo_posterior"] == "70.00"
    assert ficha["saldo_vale"] == "70.00"
    assert ficha["usuario"]


# ---------------------------------------------------------------------------
# Ajustes (VAL-11/RN-09)
# ---------------------------------------------------------------------------


async def test_ajustes_con_signo_y_limites(cliente):
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]

    sin_motivo = await cliente.post(
        f"/api/v1/vales/{vale['id']}/ajustes",
        json={"variacion": "5.00", "motivo": "  "},
    )
    assert sin_motivo.status_code == 422, sin_motivo.text

    cero = await cliente.post(
        f"/api/v1/vales/{vale['id']}/ajustes",
        json={"variacion": "0.00", "motivo": "Sin cambios"},
    )
    assert cero.status_code == 422, cero.text

    resta = await cliente.post(
        f"/api/v1/vales/{vale['id']}/ajustes",
        json={"variacion": "-10.00", "motivo": "Corrección de medición"},
    )
    assert resta.status_code == 200, resta.text
    assert resta.json()["saldo"] == "90.00"
    assert resta.json()["estado"] == "activo"

    suma = await cliente.post(
        f"/api/v1/vales/{vale['id']}/ajustes",
        json={"variacion": "5.00", "motivo": "Carga anterior pendiente"},
    )
    assert suma.status_code == 200, suma.text
    assert suma.json()["saldo"] == "95.00"

    negativo = await cliente.post(
        f"/api/v1/vales/{vale['id']}/ajustes",
        json={"variacion": "-200.00", "motivo": "Demasiado"},
    )
    assert negativo.status_code == 409, negativo.text
    assert negativo.json()["codigo"] == "AJUSTE_NEGATIVO"

    exceso = await cliente.post(
        f"/api/v1/vales/{vale['id']}/ajustes",
        json={"variacion": "10.00", "motivo": "Sobre la cantidad inicial"},
    )
    assert exceso.status_code == 409, exceso.text
    assert exceso.json()["codigo"] == "AJUSTE_EXCEDIDO"


async def test_ajuste_despierta_vale_agotado_y_no_toca_anulado(cliente):
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]

    await _vender(cliente, vale["id"], cantidad="100.00")
    detalle = (await cliente.get(f"/api/v1/vales/{vale['id']}")).json()
    assert detalle["estado"] == "agotado"

    despertado = await cliente.post(
        f"/api/v1/vales/{vale['id']}/ajustes",
        json={"variacion": "15.00", "motivo": "Galones reaparecidos en tanque"},
    )
    assert despertado.status_code == 200, despertado.text
    assert despertado.json()["saldo"] == "15.00"
    assert despertado.json()["estado"] == "activo"
    detalle = (await cliente.get(f"/api/v1/vales/{vale['id']}")).json()
    assert detalle["estado"] == "activo"

    anulacion = await cliente.post(
        f"/api/v1/vales/{vale['id']}/anular", json={"motivo": "Vale inválido"}
    )
    assert anulacion.status_code == 200, anulacion.text
    bloqueado = await cliente.post(
        f"/api/v1/vales/{vale['id']}/ajustes",
        json={"variacion": "5.00", "motivo": "No toca un anulado"},
    )
    assert bloqueado.status_code == 409, bloqueado.text
    assert bloqueado.json()["codigo"] == "VALE_NO_AJUSTABLE"


# ---------------------------------------------------------------------------
# Anulación del vale (VAL-10/P-13) y de la orden (ORD-09/RN-17)
# ---------------------------------------------------------------------------


async def test_anulacion_deja_compromiso_en_lo_consumido(cliente):
    """P-13: anula el vale y su compromiso vale lo ya consumido."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]
    await _vender(cliente, vale["id"])

    sin_motivo = await cliente.post(
        f"/api/v1/vales/{vale['id']}/anular", json={"motivo": " "}
    )
    assert sin_motivo.status_code == 422, sin_motivo.text

    anulacion = await cliente.post(
        f"/api/v1/vales/{vale['id']}/anular",
        json={"motivo": "Orden corregida tras revisar el OCR"},
    )
    assert anulacion.status_code == 200, anulacion.text
    detalle = anulacion.json()
    assert detalle["estado"] == "anulado"
    assert detalle["saldo"] == "0.00"
    assert detalle["valor_comprometido_soles"] == "465.00"  # 30 x 15.50

    otra_vez = await cliente.post(
        f"/api/v1/vales/{vale['id']}/anular", json={"motivo": "Ya está anulado"}
    )
    assert otra_vez.status_code == 409, otra_vez.text
    assert otra_vez.json()["codigo"] == "VALE_ANULADO"

    historia = (await cliente.get(f"/api/v1/vales/{vale['id']}/movimientos")).json()
    assert [m["tipo"] for m in historia] == ["emision", "consumo", "anulacion"]
    assert historia[-1]["saldo_posterior"] == "0.00"
    assert historia[-1]["motivo"] == "Orden corregida tras revisar el OCR"


async def test_vale_de_orden_anulada_no_se_anula_por_el_vale(cliente):
    """RN-13: invierte el orden: corrige la orden antes de tocar el vale."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]
    orden = datos["orden"]

    orden_anulada = await cliente.post(
        f"/api/v1/ordenes/{orden['id']}/anular",
        json={"motivo": "Prueba de orden anulada"},
    )
    assert orden_anulada.status_code == 200, orden_anulada.text

    anulacion = await cliente.post(
        f"/api/v1/vales/{vale['id']}/anular", json={"motivo": "Ya no aplica"}
    )
    assert anulacion.status_code == 409, anulacion.text
    assert anulacion.json()["codigo"] == "ORDEN_NO_EMITIBLE"


async def test_orden_con_consumos_no_se_anula_y_sin_consumos_si(cliente):
    """ORD-09/RN-17: la anulación de la orden exige ausencia de consumos."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]
    orden = datos["orden"]

    await _vender(cliente, vale["id"], cantidad="10.00")
    con_consumos = await cliente.post(
        f"/api/v1/ordenes/{orden['id']}/anular",
        json={"motivo": "Ya no aplica"},
    )
    assert con_consumos.status_code == 409, con_consumos.text
    assert con_consumos.json()["codigo"] == "ORDEN_CON_CONSUMOS"

    limpia = await _orden(cliente, datos["institucion"], estado="vigente")
    anulada = await cliente.post(
        f"/api/v1/ordenes/{limpia['id']}/anular",
        json={"motivo": "Registrada dos veces"},
    )
    assert anulada.status_code == 200, anulada.text


# ---------------------------------------------------------------------------
# Historial (CON-12) y despachos simultáneos (RN-05)
# ---------------------------------------------------------------------------


async def test_historial_ordenado_con_saldos_posteriores(cliente):
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]

    await _vender(cliente, vale["id"], cantidad="30.00")
    await cliente.post(
        f"/api/v1/vales/{vale['id']}/ajustes",
        json={"variacion": "-5.00", "motivo": "Medición"},
    )
    await _vender(cliente, vale["id"], cantidad="10.00")

    historia = (await cliente.get(f"/api/v1/vales/{vale['id']}/movimientos")).json()
    assert [m["tipo"] for m in historia] == ["emision", "consumo", "ajuste", "consumo"]
    assert [m["saldo_posterior"] for m in historia] == [
        "100.00",
        "70.00",
        "65.00",
        "55.00",
    ]
    assert [m["variacion"] for m in historia] == [
        "100.00",
        "-30.00",
        "-5.00",
        "-10.00",
    ]
    assert [int(m["id"]) for m in historia] == sorted(int(m["id"]) for m in historia)


async def test_consumos_simultaneos_no_exceden_saldo(cliente):
    """RN-05: sobre un vale de 100, cuatro despachos de 40 aceptan 2."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]

    contextos = [
        _cliente_con_rol(cliente, f"condes{indice}@pruebas.pe", "despachador")
        for indice in range(4)
    ]

    async def despachar(asgi) -> int:
        respuesta = await asgi.post(
            f"/api/v1/vales/{vale['id']}/consumos",
            json={"token_operacion": _token(), "cantidad_galones": "40.00"},
        )
        return respuesta.status_code

    try:
        clientes = [await paralelo.__aenter__() for paralelo in contextos]
        estados = await asyncio.gather(*(despachar(asgi) for asgi in clientes))
    finally:
        for paralelo in contextos:
            await paralelo.__aexit__(None, None, None)

    assert estados.count(201) == 2
    assert estados.count(409) == 2
    detalle = (await cliente.get(f"/api/v1/vales/{vale['id']}")).json()
    assert detalle["saldo"] == "20.00"
    assert detalle["estado"] == "activo"
