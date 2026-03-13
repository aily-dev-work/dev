from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from ..models import TradingSignal, WatchStock
from .signal_scoring import ScoreResult
from .technical_analysis import TechnicalSummary


def _decimal_or_none(value: Optional[Decimal]) -> Optional[Decimal]:
    return value if value is not None else None


def generate_trading_signal(
    stock: WatchStock,
    summary: TechnicalSummary,
    score: ScoreResult,
) -> TradingSignal:
    """
    テクニカルサマリとスコアから TradingSignal を生成・保存する。
    同一 (stock, signal_date) があれば更新、なければ新規作成。
    """
    # signal_date は通常 latest_date。なければ本日の日付を使う。
    if summary.latest_date:
        signal_date = date.fromisoformat(summary.latest_date)
    else:
        signal_date = date.today()

    # バイアスからシグナル種別を決定
    if score.bias == "buy":
        signal_type = "buy"
    elif score.bias == "sell":
        signal_type = "sell"
    else:
        signal_type = "neutral"

    defaults = {
        "signal_type": signal_type,
        "buy_score": Decimal(str(score.buy_score)),
        "sell_score": Decimal(str(score.sell_score)),
        "score_bias": score.bias,
        "score_strength": score.strength,
        "signal_price": _decimal_or_none(summary.latest_close),
        "latest_close": _decimal_or_none(summary.latest_close),
        "ma25": _decimal_or_none(summary.moving_averages.ma25),
        "ma75": _decimal_or_none(summary.moving_averages.ma75),
        "high_20": _decimal_or_none(summary.high_low.high_20),
        "low_20": _decimal_or_none(summary.high_low.low_20),
        "trend_short": summary.signals.trend_short,
        "trend_mid": summary.signals.trend_mid,
        "trend_long": summary.signals.trend_long,
        "volume_trend": summary.signals.volume_trend,
    }

    signal, _created = TradingSignal.objects.update_or_create(
        stock=stock,
        signal_date=signal_date,
        defaults=defaults,
    )
    return signal

