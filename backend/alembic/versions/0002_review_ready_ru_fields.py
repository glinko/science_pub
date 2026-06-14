"""Add review-ready Russian fields to paper summaries."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_review_ready_ru_fields"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("paper_summaries", sa.Column("normalized_title_ru", sa.Text(), nullable=True))
    op.add_column("paper_summaries", sa.Column("normalized_abstract_ru", sa.Text(), nullable=True))
    op.add_column("paper_summaries", sa.Column("short_summary_ru", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("paper_summaries", "short_summary_ru")
    op.drop_column("paper_summaries", "normalized_abstract_ru")
    op.drop_column("paper_summaries", "normalized_title_ru")
