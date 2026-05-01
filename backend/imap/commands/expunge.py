from imap.session import IMAPSession


async def handle_expunge(session: IMAPSession, tag: str, args: str) -> None:
    await session.expunge(tag, args)
