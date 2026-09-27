"""Phase 2: provider parsing, routing and failure handling with mocked HTTP (no network)."""
import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from ml import config
from ml.data import db, migrate, store
from ml.instruments import master
from ml.providers import http, registry
from ml.providers.alpha_vantage import AlphaVantageProvider
from ml.providers.base import InstrumentNotSupported, MalformedResponse, ProviderUnavailable, RateLimited
from ml.providers.crypto import BinanceProvider
from ml.providers.funds_and_reference import AmfiProvider, MfapiProvider, refine_class_from_figi
from ml.providers.reference_rates import FredProvider, FrankfurterProvider
from ml.providers.upstox import UpstoxProvider, classify


def response(status=200, body=None, text=None, headers=None, content=None):
    r = requests.Response()
    r.status_code = status
    r._content = content if content is not None else (text.encode() if text is not None else json.dumps(body).encode())
    r.headers.update(headers or {})
    return r


class ProviderTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(config, "DB_PATH", Path(self.tmp.name) / "p.sqlite3"), patch("time.sleep")]
        for p in self.patches:
            p.start()
        migrate.upgrade()
        http.reset_state()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        db.dispose_engines()
        self.tmp.cleanup()


class ParsingTests(ProviderTestCase):
    def test_binance_klines_normalised(self):
        klines = [[1726099200000, "1", "2", "0.5", "1.5", "10", 0, "0", 1, "0", "0", "0"], [1726185600000, "1.5", "2", "1", "1.8", "12", 0, "0", 1, "0", "0", "0"]]
        with patch("requests.request", return_value=response(body=klines)):
            series = BinanceProvider().history({"currency": "USDT"}, "BTCUSDT")
        self.assertEqual(len(series.frame), 2)
        self.assertEqual(str(series.frame["timestamp"].dt.tz), "UTC")
        self.assertEqual(series.frame["close"].tolist(), [1.5, 1.8])

    def test_frankfurter_close_only_series(self):
        body = {"rates": {"2026-09-24": {"INR": 83.1}, "2026-09-25": {"INR": 83.3}}}
        with patch("requests.request", return_value=response(body=body)):
            series = FrankfurterProvider().history({}, "USDINR")
        self.assertEqual(series.value_kind, "reference_rate")
        self.assertTrue(series.frame["open"].isna().all() and series.frame["volume"].isna().all())   # no fake OHLC/volume
        self.assertEqual(series.frame["close"].tolist(), [83.1, 83.3])

    def test_mfapi_nav_series(self):
        body = {"meta": {"scheme_name": "X"}, "data": [{"date": "25-09-2026", "nav": "29.69"}, {"date": "24-09-2026", "nav": "29.50"}]}
        with patch("requests.request", return_value=response(body=body)):
            series = MfapiProvider().history({}, "135762")
        self.assertEqual(series.value_kind, "nav")
        self.assertEqual(series.frame["close"].tolist(), [29.50, 29.69])

    def test_amfi_listing_marks_stale_schemes_inactive(self):
        text = ("Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date\n"
                "135762;INF846K01WO1;-;Axis Children's Fund;Direct Plan;Growth Option;29.6905;25-Sep-2099\n"
                "111989;INF209K01R47;-;Old Fund;Regular Plan;Growth;10.3;16-Sep-2022\n")
        with patch("requests.request", return_value=response(text=text)):
            rows, _, maps = AmfiProvider().list_instruments()
        status = {r["instrument_id"]: r["status"] for r in rows}
        self.assertEqual(status, {"MF-IN:135762": "listed", "MF-IN:111989": "inactive"})
        self.assertEqual({m["provider"] for m in maps}, {"mfapi", "amfi"})

    def test_upstox_classification(self):
        self.assertEqual(classify("NSE_EQ", "EQ", "RELIANCE INDUSTRIES LTD", "RELIANCE")[0], "equity")
        self.assertEqual(classify("NSE_EQ", "EQ", "NIP IND ETF NIFTY BEES", "NIFTYBEES")[0], "etf")
        self.assertEqual(classify("NSE_EQ", "RR", "EMBASSY OFFICE PARKS REIT", "EMBASSY")[0], "reit")
        self.assertEqual(classify("NSE_EQ", "IV", "IRB INVIT FUND", "IRBINVIT")[0], "invit")
        self.assertEqual(classify("NSE_EQ", "GS", "GOI LOAN 7.26% 2033", "726GS2033")[0], "bond")
        self.assertEqual(classify("BSE_EQ", "F", "IRFC-7.75%-15-4-33-PVT", "775IRFC33")[0], "bond")

    def test_upstox_listing_ids_and_mappings(self):
        data = [{"segment": "NSE_EQ", "instrument_type": "EQ", "trading_symbol": "RELIANCE", "name": "RELIANCE INDUSTRIES LTD", "instrument_key": "NSE_EQ|INE002A01018", "isin": "INE002A01018"},
                {"segment": "BSE_EQ", "instrument_type": "A", "trading_symbol": "RELIANCE", "exchange_token": "500325", "name": "RELIANCE INDUSTRIES LTD.", "instrument_key": "BSE_EQ|INE002A01018"},
                {"segment": "NSE_INDEX", "instrument_type": "INDEX", "trading_symbol": "NIFTY 50", "name": "Nifty 50", "instrument_key": "NSE_INDEX|Nifty 50"},
                {"segment": "NSE_FO", "instrument_type": "CE", "trading_symbol": "X", "name": "X", "instrument_key": "NSE_FO|1"}]
        with patch("requests.request", return_value=response(content=gzip.compress(json.dumps(data).encode()))):
            rows, _, maps = UpstoxProvider().list_instruments()
        self.assertEqual([r["instrument_id"] for r in rows], ["XNSE:RELIANCE", "XBOM:500325", "IDX:NSE-NIFTY50"])   # derivatives skipped
        self.assertEqual(maps[0]["provider_symbol"], "NSE_EQ|INE002A01018")

    def test_openfigi_refines_class(self):
        self.assertEqual(refine_class_from_figi([{"exchCode": "IN", "securityType": "ETP"}]), ("etf", 0.95))
        self.assertIsNone(refine_class_from_figi([{"exchCode": "US", "securityType": "ETP"}]))


