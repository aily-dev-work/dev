"""
5 分毎ジョブの実行ロジック。management コマンドと HTTP cron エンドポイントの両方から利用する。
"""
from __future__ import annotations

import logging
import time

from django.utils import timezone

from ..models import WatchStock
from .price_fetcher import fetch_and_save_5m_prices
from .signal_generation import generate_trading_signal_5m
from .signal_scoring import score_from_technical
from .technical_analysis import calculate_technical_summary_5m

logger = logging.getLogger(__name__)


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
        .order_by("updated_at", "id")
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
            logger.info(
                "run_5m stop by max_seconds before stock ticker=%s elapsed=%.3f",
                stock.ticker,
                elapsed,
            )
            break
        if max_stocks is not None and processed >= max_stocks:
            logger.info(
                "run_5m stop by max_stocks before stock ticker=%s processed=%d",
                stock.ticker,
                processed,
            )
            break

        processed += 1
        stock_start = time.monotonic()
        logger.info("run_5m stock start ticker=%s", stock.ticker)

        fetch_duration = 0.0
        save_duration = 0.0
        technical_duration = 0.0
        score_duration = 0.0
        signal_duration = 0.0

        # fetch + save 5m
        if not skip_fetch:
            # 時間上限チェック（fetch 前）
            elapsed = time.monotonic() - started_at
            if max_seconds is not None and elapsed >= max_seconds:
                logger.info(
                    "run_5m stop by max_seconds before fetch ticker=%s elapsed=%.3f",
                    stock.ticker,
                    elapsed,
                )
                processed -= 1  # この銘柄は未処理として扱う
                break
            try:
                fetch_start = time.monotonic()
                created = fetch_and_save_5m_prices(stock)
                fetch_end = time.monotonic()
                fetch_duration = fetch_end - fetch_start
                total_fetched += created
                logger.info(
                    "run_5m stock fetch duration=%.3f ticker=%s created=%d",
                    fetch_duration,
                    stock.ticker,
                    created,
                )
            except Exception as e:
                fetch_end = time.monotonic()
                fetch_duration = fetch_end - stock_start
                errors.append(f"fetch_5m {stock.ticker}: {e}")
                error_count += 1
                logger.exception("run_5m fetch_5m error ticker=%s", stock.ticker)
                continue

        # technical summary
        elapsed = time.monotonic() - started_at
        if max_seconds is not None and elapsed >= max_seconds:
            logger.info(
                "run_5m stop by max_seconds before technical ticker=%s elapsed=%.3f",
                stock.ticker,
                elapsed,
            )
            processed -= 1
            break
        try:
            tech_start = time.monotonic()
            summary = calculate_technical_summary_5m(stock)
            tech_end = time.monotonic()
            technical_duration = tech_end - tech_start
            logger.info(
                "run_5m stock technical duration=%.3f ticker=%s",
                technical_duration,
                stock.ticker,
            )
        except Exception as e:
            errors.append(f"technical_5m {stock.ticker}: {e}")
            error_count += 1
            logger.exception("run_5m technical_5m error ticker=%s", stock.ticker)
            continue

        if summary.latest_close is None:
            stock_total = time.monotonic() - stock_start
            logger.info(
                "run_5m stock skip (no latest_close) ticker=%s total_duration=%.3f",
                stock.ticker,
                stock_total,
            )
            continue

        # score
        elapsed = time.monotonic() - started_at
        if max_seconds is not None and elapsed >= max_seconds:
            logger.info(
                "run_5m stop by max_seconds before score ticker=%s elapsed=%.3f",
                stock.ticker,
                elapsed,
            )
            processed -= 1
            break
        try:
            score_start = time.monotonic()
            score_result = score_from_technical(summary)
            score_end = time.monotonic()
            score_duration = score_end - score_start
            logger.info(
                "run_5m stock score duration=%.3f ticker=%s",
                score_duration,
                stock.ticker,
            )
        except Exception as e:
            errors.append(f"score {stock.ticker}: {e}")
            error_count += 1
            logger.exception("run_5m score error ticker=%s", stock.ticker)
            continue

        # signal generation
        elapsed = time.monotonic() - started_at
        if max_seconds is not None and elapsed >= max_seconds:
            logger.info(
                "run_5m stop by max_seconds before signal ticker=%s elapsed=%.3f",
                stock.ticker,
                elapsed,
            )
            processed -= 1
            break
        try:
            signal_start = time.monotonic()
            generate_trading_signal_5m(stock, summary, score_result, bar_start)
            signal_end = time.monotonic()
            signal_duration = signal_end - signal_start
            signals_updated += 1
            success_count += 1
            logger.info(
                "run_5m stock signal duration=%.3f ticker=%s",
                signal_duration,
                stock.ticker,
            )
        except Exception as e:
            errors.append(f"signal_5m {stock.ticker}: {e}")
            error_count += 1
            logger.exception("run_5m signal_5m error ticker=%s", stock.ticker)
        finally:
            stock_total = time.monotonic() - stock_start
            save_duration = max(0.0, stock_total - fetch_duration - technical_duration - score_duration - signal_duration)
            logger.info(
                "run_5m stock total ticker=%s total=%.3f fetch=%.3f save=%.3f technical=%.3f score=%.3f signal=%.3f",
                stock.ticker,
                stock_total,
                fetch_duration,
                save_duration,
                technical_duration,
                score_duration,
                signal_duration,
            )

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
