"""Create the initial San José schema.

Revision ID: 0001_initial_schema
Revises:
"""

from collections.abc import Sequence

import app.tables  # noqa: F401
from alembic import op

from app.database import Base

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
