from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from django.db.models import Q

from ..models import SignalOutcome, TradingSignal


def _str_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _iso_or_none(d) -> Optional[str]:
    if d is None:
        return None
    return d.isoformat()


def build_signal_queryset(params) -> Iterable[TradingSignal]:
    """
    TradingSignal + SignalOutcome を結合した一覧用 QuerySet を返す。
    フィルタは QueryDict (request.query_params) を想定。
    """
    qs = TradingSignal.objects.select_related("stock", "outcome").all()

    stock_id = params.get("stock")
    ticker = params.get("ticker")
    signal_type = params.get("signal_type")
    score_bias = params.get("score_bias")
    score_strength = params.get("score_strength")
    eval_status = params.get("eval_status")
    date_from = params.get("signal_date_from")
    date_to = params.get("signal_date_to")

    if stock_id:
        qs = qs.filter(stock_id=stock_id)
    if ticker:
        qs = qs.filter(stock__ticker=ticker)
    if signal_type:
        qs = qs.filter(signal_type=signal_type)
    if score_bias:
        qs = qs.filter(score_bias=score_bias)
    if score_strength:
        qs = qs.filter(score_strength=score_strength)
    if eval_status:
        if eval_status == "pending":
            # pending の場合は outcome 未作成も含める
            qs = qs.filter(Q(outcome__eval_status="pending") | Q(outcome__isnull=True))
        else:
            qs = qs.filter(outcome__eval_status=eval_status)

    if date_from:
        qs = qs.filter(signal_date__gte=date_from)
    if date_to:
        qs = qs.filter(signal_date__lte=date_to)

    # デフォルト: signal_date 降順, created_at 降順
    qs = qs.order_by("-signal_date", "-created_at")
    return qs


def signals_to_dataset(signals: Iterable[TradingSignal]) -> List[Dict[str, Any]]:
    """
    1シグナル=1行のフラットな dict に展開する。
    """
    rows: List[Dict[str, Any]] = []

    for s in signals:
        o: Optional[SignalOutcome]
        try:
            o = s.outcome  # type: ignore[attr-defined]
        except SignalOutcome.DoesNotExist:  # type: ignore[attr-defined]
            o = None

        if o is None:
            eval_status = "pending"
        else:
            eval_status = o.eval_status

        row: Dict[str, Any] = {
            "signal_id": s.id,
            "stock_id": s.stock.id,
            "ticker": s.stock.ticker,
            "name": s.stock.name,
            "signal_date": _iso_or_none(s.signal_date),
            "signal_type": s.signal_type,
            "buy_score": float(s.buy_score),
            "sell_score": float(s.sell_score),
            "score_bias": s.score_bias,
            "score_strength": s.score_strength,
            "signal_price": _str_or_none(s.signal_price),
            "latest_close": _str_or_none(s.latest_close),
            "ma25": _str_or_none(s.ma25),
            "ma75": _str_or_none(s.ma75),
            "high_20": _str_or_none(s.high_20),
            "low_20": _str_or_none(s.low_20),
            "technical_position": _str_or_none(s.technical_position),
            "trend_short": s.trend_short,
            "trend_mid": s.trend_mid,
            "trend_long": s.trend_long,
            "volume_trend": s.volume_trend,
            "base_price": _str_or_none(o.base_price) if o else None,
            "eval_status": eval_status,
            "date_5d": _iso_or_none(o.date_5d) if o else None,
            "close_5d": _str_or_none(o.close_5d) if o else None,
            "return_5d": _str_or_none(o.return_5d) if o else None,
            "success_5d": o.success_5d if o else None,
            "date_10d": _iso_or_none(o.date_10d) if o else None,
            "close_10d": _str_or_none(o.close_10d) if o else None,
            "return_10d": _str_or_none(o.return_10d) if o else None,
            "success_10d": o.success_10d if o else None,
            "date_20d": _iso_or_none(o.date_20d) if o else None,
            "close_20d": _str_or_none(o.close_20d) if o else None,
            "return_20d": _str_or_none(o.return_20d) if o else None,
            "success_20d": o.success_20d if o else None,
            "signal_created_at": _iso_or_none(s.created_at),
            "outcome_updated_at": _iso_or_none(o.updated_at) if o else None,
        }
        rows.append(row)

    return rows

