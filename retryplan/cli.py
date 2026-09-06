"""Command-line entry point. Parses args, calls into policy.py, prints a table."""

from __future__ import annotations

import argparse
import json
import random
import sys

from retryplan.config import list_policies, load_policy
from retryplan.policy import JITTER_MODES, STRATEGIES, build_schedule, total_wait

# Applied when a value comes from neither a CLI flag nor --policy. Flags for
# these fields default to argparse.SUPPRESS instead so we can tell whether
# the user actually passed one, which is what makes --policy overridable.
DEFAULTS = {
    "strategy": "exponential",
    "attempts": 6,
    "base": 0.5,
    "factor": 2.0,
    "increment": 1.0,
    "max_delay": None,
    "jitter": None,
    "seed": None,
}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="retryplan",
        description="Preview the delay schedule a retry policy would produce.",
    )
    parser.add_argument(
        "--strategy",
        choices=STRATEGIES,
        default=argparse.SUPPRESS,
        help="backoff strategy (default: exponential)",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=argparse.SUPPRESS,
        help="number of retry attempts to compute (default: 6)",
    )
    parser.add_argument(
        "--base",
        type=float,
        default=argparse.SUPPRESS,
        help="base delay in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--factor",
        type=float,
        default=argparse.SUPPRESS,
        help="multiplier per attempt for exponential strategy (default: 2.0)",
    )
    parser.add_argument(
        "--increment",
        type=float,
        default=argparse.SUPPRESS,
        help="added delay per attempt for linear strategy (default: 1.0)",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=argparse.SUPPRESS,
        help="cap each delay at this many seconds (default: no cap)",
    )
    parser.add_argument(
        "--jitter",
        choices=JITTER_MODES,
        default=argparse.SUPPRESS,
        help="jitter mode to apply on top of the raw delay (default: none)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=argparse.SUPPRESS,
        help="seed for the jitter random generator, for reproducible output",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="output format (default: table)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="path to a config file holding saved policies (INI format)",
    )
    parser.add_argument(
        "--policy",
        default=None,
        help="name of a saved policy to load from --config; other flags override its values",
    )
    parser.add_argument(
        "--list-policies",
        action="store_true",
        help="print the policy names defined in --config and exit",
    )
    return parser.parse_args(argv)


def resolve_policy_values(args: argparse.Namespace) -> dict[str, object]:
    """Merge built-in defaults, a --policy from --config, and explicit flags.

    Precedence, low to high: DEFAULTS, then the named policy (if any), then
    whatever the user actually typed on the command line.
    """
    values = dict(DEFAULTS)
    if args.policy:
        if not args.config:
            raise ValueError("--policy requires --config")
        values.update(load_policy(args.config, args.policy))
    for key in DEFAULTS:
        if hasattr(args, key):
            values[key] = getattr(args, key)
    return values


def format_table(delays: list[float]) -> str:
    lines = ["attempt  delay (s)"]
    for attempt, delay in enumerate(delays, start=1):
        lines.append(f"{attempt:>7}  {delay:>9.3f}")
    lines.append("")
    lines.append(f"total wait: {total_wait(delays):.3f}s")
    return "\n".join(lines)


def format_json(delays: list[float]) -> str:
    payload = {
        "attempts": [
            {"attempt": attempt, "delay_seconds": delay}
            for attempt, delay in enumerate(delays, start=1)
        ],
        "total_wait_seconds": total_wait(delays),
    }
    return json.dumps(payload, indent=2)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.list_policies:
        if not args.config:
            print("retryplan: --list-policies requires --config", file=sys.stderr)
            return 1
        try:
            names = list_policies(args.config)
        except FileNotFoundError:
            print(f"retryplan: config file not found: {args.config}", file=sys.stderr)
            return 1
        for name in names:
            print(name)
        return 0

    try:
        values = resolve_policy_values(args)
    except FileNotFoundError:
        print(f"retryplan: config file not found: {args.config}", file=sys.stderr)
        return 1
    except KeyError as exc:
        print(f"retryplan: no policy named {exc.args[0]!r} in {args.config}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"retryplan: {exc}", file=sys.stderr)
        return 1

    rand = random.Random(values["seed"]) if values["jitter"] else None

    try:
        delays = build_schedule(
            strategy=values["strategy"],
            attempts=values["attempts"],
            base_seconds=values["base"],
            factor=values["factor"],
            increment_seconds=values["increment"],
            max_delay=values["max_delay"],
            jitter=values["jitter"],
            rand=rand,
        )
    except ValueError as exc:
        print(f"retryplan: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(format_json(delays))
    else:
        print(format_table(delays))
    return 0


if __name__ == "__main__":
    sys.exit(main())
