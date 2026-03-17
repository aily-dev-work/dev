"""
5 分毎ジョブの実行ロジック。management コマンドと HTTP cron エンドポイントの両方から利用する。
"""
from __future__ import annotations

from django.utils import timezone
import time

from ..models import WatchStock
from .price_fetcher import fetch_and_save_5m_prices
from .signal_generation import generate_trading_signal_5m
from .signal_scoring import score_from_technical
from .technical_analysis import calculate_technical_summary_5m


def _round_to_5min_bar(dt):
    """現在時刻を 5 分足のバー開始時刻に切り捨てる。"""
    minute = (dt.minute // 5) * 5
    return dt.replace(minute=minute, second=0, microsecond=0)


def run_5m_fetch_and_evaluate(
    skip_fetch: bool = False,
    max_stocks: int | None = None,
    max_seconds: float | None = None,
) -> dict:
    """
    全監視銘柄の 5 分足を取得（省略可）し、各銘柄でテクニカル・スコア判定してシグナルを保存する。
    戻り値: {
      "stocks_count": int,
      "5m_created": int,
      "signals_updated": int,
      "bar_start": str (ISO),
      "errors": list[str],
    }
    """
    stocks = list(
        WatchStock.objects.filter(is_active=True)
        .exclude(ticker="")
        .exclude(ticker__isnull=True)
    )
    errors: list[str] = []
    total_fetched = 0
    signals_updated = 0
    bar_start = _round_to_5min_bar(timezone.now())
    started_at = time.monotonic()
    processed = 0
    success_count = 0
    error_count = 0

    for stock in stocks:
        # 時間上限・件数上限チェック（次の銘柄に入る前に判定）
        elapsed = time.monotonic() - started_at
        if max_seconds is not None and elapsed >= max_seconds:
            break
        if max_stocks is not None and processed >= max_stocks:
            break

        processed += 1
        if not skip_fetch:
            try:
                created = fetch_and_save_5m_prices(stock)
                total_fetched += created
            except Exception as e:
                errors.append(f"fetch_5m {stock.ticker}: {e}")
                error_count += 1
                continue

        try:
            summary = calculate_technical_summary_5m(stock)
        except Exception as e:
            errors.append(f"technical_5m {stock.ticker}: {e}")
            error_count += 1
            continue

        if summary.latest_close is None:
            continue

        try:
            score_result = score_from_technical(summary)
        except Exception as e:
            errors.append(f"score {stock.ticker}: {e}")
            error_count += 1
            continue

        try:
            generate_trading_signal_5m(stock, summary, score_result, bar_start)
            signals_updated += 1
            success_count += 1
        except Exception as e:
            errors.append(f"signal_5m {stock.ticker}: {e}")
            error_count += 1

    elapsed_total = time.monotonic() - started_at
    remaining = max(len(stocks) - processed, 0)
    stopped_by_limit = bool(
        (max_seconds is not None and elapsed_total >= max_seconds)
        or (max_stocks is not None and processed >= max_stocks)
    )

    return {
        "stocks_count": len(stocks),
        "processed_count": processed,
        "success_count": success_count,
        "error_count": error_count,
        "remaining_count": remaining,
        "stopped_by_limit": stopped_by_limit,
        "elapsed_seconds": round(elapsed_total, 3),
        "5m_created": total_fetched,
        "signals_updated": signals_updated,
        "bar_start": bar_start.isoformat(),
        "errors": errors,
    }
