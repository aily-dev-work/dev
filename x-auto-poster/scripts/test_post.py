"""Interactive test post — requires typing POST exactly."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import load_settings, require_oauth_env
from app.logger import setup_logger
from app.token_manager import TokenManager
from app.x_client import XClient

TEST_TEXT = (
    "make-mensbody-naviのX API接続テストです。\n"
    "自動投稿システムの動作確認を行っています。"
)


def main() -> int:
    settings = load_settings()
    require_oauth_env(settings)
    logger = setup_logger(settings.log_path)
    tm = TokenManager(
        settings.token_path,
        settings.client_id,
        settings.client_secret,
        settings.api_base_url,
    )
    client = XClient(tm, settings.api_base_url)

    me = client.verify_auth(logger=logger)
    endpoint = f"{settings.api_base_url}/2/tweets"

    print("==== 実投稿前の確認 ====")
    print(f"投稿対象アカウント : @{me.username} ({me.name})")
    print(f"予定エンドポイント : POST {endpoint}")
    print(f"文字数             : {len(TEST_TEXT)}")
    print("--- 投稿本文 ---")
    print(TEST_TEXT)
    print("----------------")
    print("実投稿する場合は正確に「POST」と入力してください。")
    print("Enter / y / yes では投稿しません。")
    answer = input("> ").strip()
    if answer != "POST":
        print("中止しました（入力が POST ではありません）。")
        return 0

    result = client.create_tweet(TEST_TEXT, logger=logger)
    print("投稿成功")
    print(f"  投稿ID       : {result.post_id}")
    print(f"  HTTPステータス: {result.http_status}")
    print(f"  本文(返却)   : {result.text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
