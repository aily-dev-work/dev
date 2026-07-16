"""X (Twitter) API client for text posts only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import requests

from app.logger import sanitize_text
from app.token_manager import TokenManager


class XApiError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        retryable: bool = False,
        retry_after: float | None = None,
        ambiguous: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.retryable = retryable
        self.retry_after = retry_after
        self.ambiguous = ambiguous


@dataclass
class MeUser:
    id: str
    name: str
    username: str


@dataclass
class PostResult:
    post_id: str
    text: str
    http_status: int
    created_at: str | None


class XClient:
    def __init__(
        self,
        token_manager: TokenManager,
        api_base_url: str,
        session: requests.Session | None = None,
        timeout: float = 30.0,
        clock: Callable[[], Any] | None = None,
    ) -> None:
        self.token_manager = token_manager
        self.api_base_url = api_base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout
        self._refreshed_once = False

    def _auth_headers(self, *, with_json: bool = True) -> dict[str, str]:
        token = self.token_manager.ensure_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        if with_json:
            headers["Content-Type"] = "application/json"
        return headers

    def _log_rate_headers(self, response: requests.Response, logger: Any) -> None:
        for key in (
            "x-rate-limit-limit",
            "x-rate-limit-remaining",
            "x-rate-limit-reset",
        ):
            if key in response.headers:
                logger.info("rate_limit %s=%s", key, response.headers.get(key))

    def _classify_http_error(self, response: requests.Response) -> XApiError:
        status = response.status_code
        body = sanitize_text(response.text, max_len=400)
        retry_after: float | None = None
        if "Retry-After" in response.headers:
            try:
                retry_after = float(response.headers["Retry-After"])
            except ValueError:
                retry_after = None
        elif status == 429 and "x-rate-limit-reset" in response.headers:
            try:
                import time

                reset_at = int(response.headers["x-rate-limit-reset"])
                retry_after = max(0.0, float(reset_at - int(time.time())))
            except ValueError:
                retry_after = None

        if status == 400:
            return XApiError(
                f"投稿内容またはリクエストが不正です (400): {body}",
                status_code=400,
                error_code="bad_request",
            )
        if status == 401:
            return XApiError(
                "認証エラー (401)。トークン更新を試します。",
                status_code=401,
                error_code="unauthorized",
                retryable=False,
            )
        if status == 402:
            return XApiError(
                "課金/クレジット不足の可能性があります (402)。"
                " X Developer Console のクレジット残量を確認してください。",
                status_code=402,
                error_code="payment_required",
            )
        if status == 403:
            return XApiError(
                f"権限またはスコープ不足です (403): {body}",
                status_code=403,
                error_code="forbidden",
            )
        if status == 404:
            return XApiError(
                f"リソースが見つかりません (404): {body}",
                status_code=404,
                error_code="not_found",
            )
        if status == 422:
            return XApiError(
                f"処理できない実体です (422): {body}",
                status_code=422,
                error_code="unprocessable",
            )
        if status == 429:
            return XApiError(
                "レート制限に達しました (429)。",
                status_code=429,
                error_code="rate_limited",
                retryable=True,
                retry_after=retry_after,
            )
        if status >= 500:
            return XApiError(
                f"X側の一時的な障害の可能性があります ({status}): {body}",
                status_code=status,
                error_code="server_error",
                retryable=True,
            )
        return XApiError(
            f"予期しないHTTPエラー ({status}): {body}",
            status_code=status,
            error_code="http_error",
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        logger: Any | None = None,
        allow_refresh: bool = True,
    ) -> requests.Response:
        url = f"{self.api_base_url}{path}"
        try:
            response = self.session.request(
                method,
                url,
                headers=self._auth_headers(with_json=json_body is not None),
                json=json_body,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise XApiError(
                f"通信タイムアウト: {exc}",
                error_code="timeout",
                retryable=True,
            ) from exc
        except requests.ConnectionError as exc:
            raise XApiError(
                f"接続エラー: {exc}",
                error_code="connection_error",
                retryable=True,
            ) from exc
        except requests.RequestException as exc:
            # Response may have been lost — treat as ambiguous if posting
            raise XApiError(
                f"通信エラー（結果不明の可能性）: {exc}",
                error_code="network_ambiguous",
                retryable=False,
                ambiguous=True,
            ) from exc

        if logger is not None:
            self._log_rate_headers(response, logger)

        if response.status_code == 401 and allow_refresh:
            self.token_manager.refresh()
            return self._request(
                method,
                path,
                json_body=json_body,
                logger=logger,
                allow_refresh=False,
            )

        if response.status_code >= 400:
            raise self._classify_http_error(response)
        return response

    def verify_auth(self, logger: Any | None = None) -> MeUser:
        """GET /2/users/me — may refresh if 401 or expired."""
        # If no expires_at, try current token first; refresh only on 401
        response = self._request("GET", "/2/users/me", logger=logger)
        data = response.json().get("data") or {}
        return MeUser(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            username=str(data.get("username", "")),
        )

    def create_tweet(self, text: str, logger: Any | None = None) -> PostResult:
        try:
            response = self._request(
                "POST",
                "/2/tweets",
                json_body={"text": text},
                logger=logger,
            )
        except XApiError as exc:
            if exc.ambiguous:
                # Do not auto-retry post — unknown success
                raise
            raise

        payload = response.json()
        data = payload.get("data") or {}
        post_id = str(data.get("id", ""))
        if not post_id:
            raise XApiError(
                "投稿レスポンスにIDがありません。結果不明のため再送しません。",
                status_code=response.status_code,
                error_code="missing_post_id",
                ambiguous=True,
            )
        return PostResult(
            post_id=post_id,
            text=str(data.get("text", text)),
            http_status=response.status_code,
            created_at=None,
        )
