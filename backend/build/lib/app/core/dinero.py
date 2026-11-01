"""Reglas de dinero y cantidades: Decimal, nunca float (plan, sección 1).

Los montos y galones viajan como cadena en el JSON (`"1500.00"`) y en la
base son `numeric(12,2)` / `numeric(14,2)`. Aquí centraliza el formato:
redondeo a 2 decimales, mitad hacia arriba (`ROUND_HALF_UP`).
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

DOS_DECIMALES = Decimal("0.01")
CERO = Decimal("0.00")


class ErrorNumero(ValueError):
    """El valor recibido no es un monto o cantidad decimal válida."""


def a_decimal(valor: Decimal | int | str | float) -> Decimal:
    """Convierte un valor de entrada a Decimal sin perder exactitud."""
    if isinstance(valor, bool):
        raise ErrorNumero("Un booleano no es un monto válido.")
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, int):
        return Decimal(valor)
    if isinstance(valor, float):
        return Decimal(str(valor))
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            raise ErrorNumero("La cadena vacía no es un monto válido.")
        try:
            return Decimal(texto)
        except InvalidOperation as exc:
            raise ErrorNumero(f"'{valor}' no es un número decimal válido.") from exc
    raise ErrorNumero(f"Tipo no soportado para montos: {type(valor).__name__}.")


def redondear(valor: Decimal | int | str | float, exp: Decimal = DOS_DECIMALES) -> Decimal:
    """Redondea a la precisión dada, mitad hacia arriba."""
    try:
        return a_decimal(valor).quantize(exp, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ErrorNumero(f"No se puede redondear '{valor}' a {exp} decimales.") from exc


def monto(valor: Decimal | int | str | float) -> Decimal:
    """Monto monetario en soles: 2 decimales, mitad hacia arriba."""
    return redondear(valor, DOS_DECIMALES)


def cantidad(valor: Decimal | int | str | float) -> Decimal:
    """Cantidad en galones: 2 decimales, mitad hacia arriba."""
    return redondear(valor, DOS_DECIMALES)


def como_texto(valor: Decimal | int | str | float, exp: Decimal = DOS_DECIMALES) -> str:
    """Serializa para el JSON de la API, por ejemplo `"1500.00"`."""
    return format(redondear(valor, exp), "f")


def es_cero(valor: Decimal | int | str | float) -> bool:
    return a_decimal(valor) == CERO


def es_negativo(valor: Decimal | int | str | float) -> bool:
    return a_decimal(valor) < CERO


def es_positivo(valor: Decimal | int | str | float) -> bool:
    return a_decimal(valor) > CERO
