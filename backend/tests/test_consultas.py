"""Pruebas de integración para saldos y movimientos netos de consumo."""

from app.core import tiempo
from tests.test_consumos import _vender
from tests.test_vales import _emitir, _escenario


async def test_consulta_consumo_netea_reversion_y_estado_cuenta(cliente):
    escenario = await _escenario(cliente, correo="consultas.api")
    orden = escenario["orden"]
    emitido = await _emitir(
        cliente, orden["id"], escenario["combustible"]["id"], cantidades=["100.00"]
    )
    assert emitido.status_code == 201, emitido.text
    vale = emitido.json()[0]

    await _vender(cliente, vale["id"], "30.00")
    consumos = await cliente.get(f"/api/v1/vales/{vale['id']}/consumos")
    assert consumos.status_code == 200, consumos.text
    id_movimiento = next(item["id"] for item in consumos.json() if item["tipo"] == "consumo")
    revertido = await cliente.post(
        f"/api/v1/consumos/{id_movimiento}/revertir", json={"motivo": "Reversión de prueba"}
    )
    assert revertido.status_code == 200, revertido.text

    periodo = await cliente.get(
        "/api/v1/consultas/consumo",
        params={
            "orden_id": orden["id"],
            "desde": tiempo.hoy().isoformat(),
            "hasta": tiempo.hoy().isoformat(),
            "agrupacion": "dia",
        },
    )
    assert periodo.status_code == 200, periodo.text
    assert len(periodo.json()) == 1
    assert periodo.json()[0]["importe_soles"] == "0.00"
    assert periodo.json()[0]["galones"] == "0.00"

    reporte_ordenes = await cliente.get(
        "/api/v1/reportes/ordenes",
        params={"desde": orden["fecha_emision"], "hasta": orden["fecha_emision"]},
    )
    assert reporte_ordenes.status_code == 200, reporte_ordenes.text
    assert reporte_ordenes.json()["total_ordenes"] == 1
    exportado = await cliente.get(
        "/api/v1/reportes/exportar/consumo-periodo.xlsx",
        params={
            "orden_id": orden["id"],
            "desde": tiempo.hoy().isoformat(),
            "hasta": tiempo.hoy().isoformat(),
            "agrupacion": "dia",
        },
    )
    assert exportado.status_code == 200, exportado.text
    assert exportado.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    estado = await cliente.get(f"/api/v1/consultas/estado-cuenta/{escenario['institucion']['id']}")
    assert estado.status_code == 200, estado.text
    assert estado.json()["saldo_final"] == "100.00"

    saldo = await cliente.get(f"/api/v1/consultas/saldo/ordenes/{orden['id']}")
    assert saldo.status_code == 200, saldo.text
    assert saldo.json()["vales"][0]["consumido_soles"] == "0.00"
