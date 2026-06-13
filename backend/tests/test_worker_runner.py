from __future__ import annotations

from app.workers import runner


def test_worker_runner_uses_explicit_redis_connection(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class DummyRedis:
        pass

    class DummyWorker:
        def __init__(self, queues: list[str], connection: DummyRedis) -> None:
            calls["queues"] = queues
            calls["connection"] = connection

        def work(self) -> None:
            calls["worked"] = True

    class DummySettings:
        redis_url = "redis://redis:6379/0"

    redis_instance = DummyRedis()

    monkeypatch.setattr(runner, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(runner.Redis, "from_url", staticmethod(lambda url: calls.setdefault("redis_url", url) and redis_instance))
    monkeypatch.setattr(runner, "Worker", DummyWorker)

    runner.main()

    assert calls["redis_url"] == "redis://redis:6379/0"
    assert calls["queues"] == ["science-pub"]
    assert calls["worked"] is True
