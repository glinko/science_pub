import os
import sys

from redis import Redis


def main() -> int:
    url = os.environ.get("SCIENCE_PUB_REDIS_URL")
    if not url:
        return 1
    Redis.from_url(url).ping()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

