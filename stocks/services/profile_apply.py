from __future__ import annotations

from datetime import datetime

from django.core.exceptions import ValidationError

from ..models import ScoreProfile, ScoreProfileProposal


def _build_profile_name(proposal: ScoreProfileProposal) -> str:
    base = proposal.score_profile_name_snapshot or proposal.score_profile.name
    return f"{base} derived from proposal {proposal.id}"


def _build_profile_version(proposal: ScoreProfileProposal) -> str:
    ts = datetime.utcnow().isoformat(timespec="seconds")
    return f"from-proposal-{proposal.id}-{ts}"


def _validate_suggested_payload(proposal: ScoreProfileProposal) -> None:
    weights = proposal.suggested_weights_json
    thresholds = proposal.suggested_thresholds_json

    # 入力不正は ValueError で表現し、ビュー側で 400 にマッピングする
    if not isinstance(weights, dict) or not weights:
        raise ValueError("suggested_weights_json must be a non-empty object.")

    if not isinstance(thresholds, dict) or not thresholds:
        raise ValueError("suggested_thresholds_json must be a non-empty object.")


def apply_proposal_to_new_profile(proposal: ScoreProfileProposal) -> ScoreProfile:
    """
    accepted 済み proposal から新しい ScoreProfile を生成し、proposal.applied_score_profile に紐付ける。
    """
    if proposal.status != ScoreProfileProposal.STATUS_ACCEPTED:
        raise ValidationError(f"Proposal status must be 'accepted', got '{proposal.status}'.")

    if proposal.applied_score_profile is not None:
        raise ValidationError("This proposal already has an applied_score_profile.")

    _validate_suggested_payload(proposal)

    name = _build_profile_name(proposal)
    version = _build_profile_version(proposal)

    description_lines = [
        f"Generated from proposal id={proposal.id}.",
        f"Source profile snapshot: {proposal.score_profile_name_snapshot} ({proposal.score_profile_version_snapshot}).",
        "Origin: AI review suggested_weights_json and suggested_thresholds_json.",
    ]
    description = "\n".join(description_lines)

    profile = ScoreProfile.objects.create(
        name=name,
        version=version,
        is_active=False,
        description=description,
        weights_json=proposal.suggested_weights_json,
        thresholds_json=proposal.suggested_thresholds_json,
    )

    proposal.applied_score_profile = profile
    proposal.save(update_fields=["applied_score_profile", "updated_at"])

    return profile

