from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from imap.maildir import MaildirBackend
from tasks.delivery import queue_delivery


_backend = MaildirBackend()


def _match_text(value: str, op: str, target: str) -> bool:
    value = value or ""
    target = target or ""
    if op == "contains":
        return target.lower() in value.lower()
    if op == "equals":
        return value.strip().lower() == target.strip().lower()
    if op == "starts_with":
        return value.strip().lower().startswith(target.strip().lower())
    if op == "regex":
        try:
            return re.search(target, value, re.IGNORECASE) is not None
        except re.error:
            return False
    return False


def _condition_matches(condition: dict[str, Any], message: dict[str, Any]) -> bool:
    field = condition.get("field")
    op = condition.get("op", "contains")
    value = str(condition.get("value", ""))

    if field == "has_attachment":
        expected = value.lower() in {"1", "true", "yes"}
        return bool(message.get("has_attachment", False)) == expected

    if field == "from":
        return _match_text(str(message.get("from", "")), op, value)
    if field == "to":
        return _match_text(str(message.get("to", "")), op, value)
    if field == "subject":
        return _match_text(str(message.get("subject", "")), op, value)
    if field == "body":
        return _match_text(str(message.get("body", "")), op, value)

    return False


async def _ensure_label(mailbox_id: str, name: str, db: AsyncSession) -> str | None:
    result = await db.execute(
        text("SELECT id FROM labels WHERE mailbox_id = :mailbox_id AND name = :name"),
        {"mailbox_id": mailbox_id, "name": name},
    )
    row = result.mappings().first()
    if row:
        return str(row["id"])

    insert = await db.execute(
        text(
            """
            INSERT INTO labels (mailbox_id, name, color)
            VALUES (:mailbox_id, :name, '#6366f1')
            RETURNING id
            """
        ),
        {"mailbox_id": mailbox_id, "name": name},
    )
    new_row = insert.mappings().first()
    await db.commit()
    return str(new_row["id"]) if new_row else None


def _merge_flags(existing: list[str], flag: str) -> str:
    merged = set(existing or [])
    merged.add(flag)
    return "".join(sorted(merged))


async def apply_rules(mailbox_id: str, message: dict, db: AsyncSession) -> list[str]:
    result = await db.execute(
        text(
            """
            SELECT id, match_type, conditions, actions
            FROM email_rules
            WHERE mailbox_id = :mailbox_id AND is_active = true
            ORDER BY priority ASC, created_at ASC
            """
        ),
        {"mailbox_id": mailbox_id},
    )
    rules = result.mappings().all()
    if not rules:
        return []

    applied: list[str] = []
    for rule in rules:
        conditions = rule.get("conditions") or []
        actions = rule.get("actions") or []
        match_type = str(rule.get("match_type") or "any")

        matches = [_condition_matches(cond, message) for cond in conditions]
        if match_type == "all":
            should_apply = all(matches) if matches else False
        else:
            should_apply = any(matches) if matches else False
        if not should_apply:
            continue

        for action in actions:
            action_type = action.get("type")
            value = action.get("value")
            try:
                if action_type == "move_to" and value:
                    _backend.move(str(mailbox_id), message.get("folder", "Inbox"), str(value), int(message["uid"]))
                elif action_type == "label" and value:
                    label_id = await _ensure_label(mailbox_id, str(value), db)
                    if label_id:
                        await db.execute(
                            text(
                                """
                                INSERT INTO email_labels (email_uid, label_id, mailbox_id)
                                VALUES (:email_uid, :label_id, :mailbox_id)
                                ON CONFLICT DO NOTHING
                                """
                            ),
                            {"email_uid": str(message["uid"]), "label_id": label_id, "mailbox_id": mailbox_id},
                        )
                        await db.commit()
                elif action_type == "mark_read":
                    flags = _merge_flags(message.get("flags", []), "S")
                    _backend.set_flags(str(mailbox_id), message.get("folder", "Inbox"), int(message["uid"]), flags)
                elif action_type == "mark_spam":
                    _backend.move(str(mailbox_id), message.get("folder", "Inbox"), "Spam", int(message["uid"]))
                elif action_type == "forward_to" and value:
                    queue_delivery.delay(
                        {
                            "from": message.get("from"),
                            "to": str(value),
                            "subject": message.get("subject", ""),
                            "body_text": message.get("body", ""),
                        }
                    )
                elif action_type == "auto_reply" and value:
                    queue_delivery.delay(
                        {
                            "from": message.get("to"),
                            "to": message.get("from"),
                            "subject": f"Re: {message.get('subject', '')}",
                            "body_text": str(value),
                        }
                    )
                elif action_type == "delete":
                    flags = _merge_flags(message.get("flags", []), "D")
                    _backend.set_flags(str(mailbox_id), message.get("folder", "Inbox"), int(message["uid"]), flags)
                elif action_type == "star":
                    flags = _merge_flags(message.get("flags", []), "F")
                    _backend.set_flags(str(mailbox_id), message.get("folder", "Inbox"), int(message["uid"]), flags)
                else:
                    continue
                applied.append(str(action_type))
            except Exception:
                continue

    return applied
