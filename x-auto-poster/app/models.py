"""Domain models and helpers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class PostStatus(str, Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    PROCESSING = "PROCESSING"
    POSTED = "POSTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


def content_hash(content: str) -> str:
    """SHA-256 of normalized content for duplicate detection."""
    normalized = content.strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass
class Post:
    id: int | None
    content: str
    scheduled_at: str
    status: str
    content_hash: str
    x_post_id: str | None = None
    attempt_count: int = 0
    last_attempt_at: str | None = None
    posted_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: Any) -> "Post":
        return cls(
            id=row["id"],
            content=row["content"],
            scheduled_at=row["scheduled_at"],
            status=row["status"],
            content_hash=row["content_hash"],
            x_post_id=row["x_post_id"],
            attempt_count=row["attempt_count"],
            last_attempt_at=row["last_attempt_at"],
            posted_at=row["posted_at"],
            error_code=row["error_code"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def parse_tokyo_datetime(value: str, timezone_name: str = "Asia/Tokyo") -> datetime:
    """Parse 'YYYY-MM-DD HH:MM' or ISO string into timezone-aware datetime."""
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(timezone_name)
    raw = value.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            naive = datetime.strptime(raw, fmt)
            return naive.replace(tzinfo=tz)
        except ValueError:
            continue
    # ISO with offset
    dt = datetime.fromisoformat(value.strip())
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def to_iso(dt: datetime) -> str:
    """Serialize datetime to ISO 8601."""
    return dt.isoformat()


def now_tokyo(timezone_name: str = "Asia/Tokyo") -> datetime:
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo(timezone_name))
