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

Linear backoff (fixed increment per attempt) and plain fixed-delay retries
are also supported via `--strategy linear` and `--strategy fixed`. Run
`retryplan --help` for the full option list.

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
