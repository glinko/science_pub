from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import JobStatus
from app.models.job import JobRecord
from app.schemas.job import JobResponse


class JobRepository:
    async def create(
        self,
        session: AsyncSession,
        *,
        job_type: str,
        payload: dict,
    ) -> JobRecord:
        job = JobRecord(job_type=job_type, status=JobStatus.QUEUED, input_json=payload)
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job

    async def list_jobs(self, session: AsyncSession) -> list[JobResponse]:
        jobs = list((await session.scalars(select(JobRecord).order_by(JobRecord.created_at.desc()))).all())
        return [self.to_response(job) for job in jobs]

    async def mark_running(self, session: AsyncSession, job_id: UUID) -> None:
        job = await session.get(JobRecord, job_id)
        if job is None:
            return
        job.status = JobStatus.RUNNING
        await session.commit()

    async def mark_succeeded(self, session: AsyncSession, job_id: UUID, output_json: dict) -> None:
        job = await session.get(JobRecord, job_id)
        if job is None:
            return
        job.status = JobStatus.SUCCEEDED
        job.output_json = output_json
        job.error_text = None
        await session.commit()

    async def mark_failed(self, session: AsyncSession, job_id: UUID, error_text: str) -> None:
        job = await session.get(JobRecord, job_id)
        if job is None:
            return
        job.status = JobStatus.FAILED
        job.error_text = error_text
        await session.commit()

    def to_response(self, job: JobRecord) -> JobResponse:
        return JobResponse(
            id=job.id,
            job_type=job.job_type,
            status=job.status,
            input_json=job.input_json,
            output_json=job.output_json,
            error_text=job.error_text,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

