"""
フェーズ18: 現在 active な ScoreProfile を直前の profile に手動ロールバックする service。
"""
from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured

from ..models import ScoreProfile, ScoreProfileActivationHistory
from .profile_activation import activate_score_profile
from .scoring_profile import get_active_score_profile


class RollbackNotAllowedError(Exception):
    """ロールバックが許可されない状態のときに送出する。API では 409 にマッピングする。"""
    pass


def rollback_to_previous_profile(note: str = "") -> ScoreProfile:
    """
    現在 active な ScoreProfile を、直近の activation history に基づいて
    直前の profile にロールバックする。

    - 現在 active が無い → RollbackNotAllowedError
    - 現在 active が activated_profile になっている直近履歴が無い → RollbackNotAllowedError
    - その履歴の previous_profile が null → RollbackNotAllowedError
    - 戻し先 profile を active にし、履歴に activation_reason="manual_rollback" で記録する。
    """
    try:
        current_active = get_active_score_profile()
    except ImproperlyConfigured:
        raise RollbackNotAllowedError(
            "No active ScoreProfile. Cannot rollback."
        ) from None

    latest_history = (
        ScoreProfileActivationHistory.objects.filter(
            activated_profile_id=current_active.id,
        )
        .order_by("-activated_at", "-id")
        .first()
    )

    if latest_history is None:
        raise RollbackNotAllowedError(
            "No activation history found for current active profile. Cannot rollback."
        )

    if latest_history.previous_profile_id is None:
        raise RollbackNotAllowedError(
            "Current profile was the first activation; there is no previous profile to rollback to."
        )

    target_profile = latest_history.previous_profile
    return activate_score_profile(
        target_profile,
        note=note or "",
        activation_reason="manual_rollback",
    )
