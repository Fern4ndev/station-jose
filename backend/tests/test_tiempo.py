"""Pruebas de core.tiempo: Lima con desfase fijo UTC-5 y rangos de reportes."""

from datetime import UTC, date, datetime, timedelta

from app.core.tiempo import (
    DESAFASIO_LIMA,
    ahora,
    fecha_local,
    hoy,
    inicio_de_dia,
    lunes_de,
    mes_anterior,
    mes_siguiente,
    primer_dia_de_mes,
    rango_dia,
    rango_mes,
    rango_mes_actual,
    rango_mes_anterior,
    rango_semana,
)


def test_ahora_usa_desfase_fijo_utc5():
    instante = ahora()
    assert instante.utcoffset() == DESAFASIO_LIMA


def test_hoy_es_el_dia_local():
    assert hoy() == ahora().date()


def test_fecha_local_descruza_las_24_horas_de_utc():
    # 04:30 UTC cae a las 23:30 del día anterior en Lima (UTC-5).
    instante_utc = datetime(2026, 3, 15, 4, 30, tzinfo=UTC)
    assert fecha_local(instante_utc) == date(2026, 3, 14)


def test_fecha_local_instante_sin_zona_se_interpreta_en_lima():
    assert fecha_local(datetime(2026, 3, 15, 8, 0)) == date(2026, 3, 15)


def test_rango_dia_tiene_24_horas():
    inicio, fin = rango_dia(date(2026, 10, 31))
    assert inicio == inicio_de_dia(date(2026, 10, 31))
    assert fin - inicio == timedelta(days=1)


def test_rango_semana_comienza_el_lunes():
    dia_miercoles = date(2026, 10, 21)  # miércoles
    assert lunes_de(dia_miercoles) == date(2026, 10, 19)
    inicio, fin = rango_semana(dia_miercoles)
    assert inicio.date() == date(2026, 10, 19)
    assert fin.date() == date(2026, 10, 26)


def test_rango_mes_diciembre_cruza_el_anio():
    inicio, fin = rango_mes(2026, 12)
    assert inicio == inicio_de_dia(date(2026, 12, 1))
    assert fin == inicio_de_dia(date(2027, 1, 1))


def test_meses_anterior_y_siguiente_contiguos():
    assert mes_anterior(2026, 1) == (2025, 12)
    assert mes_siguiente(2026, 12) == (2027, 1)
    assert mes_anterior(2026, 3) == (2026, 2)
    assert mes_siguiente(2026, 10) == (2026, 11)
    assert primer_dia_de_mes(2026, 2) == date(2026, 2, 1)


def test_rango_mes_anterior_termina_donde_empieza_el_mes_en_curso():
    inicio_real, _ = rango_mes_actual()
    inicio_previo, fin_previo = rango_mes_anterior()

    assert fin_previo == inicio_real
    # El mes anterior tiene el largo correcto y no pisa días del mes en curso.
    dias_previos = (fin_previo - inicio_previo).days
    assert 28 <= dias_previos <= 31
    assert inicio_previo.date() < fin_previo.date() <= inicio_real.date()
