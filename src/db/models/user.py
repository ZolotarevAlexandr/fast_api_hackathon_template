from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column

from src.db.models import Base


class User(Base):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str]
    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]

    is_admin: Mapped[bool]
