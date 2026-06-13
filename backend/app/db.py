from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .config import AppSettings


class SessionManager:
    def __init__(self, settings: AppSettings) -> None:
        self.engine: AsyncEngine = create_async_engine(settings.database_url, future=True)
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def dispose(self) -> None:
        await self.engine.dispose()

    async def healthcheck(self) -> tuple[bool, str]:
        try:
            async with self.factory() as session:
                await session.execute(text("SELECT 1"))
            return True, "ok"
        except Exception as exc:  # pragma: no cover - exercised in integration
            return False, str(exc)


def build_session_manager(settings: AppSettings) -> SessionManager:
    return SessionManager(settings)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    manager: SessionManager = request.app.state.session_manager
    async with manager.factory() as session:
        yield session

