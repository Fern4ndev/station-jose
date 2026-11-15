"""User administration endpoints."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_permission
from app.database import get_db
from app.schemas.common import Pagination, UserListResponse, UserResponse
from app.schemas.user import UserCreate, UserRoleUpdate, UserStatusUpdate, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "", response_model=UserListResponse, dependencies=[Depends(require_permission("users.manage"))]
)
def list_users(
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> UserListResponse:
    items, total = UserService().list_users(db, page=page, page_size=page_size)
    return UserListResponse(
        items=[UserResponse.model_validate(item) for item in items],
        pagination=Pagination(
            page=page, page_size=page_size, total=total, pages=ceil(total / page_size)
        ),
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("users.manage"))],
)
def create_user(data: UserCreate, db: Annotated[Session, Depends(get_db)]) -> UserResponse:
    user = UserService().create_user(db, data)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("users.manage"))],
)
def get_user(user_id: UUID, db: Annotated[Session, Depends(get_db)]) -> UserResponse:
    return UserResponse.model_validate(UserService().get_user(db, user_id))


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("users.manage"))],
)
def update_user(
    user_id: UUID, data: UserUpdate, db: Annotated[Session, Depends(get_db)]
) -> UserResponse:
    user = UserService().update_user(db, user_id, data)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("users.manage"))],
)
def update_role(
    user_id: UUID, data: UserRoleUpdate, db: Annotated[Session, Depends(get_db)]
) -> UserResponse:
    user = UserService().set_role(db, user_id, data)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}/status",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("users.manage"))],
)
def update_status(
    user_id: UUID, data: UserStatusUpdate, db: Annotated[Session, Depends(get_db)]
) -> UserResponse:
    user = UserService().set_status(db, user_id, data)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)
