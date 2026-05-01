from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AiThreadMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True, fields={"from_": "from"})

    from_: str | None = None
    subject: str | None = None
    body: str | None = None
    date: datetime | str | None = None



class AiSummarizeRequest(BaseModel):
    thread_id: str | None = None
    messages: list[AiThreadMessage] | None = None


class AiSummarizeResponse(BaseModel):
    summary: str


class AiSmartReplyRequest(BaseModel):
    thread_id: str


class AiSmartReplyResponse(BaseModel):
    suggestions: list[str]


class AiPriorityEmail(BaseModel):
    model_config = ConfigDict(populate_by_name=True, fields={"from_": "from"})

    uid: int | str
    from_: str | None = None
    subject: str | None = None
    preview: str | None = None
    date: datetime | str | None = None
    priority_score: int | None = None



class AiPriorityInboxResponse(BaseModel):
    emails: list[AiPriorityEmail]


class AiSuggestLabelsRequest(BaseModel):
    email_uid: int


class AiSuggestLabelsResponse(BaseModel):
    suggestions: list[str]
