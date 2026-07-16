"""Due-post runner with retries and dry-run support."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from app.database import Database
from app.logger import preview_content
from app.models import to_iso
from app.x_client import XApiError, XClient


class Scheduler:
    def __init__(
        self,
        db: Database,
        client: XClient,
        timezone: str,
        logger: logging.Logger,
        dry_run: bool = True,
        max_attempts: int = 3,
    ) -> None:
        self.db = db
        self.client = client
        self.timezone = timezone
        self.logger = logger
        self.dry_run = dry_run
        self.max_attempts = max_attempts

    def run_once(self, limit: int = 10) -> int:
        """Process due READY posts. Returns number of successes."""
        now = datetime.now(ZoneInfo(self.timezone))
        now_iso = to_iso(now)
        posts = self.db.claim_due_posts(now_iso, limit=limit)
        if not posts:
            self.logger.info("event=run_once no due posts")
            return 0

        success = 0
        for post in posts:
            assert post.id is not None
            self.logger.info(
                "event=process post_id=%s preview=%s dry_run=%s",
                post.id,
                preview_content(post.content),
                self.dry_run,
            )
            self.db.add_execution_log(
                post.id,
                "INFO",
                "process_start",
                f"処理開始 dry_run={self.dry_run}",
            )

            if self.db.has_posted_hash(post.content_hash):
                self.db.mark_failed(
                    post.id,
                    "duplicate_posted",
                    "同一本文が既にPOSTEDのため再投稿しません",
                )
                self.db.add_execution_log(
                    post.id, "WARNING", "duplicate_block", "POSTED重複を検出"
                )
                continue

            if self.dry_run:
                self.logger.info(
                    "event=dry_run post_id=%s skip_api endpoint=POST /2/tweets",
                    post.id,
                )
                self.db.add_execution_log(
                    post.id,
                    "INFO",
                    "dry_run",
                    "DRY_RUNのためAPIは呼びませんでした",
                )
                self.db.revert_processing_to_ready(post.id)
                continue

            if not self._post_with_retries(post.id, post.content):
                continue
            success += 1
        return success

    def _post_with_retries(self, post_id: int, content: str) -> bool:
        last_error: XApiError | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = self.client.create_tweet(content, logger=self.logger)
                posted_at = to_iso(datetime.now(ZoneInfo(self.timezone)))
                self.db.mark_posted(post_id, result.post_id, posted_at)
                self.db.add_execution_log(
                    post_id,
                    "INFO",
                    "posted",
                    f"投稿成功 x_post_id={result.post_id}",
                    http_status=result.http_status,
                )
                self.logger.info(
                    "event=posted post_id=%s x_post_id=%s http=%s",
                    post_id,
                    result.post_id,
                    result.http_status,
                )
                return True
            except XApiError as exc:
                last_error = exc
                self.logger.warning(
                    "event=post_error post_id=%s attempt=%s http=%s code=%s msg=%s",
                    post_id,
                    attempt,
                    exc.status_code,
                    exc.error_code,
                    str(exc),
                )
                self.db.add_execution_log(
                    post_id,
                    "WARNING",
                    "post_error",
                    str(exc),
                    http_status=exc.status_code,
                )
                if exc.ambiguous:
                    self.db.mark_failed(
                        post_id,
                        exc.error_code or "ambiguous",
                        "結果不明のため再送せずFAILEDにしました。手動確認してください。",
                    )
                    return False
                if not exc.retryable or attempt >= self.max_attempts:
                    self.db.mark_failed(
                        post_id,
                        exc.error_code or "failed",
                        str(exc),
                    )
                    return False
                delay = exc.retry_after if exc.retry_after is not None else (2 ** attempt)
                self.logger.info(
                    "event=retry_wait post_id=%s seconds=%s", post_id, delay
                )
                time.sleep(float(delay))
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("event=unexpected post_id=%s", post_id)
                self.db.mark_failed(post_id, "unexpected", str(exc))
                return False

        if last_error:
            self.db.mark_failed(
                post_id,
                last_error.error_code or "failed",
                str(last_error),
            )
        return False
