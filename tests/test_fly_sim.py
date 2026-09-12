import json
import unittest
from pathlib import Path

from fly_sim import run_indicator, run_survey


ROOT = Path(__file__).resolve().parents[1]


class FlySimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.indicators = json.loads((ROOT / "data" / "indicators.json").read_text())

    def test_single_indicator_returns_stoplight_response(self):
        result = run_indicator(self.indicators[0], seed=7, steps=36)
        self.assertIn(result["answer"], {"red", "yellow", "green"})
        self.assertEqual(len(result["trace"]), 36)
        self.assertEqual(len(result["activity"]), 12)
        self.assertGreaterEqual(result["confidence"], 0)
        self.assertLessEqual(result["confidence"], 1)

    def test_same_seed_is_reproducible(self):
        first = run_indicator(self.indicators[1], seed=42)
        second = run_indicator(self.indicators[1], seed=42)
        self.assertEqual(first["answer"], second["answer"])
        self.assertEqual(first["metrics"], second["metrics"])

    def test_survey_has_one_result_per_indicator(self):
        survey = run_survey(self.indicators, seed=3)
        self.assertEqual(len(survey["results"]), len(self.indicators))
        self.assertEqual(sum(survey["counts"].values()), len(self.indicators))


if __name__ == "__main__":
    unittest.main()

