import unittest

import pandas as pd

from risk_managed_momentum.data.sp400 import build_event_sourced_snapshots, roster_jaccard


class Sp400MembershipTests(unittest.TestCase):
    def test_removals_precede_additions_on_same_date(self) -> None:
        seed = pd.DataFrame(
            {
                "effective_date": ["2019-01-01"] * 400,
                "ticker": [f"T{number:03d}" for number in range(400)],
            }
        )
        changes = pd.DataFrame(
            {
                "date": ["2020-01-02", "2020-01-02"],
                "action": ["added", "removed"],
                "ticker": ["NEW", "T000"],
            }
        )
        result = build_event_sourced_snapshots(
            seed, changes, start="2020-01-01", end="2020-01-03"
        )
        final = set(result.loc[result["snapshot_date"].eq(pd.Timestamp("2020-01-02")), "ticker"])
        self.assertEqual(len(final), 400)
        self.assertIn("NEW", final)
        self.assertNotIn("T000", final)

    def test_jaccard(self) -> None:
        self.assertEqual(roster_jaccard({"A", "B"}, {"B", "C"}), 1 / 3)


if __name__ == "__main__":
    unittest.main()
