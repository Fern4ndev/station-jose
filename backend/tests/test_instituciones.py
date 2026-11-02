"""Pruebas de Fase 5: instituciones (INS-01..09).

Cubre: permisos por rol, RUC obligatorio con dígito verificador, unicidad
del RUC, listado con filtros y paginación, edición parcial y regla de
administrador con órdenes registradas, baja lógica con reactivación que
conserva datos, y auditoría de los cambios.
"""

from httpx import AsyncClient

RUC_VALIDO_ESTACION = "20100104157"  # dígito verificador cuadrado (app.core.ruc)
RUC_VALIDO_VECINA = "10200109169"
RUC_VERIFICADOR_MALO = "20100104150"


async def _admin(cliente: AsyncClient, correo: str = "insadmin@pruebas.pe") -> dict:
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
        "ruc": RUC_VALIDO_ESTACION,
        "tipo": "publica",
        "modalidad_numeracion": "por_orden",
    }
    carga.update(ajustes)
    respuesta = await cliente.post("/api/v1/instituciones", json=carga)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# ---------------------------------------------------------------------------
# Permisos por rol (sección 4.1)
# ---------------------------------------------------------------------------


async def test_oficina_lee_y_edita_pero_no_desactiva(cliente):
    await _admin(cliente)
    creada = await _institucion(cliente)
    await _usuario_de_rol(cliente, "insofi@pruebas.pe", "oficina")

    lectura = await cliente.get("/api/v1/instituciones")
    assert lectura.status_code == 200

    ficha = await cliente.get(f"/api/v1/instituciones/{creada['id']}")
    assert ficha.status_code == 200

    alta = await cliente.post(
        "/api/v1/instituciones",
        json={"nombre": "Comité de Riego Paso Largo", "ruc": RUC_VALIDO_VECINA},
    )
    assert alta.status_code == 201, alta.text

    baja = await cliente.post(f"/api/v1/instituciones/{creada['id']}/desactivar")
    assert baja.status_code == 403
    assert baja.json()["codigo"] == "SIN_PERMISO"


async def test_despachador_no_ve_ni_crea_instituciones(cliente):
    await _usuario_de_rol(cliente, "insdesp@pruebas.pe", "despachador")
    lectura = await cliente.get("/api/v1/instituciones")
    assert lectura.status_code == 403
    alta = await cliente.post(
        "/api/v1/instituciones", json={"nombre": "Cooperativa La Huerta"}
    )
    assert alta.status_code == 403


# ---------------------------------------------------------------------------
# INS-01: alta con RUC verificado, obligatorio y único
# ---------------------------------------------------------------------------


async def test_alta_con_ruc_valido_y_verificador_rechazado(cliente):
    await _admin(cliente)

    alta = await _institucion(cliente)
    assert alta["nombre"] == "Municipalidad Distrital San Juan"
    assert alta["estado"] == "activa"

    verificador_malo = await cliente.post(
        "/api/v1/instituciones",
        json={"nombre": "Herbáceos del Valle", "ruc": RUC_VERIFICADOR_MALO},
    )
    assert verificador_malo.status_code == 422

    malformado = await cliente.post(
        "/api/v1/instituciones",
        json={"nombre": "Herbáceos del Valle", "ruc": "12345"},
    )
    assert malformado.status_code == 422

    sin_ruc = await cliente.post("/api/v1/instituciones", json={"nombre": "Sin RUC S.A."})
    assert sin_ruc.status_code == 422  # el RUC es obligatorio en 0001


async def test_ruc_duplicado_rechazado(cliente):
    await _admin(cliente)
    await _institucion(cliente)
    duplicada = await cliente.post(
        "/api/v1/instituciones",
        json={"nombre": "Municipalidad Duplicada", "ruc": RUC_VALIDO_ESTACION},
    )
    assert duplicada.status_code == 409
    assert duplicada.json()["codigo"] == "RUC_DUPLICADO"
    # RF-INS-01: se informa y se enlaza a la institución existente.
    assert duplicada.json()["detalles"]["institucion_id"] >= 1


