"""Property-style tests for build_schedule invariants.

Hypothesis is off the table (no third-party deps), so this does the same
thing by hand: generate a few hundred random parameter combinations from a
seeded Random instance and check invariants that should hold across all of
them, rather than hand-picking a handful of example cases.
"""

from __future__ import annotations

import random
import unittest

from retryplan.policy import JITTER_MODES, STRATEGIES, build_schedule, total_wait

RUNS = 500
EPSILON = 1e-9


def random_case(rand: random.Random) -> dict:
    return dict(
        strategy=rand.choice(STRATEGIES),
        attempts=rand.randint(1, 12),
        base_seconds=round(rand.uniform(0, 20), 3),
        factor=round(rand.uniform(1, 4), 3),
        increment_seconds=round(rand.uniform(0, 5), 3),
        max_delay=round(rand.uniform(0, 50), 3) if rand.random() < 0.5 else None,
        jitter=rand.choice((None,) + JITTER_MODES),
        seed=rand.randint(0, 1_000_000),
    )


def build(case: dict) -> list[float]:
    jitter = case["jitter"]
    rand = random.Random(case["seed"]) if jitter else None
    return build_schedule(
        strategy=case["strategy"],
        attempts=case["attempts"],
        base_seconds=case["base_seconds"],
        factor=case["factor"],
        increment_seconds=case["increment_seconds"],
        max_delay=case["max_delay"],
        jitter=jitter,
        rand=rand,
    )


class ScheduleInvariantTests(unittest.TestCase):
    def test_length_matches_attempts(self):
        rand = random.Random(0)
        for _ in range(RUNS):
            case = random_case(rand)
            self.assertEqual(len(build(case)), case["attempts"])

    def test_delays_are_non_negative(self):
        rand = random.Random(1)
        for _ in range(RUNS):
            case = random_case(rand)
            self.assertTrue(all(delay >= 0 for delay in build(case)))

    def test_max_delay_is_respected(self):
        rand = random.Random(2)
        for _ in range(RUNS):
            case = random_case(rand)
            if case["max_delay"] is None:
                continue
            for delay in build(case):
                self.assertLessEqual(delay, case["max_delay"] + EPSILON)

    def test_same_seed_reproduces_schedule(self):
        rand = random.Random(3)
        for _ in range(RUNS):
            case = random_case(rand)
            if case["jitter"] is None:
                continue
            self.assertEqual(build(case), build(case))

    def test_unjittered_schedule_is_monotonic_non_decreasing(self):
        # factor >= 1 and increment >= 0 by construction, and a cap can only
        # flatten a non-decreasing sequence, never make it dip.
        rand = random.Random(4)
        for _ in range(RUNS):
            case = random_case(rand)
            case["jitter"] = None
            delays = build(case)
            for earlier, later in zip(delays, delays[1:]):
                self.assertLessEqual(earlier, later + EPSILON)

    def test_total_wait_matches_sum(self):
        rand = random.Random(5)
        for _ in range(RUNS):
            case = random_case(rand)
            delays = build(case)
            self.assertAlmostEqual(total_wait(delays), sum(delays))

    def test_full_jitter_never_exceeds_unjittered_value(self):
        rand = random.Random(6)
        for _ in range(RUNS):
            case = random_case(rand)
            case["jitter"] = "full"
            jittered = build(case)
            unjittered = build(dict(case, jitter=None))
            for j, u in zip(jittered, unjittered):
                self.assertLessEqual(j, u + EPSILON)

    def test_equal_jitter_stays_at_or_above_half_unjittered_value(self):
        rand = random.Random(7)
        for _ in range(RUNS):
            case = random_case(rand)
            case["jitter"] = "equal"
            jittered = build(case)
            unjittered = build(dict(case, jitter=None))
            for j, u in zip(jittered, unjittered):
                self.assertGreaterEqual(j, u / 2 - EPSILON)
                self.assertLessEqual(j, u + EPSILON)


if __name__ == "__main__":
    unittest.main()
