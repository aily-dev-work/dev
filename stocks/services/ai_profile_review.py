from __future__ import annotations

import json
import os
from typing import Any, Dict, Mapping, Optional

from django.core.exceptions import ImproperlyConfigured

from ..models import ScoreProfile
from .analysis_package import (
    build_analysis_package_for_active_profile,
    build_analysis_package_for_profile,
)
from .scoring_profile import get_active_score_profile

try:
    # 新しい OpenAI Python クライアント (>=1.x) を想定
    from openai import OpenAI  # type: ignore[import]
except ImportError:  # pragma: no cover - 実環境でのみ評価
    OpenAI = None  # type: ignore[assignment]


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
    OpenAI などの外部 AI API を呼び出すための実装。

    必要な環境変数:
    - OPENAI_API_KEY: API キー（必須）
    - OPENAI_MODEL: 利用するモデル名（例: "gpt-4.1-mini"。未指定時は "gpt-4.1-mini"）
    - OPENAI_BASE_URL: オプション。自前プロキシなどを利用する場合。
    """
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    base_url = os.getenv("OPENAI_BASE_URL")

    if OpenAI is None:
        raise ImproperlyConfigured(
            "openai Python client is not installed. "
            "Install the 'openai' package and configure OPENAI_API_KEY."
        )

    if not api_key:
        raise ImproperlyConfigured(
            "OPENAI_API_KEY is not set. "
            "Set OPENAI_API_KEY (and optionally OPENAI_MODEL / OPENAI_BASE_URL) in the environment."
        )

    client_kwargs: Dict[str, Any] = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)  # type: ignore[call-arg]

    system_prompt = (
        "You are an expert quantitative trader and ML engineer. "
        "You receive a JSON package containing a trading signal profile configuration, "
        "its historical performance summary, and signal-level data. "
        "Your task is to review the current ScoreProfile with a LONG-TERM perspective: "
        "prefer stability and robustness over time; avoid overfitting to the most recent data. "
        "The package includes 'trading_style':\n"
        "  - long_term: user holds positions for weeks/months (swing/position). Optimize for multi-month consistency; favor trend and structure over short noise.\n"
        "  - short_term: user trades over days to weeks. Balance responsiveness with robustness over several weeks.\n"
        "  - day_trade: user closes positions within the same day. Optimize for intraday signal quality and short-horizon metrics.\n"
        "Propose improved weights_json and thresholds_json that suit the given trading_style and long-term view.\n\n"
        "You MUST respond with a single JSON object ONLY, without any surrounding text. "
        "The JSON MUST contain the keys:\n"
        "  - target_profile (object)\n"
        "  - analysis_summary (string)\n"
        "  - issues (array)\n"
        "  - improvement_hypotheses (array)\n"
        "  - suggested_weights_json (object)\n"
        "  - suggested_thresholds_json (object)\n"
        "  - cautions (array)\n"
        "Do not include Markdown or natural language outside of JSON."
    )

    user_payload: Dict[str, Any] = {
        "analysis_package": analysis_package,
    }
    if user_note:
        user_payload["user_note"] = user_note

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False),
        },
    ]

    completion = client.chat.completions.create(  # type: ignore[attr-defined]
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
    )

    content = completion.choices[0].message.content  # type: ignore[assignment]
    if not content:
        raise ValueError("AI response content is empty.")

    return content


def _parse_ai_response(raw_text: str) -> Dict[str, Any]:
    """
    AI からの応答文字列を JSON として解析し、期待キーと型を検証する。
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

    # 型検証
    if not isinstance(data["target_profile"], dict):
        raise ValueError("AI response field 'target_profile' must be an object.")
    if not isinstance(data["analysis_summary"], str):
        raise ValueError("AI response field 'analysis_summary' must be a string.")
    if not isinstance(data["issues"], list):
        raise ValueError("AI response field 'issues' must be a list.")
    if not isinstance(data["improvement_hypotheses"], list):
        raise ValueError("AI response field 'improvement_hypotheses' must be a list.")
    if not isinstance(data["suggested_weights_json"], dict):
        raise ValueError("AI response field 'suggested_weights_json' must be an object.")
    if not isinstance(data["suggested_thresholds_json"], dict):
        raise ValueError("AI response field 'suggested_thresholds_json' must be an object.")
    if not isinstance(data["cautions"], list):
        raise ValueError("AI response field 'cautions' must be a list.")

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

