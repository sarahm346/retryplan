import json
import unittest
from contextlib import redirect_stdout
from io import StringIO

from retryplan.cli import format_json, format_table, main


class FormatJsonTests(unittest.TestCase):
    def test_shape_matches_delays(self):
        payload = json.loads(format_json([0.5, 1.0, 2.0]))
        self.assertEqual(
            payload["attempts"],
            [
                {"attempt": 1, "delay_seconds": 0.5},
                {"attempt": 2, "delay_seconds": 1.0},
                {"attempt": 3, "delay_seconds": 2.0},
            ],
        )
        self.assertEqual(payload["total_wait_seconds"], 3.5)

    def test_empty_schedule(self):
        payload = json.loads(format_json([]))
        self.assertEqual(payload["attempts"], [])
        self.assertEqual(payload["total_wait_seconds"], 0.0)


class MainJsonOutputTests(unittest.TestCase):
    def test_prints_valid_json(self):
        out = StringIO()
        with redirect_stdout(out):
            code = main(["--strategy", "fixed", "--base", "1", "--attempts", "3", "--format", "json"])
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(len(payload["attempts"]), 3)
        self.assertEqual(payload["total_wait_seconds"], 3.0)

    def test_table_is_still_the_default(self):
        out = StringIO()
        with redirect_stdout(out):
            main(["--strategy", "fixed", "--base", "1", "--attempts", "2"])
        self.assertIn("attempt  delay (s)", out.getvalue())


class FormatTableTests(unittest.TestCase):
    def test_includes_total(self):
        table = format_table([1.0, 2.0])
        self.assertIn("total wait: 3.000s", table)


if __name__ == "__main__":
    unittest.main()
