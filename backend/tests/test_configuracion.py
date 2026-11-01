"""Pruebas de Fase 4: parámetros CFG-01, datos de estación y logo CFG-02.

Cubre: rango de parámetros (422 con el campo marcado), cambio de
`login_intentos_max` que rige sin reiniciar, permisos `config.gestionar` y
`estacion.ver` por rol, ficha de la estación (RUC con 11 dígitos) y subida
de logo inválida (contenido y tamaño) y su lectura final.
"""

import base64
import json
import os

from tests.test_combustibles import _admin  # reuso del arnés de la Fase 4
from tests.test_usuarios import _crear_usuario, _iniciar_sesion, _migrador

# PNG 1x1 real (firma completa), la unidad mínima que el endpoint debe aceptar.
PNG_MINIMO = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQ"
    "AAAABJRU5ErkJggg=="
)


def _logo_png_valido() -> bytes:
    return PNG_MINIMO


async def test_parametros_listan_con_contrato_de_validacion(cliente):
    await _admin(cliente)
    lista = await cliente.get("/api/v1/configuracion/parametros")
    assert lista.status_code == 200
    por_clave = {p["clave"]: p for p in lista.json()["items"]}

    for clave in (
        "ocr_umbral_confianza",
        "archivo_max_mb",
        "vale_formato_numeracion_estacion",
        "sesion_inactividad_min",
        "login_intentos_max",
    ):
        assert clave in por_clave, clave
        item = por_clave[clave]
        assert item["descripcion"], f"{clave} sin descripcion"
        assert item["defecto"] != ""

    # El único parámetro que admite vacío tiene defecto '' por diseño.
    assert por_clave["vale_vigencia_dias"]["defecto"] == ""
    assert por_clave["vale_vigencia_dias"]["tipo"] == "entero"

    assert por_clave["sesion_inactividad_min"] == {
        "clave": "sesion_inactividad_min",
        "valor": "60",
        "tipo": "entero",
        "defecto": "60",
        "minimo": 5,
        "maximo": 1440,
        "descripcion": "Minutos de inactividad antes de que la sesión expire (AUT-08).",
    }


async def test_parametros_fuera_de_rango_rechazados_con_detalle(cliente):
    await _admin(cliente)
    fuera = await cliente.put(
        "/api/v1/configuracion/parametros",
        json={"valores": {"login_intentos_max": "0", "sesion_inactividad_min": "9999"}},
    )
    assert fuera.status_code == 422
    assert fuera.json()["codigo"] == "VALIDACION_INVALIDA"
    assert "login_intentos_max" in str(fuera.json()["detalles"])

    desconocido = await cliente.put(
        "/api/v1/configuracion/parametros",
        json={"valores": {"parametro_inventado": "1"}},
    )
    assert desconocido.status_code == 422

    mi_decimal = await cliente.put(
        "/api/v1/configuracion/parametros",
        json={"valores": {"ocr_umbral_confianza": "1.5"}},
    )
    assert mi_decimal.status_code == 422

    mi_formato = await cliente.put(
        "/api/v1/configuracion/parametros",
        json={"valores": {"vale_formato_numeracion_estacion": "no-trae-marcas"}},
    )
    assert mi_formato.status_code == 422


async def test_cambio_de_parametro_rige_sin_reinicio(cliente):
    """El plan exige: login_intentos_max = 3 cambia el bloqueo sin reiniciar."""
    await _admin(cliente, "cfgadmin@pruebas.pe")
    await _crear_usuario("bloqueado@pruebas.pe", rol="despachador")

    guardado = await cliente.put(
        "/api/v1/configuracion/parametros",
        json={"valores": {"login_intentos_max": "3"}},
    )
    assert guardado.status_code == 200, guardado.text
    assert guardado.json()["valores"]["login_intentos_max"] == "3"

    # Bearer aparte: los intentos van sin sesión, como un atacante real.
    bearer_admin = cliente.headers["Authorization"]
    cliente.headers.pop("Authorization", None)
    cliente.cookies.clear()
    for _ in range(3):
        erroneo = await cliente.post(
            "/api/v1/auth/login",
            json={
                "correo": "bloqueado@pruebas.pe",
                "password": "clave-muy-errada",
                "recaptcha_token": "ia8d_token_aprobado",
            },
        )
        assert erroneo.status_code in (401, 400), erroneo.text
        if erroneo.status_code == 400:
            break
    bloqueo = await cliente.post(
        "/api/v1/auth/login",
        json={
            "correo": "bloqueado@pruebas.pe",
            "password": "clave-muy-errada",
            "recaptcha_token": "ia8d_token_aprobado",
        },
    )
    assert bloqueo.status_code == 400
    assert bloqueo.json()["codigo"] == "CUENTA_BLOQUEADA"

    # La tabla `parametros` no se vacía entre pruebas: con la sesión del
    # administrador se restituye el defecto para el resto de la batería.
    cliente.headers["Authorization"] = bearer_admin
    restaurado = await cliente.put(
        "/api/v1/configuracion/parametros",
        json={"valores": {"login_intentos_max": "5"}},
    )
    assert restaurado.status_code == 200

    # El cambio queda auditado y persistente: hubo dos eventos por parámetro.
    async with _migrador() as conexion:
        filas = await conexion.fetch(
            """
            SELECT despues FROM auditoria
            WHERE accion = 'actualizar_parametro' AND entidad_id = 'login_intentos_max'
            ORDER BY id
            """
        )
    valores = [json.loads(str(fila["despues"]))["valor"] for fila in filas]
    assert "3" in valores and "5" in valores


