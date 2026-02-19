from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestFormStrict
from app.dependencies import SessionDep
from app.services.auth_service import (
    authenticate_user,
    create_token_pair,
    register_user,
    rotate_refresh_token,
)
from app.schemas import RefreshTokenRequest, TokenPair, UserCreate, UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: SessionDep):
    """Register a new user account."""
    return register_user(db=db, user_in=user)


@router.post("/login", response_model=TokenPair)
def login(
    form_data: Annotated[OAuth2PasswordRequestFormStrict, Depends()], db: SessionDep
):
    """Login with username/email and password."""
    user = authenticate_user(
        db=db,
        username_or_email=form_data.username,
        password=form_data.password,
    )

    access_token, refresh_token = create_token_pair(db=db, user_id=str(user.id))
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
def refresh_tokens(payload: RefreshTokenRequest, db: SessionDep):
    """Rotate refresh token and issue new access token pair."""
    access_token, refresh_token = rotate_refresh_token(
        db=db,
        refresh_token=payload.refresh_token,
    )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)
