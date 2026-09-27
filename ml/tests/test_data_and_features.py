import unittest

import numpy as np
import pandas as pd

from ml.data.sessions import align_to_session, session_bounds, to_utc
from ml.data.validation import MarketDataError, validate_ohlcv
from ml.features.engineering import compute_features
from ml.tests.helpers import make_bars


class ValidationTests(unittest.TestCase):
    def test_removes_duplicates_invalid_rows_and_holiday_placeholders(self):
        bars = make_bars(30)
        dup = bars.iloc[[5]]
        bad = bars.iloc[[6]].assign(high=bars["low"].iloc[6] * 0.5)          # high < low
        neg = bars.iloc[[7]].assign(close=-1.0)
        placeholder = bars.iloc[[8]].copy()
        placeholder[["open", "high", "low", "close"]] = bars["close"].iloc[7]
        placeholder["volume"] = 0
        frame = pd.concat([bars.drop(index=[6, 7, 8]), dup, bad, neg, placeholder]).sample(frac=1, random_state=1)
        clean, report = validate_ohlcv(frame, "TEST")
        self.assertTrue(report["out_of_order"])
        self.assertEqual(report["duplicates_removed"], 1)
        self.assertEqual(report["invalid_rows_removed"]["impossible_ohlc"], 1)
        self.assertEqual(report["invalid_rows_removed"]["non_positive_price"], 1)
        self.assertEqual(report["holiday_placeholders_removed"], 1)
        self.assertTrue(clean["timestamp"].is_monotonic_increasing)
        self.assertEqual(len(clean), 27)   # 30 original rows minus the three that were replaced by corrupted copies

    def test_extreme_but_valid_move_is_kept_and_flagged(self):
        bars = make_bars(30)
        bars.loc[20, ["close", "high"]] = bars.loc[20, "close"] * 1.6, bars.loc[20, "close"] * 1.61
        clean, report = validate_ohlcv(bars, "TEST")
        self.assertEqual(len(clean), 30)
        # the one-day spike and its reversal on the next bar are both genuine >35% moves
        self.assertEqual(len(report["large_moves_flagged"]), 2)

    def test_missing_columns_raise(self):
        with self.assertRaises(MarketDataError):
            validate_ohlcv(pd.DataFrame({"timestamp": [], "close": []}))


class SessionTests(unittest.TestCase):
    def test_session_bounds_are_utc(self):
        open_utc, close_utc = session_bounds("2026-06-15")
        self.assertEqual(open_utc, pd.Timestamp("2026-06-15T03:45:00Z"))
        self.assertEqual(close_utc, pd.Timestamp("2026-06-15T10:00:00Z"))

    def test_news_after_close_aligns_to_next_observed_session(self):
        dates = [pd.Timestamp("2026-06-12"), pd.Timestamp("2026-06-15")]   # Friday, Monday
        self.assertEqual(align_to_session("2026-06-12T11:00:00Z", dates), pd.Timestamp("2026-06-15"))
        self.assertEqual(align_to_session("2026-06-12T05:00:00Z", dates), pd.Timestamp("2026-06-12"))
        self.assertIsNone(align_to_session("2026-06-16T11:00:00Z", dates))

    def test_naive_timestamps_are_treated_as_utc(self):
        self.assertEqual(to_utc("2026-01-01 10:00").tzinfo.tzname(None), "UTC")


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.bars, _ = validate_ohlcv(make_bars(120))
        self.features = compute_features(self.bars)

    def test_hand_computed_values(self):
        b, f = self.bars, self.features
        i = 50
        self.assertAlmostEqual(f["return_1"][i], b["close"][i] / b["close"][i - 1] - 1)
        self.assertAlmostEqual(f["gap_pct"][i], b["open"][i] / b["close"][i - 1] - 1)
        self.assertAlmostEqual(f["range_pct"][i], (b["high"][i] - b["low"][i]) / b["close"][i - 1])
        self.assertAlmostEqual(f["volume_ratio"][i], b["volume"][i] / b["volume"][i - 20:i].mean())
        self.assertAlmostEqual(f["ma20_distance"][i], b["close"][i] / b["close"][i - 20:i].mean() - 1)

    def test_no_leakage_past_features_ignore_future_rows(self):
        truncated = compute_features(self.bars.iloc[:80])
        modified = self.bars.copy()
        modified.loc[80:, ["close", "high", "volume"]] *= 5    # distort the future only
        distorted = compute_features(modified)
        cols = ["return_1", "volatility_20", "volume_ratio", "volume_zscore", "ma20_distance", "rsi_14"]
        pd.testing.assert_frame_equal(truncated[cols].iloc[:80], distorted[cols].iloc[:80])

    def test_benchmark_relative_return_is_nan_without_benchmark(self):
        self.assertTrue(self.features["relative_return"].isna().all())

    def test_benchmark_relative_return(self):
        bench = self.bars.copy()
        bench["close"] = bench["close"] * 1.0
        rel = compute_features(self.bars, bench)["relative_return"]
        self.assertTrue(np.allclose(rel.dropna(), 0.0))


class FeatureSetSelectionTests(unittest.TestCase):
    def test_set_follows_capabilities_and_calendar(self):
        from ml.features.sets import FEATURE_SETS, select_set
        self.assertEqual(select_set({"has_ohlc": True, "has_volume": True, "calendar": "XNYS"}), "ohlcv")
        self.assertEqual(select_set({"has_ohlc": True, "has_volume": True, "calendar": "24/7"}), "ohlcv_continuous")
        self.assertEqual(select_set({"has_ohlc": False, "has_volume": True}), "close_volume")
        self.assertEqual(select_set({"has_ohlc": False, "has_volume": False}), "close")
        self.assertEqual(select_set({"value_kind": "yield"}), "yield")
        continuous = FEATURE_SETS["ohlcv_continuous"]
        self.assertNotIn("gap_pct", continuous["fingerprint"])   # a 24/7 daily open is the previous close: no gap
        self.assertNotIn("gap_pct", continuous["detector"])


if __name__ == "__main__":
    unittest.main()
