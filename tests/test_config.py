import unittest
from datetime import timedelta
from pathlib import Path

from risk_managed_momentum.config import configured_ranges, load_config


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(PROJECT_ROOT / "configs" / "research.toml")
        self.ranges = configured_ranges(self.config)

    def test_development_samples_do_not_overlap(self) -> None:
        self.assertLess(self.ranges["train"].end, self.ranges["validation"].start)
        self.assertLess(self.ranges["validation"].end, self.ranges["legacy_test"].start)

    def test_split_gaps_exceed_target_horizon_in_calendar_days(self) -> None:
        conservative_gap = timedelta(days=int(self.config["target"]["horizon_days"] * 7 / 5))
        self.assertLess(
            self.ranges["train"].end + conservative_gap,
            self.ranges["validation"].start,
        )
        self.assertLess(
            self.ranges["validation"].end + conservative_gap,
            self.ranges["legacy_test"].start,
        )

    def test_modern_holdout_starts_after_reconciliation_period(self) -> None:
        self.assertLess(
            self.ranges["source_reconciliation"].end,
            self.ranges["modern_holdout"].start,
        )


if __name__ == "__main__":
    unittest.main()

