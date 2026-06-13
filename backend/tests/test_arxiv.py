from datetime import UTC, datetime

import pytest

from app.services.arxiv import ArxivCollector


ARXIV_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2506.00001v1</id>
    <updated>2026-06-13T08:00:00Z</updated>
    <published>2026-06-13T08:00:00Z</published>
    <title>Fresh Quantum Paper</title>
    <summary>Interesting abstract</summary>
    <author><name>Jane Doe</name></author>
    <category term="quant-ph" />
    <link title="pdf" href="http://arxiv.org/pdf/2506.00001v1" />
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2506.00002v1</id>
    <updated>2026-06-01T08:00:00Z</updated>
    <published>2026-06-01T08:00:00Z</published>
    <title>Old Paper</title>
    <summary>Old abstract</summary>
    <author><name>John Doe</name></author>
    <category term="cs.AI" />
    <link title="pdf" href="http://arxiv.org/pdf/2506.00002v1" />
  </entry>
</feed>
"""


def test_arxiv_parser_keeps_only_recent_entries() -> None:
    collector = ArxivCollector(base_url="http://example.test")
    now = datetime(2026, 6, 13, 12, 0, tzinfo=UTC)

    papers = collector.parse_feed(
        xml_text=ARXIV_SAMPLE,
        requested_categories=["quant-ph", "cs.AI"],
        now=now,
    )

    assert len(papers) == 1
    assert papers[0].source_id == "2506.00001v1"
    assert papers[0].categories == ["quant-ph"]


@pytest.mark.asyncio
async def test_arxiv_collector_enables_redirect_following(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class DummyResponse:
        text = "<feed />"

        def raise_for_status(self) -> None:
            return None

    class DummyClient:
        def __init__(self, *, timeout: float, follow_redirects: bool) -> None:
            captured["timeout"] = timeout
            captured["follow_redirects"] = follow_redirects

        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str) -> DummyResponse:
            captured["url"] = url
            return DummyResponse()

    collector = ArxivCollector(base_url="http://example.test/api/query", timeout=17)
    monkeypatch.setattr("app.services.arxiv.httpx.AsyncClient", DummyClient)
    monkeypatch.setattr(collector, "parse_feed", lambda xml_text, requested_categories, now: [])

    result = await collector.collect(["cs.AI"], 3)

    assert result == []
    assert captured["timeout"] == 17
    assert captured["follow_redirects"] is True
    assert captured["url"] == collector.build_url(["cs.AI"], 3)
