"""Phase 7: permitted news provider (Alpha Vantage NEWS_SENTIMENT), explicit tags, unavailable states."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from ml import config
from ml.data import cache, db, migrate, store
from ml.instruments import master
from ml.news.ingest import ingest_news
from ml.news.providers import AlphaVantageNewsProvider, NewsProviderError, av_tickers, news_provider_for
from ml.providers import http

FEED = {"items": "2", "feed": [
    {"title": "Apple unveils new chip", "url": "https://example.com/a", "time_published": "20260926T143000", "summary": "…", "source": "Benzinga",
     "ticker_sentiment": [{"ticker": "AAPL", "relevance_score": "0.91"}]},
    {"title": "Qualcomm earnings beat", "url": "https://example.com/b", "time_published": "20260926T150000", "summary": "…", "source": "MarketBeat",
     "ticker_sentiment": [{"ticker": "QCOM", "relevance_score": "0.95"}, {"ticker": "AAPL", "relevance_score": "0.12"}]},
]}


def response(body):
    r = requests.Response()
    r.status_code, r._content = 200, json.dumps(body).encode()
    return r


def instrument(iid, cls, exchange, symbol, name):
    return {"instrument_id": iid, "asset_class": cls, "exchange": exchange, "symbol": symbol, "name": name}


class NewsProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(config, "DB_PATH", Path(self.tmp.name) / "n.sqlite3"), patch("time.sleep")]
        for p in self.patches:
            p.start()
        migrate.upgrade()
        http.reset_state()
        cache.invalidate()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        cache.invalidate()
        db.dispose_engines()
        self.tmp.cleanup()

    def test_ticker_mapping_per_asset_class(self):
        self.assertEqual(av_tickers(instrument("XNAS:AAPL", "equity", "XNAS", "AAPL", "Apple")), ["AAPL"])
        self.assertEqual(av_tickers(instrument("CRYPTO:BTC-USDT", "crypto", "BINANCE", "BTCUSDT", "BTC / USDT")), ["CRYPTO:BTC"])
        self.assertEqual(av_tickers(instrument("FX:USDINR", "forex", "FX", "USDINR", "USD/INR")), ["FOREX:USD", "FOREX:INR"])
        self.assertIsNone(av_tickers(instrument("XNSE:RELIANCE", "equity", "XNSE", "RELIANCE", "Reliance")))
        self.assertIsNone(av_tickers(instrument("MF-IN:1", "mutual_fund", "AMFI", "1", "Fund")))

    def test_parsing_and_explicit_links_respect_relevance(self):
        with patch.dict(os.environ, {"ALPHAVANTAGE_API_KEY": "k"}), patch("requests.request", return_value=response(FEED)):
            items = AlphaVantageNewsProvider().search(instrument("XNAS:AAPL", "equity", "XNAS", "AAPL", "Apple Inc."))
        self.assertEqual([i["instrument_ids"] for i in items], [["XNAS:AAPL"], []])   # 0.12 relevance is not an explicit link
        self.assertEqual(items[0]["published_at"], "2026-09-26T14:30:00Z")

    def test_missing_key_raises_unavailable(self):
        with patch.dict(os.environ, {"ALPHAVANTAGE_API_KEY": ""}):
            with self.assertRaises(NewsProviderError):
                AlphaVantageNewsProvider().search(instrument("XNAS:AAPL", "equity", "XNAS", "AAPL", "Apple Inc."))

    def test_ingest_states(self):
        store.upsert_instruments([master.instrument_row("XNSE:RELIANCE", "RELIANCE", "Reliance Industries", "equity", "XNSE", country="IN", source="t", class_source="t", class_confidence=1),
                                  master.instrument_row("XNAS:AAPL", "AAPL", "Apple Inc.", "equity", "XNAS", country="US", source="t", class_source="t", class_confidence=1)],
                                 master.alias_rows("XNAS:AAPL", strong=["Apple"], tickers=["AAPL"]))
        report = ingest_news("XNSE:RELIANCE", store.get_instrument("XNSE:RELIANCE"))
        self.assertEqual((report["status"], report["reason"]), ("unavailable", "NO_NEWS_PROVIDER_FOR_ASSET"))
        with patch.dict(os.environ, {"ALPHAVANTAGE_API_KEY": ""}):
            self.assertEqual(ingest_news("XNAS:AAPL", store.get_instrument("XNAS:AAPL"))["status"], "unavailable")
        with patch.dict(os.environ, {"ALPHAVANTAGE_API_KEY": "k"}), patch("requests.request", return_value=response(FEED)), \
             patch("ml.news.ingest.get_news_analysis_service") as finbert:
            finbert.return_value.analyze_many.return_value = [{"label": "positive", "positive_probability": 0.8, "neutral_probability": 0.15,
                                                               "negative_probability": 0.05, "sentiment_score": 0.75, "confidence": 0.8, "model": "ProsusAI/finBERT"}]
            report = ingest_news("XNAS:AAPL", store.get_instrument("XNAS:AAPL"))
        self.assertEqual(report["status"], "ok")
        self.assertEqual([i["headline"] for i in report["items"]], ["Apple unveils new chip"])   # the QCOM story is not linked to AAPL
        self.assertEqual(report["items"][0]["sentiment"]["label"], "positive")

    def test_google_news_is_not_a_production_provider(self):
        provider, _ = news_provider_for(instrument("XNAS:AAPL", "equity", "XNAS", "AAPL", "Apple"))
        self.assertEqual(provider.name, "alpha_vantage_news")


if __name__ == "__main__":
    unittest.main()
