from __future__ import annotations

import asyncio
import json
import mailbox
import os
import shutil
import tarfile
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings


EXPORT_DIR = Path("/tmp/exports")
BACKUP_DIR = Path("/tmp/backups")


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _count_maildir_messages(maildir_path: Path) -> int:
    total = 0
    for folder in ("cur", "new"):
        p = maildir_path / folder
        if p.exists():
            total += sum(1 for item in p.iterdir() if item.is_file())
    return total


async def export_mailbox_mbox(mailbox_id: UUID, db: AsyncSession) -> str:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    result = await db.execute(
        text("SELECT id, maildir_path FROM mailboxes WHERE id = :mailbox_id"),
        {"mailbox_id": str(mailbox_id)},
    )
    row = result.mappings().first()
    if row is None:
        raise ValueError("Mailbox not found")

    maildir_path = Path(row["maildir_path"] or (Path(settings.maildir_base) / str(mailbox_id)))
    output = EXPORT_DIR / f"{mailbox_id}_{_ts()}.mbox"

    def _write() -> None:
        source = mailbox.Maildir(str(maildir_path), create=False)
        destination = mailbox.mbox(str(output), create=True)
        try:
            for _, message in source.iteritems():
                destination.add(message)
            destination.flush()
        finally:
            destination.close()

    await asyncio.to_thread(_write)
    return str(output)


async def export_mailbox_zip(mailbox_id: UUID, db: AsyncSession) -> str:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    result = await db.execute(
        text(
            """
            SELECT m.id, m.full_address, m.maildir_path, d.name AS domain_name
            FROM mailboxes m
            JOIN domains d ON d.id = m.domain_id
            WHERE m.id = :mailbox_id
            """
        ),
        {"mailbox_id": str(mailbox_id)},
    )
    row = result.mappings().first()
    if row is None:
        raise ValueError("Mailbox not found")

    maildir_path = Path(row["maildir_path"] or (Path(settings.maildir_base) / str(mailbox_id)))
    output = EXPORT_DIR / f"{mailbox_id}_{_ts()}.zip"

    metadata = {
        "mailbox": row["full_address"],
        "domain": row["domain_name"],
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "total_messages": _count_maildir_messages(maildir_path),
    }

    def _write_zip() -> None:
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            if maildir_path.exists():
                for path in maildir_path.rglob("*"):
                    if path.is_file():
                        archive.write(path, arcname=str(path.relative_to(maildir_path)))
            archive.writestr("metadata.json", json.dumps(metadata, indent=2))

    await asyncio.to_thread(_write_zip)
    return str(output)


async def import_mbox(mailbox_id: UUID, mbox_path: str, db: AsyncSession) -> dict:
    result = await db.execute(
        text("SELECT id, maildir_path FROM mailboxes WHERE id = :mailbox_id"),
        {"mailbox_id": str(mailbox_id)},
    )
    row = result.mappings().first()
    if row is None:
        raise ValueError("Mailbox not found")

    maildir_path = Path(row["maildir_path"] or (Path(settings.maildir_base) / str(mailbox_id)))
    cur_path = maildir_path / "cur"
    cur_path.mkdir(parents=True, exist_ok=True)

    imported = 0
    failed = 0
    skipped_duplicates = 0
    total_size = 0

    existing_hashes: set[str] = set()
    for path in cur_path.glob("*"):
        if path.is_file():
            existing_hashes.add(path.name.split(".")[0])

    mbox = mailbox.mbox(mbox_path)
    for _, message in mbox.iteritems():
        try:
            payload = message.as_bytes()
            msg_hash = str(abs(hash(payload)))
            if msg_hash in existing_hashes:
                skipped_duplicates += 1
                continue
            filename = f"{msg_hash}.imported"
            target = cur_path / filename
            target.write_bytes(payload)
            existing_hashes.add(msg_hash)
            imported += 1
            total_size += len(payload)
        except Exception:
            failed += 1

    if imported > 0:
        await db.execute(
            text("UPDATE mailboxes SET used_mb = COALESCE(used_mb, 0) + :delta WHERE id = :mailbox_id"),
            {"delta": total_size / (1024 * 1024), "mailbox_id": str(mailbox_id)},
        )
        await db.commit()

    return {"imported": imported, "failed": failed, "skipped_duplicates": skipped_duplicates}


