"""add_job_execution_table

Revision ID: 9ad9e4f60fe7
Revises: ef6f70222315
Create Date: 2026-01-10 09:49:12.678608

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9ad9e4f60fe7"
down_revision: str | None = "ef6f70222315"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_executions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(length=100), nullable=False),
        sa.Column("job_name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result_data", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_executions_id"), "job_executions", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_job_executions_id"), table_name="job_executions")
    op.drop_table("job_executions")
