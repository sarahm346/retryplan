import tempfile
import unittest
from pathlib import Path

from retryplan.config import list_policies, load_policy

SAMPLE_CONFIG = """
[prod-api]
strategy = exponential
base = 0.5
factor = 2
attempts = 6
max-delay = 10
jitter = full
seed = 42

[batch-job]
strategy = linear
base = 1
increment = 5
attempts = 3
"""


class ConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.config_path = Path(self.tmpdir.name) / "policies.ini"
        self.config_path.write_text(SAMPLE_CONFIG)


class LoadPolicyTests(ConfigTestCase):
    def test_parses_fields_to_expected_types(self):
        values = load_policy(str(self.config_path), "prod-api")
        self.assertEqual(
            values,
            {
                "strategy": "exponential",
                "base": 0.5,
                "factor": 2.0,
                "attempts": 6,
                "max_delay": 10.0,
                "jitter": "full",
                "seed": 42,
            },
        )

    def test_only_defines_fields_present_in_section(self):
        values = load_policy(str(self.config_path), "batch-job")
        self.assertEqual(
            values,
            {
                "strategy": "linear",
                "base": 1.0,
                "increment": 5.0,
                "attempts": 3,
            },
        )

    def test_missing_file_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_policy(str(Path(self.tmpdir.name) / "missing.ini"), "prod-api")

    def test_missing_section_raises_key_error(self):
        with self.assertRaises(KeyError):
            load_policy(str(self.config_path), "does-not-exist")

    def test_unknown_field_raises_value_error(self):
        bad_path = Path(self.tmpdir.name) / "bad.ini"
        bad_path.write_text("[x]\nbogus-field = 1\n")
        with self.assertRaises(ValueError):
            load_policy(str(bad_path), "x")


class ListPoliciesTests(ConfigTestCase):
    def test_returns_section_names(self):
        self.assertEqual(list_policies(str(self.config_path)), ["prod-api", "batch-job"])

    def test_missing_file_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            list_policies(str(Path(self.tmpdir.name) / "missing.ini"))


if __name__ == "__main__":
    unittest.main()
