from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import PaperStatus

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


paper_status_enum = Enum(
    PaperStatus,
    name="paperstatus",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class Paper(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "papers"
    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_papers_source_source_id"),)

    source: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500))
    abstract: Mapped[str] = mapped_column(Text)
    authors: Mapped[list[str]] = mapped_column(JSON, default=list)
    categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    pdf_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[PaperStatus] = mapped_column(paper_status_enum, default=PaperStatus.COLLECTED)
    raw_metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    scores: Mapped[list["PaperScore"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    summaries: Mapped[list["PaperSummary"]] = relationship(
        back_populates="paper",
        cascade="all, delete-orphan",
    )
    scripts: Mapped[list["Script"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    assets: Mapped[list["Asset"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    videos: Mapped[list["Video"]] = relationship(back_populates="paper", cascade="all, delete-orphan")


class PaperScore(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "paper_scores"

    paper_id: Mapped[UUID] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"))
    public_interest: Mapped[float] = mapped_column(Float)
    visual_potential: Mapped[float] = mapped_column(Float)
    novelty: Mapped[float] = mapped_column(Float)
    practical_relevance: Mapped[float] = mapped_column(Float)
    mystery: Mapped[float] = mapped_column(Float)
    credibility: Mapped[float] = mapped_column(Float)
    final_score: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text)
    model_used: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    paper: Mapped[Paper] = relationship(back_populates="scores")


class PaperSummary(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "paper_summaries"

    paper_id: Mapped[UUID] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"))
    technical_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    popular_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    hype_risks: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    paper: Mapped[Paper] = relationship(back_populates="summaries")


class Script(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "scripts"

    paper_id: Mapped[UUID] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"))
    format: Mapped[str] = mapped_column(String(50))
    language: Mapped[str] = mapped_column(String(10))
    script_text: Mapped[str] = mapped_column(Text)
    scene_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    paper: Mapped[Paper] = relationship(back_populates="scripts")


class Asset(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "assets"

    paper_id: Mapped[UUID | None] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(50))
    provider: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(1000))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    paper: Mapped[Paper | None] = relationship(back_populates="assets")


class Video(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "videos"

    paper_id: Mapped[UUID] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"))
    format: Mapped[str] = mapped_column(String(50))
    storage_path: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(50))
    youtube_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    paper: Mapped[Paper] = relationship(back_populates="videos")
