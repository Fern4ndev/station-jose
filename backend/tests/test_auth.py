"""Pruebas de Fase 2: sesión, contraseñas y auditoría (AUT-01 a AUT-10).

La batería sobrevive sin cuenta de reCAPTCHA ni SMTP: en desarrollo el
verificador rechaza solo los tokens de prueba declarados y el enlace de
recuperación se imprime en consola (capsys).
"""

import asyncio
import re
from datetime import timedelta

import asyncpg

from app.config import obtener_settings
from app.core import seguridad, tiempo
from app.db.migrar import a_dsn


async def _crear_usuario(
    correo: str,
    *,
    rol: str = "oficina",
    clave: str = "ClaveDePrueba1",
    debe_cambiar: bool | None = False,
    nombre: str = "Usuario de Prueba",
) -> int:
    """Inserta un usuario directamente en PostgreSQL y devuelve su id."""
    ajustes = obtener_settings()
    conexion = await asyncpg.connect(a_dsn(ajustes.migrador_url))
    try:
        return int(
            await conexion.fetchval(
                """
                INSERT INTO app_users
                    (full_name, email, password_hash, role, must_change_password)
                VALUES ($1, $2, $3, $4::user_role, $5)
                RETURNING id
                """,
                nombre,
                correo,
                await asyncio.to_thread(seguridad.hashear_password, clave),
                rol,
                debe_cambiar,
            )
        )
    finally:
        await conexion.close()


def _cabecera_csrf(cliente) -> dict[str, str]:
    """Origen y token CSRF de la sesión de cookies del cliente."""
    token = cliente.cookies.get("csrf_token", "")
    return {"X-CSRF-Token": token, "Origin": "http://pruebas.local"}


async def _iniciar_sesion(cliente, correo: str, clave: str):
    return await cliente.post(
        "/api/v1/auth/login",
        json={
            "correo": correo,
            "password": clave,
            "recaptcha_token": "ia8d_token_aprobado",
        },
    )


async def _actualizar_sesiones(sql: str, *parametros) -> None:
    ajustes = obtener_settings()
    conexion = await asyncpg.connect(a_dsn(ajustes.migrador_url))
    try:
        await conexion.execute(sql, *parametros)
    finally:
        await conexion.close()


# ---------------------------------------------------------------------------
# login (AUT-01/04)
# ---------------------------------------------------------------------------


async def test_login_correcto_entrega_tokens_cookie_y_auditoria(cliente):
    await _crear_usuario("ok@pruebas.pe", rol="oficina")
    respuesta = await _iniciar_sesion(cliente, "OK@pruebas.pe", "ClaveDePrueba1")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["token_type"] == "Bearer"
    assert datos["usuario"]["rol"] == "oficina"
    assert datos["must_change_password"] is False
    assert "refresh_token" in cliente.cookies
    assert "csrf_token" in cliente.cookies

    sesiones_bd = obtener_settings()
    conexion = await asyncpg.connect(a_dsn(sesiones_bd.migrador_url))
    try:
        auditoria_login = await conexion.fetchval(
            "SELECT count(*) FROM auditoria WHERE accion = 'iniciar_sesion'"
        )
        acceso = await conexion.fetchval(
            "SELECT ultimo_acceso_en IS NOT NULL FROM app_users WHERE id = 1"
        )
    finally:
        await conexion.close()
    assert int(auditoria_login) == 1
    assert acceso is True


async def test_login_con_correo_inexistente_y_clave_erronea_responden_igual(cliente):
    sin_correo = await _iniciar_sesion(cliente, "nadie@pruebas.pe", "Erronea1")
    await _crear_usuario("alguien@pruebas.pe")
    con_clave_mala = await _iniciar_sesion(cliente, "alguien@pruebas.pe", "Erronea1")
    assert sin_correo.status_code == con_clave_mala.status_code == 401
    cuerpo_sin = sin_correo.json()
    cuerpo_con = con_clave_mala.json()
    assert cuerpo_sin["codigo"] == cuerpo_con["codigo"] == "CREDENCIALES_INVALIDAS"
    assert cuerpo_sin["mensaje"] == cuerpo_con["mensaje"]


