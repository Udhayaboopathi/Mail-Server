from __future__ import annotations

import secrets
from datetime import date, datetime, timezone

from fastapi import Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_user, get_user_mailbox
from models.user import User
from routers.mail import router
from schemas.common import ActionResponse
from schemas.mail import MailSendRequest
from services.mail_service import MailService


def _remove_route(path: str, method: str) -> None:
	router.routes = [
		route
		for route in router.routes
		if not (
			getattr(route, "path", "") == path
			and method.upper() in getattr(route, "methods", set())
		)
	]


_remove_route("/api/mail/send", "POST")


class MailScheduleRequest(MailSendRequest):
	send_at: datetime


class AutoresponderRequest(BaseModel):
	is_enabled: bool
	subject: str = Field(default="Out of Office", max_length=255)
	body: str
	start_date: date | None = None
	end_date: date | None = None
	reply_once_per_sender: bool = True


class AliasCreateRequest(BaseModel):
	local_part: str
	destination: str | None = None


@router.post("/send")
async def send_mail(
	payload: MailSendRequest,
	undo_window: int = Query(default=0, ge=0, le=30),
	db: AsyncSession = Depends(get_db),
	mailbox=Depends(get_user_mailbox),
) -> dict:
	if undo_window > 0:
		send_at = datetime.now(timezone.utc).timestamp() + undo_window
		result = await db.execute(
			text(
				"""
				INSERT INTO scheduled_emails (
					mailbox_id, send_at, to_addresses, cc_addresses, bcc_addresses,
					subject, body_text, body_html, attachments, status
				) VALUES (
					:mailbox_id, to_timestamp(:send_at), :to_addresses, :cc_addresses, :bcc_addresses,
					:subject, :body_text, :body_html, CAST(:attachments AS jsonb), 'pending'
				)
				RETURNING id, send_at, status
				"""
			),
			{
				"mailbox_id": str(mailbox.id),
				"send_at": send_at,
				"to_addresses": payload.to,
				"cc_addresses": payload.cc,
				"bcc_addresses": payload.bcc,
				"subject": payload.subject,
				"body_text": payload.body_text,
				"body_html": payload.body_html,
				"attachments": "[]",
			},
		)
		row = result.mappings().first()
		await db.commit()
		return {"id": str(row["id"]), "undo_expires_at": row["send_at"], "status": "pending_undo"}

	await MailService.send_email(db, mailbox, payload.model_dump())
	return ActionResponse(status="queued").model_dump()


@router.post("/schedule")
async def schedule_send(
	payload: MailScheduleRequest,
	db: AsyncSession = Depends(get_db),
	mailbox=Depends(get_user_mailbox),
) -> dict:
	now = datetime.now(timezone.utc)
	send_at = payload.send_at if payload.send_at.tzinfo else payload.send_at.replace(tzinfo=timezone.utc)
	if send_at <= now:
		raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="send_at must be in the future")

	result = await db.execute(
		text(
			"""
			INSERT INTO scheduled_emails (
				mailbox_id, send_at, to_addresses, cc_addresses, bcc_addresses,
				subject, body_text, body_html, attachments, status
			) VALUES (
				:mailbox_id, :send_at, :to_addresses, :cc_addresses, :bcc_addresses,
				:subject, :body_text, :body_html, CAST(:attachments AS jsonb), 'pending'
			)
			RETURNING id, send_at, status
			"""
		),
		{
			"mailbox_id": str(mailbox.id),
			"send_at": send_at,
			"to_addresses": payload.to,
			"cc_addresses": payload.cc,
			"bcc_addresses": payload.bcc,
			"subject": payload.subject,
			"body_text": payload.body_text,
			"body_html": payload.body_html,
			"attachments": "[]",
		},
	)
	row = result.mappings().first()
	await db.commit()
	return {"id": str(row["id"]), "send_at": row["send_at"], "status": row["status"]}


@router.get("/scheduled")
async def list_scheduled(db: AsyncSession = Depends(get_db), mailbox=Depends(get_user_mailbox)) -> list[dict]:
	result = await db.execute(
		text(
			"""
			SELECT id, send_at, to_addresses, subject, status, created_at
			FROM scheduled_emails
			WHERE mailbox_id = :mailbox_id AND status = 'pending'
			ORDER BY send_at ASC
			"""
		),
		{"mailbox_id": str(mailbox.id)},
	)
	return [dict(item) for item in result.mappings().all()]


@router.delete("/scheduled/{scheduled_id}")
async def cancel_scheduled(scheduled_id: str, db: AsyncSession = Depends(get_db), mailbox=Depends(get_user_mailbox)) -> dict:
	result = await db.execute(
		text(
			"""
			UPDATE scheduled_emails
			SET status='cancelled'
			WHERE id = :scheduled_id
			  AND mailbox_id = :mailbox_id
			  AND status = 'pending'
			RETURNING id
			"""
		),
		{"scheduled_id": scheduled_id, "mailbox_id": str(mailbox.id)},
	)
	row = result.mappings().first()
	await db.commit()
	return {"cancelled": row is not None}


