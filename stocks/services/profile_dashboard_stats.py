"""
フェーズ23: ダッシュボード用統計 service。
ops-summary / compare / activation-history を再利用し、1レスポンスにまとめる。
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..models import ScoreProfile, ScoreProfileActivationHistory
from .evaluation_horizon import get_horizon_key_and_days
from .profile_ops_summary import build_ops_summary
from .profile_comparison import compare_profiles
from .profile_review_targets import (
    DEFAULT_MIN_EVALUATED_COUNT,
    DEFAULT_STALE_DAYS,
    DEFAULT_THRESHOLD_SUCCESS_RATE,
)
from .scoring_profile import get_active_score_profile
from .signal_summary import build_summary_queryset, summarize_signals

RECENT_ACTIVATION_HISTORY_LIMIT = 10


def _recent_activation_history(limit: int = RECENT_ACTIVATION_HISTORY_LIMIT) -> List[Dict[str, Any]]:
    """直近 N 件の activation history を API と同じ形で返す。"""
    qs = (
        ScoreProfileActivationHistory.objects.select_related(
            "previous_profile",
            "activated_profile",
            "source_proposal",
        )
        .order_by("-activated_at", "-id")[:limit]
    )
    results = []
    for h in qs:
        previous_profile = h.previous_profile
        activated_profile = h.activated_profile
        results.append({
            "id": h.id,
            "previous_profile_id": previous_profile.id if previous_profile else None,
            "previous_profile_name": (
                previous_profile.name if previous_profile is not None
                else h.previous_profile_name_snapshot or None
            ),
            "previous_profile_version": (
                previous_profile.version if previous_profile is not None
                else h.previous_profile_version_snapshot or None
            ),
            "activated_profile_id": activated_profile.id,
            "activated_profile_name": (
                activated_profile.name or h.activated_profile_name_snapshot or None
            ),
            "activated_profile_version": (
                activated_profile.version
                or h.activated_profile_version_snapshot
                or None
            ),
            "source_proposal_id": h.source_proposal_id,
            "source_proposal_name": (
                h.source_proposal.proposal_name if h.source_proposal is not None
                else h.source_proposal_name_snapshot or None
            ),
            "activation_reason": h.activation_reason,
            "note": h.note or "",
            "activated_at": h.activated_at.isoformat() if h.activated_at else None,
        })
    return results


def _profile_overview() -> Dict[str, Any]:
    """全 profile 件数 / active / inactive / proposal-derived を返す。"""
    all_profiles = ScoreProfile.objects.all()
    total = all_profiles.count()
    active_count = sum(1 for p in all_profiles if p.is_active)
    inactive_count = total - active_count
    # proposal-derived: applied_score_profile で参照されている profile
    derived_ids = set(
        ScoreProfile.objects.filter(source_proposals__isnull=False).values_list("id", flat=True)
    )
    proposal_derived_count = len(derived_ids)
    return {
        "total_count": total,
        "active_count": active_count,
        "inactive_count": inactive_count,
        "proposal_derived_count": proposal_derived_count,
    }


def _chart_data(
    signal_date_from: str | None,
    signal_date_to: str | None,
) -> Dict[str, Any]:
    """profile_success_rate_rows / profile_avg_return_rows / activation_timeline_rows を構築。"""
    params: Dict[str, Any] = {}
    if signal_date_from:
        params["signal_date_from"] = signal_date_from
    if signal_date_to:
        params["signal_date_to"] = signal_date_to

    profile_success_rate_rows: List[Dict[str, Any]] = []
    profile_avg_return_rows: List[Dict[str, Any]] = []

    for profile in ScoreProfile.objects.all():
        horizon_key, horizon_days = get_horizon_key_and_days(profile)
        params["score_profile_name"] = profile.name
        params["score_profile_version"] = profile.version
        qs = build_summary_queryset(params)
        rows = summarize_signals(qs)
        for row in rows:
            horizon_data = row.get(horizon_key) or {}
            sr = horizon_data.get("success_rate")
            ar = horizon_data.get("avg_return")
            profile_success_rate_rows.append({
                "profile_id": profile.id,
                "profile_name": profile.name,
                "profile_version": profile.version,
                "signal_type": row.get("signal_type", ""),
                "success_rate_h20": sr,
                "evaluation_horizon_days": horizon_days,
            })
            profile_avg_return_rows.append({
                "profile_id": profile.id,
                "profile_name": profile.name,
                "profile_version": profile.version,
                "signal_type": row.get("signal_type", ""),
                "avg_return_h20": ar,
                "evaluation_horizon_days": horizon_days,
            })

    timeline = _recent_activation_history(limit=50)
    activation_timeline_rows = [
        {
            "activated_at": h["activated_at"],
            "activated_profile_name": h["activated_profile_name"],
            "activated_profile_version": h["activated_profile_version"],
            "activation_reason": h["activation_reason"],
        }
        for h in timeline
    ]

    return {
        "profile_success_rate_rows": profile_success_rate_rows,
        "profile_avg_return_rows": profile_avg_return_rows,
        "activation_timeline_rows": activation_timeline_rows,
    }


def build_dashboard_stats(
    *,
    signal_date_from: str | None = None,
    signal_date_to: str | None = None,
    base_profile_id: int | None = None,
    candidate_profile_id: int | None = None,
    threshold_success_rate: float = DEFAULT_THRESHOLD_SUCCESS_RATE,
    stale_days: int = DEFAULT_STALE_DAYS,
    min_evaluated_count: int = DEFAULT_MIN_EVALUATED_COUNT,
) -> Dict[str, Any]:
    """
    ダッシュボード用の統計を1レスポンスにまとめる。
    ops_summary / compare / activation-history を再利用する。
    base_profile_id と candidate_profile_id を両方指定した場合のみ compare_snapshot を返す。
    存在しない id を指定した場合は ValueError を上げる（呼び出し側で 404 にマッピングすること）。
    """
    from django.core.exceptions import ImproperlyConfigured

    # current_active_profile
    try:
        active = get_active_score_profile()
        current_active_profile = {
            "id": active.id,
            "name": active.name,
            "version": active.version,
            "is_active": active.is_active,
            "description": active.description or "",
        }
    except ImproperlyConfigured:
        current_active_profile = None

    # ops_summary（既存 service を再利用）
    ops_summary = build_ops_summary(
        signal_date_from=signal_date_from,
        signal_date_to=signal_date_to,
        threshold_success_rate=threshold_success_rate,
        stale_days=stale_days,
        min_evaluated_count=min_evaluated_count,
    )

    # recent_activation_history
    recent_activation_history = _recent_activation_history(limit=RECENT_ACTIVATION_HISTORY_LIMIT)

    # profile_overview
    profile_overview = _profile_overview()

    # compare_snapshot（両方指定時のみ）
    compare_snapshot = None
    if base_profile_id is not None and candidate_profile_id is not None:
        compare_snapshot = compare_profiles(
            base_profile_id,
            candidate_profile_id,
            signal_date_from=signal_date_from,
            signal_date_to=signal_date_to,
        )

    # chart_data
    chart_data = _chart_data(
        signal_date_from=signal_date_from,
        signal_date_to=signal_date_to,
    )

    return {
        "current_active_profile": current_active_profile,
        "ops_summary": ops_summary,
        "recent_activation_history": recent_activation_history,
        "profile_overview": profile_overview,
        "compare_snapshot": compare_snapshot,
        "chart_data": chart_data,
    }
