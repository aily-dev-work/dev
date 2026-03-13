"""
フェーズ19: レビュー対象の抽出 service。
次に何を見直すべきか判断しやすいよう、current / stale / underperforming / accepted-not-activated を返す。
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.utils import timezone

from ..models import ScoreProfile, ScoreProfileActivationHistory, ScoreProfileProposal
from .scoring_profile import get_active_score_profile
from .signal_summary import build_summary_queryset, summarize_signals


# デフォルト判定閾値（将来の見直し用に定数化）
DEFAULT_THRESHOLD_SUCCESS_RATE = 0.5
DEFAULT_STALE_DAYS = 30


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


def _is_underperforming(
    profile: ScoreProfile,
    params: Dict[str, Any],
    threshold_success_rate: float,
) -> bool:
    """
    underperforming 判定: h20.success_rate が閾値未満の signal_type が1つでもあれば True。
    データが無い（evaluated_count=0）の場合は underperforming と見なさない。
    """
    rows = _profile_summary(profile, params)
    for row in rows:
        h20 = row.get("h20") or {}
        sr = h20.get("success_rate")
        evaluated = h20.get("evaluated_count", 0)
        if evaluated > 0 and sr is not None and sr < threshold_success_rate:
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

    # underperforming: 全 profile を対象に閾値未満かチェック
    for profile in ScoreProfile.objects.all():
        if _is_underperforming(profile, params, threshold_success_rate):
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
