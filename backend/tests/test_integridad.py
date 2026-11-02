"""Pruebas de Fase 8: integridad de saldos (AUD-05, AUD-06, AUD-02).

Cubre: verificación sin diferencias con datos coherentes, diferencia provocada
y detectada, refresco de la alerta pendiente sin duplicarla, revisión con
comentario, no repetir avisos de una diferencia ya revisada salvo que
reaparezca, indicador del panel solo para el administrador, comando CLI con
su código de salida y las garantías de la base: `vales_app` no puede
modificar, borrar ni truncar `movimientos_vale` y `auditoria`, `vales_migrador`
tampoco gracias a los disparadores, y una diferencia revisada no se reescribe
ni se elimina.
"""

import os

import asyncpg

from app.cli import ejecutar_verificar_saldos
from app.config import obtener_settings
from app.db.migrar import a_dsn
from tests.test_consumos import _vale_de_100, _vender
from tests.test_vales import _parchear_vale, _usuario_de_rol

_CODIGO_SIN_PERMISO = "42501"
_CODIGO_INMUTABLE = "55000"


def _url_aplicacion() -> str:
    """Rol de ejecución (`vales_app`), el que usa la API en producción."""
    return obtener_settings().database_url


def _url_migrador() -> str:
    """Rol dueño del esquema; conftest ya apunta a la base de pruebas."""
    return os.environ["MIGRADOR_URL"]


async def _codigo_de_error(url: str, sql: str, *argumentos: object) -> str:
    """Ejecuta la sentencia y devuelve el SQLSTATE del rechazo esperado."""
    conexion = await asyncpg.connect(a_dsn(url))
    try:
        await conexion.execute(sql, *argumentos)
    except asyncpg.PostgresError as exc:
        return exc.sqlstate or ""
    finally:
        await conexion.close()
    raise AssertionError(f"La base aceptó una sentencia que debía rechazar: {sql}")


async def _verificar(cliente) -> dict:
    respuesta = await cliente.post("/api/v1/auditoria/integridad/verificar")
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


