from imap.session import IMAPSession


async def handle_login(session: IMAPSession, tag: str, args: str) -> None:
    await session.login(tag, args)
