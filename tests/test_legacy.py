import unittest

import numpy as np
import pandas as pd

from risk_managed_momentum.data.legacy import audit_legacy_wide


class LegacyAuditTests(unittest.TestCase):
    def test_audit_reports_contract_violations(self) -> None:
        dates = pd.date_range("2024-01-01", periods=2)
        price = pd.DataFrame({"AAA": [10.0, 0.0], "BBB": [np.nan, 20.0]}, index=dates)
        volume = pd.DataFrame({"AAA": [100.0, -1.0], "BBB": [50.0, 200.0]}, index=dates)
        audit = audit_legacy_wide(price, volume)
        self.assertEqual(audit.nonpositive_prices, 1)
        self.assertEqual(audit.negative_volumes, 1)
        self.assertEqual(audit.mismatched_missing_cells, 1)


if __name__ == "__main__":
    unittest.main()

