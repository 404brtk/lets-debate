from datetime import datetime
from typing import Optional
from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, UUID4


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

    id: UUID4 = Field(..., description="User UUID")
    created_at: datetime = Field(..., description="Account creation timestamp")
    has_openai_key: bool = Field(
        default=False, description="Whether user has an OpenAI API key"
    )
    has_google_key: bool = Field(
        default=False, description="Whether user has a Google API key"
    )

    model_config = ConfigDict(from_attributes=True)


class ApiKeysUpdate(BaseModel):
    """Update API keys request."""

    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    google_api_key: Optional[str] = Field(
        default=None, description="Google/Gemini API key"
    )

    model_config = ConfigDict(extra="forbid")


class ApiKeysResponse(BaseModel):
    """API key status response."""

    has_openai_key: bool = Field(..., description="Whether OpenAI key is set")
    has_google_key: bool = Field(..., description="Whether Google key is set")
    openai_key_masked: Optional[str] = Field(
        default=None, description="Masked OpenAI key"
    )
    google_key_masked: Optional[str] = Field(
        default=None, description="Masked Google key"
    )


class Token(BaseModel):
    """JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class TokenPair(Token):
    """Access and refresh token response."""

    refresh_token: str = Field(..., description="JWT refresh token")


class RefreshTokenRequest(BaseModel):
    """Refresh token exchange request."""

    refresh_token: str = Field(..., description="JWT refresh token")


class TokenData(BaseModel):
    """Token payload data."""

    user_id: UUID4 = Field(
        ...,
        validation_alias=AliasChoices("sub", "user_id"),
        description="User UUID from token subject claim",
    )

    model_config = ConfigDict(validate_by_alias=True, validate_by_name=True)
