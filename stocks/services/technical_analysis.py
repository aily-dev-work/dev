from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from ..models import StockPriceDaily, WatchStock


@dataclass
class MovingAverages:
    ma5: Optional[Decimal]
    ma25: Optional[Decimal]
    ma75: Optional[Decimal]


@dataclass
class HighLow:
    high_20: Optional[Decimal]
    low_20: Optional[Decimal]


@dataclass
class AverageVolume:
    avg_volume_5: Optional[float]
    avg_volume_20: Optional[float]


@dataclass
class TechnicalSignals:
    trend_short: Optional[str]
    trend_mid: Optional[str]
    trend_long: Optional[str]
    volume_trend: Optional[str]


@dataclass
class TechnicalSummary:
    stock: WatchStock
    latest_date: Optional[str]
    latest_close: Optional[Decimal]
    moving_averages: MovingAverages
    high_low: HighLow
    average_volume: AverageVolume
    signals: TechnicalSignals


def _decimal_or_none(values: Iterable[Decimal]) -> Optional[Decimal]:
    items = list(values)
    if not items:
        return None
    return sum(items) / len(items)


def _float_or_none(values: Iterable[Optional[int]]) -> Optional[float]:
    cleaned = [v for v in values if v is not None]
    if not cleaned:
    return None
    return float(sum(cleaned) / len(cleaned))


def calculate_technical_summary(stock: WatchStock) -> TechnicalSummary:
    """
    指定した WatchStock について、日足データからテクニカル指標を集計する。
    データが足りない指標は None を返す。
    """
    # ordering = ["-date", "-updated_at"] なので、新しい順に取得される
    qs = StockPriceDaily.objects.filter(stock=stock).order_by("-date")

    prices = list(qs[: max(75, 20)])  # 最大 75 日分あれば十分

    if not prices:
        empty_ma = MovingAverages(ma5=None, ma25=None, ma75=None)
        empty_hl = HighLow(high_20=None, low_20=None)
        empty_vol = AverageVolume(avg_volume_5=None, avg_volume_20=None)
        empty_sig = TechnicalSignals(
            trend_short=None,
            trend_mid=None,
            trend_long=None,
            volume_trend=None,
        )
        return TechnicalSummary(
            stock=stock,
            latest_date=None,
            latest_close=None,
            moving_averages=empty_ma,
            high_low=empty_hl,
            average_volume=empty_vol,
            signals=empty_sig,
        )

    latest = prices[0]
    closes = [p.close_price for p in prices]

    # 移動平均
    ma5 = _decimal_or_none(closes[:5]) if len(closes) >= 5 else None
    ma25 = _decimal_or_none(closes[:25]) if len(closes) >= 25 else None
    ma75 = _decimal_or_none(closes[:75]) if len(closes) >= 75 else None

    moving_averages = MovingAverages(ma5=ma5, ma25=ma25, ma75=ma75)

    # 直近20営業日の高値・安値（OHLC の high/low ベース）
    high_prices_20 = [p.high_price for p in prices[:20]]
    low_prices_20 = [p.low_price for p in prices[:20]]

    high_20 = max(high_prices_20) if high_prices_20 else None
    low_20 = min(low_prices_20) if low_prices_20 else None

    high_low = HighLow(high_20=high_20, low_20=low_20)

    # 出来高平均
    volumes = [p.volume for p in prices]
    avg_volume_5 = _float_or_none(volumes[:5]) if len(volumes) >= 1 else None
    avg_volume_20 = _float_or_none(volumes[:20]) if len(volumes) >= 1 else None

    average_volume = AverageVolume(
        avg_volume_5=avg_volume_5,
        avg_volume_20=avg_volume_20,
    )

    # シンプルなトレンド判定
    latest_close = latest.close_price

    def _trend(ma: Optional[Decimal]) -> Optional[str]:
        if ma is None:
            return None
        if latest_close > ma:
            return "up"
        if latest_close < ma:
            return "down"
        return "flat"

    trend_short = _trend(ma5)
    trend_mid = _trend(ma25)
    trend_long = _trend(ma75)

    # 出来高トレンド: 5日平均 vs 20日平均
    if avg_volume_5 is None or avg_volume_20 is None or avg_volume_20 == 0:
        volume_trend = None
    else:
        ratio = avg_volume_5 / avg_volume_20
        if ratio >= 1.5:
            volume_trend = "high"
        elif ratio <= 0.5:
            volume_trend = "low"
        else:
            volume_trend = "normal"

    signals = TechnicalSignals(
        trend_short=trend_short,
        trend_mid=trend_mid,
        trend_long=trend_long,
        volume_trend=volume_trend,
    )

    return TechnicalSummary(
        stock=stock,
        latest_date=str(latest.date),
        latest_close=latest_close,
        moving_averages=moving_averages,
        high_low=high_low,
        average_volume=average_volume,
        signals=signals,
    )

