"""Pure functions for computing retry delay sequences.

Nothing in here reads a clock, sleeps, or touches the network. Jitter
functions take a random.Random instance as an argument instead of
reaching for the `random` module globally, so a test can pass a seeded
generator and get a fixed sequence back.
"""

from __future__ import annotations

import random


def fixed_delay(base_seconds: float) -> float:
    """Delay is the same on every attempt."""
    if base_seconds < 0:
        raise ValueError("base_seconds must be >= 0")
    return base_seconds


def linear_delay(attempt: int, base_seconds: float, increment_seconds: float) -> float:
    """Delay grows by a fixed amount per attempt: base + increment * (attempt - 1)."""
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    if base_seconds < 0 or increment_seconds < 0:
        raise ValueError("base_seconds and increment_seconds must be >= 0")
    return base_seconds + increment_seconds * (attempt - 1)


def exponential_delay(
    attempt: int,
    base_seconds: float,
    factor: float = 2.0,
    max_delay: float | None = None,
) -> float:
    """Delay grows by `factor` each attempt: base * factor^(attempt - 1)."""
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    if base_seconds < 0:
        raise ValueError("base_seconds must be >= 0")
    if factor < 1:
        raise ValueError("factor must be >= 1")
    delay = base_seconds * (factor ** (attempt - 1))
    if max_delay is not None:
        delay = min(delay, max_delay)
    return delay


def apply_full_jitter(delay: float, rand: random.Random) -> float:
    """AWS "full jitter": uniform random value between 0 and delay."""
    if delay < 0:
        raise ValueError("delay must be >= 0")
    return rand.uniform(0, delay)


def apply_equal_jitter(delay: float, rand: random.Random) -> float:
    """AWS "equal jitter": half the delay is fixed, half is randomized."""
    if delay < 0:
        raise ValueError("delay must be >= 0")
    half = delay / 2
    return half + rand.uniform(0, half)


def decorrelated_jitter(
    previous_delay: float,
    base_seconds: float,
    max_delay: float,
    rand: random.Random,
) -> float:
    """AWS "decorrelated jitter": next delay depends on the previous one."""
    if previous_delay < 0 or base_seconds < 0 or max_delay < 0:
        raise ValueError("delays must be >= 0")
    low = base_seconds
    high = max(base_seconds, previous_delay * 3)
    return min(max_delay, rand.uniform(low, high))


STRATEGIES = ("fixed", "linear", "exponential")
JITTER_MODES = ("full", "equal", "decorrelated")


def build_schedule(
    strategy: str,
    attempts: int,
    base_seconds: float,
    factor: float = 2.0,
    increment_seconds: float = 0.0,
    max_delay: float | None = None,
    jitter: str | None = None,
    rand: random.Random | None = None,
) -> list[float]:
    """Return the list of delays a retry loop would use, attempt 1..attempts.

    `rand` must be supplied whenever `jitter` is set, so callers control
    determinism instead of this function reaching for global random state.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy: {strategy!r}, expected one of {STRATEGIES}")
    if jitter is not None and jitter not in JITTER_MODES:
        raise ValueError(f"unknown jitter mode: {jitter!r}, expected one of {JITTER_MODES}")
    if jitter is not None and rand is None:
        raise ValueError("rand is required when jitter is set")

    delays: list[float] = []
    previous = base_seconds
    for attempt in range(1, attempts + 1):
        if strategy == "fixed":
            raw = fixed_delay(base_seconds)
        elif strategy == "linear":
            raw = linear_delay(attempt, base_seconds, increment_seconds)
            if max_delay is not None:
                raw = min(raw, max_delay)
        else:
            raw = exponential_delay(attempt, base_seconds, factor, max_delay)

        if jitter == "full":
            raw = apply_full_jitter(raw, rand)
        elif jitter == "equal":
            raw = apply_equal_jitter(raw, rand)
        elif jitter == "decorrelated":
            cap = max_delay if max_delay is not None else raw * 3 or base_seconds
            raw = decorrelated_jitter(previous, base_seconds, cap, rand)

        delays.append(raw)
        previous = raw

    return delays


def total_wait(delays: list[float]) -> float:
    """Sum of a delay schedule, useful for answering "worst case, how long?"."""
    return sum(delays)
