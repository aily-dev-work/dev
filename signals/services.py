from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from typing import Iterable
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

from .models import DetectedItem, SignalKeyword, TrackedProduct, WatchSource
from .external_signals import ExternalSignalSummary, collect_external_signals


REQUEST_TIMEOUT = 15
MAX_SUMMARY_LENGTH = 500

GENERIC_TERMS = {
    "お知らせ",
    "ニュース",
    "プレスリリース",
    "公式",
    "告知",
    "発表",
    "キャンペーン",
    "イベント",
    "商品情報",
}

ANNOUNCEMENT_TERMS = [
    "予約開始",
    "予約受付開始",
    "予約受付中",
    "予約終了",
    "受注開始",
    "受注終了",
    "販売開始",
    "販売終了",
    "発売",
    "再販",
    "再入荷",
    "抽選販売",
    "在庫切れ",
    "完売",
    "新商品",
    "限定",
]

ANNOUNCEMENT_RE = re.compile("|".join(map(re.escape, ANNOUNCEMENT_TERMS)))
GENERIC_RE = re.compile("|".join(map(re.escape, GENERIC_TERMS)))


@dataclass
class ParsedEntry:
    title: str
    url: str
    summary: str
    published_at: datetime | None
    text: str


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(str(value))
    if "<" in value and ">" in value:
        value = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def truncate_text(value: str, length: int = MAX_SUMMARY_LENGTH) -> str:
    value = clean_text(value)
    if len(value) <= length:
        return value
    return value[: length - 1].rstrip() + "..."