# ---------------------------------------------------------------------------
# INS-03 + filtros de listado
# ---------------------------------------------------------------------------


async def test_ficha_con_resumenes_en_ceros(cliente):
    await _admin(cliente)
    creada = await _institucion(cliente)
    ficha = await cliente.get(f"/api/v1/instituciones/{creada['id']}")
    datos = ficha.json()
    assert datos["nombre"] == "Municipalidad Distrital San Juan"
    assert datos["ordenes"] == 0
    assert datos["presupuesto_total"] == "0.00"
    assert datos["vales_vigentes"] == 0

    inexistente = await cliente.get("/api/v1/instituciones/4242")
    assert inexistente.status_code == 404


async def test_listado_filtro_texto_y_estado_con_paginacion(cliente):
    await _admin(cliente)
    await _institucion(cliente, nombre="Estación Fitosanitaria Norte")
    segunda = await _institucion(
        cliente,
        nombre="Club Deportivo Los Halcones",
        ruc=RUC_VALIDO_VECINA,
        tipo="privada",
        modalidad_numeracion="general",
    )
    await cliente.post(f"/api/v1/instituciones/{segunda['id']}/desactivar")

    por_texto = (await cliente.get(
        "/api/v1/instituciones", params={"texto": "fitosanitaria"}
    )).json()
    assert [i["nombre"] for i in por_texto["items"]] == ["Estación Fitosanitaria Norte"]
    assert por_texto["total"] == 1

    por_ruc = (await cliente.get(
        "/api/v1/instituciones", params={"ruc": RUC_VALIDO_ESTACION}
    )).json()
    assert por_ruc["total"] == 1

    activas = (await cliente.get(
        "/api/v1/instituciones", params={"estado": "activa"}
    )).json()
    assert activas["total"] == 1
    assert activas["items"][0]["nombre"] == "Estación Fitosanitaria Norte"

    inactivas = (await cliente.get(
        "/api/v1/instituciones", params={"estado": "inactiva"}
    )).json()
    assert inactivas["total"] == 1

    pagina = (await cliente.get(
        "/api/v1/instituciones", params={"pagina": 2, "por_pagina": 1}
    )).json()
    assert len(pagina["items"]) == 1
    assert pagina["total"] == 2
    assert pagina["pagina"] == 2


# ---------------------------------------------------------------------------
# INS-04: edición y la regla de administrador con órdenes
# ---------------------------------------------------------------------------


async def test_edicion_parcial_del_contacto_y_direccion(cliente):
    await _admin(cliente)
    creada = await _institucion(cliente)
    editada = await cliente.patch(
        f"/api/v1/instituciones/{creada['id']}",
        json={
            "representante": "Ana Quispe",
            "telefono": "998112233",
            "correo": "anjuela@pruebas.pe",
        },
    )
    assert editada.status_code == 200
    datos = editada.json()
    assert datos["representante"] == "Ana Quispe"
    assert datos["nombre"] == "Municipalidad Distrital San Juan"
    assert datos["ruc"] == RUC_VALIDO_ESTACION

    inexistente = await cliente.patch("/api/v1/instituciones/4242", json={"telefono": "123"})
    assert inexistente.status_code == 404


async def test_ruc_y_modalidad_con_ordenes_solo_administrador(cliente):
    """ORD/INS-04: con órdenes registradas no oficio RUC/modalidad ni admin."""
    await _admin(cliente)
    creada = await _institucion(cliente)
    await cliente.post(
        "/api/v1/ordenes",
        json={
            "institucion_id": creada["id"],
            "fecha_emision": "2026-10-01",
            "presupuesto_soles": "5000.00",
            "estado": "borrador",
        },
    )
    cambio_admin = await cliente.patch(
        f"/api/v1/instituciones/{creada['id']}",
        json={"modalidad_numeracion": "general"},
    )
    assert cambio_admin.status_code == 200  # el propio administrador puede

    await _usuario_de_rol(cliente, "ordoficina@pruebas.pe", "oficina")
    cambio_oficina = await cliente.patch(
        f"/api/v1/instituciones/{creada['id']}",
        json={"modalidad_numeracion": "por_orden"},
    )
    assert cambio_oficina.status_code == 409
    assert cambio_oficina.json()["codigo"] == "SOLO_ADMINISTRADOR"

    oficina_ruc = await cliente.patch(
        f"/api/v1/instituciones/{creada['id']}",
        json={"ruc": RUC_VALIDO_VECINA},
    )
    assert oficina_ruc.status_code == 409


