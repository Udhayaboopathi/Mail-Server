import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.audit import add_audit_logging
from api.middleware.rate_limit import add_rate_limiting
from api.routers import (
    admin,
    auth,
    auth_extended,
    api_keys,
    campaigns,
    calendar as cal_router,
    contacts,
    delegation,
    domains,
    ediscovery,
    labels,
    mail,
    folders,
    mailboxes,
    notes_router,
    pgp,
    rules,
    send_api,
    shared_mailboxes,
    spam_reports,
    templates,
    threads,
    tracking,
    webhooks,
    whitelabel,
    ai as ai_router,
    tasks_router,
)
from config import settings
from imap.server import create_imap_server
from smtp.server import create_smtp_server


@asynccontextmanager
async def lifespan(app: FastAPI):
    smtp_server = None
    imap_task = None
    if settings.enable_mail_servers:
        smtp_server = await create_smtp_server()
        imap_task = asyncio.create_task(create_imap_server())
    try:
        yield
    finally:
        if smtp_server is not None:
            smtp_server.close()
            await smtp_server.wait_closed()
        if imap_task is not None:
            imap_task.cancel()
            with suppress(asyncio.CancelledError):
                await imap_task


app = FastAPI(lifespan=lifespan, title="Email System", version="1.0.0")

app.add_middleware(
        CORSMiddleware,
        # Allow frontend local dev and the backend host for testing.
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            f"http://{settings.server_ip}",
            f"http://{settings.server_ip}:45645",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

add_rate_limiting(app)
add_audit_logging(app)

app.include_router(auth.router)
app.include_router(auth_extended.router, prefix="/api/auth")
app.include_router(mail.router)
app.include_router(folders.router)
app.include_router(domains.router)
app.include_router(mailboxes.router)
app.include_router(admin.router)
app.include_router(contacts.router, prefix="/api/contacts")
app.include_router(pgp.router, prefix="/api/pgp")
app.include_router(threads.router, prefix="/api/mail")
app.include_router(labels.router, prefix="/api/labels")
app.include_router(rules.router, prefix="/api/rules")
app.include_router(templates.router, prefix="/api/templates")
app.include_router(ai_router.router, prefix="/api/ai")
app.include_router(cal_router.router, prefix="/api/calendar")
app.include_router(tasks_router.router, prefix="/api/tasks")
app.include_router(notes_router.router, prefix="/api/notes")
app.include_router(shared_mailboxes.router, prefix="/api/shared-mailboxes")
app.include_router(delegation.router, prefix="/api/delegation")
app.include_router(api_keys.router, prefix="/api/keys")
app.include_router(send_api.router, prefix="/api/v1")
app.include_router(tracking.router, prefix="/api/track")
app.include_router(tracking.router, prefix="/api/unsubscribe")
app.include_router(campaigns.router, prefix="/api/campaigns")
app.include_router(webhooks.router, prefix="/api/webhooks")
app.include_router(spam_reports.router, prefix="/api/mail/report")
app.include_router(ediscovery.router, prefix="/api/admin/ediscovery")
app.include_router(whitelabel.router, prefix="/api/admin/whitelabel")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
