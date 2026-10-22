import unittest

import numpy as np
import pandas as pd

from risk_managed_momentum.features.targets import (
    drawdown_event,
    drawdown_severity,
    future_min_return,
)


def sample_prices() -> pd.DataFrame:
    return pd.DataFrame(
        {"AAA": [100.0, 110.0, 80.0, 120.0, 90.0]},
        index=pd.date_range("2024-01-01", periods=5, freq="D"),
    )


class TargetTests(unittest.TestCase):
    def test_future_window_excludes_signal_date(self) -> None:
        result = future_min_return(sample_prices(), horizon=2)
        self.assertTrue(np.isclose(result.iloc[0, 0], -0.20))
        self.assertTrue(np.isclose(result.iloc[1, 0], 80.0 / 110.0 - 1.0))

    def test_full_horizon_is_required(self) -> None:
        result = future_min_return(sample_prices(), horizon=2)
        self.assertTrue(result.iloc[-2:, 0].isna().all())

    def test_event_and_severity_share_the_same_forward_window(self) -> None:
        price = sample_prices()
        event = drawdown_event(price, horizon=2, threshold=-0.15)
        severity = drawdown_severity(price, horizon=2)
        self.assertTrue(bool(event.iloc[0, 0]))
        self.assertTrue(np.isclose(severity.iloc[0, 0], 0.20))


if __name__ == "__main__":
    unittest.main()

