"""
トレードスタイルに応じた評価期間（horizon）の選択。
成功率・平均リターンの算出に、デイトレ=5営業日・短期=10営業日・長期=20営業日を使う。
"""
from __future__ import annotations

from typing import Tuple

from ..models import ScoreProfile


def get_horizon_key_and_days(profile: ScoreProfile) -> Tuple[str, int]:
    """
    プロファイルの trading_style に応じた horizon キーと営業日数を返す。
    - day_trade → h5 (5営業日)
    - short_term → h10 (10営業日)
    - long_term → h20 (20営業日)
    未設定・不明な場合は short_term として h10 を返す。
    """
    style = getattr(profile, "trading_style", None) or "short_term"
    if style == "day_trade":
        return ("h5", 5)
    if style == "long_term":
        return ("h20", 20)
    return ("h10", 10)  # short_term 既定
