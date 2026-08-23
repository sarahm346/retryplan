import random
import unittest

from retryplan.policy import (
    apply_equal_jitter,
    apply_full_jitter,
    build_schedule,
    decorrelated_jitter,
    exponential_delay,
    fixed_delay,
    linear_delay,
    total_wait,
)


class FixedDelayTests(unittest.TestCase):
    def test_returns_base(self):
        self.assertEqual(fixed_delay(2.0), 2.0)

    def test_rejects_negative(self):
        with self.assertRaises(ValueError):
            fixed_delay(-1.0)


class LinearDelayTests(unittest.TestCase):
    def test_grows_by_increment(self):
        self.assertEqual(linear_delay(1, base_seconds=1.0, increment_seconds=0.5), 1.0)
        self.assertEqual(linear_delay(3, base_seconds=1.0, increment_seconds=0.5), 2.0)

    def test_rejects_attempt_below_one(self):
        with self.assertRaises(ValueError):
            linear_delay(0, base_seconds=1.0, increment_seconds=0.5)


class ExponentialDelayTests(unittest.TestCase):
    def test_doubles_by_default(self):
        self.assertEqual(exponential_delay(1, base_seconds=1.0), 1.0)
        self.assertEqual(exponential_delay(2, base_seconds=1.0), 2.0)
        self.assertEqual(exponential_delay(4, base_seconds=1.0), 8.0)

    def test_respects_max_delay(self):
        self.assertEqual(exponential_delay(10, base_seconds=1.0, max_delay=5.0), 5.0)

    def test_rejects_factor_below_one(self):
        with self.assertRaises(ValueError):
            exponential_delay(1, base_seconds=1.0, factor=0.5)


class JitterTests(unittest.TestCase):
    def test_full_jitter_is_bounded(self):
        rand = random.Random(1)
        value = apply_full_jitter(4.0, rand)
        self.assertGreaterEqual(value, 0.0)
        self.assertLessEqual(value, 4.0)

    def test_full_jitter_is_deterministic_for_same_seed(self):
        first = apply_full_jitter(4.0, random.Random(7))
        second = apply_full_jitter(4.0, random.Random(7))
        self.assertEqual(first, second)

    def test_equal_jitter_never_drops_below_half(self):
        rand = random.Random(3)
        value = apply_equal_jitter(4.0, rand)
        self.assertGreaterEqual(value, 2.0)
        self.assertLessEqual(value, 4.0)

    def test_decorrelated_jitter_respects_cap(self):
        rand = random.Random(9)
        value = decorrelated_jitter(previous_delay=100.0, base_seconds=1.0, max_delay=5.0, rand=rand)
        self.assertLessEqual(value, 5.0)


class BuildScheduleTests(unittest.TestCase):
    def test_exponential_without_jitter_is_deterministic(self):
        delays = build_schedule("exponential", attempts=4, base_seconds=1.0, factor=2.0)
        self.assertEqual(delays, [1.0, 2.0, 4.0, 8.0])

    def test_same_seed_gives_same_jittered_schedule(self):
        first = build_schedule(
            "exponential", attempts=5, base_seconds=1.0, jitter="full", rand=random.Random(42)
        )
        second = build_schedule(
            "exponential", attempts=5, base_seconds=1.0, jitter="full", rand=random.Random(42)
        )
        self.assertEqual(first, second)

    def test_rejects_jitter_without_rand(self):
        with self.assertRaises(ValueError):
            build_schedule("fixed", attempts=3, base_seconds=1.0, jitter="full")

    def test_rejects_unknown_strategy(self):
        with self.assertRaises(ValueError):
            build_schedule("quadratic", attempts=3, base_seconds=1.0)

    def test_rejects_attempts_below_one(self):
        with self.assertRaises(ValueError):
            build_schedule("fixed", attempts=0, base_seconds=1.0)


class TotalWaitTests(unittest.TestCase):
    def test_sums_delays(self):
        self.assertEqual(total_wait([1.0, 2.0, 3.0]), 6.0)

    def test_empty_schedule_is_zero(self):
        self.assertEqual(total_wait([]), 0.0)


if __name__ == "__main__":
    unittest.main()
