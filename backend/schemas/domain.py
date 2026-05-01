import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DomainCreate(BaseModel):
    name: str


class DomainRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_active: bool
    dkim_selector: str
    spf_record: str | None = None
    dmarc_record: str | None = None
    created_at: datetime | None = None


class DNSRecordsResponse(BaseModel):
    MX: str
    A: str
    SPF: str
    DKIM: str
    DMARC: str
