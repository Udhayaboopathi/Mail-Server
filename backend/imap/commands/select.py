from imap.session import IMAPSession


async def handle_select(session: IMAPSession, tag: str, args: str) -> None:
    await session.select(tag, args)
