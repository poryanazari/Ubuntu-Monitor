from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

import os
import sys
from pathlib import Path


def _install_root() -> Path:
    if os.environ.get("UBUNTU_MONITOR_DATA_DIR"):
        return Path(os.environ["UBUNTU_MONITOR_DATA_DIR"])
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_INSTALL_ROOT = _install_root()
_ENV_FILE = _INSTALL_ROOT / ".env"


def _default_database_url() -> str:
    db_path = _INSTALL_ROOT / "monitor.db"
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


class Settings(BaseSettings):
    secret_key: str = "change-this-secret-key-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    database_url: str = _default_database_url()
    default_admin_username: str = "admin"
    default_admin_password: str = "admin123"

    bale_bot_token: str = ""
    bale_api_base: str = "https://tapi.bale.ai/bot"
    bale_default_chat_id: str = ""
    alert_check_interval_seconds: int = 60
    agent_offline_minutes: int = 5

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
