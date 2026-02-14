from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.dependencies import SessionDep
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    register_user,
)
from app.schemas import UserCreate, UserResponse, Token

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: SessionDep):
    """Register a new user account."""
    return register_user(db=db, user_in=user)


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: SessionDep
):
    """Login with username/email and password."""
    user = authenticate_user(
        db=db,
        username_or_email=form_data.username,
        password=form_data.password,
    )

    access_token = create_access_token(user_id=str(user.id))
    return Token(access_token=access_token)
