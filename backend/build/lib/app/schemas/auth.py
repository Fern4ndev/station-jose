"""Esquemas de Pydantic de la sesión (plan, sección 5.2)."""

from pydantic import BaseModel, EmailStr, Field


class LoginPeticion(BaseModel):
    """/auth/login AUT-01: correo, contraseña y token reCAPTCHA v3."""

    correo: EmailStr
    password: str
    recaptcha_token: str = ""


class UsuarioMinimo(BaseModel):
    id: int
    nombre: str
    rol: str


class SesionRespuesta(BaseModel):
    """Respuesta de login y de cambio de contraseña exitosos."""

    access_token: str
    token_type: str = "Bearer"  # noqa: S105 - el tipo de token se declara aquí
    expira_en: int
    must_change_password: bool
    usuario: UsuarioMinimo


class PerfilUsuario(BaseModel):
    id: int
    nombre: str
    correo: str
    rol: str


class YoRespuesta(BaseModel):
    """AUT-07/08/09: usuario, rol, permisos y cambio obligatorio normalizado."""

    usuario: PerfilUsuario
    permisos: list[str]
    must_change_password: bool


class CambiarPasswordPeticion(BaseModel):
    """AUT-06: contraseña actual y nueva (mínimo 8, distinta de la actual)."""

    password_actual: str
    password_nueva: str = Field(min_length=8)


class RecuperarPeticion(BaseModel):
    """/auth/recuperar AUT-05: siempre el mismo mensaje, exista o no el correo."""

    correo: EmailStr


class RestablecerPeticion(BaseModel):
    """/auth/restablecer AUT-05/06: token de un solo uso y contraseña nueva."""

    token: str
    password_nueva: str = Field(min_length=8)


class DetalleRespuesta(BaseModel):
    detalle: str
