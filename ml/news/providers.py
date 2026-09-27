"""News provider abstraction (ML Pipeline §7). Providers return normalised items; no scraping of article pages."""
from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

from ml import config
from ml.data.sessions import iso, to_utc
from ml.news.preprocessing import clean_text, news_id_for

logger = logging.getLogger(__name__)


class NewsProviderError(RuntimeError):
    pass


class NewsProvider:
    name = "base"
    is_demo = False

    def search(self, query: str, days: int = 30) -> list[dict]:
        raise NotImplementedError


class GoogleNewsRssProvider(NewsProvider):
    """Google News RSS search feed: headline, source, link and publication time (no article bodies)."""

    name = "google_news_rss"
    url = "https://news.google.com/rss/search"

    def search(self, query: str, days: int = 30) -> list[dict]:
        params = {"q": f'"{query}" when:{days}d', "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
        try:
            response = requests.get(self.url, params=params, headers={"User-Agent": "Mozilla/5.0 (Aventra research prototype)"}, timeout=config.PROVIDER_TIMEOUT_SECONDS)
            response.raise_for_status()
            root = ET.fromstring(response.content)
        except (requests.RequestException, ET.ParseError) as error:
            raise NewsProviderError("News provider is unavailable.") from error
        items = []
        for node in root.iter("item"):
            title = clean_text(node.findtext("title"))
            source = clean_text(node.findtext("source")) or None
            if source and title.endswith(f" - {source}"):
                title = title[: -len(source) - 3].strip()
            try:
                published = to_utc(parsedate_to_datetime(node.findtext("pubDate") or ""))
            except (TypeError, ValueError):
                continue   # an item without a usable timestamp cannot be aligned — drop it
            if not title:
                continue
            items.append({"news_id": news_id_for(title, source), "headline": title, "summary": None, "source": source, "url": node.findtext("link"), "published_at": iso(published), "provider": self.name, "is_demo": False})
        return items


class DemoNewsProvider(NewsProvider):
    """SYNTHETIC headlines from data/demo/news.json (clearly labelled demo content)."""

    name = "aventra_demo_dataset"
    is_demo = True

    def search(self, query: str, days: int = 30) -> list[dict]:
        path = config.DEMO_DIR / "news.json"
        if not path.is_file():
            raise NewsProviderError("Demo news dataset is missing. Run: py -3.12 -m scripts.generate_demo_data")
        records = json.loads(path.read_text(encoding="utf-8"))["items"]
        return [{**item, "provider": self.name, "is_demo": True} for item in records]


def news_provider_for(symbol: str) -> NewsProvider:
    if symbol == "DEMO" or config.data_mode() == "demo":
        return DemoNewsProvider()
    return GoogleNewsRssProvider()
