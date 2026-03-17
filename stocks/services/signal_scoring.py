from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional

from .scoring_profile import get_active_scoring_config
from .technical_analysis import TechnicalSummary


@dataclass
class ScoreResult:
    buy_score: float
    sell_score: float
    breakdown_buy: Dict[str, float]
    breakdown_sell: Dict[str, float]
    insufficient_data: bool
    insufficient_reason: Optional[str]
    bias: str
    strength: str


def _clamp(score: float, min_value: float = 0.0, max_value: float = 100.0) -> float:
    return max(min(score, max_value), min_value)


def score_from_technical(summary: TechnicalSummary) -> ScoreResult:
    """
    TechnicalSummary から買い/売りスコアを計算する。
    重み・閾値は ScoreProfile（DB）のアクティブ設定から取得する。
    """
    config = get_active_scoring_config()
    buy_weights = config.buy_weights
    sell_weights = config.sell_weights
    bias_thresholds = config.bias_thresholds
    strength_thresholds = config.strength_thresholds

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
        breakdown_buy["trend_long_up"] = buy_weights.get("trend_long_up", 0.0)
    else:
        breakdown_buy["trend_long_up"] = 0.0
    if signals.trend_long == "down":
        breakdown_sell["trend_long_down"] = sell_weights.get("trend_long_down", 0.0)
    else:
        breakdown_sell["trend_long_down"] = 0.0

    # mid
    if signals.trend_mid == "up":
        breakdown_buy["trend_mid_up"] = buy_weights.get("trend_mid_up", 0.0)
    else:
        breakdown_buy["trend_mid_up"] = 0.0
    if signals.trend_mid == "down":
        breakdown_sell["trend_mid_down"] = sell_weights.get("trend_mid_down", 0.0)
    else:
        breakdown_sell["trend_mid_down"] = 0.0

    # short
    if signals.trend_short == "up":
        breakdown_buy["trend_short_up"] = buy_weights.get("trend_short_up", 0.0)
    else:
        breakdown_buy["trend_short_up"] = 0.0
    if signals.trend_short == "down":
        breakdown_sell["trend_short_down"] = sell_weights.get("trend_short_down", 0.0)
    else:
        breakdown_sell["trend_short_down"] = 0.0

    # ---------- 出来高 ----------
    # 買い側の出来高シグナル: 上昇系トレンド + 出来高増加のときのみ加点（長期順張り寄り）
    if (
        signals.volume_trend == "high"
        and (
            signals.trend_long == "up"
            or signals.trend_mid == "up"
            or signals.trend_short == "up"
        )
    ):
        breakdown_buy["volume_high"] = buy_weights.get("volume_high", 0.0)
    else:
        breakdown_buy["volume_high"] = 0.0

    # 売り側の出来高シグナル: 出来高が少ないとき（長期順張り初期値では weight=0 として非推奨扱い）
    if signals.volume_trend == "low":
        breakdown_sell["volume_low"] = sell_weights.get("volume_low", 0.0)
    else:
        breakdown_sell["volume_low"] = 0.0

    if signals.volume_trend is None:
        insufficient_reasons.append("volume_trend_missing")

    # ---------- 移動平均との位置関係 ----------
    # ma25
    if latest_close is not None and ma.ma25 is not None:
        if latest_close > ma.ma25:
            breakdown_buy["above_ma25"] = buy_weights.get("above_ma25", 0.0)
            breakdown_sell["below_ma25"] = 0.0
        elif latest_close < ma.ma25:
            breakdown_sell["below_ma25"] = sell_weights.get("below_ma25", 0.0)
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
            breakdown_buy["above_ma75"] = buy_weights.get("above_ma75", 0.0)
            breakdown_sell["below_ma75"] = 0.0
        elif latest_close < ma.ma75:
            breakdown_sell["below_ma75"] = sell_weights.get("below_ma75", 0.0)
            breakdown_buy["above_ma75"] = 0.0
        else:
            breakdown_buy["above_ma75"] = 0.0
            breakdown_sell["below_ma75"] = 0.0
    else:
        breakdown_buy["above_ma75"] = 0.0
        breakdown_sell["below_ma75"] = 0.0
        insufficient_reasons.append("ma75_or_latest_missing")

    # ---------- 20日高値・安値との位置関係 ----------
    # 高値圏（high_20 付近）は利確・売り警戒 → 売り加点
    # 安値圏（low_20 付近）は反発期待 → 買い加点
    if latest_close is not None and hl.high_20 is not None and hl.low_20 is not None:
        price_range = hl.high_20 - hl.low_20
        if price_range > 0:
            # 0〜1 のレンジに正規化（low_20:0, high_20:1）
            pos = float((latest_close - hl.low_20) / price_range)
            # high_20 の 80%以上の位置 → 「高値圏に近い」とみなす → 売り加点
            if pos >= 0.8:
                breakdown_sell["near_high_20"] = sell_weights.get("near_high_20", 0.0)
            else:
                breakdown_sell["near_high_20"] = 0.0
            # low_20 の 20%未満の位置 → 「安値圏に近い」とみなす → 買い加点
            if pos <= 0.2:
                breakdown_buy["near_low_20"] = buy_weights.get("near_low_20", 0.0)
            else:
                breakdown_buy["near_low_20"] = 0.0
        else:
            breakdown_buy["near_low_20"] = 0.0
            breakdown_sell["near_high_20"] = 0.0
            insufficient_reasons.append("high_low_range_zero")
    else:
        breakdown_buy["near_low_20"] = 0.0
        breakdown_sell["near_high_20"] = 0.0
        insufficient_reasons.append("high_20_or_low_20_or_latest_missing")

    # 合計スコア計算（割合: 当てはまった重みの合計 / 重み全体の合計 × 100）
    raw_buy = sum(breakdown_buy.values())
    raw_sell = sum(breakdown_sell.values())
    total_buy = sum(buy_weights.values()) or 1.0
    total_sell = sum(sell_weights.values()) or 1.0

    buy_score = _clamp(100.0 * raw_buy / total_buy)
    sell_score = _clamp(100.0 * raw_sell / total_sell)

    # バイアスと強度を判定
    diff = buy_score - sell_score
    abs_diff = abs(diff)

    neutral_abs_diff_lt = float(bias_thresholds.get("neutral_abs_diff_lt", 10.0))
    if abs_diff < neutral_abs_diff_lt:
        bias = "neutral"
    elif diff >= neutral_abs_diff_lt:
        bias = "buy"
    else:
        bias = "sell"

    weak_abs_diff_lt = float(strength_thresholds.get("weak_abs_diff_lt", 15.0))
    normal_abs_diff_lt = float(strength_thresholds.get("normal_abs_diff_lt", 30.0))

    if abs_diff < weak_abs_diff_lt:
        strength = "weak"
    elif abs_diff < normal_abs_diff_lt:
        strength = "normal"
    else:
        strength = "strong"

    insufficient_data = len(insufficient_reasons) > 0
    reason_text = ", ".join(sorted(set(insufficient_reasons))) if insufficient_reasons else None

    return ScoreResult(
        buy_score=buy_score,
        sell_score=sell_score,
        breakdown_buy=breakdown_buy,
        breakdown_sell=breakdown_sell,
        insufficient_data=insufficient_data,
        insufficient_reason=reason_text,
        bias=bias,
        strength=strength,
    )

