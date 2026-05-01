from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_user_mailbox
from schemas.calendar import CalendarEventCreate, CalendarEventResponse, CalendarEventUpdate
from services.calendar_service import create_event, delete_event, export_ics, import_ics, list_events, update_event

router = APIRouter(tags=["calendar"])


@router.get("/events", response_model=list[CalendarEventResponse])
async def get_events(start: str, end: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> list[CalendarEventResponse]:
    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
    events = await list_events(str(mailbox.id), start_dt, end_dt, db)
    return [CalendarEventResponse(**item) for item in events]


@router.post("/events", response_model=CalendarEventResponse)
async def create_event_route(payload: CalendarEventCreate, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> CalendarEventResponse:
    data = payload.model_dump()
    event = await create_event(str(mailbox.id), data, db)
    return CalendarEventResponse(**event)


@router.patch("/events/{event_id}", response_model=CalendarEventResponse)
async def update_event_route(event_id: str, payload: CalendarEventUpdate, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> CalendarEventResponse:
    data = payload.model_dump(exclude_unset=True)
    event = await update_event(event_id, data, db)
    return CalendarEventResponse(**event)


@router.delete("/events/{event_id}")
async def delete_event_route(event_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    deleted = await delete_event(event_id, db)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return {"deleted": True}


@router.post("/import")
async def import_calendar(file: UploadFile = File(...), mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    content = await file.read()
    result = await import_ics(str(mailbox.id), content, db)
    return result


@router.get("/export")
async def export_calendar(mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> Response:
    content = await export_ics(str(mailbox.id), db)
    return Response(content, media_type="text/calendar")


@router.get("/events/{event_id}/invite")
async def invite_event(event_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> Response:
    result = await db.execute(
        text("SELECT uid, title, description, location, start_at, end_at FROM calendar_events WHERE id = :id"),
        {"id": event_id},
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    ics = await export_ics(str(mailbox.id), db)
    return Response(ics, media_type="text/calendar")
