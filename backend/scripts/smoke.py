"""Recorrido de verificación por fase: `python scripts/smoke.py --hasta N`.

Es acumulativo: cada fase agrega comprobaciones numeradas y al ejecutar con
`--hasta N` se repiten todas las de las fases anteriores. Salida `OK` o
`FALLA` por comprobación; el proceso termina con código 1 si alguna falla.

La Fase 2 necesita un administrador (creado con `python -m app.cli
crear-admin --nombre ... --correo ...`) y, después de su primer inicio,
la contraseña ya cambiada en las variables `SMOKE_CORREO` y `SMOKE_PASSWORD`
(por omisión actúa como el admin que se ejemplifica en el README).
El recorrido usa tokens de prueba (`recaptcha_token: smoke`), así que contra
una base de desarrollo con reCAPTCHA real se levanta el servidor sin
`RECAPTCHA_SECRET_KEY` para correr el smoke.
"""

import argparse
import asyncio
import datetime as _dt
import os
import sys
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import TypedDict

import httpx

COMPROBACION = Callable[[httpx.AsyncClient], Awaitable[str | None]]
"""Devuelve None si la comprobación pasa; una explicación si falla."""


class Fase(TypedDict):
    numero: int
    titulo: str
    comprobaciones: tuple[tuple[str, COMPROBACION], ...]


CORREO_SMOKE = os.environ.get("SMOKE_CORREO", "admin@ejemplo.pe")
CLAVE_SMOKE = os.environ.get("SMOKE_PASSWORD", "")


async def _salud_en_ok(cliente: httpx.AsyncClient) -> str | None:
    respuesta = await cliente.get("/api/v1/salud")
    if respuesta.status_code != 200:
        return f"GET /api/v1/salud devolvió {respuesta.status_code}."
    datos = respuesta.json()
    if datos.get("estado") != "ok":
        return f"El estado no es 'ok': {datos}"
    return None


async def _enums_protegido(cliente: httpx.AsyncClient) -> str | None:
    """CAT-01/Fase 2: los catálogos piden sesión (AUT-09)."""
    respuesta = await cliente.get("/api/v1/catalogos/enums")
    if respuesta.status_code != 401:
        return f"Sin sesión devolvió {respuesta.status_code}; se esperaba 401."
    return None


async def _openapi_generado(cliente: httpx.AsyncClient) -> str | None:
    respuesta = await cliente.get("/openapi.json")
    if respuesta.status_code != 200:
        return "La documentación OpenAPI no está disponible (¿estás en desarrollo?)."
    return None


# --- Fase 2: sesión -----------------------------------------------------------------

ESTADO_FASE_2: dict[str, str] = {}


def _cabecera_csrf(cliente: httpx.AsyncClient) -> dict[str, str]:
    return {
        "X-CSRF-Token": cliente.cookies.get("csrf_token", ""),
        "Origin": str(cliente.base_url).rstrip("/"),
    }


async def _login_con_clave_erronea(cliente: httpx.AsyncClient) -> str | None:
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={
            "correo": CORREO_SMOKE,
            "password": "esta-clave-no-existe",
            "recaptcha_token": "smoke",
        },
    )
    if respuesta.status_code != 401:
        return f"Login erróneo devolvió {respuesta.status_code}; se esperaba 401."
    if respuesta.json().get("codigo") != "CREDENCIALES_INVALIDAS":
        return f"codigo inesperado: {respuesta.json().get('codigo')}"
    return None


async def _login_correcto(cliente: httpx.AsyncClient) -> str | None:
    if not CLAVE_SMOKE:
        return "Define SMOKE_PASSWORD con la contraseña vigente del administrador."
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={"correo": CORREO_SMOKE, "password": CLAVE_SMOKE, "recaptcha_token": "smoke"},
    )
    if respuesta.status_code == 400 and respuesta.json().get("codigo") == "CUENTA_BLOQUEADA":
        return "La cuenta está bloqueada por intentos previos; espera el plazo."
    if respuesta.status_code != 200:
        return f"Login devolvió {respuesta.status_code}: {respuesta.json().get('mensaje')}"
    datos = respuesta.json()
    if datos.get("must_change_password"):
        return (
            "must_change_password está en TRUE: inicia /docs y usa "
            "POST /auth/cambiar-password antes de repetir el smoke."
        )
    ESTADO_FASE_2["access"] = datos["access_token"]
    ESTADO_FASE_2["access_viejo"] = datos["access_token"]
    ESTADO_FASE_2["refresh"] = cliente.cookies.get("refresh_token", "")
    return None


