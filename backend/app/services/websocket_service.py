import json
from datetime import datetime, timezone
from typing import Literal
from typing import Optional

from fastapi import HTTPException, WebSocket, WebSocketException, status
from pydantic import UUID4
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Debate, Message, User
from app.services.auth_service import get_current_user_by_token
from app.services.debate_service import get_user_debate_or_404

ALLOWED_MESSAGE_TYPES = {
    "argument",
    "counter",
    "support",
    "question",
    "evidence",
    "conclusion",
}


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
    if token is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    try:
        user = get_current_user_by_token(token, db)
    except HTTPException as exc:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION) from exc

    try:
        debate = get_user_debate_or_404(db=db, debate_id=debate_id, user_id=user.id)
    except HTTPException as exc:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION) from exc

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
    if debate.status != "active":
        raise ValueError("Debate is not active")

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

    if msg_type == "ping":
        return "personal", pong_payload(debate_key)

    return "personal", error_payload("Unsupported message type")
