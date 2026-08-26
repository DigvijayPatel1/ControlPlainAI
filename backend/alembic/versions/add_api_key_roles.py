"""Add API-key roles for review authorization."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "add_api_key_roles"
down_revision: str | None = "add_request_checks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    role_enum = postgresql.ENUM("USER", "REVIEWER", "ADMIN", name="user_role")
    role_enum.create(op.get_bind(), checkfirst=True)
    op.add_column("api_keys", sa.Column("role", role_enum, nullable=False, server_default="USER"))
    op.alter_column("api_keys", "role", server_default=None)


def downgrade() -> None:
    op.drop_column("api_keys", "role")
    postgresql.ENUM(name="user_role").drop(op.get_bind(), checkfirst=True)
