__all__ = ["SQLAlchemyStorage", "AbstractSQLAlchemyStorage"]

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


class AbstractSQLAlchemyStorage(ABC):
    @abstractmethod
    def create_session(self) -> AsyncSession: ...

    @abstractmethod
    async def create_all(self) -> None: ...

    @abstractmethod
    async def close_connection(self): ...


class SQLAlchemyStorage(AbstractSQLAlchemyStorage):
    engine: AsyncEngine
    sessionmaker: async_sessionmaker

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine
        self.sessionmaker = async_sessionmaker(expire_on_commit=False, bind=self.engine)

    @classmethod
    def from_url(cls, url: str) -> "SQLAlchemyStorage":
        from sqlalchemy.ext.asyncio import create_async_engine  # noqa: PLC0415

        engine = create_async_engine(url)
        return cls(engine)

    def create_session(self) -> AsyncSession:
        return self.sessionmaker()

    async def create_all(self) -> None:
        from src.db.models import Base  # noqa: PLC0415

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_all(self) -> None:
        from src.db.models import Base  # noqa: PLC0415

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def close_connection(self):
        await self.engine.dispose()
