import pytest
from httpx import AsyncClient

from app.dependencies import get_health_service
from app.schemas.health import ConfigCheckItem, HealthResponse, ServiceHealth


@pytest.fixture()
def isolated_health_service(app_client: AsyncClient) -> None:
    class FakeHealthService:
        async def check(self) -> HealthResponse:
            return HealthResponse(
                status="degraded",
                services={
                    "database": ServiceHealth(ok=True, detail="db-ok"),
                    "redis": ServiceHealth(ok=True, detail="redis-ok"),
                    "minio": ServiceHealth(ok=True, detail="minio-ok"),
                    "qdrant": ServiceHealth(ok=True, detail="qdrant-ok"),
                    "litellm": ServiceHealth(ok=False, detail="litellm-fake"),
                    "gpu_llm_fast": ServiceHealth(ok=True, detail="gpu-fast-fake"),
                    "gpu_llm_deep": ServiceHealth(ok=True, detail="gpu-deep-fake"),
                    "gpu_embeddings": ServiceHealth(ok=True, detail="gpu-embeddings-fake"),
                },
            )

        async def config_checks(self) -> dict[str, ConfigCheckItem]:
            return {
                "litellm": ConfigCheckItem(ok=True, required=True, detail="litellm-check"),
                "gpu_llm_fast": ConfigCheckItem(
                    ok=True,
                    required=True,
                    detail="gpu-fast-check",
                ),
                "gpu_llm_deep": ConfigCheckItem(
                    ok=True,
                    required=True,
                    detail="gpu-deep-check",
                ),
                "gpu_embeddings": ConfigCheckItem(
                    ok=True,
                    required=True,
                    detail="gpu-embeddings-check",
                ),
            }

    app = app_client._transport.app
    app.dependency_overrides[get_health_service] = lambda: FakeHealthService()
    yield
    app.dependency_overrides.pop(get_health_service, None)


async def test_health_endpoint_returns_service_statuses(
    app_client: AsyncClient,
    isolated_health_service: None,
) -> None:
    response = await app_client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert set(payload["services"]) == {
        "database",
        "redis",
        "minio",
        "qdrant",
        "litellm",
        "gpu_llm_fast",
        "gpu_llm_deep",
        "gpu_embeddings",
    }
    assert payload["services"]["litellm"]["detail"] == "litellm-fake"


async def test_config_check_reports_warning_for_unwired_litellm(
    app_client: AsyncClient,
    isolated_health_service: None,
) -> None:
    response = await app_client.get("/config-check")

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    assert "litellm_upstream_inference_not_configured" in payload["warnings"]
    assert "gpu_integrations_declared_but_not_wired" in payload["warnings"]
    assert set(payload["checks"]) == {
        "litellm",
        "gpu_llm_fast",
        "gpu_llm_deep",
        "gpu_embeddings",
    }
    for check in payload["checks"].values():
        assert set(check) == {"ok", "required", "detail"}


async def test_collect_endpoint_persists_papers(app_client: AsyncClient) -> None:
    response = await app_client.post(
        "/collect/arxiv",
        json={"categories": ["quant-ph"], "max_results": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["inserted"] >= 0
    papers_response = await app_client.get("/papers")
    assert papers_response.status_code == 200
