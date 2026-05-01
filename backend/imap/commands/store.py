from imap.session import IMAPSession


async def handle_store(session: IMAPSession, tag: str, args: str) -> None:
    await session.store(tag, args)
