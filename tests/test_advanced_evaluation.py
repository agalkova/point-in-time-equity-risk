import unittest

import pandas as pd

from risk_managed_momentum.evaluation.calibration import (
    calibration_table,
    expected_calibration_error,
)
from risk_managed_momentum.evaluation.events import thin_non_overlapping_signals, warning_metrics
from risk_managed_momentum.evaluation.walk_forward import expanding_year_folds


class AdvancedEvaluationTests(unittest.TestCase):
    def test_walk_forward_purges_trailing_training_dates(self) -> None:
        dates = pd.bdate_range("2019-01-01", "2021-12-31")
        folds = expanding_year_folds(
            dates,
            first_test_year=2020,
            last_test_year=2021,
            purge_trading_days=40,
        )
        self.assertEqual(folds[0].test_year, 2020)
        self.assertEqual(len(pd.bdate_range(folds[0].train_dates.max(), "2019-12-31")) - 1, 40)
        self.assertLess(folds[0].train_dates.max(), folds[0].test_dates.min())

    def test_non_overlapping_signals_skip_forward_window(self) -> None:
        dates = pd.bdate_range("2024-01-01", periods=10)
        frame = pd.DataFrame({"date": dates, "ticker": "A", "target": 0})
        result = thin_non_overlapping_signals(frame, horizon_days=3)
        self.assertEqual(result["date"].tolist(), [dates[0], dates[4], dates[8]])

    def test_calibration_error_is_zero_for_matched_bins(self) -> None:
        target = pd.Series([0, 0, 1, 1])
        score = pd.Series([0.0, 0.0, 1.0, 1.0])
        table = calibration_table(target, score, bins=2)
        self.assertAlmostEqual(expected_calibration_error(table), 0.0)

    def test_warning_metrics_can_preserve_full_cross_section_threshold(self) -> None:
        frame = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
                "ticker": ["A", "B"],
                "target": [1, 0],
                "score": [0.9, 0.8],
                "warning_from_full_cross_section": [True, False],
                "first_breach_days": [5.0, float("nan")],
            }
        )
        metrics = warning_metrics(
            frame,
            score_column="score",
            warning_percentile=0.8,
            warning_column="warning_from_full_cross_section",
        )
        self.assertEqual(metrics["warnings"], 1)
        self.assertEqual(metrics["precision"], 1.0)


if __name__ == "__main__":
    unittest.main()
