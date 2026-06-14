import pytest
from uuid import UUID

from httpx import AsyncClient

from app.dependencies import get_job_dispatcher


@pytest.fixture()
def isolated_job_dispatcher(app_client: AsyncClient):
    calls: list[dict[str, object]] = []

    class FakeDispatcher:
        async def enqueue(self, job_type: str, job_id: UUID, payload: dict) -> None:
            calls.append(
                {
                    "job_type": job_type,
                    "job_id": str(job_id),
                    "payload": payload,
                }
            )

    app = app_client._transport.app
    app.dependency_overrides[get_job_dispatcher] = lambda: FakeDispatcher()
    yield calls
    app.dependency_overrides.pop(get_job_dispatcher, None)


async def test_score_jobs_endpoint_returns_tracked_job(
    app_client: AsyncClient,
    isolated_job_dispatcher,
) -> None:
    response = await app_client.post(
        "/jobs/score-papers",
        json={"limit": 3, "status": "collected", "provider": "mock"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert UUID(payload["id"])
    assert payload["job_type"] == "score-papers"
    assert payload["status"] == "queued"
    assert isolated_job_dispatcher == [
        {
            "job_type": "score-papers",
            "job_id": payload["id"],
            "payload": {"limit": 3, "status": "collected", "provider": "mock"},
        }
    ]


async def test_score_jobs_endpoint_accepts_litellm_provider(
    app_client: AsyncClient,
    isolated_job_dispatcher,
) -> None:
    response = await app_client.post(
        "/jobs/score-papers",
        json={"limit": 2, "status": "collected", "provider": "litellm"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert UUID(payload["id"])
    assert payload["job_type"] == "score-papers"
    assert payload["status"] == "queued"
    assert payload["input_json"] == {
        "limit": 2,
        "status": "collected",
        "provider": "litellm",
    }
    assert isolated_job_dispatcher == [
        {
            "job_type": "score-papers",
            "job_id": payload["id"],
            "payload": {"limit": 2, "status": "collected", "provider": "litellm"},
        }
    ]
