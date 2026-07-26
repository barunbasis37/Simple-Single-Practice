# TDD: Tests Defining Correct Bot Behavior

The deterministic part of the bot — [`static_checks.py`](../../.github/scripts/static_checks.py)
— was built test-first. Tests live in
[`.github/scripts/tests/test_static_checks.py`](../../.github/scripts/tests/test_static_checks.py).

## The cycle, as it actually happened

**Red.** `test_static_checks.py` was written against a `static_checks` module
that didn't exist yet. Running it failed immediately on import:

```
$ python .github/scripts/tests/test_static_checks.py
Traceback (most recent call last):
  ...
  from static_checks import (
ModuleNotFoundError: No module named 'static_checks'
```

**Green.** `static_checks.py` was then implemented purely to satisfy the
tests — `parse_diff`, `find_secrets`, `find_debug_statements`,
`find_todo_without_reference`, `find_missing_tests`, `run_all_checks`,
`format_findings_markdown`. Re-running:

```
$ python .github/scripts/tests/test_static_checks.py -v
...
Ran 16 tests in 0.001s

OK
```

## What the tests define as "correct behavior"

- **The assignment's own acceptance criterion** — flag a known bug in a
  sample PR — is `KnownBugSamplePrTests.test_flags_known_bug_sample_pr`. It
  feeds `run_all_checks` a synthetic diff that adds a hardcoded API key
  (`sk-live-...`) in a new untested `PaymentClient.cs`, and asserts the bot
  reports both a `security` finding and a `test-coverage` finding, with at
  least one `blocking` severity.
- Secret detection: hardcoded API keys, AWS access key IDs; ordinary code
  must **not** false-positive (`SecretDetectionTests`).
- Debug-statement / TODO noise are `style`-category, never `blocking`, and
  are skipped inside test files (`DebugStatementTests`, `TodoDetectionTests`).
- Missing-test detection: a changed non-trivial source file with no matching
  changed test file is flagged; trivial files (models, docs, config) and
  files that do have a matching test change are not
  (`MissingTestDetectionTests`).
- `parse_diff` correctly isolates added lines per file and keeps files
  separate (`ParseDiffTests`) — this is the foundation every other check
  depends on, so it's tested in isolation first.
- Output formatting groups findings by category with security/test-coverage
  (blocking-capable) before style (never-blocking), and reports a clear
  "no findings" message rather than an empty string (`FormatFindingsTests`).

## Why this part (and not the OpenAI call) is TDD'd

`static_checks.py` is deterministic — same diff in, same findings out —
which is exactly what unit tests are good at pinning down. The OpenAI-backed
half of the review ([`openai_pr_review.py`](../../.github/scripts/openai_pr_review.py))
is nondeterministic by nature; testing it meaningfully would mean testing
prompt-construction and response-parsing (which *are* deterministic and
worth covering) rather than asserting on model output text. That's a
reasonable follow-up, noted here rather than done, to keep this pass
focused on the acceptance criterion the assignment actually asks for.

## Running the tests

```
python .github/scripts/tests/test_static_checks.py -v
```

No install step, no network access, no API key required — intentional, per
[03-context-management.md](03-context-management.md)'s stdlib-only design.
