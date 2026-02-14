from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, UUID4, Field

MessageType = Literal[
    "argument",
    "counter",
    "support",
    "question",
    "evidence",
    "conclusion",
]


class MessageResponse(BaseModel):
    """Debate message response."""

    id: UUID4 = Field(..., description="Message UUID")
    agent_id: Optional[UUID4] = Field(
        default=None, description="Agent UUID (None if human)"
    )
    agent_name: str = Field(..., description="Display name of agent/human")
    content: str = Field(..., description="Message content")
    message_type: MessageType = Field(
        ...,
        description="Type: argument, counter, support, question, evidence, conclusion",
    )
    turn_number: int = Field(..., description="Debate turn number")
    created_at: datetime = Field(..., description="Message timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class MessageCreate(BaseModel):
    """Create message request (for human participation)."""

    content: str = Field(..., min_length=1, description="Message content")
    message_type: MessageType = Field(default="argument", description="Message type")

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