class FailureTests(ProviderTestCase):
    def test_missing_credentials_is_provider_unavailable(self):
        with patch.dict("os.environ", {"ALPHAVANTAGE_API_KEY": "", "UPSTOX_ACCESS_TOKEN": "", "FRED_API_KEY": ""}):
            for provider in (AlphaVantageProvider(), UpstoxProvider(), FredProvider()):
                self.assertEqual(provider.available(), (False, "missing_credentials"))
                with self.assertRaises(ProviderUnavailable):
                    provider.require_available()

    def test_rate_limit_honours_retry_after_then_raises(self):
        with patch("requests.request", return_value=response(429, {"msg": "slow down"}, headers={"Retry-After": "3"})) as mocked:
            with self.assertRaises(RateLimited):
                http.request("binance", "klines", "https://x", per_minute=600)
        self.assertEqual(mocked.call_count, 3)   # initial + 2 retries

    def test_malformed_response(self):
        with patch("requests.request", return_value=response(text="<html>oops</html>")):
            with self.assertRaises(MalformedResponse):
                BinanceProvider().history({"currency": "USDT"}, "BTCUSDT")

    def test_unknown_instrument(self):
        with patch("requests.request", return_value=response(400, {"code": -1121, "msg": "Invalid symbol."})):
            with self.assertRaises(InstrumentNotSupported):
                BinanceProvider().history({}, "NOPEUSDT")

    def test_alpha_vantage_messages(self):
        with patch.dict("os.environ", {"ALPHAVANTAGE_API_KEY": "k"}):
            with patch("requests.request", return_value=response(body={"Error Message": "Invalid API call."})):
                with self.assertRaises(InstrumentNotSupported):
                    AlphaVantageProvider().history({"calendar_code": "XNYS"}, "NOPE")
            with patch("requests.request", return_value=response(body={"Note": "Thank you for using Alpha Vantage! Our standard API rate limit is 25 requests per day."})):
                with self.assertRaises(RateLimited):
                    AlphaVantageProvider().history({"calendar_code": "XNYS"}, "IBM")

    def test_daily_budget_is_enforced_across_calls(self):
        for _ in range(3):
            store.record_provider_call("alpha_vantage", "TIME_SERIES_DAILY", "ok", 200, 10)
        with self.assertRaises(ProviderUnavailable) as ctx:
            http.request("alpha_vantage", "TIME_SERIES_DAILY", "https://x", per_minute=5, daily_budget=3)
        self.assertEqual(ctx.exception.reason, "budget_exhausted")

    def test_circuit_breaker_opens_after_repeated_failures(self):
        with patch("requests.request", side_effect=requests.ConnectionError("down")):
            for _ in range(2):
                with self.assertRaises(ProviderUnavailable):
                    http.request("frankfurter", "t", "https://x", per_minute=600, retries=2)
        with self.assertRaises(ProviderUnavailable) as ctx:
            http.request("frankfurter", "t", "https://x", per_minute=600)
        self.assertEqual(ctx.exception.reason, "circuit_open")


