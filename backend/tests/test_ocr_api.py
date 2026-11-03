"""Pruebas del ciclo API de OCR de la Fase 11."""

from types import SimpleNamespace

from app.errors import ErrorDominio
from app.services.ocr.pipeline import Campo, Extraccion
from tests.test_ordenes import PDF_MINIMO, _admin, _institucion


def _lista(*, numero: str = "12") -> Extraccion:
    return Extraccion(
        estado="lista",
        metodo="texto_digital",
        campos=(
            Campo("numero_orden", numero, numero, 0.98, False),
            Campo("fecha", "2026-03-10", "10/03/2026", 0.98, False),
            Campo("monto", "1500.00", "S/ 1,500.00", 0.98, False),
            Campo("institucion", "Municipalidad Demo", "Municipalidad Demo", 0.98, False),
        ),
        advertencias=(),
        paginas=1,
        tiempo_ms=12,
    )


async def test_subir_revisar_confirmar_y_calcular_precision(cliente, monkeypatch, tmp_path):
    await _admin(cliente, "ocrapi@pruebas.pe")
    institucion = await _institucion(cliente)
    monkeypatch.setattr(
        "app.core.archivos.obtener_settings",
        lambda: SimpleNamespace(almacenamiento_dir=tmp_path),
    )
    monkeypatch.setattr("app.routers.ocr.pipeline.procesar", lambda *_args, **_kwargs: _lista())

    subida = await cliente.post(
        "/api/v1/ocr/extracciones", files={"archivo": ("orden.pdf", PDF_MINIMO, "application/pdf")}
    )
    assert subida.status_code == 201, subida.text
    extraccion = subida.json()
    assert extraccion["estado"] == "lista"
    assert len(extraccion["campos"]) == 4

    archivo = await cliente.get(f"/api/v1/ocr/extracciones/{extraccion['id']}/archivo")
    assert archivo.status_code == 200
    assert archivo.content == PDF_MINIMO
    assert archivo.headers["x-content-type-options"] == "nosniff"

    datos = {
        "datos_revisados": False,
        "orden": {
            "institucion_id": institucion["id"],
            "numero": 12,
            "fecha_emision": "2026-03-10",
            "presupuesto_soles": "1500.00",
        },
    }
    no_revisada = await cliente.post(
        f"/api/v1/ocr/extracciones/{extraccion['id']}/confirmar", json=datos
    )
    assert no_revisada.status_code == 409
    assert no_revisada.json()["codigo"] == "EXTRACCION_NO_CONFIRMABLE"

    datos["datos_revisados"] = True
    confirmada = await cliente.post(
        f"/api/v1/ocr/extracciones/{extraccion['id']}/confirmar", json=datos
    )
    assert confirmada.status_code == 201, confirmada.text
    assert confirmada.json()["estado"] == "confirmada"
    orden = await cliente.get(f"/api/v1/ordenes/{confirmada.json()['orden_id']}")
    assert orden.status_code == 200, orden.text
    assert orden.json()["creada_con_ocr"] is True
    assert orden.json()["archivo_path"]
    assert orden.json()["archivo_tipo"] == "application/pdf"
    assert orden.json()["archivo_tamano"] == len(PDF_MINIMO)

    precision = await cliente.get("/api/v1/ocr/precision")
    assert precision.status_code == 200
    assert precision.json()["total_confirmadas"] == 1
    assert precision.json()["campos"]["fecha"] == {
        "evaluados": 1,
        "corregidos": 0,
        "precision": 1.0,
    }


async def test_reintentar_conserva_el_intento_anterior(cliente, monkeypatch, tmp_path):
    await _admin(cliente, "ocrretry@pruebas.pe")
    monkeypatch.setattr(
        "app.core.archivos.obtener_settings",
        lambda: SimpleNamespace(almacenamiento_dir=tmp_path),
    )

    def falla(*_args, **_kwargs):
        raise ErrorDominio(503, "OCR_NO_DISPONIBLE", "Motor no disponible.")

    monkeypatch.setattr("app.routers.ocr.pipeline.procesar", falla)
    subida = await cliente.post(
        "/api/v1/ocr/extracciones", files={"archivo": ("orden.pdf", PDF_MINIMO, "application/pdf")}
    )
    assert subida.status_code == 201, subida.text
    anterior = subida.json()
    assert anterior["estado"] == "fallida"
    assert anterior["error_codigo"] == "OCR_NO_DISPONIBLE"

    monkeypatch.setattr("app.routers.ocr.pipeline.procesar", lambda *_args, **_kwargs: _lista())
    reintento = await cliente.post(f"/api/v1/ocr/extracciones/{anterior['id']}/reintentar")
    assert reintento.status_code == 201, reintento.text
    actual = reintento.json()
    assert actual["id"] != anterior["id"]
    assert actual["estado"] == "lista"

    historial = await cliente.get("/api/v1/ocr/extracciones")
    assert historial.status_code == 200
    assert historial.json()["total"] == 2


async def test_motor_ocupado_conserva_extraccion_fallida(cliente, monkeypatch, tmp_path):
    await _admin(cliente, "ocrcupo@pruebas.pe")
    monkeypatch.setattr(
        "app.core.archivos.obtener_settings",
        lambda: SimpleNamespace(almacenamiento_dir=tmp_path),
    )

    def ocupado(*_args, **_kwargs):
        raise ErrorDominio(503, "OCR_OCUPADO", "Motor ocupado.")

    monkeypatch.setattr("app.routers.ocr.pipeline.procesar", ocupado)
    subida = await cliente.post(
        "/api/v1/ocr/extracciones",
        files={"archivo": ("orden.pdf", PDF_MINIMO, "application/pdf")},
    )
    assert subida.status_code == 503
    id_extraccion = subida.json()["detalles"]["extraccion_id"]
    detalle = await cliente.get(f"/api/v1/ocr/extracciones/{id_extraccion}")
    assert detalle.status_code == 200
    assert detalle.json()["estado"] == "fallida"
    assert detalle.json()["error_codigo"] == "OCR_OCUPADO"
