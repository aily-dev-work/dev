from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Mapping

from ..models import ScoreProfile, TradingSignal
from .scoring_profile import get_active_score_profile
from .signal_dataset import build_signal_queryset, signals_to_dataset
from .signal_summary import build_summary_queryset, summarize_signals


MAX_DATASET_LIMIT = 500
DEFAULT_DATASET_LIMIT = 100


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


def build_analysis_package_for_profile(
    profile: ScoreProfile,
    params: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    指定された ScoreProfile とクエリパラメータをもとに、
    AI 分析に渡しやすい analysis package を構築する。
    """
    limit = _normalize_limit(params.get("limit"))
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
        "filters": {
            **filters,
            "limit": limit,
        },
        "summary": summary_rows,
        "dataset_rows": dataset_rows,
        "notes": (
            "This package is intended as input for AI-based analysis "
            "to compare and improve ScoreProfile performance. "
            "It does not contain any AI-generated results."
        ),
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

