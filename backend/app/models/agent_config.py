from datetime import datetime
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.debate import Debate
    from app.models.message import Message


class AgentConfig(Base):
    __tablename__ = "agent_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    debate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("debates.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # skeptic, optimist, expert, pragmatist, synthesizer
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)

    # LLM configuration
    model_provider: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # openai, gemini
    model_name: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # gpt-5, gemini-3-pro, etc.
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)

    # Turn order
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    debate: Mapped["Debate"] = relationship(
        "Debate", back_populates="agent_configs", lazy="joined"
    )  # Always need debate
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="agent",
        lazy="select",  # Load messages on demand (can be many)
    )

    def __repr__(self):
        return f"<AgentConfig(id={self.id}, name={self.name}, role={self.role})>"