async def test_login_con_recaptcha_invalido_o_score_bajo_rechaza(cliente):
    await _crear_usuario("rechazo@pruebas.pe")
    for token in ("recaptcha_invalido", "recaptcha_score_bajo"):
        respuesta = await cliente.post(
            "/api/v1/auth/login",
            json={
                "correo": "rechazo@pruebas.pe",
                "password": "ClaveDePrueba1",
                "recaptcha_token": token,
            },
        )
        assert respuesta.status_code == 401, token
        assert respuesta.json()["codigo"] == "CREDENCIALES_INVALIDAS"


async def test_login_se_bloquea_tras_cinco_intentos_fallidos(cliente):
    await _crear_usuario("bloqueo@pruebas.pe")
    for _ in range(5):
        respuesta = await _iniciar_sesion(cliente, "bloqueo@pruebas.pe", "Erronea1")
        assert respuesta.status_code == 401
    sexto = await _iniciar_sesion(cliente, "bloqueo@pruebas.pe", "ClaveDePrueba1")
    assert sexto.status_code == 400
    cuerpo = sexto.json()
    assert cuerpo["codigo"] == "CUENTA_BLOQUEADA"
    assert cuerpo["detalles"]["minutos_espera"] >= 1


# ---------------------------------------------------------------------------
# UsuarioActual y cambio de contraseña obligatorio (AUT-06/07/08)
# ---------------------------------------------------------------------------


async def test_cambio_obligatorio_restringe_endpoints_que_no_son_de_sesion(cliente):
    await _crear_usuario("cambio@pruebas.pe", rol="oficina", debe_cambiar=True)
    respuesta = await _iniciar_sesion(cliente, "cambio@pruebas.pe", "ClaveDePrueba1")
    assert respuesta.json()["must_change_password"] is True
    cliente.headers["Authorization"] = f"Bearer {respuesta.json()['access_token']}"

    yo = await cliente.get("/api/v1/auth/yo")
    assert yo.status_code == 200
    catalogos_res = await cliente.get("/api/v1/catalogos/enums")
    assert catalogos_res.status_code == 403
    assert catalogos_res.json()["codigo"] == "CAMBIO_PASSWORD_OBLIGATORIO"


async def test_cambio_password_informa_correcto_y_desbloquea_la_sesion(cliente):
    await _crear_usuario("cambiox@pruebas.pe", rol="oficina", debe_cambiar=True)
    iniciar = await _iniciar_sesion(cliente, "cambiox@pruebas.pe", "ClaveDePrueba1")
    cuerpo = iniciar.json()
    assert cuerpo["must_change_password"] is True
    cliente.headers["Authorization"] = f"Bearer {cuerpo['access_token']}"

    cambio = await cliente.post(
        "/api/v1/auth/cambiar-password",
        json={"password_actual": "ClaveDePrueba1", "password_nueva": "NuevaClave99"},
    )
    assert cambio.status_code == 200
    datos = cambio.json()
    assert datos["must_change_password"] is False
    cliente.headers["Authorization"] = f"Bearer {datos['access_token']}"

    catalogos_res = await cliente.get("/api/v1/catalogos/enums")
    assert catalogos_res.status_code == 200


async def test_cambio_password_rechaza_actual_incorrecta_e_igual(cliente):
    await _crear_usuario("cambio2@pruebas.pe")
    iniciar = await _iniciar_sesion(cliente, "cambio2@pruebas.pe", "ClaveDePrueba1")
    cliente.headers["Authorization"] = f"Bearer {iniciar.json()['access_token']}"

    erronea = await cliente.post(
        "/api/v1/auth/cambiar-password",
        json={"password_actual": "Erronea1", "password_nueva": "NuevaClave99"},
    )
    assert erronea.status_code == 422
    assert erronea.json()["codigo"] == "VALIDACION_INVALIDA"

    igual = await cliente.post(
        "/api/v1/auth/cambiar-password",
        json={"password_actual": "ClaveDePrueba1", "password_nueva": "ClaveDePrueba1"},
    )
    assert igual.status_code == 422


async def test_yo_devuelve_permisos_del_rol(cliente):
    await _crear_usuario("oficina@pruebas.pe", rol="oficina")
    iniciar = await _iniciar_sesion(cliente, "oficina@pruebas.pe", "ClaveDePrueba1")
    cliente.headers["Authorization"] = f"Bearer {iniciar.json()['access_token']}"
    respuesta = await cliente.get("/api/v1/auth/yo")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["usuario"]["correo"] == "oficina@pruebas.pe"
    assert "sesion" in datos["permisos"]
    assert "vales.emitir" in datos["permisos"]
    assert "config.gestionar" not in datos["permisos"]


