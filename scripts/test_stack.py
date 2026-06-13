from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fetch_json(url: str, payload: dict | None = None, retries: int = 1, delay_seconds: float = 0.0) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if body is not None else {}
    last_error: Exception | None = None
    for attempt in range(retries):
        request = urllib.request.Request(url, data=body, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, ConnectionResetError) as exc:
            last_error = exc
            if attempt == retries - 1:
                raise
            time.sleep(delay_seconds)
    raise RuntimeError(f"request failed without exception: {last_error}")


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> None:
    fetch_json("http://127.0.0.1:8000/health", retries=12, delay_seconds=2)
    fetch_json("http://127.0.0.1:8000/version")
    fetch_json("http://127.0.0.1:8000/config-check")
    fetch_json(
        "http://127.0.0.1:8000/collect/arxiv",
        {"categories": ["cs.AI", "quant-ph"], "max_results": 5},
    )
    fetch_json("http://127.0.0.1:8000/papers?limit=5")
    fetch_json(
        "http://127.0.0.1:8000/score/papers",
        {"limit": 5, "status": "collected", "provider": "mock"},
    )
    run(
        "docker",
        "compose",
        "exec",
        "-T",
        "backend",
        "python",
        "-c",
        (
            "import asyncio; "
            "from app.config import get_settings; "
            "from app.main import build_storage_service; "
            "settings = get_settings(); "
            "service = build_storage_service(settings); "
            "result = asyncio.run(service.smoke_test()); "
            "raise SystemExit(0 if result[0] else 1)"
        ),
    )


if __name__ == "__main__":
    main()
