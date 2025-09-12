from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, SecretStr


class ApiSettings(BaseModel):
    app_root_path: str = Field("/api")
    'Prefix for the API path (e.g. "/api/v0")'
    cors_allow_origin_regex: str = ".*"
    "Allowed origins for CORS: from which domains requests to the API are allowed."
    db_url: SecretStr = Field(
        ...,
        examples=[
            "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
            "postgresql+asyncpg://postgres:postgres@db:5432/postgres",
        ],
    )
    "PostgreSQL database connection URL"
    secret_key: SecretStr = Field(...)


class AuthSettings(BaseModel):
    encryption_algorithm: str = "HS256"
    "The encryption algorithm for encryption/decryption in auth"
    access_token_ttl_minutes: int = 60
    "Access token expiration time in minutes"
    refresh_token_ttl_days: int = 7
    "Refresh token expiration time in days"
    leeway: int = 60
    "Leeway in seconds for clock skew"


class Settings(BaseModel):
    model_config = ConfigDict(json_schema_extra={"title": "Settings"}, extra="ignore")
    api_settings: ApiSettings
    auth_settings: AuthSettings

    @classmethod
    def from_yaml(cls, path: Path) -> "Settings":
        with open(path, encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)

        return cls.model_validate(yaml_config)

    @classmethod
    def save_schema(cls, path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            schema = {"$schema": "https://json-schema.org/draft-07/schema", **cls.model_json_schema()}
            yaml.dump(schema, f, sort_keys=False)
