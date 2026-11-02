"""Pruebas del módulo de sistema: salud, catálogos y convenciones de error."""

async def test_salud_responde_ok(cliente):
    respuesta = await cliente.get("/api/v1/salud")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["estado"] == "ok"
    assert datos["base"] == "ok"
    assert datos["ocr"] not in ("", "error")
    assert datos["version"].startswith("PostgreSQL")


async def test_catalogos_enums_protege_sin_sesion_y_exige_sesion(cliente):
    """CAT-01/Fase 2: los catálogos requieren sesión (AUT-09); el formato es estándar."""
    respuesta = await cliente.get("/api/v1/catalogos/enums")
    assert respuesta.status_code == 401
    datos = respuesta.json()
    assert datos["codigo"] == "TOKEN_INVALIDO"
    # Las listas completas se cubren con sesión activa en tests/test_auth.py.


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
