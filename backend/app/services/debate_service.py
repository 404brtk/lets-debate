import json
import uuid

import redis
from fastapi import HTTPException, status
from pydantic import UUID4
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentConfig, Debate, Message, User
from app.schemas import DebateCreate


def get_user_debate_or_404(db: Session, debate_id: UUID4, user_id: uuid.UUID) -> Debate:
    stmt = select(Debate).where(Debate.id == debate_id, Debate.user_id == user_id)
    debate = db.scalar(stmt)
    if debate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debate not found",
        )
    return debate


def create_debate_with_agents(
    db: Session, debate_in: DebateCreate, user: User
) -> Debate:
    roles = [agent.role for agent in debate_in.agents]
    if len(set(roles)) != len(roles):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent roles must be unique",
        )

    normalized_names = [agent.name.strip().lower() for agent in debate_in.agents]
    if len(set(normalized_names)) != len(normalized_names):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent names must be unique",
        )

    debate_row = Debate(
        user_id=user.id,
        topic=debate_in.topic,
        description=debate_in.description,
        max_turns=debate_in.max_turns,
        status="pending",
        current_turn=0,
    )
    db.add(debate_row)
    db.flush()

    for index, agent in enumerate(debate_in.agents, start=1):
        db.add(
            AgentConfig(
                debate_id=debate_row.id,
                name=agent.name,
                role=agent.role,
                system_prompt=f"You are {agent.name}, acting as a {agent.role} in this debate.",
                model_provider=agent.model_provider,
                model_name=agent.model_name,
                temperature=agent.temperature,
                order_index=index,
                is_active=True,
            )
        )

    db.commit()
    db.refresh(debate_row)
    return debate_row


def list_user_debates(db: Session, user: User, skip: int, limit: int) -> list[Debate]:
    stmt = (
        select(Debate)
        .where(Debate.user_id == user.id)
        .order_by(Debate.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def set_debate_status(
    db: Session,
    debate_id: UUID4,
    user: User,
    from_status: str,
    to_status: str,
    invalid_transition_message: str,
) -> Debate:
    debate = get_user_debate_or_404(db, debate_id, user.id)
    if debate.status != from_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=invalid_transition_message,
        )

    debate.status = to_status
    db.commit()
    db.refresh(debate)
    return debate


def get_debate_messages(
    db: Session, debate_id: UUID4, user: User, skip: int, limit: int
) -> list[Message]:
    get_user_debate_or_404(db, debate_id, user.id)
    stmt = (
        select(Message)
        .where(Message.debate_id == debate_id)
        .order_by(Message.turn_number.asc(), Message.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def publish_debate_event(
    redis_client: redis.Redis,
    debate_id: UUID4,
    event_type: str,
    payload: dict[str, object],
) -> None:
    event = {"type": event_type, "debate_id": str(debate_id), **payload}
    redis_client.publish(f"debate:{debate_id}", json.dumps(event))


def start_debate_for_user(
    db: Session,
    redis_client: redis.Redis,
    debate_id: UUID4,
    user: User,
) -> dict[str, str]:
    set_debate_status(
        db=db,
        debate_id=debate_id,
        user=user,
        from_status="pending",
        to_status="active",
        invalid_transition_message="Debate can only be started from pending status",
    )
    publish_debate_event(
        redis_client=redis_client,
        debate_id=debate_id,
        event_type="debate_started",
        payload={},
    )
    return {"message": "Debate started", "debate_id": str(debate_id)}


def pause_debate_for_user(
    db: Session,
    redis_client: redis.Redis,
    debate_id: UUID4,
    user: User,
) -> dict[str, str]:
    set_debate_status(
        db=db,
        debate_id=debate_id,
        user=user,
        from_status="active",
        to_status="paused",
        invalid_transition_message="Debate can only be paused from active status",
    )
    publish_debate_event(
        redis_client=redis_client,
        debate_id=debate_id,
        event_type="debate_paused",
        payload={},
    )
    return {"message": "Debate paused", "debate_id": str(debate_id)}


def join_debate_for_user(
    db: Session,
    redis_client: redis.Redis,
    debate_id: UUID4,
    user: User,
) -> dict[str, str]:
    debate = get_user_debate_or_404(db=db, debate_id=debate_id, user_id=user.id)
    if debate.status not in {"active", "paused"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only join an active or paused debate",
        )

    publish_debate_event(
        redis_client=redis_client,
        debate_id=debate_id,
        event_type="human_joined",
        payload={"user_id": str(user.id)},
    )

    return {"message": "Joined debate", "debate_id": str(debate_id)}
