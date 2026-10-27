from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from risk_managed_momentum.features.sec_fundamentals import (
    add_accounting_group_ranks,
    assign_point_in_time_cik,
    point_in_time_filing_join,
)


class SecFundamentalPanelTests(unittest.TestCase):
    def test_identity_assignment_respects_ticker_reuse_intervals(self) -> None:
        signals = pd.DataFrame(
            {
                "date": ["2020-06-30", "2023-06-30"],
                "ticker": ["XYZ", "XYZ"],
            }
        )
        intervals = pd.DataFrame(
            {
                "ticker": ["XYZ", "XYZ"],
                "valid_from": ["2019-01-01", "2022-01-01"],
                "valid_to": ["2021-12-31", "2024-12-31"],
                "cik": [10, 20],
                "status": ["RESOLVED", "RESOLVED"],
                "identity_source": ["test", "test"],
                "confidence": ["high", "high"],
            }
        )
        joined = assign_point_in_time_cik(signals, intervals)
        self.assertEqual(joined["cik"].tolist(), [10, 20])

    def test_filing_join_never_uses_future_information_and_expires_stale_data(self) -> None:
        signals = pd.DataFrame(
            {
                "date": pd.to_datetime(["2020-02-01", "2020-03-01", "2022-01-01"]),
                "ticker": ["A", "A", "A"],
                "cik": pd.Series([1, 1, 1], dtype="Int64"),
            }
        )
        filings = pd.DataFrame(
            {
                "cik": [1, 1],
                "filed": ["2020-02-15", "2021-02-15"],
                "period": ["2019-12-31", "2020-12-31"],
                "adsh": ["old", "new"],
                "fundamental_schema": ["nonfinancial_v1", "nonfinancial_v1"],
                "gross_margin": [0.4, 0.5],
            }
        )
        joined = point_in_time_filing_join(signals, filings, maximum_filing_age_days=300)
        self.assertTrue(pd.isna(joined.loc[0, "filed"]))
        self.assertEqual(joined.loc[1, "adsh"], "old")
        self.assertTrue(bool(joined.loc[2, "filing_is_stale"]))
        self.assertTrue(pd.isna(joined.loc[2, "filed"]))

    def test_accounting_group_ranks_preserve_missing_values_and_quality_direction(self) -> None:
        frame = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-03-31"] * 3),
                "fundamental_schema": ["nonfinancial_v1"] * 3,
                "gross_margin": [0.2, 0.4, np.nan],
                "operating_margin": [0.1, 0.2, 0.3],
                "cash_flow_margin": [0.1, 0.2, 0.3],
                "net_margin": [np.nan] * 3,
                "return_on_assets": [0.1, 0.2, 0.3],
                "liabilities_to_assets": [0.8, 0.5, 0.2],
                "equity_to_assets": [np.nan] * 3,
                "cash_flow_to_assets": [np.nan] * 3,
                "asset_growth": [0.3, 0.2, 0.1],
                "revenue_growth": [np.nan] * 3,
            }
        )
        ranked, _ = add_accounting_group_ranks(frame, minimum_quality_features=4)
        self.assertEqual(ranked.loc[0, "fundamental_rank_gross_margin"], 0.5)
        self.assertEqual(ranked.loc[1, "fundamental_rank_gross_margin"], 1.0)
        self.assertTrue(pd.isna(ranked.loc[2, "fundamental_rank_gross_margin"]))
        self.assertGreater(
            ranked.loc[2, "fundamental_quality_score"],
            ranked.loc[0, "fundamental_quality_score"],
        )
