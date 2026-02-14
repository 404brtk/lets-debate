from typing import Annotated
from fastapi import APIRouter, Query
from pydantic import UUID4

from app.dependencies import CurrentUser, RedisDep, SessionDep
from app.services.debate_service import (
    create_debate_with_agents,
    get_debate_messages,
    get_user_debate_or_404,
    join_debate_for_user,
    list_user_debates,
    pause_debate_for_user,
    start_debate_for_user,
)
from app.schemas import DebateCreate, DebateResponse, MessageResponse

router = APIRouter()


@router.post("", response_model=DebateResponse)
async def create_debate(
    debate: DebateCreate,
    current_user: CurrentUser,
    db: SessionDep,
):
    """
    Create a new debate with configured agents.

    - **topic**: The question or topic to debate
    - **description**: Optional context or background
    - **max_turns**: Maximum number of turns (5-50)
    - **agents**: 3-5 agents with different roles
    """
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


@router.post("/{debate_id}/start")
async def start_debate(
    debate_id: UUID4,
    current_user: CurrentUser,
    db: SessionDep,
    redis: RedisDep,
):
    """Start the debate."""
    return start_debate_for_user(
        db=db,
        redis_client=redis,
        debate_id=debate_id,
        user=current_user,
    )


@router.post("/{debate_id}/pause")
async def pause_debate(
    debate_id: UUID4,
    current_user: CurrentUser,
    db: SessionDep,
    redis: RedisDep,
):
    """Pause the debate."""
    return pause_debate_for_user(
        db=db,
        redis_client=redis,
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


@router.post("/{debate_id}/participate")
async def human_participate(
    debate_id: UUID4,
    current_user: CurrentUser,
    db: SessionDep,
    redis: RedisDep,
):
    """Join the debate as a human participant."""
    return join_debate_for_user(
        db=db,
        redis_client=redis,
        debate_id=debate_id,
        user=current_user,
    )