async def _yo_con_permisos(cliente: httpx.AsyncClient) -> str | None:
    cliente.headers["Authorization"] = f"Bearer {ESTADO_FASE_2['access']}"
    try:
        respuesta = await cliente.get("/api/v1/auth/yo")
    except httpx.HTTPError as exc:
        return f"GET /auth/yo falló: {exc}"
    if respuesta.status_code != 200:
        return f"GET /auth/yo devolvió {respuesta.status_code}."
    datos = respuesta.json()
    if "sesion" not in datos.get("permisos", []):
        return "El rol del usuario no declara el permiso 'sesion'."
    return None


async def _enums_con_sesion(cliente: httpx.AsyncClient) -> str | None:
    try:
        respuesta = await cliente.get("/api/v1/catalogos/enums")
    except httpx.HTTPError as exc:
        return f"GET /catalogos/enums falló: {exc}"
    if respuesta.status_code != 200:
        return f"GET /catalogos/enums devolvió {respuesta.status_code}."
    datos = respuesta.json()
    faltan = [
        clave
        for clave in (
            "roles",
            "estados_orden",
            "estados_vale",
            "tipos_movimiento",
            "permisos",
        )
        if clave not in datos
    ]
    if faltan:
        return f"Faltan claves en la respuesta: {', '.join(faltan)}."
    return None


async def _refresh_rota_con_csrf(cliente: httpx.AsyncClient) -> str | None:
    cliente.headers.pop("Authorization", None)
    try:
        respuesta = await cliente.post("/api/v1/auth/refresh", headers=_cabecera_csrf(cliente))
    except httpx.HTTPError as exc:
        return f"POST /auth/refresh falló: {exc}"
    if respuesta.status_code != 200:
        return (
            f"POST /auth/refresh devolvió {respuesta.status_code}: "
            f"{respuesta.json().get('mensaje')}"
        )
    token_nuevo = cliente.cookies.get("refresh_token", "")
    if not token_nuevo or token_nuevo == ESTADO_FASE_2.get("refresh"):
        return "La cookie de refresh no rotó."
    ESTADO_FASE_2["access"] = respuesta.json()["access_token"]
    ESTADO_FASE_2["refresh"] = token_nuevo
    return None


async def _sin_csrf_rechaza(cliente: httpx.AsyncClient) -> str | None:
    try:
        respuesta = await cliente.post("/api/v1/auth/refresh")
    except httpx.HTTPError as exc:
        return f"POST /auth/refresh sin CSRF falló: {exc}"
    if respuesta.status_code != 403:
        return f"Sin token CSRF devolvió {respuesta.status_code}; se esperaba 403."
    if respuesta.json().get("codigo") != "CSRF_INVALIDO":
        return f"codigo inesperado: {respuesta.json().get('codigo')}"
    return None


async def _logout_revoca(cliente: httpx.AsyncClient) -> str | None:
    access = ESTADO_FASE_2.get("access")
    if not access:
        return "No hay access token de la fase (falló el login o el refresh)."
    cliente.headers["Authorization"] = f"Bearer {access}"
    try:
        respuesta = await cliente.post("/api/v1/auth/logout", headers=_cabecera_csrf(cliente))
    except httpx.HTTPError as exc:
        return f"POST /auth/logout falló: {exc}"
    if respuesta.status_code != 200:
        return f"POST /auth/logout devolvió {respuesta.status_code}."
    ESTADO_FASE_2.clear()
    return None


async def _yo_sin_sesion_rechaza(cliente: httpx.AsyncClient) -> str | None:
    cliente.headers.pop("Authorization", None)  # no bearer tras el logout.
    try:
        respuesta = await cliente.get("/api/v1/auth/yo")
    except httpx.HTTPError as exc:
        return f"GET /auth/yo falló: {exc}"
    if respuesta.status_code != 401:
        return f"Sin sesión devolvió {respuesta.status_code}; se esperaba 401."
    return None


# --- Fase 3: usuarios, roles y permisos --------------------------------------------

CLAVE_OPERADOR_SMOKE = "OperadorSmoke33"

ESTADO_FASE_3: dict[str, str | int] = {}


async def _usuarios_sin_sesion_rechaza(cliente: httpx.AsyncClient) -> str | None:
    """UX-02/Fase 3: el módulo usuarios exige permiso usuarios.gestionar."""
    try:
        respuesta = await cliente.get("/api/v1/usuarios")
    except httpx.HTTPError as exc:
        return f"GET /usuarios falló: {exc}"
    if respuesta.status_code != 401:
        return f"Sin sesión devolvió {respuesta.status_code}; se esperaba 401."
    return None


def _ms_actuales() -> str:
    """Marca de tiempo en ms, para un correo único por corrida del smoke."""
    import time

    return str(int(time.time() * 1000))


