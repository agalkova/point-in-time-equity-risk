import unittest

import numpy as np
import pandas as pd

from risk_managed_momentum.evaluation.alpha_portfolio import alpha_target_weights
from risk_managed_momentum.evaluation.attribution import factor_regression
from risk_managed_momentum.features.alpha import month_end_trading_dates


class AlphaResearchTests(unittest.TestCase):
    def test_month_end_dates_use_last_available_trading_day(self) -> None:
        dates = pd.to_datetime(["2024-01-30", "2024-01-31", "2024-02-28", "2024-02-29"])
        result = month_end_trading_dates(dates)
        self.assertEqual(result.tolist(), [dates[1], dates[3]])

    def test_long_short_weights_are_market_neutral_and_unit_gross(self) -> None:
        signals = pd.DataFrame(
            {"ticker": list("ABCDEF"), "score": [6, 5, 4, 3, 2, 1]}
        )
        weights = alpha_target_weights(
            signals,
            score_column="score",
            mode="long_short",
            top_n=2,
        )
        self.assertAlmostEqual(float(weights.sum()), 0.0)
        self.assertAlmostEqual(float(weights.abs().sum()), 1.0)
        self.assertEqual(set(weights[weights > 0].index), {"A", "B"})
        self.assertEqual(set(weights[weights < 0].index), {"E", "F"})

    def test_factor_regression_recovers_known_market_loading(self) -> None:
        dates = pd.bdate_range("2024-01-01", periods=100)
        market = np.linspace(-0.01, 0.01, len(dates))
        factors = pd.DataFrame(
            {
                "date": dates,
                "MKT_RF": market,
                "SMB": 0.0,
                "HML": 0.0,
                "RMW": 0.0,
                "CMA": 0.0,
                "MOM": 0.0,
                "RF": 0.0001,
            }
        )
        portfolio = pd.DataFrame(
            {"date": dates, "net_return": 0.0002 + 1.5 * market}
        )
        result = factor_regression(portfolio, factors)
        self.assertAlmostEqual(result["beta_mkt_rf"], 1.5, places=6)
        self.assertAlmostEqual(result["annualized_alpha"], 0.0001 * 252.0, places=6)

        raw_result = factor_regression(
            portfolio,
            factors,
            subtract_risk_free_rate=False,
        )
        self.assertAlmostEqual(raw_result["annualized_alpha"], 0.0002 * 252.0, places=6)


if __name__ == "__main__":
    unittest.main()
