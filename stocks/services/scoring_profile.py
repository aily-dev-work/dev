from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from django.core.exceptions import ImproperlyConfigured

from ..models import ScoreProfile


@dataclass
class ScoringConfig:
    buy_weights: Dict[str, float]
    sell_weights: Dict[str, float]
    bias_thresholds: Dict[str, Any]
    strength_thresholds: Dict[str, Any]


def get_active_score_profile() -> ScoreProfile:
    """
    現在有効な ScoreProfile を 1件取得する。

    - 該当 0 件 → ImproperlyConfigured
    - 複数件 → ImproperlyConfigured
    """
    try:
        profile = ScoreProfile.objects.get(is_active=True)
    except ScoreProfile.DoesNotExist:
        raise ImproperlyConfigured(
            "No active ScoreProfile found. "
            "Please create and activate a score profile (フェーズ8のスコア設定プロファイル)."
        )
    except ScoreProfile.MultipleObjectsReturned:
        raise ImproperlyConfigured(
            "Multiple active ScoreProfile rows found. "
            "Please ensure exactly one active profile is configured."
        )
    return profile


def get_active_scoring_config() -> ScoringConfig:
    """
    現在有効な ScoreProfile からスコア設定を取得する。
    """
    profile = get_active_score_profile()

    data = profile.weights_json or {}
    thresholds = profile.thresholds_json or {}

    buy_weights = data.get("buy", {})
    sell_weights = data.get("sell", {})

    bias_thresholds = thresholds.get(
        "bias",
        {
            "neutral_abs_diff_lt": 10.0,
        },
    )
    strength_thresholds = thresholds.get(
        "strength",
        {
            "weak_abs_diff_lt": 15.0,
            "normal_abs_diff_lt": 30.0,
        },
    )

    return ScoringConfig(
        buy_weights={k: float(v) for k, v in buy_weights.items()},
        sell_weights={k: float(v) for k, v in sell_weights.items()},
        bias_thresholds=bias_thresholds,
        strength_thresholds=strength_thresholds,
    )

