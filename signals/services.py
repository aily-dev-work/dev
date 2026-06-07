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
from django.utils import timezone

from .models import DetectedItem, SignalKeyword, WatchSource


REQUEST_TIMEOUT = 15
MAX_SUMMARY_LENGTH = 500


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
    return value[: length - 1].rstrip() + "…"


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


def save_detected_item(
    source: WatchSource,
    entry: ParsedEntry,
    matched_keywords: list[str],
    total_score: int,
) -> tuple[DetectedItem | None, bool]:
    if not matched_keywords:
        return None, False

    item, created = DetectedItem.objects.get_or_create(
        url=entry.url,
        defaults={
            "source": source,
            "title": entry.title or source.name,
            "summary": entry.summary,
            "published_at": entry.published_at,
            "matched_keywords": matched_keywords,
            "total_score": total_score,
            "is_alert": total_score >= 50,
        },
    )
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
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; premium-monitor/1.0)",
        },
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


def process_source(source: WatchSource) -> dict:
    keywords = load_active_keywords()
    entries = fetch_source_entries(source)
    created_count = 0
    skipped_count = 0
    matched_count = 0

    for entry in entries:
        matched_keywords, total_score = detect_keywords(
            f"{entry.title}\n{entry.text}",
            keywords,
        )
        if not matched_keywords:
            skipped_count += 1
            continue

        item, created = save_detected_item(source, entry, matched_keywords, total_score)
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
    }
