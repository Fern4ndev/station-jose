"""Pruebas de core.dinero: Decimal, redondeo y serialización."""

from decimal import Decimal

import pytest

from app.core.dinero import (
    ErrorNumero,
    a_decimal,
    como_texto,
    es_cero,
    es_negativo,
    es_positivo,
    monto,
)


def test_a_decimal_acepta_decimal_entero_y_cadena():
    assert a_decimal(Decimal("7.5")) == Decimal("7.5")
    assert a_decimal(7) == Decimal("7")
    assert a_decimal(" 7.500 ") == Decimal("7.500")


def test_a_decimal_convierte_float_via_str_sin_drift_binario():
    assert a_decimal(0.1) == Decimal("0.1")


def test_a_decimal_rechaza_invalidos():
    for invalido in ("abc", "", None, True, []):
        with pytest.raises(ErrorNumero):
            a_decimal(invalido)


def test_monto_redondea_a_dos_decimales_con_mitad_hacia_arriba():
    assert monto("15.805") == Decimal("15.81")
    assert monto("2.675") == Decimal("2.68")
    assert monto("0.005") == Decimal("0.01")
    assert monto("19.994") == Decimal("19.99")


def test_monto_redondeo_mitad_hacia_arriba_con_negativos_y_cero():
    # En la API nunca deben llegar acumulaciones negativas, salvo la
    # variación de un ajuste; el redondeo es idempotente sin sorpresas.
    assert monto("-2.675") == Decimal("-2.68")
    assert monto(0) == Decimal("0.00")


def test_cantidad_y_monto_son_equivalentes_a_dos_decimales():
    assert monto("100") == monto(100) == Decimal("100.00")


def test_como_texto_serializa_con_dos_decimales():
    assert como_texto("1500.00") == "1500.00"
    assert como_texto("1") == "1.00"
    assert como_texto("43.666") == "43.67"


def test_comparadores_de_signo():
    assert es_positivo("0.01")
    assert not es_negativo("0.00")
    assert es_negativo("-6.33")
    assert es_cero("0.00")
