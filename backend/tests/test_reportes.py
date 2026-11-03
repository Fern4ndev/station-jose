"""Pruebas sin base para rangos Lima y escritura XLSX."""

from datetime import date, datetime
from io import BytesIO

from openpyxl import load_workbook

from app.services import reportes, xlsx


def test_rangos_de_reporte_usan_fecha_de_lima(monkeypatch):
    monkeypatch.setattr("app.services.reportes.tiempo.hoy", lambda: date(2026, 11, 4))
    rangos = reportes.rangos()
    assert rangos["hoy"] == {"desde": date(2026, 11, 4), "hasta": date(2026, 11, 4)}
    assert rangos["esta_semana"] == {
        "desde": date(2026, 11, 2),
        "hasta": date(2026, 11, 8),
    }
    assert rangos["mes_anterior"] == {
        "desde": date(2026, 10, 1),
        "hasta": date(2026, 10, 31),
    }


def test_exportacion_xlsx_conserva_encabezados_y_datos():
    archivo = xlsx.crear(
        "consumo",
        ["periodo", "importe_soles"],
        [{"periodo": date(2026, 11, 4), "importe_soles": "12.50"}],
    )
    libro = load_workbook(BytesIO(archivo), read_only=False, data_only=True)
    hoja = libro["consumo"]
    assert list(hoja.values) == [
        ("periodo", "importe_soles"),
        (datetime(2026, 11, 4), "12.50"),
    ]
    assert hoja["A1"].font.bold is True
