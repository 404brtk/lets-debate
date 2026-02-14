from typing import Annotated, Optional
from fastapi import Depends, Request
from sqlalchemy.orm import Session
import redis

from app.config import get_settings
from app.db.session import get_db

settings = get_settings()

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
