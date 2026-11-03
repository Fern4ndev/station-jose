"""Mide consultas representativas en PostgreSQL de pruebas (Fase 12).

Preparación: `python -m app.cli cargar-volumen --movimientos 50000 --vale-id ID --test`.
Ejecución: `python scripts/benchmark.py --vale-id ID --orden-id ID`.
No modifica datos y se niega a conectarse a DATABASE_URL de desarrollo.
"""

import argparse
import asyncio
import json
import statistics
import time

import asyncpg

from app.config import obtener_settings
from app.db.migrar import a_dsn

CONSULTAS = {
    "movimientos por vale": """
        SELECT coalesce(sum(variacion),0)
        FROM movimientos_vale
        WHERE vale_id=$1 AND fecha_local >= CURRENT_DATE - 30
    """,
    "saldo por orden": """
        SELECT v.id, v.saldo, coalesce(sum(m.variacion),0)
        FROM vales v LEFT JOIN movimientos_vale m ON m.vale_id=v.id
        WHERE v.orden_compra_id=$1
        GROUP BY v.id
    """,
    "estado de cuenta institucional": """
        SELECT sum(m.variacion)
        FROM movimientos_vale m
        JOIN vales v ON v.id=m.vale_id
        JOIN ordenes_compra o ON o.id=v.orden_compra_id
        WHERE o.institucion_id=(SELECT institucion_id FROM ordenes_compra WHERE id=$1)
          AND m.fecha_local >= CURRENT_DATE - 30
    """,
}


async def medir(repeticiones: int, vale_id: int, orden_id: int) -> int:
    url = obtener_settings().database_url_test
    if not url:
        print("Falta DATABASE_URL_TEST; no se conecta a la base de desarrollo.")
        return 2
    conexion = await asyncpg.connect(
        a_dsn(url), server_settings={"default_transaction_read_only": "on"}
    )
    try:
        async with conexion.transaction(readonly=True):
            vale_existe = await conexion.fetchval("SELECT 1 FROM vales WHERE id=$1", vale_id)
            orden = await conexion.fetchrow(
                "SELECT institucion_id FROM ordenes_compra WHERE id=$1", orden_id
            )
            if not vale_existe or not orden:
                print("vale-id u orden-id no existen en la base de pruebas.")
                return 2
            parametros = {
                "movimientos por vale": (vale_id,),
                "saldo por orden": (orden_id,),
                "estado de cuenta institucional": (orden_id,),
            }
            for etiqueta, sql in CONSULTAS.items():
                tiempos_ms: list[float] = []
                explain = "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql
                for _ in range(repeticiones):
                    inicio = time.perf_counter()
                    plan = await conexion.fetchval(explain, *parametros[etiqueta])
                    tiempos_ms.append((time.perf_counter() - inicio) * 1000)
                    json.loads(plan)[0]["Plan"]
                mediana = statistics.median(tiempos_ms)
                estado = "OK" if mediana < 1000 else "FUERA DE META"
                print(f"{etiqueta}: mediana {mediana:.2f} ms ({estado}, {repeticiones} corridas)")
                if mediana >= 1000:
                    return 1
        return 0
    finally:
        await conexion.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vale-id", type=int, required=True)
    parser.add_argument("--orden-id", type=int, required=True)
    parser.add_argument("--repeticiones", type=int, default=5)
    args = parser.parse_args()
    if args.repeticiones < 1 or args.repeticiones > 50:
        parser.error("--repeticiones debe estar entre 1 y 50")
    return asyncio.run(medir(args.repeticiones, args.vale_id, args.orden_id))


if __name__ == "__main__":
    raise SystemExit(main())
