import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token as create_access_token_core
from app.core.security import (
    create_refresh_token,
    credentials_exception,
    decode_access_token_subject,
    decode_refresh_token_data,
    get_refresh_token_expiry,
    hash_password,
    verify_password,
)
from app.models import RefreshToken, User
from app.schemas import UserCreate


def create_access_token(user_id: str) -> str:
    return create_access_token_core(subject=user_id)


def create_token_pair(db: Session, user_id: str) -> tuple[str, str]:
    access_token = create_access_token_core(subject=user_id)
    refresh_token, refresh_jti = create_refresh_token(subject=user_id)

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError as exc:
        raise credentials_exception() from exc

    db.add(
        RefreshToken(
            user_id=user_uuid,
            token_jti=refresh_jti,
            expires_at=get_refresh_token_expiry(),
        )
    )
    db.commit()
    return access_token, refresh_token


def rotate_refresh_token(db: Session, refresh_token: str) -> tuple[str, str]:
    user_id, token_jti = decode_refresh_token_data(refresh_token)

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError as exc:
        raise credentials_exception() from exc

    stored_token = db.scalar(
        select(RefreshToken).where(RefreshToken.token_jti == token_jti)
    )
    if stored_token is None or stored_token.user_id != user_uuid:
        raise credentials_exception()

    now = datetime.now(timezone.utc)
    if stored_token.revoked_at is not None or stored_token.expires_at <= now:
        raise credentials_exception()

    user = db.get(User, user_uuid)
    if user is None or not user.is_active:
        raise credentials_exception()

    new_refresh_token, new_jti = create_refresh_token(subject=str(user.id))

    stored_token.revoked_at = now
    stored_token.replaced_by_jti = new_jti
    db.add(
        RefreshToken(
            user_id=user.id,
            token_jti=new_jti,
            expires_at=get_refresh_token_expiry(),
        )
    )
    db.commit()

    access_token = create_access_token_core(subject=str(user.id))
    return access_token, new_refresh_token


def cleanup_expired_refresh_tokens(db: Session) -> int:
    result = db.execute(
        delete(RefreshToken).where(RefreshToken.expires_at < datetime.now(timezone.utc))
    )
    db.commit()
    return int(result.rowcount or 0)


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
