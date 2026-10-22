import unittest

import pandas as pd

from risk_managed_momentum.data.sec import normalize_annual_companyfacts
from risk_managed_momentum.features.fundamentals import (
    build_filing_features,
    point_in_time_fundamentals,
)


class SecFundamentalsTests(unittest.TestCase):
    def test_normalizer_rejects_comparative_and_nonannual_values(self) -> None:
        payload = {
            "facts": {
                "us-gaap": {
                    "Assets": {
                        "units": {
                            "USD": [
                                {
                                    "end": "2023-12-31",
                                    "val": 100,
                                    "form": "10-K",
                                    "fp": "FY",
                                    "fy": 2023,
                                    "filed": "2024-02-15",
                                    "accn": "a",
                                },
                                {
                                    "end": "2022-12-31",
                                    "val": 90,
                                    "form": "10-K",
                                    "fp": "FY",
                                    "fy": 2023,
                                    "filed": "2024-02-15",
                                    "accn": "a",
                                },
                            ]
                        }
                    },
                    "Revenues": {
                        "units": {
                            "USD": [
                                {
                                    "start": "2023-01-01",
                                    "end": "2023-12-31",
                                    "val": 50,
                                    "form": "10-K",
                                    "fp": "FY",
                                    "fy": 2023,
                                    "filed": "2024-02-15",
                                    "accn": "a",
                                },
                                {
                                    "start": "2023-10-01",
                                    "end": "2023-12-31",
                                    "val": 12,
                                    "form": "10-K",
                                    "fp": "FY",
                                    "fy": 2023,
                                    "filed": "2024-02-15",
                                    "accn": "a",
                                },
                            ]
                        }
                    },
                }
            }
        }
        result = normalize_annual_companyfacts(payload, "ABC")
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["assets"], 100)
        self.assertEqual(result.iloc[0]["revenue"], 50)

    def test_asof_join_does_not_reveal_unfiled_statement(self) -> None:
        annual = pd.DataFrame(
            {
                "ticker": ["ABC", "ABC"],
                "fiscal_year": [2022, 2023],
                "end": ["2022-12-31", "2023-12-31"],
                "filed": ["2023-02-15", "2024-02-15"],
                "net_income": [10.0, 12.0],
                "revenue": [50.0, 55.0],
                "gross_profit": [25.0, 28.0],
                "operating_income": [12.0, 14.0],
                "operating_cash_flow": [11.0, 13.0],
                "weighted_avg_shares_diluted": [10.0, 9.5],
            }
        )
        features = build_filing_features(annual)
        signals = pd.DataFrame(
            {"ticker": ["ABC", "ABC"], "date": ["2024-01-31", "2024-02-29"]}
        )
        result = point_in_time_fundamentals(features, signals)
        self.assertEqual(result.loc[0, "end"], pd.Timestamp("2022-12-31"))
        self.assertEqual(result.loc[1, "end"], pd.Timestamp("2023-12-31"))


if __name__ == "__main__":
    unittest.main()
