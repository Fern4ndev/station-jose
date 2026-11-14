"""Authentication session persistence operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.tables import AuthSession


class AuthSessionRepository:
    def create(self, db: Session, *, user_id: UUID, jti: str, expires_at: datetime) -> AuthSession:
        session = AuthSession(user_id=user_id, jti=jti, expires_at=expires_at)
        db.add(session)
        return session

    def get_active(self, db: Session, *, user_id: UUID, jti: str, now: datetime) -> AuthSession | None:
        return db.scalar(
            select(AuthSession).where(
                AuthSession.user_id == user_id,
                AuthSession.jti == jti,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
        )

    def revoke(self, session: AuthSession, *, now: datetime) -> None:
        session.revoked_at = now

    def revoke_all_for_user(self, db: Session, *, user_id: UUID, now: datetime) -> None:
        sessions = db.scalars(
            select(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        )
        for session in sessions:
            session.revoked_at = now
