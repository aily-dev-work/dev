"""
フェーズ19: レビュー対象の抽出 service。
次に何を見直すべきか判断しやすいよう、current / stale / underperforming / accepted-not-activated を返す。
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.utils import timezone

from ..models import ScoreProfile, ScoreProfileActivationHistory, ScoreProfileProposal
from .evaluation_horizon import get_horizon_key_and_days
from .scoring_profile import get_active_score_profile
from .signal_summary import build_summary_queryset, summarize_signals


# デフォルト判定閾値（将来の見直し用に定数化）
DEFAULT_THRESHOLD_SUCCESS_RATE = 0.5
DEFAULT_STALE_DAYS = 30
DEFAULT_MIN_EVALUATED_COUNT = 5


def _profile_summary(
    profile: ScoreProfile,
    params: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """1 profile の summary を取得（既存 summary service を利用）。"""
    p = {
        **params,
        "score_profile_name": profile.name,
        "score_profile_version": profile.version,
    }
    qs = build_summary_queryset(p)
    return summarize_signals(qs)


# 成績 5 段階 + 未判定（API で返す値）
PERFORMANCE_EXCELLENT = "excellent"   # 優秀
PERFORMANCE_GOOD = "good"             # 良好
PERFORMANCE_AVERAGE = "average"       # 普通
PERFORMANCE_NEEDS_REVIEW = "needs_review"  # 要見直し
PERFORMANCE_POOR = "poor"             # 要改善
PERFORMANCE_UNRATED = "unrated"       # 未判定


def get_performance_level(
    profile: ScoreProfile,
    params: Dict[str, Any],
    min_evaluated_count: int,
) -> str:
    """
    プロファイルの成績を 5 段階 + 未判定で返す。
    トレードスタイルに応じた評価期間（h5/h10/h20）で、評価件数が足りている signal_type の
    成功率の最小値で判定。いずれも件数不足なら unrated。
    """
    horizon_key, _ = get_horizon_key_and_days(profile)
    rows = _profile_summary(profile, params)
    rates: List[float] = []
    for row in rows:
        horizon_data = row.get(horizon_key) or {}
        sr = horizon_data.get("success_rate")
        evaluated = horizon_data.get("evaluated_count", 0)
        if evaluated >= min_evaluated_count and sr is not None:
            rates.append(float(sr))
    if not rates:
        return PERFORMANCE_UNRATED
    min_sr = min(rates)
    if min_sr >= 0.75:
        return PERFORMANCE_EXCELLENT
    if min_sr >= 0.6:
        return PERFORMANCE_GOOD
    if min_sr >= 0.5:
        return PERFORMANCE_AVERAGE
    if min_sr >= 0.3:
        return PERFORMANCE_NEEDS_REVIEW
    return PERFORMANCE_POOR


def _is_underperforming(
    profile: ScoreProfile,
    params: Dict[str, Any],
    threshold_success_rate: float,
    min_evaluated_count: int,
) -> bool:
    """
    underperforming 判定: プロファイルのトレードスタイルに応じた評価期間（h5/h10/h20）で、
    いずれかの signal_type で evaluated_count >= min_evaluated_count かつ
    success_rate < threshold_success_rate なら True。
    データが無い、または evaluated_count が不足している場合は underperforming と見なさない。
    """
    horizon_key, _ = get_horizon_key_and_days(profile)
    rows = _profile_summary(profile, params)
    for row in rows:
        horizon_data = row.get(horizon_key) or {}
        sr = horizon_data.get("success_rate")
        evaluated = horizon_data.get("evaluated_count", 0)
        if (
            evaluated >= min_evaluated_count
            and sr is not None
            and sr < threshold_success_rate
        ):
            return True
    return False


def _is_stale(
    profile: ScoreProfile,
    stale_days: int,
) -> bool:
    """
    stale 判定: この profile が activated_profile になっている直近の履歴の
    activated_at から stale_days 日以上経過していれば True。
    """
    latest = (
        ScoreProfileActivationHistory.objects.filter(activated_profile_id=profile.id)
        .order_by("-activated_at", "-id")
        .first()
    )
    if latest is None:
        return False
    boundary = timezone.now() - timedelta(days=stale_days)
    return latest.activated_at <= boundary


def get_review_targets(
    *,
    signal_date_from: Optional[str] = None,
    signal_date_to: Optional[str] = None,
    threshold_success_rate: float = DEFAULT_THRESHOLD_SUCCESS_RATE,
    stale_days: int = DEFAULT_STALE_DAYS,
    min_evaluated_count: int = DEFAULT_MIN_EVALUATED_COUNT,
) -> Dict[str, Any]:
    """
    レビュー対象を抽出する。

    返却キー:
    - current_active_profile: 現在 active な profile の簡易情報（いなければ null）
    - stale_active_profiles: 長く active のままで見直しされていない profile のリスト
    - underperforming_profiles: 直近期間で h20 success_rate が閾値未満の profile のリスト
    - accepted_not_activated_profiles: accepted 済みだがまだ active にしていない proposal 由来 profile のリスト
    """
    params: Dict[str, Any] = {}
    if signal_date_from:
        params["signal_date_from"] = signal_date_from
    if signal_date_to:
        params["signal_date_to"] = signal_date_to

    result: Dict[str, Any] = {
        "current_active_profile": None,
        "stale_active_profiles": [],
        "underperforming_profiles": [],
        "accepted_not_activated_profiles": [],
    }

    try:
        current = get_active_score_profile()
    except Exception:
        current = None

    if current is not None:
        result["current_active_profile"] = {
            "id": current.id,
            "name": current.name,
            "version": current.version,
            "is_active": current.is_active,
        }
        if _is_stale(current, stale_days):
            result["stale_active_profiles"].append({
                "id": current.id,
                "name": current.name,
                "version": current.version,
                "is_active": current.is_active,
            })

    # underperforming: 全 profile を対象に閾値未満かつ最低評価件数以上かチェック
    for profile in ScoreProfile.objects.all():
        if _is_underperforming(
            profile, params, threshold_success_rate, min_evaluated_count
        ):
            result["underperforming_profiles"].append({
                "id": profile.id,
                "name": profile.name,
                "version": profile.version,
                "is_active": profile.is_active,
            })

    # accepted 済みで applied_score_profile が存在し、その profile が未 active のもの
    for proposal in ScoreProfileProposal.objects.filter(
        status=ScoreProfileProposal.STATUS_ACCEPTED,
        applied_score_profile__isnull=False,
    ).select_related("applied_score_profile"):
        prof = proposal.applied_score_profile
        if prof is not None and not prof.is_active:
            # 重複を避ける（同じ profile が複数 proposal から生成されている場合）
            already = next(
                (p for p in result["accepted_not_activated_profiles"] if p["id"] == prof.id),
                None,
            )
            if not already:
                result["accepted_not_activated_profiles"].append({
                    "id": prof.id,
                    "name": prof.name,
                    "version": prof.version,
                    "is_active": prof.is_active,
                    "source_proposal_id": proposal.id,
                    "source_proposal_name": proposal.proposal_name,
                })

    return result
