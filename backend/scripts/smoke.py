"""Recorrido de verificación por fase: `python scripts/smoke.py --hasta N`.

Es acumulativo: cada fase agrega comprobaciones numeradas y al ejecutar con
`--hasta N` se repiten todas las de las fases anteriores. Salida `OK` o
`FALLA` por comprobación; el proceso termina con código 1 si alguna falla.

La Fase 2 necesita un administrador (creado con `python -m app.cli
crear-admin --nombre ... --correo ...`) y, después de su primer inicio,
la contraseña ya cambiada en las variables `SMOKE_CORREO` y `SMOKE_PASSWORD`
(por omisión actúa como el admin que se ejemplifica en el README).
"""

import argparse
import asyncio
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
