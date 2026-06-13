from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from xml.etree import ElementTree

import httpx


ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


@dataclass(slots=True)
class CollectedPaper:
    source: str
    source_id: str
    title: str
    abstract: str
    authors: list[str]
    categories: list[str]
    pdf_url: str | None
    published_at: datetime
    raw_metadata_json: dict


class ArxivCollector:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url
        self.timeout = timeout

    def build_url(self, categories: list[str], max_results: int) -> str:
        categories = categories or ["cs.AI"]
        search_terms = " OR ".join(f"cat:{category}" for category in categories)
        query = urlencode(
            {
                "search_query": search_terms,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "max_results": max_results,
            }
        )
        return f"{self.base_url}?{query}"

    async def collect(self, categories: list[str], max_results: int) -> list[CollectedPaper]:
        url = self.build_url(categories, max_results)
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
        return self.parse_feed(response.text, categories, now=datetime.now(UTC))

    def parse_feed(
        self,
        xml_text: str,
        requested_categories: list[str],
        now: datetime,
    ) -> list[CollectedPaper]:
        requested_categories = requested_categories or ["cs.AI"]
        threshold = now - timedelta(hours=24)
        root = ElementTree.fromstring(xml_text)
        parsed: list[CollectedPaper] = []
        for entry in root.findall("atom:entry", ATOM_NS):
            published_text = entry.findtext("atom:published", default="", namespaces=ATOM_NS)
            published_at = datetime.fromisoformat(published_text.replace("Z", "+00:00"))
            if published_at < threshold:
                continue
            categories = [
                category.attrib["term"]
                for category in entry.findall("atom:category", ATOM_NS)
                if category.attrib.get("term")
            ]
            if not set(categories).intersection(requested_categories):
                continue
            identifier = entry.findtext("atom:id", default="", namespaces=ATOM_NS).rstrip("/").split("/")[-1]
            authors = [
                author.findtext("atom:name", default="", namespaces=ATOM_NS)
                for author in entry.findall("atom:author", ATOM_NS)
            ]
            pdf_url = None
            for link in entry.findall("atom:link", ATOM_NS):
                if link.attrib.get("title") == "pdf":
                    pdf_url = link.attrib.get("href")
                    break
            parsed.append(
                CollectedPaper(
                    source="arxiv",
                    source_id=identifier,
                    title=(entry.findtext("atom:title", default="", namespaces=ATOM_NS) or "").strip(),
                    abstract=(entry.findtext("atom:summary", default="", namespaces=ATOM_NS) or "").strip(),
                    authors=[author for author in authors if author],
                    categories=categories,
                    pdf_url=pdf_url,
                    published_at=published_at,
                    raw_metadata_json={
                        "id": identifier,
                        "authors": authors,
                        "categories": categories,
                    },
                )
            )
        return parsed
