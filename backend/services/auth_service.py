from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.session import Session
from models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        return pwd_context.verify(password, hashed_password)

    @staticmethod
    def create_access_token(subject: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": subject,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()),
            "type": "access",
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def create_refresh_token(subject: str) -> tuple[str, str]:
        token = secrets.token_urlsafe(48)
        token_hash = sha256(token.encode("utf-8")).hexdigest()
        return token, token_hash

    @staticmethod
    def hash_token(token: str) -> str:
        return sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    async def authenticate_user(session: AsyncSession, email: str, password: str) -> User | None:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            return None
        if not AuthService.verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    async def store_refresh_token(session: AsyncSession, user: User, token_hash: str, ip_address: str | None) -> Session:
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        session_row = Session(user_id=user.id, refresh_token_hash=token_hash, expires_at=expires_at, ip_address=ip_address)
        session.add(session_row)
        await session.commit()
        await session.refresh(session_row)
        return session_row

    @staticmethod
    async def invalidate_refresh_token(session: AsyncSession, token_hash: str) -> None:
        result = await session.execute(select(Session).where(Session.refresh_token_hash == token_hash))
        row = result.scalar_one_or_none()
        if row:
            await session.delete(row)
            await session.commit()
