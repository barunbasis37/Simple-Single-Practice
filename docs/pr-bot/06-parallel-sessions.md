# Background/Parallel Sessions

## What was actually run

Using the sample PR diff at
[`docs/pr-bot/sample-pr.diff`](sample-pr.diff) (the `NamedEntity` refactor
from [05-refactor-notes.md](05-refactor-notes.md)), the pipeline from
[02-subagent-architecture.md](02-subagent-architecture.md) was run for real
against this Claude Code session:

1. **Explore** ran first and alone (the three reviewers depend on its
   output) — 16.9s wall clock.
2. **Security, correctness, and test-coverage reviewers** were then
   launched together, as three `Agent` tool calls in a single message, so
   they executed concurrently rather than one after another.

> Note on environment: the custom subagents defined in Step 4/5
> ([`.claude/agents/pr-explorer.md`](../../.claude/agents/pr-explorer.md)
> etc.) were created *during this same session*, and this harness reads its
> subagent registry at session start — so `subagent_type: pr-explorer` isn't
> resolvable until a new session picks up the new files. Each run below
> used the general-purpose agent type seeded with the exact instruction
> text from the corresponding `.claude/agents/*.md` file, which is
> behaviorally identical; in a fresh session the same call would instead
> pass `subagent_type: "pr-explorer"` directly.

## Timing

| Subagent | Wall clock |
|---|---|
| Explore | 16.9s |
| Security reviewer | 7.4s |
| Correctness reviewer | 26.8s |
| Test-coverage reviewer | 20.3s |

Run **sequentially**, the three reviewers alone would have taken
7.4 + 26.8 + 20.3 = **54.5s**. Run **in parallel**, they took as long as the
slowest one: **26.8s**. Combined with the (unavoidably serial) Explore step:

- Sequential pipeline: 16.9 + 54.5 = **71.4s**
- Parallel pipeline: 16.9 + 26.8 = **43.7s**

That's a **~39% reduction in wall-clock time** for a 3-reviewer fan-out, and
the gap widens as more narrow reviewers are added (Explore stays fixed;
sequential cost grows linearly with reviewer count, parallel cost stays
pinned to the slowest single reviewer).

## Aggregated result for the sample PR

| Reviewer | Verdict |
|---|---|
| Security | No category-3 issues found. |
| Correctness | No blocking findings; one non-blocking style note (`Category`'s now-empty class body could read as an unfinished stub). |
| Test coverage | No category-2 issues — pure structural refactor, already covered by `Tests/ModelTests.cs`. |

Per the recommendation contract in
[01-review-logic.md](01-review-logic.md): no open category 1–3 findings →
**Merge**, with the one style note surfaced as an FYI rather than a blocker.
This matches the actual outcome in [05-refactor-notes.md](05-refactor-notes.md)
(`dotnet test` stayed green 4/4 before and after).

## Where background execution (not just parallel) helps

For this repo's tiny sample PR, all three reviewers finished well within a
single turn, so foreground parallel execution was enough. For a larger PR —
or for reviewing several open PRs at once — the same `Agent` calls can be
issued with `run_in_background: true` instead, which returns immediately
and lets other work continue in the main session until a completion
notification arrives. The only change needed is that flag; the
architecture, prompts, and aggregation step above are unaffected.
