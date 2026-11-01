"""Pruebas de Fase 4: combustibles, precios e inmutabilidad del histórico (CMB-01..04).

Cubre: precio vigente con dos cambios, fecha anterior rechazada, precio
duplicado por fecha, inexistencia de edición/borrado de precios (ausencia de
rutas y REVOKE en la base), nombres duplicados, permisos catalogo.ver y
catalogo.gestionar por rol, y auditoría de los cambios.
"""

import asyncio

import asyncpg
import pytest
from fastapi.routing import APIRoute

from app.config import obtener_settings
from app.db.migrar import a_dsn
from app.main import app as aplicacion

PRECIO_INICIAL = "15.50"
PRECIO_SEGUNDO = "16.80"


async def _admin(cliente, correo: str = "catadmin@pruebas.pe") -> dict:
    """Crea un administrador, inicia sesión y deja su Bearer en el cliente."""
    from tests.test_usuarios import _crear_usuario, _iniciar_sesion

    await _crear_usuario(correo, rol="administrador")
    sesion = await _iniciar_sesion(cliente, correo)
    cliente.headers["Authorization"] = f"Bearer {sesion['access_token']}"
    return sesion


async def _usuario_de_rol(cliente, correo: str, rol: str) -> dict:
    from tests.test_usuarios import _crear_usuario, _iniciar_sesion

    await _crear_usuario(correo, rol=rol)
    sesion = await _iniciar_sesion(cliente, correo)
    cliente.headers["Authorization"] = f"Bearer {sesion['access_token']}"
    return sesion


async def _crear_combustible(cliente, nombre: str) -> dict:
    respuesta = await cliente.post("/api/v1/combustibles", json={"nombre": nombre})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# ---------------------------------------------------------------------------
# CMB-01: catálogo, creación, edición y permisos
# ---------------------------------------------------------------------------


async def test_oficina_lee_catalogo_pero_no_gestiona(cliente):
    await _admin(cliente)
    await _usuario_de_rol(cliente, "catofi@pruebas.pe", "oficina")

    lectura = await cliente.get("/api/v1/combustibles")
    assert lectura.status_code == 200

    alta = await cliente.post("/api/v1/combustibles", json={"nombre": "Prohibido X"})
    assert alta.status_code == 403
    assert alta.json()["codigo"] == "SIN_PERMISO"


async def test_despachador_no_ve_catalogo(cliente):
    await _usuario_de_rol(cliente, "catdesp@pruebas.pe", "despachador")
    lectura = await cliente.get("/api/v1/combustibles")
    assert lectura.status_code == 403
    assert lectura.json()["codigo"] == "SIN_PERMISO"


async def test_crear_y_editar_combustible_con_auditoria(cliente):
    await _admin(cliente)

    filas = await cliente.get("/api/v1/combustibles")
    assert filas.status_code == 200
    assert filas.json()["items"] == []  # el catálogo arranca vacío entre pruebas

    alta = await _crear_combustible(cliente, "Diésel B5")
    assert alta["nombre"] == "Diésel B5"
    assert alta["activo"] is True

    duplicado = await cliente.post("/api/v1/combustibles", json={"nombre": "diésel b5"})
    assert duplicado.status_code == 409
    assert duplicado.json()["codigo"] == "NOMBRE_DUPLICADO"

    sin_nombre = await cliente.post("/api/v1/combustibles", json={"nombre": "  "})
    assert sin_nombre.status_code == 422

    edicion = await cliente.patch(
        f"/api/v1/combustibles/{alta['id']}", json={"nombre": "Diésel B5 U"}
    )
    assert edicion.status_code == 200
    assert edicion.json()["nombre"] == "Diésel B5 U"

    desactivado = await cliente.patch(
        f"/api/v1/combustibles/{alta['id']}", json={"activo": False}
    )
    assert desactivado.json()["activo"] is False

    inexistente = await cliente.patch(
        "/api/v1/combustibles/9999", json={"activo": True}
    )
    assert inexistente.status_code == 404

    from tests.test_usuarios import _migrador

    async with _migrador() as conexion:
        filas = await conexion.fetch(
            "SELECT accion FROM auditoria WHERE entidad = 'combustible' ORDER BY id"
        )
    assert {f["accion"] for f in filas} == {"crear_combustible", "editar_combustible"}


