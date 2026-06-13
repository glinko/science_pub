from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> None:
    run("docker", "compose", "exec", "-T", "backend", "python", "-m", "alembic", "upgrade", "head")
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
            "asyncio.run(service.ensure_buckets())"
        ),
    )


if __name__ == "__main__":
    main()

