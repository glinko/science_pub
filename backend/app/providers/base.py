from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    async def generate(self, prompt: str, model: str | None = None) -> str:
        ...

