import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd

from risk_managed_momentum.config import load_config
from risk_managed_momentum.features.episodes import build_exuberance_episode_dataset
from risk_managed_momentum.models.hazard import fit_hazard_model
from risk_managed_momentum.operations.artifacts import publish_atomic_run
from risk_managed_momentum.operations.pipeline import score_and_monitor
from risk_managed_momentum.operations.registry import (
    activate_model,
    load_active_model,
    register_model_artifact,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PipelineIntegrationTests(unittest.TestCase):
    def test_synthetic_data_to_registered_model_to_published_signals(self) -> None:
        base_config = load_config(PROJECT_ROOT / "configs/research.toml")
        hazard_config = {
            "episode": {
                "washout_trading_days": 20,
                "runup_lookback_days": 60,
                "minimum_runup": 0.20,
                "peak_lookback_days": 60,
                "maximum_distance_below_peak": -0.10,
            },
            "outcome": {
                "drawdown_threshold": -0.15,
                "maximum_horizon_days": 60,
                "horizon_end_days": [10, 20, 40, 60],
            },
        }
        rng = np.random.default_rng(4)
        dates = pd.bdate_range("2022-01-03", periods=420)
        tickers = [f"SYN{index:02d}" for index in range(12)]
        returns = rng.normal(0.0002, 0.008, (len(dates), len(tickers)))
        for ticker_index in range(len(tickers)):
            for day in [130 + ticker_index % 3 * 5, 260 + ticker_index % 4 * 4, 419]:
                returns[day, ticker_index] += 0.24
        price = pd.DataFrame(
            100.0 * np.exp(np.cumsum(returns, axis=0)),
            index=dates,
            columns=tickers,
        )
        volume = pd.DataFrame(
            rng.lognormal(13.0, 0.25, price.shape),
            index=dates,
            columns=tickers,
        )
        membership = pd.DataFrame(True, index=dates, columns=tickers)
        episodes = build_exuberance_episode_dataset(
            price,
            volume,
            base_config,
            hazard_config,
            membership=membership,
            include_unlabeled=True,
        )
        training = episodes.frame.copy()
        training["first_breach_days"] = np.resize(
            np.array([5.0, 15.0, 30.0, 50.0, np.nan]), len(training)
        )
        model = fit_hazard_model(
            training,
            episodes.feature_columns,
            [10, 20, 40, 60],
            c=0.01,
            maximum_iterations=500,
            random_seed=42,
        )
        operations = {
            "pipeline": {"recent_monitoring_calendar_days": 1000},
            "monitoring_reference": {
                "start": str(dates[0].date()),
                "end": str(dates[-1].date()),
            },
            "quality_gates": {
                "minimum_history_trading_days": 180,
                "minimum_latest_membership_coverage": 0.95,
                "maximum_market_data_staleness_calendar_days": 4,
                "minimum_recent_episodes": 1,
            },
            "drift": {"bins": 5, "warning_psi": 0.10, "failure_psi": 0.25},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact, _ = register_model_artifact(
                root / "registry",
                model,
                {
                    "model_specification": "synthetic-test-v1",
                    "training_data_sha256": "synthetic-data",
                    "training_config_sha256": "synthetic-config",
                    "training_last_episode_date": str(training["date"].max().date()),
                    "training_episodes": len(training),
                },
            )
            activate_model(root / "registry", artifact.name)
            frozen_model, metadata, _ = load_active_model(root / "registry")
            result = score_and_monitor(
                price=price,
                volume=volume,
                membership=membership,
                requested_as_of=dates[-1],
                market_data_date=dates[-1],
                model=frozen_model,
                base_config=deepcopy(base_config),
                hazard_config=hazard_config,
                operations_config=operations,
            )
            output, reused = publish_atomic_run(
                root / "runs",
                "synthetic-e2e",
                signals=result.signals,
                health=result.health,
                manifest={"model_artifact_id": metadata["artifact_id"]},
            )
            self.assertFalse(reused)
            self.assertEqual(result.health["status"], "PASS")
            self.assertGreater(len(result.signals), 0)
            self.assertTrue((output / "manifest.json").exists())
            self.assertTrue((output / "signals.csv").exists())


if __name__ == "__main__":
    unittest.main()
