from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RuleCondition(BaseModel):
    field: str
    op: str
    value: str | None = None


class RuleAction(BaseModel):
    type: str
    value: str | None = None


class RuleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    match_type: str = Field(default="any")
    conditions: list[RuleCondition]
    actions: list[RuleAction]
    priority: int = 0


class RuleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    match_type: str | None = None
    conditions: list[RuleCondition] | None = None
    actions: list[RuleAction] | None = None
    priority: int | None = None
    is_active: bool | None = None


class RuleResponse(BaseModel):
    id: str
    mailbox_id: str
    name: str
    is_active: bool
    priority: int
    match_type: str
    conditions: list[RuleCondition]
    actions: list[RuleAction]
    created_at: datetime


class RuleTestResult(BaseModel):
    uid: str
    subject: str
    would_apply: bool
    actions_that_would_run: list[str]