async def _login_admin_para_usuarios(cliente: httpx.AsyncClient) -> str | None:
    """Inicia sesión con el administrador y guarda su id para USR-07."""
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={"correo": CORREO_SMOKE, "password": CLAVE_SMOKE, "recaptcha_token": "smoke"},
    )
    if respuesta.status_code != 200:
        cuerpo = respuesta.json()
        return (
            "Login del administrador devolvió "
            f"{respuesta.status_code}: {cuerpo.get('mensaje')}"
        )
    ESTADO_FASE_3["access_admin"] = respuesta.json()["access_token"]
    cliente.headers["Authorization"] = f"Bearer {ESTADO_FASE_3['access_admin']}"
    yo = await cliente.get("/api/v1/auth/yo")
    if yo.status_code != 200:
        return f"GET /auth/yo del admin devolvió {yo.status_code}."
    ESTADO_FASE_3["admin_id"] = yo.json()["usuario"]["id"]
    return None


async def _crea_operador(cliente: httpx.AsyncClient) -> str | None:
    """USR-01: el admin crea un operador; la contraseña temporal llega una vez."""
    sufijo = _ms_actuales()  # correo único por corrida, sin rechazos 409
    correo = f"operador-{sufijo}@ejemplo.pe"
    ESTADO_FASE_3["correo_operador"] = correo
    cliente.headers["Authorization"] = f"Bearer {ESTADO_FASE_3['access_admin']}"
    respuesta = await cliente.post(
        "/api/v1/usuarios",
        json={
            "nombre": f"Operador Smoke {sufijo}",
            "correo": correo,
            "rol": "despachador",
        },
    )
    if respuesta.status_code != 201:
        return f"POST /usuarios devolvió {respuesta.status_code}: {respuesta.json().get('mensaje')}"
    datos = respuesta.json()
    ESTADO_FASE_3["id_operador"] = datos["id"]
    ESTADO_FASE_3["clave_temporal"] = datos["password_temporal"]

    # USR-02: el listado con búsqueda encuentra al recién creado.
    busqueda = await cliente.get("/api/v1/usuarios", params={"q": correo})
    if busqueda.status_code != 200:
        return f"GET /usuarios?q= devolvió {busqueda.status_code}."
    if int(busqueda.json()["total"]) < 1:
        return "El listado con búsqueda no encontró al operador recién creado."
    return None


async def _login_operador_con_temporal(cliente: httpx.AsyncClient) -> str | None:
    """El operador entra con su contraseña temporal (RF-AUT-07 entra en juego)."""
    cliente.headers.pop("Authorization", None)
    cliente.cookies.clear()
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={
            "correo": str(ESTADO_FASE_3["correo_operador"]),
            "password": str(ESTADO_FASE_3["clave_temporal"]),
            "recaptcha_token": "smoke",
        },
    )
    if respuesta.status_code != 200:
        cuerpo = respuesta.json()
        return (
            "Login del operador devolvió "
            f"{respuesta.status_code}: {cuerpo.get('mensaje')}"
        )
    datos = respuesta.json()
    if not datos.get("must_change_password"):
        return "El operador debería tener must_change_password en TRUE."
    ESTADO_FASE_3["access_temporal"] = datos["access_token"]
    return None


async def _operador_restringido_al_cambiar(cliente: httpx.AsyncClient) -> str | None:
    """AUT-06: con cambio obligatorio solo pasan /auth/yo, cambiar-password y logout."""
    cliente.headers["Authorization"] = f"Bearer {ESTADO_FASE_3['access_temporal']}"
    respuesta = await cliente.get("/api/v1/usuarios")
    if respuesta.status_code != 403:
        return (
            f"GET /usuarios con cambio pendiente devolvió {respuesta.status_code}"
            "; se esperaba 403."
        )
    if respuesta.json().get("codigo") != "CAMBIO_PASSWORD_OBLIGATORIO":
        return f"codigo inesperado: {respuesta.json().get('codigo')}"
    return None


async def _operador_cambia_password(cliente: httpx.AsyncClient) -> str | None:
    cliente.headers["Authorization"] = f"Bearer {ESTADO_FASE_3['access_temporal']}"
    respuesta = await cliente.post(
        "/api/v1/auth/cambiar-password",
        json={
            "password_actual": ESTADO_FASE_3["clave_temporal"],
            "password_nueva": CLAVE_OPERADOR_SMOKE,
        },
    )
    if respuesta.status_code != 200:
        cuerpo = respuesta.json()
        return (
            "POST /auth/cambiar-password del operador devolvió "
            f"{respuesta.status_code}: {cuerpo.get('mensaje')}"
        )
    ESTADO_FASE_3["access_operador"] = respuesta.json()["access_token"]
    return None


async def _operador_sin_permiso(cliente: httpx.AsyncClient) -> str | None:
    """Sección 4.1: `usuarios.gestionar` solo lo tiene el administrador."""
    cliente.headers["Authorization"] = f"Bearer {ESTADO_FASE_3['access_operador']}"
    respuesta = await cliente.get("/api/v1/usuarios")
    if respuesta.status_code != 403:
        return f"GET /usuarios del operador devolvió {respuesta.status_code}; se esperaba 403."
    if respuesta.json().get("codigo") != "SIN_PERMISO":
        return f"codigo inesperado: {respuesta.json().get('codigo')}"
    return None


