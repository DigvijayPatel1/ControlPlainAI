"""Add prompt optimization metrics to request logs.

Revision ID: a1b2c3d4e5f6
Revises: cce8e15cbb1e
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "cce8e15cbb1e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add prompt optimization metrics to request_logs."""
    op.add_column(
        "request_logs",
        sa.Column(
            "original_prompt_tokens",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "request_logs",
        sa.Column(
            "optimized_prompt_tokens",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "request_logs",
        sa.Column(
            "tokens_saved",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "request_logs",
        sa.Column(
            "savings_usd",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    """Remove prompt optimization metrics from request_logs."""
    op.drop_column("request_logs", "savings_usd")
    op.drop_column("request_logs", "tokens_saved")
    op.drop_column("request_logs", "optimized_prompt_tokens")
    op.drop_column("request_logs", "original_prompt_tokens")

