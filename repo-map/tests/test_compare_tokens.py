import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compare_tokens.py"
spec = importlib.util.spec_from_file_location("compare_tokens", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def record(mode, tokens, run=1, correct=True):
    return {"task": "locate", "run": run, "mode": mode, "input_tokens": tokens,
            "output_tokens": 0, "correct": correct}


class CompareTokensTests(unittest.TestCase):
    def test_setup_is_counted_once_and_break_even_uses_paired_savings(self):
        result = module.compare([record("baseline", 100), record("repo-map", 60),
                                 record("baseline", 120, 2), record("repo-map", 80, 2)], 50)
        self.assertEqual(result["saved_tokens"], 30)
        self.assertEqual(result["savings_percent"], 13.64)
        self.assertEqual(result["median_paired_saved_tokens"], 40)
        self.assertEqual(result["break_even_queries_estimate"], 2)

    def test_incorrect_and_missing_pairs_do_not_count_as_savings(self):
        result = module.compare([record("baseline", 100), record("repo-map", 60),
                                 record("baseline", 1000, 2), record("repo-map", 1, 2, False),
                                 record("baseline", 200, 3)])
        self.assertEqual(result["successful_pairs"], 1)
        self.assertEqual(result["excluded_pairs"], 2)
        self.assertEqual(result["saved_tokens"], 40)
        self.assertEqual(result["quality"]["baseline"]["success_rate"], 1)
        self.assertEqual(result["quality"]["repo-map"]["success_rate"], 0.5)

    def test_regression_and_zero_baseline(self):
        result = module.compare([record("baseline", 100), record("repo-map", 150)])
        self.assertEqual(result["savings_percent"], -50)
        self.assertIsNone(result["break_even_queries_estimate"])
        result = module.compare([record("baseline", 0), record("repo-map", 0)])
        self.assertIsNone(result["savings_percent"])

    def test_rejects_invalid_duplicate_and_unpaired_records(self):
        baseline = record("baseline", 100)
        mapped = record("repo-map", 50)
        for invalid in ([baseline, baseline], [baseline],
                        [baseline, {**mapped, "input_tokens": -1}],
                        [baseline, {**mapped, "input_tokens": True}],
                        [baseline, {**mapped, "correct": "true"}],
                        [baseline, {**mapped, "mode": "unknown"}], [None]):
            with self.subTest(records=invalid), self.assertRaises(ValueError):
                module.compare(invalid)


if __name__ == "__main__":
    unittest.main()
