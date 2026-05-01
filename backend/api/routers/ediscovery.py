from __future__ import annotations

import asyncio
import json
import mailbox
import zipfile
from datetime import datetime, timezone
from email import message_from_bytes
from email.policy import default
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal, get_db
from deps import get_user_mailbox, require_admin
from schemas.ediscovery import EdiscoveryExportCreate, EdiscoveryExportListItem

router = APIRouter(tags=["ediscovery"])

EXPORT_DIR = Path("/tmp/ediscovery")


def _message_matches(message, query: dict[str, Any]) -> bool:
    if query.get("from") and query["from"].lower() not in str(message.get("From", "")).lower():
        return False
    if query.get("to") and query["to"].lower() not in str(message.get("To", "")).lower():
        return False
    if query.get("subject") and query["subject"].lower() not in str(message.get("Subject", "")).lower():
        return False
    date_from = query.get("date_from")
    date_to = query.get("date_to")
    if date_from or date_to:
        try:
            msg_date = parsedate_to_datetime(str(message.get("Date", "")))
        except Exception:
            msg_date = None
        if msg_date:
            if date_from and msg_date < date_from:
                return False
            if date_to and msg_date > date_to:
                return False
    return True


async def _run_export(export_id: str, domain_id: str, query: dict[str, Any]) -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output = EXPORT_DIR / f"{export_id}.zip"

    async with AsyncSessionLocal() as db:
        mailbox_query = "SELECT id, full_address, maildir_path FROM mailboxes WHERE domain_id = :domain_id"
        params = {"domain_id": domain_id}
        if query.get("mailboxes"):
            mailbox_query += " AND id = ANY(:mailboxes)"
            params["mailboxes"] = query["mailboxes"]
        result = await db.execute(text(mailbox_query), params)
        mailboxes = result.mappings().all()

        total_messages = 0

        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for mailbox_row in mailboxes:
                maildir_path = Path(mailbox_row["maildir_path"] or Path("/var/mail") / str(mailbox_row["id"]))
                if not maildir_path.exists():
                    continue
                mdir = mailbox.Maildir(str(maildir_path), create=False)
                for key in mdir.iterkeys():
                    msg = mdir.get_message(key)
                    if not _message_matches(msg, query):
                        continue
                    payload = msg.as_bytes()
                    arcname = f"{mailbox_row['full_address']}/{key}.eml"
                    archive.writestr(arcname, payload)
                    total_messages += 1

        await db.execute(
            text(
                """
                UPDATE ediscovery_exports
                SET status = 'completed', file_path = :path, total_messages = :total, completed_at = now()
                WHERE id = :id
                """
            ),
            {"id": export_id, "path": str(output), "total": total_messages},
        )
        await db.commit()


@router.post("/export", response_model=EdiscoveryExportListItem)
async def create_export(
    payload: EdiscoveryExportCreate,
    background: BackgroundTasks,
    _: object = Depends(require_admin),
    mailbox=Depends(get_user_mailbox),
    db: AsyncSession = Depends(get_db),
) -> EdiscoveryExportListItem:
    domain_row = await db.execute(
        text("SELECT ediscovery_enabled FROM domains WHERE id = :id"),
        {"id": str(mailbox.domain_id)},
    )
    domain = domain_row.mappings().first()
    if domain is None or not domain["ediscovery_enabled"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="eDiscovery not enabled")

    result = await db.execute(
        text(
            """
            INSERT INTO ediscovery_exports (domain_id, requested_by, query, status, created_at)
            VALUES (:domain_id, :requested_by, CAST(:query AS jsonb), 'pending', now())
            RETURNING *
            """
        ),
        {
            "domain_id": str(mailbox.domain_id),
            "requested_by": str(mailbox.user_id),
            "query": json.dumps(payload.model_dump(exclude_unset=True, by_alias=True)),
        },
    )
    row = result.mappings().first()
    await db.commit()

    background.add_task(
        _run_export,
        str(row["id"]),
        str(mailbox.domain_id),
        payload.model_dump(exclude_unset=True, by_alias=True),
    )
    return EdiscoveryExportListItem(**row)


@router.get("/exports", response_model=list[EdiscoveryExportListItem])
async def list_exports(_: object = Depends(require_admin), mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> list[EdiscoveryExportListItem]:
    result = await db.execute(
        text("SELECT * FROM ediscovery_exports WHERE domain_id = :domain_id ORDER BY created_at DESC"),
        {"domain_id": str(mailbox.domain_id)},
    )
    return [EdiscoveryExportListItem(**row) for row in result.mappings().all()]


@router.get("/exports/{export_id}/download")
async def download_export(export_id: str, _: object = Depends(require_admin), mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> FileResponse:
    result = await db.execute(
        text("SELECT file_path FROM ediscovery_exports WHERE id = :id AND domain_id = :domain_id"),
        {"id": export_id, "domain_id": str(mailbox.domain_id)},
    )
    row = result.mappings().first()
    if row is None or not row["file_path"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not ready")
    path = Path(row["file_path"])
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing")
    return FileResponse(path)
