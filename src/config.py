import os
from pathlib import Path

from src.config_schema import ApiSettings, AuthSettings, Settings

settings_path = os.getenv("SETTINGS_PATH", "settings.yaml")
settings: Settings = Settings.from_yaml(Path(settings_path))
api_settings: ApiSettings = settings.api_settings
auth_settings: AuthSettings = settings.auth_settings
