from datetime import datetime, timedelta, timezone
import secrets
from typing import Optional

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from pwdlib import PasswordHash

from app.config import get_settings
from app.schemas.auth import TokenData

settings = get_settings()
REFRESH_TOKEN_JTI_BYTES = 32
REFRESH_TOKEN_JTI_LENGTH = REFRESH_TOKEN_JTI_BYTES * 2
JWT_DECODE_OPTIONS = {
    "verify_signature": True,
    "verify_exp": True,
    "verify_iat": True,
    "require_exp": True,
    "require_iat": True,
}

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    refreshUrl="/api/v1/auth/refresh",
)


def credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_refresh_token_expiry(expires_delta: Optional[timedelta] = None) -> datetime:
    expire_delta = expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return datetime.now(timezone.utc) + expire_delta


def generate_refresh_token_jti() -> str:
    jti = secrets.token_hex(REFRESH_TOKEN_JTI_BYTES)
    if len(jti) != REFRESH_TOKEN_JTI_LENGTH:
        raise RuntimeError("Invalid refresh token JTI length")
    return jti


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire_delta = expires_delta or timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    expire = datetime.now(timezone.utc) + expire_delta
    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, str]:
    jti = generate_refresh_token_jti()
    expire = get_refresh_token_expiry(expires_delta=expires_delta)
    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": jti,
        "type": "refresh",
    }
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti


def decode_access_token_subject(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options=JWT_DECODE_OPTIONS,
        )
        token_data = TokenData.model_validate(payload)
    except (JWTError, ValidationError) as exc:
        raise credentials_exception() from exc

    token_type = payload.get("type")
    if token_type is not None and token_type != "access":
        raise credentials_exception()

    return str(token_data.user_id)


def decode_refresh_token_data(token: str) -> tuple[str, str]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options=JWT_DECODE_OPTIONS,
        )
        token_data = TokenData.model_validate(payload)
    except (JWTError, ValidationError) as exc:
        raise credentials_exception() from exc

    token_jti = payload.get("jti")
    token_type = payload.get("type")

    if not isinstance(token_jti, str) or not token_jti:
        raise credentials_exception()
    if token_type != "refresh":
        raise credentials_exception()
    if len(token_jti) != REFRESH_TOKEN_JTI_LENGTH:
        raise credentials_exception()
    try:
        int(token_jti, 16)
    except ValueError as exc:
        raise credentials_exception() from exc

    return str(token_data.user_id), token_jti
