from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class TotpSetupResponse(BaseModel):
    secret: str
    qr_uri: str
    backup_codes: list[str]


class TotpCodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=10)


class TotpDisableRequest(BaseModel):
    password: str = Field(min_length=8)


class TotpVerifyResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginActivityItem(BaseModel):
    id: str
    ip_address: str
    user_agent: str | None = None
    device_type: str | None = None
    location: str | None = None
    success: bool
    failure_reason: str | None = None
    created_at: datetime
