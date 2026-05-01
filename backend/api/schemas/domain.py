import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    cloudflare_zone_id: str | None = None
    dns_verified: bool = False
    created_at: datetime | None = None


class DomainCreateResponse(BaseModel):
    id: uuid.UUID
    name: str
    dkim_selector: str
    dkim_public_key: str
    dns_verified: bool
    created_at: datetime | None


class DNSRecordsResponse(BaseModel):
    MX: str
    A: str
    SPF: str
    DKIM: str
    DMARC: str


class DNSAutoConfigRequest(BaseModel):
    cloudflare_zone_id: str | None = None


class DNSAutoConfigResponse(BaseModel):
    success: bool
    records_created: dict
    message: str


class DNSGuideRecord(BaseModel):
    type: str
    name: str
    value: str
    priority: str
    ttl: str
    purpose: str


class DNSGuideResponse(BaseModel):
    domain: str
    records: list[DNSGuideRecord]
    ptr_note: str
    propagation_note: str
    verify_commands: dict[str, str]


class DNSVerifyResponse(BaseModel):
    mx: bool
    a: bool
    spf: bool
    dkim: bool
    dmarc: bool
    all_valid: bool
    verified_at: datetime | None


class DomainUserCreate(BaseModel):
    local_part: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8)
    quota_mb: int = Field(default=1024, gt=0)


class DomainUserRead(BaseModel):
    id: uuid.UUID
    full_address: str
    local_part: str
    quota_mb: int
    used_mb: float
    is_active: bool
    created_at: datetime | None
