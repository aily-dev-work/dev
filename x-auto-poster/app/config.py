"""Application configuration loaded from .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Project root: D:\dev\x-auto-poster (parent of app/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings."""

    client_id: str
    client_secret: str
    api_base_url: str
    timezone: str
    dry_run: bool
    project_root: Path
    data_dir: Path
    logs_dir: Path
    db_path: Path
    token_path: Path
    log_path: Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings(env_file: Path | None = None) -> Settings:
    """Load settings from .env under the project root."""
    root = PROJECT_ROOT
    dotenv_path = env_file or (root / ".env")
    if dotenv_path.exists():
        load_dotenv(dotenv_path, override=False)

    data_dir = root / "data"
    logs_dir = root / "logs"

    return Settings(
        client_id=os.getenv("X_CLIENT_ID", "").strip(),
        client_secret=os.getenv("X_CLIENT_SECRET", "").strip(),
        api_base_url=os.getenv("X_API_BASE_URL", "https://api.x.com").rstrip("/"),
        timezone=os.getenv("APP_TIMEZONE", "Asia/Tokyo").strip() or "Asia/Tokyo",
        dry_run=_as_bool(os.getenv("DRY_RUN"), default=True),
        project_root=root,
        data_dir=data_dir,
        logs_dir=logs_dir,
        db_path=data_dir / "x_poster.db",
        token_path=data_dir / "oauth_tokens.json",
        log_path=logs_dir / "x_poster.log",
    )


def require_oauth_env(settings: Settings) -> None:
    """Raise if Client ID / Secret are missing."""
    missing: list[str] = []
    if not settings.client_id:
        missing.append("X_CLIENT_ID")
    if not settings.client_secret:
        missing.append("X_CLIENT_SECRET")
    if missing:
        raise ValueError(
            "必須の環境変数が未設定です: "
            + ", ".join(missing)
            + "。.env を確認してください。"
        )