class RouterTests(ProviderTestCase):
    def _fx_instrument(self):
        rows = [master.instrument_row("FX:USDINR", "USDINR", "US Dollar / Indian Rupee", "forex", "FX", currency="INR", source="t", class_source="t", class_confidence=1)]
        maps = [{"instrument_id": "FX:USDINR", "provider": "frankfurter", "provider_symbol": "USDINR", "priority": 10},
                {"instrument_id": "FX:USDINR", "provider": "ecb", "provider_symbol": "USDINR", "priority": 20}]
        store.upsert_instruments(rows, [], maps)
        return store.get_instrument("FX:USDINR")

    def test_falls_back_to_next_legitimate_provider(self):
        instrument = self._fx_instrument()
        ecb_csv = "TIME_PERIOD,OBS_VALUE\n2026-09-24,90.1\n2026-09-25,90.2\n"
        usd_csv = "TIME_PERIOD,OBS_VALUE\n2026-09-24,1.10\n2026-09-25,1.12\n"

        def fake(method, url, **kwargs):
            if "frankfurter" in url:
                return response(500, {"message": "down"})
            return response(text=ecb_csv if ".INR." in url else usd_csv)
        with patch("requests.request", side_effect=fake):
            series, attempts = registry.fetch_history(instrument)
        self.assertEqual(series.provider, "ecb")
        self.assertEqual([a["status"] for a in attempts], ["PROVIDER_UNAVAILABLE", "OK"])
        self.assertAlmostEqual(series.frame["close"].iloc[-1], 90.2 / 1.12)   # genuine cross of two EUR reference rates

    def test_no_provider_and_missing_credentials_are_explicit(self):
        store.upsert_instruments([master.instrument_row("XNAS:AAPL", "AAPL", "Apple Inc.", "equity", "XNAS", country="US", currency="USD", source="t", class_source="t", class_confidence=1)])
        with patch.dict("os.environ", {"ALPHAVANTAGE_API_KEY": ""}):
            with self.assertRaises(registry.DataUnavailable) as ctx:
                registry.fetch_history(store.get_instrument("XNAS:AAPL"))
        self.assertEqual(ctx.exception.code, "PROVIDER_UNAVAILABLE")
        self.assertIn("ALPHAVANTAGE_API_KEY", ctx.exception.attempts[0]["detail"])
        with self.assertRaises(registry.DataUnavailable) as ctx:
            registry.fetch_history({"asset_class": "equity", "exchange": "XLON", "providers": []})
        self.assertEqual(ctx.exception.code, "NO_PROVIDER_FOR_ASSET")

    def test_yahoo_is_not_registered_and_synthetic_only_in_tests(self):
        self.assertNotIn("yahoo_finance_chart", registry.providers())
        with patch.dict("os.environ", {"AVENTRA_ENABLE_SYNTHETIC_TEST_DATA": ""}):
            self.assertNotIn("aventra_demo_dataset", registry.providers())
        with patch.dict("os.environ", {"AVENTRA_ENABLE_SYNTHETIC_TEST_DATA": "1"}):
            self.assertIn("aventra_demo_dataset", registry.providers())

    def test_capability_matrix_reports_configuration(self):
        with patch.dict("os.environ", {"FRED_API_KEY": ""}):
            matrix = {row["provider"]: row for row in registry.capability_matrix()}
        self.assertFalse(matrix["fred"]["configured"])
        self.assertTrue(matrix["binance"]["configured"])
        self.assertIn("forex", matrix["frankfurter"]["asset_classes"])


if __name__ == "__main__":
    unittest.main()
