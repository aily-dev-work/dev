from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Mapping

from ..models import ScoreProfile, TradingSignal
from .scoring_profile import get_active_score_profile
from .signal_dataset import build_signal_queryset, signals_to_dataset
from .signal_summary import build_summary_queryset, summarize_signals


MAX_DATASET_LIMIT = 500
DEFAULT_DATASET_LIMIT = 100

# トレードスタイル: 長期・短期・デイトレ。分析データ量とAIの最適化方針に使う。
TRADING_STYLE_LONG_TERM = "long_term"   # 長期保有（スイング・ポジション）
TRADING_STYLE_SHORT_TERM = "short_term"  # 短期トレード（数日〜数週間）
TRADING_STYLE_DAY_TRADE = "day_trade"    # デイトレード（当日決済）
TRADING_STYLE_CHOICES = (TRADING_STYLE_LONG_TERM, TRADING_STYLE_SHORT_TERM, TRADING_STYLE_DAY_TRADE)

# スタイル別のデフォルト dataset 件数（長期ほど多く取り長期的な視点で分析）
STYLE_DEFAULT_LIMIT = {
    TRADING_STYLE_LONG_TERM: 500,
    TRADING_STYLE_SHORT_TERM: 300,
    TRADING_STYLE_DAY_TRADE: 150,
}


def _normalize_limit(raw: Any) -> int:
    try:
        if raw is None or raw == "":
            return DEFAULT_DATASET_LIMIT
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_DATASET_LIMIT
    if value <= 0:
        return DEFAULT_DATASET_LIMIT
    return min(value, MAX_DATASET_LIMIT)


def _extract_filters(params: Mapping[str, Any]) -> Dict[str, Any]:
    keys = [
        "ticker",
        "signal_date_from",
        "signal_date_to",
        "signal_type",
    ]
    return {k: params.get(k) for k in keys if params.get(k) not in (None, "")}


def _get_trading_style(params: Mapping[str, Any]) -> str:
    raw = params.get("trading_style")
    if isinstance(raw, (list, tuple)) and raw:
        raw = raw[0]
    if raw in TRADING_STYLE_CHOICES:
        return raw
    return TRADING_STYLE_SHORT_TERM


def build_analysis_package_for_profile(
    profile: ScoreProfile,
    params: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    指定された ScoreProfile とクエリパラメータをもとに、
    AI 分析に渡しやすい analysis package を構築する。
    trading_style により長期視点用のデータ量を調整する。
    リクエストで未指定の場合はプロファイルの trading_style をフォールバックに使う。
    """
    trading_style = _get_trading_style(params)
    if hasattr(profile, "trading_style") and profile.trading_style in TRADING_STYLE_CHOICES:
        raw = params.get("trading_style")
        if isinstance(raw, (list, tuple)) and raw:
            raw = raw[0]
        if not raw or raw not in TRADING_STYLE_CHOICES:
            trading_style = profile.trading_style
    style_limit = STYLE_DEFAULT_LIMIT.get(trading_style, DEFAULT_DATASET_LIMIT)
    limit = _normalize_limit(params.get("limit") or style_limit)
    filters = _extract_filters(params)

    # summary 用 QuerySet: さらに score_profile_name / version で絞り込む
    summary_params: Dict[str, Any] = dict(params)
    summary_params["score_profile_name"] = profile.name
    summary_params["score_profile_version"] = profile.version
    summary_qs = build_summary_queryset(summary_params)
    summary_rows = summarize_signals(summary_qs)

    # dataset 用 QuerySet: build_signal_queryset でベースフィルタを適用し、profile で絞り込む
    dataset_qs = build_signal_queryset(params)
    dataset_qs = dataset_qs.filter(
        score_profile_name=profile.name,
        score_profile_version=profile.version,
    )
    # build_signal_queryset 内ですでに新しい順に order_by 済み
    dataset_qs = dataset_qs[:limit]
    dataset_rows = signals_to_dataset(dataset_qs)

    package_notes = (
        "This package is intended for AI analysis to improve ScoreProfile with a LONG-TERM perspective. "
        "It does not contain any AI-generated results. "
    )
    if trading_style == TRADING_STYLE_LONG_TERM:
        package_notes += (
            "The user trades with a long-term horizon (swing/position). "
            "Optimize for stability and multi-month performance; avoid overfitting to recent short-term moves."
        )
    elif trading_style == TRADING_STYLE_SHORT_TERM:
        package_notes += (
            "The user does short-term trading (days to weeks). "
            "Balance responsiveness with robustness over several weeks."
        )
    else:
        package_notes += (
            "The user is a day trader (same-day exit). "
            "Optimize for intraday signal quality; short-horizon metrics matter most."
        )

    package: Dict[str, Any] = {
        "target_profile": {
            "id": profile.id,
            "name": profile.name,
            "version": profile.version,
            "is_active": profile.is_active,
        },
        "config": {
            "weights_json": profile.weights_json,
            "thresholds_json": profile.thresholds_json,
        },
        "trading_style": trading_style,
        "filters": {
            **filters,
            "limit": limit,
        },
        "summary": summary_rows,
        "dataset_rows": dataset_rows,
        "notes": package_notes,
    }
    return package


def build_analysis_package_for_active_profile(
    params: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    現在 active な ScoreProfile を対象とした analysis package を構築する。
    """
    profile = get_active_score_profile()
    return build_analysis_package_for_profile(profile, params)

