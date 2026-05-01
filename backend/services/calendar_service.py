from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from icalendar import Calendar, Event
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _normalize_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if hasattr(value, "dt"):
        return _normalize_dt(value.dt)
    raise ValueError("Invalid datetime")


def _parse_attendees(raw: Any) -> list[dict[str, str]]:
    if not raw:
        return []
    items = raw if isinstance(raw, list) else [raw]
    attendees: list[dict[str, str]] = []
    for item in items:
        email = str(item).replace("mailto:", "")
        name = None
        if hasattr(item, "params"):
            name = item.params.get("CN")
        attendees.append({"email": email, "name": name or ""})
    return attendees


async def list_events(mailbox_id: str, start: datetime, end: datetime, db: AsyncSession) -> list:
    result = await db.execute(
        text(
            """
            SELECT *
            FROM calendar_events
            WHERE mailbox_id = :mailbox_id
              AND start_at >= :start_at
              AND end_at <= :end_at
            ORDER BY start_at ASC
            """
        ),
        {"mailbox_id": mailbox_id, "start_at": start, "end_at": end},
    )
    return [dict(row) for row in result.mappings().all()]


async def create_event(mailbox_id: str, data: dict, db: AsyncSession) -> dict:
    result = await db.execute(
        text(
            """
            INSERT INTO calendar_events (
                mailbox_id, uid, title, description, location, start_at, end_at, all_day,
                rrule, attendees, linked_email_uid, created_at, updated_at
            ) VALUES (
                :mailbox_id, :uid, :title, :description, :location, :start_at, :end_at, :all_day,
                :rrule, CAST(:attendees AS jsonb), :linked_email_uid, now(), now()
            )
            RETURNING *
            """
        ),
        {
            "mailbox_id": mailbox_id,
            "uid": data["uid"],
            "title": data["title"],
            "description": data.get("description"),
            "location": data.get("location"),
            "start_at": data["start_at"],
            "end_at": data["end_at"],
            "all_day": data.get("all_day", False),
            "rrule": data.get("rrule"),
            "attendees": json.dumps(data.get("attendees", [])),
            "linked_email_uid": data.get("linked_email_uid"),
        },
    )
    row = result.mappings().first()
    await db.commit()
    return dict(row)


async def update_event(event_id: str, data: dict, db: AsyncSession) -> dict:
    result = await db.execute(
        text(
            """
            UPDATE calendar_events
            SET title = COALESCE(:title, title),
                description = COALESCE(:description, description),
                location = COALESCE(:location, location),
                start_at = COALESCE(:start_at, start_at),
                end_at = COALESCE(:end_at, end_at),
                all_day = COALESCE(:all_day, all_day),
                rrule = COALESCE(:rrule, rrule),
                attendees = COALESCE(CAST(:attendees AS jsonb), attendees),
                linked_email_uid = COALESCE(:linked_email_uid, linked_email_uid),
                updated_at = now()
            WHERE id = :event_id
            RETURNING *
            """
        ),
        {
            "event_id": event_id,
            "title": data.get("title"),
            "description": data.get("description"),
            "location": data.get("location"),
            "start_at": data.get("start_at"),
            "end_at": data.get("end_at"),
            "all_day": data.get("all_day"),
            "rrule": data.get("rrule"),
            "attendees": json.dumps(data["attendees"]) if "attendees" in data else None,
            "linked_email_uid": data.get("linked_email_uid"),
        },
    )
    row = result.mappings().first()
    await db.commit()
    if row is None:
        raise ValueError("Event not found")
    return dict(row)


async def delete_event(event_id: str, db: AsyncSession) -> bool:
    result = await db.execute(text("DELETE FROM calendar_events WHERE id = :event_id"), {"event_id": event_id})
    await db.commit()
    return result.rowcount > 0


async def import_ics(mailbox_id: str, ics_bytes: bytes, db: AsyncSession) -> dict:
    calendar = Calendar.from_ical(ics_bytes)
    imported = 0
    for component in calendar.walk():
        if component.name != "VEVENT":
            continue
        uid = str(component.get("uid"))
        start_at = _normalize_dt(component.get("dtstart"))
        end_at = _normalize_dt(component.get("dtend"))
        attendees = _parse_attendees(component.get("attendee"))
        await db.execute(
            text(
                """
                INSERT INTO calendar_events (
                    mailbox_id, uid, title, description, location, start_at, end_at, all_day,
                    rrule, attendees, linked_email_uid, created_at, updated_at
                ) VALUES (
                    :mailbox_id, :uid, :title, :description, :location, :start_at, :end_at, :all_day,
                    :rrule, CAST(:attendees AS jsonb), :linked_email_uid, now(), now()
                )
                ON CONFLICT (uid) DO NOTHING
                """
            ),
            {
                "mailbox_id": mailbox_id,
                "uid": uid,
                "title": str(component.get("summary", "")),
                "description": str(component.get("description", "")) or None,
                "location": str(component.get("location", "")) or None,
                "start_at": start_at,
                "end_at": end_at,
                "all_day": bool(component.get("x-allday", False)),
                "rrule": str(component.get("rrule")) if component.get("rrule") else None,
                "attendees": json.dumps(attendees),
                "linked_email_uid": None,
            },
        )
        imported += 1
    await db.commit()
    return {"imported": imported}


async def export_ics(mailbox_id: str, db: AsyncSession) -> bytes:
    result = await db.execute(text("SELECT * FROM calendar_events WHERE mailbox_id = :mailbox_id"), {"mailbox_id": mailbox_id})
    calendar = Calendar()
    calendar.add("prodid", "-//Mail//Calendar//EN")
    calendar.add("version", "2.0")

    for row in result.mappings().all():
        event = Event()
        event.add("uid", row["uid"])
        event.add("summary", row["title"])
        if row.get("description"):
            event.add("description", row["description"])
        if row.get("location"):
            event.add("location", row["location"])
        event.add("dtstart", row["start_at"])
        event.add("dtend", row["end_at"])
        if row.get("rrule"):
            event.add("rrule", row["rrule"])
        attendees = row.get("attendees") or []
        for attendee in attendees:
            email = attendee.get("email")
            if email:
                event.add("attendee", f"mailto:{email}")
        calendar.add_component(event)

    return calendar.to_ical()
