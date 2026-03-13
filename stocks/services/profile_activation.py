from __future__ import annotations

from django.db import transaction

from ..models import ScoreProfile


@transaction.atomic
def activate_score_profile(profile: ScoreProfile) -> ScoreProfile:
    """
    指定された ScoreProfile を active にし、それ以外の active プロファイルを inactive にする。

    - すでに profile.is_active=True の場合も冪等に動作し、最終的に active はこの1件だけになる。
    """
    # 他の active プロファイルをすべて off にする
    ScoreProfile.objects.filter(is_active=True).exclude(id=profile.id).update(is_active=False)

    if not profile.is_active:
        profile.is_active = True
        profile.save(update_fields=["is_active", "updated_at"])

    return profile

