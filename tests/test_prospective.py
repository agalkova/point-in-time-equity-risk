import tempfile
import unittest
from pathlib import Path

import pandas as pd

from risk_managed_momentum.prospective import append_ledger_entry, write_immutable_frame


class ProspectiveRecordTests(unittest.TestCase):
    def test_snapshot_cannot_be_silently_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "signal.csv"
            original = pd.DataFrame({"ticker": ["A"], "weight": [1.0]})
            write_immutable_frame(path, original)
            write_immutable_frame(path, original)
            with self.assertRaises(FileExistsError):
                write_immutable_frame(
                    path,
                    pd.DataFrame({"ticker": ["B"], "weight": [1.0]}),
                )

    def test_ledger_rejects_conflicting_duplicate_date(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.csv"
            append_ledger_entry(path, {"signal_date": "2026-10-30", "digest": "one"})
            append_ledger_entry(path, {"signal_date": "2026-10-30", "digest": "one"})
            with self.assertRaises(FileExistsError):
                append_ledger_entry(
                    path,
                    {"signal_date": "2026-10-30", "digest": "different"},
                )


if __name__ == "__main__":
    unittest.main()
