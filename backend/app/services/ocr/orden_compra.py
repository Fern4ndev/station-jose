"""Extracción estructurada y conservadora de órdenes de compra escaneadas."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

ETIQUETA_RUC = re.compile(r"\bR\s*U\s*C\s*:?\s*(\d[\d\s]{9,14})", re.I)

SIAF = re.compile(r"\bN\s*[°ºo*]?\s*Exp\.?\s*S(?:IAF|UF|IF|IA)\s*:?\s*([A-Z0-9.-]{6,16})", re.I)

PARTIDA = re.compile(
    r"^\s*(\d{6,})\s+(\d+(?:[.,]\d+)?\.?)\s+([A-ZÁÉÍÓÚÜ]{2,})\s+(.+?)\s+(\d[\d.,]*)\s+(\d[\d.,]*)\s*$",
    re.I,
)

UNIDADES = {"GALON", "GALONES", "GLN", "LITRO", "LITROS", "LT", "UNIDAD", "UND"}

def decimal_texto(texto: str) -> str | None:
    """Normaliza separadores peruanos y de miles sin perder decimales."""
    limpio = texto.replace(" ", "").strip(".,")
    if not limpio:
        return None
    coma, punto = limpio.rfind(","), limpio.rfind(".")
    if coma >= 0 and punto >= 0:
        decimal = "," if coma > punto else "."
        miles = "." if decimal == "," else ","
        limpio = limpio.replace(miles, "").replace(decimal, ".")
    elif coma >= 0:
        antes, despues = limpio.rsplit(",", 1)
        limpio = (
            antes + despues
            if len(despues) == 3 and antes.lstrip("+-").isdigit()
            else antes + "." + despues
        )
    elif punto >= 0:
        antes, despues = limpio.rsplit(".", 1)
        if len(despues) == 3 and antes.lstrip("+-").isdigit():
            limpio = antes + despues
    try:
        return format(Decimal(limpio).normalize(), "f")
    except InvalidOperation:
        return None

def fecha_iso(texto: str) -> str | None:
    try:
        dia, mes, anio = (int(parte) for parte in texto.split())
        return date(anio, mes, dia).isoformat()
    except (ValueError, TypeError):
        return None

def fecha_ocr(texto: str) -> tuple[str | None, str | None]:
    """Acepta la inversión de dos dígitos del mes solo si recupera una fecha válida."""
    partes = texto.split()
    if len(partes) != 3:
        return None, None
    dia, mes, anio = (parte.translate(str.maketrans({"O": "0", "o": "0"})) for parte in partes)
    original = " ".join((dia, mes, anio))
    fecha = fecha_iso(original)
    if fecha:
        return fecha, None
    if len(mes) == 2:
        corregido = fecha_iso(" ".join((dia, mes[::-1], anio)))
        if corregido:
            return corregido, f"mes OCR {mes} invertido a {mes[::-1]}"
    return None, None

def recortar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip(" :;,.\t")

def identificador_numerico(texto: str) -> str:
    """Corrige confusiones de OCR en IDs que solo admiten dígitos."""
    traduccion = str.maketrans(
        {"O": "0", "o": "0", "C": "0", "c": "0", "I": "1", "l": "1", "S": "5"}
    )
    return re.sub(r"[^\d-]", "", texto.translate(traduccion))

def extraer_campos(texto: str, lineas: list[str]) -> dict:
    numero_fallback = None
    for linea in lineas[:12]:
        if "COMPRA" not in linea.upper():
            continue
        encontrado_numero = re.search(r"\bN\s*[°ºo*]\s*[:#]?\s*([\dOIlS.-]+)", linea, re.I)
        if encontrado_numero:
            numero_fallback = encontrado_numero.group(1)
            break
        numeros = re.findall(r"(?<!\d)\d{4,}(?:[-–]\d{2,4})?(?!\d)", linea)  # noqa: RUF001
        if numeros:
            numero_fallback = numeros[-1]
            break
    siaf = SIAF.search(texto)

    proveedor = None
    direccion_proveedor = None
    for linea in lineas:
        encontrado = re.search(
            r"(?:Se[nñ]or(?:\(es\)|es)?|SONO\s*\(O\))\s*:\s*(.+?)(?:\s+N\s*[^\w]?\s*Cuadro|$)",
            linea,
            re.I,
        )
        if encontrado:
            proveedor = recortar(encontrado.group(1))
            break
    for linea in lineas:
        encontrado = re.search(
            r"Direcci[oó]n\s*:?\s*(.+?)(?:\s+T[l1i]po\s+de\s+Proceso|\s+CCI\s*:|\s+N\s*[^\w]?\s*Cuadro|$)",
            linea,
            re.I,
        )
        if encontrado:
            direccion_proveedor = (
                recortar(
                    re.split(r"\s+R\s*U\s*C\s*:?", encontrado.group(1), maxsplit=1, flags=re.I)[0]
                )
                or None
            )
            break

    unidad = None
    fecha = None
    fecha_correccion = None
    for indice, linea in enumerate(lineas):
        if re.search(r"UNIDAD.{0,12}(?:EJECUTORA|CUTORA)", linea, re.I):
            encontrado = re.search(r"UNIDAD.{0,12}?(?:EJECUTORA|CUTORA)\s*:?\s*(.+)$", linea, re.I)
            candidato = encontrado.group(1) if encontrado else ""
            candidato = re.sub(
                r"\bNRO\.?\s*,?\s*IDENTIFICACI[ÓO]N\s*:?\s*\d+", "", candidato, flags=re.I
            )
            fecha_en_linea = re.search(r"\b(\d{1,2}\s+\d{1,2}\s+20\d{2})\b", candidato)
            if fecha_en_linea:
                fecha, fecha_correccion = fecha_ocr(fecha_en_linea.group(1))
                candidato = candidato[: fecha_en_linea.start()]
            unidad = recortar(candidato) or None
            if not fecha and re.search(
                r"D[i1l]a\s+Mes\s+A[nñN][oO]",
                " ".join(lineas[max(0, indice - 1) : indice + 2]),
                re.I,
            ):
                for cerca in lineas[indice : indice + 3]:
                    encontrada_fecha = re.search(r"\b(\d{1,2}\s+\d{1,2}\s+20\d{2})\b", cerca)
                    if encontrada_fecha:
                        fecha, fecha_correccion = fecha_ocr(encontrada_fecha.group(1))
                        break
            break
    if not fecha:
        for indice, linea in enumerate(lineas):
            if re.search(r"D[i1l]a\s+Mes\s+A[nñN][oO]", linea, re.I):
                for cerca in lineas[indice : indice + 4]:
                    encontrada_fecha = re.search(r"\b(\d{1,2}\s+\d{1,2}\s+20\d{2})\b", cerca)
                    if encontrada_fecha:
                        fecha, fecha_correccion = fecha_ocr(encontrada_fecha.group(1))
                        break
                break
    if not fecha:
        for linea in lineas[:14]:
            for coincidencia in re.finditer(r"\b(\d{1,2}\s+\d{1,2}\s+20\d{2})\b", linea):
                fecha, fecha_correccion = fecha_ocr(coincidencia.group(1))
                if fecha:
                    break
            if fecha:
                break

    ruc_proveedor = None
    proveedor_indice = next(
        (i for i, linea in enumerate(lineas) if re.search(r"DATOS DEL PROVEEDOR", linea, re.I)), 0
    )
    for linea in lineas[proveedor_indice : proveedor_indice + 8]:
        encontrado = ETIQUETA_RUC.search(linea)
        if encontrado:
            digitos = re.sub(r"\D", "", encontrado.group(1))
            if len(digitos) == 11:
                ruc_proveedor = digitos
                break

    ruc_ejecutora = None
    facturar = re.search(
        r"F(?:ac|act|at)ur\w*\s+a\s+nombre\s+de\s*:?(?P<seccion>.{0,700})", texto, re.I | re.S
    )
    if facturar:
        ruc_contexto = re.search(
            r"(?:R\s*U\s*C\s*:?\s*(\d[\d\s]{9,14})|(\d[\d\s]{9,14})\s*R\s*U\s*C|\b(\d{11})\b)",
            facturar.group("seccion").split("Agradecemos", 1)[0],
            re.I,
        )
        digitos = (
            re.sub("\\D", "", next((grupo for grupo in ruc_contexto.groups() if grupo), ""))
            if ruc_contexto
            else ""
        )
        if len(digitos) == 11:
            ruc_ejecutora = digitos

    sede = None
    if proveedor and re.search(r"SANTA\s*MART(?:A|HA)", proveedor, re.I):
        sede = "Santa Marta"
    elif proveedor and re.search(r"SAN\s+JOS[EÉ]", proveedor, re.I):
        sede = "San José"
    for linea in lineas:
        if sede:
            break
        match = re.search(r"\b(SANTA\s+MARTA|SAN\s+JOS[EÉ])\b", linea, re.I)
        if match and re.search(
            r"ESTACI[ÓO]N|SEDE|LUGAR|DIRECCI[ÓO]N|ENTREGA|SURTIDOR", linea, re.I
        ):
            sede = "Santa Marta" if "SANTA" in match.group(1).upper() else "San José"
            break

    partidas = []
    partidas_pendientes = []
    for linea in lineas:
        match = PARTIDA.match(linea)
        if not match:
            continue
        codigo, cantidad_raw, unidad_medida, descripcion, unitario_raw, total_raw = match.groups()
        if unidad_medida.upper() not in UNIDADES:
            continue
        cantidad = decimal_texto(cantidad_raw)
        precio_unitario_raw = decimal_texto(unitario_raw)
        precio_total_raw = decimal_texto(total_raw)
        precio_unitario = (
            format(Decimal(precio_unitario_raw).quantize(Decimal("0.01")), "f")
            if precio_unitario_raw
            else None
        )
        precio_total = (
            format(Decimal(precio_total_raw).quantize(Decimal("0.01")), "f")
            if precio_total_raw
            else None
        )
        if not cantidad or not precio_unitario or not precio_total:
            partidas_pendientes.append(
                {"evidencia": linea, "motivo": "No se pudieron normalizar los importes."}
            )
            continue
        cantidad_num = Decimal(cantidad)
        unitario_num = Decimal(precio_unitario)
        total_num = Decimal(precio_total)
        if not (Decimal("0") < cantidad_num < Decimal("100000")):
            partidas_pendientes.append(
                {"evidencia": linea, "motivo": "Cantidad fuera de rango razonable."}
            )
            continue
        if not (Decimal("5") <= unitario_num <= Decimal("150")):
            partidas_pendientes.append(
                {"evidencia": linea, "motivo": "Precio unitario requiere revisión."}
            )
            continue
        if abs(cantidad_num * unitario_num - total_num) > max(
            Decimal("0.05"), total_num * Decimal("0.01")
        ):
            partidas_pendientes.append(
                {
                    "evidencia": linea,
                    "motivo": "Cantidad × precio unitario no coincide con el total.",  # noqa: RUF001
                }
            )
            continue
        descripcion_limpia = recortar(descripcion).upper()
        descripcion_limpia = re.sub(r"^(?:I?DIESEL|[O0]IESEL)\b", "DIESEL", descripcion_limpia)
        descripcion_limpia = re.sub(r"\bDIESEL\s+85\b", "DIESEL B5", descripcion_limpia)
        descripcion_limpia = re.sub(r"\bSSO\b", "S50", descripcion_limpia)
        partidas.append(
            {
                "codigo": codigo,
                "cantidad": cantidad,
                "unidad_medida": unidad_medida.upper(),
                "descripcion": descripcion_limpia,
                "precio_unitario": precio_unitario,
                "precio_total": precio_total,
                "evidencia": linea,
            }
        )

    filas_vistas = set()
    partidas_unicas = []
    for partida in partidas:
        clave_fila = tuple(
            partida.get(clave)
            for clave in (
                "codigo",
                "cantidad",
                "unidad_medida",
                "descripcion",
                "precio_unitario",
                "precio_total",
            )
        )
        if clave_fila in filas_vistas:
            partidas_pendientes.append(
                {
                    "evidencia": partida["evidencia"],
                    "motivo": (
                        "Renglón idéntico repetido en el OCR; revisar si es una "
                        "página duplicada."
                    ),
                }
            )
            continue
        filas_vistas.add(clave_fila)
        partidas_unicas.append(partida)
    partidas = partidas_unicas

    warnings = []
    if not numero_fallback:
        warnings.append("No se identificó con seguridad el número de orden.")
    if not siaf:
        warnings.append("No se identificó el Exp. SIAF.")
    if not fecha:
        warnings.append("No se identificó una fecha válida.")
    if not proveedor:
        warnings.append("No se identificó el proveedor.")
    if not unidad:
        warnings.append("No se identificó la unidad ejecutora.")
    if not ruc_ejecutora:
        warnings.append("No se identificó el RUC de la unidad ejecutora (separado del proveedor).")
    if not sede:
        warnings.append("La orden no identifica explícitamente la sede Santa Marta o San José.")
    if not partidas:
        warnings.append("No se pudieron confirmar partidas de combustible; revisar tabla y OCR.")
    if partidas_pendientes:
        warnings.append(
            f"{len(partidas_pendientes)} posible(s) partida(s) excluida(s) por "
            "baja confianza o inconsistencia aritmética."
        )
    if fecha_correccion:
        warnings.append(f"Fecha corregida por patrón OCR: {fecha_correccion}; verificar en el PDF.")
    return {
        "numero_orden": identificador_numerico(numero_fallback) if numero_fallback else None,
        "numero_siaf": identificador_numerico(siaf.group(1)) if siaf else None,
        "fecha": fecha,
        "fecha_dia_mes_anio": date.fromisoformat(fecha).strftime("%d/%m/%Y") if fecha else None,
        "fecha_correccion_ocr": fecha_correccion,
        "proveedor": {
            "razon_social": proveedor,
            "ruc": ruc_proveedor,
            "direccion": direccion_proveedor,
        },
        "sede_estacion": sede,
        "unidad_ejecutora": unidad,
        "codigo_unidad_ejecutora": (
            re.match(r"\s*(\d{3})\b", unidad).group(1)
            if unidad and re.match(r"\s*(\d{3})\b", unidad)
            else None
        ),
        "ruc_unidad_ejecutora": ruc_ejecutora,
        "partidas_combustible": partidas,
        "partidas_pendientes_revision": partidas_pendientes,
        "advertencias": warnings,
    }