@router.delete("/send/{scheduled_id}/undo")
async def undo_send(scheduled_id: str, db: AsyncSession = Depends(get_db), mailbox=Depends(get_user_mailbox)) -> dict:
	result = await db.execute(
		text(
			"""
			UPDATE scheduled_emails
			SET status='cancelled'
			WHERE id = :scheduled_id
			  AND mailbox_id = :mailbox_id
			  AND status = 'pending'
			  AND send_at > now()
			RETURNING id
			"""
		),
		{"scheduled_id": scheduled_id, "mailbox_id": str(mailbox.id)},
	)
	row = result.mappings().first()
	await db.commit()
	if row is None:
		return {"cancelled": False, "message": "Undo window expired or message already sent"}
	return {"cancelled": True, "message": "Send cancelled"}


@router.get("/autoresponder")
async def get_autoresponder(db: AsyncSession = Depends(get_db), mailbox=Depends(get_user_mailbox)) -> dict | None:
	result = await db.execute(
		text("SELECT * FROM autoresponders WHERE mailbox_id = :mailbox_id LIMIT 1"),
		{"mailbox_id": str(mailbox.id)},
	)
	row = result.mappings().first()
	return dict(row) if row else None


@router.put("/autoresponder")
async def upsert_autoresponder(
	payload: AutoresponderRequest,
	db: AsyncSession = Depends(get_db),
	mailbox=Depends(get_user_mailbox),
) -> dict:
	await db.execute(
		text(
			"""
			INSERT INTO autoresponders (mailbox_id, is_enabled, subject, body, start_date, end_date, reply_once_per_sender, updated_at)
			VALUES (:mailbox_id, :is_enabled, :subject, :body, :start_date, :end_date, :reply_once_per_sender, now())
			ON CONFLICT (mailbox_id) DO UPDATE SET
				is_enabled = EXCLUDED.is_enabled,
				subject = EXCLUDED.subject,
				body = EXCLUDED.body,
				start_date = EXCLUDED.start_date,
				end_date = EXCLUDED.end_date,
				reply_once_per_sender = EXCLUDED.reply_once_per_sender,
				updated_at = now()
			"""
		),
		{
			"mailbox_id": str(mailbox.id),
			"is_enabled": payload.is_enabled,
			"subject": payload.subject,
			"body": payload.body,
			"start_date": payload.start_date,
			"end_date": payload.end_date,
			"reply_once_per_sender": payload.reply_once_per_sender,
		},
	)
	await db.commit()
	return {"status": "updated"}


@router.delete("/autoresponder")
async def delete_autoresponder(db: AsyncSession = Depends(get_db), mailbox=Depends(get_user_mailbox)) -> dict:
	await db.execute(text("DELETE FROM autoresponders WHERE mailbox_id = :mailbox_id"), {"mailbox_id": str(mailbox.id)})
	await db.commit()
	return {"status": "deleted"}


@router.get("/aliases")
async def list_aliases(db: AsyncSession = Depends(get_db), mailbox=Depends(get_user_mailbox)) -> list[dict]:
	result = await db.execute(
		text(
			"""
			SELECT a.id, a.source_address, a.destination_address, a.is_active, a.created_at,
				   a.is_catch_all, a.forward_only
			FROM aliases a
			WHERE a.destination_address = :destination
			ORDER BY a.created_at DESC
			"""
		),
		{"destination": mailbox.full_address},
	)
	return [dict(row) for row in result.mappings().all()]


@router.post("/aliases")
async def create_alias(payload: AliasCreateRequest, db: AsyncSession = Depends(get_db), mailbox=Depends(get_user_mailbox)) -> dict:
	domain = mailbox.full_address.split("@", 1)[1]
	local_part = payload.local_part.strip().lower()
	if local_part == "random":
		local_part = f"shop-{secrets.token_hex(2)}"
	source_address = f"{local_part}@{domain}"
	destination = payload.destination or mailbox.full_address

	domain_result = await db.execute(text("SELECT id FROM domains WHERE name = :name LIMIT 1"), {"name": domain})
	domain_row = domain_result.mappings().first()
	if domain_row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

	result = await db.execute(
		text(
			"""
			INSERT INTO aliases (source_address, destination_address, domain_id, is_active, is_catch_all, forward_only)
			VALUES (:source_address, :destination_address, :domain_id, true, false, true)
			RETURNING id, source_address, destination_address, is_active, is_catch_all, forward_only, created_at
			"""
		),
		{
			"source_address": source_address,
			"destination_address": destination,
			"domain_id": str(domain_row["id"]),
		},
	)
	row = result.mappings().first()
	await db.commit()
	return dict(row)


@router.delete("/aliases/{alias_id}")
async def deactivate_alias(alias_id: str, db: AsyncSession = Depends(get_db), mailbox=Depends(get_user_mailbox)) -> dict:
	await db.execute(
		text(
			"""
			UPDATE aliases
			SET is_active = false
			WHERE id = :alias_id
			  AND destination_address = :destination
			"""
		),
		{"alias_id": alias_id, "destination": mailbox.full_address},
	)
	await db.commit()
	return {"status": "deactivated"}
