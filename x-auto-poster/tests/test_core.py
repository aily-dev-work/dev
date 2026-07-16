"""Unit tests with mocked HTTP — no real X API calls."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.config import PROJECT_ROOT, load_settings
from app.database import Database, DuplicateContentError
from app.logger import mask_secret
from app.models import content_hash, now_tokyo, parse_tokyo_datetime, to_iso
from app.scheduler import Scheduler
from app.token_manager import OAuthTokens, TokenManager
from app.x_client import XApiError, XClient


@pytest.fixture()
def tmp_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data = tmp_path / "data"
    logs = tmp_path / "logs"
    data.mkdir()
    logs.mkdir()
    env = tmp_path / ".env"
    env.write_text(
        "\n".join(
            [
                "X_CLIENT_ID=testid",
                "X_CLIENT_SECRET=testsecret",
                "X_API_BASE_URL=https://api.x.com",
                "APP_TIMEZONE=Asia/Tokyo",
                "DRY_RUN=true",
            ]
        ),
        encoding="utf-8",
    )
    tokens = {
        "access_token": "access_token_value_123456",
        "refresh_token": "refresh_token_value_123456",
        "token_type": "bearer",
        "expires_at": None,
        "scope": "tweet.read tweet.write users.read offline.access",
    }
    (data / "oauth_tokens.json").write_text(
        json.dumps(tokens), encoding="utf-8"
    )
    monkeypatch.setenv("X_CLIENT_ID", "testid")
    monkeypatch.setenv("X_CLIENT_SECRET", "testsecret")
    monkeypatch.setenv("X_API_BASE_URL", "https://api.x.com")
    monkeypatch.setenv("APP_TIMEZONE", "Asia/Tokyo")
    monkeypatch.setenv("DRY_RUN", "true")
    return tmp_path


def test_project_root_on_d_drive() -> None:
    assert PROJECT_ROOT.drive.upper() == "D:"
    assert PROJECT_ROOT.name == "x-auto-poster"
    assert PROJECT_ROOT.parent.name.lower() == "dev"


def test_mask_secret() -> None:
    assert mask_secret("abcdefghijklmnop") == "abcd...mnop"
    assert mask_secret("") == "(empty)"


def test_content_hash_stable() -> None:
    assert content_hash("hello") == content_hash("  hello  ")
    assert content_hash("a") != content_hash("b")


def test_duplicate_prevention(tmp_project: Path) -> None:
    db = Database(tmp_project / "data" / "x_poster.db")
    db.init_schema()
    now = to_iso(now_tokyo())
    db.add_post("同じ本文", now)
    with pytest.raises(DuplicateContentError):
        db.add_post("同じ本文", now)


def test_due_posts_claim(tmp_project: Path) -> None:
    db = Database(tmp_project / "data" / "x_poster.db")
    db.init_schema()
    past = to_iso(parse_tokyo_datetime("2020-01-01 00:00"))
    future = to_iso(parse_tokyo_datetime("2099-01-01 00:00"))
    db.add_post("past post", past)
    db.add_post("future post", future)
    claimed = db.claim_due_posts(to_iso(now_tokyo()))
    assert len(claimed) == 1
    assert claimed[0].content == "past post"
    assert claimed[0].status == "PROCESSING"


def test_token_expiry(tmp_project: Path) -> None:
    path = tmp_project / "data" / "oauth_tokens.json"
    tm = TokenManager(path, "id", "secret", "https://api.x.com")
    tokens = tm.load()
    expired = OAuthTokens(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
    )
    tm.save(expired)
    assert tm.is_access_expired() is True
    future = OAuthTokens(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    )
    tm.save(future)
    assert tm.is_access_expired() is False


def test_refresh_keeps_old_refresh_token(tmp_project: Path) -> None:
    path = tmp_project / "data" / "oauth_tokens.json"
    tm = TokenManager(path, "id", "secret", "https://api.x.com")
    before = tm.load()
    updated = tm.apply_refresh_response(
        {"access_token": "new_access_abcdefgh", "expires_in": 7200}
    )
    assert updated.access_token.startswith("new_access")
    assert updated.refresh_token == before.refresh_token


def test_refresh_replaces_refresh_token(tmp_project: Path) -> None:
    path = tmp_project / "data" / "oauth_tokens.json"
    tm = TokenManager(path, "id", "secret", "https://api.x.com")
    updated = tm.apply_refresh_response(
        {
            "access_token": "new_access_abcdefgh",
            "refresh_token": "brand_new_refresh_token_xx",
            "expires_in": 7200,
        }
    )
    assert updated.refresh_token == "brand_new_refresh_token_xx"


def test_401_refresh_once(tmp_project: Path) -> None:
    path = tmp_project / "data" / "oauth_tokens.json"
    session = MagicMock()
    unauthorized = MagicMock()
    unauthorized.status_code = 401
    unauthorized.headers = {}
    unauthorized.text = "unauthorized"
    ok = MagicMock()
    ok.status_code = 200
    ok.headers = {"x-rate-limit-remaining": "10"}
    ok.json.return_value = {"data": {"id": "1", "name": "n", "username": "u"}}
    # First GET 401, after refresh GET 200
    session.request.side_effect = [unauthorized, ok]

    refresh_resp = MagicMock()
    refresh_resp.status_code = 200
    refresh_resp.json.return_value = {
        "access_token": "refreshed_access_token_xx",
        "expires_in": 7200,
    }
    session.post.return_value = refresh_resp

    tm = TokenManager(path, "id", "secret", "https://api.x.com", session=session)
    client = XClient(tm, "https://api.x.com", session=session)
    me = client.verify_auth()
    assert me.username == "u"
    assert session.request.call_count == 2
    assert session.post.call_count == 1


def test_429_retry_after() -> None:
    response = MagicMock()
    response.status_code = 429
    response.headers = {"Retry-After": "12"}
    response.text = "rate"
    client = XClient(
        TokenManager(Path("."), "a", "b", "https://api.x.com"),
        "https://api.x.com",
    )
    err = client._classify_http_error(response)
    assert err.retryable is True
    assert err.retry_after == 12.0


def test_posted_not_reprocessed(tmp_project: Path) -> None:
    db = Database(tmp_project / "data" / "x_poster.db")
    db.init_schema()
    past = to_iso(parse_tokyo_datetime("2020-01-01 00:00"))
    pid = db.add_post("already", past)
    db.mark_posted(pid, "123", to_iso(now_tokyo()))
    claimed = db.claim_due_posts(to_iso(now_tokyo()))
    assert claimed == []


def test_dry_run_skips_api(tmp_project: Path) -> None:
    db = Database(tmp_project / "data" / "x_poster.db")
    db.init_schema()
    past = to_iso(parse_tokyo_datetime("2020-01-01 00:00"))
    db.add_post("dry run body", past)
    client = MagicMock()
    logger = MagicMock()
    sched = Scheduler(db, client, "Asia/Tokyo", logger, dry_run=True)
    count = sched.run_once()
    assert count == 0
    client.create_tweet.assert_not_called()
    posts = db.list_posts()
    assert any(p.status == "READY" for p in posts)


def test_load_settings_paths() -> None:
    settings = load_settings()
    assert settings.project_root == PROJECT_ROOT
    assert settings.db_path == PROJECT_ROOT / "data" / "x_poster.db"
    assert settings.token_path == PROJECT_ROOT / "data" / "oauth_tokens.json"
