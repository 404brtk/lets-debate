import logging
from typing import Optional

from fastapi import (
    APIRouter,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import UUID4

from app.dependencies import SessionDep
from app.services.debate_service import set_debate_status
from app.services.websocket_service import (
    ConnectionManager,
    authenticate_websocket_user,
    connected_payload,
    error_payload,
    parse_json_message,
    process_client_message,
    run_debate_via_websocket,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/debates/{debate_id}")
async def debate_websocket(
    websocket: WebSocket,
    debate_id: UUID4,
    db: SessionDep,
    token: Optional[str] = Query(default=None),
):
    """
    WebSocket endpoint for real-time debate updates.

    Client messages:
    - {"type": "start_debate"}: Start the automated AI debate
    - {"type": "human_message", "content": "...", "message_type": "argument"}: Human participation
    - {"type": "ping"}: Keep-alive ping

    Server events:
    - agent_thinking: Agent is generating response
    - agent_token: Streaming token from current agent
    - agent_spoke: Agent finished their turn
    - human_spoke: Human posted a message
    - debate_completed: Debate finished
    - error: Error occurred
    - connected: Connection confirmed
    - pong: Ping response
    """
    # Accept the connection FIRST, then authenticate.
    # This avoids the 403 HTTP rejection that FastAPI sends when a
    # WebSocketException is raised before accept().
    await websocket.accept()

    try:
        user, debate = authenticate_websocket_user(
            db=db, debate_id=debate_id, token=token
        )
    except Exception as exc:
        logger.warning("WebSocket auth failed for debate %s: %s", debate_id, exc)
        await websocket.send_json(error_payload(f"Authentication failed: {str(exc)}"))
        await websocket.close(code=1008, reason="Authentication failed")
        return

    debate_key = str(debate_id)

    # Register this connection with the manager (already accepted above)
    if debate_key not in manager.active_connections:
        manager.active_connections[debate_key] = []
    manager.active_connections[debate_key].append(websocket)

    try:
        # Send connection confirmation
        await manager.send_personal_message(connected_payload(debate_key), websocket)

        # Listen for client messages
        while True:
            data = await websocket.receive_text()
            logger.info("WS received message: %s", data[:200])

            try:
                message = parse_json_message(data)
            except Exception:
                await manager.send_personal_message(
                    error_payload("Invalid JSON payload"), websocket
                )
                continue

            msg_type = message.get("type")
            logger.info(
                "WS message type: %s, debate status: %s", msg_type, debate.status
            )

            if msg_type == "start_debate":
                # Transition debate to active status
                if debate.status == "pending" or debate.status == "paused":
                    from_status = debate.status
                    try:
                        set_debate_status(
                            db=db,
                            debate_id=debate_id,
                            user=user,
                            from_status=from_status,
                            to_status="active",
                            invalid_transition_message=f"Cannot start debate from {from_status} status",
                        )
                        # Refresh the debate object
                        db.refresh(debate)
                        logger.info("Debate status changed to: %s", debate.status)
                    except Exception as exc:
                        logger.error("Failed to start debate: %s", exc)
                        await manager.send_personal_message(
                            error_payload(str(exc)), websocket
                        )
                        continue

                if debate.status != "active":
                    await manager.send_personal_message(
                        error_payload(
                            f"Debate is in '{debate.status}' status, cannot start"
                        ),
                        websocket,
                    )
                    continue

                logger.info("Starting debate run via websocket...")
                # Run the full debate with streaming
                await run_debate_via_websocket(
                    manager=manager,
                    db=db,
                    debate=debate,
                    user=user,
                    debate_key=debate_key,
                )

            else:
                # Handle other message types (human_message, ping)
                dispatch, payload = process_client_message(
                    db=db,
                    debate=debate,
                    user=user,
                    debate_key=debate_key,
                    raw_data=data,
                )

                if dispatch == "broadcast":
                    await manager.broadcast(debate_key, payload)
                else:
                    await manager.send_personal_message(payload, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket, debate_key)
