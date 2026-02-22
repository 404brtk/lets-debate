from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, UUID4, Field

AgentRole = Literal["skeptic", "optimist", "expert", "pragmatist", "synthesizer"]
ModelProvider = Literal["openai", "gemini", "ollama"]
DebateStatus = Literal["pending", "active", "paused", "completed"]


class AgentConfig(BaseModel):
    """Agent configuration for debate."""

    role: AgentRole = Field(
        ...,
        description="Agent role: skeptic, optimist, expert, pragmatist, synthesizer",
    )
    name: str = Field(
        ..., min_length=1, max_length=50, description="Agent display name"
    )
    model_provider: ModelProvider = Field(
        ..., description="LLM provider: openai or gemini"
    )
    model_name: str = Field(..., description="Model name: gemini-2.5-flash, etc.")
    temperature: float = Field(
        default=0.5, ge=0.0, le=2.0, description="LLM temperature"
    )

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AgentConfigResponse(BaseModel):
    """Agent config in debate responses."""

    id: UUID4 = Field(..., description="Agent config UUID")
    name: str = Field(..., description="Agent display name")
    role: AgentRole = Field(..., description="Agent role")
    model_provider: ModelProvider = Field(..., description="LLM provider")
    model_name: str = Field(..., description="Model name")
    temperature: float = Field(..., description="LLM temperature")
    order_index: int = Field(..., description="Turn order index")
    is_active: bool = Field(..., description="Whether agent is active")

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class DebateCreate(BaseModel):
    """Create debate request."""

    topic: str = Field(
        ..., min_length=5, max_length=500, description="Debate topic/question"
    )
    description: Optional[str] = Field(
        default=None, max_length=2000, description="Optional context"
    )
    max_turns: int = Field(
        default=20, ge=5, le=50, description="Maximum number of turns"
    )
    agents: list[AgentConfig] = Field(
        ..., min_length=2, max_length=5, description="Agent configurations"
    )

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DebateResponse(BaseModel):
    """Debate response."""

    id: UUID4 = Field(..., description="Debate UUID")
    topic: str = Field(..., description="Debate topic")
    description: Optional[str] = Field(default=None, description="Debate description")
    status: DebateStatus = Field(
        ..., description="Debate status: pending, active, paused, completed"
    )
    max_turns: int = Field(..., description="Maximum turns")
    current_turn: int = Field(..., description="Current turn number")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(
        default=None, description="Last update timestamp"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="Completion timestamp"
    )
    summary: Optional[str] = Field(default=None, description="Consensus summary")
    agent_configs: list[AgentConfigResponse] = Field(
        default_factory=list, description="Agent configurations"
    )

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )
