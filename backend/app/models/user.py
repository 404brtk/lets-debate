from datetime import datetime
from typing import Optional, TYPE_CHECKING
import uuid

from sqlalchemy import Boolean, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.debate import Debate
    from app.models.refresh_token import RefreshToken


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Encrypted LLM API keys (user-provided)
    encrypted_openai_key: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, default=None
    )
    encrypted_google_key: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, default=None
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    debates: Mapped[list["Debate"]] = relationship(
        "Debate",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"

    @property
    def has_openai_key(self) -> bool:
        return self.encrypted_openai_key is not None

    @property
    def has_google_key(self) -> bool:
        return self.encrypted_google_key is not None
