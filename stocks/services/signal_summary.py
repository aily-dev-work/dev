from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from ..models import SignalOutcome, TradingSignal


@dataclass
class HorizonSummary:
    evaluated_count: int
    success_count: int
    success_rate: Optional[float]
    avg_return: Optional[float]


@dataclass
class ProfileSignalSummary:
    score_profile_name: str
    score_profile_version: str
    signal_type: str
    total_signals: int
    h5: HorizonSummary
    h10: HorizonSummary
    h20: HorizonSummary


def _to_float(value: Optional[Decimal]) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def _horizon_summary(
    returns: List[Optional[Decimal]],
    successes: List[Optional[bool]],
    signal_type: str,
) -> HorizonSummary:
    """
    1つの horizon（5d/10d/20d）のサマリを計算する。
    - evaluated_count: return が非 None の件数
    - success_count: 「成功」判定の件数
    - success_rate: success_count / evaluated_count （evaluated_count=0 の場合は None）
    - avg_return: return の平均（evaluated_count=0 の場合は None）
    """
    evaluated_returns: List[Decimal] = []
    evaluated_success: List[bool] = []

    for r, s in zip(returns, successes):
        if r is None:
            continue
        evaluated_returns.append(r)
        # success_* は buy/sell それぞれ Phase6 で定義済み。ここでは True/False/None をそのまま扱う。
        if s is not None:
            evaluated_success.append(bool(s))

    evaluated_count = len(evaluated_returns)
    success_count = sum(1 for s in evaluated_success if s)

    if evaluated_count > 0:
        success_rate: Optional[float] = success_count / evaluated_count
        avg_return: Optional[float] = float(sum(evaluated_returns) / evaluated_count)
    else:
        success_rate = None
        avg_return = None

    return HorizonSummary(
        evaluated_count=evaluated_count,
        success_count=success_count,
        success_rate=success_rate,
        avg_return=avg_return,
    )


def build_summary_queryset(params) -> Iterable[TradingSignal]:
    """
    TradingSignal + SignalOutcome を対象に、summary 用の QuerySet を構築する。
    対応フィルタ:
    - ticker
    - signal_date_from
    - signal_date_to
    - score_profile_name
    - score_profile_version
    - signal_type
    """
    qs = TradingSignal.objects.select_related("stock", "outcome").all()

    ticker = params.get("ticker")
    date_from = params.get("signal_date_from")
    date_to = params.get("signal_date_to")
    score_profile_name = params.get("score_profile_name")
    score_profile_version = params.get("score_profile_version")
    signal_type = params.get("signal_type")

    if ticker:
        qs = qs.filter(stock__ticker=ticker)
    if date_from:
        qs = qs.filter(signal_date__gte=date_from)
    if date_to:
        qs = qs.filter(signal_date__lte=date_to)
    if score_profile_name:
        qs = qs.filter(score_profile_name=score_profile_name)
    if score_profile_version:
        qs = qs.filter(score_profile_version=score_profile_version)
    if signal_type:
        qs = qs.filter(signal_type=signal_type)

    return qs


def summarize_signals(signals: Iterable[TradingSignal]) -> List[Dict[str, Any]]:
    """
    TradingSignal 群を profile_name / profile_version / signal_type ごとに集計し、
    summary のリストとして返す。
    """
    # グルーピングキー: (score_profile_name, score_profile_version, signal_type)
    groups: Dict[tuple[str, str, str], List[TradingSignal]] = {}

    for s in signals:
        key = (
            s.score_profile_name or "",
            s.score_profile_version or "",
            s.signal_type,
        )
        groups.setdefault(key, []).append(s)

    summaries: List[ProfileSignalSummary] = []

    for (profile_name, profile_version, signal_type), group_signals in groups.items():
        total_signals = len(group_signals)

        # horizon 別に returns / successes を集める
        returns_5: List[Optional[Decimal]] = []
        returns_10: List[Optional[Decimal]] = []
        returns_20: List[Optional[Decimal]] = []
        success_5: List[Optional[bool]] = []
        success_10: List[Optional[bool]] = []
        success_20: List[Optional[bool]] = []

        for s in group_signals:
            try:
                o: Optional[SignalOutcome] = s.outcome  # type: ignore[attr-defined]
            except SignalOutcome.DoesNotExist:  # type: ignore[attr-defined]
                o = None

            if o is None:
                # outcome 未評価のシグナルは evaluated_count に含めない
                returns_5.append(None)
                returns_10.append(None)
                returns_20.append(None)
                success_5.append(None)
                success_10.append(None)
                success_20.append(None)
            else:
                returns_5.append(o.return_5d)
                returns_10.append(o.return_10d)
                returns_20.append(o.return_20d)
                success_5.append(o.success_5d)
                success_10.append(o.success_10d)
                success_20.append(o.success_20d)

        h5 = _horizon_summary(returns_5, success_5, signal_type)
        h10 = _horizon_summary(returns_10, success_10, signal_type)
        h20 = _horizon_summary(returns_20, success_20, signal_type)

        summaries.append(
            ProfileSignalSummary(
                score_profile_name=profile_name,
                score_profile_version=profile_version,
                signal_type=signal_type,
                total_signals=total_signals,
                h5=h5,
                h10=h10,
                h20=h20,
            )
        )

    # 並び順: score_profile_name, score_profile_version, signal_type
    summaries.sort(
        key=lambda s: (s.score_profile_name, s.score_profile_version, s.signal_type)
    )

    # dict へ展開
    rows: List[Dict[str, Any]] = []
    for s in summaries:
        row: Dict[str, Any] = {
            "score_profile_name": s.score_profile_name,
            "score_profile_version": s.score_profile_version,
            "signal_type": s.signal_type,
            "total_signals": s.total_signals,
            "h5": asdict(s.h5),
            "h10": asdict(s.h10),
            "h20": asdict(s.h20),
        }
        rows.append(row)

    return rows

