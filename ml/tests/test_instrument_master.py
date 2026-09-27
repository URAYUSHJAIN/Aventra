"""Phase 1: canonical IDs, Alembic migrations (incl. v0.1 legacy import), store round-trips and master search."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from ml import config
from ml.data import migrate, store
from ml.instruments import ids, master


class TempDatabase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "t.sqlite3"
        self.patch = patch.object(config, "DB_PATH", self.db_path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        from ml.data import db
        db.dispose_engines()   # release file handles before the temp dir is removed
        self.tmp.cleanup()


class IdTests(unittest.TestCase):
    def test_parse_and_normalise(self):
        self.assertEqual(str(ids.parse("xnse:reliance")), "XNSE:RELIANCE")
        self.assertEqual(str(ids.parse("RELIANCE")), "XNSE:RELIANCE")            # legacy bare symbol
        self.assertEqual(str(ids.parse("reliance.ns")), "XNSE:RELIANCE")
        self.assertEqual(str(ids.parse("CRYPTO:CG-bitcoin")), "CRYPTO:CG-bitcoin")  # case preserved for crypto
        self.assertEqual(str(ids.parse("FX:usdinr")), "FX:USDINR")
        self.assertEqual(ids.safe_key("IDX:^GSPC"), "IDX__GSPC")

    def test_rejects_unsafe_input(self):
        for bad in ("", "BAD:ID", "XNSE:A B", "XNSE:../etc", "X" * 90, "XNSE:DROP TABLE", "http://x"):
            with self.assertRaises(ids.InvalidInstrumentId, msg=bad):
                ids.parse(bad)
        with self.assertRaises(ids.InvalidInstrumentId):
            ids.parse("RELIANCE", allow_legacy=False)


class MigrationTests(TempDatabase):
    def test_fresh_database_migrates_to_head(self):
        migrate.upgrade()
        con = sqlite3.connect(self.db_path)
        tables = {t for (t,) in con.execute("select name from sqlite_master where type='table'")}
        self.assertTrue({"instruments", "instrument_aliases", "provider_symbols", "prices", "news", "sentiment", "jobs", "watchlists", "analysis_runs"} <= tables)
        from alembic.script import ScriptDirectory
        head = ScriptDirectory.from_config(migrate.alembic_config()).get_current_head()
        version = con.execute("select version_num from alembic_version").fetchone()[0]
        con.close()
        self.assertEqual(version, head)
        migrate.upgrade()   # idempotent

    def test_v01_database_is_preserved_and_imported(self):
        con = sqlite3.connect(self.db_path)
        con.executescript("""
            CREATE TABLE prices (symbol TEXT, timestamp TEXT, open REAL, high REAL, low REAL, close REAL, adj_close REAL, volume REAL, source TEXT, fetched_at TEXT, PRIMARY KEY (symbol, timestamp));
            CREATE TABLE news (news_id TEXT PRIMARY KEY, headline TEXT, summary TEXT, source TEXT, url TEXT, published_at TEXT, provider TEXT, is_demo INTEGER, fetched_at TEXT);
            CREATE TABLE news_links (news_id TEXT, symbol TEXT, entity_match_confidence REAL, mapping_method TEXT, PRIMARY KEY (news_id, symbol));
            CREATE TABLE news_sentiment (news_id TEXT PRIMARY KEY, label TEXT, positive_probability REAL, neutral_probability REAL, negative_probability REAL, sentiment_score REAL, confidence REAL, model TEXT, model_version TEXT, analysed_at TEXT);
            CREATE INDEX idx_news_published ON news (published_at);
            INSERT INTO prices VALUES ('TCS','2026-09-25T03:45:00Z',1,2,0.5,1.5,1.5,100,'yahoo_finance_chart','2026-09-26T00:00:00Z');
            INSERT INTO prices VALUES ('DEMO','2026-09-25T03:45:00Z',1,2,0.5,1.5,1.5,100,'aventra_demo_dataset','2026-09-26T00:00:00Z');
            INSERT INTO news VALUES ('N1','TCS wins deal',NULL,'Src','u','2026-09-25T05:00:00Z','google_news_rss',0,'2026-09-25T06:00:00Z');
            INSERT INTO news VALUES ('N2','Synthetic',NULL,'Demo',NULL,'2026-09-25T05:00:00Z','aventra_demo_dataset',1,'2026-09-25T06:00:00Z');
            INSERT INTO news_links VALUES ('N1','TCS',0.95,'strong_alias');
            INSERT INTO news_links VALUES ('N2','DEMO',1.0,'explicit_metadata');
            INSERT INTO news_sentiment VALUES ('N1','positive',0.9,0.05,0.05,0.85,0.9,'ProsusAI/finBERT','v','2026-09-25T06:00:00Z');
        """)
        con.commit(); con.close()
        migrate.upgrade()
        con = sqlite3.connect(self.db_path)
        self.assertEqual(con.execute("select count(*) from legacy_prices").fetchone()[0], 2)     # nothing dropped
        self.assertEqual(con.execute("select instrument_id, provider, quality from prices").fetchall(), [("XNSE:TCS", "yahoo_finance_chart", "legacy")])
        self.assertEqual(con.execute("select news_id from news").fetchall(), [("N1",)])       # synthetic item not imported
        self.assertEqual(con.execute("select instrument_id from news_links").fetchall(), [("XNSE:TCS",)])
        con.close()
        self.assertTrue(store.load_prices("XNSE:TCS").empty)                                  # legacy Yahoo rows never served
        self.assertEqual(len(store.load_prices("XNSE:TCS", providers={"yahoo_finance_chart"})), 1)
        self.assertEqual(store.load_news("XNSE:TCS"), [])                                    # legacy Google News rows stored but never served (C23)
        self.assertEqual(store.sentiment_for(["N1"])["N1"]["label"], "positive")              # …their FinBERT output is preserved


class StoreAndSearchTests(TempDatabase):
    def setUp(self):
        super().setUp()
        migrate.upgrade()
        rows = [
            master.instrument_row("XNSE:RELIANCE", "RELIANCE", "Reliance Industries Ltd", "equity", "XNSE", country="IN", currency="INR", source="t", class_source="t", class_confidence=1.0),
            master.instrument_row("XNSE:RPOWER", "RPOWER", "Reliance Power Ltd", "equity", "XNSE", country="IN", currency="INR", source="t", class_source="t", class_confidence=1.0),
            master.instrument_row("XNAS:AAPL", "AAPL", "Apple Inc.", "equity", "XNAS", country="US", currency="USD", source="t", class_source="t", class_confidence=1.0),
            master.instrument_row("CRYPTO:BTC-USDT", "BTCUSDT", "Bitcoin / TetherUS", "crypto", "BINANCE", currency="USDT", source="t", class_source="t", class_confidence=1.0),
        ]
        aliases = master.alias_rows("XNSE:RELIANCE", strong=["Reliance Industries", "RIL"], exclude=["Reliance Power"], tickers=["RELIANCE"])
        aliases += master.alias_rows("CRYPTO:BTC-USDT", strong=["Bitcoin"], tickers=["BTC"])
        providers = [{"instrument_id": "XNAS:AAPL", "provider": "alpha_vantage", "provider_symbol": "AAPL", "priority": 10}]
        store.upsert_instruments(rows, aliases, providers)

    def test_instrument_round_trip_and_capabilities(self):
        row = master.get("XNSE:RELIANCE")
        self.assertEqual(row["timezone"], "Asia/Kolkata")
        self.assertEqual(row["calendar_code"], "XBOM")
        self.assertTrue(row["capabilities"]["has_volume"])
        self.assertEqual(master.get("XNAS:AAPL")["providers"][0]["provider_symbol"], "AAPL")
        self.assertEqual(master.get("CRYPTO:BTC-USDT")["calendar_code"], "24/7")

    def test_search_ranking_filters_and_pagination(self):
        items = master.search("reliance")["items"]
        self.assertEqual(items[0]["instrument_id"], "XNSE:RELIANCE")                         # exact symbol first
        self.assertIn("XNSE:RPOWER", [i["instrument_id"] for i in items])
        self.assertEqual(master.search("bitcoin")["items"][0]["instrument_id"], "CRYPTO:BTC-USDT")   # alias match
        self.assertEqual(master.search("apple")["items"][0]["instrument_id"], "XNAS:AAPL")          # name prefix
        self.assertEqual([i["instrument_id"] for i in master.search("reliance", country="US")["items"]], [])
        page1 = master.search("l", limit=1)
        self.assertEqual(len(page1["items"]), 1)
        page2 = master.search("l", limit=1, cursor=page1["next_cursor"])
        self.assertNotEqual(page1["items"][0]["instrument_id"], page2["items"][0]["instrument_id"])
        self.assertEqual(master.search("")["items"], [])
        self.assertEqual(master.search("%' OR 1=1 --")["items"], [])                         # no SQL injection effect

    def test_prices_store_provenance(self):
        frame = pd.DataFrame([{"instrument_id": "XNAS:AAPL", "interval": "1d", "timestamp": "2026-09-25T13:30:00Z", "open": 1, "high": 2, "low": 0.5,
                               "close": 1.5, "volume": 10, "provider": "alpha_vantage", "provider_symbol": "AAPL", "currency": "USD", "timezone": "America/New_York"}])
        store.upsert_prices(frame)
        store.upsert_prices(frame.assign(close=1.6))                                         # upsert, no duplicate
        loaded = store.load_prices("XNAS:AAPL")
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded["close"].iloc[0], 1.6)
        self.assertEqual(loaded["provider"].iloc[0], "alpha_vantage")
        self.assertEqual(str(loaded["timestamp"].iloc[0].tz), "UTC")

    def test_watchlist_comes_from_configuration(self):
        with patch.dict("os.environ", {"AVENTRA_DEFAULT_WATCHLIST": "XNAS:AAPL, bad id, CRYPTO:BTC-USDT"}):
            self.assertEqual(master.ensure_default_watchlist(), ["XNAS:AAPL", "CRYPTO:BTC-USDT"])
        self.assertEqual(store.get_watchlist()["items"], ["XNAS:AAPL", "CRYPTO:BTC-USDT"])

    def test_reference_seed_skips_synthetic_asset(self):
        self.assertEqual(master.seed_from_reference(), 5)
        self.assertIsNone(store.get_instrument("XNSE:DEMO"))
        self.assertIn("Reliance Power", [a["alias"] for a in master.get("XNSE:RELIANCE")["aliases"] if a["kind"] == "exclude"])


if __name__ == "__main__":
    unittest.main()
