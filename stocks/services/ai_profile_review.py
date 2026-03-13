from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Optional

from django.core.exceptions import ImproperlyConfigured

from ..models import ScoreProfile
from .analysis_package import (
    build_analysis_package_for_active_profile,
    build_analysis_package_for_profile,
)
from .scoring_profile import get_active_score_profile


EXPECTED_KEYS = {
    "target_profile",
    "analysis_summary",
    "issues",
    "improvement_hypotheses",
    "suggested_weights_json",
    "suggested_thresholds_json",
    "cautions",
}


def _call_openai_with_package(
    analysis_package: Dict[str, Any],
    user_note: Optional[str] = None,
) -> str:
    """
    OpenAI などの外部 AI API を呼び出すためのフック。

    実運用ではここで OpenAI クライアントを初期化し、
    analysis_package と user_note をプロンプトに含めて JSON 文字列を返す。

    このリポジトリではテスト時に monkeypatch されることを前提とし、
    デフォルト実装は設定不足エラーを送出する。
    """
    raise ImproperlyConfigured(
        "AI client is not configured. Please implement _call_openai_with_package "
        "with a real OpenAI (or other) client before using this feature in production."
    )


def _parse_ai_response(raw_text: str) -> Dict[str, Any]:
    """
    AI からの応答文字列を JSON として解析し、期待キーの存在を検証する。
    """
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI response is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("AI response JSON must be an object.")

    missing = EXPECTED_KEYS - data.keys()
    if missing:
        raise ValueError(f"AI response is missing expected keys: {sorted(missing)}")

    return data


def build_ai_review_for_profile(
    profile: ScoreProfile,
    params: Mapping[str, Any],
    user_note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    指定 ScoreProfile 向けの analysis-package を生成し、
    それを AI に渡して改善提案 JSON を取得する。
    """
    analysis_package = build_analysis_package_for_profile(profile, params)

    raw = _call_openai_with_package(analysis_package, user_note=user_note)
    parsed = _parse_ai_response(raw)
    return parsed


def build_ai_review_for_active_profile(
    params: Mapping[str, Any],
    user_note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    active な ScoreProfile を対象に AI レビューを実行する。
    """
    profile = get_active_score_profile()
    return build_ai_review_for_profile(profile, params, user_note=user_note)

