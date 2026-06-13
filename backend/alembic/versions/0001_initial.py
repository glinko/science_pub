"""Initial schema for milestone 1."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

paper_status = postgresql.ENUM(
    "collected",
    "scored",
    "selected",
    "analyzed",
    "scripted",
    "assets_ready",
    "rendered",
    "approved",
    "rejected",
    "published",
    "failed",
    name="paperstatus",
    create_type=False,
)
job_status = postgresql.ENUM(
    "queued",
    "running",
    "succeeded",
    "failed",
    name="jobstatus",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    paper_status.create(bind, checkfirst=True)
    job_status.create(bind, checkfirst=True)

    op.create_table(
        "papers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=False),
        sa.Column("authors", sa.JSON(), nullable=False),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("pdf_url", sa.String(length=1000), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", paper_status, nullable=False),
        sa.Column("raw_metadata_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("source", "source_id", name="uq_papers_source_source_id"),
    )
    op.create_table(
        "paper_scores",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("paper_id", sa.Uuid(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("public_interest", sa.Float(), nullable=False),
        sa.Column("visual_potential", sa.Float(), nullable=False),
        sa.Column("novelty", sa.Float(), nullable=False),
        sa.Column("practical_relevance", sa.Float(), nullable=False),
        sa.Column("mystery", sa.Float(), nullable=False),
        sa.Column("credibility", sa.Float(), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("model_used", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "paper_summaries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("paper_id", sa.Uuid(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("technical_summary", sa.Text(), nullable=True),
        sa.Column("popular_summary", sa.Text(), nullable=True),
        sa.Column("limitations", sa.Text(), nullable=True),
        sa.Column("hype_risks", sa.Text(), nullable=True),
        sa.Column("model_used", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "scripts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("paper_id", sa.Uuid(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", sa.String(length=50), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("script_text", sa.Text(), nullable=False),
        sa.Column("scene_json", sa.JSON(), nullable=True),
        sa.Column("model_used", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("paper_id", sa.Uuid(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=True),
        sa.Column("asset_type", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=1000), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "videos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("paper_id", sa.Uuid(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", sa.String(length=50), nullable=False),
        sa.Column("storage_path", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("youtube_url", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("jobs")
    op.drop_table("videos")
    op.drop_table("assets")
    op.drop_table("scripts")
    op.drop_table("paper_summaries")
    op.drop_table("paper_scores")
    op.drop_table("papers")
    bind = op.get_bind()
    job_status.drop(bind, checkfirst=True)
    paper_status.drop(bind, checkfirst=True)
