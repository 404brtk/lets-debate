import uuid
from typing import Annotated, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import redis

from app.config import get_settings
from app.db.session import get_db
from app.models import User

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# db session dependency
SessionDep = Annotated[Session, Depends(get_db)]


def create_redis_client() -> redis.Redis:
    """Create application-scoped Redis client."""
    return redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
    )


def close_redis_client(client: redis.Redis) -> None:
    """Close Redis client and its pool connections."""
    try:
        client.close()
    except AttributeError:
        client.connection_pool.disconnect()


def get_redis(request: Request) -> redis.Redis:
    """Dependency to get Redis client from app state."""
    client: Optional[redis.Redis] = getattr(request.app.state, "redis", None)
    if client is None:
        raise RuntimeError("Redis client not initialized")
    return client


# redis dependency
RedisDep = Annotated[redis.Redis, Depends(get_redis)]


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_access_token(token: str) -> str:
    """Decode JWT token and return user id (subject)."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError as exc:
        raise _credentials_exception() from exc

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise _credentials_exception()

    return user_id


def get_current_user_by_token(token: str, db: SessionDep) -> User:
    """Resolve and validate current user from JWT token."""
    user_id = decode_access_token(token)
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError as exc:
        raise _credentials_exception() from exc

    user = db.get(User, user_uuid)
    if user is None or not user.is_active:
        raise _credentials_exception()

    return user


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: SessionDep
) -> User:
    """Get current authenticated active user from bearer token."""
    return get_current_user_by_token(token, db)


CurrentUser = Annotated[User, Depends(get_current_user)]
