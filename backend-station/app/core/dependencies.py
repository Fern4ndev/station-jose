"""Reusable FastAPI authentication and authorization dependencies."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationRequiredError, PermissionDeniedError
from app.core.permissions import UserRole, permissions_for_role
from app.database import get_db
from app.services.auth_service import AuthService
from app.tables import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    if credentials is None:
        raise AuthenticationRequiredError("Se requiere autenticación.")
    return AuthService().get_user_from_token(db, credentials.credentials, settings)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(permission: str) -> Callable[[User], User]:
    def dependency(user: CurrentUser) -> User:
        if permission not in permissions_for_role(UserRole(user.role)):
            raise PermissionDeniedError("No tiene permisos para realizar esta operación.")
        return user

    return dependency
