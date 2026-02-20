from typing import Annotated
from fastapi import APIRouter, Query, status as http_status
from fastapi.responses import Response
from pydantic import UUID4

from app.dependencies import CurrentUser, SessionDep
from app.services.debate_service import (
    create_debate_with_agents,
    delete_debate_for_user,
    get_debate_messages,
    get_user_debate_or_404,
    list_user_debates,
    participate_in_debate,
    resume_debate_for_user,
    stop_debate_for_user,
)
from app.schemas import DebateCreate, DebateResponse, MessageCreate, MessageResponse

router = APIRouter()


@router.post("", response_model=DebateResponse)
async def create_debate(
    debate: DebateCreate,
    current_user: CurrentUser,
    db: SessionDep,
):
    """Create a new debate with configured agents."""
    return create_debate_with_agents(db=db, debate_in=debate, user=current_user)


@router.get("", response_model=list[DebateResponse])
async def list_debates(
    current_user: CurrentUser,
    db: SessionDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
):
    """List debates with pagination."""
    return list_user_debates(db=db, user=current_user, skip=skip, limit=limit)


@router.get("/{debate_id}", response_model=DebateResponse)
async def get_debate(debate_id: UUID4, current_user: CurrentUser, db: SessionDep):
    """Get debate details by ID."""
    return get_user_debate_or_404(db=db, debate_id=debate_id, user_id=current_user.id)


@router.delete("/{debate_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_debate(
    debate_id: UUID4,
    current_user: CurrentUser,
    db: SessionDep,
):
    """Delete a debate and all related data."""
    delete_debate_for_user(db=db, debate_id=debate_id, user=current_user)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.post("/{debate_id}/stop")
async def stop_debate(
    debate_id: UUID4,
    current_user: CurrentUser,
    db: SessionDep,
):
    """Stop a running debate (signals WS session and updates DB status to paused)."""
    return stop_debate_for_user(
        db=db,
        debate_id=debate_id,
        user=current_user,
    )


@router.post("/{debate_id}/resume")
async def resume_debate(
    debate_id: UUID4,
    current_user: CurrentUser,
    db: SessionDep,
):
    """Resume a paused debate (sets DB status to active; WS start_debate triggers execution)."""
    return resume_debate_for_user(
        db=db,
        debate_id=debate_id,
        user=current_user,
    )


@router.get("/{debate_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    debate_id: UUID4,
    current_user: CurrentUser,
    db: SessionDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    """Get debate messages with pagination."""
    return get_debate_messages(
        db=db,
        debate_id=debate_id,
        user=current_user,
        skip=skip,
        limit=limit,
    )


@router.post("/{debate_id}/participate", response_model=MessageResponse)
async def human_participate(
    debate_id: UUID4,
    body: MessageCreate,
    current_user: CurrentUser,
    db: SessionDep,
):
    """Submit a human message to an active debate."""
    return participate_in_debate(
        db=db,
        debate_id=debate_id,
        user=current_user,
        content=body.content,
        message_type=body.message_type,
    )
