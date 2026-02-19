# Auth schemas
from app.schemas.auth import (
    ApiKeysResponse,
    ApiKeysUpdate,
    RefreshTokenRequest,
    Token,
    TokenData,
    TokenPair,
    UserCreate,
    UserResponse,
)

# Debate schemas
from app.schemas.debate import (
    AgentConfig,
    AgentConfigResponse,
    DebateCreate,
    DebateResponse,
)

# Message schemas
from app.schemas.message import MessageResponse, MessageCreate

# WebSocket event schemas
from app.schemas.websocket import (
    DebateEvent,
    AgentThinkingEvent,
    AgentSpokeEvent,
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
    "ApiKeysUpdate",
    "ApiKeysResponse",
    # Debate
    "AgentConfig",
    "AgentConfigResponse",
    "DebateCreate",
    "DebateResponse",
    # Message
    "MessageResponse",
    "MessageCreate",
    # WebSocket
    "DebateEvent",
    "AgentThinkingEvent",
    "AgentSpokeEvent",
    "DebateStatusEvent",
    "ErrorEvent",
    "ConnectedEvent",
]
