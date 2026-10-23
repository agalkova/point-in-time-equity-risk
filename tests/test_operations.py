import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from risk_managed_momentum.features.build import build_research_dataset
from risk_managed_momentum.operations.artifacts import publish_atomic_run
from risk_managed_momentum.operations.monitoring import population_stability_index


class OperationsTests(unittest.TestCase):
    def test_unlabeled_mode_keeps_latest_eligible_signal(self) -> None:
        dates = pd.bdate_range("2024-01-01", periods=180)
        price = pd.DataFrame(
            {"A": 100.0 * np.power(1.004, np.arange(len(dates), dtype=float))},
            index=dates,
        )
        volume = pd.DataFrame(1_000_000.0, index=dates, columns=["A"])
        config = {
            "eligibility": {"minimum_runup": 0.20, "maximum_distance_below_peak": -0.10},
            "target": {"horizon_days": 40, "drawdown_threshold": -0.15},
        }
        research = build_research_dataset(price, volume, config)
        live = build_research_dataset(price, volume, config, include_unlabeled=True)
        self.assertNotIn(dates[-1], set(research.frame["date"]))
        latest = live.frame[live.frame["date"].eq(dates[-1])]
        self.assertEqual(len(latest), 1)
        self.assertTrue(latest["target"].isna().all())

    def test_population_stability_index_detects_shift(self) -> None:
        reference = np.linspace(0.0, 1.0, 1000)
        self.assertLess(population_stability_index(reference, reference), 1e-12)
        self.assertGreater(population_stability_index(reference, reference + 1.0), 0.25)

    def test_atomic_run_is_idempotent_and_rejects_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            signals = pd.DataFrame({"ticker": ["A"], "risk": [0.2]})
            first, reused = publish_atomic_run(
                root,
                "run-1",
                signals=signals,
                health={"status": "PASS"},
                manifest={"version": "1"},
            )
            self.assertTrue(first.exists())
            _, reused = publish_atomic_run(
                root,
                "run-1",
                signals=signals,
                health={"status": "PASS"},
                manifest={"version": "1"},
            )
            self.assertTrue(reused)
            with self.assertRaises(FileExistsError):
                publish_atomic_run(
                    root,
                    "run-1",
                    signals=pd.DataFrame({"ticker": ["B"], "risk": [0.2]}),
                    health={"status": "PASS"},
                    manifest={"version": "1"},
                )


if __name__ == "__main__":
    unittest.main()

