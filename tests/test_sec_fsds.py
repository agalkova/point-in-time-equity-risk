import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from risk_managed_momentum.data.sec_fsds import (
    FUNDAMENTAL_SCHEMAS,
    _parse_sec_date,
    assign_fundamental_schema,
    assign_historical_fundamental_schema,
    normalize_annual_filings,
    read_relevant_numbers,
    schema_for_sic,
    select_sector_pilot,
)


class SecFsdsTests(unittest.TestCase):
    def test_sic_proxy_selects_financial_and_real_estate_schemas(self) -> None:
        self.assertEqual(schema_for_sic(6021), "financials_v1")
        self.assertEqual(schema_for_sic(6798), "real_estate_v1")
        self.assertEqual(schema_for_sic(7372), "nonfinancial_v1")

    def test_current_gics_overrides_historical_sic_proxy(self) -> None:
        frame = pd.DataFrame(
            {
                "cik": [1],
                "sic": [6021],
                **{feature: [1.0] for feature in FUNDAMENTAL_SCHEMAS["nonfinancial_v1"]},
            }
        )
        sectors = pd.DataFrame({"cik": [1], "sector": ["Industrials"]})

        result = assign_historical_fundamental_schema(frame, sectors)

        self.assertEqual(result.iloc[0]["fundamental_schema"], "nonfinancial_v1")
        self.assertEqual(result.iloc[0]["sector_source"], "current_gics")
        self.assertTrue(result.iloc[0]["schema_complete"])

    def test_sector_aware_schema_assignment(self) -> None:
        rows = []
        for sector, schema in [
            ("Industrials", "nonfinancial_v1"),
            ("Financials", "financials_v1"),
            ("Real Estate", "real_estate_v1"),
        ]:
            row = {"sector": sector, **{feature: 1.0 for feature in FUNDAMENTAL_SCHEMAS[schema]}}
            rows.append(row)

        result = assign_fundamental_schema(pd.DataFrame(rows))

        self.assertEqual(
            result["fundamental_schema"].tolist(),
            ["nonfinancial_v1", "financials_v1", "real_estate_v1"],
        )
        self.assertTrue(result["schema_complete"].all())

    def test_number_reader_rejects_dimensional_segment_facts(self) -> None:
        submissions = pd.DataFrame({"adsh": ["x"]})
        numbers = pd.DataFrame(
            {
                "adsh": ["x", "x"],
                "tag": ["Revenues", "Revenues"],
                "version": ["us-gaap/2023", "us-gaap/2023"],
                "ddate": [20231231, 20231231],
                "qtrs": [4, 4],
                "uom": ["USD", "USD"],
                "segments": [None, "BusinessSegments=Example;"],
                "coreg": [None, None],
                "value": [100.0, 25.0],
            }
        )
        with TemporaryDirectory() as directory:
            archive_path = Path(directory) / "quarter.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("num.txt", numbers.to_csv(sep="\t", index=False))

            result = read_relevant_numbers(archive_path, submissions)

        self.assertEqual(result["value"].tolist(), [100.0])

    def test_sec_dates_accept_integer_and_float_storage(self) -> None:
        actual = _parse_sec_date(pd.Series([20240131, 20240131.0, "20240131", None]))

        self.assertEqual(actual.iloc[:3].dt.strftime("%Y-%m-%d").tolist(), ["2024-01-31"] * 3)
        self.assertTrue(pd.isna(actual.iloc[3]))

    def test_normalizes_six_filing_date_features(self) -> None:
        submissions = pd.DataFrame(
            {
                "adsh": ["x"],
                "cik": [1],
                "name": ["Example"],
                "sic": [1000],
                "form": ["10-K"],
                "period": [pd.Timestamp("2023-12-31")],
                "fy": [2023],
                "fp": ["FY"],
                "filed": [pd.Timestamp("2024-02-15")],
                "instance": ["example.htm"],
            }
        )
        facts = {
            "RevenueFromContractWithCustomerExcludingAssessedTax": (100.0, 4, "2023-12-31"),
            "GrossProfit": (40.0, 4, "2023-12-31"),
            "OperatingIncomeLoss": (20.0, 4, "2023-12-31"),
            "NetIncomeLoss": (10.0, 4, "2023-12-31"),
            "NetCashProvidedByUsedInOperatingActivities": (15.0, 4, "2023-12-31"),
            "Assets": (200.0, 0, "2023-12-31"),
            "Liabilities": (80.0, 0, "2023-12-31"),
            "StockholdersEquity": (120.0, 0, "2023-12-31"),
        }
        rows = [
            {
                "adsh": "x",
                "tag": tag,
                "version": "us-gaap/2023",
                "ddate": pd.Timestamp(date),
                "qtrs": qtrs,
                "uom": "USD",
                "value": value,
                "concept": {
                    "RevenueFromContractWithCustomerExcludingAssessedTax": "revenue",
                    "GrossProfit": "gross_profit",
                    "OperatingIncomeLoss": "operating_income",
                    "NetIncomeLoss": "net_income",
                    "NetCashProvidedByUsedInOperatingActivities": "operating_cash_flow",
                    "Assets": "assets",
                    "Liabilities": "liabilities",
                    "StockholdersEquity": "equity",
                }[tag],
            }
            for tag, (value, qtrs, date) in facts.items()
        ]
        rows.append(
            {
                "adsh": "x",
                "tag": "Assets",
                "version": "us-gaap/2023",
                "ddate": pd.Timestamp("2022-12-31"),
                "qtrs": 0,
                "uom": "USD",
                "value": 160.0,
                "concept": "assets",
            }
        )
        rows.append(
            {
                "adsh": "x",
                "tag": "RevenueFromContractWithCustomerExcludingAssessedTax",
                "version": "us-gaap/2023",
                "ddate": pd.Timestamp("2022-12-31"),
                "qtrs": 4,
                "uom": "USD",
                "value": 80.0,
                "concept": "revenue",
            }
        )
        result = normalize_annual_filings(submissions, pd.DataFrame(rows)).iloc[0]
        self.assertEqual(result["filed"], pd.Timestamp("2024-02-15"))
        self.assertAlmostEqual(result["gross_margin"], 0.4)
        self.assertAlmostEqual(result["operating_margin"], 0.2)
        self.assertAlmostEqual(result["cash_flow_margin"], 0.15)
        self.assertAlmostEqual(result["return_on_assets"], 10 / 180)
        self.assertAlmostEqual(result["liabilities_to_assets"], 0.4)
        self.assertAlmostEqual(result["asset_growth"], 0.25)
        self.assertAlmostEqual(result["net_margin"], 0.1)
        self.assertAlmostEqual(result["equity_to_assets"], 0.6)
        self.assertAlmostEqual(result["cash_flow_to_assets"], 15 / 180)
        self.assertAlmostEqual(result["revenue_growth"], 0.25)

    def test_derives_gross_profit_and_liabilities_from_balance_sheet_identities(self) -> None:
        submissions = pd.DataFrame(
            {
                "adsh": ["x"],
                "cik": [1],
                "name": ["Example"],
                "sic": [1000],
                "form": ["10-K"],
                "period": [pd.Timestamp("2023-12-31")],
                "fy": [2023],
                "fp": ["FY"],
                "filed": [pd.Timestamp("2024-02-15")],
                "instance": ["example.htm"],
            }
        )
        facts = pd.DataFrame(
            [
                (
                    "RevenueFromContractWithCustomerExcludingAssessedTax",
                    "revenue",
                    100,
                    4,
                    "2023-12-31",
                ),
                ("CostOfGoodsAndServicesSold", "cost_of_revenue", 60, 4, "2023-12-31"),
                ("OperatingIncomeLoss", "operating_income", 20, 4, "2023-12-31"),
                ("NetIncomeLoss", "net_income", 10, 4, "2023-12-31"),
                (
                    "NetCashProvidedByUsedInOperatingActivities",
                    "operating_cash_flow",
                    15,
                    4,
                    "2023-12-31",
                ),
                ("Assets", "assets", 200, 0, "2023-12-31"),
                ("Assets", "assets", 160, 0, "2022-12-31"),
                (
                    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
                    "equity",
                    120,
                    0,
                    "2023-12-31",
                ),
            ],
            columns=["tag", "concept", "value", "qtrs", "ddate"],
        )
        facts["adsh"] = "x"
        facts["version"] = "us-gaap/2023"
        facts["ddate"] = pd.to_datetime(facts["ddate"])
        facts["uom"] = "USD"

        result = normalize_annual_filings(submissions, facts).iloc[0]

        self.assertAlmostEqual(result["gross_margin"], 0.4)
        self.assertAlmostEqual(result["liabilities_to_assets"], 0.4)

    def test_sector_pilot_is_deterministic_and_balanced(self) -> None:
        frame = pd.DataFrame(
            {
                "ticker": ["A", "B", "C", "D", "E", "F"],
                "sector": ["One", "One", "One", "Two", "Two", "Two"],
            }
        )
        result = select_sector_pilot(frame, count=4)
        self.assertEqual(result["ticker"].tolist(), ["A", "D", "B", "E"])


if __name__ == "__main__":
    unittest.main()
