from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EdiscoveryExportCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, fields={"from_": "from"})

    from_: str | None = None
    to: str | None = None
    subject: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    mailboxes: list[str] | None = None



class EdiscoveryExportListItem(BaseModel):
    id: str
    domain_id: str
    requested_by: str | None
    query: dict
    status: str
    file_path: str | None = None
    total_messages: int
    created_at: datetime
    completed_at: datetime | None = None
