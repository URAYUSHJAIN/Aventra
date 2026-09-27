"""News text normalisation and de-duplication (ML Pipeline §12). Originals are preserved for evidence."""
from __future__ import annotations

import hashlib
import html
import re
import unicodedata

_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", html.unescape(_TAG.sub(" ", text)))
    return _SPACE.sub(" ", text).strip()


def normalise_headline(headline: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", clean_text(headline).lower())


def news_id_for(headline: str, source: str | None) -> str:
    digest = hashlib.sha1(f"{normalise_headline(headline)}|{(source or '').lower()}".encode("utf-8")).hexdigest()
    return f"N{digest[:15]}"


def deduplicate(items: list[dict]) -> tuple[list[dict], int]:
    """Drop items with an empty headline or a repeated URL / normalised headline. Returns (kept, removed_count)."""
    seen_urls, seen_titles, kept = set(), set(), []
    for item in items:
        title = normalise_headline(item.get("headline", ""))
        url = (item.get("url") or "").strip()
        if not title or title in seen_titles or (url and url in seen_urls):
            continue
        seen_titles.add(title)
        if url:
            seen_urls.add(url)
        kept.append(item)
    return kept, len(items) - len(kept)
