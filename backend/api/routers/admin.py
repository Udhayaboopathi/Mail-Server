from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal, get_db
from deps import require_admin
from models.user import User
from routers.admin import router
from services.backup_service import create_full_backup, restore_full_backup


async def _complete_backup_job(job_id: str) -> None:
	async with AsyncSessionLocal() as session:
		try:
			file_path = await create_full_backup(session)
			file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
			await session.execute(
				text(
					"""
					UPDATE backup_jobs
					SET status='done', file_path=:file_path, file_size_mb=:file_size_mb, completed_at=now()
					WHERE id = :job_id
					"""
				),
				{"job_id": job_id, "file_path": file_path, "file_size_mb": file_size_mb},
			)
		except Exception as exc:
			await session.execute(
				text(
					"""
					UPDATE backup_jobs
					SET status='failed', error_message=:error_message, completed_at=now()
					WHERE id = :job_id
					"""
				),
				{"job_id": job_id, "error_message": str(exc)},
			)
		await session.commit()


@router.post("/backup/full")
async def trigger_full_backup(
	background_tasks: BackgroundTasks,
	_: User = Depends(require_admin),
	db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
	job_id = str(uuid4())
	await db.execute(
		text(
			"""
			INSERT INTO backup_jobs (id, type, status)
			VALUES (:id, 'full', 'running')
			"""
		),
		{"id": job_id},
	)
	await db.commit()
	background_tasks.add_task(_complete_backup_job, job_id)
	return {"job_id": job_id, "status": "running"}


@router.get("/backup/jobs")
async def list_backup_jobs(_: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> list[dict]:
	result = await db.execute(
		text(
			"""
			SELECT id, type, status, mailbox_id, file_path, file_size_mb, total_messages,
				   error_message, created_at, completed_at
			FROM backup_jobs
			ORDER BY created_at DESC
			"""
		)
	)
	return [dict(item) for item in result.mappings().all()]


@router.get("/backup/{job_id}/download")
async def download_backup(job_id: str, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> FileResponse:
	result = await db.execute(text("SELECT file_path FROM backup_jobs WHERE id = :job_id"), {"job_id": job_id})
	row = result.mappings().first()
	if row is None or not row.get("file_path"):
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup file not found")
	file_path = Path(str(row["file_path"]))
	if not file_path.exists():
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup file does not exist")
	return FileResponse(path=str(file_path), filename=file_path.name, media_type="application/gzip")


@router.post("/backup/restore")
async def restore_backup(
	backup_file: UploadFile = File(...),
	_: User = Depends(require_admin),
	db: AsyncSession = Depends(get_db),
) -> dict:
	if not backup_file.filename or not backup_file.filename.endswith(".tar.gz"):
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .tar.gz backups are supported")

	restore_dir = Path("/tmp/restore_uploads")
	restore_dir.mkdir(parents=True, exist_ok=True)
	destination = restore_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{backup_file.filename}"

	content = await backup_file.read()
	destination.write_bytes(content)
	result = await restore_full_backup(str(destination), db)
	return result
