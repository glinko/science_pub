from __future__ import annotations

from pydantic import BaseModel


class SceneDraft(BaseModel):
    scene_number: int
    purpose: str
    narration: str
    visual_cue: str


class AnalyzeScriptDraft(BaseModel):
    technical_summary: str
    popular_summary: str
    limitations: str
    hype_risks: str
    script_text: str
    scenes: list[SceneDraft]
    model_used: str
