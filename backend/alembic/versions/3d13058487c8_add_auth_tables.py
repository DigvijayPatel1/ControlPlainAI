"""add auth tables

Revision ID: 3d13058487c8
Revises: add_api_key_roles
Create Date: 2026-08-29 17:40:07.759744

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3d13058487c8'
down_revision: Union[str, Sequence[str], None] = 'add_api_key_roles'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Creates the `users` table backing the dashboard's JWT-authenticated
    accounts. This table was never created by any prior revision even
    though app.models.user.User (and the whole /auth/* flow) depends on
    it — the `user_role` enum type already exists from the
    add_api_key_roles revision, so it's reused here (create_type=False)
    rather than re-created.
    """
    role_enum = postgresql.ENUM("USER", "REVIEWER", "ADMIN", name="user_role", create_type=False)

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("role", role_enum, nullable=False, server_default="USER"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("default_principal_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.alter_column("users", "role", server_default=None)
    op.alter_column("users", "is_active", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")