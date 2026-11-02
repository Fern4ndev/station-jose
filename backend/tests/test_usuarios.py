"""Pruebas de Fase 3: usuarios, roles y la autorización de toda la API (USR-01..07).

1. La prueba global de autorización recorre `app.routes` y falla si algún
   endpoint, salvo los públicos declarados en el plan, no exige una sesión
   (dependencia `usuario_actual*`). Cualquier endpoint nuevo sin protección
   rompe la suite antes de llegar a producción.
2. Permisos por rol en `/usuarios` (`usuarios.gestionar` solo administrador).
3. Casos de uso: alta con contraseña temporal (must_change TRUE), listado con
   búsqueda/filtro/paginación, edición con auditoría antes/después, correo
   duplicado, protección del último administrador y restablecimiento que
   cierra sesiones y obliga al cambio de contraseña.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from fastapi.routing import APIRoute

from app.config import obtener_settings
from app.core import seguridad
from app.core.dominio import ROLES  # referencia del catálogo cerrado

CLAVE_TEMPORAL = "ClaveDePrueba1"

RUTAS_PUBLICAS = frozenset(
    {
        "/api/v1/salud",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/recuperar",
        "/api/v1/auth/restablecer",
    }
)
RUTAS_DOCUMENTACION = frozenset(
    {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
)


async def _conexion_migrador() -> AsyncIterator[asyncpg.Connection]:
    """Conexión con el rol dueño del esquema para consultas de verificación."""
    dsn = a_dsn(obtener_settings().migrador_url)
    conexional = await asyncpg.connect(dsn)
    try:
        yield conexional
    finally:
        await conexional.close()


@asynccontextmanager
async def _migrador():
    """Context manager equivalente para usos puntuales."""
    async for conexion in _conexion_migrador():
        yield conexion


async def _crear_usuario(
    correo: str,
    *,
    rol: str = "oficina",
    clave: str = CLAVE_TEMPORAL,
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


async def _iniciar_sesion(cliente, correo: str, clave: str = CLAVE_TEMPORAL) -> dict:
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={
            "correo": correo,
            "password": clave,
            "recaptcha_token": "ia8d_token_aprobado",
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


# ---------------------------------------------------------------------------
# Prueba global de autorización (plan Fase 3)
# ---------------------------------------------------------------------------

from app import dependencies  # noqa: E402
from app.db.migrar import a_dsn  # noqa: E402
from app.main import app as aplicacion  # noqa: E402

RUTAS_SIN_PROTECCION = RUTAS_PUBLICAS | RUTAS_DOCUMENTACION
DEPENDENCIAS_DE_SESION = {
    dependencies.usuario_actual,
    dependencies.usuario_actual_autorizado,
}


def _rutas_de_api():
    """Toda APIRoute montada, con su ruta completa (prefijo v1 incluido)."""
    prefijo = obtener_settings().api_v1_prefix
    for ruta in aplicacion.routes:
        if isinstance(ruta, APIRoute):
            yield prefijo + ruta.path, ruta


def _dependencias_recursivas(ruta) -> set:
    """Llamadas del endpoint y de todas sus dependencias anidadas."""
    pila = [ruta.dependant]
    hallazgos: set = set()
    while pila:
        dependencia = pila.pop()
        hallazgos.add(dependencia.call)
        pila.extend(dependencia.dependencies)
    return hallazgos


async def test_toda_ruta_no_publica_exige_sesion():
    """Ningún endpoint v1 queda sin su dependencia de sesión ni estar público."""
    sin_proteccion = []
    for ruta_completa, ruta in _rutas_de_api():
        if ruta_completa in RUTAS_SIN_PROTECCION:
            continue
        protegida = _dependencias_recursivas(ruta) & DEPENDENCIAS_DE_SESION
        if not protegida:
            sin_proteccion.append(ruta_completa)
    assert sin_proteccion == [], (
        "Estas rutas exigen una dependencia de sesión: " + ", ".join(sin_proteccion)
    )


# ---------------------------------------------------------------------------
# Permisos por rol (sección 4.1 del plan)
# ---------------------------------------------------------------------------


async def test_solo_administrador_gestiona_usuarios(cliente):
    await _crear_usuario("admin@pruebas.pe", rol="administrador", nombre="Yo Admin")
    await _crear_usuario("ofi@pruebas.pe", rol="oficina", nombre="Yo Oficina")
    await _crear_usuario("desp@pruebas.pe", rol="despachador", nombre="Yo Despacho")

    sesion_admin = await _iniciar_sesion(cliente, "admin@pruebas.pe")
    cliente.headers["Authorization"] = f"Bearer {sesion_admin['access_token']}"
    permitido = await cliente.get("/api/v1/usuarios")
    assert permitido.status_code == 200
    assert permitido.json()["total"] == 3

    for correo in ("ofi@pruebas.pe", "desp@pruebas.pe"):
        sesion_otro = await _iniciar_sesion(cliente, correo)
        cliente.headers["Authorization"] = f"Bearer {sesion_otro['access_token']}"
        denegado = await cliente.get("/api/v1/usuarios")
        assert denegado.status_code == 403, correo
        assert denegado.json()["codigo"] == "SIN_PERMISO"


async def test_post_usuarios_sin_permiso_rechaza(cliente):
    await _crear_usuario("ofi2@pruebas.pe", rol="oficina")
    sesion = await _iniciar_sesion(cliente, "ofi2@pruebas.pe")
    cliente.headers["Authorization"] = f"Bearer {sesion['access_token']}"
    alta = await cliente.post(
        "/api/v1/usuarios",
        json={"nombre": "No Debe", "correo": "nodebe@pruebas.pe", "rol": "oficina"},
    )
    assert alta.status_code == 403
    assert alta.json()["codigo"] == "SIN_PERMISO"


# ---------------------------------------------------------------------------
# Alta (USR-01), listado (USR-02) y detalle
# ---------------------------------------------------------------------------


async def test_alta_entrega_clave_temporal_y_exige_cambio(cliente):
    await _crear_usuario("creador@pruebas.pe", rol="administrador")
    sesion = await _iniciar_sesion(cliente, "creador@pruebas.pe")
    cliente.headers["Authorization"] = f"Bearer {sesion['access_token']}"

    alta = await cliente.post(
        "/api/v1/usuarios",
        json={
            "nombre": "Nuevo Operador",
            "correo": "nuevo@pruebas.pe",
            "rol": "despachador",
        },
    )
    assert alta.status_code == 201, alta.text
    datos = alta.json()
    assert len(datos["password_temporal"]) >= 8
    assert datos["rol"] == "despachador"

    # El usuario creado inicia sesión y solo puede cambiar su contraseña (AUT-06).
    cliente.headers["Authorization"] = ""
    cliente.cookies.clear()
    sesion_nueva = await _iniciar_sesion(
        cliente, "nuevo@pruebas.pe", datos["password_temporal"]
    )
    assert sesion_nueva["must_change_password"] is True
    cliente.headers["Authorization"] = f"Bearer {sesion_nueva['access_token']}"
    bloqueado = await cliente.get("/api/v1/usuarios")
    assert bloqueado.status_code == 403
    assert bloqueado.json()["codigo"] == "CAMBIO_PASSWORD_OBLIGATORIO"


async def test_alta_devuelve_correo_duplicado_y_audita(cliente):
    await _crear_usuario("duplicador@pruebas.pe", rol="administrador")
    await _crear_usuario("repetido@pruebas.pe", rol="oficina")
    sesion = await _iniciar_sesion(cliente, "duplicador@pruebas.pe")
    cliente.headers["Authorization"] = f"Bearer {sesion['access_token']}"

    alta = await cliente.post(
        "/api/v1/usuarios",
        json={
            "nombre": "Repetido",
            "correo": "Repetido@pruebas.pe",
            "rol": "despachador",
        },
    )
    assert alta.status_code == 409
    assert alta.json()["codigo"] == "CORREO_DUPLICADO"

    crear_ok = await cliente.post(
        "/api/v1/usuarios",
        json={"nombre": "Una Mas", "correo": "unamas@pruebas.pe", "rol": "oficina"},
    )
    assert crear_ok.status_code == 201
    async with _migrador() as conexion:
        filas = await conexion.fetch(
            "SELECT despues FROM auditoria WHERE accion = 'crear_usuario'"
        )
    assert len(filas) == 1
    assert json.loads(str(filas[0]["despues"]))["correo"] == "unamas@pruebas.pe"


async def test_listado_busca_filtra_y_pagina(cliente):
    await _crear_usuario(
        "listador@pruebas.pe", rol="administrador", nombre="Z Todos Admin"
    )
    await _crear_usuario("n1@pruebas.pe", rol="oficina", nombre="Ana Nunez")
    await _crear_usuario("n2@pruebas.pe", rol="oficina", nombre="Ana Torres")
    await _crear_usuario("n3@pruebas.pe", rol="despachador", nombre="Ana Despacho")

    sesion = await _iniciar_sesion(cliente, "listador@pruebas.pe")
    cliente.headers["Authorization"] = f"Bearer {sesion['access_token']}"

    por_nombre = await cliente.get("/api/v1/usuarios", params={"q": "ana"})
    assert por_nombre.status_code == 200
    datos = por_nombre.json()
    assert datos["total"] == 3
    assert [u["nombre"] for u in datos["items"]][:2] == ["Ana Despacho", "Ana Nunez"]

    por_correo = await cliente.get("/api/v1/usuarios", params={"q": "n3@"})
    assert por_correo.json()["total"] == 1

    por_rol = await cliente.get("/api/v1/usuarios", params={"rol": "oficina"})
    assert por_rol.json()["total"] == 2

    paginado = await cliente.get(
        "/api/v1/usuarios", params={"pagina": 2, "por_pagina": 2}
    )
    assert paginado.json()["pagina"] == 2
    assert paginado.json()["total"] == 4

    rol_invalido = await cliente.get("/api/v1/usuarios", params={"rol": "gerente"})
    assert rol_invalido.status_code == 422
    assert rol_invalido.json()["codigo"] == "VALIDACION_INVALIDA"


async def test_detalle_404_formato_estandar(cliente):
    await _crear_usuario("detalle404@pruebas.pe", rol="administrador")
    sesion = await _iniciar_sesion(cliente, "detalle404@pruebas.pe")
    cliente.headers["Authorization"] = f"Bearer {sesion['access_token']}"

    respuesta = await cliente.get("/api/v1/usuarios/99999")
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "RECURSO_NO_ENCONTRADO"


# ---------------------------------------------------------------------------
# Edición (USR-03/04) con auditoría antes/después
# ---------------------------------------------------------------------------


async def test_editar_nombre_y_auditoria_antes_despues(cliente):
    await _crear_usuario("editor@pruebas.pe", rol="administrador")
    id_edicion = await _crear_usuario(
        "victima@pruebas.pe", rol="oficina", nombre="Nombre Viejo"
    )
    sesion = await _iniciar_sesion(cliente, "editor@pruebas.pe")
    cliente.headers["Authorization"] = f"Bearer {sesion['access_token']}"

    respuesta = await cliente.patch(
        f"/api/v1/usuarios/{id_edicion}", json={"nombre": "Nombre Nuevo"}
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["nombre"] == "Nombre Nuevo"
    assert datos["rol"] == "oficina"

    async with _migrador() as conexion:
        fila = await conexion.fetchrow(
            "SELECT antes, despues FROM auditoria WHERE accion = 'editar_usuario'"
        )
    assert json.loads(str(fila["antes"])) == {"nombre": "Nombre Viejo"}
    assert json.loads(str(fila["despues"])) == {"nombre": "Nombre Nuevo"}


async def test_editar_correo_duplicado_rechaza_y_sin_cambios_no_audita(cliente):
    await _crear_usuario("editorx@pruebas.pe", rol="administrador")
    await _crear_usuario("tomada@pruebas.pe", rol="oficina")
    id_edicion = await _crear_usuario("paraeditarx@pruebas.pe", rol="oficina")
    sesion = await _iniciar_sesion(cliente, "editorx@pruebas.pe")
    cliente.headers["Authorization"] = f"Bearer {sesion['access_token']}"

    respuesta = await cliente.patch(
        f"/api/v1/usuarios/{id_edicion}", json={"correo": "tomada@pruebas.pe"}
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "CORREO_DUPLICADO"

    # La edición sin cambios no genera auditoría vacía.
    sin_cambios = await cliente.patch(
        f"/api/v1/usuarios/{id_edicion}", json={"correo": "paraeditarx@pruebas.pe"}
    )
    assert sin_cambios.status_code == 200
    async with _migrador() as conexion:
        total = await conexion.fetchval(
            "SELECT count(*) FROM auditoria WHERE accion = 'editar_usuario'"
        )
    assert int(total) == 0


async def test_edicion_rol_invalido_rechaza(cliente):
    await _crear_usuario("editorrol@pruebas.pe", rol="administrador")
    id_edicion = await _crear_usuario("paraeditarrol@pruebas.pe", rol="oficina")
    sesion = await _iniciar_sesion(cliente, "editorrol@pruebas.pe")
    cliente.headers["Authorization"] = f"Bearer {sesion['access_token']}"

    respuesta = await cliente.patch(
        f"/api/v1/usuarios/{id_edicion}", json={"rol": "gerente"}
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "VALIDACION_INVALIDA"
    assert "gerente" not in ROLES


# ---------------------------------------------------------------------------
# Protección del último administrador (USR-07)
# ---------------------------------------------------------------------------


async def test_no_se_quita_el_rol_al_unico_administrador(cliente):
    await _crear_usuario("unico@pruebas.pe", rol="administrador", nombre="Único Admin")
    sesion = await _iniciar_sesion(cliente, "unico@pruebas.pe")
    cliente.headers["Authorization"] = f"Bearer {sesion['access_token']}"

    rechazo = await cliente.patch("/api/v1/usuarios/1", json={"rol": "oficina"})
    assert rechazo.status_code == 409
    cuerpo = rechazo.json()
    assert cuerpo["codigo"] == "ULTIMO_ADMINISTRADOR"
    assert "administrador" in cuerpo["mensaje"].lower()

    # El rol no cambió en la base.
    async with _migrador() as conexion:
        rol = await conexion.fetchval("SELECT role::text FROM app_users WHERE id = 1")
    assert rol == "administrador"


async def test_con_segundo_administrador_se_puede_reducir_al_primero(cliente):
    id_unico = await _crear_usuario(
        "primero@pruebas.pe", rol="administrador", nombre="Primero"
    )
    await _crear_usuario("segundo@pruebas.pe", rol="administrador", nombre="Segundo")
    sesion = await _iniciar_sesion(cliente, "segundo@pruebas.pe")
    cliente.headers["Authorization"] = f"Bearer {sesion['access_token']}"

    cambio = await cliente.patch(f"/api/v1/usuarios/{id_unico}", json={"rol": "oficina"})
    assert cambio.status_code == 200
    assert cambio.json()["rol"] == "oficina"


# ---------------------------------------------------------------------------
# Restablecimiento de contraseña (USR-06)
# ---------------------------------------------------------------------------


async def test_restablecer_cierra_sesiones_y_obliga_al_cambio(cliente):
    await _crear_usuario("restablecedor@pruebas.pe", rol="administrador")
    id_afectado = await _crear_usuario("afectado@pruebas.pe", rol="oficina")
    sesion_admin = await _iniciar_sesion(cliente, "restablecedor@pruebas.pe")
    cliente.headers["Authorization"] = f"Bearer {sesion_admin['access_token']}"

    # El afectado tiene su sesión abierta antes del restablecimiento.
    cliente.cookies.clear()
    cliente.headers["Authorization"] = ""
    sesion_vieja = await _iniciar_sesion(cliente, "afectado@pruebas.pe")
    cliente.headers["Authorization"] = f"Bearer {sesion_vieja['access_token']}"
    assert (await cliente.get("/api/v1/auth/yo")).status_code == 200

    # El administrador restablece con su propia sesión (Bearer, sin CSRF).
    cliente.headers["Authorization"] = f"Bearer {sesion_admin['access_token']}"
    respuesta = await cliente.post(
        f"/api/v1/usuarios/{id_afectado}/restablecer-password"
    )
    assert respuesta.status_code == 200, respuesta.text
    nueva_temporal = respuesta.json()["password_temporal"]

    # La sesión previa del afectado quedó revocada (401 TOKEN_INVALIDO).
    cliente.headers["Authorization"] = f"Bearer {sesion_vieja['access_token']}"
    vieja = await cliente.get("/api/v1/auth/yo")
    assert vieja.status_code == 401
    assert vieja.json()["codigo"] == "TOKEN_INVALIDO"

    # En la base: cambio obligatorio activo y sesiones revocadas.
    async with _migrador() as conexion:
        obligatorio = await conexion.fetchval(
            "SELECT must_change_password FROM app_users WHERE id = $1", id_afectado
        )
        revocadas = await conexion.fetchval(
            """
            SELECT count(*) FROM refresh_tokens
            WHERE app_user_id = $1 AND revocado_en IS NOT NULL
            """,
            id_afectado,
        )
    assert obligatorio is True
    assert int(revocadas) >= 1

    # La contraseña temporal funciona y sigue pendiente el cambio obligatorio.
    cliente.headers["Authorization"] = ""
    sesion_nueva = await _iniciar_sesion(cliente, "afectado@pruebas.pe", nueva_temporal)
    assert sesion_nueva["must_change_password"] is True

    # La acción queda auditada.
    async with _migrador() as conexion:
        total = await conexion.fetchval(
            "SELECT count(*) FROM auditoria WHERE accion = 'restablecer_password_admin'"
        )
    assert int(total) == 1


# ---------------------------------------------------------------------------
# Convenciones del módulo
# ---------------------------------------------------------------------------


async def test_paginacion_invalida_rechaza(cliente):
    await _crear_usuario("paginador@pruebas.pe", rol="administrador")
    sesion = await _iniciar_sesion(cliente, "paginador@pruebas.pe")
    cliente.headers["Authorization"] = f"Bearer {sesion['access_token']}"

    respuesta = await cliente.get("/api/v1/usuarios", params={"pagina": 0})
    assert respuesta.status_code == 422
