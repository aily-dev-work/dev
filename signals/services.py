from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

from .external_signals import ExternalSignalSummary, collect_external_signals
from .models import DetectedItem, SignalKeyword, TrackedProduct, WatchSource


REQUEST_TIMEOUT = 15
MAX_SUMMARY_LENGTH = 500
MAX_HTML_LINKS_PER_SOURCE = 8

GENERIC_TITLE_MARKERS = [
    "公式サイト",
    "オフィシャルサイト",
    "ホームページ",
    "通販サイト",
    "ポータルサイト",
    "製品情報ポータル",
    "ニュースリリース一覧",
    "一覧",
    "トップ",
    "お知らせ",
    "新着情報",
    "会社概要",
    "about",
    "news",
    "portal",
    "site",
    "home",
    "index",
]

ANNOUNCEMENT_PREFIXES = [
    "【予約開始】",
    "【予約受付開始】",
    "【予約受付中】",
    "【新商品】",
    "【新製品】",
    "【発売】",
    "【再販】",
    "【抽選販売】",
    "【お知らせ】",
    "【重要】",
]

ANNOUNCEMENT_WORDS = [
    "予約開始",
    "予約受付",
    "新商品",
    "新製品",
    "発売",
    "再販",
    "抽選販売",
    "販売終了",
    "在庫切れ",
    "完売",
    "限定",
]

RELEASE_KEYWORDS = [
    "商品化",
    "登場",
    "発売",
    "予約受付開始",
    "予約受付中",
    "初商品化",
    "初の立体化",
    "初立体化",
    "プレミアムバンダイで予約受付開始",
]

RELEASE_SIGNAL_SCORES = {
    "商品化": 15,
    "登場": 12,
    "発売": 12,
    "予約受付開始": 15,
    "予約受付中": 10,
    "初商品化": 18,
    "初の立体化": 18,
    "初立体化": 18,
    "プレミアムバンダイで予約受付開始": 12,
}

STRICT_NON_PRODUCT_PHRASES = [
    "FAQ",
    "更新",
    "お問い合わせ",
    "お問い合わせフォーム",
    "お知らせ",
    "新着情報",
    "ニュース",
    "一覧",
    "決済",
    "フィッシング",
    "ホームページ",
    "公式サイト",
    "通販サイト",
    "ポータルサイト",
    "製品情報",
    "商品情報",
]

NON_PRODUCT_SECTION_WORDS = {
    "トピックス",
    "更新情報",
    "発売スケジュール",
    "キャンペーン",
    "キャンペーン・セール情報",
    "セール",
    "セール情報",
    "決済",
    "フィッシング",
    "フィッシング詐欺",
    "FAQ",
    "よくあるご質問",
    "お知らせ",
    "新着情報",
    "ニュース",
    "一覧",
    "情報",
    "サイト",
    "ホームページ",
    "ポータル",
    "ニュースリリース",
    "製品情報",
    "商品情報",
}

CATEGORY_NOISE_WORDS = {
    "フィギュア",
    "プラモデル",
    "ゲーム",
    "アニメ",
    "マンガ",
    "ノベル",
    "キャラクター",
    "グッズ",
    "玩具",
    "ホビー",
}

HTML_LINK_HINT_WORDS = [
    "news",
    "topic",
    "release",
    "press",
    "article",
    "product",
    "item",
    "detail",
    "goods",
    "shop",
    "campaign",
    "announce",
    "info",
    "お知らせ",
    "ニュース",
    "新商品",
    "新製品",
    "予約",
    "発売",
    "再販",
    "限定",
    "抽選",
    "在庫",
    "完売",
    "商品",
]

SENTENCE_NOISE_MARKERS = [
    "、",
    "。",
    "！",
    "？",
    "!",
    "?",
    "知ることができる",
    "最新情報",
    "総合サイト",
    "ニュース",
]

