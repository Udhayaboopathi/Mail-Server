from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

from config import settings
from database import AsyncSessionLocal
from tasks.celery_app import celery_app


@celery_app.task(name="tasks.retention_tasks.enforce_retention_policies")
def enforce_retention_policies() -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            domains = await db.execute(
                text("SELECT id, retention_days FROM domains WHERE retention_days > 0")
            )
            for domain in domains.mappings().all():
                cutoff = datetime.now(timezone.utc) - timedelta(days=int(domain["retention_days"]))
                mailboxes = await db.execute(
                    text("SELECT id, maildir_path FROM mailboxes WHERE domain_id = :domain_id"),
                    {"domain_id": str(domain["id"])},
                )
                for mailbox in mailboxes.mappings().all():
                    maildir_path = Path(mailbox["maildir_path"] or Path(settings.maildir_base) / str(mailbox["id"]))
                    if not maildir_path.exists():
                        continue
                    removed_bytes = 0
                    for folder in ("cur", "new"):
                        folder_path = maildir_path / folder
                        if not folder_path.exists():
                            continue
                        for item in folder_path.iterdir():
                            if not item.is_file():
                                continue
                            mtime = datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc)
                            if mtime < cutoff:
                                removed_bytes += item.stat().st_size
                                item.unlink(missing_ok=True)

                    if removed_bytes > 0:
                        await db.execute(
                            text(
                                """
                                UPDATE mailboxes
                                SET used_mb = GREATEST(used_mb - :delta, 0)
                                WHERE id = :mailbox_id
                                """
                            ),
                            {"delta": removed_bytes / (1024 * 1024), "mailbox_id": str(mailbox["id"])},
                        )
                        await db.execute(
                            text(
                                """
                                INSERT INTO audit_logs (action, target)
                                VALUES (:action, :target)
                                """
                            ),
                            {
                                "action": "retention_cleanup",
                                "target": f"{mailbox['id']}:{removed_bytes}",
                            },
                        )
            await db.commit()

    import asyncio

    asyncio.run(_run())
