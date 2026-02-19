from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestFormStrict
from app.dependencies import CurrentUser, SessionDep
from app.services.auth_service import (
    authenticate_user,
    create_token_pair,
    get_user_api_keys_status,
    register_user,
    rotate_refresh_token,
    update_user_api_keys,
)
from app.schemas import (
    ApiKeysResponse,
    ApiKeysUpdate,
    RefreshTokenRequest,
    TokenPair,
    UserCreate,
    UserResponse,
)

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


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: CurrentUser):
    """Get profile of currently authenticated user."""
    return current_user


@router.get("/me/api-keys", response_model=ApiKeysResponse)
def get_api_keys(current_user: CurrentUser):
    """Get API key status (masked, not plaintext)."""
    return get_user_api_keys_status(current_user)


@router.put("/me/api-keys", response_model=ApiKeysResponse)
def set_api_keys(
    payload: ApiKeysUpdate,
    current_user: CurrentUser,
    db: SessionDep,
):
    """Save or update user API keys (encrypted at rest)."""
    user = update_user_api_keys(
        db=db,
        user=current_user,
        openai_api_key=payload.openai_api_key,
        google_api_key=payload.google_api_key,
    )
    return get_user_api_keys_status(user)
