"""Pruebas de la Fase 9: normalizadores, extractor y pipeline del OCR.

La lectura del motor real entra por los fixtures `oc_digital.pdf` y
`oc_foto.jpg` (generados con `scripts/fixtures_ocr.py`, datos ficticios);
las fallas del motor se simulan parchando `crear_motor` e `inferir`, de modo
que la suite no pende de que el modelo cargue rápido o lento.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from app.core.ruc import PESOS
from app.errors import ErrorDominio
from app.services.ocr import extractor, lector, normalizador, pipeline, rapidocr
from app.services.ocr.lector import Palabra
from app.services.ocr.pipeline import AjustesOcr

CATALOGO = ("Diésel B5", "Gasohol 90", "Gasohol 95", "GLP")


def _fixture(nombre: str) -> bytes:
    ruta = Path(__file__).parent / "fixtures" / nombre
    assert ruta.is_file(), f"Falta el fixture {nombre}: corre scripts/fixtures_ocr.py"
    return ruta.read_bytes()


def _ruc_valido(base: str = "20481234560") -> str:
    """RUC válido construido con el mismo algoritmo del core (módulo 11)."""
    digitos = [int(letra) for letra in base]
    suma = sum(digito * peso for digito, peso in zip(digitos[:10], PESOS, strict=True))
    resto = suma % 11
    verificador = 11 - resto
    if verificador == 10:
        verificador = 0
    elif verificador == 11:
        verificador = 1
    return base + str(verificador)


# ---------------------------------------------------------------- normalizador
@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("15/03/2027", "2027-03-15"),
        ("15-03-2027", "2027-03-15"),
        ("15.03.2027", "2027-03-15"),
        ("2027-03-15", "2027-03-15"),
        ("15 de marzo de 2027", "2027-03-15"),
        ("01 DE ENERO DE 2028", "2028-01-01"),
        # Límites: inválidas devuelven None, nunca una fecha inventada.
        ("30 de febrero de 2027", None),
        ("30.02.2027", None),
        ("15/03/27", None),  # año de 2 dígitos no se acepta
        ("", None),
    ],
)
def test_normalizar_fecha(texto: str, esperado: str | None):
    assert normalizador.normalizar_fecha(texto) == esperado


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("S/ 1,500.00", "1500.00"),
        ("S/.1500.00", "1500.00"),
        ("1.500,00", "1500.00"),
        ("1,500.00", "1500.00"),
        ("1500.5", "1500.50"),
        ("1500", "1500.00"),
        (": S/ 1,500.00", "1500.00"),  # la etiqueta quedó pegada al OCR de línea
        ("S/ -,5O0.50", "-500.50"),  # confusiones O -> 0 y signo
        ("S/ 1.500,50", "1500.50"),
        ("0.005", "0.01"),  # redondeo mitad hacia arriba
        ("sin cifra alguna", None),
        ("", None),
    ],
)
def test_normalizar_monto(texto: str, esperado: str | None):
    assert normalizador.normalizar_monto(texto) == esperado


def test_normalizar_numero_suelta_etiquetas_y_conserva_serie():
    assert normalizador.normalizar_numero("N° 0018-2026") == "0018-2026"
    assert normalizador.normalizar_numero("N° OOl8-2026") == "0018-2026"  # O/l -> 0/1
    assert normalizador.normalizar_numero("0018") == "0018"
    # La etiqueta puede quedar pegada dentro de la misma palabra del OCR.
    assert normalizador.normalizar_numero("N°: 0018-2026") == "0018-2026"


def test_normalizar_ruc_pide_el_digitos_verificadores_correctos():
    ruc = _ruc_valido()
    assert normalizador.normalizar_ruc(ruc) == ruc
    # Alterar el dígito verificador lo deja fuera.
    alterado = ruc[:-1] + str((int(ruc[-1]) + 1) % 10)
    assert normalizador.normalizar_ruc(alterado) is None


def test_normalizar_ruc_rechaza_texto_sin_digitos_de_11():
    assert normalizador.normalizar_ruc("123 parpadeo") is None
    assert normalizador.normalizar_ruc("12345678901") is None  # módulo 11 no cuadra


def test_normalizar_combustible_con_el_catalogo():
    assert normalizador.normalizar_combustible("DIESEL B5", CATALOGO) == "Diésel B5"
    assert normalizador.normalizar_combustible("gasohol 90", CATALOGO) == "Gasohol 90"
    assert normalizador.normalizar_combustible("GA-SOHOL 90", CATALOGO) == "Gasohol 90"
    assert normalizador.normalizar_combustible("Gasolina000", CATALOGO) is None
    assert normalizador.normalizar_combustible("Diésel", ()) is None  # catálogo vacío


# ------------------------------------------------------------------- extractor
def fila(texto: str, y: float, *, x0: float = 50.0, confianza: float = 0.95) -> Palabra:
    """Palabra OCR de línea completa: etiqueta y valor en la misma caja."""
    return Palabra(
        texto=texto,
        x0=x0,
        y0=y,
        x1=x0 + len(texto) * 10.0,
        y1=y + 20.0,
        confianza=confianza,
        pagina=0,
    )


def test_extraer_del_ocr_de_linea():
    # El motor suele devolver una caja por línea: la etiqueta y el valor
    # comparten palabra. El extractor debe recortar el valor a mitad de caja.
    ocr_de_linea = [
        fila("SEÑORES: INSTITUCION DEMO DEL SUR S.A.C.", 100),
        fila("ORDEN DE COMPRA N° 0018-2026", 140),
        fila("FECHA: 15/03/2027", 180),
        fila("MONTO: S/ 1,500.00", 220),
    ]
    campos = extractor.extraer(ocr_de_linea)
    assert campos["numero_orden"].valor == "0018-2026"
    assert campos["fecha"].valor == "2027-03-15"
    assert campos["monto"].valor == "1500.00"
    assert campos["institucion"].valor == "INSTITUCION DEMO DEL SUR S.A.C."
    # La confianza por campo sale de las palabras que contienen el valor.
    assert campos["numero_orden"].palabras[0].confianza == 0.95


def test_extraer_con_valor_debajo_de_la_etiqueta():
    etiqueta_separada = [
        fila("Orden de compra:", 100),
        fila("0042-2024", 140),
        fila("Fecha:", 180),
        fila("10/12/2025", 220),
        fila("Monto:", 260),
        fila("S/ 980.25", 300),
        fila("Señores:", 340),
        fila("MUNICIPALIDAD DEMO", 380),
    ]
    campos = extractor.extraer(etiqueta_separada)
    assert campos["numero_orden"].valor == "0042-2024"
    assert campos["fecha"].valor == "2025-12-10"
    assert campos["monto"].valor == "980.25"
    assert campos["institucion"].valor == "MUNICIPALIDAD DEMO"


def test_extraer_de_texto_digital_palabra_a_palabra():
    # El texto digital de pdfplumber ya trae cada palabra cortada.
    import re

    digital = []
    y = 0.0
    for texto in (
        "MUNICIPALIDAD DEMO",
        "ORDEN DE COMPRA N° 0018-2026",
        "FECHA: 15/03/2027",
        "MONTO: S/ 1,500.00",
    ):
        for palabra in texto.split():
            digital.append(
                Palabra(
                    texto=palabra,
                    x0=50.0 + (len(digital) % 10) * 10.0,
                    y0=y,
                    x1=50.0 + (len(digital) % 10) * 10.0 + len(palabra) * 8.0,
                    y1=y + 16.0,
                    confianza=lector.CONFIANZA_DIGITAL,
                    pagina=0,
                )
            )
        y += 24.0
    campos = extractor.extraer(digital)
    assert campos["numero_orden"].valor == "0018-2026"
    assert campos["fecha"].valor == "2027-03-15"
    assert campos["monto"].valor == "1500.00"
    assert campos["institucion"].valor == "MUNICIPALIDAD DEMO"
    del re  # el import acompaña a la construcción explícita de las cajas


def test_extraer_sin_pistas_deja_valores_vacios():
    campos = extractor.extraer([fila("contenido sin anclas", 100)])
    assert all(campo.valor == "" for campo in campos.values())
    assert all(campo.palabras == () for campo in campos.values())


# --------------------------------------------------------------------- lector
def test_clasificar_formato_rechaza_otros_archivos():
    with pytest.raises(ErrorDominio) as captura:
        lector.clasificar_formato(b"GIF89a no admitido")
    assert captura.value.codigo == "ARCHIVO_NO_PERMITIDO"


def test_leer_pdf_digital_termina_en_texto_digital():
    documento = lector.leer(_fixture("oc_digital.pdf"))
    assert documento.metodo == lector.TIPO_DIGITAL
    textos = " ".join(palabra.texto for palabra in documento.palabras)
    assert "0018-2026" in textos
    assert "1500.00" in textos


def test_leer_imagen_correccion_exif():
    import cv2
    import numpy as np
    from app.services.ocr.lector import _corregir_orientacion

    imagen = np.zeros((60, 120), dtype=np.uint8)
    imagen[20:40, 40:80] = 255  # un rectángulo de 80x20 se ve ancho
    derecha = _corregir_orientacion(imagen, 6)
    assert derecha.shape == (120, 60)  # después de girar, es alta


# ------------------------------------------------------------------- pipeline
AJUSTES = AjustesOcr(dpi=200, tiempo_segundos=120.0)


def test_pipeline_texto_digital():
    extraccion = pipeline.procesar(_fixture("oc_digital.pdf"), ajustes=AJUSTES)
    assert extraccion.estado == "lista"
    assert extraccion.metodo == lector.TIPO_DIGITAL
    valores = {campo.clave: campo for campo in extraccion.campos}
    assert valores["numero_orden"].valor == "0018-2026"
    assert valores["fecha"].valor == "2027-03-15"
    assert valores["monto"].valor == "1500.00"
    assert valores["institucion"].valor == "INSTITUCION DEMO DEL SUR S.A.C."
    assert all(campo.confianza == lector.CONFIANZA_DIGITAL for campo in valores.values())
    assert extraccion.advertencias == ()


def test_pipeline_foto_con_el_motor_real():
    extraccion = pipeline.procesar(_fixture("oc_foto.jpg"), ajustes=AJUSTES)
    assert extraccion.estado == "lista"
    assert extraccion.metodo == lector.TIPO_OCR
    valores = {campo.clave: campo for campo in extraccion.campos}
    assert valores["numero_orden"].valor == "0018-2026"
    assert valores["fecha"].valor == "2027-03-15"
    assert valores["monto"].valor == "1500.00"
    assert valores["institucion"].valor == "INSTITUCION DEMO DEL SUR S.A.C."
    # La confianza real del motor entra en el promedio de las palabras.
    assert all(0.5 <= campo.confianza <= 1.0 for campo in valores.values())


def test_pipeline_del_pdf_corrupto_avisa_archivo_corrupto():
    with pytest.raises(ErrorDominio) as captura:
        pipeline.procesar(b"%PDF- bola de datos inutilizable", ajustes=AJUSTES)
    assert captura.value.codigo == "ARCHIVO_CORRUPTO"


def test_pipeline_no_disponible_por_carga_fallida(monkeypatch):
    def crear_motor_fallido():
        raise RuntimeError("no se encontró el modelo")

    monkeypatch.setattr(rapidocr, "crear_motor", crear_motor_fallido)
    with pytest.raises(ErrorDominio) as captura:
        pipeline.procesar(_fixture("oc_foto.jpg"), ajustes=AJUSTES)
    assert captura.value.codigo == "OCR_NO_DISPONIBLE"
    assert captura.value.status_code == 503
    # Sin trazas internas: el mensaje estándar no expone la excepción.
    assert "RuntimeError" not in captura.value.mensaje


def test_pipeline_tiempo_agotado(monkeypatch):
    def inferir_lento(_motor, _matriz):
        import time

        time.sleep(1.0)
        return ()

    monkeypatch.setattr(rapidocr, "inferir", inferir_lento)
    try:
        extraccion = pipeline.procesar(
            _fixture("oc_foto.jpg"), ajustes=AjustesOcr(tiempo_segundos=0.05)
        )
        assert extraccion.estado == "fallida"
        assert extraccion.motivo == pipeline.MOTIVO_TIEMPO
    finally:
        rapidocr.reiniciar_motor()
        pipeline.reiniciar_concurrencia()


def test_pipeline_concurrencia_saturada():
    # Se toman los turnos del semáforo del proceso: sin turno dentro del
    # margen, el pipeline responde OCR_OCUPADO (503) sin esperar.
    try:
        semaforo = pipeline._semaphore(1)
        semaforo.acquire()
        semaforo.acquire()
        ajustes = AjustesOcr(tiempo_segundos=60.0, turno_segundos=0.05, concurrencia=1)
        with pytest.raises(ErrorDominio) as captura:
            pipeline.procesar(_fixture("oc_digital.pdf"), ajustes=ajustes)
        assert captura.value.codigo == "OCR_OCUPADO"
        assert captura.value.status_code == 503
    finally:
        pipeline.reiniciar_concurrencia()
