from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LabelCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(default="#6366f1", min_length=4, max_length=7)


class LabelUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, min_length=4, max_length=7)


class LabelResponse(BaseModel):
    id: str
    name: str
    color: str
    created_at: datetime
