from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.enums import JobStatus

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


job_status_enum = Enum(
    JobStatus,
    name="jobstatus",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class JobRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "jobs"

    job_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[JobStatus] = mapped_column(job_status_enum, default=JobStatus.QUEUED)
    input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
