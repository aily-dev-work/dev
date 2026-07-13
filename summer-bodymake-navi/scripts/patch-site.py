#!/usr/bin/env python3
"""サイト全体への共通パッチ（スクリプト注入・季節表現・A8コメント除去）"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REPLACEMENTS = [
    ("夏までのロードマップを見る", "8週間ロードマップを見る"),
    ("30代男性が夏までに変わるロードマップ", "30代男性の男磨きロードマップ"),
    ("夏までに清潔感と体型を整える", "8週間で清潔感と体型を整える"),
    ("夏までの計画は", "8週間の計画は"),
    ("30代 夏 ロードマップ", "30代 男磨きロードマップ"),
    ("30代男性が夏までに変わる", "30代男性の男磨き"),
]

A8_COMMENT = re.compile(
    r"\s*<!-- A8[^>]*-->\s*\n?", re.IGNORECASE
)

ROOT_SCRIPTS = """  <script src="js/site-config.js"></script>
  <script src="js/analytics.js" defer></script>
  <script src="js/site.js" defer></script>"""

ARTICLE_SCRIPTS = """  <script src="../js/site-config.js"></script>
  <script src="../js/analytics.js" defer></script>
  <script src="../js/site.js" defer></script>"""

OLD_SCRIPTS = re.compile(
    r'\s*<script src="(?:\.\./)?js/main\.js" defer></script>\s*',
    re.IGNORECASE,
)


def patch_nav(html: str) -> str:
    html = html.replace(
        '<nav class="site-nav" aria-label="メインナビゲーション">',
        '<nav class="site-nav" id="site-nav" aria-label="メインナビゲーション">',
    )
    html = html.replace(
        '<nav class="site-nav"><ul>',
        '<nav class="site-nav" id="site-nav" aria-label="メインナビゲーション"><ul>',
    )
    return html


def inject_scripts(html: str, is_article: bool) -> str:
    html = OLD_SCRIPTS.sub("\n", html)
    marker = "js/site.js"
    if marker in html:
        return html
    scripts = ARTICLE_SCRIPTS if is_article else ROOT_SCRIPTS
    if "</body>" not in html:
        return html
    return html.replace("</body>", scripts + "\n</body>", 1)


def patch_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text

    for old, new in REPLACEMENTS:
        text = text.replace(old, new)

    text = A8_COMMENT.sub("\n", text)
    text = patch_nav(text)
    text = inject_scripts(text, path.parent.name == "articles")

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = []
    for path in sorted(ROOT.rglob("*.html")):
        if path.parent.name == "scripts":
            continue
        if patch_file(path):
            changed.append(path.relative_to(ROOT))
    print(f"Patched {len(changed)} file(s)")
    for p in changed:
        print(f"  - {p}")


if __name__ == "__main__":
    main()
