# Auth schemas
from app.schemas.auth import (
    RefreshTokenRequest,
    Token,
    TokenData,
    TokenPair,
    UserCreate,
    UserResponse,
)

# Debate schemas
from app.schemas.debate import AgentConfig, DebateCreate, DebateResponse

# Message schemas
from app.schemas.message import MessageResponse, MessageCreate

# WebSocket event schemas
from app.schemas.websocket import (
    DebateEvent,
    AgentThinkingEvent,
    AgentSpokeEvent,
    HumanJoinedEvent,
    DebateStatusEvent,
    ErrorEvent,
    ConnectedEvent,
)

__all__ = [
    # Auth
    "UserCreate",
    "UserResponse",
    "Token",
    "TokenPair",
    "RefreshTokenRequest",
    "TokenData",
    # Debate
    "AgentConfig",
    "DebateCreate",
    "DebateResponse",
    # Message
    "MessageResponse",
    "MessageCreate",
    # WebSocket
    "DebateEvent",
    "AgentThinkingEvent",
    "AgentSpokeEvent",
    "HumanJoinedEvent",
    "DebateStatusEvent",
    "ErrorEvent",
    "ConnectedEvent",
]
