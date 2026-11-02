"""Tiempo de operación en la zona horaria de Lima (plan, sección 1).

Lima no tiene horario de verano, así que no dependemos de las bases de zonas
horarias del sistema: se usa un desfase fijo de UTC-5. Los rangos son
abiertos al final (`[inicio, fin)`), listos para filtros `desde`/`hasta`.
"""

from datetime import date, datetime, time, timedelta, timezone

DESAFASIO_LIMA = timedelta(hours=-5)
ZONA_LIMA = timezone(DESAFASIO_LIMA, "America/Lima")


def ahora() -> datetime:
    """Instante actual en Lima, con desfase `-05:00`."""
    return datetime.now(tz=ZONA_LIMA)


def hoy() -> date:
    """Fecha local de Lima del instante actual."""
    return ahora().date()


def fecha_local(instante: datetime) -> date:
    """Agrupa un instante en su día de Lima, sea UTC u otra zona.

    Un instante sin zona se interpreta como hora de Lima (no como la zona
    local del servidor), para que los reportes no dependan de la máquina.
    """
    if instante.tzinfo is None:
        return instante.replace(tzinfo=ZONA_LIMA).date()
    return instante.astimezone(ZONA_LIMA).date()


def inicio_de_dia(dia: date) -> datetime:
    """El primer instante del día de Lima, 00:00-05:00."""
    return datetime.combine(dia, time.min, tzinfo=ZONA_LIMA)


def dia_siguiente(dia: date) -> date:
    return dia + timedelta(days=1)


def rango_dia(dia: date) -> tuple[datetime, datetime]:
    """`[00:00 del día, 00:00 del día siguiente)` en Lima."""
    inicio = inicio_de_dia(dia)
    return inicio, inicio_de_dia(dia_siguiente(dia))


def lunes_de(dia: date) -> date:
    """La semana empieza el lunes (para los reportes semanales)."""
    return dia - timedelta(days=dia.weekday())


def rango_semana(dia: date) -> tuple[datetime, datetime]:
    """`[lunes 00:00, lunes siguiente 00:00)` de la semana que contiene `dia`."""
    lunes = lunes_de(dia)
    lunes_siguiente = lunes + timedelta(days=7)
    return inicio_de_dia(lunes), inicio_de_dia(lunes_siguiente)


def primer_dia_de_mes(anio: int, mes: int) -> date:
    return date(anio, mes, 1)


def mes_siguiente(anio: int, mes: int) -> tuple[int, int]:
    """El `(año, mes)` siguiente al dado, inclusive diciembre → enero."""
    return (anio + 1, 1) if mes == 12 else (anio, mes + 1)


def mes_anterior(anio: int, mes: int) -> tuple[int, int]:
    """El `(año, mes)` anterior al dado, incluido enero → diciembre."""
    return (anio - 1, 12) if mes == 1 else (anio, mes - 1)


def rango_mes(anio: int, mes: int) -> tuple[datetime, datetime]:
    """`[día 1 00:00, día 1 del mes siguiente 00:00)` del mes dado."""
    fin_anio, fin_mes = mes_siguiente(anio, mes)
    return (
        inicio_de_dia(primer_dia_de_mes(anio, mes)),
        inicio_de_dia(primer_dia_de_mes(fin_anio, fin_mes)),
    )


def rango_mes_actual() -> tuple[datetime, datetime]:
    referencia = hoy()
    return rango_mes(referencia.year, referencia.month)


def rango_mes_anterior() -> tuple[datetime, datetime]:
    referencia = hoy()
    anio, mes = mes_anterior(referencia.year, referencia.month)
    return rango_mes(anio, mes)
