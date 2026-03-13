from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from ..models import SignalOutcome, StockPriceDaily, TradingSignal


@dataclass
class HorizonResult:
    date: Optional[str]
    close: Optional[Decimal]
    ret: Optional[Decimal]
    success: Optional[bool]


def _compute_return(base: Optional[Decimal], close: Optional[Decimal]) -> Optional[Decimal]:
    if base is None or close is None or base == 0:
        return None
    return (close - base) / base


def _success(signal_type: str, ret: Optional[Decimal]) -> Optional[bool]:
    if ret is None:
        return None
    if signal_type == "buy":
        return ret > 0
    if signal_type == "sell":
        return ret < 0
    # neutral は判定しない
    return None


def evaluate_signal(signal: TradingSignal) -> SignalOutcome:
    """
    TradingSignal を評価して SignalOutcome を生成・更新する。
    - signal_date より後の StockPriceDaily を使って 5/10/20 営業日後を評価
    """
    base_price: Optional[Decimal] = signal.signal_price or signal.latest_close

    qs = (
        StockPriceDaily.objects.filter(stock=signal.stock, date__gt=signal.signal_date)
        .order_by("date")
    )
    days = list(qs)

    def _pick(idx: int) -> Optional[StockPriceDaily]:
        return days[idx] if len(days) > idx else None

    h5 = _pick(4)
    h10 = _pick(9)
    h20 = _pick(19)

    def _horizon(h: Optional[StockPriceDaily]) -> HorizonResult:
        if h is None:
            return HorizonResult(None, None, None, None)
        close = h.close_price
        ret = _compute_return(base_price, close)
        succ = _success(signal.signal_type, ret)
        return HorizonResult(h.date.isoformat(), close, ret, succ)

    r5 = _horizon(h5)
    r10 = _horizon(h10)
    r20 = _horizon(h20)

    # eval_status 判定: return_* の有無を基準にする
    has_5 = r5.ret is not None
    has_10 = r10.ret is not None
    has_20 = r20.ret is not None
    any_ret = has_5 or has_10 or has_20
    all_ret = has_5 and has_10 and has_20

    if not any_ret:
        eval_status = "pending"
    elif all_ret:
        eval_status = "completed"
    else:
        eval_status = "partial"

    outcome, _created = SignalOutcome.objects.update_or_create(
        signal=signal,
        defaults={
            "base_price": base_price,
            "eval_status": eval_status,
            "date_5d": h5.date if h5 else None,
            "close_5d": r5.close,
            "return_5d": r5.ret,
            "success_5d": r5.success,
            "date_10d": h10.date if h10 else None,
            "close_10d": r10.close,
            "return_10d": r10.ret,
            "success_10d": r10.success,
            "date_20d": h20.date if h20 else None,
            "close_20d": r20.close,
            "return_20d": r20.ret,
            "success_20d": r20.success,
        },
    )
    return outcome