async def test_listado_filtro_activo_incluye_precio_vigente(cliente):
    await _admin(cliente)
    gas = await _crear_combustible(cliente, "Gasohol 90")
    await _crear_combustible(cliente, "Gasohol 95")

    await cliente.patch(f"/api/v1/combustibles/{gas['id']}", json={"activo": False})

    todos = (await cliente.get("/api/v1/combustibles")).json()
    assert len(todos["items"]) == 2

    activos = (await cliente.get(
        "/api/v1/combustibles", params={"activo": "true"}
    )).json()
    assert {c["nombre"] for c in activos["items"]} == {"Gasohol 95"}

    sin_precio = next(c for c in activos["items"] if c["nombre"] == "Gasohol 95")
    assert sin_precio["precio_vigente"] is None

    registrados = await cliente.post(
        f"/api/v1/combustibles/{sin_precio['id']}/precios",
        json={"precio_galon": "15.20", "vigente_desde": "2026-11-01"},
    )
    assert registrados.status_code == 201, registrados.text
    activos = (await cliente.get(
        "/api/v1/combustibles", params={"activo": "true"}
    )).json()
    con_precio = next(c for c in activos["items"] if c["nombre"] == "Gasohol 95")
    assert con_precio["precio_vigente"]["precio_galon"] == "15.20"


# ---------------------------------------------------------------------------
# CMB-02/03: precios, vigencia e inmutabilidad
# ---------------------------------------------------------------------------


async def test_precio_vigente_con_dos_cambios(cliente):
    await _admin(cliente)
    gas = await _crear_combustible(cliente, "Gasohol 95")

    primero = await cliente.post(
        f"/api/v1/combustibles/{gas['id']}/precios",
        json={"precio_galon": PRECIO_INICIAL, "vigente_desde": "2026-01-01"},
    )
    assert primero.status_code == 201, primero.text
    segundo = await cliente.post(
        f"/api/v1/combustibles/{gas['id']}/precios",
        json={"precio_galon": PRECIO_SEGUNDO, "vigente_desde": "2026-06-01"},
    )
    assert segundo.status_code == 201

    listado = (await cliente.get("/api/v1/combustibles")).json()["items"][0]
    # El precio vigente hoy es el último con vigencia menor o igual.
    assert listado["precio_vigente"] == {
        "precio_galon": PRECIO_SEGUNDO,
        "vigente_desde": "2026-06-01",
    }

    historico = (await cliente.get(
        f"/api/v1/combustibles/{gas['id']}/precios"
    )).json()
    assert [p["precio_galon"] for p in historico] == [PRECIO_SEGUNDO, PRECIO_INICIAL]
    # El precio nuevo queda asociado a la cuenta registradora.
    assert historico[0]["registrado_por"] is not None


async def test_fecha_anterior_y_duplicada_rechazadas(cliente):
    await _admin(cliente)
    gas = await _crear_combustible(cliente, "Diésel B5")

    await cliente.post(
        f"/api/v1/combustibles/{gas['id']}/precios",
        json={"precio_galon": PRECIO_INICIAL, "vigente_desde": "2026-06-01"},
    )
    atrasado = await cliente.post(
        f"/api/v1/combustibles/{gas['id']}/precios",
        json={"precio_galon": "17.00", "vigente_desde": "2026-03-01"},
    )
    assert atrasado.status_code == 409
    assert atrasado.json()["codigo"] == "FECHA_PRECIO_ATRASADA"

    repetido = await cliente.post(
        f"/api/v1/combustibles/{gas['id']}/precios",
        json={"precio_galon": "17.00", "vigente_desde": "2026-06-01"},
    )
    assert repetido.status_code == 409
    assert repetido.json()["codigo"] == "FECHA_PRECIO_DUPLICADA"

    inexistente = await cliente.post(
        "/api/v1/combustibles/9999/precios",
        json={"precio_galon": "17.00", "vigente_desde": "2026-07-01"},
    )
    assert inexistente.status_code == 404


@pytest.mark.parametrize("precio", ["0.00", "-1.50", "abc", ""])
async def test_precio_invalido_rechazado(cliente, precio):
    await _admin(cliente)
    gas = await _crear_combustible(cliente, "Gasohol 90")
    respuesta = await cliente.post(
        f"/api/v1/combustibles/{gas['id']}/precios",
        json={"precio_galon": precio, "vigente_desde": "2026-11-01"},
    )
    assert respuesta.status_code == 422


def test_no_existen_rutas_para_editar_o_borrar_precios():
    """CMB-02/RN-16: el histórico no se edita ni se elimina por la API."""
    rutas = {
        (ruta.methods, ruta.path)
        for ruta in aplicacion.routes
        if isinstance(ruta, APIRoute)
    }
    editadas = [
        (metodos, ruta)
        for metodos, ruta in rutas
        if "precios" in ruta and (metodos & {"PUT", "PATCH", "DELETE"})
    ]
    assert editadas == []


async def test_la_base_rechaza_update_y_delete_con_el_rol_de_aplicacion():
    """La migración 0004 dejó `vales_app` sin UPDATE/DELETE/TRUNCATE en precios."""
    ajustes = obtener_settings()
    assert ajustes.database_url, "La suite siempre opera sobre la base de pruebas"
    dsn = a_dsn(ajustes.database_url)
    conexion = await asyncio.wait_for(asyncpg.connect(dsn), timeout=10)
    try:
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conexion.execute("UPDATE precios_combustible SET precio_galon = 1")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conexion.execute("DELETE FROM precios_combustible")
    finally:
        await conexion.close()
