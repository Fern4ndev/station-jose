"""Password hashing and JWT helpers."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import Settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    return password_hash.verify(password, encoded_hash)


def create_access_token(*, user_id: UUID, jti: str, expires_at: datetime, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key.get_secret_value(), algorithm=settings.jwt_algorithm)


def token_expiration(settings: Settings) -> datetime:
    return datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)


def new_jti() -> str:
    return str(uuid4())


def decode_access_token(token: str, settings: Settings) -> dict[str, object]:
    return jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        options={"require": ["sub", "jti", "iss", "exp"]},
    )