async def _pendientes(cliente) -> dict:
    respuesta = await cliente.get(
        "/api/v1/auditoria/integridad/diferencias", params={"revisada": False}
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


# ---------------------------------------------------------------------------
# Verificación (AUD-05)
# ---------------------------------------------------------------------------


async def test_sin_diferencias_con_saldos_coherentes(cliente):
    """AUD-05: con datos que cuadran, la corrida informa cero diferencias."""
    datos = await _vale_de_100(cliente)
    await _vender(cliente, datos["vale"]["id"], "30.00")

    resultado = await _verificar(cliente)
    assert resultado["vales_revisados"] == 1
    assert resultado["diferencias"] == 0
    assert resultado["ejecutada_por_nombre"] == "Usuario de Prueba"

    ultima = (
        await cliente.get("/api/v1/auditoria/integridad/ultima")
    ).json()
    assert ultima["verificacion"]["id"] == resultado["id"]
    assert ultima["verificacion"]["diferencias"] == 0
    assert ultima["diferencias_pendientes"] == 0

    historial = (
        await cliente.get("/api/v1/auditoria/integridad/verificaciones")
    ).json()
    assert historial["total"] == 1
    assert historial["items"][0]["id"] == resultado["id"]


async def test_ultima_sin_verificaciones_devuelve_nulo(cliente):
    """AUD-05: antes de la primera corrida no hay resultado que mostrar."""
    await _vale_de_100(cliente)

    respuesta = await cliente.get("/api/v1/auditoria/integridad/ultima")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["verificacion"] is None
    assert respuesta.json()["diferencias_pendientes"] == 0


async def test_diferencia_provocada_se_detecta(cliente):
    """AUD-05: un saldo alterado por fuera del sistema aparece como descuadre."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]
    await _vender(cliente, vale["id"], "30.00")
    await _parchear_vale(vale["id"], {"saldo": "71.00"})

    resultado = await _verificar(cliente)
    assert resultado["vales_revisados"] == 1
    assert resultado["diferencias"] == 1

    pendientes = await _pendientes(cliente)
    assert pendientes["total"] == 1
    diferencia = pendientes["items"][0]
    assert diferencia["vale_id"] == vale["id"]
    assert diferencia["numero_estacion"] == vale["numero_estacion"]
    assert diferencia["saldo_almacenado"] == "71.00"
    assert diferencia["saldo_recalculado"] == "70.00"
    assert diferencia["diferencia"] == "1.00"
    assert diferencia["revisada"] is False
    assert diferencia["comentario"] is None

    todas = (
        await cliente.get("/api/v1/auditoria/integridad/diferencias")
    ).json()
    assert todas["total"] == 1


async def test_alerta_pendiente_se_refresca_sin_duplicarse(cliente):
    """AUD-06: el descuadre sigue abierto y la corrida actualiza sus saldos."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]
    await _vender(cliente, vale["id"], "30.00")
    await _parchear_vale(vale["id"], {"saldo": "71.00"})
    await _verificar(cliente)
    primera = (await _pendientes(cliente))["items"][0]

    await _parchear_vale(vale["id"], {"saldo": "73.00"})
    await _verificar(cliente)
    pendientes = await _pendientes(cliente)
    assert pendientes["total"] == 1
    assert pendientes["items"][0]["id"] == primera["id"]
    assert pendientes["items"][0]["saldo_almacenado"] == "73.00"
    assert pendientes["items"][0]["diferencia"] == "3.00"


# ---------------------------------------------------------------------------
# Revisión (AUD-06)
# ---------------------------------------------------------------------------


async def test_revisar_marca_la_diferencia_con_comentario(cliente):
    """AUD-06: la revisión queda con revisor, fecha y comentario."""
    datos = await _vale_de_100(cliente)
    await _parchear_vale(datos["vale"]["id"], {"saldo": "99.00"})
    await _verificar(cliente)
    diferencia = (await _pendientes(cliente))["items"][0]

    respuesta = await cliente.post(
        f"/api/v1/auditoria/integridad/diferencias/{diferencia['id']}/revisar",
        json={"comentario": "Carga corregida en el comprobante físico"},
    )
    assert respuesta.status_code == 200, respuesta.text
    revisada = respuesta.json()
    assert revisada["revisada"] is True
    assert revisada["comentario"] == "Carga corregida en el comprobante físico"
    assert revisada["revisada_por_nombre"] == "Usuario de Prueba"
    assert revisada["revisada_en"] is not None

    assert (await _pendientes(cliente))["total"] == 0
    revisadas = (
        await cliente.get(
            "/api/v1/auditoria/integridad/diferencias", params={"revisada": True}
        )
    ).json()
    assert revisadas["total"] == 1
    assert revisadas["items"][0]["id"] == diferencia["id"]


async def test_diferencia_revisada_no_se_repite_si_no_cambia(cliente):
    """AUD-06: el aviso aceptado no vuelve en cada corrida."""
    datos = await _vale_de_100(cliente)
    await _parchear_vale(datos["vale"]["id"], {"saldo": "99.00"})
    await _verificar(cliente)
    diferencia = (await _pendientes(cliente))["items"][0]
    await cliente.post(
        f"/api/v1/auditoria/integridad/diferencias/{diferencia['id']}/revisar",
        json={"comentario": "Saldo verificado contra el kardex"},
    )

    segunda = await _verificar(cliente)
    assert segunda["diferencias"] == 1  # el descuadre sigue ahí
    assert (await _pendientes(cliente))["total"] == 0  # pero no se re-avisa

    tercera = await _verificar(cliente)
    assert tercera["diferencias"] == 1
    assert (await _pendientes(cliente))["total"] == 0


async def test_diferencia_que_reaparece_con_otro_saldo_avisa_de_nuevo(cliente):
    """AUD-06: si el descuadre cambió, es una alerta nueva que revisar."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]
    await _parchear_vale(vale["id"], {"saldo": "99.00"})
    await _verificar(cliente)
    primera = (await _pendientes(cliente))["items"][0]
    await cliente.post(
        f"/api/v1/auditoria/integridad/diferencias/{primera['id']}/revisar",
        json={"comentario": "Diferencia de un céntimo aceptada"},
    )

    await _parchear_vale(vale["id"], {"saldo": "95.00"})
    await _verificar(cliente)
    pendientes = await _pendientes(cliente)
    assert pendientes["total"] == 1
    assert pendientes["items"][0]["id"] != primera["id"]
    assert pendientes["items"][0]["saldo_almacenado"] == "95.00"


async def test_revisar_exige_comentario_y_no_repite_la_revision(cliente):
    """AUD-06: comentario obligatorio, 404 si no existe y 409 si ya se revisó."""
    datos = await _vale_de_100(cliente)
    await _parchear_vale(datos["vale"]["id"], {"saldo": "99.00"})
    await _verificar(cliente)
    diferencia = (await _pendientes(cliente))["items"][0]

    vacio = await cliente.post(
        f"/api/v1/auditoria/integridad/diferencias/{diferencia['id']}/revisar",
        json={"comentario": "   "},
    )
    assert vacio.status_code == 422
    assert vacio.json()["codigo"] == "VALIDACION_INVALIDA"

    inexistente = await cliente.post(
        "/api/v1/auditoria/integridad/diferencias/999999/revisar",
        json={"comentario": "No existe"},
    )
    assert inexistente.status_code == 404
    assert inexistente.json()["codigo"] == "DIFERENCIA_NO_ENCONTRADA"

    primera = await cliente.post(
        f"/api/v1/auditoria/integridad/diferencias/{diferencia['id']}/revisar",
        json={"comentario": "Revisada una sola vez"},
    )
    assert primera.status_code == 200, primera.text

    repetida = await cliente.post(
        f"/api/v1/auditoria/integridad/diferencias/{diferencia['id']}/revisar",
        json={"comentario": "Segunda revisión"},
    )
    assert repetida.status_code == 409
    assert repetida.json()["codigo"] == "DIFERENCIA_YA_REVISADA"


# ---------------------------------------------------------------------------
# Permisos e indicador del panel (AUD-02, AUD-06)
# ---------------------------------------------------------------------------


async def test_auditoria_e_integridad_solo_para_el_administrador(cliente):
    """Solo el administrador tiene `auditoria.ver`."""
    await _vale_de_100(cliente)
    await _usuario_de_rol(cliente, "oficina.integridad@pruebas.pe", "oficina")

    for metodo, ruta in (
        ("get", "/api/v1/auditoria/bitacora"),
        ("get", "/api/v1/auditoria/integridad/ultima"),
        ("get", "/api/v1/auditoria/integridad/verificaciones"),
        ("get", "/api/v1/auditoria/integridad/diferencias"),
    ):
        respuesta = await getattr(cliente, metodo)(ruta)
        assert respuesta.status_code == 403, f"{ruta} → {respuesta.status_code}"
        assert respuesta.json()["codigo"] == "SIN_PERMISO"
    verificar = await cliente.post("/api/v1/auditoria/integridad/verificar")
    assert verificar.status_code == 403


async def test_panel_muestra_diferencias_solo_al_administrador(cliente):
    """AUD-06 en el panel: el administrador ve el contador de pendientes."""
    datos = await _vale_de_100(cliente)
    await _parchear_vale(datos["vale"]["id"], {"saldo": "99.00"})
    await _verificar(cliente)

    admin = (await cliente.get("/api/v1/panel/indicadores")).json()
    assert admin["diferencias_sin_revisar"] == 1

    await _usuario_de_rol(cliente, "oficina.panel@pruebas.pe", "oficina")
    oficina = await cliente.get("/api/v1/panel/indicadores")
    assert oficina.status_code == 200, oficina.text
    assert oficina.json()["diferencias_sin_revisar"] is None


# ---------------------------------------------------------------------------
# Comando CLI (AUD-05)
# ---------------------------------------------------------------------------


async def test_cli_verificar_saldos_codigo_de_salida(cliente, capsys):
    """AUD-05: 0 sin diferencias y 1 cuando hay descuadres."""
    datos = await _vale_de_100(cliente)
    await _vender(cliente, datos["vale"]["id"], "30.00")

    assert await ejecutar_verificar_saldos() == 0
    assert "0 diferencias" in capsys.readouterr().out

    await _parchear_vale(datos["vale"]["id"], {"saldo": "71.00"})
    assert await ejecutar_verificar_saldos() == 1
    salida = capsys.readouterr()
    assert "1 diferencias" in salida.out
    assert "diferencias" in salida.err


# ---------------------------------------------------------------------------
# Garantías de la base (AUD-02)
# ---------------------------------------------------------------------------

_SENTENCIAS_PROHIBIDAS = (
    "UPDATE movimientos_vale SET variacion = 0",
    "DELETE FROM movimientos_vale",
    "UPDATE auditoria SET accion = 'falseada'",
    "DELETE FROM auditoria",
    "TRUNCATE movimientos_vale",
    "TRUNCATE auditoria",
)


async def test_vales_app_no_puede_mutar_ni_truncar(cliente):
    """AUD-02: el rol de la aplicación solo inserta en movimientos y bitácora."""
    datos = await _vale_de_100(cliente)
    await _vender(cliente, datos["vale"]["id"], "10.00")

    for sentencia in _SENTENCIAS_PROHIBIDAS:
        codigo = await _codigo_de_error(_url_aplicacion(), sentencia)
        assert codigo == _CODIGO_SIN_PERMISO, f"{sentencia} → {codigo}"


async def test_vales_migrador_tampoco_altera_ni_trunca(cliente):
    """AUD-02: los disparadores también frenan al dueño del esquema."""
    datos = await _vale_de_100(cliente)
    await _vender(cliente, datos["vale"]["id"], "10.00")

    for sentencia in _SENTENCIAS_PROHIBIDAS:
        codigo = await _codigo_de_error(_url_migrador(), sentencia)
        assert codigo == _CODIGO_INMUTABLE, f"{sentencia} → {codigo}"


async def test_diferencia_revisada_queda_congelada(cliente):
    """AUD-06: la evidencia no se reescribe ni se borra."""
    datos = await _vale_de_100(cliente)
    vale = datos["vale"]
    await _parchear_vale(vale["id"], {"saldo": "99.00"})
    await _verificar(cliente)
    diferencia = (await _pendientes(cliente))["items"][0]
    url = _url_migrador()

    # Pendiente: el origen (vale y fecha de detección) ya es inmutable.
    codigo = await _codigo_de_error(
        url,
        "UPDATE diferencias_integridad SET vale_id = vale_id + 1 WHERE id = $1",
        diferencia["id"],
    )
    assert codigo == _CODIGO_INMUTABLE
    codigo = await _codigo_de_error(
        url, "DELETE FROM diferencias_integridad WHERE id = $1", diferencia["id"]
    )
    assert codigo == _CODIGO_INMUTABLE

    await cliente.post(
        f"/api/v1/auditoria/integridad/diferencias/{diferencia['id']}/revisar",
        json={"comentario": "Revisada antes de congelarse"},
    )
    codigo = await _codigo_de_error(
        url,
        "UPDATE diferencias_integridad SET comentario = 'otro' WHERE id = $1",
        diferencia["id"],
    )
    assert codigo == _CODIGO_INMUTABLE
    codigo = await _codigo_de_error(
        url, "DELETE FROM diferencias_integridad WHERE id = $1", diferencia["id"]
    )
    assert codigo == _CODIGO_INMUTABLE
