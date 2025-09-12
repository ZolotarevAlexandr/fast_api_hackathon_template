from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi_derive_responses import AutoDeriveResponsesAPIRoute
from passlib.context import CryptContext
from starlette import status

from src.api.auth.dependencies import get_current_user, require_admin
from src.api.repositories.dependencies import get_user_repository
from src.db.models import User
from src.db.repositories import UserRepository
from src.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"], route_class=AutoDeriveResponsesAPIRoute)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    _: User = Depends(require_admin),
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserResponse:
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
        is_admin=payload.is_admin,
    )
    return UserResponse.model_validate(user)


@router.get("")
async def list_users(
    _: User = Depends(require_admin),
    user_repository: UserRepository = Depends(get_user_repository),
) -> list[UserResponse]:
    users = await user_repository.list_users()
    return [UserResponse.model_validate(user) for user in users]


@router.get("/{user_id}")
async def get_user_endpoint(
    user_id: int,
    current_user: User = Depends(get_current_user),
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserResponse:
    user = await user_repository.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return UserResponse.model_validate(user)


@router.patch("/{user_id}")
async def edit_user_endpoint(
    user_id: int,
    name: str | None = None,
    username: str | None = None,
    email: str | None = None,
    password: str | None = None,
    is_admin: bool | None = None,
    current_user: User = Depends(get_current_user),
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserResponse:
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    existing_email = await user_repository.get_user_by_email(str(email))
    if existing_email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")

    existing_username = await user_repository.get_user_by_username(str(username))
    if existing_username:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already in use")

    update_kwargs: dict = {}
    if name is not None:
        update_kwargs["name"] = name
    if username is not None:
        update_kwargs["username"] = username
    if email is not None:
        update_kwargs["email"] = email
    if password is not None:
        update_kwargs["hashed_password"] = pwd_context.hash(password)
    if is_admin is not None:
        if not current_user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can change admin flag")
        update_kwargs["is_admin"] = is_admin

    if not update_kwargs:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No changes provided")

    edited = await user_repository.edit_user(user_id, **update_kwargs)
    if edited is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")
    return UserResponse.model_validate(edited)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    user_id: int,
    user: User = Depends(require_admin),
    user_repository: UserRepository = Depends(get_user_repository),
):
    if user.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
    deleted = await user_repository.delete_user(user_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
