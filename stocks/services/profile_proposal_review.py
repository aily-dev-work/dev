from __future__ import annotations

from typing import Literal

from django.core.exceptions import ValidationError

from ..models import ScoreProfileProposal

AllowedStatus = Literal[
    ScoreProfileProposal.STATUS_DRAFT,
    ScoreProfileProposal.STATUS_REVIEWED,
    ScoreProfileProposal.STATUS_ACCEPTED,
    ScoreProfileProposal.STATUS_REJECTED,
]


def validate_status(value: str) -> None:
    allowed = {
        ScoreProfileProposal.STATUS_DRAFT,
        ScoreProfileProposal.STATUS_REVIEWED,
        ScoreProfileProposal.STATUS_ACCEPTED,
        ScoreProfileProposal.STATUS_REJECTED,
    }
    if value not in allowed:
        raise ValidationError(f"Invalid status: {value}")


def can_delete(proposal: ScoreProfileProposal) -> bool:
    """
    削除ルール:
    - draft: 削除可
    - rejected: 削除可
    - reviewed: 削除不可
    - accepted: 削除不可
    """
    return proposal.status in {
        ScoreProfileProposal.STATUS_DRAFT,
        ScoreProfileProposal.STATUS_REJECTED,
    }


def update_review_fields(
    proposal: ScoreProfileProposal,
    *,
    status: str | None = None,
    review_note: str | None = None,
) -> ScoreProfileProposal:
    """
    status / review_note のみを更新する。
    その他のフィールドはこの層では一切変更しない。
    """
    if status is not None:
        validate_status(status)
        proposal.status = status

    if review_note is not None:
        proposal.review_note = review_note

    proposal.save(update_fields=["status", "review_note", "updated_at"])
    return proposal

