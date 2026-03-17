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
    started_at = time.monotonic()
    errors: list[str] = []
    logger.warning(
        "run_5m_fetch_and_evaluate entered skip_fetch=%s max_stocks=%s max_seconds=%s",
        skip_fetch,
        max_stocks,
        max_seconds,
    )

    # 段階的切り分け: まずは queryset と対象件数のみ確認して返す
    total_all = WatchStock.objects.count()
    total_active = WatchStock.objects.filter(is_active=True).count()
    total_with_ticker = (
        WatchStock.objects.filter(is_active=True)
        .exclude(ticker="")
        .exclude(ticker__isnull=True)
        .count()
    )
    logger.warning(
        "run_5m_fetch_and_evaluate stocks counts total_all=%d total_active=%d total_active_with_ticker=%d",
        total_all,
        total_active,
        total_with_ticker,
    )

    stocks_qs = (
        WatchStock.objects.filter(is_active=True)
        .exclude(ticker="")
        .exclude(ticker__isnull=True)
        .order_by("updated_at", "id")
    )
    stocks = list(stocks_qs)
    logger.warning(
        "run_5m_fetch_and_evaluate stocks queryset evaluated skip_fetch=%s max_stocks=%s max_seconds=%s stocks_count=%d",
        skip_fetch,
        max_stocks,
        max_seconds,
        len(stocks),
    )

    if not stocks:
        logger.warning("run_5m_fetch_and_evaluate no stocks found, returning early")
        elapsed_total = time.monotonic() - started_at
        return {
            "stocks_count": 0,
            "processed_count": 0,
            "success_count": 0,
            "error_count": 0,
            "remaining_count": 0,
            "stopped_by_limit": False,
            "elapsed_seconds": round(elapsed_total, 3),
            "5m_created": 0,
            "signals_updated": 0,
            "bar_start": None,
            "errors": [],
            "current_stock_ticker": None,
            "stopped_at_step": "before_loop",
        }

    # 段階的切り分け: 先頭1件のみ処理する
    first = stocks[0]
    logger.warning(
        "run_5m first stock selected ticker=%s id=%s",
        first.ticker,
        first.id,
    )
    logger.warning(
        "run_5m stock start ticker=%s id=%s",
        first.ticker,
        first.id,
    )
    # fetch ステージ（skip_fetch=False のときのみ実行し、ここで一旦返す）
    if not skip_fetch:
        try:
            fetch_start = time.monotonic()
            logger.warning(
                "run_5m before fetch ticker=%s id=%s",
                first.ticker,
                first.id,
            )
            created = fetch_and_save_5m_prices(first)
            fetch_end = time.monotonic()
            fetch_duration = fetch_end - fetch_start
            logger.warning(
                "run_5m after fetch ticker=%s id=%s duration=%.3f created=%d",
                first.ticker,
                first.id,
                fetch_duration,
                created,
            )
            elapsed_total = time.monotonic() - started_at
            return {
                "stocks_count": len(stocks),
                "processed_count": 1,
                "success_count": 1,
                "error_count": 0,
                "remaining_count": max(len(stocks) - 1, 0),
                "stopped_by_limit": False,
                "elapsed_seconds": round(elapsed_total, 3),
                "5m_created": created,
                "signals_updated": 0,
                "bar_start": None,
                "errors": [],
                "current_stock_ticker": first.ticker,
                "stopped_at_step": "after_fetch",
            }
        except Exception as e:
            logger.exception(
                "run_5m fetch_5m error ticker=%s id=%s",
                first.ticker,
                first.id,
            )
            errors.append(f"fetch_5m {first.ticker}: {e}")
            elapsed_total = time.monotonic() - started_at
            return {
                "stocks_count": len(stocks),
                "processed_count": 1,
                "success_count": 0,
                "error_count": 1,
                "remaining_count": max(len(stocks) - 1, 0),
                "stopped_by_limit": False,
                "elapsed_seconds": round(elapsed_total, 3),
                "5m_created": 0,
                "signals_updated": 0,
                "bar_start": None,
                "errors": errors,
                "current_stock_ticker": first.ticker,
                "stopped_at_step": "fetch_error",
            }

    # ここから先は skip_fetch=True（no_fetch=1）専用の technical / score / signal チェーン
    logger.warning(
        "run_5m before technical ticker=%s id=%s (skip_fetch=%s)",
        first.ticker,
        first.id,
        skip_fetch,
    )

    # technical
    try:
        tech_start = time.monotonic()
        logger.warning(
            "run_5m technical start ticker=%s id=%s",
            first.ticker,
            first.id,
        )
        summary = calculate_technical_summary_5m(first)
        tech_end = time.monotonic()
        technical_duration = tech_end - tech_start
        has_latest = hasattr(summary, "latest_close")
        logger.warning(
            "run_5m technical done ticker=%s id=%s duration=%.3f type=%s has_latest_close=%s",
            first.ticker,
            first.id,
            technical_duration,
            type(summary).__name__,
            has_latest,
        )
    except Exception as e:
        logger.exception(
            "run_5m technical_5m error ticker=%s id=%s",
            first.ticker,
            first.id,
        )
        errors.append(f"technical_5m {first.ticker}: {e}")
        elapsed_total = time.monotonic() - started_at
        return {
            "stocks_count": len(stocks),
            "processed_count": 1,
            "success_count": 0,
            "error_count": 1,
            "remaining_count": max(len(stocks) - 1, 0),
            "stopped_by_limit": False,
            "elapsed_seconds": round(elapsed_total, 3),
            "5m_created": 0,
            "signals_updated": 0,
            "bar_start": None,
            "errors": errors,
            "current_stock_ticker": first.ticker,
            "stopped_at_step": "technical_error",
        }

    # score（先頭1件のみ）
    try:
        score_start = time.monotonic()
        logger.warning(
            "run_5m before score ticker=%s id=%s",
            first.ticker,
            first.id,
        )
        score_result = score_from_technical(summary)
        score_end = time.monotonic()
        score_duration = score_end - score_start
        logger.warning(
            "run_5m after score ticker=%s id=%s duration=%.3f buy=%.1f sell=%.1f bias=%s strength=%s",
            first.ticker,
            first.id,
            score_duration,
            getattr(score_result, "buy_score", 0.0),
            getattr(score_result, "sell_score", 0.0),
            getattr(score_result, "bias", None),
            getattr(score_result, "strength", None),
        )
    except Exception as e:
        logger.exception(
            "run_5m score_5m error ticker=%s id=%s",
            first.ticker,
            first.id,
        )
        errors.append(f"score_5m {first.ticker}: {e}")
        elapsed_total = time.monotonic() - started_at
        return {
            "stocks_count": len(stocks),
            "processed_count": 1,
            "success_count": 0,
            "error_count": 1,
            "remaining_count": max(len(stocks) - 1, 0),
            "stopped_by_limit": False,
            "elapsed_seconds": round(elapsed_total, 3),
            "5m_created": 0,
            "signals_updated": 0,
            "bar_start": None,
            "errors": errors,
            "current_stock_ticker": first.ticker,
            "stopped_at_step": "score_error",
        }

    # signal（先頭1件のみ）
    try:
        signal_start = time.monotonic()
        logger.warning(
            "run_5m before signal ticker=%s id=%s",
            first.ticker,
            first.id,
        )
        bar_start = _round_to_5min_bar(timezone.now())
        signal = generate_trading_signal_5m(first, summary, score_result, bar_start)
        signal_end = time.monotonic()
        signal_duration = signal_end - signal_start
        logger.warning(
            "run_5m after signal ticker=%s id=%s duration=%.3f signal_type=%s action=%s",
            first.ticker,
            first.id,
            signal_duration,
            getattr(signal, "signal_type", None),
            getattr(signal, "score_bias", None),
        )
        elapsed_total = time.monotonic() - started_at
        return {
            "stocks_count": len(stocks),
            "processed_count": 1,
            "success_count": 1,
            "error_count": 0,
            "remaining_count": max(len(stocks) - 1, 0),
            "stopped_by_limit": False,
            "elapsed_seconds": round(elapsed_total, 3),
            "5m_created": 0,
            "signals_updated": 1,
            "bar_start": bar_start.isoformat(),
            "errors": [],
            "current_stock_ticker": first.ticker,
            "stopped_at_step": "after_signal",
        }
    except Exception as e:
        logger.exception(
            "run_5m signal_5m error ticker=%s id=%s",
            first.ticker,
            first.id,
        )
        errors.append(f"signal_5m {first.ticker}: {e}")
        elapsed_total = time.monotonic() - started_at
        return {
            "stocks_count": len(stocks),
            "processed_count": 1,
            "success_count": 0,
            "error_count": 1,
            "remaining_count": max(len(stocks) - 1, 0),
            "stopped_by_limit": False,
            "elapsed_seconds": round(elapsed_total, 3),
            "5m_created": 0,
            "signals_updated": 0,
            "bar_start": None,
            "errors": errors,
            "current_stock_ticker": first.ticker,
            "stopped_at_step": "signal_error",
        }
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
    last_stock_ticker: str | None = None
    stopped_at_step: str | None = None

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
        last_stock_ticker = stock.ticker
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
                stopped_at_step = "fetch"
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
            stopped_at_step = "technical"
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
            stopped_at_step = "score"
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
            stopped_at_step = "signal"
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
        "current_stock_ticker": last_stock_ticker,
        "stopped_at_step": stopped_at_step,
        "stopped_by_limit": stopped_by_limit,
        "elapsed_seconds": round(elapsed_total, 3),
        "5m_created": total_fetched,
        "signals_updated": signals_updated,
        "bar_start": bar_start.isoformat(),
        "errors": errors,
    }
