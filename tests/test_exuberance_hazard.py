import unittest

import numpy as np
import pandas as pd

from risk_managed_momentum.features.episodes import exuberance_onsets
from risk_managed_momentum.models.hazard import (
    expand_hazard_training_rows,
    fit_hazard_model,
    predict_cumulative_risk,
)


class ExuberanceHazardTests(unittest.TestCase):
    def test_onset_requires_washout_before_reentry(self) -> None:
        dates = pd.bdate_range("2024-01-01", periods=12)
        price = pd.DataFrame(
            {"A": [100, 100, 121, 122, 123, 100, 100, 100, 100, 125, 126, 127]},
            index=dates,
        )
        member = pd.DataFrame(True, index=dates, columns=["A"])
        onset = exuberance_onsets(
            price,
            member,
            runup_lookback_days=2,
            minimum_runup=0.20,
            peak_lookback_days=2,
            maximum_distance_below_peak=-0.10,
            washout_trading_days=3,
        )
        self.assertEqual(onset.index[onset["A"]].tolist(), [dates[2], dates[9]])

    def test_training_expansion_stops_after_first_event(self) -> None:
        episodes = pd.DataFrame({"x": [1.0, 2.0], "first_breach_days": [15.0, np.nan]})
        expanded = expand_hazard_training_rows(episodes, ["x"], [10, 20, 40, 60])
        self.assertEqual(len(expanded), 6)
        self.assertEqual(int(expanded["hazard_event"].sum()), 1)

    def test_cumulative_risk_is_monotonic(self) -> None:
        episodes = pd.DataFrame(
            {
                "x": np.linspace(-2.0, 2.0, 30),
                "first_breach_days": [np.nan] * 20 + [5.0] * 10,
            }
        )
        fitted = fit_hazard_model(
            episodes,
            ["x"],
            [10, 20, 40, 60],
            c=0.01,
            maximum_iterations=1000,
            random_seed=42,
        )
        scored = predict_cumulative_risk(fitted, episodes)
        risks = scored[["risk_10", "risk_20", "risk_40", "risk_60"]].to_numpy()
        self.assertTrue((np.diff(risks, axis=1) >= 0.0).all())


if __name__ == "__main__":
    unittest.main()

