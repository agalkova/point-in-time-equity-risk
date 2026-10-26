import unittest

import pandas as pd

from risk_managed_momentum.evaluation.portfolio import simulate_portfolio, target_weights


class PortfolioTests(unittest.TestCase):
    def test_position_cap_leaves_cash_when_fewer_than_required_names(self) -> None:
        signals = pd.DataFrame(
            {
                "ticker": ["A", "B"],
                "rank_ret_60": [0.9, 0.8],
                "risk_score": [0.1, 0.2],
            }
        )
        weights = target_weights(
            signals,
            strategy="momentum",
            top_n=50,
            maximum_position_weight=0.02,
        )
        self.assertEqual(weights.max(), 0.02)
        self.assertAlmostEqual(weights.sum(), 0.04)

    def test_transaction_cost_is_charged_on_initial_purchase(self) -> None:
        dates = pd.bdate_range("2024-01-01", periods=6)
        price = pd.DataFrame({"A": [100.0] * 6}, index=dates)
        signals = pd.DataFrame(
            {
                "date": dates,
                "ticker": ["A"] * 6,
                "rank_ret_60": [1.0] * 6,
                "risk_score": [0.1] * 6,
            }
        )
        daily = simulate_portfolio(
            price,
            signals,
            frequency="weekly",
            strategy="momentum",
            top_n=1,
            maximum_position_weight=1.0,
            one_way_cost_bps=10.0,
        )
        self.assertAlmostEqual(daily.iloc[0]["net_return"], -0.001)

    def test_missing_held_return_fails_closed(self) -> None:
        dates = pd.bdate_range("2024-01-01", periods=10)
        price = pd.DataFrame(
            {"A": [100.0] * 5 + [float("nan")] * 5},
            index=dates,
        )
        signals = pd.DataFrame(
            {
                "date": dates,
                "ticker": ["A"] * len(dates),
                "rank_ret_60": [1.0] * len(dates),
                "risk_score": [0.1] * len(dates),
            }
        )
        with self.assertRaisesRegex(ValueError, "Missing held-security returns"):
            simulate_portfolio(
                price,
                signals,
                frequency="weekly",
                strategy="momentum",
                top_n=1,
                maximum_position_weight=1.0,
            )


if __name__ == "__main__":
    unittest.main()
