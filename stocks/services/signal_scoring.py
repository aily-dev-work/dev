from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional

from .technical_analysis import TechnicalSummary


@dataclass
class ScoreResult:
    buy_score: float
    sell_score: float
    breakdown_buy: Dict[str, float]
    breakdown_sell: Dict[str, float]
    insufficient_data: bool
    insufficient_reason: Optional[str]


def _clamp(score: float, min_value: float = 0.0, max_value: float = 100.0) -> float:
    return max(min(score, max_value), min_value)


# 初版の重み定義（後で調整しやすいようにまとめておく）
BUY_WEIGHTS: Dict[str, float] = {
    "trend_long_up": 20.0,
    "trend_mid_up": 15.0,
    "trend_short_up": 10.0,
    "volume_high": 10.0,
    "above_ma25": 10.0,
    "above_ma75": 10.0,
    "near_high_20": 10.0,
}

SELL_WEIGHTS: Dict[str, float] = {
    "trend_long_down": 20.0,
    "trend_mid_down": 15.0,
    "trend_short_down": 10.0,
    "volume_low": 10.0,
    "below_ma25": 10.0,
    "below_ma75": 10.0,
    "near_low_20": 10.0,
}


def score_from_technical(summary: TechnicalSummary) -> ScoreResult:
    """
    フェーズ3の TechnicalSummary から買い/売りスコアを計算する。
    データ不足の場合でも 0〜100 の範囲でスコアを返しつつ、insufficient_data フラグを立てる。
    """
    breakdown_buy: Dict[str, float] = {}
    breakdown_sell: Dict[str, float] = {}
    insufficient_reasons = []

    signals = summary.signals
    ma = summary.moving_averages
    hl = summary.high_low
    latest_close: Optional[Decimal] = summary.latest_close

    # ---------- トレンド系 ----------
    # long
    if signals.trend_long == "up":
        breakdown_buy["trend_long_up"] = BUY_WEIGHTS["trend_long_up"]
    else:
        breakdown_buy["trend_long_up"] = 0.0
    if signals.trend_long == "down":
        breakdown_sell["trend_long_down"] = SELL_WEIGHTS["trend_long_down"]
    else:
        breakdown_sell["trend_long_down"] = 0.0

    # mid
    if signals.trend_mid == "up":
        breakdown_buy["trend_mid_up"] = BUY_WEIGHTS["trend_mid_up"]
    else:
        breakdown_buy["trend_mid_up"] = 0.0
    if signals.trend_mid == "down":
        breakdown_sell["trend_mid_down"] = SELL_WEIGHTS["trend_mid_down"]
    else:
        breakdown_sell["trend_mid_down"] = 0.0

    # short
    if signals.trend_short == "up":
        breakdown_buy["trend_short_up"] = BUY_WEIGHTS["trend_short_up"]
    else:
        breakdown_buy["trend_short_up"] = 0.0
    if signals.trend_short == "down":
        breakdown_sell["trend_short_down"] = SELL_WEIGHTS["trend_short_down"]
    else:
        breakdown_sell["trend_short_down"] = 0.0

    # ---------- 出来高 ----------
    if signals.volume_trend == "high":
        breakdown_buy["volume_high"] = BUY_WEIGHTS["volume_high"]
    else:
        breakdown_buy["volume_high"] = 0.0

    if signals.volume_trend == "low":
        breakdown_sell["volume_low"] = SELL_WEIGHTS["volume_low"]
    else:
        breakdown_sell["volume_low"] = 0.0

    if signals.volume_trend is None:
        insufficient_reasons.append("volume_trend_missing")

    # ---------- 移動平均との位置関係 ----------
    # ma25
    if latest_close is not None and ma.ma25 is not None:
        if latest_close > ma.ma25:
            breakdown_buy["above_ma25"] = BUY_WEIGHTS["above_ma25"]
            breakdown_sell["below_ma25"] = 0.0
        elif latest_close < ma.ma25:
            breakdown_sell["below_ma25"] = SELL_WEIGHTS["below_ma25"]
            breakdown_buy["above_ma25"] = 0.0
        else:
            breakdown_buy["above_ma25"] = 0.0
            breakdown_sell["below_ma25"] = 0.0
    else:
        breakdown_buy["above_ma25"] = 0.0
        breakdown_sell["below_ma25"] = 0.0
        insufficient_reasons.append("ma25_or_latest_missing")

    # ma75
    if latest_close is not None and ma.ma75 is not None:
        if latest_close > ma.ma75:
            breakdown_buy["above_ma75"] = BUY_WEIGHTS["above_ma75"]
            breakdown_sell["below_ma75"] = 0.0
        elif latest_close < ma.ma75:
            breakdown_sell["below_ma75"] = SELL_WEIGHTS["below_ma75"]
            breakdown_buy["above_ma75"] = 0.0
        else:
            breakdown_buy["above_ma75"] = 0.0
            breakdown_sell["below_ma75"] = 0.0
    else:
        breakdown_buy["above_ma75"] = 0.0
        breakdown_sell["below_ma75"] = 0.0
        insufficient_reasons.append("ma75_or_latest_missing")

    # ---------- 20日高値・安値との位置関係 ----------
    # high_20 付近に近づいている（上昇基調） → 買い加点
    # low_20 付近に近づきそう（弱い） → 売り加点
    if latest_close is not None and hl.high_20 is not None and hl.low_20 is not None:
        price_range = hl.high_20 - hl.low_20
        if price_range > 0:
            # 0〜1 のレンジに正規化（low_20:0, high_20:1）
            pos = float((latest_close - hl.low_20) / price_range)
            # high_20 の 70%以上の位置 → 「高値圏に近い」とみなす
            if pos >= 0.7:
                breakdown_buy["near_high_20"] = BUY_WEIGHTS["near_high_20"]
            else:
                breakdown_buy["near_high_20"] = 0.0
            # low_20 の 30%未満の位置 → 「安値圏に近い」とみなす
            if pos <= 0.3:
                breakdown_sell["near_low_20"] = SELL_WEIGHTS["near_low_20"]
            else:
                breakdown_sell["near_low_20"] = 0.0
        else:
            breakdown_buy["near_high_20"] = 0.0
            breakdown_sell["near_low_20"] = 0.0
            insufficient_reasons.append("high_low_range_zero")
    else:
        breakdown_buy["near_high_20"] = 0.0
        breakdown_sell["near_low_20"] = 0.0
        insufficient_reasons.append("high_20_or_low_20_or_latest_missing")

    # 合計スコア計算＆クランプ
    raw_buy = sum(breakdown_buy.values())
    raw_sell = sum(breakdown_sell.values())

    buy_score = _clamp(raw_buy)
    sell_score = _clamp(raw_sell)

    insufficient_data = len(insufficient_reasons) > 0
    reason_text = ", ".join(sorted(set(insufficient_reasons))) if insufficient_reasons else None

    return ScoreResult(
        buy_score=buy_score,
        sell_score=sell_score,
        breakdown_buy=breakdown_buy,
        breakdown_sell=breakdown_sell,
        insufficient_data=insufficient_data,
        insufficient_reason=reason_text,
    )

