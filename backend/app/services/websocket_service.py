import asyncio
import json
import uuid as _uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import HTTPException, WebSocket
from pydantic import UUID4
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, Session

from app.models import Debate, Message, User
from app.services.auth_service import get_current_user_by_token, get_decrypted_api_keys
from app.services.llm_service import (
    AgentSpec,
    DebateGraphState,
    generate_consensus,
    run_full_debate,
)

ALLOWED_MESSAGE_TYPES = {
    "argument",
    "counter",
    "support",
    "question",
    "evidence",
    "conclusion",
}


@dataclass
class DebateSession:
    """Tracks a running debate's control handles."""

    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    human_message_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    task: Optional[asyncio.Task] = None


# Module-level registry of active debate sessions keyed by debate_id string
active_debate_sessions: dict[str, DebateSession] = {}


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, debate_id: str) -> None:
        await websocket.accept()
        if debate_id not in self.active_connections:
            self.active_connections[debate_id] = []
        self.active_connections[debate_id].append(websocket)

    def disconnect(self, websocket: WebSocket, debate_id: str) -> None:
        if debate_id not in self.active_connections:
            return
        if websocket in self.active_connections[debate_id]:
            self.active_connections[debate_id].remove(websocket)
        if not self.active_connections[debate_id]:
            del self.active_connections[debate_id]

    async def send_personal_message(
        self, message: dict[str, object], websocket: WebSocket
    ) -> None:
        await websocket.send_json(message)

    async def broadcast(self, debate_id: str, message: dict[str, object]) -> None:
        if debate_id not in self.active_connections:
            return

        dead_connections: list[WebSocket] = []
        for connection in self.active_connections[debate_id]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        for connection in dead_connections:
            self.disconnect(connection, debate_id)


def authenticate_websocket_user(
    db: Session, debate_id: UUID4, token: Optional[str]
) -> tuple[User, Debate]:
    """Authenticate a WebSocket user and return the user + debate."""
    if token is None:
        raise ValueError("Missing authentication token")

    try:
        user = get_current_user_by_token(token, db)
    except HTTPException as exc:
        raise ValueError("Invalid or expired authentication token") from exc

    stmt = (
        select(Debate)
        .options(joinedload(Debate.agent_configs))
        .where(Debate.id == debate_id, Debate.user_id == user.id)
    )
    debate = db.scalar(stmt)
    if debate is None:
        raise ValueError("Debate not found or access denied")

    return user, debate


def parse_json_message(raw_data: str) -> dict[str, object]:
    return json.loads(raw_data)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def error_payload(error: str) -> dict[str, str]:
    return {
        "type": "error",
        "error": error,
        "timestamp": utc_timestamp(),
    }


def connected_payload(debate_key: str) -> dict[str, str]:
    return {
        "type": "connected",
        "debate_id": debate_key,
        "message": "Connected to debate",
        "timestamp": utc_timestamp(),
    }


def pong_payload(debate_key: str) -> dict[str, str]:
    return {
        "type": "pong",
        "debate_id": debate_key,
        "timestamp": utc_timestamp(),
    }


def persist_human_message(
    db: Session,
    debate: Debate,
    user: User,
    content: str,
    message_type: str,
) -> Message:
    if debate.status not in ("active", "paused"):
        raise ValueError("Debate is not active or paused")

    if message_type not in ALLOWED_MESSAGE_TYPES:
        raise ValueError("Unsupported message_type")

    max_turn = db.scalar(
        select(func.max(Message.turn_number)).where(Message.debate_id == debate.id)
    )
    next_turn = (max_turn or 0) + 1

    message_row = Message(
        debate_id=debate.id,
        agent_id=None,
        agent_name=user.username,
        content=content,
        message_type=message_type,
        turn_number=next_turn,
    )
    db.add(message_row)
    debate.current_turn = next_turn
    db.commit()
    db.refresh(message_row)
    return message_row


def _build_agent_specs(debate: Debate) -> list[AgentSpec]:
    """Convert DB AgentConfig models to AgentSpec data classes for the LLM service."""
    agents = sorted(debate.agent_configs, key=lambda a: a.order_index)
    return [
        AgentSpec(
            id=str(a.id),
            name=a.name,
            role=a.role,
            model_provider=a.model_provider,
            model_name=a.model_name,
            temperature=a.temperature,
            system_prompt=a.system_prompt,
            order_index=a.order_index,
        )
        for a in agents
        if a.is_active
    ]


