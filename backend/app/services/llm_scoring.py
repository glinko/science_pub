from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.models.paper import Paper
from app.providers.litellm_provider import LiteLLMProvider
from app.schemas.scoring import ScoreBreakdown


def build_scoring_prompt(paper: Paper) -> str:
    authors = ", ".join(paper.authors) if paper.authors else "Unknown"
    categories = ", ".join(paper.categories) if paper.categories else "Uncategorized"

    return (
        "You are scoring a scientific paper for short-form science storytelling.\n"
        "Read the paper metadata and score each dimension from 0 to 10.\n"
        "Return valid JSON only with these keys: "
        "public_interest, visual_potential, novelty, practical_relevance, "
        "mystery, credibility, explanation.\n"
        f"Title: {paper.title}\n"
        f"Abstract: {paper.abstract}\n"
        f"Authors: {authors}\n"
        f"Categories: {categories}\n"
        "Scoring guidance:\n"
        "- public_interest: How broadly interesting or attention-grabbing this is.\n"
        "- visual_potential: How easy it is to visualize in compelling scenes.\n"
        "- novelty: How surprising, fresh, or unexpected the result feels.\n"
        "- practical_relevance: How much this could matter in the real world.\n"
        "- mystery: How much curiosity, tension, or unanswered intrigue it creates.\n"
        "- credibility: How believable and methodologically solid it appears.\n"
        "- explanation: A concise reason for the scores.\n"
    )


def parse_scoring_response(raw_text: str) -> ScoreBreakdown:
    try:
        payload = json.loads(_extract_json_payload(raw_text))
        return ScoreBreakdown.model_validate(payload)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"Invalid scoring response: {exc}") from exc


class LiteLLMPaperScorer:
    def __init__(self, provider: LiteLLMProvider, model: str) -> None:
        self.provider = provider
        self.model = model

    async def score_paper(self, paper: Paper) -> ScoreBreakdown:
        prompt = build_scoring_prompt(paper)
        raw_text = await self.provider.generate(prompt, self.model)
        return parse_scoring_response(raw_text)


def _extract_json_payload(raw_text: str) -> str:
    stripped = raw_text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fenced_match:
        return fenced_match.group(1)

    object_match = re.search(r"(\{.*\})", stripped, flags=re.DOTALL)
    if object_match:
        return object_match.group(1)

    return stripped
