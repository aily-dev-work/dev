"""
フェーズ20: 運用向け ops-summary service。
review-targets の結果を集約し、通知本文に流用しやすい summary を返す。
"""
from __future__ import annotations

from typing import Any, Dict

from django.utils import timezone

from .profile_review_targets import get_review_targets


def build_ops_summary(
    *,
    signal_date_from: str | None = None,
    signal_date_to: str | None = None,
    threshold_success_rate: float,
    stale_days: int,
    min_evaluated_count: int,
) -> Dict[str, Any]:
    """
    review-targets の結果をもとに運用向け summary を構築する。
    """
    targets = get_review_targets(
        signal_date_from=signal_date_from,
        signal_date_to=signal_date_to,
        threshold_success_rate=threshold_success_rate,
        stale_days=stale_days,
        min_evaluated_count=min_evaluated_count,
    )

    stale = targets.get("stale_active_profiles") or []
    under = targets.get("underperforming_profiles") or []
    accepted = targets.get("accepted_not_activated_profiles") or []

    counts = {
        "stale_active_count": len(stale),
        "underperforming_count": len(under),
        "accepted_not_activated_count": len(accepted),
    }

    current = targets.get("current_active_profile")

    message_lines: list[str] = []

    if current:
        message_lines.append(
            f"Active profile: {current.get('name')} {current.get('version')} (id={current.get('id')})"
        )
    else:
        message_lines.append("No active profile configured.")

    # counts を英語の短い文でサマリ
    if counts["stale_active_count"] == 0:
        message_lines.append("No stale active profiles.")
    else:
        n = counts["stale_active_count"]
        suffix = "profile" if n == 1 else "profiles"
        message_lines.append(f"{n} stale active {suffix} found.")
        ids = ", ".join(str(p.get("id")) for p in stale)
        message_lines.append(f"Stale active profile ids: {ids}.")

    if counts["underperforming_count"] == 0:
        message_lines.append("No underperforming profiles.")
    else:
        n = counts["underperforming_count"]
        suffix = "profile" if n == 1 else "profiles"
        message_lines.append(f"{n} underperforming {suffix} found.")
        ids = ", ".join(str(p.get("id")) for p in under)
        message_lines.append(f"Underperforming profile ids: {ids}.")

    if counts["accepted_not_activated_count"] == 0:
        message_lines.append("No accepted but not activated proposal-derived profiles.")
    else:
        n = counts["accepted_not_activated_count"]
        suffix = "profile" if n == 1 else "profiles"
        message_lines.append(
            f"{n} accepted but not activated proposal-derived {suffix} found."
        )
        ids = ", ".join(str(p.get("id")) for p in accepted)
        message_lines.append(f"Accepted but not activated profile ids: {ids}.")

    return {
        "generated_at": timezone.now().isoformat(),
        "current_active_profile": current,
        "stale_active_profiles": stale,
        "underperforming_profiles": under,
        "accepted_not_activated_profiles": accepted,
        "counts": counts,
        "message_lines": message_lines,
    }

