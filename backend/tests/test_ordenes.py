"""Pruebas de Fase 5: órdenes de compra (ORD-01..10).

Cubre: permisos por rol, alta con estado inicial, unicidad por institución
y año (RN-12) con proyección del número, advertencia de duplicado (ORD-08)
con ajuste de confirmación, transiciones válidas e inválidas (sección 3.4),
motivo obligatorio en la anulación, serie de numeración por orden (VAL-15),
documento adjunto validado por firma y con tope del parámetro, y totales
derivados en el detalle (RN-03, en cero sin vales).
"""

import asyncpg
import pytest
from httpx import AsyncClient

from app.config import obtener_settings
from app.db.migrar import a_dsn

RUC_VALIDO = "20100104157"


async def _admin(cliente: AsyncClient, correo: str = "ordadmin@pruebas.pe") -> dict:
    from tests.test_usuarios import _crear_usuario, _iniciar_sesion

    await _crear_usuario(correo, rol="administrador")
    sesion = await _iniciar_sesion(cliente, correo)
    cliente.headers["Authorization"] = f"Bearer {sesion['access_token']}"
    return sesion


async def _usuario_de_rol(cliente: AsyncClient, correo: str, rol: str) -> dict:
    from tests.test_usuarios import _crear_usuario, _iniciar_sesion

    await _crear_usuario(correo, rol=rol)
    sesion = await _iniciar_sesion(cliente, correo)
    cliente.headers["Authorization"] = f"Bearer {sesion['access_token']}"
    return sesion


async def _institucion(cliente: AsyncClient, **ajustes) -> dict:
    carga = {
        "nombre": "Municipalidad Distrital San Juan",
        "ruc": RUC_VALIDO,
        "tipo": "publica",
        "modalidad_numeracion": ajustes.pop("modalidad_numeracion", "por_orden"),
    }
    carga.update(ajustes)
    respuesta = await cliente.post("/api/v1/instituciones", json=carga)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


async def _orden(cliente: AsyncClient, **ajustes) -> dict:
    institucion = ajustes.pop("institucion")
    carga = {
        "institucion_id": institucion["id"],
        "fecha_emision": "2026-10-05",
        "presupuesto_soles": "5000.00",
        "estado": "borrador",
    }
    carga.update(ajustes)
    respuesta = await cliente.post("/api/v1/ordenes", json=carga)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


PDF_MINIMO = (
    b"%PDF-1.4\\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\\n"
    b"xref\\n0 4\\ntrailer<</Size 4/Root 1 0 R>>\\nstartxref\\n%%EOF\\n"
)


# ---------------------------------------------------------------------------
# Permisos por rol (sección 4.1)
# ---------------------------------------------------------------------------


async def test_oficina_puede_gestionar_ordenes_pero_no_anular(cliente):
    await _admin(cliente)
    institucion = await _institucion(cliente)
    await _usuario_de_rol(cliente, "ordoficina@pruebas.pe", "oficina")

    lectura = await cliente.get("/api/v1/ordenes")
    assert lectura.status_code == 200

    alta = await _orden(cliente, institucion=institucion)
    assert alta["estado"] == "borrador"

    anulada = await cliente.post(
        f"/api/v1/ordenes/{alta['id']}/anular", json={"motivo": "prueba de permiso"}
    )
    assert anulada.status_code == 403
    assert anulada.json()["codigo"] == "SIN_PERMISO"



async def test_despachador_no_ve_ordenes(cliente):
    await _usuario_de_rol(cliente, "orddesp@pruebas.pe", "despachador")
    lectura = await cliente.get("/api/v1/ordenes")
    assert lectura.status_code == 403


# ---------------------------------------------------------------------------
# ORD-01/02: alta, número proyectado y unicidad por institución y año
# ---------------------------------------------------------------------------


async def test_alta_borrador_y_vigente_con_numero_proyectado(cliente):
    await _admin(cliente)
    institucion = await _institucion(cliente)

    primera = await _orden(
        cliente, institucion=institucion, estado="vigente", fecha_emision="2026-03-10"
    )
    assert primera["numero"] == "1"
    assert primera["estado"] == "vigente"

    segunda = await _orden(cliente, institucion=institucion, estado="borrador")
    assert segunda["numero"] == "2"
    assert segunda["anio"] == 2026

    # Con número fijado por el cliente, el valor gana.
    fijada = await _orden(
        cliente, institucion=institucion, numero=7, fecha_emision="2026-04-01"
    )
    assert fijada["numero"] == "7"


