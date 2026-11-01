"""Sesión y autenticación (M01, plan sección 5.2).

Access JWT Bearer de vida corta + refresh rotatorio en cookie HttpOnly
(Secure en producción, SameSite=Lax) bajo `/api/v1/auth`; CSRF de doble
cookie para refresh y logout. No existe ninguna ruta de registro (AUT-03).
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import obtener_settings
from app.core import seguridad, tiempo
from app.core.permisos import permisos_del_rol
from app.db.sesion import SesionBd
from app.dependencies import (
    COOKIES_CSRF,
    COOKIES_REFRESCO,
    UsuarioActualSinCambios,
    ip_de_peticion,
    proteccion_csrf,
    user_agent_de_peticion,
)
from app.errors import ErrorDominio
from app.schemas.auth import (
    CambiarPasswordPeticion,
    LoginPeticion,
    RecuperarPeticion,
    RestablecerPeticion,
)
from app.services import auditoria, correo, parametros, sesiones

# La cookie de refresco solo viaja por las rutas /auth/: nunca en el resto.
RUTA_COOKIE = "/api/v1/auth"

router = APIRouter(prefix="/auth", tags=["auth"])


def _cookies_de_sesion(
    respuesta: JSONResponse, token_refresco: str, dias: int
) -> JSONResponse:
    ajustes = obtener_settings()
    respuesta.set_cookie(
        key=COOKIES_REFRESCO,
        value=token_refresco,
        httponly=True,
        secure=not ajustes.es_desarrollo,
        samesite="lax",
        path=RUTA_COOKIE,
        max_age=dias * 24 * 3600,
    )
    respuesta.set_cookie(
        key=COOKIES_CSRF,
        value=seguridad.generar_token_csrf(),
        httponly=False,
        secure=not ajustes.es_desarrollo,
        samesite="lax",
        path="/",
        max_age=dias * 24 * 3600,
    )
    return respuesta


def _cuerpo_sesion(nueva: sesiones.SesionEmitida) -> dict:
    return {
        "access_token": nueva.access_token,
        "token_type": "Bearer",
        "expira_en": nueva.segundos_access,
        "must_change_password": nueva.debe_cambiar_password,
        "usuario": {
            "id": nueva.usuario_id,
            "nombre": nueva.nombre,
            "rol": nueva.rol,
        },
    }


@router.post("/login")
async def login(peticion: LoginPeticion, request: Request, sesion: SesionBd) -> JSONResponse:
    """AUT-01/04: verifica reCAPTCHA, límite de intentos y credenciales."""
    ip = ip_de_peticion(request)
    agent = user_agent_de_peticion(request)

    if not await sesiones.verificar_recaptcha(
        peticion.recaptcha_token, request.headers.get("host")
    ):
        raise ErrorDominio(
            401, "CREDENCIALES_INVALIDAS", "Verificación reCAPTCHA rechazada."
        )

    bloqueo = await sesiones.minutos_bloqueo_restantes(sesion, peticion.correo)
    if bloqueo is not None:
        await sesiones.registrar_intento(
            sesion, correo=peticion.correo, ip=ip, exitoso=False, motivo="bloqueo"
        )
        await sesiones.registrar_login_en_auditoria(
            sesion,
            usuario_id=None,
            accion="iniciar_sesion_bloqueado",
            correo=peticion.correo,
            ip=ip,
            user_agent=agent,
        )
        await sesion.commit()
        raise ErrorDominio(
            400,
            "CUENTA_BLOQUEADA",
            f"Demasiados intentos fallidos. Intente nuevamente en {bloqueo} minutos.",
            {"minutos_espera": bloqueo},
        )

    usuario = await sesiones.usuario_por_correo(sesion, peticion.correo)
    # La comparación es idéntica y tarda lo suyo también para correo ausente,
    # para no revelar cuál dato falló (AUT-01).
    contrasena_ok = (
        usuario is not None
        and await sesiones.verificar_password(
            peticion.password, str(usuario["password_hash"])
        )
    )
    if not contrasena_ok:
        await sesiones.registrar_intento(
            sesion, correo=peticion.correo, ip=ip, exitoso=False, motivo="credenciales"
        )
        await sesiones.registrar_login_en_auditoria(
            sesion,
            usuario_id=int(usuario["id"]) if usuario else None,
            accion="iniciar_sesion_fallido",
            correo=peticion.correo,
            ip=ip,
            user_agent=agent,
        )
        await sesion.commit()
        raise ErrorDominio(401, "CREDENCIALES_INVALIDAS", "Correo o contraseña incorrectos.")

    debe_cambiar = bool(usuario["must_change_password"])
    nueva = await sesiones.emitir_sesion(
        sesion,
        usuario_id=int(usuario["id"]),
        nombre=str(usuario["full_name"]),
        rol=str(usuario["role"]),
        debe_cambiar_password=debe_cambiar,
        ip=ip,
        user_agent=agent,
    )
    await sesiones.registrar_intento(
        sesion, correo=peticion.correo, ip=ip, exitoso=True
    )
    await sesiones.registrar_login_en_auditoria(
        sesion,
        usuario_id=int(usuario["id"]),
        accion="iniciar_sesion",
        correo=peticion.correo,
        ip=ip,
        user_agent=agent,
    )
    await sesion.execute(
        text("UPDATE app_users SET ultimo_acceso_en = :ahora WHERE id = :id"),
        {"id": int(usuario["id"]), "ahora": tiempo.ahora()},
    )
    await sesion.commit()
    dias_refresh = max(1, await parametros.numero(sesion, "refresh_token_dias"))
    return _cookies_de_sesion(
        JSONResponse(content=_cuerpo_sesion(nueva), status_code=200),
        nueva.token_refresco,
        dias_refresh,
    )


@router.post("/refresh", dependencies=[Depends(proteccion_csrf)])
async def refresh(request: Request, sesion: SesionBd) -> JSONResponse:
    """AUT-10: rota el refresh token; la reutilización revoca la familia."""
    token_cookie = request.cookies.get(COOKIES_REFRESCO)
    if not token_cookie:
        raise ErrorDominio(401, "TOKEN_INVALIDO", "No hay sesión de refresco.")

    nueva = await sesiones.rotar_refresh(
        sesion,
        token_actual=token_cookie,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    if nueva is None:
        await sesion.commit()
        raise ErrorDominio(
            401,
            "TOKEN_INVALIDO",
            "El refresh token no es válido, está revocado o fue reutilizado.",
        )
    await sesion.commit()
    dias_refresh = max(1, await parametros.numero(sesion, "refresh_token_dias"))
    return _cookies_de_sesion(
        JSONResponse(content=_cuerpo_sesion(nueva), status_code=200),
        nueva.token_refresco,
        dias_refresh,
    )


@router.post("/logout", dependencies=[Depends(proteccion_csrf)])
async def logout(
    usuario: UsuarioActualSinCambios, request: Request, sesion: SesionBd
) -> JSONResponse:
    """AUT-02: revoca la familia de refresh tokens y deja inerte el access JWT."""
    if usuario.familia_id:
        await sesiones.revocar_familia(sesion, familia_id=usuario.familia_id)
    await auditoria.registrar(
        sesion,
        usuario_id=usuario.id,
        accion="cerrar_sesion",
        entidad="app_user",
        entidad_id=usuario.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    respuesta = JSONResponse(content={"detalle": "sesion_cerrada"}, status_code=200)
    respuesta.delete_cookie(COOKIES_REFRESCO, path=RUTA_COOKIE)
    respuesta.delete_cookie(COOKIES_CSRF, path="/")
    return respuesta


@router.get("/yo")
async def yo(usuario: UsuarioActualSinCambios, sesion: SesionBd) -> dict:
    """AUT-07/08/09: usuario, rol, permisos del rol y cambio obligatorio."""
    return {
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "correo": usuario.correo,
            "rol": usuario.rol,
        },
        "permisos": list(permisos_del_rol(usuario.rol)),
        "must_change_password": usuario.debe_cambiar_password,
    }


@router.post("/recuperar")
async def recuperar(peticion: RecuperarPeticion, request: Request, sesion: SesionBd) -> dict:
    """AUT-05: token de un solo uso; respuesta idéntica exista o no el correo."""
    usuario = await sesiones.usuario_por_correo(sesion, peticion.correo)
    if usuario is not None:
        ajustes = obtener_settings()
        token = seguridad.generar_token_opaco()
        expira = tiempo.ahora() + timedelta(minutes=ajustes.recuperacion_token_minutos)
        await sesion.execute(
            text(
                """
                INSERT INTO tokens_recuperacion (app_user_id, token_hash, expira_en)
                VALUES (:usuario_id, :hash, :expira)
                """
            ),
            {
                "usuario_id": int(usuario["id"]),
                "hash": seguridad.hash_opaco(token),
                "expira": expira,
            },
        )
        base = ajustes.frontend_url.strip().rstrip("/")
        enlace = (
            f"{base}/restablecer?token={token}"
            if base
            else f"/restablecer?token={token} (configure FRONTEND_URL para el dominio)"
        )
        await respuesta_correo(peticion.correo, enlace)
        await sesion.commit()
    return {
        "detalle": "Si el correo está registrado, recibirá la instrucción de restablecimiento."
    }


async def respuesta_correo(destinatario: str, enlace: str) -> None:
    """P-08: con SMTP envía; sin SMTP imprime el enlace en la consola."""
    await correo.enviar_enlace_recuperacion(destinatario, enlace)


@router.post("/restablecer")
async def restablecer(
    peticion: RestablecerPeticion, request: Request, sesion: SesionBd
) -> dict:
    """AUT-05/06: consume el token y fija la nueva contraseña (un solo uso)."""
    filas = await sesion.execute(
        text(
            """
            SELECT tr.id, tr.expira_en, tr.usado_en, u.id AS usuario_id, u.email
            FROM tokens_recuperacion tr
            JOIN app_users u ON u.id = tr.app_user_id
            WHERE tr.token_hash = :hash
            """
        ),
        {"hash": seguridad.hash_opaco(peticion.token.strip())},
    )
    fila = filas.mappings().first()
    if (
        fila is None
        or fila["usado_en"] is not None
        or fila["expira_en"] <= tiempo.ahora()
    ):
        raise ErrorDominio(400, "TOKEN_INVALIDO", "El enlace no es válido o ya expiró.")

    hash_nuevo = seguridad.hashear_password(peticion.password_nueva)
    ahora = tiempo.ahora()
    await sesion.execute(
        text(
            """
            UPDATE app_users
            SET password_hash = :hash, must_change_password = NULL,
                password_cambiado_en = :ahora
            WHERE id = :usuario_id
            """
        ),
        {"hash": hash_nuevo, "usuario_id": int(fila["usuario_id"]), "ahora": ahora},
    )
    await sesion.execute(
        text("UPDATE tokens_recuperacion SET usado_en = :ahora WHERE id = :id"),
        {"id": int(fila["id"]), "ahora": ahora},
    )
    await sesiones.revocar_todas(sesion, usuario_id=int(fila["usuario_id"]))
    await auditoria.registrar(
        sesion,
        usuario_id=int(fila["usuario_id"]),
        accion="restablecer_password",
        entidad="app_user",
        entidad_id=int(fila["usuario_id"]),
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return {"detalle": "La contraseña se actualizó. Inicie sesión con la nueva."}


@router.post("/cambiar-password")
async def cambiar_password(
    peticion: CambiarPasswordPeticion,
    usuario: UsuarioActualSinCambios,
    request: Request,
    sesion: SesionBd,
) -> JSONResponse:
    """AUT-06/07: exige la contraseña actual; nueva de mínimo 8 y distinta."""
    filas = await sesion.execute(
        text("SELECT password_hash FROM app_users WHERE id = :id"),
        {"id": usuario.id},
    )
    hash_actual = filas.scalar_one()
    if not await sesiones.verificar_password(peticion.password_actual, str(hash_actual)):
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"password_actual": ["La contraseña actual no es correcta."]},
        )
    if peticion.password_nueva == peticion.password_actual:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"password_nueva": ["La nueva contraseña debe ser distinta de la actual."]},
        )

    ahora = tiempo.ahora()
    await sesion.execute(
        text(
            """
            UPDATE app_users
            SET password_hash = :hash, must_change_password = NULL,
                password_cambiado_en = :ahora
            WHERE id = :id
            """
        ),
        {
            "hash": seguridad.hashear_password(peticion.password_nueva),
            "id": usuario.id,
            "ahora": ahora,
        },
    )
    if usuario.familia_id:
        # El cambio de contraseña invalida la familia actual (plan, sección 1).
        await sesiones.revocar_familia(sesion, familia_id=usuario.familia_id)
    dias_refresh = max(1, await parametros.numero(sesion, "refresh_token_dias"))
    nueva = await sesiones.emitir_sesion(
        sesion,
        usuario_id=usuario.id,
        nombre=usuario.nombre,
        rol=usuario.rol,
        debe_cambiar_password=False,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await auditoria.registrar(
        sesion,
        usuario_id=usuario.id,
        accion="cambiar_password",
        entidad="app_user",
        entidad_id=usuario.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return _cookies_de_sesion(
        JSONResponse(content=_cuerpo_sesion(nueva), status_code=200),
        nueva.token_refresco,
        dias_refresh,
    )
