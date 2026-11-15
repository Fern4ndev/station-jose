"""Authentication use cases."""

from datetime import UTC, datetime
from uuid import UUID

from jwt.exceptions import PyJWTError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.permissions import permissions_for_role
from app.core.security import (
    create_access_token,
    decode_access_token,
    new_jti,
    token_expiration,
    verify_password,
)
from app.repositories.auth_session_repository import AuthSessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.common import UserResponse
from app.tables import User


class InvalidCredentialsError(AppError):
    status_code = 401
    code = "INVALID_CREDENTIALS"


class InactiveUserError(AppError):
    status_code = 401
    code = "INACTIVE_USER"


class InvalidTokenError(AppError):
    status_code = 401
    code = "INVALID_TOKEN"


class AuthService:
    def __init__(self) -> None:
        self.users = UserRepository()
        self.sessions = AuthSessionRepository()

    def login(self, db: Session, data: LoginRequest, settings: Settings) -> TokenResponse:
        user = self.users.get_by_email(db, data.email.lower())
        if user is None or not verify_password(data.password, user.password_hash):
            raise InvalidCredentialsError("Correo o contraseña inválidos.")
        if not user.is_active:
            raise InactiveUserError("La cuenta está deshabilitada.")
        expires_at = token_expiration(settings)
        jti = new_jti()
        self.sessions.create(db, user_id=user.id, jti=jti, expires_at=expires_at)
        token = create_access_token(
            user_id=user.id, jti=jti, expires_at=expires_at, settings=settings
        )
        db.commit()
        return TokenResponse(
            access_token=token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user, from_attributes=True),
            permissions=sorted(permissions_for_role(user.role)),
        )

    def get_user_from_token(self, db: Session, token: str, settings: Settings) -> User:
        try:
            payload = decode_access_token(token, settings)
            user_id = UUID(str(payload["sub"]))
            jti = str(payload["jti"])
        except (PyJWTError, ValueError, KeyError, TypeError) as exc:
            raise InvalidTokenError("El token no es válido.") from exc
        user = self.users.get_by_id(db, user_id)
        if user is None or not user.is_active:
            raise InvalidTokenError("El token no es válido.")
        session = self.sessions.get_active(db, user_id=user.id, jti=jti, now=datetime.now(UTC))
        if session is None:
            raise InvalidTokenError("La sesión no está activa.")
        return user

    def logout(self, db: Session, *, user: User, token: str, settings: Settings) -> None:
        try:
            payload = decode_access_token(token, settings)
            jti = str(payload["jti"])
        except (PyJWTError, KeyError, TypeError) as exc:
            raise InvalidTokenError("El token no es válido.") from exc
        session = self.sessions.get_active(db, user_id=user.id, jti=jti, now=datetime.now(UTC))
        if session is not None:
            self.sessions.revoke(session, now=datetime.now(UTC))
            db.commit()
