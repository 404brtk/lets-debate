from datetime import datetime
from typing import Optional, TYPE_CHECKING
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.agent_config import AgentConfig
    from app.models.message import Message
    from app.models.user import User


class Debate(Base):
    """Debate session model."""

    __tablename__ = "debates"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, active, paused, completed
    max_turns: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    current_turn: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Summary after completion
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    consensus_score: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True
    )  # Store as string to avoid float issues

    # Relationships
    user: Mapped["User"] = relationship(
        "User", back_populates="debates", lazy="joined"
    )  # Eager load user
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="debate",
        cascade="all, delete-orphan",
        lazy="select",  # Load messages on demand (can be many)
        order_by="Message.turn_number",
    )
    agent_configs: Mapped[list["AgentConfig"]] = relationship(
        "AgentConfig",
        back_populates="debate",
        cascade="all, delete-orphan",
        lazy="joined",  # Eager load agents (usually 3-5, not many)
    )

    def __repr__(self):
        return f"<Debate(id={self.id}, topic={self.topic[:50]}, status={self.status})>"
