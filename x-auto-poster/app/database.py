"""SQLite access layer."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Iterable

from app.logger import sanitize_text
from app.models import Post, PostStatus, content_hash, now_tokyo, to_iso


class DuplicateContentError(Exception):
    """Raised when the same content_hash already exists as POSTED/READY/PROCESSING."""


class Database:
    def __init__(self, db_path: Path, timezone: str = "Asia/Tokyo") -> None:
        self.db_path = db_path
        self.timezone = timezone

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    scheduled_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    x_post_id TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    last_attempt_at TEXT,
                    posted_at TEXT,
                    error_code TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_posts_status_scheduled
                    ON posts(status, scheduled_at);
                CREATE INDEX IF NOT EXISTS idx_posts_content_hash
                    ON posts(content_hash);

                CREATE TABLE IF NOT EXISTS execution_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER,
                    level TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    http_status INTEGER,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(post_id) REFERENCES posts(id)
                );
                """
            )

    def add_post(self, content: str, scheduled_at_iso: str, status: str = PostStatus.READY.value) -> int:
        digest = content_hash(content)
        now = to_iso(now_tokyo(self.timezone))
        with self.connect() as conn:
            blocking = conn.execute(
                """
                SELECT id, status FROM posts
                WHERE content_hash = ?
                  AND status IN ('READY', 'PROCESSING', 'POSTED')
                LIMIT 1
                """,
                (digest,),
            ).fetchone()
            if blocking:
                raise DuplicateContentError(
                    f"同一本文の投稿が既に存在します (id={blocking['id']}, status={blocking['status']})"
                )
            cur = conn.execute(
                """
                INSERT INTO posts (
                    content, scheduled_at, status, content_hash,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (content, scheduled_at_iso, status, digest, now, now),
            )
            return int(cur.lastrowid)

    def list_posts(self, include_posted: bool = False) -> list[Post]:
        with self.connect() as conn:
            if include_posted:
                rows = conn.execute(
                    "SELECT * FROM posts ORDER BY scheduled_at ASC, id ASC"
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM posts
                    WHERE status IN ('DRAFT', 'READY', 'PROCESSING', 'FAILED')
                    ORDER BY scheduled_at ASC, id ASC
                    """
                ).fetchall()
            return [Post.from_row(r) for r in rows]

    def get_post(self, post_id: int) -> Post | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
            return Post.from_row(row) if row else None

    def claim_due_posts(self, now_iso: str, limit: int = 10) -> list[Post]:
        """Atomically move READY due posts to PROCESSING and return them."""
        claimed: list[Post] = []
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM posts
                WHERE status = 'READY'
                  AND scheduled_at <= ?
                ORDER BY scheduled_at ASC, id ASC
                LIMIT ?
                """,
                (now_iso, limit),
            ).fetchall()
            for row in rows:
                updated = conn.execute(
                    """
                    UPDATE posts
                    SET status = 'PROCESSING',
                        attempt_count = attempt_count + 1,
                        last_attempt_at = ?,
                        updated_at = ?
                    WHERE id = ? AND status = 'READY'
                    """,
                    (now_iso, now_iso, row["id"]),
                )
                if updated.rowcount == 1:
                    fresh = conn.execute(
                        "SELECT * FROM posts WHERE id = ?", (row["id"],)
                    ).fetchone()
                    claimed.append(Post.from_row(fresh))
        return claimed

    def mark_posted(
        self,
        post_id: int,
        x_post_id: str,
        posted_at_iso: str,
    ) -> None:
        now = to_iso(now_tokyo(self.timezone))
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE posts
                SET status = 'POSTED',
                    x_post_id = ?,
                    posted_at = ?,
                    error_code = NULL,
                    error_message = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (x_post_id, posted_at_iso, now, post_id),
            )

    def mark_failed(
        self,
        post_id: int,
        error_code: str | None,
        error_message: str | None,
    ) -> None:
        now = to_iso(now_tokyo(self.timezone))
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE posts
                SET status = 'FAILED',
                    error_code = ?,
                    error_message = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    error_code,
                    sanitize_text(error_message, max_len=800) if error_message else None,
                    now,
                    post_id,
                ),
            )

    def revert_processing_to_ready(self, post_id: int) -> None:
        """Used when dry-run skips actual post."""
        now = to_iso(now_tokyo(self.timezone))
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE posts
                SET status = 'READY',
                    attempt_count = CASE WHEN attempt_count > 0 THEN attempt_count - 1 ELSE 0 END,
                    updated_at = ?
                WHERE id = ? AND status = 'PROCESSING'
                """,
                (now, post_id),
            )

    def cancel_post(self, post_id: int) -> bool:
        now = to_iso(now_tokyo(self.timezone))
        with self.connect() as conn:
            cur = conn.execute(
                """
                UPDATE posts
                SET status = 'CANCELLED', updated_at = ?
                WHERE id = ? AND status IN ('DRAFT', 'READY', 'FAILED')
                """,
                (now, post_id),
            )
            return cur.rowcount == 1

    def retry_post(self, post_id: int) -> bool:
        now = to_iso(now_tokyo(self.timezone))
        with self.connect() as conn:
            cur = conn.execute(
                """
                UPDATE posts
                SET status = 'READY',
                    error_code = NULL,
                    error_message = NULL,
                    updated_at = ?
                WHERE id = ? AND status = 'FAILED'
                """,
                (now, post_id),
            )
            return cur.rowcount == 1

    def add_execution_log(
        self,
        post_id: int | None,
        level: str,
        event_type: str,
        message: str,
        http_status: int | None = None,
    ) -> None:
        now = to_iso(now_tokyo(self.timezone))
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO execution_logs (
                    post_id, level, event_type, http_status, message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    post_id,
                    level,
                    event_type,
                    http_status,
                    sanitize_text(message, max_len=1000),
                    now,
                ),
            )

    def has_posted_hash(self, digest: str) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM posts WHERE content_hash = ? AND status = 'POSTED' LIMIT 1",
                (digest,),
            ).fetchone()
            return row is not None
