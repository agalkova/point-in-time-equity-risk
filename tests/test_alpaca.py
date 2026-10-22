import unittest

from risk_managed_momentum.data.alpaca import (
    AlpacaDataError,
    AlpacaHistoricalClient,
    normalize_bars,
    normalize_symbols,
)


class AlpacaTests(unittest.TestCase):
    def test_normalize_symbols_is_stable_and_unique(self) -> None:
        self.assertEqual(normalize_symbols([" msft ", "AAPL", "aapl"]), ["AAPL", "MSFT"])

    def test_normalize_multi_symbol_page(self) -> None:
        payload = {
            "bars": {
                "AAPL": [
                    {
                        "t": "2024-01-02T05:00:00Z",
                        "o": 100.0,
                        "h": 105.0,
                        "l": 99.0,
                        "c": 104.0,
                        "v": 1_000,
                        "n": 50,
                        "vw": 102.0,
                    }
                ]
            },
            "next_page_token": None,
        }
        frame = normalize_bars(payload, adjustment="raw", feed="sip")
        self.assertEqual(list(frame["ticker"]), ["AAPL"])
        self.assertEqual(list(frame["feed"]), ["sip"])
        self.assertEqual(list(frame["volume"]), [1_000])

    def test_missing_bars_mapping_is_rejected(self) -> None:
        with self.assertRaises(AlpacaDataError):
            normalize_bars({}, adjustment="raw", feed="sip")

    def test_client_refuses_iex_for_this_project(self) -> None:
        client = AlpacaHistoricalClient("key", "secret")
        with self.assertRaisesRegex(ValueError, "feed='sip'"):
            client.download_daily_bars(
                ["AAPL"],
                start="2024-01-01",
                end="2024-01-02",
                feed="iex",
            )


if __name__ == "__main__":
    unittest.main()

