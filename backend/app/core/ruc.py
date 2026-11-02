"""Validación del RUC peruano (Fase 5, plan sección 6).

Un RUC son 11 dígitos: los 10 primeros llevan el número y el último es el
dígito verificador. El plan fija el algoritmo exacto: pesos 5, 4, 3, 2, 7, 6,
5, 4, 3, 2 sobre los dígitos 1..10; el resto de la suma entre 11 define el
verificador (11 - resto, con 10 → 0 y 11 → 1).
"""

PESOS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


def es_valido(ruc: str | None) -> bool:
    """True si el RUC tiene 11 dígitos y el verificador cuadra."""
    if not ruc or not ruc.isdigit() or len(ruc) != 11:
        return False
    digitos = [int(caracter) for caracter in ruc[:10]]
    suma = sum(digito * peso for digito, peso in zip(digitos, PESOS, strict=True))
    resto = suma % 11
    verificador_calculado = 11 - resto
    if verificador_calculado == 10:
        verificador_calculado = 0
    elif verificador_calculado == 11:
        verificador_calculado = 1
    return verificador_calculado == int(ruc[10])