async def test_numero_duplicado_por_institucion_anio_rechazado(cliente):
    await _admin(cliente)
    institucion = await _institucion(cliente)
    await _orden(cliente, institucion=institucion, numero=3, fecha_emision="2026-05-01")
    repetida = await cliente.post(
        "/api/v1/ordenes",
        json={
            "institucion_id": institucion["id"],
            "numero": 3,
            "fecha_emision": "2026-06-15",
            "presupuesto_soles": "1000.00",
            "estado": "borrador",
        },
    )
    assert repetida.status_code == 409
    assert repetida.json()["codigo"] == "ORDEN_DUPLICADA"
    # RF-ORD-02: el rechazo enlaza a la orden existente.
    assert repetida.json()["detalles"]["orden_id"] >= 1

    # El mismo número en otra institución no choca (RN-12 es por institución).
    otra = await _institucion(cliente, nombre="Entidad Vecina S.A.", ruc="10200109169")
    vecina = await _orden(
        cliente, institucion=otra, numero=3, fecha_emision="2026-05-01"
    )
    assert vecina["numero"] == "3"


@pytest.mark.parametrize(
    "carga_extra",
    [
        {"presupuesto_soles": "0.00"},
        {"presupuesto_soles": "-5.00"},
        {"presupuesto_soles": "abc"},
        {"fecha_emision": "2099-01-01"},  # fecha futura
        {"estado": "cerrada"},  # estado inicial inválido
        {"institucion_id": 987654321},  # inexistente
    ],
)
async def test_crear_rechazos_de_validacion(cliente, carga_extra):
    await _admin(cliente)
    institucion = await _institucion(cliente)
    carga = {
        "institucion_id": institucion["id"],
        "fecha_emision": "2026-09-30",
        "presupuesto_soles": "1000.00",
        "estado": "borrador",
    }
    carga.update(carga_extra)
    respuesta = await cliente.post("/api/v1/ordenes", json=carga)
    assert respuesta.status_code in (409, 422), respuesta.text


