"""add auth tables

Revision ID: 3d13058487c8
Revises: add_api_key_roles
Create Date: 2026-08-29 17:40:07.759744

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d13058487c8'
down_revision: Union[str, Sequence[str], None] = 'add_api_key_roles'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
