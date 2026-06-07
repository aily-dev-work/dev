from __future__ import annotations

import math
import re
from dataclasses import dataclass
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

try:
    from pytrends.request import TrendReq
except Exception:  # pragma: no cover - optional dependency
    TrendReq = None


REQUEST_TIMEOUT = 12
SOCIAL_DOMAINS = ["x.com", "threads.net", "instagram.com", "mastodon.social"]


@dataclass
class ExternalSignalSummary:
    google_interest: int = 0
    google_growth_pct: int = 0
    social_mentions: int = 0
    social_buzz_score: int = 0
    google_trend_score: int = 0
    external_score: int = 0
    summary: str = ""


def _search_result_count(query: str) -> int:
    url = "https://www.google.com/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; premium-monitor/1.0)",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    }
    params = {
        "q": query,
        "hl": "ja",
        "gl": "jp",
        "num": 10,
        "pws": 0,
    }
    resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    stats = soup.select_one("#result-stats")
    if stats:
        text = stats.get_text(" ", strip=True)
        match = re.search(r"([0-9,]+)", text)
        if match:
            return int(match.group(1).replace(",", ""))
    return len(soup.select("div.g"))


def _collect_google_trends(term: str) -> tuple[int, int, int]:
    if TrendReq is None:
        return 0, 0, 0

    try:
        pytrends = TrendReq(hl="ja-JP", tz=540, timeout=(5, 10))
        pytrends.build_payload([term], timeframe="today 3-m", geo="JP")
        data = pytrends.interest_over_time()
    except Exception:
        return 0, 0, 0

    if data is None or data.empty or term not in data.columns:
        return 0, 0, 0

    series = data[term].astype(float)
    if len(series) < 4:
        current_avg = int(round(series.mean()))
        growth_pct = 0
    else:
        midpoint = max(len(series) // 2, 1)
        prev_avg = float(series.iloc[:midpoint].mean())
        current_avg = float(series.iloc[midpoint:].mean())
        if prev_avg <= 0:
            growth_pct = 100 if current_avg > 0 else 0
        else:
            growth_pct = int(round(((current_avg - prev_avg) / prev_avg) * 100))
        current_avg = int(round(current_avg))

    interest_score = max(0, min(100, current_avg))
    growth_score = max(0, min(100, growth_pct if growth_pct > 0 else 0))
    trend_score = max(0, min(100, int(interest_score * 0.6 + growth_score * 0.4)))
    return interest_score, growth_pct, trend_score


def _collect_social_buzz(term: str) -> tuple[int, int]:
    total_mentions = 0
    combined_query = f'("{term}") (' + " OR ".join(f"site:{domain}" for domain in SOCIAL_DOMAINS) + ")"
    try:
        total_mentions = _search_result_count(combined_query)
    except Exception:
        total_mentions = 0

    social_score = int(min(40, math.log10(total_mentions + 1) * 20))
    return total_mentions, social_score


def collect_external_signals(product_name: str) -> ExternalSignalSummary:
    google_interest, google_growth_pct, google_trend_score = _collect_google_trends(product_name)
    social_mentions, social_buzz_score = _collect_social_buzz(product_name)
    external_score = max(0, min(100, int(google_trend_score * 0.7 + social_buzz_score * 0.3)))

    summary_parts = []
    if google_trend_score:
        summary_parts.append(f"Google注目度 {google_trend_score}")
    if google_growth_pct:
        summary_parts.append(f"Google成長 {google_growth_pct}%")
    if social_mentions:
        summary_parts.append(f"SNS言及 {social_mentions}件")
    if social_buzz_score:
        summary_parts.append(f"SNSスコア {social_buzz_score}")
    if not summary_parts:
        summary_parts.append("外部信号は取得できませんでした")

    return ExternalSignalSummary(
        google_interest=google_interest,
        google_growth_pct=google_growth_pct,
        social_mentions=social_mentions,
        social_buzz_score=social_buzz_score,
        google_trend_score=google_trend_score,
        external_score=external_score,
        summary=" / ".join(summary_parts),
    )
