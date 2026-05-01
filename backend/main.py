import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.audit import add_audit_logging
from api.middleware.rate_limit import add_rate_limiting
from api.routers import admin, auth, contacts, domains, folders, mail, mailboxes
from config import settings
from database import engine
from imap.server import create_imap_server
from models import Base
from smtp.server import create_smtp_server


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
    allow_origins=[
        settings.frontend_url.rstrip("/"),
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

add_rate_limiting(app)
add_audit_logging(app)

app.include_router(auth.router)
app.include_router(mail.router)
app.include_router(folders.router)
app.include_router(domains.router)
app.include_router(mailboxes.router)
app.include_router(admin.router)
app.include_router(contacts.router, prefix="/api/contacts")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
