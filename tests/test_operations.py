import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from risk_managed_momentum.features.build import build_research_dataset
from risk_managed_momentum.models.hazard import fit_hazard_model
from risk_managed_momentum.operations.artifacts import publish_atomic_run
from risk_managed_momentum.operations.monitoring import (
    build_health_report,
    population_stability_index,
)
from risk_managed_momentum.operations.refresh import atomic_write_dataframes, merge_bar_history
from risk_managed_momentum.operations.registry import (
    activate_model,
    load_active_model,
    load_model_pointer,
    register_model_artifact,
    set_model_pointer,
)
from risk_managed_momentum.operations.runtime import ConcurrentRunError, exclusive_run_lock
from scripts.run_scheduled_operations import alert_signature, alert_transition


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

    def test_atomic_run_rejects_nonfinite_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            publish_atomic_run(
                Path(directory),
                "run-nan",
                signals=pd.DataFrame(),
                health={"score_psi": float("nan")},
                manifest={"version": "1"},
            )

    def test_model_registry_round_trip_and_checksum(self) -> None:
        episodes = pd.DataFrame(
            {
                "factor_a": np.linspace(-1.0, 1.0, 20),
                "factor_b": np.tile([0.0, 1.0], 10),
                "first_breach_days": [5.0, 15.0, np.nan, np.nan] * 5,
            }
        )
        fitted = fit_hazard_model(
            episodes,
            ["factor_a", "factor_b"],
            [10, 20],
            c=1.0,
            maximum_iterations=200,
            random_seed=7,
        )
        metadata = {
            "model_specification": "test-v1",
            "training_data_sha256": "data-hash",
            "training_config_sha256": "config-hash",
            "training_last_episode_date": "2024-12-31",
            "training_episodes": len(episodes),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact, reused = register_model_artifact(root, fitted, metadata)
            self.assertFalse(reused)
            _, reused = register_model_artifact(root, fitted, metadata)
            self.assertTrue(reused)
            activate_model(root, artifact.name)
            set_model_pointer(root, artifact.name, "SHADOW")
            loaded, loaded_metadata, loaded_path = load_active_model(root)
            self.assertEqual(loaded.feature_columns, ["factor_a", "factor_b"])
            self.assertEqual(loaded_metadata["artifact_id"], artifact.name)
            self.assertEqual(loaded_path, artifact)
            shadow, _, _ = load_model_pointer(root, "SHADOW")
            self.assertEqual(shadow.feature_columns, loaded.feature_columns)
            model_path = artifact / "model.joblib"
            model_path.write_bytes(model_path.read_bytes() + b"tampered")
            with self.assertRaises(ValueError):
                load_active_model(root)

    def test_health_report_fails_for_stale_data_and_stays_json_safe(self) -> None:
        dates = pd.bdate_range("2024-01-01", periods=200)
        market_date = dates[-1]
        price = pd.DataFrame({"A": np.linspace(100.0, 120.0, len(dates))}, index=dates)
        membership = pd.DataFrame(True, index=dates, columns=["A"])
        reference = pd.DataFrame(
            {"factor": np.linspace(0.0, 1.0, 100), "risk": np.linspace(0.0, 1.0, 100)}
        )
        report = build_health_report(
            requested_as_of=market_date + pd.Timedelta(days=10),
            market_data_date=market_date,
            price=price,
            membership=membership,
            reference_episodes=reference,
            recent_episodes=reference.copy(),
            feature_columns=["factor"],
            score_column="risk",
            quality_config={
                "minimum_history_trading_days": 180,
                "minimum_latest_membership_coverage": 0.95,
                "maximum_market_data_staleness_calendar_days": 4,
                "minimum_recent_episodes": 25,
            },
            drift_config={"bins": 10, "warning_psi": 0.10, "failure_psi": 0.25},
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["signals_authorized"])
        self.assertFalse(report["gates"]["market_data_staleness_days"]["passed"])

    def test_bar_refresh_replaces_overlap_without_duplicates(self) -> None:
        columns = [
            "timestamp",
            "date",
            "ticker",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
        existing = pd.DataFrame(
            [
                ["2024-01-01T00:00:00Z", "2024-01-01", "A", 1, 1, 1, 1, 10],
                ["2024-01-02T00:00:00Z", "2024-01-02", "A", 2, 2, 2, 2, 20],
            ],
            columns=columns,
        )
        incoming = pd.DataFrame(
            [
                ["2024-01-02T00:00:00Z", "2024-01-02", "A", 3, 3, 3, 3, 30],
                ["2024-01-03T00:00:00Z", "2024-01-03", "A", 4, 4, 4, 4, 40],
            ],
            columns=columns,
        )
        merged = merge_bar_history(
            existing,
            incoming,
            replace_from=pd.Timestamp("2024-01-02"),
        )
        self.assertEqual(merged["close"].tolist(), [1, 3, 4])
        self.assertFalse(merged.duplicated(["ticker", "date"]).any())

    def test_exclusive_run_lock_rejects_concurrent_holder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "pipeline.lock"
            with (
                exclusive_run_lock(lock),
                self.assertRaises(ConcurrentRunError),
                exclusive_run_lock(lock),
            ):
                self.fail("A second lock holder should never enter")

    def test_dataframe_transaction_can_replace_multiple_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "one" / "first.csv"
            second = root / "two" / "second.csv"
            atomic_write_dataframes(
                {
                    first: pd.DataFrame({"value": [1]}),
                    second: pd.DataFrame({"value": [2]}),
                }
            )
            self.assertEqual(pd.read_csv(first)["value"].tolist(), [1])
            self.assertEqual(pd.read_csv(second)["value"].tolist(), [2])

    def test_dataframe_transaction_can_write_deterministic_gzip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "frame.csv.gz"
            frame = pd.DataFrame({"value": [1, 2]})
            options = {
                destination: {"compression": {"method": "gzip", "mtime": 0}}
            }
            atomic_write_dataframes({destination: frame}, csv_options=options)
            first = destination.read_bytes()
            atomic_write_dataframes({destination: frame}, csv_options=options)
            self.assertEqual(destination.read_bytes(), first)

    def test_alert_transition_suppresses_duplicate_and_reports_recovery(self) -> None:
        failure = {
            "status": "FAIL",
            "health_status": "FAIL",
            "stage": "risk_pipeline",
            "pipeline_result": {"run_id": "run-1", "market_data_date": "2026-10-23"},
            "steps": [{"stderr": ""}],
        }
        should_alert, reason = alert_transition(None, failure, alert_on_warn=True)
        self.assertTrue(should_alert)
        self.assertEqual(reason, "new_or_changed_problem")
        previous = {
            "problem": True,
            "signature": alert_signature(failure),
        }
        should_alert, reason = alert_transition(previous, failure, alert_on_warn=True)
        self.assertFalse(should_alert)
        self.assertEqual(reason, "unchanged")
        recovery = {
            **failure,
            "status": "PASS",
            "health_status": "PASS",
            "pipeline_result": {"run_id": "run-2", "market_data_date": "2026-10-24"},
        }
        should_alert, reason = alert_transition(previous, recovery, alert_on_warn=True)
        self.assertTrue(should_alert)
        self.assertEqual(reason, "recovered")


if __name__ == "__main__":
    unittest.main()

