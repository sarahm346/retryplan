"""Load named retry policies out of an INI-style config file.

The point is to stop retyping the same --strategy/--base/--factor flags for
policies you check often. A config file holds one section per named policy;
the CLI loads a section as a set of defaults that individual flags can still
override.
"""

from __future__ import annotations

import configparser
from pathlib import Path

# Maps config file keys (hyphenated, matching the CLI flag names) to the
# type used to parse them out of the string values configparser hands back.
FIELDS = {
    "strategy": str,
    "attempts": int,
    "base": float,
    "factor": float,
    "increment": float,
    "max-delay": float,
    "jitter": str,
    "seed": int,
}


def load_policy(path: str, name: str) -> dict[str, object]:
    """Read one named section out of a policy config file.

    Returns a dict keyed by the CLI's underscore-style field names (so
    "max-delay" in the file becomes "max_delay" here), ready to merge into
    the CLI's own defaults.
    """
    if not Path(path).is_file():
        raise FileNotFoundError(path)

    parser = configparser.ConfigParser()
    parser.read(path)
    if not parser.has_section(name):
        raise KeyError(name)

    values: dict[str, object] = {}
    for key, raw_value in parser.items(name):
        if key not in FIELDS:
            raise ValueError(f"unknown policy field {key!r} in section [{name}]")
        values[key.replace("-", "_")] = FIELDS[key](raw_value)
    return values


def list_policies(path: str) -> list[str]:
    """Names of every policy section defined in a config file, in file order."""
    if not Path(path).is_file():
        raise FileNotFoundError(path)

    parser = configparser.ConfigParser()
    parser.read(path)
    return parser.sections()
