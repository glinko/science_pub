from fastapi import APIRouter

from .collect import router as collect_router
from .health import router as health_router
from .jobs import router as jobs_router
from .papers import router as papers_router
from .score import router as score_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(collect_router)
api_router.include_router(papers_router)
api_router.include_router(score_router)
api_router.include_router(jobs_router)

