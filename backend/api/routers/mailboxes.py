from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_user
from models.user import User
from routers.mailboxes import router
from services.backup_service import export_mailbox_mbox, export_mailbox_zip, import_eml_zip, import_mbox


async def _ensure_mailbox_access(mailbox_id: str, user: User, db: AsyncSession) -> None:
	result = await db.execute(text("SELECT user_id FROM mailboxes WHERE id = :mailbox_id"), {"mailbox_id": mailbox_id})
	row = result.mappings().first()
	if row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mailbox not found")
	if not user.is_admin and str(row["user_id"]) != str(user.id):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this mailbox")


@router.post("/{mailbox_id}/export/mbox")
async def mailbox_export_mbox(
	mailbox_id: str,
	user: User = Depends(get_current_user),
	db: AsyncSession = Depends(get_db),
) -> FileResponse:
	await _ensure_mailbox_access(mailbox_id, user, db)
	file_path = await export_mailbox_mbox(UUID(mailbox_id), db)
	path = Path(file_path)
	return FileResponse(path=str(path), filename=path.name, media_type="application/mbox")


@router.post("/{mailbox_id}/export/zip")
async def mailbox_export_zip(
	mailbox_id: str,
	user: User = Depends(get_current_user),
	db: AsyncSession = Depends(get_db),
) -> FileResponse:
	await _ensure_mailbox_access(mailbox_id, user, db)
	file_path = await export_mailbox_zip(UUID(mailbox_id), db)
	path = Path(file_path)
	return FileResponse(path=str(path), filename=path.name, media_type="application/zip")


@router.post("/{mailbox_id}/import/mbox")
async def mailbox_import_mbox(
	mailbox_id: str,
	import_file: UploadFile = File(...),
	user: User = Depends(get_current_user),
	db: AsyncSession = Depends(get_db),
) -> dict:
	await _ensure_mailbox_access(mailbox_id, user, db)
	if not import_file.filename or not import_file.filename.lower().endswith(".mbox"):
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload an .mbox file")
	uploads = Path("/tmp/imports")
	uploads.mkdir(parents=True, exist_ok=True)
	temp_path = uploads / f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{import_file.filename}"
	temp_path.write_bytes(await import_file.read())
	return await import_mbox(UUID(mailbox_id), str(temp_path), db)


@router.post("/{mailbox_id}/import/zip")
async def mailbox_import_zip(
	mailbox_id: str,
	import_file: UploadFile = File(...),
	user: User = Depends(get_current_user),
	db: AsyncSession = Depends(get_db),
) -> dict:
	await _ensure_mailbox_access(mailbox_id, user, db)
	if not import_file.filename or not import_file.filename.lower().endswith(".zip"):
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload a .zip file")
	uploads = Path("/tmp/imports")
	uploads.mkdir(parents=True, exist_ok=True)
	temp_path = uploads / f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{import_file.filename}"
	temp_path.write_bytes(await import_file.read())
	return await import_eml_zip(UUID(mailbox_id), str(temp_path), db)
