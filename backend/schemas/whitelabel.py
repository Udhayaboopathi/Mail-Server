from __future__ import annotations

from pydantic import BaseModel


class WhitelabelResponse(BaseModel):
    logo_url: str | None = None
    primary_color: str | None = None
    company_name: str | None = None


class WhitelabelUpdateRequest(BaseModel):
    logo_url: str | None = None
    primary_color: str | None = None
    company_name: str | None = None
