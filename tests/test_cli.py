import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

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


class PolicyConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.config_path = Path(self.tmpdir.name) / "policies.ini"
        self.config_path.write_text(
            "[prod-api]\n"
            "strategy = fixed\n"
            "base = 2\n"
            "attempts = 3\n"
        )

    def test_loads_named_policy(self):
        out = StringIO()
        with redirect_stdout(out):
            code = main(["--config", str(self.config_path), "--policy", "prod-api", "--format", "json"])
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(len(payload["attempts"]), 3)
        self.assertEqual(payload["attempts"][0]["delay_seconds"], 2.0)

    def test_explicit_flag_overrides_policy_value(self):
        out = StringIO()
        with redirect_stdout(out):
            code = main(
                [
                    "--config", str(self.config_path),
                    "--policy", "prod-api",
                    "--attempts", "5",
                    "--format", "json",
                ]
            )
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(len(payload["attempts"]), 5)

    def test_unknown_policy_name_is_a_clean_error(self):
        err = StringIO()
        with redirect_stderr(err):
            code = main(["--config", str(self.config_path), "--policy", "nope"])
        self.assertEqual(code, 1)
        self.assertIn("nope", err.getvalue())

    def test_missing_config_file_is_a_clean_error(self):
        err = StringIO()
        with redirect_stderr(err):
            code = main(["--config", str(self.tmpdir.name) + "/missing.ini", "--policy", "prod-api"])
        self.assertEqual(code, 1)
        self.assertIn("not found", err.getvalue())

    def test_policy_without_config_is_a_clean_error(self):
        err = StringIO()
        with redirect_stderr(err):
            code = main(["--policy", "prod-api"])
        self.assertEqual(code, 1)
        self.assertIn("--config", err.getvalue())

    def test_list_policies(self):
        out = StringIO()
        with redirect_stdout(out):
            code = main(["--config", str(self.config_path), "--list-policies"])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().splitlines(), ["prod-api"])


if __name__ == "__main__":
    unittest.main()
