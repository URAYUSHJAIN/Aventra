import unittest

import numpy as np
import pandas as pd

from ml import config
from ml.anomaly.detectors import EcdfNormalizer, UnsupervisedDetector
from ml.anomaly.ensemble import combine
from ml.anomaly.statistical import statistical_scores
from ml.data.validation import validate_ohlcv
from ml.features.engineering import compute_features
from ml.fingerprint.baseline import compute_fingerprint, deviation_score, rolling_robust_baseline
from ml.tests.helpers import make_bars


class FingerprintTests(unittest.TestCase):
    def test_deviation_score_mapping(self):
        self.assertEqual(deviation_score(1.0), 0.0)
        self.assertEqual(deviation_score(config.Z_SCORE_CAP + 1), 1.0)
        self.assertAlmostEqual(deviation_score(4.0), (4.0 - 2.0) / (6.0 - 2.0))

    def test_robust_z_hand_computed(self):
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 10.0])
        result = rolling_robust_baseline(values, window=5, min_history=5, guard_z=100)
        # history 1..5 -> median 3, MAD 1 -> scale 1.4826
        self.assertAlmostEqual(result["median"][5], 3.0)
        self.assertAlmostEqual(result["z"][5], (10 - 3) / 1.4826, places=4)
        self.assertTrue(np.isnan(result["z"][:5]).all())    # insufficient history

    def test_guarded_update_clips_extreme_observation(self):
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 1000.0, 3.0])
        result = rolling_robust_baseline(values, window=6, min_history=5, guard_z=4.0)
        clipped = 3.0 + 4.0 * 1.4826
        self.assertAlmostEqual(result["final_history"].max(), clipped, places=4)

    def test_fingerprint_has_no_leakage_and_reports_insufficient_history(self):
        bars, _ = validate_ohlcv(make_bars(300))
        feats = compute_features(bars)
        fp_full, _ = compute_fingerprint(feats)
        fp_trunc, _ = compute_fingerprint(feats.iloc[:200])
        pd.testing.assert_series_equal(fp_full["fingerprint_score"].iloc[:200], fp_trunc["fingerprint_score"])
        self.assertEqual(fp_full["fingerprint_status"].iloc[10], "insufficient_history")
        self.assertEqual(fp_full["fingerprint_status"].iloc[-1], "ok")


class DetectorTests(unittest.TestCase):
    def setUp(self):
        bars, _ = validate_ohlcv(make_bars(400))
        self.feats = compute_features(bars)

    def test_ecdf_normaliser(self):
        norm = EcdfNormalizer(floor=0.9).fit(np.arange(100, dtype=float))
        self.assertEqual(norm.transform(np.array([50.0]))[0], 0.0)
        self.assertEqual(norm.transform(np.array([1000.0]))[0], 1.0)
        self.assertTrue(np.isnan(norm.transform(np.array([np.nan]))[0]))

    def test_isolation_forest_is_deterministic_and_flags_injected_outlier(self):
        train, test = self.feats.iloc[:300], self.feats.iloc[300:].copy()
        test.loc[test.index[50], ["return_1", "log_return", "range_pct", "volume_ratio", "gap_pct"]] = [0.2, 0.18, 0.25, 8.0, 0.1]
        a = UnsupervisedDetector("isolation_forest").fit(train).score(test)
        b = UnsupervisedDetector("isolation_forest").fit(train).score(test)
        np.testing.assert_array_equal(a, b)
        self.assertEqual(int(np.nanargmax(a)), 50)      # the injected bar is the most anomalous test bar
        self.assertGreater(a[50], 0.9)
        self.assertLess(np.nanmedian(a), 0.2)

    def test_lof_detector_scores(self):
        scores = UnsupervisedDetector("lof").fit(self.feats.iloc[:300]).score(self.feats.iloc[300:])
        self.assertTrue(((scores >= 0) & (scores <= 1) | np.isnan(scores)).all())

    def test_statistical_score_uses_prior_window(self):
        stat = statistical_scores(self.feats)
        # log_volume has no lag, so its prior 20-bar window is first complete at index 20
        self.assertTrue(stat["statistical_score"].iloc[:20].isna().all())
        self.assertFalse(np.isnan(stat["statistical_score"].iloc[20]))
        self.assertTrue(stat["statistical_score"].dropna().between(0, 1).all())

    def test_ensemble_renormalises_and_assigns_severity(self):
        frame = pd.DataFrame({"statistical": [1.0, 0.0, np.nan], "fingerprint": [1.0, 0.0, 0.5], "isolation_forest": [1.0, np.nan, np.nan]})
        out = combine(frame)
        self.assertAlmostEqual(out["anomaly_score"][0], 1.0)
        self.assertEqual(out["severity"][0], "CRITICAL")
        self.assertTrue(out["is_anomaly"][0])
        self.assertAlmostEqual(out["anomaly_score"][2], 0.5)      # only fingerprint available
        self.assertEqual(out["model_agreement"][0], 1.0)
        self.assertEqual(out["components_available"][1], 2)


if __name__ == "__main__":
    unittest.main()