async def test_institucion_inactiva_no_recibe_ordenes_ni_series(cliente):
    await _admin(cliente)
    institucion = await _institucion(cliente)
    await cliente.post(f"/api/v1/instituciones/{institucion['id']}/desactivar")
    respuesta = await cliente.post(
        "/api/v1/ordenes",
        json={
            "institucion_id": institucion["id"],
            "fecha_emision": "2026-09-30",
            "presupuesto_soles": "1000.00",
        },
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "INSTITUCION_INACTIVA"


async def test_combustible_inexistente_rechazado(cliente):
    await _admin(cliente)
    institucion = await _institucion(cliente)
    respuesta = await cliente.post(
        "/api/v1/ordenes",
        json={
            "institucion_id": institucion["id"],
            "fecha_emision": "2026-09-30",
            "presupuesto_soles": "1000.00",
            "combustible_id": 4242,
        },
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "COMBUSTIBLE_INEXISTENTE"


# ---------------------------------------------------------------------------
# ORD-08: advertencia de duplicado
# ---------------------------------------------------------------------------


async def test_advertencia_de_duplicado_y_confirmacion(cliente):
    await _admin(cliente)
    institucion = await _institucion(cliente)
    await _orden(
        cliente,
        institucion=institucion,
        numero=1,
        fecha_emision="2026-10-05",
        presupuesto_soles="5000.00",
    )

    cruzado = await cliente.post(
        "/api/v1/ordenes/duplicado",
        json={
            "institucion_id": institucion["id"],
            "fecha_emision": "2026-10-05",
            "presupuesto_soles": "5000.00",
        },
    )
    assert cruzado.status_code == 200, cruzado.text
    aviso = cruzado.json()
    assert aviso["certificada"] is True
    assert aviso["orden"]["numero"] == "1"

    sin_ajuste = await cliente.post(
        "/api/v1/ordenes",
        json={
            "institucion_id": institucion["id"],
            "fecha_emision": "2026-10-05",
            "presupuesto_soles": "5000.00",
        },
    )
    assert sin_ajuste.status_code == 409
    assert sin_ajuste.json()["codigo"] == "ORDEN_POSIBLE_DUPLICADA"

    confirmada = await cliente.post(
        "/api/v1/ordenes",
        json={
            "institucion_id": institucion["id"],
            "fecha_emision": "2026-10-05",
            "presupuesto_soles": "5000.00",
            "confirmar_duplicado": True,
        },
    )
    assert confirmada.status_code == 201, confirmada.text

    # Otra fecha o presupuesto distintos no dispara la advertencia.
    distinta = await cliente.post(
        "/api/v1/ordenes/duplicado",
        json={
            "institucion_id": institucion["id"],
            "fecha_emision": "2026-10-06",
            "presupuesto_soles": "5000.00",
        },
    )
    assert distinta.json()["certificada"] is False

    # La advertencia no cruza institucionalmente.
    otra = await _institucion(cliente, nombre="Entidad Breve S.A.", ruc="10200109169")
    externa = await cliente.post(
        "/api/v1/ordenes/duplicado",
        json={
            "institucion_id": otra["id"],
            "fecha_emision": "2026-10-05",
            "presupuesto_soles": "5000.00",
        },
    )
    assert externa.json()["certificada"] is False


# ---------------------------------------------------------------------------
# ORD-03: edición restringida
# ---------------------------------------------------------------------------


async def test_edicion_parcial_con_y_sin_vales(cliente):
    await _admin(cliente)
    institucion = await _institucion(cliente)
    orden = await _orden(cliente, institucion=institucion, estado="vigente")

    editada = await cliente.patch(
        f"/api/v1/ordenes/{orden['id']}",
        json={"observaciones": "Reposición de vales para patrullaje", "confirmar_duplicado": False},
    )
    assert editada.status_code == 200
    assert editada.json()["observaciones"] == ("Reposición de vales para patrullaje")

    cerrada = await cliente.post(
        f"/api/v1/ordenes/{orden['id']}/cerrar",
        # sin vales, el cierre es válida con la orden vigente
    )
    assert cerrada.status_code == 200, cerrada.text

    tras_cierre = await cliente.patch(
        f"/api/v1/ordenes/{orden['id']}", json={"observaciones": "late"}
    )
    assert tras_cierre.status_code == 409
    assert tras_cierre.json()["codigo"] == "ESTADO_INVALIDO"

    inexistente = await cliente.patch(
        "/api/v1/ordenes/4242", json={"observaciones": "x"}
    )
    assert inexistente.status_code == 404


# ---------------------------------------------------------------------------
# ORD-04: documento adjunto
# ---------------------------------------------------------------------------


async def test_adjuntar_y_leer_documento_pdf(cliente):
    await _admin(cliente)
    institucion = await _institucion(cliente)
    orden = await _orden(cliente, institucion=institucion)

    subida = await cliente.post(
        f"/api/v1/ordenes/{orden['id']}/archivo", content=PDF_MINIMO
    )
    assert subida.status_code == 200, subida.text
    cuerpo = subida.json()
    assert cuerpo["media_type"] == "application/pdf"
    assert cuerpo["archivo_tamano"] == len(PDF_MINIMO)
    assert len(cuerpo["archivo_hash"]) == 64

    descarga = await cliente.get(f"/api/v1/ordenes/{orden['id']}/archivo")
    assert descarga.status_code == 200
    assert descarga.content == PDF_MINIMO
    assert descarga.headers["content-type"].startswith("application/pdf")
    assert descarga.headers["x-content-type-options"] == "nosniff"

    sin_archivo = await cliente.get("/api/v1/ordenes/99999/archivo")
    assert sin_archivo.status_code == 404


async def test_archivo_rechaza_formato_y_supera_el_parametro(cliente):
    await _admin(cliente)
    institucion = await _institucion(cliente)
    orden = await _orden(cliente, institucion=institucion)

    # Firma desconocida (GIF aunque su extensión diga .pdf).
    rechazado = await cliente.post(
        f"/api/v1/ordenes/{orden['id']}/archivo",
        content=b"GIF89a" + b"x" * 100,
    )
    assert rechazado.status_code == 422
    assert rechazado.json()["codigo"] == "FORMATO_INVALIDO"

    # Bajar el tope al parámetro y superarlo (CFG-01: archivo_max_mb = 1).
    ajustes = obtener_settings()
    conexion = await asyncpg.connect(a_dsn(ajustes.database_url))
    try:
        await conexion.execute(
            "UPDATE parametros SET valor = '1' WHERE clave = 'archivo_max_mb'"
        )
    finally:
        await conexion.close()
    gigante = b"%PDF-1.4" + b"0" * (2 * 1024 * 1024)
    demasiado = await cliente.post(
        f"/api/v1/ordenes/{orden['id']}/archivo", content=gigante
    )
    assert demasiado.status_code == 422
    assert demasiado.json()["codigo"] == "ARCHIVO_MUY_GRANDE"


@pytest.mark.parametrize(
    "estados",
    [
        ("borrador", "vigente", "cerrada"),
        ("borrador", "anulada"),
    ],
)
async def test_transiciones_validas(cliente, estados):
    await _admin(cliente)
    institucion = await _institucion(cliente)
    orden = await _orden(cliente, institucion=institucion)
    for estado in estados[1:]:
        if estado == "vigente":
            respuesta = await cliente.post(f"/api/v1/ordenes/{orden['id']}/marcar-vigente")
        elif estado == "cerrada":
            respuesta = await cliente.post(f"/api/v1/ordenes/{orden['id']}/cerrar")
        else:
            respuesta = await cliente.post(
                f"/api/v1/ordenes/{orden['id']}/anular",
                json={"motivo": "duplicada en papeleo"},
            )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["estado"] == estado


@pytest.mark.parametrize(
    "estados_puente, ruta_final, con_motivo",
    [
        (["marcar-vigente", "cerrar"], "anular", True),  # cerrada es terminal
        (["anular"], "marcar-vigente", False),  # anulada es terminal
    ],
)
async def test_transiciones_invalidas(cliente, estados_puente, ruta_final, con_motivo):
    await _admin(cliente)
    institucion = await _institucion(cliente)
    orden = await _orden(cliente, institucion=institucion)
    for ruta in estados_puente:
        if ruta == "anular":
            respuesta = await cliente.post(
                f"/api/v1/ordenes/{orden['id']}/anular", json={"motivo": "prueba"}
            )
        else:
            respuesta = await cliente.post(f"/api/v1/ordenes/{orden['id']}/{ruta}")
        assert respuesta.status_code == 200, respuesta.text
    if con_motivo:
        respuesta = await cliente.post(
            f"/api/v1/ordenes/{orden['id']}/anular", json={"motivo": "otra prueba"}
        )
    else:
        respuesta = await cliente.post(f"/api/v1/ordenes/{orden['id']}/{ruta_final}")
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "TRANSICION_INVALIDA"


async def test_anular_sin_motivo_rechazado_y_sin_consumos_ok(cliente):
    """ORD-09/RN-17: motivo obligatorio; sin vales no hay consumos que impidan."""
    await _admin(cliente)
    institucion = await _institucion(cliente)
    orden = await _orden(cliente, institucion=institucion, estado="borrador")

    vacio = await cliente.post(
        f"/api/v1/ordenes/{orden['id']}/anular", json={"motivo": "   "}
    )
    assert vacio.status_code == 422

    anulada = await cliente.post(
        f"/api/v1/ordenes/{orden['id']}/anular", json={"motivo": "Registrada dos veces"}
    )
    assert anulada.status_code == 200, anulada.text
    assert anulada.json()["estado"] == "anulada"
    assert anulada.json()["motivo_anulacion"] == "Registrada dos veces"

    ya_anulada = await cliente.post(
        f"/api/v1/ordenes/{orden['id']}/anular", json={"motivo": "otra vez"}
    )
    assert ya_anulada.status_code == 409


# ---------------------------------------------------------------------------
#Detalle ORD-06 y serie (VAL-15)
# ---------------------------------------------------------------------------


async def test_detalle_con_totales_en_cero_y_ficha_404(cliente):
    await _admin(cliente)
    institucion = await _institucion(cliente)
    orden = await _orden(
        cliente, institucion=institucion, estado="vigente", fecha_emision="2026-02-02"
    )
    detalle = (await cliente.get(f"/api/v1/ordenes/{orden['id']}")).json()
    assert detalle["total_emitido_soles"] == "0.00"
    assert detalle["total_emitido_galones"] == "0.00"
    assert detalle["total_consumido_soles"] == "0.00"
    assert detalle["presupuesto_restante_soles"] == "5000.00"
    assert detalle["cantidad_vales"] == 0
    assert detalle["vales"] == []
    assert detalle["razon_social"] == "Municipalidad Distrital San Juan"
    assert detalle["fecha_emision"] == "2026-02-02"

    inexistente = await cliente.get("/api/v1/ordenes/4242")
    assert inexistente.status_code == 404


async def test_listado_con_filtros_de_institucion_estado_y_fecha(cliente):
    """ORD-05: listado con filtros combinables y paginación."""
    await _admin(cliente)
    institucion = await _institucion(cliente)
    await _orden(
        cliente, institucion=institucion, estado="vigente", fecha_emision="2026-05-01"
    )
    await _orden(cliente, institucion=institucion, estado="borrador")

    vigentes = (await cliente.get(
        "/api/v1/ordenes", params={"estado": "vigente"}
    )).json()["items"]
    assert len(vigentes) == 1
    assert vigentes[0]["estado"] == "vigente"

    total = (await cliente.get(
        "/api/v1/ordenes", params={"institucion_id": institucion["id"]}
    )).json()["total"]
    assert total == 2

    rango = (await cliente.get(
        "/api/v1/ordenes", params={"desde": "2026-05-01", "hasta": "2026-05-31"}
    )).json()["total"]
    assert rango == 1

    texto_num = (await cliente.get(
        "/api/v1/ordenes", params={"texto": "Municipalidad"}
    )).json()["total"]
    assert texto_num == 2


async def test_serie_por_orden_y_reglas_de_validacion(cliente):
    """ORD-01: serie solo con modalidad por_orden y rango coherente; ORD-02b: stock."""
    await _admin(cliente)
    institucion = await _institucion(cliente, modalidad_numeracion="por_orden")

    sin_serie_completa = await cliente.post(
        "/api/v1/ordenes",
        json={
            "institucion_id": institucion["id"],
            "fecha_emision": "2026-09-30",
            "presupuesto_soles": "1000.00",
            "serie_desde": 10,
        },
    )
    assert sin_serie_completa.status_code == 422
    assert sin_serie_completa.json()["codigo"] == "SERIE_INCOMPLETA"

    invertida = await cliente.post(
        "/api/v1/ordenes",
        json={
            "institucion_id": institucion["id"],
            "fecha_emision": "2026-09-30",
            "presupuesto_soles": "1000.00",
            "serie_desde": 50,
            "serie_hasta": 10,
        },
    )
    assert invertida.status_code == 422
    assert invertida.json()["codigo"] == "SERIE_INVALIDA"

    orden = await _serie_creada(cliente, institucion)
    stock = (await cliente.get(f"/api/v1/ordenes/{orden['id']}/serie")).json()
    assert stock["serie_desde"] == 10
    assert stock["total_rango"] == 31
    assert stock["usados"] == []
    assert stock["disponibles"][0] == 10
    assert stock["disponibles"][-1] == 40

    # La serie no aplica a una institución con numeración general.
    general = await _institucion(
        cliente, nombre="Estación General S.A.", ruc="10200109169",
        modalidad_numeracion="no_aplica",
    )
    no_aplica = await cliente.post(
        "/api/v1/ordenes",
        json={
            "institucion_id": general["id"],
            "fecha_emision": "2026-09-30",
            "presupuesto_soles": "1000.00",
            "serie_desde": 1,
            "serie_hasta": 5,
        },
    )
    assert no_aplica.status_code == 422
    assert no_aplica.json()["codigo"] == "SERIE_NO_APLICABLE"

    sin_serie = await _orden(cliente, institucion=general)
    stock_vacio = await cliente.get(f"/api/v1/ordenes/{sin_serie['id']}/serie")
    assert stock_vacio.status_code == 409
    assert stock_vacio.json()["codigo"] == "SIN_SERIE"


async def _serie_creada(cliente: AsyncClient, institucion: dict) -> dict:
    respuesta = await cliente.post(
        "/api/v1/ordenes",
        json={
            "institucion_id": institucion["id"],
            "fecha_emision": "2026-09-30",
            "presupuesto_soles": "1000.00",
            "serie_desde": 10,
            "serie_hasta": 40,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# ---------------------------------------------------------------------------
# Cierre de fase: sin ruta de edición/borrado físico (RN-11)
# ---------------------------------------------------------------------------


def test_no_existen_rutas_para_eliminar_ordenes_ni_instituciones():
    from fastapi.routing import APIRoute

    from app.main import app as aplicacion

    rutas = {
        (ruta.methods, ruta.path)
        for ruta in aplicacion.routes
        if isinstance(ruta, APIRoute)
    }
    delete = [
        (metodos, ruta)
        for metodos, ruta in rutas
        if "DELETE" in metodos
        and ("instituciones" in ruta or "ordenes" in ruta)
    ]
    assert delete == []
