"""OAuth token storage and refresh."""

from __future__ import annotations

import json
import os
from base64 import b64encode
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from app.logger import mask_secret


@dataclass
class OAuthTokens:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: str | None = None
    scope: str = "tweet.read tweet.write users.read offline.access"

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at,
            "scope": self.scope,
        }


class TokenManager:
    """Load/save tokens and refresh via OAuth 2.0."""

    def __init__(
        self,
        token_path: Path,
        client_id: str,
        client_secret: str,
        api_base_url: str,
        session: requests.Session | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.token_path = token_path
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_base_url = api_base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout
        self._tokens: OAuthTokens | None = None

    def load(self) -> OAuthTokens:
        if not self.token_path.exists():
            raise FileNotFoundError(
                f"トークンファイルがありません: {self.token_path}。"
                " data/oauth_tokens.json に Access Token / Refresh Token を保存してください。"
            )
        data = json.loads(self.token_path.read_text(encoding="utf-8"))
        access = (data.get("access_token") or "").strip()
        refresh = (data.get("refresh_token") or "").strip()
        if not access or not refresh:
            raise ValueError(
                "oauth_tokens.json の access_token / refresh_token が空です。"
            )
        self._tokens = OAuthTokens(
            access_token=access,
            refresh_token=refresh,
            token_type=data.get("token_type") or "bearer",
            expires_at=data.get("expires_at"),
            scope=data.get("scope")
            or "tweet.read tweet.write users.read offline.access",
        )
        return self._tokens

    def save(self, tokens: OAuthTokens) -> None:
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(tokens.to_dict(), ensure_ascii=False, indent=2)
        tmp_path = self.token_path.with_suffix(self.token_path.suffix + ".tmp")
        tmp_path.write_text(payload + "\n", encoding="utf-8")
        os.replace(tmp_path, self.token_path)
        self._tokens = tokens

    @property
    def tokens(self) -> OAuthTokens:
        if self._tokens is None:
            return self.load()
        return self._tokens

    def is_access_expired(self, skew_seconds: int = 300) -> bool:
        """True if expires_at is within skew (default 5 minutes)."""
        tokens = self.tokens
        if not tokens.expires_at:
            return False
        expires = datetime.fromisoformat(tokens.expires_at)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return now >= (expires - timedelta(seconds=skew_seconds))

    def ensure_access_token(self) -> str:
        tokens = self.load()
        if tokens.expires_at and self.is_access_expired():
            self.refresh()
        return self.tokens.access_token

    def refresh(self) -> OAuthTokens:
        """Refresh access token using refresh_token. Does not log secrets."""
        current = self.load()
        token_url = f"{self.api_base_url}/2/oauth2/token"
        basic = b64encode(
            f"{self.client_id}:{self.client_secret}".encode("utf-8")
        ).decode("ascii")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic}",
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": current.refresh_token,
        }
        try:
            response = self.session.post(
                token_url,
                headers=headers,
                data=data,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"トークン更新の通信に失敗しました: {exc}") from exc

        if response.status_code == 400:
            try:
                err = response.json()
            except Exception:
                err = {}
            if err.get("error") == "invalid_grant":
                raise RuntimeError(
                    "Refresh Token が無効です (invalid_grant)。"
                    " X Developer Console で再認可し、oauth_tokens.json を更新してください。"
                )

        if response.status_code >= 400:
            raise RuntimeError(
                f"トークン更新に失敗しました (HTTP {response.status_code})。"
                " Client ID/Secret と Refresh Token を確認してください。"
            )

        body = response.json()
        new_access = body.get("access_token")
        if not new_access:
            raise RuntimeError("トークン更新レスポンスに access_token がありません。")

        new_refresh = body.get("refresh_token") or current.refresh_token
        expires_in = body.get("expires_in")
        expires_at: str | None = current.expires_at
        if expires_in is not None:
            expires_at = (
                datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
            ).isoformat()

        updated = OAuthTokens(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type=body.get("token_type") or "bearer",
            expires_at=expires_at,
            scope=body.get("scope") or current.scope,
        )
        self.save(updated)
        return updated

    def apply_refresh_response(self, body: dict[str, Any]) -> OAuthTokens:
        """Apply a refresh response dict (used by tests)."""
        current = self.load()
        new_access = body["access_token"]
        new_refresh = body.get("refresh_token") or current.refresh_token
        expires_at = current.expires_at
        if "expires_in" in body:
            expires_at = (
                datetime.now(timezone.utc)
                + timedelta(seconds=int(body["expires_in"]))
            ).isoformat()
        updated = OAuthTokens(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type=body.get("token_type") or "bearer",
            expires_at=expires_at,
            scope=body.get("scope") or current.scope,
        )
        self.save(updated)
        return updated

    def masked_summary(self) -> str:
        t = self.tokens
        return (
            f"access={mask_secret(t.access_token)} "
            f"refresh={mask_secret(t.refresh_token)} "
            f"expires_at={t.expires_at}"
        )
