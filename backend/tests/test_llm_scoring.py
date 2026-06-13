from datetime import UTC, datetime

import pytest

from app.models.paper import Paper
from app.schemas.scoring import ScoreBreakdown
from app.services.llm_scoring import (
    LiteLLMPaperScorer,
    build_scoring_prompt,
    parse_scoring_response,
)


def make_paper() -> Paper:
    return Paper(
        source="arxiv",
        source_id="2606.12345v1",
        title="Learning Useful Things from Starlight",
        abstract="A study about extracting scientific signals from telescope observations.",
        authors=["Ada Lovelace", "Grace Hopper"],
        categories=["astro-ph", "cs.LG"],
        pdf_url="https://arxiv.org/pdf/2606.12345v1",
        published_at=datetime(2026, 6, 13, 12, 0, tzinfo=UTC),
        raw_metadata_json={"source": "fixture"},
    )


def test_build_scoring_prompt_mentions_dimensions_and_json_requirement() -> None:
    prompt = build_scoring_prompt(make_paper())

    assert "public_interest" in prompt
    assert "visual_potential" in prompt
    assert "novelty" in prompt
    assert "practical_relevance" in prompt
    assert "mystery" in prompt
    assert "credibility" in prompt
    assert "explanation" in prompt
    assert "Return valid JSON only" in prompt


def test_parse_scoring_response_returns_score_breakdown_from_valid_json() -> None:
    result = parse_scoring_response(
        """
        {
          "public_interest": 8.5,
          "visual_potential": 7.0,
          "novelty": 9.0,
          "practical_relevance": 6.5,
          "mystery": 5.0,
          "credibility": 8.0,
          "explanation": "Strong story with credible methods."
        }
        """
    )

    assert result == ScoreBreakdown(
        public_interest=8.5,
        visual_potential=7.0,
        novelty=9.0,
        practical_relevance=6.5,
        mystery=5.0,
        credibility=8.0,
        explanation="Strong story with credible methods.",
    )


def test_parse_scoring_response_rejects_out_of_range_values() -> None:
    with pytest.raises(ValueError, match="0"):
        parse_scoring_response(
            """
            {
              "public_interest": 11,
              "visual_potential": 7.0,
              "novelty": 9.0,
              "practical_relevance": 6.5,
              "mystery": 5.0,
              "credibility": 8.0,
              "explanation": "Invalid because one score exceeds the range."
            }
            """
        )


@pytest.mark.asyncio
async def test_score_paper_uses_provider_and_model_to_return_breakdown() -> None:
    captured: dict[str, str] = {}

    class DummyProvider:
        async def generate(self, prompt: str, model: str) -> str:
            captured["prompt"] = prompt
            captured["model"] = model
            return """
            {
              "public_interest": 8.0,
              "visual_potential": 7.5,
              "novelty": 8.5,
              "practical_relevance": 7.0,
              "mystery": 6.0,
              "credibility": 9.0,
              "explanation": "Compelling and believable research."
            }
            """

    scorer = LiteLLMPaperScorer(DummyProvider(), "gpt-test")

    result = await scorer.score_paper(make_paper())

    assert result == ScoreBreakdown(
        public_interest=8.0,
        visual_potential=7.5,
        novelty=8.5,
        practical_relevance=7.0,
        mystery=6.0,
        credibility=9.0,
        explanation="Compelling and believable research.",
    )
    assert captured["model"] == "gpt-test"
    assert "Learning Useful Things from Starlight" in captured["prompt"]
