from __future__ import annotations

from django.db import transaction

from ..models import ScoreProfile, ScoreProfileActivationHistory, ScoreProfileProposal


@transaction.atomic
def activate_score_profile(
    profile: ScoreProfile,
    *,
    note: str = "",
    activation_reason: str = "manual_activate",
) -> ScoreProfile:
    """
    指定された ScoreProfile を active にし、それ以外の active プロファイルを inactive にする。

    - すでに profile.is_active=True の場合も冪等に動作し、最終的に active はこの1件だけになる。
    - フェーズ17: active 切替時に ScoreProfileActivationHistory を 1件自動作成する。
      - ただし「既に active だった profile を再 activate」するだけの場合は履歴を増やさない。
    """
    # 切り替え前に active だったプロファイル（初回は None 可）
    previous_active = (
        ScoreProfile.objects.filter(is_active=True)
        .exclude(id=profile.id)
        .order_by("-updated_at")
        .first()
    )

    was_active_before = bool(profile.is_active)

    # 他の active プロファイルをすべて off にする
    ScoreProfile.objects.filter(is_active=True).exclude(id=profile.id).update(
        is_active=False
    )

    if not profile.is_active:
        profile.is_active = True
        profile.save(update_fields=["is_active", "updated_at"])

    # すでに active だった profile を再 activate するだけの場合は履歴を増やさない
    if was_active_before and previous_active is None:
        return profile

    # proposal 由来の profile であれば可能な範囲で source_proposal を特定
    source_proposal = (
        ScoreProfileProposal.objects.filter(applied_score_profile=profile)
        .order_by("-created_at")
        .first()
    )

    ScoreProfileActivationHistory.objects.create(
        previous_profile=previous_active,
        activated_profile=profile,
        source_proposal=source_proposal,
        previous_profile_name_snapshot=previous_active.name if previous_active else "",
        previous_profile_version_snapshot=previous_active.version if previous_active else "",
        activated_profile_name_snapshot=profile.name,
        activated_profile_version_snapshot=profile.version,
        source_proposal_name_snapshot=(
            source_proposal.proposal_name if source_proposal else ""
        ),
        activation_reason=activation_reason,
        note=note or "",
    )

    return profile

