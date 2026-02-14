from datetime import datetime
from typing import Optional, TYPE_CHECKING
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.agent_config import AgentConfig
    from app.models.debate import Debate


class Message(Base):
    """Debate message model."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    debate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("debates.id"), nullable=False
    )
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agent_configs.id"), nullable=True
    )  # NULL if human
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(
        String(20), default="argument", nullable=False
    )  # argument, counter, support, question, evidence, conclusion
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("messages.id"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # LLM metadata
    model_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tokens_input: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # Store as string for precision

    # Analysis
    sentiment: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True
    )  # -1.0 to 1.0 as string
    extra_data: Mapped[dict[str, object]] = mapped_column(
        JSONB, default=dict, nullable=False
    )  # Flexible metadata storage (can't use 'metadata' - reserved)

    # Relationships
    debate: Mapped["Debate"] = relationship(
        "Debate", back_populates="messages", lazy="joined"
    )  # Always need debate
    agent: Mapped[Optional["AgentConfig"]] = relationship(
        "AgentConfig", back_populates="messages", lazy="joined"
    )  # Always need agent info

    def __repr__(self):
        return f"<Message(id={self.id}, debate_id={self.debate_id}, turn={self.turn_number})>"
