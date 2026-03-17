"""
Yahoo Finance から株価を取得して DB に保存する共通ロジック。
5 分毎の自動取得ジョブから利用する。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from django.db import connection
import logging

from ..models import StockPrice5Min, WatchStock

logger = logging.getLogger(__name__)


def _fetch_yahoo_chart(ticker: str, interval: str, range_param: str, timeout: int = 8) -> Optional[dict]:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}"
        f"?interval={interval}&range={range_param}"
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
    )
    try:
        logger.warning(
            "price_fetcher yahoo request start ticker=%s interval=%s range=%s timeout=%s",
            ticker,
            interval,
            range_param,
            timeout,
        )
        # timeout は接続+読み取りの上限秒数（長くなりすぎないよう 8 秒程度に制限）
        start = datetime.now(timezone.utc)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode()
        end = datetime.now(timezone.utc)
        duration = (end - start).total_seconds()
        logger.warning(
            "price_fetcher yahoo request done ticker=%s status=%s duration=%.3f",
            ticker,
            getattr(resp, "status", None) if "resp" in locals() else None,
            duration,
        )
        return json.loads(body)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as e:
        logger.exception(
            "price_fetcher yahoo request error ticker=%s interval=%s range=%s",
            ticker,
            interval,
            range_param,
        )
        return None


def _parse_quote(data: dict):
    result = (data.get("chart") or {}).get("result")
    if not result:
        return None
    res = result[0]
    timestamps = res.get("timestamp") or []
    quote = ((res.get("indicators") or {}).get("quote") or [{}])[0]
    return (
        timestamps,
        quote.get("open") or [],
        quote.get("high") or [],
        quote.get("low") or [],
        quote.get("close") or [],
        quote.get("volume") or [],
    )


def fetch_and_save_5m_prices(stock: WatchStock, max_bars: int | None = None) -> int:
    """
    指定銘柄の 5 分足を Yahoo Finance から取得し StockPrice5Min に保存する。
    新規作成した件数を返す。失敗時は 0。
    """
    ticker = (stock.ticker or "").strip()
    if not ticker:
        return 0

    logger.warning(
        "price_fetcher fetch_and_save_5m_prices entered ticker=%s id=%s",
        ticker,
        getattr(stock, "id", None),
    )

    connection.close()
    yahoo_start = datetime.now(timezone.utc)
    data = _fetch_yahoo_chart(ticker, "5m", "60d")
    yahoo_end = datetime.now(timezone.utc)
    yahoo_duration = (yahoo_end - yahoo_start).total_seconds()
    if not data:
        logger.warning(
            "price_fetcher yahoo data missing ticker=%s duration=%.3f",
            ticker,
            yahoo_duration,
        )
        return 0

    parse_start = datetime.now(timezone.utc)
    parsed = _parse_quote(data)
    parse_end = datetime.now(timezone.utc)
    parse_duration = (parse_end - parse_start).total_seconds()
    if not parsed:
        logger.warning(
            "price_fetcher parse failed ticker=%s duration=%.3f",
            ticker,
            parse_duration,
        )
        return 0

    timestamps, opens, highs, lows, closes, volumes = parsed
    original_bars = len(timestamps)
    if max_bars is not None and original_bars > max_bars:
        # 直近 max_bars 本のみに絞る（末尾側が新しいと仮定）
        timestamps = timestamps[-max_bars:]
        opens = opens[-max_bars:] if opens else []
        highs = highs[-max_bars:] if highs else []
        lows = lows[-max_bars:] if lows else []
        closes = closes[-max_bars:] if closes else []
        volumes = volumes[-max_bars:] if volumes else []
    logger.warning(
        "price_fetcher parse done ticker=%s duration=%.3f bars=%d limited_bars=%d",
        ticker,
        parse_duration,
        original_bars,
        len(timestamps),
    )

    # 既存行の件数だけ事前に確認（本体ロジックは update_or_create のまま）
    existing_start = datetime.now(timezone.utc)
    existing_count = StockPrice5Min.objects.filter(stock=stock).count()
    existing_end = datetime.now(timezone.utc)
    existing_duration = (existing_end - existing_start).total_seconds()
    logger.warning(
        "price_fetcher existing rows load done ticker=%s duration=%.3f existing_count=%d",
        ticker,
        existing_duration,
        existing_count,
    )

    save_start = datetime.now(timezone.utc)
    logger.warning(
        "price_fetcher save loop start ticker=%s bars_to_save=%d",
        ticker,
        len(timestamps),
    )
    created = 0
    updated = 0
    for i in range(len(timestamps)):
        ts = timestamps[i]
        if ts is None:
            continue
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        o = opens[i] if i < len(opens) else None
        h = highs[i] if i < len(highs) else None
        l_ = lows[i] if i < len(lows) else None
        c = closes[i] if i < len(closes) else None
        v = volumes[i] if i < len(volumes) else None
        if c is None and o is None and h is None and l_ is None:
            continue
        close_val = Decimal(str(c)) if c is not None else (Decimal(str(o)) if o is not None else None)
        if close_val is None:
            continue
        open_val = Decimal(str(o)) if o is not None else close_val
        high_val = Decimal(str(h)) if h is not None else close_val
        low_val = Decimal(str(l_)) if l_ is not None else close_val
        vol = int(v) if v is not None and v == v else None
        obj, was_created = StockPrice5Min.objects.update_or_create(
            stock=stock,
            datetime=dt,
            defaults={
                "open_price": open_val,
                "high_price": high_val,
                "low_price": low_val,
                "close_price": close_val,
                "volume": vol,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1
    save_end = datetime.now(timezone.utc)
    save_duration = (save_end - save_start).total_seconds()
    logger.warning(
        "price_fetcher save loop done ticker=%s duration=%.3f created=%d updated=%d",
        ticker,
        save_duration,
        created,
        updated,
    )
    total_duration = (save_end - yahoo_start).total_seconds()
    logger.warning(
        "price_fetcher fetch_and_save_5m_prices finished ticker=%s total_duration=%.3f",
        ticker,
        total_duration,
    )
    return created
