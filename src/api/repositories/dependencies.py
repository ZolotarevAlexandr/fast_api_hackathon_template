from fastapi import Depends, Request

from src.db.repositories import (
    UserRepository,
)
from src.db.storage import AbstractSQLAlchemyStorage


def get_storage(request: Request) -> AbstractSQLAlchemyStorage:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        raise RuntimeError("Storage is not initialized. Check lifespan setup.")
    return storage


def get_user_repository(
    storage: AbstractSQLAlchemyStorage = Depends(get_storage),
) -> UserRepository:
    return UserRepository(storage)