def _load_existing_messages(db: Session, debate_id) -> list[dict]:
    """Load existing debate messages for LLM context."""
    stmt = (
        select(Message)
        .where(Message.debate_id == debate_id)
        .order_by(Message.turn_number.asc(), Message.created_at.asc())
    )
    return [
        {
            "agent_id": str(m.agent_id) if m.agent_id else None,
            "agent_name": m.agent_name,
            "content": m.content,
            "turn_number": m.turn_number,
        }
        for m in db.scalars(stmt).unique().all()
    ]


def _resolve_next_agent_index(
    agents: list[AgentSpec], existing_messages: list[dict]
) -> int:
    """Pick the next speaking agent based on the last AI speaker in history."""
    if not agents:
        return 0

    for msg in reversed(existing_messages):
        agent_id = msg.get("agent_id")
        if not agent_id:
            continue

        for idx, agent in enumerate(agents):
            if agent.id == agent_id:
                return (idx + 1) % len(agents)

    return 0


async def run_debate_via_websocket(
    manager: ConnectionManager,
    db: Session,
    debate: Debate,
    user: User,
    debate_key: str,
    session: DebateSession,
) -> None:
    """Run the full automated debate, streaming events over WebSocket."""
    api_keys = get_decrypted_api_keys(user)
    agents = _build_agent_specs(debate)

    if not agents:
        await manager.broadcast(
            debate_key, error_payload("No active agents configured for this debate")
        )
        return

    # Validate that the user has API keys for all required providers
    required_providers = {a.model_provider for a in agents}
    required_providers.discard("ollama")  # Ollama needs no API key
    key_map = {"openai": api_keys.get("openai"), "gemini": api_keys.get("google")}
    missing = [p for p in required_providers if not key_map.get(p)]
    if missing:
        await manager.broadcast(
            debate_key,
            error_payload(
                f"Missing API key(s) for provider(s): {', '.join(missing)}. "
                "Please add your API key in profile settings."
            ),
        )
        return

    existing_messages = _load_existing_messages(db, debate.id)

    state = DebateGraphState(
        topic=debate.topic,
        description=debate.description or "",
        agents=agents,
        api_keys=api_keys,
        messages=existing_messages,
        current_agent_index=_resolve_next_agent_index(agents, existing_messages),
        turn_count=debate.current_turn,
        max_turns=debate.max_turns,
    )

    debate_paused = False

    try:
        async for event in run_full_debate(
            state,
            stop_event=session.stop_event,
            human_message_queue=session.human_message_queue,
        ):
            event_type = event["type"]

            if event_type == "agent_thinking":
                agent: AgentSpec = event["agent"]
                await manager.broadcast(
                    debate_key,
                    {
                        "type": "agent_thinking",
                        "debate_id": debate_key,
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "agent_role": agent.role,
                        "timestamp": utc_timestamp(),
                    },
                )

            elif event_type == "agent_token":
                agent = event["agent"]
                await manager.broadcast(
                    debate_key,
                    {
                        "type": "agent_token",
                        "debate_id": debate_key,
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "token": event["token"],
                    },
                )

            elif event_type == "agent_spoke":
                agent = event["agent"]
                turn = event["turn"]
                content = event["content"]

                # Persist the message to DB
                message_row = Message(
                    debate_id=debate.id,
                    agent_id=None,
                    agent_name=agent.name,
                    content=content,
                    message_type="argument",
                    turn_number=turn,
                    model_used=agent.model_name,
                )
                try:
                    message_row.agent_id = _uuid.UUID(agent.id)
                except (ValueError, AttributeError):
                    pass

                db.add(message_row)
                debate.current_turn = turn
                db.commit()
                db.refresh(message_row)

                await manager.broadcast(
                    debate_key,
                    {
                        "type": "agent_spoke",
                        "debate_id": debate_key,
                        "message_id": str(message_row.id),
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "agent_role": agent.role,
                        "content": content,
                        "message_type": "argument",
                        "turn_number": turn,
                        "timestamp": message_row.created_at.isoformat(),
                    },
                )

            elif event_type == "human_injected":
                human_msg = event["message"]
                await manager.broadcast(
                    debate_key,
                    {
                        "type": "human_injected",
                        "debate_id": debate_key,
                        "agent_name": human_msg.get("agent_name", "Human"),
                        "content": human_msg.get("content", ""),
                        "turn_number": human_msg.get("turn_number", 0),
                        "timestamp": utc_timestamp(),
                    },
                )

            elif event_type == "debate_paused":
                debate_paused = True
                debate.status = "paused"
                db.commit()

                await manager.broadcast(
                    debate_key,
                    {
                        "type": "debate_paused",
                        "debate_id": debate_key,
                        "total_turns": event["total_turns"],
                        "timestamp": utc_timestamp(),
                    },
                )

            elif event_type == "debate_completed":
                debate.status = "completed"
                debate.completed_at = datetime.now(timezone.utc)
                db.commit()

                await manager.broadcast(
                    debate_key,
                    {
                        "type": "debate_completed",
                        "debate_id": debate_key,
                        "total_turns": event["total_turns"],
                        "timestamp": utc_timestamp(),
                    },
                )

        # Generate consensus after natural completion (not paused)
        if not debate_paused:
            await manager.broadcast(
                debate_key,
                {
                    "type": "consensus_started",
                    "debate_id": debate_key,
                    "timestamp": utc_timestamp(),
                },
            )

            try:
                async for c_event in generate_consensus(state):
                    if c_event["type"] == "consensus_token":
                        await manager.broadcast(
                            debate_key,
                            {
                                "type": "consensus_token",
                                "debate_id": debate_key,
                                "token": c_event["token"],
                            },
                        )
                    elif c_event["type"] == "consensus_complete":
                        db.refresh(debate)
                        debate.summary = c_event["summary"]
                        db.commit()
                        db.refresh(debate)

                        await manager.broadcast(
                            debate_key,
                            {
                                "type": "consensus_generated",
                                "debate_id": debate_key,
                                "summary": c_event["summary"],
                                "timestamp": utc_timestamp(),
                            },
                        )
            except Exception as exc:
                await manager.broadcast(
                    debate_key,
                    error_payload(f"Consensus generation failed: {str(exc)}"),
                )

    except asyncio.CancelledError:
        # Task was cancelled (e.g. client disconnected)
        debate.status = "paused"
        db.commit()
        await manager.broadcast(
            debate_key,
            {
                "type": "debate_paused",
                "debate_id": debate_key,
                "total_turns": state.turn_count,
                "timestamp": utc_timestamp(),
            },
        )
    except Exception as exc:
        await manager.broadcast(
            debate_key,
            error_payload(f"Debate error: {str(exc)}"),
        )
        raise
    finally:
        # Clean up session from registry
        active_debate_sessions.pop(debate_key, None)


