from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class DebateEvent(BaseModel):
    """Base WebSocket event."""

    type: str = Field(..., description="Event type")
    debate_id: str = Field(..., description="Debate UUID")
    timestamp: datetime = Field(..., description="Event timestamp")


class AgentThinkingEvent(DebateEvent):
    """Agent is generating response."""

    type: str = Field(default="agent_thinking", description="Event type")
    agent_id: str = Field(..., description="Agent UUID")
    agent_name: str = Field(..., description="Agent name")
    estimated_wait_ms: Optional[int] = Field(
        default=None, description="Estimated wait time in ms"
    )


class AgentSpokeEvent(DebateEvent):
    """Agent posted a message."""

    type: str = Field(default="agent_spoke", description="Event type")
    message: Dict[str, Any] = Field(..., description="Message data")
    next_agent: Optional[Dict[str, Any]] = Field(
        default=None, description="Next agent info"
    )


class DebateStatusEvent(DebateEvent):
    """Debate status changed."""

    type: str = Field(default="debate_status", description="Event type")
    status: str = Field(..., description="Status: started, paused, completed")
    reason: Optional[str] = Field(default=None, description="Status change reason")


class ErrorEvent(DebateEvent):
    """Error occurred."""

    type: str = Field(default="error", description="Event type")
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    recoverable: bool = Field(default=True, description="Whether error is recoverable")


class ConnectedEvent(DebateEvent):
    """Client connected successfully."""

    type: str = Field(default="connected", description="Event type")
    message: str = Field(..., description="Connection confirmation message")
