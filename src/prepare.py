import asyncio
import secrets
import shutil
import subprocess
from pathlib import Path

import yaml
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

BASE_DIR = Path(__file__).resolve().parents[1]
SETTINGS_TEMPLATE = BASE_DIR / "settings.example.yaml"
SETTINGS_FILE = BASE_DIR / "settings.yaml"
PRE_COMMIT_CONFIG = BASE_DIR / ".pre-commit-config.yaml"
DEFAULT_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"


def get_settings():
    """
    Load and return the settings from `settings.yaml` if it exists.
    """
    if not SETTINGS_FILE.exists():
        raise RuntimeError("❌ No `settings.yaml` found.")

    try:
        with open(SETTINGS_FILE) as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        raise RuntimeError("❌ No `settings.yaml` found.") from e


def ensure_settings_file():
    """
    Ensure `settings.yaml` exists. If not, copy `settings.yaml.example`.
    """
    if not SETTINGS_TEMPLATE.exists():
        print("❌ No `settings.yaml.example` found. Skipping copying.")
        return

    if SETTINGS_FILE.exists():
        print("✅ `settings.yaml` exists.")
        return

    shutil.copy(SETTINGS_TEMPLATE, SETTINGS_FILE)
    print(f"✅ Copied `{SETTINGS_TEMPLATE}` to `{SETTINGS_FILE}`")


def check_and_generate_secret_key():
    """
    Ensure the secret_key is set in `settings.yaml`. If missing, generate random one
    """
    settings = get_settings()
    secret_key = settings.get("api_settings", {}).get("secret_key")

    if not secret_key or secret_key == "...":
        print("⚠️ `secret_key` is missing in `settings.yaml`.")
        print("  ➡️ Generate a random one")
        secret = secrets.token_hex(32)
        try:
            with open(SETTINGS_FILE) as f:
                as_text = f.read()
            as_text = as_text.replace("secret_key: null", f'secret_key: "{secret}"')
            as_text = as_text.replace("secret_key: ...", f'secret_key: "{secret}"')
            with open(SETTINGS_FILE, "w") as f:
                f.write(as_text)
            print("  ✅ `secret_key` has been updated in `settings.yaml`.")
        except Exception as e:
            print(f"  ❌ Error updating `settings.yaml`: {e}")

    else:
        print("✅ `secret_key` is specified.")


def check_database_access():
    """
    Ensure the database is accessible using `db_url` from `settings.yaml`. If missing, set a default value.
    """
    settings = get_settings()
    db_url = settings.get("api_settings", {}).get("db_url")

    if not db_url or db_url == "...":
        print("⚠️ `db_url` is missing in `settings.yaml`. Setting default one.")

        try:
            with open(SETTINGS_FILE) as f:
                as_text = f.read()
            as_text = as_text.replace("db_url: null", f"db_url: {DEFAULT_DB_URL}")
            as_text = as_text.replace("db_url: ...", f"db_url: {DEFAULT_DB_URL}")
            with open(SETTINGS_FILE, "w") as f:
                f.write(as_text)
            print("  ✅ `db_url` has been updated in `settings.yaml`.")
            db_url = DEFAULT_DB_URL
        except Exception as e:
            print(f"  ❌ Error updating `settings.yaml`: {e}")
            return

    def run_alembic_upgrade():
        """
        Run `alembic upgrade head` to apply migrations.
        """
        try:
            print("⚙️ Running Alembic migrations...")
            subprocess.run(["alembic", "upgrade", "head"], check=True, text=True, capture_output=True)
            print("  ✅ Alembic migrations applied successfully.")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Error running Alembic migrations:\n  {e.stderr}")
        except Exception as e:
            print(f"  ❌ Unexpected error running Alembic migrations: {e}")

    async def test_connection():
        try:
            engine = create_async_engine(db_url)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                print("✅ Successfully connected to the database.")
            run_alembic_upgrade()
        except Exception:
            print(f"❌ Failed to connect to the database at `{db_url}`")

    asyncio.run(test_connection())


def prepare():
    """
    Prepare the project for the run.
    """
    print("⚙️ Running prepare script...")
    ensure_settings_file()
    check_and_generate_secret_key()
    check_database_access()
    print("✅ All setup steps completed.")
