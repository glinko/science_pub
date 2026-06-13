from uuid import UUID

from httpx import AsyncClient


async def test_score_jobs_endpoint_returns_tracked_job(app_client: AsyncClient) -> None:
    response = await app_client.post(
        "/jobs/score-papers",
        json={"limit": 3, "status": "collected", "provider": "mock"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert UUID(payload["id"])
    assert payload["job_type"] == "score-papers"
    assert payload["status"] == "queued"
