import httpx
import pytest

from app.providers.litellm_provider import LiteLLMProvider, ProviderNotReadyError


@pytest.mark.asyncio
async def test_generate_returns_first_choice_message_content_from_default_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            captured["timeout"] = kwargs["timeout"]

        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(
            self,
            url: str,
            json: dict[str, object],
            headers: dict[str, str] | None = None,
        ) -> httpx.Response:
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "choices": [
                        {
                            "message": {
                                "content": "generated text",
                            }
                        }
                    ]
                },
            )

    monkeypatch.setattr("app.providers.litellm_provider.httpx.AsyncClient", DummyClient)

    provider = LiteLLMProvider(
        base_url="http://localhost:4000",
        timeout=12.5,
        default_model="gpu/fast-small",
    )

    result = await provider.generate("Hello there")

    assert result == "generated text"
    assert captured == {
        "timeout": 12.5,
        "url": "http://localhost:4000/chat/completions",
        "json": {
            "model": "gpu/fast-small",
            "messages": [{"role": "user", "content": "Hello there"}],
        },
        "headers": {"Content-Type": "application/json"},
    }


@pytest.mark.asyncio
async def test_generate_sends_bearer_auth_header_when_api_key_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(
            self,
            url: str,
            json: dict[str, object],
            headers: dict[str, str] | None = None,
        ) -> httpx.Response:
            captured["headers"] = headers
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "choices": [
                        {
                            "message": {
                                "content": "generated text",
                            }
                        }
                    ]
                },
            )

    monkeypatch.setattr("app.providers.litellm_provider.httpx.AsyncClient", DummyClient)

    provider = LiteLLMProvider(
        base_url="http://localhost:4000",
        timeout=12.5,
        default_model="gpu/fast-small",
        api_key="science-pub-local-only",
    )

    await provider.generate("Hello there")

    assert captured["headers"] == {
        "Content-Type": "application/json",
        "Authorization": "Bearer science-pub-local-only",
    }


@pytest.mark.asyncio
async def test_generate_raises_when_litellm_response_payload_is_unexpected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(
            self,
            url: str,
            json: dict[str, object],
            headers: dict[str, str] | None = None,
        ) -> httpx.Response:
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={"choices": []},
            )

    monkeypatch.setattr("app.providers.litellm_provider.httpx.AsyncClient", DummyClient)

    provider = LiteLLMProvider(
        base_url="http://localhost:4000",
        timeout=12.5,
        default_model="gpu/fast-small",
    )

    with pytest.raises(
        ProviderNotReadyError,
        match="LiteLLM returned an unexpected response payload\\.",
    ):
        await provider.generate("Hello there")


@pytest.mark.asyncio
async def test_generate_wraps_http_errors_as_provider_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(
            self,
            url: str,
            json: dict[str, object],
            headers: dict[str, str] | None = None,
        ) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("app.providers.litellm_provider.httpx.AsyncClient", DummyClient)

    provider = LiteLLMProvider(
        base_url="http://localhost:4000",
        timeout=12.5,
        default_model="gpu/fast-small",
    )

    with pytest.raises(
        ProviderNotReadyError,
        match="LiteLLM request failed: connection refused",
    ):
        await provider.generate("Hello there")
