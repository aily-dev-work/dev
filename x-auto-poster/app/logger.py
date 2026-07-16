"""Logging setup with rotation; never log secrets."""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

_SECRET_PATTERNS = [
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]+"),
    re.compile(r"(?i)(access_token[\"']?\s*[:=]\s*[\"']?)[^\"'\s,}]+"),
    re.compile(r"(?i)(refresh_token[\"']?\s*[:=]\s*[\"']?)[^\"'\s,}]+"),
    re.compile(r"(?i)(client_secret[\"']?\s*[:=]\s*[\"']?)[^\"'\s,}]+"),
]


def mask_secret(value: str | None, visible: int = 4) -> str:
    """Mask a secret, keeping first/last visible chars."""
    if not value:
        return "(empty)"
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}...{value[-visible:]}"


def sanitize_text(text: str | None, max_len: int = 500) -> str:
    """Remove likely secrets and truncate."""
    if text is None:
        return ""
    cleaned = text
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub(r"\1***", cleaned)
    cleaned = cleaned.replace("\r", "\\r").replace("\n", "\\n")
    if len(cleaned) > max_len:
        return cleaned[:max_len] + "…"
    return cleaned


def preview_content(text: str, max_len: int = 80) -> str:
    """Safe preview of post body for logs."""
    return sanitize_text(text, max_len=max_len)


def setup_logger(log_path: Path, name: str = "x_poster") -> logging.Logger:
    """Configure rotating file + console logger."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(console)
    logger.propagate = False
    return logger
