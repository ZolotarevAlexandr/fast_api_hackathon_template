from contextlib import asynccontextmanager

from fastapi import FastAPI

import src.api.logging_  # noqa: F401
from src.config import api_settings
from src.db import SQLAlchemyStorage


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Application startup
    storage = SQLAlchemyStorage.from_url(api_settings.db_url.get_secret_value())
    app.state.storage = storage

    try:
        yield
    finally:
        # Application shutdown
        await storage.close_connection()
