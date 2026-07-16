"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.config import load_settings, require_oauth_env
from app.database import Database, DuplicateContentError
from app.logger import setup_logger
from app.models import parse_tokyo_datetime, to_iso
from app.scheduler import Scheduler
from app.token_manager import TokenManager
from app.x_client import XClient


def _build_services(dry_run_override: bool | None = None):
    settings = load_settings()
    require_oauth_env(settings)
    logger = setup_logger(settings.log_path)
    db = Database(settings.db_path, timezone=settings.timezone)
    token_manager = TokenManager(
        settings.token_path,
        settings.client_id,
        settings.client_secret,
        settings.api_base_url,
    )
    client = XClient(token_manager, settings.api_base_url)
    dry_run = settings.dry_run if dry_run_override is None else dry_run_override
    scheduler = Scheduler(
        db=db,
        client=client,
        timezone=settings.timezone,
        logger=logger,
        dry_run=dry_run,
    )
    return settings, db, token_manager, client, scheduler, logger


def cmd_init_db(_: argparse.Namespace) -> int:
    settings = load_settings()
    db = Database(settings.db_path, timezone=settings.timezone)
    db.init_schema()
    print(f"DBを初期化しました: {settings.db_path}")
    return 0


def cmd_verify_auth(_: argparse.Namespace) -> int:
    settings, _db, token_manager, client, _scheduler, logger = _build_services()
    if not settings.token_path.exists():
        print(f"トークンファイルがありません: {settings.token_path}")
        return 1
    print("トークン概要:", token_manager.masked_summary())
    me = client.verify_auth(logger=logger)
    print("認証成功")
    print(f"  ユーザーID : {me.id}")
    print(f"  表示名     : {me.name}")
    print(f"  ユーザー名 : @{me.username}")
    return 0


def cmd_add_post(args: argparse.Namespace) -> int:
    settings = load_settings()
    db = Database(settings.db_path, timezone=settings.timezone)
    db.init_schema()
    dt = parse_tokyo_datetime(args.scheduled_at, settings.timezone)
    try:
        post_id = db.add_post(args.text, to_iso(dt))
    except DuplicateContentError as exc:
        print(f"登録できません: {exc}")
        return 1
    print("投稿を登録しました")
    print(f"  ID           : {post_id}")
    print(f"  scheduled_at : {to_iso(dt)}")
    print(f"  文字数       : {len(args.text)}")
    return 0


def cmd_list_posts(args: argparse.Namespace) -> int:
    settings = load_settings()
    db = Database(settings.db_path, timezone=settings.timezone)
    posts = db.list_posts(include_posted=args.all)
    if not posts:
        print("対象の投稿はありません")
        return 0
    for post in posts:
        preview = post.content.replace("\n", " ")[:60]
        print(
            f"#{post.id} [{post.status}] {post.scheduled_at} | {preview}"
            + ("…" if len(post.content) > 60 else "")
        )
    return 0


def cmd_run_once(args: argparse.Namespace) -> int:
    dry = True if args.dry_run else None
    if args.real:
        dry = False
    settings, _db, _tm, _client, scheduler, logger = _build_services(dry_run_override=dry)
    mode = "DRY-RUN" if scheduler.dry_run else "LIVE"
    print(f"run-once を開始します ({mode})")
    logger.info("event=cli_run_once mode=%s", mode)
    count = scheduler.run_once()
    print(f"完了: 成功 {count} 件（dry_run={scheduler.dry_run}）")
    if scheduler.dry_run:
        print("※ DRY_RUNのため実際のX投稿は行っていません")
    return 0


def cmd_cancel_post(args: argparse.Namespace) -> int:
    settings = load_settings()
    db = Database(settings.db_path, timezone=settings.timezone)
    if db.cancel_post(args.id):
        print(f"投稿 #{args.id} を CANCELLED にしました")
        return 0
    print(f"投稿 #{args.id} を取り消せませんでした（状態を確認してください）")
    return 1


def cmd_retry_post(args: argparse.Namespace) -> int:
    settings = load_settings()
    db = Database(settings.db_path, timezone=settings.timezone)
    if db.retry_post(args.id):
        print(f"投稿 #{args.id} を READY に戻しました")
        return 0
    print(f"投稿 #{args.id} を READY に戻せませんでした（FAILEDのみ対象）")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="X Auto Poster CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init-db", help="データベースを初期化")
    p_init.set_defaults(func=cmd_init_db)

    p_auth = sub.add_parser("verify-auth", help="認証アカウントを確認")
    p_auth.set_defaults(func=cmd_verify_auth)

    p_add = sub.add_parser("add-post", help="予約投稿を追加")
    p_add.add_argument("--text", required=True, help="投稿本文")
    p_add.add_argument("--scheduled-at", required=True, help="例: 2026-07-15 12:00")
    p_add.set_defaults(func=cmd_add_post)

    p_list = sub.add_parser("list-posts", help="未投稿などを一覧")
    p_list.add_argument("--all", action="store_true", help="POSTEDも含める")
    p_list.set_defaults(func=cmd_list_posts)

    p_run = sub.add_parser("run-once", help="期限到来分を1回処理")
    p_run.add_argument("--dry-run", action="store_true", help="APIを呼ばず対象だけ確認")
    p_run.add_argument(
        "--real",
        action="store_true",
        help="環境変数に関わらず実投稿する（注意）",
    )
    p_run.set_defaults(func=cmd_run_once)

    p_cancel = sub.add_parser("cancel-post", help="投稿を取消")
    p_cancel.add_argument("--id", type=int, required=True)
    p_cancel.set_defaults(func=cmd_cancel_post)

    p_retry = sub.add_parser("retry-post", help="FAILEDをREADYへ戻す")
    p_retry.add_argument("--id", type=int, required=True)
    p_retry.set_defaults(func=cmd_retry_post)

    return parser


def main(argv: list[str] | None = None) -> int:
    # Ensure project root is on sys.path when run as python -m app.cli
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