async def _ultimo_admin_protegido(cliente: httpx.AsyncClient) -> str | None:
    """USR-07: no se le puede cambiar el rol al único administrador.

    Solo es posible cuando el admin del smoke es el ÚLTIMO. Contra una base
    con mas administradores (p. ej. desarrollo) el parche es legítimo y el
    smoke no toca datos: la protección se valida estrictamente en pytest.
    """
    cliente.headers["Authorization"] = f"Bearer {ESTADO_FASE_3['access_admin']}"
    respuesta = await cliente.get("/api/v1/usuarios", params={"rol": "administrador"})
    if respuesta.status_code != 200:
        return f"GET /usuarios?rol=administrador devolución {respuesta.status_code}."
    if int(respuesta.json()["total"]) > 1:
        print("        nota: hay mas de un administrador; USR-07 se omite (verificado en pytest).")
        return None
    parche = await cliente.patch(
        f"/api/v1/usuarios/{ESTADO_FASE_3['admin_id']}",
        json={"rol": "despachador"},
    )
    if parche.status_code != 409:
        return f"PATCH del rol del único admin devolvió {parche.status_code}; se esperaba 409."
    if parche.json().get("codigo") != "ULTIMO_ADMINISTRADOR":
        return f"codigo inesperado: {parche.json().get('codigo')}"
    return None


async def _restablece_operador(cliente: httpx.AsyncClient) -> str | None:
    """USR-06: nueva contraseña temporal mostrada una sola vez."""
    respuesta = await cliente.post(
        f"/api/v1/usuarios/{ESTADO_FASE_3['id_operador']}/restablecer-password"
    )
    if respuesta.status_code != 200:
        cuerpo = respuesta.json()
        return (
            "POST restablecer-password devolvió "
            f"{respuesta.status_code}: {cuerpo.get('mensaje')}"
        )
    nueva = respuesta.json()["password_temporal"]
    if nueva == ESTADO_FASE_3["clave_temporal"]:
        return "La contraseña temporal restablecida no debería repetirse."
    ESTADO_FASE_3.clear()
    cliente.headers.pop("Authorization", None)
    return None


# --- Fase 4: configuración, combustibles y precios ------------------------------

ESTADO_FASE_4: dict[str, str] = {}


async def _login_admin_para_fase4(cliente: httpx.AsyncClient) -> str | None:
    """Sesión del administrador del smoke para el módulo de configuración."""
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={"correo": CORREO_SMOKE, "password": CLAVE_SMOKE, "recaptcha_token": "smoke"},
    )
    if respuesta.status_code != 200:
        return f"Login devolvió {respuesta.status_code}: {respuesta.json().get('mensaje')}"
    ESTADO_FASE_4["access"] = respuesta.json()["access_token"]
    ESTADO_FASE_4["ms"] = _ms_actuales()
    cliente.headers["Authorization"] = f"Bearer {ESTADO_FASE_4['access']}"
    return None


async def _combustible_creado_y_listado(cliente: httpx.AsyncClient) -> str | None:
    """CMB-01: alta del tipo y catálogo con `precio_vigente` inicial nulo."""
    nombre = f"Gasohol Smoke {ESTADO_FASE_4['ms']}"
    alta = await cliente.post("/api/v1/combustibles", json={"nombre": nombre})
    if alta.status_code != 201:
        return f"POST /combustibles devolvió {alta.status_code}: {alta.json().get('mensaje')}"
    ESTADO_FASE_4["combustible_id"] = str(alta.json()["id"])
    listado = await cliente.get("/api/v1/combustibles", params={"activo": "true"})
    items = listado.json()["items"]
    hallado = next((c for c in items if str(c["id"]) == ESTADO_FASE_4["combustible_id"]), None)
    if hallado is None:
        return "El combustible creado no aparece en el listado."
    if hallado["precio_vigente"] is not None:
        return "El catálogo debería arrancar sin precio vigente."
    return None


async def _precio_registrado_vigente_primero(cliente: httpx.AsyncClient) -> str | None:
    """CMB-02/03: registra el precio del día y el histórico lo muestra primero."""
    combustible = ESTADO_FASE_4["combustible_id"]
    hoy = _dt.date.today().isoformat()
    precio = await cliente.post(
        f"/api/v1/combustibles/{combustible}/precios",
        json={"precio_galon": "15.75", "vigente_desde": hoy},
    )
    if precio.status_code == 409:  # precio del día ya sembrado: idempotente
        pass
    elif precio.status_code != 201:
        return f"POST precios devolvió {precio.status_code}: {precio.json().get('mensaje')}"

    listado = await cliente.get("/api/v1/combustibles", params={"activo": "true"})
    hallado = next(
        c
        for c in listado.json()["items"]
        if str(c["id"]) == combustible
    )
    vigente = hallado["precio_vigente"]
    if not vigente or vigente["vigente_desde"] != hoy:
        return f"El precio vigente no es el de hoy: {vigente}"

    historico = await cliente.get(f"/api/v1/combustibles/{combustible}/precios")
    if historico.json()[0]["vigente_desde"] != hoy:
        return "El histórico no muestra el precio más reciente primero."
    return None


