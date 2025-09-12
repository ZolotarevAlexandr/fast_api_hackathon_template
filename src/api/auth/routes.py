from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_derive_responses import AutoDeriveResponsesAPIRoute
from passlib.context import CryptContext

from src.api.auth.dependencies import get_current_user
from src.api.auth.util import ACCESS_TTL, REFRESH_TTL, create_access_token, create_refresh_token, decode_token
from src.api.repositories.dependencies import get_user_repository
from src.db.models import User
from src.db.repositories import UserRepository
from src.schemas import LoginRequest, RefreshTokenRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"], route_class=AutoDeriveResponsesAPIRoute)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    user_repository: UserRepository = Depends(get_user_repository),
) -> TokenResponse:
    existing_email = await user_repository.get_user_by_email(str(payload.email))
    if existing_email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")

    existing_username = await user_repository.get_user_by_username(str(payload.username))
    if existing_username:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already in use")

    hashed = pwd_context.hash(payload.password)
    user = await user_repository.create_user(
        name=payload.name,
        username=payload.username,
        email=str(payload.email),
        hashed_password=hashed,
    )

    scope = "admin" if user.is_admin else None
    access_token = create_access_token(subject=str(user.id), scope=scope)
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(ACCESS_TTL.total_seconds()),
        refresh_expires_in=int(REFRESH_TTL.total_seconds()),
    )


@router.post("/token")
async def login(
    credentials: LoginRequest,
    user_repository: UserRepository = Depends(get_user_repository),
) -> TokenResponse:
    user = await user_repository.get_user_by_username(credentials.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})

    verified, new_hash = pwd_context.verify_and_update(credentials.password, user.hashed_password)
    if not verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    if new_hash:
        await user_repository.edit_user(user.id, hashed_password=new_hash)

    scope = "admin" if user.is_admin else None
    access_token = create_access_token(subject=str(user.id), scope=scope)
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(ACCESS_TTL.total_seconds()),
        refresh_expires_in=int(REFRESH_TTL.total_seconds()),
    )


@router.post("/refresh")
async def refresh_token(
    request: RefreshTokenRequest,
    user_repository: UserRepository = Depends(get_user_repository),
) -> TokenResponse:
    payload = decode_token(request.refresh_token, expected_type="refresh")
    user = await user_repository.get_user(int(payload.sub))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})

    scope = "admin" if user.is_admin else None
    new_access = create_access_token(subject=str(user.id), scope=scope)
    new_refresh = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=int(ACCESS_TTL.total_seconds()),
        refresh_expires_in=int(REFRESH_TTL.total_seconds()),
    )


@router.get("/me")
async def read_me(current_user: Annotated[User, Depends(get_current_user)]) -> "UserResponse":
    return UserResponse.model_validate(current_user)
