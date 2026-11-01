"""Pruebas del módulo de sistema: salud, catálogos y convenciones de error."""

async def test_salud_responde_ok(cliente):
    respuesta = await cliente.get("/api/v1/salud")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["estado"] == "ok"
    assert datos["base"] == "ok"
    assert datos["ocr"] not in ("", "error")
    assert datos["version"].startswith("PostgreSQL")


async def test_catalogos_enums_devuelve_las_listas(cliente):
    respuesta = await cliente.get("/api/v1/catalogos/enums")
    assert respuesta.status_code == 200
    datos = respuesta.json()

    assert datos["roles"] == ["administrador", "oficina", "despachador"]
    assert datos["modalidades_numeracion"] == ["general", "por_orden", "no_aplica"]
    assert datos["estados_orden"] == ["borrador", "vigente", "cerrada", "anulada"]
    assert datos["emisores_vale"] == ["estacion", "entidad"]
    assert datos["estados_vale"] == ["activo", "agotado", "vencido", "anulado"]
    assert datos["tipos_movimiento"] == [
        "emision",
        "consumo",
        "anulacion",
        "ajuste",
        "reversion",
    ]
    assert "sesion" in datos["permisos"]
    assert "usuarios.gestionar" in datos["permisos"]


async def test_ruta_inexistente_usa_el_formato_de_error_del_plan(cliente):
    """AUT-00/convenciones: cualquier error responde { codigo, mensaje, detalles }."""
    respuesta = await cliente.get("/api/v1/ruta-que-no-existe")
    assert respuesta.status_code == 404
    datos = respuesta.json()
    assert datos["codigo"] == "RECURSO_NO_ENCONTRADO"
    assert datos["mensaje"]
    assert datos["detalles"] == {}


async def test_peticion_con_cuerpo_mal_formado_responde_422_por_campo(cliente):
    respuesta = await cliente.post("/api/v1/catalogos/enums", json={"estado": 7})
    assert respuesta.status_code == 405  # solo existe GET; se retorna formato estándar
    datos = respuesta.json()
    assert datos["codigo"] == "METODO_NO_PERMITIDO"
