from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_user_mailbox
from imap.maildir import MaildirBackend
from schemas.tasks import TaskCreateRequest, TaskResponse, TaskUpdateRequest

router = APIRouter(tags=["tasks"])

_backend = MaildirBackend()


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    completed: bool | None = Query(default=None),
    mailbox=Depends(get_user_mailbox),
    db: AsyncSession = Depends(get_db),
) -> list[TaskResponse]:
    query = "SELECT * FROM tasks WHERE mailbox_id = :mailbox_id"
    params = {"mailbox_id": str(mailbox.id)}
    if completed is not None:
        query += " AND is_completed = :completed"
        params["completed"] = completed
    query += " ORDER BY created_at DESC"
    result = await db.execute(text(query), params)
    return [TaskResponse(**row) for row in result.mappings().all()]


@router.post("", response_model=TaskResponse)
async def create_task(payload: TaskCreateRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> TaskResponse:
    result = await db.execute(
        text(
            """
            INSERT INTO tasks (mailbox_id, title, description, due_at, priority, linked_email_uid, created_at, updated_at)
            VALUES (:mailbox_id, :title, :description, :due_at, :priority, :linked_email_uid, now(), now())
            RETURNING *
            """
        ),
        {
            "mailbox_id": str(mailbox.id),
            "title": payload.title,
            "description": payload.description,
            "due_at": payload.due_at,
            "priority": payload.priority,
            "linked_email_uid": payload.linked_email_uid,
        },
    )
    row = result.mappings().first()
    await db.commit()
    return TaskResponse(**row)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, payload: TaskUpdateRequest, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> TaskResponse:
    result = await db.execute(
        text(
            """
            UPDATE tasks
            SET title = COALESCE(:title, title),
                description = COALESCE(:description, description),
                due_at = COALESCE(:due_at, due_at),
                priority = COALESCE(:priority, priority),
                linked_email_uid = COALESCE(:linked_email_uid, linked_email_uid),
                updated_at = now()
            WHERE id = :task_id AND mailbox_id = :mailbox_id
            RETURNING *
            """
        ),
        {
            "task_id": task_id,
            "mailbox_id": str(mailbox.id),
            "title": payload.title,
            "description": payload.description,
            "due_at": payload.due_at,
            "priority": payload.priority,
            "linked_email_uid": payload.linked_email_uid,
        },
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    await db.commit()
    return TaskResponse(**row)


@router.delete("/{task_id}")
async def delete_task(task_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(
        text("DELETE FROM tasks WHERE id = :task_id AND mailbox_id = :mailbox_id"),
        {"task_id": task_id, "mailbox_id": str(mailbox.id)},
    )
    await db.commit()
    return {"status": "deleted"}


@router.post("/{task_id}/complete")
async def complete_task(task_id: str, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        text(
            """
            UPDATE tasks
            SET is_completed = true, completed_at = now(), updated_at = now()
            WHERE id = :task_id AND mailbox_id = :mailbox_id
            """
        ),
        {"task_id": task_id, "mailbox_id": str(mailbox.id)},
    )
    await db.commit()
    return {"completed": result.rowcount > 0}


@router.post("/from-email/{email_uid}", response_model=TaskResponse)
async def create_from_email(email_uid: int, mailbox=Depends(get_user_mailbox), db: AsyncSession = Depends(get_db)) -> TaskResponse:
    message = _backend.read_message(str(mailbox.id), "Inbox", email_uid)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    subject = message.get("Subject", "Follow up")
    result = await db.execute(
        text(
            """
            INSERT INTO tasks (mailbox_id, title, description, linked_email_uid, created_at, updated_at)
            VALUES (:mailbox_id, :title, NULL, :linked_email_uid, now(), now())
            RETURNING *
            """
        ),
        {"mailbox_id": str(mailbox.id), "title": subject, "linked_email_uid": str(email_uid)},
    )
    row = result.mappings().first()
    await db.commit()
    return TaskResponse(**row)
