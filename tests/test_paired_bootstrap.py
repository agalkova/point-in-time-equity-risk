import unittest

import numpy as np
import pandas as pd

from risk_managed_momentum.evaluation.paired_bootstrap import paired_date_block_bootstrap


class PairedBootstrapTests(unittest.TestCase):
    def test_detects_better_paired_scores(self) -> None:
        dates = np.repeat(pd.bdate_range("2024-01-01", periods=20), 4)
        target = np.tile([0, 0, 1, 1], 20)
        frame = pd.DataFrame(
            {
                "date": dates,
                "target": target,
                "champion": np.tile([0.4, 0.6, 0.4, 0.6], 20),
                "challenger": np.tile([0.1, 0.2, 0.8, 0.9], 20),
            }
        )
        result = paired_date_block_bootstrap(
            frame,
            target_column="target",
            first_score_column="champion",
            second_score_column="challenger",
            block_length=5,
            iterations=100,
            random_seed=7,
        )
        self.assertTrue(result["ci_lower_95"].gt(0.0).all())


if __name__ == "__main__":
    unittest.main()
