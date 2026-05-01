from __future__ import annotations

from email import message_from_bytes
from email.policy import default

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_user_mailbox
from imap.maildir import MaildirBackend
from schemas.rules import RuleCreateRequest, RuleResponse, RuleTestResult, RuleUpdateRequest
from services.rules_service import _condition_matches

router = APIRouter(tags=["rules"])

_backend = MaildirBackend()


def _message_body(raw: bytes | None) -> str:
    if not raw:
        return ""
    msg = message_from_bytes(raw, policy=default)
    body = msg.get_body(preferencelist=("plain",))
    if body:
        return body.get_content()
    payload = msg.get_payload()
    if isinstance(payload, str):
        return payload
    return ""


@router.get("", response_model=list[RuleResponse])
async def list_rules(mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> list[RuleResponse]:
    result = await db.execute(
        text("SELECT * FROM email_rules WHERE mailbox_id = :mailbox_id ORDER BY priority ASC, created_at ASC"),
        {"mailbox_id": str(mailbox.id)},
    )
    return [RuleResponse(**row) for row in result.mappings().all()]


@router.post("", response_model=RuleResponse)
async def create_rule(payload: RuleCreateRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> RuleResponse:
    result = await db.execute(
        text(
            """
            INSERT INTO email_rules (mailbox_id, name, is_active, priority, match_type, conditions, actions, created_at)
            VALUES (:mailbox_id, :name, true, :priority, :match_type, CAST(:conditions AS jsonb), CAST(:actions AS jsonb), now())
            RETURNING *
            """
        ),
        {
            "mailbox_id": str(mailbox.id),
            "name": payload.name,
            "priority": payload.priority,
            "match_type": payload.match_type,
            "conditions": payload.conditions,
            "actions": payload.actions,
        },
    )
    row = result.mappings().first()
    await db.commit()
    return RuleResponse(**row)


@router.patch("/{rule_id}", response_model=RuleResponse)
async def update_rule(rule_id: str, payload: RuleUpdateRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> RuleResponse:
    result = await db.execute(
        text(
            """
            UPDATE email_rules
            SET name = COALESCE(:name, name),
                is_active = COALESCE(:is_active, is_active),
                priority = COALESCE(:priority, priority),
                match_type = COALESCE(:match_type, match_type),
                conditions = COALESCE(CAST(:conditions AS jsonb), conditions),
                actions = COALESCE(CAST(:actions AS jsonb), actions)
            WHERE id = :rule_id AND mailbox_id = :mailbox_id
            RETURNING *
            """
        ),
        {
            "rule_id": rule_id,
            "mailbox_id": str(mailbox.id),
            "name": payload.name,
            "is_active": payload.is_active,
            "priority": payload.priority,
            "match_type": payload.match_type,
            "conditions": payload.conditions,
            "actions": payload.actions,
        },
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    await db.commit()
    return RuleResponse(**row)


@router.delete("/{rule_id}")
async def delete_rule(rule_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(
        text("DELETE FROM email_rules WHERE id = :rule_id AND mailbox_id = :mailbox_id"),
        {"rule_id": rule_id, "mailbox_id": str(mailbox.id)},
    )
    await db.commit()
    return {"status": "deleted"}


@router.post("/{rule_id}/test", response_model=list[RuleTestResult])
async def test_rule(rule_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> list[RuleTestResult]:
    result = await db.execute(
        text("SELECT match_type, conditions, actions FROM email_rules WHERE id = :rule_id AND mailbox_id = :mailbox_id"),
        {"rule_id": rule_id, "mailbox_id": str(mailbox.id)},
    )
    rule = result.mappings().first()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    conditions = rule.get("conditions") or []
    match_type = str(rule.get("match_type") or "any")
    action_types = [action.get("type") for action in (rule.get("actions") or []) if action.get("type")]

    messages = _backend.list_messages(str(mailbox.id), "Inbox")[:20]
    results: list[RuleTestResult] = []
    for item in messages:
        message_payload = {
            "from": item.get("from"),
            "to": item.get("to"),
            "subject": item.get("subject"),
            "body": _message_body(item.get("raw")),
            "has_attachment": False,
        }
        checks = [_condition_matches(cond, message_payload) for cond in conditions]
        would_apply = all(checks) if match_type == "all" else any(checks)
        results.append(
            RuleTestResult(
                uid=str(item.get("uid")),
                subject=str(item.get("subject")),
                would_apply=bool(would_apply),
                actions_that_would_run=action_types,
            )
        )

    return results
