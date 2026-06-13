from __future__ import annotations

import json


class MockLLMProvider:
    async def generate(self, prompt: str, model: str | None = None) -> str:
        return json.dumps(
            {
                "prompt_excerpt": prompt[:80],
                "model": model or "mock",
                "note": "Mock provider does not call an external LLM.",
            }
        )