async def _precio_historico_inmutable(cliente: httpx.AsyncClient) -> str | None:
    """CMB-02/RN-16: fecha anterior al último precio se rechaza (409)."""
    combustible = ESTADO_FASE_4["combustible_id"]
    atrasado = await cliente.post(
        f"/api/v1/combustibles/{combustible}/precios",
        json={"precio_galon": "16.10", "vigente_desde": "2020-01-01"},
    )
    if atrasado.status_code != 409:
        return f"La fecha retroactiva devolvió {atrasado.status_code}; se esperaba 409."
    if atrasado.json().get("codigo") != "FECHA_PRECIO_ATRASADA":
        return f"codigo inesperado: {atrasado.json().get('codigo')}"
    return None


async def _parametros_leen_rango_y_guardan(cliente: httpx.AsyncClient) -> str | None:
    """CFG-01: catálogo con contrato y guardado de un valor dentro del rango."""
    lista = await cliente.get("/api/v1/configuracion/parametros")
    if lista.status_code != 200:
        return f"GET /configuracion/parametros devolvió {lista.status_code}."
    contrato = {p["clave"]: p for p in lista.json()["items"]}
    if "login_intentos_max" not in contrato or "vale_vigencia_dias" not in contrato:
        return "Faltan parámetros declarados del plan."

    fuera = await cliente.put(
        "/api/v1/configuracion/parametros",
        json={"valores": {"login_intentos_max": "0"}},
    )
    if fuera.status_code != 422:
        return f"Un valor fuera de rango devolvió {fuera.status_code}; se esperaba 422."

    ajustado = await cliente.put(
        "/api/v1/configuracion/parametros",
        json={"valores": {"ocr_umbral_confianza": "0.85"}},
    )
    if ajustado.status_code != 200:
        return f"PUT de un valor válido devolvió {ajustado.status_code}."
    confirmado = await cliente.get("/api/v1/configuracion/parametros")
    valor = next(
        p for p in confirmado.json()["items"] if p["clave"] == "ocr_umbral_confianza"
    )
    if valor["valor"] != "0.85":
        return f"El valor no rige de inmediato: {valor['valor']}"
    return None


async def _estacion_gestionada_y_protegida(cliente: httpx.AsyncClient) -> str | None:
    """CFG-02: ficha de la estación se guarda y se lee con `estacion.ver`."""
    ficha = await cliente.put(
        "/api/v1/configuracion/estacion",
        json={
            "nombre": "Estación San José (smoke)",
            "ruc": "20100047218",
            "direccion": "Av. del Smoke 123",
        },
    )
    if ficha.status_code != 200:
        return (
            "PUT /configuracion/estacion devolvió "
            f"{ficha.status_code}: {ficha.json().get('mensaje')}"
        )
    lectura = await cliente.get("/api/v1/configuracion/estacion")
    if lectura.status_code != 200 or "San José" not in lectura.json()["nombre"]:
        return f"GET /configuracion/estacion: {lectura.status_code} {lectura.text[:120]}"
    return None


async def _logo_rechazado_por_contenido(cliente: httpx.AsyncClient) -> str | None:
    """CFG-02: la subida se valida por firma binaria, nunca por extensión."""
    impostor = await cliente.post(
        "/api/v1/configuracion/estacion/logo",
        files={"archivo": ("logo.png", b"texto plano no es un png", "image/png")},
    )
    if impostor.status_code != 422:
        return f"Un archivo impostor devolvió {impostor.status_code}; se esperaba 422."
    if impostor.json().get("codigo") != "FORMATO_INVALIDO":
        return f"codigo inesperado: {impostor.json().get('codigo')}"
    # Cierre de fase: se cierra la sesión del smoke.
    cliente.headers.pop("Authorization", None)
    ESTADO_FASE_4.clear()
    return None


# --- Fase 6: vales, emisión y vales de entidad ---------------------------------

ESTADO_FASE_6: dict[str, str] = {}
RUC_SMOKE = "20100104157"