async def import_eml_zip(mailbox_id: UUID, zip_path: str, db: AsyncSession) -> dict:
    result = await db.execute(
        text("SELECT id, maildir_path FROM mailboxes WHERE id = :mailbox_id"),
        {"mailbox_id": str(mailbox_id)},
    )
    row = result.mappings().first()
    if row is None:
        raise ValueError("Mailbox not found")

    maildir_path = Path(row["maildir_path"] or (Path(settings.maildir_base) / str(mailbox_id)))
    cur_path = maildir_path / "cur"
    cur_path.mkdir(parents=True, exist_ok=True)

    imported = 0
    failed = 0
    total_size = 0

    with tempfile.TemporaryDirectory(prefix="email-import-") as temp_dir:
        temp = Path(temp_dir)

        def _extract() -> None:
            with zipfile.ZipFile(zip_path, "r") as archive:
                archive.extractall(temp)

        await asyncio.to_thread(_extract)

        for eml in temp.rglob("*.eml"):
            try:
                payload = eml.read_bytes()
                filename = f"{abs(hash(payload))}.imported"
                (cur_path / filename).write_bytes(payload)
                imported += 1
                total_size += len(payload)
            except Exception:
                failed += 1

    if imported > 0:
        await db.execute(
            text("UPDATE mailboxes SET used_mb = COALESCE(used_mb, 0) + :delta WHERE id = :mailbox_id"),
            {"delta": total_size / (1024 * 1024), "mailbox_id": str(mailbox_id)},
        )
        await db.commit()

    return {"imported": imported, "failed": failed}


async def create_full_backup(db: AsyncSession) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _ts()

    with tempfile.TemporaryDirectory(prefix="email-full-backup-") as temp_dir:
        temp = Path(temp_dir)
        backup_sql = temp / "backup.sql"
        mail_tar = temp / "mail_data.tar.gz"

        db_url = settings.database_url.replace("+asyncpg", "")

        dump_proc = await asyncio.create_subprocess_exec(
            "pg_dump",
            db_url,
            "-f",
            str(backup_sql),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, dump_err = await dump_proc.communicate()
        if dump_proc.returncode != 0:
            raise RuntimeError(f"pg_dump failed: {dump_err.decode('utf-8', errors='ignore')}")

        def _archive_mail() -> None:
            with tarfile.open(mail_tar, "w:gz") as archive:
                archive.add(settings.maildir_base, arcname="maildir")

        await asyncio.to_thread(_archive_mail)

        output = BACKUP_DIR / f"full_{stamp}.tar.gz"

        def _pack() -> None:
            with tarfile.open(output, "w:gz") as archive:
                archive.add(backup_sql, arcname="backup.sql")
                archive.add(mail_tar, arcname="mail_data.tar.gz")

        await asyncio.to_thread(_pack)
        return str(output)


async def restore_full_backup(backup_path: str, db: AsyncSession) -> dict:
    restored_messages = 0
    restored_mailboxes = 0

    with tempfile.TemporaryDirectory(prefix="email-restore-") as temp_dir:
        temp = Path(temp_dir)

        def _extract() -> None:
            with tarfile.open(backup_path, "r:gz") as archive:
                archive.extractall(temp)

        await asyncio.to_thread(_extract)

        backup_sql = temp / "backup.sql"
        mail_tar = temp / "mail_data.tar.gz"

        db_url = settings.database_url.replace("+asyncpg", "")
        restore_proc = await asyncio.create_subprocess_exec(
            "psql",
            db_url,
            "-f",
            str(backup_sql),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, restore_err = await restore_proc.communicate()
        if restore_proc.returncode != 0:
            raise RuntimeError(f"psql restore failed: {restore_err.decode('utf-8', errors='ignore')}")

        def _restore_mail() -> None:
            nonlocal restored_messages, restored_mailboxes
            target = Path(settings.maildir_base)
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)
            with tarfile.open(mail_tar, "r:gz") as archive:
                archive.extractall(temp)
            extracted_maildir = temp / "maildir"
            if extracted_maildir.exists():
                for item in extracted_maildir.iterdir():
                    destination = target / item.name
                    if item.is_dir():
                        shutil.copytree(item, destination, dirs_exist_ok=True)
                        restored_mailboxes += 1
                        restored_messages += _count_maildir_messages(destination)
                    else:
                        shutil.copy2(item, destination)

        await asyncio.to_thread(_restore_mail)

    return {
        "status": "restored",
        "restored_mailboxes": restored_mailboxes,
        "restored_messages": restored_messages,
    }


async def schedule_auto_backup(interval_hours: int = 24) -> None:
    from database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        backup_path = await create_full_backup(session)

        backups = sorted(BACKUP_DIR.glob("full_*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
        for stale in backups[7:]:
            stale.unlink(missing_ok=True)

        await session.execute(
            text(
                """
                INSERT INTO audit_logs (action, target)
                VALUES (:action, :target)
                """
            ),
            {
                "action": "scheduled_backup",
                "target": json.dumps({"path": backup_path, "interval_hours": interval_hours}),
            },
        )
        await session.commit()
