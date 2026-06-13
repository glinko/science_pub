from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import AppSettings
from app.dependencies import get_collector, get_job_dispatcher
from app.db import get_session
from app.main import create_app
from app.models.base import Base
from app.services.arxiv import CollectedPaper
from app.workers.queue import InlineJobDispatcher


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
def settings(tmp_path: Path) -> AppSettings:
    db_path = tmp_path / "science-pub.db"
    return AppSettings(
        app_name="Science Pub Test",
        version="0.1.0-test",
        testing=True,
        database_url=f"sqlite+aiosqlite:///{db_path}",
        redis_url="redis://localhost:6379/9",
        minio_endpoint="localhost:9000",
        minio_access_key="minioadmin",
        minio_secret_key="minioadmin",
        minio_secure=False,
        qdrant_url="http://localhost:6333",
        litellm_url="http://localhost:4000",
    )


@pytest.fixture()
async def session_factory(
    settings: AppSettings,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(settings.database_url, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture()
async def app_client(
    settings: AppSettings,
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    app = create_app(settings=settings)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    class FakeCollector:
        async def collect(self, categories: list[str], max_results: int) -> list[CollectedPaper]:
            return [
                CollectedPaper(
                    source="arxiv",
                    source_id="2506.12345v1",
                    title="Synthetic test paper",
                    abstract="A deterministic fixture paper for tests.",
                    authors=["Test Author"],
                    categories=categories or ["quant-ph"],
                    pdf_url="http://arxiv.org/pdf/2506.12345v1",
                    published_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
                    raw_metadata_json={"source": "fixture"},
                )
            ]

    app.dependency_overrides[get_collector] = lambda: FakeCollector()
    app.dependency_overrides[get_job_dispatcher] = lambda: InlineJobDispatcher()

    app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
