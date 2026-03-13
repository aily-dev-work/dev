from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Mapping

from ..models import ScoreProfile, ScoreProfileProposal


def build_proposal_name(profile: ScoreProfile) -> str:
    """
    ScoreProfile 向け提案のデフォルト名を生成する。

    例: "Default scoring profile v1 proposal 2026-03-13T12:34:56"
    """
    timestamp = datetime.utcnow().isoformat(timespec="seconds")
    return f"{profile.name} {profile.version} proposal {timestamp}"


def save_profile_proposal(
    profile: ScoreProfile,
    filters: Mapping[str, Any],
    ai_result: Mapping[str, Any],
) -> ScoreProfileProposal:
    """
    AI レビュー結果を ScoreProfileProposal として保存する。

    ai_result には少なくとも以下のキーが含まれている前提:
    - target_profile
    - analysis_summary
    - issues
    - improvement_hypotheses
    - suggested_weights_json
    - suggested_thresholds_json
    - cautions
    """
    proposal = ScoreProfileProposal.objects.create(
        score_profile=profile,
        proposal_name=build_proposal_name(profile),
        status=ScoreProfileProposal.STATUS_DRAFT,
        score_profile_name_snapshot=profile.name,
        score_profile_version_snapshot=profile.version,
        source_filters_json=dict(filters),
        analysis_summary=str(ai_result.get("analysis_summary", "")),
        issues_json=ai_result.get("issues", []),
        improvement_hypotheses_json=ai_result.get("improvement_hypotheses", []),
        suggested_weights_json=ai_result.get("suggested_weights_json", {}),
        suggested_thresholds_json=ai_result.get("suggested_thresholds_json", {}),
        cautions_json=ai_result.get("cautions", []),
        raw_ai_response_json=ai_result,
    )
    return proposal

