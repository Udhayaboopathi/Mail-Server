from __future__ import annotations

from pydantic import BaseModel, Field


class PgpGenerateRequest(BaseModel):
    passphrase: str = Field(min_length=8)


class PgpKeyResponse(BaseModel):
    fingerprint: str
    public_key: str


class PgpPublicKeyResponse(BaseModel):
    public_key: str
