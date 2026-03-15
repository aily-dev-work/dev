"""
Yahoo Finance から株価を取得して DB に保存する共通ロジック。
5 分毎の自動取得ジョブから利用する。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from django.db import connection
from django.utils import timezone

from ..models import StockPrice5Min, WatchStock


def _fetch_yahoo_chart(ticker: str, interval: str, range_param: str, timeout: int = 15) -> Optional[dict]:
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
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError):
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


def fetch_and_save_5m_prices(stock: WatchStock) -> int:
    """
    指定銘柄の 5 分足を Yahoo Finance から取得し StockPrice5Min に保存する。
    新規作成した件数を返す。失敗時は 0。
    """
    ticker = (stock.ticker or "").strip()
    if not ticker:
        return 0

    connection.close()
    data = _fetch_yahoo_chart(ticker, "5m", "60d")
    if not data:
        return 0

    parsed = _parse_quote(data)
    if not parsed:
        return 0

    timestamps, opens, highs, lows, closes, volumes = parsed
    created = 0
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
        _, was_created = StockPrice5Min.objects.update_or_create(
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
    return created