# ---------------------------------------------------------------------------
# Refresh rotatorio, CSRF, expiración y reutilización (AUT-10)
# ---------------------------------------------------------------------------


async def test_refresh_requiere_csrf(cliente):
    await _crear_usuario("csrf@pruebas.pe")
    iniciar = await _iniciar_sesion(cliente, "csrf@pruebas.pe", "ClaveDePrueba1")
    assert iniciar.status_code == 200
    sin_csrf = await cliente.post("/api/v1/auth/refresh")
    assert sin_csrf.status_code == 403
    assert sin_csrf.json()["codigo"] == "CSRF_INVALIDO"


async def test_refresh_rota_el_token_y_reutilizar_el_anterior_revoca(cliente):
    await _crear_usuario("rota@pruebas.pe")
    iniciar = await _iniciar_sesion(cliente, "rota@pruebas.pe", "ClaveDePrueba1")
    token_viejo = cliente.cookies.get("refresh_token", "")

    rotado = await cliente.post(
        "/api/v1/auth/refresh", headers=_cabecera_csrf(cliente)
    )
    assert rotado.status_code == 200
    token_nuevo = cliente.cookies.get("refresh_token", "")
    assert token_nuevo != token_viejo
    assert rotado.json()["access_token"] != iniciar.json()["access_token"]

    # Reutilizar el token antiguo señala la familia comprometida: revoca todo.
    cliente.cookies.set("refresh_token", token_viejo, domain="pruebas.local")
    reintento = await cliente.post(
        "/api/v1/auth/refresh", headers=_cabecera_csrf(cliente)
    )
    assert reintento.status_code == 401
    assert reintento.json()["codigo"] == "TOKEN_INVALIDO"

    # El token nuevo de esa familia también quedó revocado.
    cliente.cookies.set("refresh_token", token_nuevo, domain="pruebas.local")
    siguiente = await cliente.post(
        "/api/v1/auth/refresh", headers=_cabecera_csrf(cliente)
    )
    assert siguiente.status_code == 401


async def test_refresh_con_token_expirado_rechaza(cliente):
    await _crear_usuario("expira@pruebas.pe")
    iniciar = await _iniciar_sesion(cliente, "expira@pruebas.pe", "ClaveDePrueba1")
    assert iniciar.status_code == 200
    # El CHECK exige expira_en > emitido_en: se retroceden ambos instantes.
    await _actualizar_sesiones(
        """
        UPDATE refresh_tokens
        SET emitido_en = $1, expira_en = $2, ultimo_uso_en = $1
        """,
        tiempo.ahora() - timedelta(hours=2),
        tiempo.ahora() - timedelta(hours=1),
    )
    respuesta = await cliente.post(
        "/api/v1/auth/refresh", headers=_cabecera_csrf(cliente)
    )
    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "TOKEN_INVALIDO"


async def test_acceso_expira_por_inactividad_de_la_sesion(cliente):
    await _crear_usuario("inactivo@pruebas.pe")
    iniciar = await _iniciar_sesion(cliente, "inactivo@pruebas.pe", "ClaveDePrueba1")
    access = iniciar.json()["access_token"]
    cliente.headers["Authorization"] = f"Bearer {access}"
    assert (await cliente.get("/api/v1/auth/yo")).status_code == 200

    # Se retroceden la actividad y el `iat` referencia: la sesión quedó fría.
    hace = tiempo.ahora() - timedelta(minutes=61)
    await _actualizar_sesiones(
        "UPDATE refresh_tokens SET ultimo_uso_en = $1, emitido_en = $1", hace
    )
    expirada = await cliente.get("/api/v1/auth/yo")
    assert expirada.status_code == 401
    assert expirada.json()["codigo"] == "SESION_EXPIRADA"


# ---------------------------------------------------------------------------
# Logout y revocación (AUT-02)
# ---------------------------------------------------------------------------


