from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ..models import TradingSignal, WatchStock
from .scoring_profile import get_active_score_profile
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

    # 20日レンジ内での位置（technical_position）
    technical_position: Optional[Decimal]
    if (
        summary.latest_close is not None
        and summary.high_low.high_20 is not None
        and summary.high_low.low_20 is not None
    ):
        range_span = summary.high_low.high_20 - summary.high_low.low_20
        if range_span and range_span != 0:
            technical_position = (summary.latest_close - summary.high_low.low_20) / range_span
        else:
            technical_position = None
    else:
        technical_position = None

    # 使用した ScoreProfile を取得（フェーズ8の active profile）
    profile = get_active_score_profile()

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
        "technical_position": _decimal_or_none(technical_position),
        "trend_short": summary.signals.trend_short,
        "trend_mid": summary.signals.trend_mid,
        "trend_long": summary.signals.trend_long,
        "volume_trend": summary.signals.volume_trend,
        "score_profile": profile,
        "score_profile_name": profile.name,
        "score_profile_version": profile.version,
    }

    signal, _created = TradingSignal.objects.update_or_create(
        stock=stock,
        signal_date=signal_date,
        signal_datetime=None,
        defaults=defaults,
    )
    return signal


def generate_trading_signal_5m(
    stock: WatchStock,
    summary: TechnicalSummary,
    score: ScoreResult,
    signal_datetime: datetime,
) -> TradingSignal:
    """
    5分足テクニカルサマリとスコアから TradingSignal を生成・保存する（intraday 用）。
    同一 (stock, signal_date, signal_datetime) があれば更新。signal_datetime は 5 分足の
    バー開始時刻に揃えておくこと（同 5 分枠内の重複実行で上書きされる）。
    """
    if summary.latest_date:
        signal_date = date.fromisoformat(summary.latest_date)
    else:
        signal_date = signal_datetime.date()

    if score.bias == "buy":
        signal_type = "buy"
    elif score.bias == "sell":
        signal_type = "sell"
    else:
        signal_type = "neutral"

    technical_position: Optional[Decimal]
    if (
        summary.latest_close is not None
        and summary.high_low.high_20 is not None
        and summary.high_low.low_20 is not None
    ):
        range_span = summary.high_low.high_20 - summary.high_low.low_20
        if range_span and range_span != 0:
            technical_position = (summary.latest_close - summary.high_low.low_20) / range_span
        else:
            technical_position = None
    else:
        technical_position = None

    profile = get_active_score_profile()

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
        "technical_position": _decimal_or_none(technical_position),
        "trend_short": summary.signals.trend_short,
        "trend_mid": summary.signals.trend_mid,
        "trend_long": summary.signals.trend_long,
        "volume_trend": summary.signals.volume_trend,
        "score_profile": profile,
        "score_profile_name": profile.name,
        "score_profile_version": profile.version,
    }

    signal, _created = TradingSignal.objects.update_or_create(
        stock=stock,
        signal_date=signal_date,
        signal_datetime=signal_datetime,
        defaults=defaults,
    )
    return signal

