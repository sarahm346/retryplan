# retryplan

Every time I add retry logic to something, I end up doing the same napkin
math: if the base delay is 0.5s and it doubles each attempt, how long until
the 6th retry, and does that blow past my timeout budget? `retryplan` just
answers that from the command line instead of me writing a throwaway script
each time.

## Usage

Exponential backoff, doubling from 0.5s, 6 attempts:

```
$ retryplan --strategy exponential --base 0.5 --factor 2 --attempts 6
attempt  delay (s)
      1      0.500
      2      1.000
      3      2.000
      4      4.000
      5      8.000
      6     16.000

total wait: 31.500s
```

Cap it so nothing waits longer than 5 seconds:

```
$ retryplan --strategy exponential --base 0.5 --factor 2 --attempts 6 --max-delay 5
attempt  delay (s)
      1      0.500
      2      1.000
      3      2.000
      4      4.000
      5      5.000
      6      5.000

total wait: 17.500s
```

Add jitter so you can see roughly what a jittered schedule looks like
(pass `--seed` to get the same output twice):

```
$ retryplan --strategy exponential --base 0.5 --jitter full --seed 1
```

Decorrelated jitter is different from full/equal jitter: each delay is
drawn between the base delay and three times the *previous* delay, rather
than being derived from the raw backoff value for that attempt. That means
it can grow without bound unless you also pass `--max-delay`:

```
$ retryplan --strategy exponential --base 0.5 --jitter decorrelated --max-delay 20 --seed 1
```

As long as `--max-delay` is set, `--factor` and `--increment` have no effect
on a decorrelated schedule, since each delay is computed from the previous
delay and the cap rather than from the strategy's own growth curve; only
`--base`, `--max-delay`, and `--attempts` matter. (Leave `--max-delay` unset
and the first delay falls back to the strategy's raw value, so those flags
briefly matter again -- another reason to always pass `--max-delay` with
decorrelated jitter.)

Linear backoff (fixed increment per attempt) and plain fixed-delay retries
are also supported via `--strategy linear` and `--strategy fixed`. Run
`retryplan --help` for the full option list.

Pass `--format json` to get the same schedule as JSON, for feeding into
another script instead of reading it off a terminal:

```
$ retryplan --strategy fixed --base 1 --attempts 3 --format json
{
  "attempts": [
    {
      "attempt": 1,
      "delay_seconds": 1.0
    },
    {
      "attempt": 2,
      "delay_seconds": 1.0
    },
    {
      "attempt": 3,
      "delay_seconds": 1.0
    }
  ],
  "total_wait_seconds": 3.0
}
```

## Saved policies

Typing the same flags for a policy you check often gets old. Put it in an
INI-style config file instead, one section per named policy:

```ini
[prod-api]
strategy = exponential
base = 0.5
factor = 2
attempts = 6
max-delay = 10
jitter = full
seed = 42
```

Then load it with `--config` and `--policy`:

```
$ retryplan --config policies.ini --policy prod-api
```

Any other flag on the command line overrides the value from the policy, so
you can check a variant without editing the file:

```
$ retryplan --config policies.ini --policy prod-api --attempts 10
```

`--list-policies` prints the section names in a config file without running
anything:

```
$ retryplan --config policies.ini --list-policies
prod-api
```

## Why

Backoff math is easy to get wrong in ways that only show up in production:
forgetting the cap, doubling one attempt too many, jitter that's too wide
or too narrow. This tool lets you eyeball a schedule before you commit to
it in code.

## Install

No dependencies beyond the Python standard library.

```
pip install -e .
```

or just run it in place:

```
python -m retryplan.cli --strategy fixed --base 1 --attempts 3
```

## Library use

The delay math lives in `retryplan/policy.py` as plain functions with no
I/O, so it can be imported and used directly:

```python
from retryplan.policy import build_schedule

delays = build_schedule("exponential", attempts=5, base_seconds=0.5, factor=2.0)
```

## Development

```
python -m unittest discover -s tests
```

## License

MIT, see LICENSE.
