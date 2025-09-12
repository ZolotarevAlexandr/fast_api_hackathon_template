from typing import Literal

from pydantic import ConfigDict, EmailStr, Field

from src.schemas.pydantic_base import BaseSchema

TokenType = Literal["access", "refresh"]


class TokenPayload(BaseSchema):
    sub: str
    exp: int  # NumericDate
    iat: int  # NumericDate
    nbf: int | None = None  # NumericDate
    type: TokenType


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    auth_scheme: str = "bearer"

    expires_in: int = Field(..., description="Access token TTL in seconds")
    refresh_expires_in: int = Field(..., description="Refresh token TTL in seconds")

    model_config = ConfigDict(from_attributes=True)


class RefreshTokenRequest(BaseSchema):
    refresh_token: str


class RegisterRequest(BaseSchema):
    name: str
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseSchema):
    username: str
    password: str
