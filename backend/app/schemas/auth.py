from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(
        ..., min_length=3, max_length=50, description="Unique username"
    )


class UserCreate(UserBase):
    """User registration request."""

    password: str = Field(..., min_length=8, description="User password")


class UserResponse(UserBase):
    """User response model."""

    id: str = Field(..., description="User UUID")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class TokenData(BaseModel):
    """Token payload data."""

    user_id: Optional[str] = Field(default=None, description="User ID from token")
