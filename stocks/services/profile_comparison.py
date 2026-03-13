"""
フェーズ19: active profile と候補 profile の比較用サマリ service。
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..models import ScoreProfile, ScoreProfileProposal
from .signal_summary import build_summary_queryset, summarize_signals


def _profile_info(profile: ScoreProfile) -> Dict[str, Any]:
    """profile の基本情報と source proposal の有無を返す。"""
    source_proposal = (
        ScoreProfileProposal.objects.filter(applied_score_profile=profile)
        .order_by("-created_at")
        .first()
    )
    return {
        "id": profile.id,
        "name": profile.name,
        "version": profile.version,
        "is_active": profile.is_active,
        "source_proposal_id": source_proposal.id if source_proposal else None,
        "source_proposal_name": source_proposal.proposal_name if source_proposal else None,
    }


def _summary_for_profile(
    profile: ScoreProfile,
    signal_date_from: str | None,
    signal_date_to: str | None,
) -> List[Dict[str, Any]]:
    """1 profile の summary を取得。"""
    params: Dict[str, Any] = {
        "score_profile_name": profile.name,
        "score_profile_version": profile.version,
    }
    if signal_date_from:
        params["signal_date_from"] = signal_date_from
    if signal_date_to:
        params["signal_date_to"] = signal_date_to
    qs = build_summary_queryset(params)
    return summarize_signals(qs)


def compare_profiles(
    base_profile_id: int,
    candidate_profile_id: int,
    *,
    signal_date_from: str | None = None,
    signal_date_to: str | None = None,
) -> Dict[str, Any]:
    """
    base と candidate の2 profile を比較用サマリで返す。
    同じ profile id を指定した場合も 200 で同じ構造を返す（冪等）。
    """
    try:
        base = ScoreProfile.objects.get(pk=base_profile_id)
    except ScoreProfile.DoesNotExist:
        raise ValueError("Base profile not found.") from None

    try:
        candidate = ScoreProfile.objects.get(pk=candidate_profile_id)
    except ScoreProfile.DoesNotExist:
        raise ValueError("Candidate profile not found.") from None

    base_summaries = _summary_for_profile(base, signal_date_from, signal_date_to)
    candidate_summaries = _summary_for_profile(
        candidate, signal_date_from, signal_date_to
    )

    # signal_type をキーにしたマップ
    base_by_type: Dict[str, Dict[str, Any]] = {
        row["signal_type"]: row for row in base_summaries
    }
    candidate_by_type: Dict[str, Dict[str, Any]] = {
        row["signal_type"]: row for row in candidate_summaries
    }
    all_types = sorted(set(base_by_type) | set(candidate_by_type))

    comparison: List[Dict[str, Any]] = []
    for signal_type in all_types:
        b = base_by_type.get(signal_type)
        c = candidate_by_type.get(signal_type)
        comparison.append({
            "signal_type": signal_type,
            "base": b or {
                "total_signals": 0,
                "h5": {"evaluated_count": 0, "success_count": 0, "success_rate": None, "avg_return": None},
                "h10": {"evaluated_count": 0, "success_count": 0, "success_rate": None, "avg_return": None},
                "h20": {"evaluated_count": 0, "success_count": 0, "success_rate": None, "avg_return": None},
            },
            "candidate": c or {
                "total_signals": 0,
                "h5": {"evaluated_count": 0, "success_count": 0, "success_rate": None, "avg_return": None},
                "h10": {"evaluated_count": 0, "success_count": 0, "success_rate": None, "avg_return": None},
                "h20": {"evaluated_count": 0, "success_count": 0, "success_rate": None, "avg_return": None},
            },
        })

    return {
        "base_profile": _profile_info(base),
        "candidate_profile": _profile_info(candidate),
        "comparison": comparison,
    }
