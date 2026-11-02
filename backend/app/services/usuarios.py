"""Casos de uso del módulo Usuarios (M02, plan sección 5.3).

Cada caso de uso es una función sobre la sesión; el router commitea.
US-05 (activar/desactivar cuentas) no existe: el plan no define flujo de
activación y las cuentas no se borran físicamente (RN-11). La protección
del último administrador (USR-07) es un conteo SQL que se ejecuta solo
cuando el cambio de rol afecta a un administrador.
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import seguridad
from app.errors import ErrorDominio
from app.services import auditoria, sesiones

# Límite de paginación: se cota para que ninguna consulta traiga de más.
MAXIMA_POR_PAGINA = 50

CODIGO_UNICO_VIOLADO = "23505"


async def crear(
    sesion: AsyncSession,
    *,
    nombre: str,
    correo: str,
    rol: str,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> tuple[int, str]:
    """USR-01: crea la cuenta con contraseña temporal; la devuelve una vez.

    Devuelve `(id, clave_temporal)`. La cuenta nace con
    `must_change_password = TRUE` (RF-AUT-07): en el primer inicio el usuario
    debe cambiarla antes de usar el resto de la API.
    """
    clave_temporal = seguridad.generar_password_temporal()
    hash_clave = await asyncio.to_thread(seguridad.hashear_password, clave_temporal)
    try:
        fila = (
            await sesion.execute(
                text(
                    """
                    INSERT INTO app_users
                        (full_name, email, password_hash, role, must_change_password)
                    VALUES
                        (:nombre, :correo, :hash, CAST(:rol AS user_role), TRUE)
                    RETURNING id
                    """
                ),
                {
                    "nombre": nombre.strip(),
                    "correo": correo.strip().lower(),
                    "hash": hash_clave,
                    "rol": rol,
                },
            )
        ).one()
    except IntegrityError as exc:
        if getattr(exc.orig, "pgcode", None) == CODIGO_UNICO_VIOLADO:
            raise ErrorDominio(
                409,
                "CORREO_DUPLICADO",
                "Ya existe un usuario con ese correo.",
                {"correo": ["El correo ya está registrado."]},
            ) from exc
        raise
    usuario_id = int(fila.id)
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="crear_usuario",
        entidad="app_user",
        entidad_id=usuario_id,
        despues={"nombre": nombre.strip(), "correo": correo.strip().lower(), "rol": rol},
        ip=ip,
        user_agent=user_agent,
    )
    return usuario_id, clave_temporal


async def listar(
    sesion: AsyncSession,
    *,
    busqueda: str,
    rol: str | None,
    pagina: int,
    por_pagina: int,
) -> tuple[list, int]:
    """USR-02: listado paginado con búsqueda por nombre/correo y filtro de rol."""
    limite = min(por_pagina, MAXIMA_POR_PAGINA)
    filtro = busqueda.strip().lower()
    # La condición se arma con literales fijos (nada llega interpolado):
    # asyncpg no infiere el tipo de un parámetro que solo se compara con NULL.
    condicion_rol = "role = CAST(:rol AS user_role)" if rol else "TRUE"
    condicion_busqueda = (
        "(lower(full_name) LIKE '%' || :filtro || '%'"
        " OR lower(email) LIKE '%' || :filtro || '%')"
        if filtro
        else "TRUE"
    )
    # El resto de la consulta nunca trae datos del usuario: sus únicas dos
    # piezas variables son literales fijos que se ensamblan aquí.
    consulta = (
        "SELECT id, full_name, email, role, must_change_password, creado_en"  # noqa: S608
        " FROM app_users WHERE "
        + condicion_rol
        + " AND "
        + condicion_busqueda
        + " ORDER BY full_name, id LIMIT :limite OFFSET :salto"
    )
    total_consulta = (
        "SELECT count(*) FROM app_users WHERE "  # noqa: S608
        + condicion_rol
        + " AND "
        + condicion_busqueda
    )
    datos = await sesion.execute(
        text(consulta),
        {
            "rol": rol,
            "filtro": filtro,
            "limite": limite,
            "salto": (pagina - 1) * limite,
        },
    )
    total = await sesion.execute(
        text(total_consulta),
        {"rol": rol, "filtro": filtro},
    )
    filas = datos.mappings().all()
    return [dict(fila) for fila in filas], int(total.scalar_one())


async def obtener(sesion: AsyncSession, usuario_id: int) -> dict:
    """USR-02: detalle del usuario; 404 si no existe."""
    fila = (
        await sesion.execute(
            text(
                """
                SELECT id, full_name, email, role, must_change_password,
                       creado_en, ultimo_acceso_en
                FROM app_users
                WHERE id = :id
                """
            ),
            {"id": usuario_id},
        )
    ).mappings().first()
    if fila is None:
        raise ErrorDominio(404, "RECURSO_NO_ENCONTRADO", "El usuario no existe.")
    return dict(fila)


async def _protegido_ultimo_admin(sesion: AsyncSession, usuario_id: int) -> bool:
    """La cuenta es administradora y es la única: no se le puede quitar el rol (USR-07)."""
    fila = (
        await sesion.execute(
            text(
                """
                SELECT (SELECT role FROM app_users WHERE id = :id) = 'administrador'
                       AND (SELECT count(*)
                            FROM app_users
                            WHERE role = 'administrador' AND id <> :id) = 0
                """
            ),
            {"id": usuario_id},
        )
    ).scalar_one_or_none()
    return bool(fila)


async def editar(
    sesion: AsyncSession,
    usuario_id: int,
    *,
    nombre: str | None,
    correo: str | None,
    rol: str | None,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> dict:
    """USR-03/04: cambia nombre, correo o rol; protege al último administrador.

    Devuelve el detalle actualizado. El cambio de rol rige desde la
    siguiente acción del usuario, porque cada petición lee el rol de la base.
    """
    actual = await obtener(sesion, usuario_id)

    if (
        rol is not None
        and rol != actual["role"]
        and await _protegido_ultimo_admin(sesion, usuario_id)
    ):
        raise ErrorDominio(
            409,
            "ULTIMO_ADMINISTRADOR",
            "No se puede cambiar el rol del único administrador activo: el "
            "sistema quedaría sin administradores. Cree otro administrador primero.",
        )

    correo_actualizado = correo.strip().lower() if correo is not None else None
    if correo_actualizado is not None and correo_actualizado != str(actual["email"]):
        repetido = (
            await sesion.execute(
                text("SELECT id FROM app_users WHERE lower(email) = :correo AND id <> :id"),
                {"correo": correo_actualizado, "id": usuario_id},
            )
        ).first()
        if repetido is not None:
            raise ErrorDominio(
                409,
                "CORREO_DUPLICADO",
                "Ya existe un usuario con ese correo.",
                {"correo": ["El correo ya está registrado."]},
            )

    antes: dict[str, object] = {}
    despues: dict[str, object] = {}
    asignaciones: list[str] = []
    valores: dict[str, object] = {"id": usuario_id}
    if nombre is not None and nombre.strip() != str(actual["full_name"]):
        asignaciones.append("full_name = :nombre")
        valores["nombre"] = nombre.strip()
        antes["nombre"] = actual["full_name"]
        despues["nombre"] = nombre.strip()
    if correo_actualizado is not None and correo_actualizado != str(actual["email"]):
        asignaciones.append("email = :correo")
        valores["correo"] = correo_actualizado
        antes["correo"] = actual["email"]
        despues["correo"] = correo_actualizado
    if rol is not None and rol != actual["role"]:
        asignaciones.append("role = CAST(:rol AS user_role)")
        valores["rol"] = rol
        antes["rol"] = actual["role"]
        despues["rol"] = rol

    if asignaciones:
        await sesion.execute(
            text(f"UPDATE app_users SET {', '.join(asignaciones)} WHERE id = :id"),  # noqa: S608
            valores,
        )
        await auditoria.registrar(
            sesion,
            usuario_id=actor_id,
            accion="editar_usuario",
            entidad="app_user",
            entidad_id=usuario_id,
            antes=antes,
            despues=despues,
            ip=ip,
            user_agent=user_agent,
        )
    return await obtener(sesion, usuario_id)


async def restablecer_password(
    sesion: AsyncSession,
    usuario_id: int,
    *,
    admin_id: int,
    ip: str | None,
    user_agent: str | None,
) -> str:
    """USR-06: contraseña temporal mostrada una sola vez (al administrador).

    Más allá de USR-06, revoca todas las sesiones abiertas del usuario y le
    exige el cambio en su siguiente inicio (RF-AUT-07 vía must_change_password).
    """
    await obtener(sesion, usuario_id)
    clave_temporal = seguridad.generar_password_temporal()
    hash_clave = await asyncio.to_thread(seguridad.hashear_password, clave_temporal)
    await sesion.execute(
        text(
            """
            UPDATE app_users
            SET password_hash = :hash, must_change_password = TRUE
            WHERE id = :id
            """
        ),
        {"hash": hash_clave, "id": usuario_id},
    )
    # El restablecimiento cierra todas las sesiones abiertas del usuario.
    await sesiones.revocar_todas(sesion, usuario_id=usuario_id)
    await auditoria.registrar(
        sesion,
        usuario_id=admin_id,
        accion="restablecer_password_admin",
        entidad="app_user",
        entidad_id=usuario_id,
        despues={"password_temporal": True},
        ip=ip,
        user_agent=user_agent,
    )
    return clave_temporal
