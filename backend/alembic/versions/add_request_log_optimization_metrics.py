"""Add prompt optimization metrics to request logs."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "add_request_log_optimization_metrics"
down_revision: str | None = "cce8e15cbb1e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("request_logs", sa.Column("original_prompt_tokens", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("request_logs", sa.Column("optimized_prompt_tokens", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("request_logs", sa.Column("tokens_saved", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("request_logs", sa.Column("savings_usd", sa.Float(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("request_logs", "savings_usd")
    op.drop_column("request_logs", "tokens_saved")
    op.drop_column("request_logs", "optimized_prompt_tokens")
    op.drop_column("request_logs", "original_prompt_tokens")
