from httpx import AsyncClient


async def test_health_endpoint_returns_service_statuses(app_client: AsyncClient) -> None:
    response = await app_client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert set(payload["services"]) == {"database", "redis", "minio", "qdrant", "litellm"}


async def test_config_check_reports_warning_for_unwired_litellm(app_client: AsyncClient) -> None:
    response = await app_client.get("/config-check")

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    assert "litellm_upstream_inference_not_configured" in payload["warnings"]


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