TRAILING_NOISE_WORDS = {
    "限定",
    "予約",
    "再販",
    "発売",
    "販売終了",
    "在庫切れ",
    "完売",
    "抽選",
    "抽選販売",
    "新商品",
    "新製品",
    "お知らせ",
    "重要",
}


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
    text = html.unescape(str(value))
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def truncate_text(value: str, length: int = MAX_SUMMARY_LENGTH) -> str:
    text = clean_text(value)
    if len(text) <= length:
        return text
    return text[: length - 1].rstrip() + "..."


def normalize_product_name(value: str) -> str:
    text = clean_text(value)
    text = re.sub(r"^(?:【[^】]{0,20}】|\[[^\]]{0,20}\]|\([^)]{0,20}\))+", "", text)
    for prefix in ANNOUNCEMENT_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    text = re.sub(r"^(?:新商品|新製品|予約開始|予約受付|発売|再販|抽選販売|お知らせ|重要)[:：\-\s]+", "", text)
    text = re.sub(r"\s+", " ", text).strip(" ｜|/-:：・")

    tokens = text.split(" ")
    while tokens and tokens[-1] in TRAILING_NOISE_WORDS:
        tokens.pop()
    return " ".join(tokens).strip(" ｜|/-:：・")


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

    for keyword, score in RELEASE_SIGNAL_SCORES.items():
        if keyword.lower() in haystack and keyword not in matched:
            matched.append(keyword)
            total_score += score
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
    if any(keyword in {"抽選販売", "販売終了", "再販なし", "在庫切れ"} for keyword in matched_keywords):
        probability += 10
    if any(keyword in {"限定", "完売"} for keyword in matched_keywords):
        probability += 5

    return max(1, min(99, probability))


def _classify_matched_keywords(matched_keywords: list[str]) -> list[str]:
    labels: list[str] = []

    if any(keyword in {"商品化", "登場", "発売", "予約受付開始", "予約受付中", "初商品化", "初の立体化", "初立体化"} for keyword in matched_keywords):
        labels.append("発売・商品化告知")
    if any(keyword in {"限定", "完売", "在庫切れ", "販売終了", "受注終了", "再販なし", "再販未定"} for keyword in matched_keywords):
        labels.append("供給制限・希少化")
    if any(keyword in {"抽選販売", "予約終了"} for keyword in matched_keywords):
        labels.append("入手難化")
    if any(keyword in {"限定", "抽選販売"} for keyword in matched_keywords):
        labels.append("話題化しやすい条件")
    return labels


def _describe_external_signals(external_signals: ExternalSignalSummary | None) -> list[str]:
    if not external_signals:
        return []

    labels: list[str] = []
    if external_signals.google_trend_score >= 60:
        labels.append(f"Google注目度が高い ({external_signals.google_trend_score})")
    elif external_signals.google_trend_score >= 30:
        labels.append(f"Google注目度が上向き ({external_signals.google_trend_score})")

    if external_signals.google_growth_pct >= 100:
        labels.append(f"検索需要が急伸 (+{external_signals.google_growth_pct}%)")
    elif external_signals.google_growth_pct > 0:
        labels.append(f"検索需要が増加 (+{external_signals.google_growth_pct}%)")

    if external_signals.social_mentions >= 100:
        labels.append(f"SNS言及が多い ({external_signals.social_mentions})")
    elif external_signals.social_mentions >= 10:
        labels.append(f"SNS言及が一定数ある ({external_signals.social_mentions})")

    if external_signals.social_buzz_score >= 20:
        labels.append(f"SNS反応が強い ({external_signals.social_buzz_score})")
    elif external_signals.social_buzz_score > 0:
        labels.append(f"SNS反応あり ({external_signals.social_buzz_score})")

    return labels


