import unittest

import numpy as np
import pandas as pd
from scipy.special import expit, logit

from risk_managed_momentum.evaluation.episode_portfolio import episode_overlay_returns
from risk_managed_momentum.evaluation.recalibration import intercept_adjustment


class CalibratedOverlayTests(unittest.TestCase):
    def test_intercept_adjustment_matches_observed_rate(self) -> None:
        probability = np.array([0.05, 0.10, 0.20, 0.30])
        outcome = np.array([0, 1, 0, 1])
        delta = intercept_adjustment(probability, outcome)
        adjusted = expit(logit(probability) + delta)
        self.assertAlmostEqual(float(adjusted.mean()), float(outcome.mean()), places=10)

    def test_overlay_enters_after_signal_and_excludes_high_risk(self) -> None:
        dates = pd.bdate_range("2024-01-01", periods=7)
        price = pd.DataFrame(
            {
                "A": [100, 100, 110, 110, 110, 110, 110],
                "B": [100, 100, 90, 90, 90, 90, 90],
            },
            index=dates,
        )
        episodes = pd.DataFrame(
            {"date": [dates[0], dates[0]], "ticker": ["A", "B"], "risk": [0.1, 0.9]}
        )
        result, diagnostics = episode_overlay_returns(
            price,
            episodes,
            risk_column="risk",
            high_risk_threshold=0.5,
            holding_period=2,
            entry_delay=1,
            one_way_cost_bps=0.0,
        )
        self.assertEqual(diagnostics["excluded_episodes"], 1)
        self.assertAlmostEqual(result.loc[dates[1], "baseline_gross_return"], 0.0)
        self.assertAlmostEqual(result.loc[dates[1], "overlay_gross_return"], 0.1)
        self.assertTrue(result.loc[dates[1], "overlay_invested"])


if __name__ == "__main__":
    unittest.main()

