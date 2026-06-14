from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import get_job_dispatcher, get_job_repository
from app.schemas.job import AnalyzeScriptJobRequest, CollectJobRequest, JobRequest, JobResponse
from app.services.jobs import JobRepository
from app.workers.queue import JobDispatcher

router = APIRouter()


@router.post("/jobs/collect-arxiv", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_collect_job(
    payload: CollectJobRequest,
    session: AsyncSession = Depends(get_session),
    jobs: JobRepository = Depends(get_job_repository),
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
) -> JobResponse:
    job = await jobs.create(session, job_type="collect-arxiv", payload=payload.model_dump())
    await dispatcher.enqueue("collect-arxiv", job.id, payload.model_dump())
    return jobs.to_response(job)


@router.post("/jobs/score-papers", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_score_job(
    payload: JobRequest,
    session: AsyncSession = Depends(get_session),
    jobs: JobRepository = Depends(get_job_repository),
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
) -> JobResponse:
    job = await jobs.create(session, job_type="score-papers", payload=payload.model_dump(mode="json"))
    await dispatcher.enqueue("score-papers", job.id, payload.model_dump(mode="json"))
    return jobs.to_response(job)


@router.post("/jobs/analyze-script-papers", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_analyze_script_job(
    payload: AnalyzeScriptJobRequest,
    session: AsyncSession = Depends(get_session),
    jobs: JobRepository = Depends(get_job_repository),
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
) -> JobResponse:
    data = payload.model_dump(mode="json", exclude_none=True)
    job = await jobs.create(session, job_type="analyze-script-papers", payload=data)
    await dispatcher.enqueue("analyze-script-papers", job.id, data)
    return jobs.to_response(job)


@router.get("/jobs", response_model=list[JobResponse])
async def list_jobs(
    session: AsyncSession = Depends(get_session),
    jobs: JobRepository = Depends(get_job_repository),
) -> list[JobResponse]:
    return await jobs.list_jobs(session)