def build_reason(
    product_name: str,
    matched_keywords: list[str],
    matched_term: str,
    product_confidence: int,
    premium_probability: int = 0,
    external_signals: ExternalSignalSummary | None = None,
) -> str:
    parts = [f"商品候補: {product_name}"]
    if matched_term and clean_text(matched_term) != clean_text(product_name):
        parts.append(f"抽出元: {matched_term}")
    if matched_keywords:
        parts.append("検知キーワード: " + ", ".join(matched_keywords))

    keyword_groups = _classify_matched_keywords(matched_keywords)
    if keyword_groups:
        parts.append("プレ値要因: " + ", ".join(keyword_groups))

    if product_confidence >= 90:
        parts.append("商品との紐づきが強い")
    elif product_confidence >= 75:
        parts.append("商品との紐づきが中程度")
    else:
        parts.append("商品との紐づきが弱い")

    if premium_probability >= 80:
        parts.append("総合判定: 強いプレ値候補")
    elif premium_probability >= 50:
        parts.append("総合判定: プレ値候補")
    elif premium_probability > 0:
        parts.append("総合判定: 監視継続")

    external_labels = _describe_external_signals(external_signals)
    if external_labels:
        parts.append("外部信号: " + ", ".join(external_labels))

    if external_signals:
        parts.append(external_signals.summary)
    return "\n".join(parts)


def is_generic_page(text: str) -> bool:
    lowered = clean_text(text).lower()
    return any(marker.lower() in lowered for marker in GENERIC_TITLE_MARKERS)


def looks_like_product_name(candidate: str, source_name: str = "", strict: bool = True) -> bool:
    text = normalize_product_name(candidate)
    if not text:
        return False
    if any(phrase in text for phrase in STRICT_NON_PRODUCT_PHRASES):
        return False
    if is_generic_page(text):
        return False
    if text in ANNOUNCEMENT_WORDS:
        return False
    if any(marker in text for marker in SENTENCE_NOISE_MARKERS):
        return False

    source_text = normalize_product_name(source_name)
    if source_text and text == source_text:
        return False

    tokens = [part for part in re.split(r"[\s｜|/／:\-・]+", text) if part]
    if any(token in NON_PRODUCT_SECTION_WORDS for token in tokens):
        return False

    has_digit_or_latin = bool(re.search(r"[0-9A-Za-z]", text))
    has_hint = any(token in text for token in ("DX", "CSM", "BOX", "SET", "MEMORIAL", "EXTRA", "ver."))

    if not strict:
        return has_digit_or_latin or has_hint or len(text) >= 2

    if not has_digit_or_latin and not has_hint and len(tokens) < 2:
        return False

    if not has_digit_or_latin and any(
        token in CATEGORY_NOISE_WORDS or any(word in token for word in CATEGORY_NOISE_WORDS)
        for token in tokens
    ):
        return False

    return True


def split_on_separators(value: str) -> str:
    parts = re.split(r"[｜|/／:\-]", clean_text(value))
    cleaned = [normalize_product_name(part) for part in parts]
    cleaned = [part for part in cleaned if part]
    if not cleaned:
        return ""
    return max(cleaned, key=len)


def score_release_candidate(candidate: str) -> int:
    text = normalize_product_name(candidate)
    if not text:
        return 0

    score = 0
    if re.search(r"\d", text):
        score += 4
    if re.search(r"[A-Za-z]", text):
        score += 3
    if any(token in text for token in ("DX", "CSM", "ver.", "VER.", "MEMORIAL", "EXTRA", "SET", "BOX")):
        score += 3
    if any(token in text for token in ("(", ")", "・", " ", "-", "／", "/")):
        score += 1
    if len(text) >= 8:
        score += 2
    elif len(text) >= 5:
        score += 1
    return score


