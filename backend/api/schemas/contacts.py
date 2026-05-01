from datetime import datetime

from pydantic import BaseModel, Field


class ContactCreate(BaseModel):
    email: str = Field(min_length=3, max_length=319)
    name: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class ContactUpdate(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=319)
    name: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class ContactRead(BaseModel):
    id: str | None = None
    email: str
    name: str | None = None
    notes: str | None = None
    created_at: datetime | None = None
