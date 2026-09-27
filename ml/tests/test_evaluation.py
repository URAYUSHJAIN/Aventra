import unittest

import numpy as np

from ml.data.validation import validate_ohlcv
from ml.evaluation.synthetic import MIN_GAP, _metrics_at, choose_positions, evaluate_scores, inject
from ml.tests.helpers import make_bars


class EvaluationHelperTests(unittest.TestCase):
    def test_price_jump_is_a_persistent_level_shift_and_keeps_ohlc_valid(self):
        bars, _ = validate_ohlcv(make_bars(60))
        out = inject(bars, [30], ["price_jump_down"], sigma=0.01)
        self.assertAlmostEqual(out["close"][30] / bars["close"][30], 0.95)
        self.assertAlmostEqual(out["close"][50] / bars["close"][50], 0.95)
        self.assertEqual(out["close"][29], bars["close"][29])            # the past is untouched
        _, report = validate_ohlcv(out)
        self.assertEqual(report["invalid_rows_removed"]["impossible_ohlc"], 0)

    def test_positions_respect_minimum_gap(self):
        positions = choose_positions(np.random.default_rng(0), 0, 400, 10)
        self.assertTrue(all(b - a >= MIN_GAP for a, b in zip(positions, positions[1:])))

    def test_metrics(self):
        m = _metrics_at(np.array([0.9, 0.8, 0.1, 0.7]), np.array([True, False, False, True]), 0.75)
        self.assertEqual((m["tp"], m["fp"], m["fn"]), (1, 1, 1))
        self.assertAlmostEqual(m["precision"], 0.5)
        self.assertAlmostEqual(m["fpr"], 0.5)

    def test_threshold_is_chosen_on_validation_not_test(self):
        scores = np.array([0.9, 0.1, 0.2, 0.3, 0.95, 0.4])
        labels = np.array([True, False, False, False, True, False])
        val = np.array([True, True, True, False, False, False])
        test = ~val
        result = evaluate_scores(scores, labels, val, test)
        self.assertEqual(result["at_validation_threshold"]["threshold"], 0.9)
        self.assertEqual(result["precision_at_k"], 1.0)


if __name__ == "__main__":
    unittest.main()
