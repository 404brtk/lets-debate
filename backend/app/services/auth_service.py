import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token as create_access_token_core
from app.core.security import (
    credentials_exception,
    decode_access_token_subject,
    hash_password,
    verify_password,
)
from app.models import User
from app.schemas import UserCreate


def create_access_token(user_id: str) -> str:
    return create_access_token_core(subject=user_id)


def get_current_user_by_token(token: str, db: Session) -> User:
    user_id = decode_access_token_subject(token)
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError as exc:
        raise credentials_exception() from exc

    user = db.get(User, user_uuid)
    if user is None or not user.is_active:
        raise credentials_exception()

    return user


def register_user(db: Session, user_in: UserCreate) -> User:
    existing_user = db.scalar(
        select(User).where(
            or_(User.email == user_in.email, User.username == user_in.username)
        )
    )
    if existing_user is not None:
        if existing_user.email == user_in.email:
            detail = "Email already registered"
        else:
            detail = "Username already taken"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    db_user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=hash_password(user_in.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, username_or_email: str, password: str) -> User:
    user = db.scalar(
        select(User).where(
            or_(User.username == username_or_email, User.email == username_or_email)
        )
    )

    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user