def parse_struct_time(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime(*value[:6], tzinfo=dt_timezone.utc)
    except Exception:
        return None


def load_active_keywords() -> list[SignalKeyword]:
    return list(SignalKeyword.objects.filter(is_active=True).order_by("-score", "keyword"))


def detect_keywords(text: str, keywords: Iterable[SignalKeyword]) -> tuple[list[str], int]:
    haystack = clean_text(text).lower()
    matched: list[str] = []
    total_score = 0
    for keyword in keywords:
        needle = clean_text(keyword.keyword).lower()
        if needle and needle in haystack:
            matched.append(keyword.keyword)
            total_score += int(keyword.score)
    return matched, total_score


def estimate_probability(
    total_score: int,
    matched_keywords: list[str],
    product_confidence: int,
    external_signals: ExternalSignalSummary | None = None,
) -> int:
    external_score = external_signals.external_score if external_signals else 0
    probability = 15 + int(total_score * 0.55)
    probability += max(0, product_confidence - 70) // 2
    probability += int(external_score * 0.35)

    if len(matched_keywords) >= 2:
        probability += 6
    if any(keyword in {"再販なし", "生産終了", "販売終了", "完売"} for keyword in matched_keywords):
        probability += 10
    if any(keyword in {"抽選販売", "限定"} for keyword in matched_keywords):
        probability += 5

    return max(1, min(99, probability))


def build_reason(
    product_name: str,
    matched_keywords: list[str],
    matched_term: str,
    product_confidence: int,
    external_signals: ExternalSignalSummary | None = None,
) -> str:
    parts = [f"商品名候補: {product_name}"]
    if matched_term and clean_text(matched_term) != clean_text(product_name):
        parts.append(f"抽出元: {matched_term}")
    if matched_keywords:
        parts.append("検知キーワード: " + ", ".join(matched_keywords))
    if product_confidence >= 90:
        parts.append("商品との紐づきが強い")
    elif product_confidence >= 75:
        parts.append("商品との紐づきが中程度")
    else:
        parts.append("商品との紐づきが弱め")
    if external_signals:
        parts.append(external_signals.summary)
    return " / ".join(parts)


def sanitize_candidate(value: str | None) -> str:
    text = clean_text(value)
    if not text:
        return ""

    text = GENERIC_RE.sub("", text)
    text = ANNOUNCEMENT_RE.sub("", text)
    text = re.sub(r"\b(?:news|info|release)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" -–—:：|｜/／[]（）()【】")
    text = re.sub(r"\s*(?:の)?(?:予約開始|予約受付開始|予約受付中|受注開始|受注終了|販売開始|販売終了|発売|再販|再入荷|抽選販売|在庫切れ|完売|新商品|限定)\s*$", "", text)
    text = re.sub(r"^[・■◆◇★☆※\s]+", "", text)

    if len(text) < 2:
        return ""
    if text in GENERIC_TERMS:
        return ""
    return text


def split_on_separators(value: str) -> str:
    parts = re.split(r"[｜|/:：・\-–—]", clean_text(value))
    parts = [sanitize_candidate(part) for part in parts]
    parts = [part for part in parts if part]
    if not parts:
        return ""
    return max(parts, key=len)


def discover_product_name(entry: ParsedEntry, source: WatchSource) -> tuple[str | None, str, int]:
    """
    Return (product_name, matched_term, confidence).
    We infer product names from page/feed titles so users do not need to pre-register products.
    """
    title = clean_text(entry.title)
    summary = clean_text(entry.summary)
    source_name = clean_text(source.name)
    candidates = [text for text in [title, summary] if text]

    # Bracketed names are usually the strongest signal.
    for text in candidates:
        for match in re.finditer(r"[【\[\(（](.+?)[】\]\)）]", text):
            candidate = sanitize_candidate(match.group(1))
            if candidate:
                return candidate, match.group(1), 95

    # Remove boilerplate and take the most product-like segment.
    for text in candidates:
        candidate = sanitize_candidate(text)
        if not candidate:
            continue
        candidate = split_on_separators(candidate) or candidate
        if candidate and candidate not in GENERIC_TERMS:
            confidence = 80 if candidate.lower() != source_name.lower() else 60
            return candidate, text, confidence

    raw = sanitize_candidate(title)
    if raw:
        confidence = 78 if source_name.lower() not in raw.lower() else 65
        return raw, title, confidence

    return None, "", 0


def save_detected_item(
    source: WatchSource,
    product: TrackedProduct,
    entry: ParsedEntry,
    matched_keywords: list[str],
    total_score: int,
    matched_term: str = "",
    product_confidence: int = 0,
    external_signals: ExternalSignalSummary | None = None,
) -> tuple[DetectedItem | None, bool]:
    if not matched_keywords:
        return None, False

    premium_probability = estimate_probability(
        total_score,
        matched_keywords,
        product_confidence,
        external_signals=external_signals,
    )
    defaults = {
        "source": source,
        "product": product,
        "title": entry.title or source.name,
        "summary": entry.summary,
        "published_at": entry.published_at,
        "matched_keywords": matched_keywords,
        "total_score": total_score,
        "is_alert": total_score >= 50,
        "premium_probability": premium_probability,
        "google_trend_score": external_signals.google_trend_score if external_signals else 0,
        "google_trend_growth_pct": external_signals.google_growth_pct if external_signals else 0,
        "social_buzz_score": external_signals.social_buzz_score if external_signals else 0,
        "social_mentions": external_signals.social_mentions if external_signals else 0,
        "external_signal_summary": external_signals.summary if external_signals else "",
        "prevalue_reason": build_reason(
            product_name=product.name,
            matched_keywords=matched_keywords,
            matched_term=matched_term,
            product_confidence=product_confidence,
            external_signals=external_signals,
        ),
    }

    item, created = DetectedItem.objects.get_or_create(
        url=entry.url,
        defaults=defaults,
    )
    if not created:
        changed_fields = []
        for field, value in defaults.items():
            if getattr(item, field) != value:
                setattr(item, field, value)
                changed_fields.append(field)
        if changed_fields:
            item.save(update_fields=changed_fields)
    return item, created


def fetch_rss_entries(source: WatchSource) -> list[ParsedEntry]:
    feed = feedparser.parse(source.url)
    entries: list[ParsedEntry] = []
    for entry in getattr(feed, "entries", []):
        link = clean_text(entry.get("link")) or source.url
        entry_url = urljoin(source.url, link)
        title = clean_text(entry.get("title")) or source.name
        summary = clean_text(
            entry.get("summary")
            or entry.get("description")
            or (entry.get("content") or [{}])[0].get("value")
        )
        content_values = []
        for block in entry.get("content", []) or []:
            content_values.append(clean_text(block.get("value")))
        body_text = " ".join(v for v in [title, summary, " ".join(content_values)] if v)
        entries.append(
            ParsedEntry(
                title=title,
                url=entry_url,
                summary=truncate_text(summary or body_text),
                published_at=parse_struct_time(entry.get("published_parsed") or entry.get("updated_parsed")),
                text=body_text,
            )
        )
    return entries


def fetch_html_entry(source: WatchSource) -> ParsedEntry:
    response = requests.get(
        source.url,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": "Mozilla/5.0 (compatible; premium-monitor/1.0)"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    page_title = clean_text(soup.title.get_text(" ", strip=True) if soup.title else "")
    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_description = clean_text(meta_tag.get("content"))

    body_node = soup.body or soup
    body_text = clean_text(body_node.get_text(" ", strip=True))
    title = page_title or source.name
    summary = truncate_text(meta_description or body_text)
    return ParsedEntry(
        title=title,
        url=response.url or source.url,
        summary=summary,
        published_at=None,
        text=" ".join(v for v in [title, meta_description, body_text] if v),
    )


def fetch_source_entries(source: WatchSource) -> list[ParsedEntry]:
    if source.source_type == WatchSource.SOURCE_TYPE_RSS:
        return fetch_rss_entries(source)
    if source.source_type == WatchSource.SOURCE_TYPE_HTML:
        return [fetch_html_entry(source)]
    raise ValueError(f"Unsupported source_type: {source.source_type}")


def get_or_create_discovered_product(product_name: str) -> TrackedProduct:
    product, _ = TrackedProduct.objects.get_or_create(
        name=product_name,
        defaults={"is_active": True},
    )
    if not product.is_active:
        product.is_active = True
        product.save(update_fields=["is_active", "updated_at"])
    return product


def process_source(source: WatchSource) -> dict:
    keywords = load_active_keywords()
    entries = fetch_source_entries(source)
    created_count = 0
    skipped_count = 0
    matched_count = 0
    unmatched_product_count = 0
    discovered_products: set[str] = set()
    external_signal_cache: dict[str, ExternalSignalSummary] = {}

    for entry in entries:
        product_name, matched_term, product_confidence = discover_product_name(entry, source)
        if not product_name:
            unmatched_product_count += 1
            continue

        product = get_or_create_discovered_product(product_name)
        discovered_products.add(product.name)
        external_signals = external_signal_cache.get(product.name)
        if external_signals is None:
            external_signals = collect_external_signals(product.name)
            external_signal_cache[product.name] = external_signals

        matched_keywords, total_score = detect_keywords(
            f"{entry.title}\n{entry.summary}\n{entry.text}",
            keywords,
        )
        if not matched_keywords:
            skipped_count += 1
            continue

        _, created = save_detected_item(
            source,
            product,
            entry,
            matched_keywords,
            total_score,
            matched_term=matched_term,
            product_confidence=product_confidence,
            external_signals=external_signals,
        )
        if created:
            created_count += 1
            matched_count += 1
        else:
            skipped_count += 1

    return {
        "source": source.name,
        "entries": len(entries),
        "created": created_count,
        "matched": matched_count,
        "skipped": skipped_count,
        "unmatched_products": unmatched_product_count,
        "discovered_products": len(discovered_products),
        "external_signals": {name: external_signal_cache[name].summary for name in discovered_products},
    }
