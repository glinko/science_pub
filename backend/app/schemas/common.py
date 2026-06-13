from __future__ import annotations

from pydantic import BaseModel, Field


class PaginatedResponse(BaseModel):
    total: int
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)

