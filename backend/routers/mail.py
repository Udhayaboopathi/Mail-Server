from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_user, get_user_mailbox
from models.user import User
from schemas.common import ActionResponse
from schemas.mail import MailFlagsRequest, MailMessageRead, MailMoveRequest, MailSendRequest, MailSummary, SearchResponse
from schemas.folder import FolderListResponse
from services.mail_service import MailService

router = APIRouter(prefix="/api/mail", tags=["mail"])


@router.get("/folders", response_model=FolderListResponse)
async def list_folders(_: User = Depends(get_current_user)) -> FolderListResponse:
    return FolderListResponse(folders=["Inbox", "Sent", "Drafts", "Trash", "Spam"])


@router.get("/{folder}", response_model=list[MailSummary])
async def list_messages(folder: str, page: int = Query(default=1, ge=1), limit: int = Query(default=50, ge=1, le=100), mailbox=Depends(get_user_mailbox)) -> list[MailSummary]:
    results = await MailService.list_messages(str(mailbox.id), folder, page, limit)
    return [MailSummary(**item) for item in results]


@router.get("/{folder}/{uid}", response_model=MailMessageRead)
async def get_message(folder: str, uid: int, mailbox=Depends(get_user_mailbox)) -> MailMessageRead:
    message = await MailService.get_message(str(mailbox.id), folder, uid)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return MailMessageRead(**message)


@router.post("/send", response_model=ActionResponse)
async def send_mail(payload: MailSendRequest, db: AsyncSession = Depends(get_db), mailbox=Depends(get_user_mailbox)) -> ActionResponse:
    await MailService.send_email(db, mailbox, payload.model_dump())
    return ActionResponse(status="queued")


@router.delete("/{folder}/{uid}", response_model=ActionResponse)
async def delete_message(folder: str, uid: int, mailbox=Depends(get_user_mailbox)) -> ActionResponse:
    MailService.backend.remove(str(mailbox.id), folder, uid)
    return ActionResponse(status="deleted")


@router.patch("/{folder}/{uid}/flags", response_model=ActionResponse)
async def set_flags(folder: str, uid: int, flags: MailFlagsRequest, mailbox=Depends(get_user_mailbox)) -> ActionResponse:
    active_flags = []
    if flags.seen:
        active_flags.append("S")
    if flags.flagged:
        active_flags.append("F")
    if flags.answered:
        active_flags.append("A")
    MailService.backend.set_flags(str(mailbox.id), folder, uid, "".join(active_flags))
    return ActionResponse(status="updated")


@router.post("/{folder}/{uid}/move", response_model=ActionResponse)
async def move_message(folder: str, uid: int, destination: MailMoveRequest, mailbox=Depends(get_user_mailbox)) -> ActionResponse:
    MailService.backend.move(str(mailbox.id), folder, destination.folder, uid)
    return ActionResponse(status="moved")


@router.get("/search", response_model=SearchResponse)
async def search(q: str, mailbox=Depends(get_user_mailbox)) -> SearchResponse:
    messages = MailService.backend.list_messages(str(mailbox.id), "Inbox")
    lowered = q.lower()
    results = [
        MailSummary(
            id=str(item["uid"]),
            uid=int(item["uid"]),
            sender=str(item["from"]),
            recipients=[str(item["to"])],
            subject=str(item["subject"]),
            date=str(item["date"]),
            flags=list(item["flags"]),
            size=int(item["size"]),
            has_attachments=False,
            preview="",
        )
        for item in messages
        if lowered in str(item["subject"]).lower() or lowered in str(item["from"]).lower()
    ]
    return SearchResponse(results=results)
