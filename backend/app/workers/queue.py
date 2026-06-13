from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from uuid import UUID

from redis import Redis
from rq import Queue

from app.config import AppSettings


class JobDispatcher(ABC):
    @abstractmethod
    async def enqueue(self, job_type: str, job_id: UUID, payload: dict) -> None:
        raise NotImplementedError


class InlineJobDispatcher(JobDispatcher):
    def __init__(self, handlers: dict[str, Callable[[UUID, dict], None]] | None = None) -> None:
        self.handlers = handlers or {}

    async def enqueue(self, job_type: str, job_id: UUID, payload: dict) -> None:
        handler = self.handlers.get(job_type)
        if handler:
            handler(job_id, payload)


class RQJobDispatcher(JobDispatcher):
    def __init__(self, redis_url: str) -> None:
        self.redis = Redis.from_url(redis_url)
        self.queue = Queue("science-pub", connection=self.redis)

    async def enqueue(self, job_type: str, job_id: UUID, payload: dict) -> None:
        from .tasks import run_collect_arxiv_job, run_score_papers_job

        handlers = {
            "collect-arxiv": run_collect_arxiv_job,
            "score-papers": run_score_papers_job,
        }
        self.queue.enqueue(handlers[job_type], str(job_id), payload, job_id=str(job_id))


def build_dispatcher(settings: AppSettings) -> JobDispatcher:
    if settings.testing:
        return InlineJobDispatcher()
    return RQJobDispatcher(settings.redis_url)

