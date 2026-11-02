"""Concurrencia real de consumos: `python scripts/probar_concurrencia.py`.

Lanza `--procesos` hilos (cada uno con su propio inicio de sesión y su
propio `token_operacion`) que despachan `--cantidad` galones al mismo
tiempo sobre un mismo vale, identificado por `--numero-estacion`.

El servidor debe resolver la carrera solo con `FOR UPDATE` y el índice
único de `token_operacion`: sobre un vale de 100 galones con
`--procesos 10 --cantidad 15` imprime «aceptados 6 / rechazados 4 / saldo
final 10.00» y termina en verde. Si el saldo final no cuadra con
`inicial - aceptados x cantidad`, el proceso devuelve 1.

Sesión: `SMOKE_CORREO` y `SMOKE_PASSWORD` como en `smoke.py`; el usuario
debe tener `consumos.registrar` (administrador u oficina).
"""

import argparse
import json
import os
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress

import httpx

CORREO = os.environ.get("SMOKE_CORREO", "admin@ejemplo.pe")
CLAVE = os.environ.get("SMOKE_PASSWORD", "")
_CANDADO = threading.Lock()


def _preparar_salida() -> None:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            with suppress(OSError, ValueError):
                flujo.reconfigure(encoding="utf-8", errors="replace")


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="origen de la API")
    parser.add_argument(
        "--numero-estacion", required=True, help="número del vale a despachar"
    )
    parser.add_argument("--procesos", type=int, default=10, help="hilos simultáneos")
    parser.add_argument("--cantidad", default="15.00", help="galones por despacho")
    parser.add_argument("--segundos", type=float, default=30.0, help="tiempo por petición")
    return parser


def _iniciar_sesion(base_url: str, segundos: float) -> tuple[httpx.Client, str]:
    """Un cliente httpx con su propia sesión (AUT-01..03)."""
    cliente = httpx.Client(base_url=base_url, timeout=segundos)
    respuesta = cliente.post(
        "/api/v1/auth/login",
        json={"correo": CORREO, "password": CLAVE, "recaptcha_token": "smoke"},
    )
    if respuesta.status_code != 200:
        cliente.close()
        detalle = respuesta.json().get("mensaje", respuesta.text)
        raise SystemExit(
            f"FALLA: el login de {CORREO} devolvió {respuesta.status_code}: {detalle}"
        )
    if respuesta.json().get("must_change_password"):
        cliente.close()
        raise SystemExit(
            f"FALLA: {CORREO} debe cambiar su contraseña en /docs antes de la prueba."
        )
    cliente.headers["Authorization"] = f"Bearer {respuesta.json()['access_token']}"
    return cliente, str(respuesta.json()["usuario"]["id"])


def _halla_vale(cliente: httpx.Client, numero: str) -> dict:
    respuesta = cliente.get("/api/v1/vales/buscar", params={"q": numero})
    if respuesta.status_code != 200:
        raise SystemExit(f"FALLA: GET /vales/buscar devolvió {respuesta.status_code}.")
    candidatos = [v for v in respuesta.json() if v.get("numero_estacion") == numero]
    if not candidatos:
        raise SystemExit(f"FALLA: no hay vale de estación con número {numero}.")
    return candidatos[0]


def _despachar(
    cliente: httpx.Client, vale_id: int, cantidad: str, rastreo: dict, orden: int
) -> None:
    """Despacha en su sesión y registra el resultado en `rastreo`."""
    estado, detalle = None, ""
    try:
        respuesta = cliente.post(
            f"/api/v1/vales/{vale_id}/consumos",
            json={"token_operacion": str(uuid.uuid4()), "cantidad_galones": cantidad},
        )
        estado = respuesta.status_code
        if estado != 201:
            try:
                detalle = respuesta.json().get("mensaje", respuesta.text)
            except json.JSONDecodeError:
                detalle = respuesta.text
    except httpx.HTTPError as exc:
        estado, detalle = 0, f"sin conexión: {exc}"
    with _CANDADO:
        rastreo[orden] = (estado, detalle)


def main() -> int:
    _preparar_salida()
    if not CLAVE:
        print(
            "Define SMOKE_PASSWORD con la contraseña del usuario de despacho.",
            file=sys.stderr,
        )
        return 2

    argumentos = construir_parser().parse_args()
    base_url = argumentos.url.rstrip("/")
    procesos = max(1, argumentos.procesos)

    cliente, _ = _iniciar_sesion(base_url, argumentos.segundos)
    vale = _halla_vale(cliente, argumentos.numero_estacion)
    vale_id = int(vale["id"])
    saldo_inicial = vale["saldo"]
    print(
        f"Vale {argumentos.numero_estacion} (id {vale_id}), saldo inicial "
        f"{saldo_inicial}: {procesos} despachos de {argumentos.cantidad} en carrera."
    )

    sesiones: list[tuple[httpx.Client, str]] = [
        _iniciar_sesion(base_url, argumentos.segundos) for _ in range(procesos)
    ]
    rastreo: dict[int, tuple[int, str]] = {}
    with ThreadPoolExecutor(max_workers=procesos) as tren:
        futuros = [
            (
                orden,
                tren.submit(
                    _despachar,
                    sesiones[orden][0],
                    vale_id,
                    argumentos.cantidad,
                    rastreo,
                    orden,
                ),
            )
            for orden in range(procesos)
        ]
        for _, futuro in futuros:
            futuro.result()
    for sesion, _ in sesiones:
        sesion.close()

    resultados = [rastreo[orden] for orden in sorted(rastreo)]
    aceptados = sum(1 for estado, _ in resultados if estado == 201)
    por_codigo: dict[int, int] = {}
    for estado, _ in resultados:
        por_codigo[estado] = por_codigo.get(estado, 0) + 1
    for estado, detalle in resultados:
        if estado != 201:
            print(f"  hilo → {estado}: {detalle}")
    print(
        f"aceptados {aceptados} / rechazados {procesos - aceptados} "
        f"(por código HTTP {json.dumps(por_codigo, sort_keys=True)})"
    )

    detalle_vale = cliente.get(f"/api/v1/vales/{vale_id}")
    if detalle_vale.status_code != 200:
        print(f"FALLA: GET /vales/{vale_id} devolvió {detalle_vale.status_code}.")
        cliente.close()
        return 1
    saldo_final = detalle_vale.json()["saldo"]
    print(f"saldo final {saldo_final}")

    esperado = f"{float(saldo_inicial) - aceptados * float(argumentos.cantidad):.2f}"
    cliente.close()
    if saldo_final != esperado:
        print(
            f"FALLA: el saldo final {saldo_final} no cuadra con "
            f"{saldo_inicial} - {aceptados} x {argumentos.cantidad} = {esperado}."
        )
        return 1
    print("Prueba de concurrencia terminada en verde.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
