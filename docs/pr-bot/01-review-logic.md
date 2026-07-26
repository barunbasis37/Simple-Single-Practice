# Review Logic Definition

This document is the precise definition of what the PR bot checks. Everything
downstream (subagent prompts, static checks, CI wiring) implements this list —
if a check isn't traceable to a line here, it shouldn't be in the bot, because
undefined checks are what make review bots noisy instead of useful.

## Categories checked, in priority order

### 1. Logic errors (highest priority — blocks merge)
- Off-by-one / boundary errors in changed control flow.
- Null/None handling on values that can plausibly be null given the diff's
  own types (e.g. a `string?` used without a guard).
- Contradictions between a function's name/docstring and what it does.
- Changed behavior that isn't reflected in any updated test.

### 2. Missing tests (blocks merge for non-trivial logic changes)
- New or changed public methods/endpoints with no corresponding new/changed
  test in the diff.
- Bug fixes that don't add a regression test reproducing the original bug.
- Definition of "non-trivial": anything beyond property getters/setters,
  pure data classes, or config/docs changes.

### 3. Security issues (blocks merge)
- Hardcoded secrets, tokens, connection strings, or API keys.
- Unsanitized input reaching a shell command, SQL string, or HTML output
  (command injection, SQL injection, XSS).
- Newly added dependencies pulled from unpinned/untrusted sources.
- Overly broad permissions (e.g. a workflow requesting `write` access it
  doesn't use).

### 4. Style/consistency (comment only — never blocks merge)
- Deviation from the file's existing naming/formatting conventions.
- Dead code, commented-out blocks, leftover debug prints, stray `TODO`s
  without an issue reference.
- Duplication that a small refactor would remove (noted, not required).

## What the bot explicitly does NOT do

- Rewrite code style to match a reviewer's personal taste — only flags
  deviation from *this repo's own* existing conventions.
- Block on category 4 findings. Style comments are informational.
- Guess at intent beyond what the diff and PR description state. If context
  is missing, the bot says so instead of inventing a rationale.

## Output contract

Every review produced by the bot (subagent-authored comment, per subagent
finding) must be traceable to exactly one category above. A finding that
doesn't fit a category is dropped — it's noise, not a signal.

The final PR comment always ends with an explicit recommendation, one of:

- `Merge` — no category 1–3 findings.
- `Merge with changes` — only category 4 findings, or category 1–3 findings
  the author has already addressed in the same PR.
- `Do not merge` — at least one open category 1–3 finding.

This mirrors (and is implemented by) the recommendation contract already
built into [`openai_pr_review.py`](../../.github/scripts/openai_pr_review.py).
