"""Command-line entry point. Parses args, calls into policy.py, prints a table."""

from __future__ import annotations

import argparse
import random
import sys

from retryplan.policy import JITTER_MODES, STRATEGIES, build_schedule, total_wait


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="retryplan",
        description="Preview the delay schedule a retry policy would produce.",
    )
    parser.add_argument(
        "--strategy",
        choices=STRATEGIES,
        default="exponential",
        help="backoff strategy (default: exponential)",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=6,
        help="number of retry attempts to compute (default: 6)",
    )
    parser.add_argument(
        "--base",
        type=float,
        default=0.5,
        help="base delay in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--factor",
        type=float,
        default=2.0,
        help="multiplier per attempt for exponential strategy (default: 2.0)",
    )
    parser.add_argument(
        "--increment",
        type=float,
        default=1.0,
        help="added delay per attempt for linear strategy (default: 1.0)",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=None,
        help="cap each delay at this many seconds (default: no cap)",
    )
    parser.add_argument(
        "--jitter",
        choices=JITTER_MODES,
        default=None,
        help="jitter mode to apply on top of the raw delay (default: none)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="seed for the jitter random generator, for reproducible output",
    )
    return parser.parse_args(argv)


def format_table(delays: list[float]) -> str:
    lines = ["attempt  delay (s)"]
    for attempt, delay in enumerate(delays, start=1):
        lines.append(f"{attempt:>7}  {delay:>9.3f}")
    lines.append("")
    lines.append(f"total wait: {total_wait(delays):.3f}s")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    rand = random.Random(args.seed) if args.jitter else None

    try:
        delays = build_schedule(
            strategy=args.strategy,
            attempts=args.attempts,
            base_seconds=args.base,
            factor=args.factor,
            increment_seconds=args.increment,
            max_delay=args.max_delay,
            jitter=args.jitter,
            rand=rand,
        )
    except ValueError as exc:
        print(f"retryplan: {exc}", file=sys.stderr)
        return 1

    print(format_table(delays))
    return 0


if __name__ == "__main__":
    sys.exit(main())
