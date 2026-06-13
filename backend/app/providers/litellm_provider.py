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
        if not (model or self.default_model):
            raise ProviderNotReadyError("LiteLLM model is not configured yet.")
        raise ProviderNotReadyError("LiteLLM inference wiring is deferred to Phase 9.")

    async def healthcheck(self) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health/liveliness")
                response.raise_for_status()
            return True, "ok"
        except Exception as exc:  # pragma: no cover - exercised in integration
            return False, str(exc)