async def _login_admin_para_fase6(cliente: httpx.AsyncClient) -> str | None:
    """Sesión del administrador del smoke para el módulo de vales."""
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={"correo": CORREO_SMOKE, "password": CLAVE_SMOKE, "recaptcha_token": "smoke"},
    )
    if respuesta.status_code != 200:
        return f"Login devolvió {respuesta.status_code}: {respuesta.json().get('mensaje')}"
    cliente.headers["Authorization"] = f"Bearer {respuesta.json()['access_token']}"
    return None


async def _escenario_para_fase6(cliente: httpx.AsyncClient) -> str | None:
    """Combustible con precio, institución con numeración general y la orden.

    La orden se queda corta a propósito: con el precio de S/ 15.75 el
    galón, un presupuesto de S/ 1000.00 deja techo de 63.49 galones.
    """
    marca = ESTADO_FASE_6["ms"] = _ms_actuales()
    combustible = await cliente.post(
        "/api/v1/combustibles", json={"nombre": f"Vales Smoke {marca}"}
    )
    if combustible.status_code != 201:
        return f"POST /combustibles devolvió {combustible.status_code}."
    id_combustible = combustible.json()["id"]
    ESTADO_FASE_6["combustible"] = str(id_combustible)
    precio = await cliente.post(
        f"/api/v1/combustibles/{id_combustible}/precios",
        json={"precio_galon": "15.75", "vigente_desde": _dt.date.today().isoformat()},
    )
    if precio.status_code != 201:
        return f"POST precios devolvió {precio.status_code}: {precio.json().get('mensaje')}"

    institucion = await cliente.post(
        "/api/v1/instituciones",
        json={
            "nombre": f"Institución Smoke {marca}",
            "ruc": RUC_SMOKE,
            "tipo": "publica",
            "modalidad_numeracion": "general",
        },
    )
    if institucion.status_code == 409:
        # RUC único: una corrida previa ya lo sembró; se reutiliza.
        fallback = await cliente.get(f"/api/v1/instituciones/ruc/{RUC_SMOKE}")
        existente = (fallback.json() or {}).get("institucion")
        if fallback.status_code != 200 or not existente:
            return "No se pudo crear ni hallar la institución del smoke (RUC único)."
        institucion = None
        institucion_fila = existente
    elif institucion.status_code != 201:
        return (
            "POST /instituciones devolvió "
            f"{institucion.status_code}: {institucion.json().get('mensaje')}"
        )
    else:
        institucion_fila = institucion.json()
    ESTADO_FASE_6["institucion"] = str(institucion_fila["id"])

    orden = await cliente.post(
        "/api/v1/ordenes",
        json={
            "institucion_id": institucion_fila["id"],
            "fecha_emision": _dt.date.today().isoformat(),
            "presupuesto_soles": "1000.00",
            "estado": "vigente",
            "confirmar_duplicado": True,
        },
    )
    if orden.status_code != 201:
        return f"POST /ordenes devolvió {orden.status_code}: {orden.json().get('mensaje')}"
    ESTADO_FASE_6["orden"] = str(orden.json()["id"])
    return None


async def _simulacion_no_guarda(cliente: httpx.AsyncClient) -> str | None:
    """VAL-03/CMB-04: la vista previa devuelve techo y total sin escribir nada."""
    orden = ESTADO_FASE_6["orden"]
    combustible = ESTADO_FASE_6["combustible"]
    respuesta = await cliente.post(
        f"/api/v1/ordenes/{orden}/vales/simulacion",
        json={"combustible_id": int(combustible), "cantidades": ["20.00", "20.00"]},
    )
    if respuesta.status_code != 200:
        return (
            f"POST simulacion devolvió {respuesta.status_code}: "
            f"{respuesta.json().get('mensaje')}"
        )
    datos = respuesta.json()
    if datos["precio_galon"] != "15.75":
        return f"El precio vigente no es 15.75: {datos['precio_galon']}"
    if datos["total_soles"] != "630.00":
        return f"El total de la simulación no es 630.00: {datos['total_soles']}"
    if datos["presupuesto_restante_soles"] != "1000.00":
        return "La simulación modificó el presupuesto restante."
    maximo = float(datos["maximo_galones"])
    if not 63.48 <= maximo <= 63.50:
        return f"El máximo de galones no es el techo de 1000/15.75: {maximo}"

    listado = await cliente.get("/api/v1/vales", params={"orden_id": int(orden)})
    if listado.status_code != 200:
        return f"GET /vales devolvió {listado.status_code}."
    if listado.json()["total"] != 0:
        return "La simulación dejó vales en la base."
    return None