def extract_release_product_candidate(text: str, source_name: str = "") -> tuple[str | None, str, int]:
    title = clean_text(text)
    if not title or not any(keyword in title for keyword in RELEASE_KEYWORDS):
        return None, "", 0

    quoted_candidates: list[tuple[str, str]] = []
    for match in re.finditer(r"[「『](.+?)[」』]", title):
        quoted = normalize_product_name(match.group(1))
        if quoted:
            quoted_candidates.append((quoted, match.group(1)))

    if quoted_candidates:
        ranked = sorted(
            quoted_candidates,
            key=lambda item: score_release_candidate(item[0]),
            reverse=True,
        )
        for candidate, matched_term in ranked:
            if looks_like_product_name(candidate, source_name, strict=False):
                return candidate, matched_term, 96

    explicit_patterns = [
        r"(?P<product>[^「」『』。、！？\n]{2,80}?)(?:が|を)(?:[^。！？\n]{0,40}?)(?:商品化|登場|発売|予約受付開始|初商品化|初の立体化)",
        r"(?P<product>[^「」『』。、！？\n]{2,80}?)(?:が|を)\s*プレミアムバンダイで予約受付開始",
        r"(?P<product>[^「」『』。、！？\n]{2,80}?)(?:が|を)\s*商品化",
    ]
    for pattern in explicit_patterns:
        match = re.search(pattern, title)
        if not match:
            continue
        candidate = normalize_product_name(match.group("product"))
        candidate = candidate.split("より")[-1].strip()
        candidate = candidate.split("の")[-1].strip()
        candidate = split_on_separators(candidate) or candidate
        if looks_like_product_name(candidate, source_name, strict=False):
            return candidate, match.group("product"), 94

    return None, "", 0


def discover_product_name(entry: ParsedEntry, source: WatchSource) -> tuple[str | None, str, int]:
    title = clean_text(entry.title)
    summary = clean_text(entry.summary)
    source_name = clean_text(source.name)

    if is_generic_page(title) and not any(prefix in title for prefix in ANNOUNCEMENT_PREFIXES):
        return None, "", 0
    if not title and is_generic_page(summary):
        return None, "", 0

    candidates = [text for text in [title, summary] if text]

    for text in candidates:
        product_name, matched_term, confidence = extract_release_product_candidate(text, source_name)
        if product_name:
            return product_name, matched_term, confidence

    for text in candidates:
        for match in re.finditer(r"[「『](.+?)[」』]", text):
            quoted = normalize_product_name(match.group(1))
            if looks_like_product_name(quoted, source_name, strict=False):
                return quoted, match.group(1), 95

    for text in candidates:
        if not any(word in text for word in ANNOUNCEMENT_WORDS):
            continue
        candidate = split_on_separators(text)
        if looks_like_product_name(candidate, source_name):
            return candidate, text, 80

    for text in candidates:
        candidate = normalize_product_name(text)
        if looks_like_product_name(candidate, source_name):
            confidence = 72 if len(candidate) < 8 else 78
            return candidate, text, confidence

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
            premium_probability=premium_probability,
            external_signals=external_signals,
        ),
    }

    item, created = DetectedItem.objects.get_or_create(url=entry.url, defaults=defaults)
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


def fetch_html_document(url: str, fallback_name: str) -> tuple[ParsedEntry, BeautifulSoup]:
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": "Mozilla/5.0 (compatible; premium-monitor/1.0)"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    og_title = ""
    og_title_tag = soup.find("meta", attrs={"property": "og:title"})
    if og_title_tag and og_title_tag.get("content"):
        og_title = clean_text(og_title_tag.get("content"))

    page_heading = ""
    heading = soup.find(["h1", "h2"])
    if heading:
        page_heading = clean_text(heading.get_text(" ", strip=True))

    page_title = clean_text(soup.title.get_text(" ", strip=True) if soup.title else "")
    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_description = clean_text(meta_tag.get("content"))

    body_node = soup.body or soup
    body_text = clean_text(body_node.get_text(" ", strip=True))
    title = page_heading or og_title or page_title or fallback_name
    summary = truncate_text(meta_description or body_text)
    entry = ParsedEntry(
        title=title,
        url=response.url or url,
        summary=summary,
        published_at=None,
        text=" ".join(v for v in [title, og_title, page_title, meta_description, body_text] if v),
    )
    return entry, soup


