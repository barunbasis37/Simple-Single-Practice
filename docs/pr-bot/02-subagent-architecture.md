# Subagent Architecture

## Why subagents at all

A single "read the whole diff and comment" prompt either (a) reads full file
contents for every changed file and blows up the context window on anything
but a tiny PR, or (b) skims and misses things. Splitting the work lets each
piece stay narrow: one agent's job is *find the relevant context*, another's
is *decide what's worth checking*, and the rest each check exactly one
category from [01-review-logic.md](01-review-logic.md). Narrow jobs produce
outputs that are easy to verify — a reviewer that only ever talks about
security is easy to sanity-check; one that talks about everything isn't.

## The four roles

```
                    ┌─────────────────┐
   PR diff  ──────▶ │  Explore agent   │  gathers context, returns a
                    │  (pr-explorer)   │  compact structured summary
                    └────────┬─────────┘
                             │ summary (not full files)
                             ▼
                    ┌─────────────────┐
                    │   Plan agent     │  decides WHICH reviewers are
                    │ (built-in Plan)  │  worth running for this diff
                    └────────┬─────────┘
                             │ scoped review plan
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌────────────────┐ ┌──────────────┐ ┌────────────────────┐
     │ pr-security-    │ │ pr-           │ │ pr-test-coverage-   │
     │ reviewer        │ │ correctness-  │ │ reviewer            │
     │ (category 3)    │ │ reviewer      │ │ (category 2)        │
     │                 │ │ (cat. 1 + 4)  │ │                     │
     └────────┬────────┘ └──────┬───────┘ └──────────┬──────────┘
              │                  │                     │
              └──────────────────┼─────────────────────┘
                                  ▼
                      ┌───────────────────────┐
                      │   Aggregation step     │  merges findings,
                      │ (orchestrator session  │  drops anything that
                      │  or CI script)         │  doesn't map to a
                      └───────────────────────┘  category, emits the
                                                  Merge/Do-not-merge line
```

### 1. Explore agent — [`.claude/agents/pr-explorer.md`](../../.claude/agents/pr-explorer.md)
Read-only. Given a base/head ref, it lists changed files, pulls just the
diff hunks (not whole files), and only opens full file content when a hunk
is ambiguous without surrounding code (e.g. a one-line change inside a large
method). It returns a short Markdown summary: what changed, why (from commit
messages/PR description), which files have no corresponding test change.
This exists so the review agents below never have to re-derive "what even
changed here" themselves — that work happens once.

### 2. Plan agent — built-in `Plan` agent type
Reused as-is rather than rebuilt: its job (decide implementation strategy /
what needs attention) maps directly onto "decide what's worth reviewing."
Given the Explore summary, it decides which of the three review subagents
below are actually relevant — e.g. a docs-only PR skips the security and
test-coverage reviewers entirely. This exists to avoid paying for (and
reading the output of) reviewers that have nothing to say.

### 3. Review subagents — narrow, one category each
- [`pr-security-reviewer.md`](../../.claude/agents/pr-security-reviewer.md) — category 3 only (secrets, injection, unsafe permissions).
- [`pr-correctness-reviewer.md`](../../.claude/agents/pr-correctness-reviewer.md) — category 1 (logic errors) plus lightweight category 4 (style) notes.
- [`pr-test-coverage-reviewer.md`](../../.claude/agents/pr-test-coverage-reviewer.md) — category 2 only (missing/insufficient tests).

Each exists as its own subagent (rather than one combined reviewer) so a
noisy or wrong finding is traceable to one narrow prompt and easy to fix
without risking regressions in the other categories.

### 4. Aggregation
There is no separate "aggregator subagent" — merging findings is mechanical
(concatenate, dedupe, drop anything uncategorized, compute the merge
recommendation from the highest-severity open finding) so it doesn't need an
LLM call. Interactively this is the orchestrating Claude Code session; in CI
it's [`openai_pr_review.py`](../../.github/scripts/openai_pr_review.py) plus
[`static_checks.py`](../../.github/scripts/static_checks.py) (see
[06-context-management.md](06-context-management.md) for why the deployed
bot runs one consolidated LLM pass instead of four live subagent calls per
PR).
