from __future__ import annotations

import json
import re
from typing import Any

from anthropic import AsyncAnthropic

from config import settings

_MODEL = "claude-sonnet-4-20250514"
_MAX_TOKENS = 1000


def _ai_ready() -> bool:
    return bool(settings.anthropic_api_key)


def _client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


def _extract_text(response: Any) -> str:
    if not getattr(response, "content", None):
        return ""
    parts = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts).strip()


def _extract_json(text: str) -> Any:
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON in response")
    return json.loads(match.group(1))


def _render_thread(messages: list[dict]) -> str:
    lines = []
    for item in messages:
        lines.append(
            "From: {from_}\nSubject: {subject}\nDate: {date}\nBody: {body}".format(
                from_=item.get("from", ""),
                subject=item.get("subject", ""),
                date=item.get("date", ""),
                body=item.get("body", ""),
            )
        )
    return "\n\n".join(lines)


async def summarize_thread(messages: list[dict]) -> str:
    if not settings.ai_summary_enabled or not _ai_ready():
        return ""
    prompt = "Summarize this email thread in 2-3 sentences.\n\n" + _render_thread(messages)
    response = await _client().messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_text(response)


async def smart_reply_suggestions(thread: list[dict]) -> list[str]:
    if not settings.ai_smart_reply_enabled or not _ai_ready():
        return []
    prompt = (
        "Suggest 3 short reply options for this email thread. "
        "Return a JSON array of strings.\n\n" + _render_thread(thread)
    )
    response = await _client().messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    text = _extract_text(response)
    try:
        data = _extract_json(text)
    except Exception:
        return [line.strip("- ") for line in text.splitlines() if line.strip()][:3]
    return [str(item) for item in data][:3]


async def rank_emails_by_priority(emails: list[dict], user_context: dict) -> list[dict]:
    if not settings.ai_priority_inbox_enabled or not _ai_ready():
        return [dict(item, priority_score=0) for item in emails]

    prompt = (
        "Score each email 0-100 for priority using the user context. "
        "Return JSON array of {uid, score}.\n\n"
        "User context: {context}\n\nEmails:\n{emails}"
    ).format(context=json.dumps(user_context), emails=json.dumps(emails))

    response = await _client().messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    text = _extract_text(response)
    scores: dict[str, int] = {}
    try:
        parsed = _extract_json(text)
        for item in parsed:
            scores[str(item.get("uid"))] = int(item.get("score", 0))
    except Exception:
        scores = {}

    ranked = []
    for item in emails:
        uid = str(item.get("uid"))
        score = scores.get(uid, 0)
        ranked.append(dict(item, priority_score=score))
    ranked.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
    return ranked


async def suggest_labels(email: dict, existing_labels: list[str]) -> list[str]:
    if not _ai_ready():
        return []
    prompt = (
        "Suggest labels from this list only: {labels}. "
        "Return a JSON array of label names.\n\nEmail:\n{email}"
    ).format(labels=existing_labels, email=json.dumps(email))

    response = await _client().messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    text = _extract_text(response)
    try:
        data = _extract_json(text)
    except Exception:
        return []
    return [label for label in data if label in existing_labels]
