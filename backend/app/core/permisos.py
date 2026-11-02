"""Catálogo de roles y permisos que declara cada endpoint (plan, sección 4.1).

La matriz rol → permisos se completa en la Fase 3; aquí vive la fusión de
cadenas exactas que el endpoint `/catalogos/enums` ofrece al frontend y que
`Depends(requiere_permiso(...))` comparará.
"""

ROLES = ("administrador", "oficina", "despachador")

PERMISOS = (
    "sesion",
    "usuarios.gestionar",
    "instituciones.ver",
    "instituciones.editar",
    "instituciones.desactivar",
    "ordenes.ver",
    "ordenes.editar",
    "ordenes.anular",
    "vales.ver",
    "vales.emitir",
    "vales.anular",
    "vales.ajustar",
    "consultas.ver",
    "consumos.buscar",
    "consumos.registrar",
    "consumos.revertir",
    "reportes.ver",
    "catalogo.ver",
    "catalogo.gestionar",
    "estacion.ver",
    "ocr.usar",
    "ocr.historial",
    "historial.ver",
    "auditoria.ver",
    "config.gestionar",
)

# Matriz rol → permisos de la sección 4.1 del plan. El administrador lo tiene
# todo; oficina y despachador solo lo que la sección declara de forma
# explícita.
PERMISOS_POR_ROL: dict[str, frozenset[str]] = {
    "administrador": frozenset(PERMISOS),
    "oficina": frozenset(
        {
            "sesion",
            "instituciones.ver",
            "instituciones.editar",
            "ordenes.ver",
            "ordenes.editar",
            "vales.ver",
            "vales.emitir",
            "consultas.ver",
            "consumos.buscar",
            "consumos.registrar",
            "reportes.ver",
            "catalogo.ver",
            "estacion.ver",
            "ocr.usar",
            "historial.ver",
        }
    ),
    "despachador": frozenset(
        {"sesion", "consumos.buscar", "consumos.registrar"}
    ),
}


def permisos_del_rol(rol: str) -> tuple[str, ...]:
    """Permisos ordenados del rol, para `/auth/yo` y el menú de Angular."""
    concedidos = PERMISOS_POR_ROL.get(rol, frozenset())
    return tuple(permiso for permiso in PERMISOS if permiso in concedidos)
