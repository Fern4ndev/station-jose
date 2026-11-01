"""Valores cerrados del dominio que comparten PostgreSQL, API y frontend.

Son las mismas cadenas que los tipos enum de la migración 0001; listarlas aquí
permite a `/catalogos/enums` responder sin leer la base en cada consulta.
"""

from app.core.permisos import PERMISOS as PERMISOS  # reexport para el catálogo

ROLES = ("administrador", "oficina", "despachador")

TIPOS_INSTITUCION = ("publica", "privada", "ong", "otra")
ESTADOS_INSTITUCION = ("activa", "inactiva")
MODALIDADES_NUMERACION = ("general", "por_orden", "no_aplica")

ESTADOS_ORDEN = ("borrador", "vigente", "cerrada", "anulada")

ESTADOS_OCR = ("pendiente", "procesando", "lista", "fallida", "confirmada", "descartada")
METODOS_OCR = ("texto_digital", "ocr")

EMISORES_VALE = ("estacion", "entidad")
ESTADOS_VALE = ("activo", "agotado", "vencido", "anulado")
TIPOS_MOVIMIENTO = ("emision", "consumo", "anulacion", "ajuste", "reversion")
