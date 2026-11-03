"""Pruebas del evaluador del OCR (Fase 10).

Cubren la comparación documento a documento (correcto / incorrecto /
no hallado, con y sin confianza alta), las métricas agregadas por campo y
categoría, el trato de las lecturas caídas y la validación de la verdad
terreno y de la división. El pipeline real no se toca: se pasa un dict de
(campos, confianza) como lo arma `evaluar_ocr.correr`.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RUTA_SCRIPT = RAIZ / "scripts" / "evaluar_ocr.py"


def cargar_evaluar():
    """Carga el script por ruta: `scripts/` no es un paquete."""
    especifico = importlib.util.spec_from_file_location(
        "evaluar_ocr", RUTA_SCRIPT
    )
    modulo = importlib.util.module_from_spec(especifico)
    sys.modules.setdefault("evaluar_ocr", modulo)
    especifico.loader.exec_module(modulo)
    return modulo


evaluar = cargar_evaluar()

VERDAD = {
    "archivo": "ORD-0123.pdf",
    "categoria": "digital",
    "campos": {
        "numero_orden": "0018-2026",
        "fecha": "2027-03-15",
        "monto": "1500.00",
        "institucion": "Municipalidad demo del sur S.A.C.",
    },
}

CAMPOS_OK = {
    "numero_orden": ("0018-2026", 0.99),
    "fecha": ("2027-03-15", 0.99),
    "monto": ("1,500.00".replace(",", ""), 0.99),
    "institucion": ("MUNICIPALIDAD DEMO DEL SUR S.A.C.", 0.99),
}


class TestCompararDocumento:
    def test_todo_igual_es_correcto_sin_importar_mayusculas(self):
        resultado = evaluar.comparar_documento(VERDAD, CAMPOS_OK, umbral=0.80)
        assert resultado["completo"]
        assert set(resultado["campos"].values()) == {"correcto"}
        assert resultado["diferencias"] == {}

    def test_institucion_con_espacios_dobles_cuenta_igual(self):
        campos = dict(CAMPOS_OK, institucion=("MUNICIPALIDAD  DEMO DEL SUR S.A.C.", 0.9))
        resultado = evaluar.comparar_documento(VERDAD, campos, umbral=0.80)
        assert resultado["campos"]["institucion"] == "correcto"

    def test_valor_diferido_con_confianza_alta_queda_maracado(self):
        campos = dict(CAMPOS_OK, monto=("11500.00", 0.91))
        resultado = evaluar.comparar_documento(VERDAD, campos, umbral=0.80)
        assert resultado["campos"]["monto"] == "incorrecto"
        diferencia = resultado["diferencias"]["monto"]
        assert diferencia["esperado"] == "1500.00"
        assert diferencia["leido"] == "11500.00"
        assert diferencia["confianza_alta"]

    def test_la_confi_baja_marca_la_diferencia_baja(self):
        campos = dict(CAMPOS_OK, monto=("11500.00", 0.40))
        resultado = evaluar.comparar_documento(VERDAD, campos, umbral=0.80)
        assert resultado["diferencias"]["monto"]["confianza_alta"] is False

    def test_campos_vacios_son_no_hallados_y_no_completo(self):
        campos = {clave: (valor[0], valor[1]) for clave, valor in CAMPOS_OK.items()}
        campos["fecha"] = ("", 0.0)
        resultado = evaluar.comparar_documento(VERDAD, campos, umbral=0.80)
        assert resultado["campos"]["fecha"] == "no_hallado"
        assert not resultado["completo"]


def doc(
    archivo: str, categoria: str, campos: dict, estado: str = "lista", tiempo: int = 10
) -> dict:
    """Resultado documento-level como lo devuelve `evaluar_ocr.correr`."""
    return {
        "archivo": archivo,
        "categoria": categoria,
        "estado": estado,
        "motivo": "" if estado == "lista" else "OCR_TIMEOUT",
        "tiempo_ms": tiempo,
        "metodo": "ocr" if categoria != "digital" else "texto_digital",
        "campos": campos,
        "diferencias": {},
        "completo": all(v == "correcto" for v in campos.values())
        and estado == "lista",
    }


class TestResumir:
    def dos_docs(self) -> list[dict]:
        ok = {clave: "correcto" for clave in VERDAD["campos"]}
        caido = dict.fromkeys(VERDAD["campos"], "no_hallado")
        mal = dict(ok, fecha="incorrecto")
        d1 = doc("a.pdf", "digital", ok, tiempo=20)
        d2 = doc("b.jpg", "foto", caido, estado="fallida", tiempo=1000)
        d3 = doc("c.jpg", "foto", mal, tiempo=30)
        d3["diferencias"] = {"fecha": {"confianza_alta": True}}
        return [d1, d2, d3]

    def test_metricas_totales(self):
        resumen = evaluar.resumir(self.dos_docs(), metas={}, umbral=0.80)
        global_ = resumen["global"]
        assert global_["documentos"] == 3
        assert global_["listos"] == 2
        assert global_["fallidos"] == 1
        assert global_["tiempo_medio_ms"] == round((20 + 1000 + 30) / 3)

    def test_documentos_completos_pc(self):
        resumen = evaluar.resumir(self.dos_docs(), metas={}, umbral=0.80)
        assert resumen["documentos_completos_pc"] == round(1 / 3 * 100, 2)

    def test_exactitud_y_no_hallados_por_campo(self):
        resumen = evaluar.resumir(self.dos_docs(), metas={}, umbral=0.80)
        fecha = resumen["exactitud_por_campo"]["fecha"]
        # d1 correcta; d2 caída (no hallado); d3 incorrecta con confianza alta.
        assert fecha["correctos"] == 1
        assert fecha["no_hallados"] == 1
        assert fecha["incorrectos"] == 1
        assert fecha["incorrectos_confi_alta"] == 1
        assert fecha["exactitud"] == round(1 / 3, 4)

    def test_metas_marcadas_y_sin_meta(self):
        metas = {"campos": {"fecha": 0.99, "monto": None}}
        resumen = evaluar.resumir(self.dos_docs(), metas, umbral=0.80)
        assert resumen["exactitud_por_campo"]["fecha"]["cumple"] is False
        # monto sin meta declarada: cumple es None, no engaña.
        assert resumen["exactitud_por_campo"]["monto"]["cumple"] is None

    def test_desglose_por_categoria(self):
        resumen = evaluar.resumir(self.dos_docs(), metas={}, umbral=0.80)
        digital = resumen["por_categoria"]["digital"]
        foto = resumen["por_categoria"]["foto"]
        assert digital["documentos"] == 1
        assert foto["documentos"] == 2
        assert foto["fallidos"] == 1
        assert "escaneo" not in resumen["por_categoria"]


class TestCargaYDivision:
    def test_verdad_valida_se_carga(self, tmp_path: Path):
        ruta = tmp_path / "ORD-1.pdf.json"
        ruta.write_text(json.dumps(VERDAD), encoding="utf-8")
        assert evaluar.cargar_verdad(ruta)["categoria"] == "digital"

    def test_verdad_sin_claves_avisa(self, tmp_path: Path):
        ruta = tmp_path / "mal.json"
        ruta.write_text(json.dumps({"archivo": "x"}), encoding="utf-8")
        try:
            evaluar.cargar_verdad(ruta)
        except ValueError as exc:
            assert "categoria" in str(exc) and "campos" in str(exc)
        else:
            raise AssertionError("debió rechazar la verdad incompleta")

    def test_categoria_fuera_de_catalogo(self, tmp_path: Path):
        ruta = tmp_path / "mal.json"
        mala = dict(VERDAD, categoria="rayos_x")
        ruta.write_text(json.dumps(mala), encoding="utf-8")
        try:
            evaluar.cargar_verdad(ruta)
        except ValueError as exc:
            assert "escaneo" in str(exc)
        else:
            raise AssertionError("debió rechazar la categoría y notas del plan")

    def test_division_vacia_devuelve_lista_vacia(self, tmp_path: Path):
        ruta = tmp_path / "division.json"
        ruta.write_text(json.dumps({"desarrollo": [], "prueba": []}), encoding="utf-8")
        assert evaluar.cargar_division(ruta, "desarrollo") == []