# ---------------------------------------------------------------------------
# CFG-02: datos de la estación
# ---------------------------------------------------------------------------


async def test_oficina_ve_estacion_pero_no_configura(cliente):
    await _admin(cliente, "cfgestacion@pruebas.pe")

    # La ficha la crea el administrador: después la lee oficina para imprimir.
    await cliente.put(
        "/api/v1/configuracion/estacion",
        json={"nombre": "Estación San José", "ruc": "20100047218"},
    )

    await _crear_usuario("cfgofi@pruebas.pe", rol="oficina")
    sesion_ofi = await _iniciar_sesion(cliente, "cfgofi@pruebas.pe")
    cliente.headers["Authorization"] = f"Bearer {sesion_ofi['access_token']}"

    lectura = await cliente.get("/api/v1/configuracion/estacion")
    assert lectura.status_code == 200
    assert lectura.json()["nombre"] == "Estación San José"

    ficha = await cliente.put(
        "/api/v1/configuracion/estacion",
        json={"nombre": "Estación San José", "ruc": "20100047218"},
    )
    assert ficha.status_code == 403
    assert ficha.json()["codigo"] == "SIN_PERMISO"


async def test_estacion_sin_registrar_da_404(cliente):
    await _admin(cliente, "cfgsin@pruebas.pe")
    falta = await cliente.get("/api/v1/configuracion/estacion")
    assert falta.status_code == 404


async def test_estacion_crear_y_actualizar_con_validaciones(cliente):
    await _admin(cliente, "cfgficha@pruebas.pe")

    ruc_mal = await cliente.put(
        "/api/v1/configuracion/estacion",
        json={"nombre": "Estación San José", "ruc": "12345"},
    )
    assert ruc_mal.status_code == 422

    alta = await cliente.put(
        "/api/v1/configuracion/estacion",
        json={
            "nombre": "Estación de Servicio San José",
            "ruc": "20100047218",
            "direccion": "Av.Principal 123, Lima",
            "telefono": "(01) 2345678",
            "correo": "contacto@sanjose.pe",
        },
    )
    assert alta.status_code == 200, alta.text
    assert alta.json()["ruc"] == "20100047218"

    actualizada = await cliente.put(
        "/api/v1/configuracion/estacion",
        json={"nombre": "Estación San José Sur", "ruc": "20100047219"},
    )
    assert actualizada.status_code == 200
    # Ficha única: sigue siendo la misma fila.
    ficha = (await cliente.get("/api/v1/configuracion/estacion")).json()
    assert ficha["nombre"] == "Estación San José Sur"


# ---------------------------------------------------------------------------
# CFG-02: logo (PNG/JPG por contenido, hasta 1 MB)
# ---------------------------------------------------------------------------


async def test_logo_invalido_rechazado(cliente):
    await _admin(cliente, "cfglogo@pruebas.pe")

    vacio = await cliente.post("/api/v1/configuracion/estacion/logo", files={})
    assert vacio.status_code in (422, 400)

    impostor = await cliente.post(
        "/api/v1/configuracion/estacion/logo",
        files={"archivo": ("logo.png", b"esto no es un png", "image/png")},
    )
    assert impostor.status_code == 422
    assert impostor.json()["codigo"] == "FORMATO_INVALIDO"

    # Content-type honesto pero contenido con firma de PDF: se detecta.
    pdf_camuflado = await cliente.post(
        "/api/v1/configuracion/estacion/logo",
        files={"archivo": ("logo.jpg", b"%PDF-1.4 camuflado", "image/jpeg")},
    )
    assert pdf_camuflado.status_code == 422


async def test_logo_demasiado_grande_rechazado(cliente):
    await _admin(cliente, "cfggrande@pruebas.pe")
    bytes_png = _logo_png_valido()
    cuerpo = bytes_png + b"\x00" * (1_048_576)  # padding > 1 MB mantiene la firma
    respuesta = await cliente.post(
        "/api/v1/configuracion/estacion/logo",
        files={"archivo": ("logo.png", cuerpo, "image/png")},
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "ARCHIVO_MUY_GRANDE"


async def test_logo_valido_se_guarda_y_se_lee(cliente):
    await _admin(cliente, "cfglogo2@pruebas.pe")
    await _crear_usuario("cfgofi2@pruebas.pe", rol="oficina")

    subida = await cliente.post(
        "/api/v1/configuracion/estacion/logo",
        files={"archivo": ("logo.png", _logo_png_valido(), "image/png")},
    )
    assert subida.status_code == 201, subida.text
    assert subida.json()["media_type"] == "image/png"

    # El fichero vive en `almacenamiento/estacion/`.
    from app.config import obtener_settings as ajustes

    ruta = ajustes().almacenamiento_dir / "estacion"
    assert (ruta / "logo.png").exists()

    # La lectura queda a cargo de `estacion.ver` (oficina la usa para imprimir).
    sesion_ofi = await _iniciar_sesion(cliente, "cfgofi2@pruebas.pe")
    cliente.headers["Authorization"] = f"Bearer {sesion_ofi['access_token']}"
    descarga = await cliente.get("/api/v1/configuracion/estacion/logo")
    assert descarga.status_code == 200
    assert descarga.headers["content-type"].startswith("image/png")
    assert descarga.headers["x-content-type-options"] == "nosniff"

    # La ficha refleja el logo aunque se creó en la subida.
    ficha = (await cliente.get("/api/v1/configuracion/estacion")).json()
    assert ficha["logo_path"] == "logo.png"

    os.remove(ruta / "logo.png")  # sin rastros entre corridas
