from __future__ import annotations

import httpx


class ProviderNotReadyError(RuntimeError):
    pass


class LiteLLMProvider:
    def __init__(self, base_url: str, timeout: float, default_model: str | None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.default_model = default_model

    async def generate(self, prompt: str, model: str | None = None) -> str:
        model_name = model or self.default_model
        if not model_name:
            raise ProviderNotReadyError("LiteLLM model is not configured yet.")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderNotReadyError(f"LiteLLM request failed: {exc}") from exc

        try:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderNotReadyError(
                "LiteLLM returned an unexpected response payload."
            ) from exc

    async def healthcheck(self) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health/liveliness")
                response.raise_for_status()
            return True, "ok"
        except Exception as exc:  # pragma: no cover - exercised in integration
            return False, str(exc)
