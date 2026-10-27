import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from risk_managed_momentum.data.sec_identity import (
    attach_interval_names,
    build_sec_identity_map,
    carry_forward_resolved_identities,
    load_fsds_submission_registry,
    membership_intervals,
    normalize_company_name,
    resolve_identity_names,
)


class SecIdentityTests(unittest.TestCase):
    def test_carries_forward_a_resolved_matching_interval(self) -> None:
        current = pd.DataFrame(
            {
                "ticker": ["OLD"],
                "interval": [1],
                "valid_from": [pd.Timestamp("2020-01-01")],
                "valid_to": [pd.Timestamp("2021-01-01")],
                "cik": pd.Series([pd.NA], dtype="Int64"),
                "sec_name": [pd.NA],
                "identity_source": ["unresolved"],
                "confidence": ["none"],
                "name_similarity": [0.0],
                "status": ["REVIEW"],
                "reason": ["No safe match"],
            }
        )
        previous = current.copy()
        previous.loc[
            0, ["cik", "sec_name", "identity_source", "confidence", "status", "reason"]
        ] = [
            123,
            "Old Company",
            "sec_fsds_submission_name",
            "high",
            "RESOLVED",
            "Decisive filing-name match",
        ]

        result = carry_forward_resolved_identities(current, previous)

        self.assertEqual(result.iloc[0]["cik"], 123)
        self.assertEqual(result.iloc[0]["status"], "RESOLVED")

    def test_loads_filing_names_from_fsds_archive(self) -> None:
        submissions = pd.DataFrame(
            {
                "cik": [123, 123, 456],
                "name": ["Example Corporation", "Example Corporation", "Other Bank, Inc."],
                "filed": [20240110, 20240210, 20240310],
            }
        )
        with TemporaryDirectory() as directory:
            archive_path = Path(directory) / "quarter.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("sub.txt", submissions.to_csv(sep="\t", index=False))

            result = load_fsds_submission_registry(archive_path)

        self.assertEqual(result["cik"].tolist(), [123, 123, 456])
        self.assertEqual(result["normalized_name"].tolist(), ["example", "example", "other bank"])
        self.assertEqual(result["filed"].dt.year.tolist(), [2024, 2024, 2024])

    def test_filing_name_match_is_time_aligned_to_membership(self) -> None:
        identities = pd.DataFrame(
            {
                "ticker": ["OLD"],
                "interval": [1],
                "valid_from": [pd.Timestamp("2015-01-01")],
                "valid_to": [pd.Timestamp("2016-01-31")],
                "membership_name": ["Same Name Corporation"],
                "cik": pd.Series([pd.NA], dtype="Int64"),
                "sec_name": [pd.NA],
                "identity_source": ["unresolved"],
                "confidence": ["none"],
                "name_similarity": [0.0],
                "status": ["REVIEW"],
                "reason": ["No safe match"],
            }
        )
        entities = pd.DataFrame(
            {
                "cik": [111, 222],
                "sec_name": ["SAME NAME CORP", "SAME NAME CORP"],
                "normalized_name": ["same name", "same name"],
                "filed": pd.to_datetime(["2015-03-01", "2025-03-01"]),
            }
        )

        result = resolve_identity_names(identities, entities)

        self.assertEqual(result.iloc[0]["cik"], 111)

    def test_lookalike_company_names_do_not_match(self) -> None:
        identities = pd.DataFrame(
            {
                "membership_name": ["Alexion Pharmaceuticals"],
                "cik": pd.Series([pd.NA], dtype="Int64"),
                "sec_name": [pd.NA],
                "identity_source": ["unresolved"],
                "confidence": ["none"],
                "name_similarity": [0.0],
                "status": ["REVIEW"],
                "reason": ["No safe match"],
            }
        )
        entities = pd.DataFrame(
            {
                "cik": [1062822],
                "sec_name": ["LEXICON PHARMACEUTICALS, INC."],
                "normalized_name": ["lexicon pharmaceuticals"],
            }
        )

        result = resolve_identity_names(identities, entities)

        self.assertEqual(result.iloc[0]["status"], "REVIEW")
        self.assertTrue(pd.isna(result.iloc[0]["cik"]))

    def test_name_normalization_removes_legal_suffixes(self) -> None:
        self.assertEqual(normalize_company_name("The Example Corporation /DE/"), "example")

    def test_reused_ticker_requires_review_for_old_interval(self) -> None:
        daily = pd.DataFrame(
            {
                "date": pd.to_datetime(["2020-01-02", "2020-01-03", "2024-01-02", "2024-01-03"]),
                "ticker": ["OLD", "OLD", "OLD", "OLD"],
            }
        )
        current = pd.DataFrame({"ticker": ["OLD"], "security": ["New Company"], "cik": [200]})
        changes = pd.DataFrame(
            {
                "date": pd.to_datetime(["2020-01-06", "2024-01-02"]),
                "added_ticker": [None, "OLD"],
                "added_security": [None, "New Company"],
                "removed_ticker": ["OLD", None],
                "removed_security": ["Old Company", None],
            }
        )
        intervals = attach_interval_names(membership_intervals(daily), current, changes)
        registry = pd.DataFrame(
            {"sec_ticker": ["OLD"], "cik": [200], "sec_name": ["New Company Inc."]}
        )

        result = build_sec_identity_map(intervals, current, registry)

        self.assertEqual(result["status"].tolist(), ["REVIEW", "RESOLVED"])
        self.assertTrue(pd.isna(result.iloc[0]["cik"]))
        self.assertEqual(result.iloc[1]["cik"], 200)

    def test_unique_historical_ticker_with_matching_name_resolves(self) -> None:
        intervals = pd.DataFrame(
            {
                "ticker": ["HIST"],
                "interval": [1],
                "valid_from": [pd.Timestamp("2020-01-01")],
                "valid_to": [pd.Timestamp("2021-01-01")],
                "membership_days": [250],
                "membership_name": ["Historical Systems, Inc."],
                "name_source": ["membership_removal"],
            }
        )
        current = pd.DataFrame(columns=["ticker", "security", "cik"])
        registry = pd.DataFrame(
            {"sec_ticker": ["HIST"], "cik": [123], "sec_name": ["Historical Systems Inc"]}
        )

        result = build_sec_identity_map(intervals, current, registry)

        self.assertEqual(result.iloc[0]["status"], "RESOLVED")
        self.assertEqual(result.iloc[0]["cik"], 123)

    def test_filing_name_fallback_requires_a_decisive_match(self) -> None:
        identities = pd.DataFrame(
            {
                "membership_name": ["Acme Semiconductor Holdings"],
                "cik": pd.Series([pd.NA], dtype="Int64"),
                "sec_name": [pd.NA],
                "identity_source": ["unresolved"],
                "confidence": ["none"],
                "name_similarity": [0.0],
                "status": ["REVIEW"],
                "reason": ["No safe SEC ticker/CIK match"],
            }
        )
        entities = pd.DataFrame(
            {
                "cik": [456, 789],
                "sec_name": ["ACME SEMICONDUCTOR HOLDINGS INC", "UNRELATED INDUSTRIES INC"],
                "normalized_name": ["acme semiconductor holdings", "unrelated industries"],
            }
        )

        result = resolve_identity_names(identities, entities)

        self.assertEqual(result.iloc[0]["status"], "RESOLVED")
        self.assertEqual(result.iloc[0]["cik"], 456)
        self.assertEqual(result.iloc[0]["identity_source"], "sec_fsds_submission_name")


if __name__ == "__main__":
    unittest.main()