def is_relevant_html_link(text: str, href: str) -> bool:
    combined = f"{clean_text(text)} {clean_text(href)}".lower()
    if not combined.strip():
        return False
    if combined.startswith("javascript:") or combined.startswith("mailto:"):
        return False
    if any(word.lower() in combined for word in HTML_LINK_HINT_WORDS):
        return True
    return bool(re.search(r"/(?:news|topics|release|press|product|item|goods|shop|campaign|detail|article|info)/", combined))


def score_html_link(text: str, href: str) -> int:
    combined = f"{clean_text(text)} {clean_text(href)}".lower()
    score = 0
    if re.search(r"/press/\d{4}/\d{2}/\d+", href):
        score += 50
    if re.search(r"/(?:news|topics|release|press|product|item|goods|shop|campaign|detail|article|info)/", href.lower()):
        score += 20
    if any(word.lower() in combined for word in ("商品", "予約", "発売", "再販", "限定", "抽選", "登場", "商品化", "立体化")):
        score += 15
    if re.search(r"\d{4}/\d{2}/\d{2}", text):
        score += 10
    if re.search(r"【|「|『", text):
        score += 10
    if any(word.lower() in combined for word in HTML_LINK_HINT_WORDS):
        score += 5
    return score


def extract_relevant_html_links(base_url: str, soup: BeautifulSoup) -> list[str]:
    base = urlparse(base_url)
    scored_links: list[tuple[int, str]] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = clean_text(anchor.get("href"))
        if not href or href.startswith("#"):
            continue

        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc and base.netloc and parsed.netloc != base.netloc:
            continue
        if absolute.rstrip("/") == base_url.rstrip("/"):
            continue

        anchor_text = clean_text(anchor.get_text(" ", strip=True))
        if not is_relevant_html_link(anchor_text, absolute):
            continue

        normalized = absolute.split("#", 1)[0]
        if normalized in seen:
            continue
        seen.add(normalized)
        scored_links.append((score_html_link(anchor_text, normalized), normalized))

    scored_links.sort(key=lambda item: item[0], reverse=True)
    links = [link for _, link in scored_links[:MAX_HTML_LINKS_PER_SOURCE]]
    return links


def fetch_source_entries(source: WatchSource) -> list[ParsedEntry]:
    if source.source_type == WatchSource.SOURCE_TYPE_RSS:
        return fetch_rss_entries(source)
    if source.source_type == WatchSource.SOURCE_TYPE_HTML:
        root_entry, soup = fetch_html_document(source.url, source.name)
        entries = [root_entry]
        for link in extract_relevant_html_links(root_entry.url, soup):
            try:
                child_entry, _ = fetch_html_document(link, source.name)
            except Exception:
                continue
            entries.append(child_entry)
        return entries
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
    pending_records: list[tuple[WatchSource, TrackedProduct, ParsedEntry, list[str], int, str, int]] = []

    for entry in entries:
        product_name, matched_term, product_confidence = discover_product_name(entry, source)
        if not product_name:
            unmatched_product_count += 1
            continue

        product = get_or_create_discovered_product(product_name)
        discovered_products.add(product.name)

        matched_keywords, total_score = detect_keywords(
            f"{entry.title}\n{entry.summary}\n{entry.text}",
            keywords,
        )
        if not matched_keywords:
            skipped_count += 1
            continue

        pending_records.append(
            (
                source,
                product,
                entry,
                matched_keywords,
                total_score,
                matched_term,
                product_confidence,
            )
        )

    if discovered_products:
        max_workers = min(4, len(discovered_products))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(collect_external_signals, product_name): product_name
                for product_name in discovered_products
            }
            for future in as_completed(future_map):
                product_name = future_map[future]
                try:
                    external_signal_cache[product_name] = future.result()
                except Exception:
                    external_signal_cache[product_name] = ExternalSignalSummary()

    for source_obj, product, entry, matched_keywords, total_score, matched_term, product_confidence in pending_records:
        external_signals = external_signal_cache.get(product.name)
        _, created = save_detected_item(
            source_obj,
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
