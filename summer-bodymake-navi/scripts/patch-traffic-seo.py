#!/usr/bin/env python3
"""One-off traffic SEO patches."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GTAG_BLOCK = re.compile(
    r"\n  <!-- Google tag \(gtag\.js\) -->\n"
    r'  <script async src="https://www\.googletagmanager\.com/gtag/js\?id=G-HZPREEZSHM"></script>\n'
    r"  <script>\n"
    r"    window\.dataLayer = window\.dataLayer \|\| \[\];\n"
    r"    function gtag\(\)\{dataLayer\.push\(arguments\);\}\n"
    r"    gtag\('js', new Date\(\)\);\n"
    r"    gtag\('config', 'G-HZPREEZSHM'\);\n"
    r"  </script>\n",
    re.MULTILINE,
)


def patch_index() -> None:
    path = ROOT / "index.html"
    text = path.read_text(encoding="utf-8")
    text = GTAG_BLOCK.sub("\n", text, count=1)
    text = text.replace(
        "<title>メンズ男磨きナビ｜脱毛・ジム・日焼け止めで清潔感を整える</title>",
        "<title>メンズ脱毛・ジム・日焼け止め｜男磨きの始め方とおすすめ比較</title>",
    )
    text = text.replace(
        'content="清潔感と印象を整えたい男性へ。メンズ脱毛、ジム、日焼け止め・スキンケアの始め方を検索意図別に解説。料金相場や続け方も紹介します。"',
        'content="メンズ脱毛の料金・おすすめクリニック、ジム初心者メニュー、男性向け日焼け止めを比較。清潔感を上げる優先順位と今週の一歩がわかる男磨きガイド。"',
    )
    if 'id="search-intent-heading"' not in text:
        needle = '      <section class="popular-articles" aria-labelledby="popular-heading">'
        insert = """      <section class="popular-articles" aria-labelledby="search-intent-heading">
        <h2 id="search-intent-heading" class="section-title">よくある検索から読む</h2>
        <p>Googleで検索される悩みに合わせて記事を用意しています。気になる文言から入ってください。</p>
        <ul class="article-link-grid">
          <li><a href="articles/medical-hair-removal-ranking.html">メンズ医療脱毛 おすすめ</a></li>
          <li><a href="articles/mens-hair-removal-cost.html">メンズ脱毛 料金 相場</a></li>
          <li><a href="articles/beard-hair-removal-men.html">ヒゲ脱毛 メンズ おすすめ</a></li>
          <li><a href="articles/mens-sunscreen-recommend.html">男性 日焼け止め おすすめ</a></li>
          <li><a href="articles/gym-beginner-men.html">ジム 初心者 男 メニュー</a></li>
          <li><a href="articles/clean-impression-men.html">清潔感のある男性 なるには</a></li>
        </ul>
      </section>

"""
        if needle not in text:
            raise SystemExit("popular-articles section not found")
        text = text.replace(needle, insert + needle, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path.relative_to(ROOT))


def patch_articles_index() -> None:
    path = ROOT / "articles" / "index.html"
    text = path.read_text(encoding="utf-8")
    text2, n = GTAG_BLOCK.subn("\n", text, count=1)
    if n != 1:
        raise SystemExit(f"expected 1 gtag block in articles/index, got {n}")
    path.write_text(text2, encoding="utf-8")
    print("patched", path.relative_to(ROOT))


def patch_sitemap_home() -> None:
    path = ROOT / "sitemap.xml"
    text = path.read_text(encoding="utf-8")
    text2, n = re.subn(
        r"(<loc>https://mens-body\.com/</loc>\s*<lastmod>)[^<]+",
        r"\g<1>2026-07-14",
        text,
        count=1,
    )
    if n != 1:
        raise SystemExit("sitemap home lastmod not updated")
    path.write_text(text2, encoding="utf-8")
    print("patched sitemap home lastmod")


if __name__ == "__main__":
    patch_index()
    patch_articles_index()
    patch_sitemap_home()
