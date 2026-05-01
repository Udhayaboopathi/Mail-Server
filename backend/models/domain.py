import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Text, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    dkim_private_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    dkim_selector: Mapped[str] = mapped_column(String(63), default="mail", nullable=False)
    spf_record: Mapped[str | None] = mapped_column(Text, nullable=True)
    dmarc_record: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    mailboxes = relationship("Mailbox", back_populates="domain", cascade="all, delete-orphan")
    aliases = relationship("Alias", back_populates="domain", cascade="all, delete-orphan")