def process_client_message(
    db: Session,
    debate: Debate,
    user: User,
    debate_key: str,
    raw_data: str,
) -> tuple[Literal["personal", "broadcast"], dict[str, object]]:
    try:
        message = parse_json_message(raw_data)
    except json.JSONDecodeError:
        return "personal", error_payload("Invalid JSON payload")

    msg_type = message.get("type")

    if msg_type == "human_message":
        content = str(message.get("content", "")).strip()
        if not content:
            return "personal", error_payload("Message content cannot be empty")

        message_type = str(message.get("message_type", "argument"))
        if message_type not in ALLOWED_MESSAGE_TYPES:
            return "personal", error_payload("Unsupported message_type")

        try:
            message_row = persist_human_message(
                db=db,
                debate=debate,
                user=user,
                content=content,
                message_type=message_type,
            )
        except ValueError as exc:
            return "personal", error_payload(str(exc))

        # Also enqueue into the running debate session so agents see this message
        session = active_debate_sessions.get(debate_key)
        if session is not None and not session.stop_event.is_set():
            session.human_message_queue.put_nowait(
                {
                    "agent_name": user.username,
                    "content": content,
                    "turn_number": message_row.turn_number,
                    "role": "human",
                }
            )

        return (
            "broadcast",
            {
                "type": "human_spoke",
                "debate_id": debate_key,
                "message_id": str(message_row.id),
                "user_id": str(user.id),
                "username": user.username,
                "content": message_row.content,
                "message_type": message_row.message_type,
                "turn_number": message_row.turn_number,
                "timestamp": message_row.created_at.isoformat(),
            },
        )

    if msg_type == "pause_debate":
        session = active_debate_sessions.get(debate_key)
        if session is not None:
            session.stop_event.set()
            return "personal", {
                "type": "pause_acknowledged",
                "debate_id": debate_key,
                "timestamp": utc_timestamp(),
            }
        return "personal", error_payload("No active debate session to pause")

    if msg_type == "ping":
        return "personal", pong_payload(debate_key)

    return "personal", error_payload("Unsupported message type")
