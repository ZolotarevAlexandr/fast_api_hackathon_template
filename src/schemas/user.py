from pydantic import ConfigDict, EmailStr

from src.schemas.pydantic_base import BaseSchema


class UserCreate(BaseSchema):
    name: str
    username: str
    email: EmailStr
    password: str
    is_admin: bool = False


class UserResponse(BaseSchema):
    id: int
    name: str
    username: str
    email: EmailStr
    is_admin: bool

    model_config = ConfigDict(from_attributes=True)
