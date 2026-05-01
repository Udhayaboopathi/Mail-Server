from __future__ import annotations

from pydantic import BaseModel, Field


class SpamReportRequest(BaseModel):
    email_uid: str
    from_address: str | None = None


class SpamReportResponse(BaseModel):
    status: str
