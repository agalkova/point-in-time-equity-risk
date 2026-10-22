import unittest

import numpy as np
import pandas as pd

from risk_managed_momentum.evaluation.optimized_portfolio import optimize_alpha_weights


class OptimizedPortfolioTests(unittest.TestCase):
    def test_optimizer_respects_weight_and_beta_constraints(self) -> None:
        rng = np.random.default_rng(42)
        dates = pd.bdate_range("2024-01-01", periods=126)
        market = pd.Series(rng.normal(0.0003, 0.01, len(dates)), index=dates)
        tickers = [f"S{index:02d}" for index in range(40)]
        returns = pd.DataFrame(
            {
                ticker: (0.8 + index / 100.0) * market.to_numpy()
                + rng.normal(0.0, 0.006, len(dates))
                for index, ticker in enumerate(tickers)
            },
            index=dates,
        )
        signals = pd.DataFrame(
            {"ticker": tickers, "score_ridge": np.linspace(0.0, 1.0, len(tickers))}
        )
        config = {
            "optimizer": {
                "candidate_count": 40,
                "maximum_position_weight": 0.03,
                "minimum_asset_observations": 80,
                "covariance_diagonal_shrinkage": 0.5,
                "risk_aversion": 3.0,
                "turnover_penalty": 0.03,
                "minimum_beta": 0.75,
                "maximum_beta": 1.05,
                "solver_max_iterations": 500,
            }
        }
        result = optimize_alpha_weights(
            signals,
            returns,
            market,
            pd.Series(dtype=float),
            config,
        )
        self.assertAlmostEqual(float(result.weights.sum()), 1.0, places=8)
        self.assertLessEqual(float(result.weights.max()), 0.0300001)
        self.assertGreaterEqual(result.estimated_beta, 0.75 - 1e-6)
        self.assertLessEqual(result.estimated_beta, 1.05 + 1e-6)


if __name__ == "__main__":
    unittest.main()
