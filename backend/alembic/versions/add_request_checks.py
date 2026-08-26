"""Store individual guardrail check results."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "add_request_checks"
down_revision: str | None = "add_request_log_optimization_metrics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "request_checks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("request_log_id", sa.UUID(), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("check_name", sa.String(length=64), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("corrections", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["request_log_id"], ["request_logs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_request_checks_request_log_id", "request_checks", ["request_log_id"])


def downgrade() -> None:
    op.drop_index("ix_request_checks_request_log_id", table_name="request_checks")
    op.drop_table("request_checks")