"""Security primitive tests."""

from uuid import uuid4

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    new_jti,
    token_expiration,
    verify_password,
)


def test_password_hash_is_not_reversible_and_verifies() -> None:
    password = "correct-horse-battery-staple"
    encoded = hash_password(password)

    assert encoded != password
    assert verify_password(password, encoded)
    assert not verify_password("wrong-password", encoded)


def test_access_token_contains_required_claims() -> None:
    settings = Settings()
    jti = new_jti()
    token = create_access_token(
        user_id=uuid4(),
        jti=jti,
        expires_at=token_expiration(settings),
        settings=settings,
    )

    payload = decode_access_token(token, settings)

    assert payload["jti"] == jti
    assert payload["iss"] == settings.jwt_issuer
