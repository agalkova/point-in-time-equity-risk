import tempfile
import unittest
from pathlib import Path

from risk_managed_momentum.data.corporate_actions import (
    load_corporate_action_overrides,
    normalize_corporate_actions,
)


class CorporateActionTests(unittest.TestCase):
    def test_normalizes_categorized_actions(self) -> None:
        frame = normalize_corporate_actions(
            {
                "corporate_actions": {
                    "cash_mergers": [
                        {
                            "id": "one",
                            "acquiree_symbol": "OLD",
                            "effective_date": "2024-03-01",
                            "rate": 42.0,
                        }
                    ],
                    "name_changes": [
                        {
                            "id": "two",
                            "old_symbol": "AAA",
                            "new_symbol": "BBB",
                            "process_date": "2024-02-01",
                        }
                    ],
                }
            }
        )
        self.assertEqual(frame["action_symbol"].tolist(), ["AAA", "OLD"])
        self.assertEqual(frame["action_type"].tolist(), ["name_changes", "cash_mergers"])
        self.assertEqual(str(frame.iloc[1]["action_date"]), "2024-03-01")

    def test_loads_reviewed_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "actions.toml"
            path.write_text(
                '[[action]]\naction_symbol="OLD"\naction_date="2024-01-02"\n'
                'action_type="cash_mergers"\nrate=42.0\n'
            )
            frame = load_corporate_action_overrides(path)
        self.assertEqual(frame.iloc[0]["action_symbol"], "OLD")
        self.assertEqual(str(frame.iloc[0]["action_date"]), "2024-01-02")


if __name__ == "__main__":
    unittest.main()