async def _emite_dos_vales(cliente: httpx.AsyncClient) -> str | None:
    """VAL-01/VAL-02: emisión con numeración de estación y precio retenido."""
    orden = ESTADO_FASE_6["orden"]
    combustible = ESTADO_FASE_6["combustible"]
    emitidos = await cliente.post(
        f"/api/v1/ordenes/{orden}/vales",
        json={"combustible_id": int(combustible), "cantidades": ["20.00", "20.00"]},
    )
    if emitidos.status_code != 201:
        return f"POST vales devolvió {emitidos.status_code}: {emitidos.json().get('mensaje')}"
    vales = emitidos.json()
    if len(vales) != 2:
        return f"Se esperaban 2 vales, llegaron {len(vales)}"
    for vale in vales:
        if vale["valor_soles"] != "315.00":
            return f"El vale acumuló un valor inesperado: {vale['valor_soles']}"
        if not vale["numero_estacion"]:
            return "El vale de estación llegó sin número."
    return None


async def _exceso_rechazado_con_maximo(cliente: httpx.AsyncClient) -> str | None:
    """VAL-03: 409 PRESUPUESTO_EXCEDIDO con el restante y el máximo de galones."""
    orden = ESTADO_FASE_6["orden"]
    combustible = ESTADO_FASE_6["combustible"]
    exceso = await cliente.post(
        f"/api/v1/ordenes/{orden}/vales",
        json={"combustible_id": int(combustible), "cantidades": ["30.00"]},
    )
    if exceso.status_code != 409:
        return f"Una emisión que excede devolvió {exceso.status_code}; se esperaba 409."
    datos = exceso.json()
    if datos.get("codigo") != "PRESUPUESTO_EXCEDIDO":
        return f"codigo inesperado: {datos.get('codigo')}"
    detalles = datos.get("detalles", {})
    if detalles.get("presupuesto_restante_soles") != "370.00":
        return "El restante no refleja los dos vales de 315.00."
    maximo = float(detalles.get("maximo_galones", "0"))
    if not 23.48 <= maximo <= 23.50:
        return f"El máximo de galones no cuadra con 370/15.75: {maximo}"
    return None


async def _vale_entidad_y_duplicado(cliente: httpx.AsyncClient) -> str | None:
    """VAL-05/D-02: el número lo da la institución; repetido en la serie, 409."""
    orden = ESTADO_FASE_6["orden"]
    combustible = ESTADO_FASE_6["combustible"]
    numero = f"VA-ENT-{ESTADO_FASE_6['ms']}-001"
    ESTADO_FASE_6["numero"] = numero
    primero = await cliente.post(
        f"/api/v1/ordenes/{orden}/vales-entidad",
        json={"numero_entidad": numero, "combustible_id": int(combustible), "cantidad": "5.00"},
    )
    if primero.status_code != 201:
        return (
            "POST vales-entidad devolvió "
            f"{primero.status_code}: {primero.json().get('mensaje')}"
        )
    if primero.json()["numero_entidad"] != numero:
        return "El número de entidad no se conservó tal como lo envió la institución."

    repetido = await cliente.post(
        f"/api/v1/ordenes/{orden}/vales-entidad",
        json={"numero_entidad": numero, "combustible_id": int(combustible), "cantidad": "5.00"},
    )
    if repetido.status_code != 409:
        return f"Un número repetido devolvió {repetido.status_code}; se esperaba 409."
    if repetido.json().get("codigo") != "NUMERO_ENTIDAD_DUPLICADO":
        return f"codigo inesperado: {repetido.json().get('codigo')}"
    return None


async def _busca_por_numero_entidad(cliente: httpx.AsyncClient) -> str | None:
    """QRY-01: el buscador halla el vale de entidad por su número."""
    respuesta = await cliente.get("/api/v1/vales/buscar", params={"q": ESTADO_FASE_6["numero"]})
    if respuesta.status_code != 200:
        return f"GET /vales/buscar devolvió {respuesta.status_code}."
    candidatos = respuesta.json()
    hallado = [c for c in candidatos if c["numero_entidad"] == ESTADO_FASE_6["numero"]]
    if not hallado:
        return "El buscador no encontró el vale de entidad recién registrado."
    if not hallado[0].get("saldo") or float(hallado[0]["saldo"]) != 5.0:
        return f"El saldo del candidato no es 5.00: {hallado[0]}"

    # Cierre de fase: se cierra la sesión del smoke.
    cliente.headers.pop("Authorization", None)
    ESTADO_FASE_6.clear()
    return None