async def test_logout_revoca_familia_y_access(cliente):
    await _crear_usuario("salida@pruebas.pe")
    iniciar = await _iniciar_sesion(cliente, "salida@pruebas.pe", "ClaveDePrueba1")
    access = iniciar.json()["access_token"]
    cliente.headers["Authorization"] = f"Bearer {access}"

    logout = await cliente.post("/api/v1/auth/logout", headers=_cabecera_csrf(cliente))
    assert logout.status_code == 200

    cliente.cookies.set("refresh_token", "", domain="pruebas.local")
    mas_refresh = await cliente.post(
        "/api/v1/auth/refresh", headers=_cabecera_csrf(cliente)
    )
    assert mas_refresh.status_code == 401
    mas_uso = await cliente.get("/api/v1/auth/yo")
    assert mas_uso.status_code == 401

    conexion = await asyncpg.connect(a_dsn(obtener_settings().migrador_url))
    try:
        revocadas = await conexion.fetchval(
            "SELECT count(*) FROM refresh_tokens WHERE revocado_en IS NOT NULL"
        )
    finally:
        await conexion.close()
    assert int(revocadas) >= 1


# ---------------------------------------------------------------------------
# Recuperación de contraseña (AUT-05)
# ---------------------------------------------------------------------------


async def test_recuperar_responde_igual_con_correo_inexistente(cliente, capsys):
    respuesta = await cliente.post(
        "/api/v1/auth/recuperar", json={"correo": "nadie@pruebas.pe"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["detalle"]
    # Sin el correo registrado no se imprime enlace alguno.
    assert "[recuperación]" not in capsys.readouterr().out


async def test_recuperar_emite_enlace_y_el_token_es_de_un_solo_uso(cliente, capsys):
    await _crear_usuario("recupera@pruebas.pe")
    respuesta = await cliente.post(
        "/api/v1/auth/recuperar", json={"correo": "recupera@pruebas.pe"}
    )
    assert respuesta.status_code == 200
    salida = capsys.readouterr().out
    hallazgo = re.search(r"token=([A-Za-z0-9_\-]+)", salida)
    assert hallazgo is not None
    token = hallazgo.group(1)

    restablecer = await cliente.post(
        "/api/v1/auth/restablecer",
        json={"token": token, "password_nueva": "Recuperada88"},
    )
    assert restablecer.status_code == 200

    nueva_sesion = await _iniciar_sesion(cliente, "recupera@pruebas.pe", "Recuperada88")
    assert nueva_sesion.status_code == 200

    repetido = await cliente.post(
        "/api/v1/auth/restablecer",
        json={"token": token, "password_nueva": "OtraClave77"},
    )
    assert repetido.status_code == 400
    assert repetido.json()["codigo"] == "TOKEN_INVALIDO"


async def test_recuperar_con_token_vencido_rechaza(cliente, capsys):
    await _crear_usuario("vence@pruebas.pe")
    await cliente.post("/api/v1/auth/recuperar", json={"correo": "vence@pruebas.pe"})
    hallazgo = re.search(r"token=([A-Za-z0-9_\-]+)", capsys.readouterr().out)
    assert hallazgo is not None
    # El CHECK exige expira_en > creado_en: se retroceden ambos instantes.
    await _actualizar_sesiones(
        """
        UPDATE tokens_recuperacion
        SET creado_en = $1, expira_en = $2
        """,
        tiempo.ahora() - timedelta(minutes=2),
        tiempo.ahora() - timedelta(minutes=1),
    )
    respuesta = await cliente.post(
        "/api/v1/auth/restablecer",
        json={"token": hallazgo.group(1), "password_nueva": "Recuperada88"},
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "TOKEN_INVALIDO"


# ---------------------------------------------------------------------------
# Convenciones generales
# ---------------------------------------------------------------------------


async def test_no_existe_ruta_de_registro(cliente):
    respuesta = await cliente.post(
        "/api/v1/auth/registro",
        json={"correo": "nuevo@pruebas.pe", "password": "AlgunaClave1"},
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "RECURSO_NO_ENCONTRADO"


async def test_acceso_sin_token_responde_formato_estandar(cliente):
    respuesta = await cliente.get("/api/v1/catalogos/enums")
    assert respuesta.status_code == 401
    datos = respuesta.json()
    assert datos["codigo"] == "TOKEN_INVALIDO"
    assert datos["detalles"] == {}
