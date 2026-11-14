"""User management use cases."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ResourceNotFoundError
from app.core.permissions import UserRole
from app.core.security import hash_password
from app.repositories.branch_repository import BranchRepository
from app.repositories.auth_session_repository import AuthSessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserRoleUpdate, UserStatusUpdate, UserUpdate
from app.tables import User


class DuplicateUserError(AppError):
    status_code = 409
    code = "DUPLICATE_USER"


class LastActiveAdminError(AppError):
    status_code = 409
    code = "LAST_ACTIVE_ADMIN"


class UserService:
    def __init__(self) -> None:
        self.users = UserRepository()
        self.branches = BranchRepository()
        self.sessions = AuthSessionRepository()

    def create_user(self, db: Session, data: UserCreate) -> User:
        if self.users.get_by_email(db, data.email.lower()) or self.users.get_by_dni(db, data.dni):
            raise DuplicateUserError("El correo o DNI ya está registrado.")
        self._validate_branch(db, data.role, data.branch_id)
        user = User(
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            dni=data.dni.strip(),
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            role=data.role.value,
            branch_id=data.branch_id,
        )
        db.add(user)
        try:
            db.flush()
        except IntegrityError as exc:
            raise DuplicateUserError("El correo o DNI ya está registrado.") from exc
        return user

    def update_user(self, db: Session, user_id: UUID, data: UserUpdate) -> User:
        user = self.get_user(db, user_id)
        if data.first_name is not None:
            user.first_name = data.first_name.strip()
        if data.last_name is not None:
            user.last_name = data.last_name.strip()
        db.flush()
        return user

    def set_status(self, db: Session, user_id: UUID, data: UserStatusUpdate) -> User:
        user = self.get_user(db, user_id)
        if user.is_active and not data.is_active and user.role == UserRole.ADMIN.value:
            if self.users.count_active_admins(db) <= 1:
                raise LastActiveAdminError("No se puede deshabilitar el último administrador activo.")
        user.is_active = data.is_active
        if not data.is_active:
            self.sessions.revoke_all_for_user(db, user_id=user.id, now=datetime.now(UTC))
        db.flush()
        return user

    def set_role(self, db: Session, user_id: UUID, data: UserRoleUpdate) -> User:
        user = self.get_user(db, user_id)
        if user.role == UserRole.ADMIN.value and data.role != UserRole.ADMIN:
            if user.is_active and self.users.count_active_admins(db) <= 1:
                raise LastActiveAdminError("No se puede retirar el rol del último administrador activo.")
        self._validate_branch(db, data.role, data.branch_id)
        user.role = data.role.value
        user.branch_id = data.branch_id
        db.flush()
        return user

    def get_user(self, db: Session, user_id: UUID) -> User:
        user = self.users.get_by_id(db, user_id)
        if user is None:
            raise ResourceNotFoundError("Usuario no encontrado.")
        return user

    def _validate_branch(self, db: Session, role: UserRole, branch_id: UUID | None) -> None:
        if role == UserRole.ATTENDANT and branch_id is None:
            raise AppError("La sede es obligatoria para un grifero.", details={"field": "branch_id"})
        if branch_id is not None and self.branches.get_by_id(db, branch_id) is None:
            raise ResourceNotFoundError("Sede no encontrada.")
