import unittest

import numpy as np
import pandas as pd

from risk_managed_momentum.data.outcome_prices import (
    fill_internal_price_gaps,
    resolve_outcome_prices,
)


class OutcomePriceTests(unittest.TestCase):
    def test_internal_gap_is_filled_only_if_trading_resumes(self) -> None:
        dates = pd.bdate_range("2024-01-01", periods=6)
        price = pd.DataFrame(
            {
                "RESUMES": [10.0, np.nan, 11.0, 12.0, 13.0, 14.0],
                "STOPS": [20.0, 21.0, np.nan, np.nan, np.nan, np.nan],
            },
            index=dates,
        )
        result = fill_internal_price_gaps(price, maximum_gap_days=2)
        self.assertEqual(result.loc[dates[1], "RESUMES"], 10.0)
        self.assertTrue(result.loc[dates[2] :, "STOPS"].isna().all())

    def test_cash_merger_carries_consideration_forward(self) -> None:
        dates = pd.bdate_range("2024-01-01", periods=6)
        price = pd.DataFrame({"OLD": [40.0, 41.0, np.nan, np.nan, np.nan, np.nan]}, index=dates)
        actions = pd.DataFrame(
            {
                "action_date": [dates[2]],
                "action_symbol": ["OLD"],
                "action_type": ["cash_mergers"],
                "rate": [42.0],
            }
        )
        result = resolve_outcome_prices(price, actions)
        self.assertTrue((result.prices.loc[dates[2] :, "OLD"] == 42.0).all())
        self.assertEqual(result.audit.iloc[0]["resolution_status"], "cash_consideration")

    def test_stock_merger_follows_successor_value(self) -> None:
        dates = pd.bdate_range("2024-01-01", periods=6)
        price = pd.DataFrame(
            {
                "OLD": [40.0, 41.0, np.nan, np.nan, np.nan, np.nan],
                "NEW": [20.0, 20.5, 21.0, 22.0, 23.0, 24.0],
            },
            index=dates,
        )
        actions = pd.DataFrame(
            {
                "action_date": [dates[2]],
                "action_symbol": ["OLD"],
                "action_type": ["stock_and_cash_mergers"],
                "acquirer_symbol": ["NEW"],
                "acquirer_rate": [2.0],
                "acquiree_rate": [1.0],
                "cash_rate": [3.0],
            }
        )
        result = resolve_outcome_prices(price, actions)
        self.assertEqual(result.prices.loc[dates[3], "OLD"], 47.0)
        self.assertEqual(result.audit.iloc[0]["resolution_status"], "successor_consideration")

    def test_reused_ticker_is_not_overwritten_by_old_merger(self) -> None:
        dates = pd.bdate_range("2024-01-01", periods=50)
        price = pd.DataFrame({"OLD": np.nan}, index=dates)
        price.loc[dates[:2], "OLD"] = [40.0, 41.0]
        price.loc[dates[-2:], "OLD"] = [100.0, 101.0]
        actions = pd.DataFrame(
            {
                "action_date": [dates[2]],
                "action_symbol": ["OLD"],
                "action_type": ["cash_mergers"],
                "rate": [42.0],
            }
        )
        result = resolve_outcome_prices(price, actions)
        self.assertEqual(result.prices.loc[dates[20], "OLD"], 42.0)
        self.assertEqual(result.prices.loc[dates[-1], "OLD"], 101.0)


if __name__ == "__main__":
    unittest.main()
