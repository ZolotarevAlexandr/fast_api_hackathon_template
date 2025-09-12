from typing import Self

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import AbstractSQLAlchemyStorage
from src.db.models import User


class UserRepository:
    storage: AbstractSQLAlchemyStorage

    def __init__(self, storage: AbstractSQLAlchemyStorage) -> None:
        self.storage = storage

    def update_storage(self, storage: AbstractSQLAlchemyStorage) -> Self:
        self.storage = storage
        return self

    def _create_session(self) -> AsyncSession:
        return self.storage.create_session()

    async def create_user(self, name: str, username: str, email: str, hashed_password: str, is_admin: bool = False) -> User:
        async with self._create_session() as session:
            user = User(
                name=name,
                username=username,
                email=email,
                hashed_password=hashed_password,
                is_admin=is_admin,
            )
            session.add(user)
            await session.commit()
            return user

    async def get_user(self, user_id: int) -> User | None:
        async with self._create_session() as session:
            user = await session.get(User, user_id)
            return user

    async def get_user_by_email(self, email: str) -> User | None:
        async with self._create_session() as session:
            result = await session.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> User | None:
        async with self._create_session() as session:
            result = await session.execute(select(User).where(User.username == username))
            return result.scalar_one_or_none()

    async def edit_user(
        self,
        user_id: int,
        *,
        name: str | None = None,
        username: str | None = None,
        email: str | None = None,
        hashed_password: str | None = None,
        is_admin: bool | None = None,
    ) -> User | None:
        async with self._create_session() as session:
            user = await session.get(User, user_id)
            if user is None:
                return None

            if name is not None:
                user.name = name
            if username is not None:
                user.username = username
            if email is not None:
                user.email = email
            if hashed_password is not None:
                user.hashed_password = hashed_password
            if is_admin is not None:
                user.is_admin = is_admin

            await session.commit()
            return user

    async def delete_user(self, user_id: int) -> User | None:
        async with self._create_session() as session:
            user = await session.get(User, user_id)
            if user is None:
                return None
            await session.delete(user)
            await session.commit()
            return user

    async def list_users(self) -> list[User]:
        async with self._create_session() as session:
            result = await session.execute(select(User))
            return list(result.scalars().all())