# ---------------------------------------------------------------------------
# INS-06/07: baja lógica y reactivación
# ---------------------------------------------------------------------------


async def test_desactivar_y_reactivar_conserva_datos(cliente):
    await _admin(cliente)
    creada = await _institucion(cliente)
    desactivada = await cliente.post(
        f"/api/v1/instituciones/{creada['id']}/desactivar"
    )
    assert desactivada.status_code == 200
    assert desactivada.json()["estado"] == "inactiva"

    fic1 = await cliente.get(f"/api/v1/instituciones/{creada['id']}")
    assert fic1.json()["estado"] == "inactiva"

    reactivada = await cliente.post(
        f"/api/v1/instituciones/{creada['id']}/reactivar"
    )
    assert reactivada.status_code == 200
    assert reactivada.json()["estado"] == "activa"

    ficha = (await cliente.get(f"/api/v1/instituciones/{creada['id']}")).json()
    assert ficha["nombre"] == "Municipalidad Distrital San Juan"
    assert ficha["ruc"] == RUC_VALIDO_ESTACION

    ya_activa = await cliente.post(
        f"/api/v1/instituciones/{creada['id']}/reactivar"
    )
    assert ya_activa.status_code == 409
    assert ya_activa.json()["codigo"] == "INSTITUCION_YA_ACTIVA"

    inexistente = await cliente.post("/api/v1/instituciones/4242/reactivar")
    assert inexistente.status_code == 404


# ---------------------------------------------------------------------------
# Auditoría
# ---------------------------------------------------------------------------


async def test_auditoria_registra_creacion_edicion_y_baja(cliente):
    await _admin(cliente)
    creada = await _institucion(cliente)
    await cliente.patch(
        f"/api/v1/instituciones/{creada['id']}", json={"telefono": "01 223344"}
    )
    await cliente.post(f"/api/v1/instituciones/{creada['id']}/desactivar")

    from tests.test_usuarios import _migrador

    async with _migrador() as conexion:
        filas = await conexion.fetch(
            "SELECT accion FROM auditoria WHERE entidad = 'instituciones' ORDER BY id"
        )
    acciones = [fila["accion"] for fila in filas]
    assert acciones == [
        "institucion_creada",
        "institucion_editada",
        "institucion_desactivada",
    ]


# ---------------------------------------------------------------------------
# Verificación de RUC en vivo (INS-01/OCR-08)
# ---------------------------------------------------------------------------


async def test_verificacion_de_ruc_valida_y_enlaza_a_la_existente(cliente):
    """GET /instituciones/ruc/{ruc}: valido, libre, dígito mal y malformado."""
    await _admin(cliente)
    creada = await _institucion(cliente)

    existente = (
        await cliente.get(f"/api/v1/instituciones/ruc/{RUC_VALIDO_ESTACION}")
    ).json()
    assert existente["valido"] is True
    assert existente["institucion"]["id"] == creada["id"]
    assert existente["institucion"]["ruc"] == RUC_VALIDO_ESTACION

    libre = (
        await cliente.get(f"/api/v1/instituciones/ruc/{RUC_VALIDO_VECINA}")
    ).json()
    assert libre["valido"] is True
    assert libre["institucion"] is None

    con_digito_mal = await cliente.get("/api/v1/instituciones/ruc/20100104158")
    assert con_digito_mal.status_code == 200
    assert con_digito_mal.json()["valido"] is False
    assert con_digito_mal.json()["institucion"] is None

    malformado = await cliente.get("/api/v1/instituciones/ruc/12345")
    assert malformado.json()["valido"] is False
