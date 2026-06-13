from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.config import AppSettings
from app.dependencies import get_scoring_service
from app.providers.litellm_provider import ProviderNotReadyError


@pytest.fixture()
def isolated_scoring_service(app_client: AsyncClient):
    class FakeScoringService:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        async def score_papers(self, session, *, limit: int, status, provider: str) -> int:
            self.calls.append(
                {
                    "session_type": type(session).__name__,
                    "limit": limit,
                    "status": status,
                    "provider": provider,
                }
            )
            return 4

    fake_service = FakeScoringService()
    app = app_client._transport.app
    app.dependency_overrides[get_scoring_service] = lambda: fake_service
    yield fake_service
    app.dependency_overrides.pop(get_scoring_service, None)


async def test_score_papers_accepts_litellm_and_returns_provider(
    app_client: AsyncClient,
    isolated_scoring_service,
    settings: AppSettings,
) -> None:
    response = await app_client.post(
        "/score/papers",
        json={"limit": 3, "status": "collected", "provider": "litellm"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["processed"] == 4
    assert payload["provider"] == "litellm"
    assert payload["threshold"] == settings.score_threshold
    assert isolated_scoring_service.calls == [
        {
            "session_type": "AsyncSession",
            "limit": 3,
            "status": "collected",
            "provider": "litellm",
        }
    ]


async def test_score_papers_returns_503_when_provider_not_ready(app_client: AsyncClient) -> None:
    class UnreadyScoringService:
        async def score_papers(self, session, *, limit: int, status, provider: str) -> int:
            raise ProviderNotReadyError("LiteLLM model is not configured yet.")

    app = app_client._transport.app
    app.dependency_overrides[get_scoring_service] = lambda: UnreadyScoringService()
    try:
        response = await app_client.post(
            "/score/papers",
            json={"limit": 1, "status": "collected", "provider": "litellm"},
        )
    finally:
        app.dependency_overrides.pop(get_scoring_service, None)

    assert response.status_code == 503
    assert response.json() == {"detail": "LiteLLM model is not configured yet."}