FASES: tuple[Fase, ...] = (
    {
        "numero": 1,
        "titulo": "Esqueleto FastAPI, PostgreSQL y migraciones propias",
        "comprobaciones": (
            ("001 salud con PostgreSQL y OCR en ok", _salud_en_ok),
            ("002 catálogos de enums protegidos piden sesión", _enums_protegido),
            ("003 documentación OpenAPI generada", _openapi_generado),
        ),
    },
    {
        "numero": 2,
        "titulo": "Autenticación, sesiones y auditoría base",
        "comprobaciones": (
            ("004 login rechaza credenciales erróneas", _login_con_clave_erronea),
            ("005 login con SMOKE_CORREO/SMOKE_PASSWORD", _login_correcto),
            ("006 /auth/yo devuelve user y permisos", _yo_con_permisos),
            ("007 enums con sesión y listas completas", _enums_con_sesion),
            ("008 refresh rota con la cookie y CSRF", _refresh_rota_con_csrf),
            ("009 reutilizar refresh sin CSRF es rechazado", _sin_csrf_rechaza),
            ("010 logout cierra la sesión", _logout_revoca),
            ("011 sin sesión ya no hay datos", _yo_sin_sesion_rechaza),
        ),
    },
    {
        "numero": 3,
        "titulo": "Usuarios, roles y permisos",
        "comprobaciones": (
            ("012 /usuarios pide sesión sin bearer", _usuarios_sin_sesion_rechaza),
            ("013 login del administrador del smoke", _login_admin_para_usuarios),
            ("014 el admin crea un operador y lo halla", _crea_operador),
            ("015 el operador entra con su clave temporal", _login_operador_con_temporal),
            ("016 cambio pendiente bloquea /usuarios", _operador_restringido_al_cambiar),
            ("017 el operador cambia su contraseña", _operador_cambia_password),
            ("018 sin el permiso, /usuarios responde 403 SIN_PERMISO", _operador_sin_permiso),
            ("019 el único administrador no puede cambiar su rol", _ultimo_admin_protegido),
            ("020 restablecer-password entrega una temporal nueva", _restablece_operador),
        ),
    },
    {
        "numero": 4,
        "titulo": "Configuración, combustibles y precios",
        "comprobaciones": (
            ("021 login del administrador del smoke", _login_admin_para_fase4),
            ("022 combustible creado y listado con precio nulo", _combustible_creado_y_listado),
            ("023 precio del día registrado y vigente en el catálogo",
             _precio_registrado_vigente_primero),
            ("024 fecha retroactiva de precio rechazada (409)", _precio_historico_inmutable),
            ("025 parámetros con rango y guardado inmediato", _parametros_leen_rango_y_guardan),
            ("026 ficha de la estación se guarda y se lee", _estacion_gestionada_y_protegida),
            ("027 logo impostor rechazado por contenido", _logo_rechazado_por_contenido),
        ),
    },
    {
        "numero": 6,
        "titulo": "Vales: emisión y vales de entidad",
        "comprobaciones": (
            ("028 login del administrador del smoke", _login_admin_para_fase6),
            ("029 escenario: combustible con precio, institución y orden vigente",
             _escenario_para_fase6),
            ("030 simulación entrega techo y total sin guardar nada", _simulacion_no_guarda),
            ("031 emisión de 2 vales con precio retenido y numeración",
             _emite_dos_vales),
            ("032 emisión excedida rechazada con máximo de galones",
             _exceso_rechazado_con_maximo),
            ("033 vale de entidad registra y su duplicado da 409",
             _vale_entidad_y_duplicado),
            ("034 búsqueda global halla el vale por número de entidad",
             _busca_por_numero_entidad),
        ),
    },
)


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="origen de la API")
    parser.add_argument("--hasta", type=int, default=1, help="última fase a comprobar")
    parser.add_argument("--segundos", type=float, default=10.0, help="segundos por petición")
    return parser


def _fases_hasta(limite: int) -> tuple[Fase, ...]:
    fases = tuple(fase for fase in FASES if fase["numero"] <= limite)
    if limite > FASES[-1]["numero"]:
        print(
            f"Aviso: la fase {limite} aún no tiene comprobaciones; máximo {FASES[-1]['numero']}.",
            file=sys.stderr,
        )
    return fases


async def recorrer(url: str, limite: int, segundos: float) -> int:
    fallas = 0
    limite_util = max(1, limite)
    async with httpx.AsyncClient(base_url=url, timeout=segundos) as cliente:
        for fase in _fases_hasta(limite_util):
            print(f"\nFase {fase['numero']}: {fase['titulo']}")
            for titulo, comprobar in fase["comprobaciones"]:
                try:
                    detalle = await comprobar(cliente)
                except httpx.HTTPError as exc:
                    detalle = f"No se pudo conectar: {exc}"
                if detalle is None:
                    print(f"  OK    {titulo}")
                else:
                    fallas += 1
                    print(f"  FALLA {titulo}: {detalle}")
    return 1 if fallas else 0


def main() -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            with suppress(OSError, ValueError):  # flujo no reconfigurable
                flujo.reconfigure(encoding="utf-8", errors="replace")
    argumentos = construir_parser().parse_args()
    print(f"Recorrido smoke contra {argumentos.url} hasta la fase {argumentos.hasta}.")
    codigo = asyncio.run(recorrer(argumentos.url, argumentos.hasta, argumentos.segundos))
    if codigo == 0:
        print("\nRecorrido terminado en verde.")
    else:
        print("\nRecorrido con fallas.", file=sys.stderr)
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
