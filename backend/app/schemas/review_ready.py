from __future__ import annotations

from pydantic import BaseModel


class ReviewDraftResponse(BaseModel):
    ru_title: str
    ru_abstract: str
    summary: str
    model_used: str | None = None
