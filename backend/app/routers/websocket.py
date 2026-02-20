import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import UUID4

from app.db.session import SessionLocal
from app.services.websocket_service import (
    ConnectionManager,
    DebateSession,
    active_debate_sessions,
    authenticate_websocket_user,
    connected_payload,
    error_payload,
    parse_json_message,
    process_client_message,
    run_debate_via_websocket,
)

logger = logging.getLogger(__name__)

router = APIRouter()
manager = ConnectionManager()


@router.websocket("/debates/{debate_id}")
async def websocket_debate(
    websocket: WebSocket,
    debate_id: UUID4,
    token: str = Query(default=None),
):
    """WebSocket endpoint for real-time debate interaction.

    Key design: debate execution runs as an asyncio.Task so the
    WS receive loop remains free to process pause/human messages.
    """
    db = SessionLocal()
    debate_key = str(debate_id)

    await manager.connect(websocket, debate_key)

    try:
        # Authenticate
        try:
            user, debate = authenticate_websocket_user(db, debate_id, token)
        except ValueError as exc:
            await manager.send_personal_message(error_payload(str(exc)), websocket)
            return

        await manager.send_personal_message(connected_payload(debate_key), websocket)

        # Main receive loop — never blocked by debate execution
        while True:
            raw_data = await websocket.receive_text()

            try:
                message = parse_json_message(raw_data)
            except Exception:
                await manager.send_personal_message(
                    error_payload("Invalid JSON payload"), websocket
                )
                continue

            msg_type = message.get("type")

            if msg_type == "start_debate":
                # Validate status transition
                if debate.status not in ("pending", "paused"):
                    await manager.send_personal_message(
                        error_payload(
                            f"Cannot start debate in '{debate.status}' status"
                        ),
                        websocket,
                    )
                    continue

                # Don't start if already running
                if debate_key in active_debate_sessions:
                    await manager.send_personal_message(
                        error_payload("Debate is already running"),
                        websocket,
                    )
                    continue

                # Transition to active
                debate.status = "active"
                db.commit()

                # Create session and register
                session = DebateSession()
                active_debate_sessions[debate_key] = session

                # Launch debate as background task
                session.task = asyncio.create_task(
                    run_debate_via_websocket(
                        manager=manager,
                        db=db,
                        debate=debate,
                        user=user,
                        debate_key=debate_key,
                        session=session,
                    )
                )

                await manager.broadcast(
                    debate_key,
                    {
                        "type": "debate_started",
                        "debate_id": debate_key,
                    },
                )

            elif msg_type == "pause_debate":
                session = active_debate_sessions.get(debate_key)
                if session is not None:
                    session.stop_event.set()
                else:
                    await manager.send_personal_message(
                        error_payload("No active debate session to pause"),
                        websocket,
                    )

            elif msg_type == "human_message":
                scope, payload = process_client_message(
                    db=db,
                    debate=debate,
                    user=user,
                    debate_key=debate_key,
                    raw_data=raw_data,
                )

                if (
                    scope == "broadcast"
                    and payload.get("type") == "human_spoke"
                    and debate.status == "paused"
                    and debate_key not in active_debate_sessions
                ):
                    debate.status = "active"
                    db.commit()

                    session = DebateSession()
                    active_debate_sessions[debate_key] = session
                    session.task = asyncio.create_task(
                        run_debate_via_websocket(
                            manager=manager,
                            db=db,
                            debate=debate,
                            user=user,
                            debate_key=debate_key,
                            session=session,
                        )
                    )

                    await manager.broadcast(
                        debate_key,
                        {
                            "type": "debate_started",
                            "debate_id": debate_key,
                        },
                    )

                if scope == "broadcast":
                    await manager.broadcast(debate_key, payload)
                else:
                    await manager.send_personal_message(payload, websocket)

            elif msg_type == "ping":
                await manager.send_personal_message(
                    {"type": "pong", "debate_id": debate_key}, websocket
                )

            else:
                await manager.send_personal_message(
                    error_payload("Unsupported message type"), websocket
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for debate {debate_key}")
    except Exception as exc:
        logger.error(f"WebSocket error for debate {debate_key}: {exc}")
    finally:
        manager.disconnect(websocket, debate_key)

        # Cancel running debate task if this was the last connection
        if debate_key not in manager.active_connections:
            session = active_debate_sessions.get(debate_key)
            if session is not None and session.task is not None:
                session.task.cancel()
                try:
                    await session.task
                except (asyncio.CancelledError, Exception):
                    pass
                active_debate_sessions.pop(debate_key, None)

        db.close()
