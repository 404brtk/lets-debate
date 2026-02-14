from typing import Optional
from fastapi import (
    APIRouter,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import UUID4

from app.dependencies import SessionDep
from app.services.websocket_service import (
    ConnectionManager,
    authenticate_websocket_user,
    connected_payload,
    process_client_message,
)

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

    Events:
    - agent_thinking: Agent is generating response
    - agent_spoke: Agent posted a message
    - human_joined: Human participant joined
    - debate_started: Debate began
    - debate_paused: Debate paused
    - debate_completed: Debate finished
    - error: Error occurred
    """
    user, debate = authenticate_websocket_user(db=db, debate_id=debate_id, token=token)

    debate_key = str(debate_id)
    await manager.connect(websocket, debate_key)

    try:
        # Send connection confirmation
        await manager.send_personal_message(connected_payload(debate_key), websocket)

        # Listen for client messages
        while True:
            data = await websocket.receive_text()
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
        # Optionally notify others that someone left
        # await manager.broadcast(debate_key, {"type": "viewer_left", ...})
