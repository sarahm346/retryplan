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
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("POLICY_A", "POLICY_B"),
        default=None,
        help="print two named policies from --config side by side instead of running one",
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


def resolve_named_policy_values(config: str, name: str) -> dict[str, object]:
    """DEFAULTS overridden by one named policy section, with no CLI flags in play.

    Used by --compare, where two policies are shown side by side and there is
    no single set of CLI flags that could unambiguously override both.
    """
    values = dict(DEFAULTS)
    values.update(load_policy(config, name))
    return values


def build_schedule_from_values(values: dict[str, object]) -> list[float]:
    rand = random.Random(values["seed"]) if values["jitter"] else None
    return build_schedule(
        strategy=values["strategy"],
        attempts=values["attempts"],
        base_seconds=values["base"],
        factor=values["factor"],
        increment_seconds=values["increment"],
        max_delay=values["max_delay"],
        jitter=values["jitter"],
        rand=rand,
    )


def format_compare_table(name_a: str, delays_a: list[float], name_b: str, delays_b: list[float]) -> str:
    width_a = max(len(name_a), 9)
    width_b = max(len(name_b), 9)
    header = f"attempt  {name_a:>{width_a}}  {name_b:>{width_b}}  diff"
    lines = [header]
    for attempt in range(1, max(len(delays_a), len(delays_b)) + 1):
        a = delays_a[attempt - 1] if attempt <= len(delays_a) else None
        b = delays_b[attempt - 1] if attempt <= len(delays_b) else None
        a_str = f"{a:>{width_a}.3f}" if a is not None else f"{'-':>{width_a}}"
        b_str = f"{b:>{width_b}.3f}" if b is not None else f"{'-':>{width_b}}"
        diff_str = f"{b - a:+.3f}" if a is not None and b is not None else "-"
        lines.append(f"{attempt:>7}  {a_str}  {b_str}  {diff_str}")
    lines.append("")
    lines.append(
        f"total wait: {name_a} {total_wait(delays_a):.3f}s, "
        f"{name_b} {total_wait(delays_b):.3f}s"
    )
    return "\n".join(lines)


def format_compare_json(name_a: str, delays_a: list[float], name_b: str, delays_b: list[float]) -> str:
    def payload(delays: list[float]) -> dict[str, object]:
        return {
            "attempts": [
                {"attempt": attempt, "delay_seconds": delay}
                for attempt, delay in enumerate(delays, start=1)
            ],
            "total_wait_seconds": total_wait(delays),
        }

    return json.dumps({"policies": {name_a: payload(delays_a), name_b: payload(delays_b)}}, indent=2)


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

    if args.compare:
        if not args.config:
            print("retryplan: --compare requires --config", file=sys.stderr)
            return 1
        name_a, name_b = args.compare
        try:
            values_a = resolve_named_policy_values(args.config, name_a)
            values_b = resolve_named_policy_values(args.config, name_b)
        except FileNotFoundError:
            print(f"retryplan: config file not found: {args.config}", file=sys.stderr)
            return 1
        except KeyError as exc:
            print(f"retryplan: no policy named {exc.args[0]!r} in {args.config}", file=sys.stderr)
            return 1
        except ValueError as exc:
            print(f"retryplan: {exc}", file=sys.stderr)
            return 1

        try:
            delays_a = build_schedule_from_values(values_a)
            delays_b = build_schedule_from_values(values_b)
        except ValueError as exc:
            print(f"retryplan: {exc}", file=sys.stderr)
            return 1

        if args.format == "json":
            print(format_compare_json(name_a, delays_a, name_b, delays_b))
        else:
            print(format_compare_table(name_a, delays_a, name_b, delays_b))
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

    try:
        delays = build_schedule_from_values(values)
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
